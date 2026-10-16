"""Primary-role gated scorer.

Adjusts pattern scores based on evidence that the pattern is the
PRIMARY algorithmic strategy vs incidental implementation behavior.

Architecture:
  structural_score (from scorer.py) × primary_role_gate = final_score

The gate is a multiplier in range [0.0, 1.0]:
  1.0 = pattern is clearly primary → full structural score
  0.5 = pattern is somewhat relevant → reduced score
  0.0 = pattern is incidental / bookkeeping → suppress score

This module is designed to work alongside the existing scorer, NOT replace it.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from .features import SemanticFeatures, PrimaryRoleFeatures
from .scorer import PatternScore, score_patterns


@dataclass
class RoleGateEvidence:
    """Evidence for why a gate value was applied."""
    signal: str
    impact: float  # positive = promote, negative = suppress
    description: str


@dataclass
class PrimaryRoleResult:
    """Result of primary-role gating."""
    pattern: str
    structural_score: float
    gate: float
    final_score: float
    is_primary: bool  # gate >= 0.5
    gate_evidence: List[RoleGateEvidence] = field(default_factory=list)
    classification: str = ""  # "primary", "incidental", "structural_only", "not_classifiable"


def compute_primary_role_scores(features: SemanticFeatures) -> Dict[str, PrimaryRoleResult]:
    """Compute primary-role gated scores for all patterns.

    Args:
        features: Extracted semantic features including primary-role features

    Returns:
        Dict mapping pattern name to PrimaryRoleResult
    """
    # Get structural scores
    structural_scores = score_patterns(features)
    pr = features.primary_role

    results = {}
    results["two_pointers_opposite"] = _gate_two_pointers(
        structural_scores.get("two_pointers_opposite"), pr)
    results["prefix_sum"] = _gate_prefix_sum(
        structural_scores.get("prefix_sum"), pr)
    results["hash_map_lookup"] = _gate_hash_map(
        structural_scores.get("hash_map_lookup"), pr)
    results["array_traversal"] = _gate_array_traversal(
        structural_scores.get("array_traversal"), pr)

    return results


def _gate_two_pointers(structural: PatternScore, pr: PrimaryRoleFeatures) -> PrimaryRoleResult:
    """Gate two_pointers_opposite based on primary-role evidence.

    Policy: SEMANTIC PRIMARY (from Experiment 2B)
    Two pointers is primary when:
    - Both pointer variables influence the result
    - The bidirectional movement drives decisions
    - There's no stronger competing pattern (binary search)

    The gate reduces score when the movement appears incidental.
    """
    gate = 1.0
    evidence = []

    if not structural or structural.score <= 0:
        return PrimaryRoleResult(
            pattern="two_pointers_opposite",
            structural_score=0.0, gate=1.0, final_score=0.0,
            is_primary=False, classification="not_detected",
        )

    # Check competing pattern: binary search
    if pr.has_competing_loop_pattern:
        gate *= 0.4
        evidence.append(RoleGateEvidence(
            "competing_pattern", -0.6,
            "Competing pattern (binary search / sorting) detected — bidirectional movement may be incidental",
        ))

    # Check centrality: result depends on candidate
    if pr.result_depends_on_candidate:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "result_dependency", 0.0,
            "Return value depends on pointer variables",
        ))
    else:
        # If result doesn't depend on pointers, reduce confidence
        gate *= 0.7
        evidence.append(RoleGateEvidence(
            "no_result_dependency", -0.3,
            "Return value does not depend on pointer variables",
        ))

    # Check if pointers drive decisions (loop condition, branches)
    if pr.candidate_drives_decision:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "drives_decision", 0.0,
            "Pointer variables are used in loop condition or branch decisions",
        ))
    else:
        gate *= 0.8
        evidence.append(RoleGateEvidence(
            "no_decision_role", -0.2,
            "Pointer variables do not drive loop or branch decisions",
        ))

    final_score = structural.score * gate
    is_primary = gate >= 0.5

    return PrimaryRoleResult(
        pattern="two_pointers_opposite",
        structural_score=structural.score,
        gate=gate,
        final_score=final_score,
        is_primary=is_primary,
        gate_evidence=evidence,
        classification="primary" if is_primary else "incidental",
    )


def _gate_prefix_sum(structural: PatternScore, pr: PrimaryRoleFeatures) -> PrimaryRoleResult:
    """Gate prefix_sum based on primary-role evidence.

    Policy: AST-PRIMARY + SEMANTIC GAPS (from Experiment 2B)
    Prefix sum is primary when:
    - The accumulated value is used later to make decisions or compose the result
    - It's not just a counter (i += 1)

    The gate suppresses when:
    - The accumulation is incidental (just a counter)
    - The accumulated value is not used outside the loop
    """
    gate = 1.0
    evidence = []

    if not structural or structural.score <= 0:
        return PrimaryRoleResult(
            pattern="prefix_sum",
            structural_score=0.0, gate=1.0, final_score=0.0,
            is_primary=False, classification="not_detected",
        )

    # Simple counter is NOT prefix sum
    if pr.has_simple_counter and not pr.result_depends_on_candidate:
        gate *= 0.2
        evidence.append(RoleGateEvidence(
            "simple_counter", -0.8,
            "Accumulation appears to be a simple counter, not prefix-sum logic",
        ))

    # Check if accumulated value feeds into the result
    if pr.result_depends_on_candidate:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "result_dependency", 0.0,
            "Accumulated value feeds into the return value",
        ))
    elif pr.candidate_drives_decision:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "drives_decision", 0.0,
            "Accumulated value drives branch decisions",
        ))
    else:
        gate *= 0.7
        evidence.append(RoleGateEvidence(
            "no_centrality", -0.3,
            "Accumulated value is not used outside the accumulation loop",
        ))

    # Assignment accumulation is a strong structural signal for prefix recurrence
    if pr.result_depends_on_candidate:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "primary_candidate", 0.0,
            "Accumulation is central to the algorithm",
        ))

    final_score = structural.score * gate
    is_primary = gate >= 0.5

    return PrimaryRoleResult(
        pattern="prefix_sum",
        structural_score=structural.score,
        gate=gate,
        final_score=final_score,
        is_primary=is_primary,
        gate_evidence=evidence,
        classification="primary" if is_primary else "incidental",
    )


def _gate_hash_map(structural: PatternScore, pr: PrimaryRoleFeatures) -> PrimaryRoleResult:
    """Gate hash_map_lookup based on primary-role evidence.

    Policy: AGREEMENT (from Experiment 2B)
    hash_map_lookup is primary when:
    - The lookup result drives control flow
    - The dict/set is not just bookkeeping (visited, frequency)

    The gate suppresses bookkeeping usage heavily.
    """
    gate = 1.0
    evidence = []

    if not structural or structural.score <= 0:
        return PrimaryRoleResult(
            pattern="hash_map_lookup",
            structural_score=0.0, gate=1.0, final_score=0.0,
            is_primary=False, classification="not_detected",
        )

    # Bookkeeping detection: visited set, frequency map
    if pr.has_hash_bookkeeping:
        gate *= 0.3
        evidence.append(RoleGateEvidence(
            "bookkeeping", -0.7,
            "Dict/set appears to be used for visited tracking or frequency counting",
        ))

    # Check if result depends on lookup
    if pr.result_depends_on_candidate:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "result_dependency", 0.0,
            "Lookup result feeds into the return value",
        ))
    elif pr.candidate_drives_decision:
        gate *= 1.0
        evidence.append(RoleGateEvidence(
            "drives_decision", 0.0,
            "Lookup result drives branch decisions",
        ))
    else:
        gate *= 0.6
        evidence.append(RoleGateEvidence(
            "no_centrality", -0.4,
            "Lookup result does not appear to drive the algorithm",
        ))

    final_score = structural.score * gate
    is_primary = gate >= 0.5

    return PrimaryRoleResult(
        pattern="hash_map_lookup",
        structural_score=structural.score,
        gate=gate,
        final_score=final_score,
        is_primary=is_primary,
        gate_evidence=evidence,
        classification="primary" if is_primary else ("bookkeeping" if pr.has_hash_bookkeeping else "structural_only"),
    )


def _gate_array_traversal(structural: PatternScore, pr: PrimaryRoleFeatures) -> PrimaryRoleResult:
    """Gate array_traversal based on primary-role evidence.

    Policy: AST-ONLY (from Experiment 2B)

    array_traversal is too broad as an algorithmic concept. The primary-role
    gate cannot reliably distinguish "the algorithm is array traversal" from
    "the algorithm iterates an array as part of another strategy."

    Therefore: the gate is permissive but the classification is
    "structural_only" — the semantic layer cannot authoritatively
    classify this pattern.
    """
    gate = 1.0
    evidence = []

    if not structural or structural.score <= 0:
        return PrimaryRoleResult(
            pattern="array_traversal",
            structural_score=0.0, gate=1.0, final_score=0.0,
            is_primary=False, classification="not_detected",
        )

    # array_traversal as a PRIMARY pattern is very rare.
    # Most algorithms that iterate arrays have a more specific primary pattern.
    # The semantic layer marks this as structural_only.
    gate = 1.0  # Don't suppress — but classify as structural_only
    evidence.append(RoleGateEvidence(
        "structural_only_pattern", 0.0,
        "array_traversal is a structural pattern; semantic layer cannot classify it as primary",
    ))

    return PrimaryRoleResult(
        pattern="array_traversal",
        structural_score=structural.score,
        gate=gate,
        final_score=structural.score,
        is_primary=False,
        gate_evidence=evidence,
        classification="structural_only",
    )
