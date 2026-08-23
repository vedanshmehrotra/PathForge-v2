"""Strategy compatibility metadata and semantic coherence validation.

Phase 5B: Adds compatibility metadata to strategy definitions and extends
solution-group validation to detect semantically incoherent combinations.

Design principles:
- Only evidence-backed contradictions are marked mutually exclusive
- "Rarely coexist" ≠ "mutually exclusive"
- Warnings are never silently promoted to rejections
- Original groups are never silently rewritten
"""
from typing import Optional


# ============================================================
# Strategy compatibility metadata
# ============================================================

# Each entry defines:
#   mutually_exclusive_with: strategies that CANNOT coexist as required
#   compatible_with: techniques/concepts that are compatible (informational)
#   reason: why the relationship holds

STRATEGY_COMPATIBILITY: dict[str, dict] = {
    "dfs_backtracking": {
        "mutually_exclusive_with": ["dp_top_down"],
        "compatible_with": ["recursive_branching", "state_restoration", "early_termination"],
        "reason": (
            "dfs_backtracking requires state_restoration (add/append → recurse → remove/pop) "
            "and EXCLUDES cache_lookup/cache_write. dp_top_down requires cache_lookup and "
            "cache_write and EXCLUDES state_restoration. These are structurally contradictory: "
            "a solution cannot simultaneously require memoization AND require state restoration "
            "while excluding cache."
        ),
    },
    "dp_top_down": {
        "mutually_exclusive_with": ["dfs_backtracking"],
        "compatible_with": ["recursive_branching", "cache_lookup", "cache_write"],
        "reason": (
            "dp_top_down requires cache_lookup and cache_write, excludes state_restoration. "
            "dfs_backtracking requires state_restoration, excludes cache. Structural contradiction."
        ),
    },
    "binary_search": {
        "mutually_exclusive_with": [],
        "compatible_with": ["bidirectional_index_scan", "midpoint_calculation"],
        "reason": (
            "binary_search requires midpoint_calculation and excludes opposite_direction_updates. "
            "two_pointers_opposite requires opposite_direction_updates and excludes midpoint. "
            "These are absence-constraint exclusions at the strategy evaluator level, "
            "but a solution group could theoretically require both if the evaluator allowed it. "
            "However, since the evaluator enforces these as hard constraints, requiring both "
            "would create an unsatisfiable group. We mark this as a warning, not rejection, "
            "because the group validator should warn but the evaluator would simply not match."
        ),
    },
    "two_pointers_opposite": {
        "mutually_exclusive_with": [],
        "compatible_with": ["bidirectional_index_scan"],
        "reason": (
            "two_pointers_opposite and binary_search have mutually exclusive absence constraints "
            "in the evaluator (midpoint vs opposite_direction_updates), but this is an evaluator "
            "constraint, not a strategy-definition contradiction. A group requiring both would "
            "never be satisfied, which is a warning-level issue."
        ),
    },
    "sliding_window": {
        "mutually_exclusive_with": [],
        "compatible_with": ["loop_state_tracking", "fixed_window_maintenance"],
        "reason": (
            "sliding_window excludes opposite_direction_updates and midpoint_calculation. "
            "binary_search requires midpoint. A group requiring both would be unsatisfiable. "
            "Warning-level, not rejection."
        ),
    },
    "bfs_shortest_path": {
        "mutually_exclusive_with": [],
        "compatible_with": ["queue_dequeue", "neighbor_traversal", "visited_tracking"],
        "reason": (
            "bfs_shortest_path excludes recursive_branching in the evaluator. "
            "A group requiring both bfs_shortest_path and recursive_branching would "
            "never be satisfied. Warning-level."
        ),
    },
    "dp_bottom_up": {
        "mutually_exclusive_with": [],
        "compatible_with": ["iterative_table_filling", "indexed_write", "index_lookback"],
        "reason": (
            "dp_bottom_up excludes recursive_branching in the evaluator. "
            "A group requiring both dp_bottom_up and recursive_branching would "
            "never be satisfied. Warning-level."
        ),
    },
    "union_find": {
        "mutually_exclusive_with": [],
        "compatible_with": ["parent_pointer_chase", "parent_root_merge"],
        "reason": "No known contradictions with other strategies.",
    },
    "monotonic_stack_strategy": {
        "mutually_exclusive_with": [],
        "compatible_with": ["monotonic_stack_maintenance", "stack_operation"],
        "reason": "No known contradictions with other strategies.",
    },
}


def get_strategy_compatibility(strategy_id: str) -> Optional[dict]:
    """Get compatibility metadata for a strategy."""
    return STRATEGY_COMPATIBILITY.get(strategy_id)


def check_mutual_exclusion(required_strategies: list[str]) -> list[tuple[str, str, str]]:
    """Check if any required strategies are mutually exclusive.

    Returns a list of (strategy_a, strategy_b, reason) tuples for each
    conflicting pair found.
    """
    conflicts = []
    required_set = set(required_strategies)

    for strategy_id in required_set:
        compat = STRATEGY_COMPATIBILITY.get(strategy_id, {})
        exclusive_with = compat.get("mutually_exclusive_with", [])
        for other in exclusive_with:
            if other in required_set:
                # Avoid duplicate pairs (A,B) and (B,A)
                pair = tuple(sorted([strategy_id, other]))
                reason = compat.get("reason", "Mutually exclusive strategies")
                if not any(
                    tuple(sorted([c[0], c[1]])) == pair for c in conflicts
                ):
                    conflicts.append((strategy_id, other, reason))

    return conflicts


def check_unsatisfiable_combinations(required_strategies: list[str]) -> list[tuple[str, str, str]]:
    """Check if required strategies have evaluator-level conflicts that would
    prevent any submission from satisfying the group.

    These are warnings, not rejections — the group is structurally valid
    but practically unsatisfiable.
    """
    warnings = []
    required_set = set(required_strategies)

    # Known evaluator-level conflicts (absence constraints):
    # binary_search requires midpoint, excludes opposite_direction_updates
    # two_pointers_opposite requires opposite_direction_updates, excludes midpoint
    # → requiring both means no submission can satisfy both

    evaluator_conflicts = [
        ("binary_search", "two_pointers_opposite",
         "binary_search requires midpoint_calculation and excludes opposite_direction_updates; "
         "two_pointers_opposite requires opposite_direction_updates and excludes midpoint_calculation. "
         "No submission can satisfy both simultaneously."),
        ("binary_search", "sliding_window",
         "binary_search requires midpoint_calculation; sliding_window excludes midpoint_calculation. "
         "No submission can satisfy both simultaneously."),
        ("bfs_shortest_path", "recursive_branching",
         "bfs_shortest_path excludes recursive_branching in the evaluator. "
         "A group requiring both would never be satisfied."),
        ("dp_bottom_up", "recursive_branching",
         "dp_bottom_up excludes recursive_branching. A group requiring both would never be satisfied."),
    ]

    for strat_a, strat_b, reason in evaluator_conflicts:
        if strat_a in required_set and strat_b in required_set:
            pair = tuple(sorted([strat_a, strat_b]))
            if not any(tuple(sorted([w[0], w[1]])) == pair for w in warnings):
                warnings.append((strat_a, strat_b, reason))

    return warnings
