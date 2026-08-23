"""Shadow analysis runner — orchestrates the new fact/technique/strategy path.

Runs alongside the existing detector system. Does NOT affect production behavior.
If the new path fails, the existing analysis continues normally.
"""
import ast
import time
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    MatchOutcome, EXTRACTOR_VERSION,
)
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups


def run_shadow_analysis(
    code: str,
    solution_groups: Optional[list] = None,
) -> Optional[dict]:
    """Run the shadow analysis path on submitted code.

    This function:
    1. Parses the code into AST
    2. Extracts structural facts
    3. Detects techniques from facts
    4. Evaluates strategies from techniques
    5. Evaluates solution-group satisfaction
    6. Returns the match outcome as a serializable dict

    If any step fails, returns None (graceful degradation).
    The existing production analysis is NOT affected.
    """
    try:
        t0 = time.perf_counter()

        # Step 1: Parse code into AST
        tree = ast.parse(code)

        # Step 2: Extract structural facts
        facts = extract_structural_facts(tree)

        # Step 3: Detect techniques
        technique_evidence = detect_techniques(facts)

        # Step 4: Evaluate strategies
        strategy_evidence = evaluate_strategies(technique_evidence, facts)

        # Step 5: Evaluate solution groups (matching)
        if solution_groups:
            match_outcome = evaluate_solution_groups(
                solution_groups, technique_evidence, strategy_evidence, facts
            )
        else:
            # No solution groups → UNRESOLVED
            match_outcome = MatchOutcome(
                outcome="UNRESOLVED",
                authority_tier="unknown",
                technique_evidence=technique_evidence,
                strategy_evidence=strategy_evidence,
                structural_facts=facts,
                reasoning=["No solution groups provided for matching"],
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "structural_facts": [_fact_to_dict(f) for f in facts],
            "technique_evidence": [_tech_to_dict(t) for t in technique_evidence],
            "strategy_evidence": [_strat_to_dict(s) for s in strategy_evidence],
            "match_outcome": _outcome_to_dict(match_outcome),
            "extractor_version": EXTRACTOR_VERSION,
            "elapsed_ms": round(elapsed_ms, 2),
        }

    except Exception as e:
        # Graceful degradation: shadow failure must not affect production
        return None


def _fact_to_dict(fact) -> dict:
    """Convert a StructuralFact to a serializable dict."""
    return {
        "fact_id": fact.fact_id,
        "fact_type": fact.fact_type,
        "ast_ref": fact.ast_ref,
        "attributes": fact.attributes,
        "extractor_version": fact.extractor_version,
    }


def _tech_to_dict(tech) -> dict:
    """Convert a TechniqueEvidence to a serializable dict."""
    return {
        "technique_id": tech.technique_id,
        "technique_version": tech.technique_version,
        "supporting_fact_ids": tech.supporting_fact_ids,
        "presence_confidence": tech.presence_confidence,
        "centrality": tech.centrality,
    }


def _strat_to_dict(strat) -> dict:
    """Convert a StrategyEvidence to a serializable dict."""
    return {
        "strategy_id": strat.strategy_id,
        "strategy_version": strat.strategy_version,
        "supporting_technique_ids": strat.supporting_technique_ids,
        "supporting_fact_ids": strat.supporting_fact_ids,
        "confidence": strat.confidence,
        "problem_context_signals": strat.problem_context_signals,
    }


def _outcome_to_dict(outcome) -> dict:
    """Convert a MatchOutcome to a serializable dict."""
    return {
        "outcome": outcome.outcome,
        "satisfied_group_ids": outcome.satisfied_group_ids,
        "authority_tier": outcome.authority_tier,
        "primary_strategy": outcome.primary_strategy,
        "reasoning": outcome.reasoning,
        "technique_count": len(outcome.technique_evidence),
        "strategy_count": len(outcome.strategy_evidence),
        "fact_count": len(outcome.structural_facts),
    }
