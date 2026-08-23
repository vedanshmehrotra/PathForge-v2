"""Cross-pattern competition model.

When multiple structural behaviors coexist in a program, this module
determines which pattern(s) best explain the algorithmic strategy.

Architecture:
  structural_score × primary_role_gate × competition_suppression = final_score

The competition model applies pattern-specific mutual exclusion rules
based on known algorithmic relationships. It does NOT force a single
label — legitimate multi-pattern combinations are preserved.

Key design principle:
  Competition suppresses INCIDENTAL patterns, not PRIMARY patterns.
  When two patterns genuinely coexist, both remain.
  When one pattern is incidental to another, the incidental one is suppressed.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .features import SemanticFeatures  # noqa: F401


@dataclass
class CompetitionEvidence:
    """Evidence for why a competition adjustment was applied."""
    rule: str
    suppressor_pattern: str
    suppressed_pattern: str
    impact: float  # multiplier applied to suppressed pattern's score
    reason: str


@dataclass
class CompetitionResult:
    """Result of cross-pattern competition for a single pattern."""
    pattern: str
    original_score: float
    competition_multiplier: float
    final_score: float
    suppressed: bool  # True if competition reduced score below threshold
    competition_evidence: List[CompetitionEvidence] = field(default_factory=list)
    classification: str = ""  # "primary", "secondary", "incidental", "structural_only"


def apply_competition(
    pattern_scores: Dict[str, float],
    features: SemanticFeatures,
    ast_patterns: Optional[set] = None,
) -> Dict[str, CompetitionResult]:
    """Apply cross-pattern competition rules.

    Args:
        pattern_scores: Dict mapping pattern name to score (0.0-1.0)
        features: Extracted semantic features
        ast_patterns: Set of pattern IDs detected by existing AST engine (optional)

    Returns:
        Dict mapping pattern name to CompetitionResult
    """
    results = {}
    for pat, score in pattern_scores.items():
        results[pat] = CompetitionResult(
            pattern=pat,
            original_score=score,
            competition_multiplier=1.0,
            final_score=score,
            suppressed=False,
        )

    # Apply competition rules
    _rule_prefix_sum_vs_hash_map(results, features)
    _rule_bfs_dfs_vs_hash_map(results, features)
    _rule_binary_search_vs_two_pointers(results, features)
    _rule_sorting_vs_array_traversal(results, features)
    _rule_dp_vs_prefix_sum(results, features)
    _rule_array_traversal_demotion(results, features)

    # Apply multipliers
    for pat, r in results.items():
        r.final_score = r.original_score * r.competition_multiplier
        r.suppressed = r.final_score < 0.3  # threshold for "detected"

    return results


def _rule_prefix_sum_vs_hash_map(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """When prefix_sum has strong accumulation evidence, the membership test
    is likely incidental (used for validation, not as the primary strategy).

    Suppress hash_map_lookup when:
    - prefix_sum has strong structural evidence (accumulation from collection)
    - The membership test is on the same collection being accumulated
    - OR the membership test is a simple 'x in collection' guard
    """
    prefix_score = results.get("prefix_sum", CompetitionResult("prefix_sum", 0, 1, 0, False)).original_score
    hash_score = results.get("hash_map_lookup", CompetitionResult("hash_map_lookup", 0, 1, 0, False)).original_score

    if prefix_score < 0.3 or hash_score < 0.3:
        return

    # Strong prefix_sum evidence: accumulation from collection + running sum
    has_strong_prefix = (
        features.accumulation.has_accumulation
        and features.accumulation.has_numeric_accumulation
        and (features.accumulation.has_running_sum
             or features.accumulation.has_append_accumulation
             or features.accumulation.has_assignment_accumulation)
    )

    if has_strong_prefix:
        # Check if membership test is on a simple collection (not a dedicated dict/set)
        membership_is_simple = (
            features.access.has_membership_test
            and not features.access.membership_on_hash_collection
            and not features.access.has_dict_get_lookup
        )

        # If prefix_sum is strong AND membership is simple (or on the accumulated collection),
        # suppress hash_map_lookup
        if membership_is_simple or (features.access.has_membership_test and prefix_score > 0.5):
            r = results["hash_map_lookup"]
            suppression = 0.3  # Reduce but don't eliminate entirely
            r.competition_multiplier *= suppression
            r.competition_evidence.append(CompetitionEvidence(
                rule="prefix_sum_dominates_hash_map",
                suppressor_pattern="prefix_sum",
                suppressed_pattern="hash_map_lookup",
                impact=suppression,
                reason=f"prefix_sum score={prefix_score:.3f} with accumulation evidence; "
                       f"membership test appears incidental",
            ))


def _rule_bfs_dfs_vs_hash_map(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """When BFS/DFS structural signals are present, the hash map usage
    is likely a visited set or frequency counter, not a primary lookup strategy.

    Detect BFS/DFS signals:
    - Stack/queue behavior (push/pop or append/popleft)
    - Visited set pattern (if x in visited: continue)
    - Graph neighbor iteration
    """
    hash_score = results.get("hash_map_lookup", CompetitionResult("hash_map_lookup", 0, 1, 0, False)).original_score

    if hash_score < 0.3:
        return

    # Check for BFS/DFS structural signals using available features
    has_visited_set = False

    # 1. visited set: membership test on a set variable
    if (features.access.has_membership_test
            and features.access.membership_collection_type == "set"):
        has_visited_set = True

    # 2. Stack/queue: dict construction with membership test (visited tracking)
    if (features.access.dict_vars
            and features.access.has_membership_test
            and features.access.membership_on_hash_collection):
        has_visited_set = True

    # 3. Bookkeeping detection from primary role
    if features.primary_role.has_hash_bookkeeping:
        has_visited_set = True

    if has_visited_set:
        r = results["hash_map_lookup"]
        suppression = 0.4
        r.competition_multiplier *= suppression
        r.competition_evidence.append(CompetitionEvidence(
            rule="bfs_dfs_vs_hash_map",
            suppressor_pattern="graph_traversal",
            suppressed_pattern="hash_map_lookup",
            impact=suppression,
            reason="Hash map usage appears to be visited set / bookkeeping for graph traversal",
        ))


def _rule_binary_search_vs_two_pointers(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """When binary search signals are present, bidirectional pointer movement
    is part of the binary search partition, not two-pointers-algorithm.

    Binary search signals:
    - mid = (left + right) // 2
    - left/right updating based on mid comparison
    - while left <= right
    """
    tp_score = results.get("two_pointers_opposite", CompetitionResult("two_pointers_opposite", 0, 1, 0, False)).original_score

    if tp_score < 0.3:
        return

    # Check for competing binary search pattern
    if features.primary_role.has_competing_loop_pattern:
        r = results["two_pointers_opposite"]
        suppression = 0.3
        r.competition_multiplier *= suppression
        r.competition_evidence.append(CompetitionEvidence(
            rule="binary_search_vs_two_pointers",
            suppressor_pattern="binary_search",
            suppressed_pattern="two_pointers_opposite",
            impact=suppression,
            reason="Bidirectional movement is part of binary search partition, not two-pointers algorithm",
        ))


def _rule_sorting_vs_array_traversal(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """When sorting-like patterns are detected, array traversal is incidental.

    Sorting signals:
    - Nested loops with indexed access
    - Conditional swap (if arr[j] > arr[j+1]: swap)
    - Inner loop bound depends on outer loop index
    """
    at_score = results.get("array_traversal", CompetitionResult("array_traversal", 0, 1, 0, False)).original_score

    if at_score < 0.3:
        return

    # Check for sorting-like nested loop pattern
    if (features.loops.for_loops >= 2
            and features.access.has_indexed_access
            and features.primary_role.has_competing_loop_pattern):
        r = results["array_traversal"]
        suppression = 0.5
        r.competition_multiplier *= suppression
        r.competition_evidence.append(CompetitionEvidence(
            rule="sorting_vs_array_traversal",
            suppressor_pattern="sorting",
            suppressed_pattern="array_traversal",
            impact=suppression,
            reason="Nested indexed loops with swap pattern suggest sorting, not array traversal",
        ))


def _rule_dp_vs_prefix_sum(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """When DP-like patterns are present, prefix_sum may be incidental.

    DP signals:
    - 2D array access (dp[i][j])
    - Multiple accumulation patterns
    - Nested loops with state reuse

    This is a WEAK rule — only apply when DP evidence is very strong.
    """
    prefix_score = results.get("prefix_sum", CompetitionResult("prefix_sum", 0, 1, 0, False)).original_score

    if prefix_score < 0.3:
        return

    # Very conservative: only suppress if prefix_sum score is low AND
    # we have strong DP indicators (which we don't currently detect well)
    # Therefore: this rule is intentionally a no-op for now
    pass


def _rule_array_traversal_demotion(
    results: Dict[str, CompetitionResult],
    features: SemanticFeatures,
) -> None:
    """Array traversal is structurally present in nearly every algorithm.

    When more specific patterns are detected, array_traversal should be
    demoted to "structural_only" rather than treated as a primary pattern.
    """
    at_result = results.get("array_traversal")
    if not at_result or at_result.original_score < 0.3:
        return

    # Count how many other patterns have meaningful scores
    other_strong = sum(
        1 for pat, r in results.items()
        if pat != "array_traversal" and r.original_score >= 0.3
    )

    if other_strong >= 2:
        # Multiple other patterns detected → array_traversal is almost certainly incidental
        r = results["array_traversal"]
        suppression = 0.4
        r.competition_multiplier *= suppression
        r.competition_evidence.append(CompetitionEvidence(
            rule="array_traversal_demotion",
            suppressor_pattern="multiple_other_patterns",
            suppressed_pattern="array_traversal",
            impact=suppression,
            reason=f"{other_strong} other patterns detected; array traversal is structural, not primary",
        ))
    elif other_strong == 1:
        # One other pattern detected → moderate demotion
        r = results["array_traversal"]
        suppression = 0.7
        r.competition_multiplier *= suppression
        r.competition_evidence.append(CompetitionEvidence(
            rule="array_traversal_mild_demotion",
            suppressor_pattern="one_other_pattern",
            suppressed_pattern="array_traversal",
            impact=suppression,
            reason="One other pattern detected; array traversal may be secondary",
        ))
