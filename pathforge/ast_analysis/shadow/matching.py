"""Solution-group satisfaction matching with authority gating.

Evaluates solution groups against technique and strategy evidence.
Produces CONFIRMED / UNRESOLVED / CONTRADICTED outcomes.

Authority rules:
- bootstrap / llm_proposed must NEVER produce authoritative CONTRADICTED
- low-authority contradiction becomes UNRESOLVED
- UNRESOLVED must not trigger ELO, gaps, or recommendations
"""
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    TechniqueEvidence, StrategyEvidence, MatchOutcome, StructuralFact,
)


# Authority tiers that can produce authoritative outcomes
_AUTHORITATIVE_TIERS = {"structurally_observed", "externally_listed", "editorial"}


def evaluate_solution_groups(
    solution_groups: list[dict],
    technique_evidence: list[TechniqueEvidence],
    strategy_evidence: list[StrategyEvidence],
    facts: list[StructuralFact],
) -> MatchOutcome:
    """Evaluate solution groups against derived evidence.

    Args:
        solution_groups: List of solution group definitions with
            required/optional/excluded/threshold/authority_tier.
        technique_evidence: Detected technique evidence.
        strategy_evidence: Detected strategy evidence.
        facts: Structural facts from extraction.

    Returns:
        MatchOutcome with outcome = CONFIRMED | UNRESOLVED | CONTRADICTED
    """
    if not solution_groups:
        return MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="unknown",
            technique_evidence=technique_evidence,
            strategy_evidence=strategy_evidence,
            structural_facts=facts,
            reasoning=["No solution groups provided"],
        )

    detected_techniques = {e.technique_id: e for e in technique_evidence}
    detected_strategies = {e.strategy_id: e for e in strategy_evidence}

    best_outcome = "UNRESOLVED"
    best_group_id = None
    best_satisfaction = 0.0
    best_authority = "unknown"
    reasoning = []

    for group in solution_groups:
        result = _evaluate_single_group(
            group, detected_techniques, detected_strategies
        )
        group_id = group.get("id", "unknown")
        group_satisfaction = result["satisfaction"]
        group_outcome = result["outcome"]
        group_authority = group.get("authority_tier", "bootstrap")

        reasoning.append(
            f"Group {group_id}: satisfaction={group_satisfaction:.3f}, "
            f"raw_outcome={group_outcome}, authority={group_authority}"
        )

        # Authority-gated outcome for this group
        if group_outcome == "satisfied":
            group_final = "CONFIRMED"
        elif group_outcome == "contradicted":
            if group_authority in _AUTHORITATIVE_TIERS:
                group_final = "CONTRADICTED"
            else:
                group_final = "UNRESOLVED"
                reasoning.append(
                    f"Group {group_id}: CONTRADICTED downgraded to UNRESOLVED "
                    f"(authority={group_authority} is not authoritative)"
                )
        else:
            group_final = "UNRESOLVED"

        # Priority: CONTRADICTED > CONFIRMED > UNRESOLVED
        # For same level, prefer higher satisfaction
        priority = {"CONTRADICTED": 3, "CONFIRMED": 2, "UNRESOLVED": 1}
        cur_priority = priority.get(best_outcome, 0)
        new_priority = priority.get(group_final, 0)

        if new_priority > cur_priority or (
            new_priority == cur_priority and group_satisfaction > best_satisfaction
        ):
            best_outcome = group_final
            best_satisfaction = group_satisfaction
            best_group_id = group_id
            best_authority = group_authority

    return MatchOutcome(
        outcome=best_outcome,
        satisfied_group_ids=[best_group_id] if best_group_id and best_outcome == "CONFIRMED" else [],
        authority_tier=best_authority,
        technique_evidence=technique_evidence,
        strategy_evidence=strategy_evidence,
        structural_facts=facts,
        primary_strategy=_get_primary_strategy(strategy_evidence),
        reasoning=reasoning,
    )


def _evaluate_single_group(
    group: dict,
    detected_techniques: dict,
    detected_strategies: dict,
) -> dict:
    """Evaluate a single solution group against detected evidence.

    Returns dict with:
        - outcome: "satisfied" | "unsatisfied" | "contradicted"
        - satisfaction: float [0.0, 1.0]
    """
    required = group.get("required", [])
    optional = group.get("optional", [])
    excluded = group.get("excluded", [])
    threshold = group.get("threshold", 0.5)

    # Check excluded evidence — if present, contradicts
    for exc in excluded:
        if exc in detected_techniques or exc in detected_strategies:
            return {"outcome": "contradicted", "satisfaction": 0.0}

    # Check required evidence — all must be present with sufficient confidence
    required_met = 0
    for req in required:
        if req in detected_techniques:
            te = detected_techniques[req]
            if te.presence_confidence >= 0.5:  # Minimum confidence threshold
                required_met += 1
        elif req in detected_strategies:
            se = detected_strategies[req]
            if se.confidence >= 0.5:
                required_met += 1

    if required and required_met < len(required):
        return {"outcome": "unsatisfied", "satisfaction": 0.0}

    # Compute satisfaction score
    satisfaction = 0.0

    if required:
        # Average confidence of matched required evidence
        req_confs = []
        for req in required:
            if req in detected_techniques:
                req_confs.append(detected_techniques[req].presence_confidence)
            elif req in detected_strategies:
                req_confs.append(detected_strategies[req].confidence)
        if req_confs:
            satisfaction = sum(req_confs) / len(req_confs)

    # Boost from optional evidence
    optional_boost = 0.0
    optional_count = 0
    for opt in optional:
        if opt in detected_techniques:
            optional_boost += detected_techniques[opt].presence_confidence * 0.15
            optional_count += 1
        elif opt in detected_strategies:
            optional_boost += detected_strategies[opt].confidence * 0.15
            optional_count += 1

    satisfaction = min(1.0, satisfaction + optional_boost)

    # Apply threshold
    if satisfaction >= threshold:
        return {"outcome": "satisfied", "satisfaction": satisfaction}
    else:
        return {"outcome": "unsatisfied", "satisfaction": satisfaction}


def _get_primary_strategy(strategy_evidence: list[StrategyEvidence]) -> Optional[str]:
    """Derive the primary strategy projection.

    Returns the strategy with highest confidence, or None.
    """
    if not strategy_evidence:
        return None
    best = max(strategy_evidence, key=lambda e: e.confidence)
    if best.confidence >= 0.7:
        return best.strategy_id
    return None
