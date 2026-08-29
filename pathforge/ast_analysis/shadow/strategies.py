"""Strategy definitions — derive strategy evidence from technique evidence.

Implements strategies from PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md:
- S1: binary_search
- S2: sliding_window
- S3: two_pointers_opposite
- S4: dfs_backtracking
- S5: bfs_shortest_path
- S6: dp_top_down
- S7: dp_bottom_up
- S8: union_find

A strategy is defined by:
- required techniques
- required structural constraints
- optional techniques
- relevant problem-context tags
"""
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, StrategyEvidence,
)


STRATEGY_VERSION = "1.0.0"


def evaluate_strategies(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> list[StrategyEvidence]:
    """Evaluate all strategy definitions against detected techniques and facts.

    Returns a list of StrategyEvidence for strategies that were detected.
    """
    evaluators = [
        _evaluate_two_pointers_opposite,
        _evaluate_binary_search,
        _evaluate_sliding_window,
        _evaluate_dfs_backtracking,
        _evaluate_dp_top_down,
        _evaluate_dp_bottom_up,
        _evaluate_bfs_shortest_path,
        _evaluate_union_find,
        _evaluate_monotonic_stack_strategy,
    ]
    results = []
    for evaluator in evaluators:
        result = evaluator(technique_evidence, facts)
        if result is not None:
            results.append(result)
    return results


def _technique_ids(evidence: list[TechniqueEvidence]) -> set:
    """Get the set of detected technique IDs."""
    return {e.technique_id for e in evidence}


def _fact_types(facts: list[StructuralFact]) -> set:
    """Get the set of all fact types present."""
    return {f.fact_type for f in facts}


def _get_technique_confidence(tech_id: str, evidence: list[TechniqueEvidence]) -> float:
    """Get the presence_confidence for a technique, or 0.0 if not found."""
    for te in evidence:
        if te.technique_id == tech_id:
            return te.presence_confidence
    return 0.0


def _collect_supporting_facts(
    fact_types_wanted: set,
    facts: list[StructuralFact],
    max_count: int = 10,
) -> list[str]:
    """Collect fact IDs of facts matching the wanted types, up to max_count."""
    result = []
    for f in facts:
        if f.fact_type in fact_types_wanted and len(result) < max_count:
            result.append(f.fact_id)
    return result


# ============================================================
# S3: Two Pointers (Opposite Direction)
# ============================================================

def _evaluate_two_pointers_opposite(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S3: Two Pointers (Opposite Direction)

    Required technique: bidirectional_index_scan
    Required structural constraints:
    - while-loop with comparison on two index variables
    - no midpoint calculation (distinguishes from binary search)
    - both indices are updated in opposite directions
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    if "bidirectional_index_scan" not in tech_ids:
        return None

    has_while_comparison = "while_loop_comparison" in fact_types
    has_opposite = "opposite_direction_updates" in fact_types

    if not has_while_comparison or not has_opposite:
        return None

    # Absence constraint: no midpoint calculation
    if "midpoint_calculation" in fact_types:
        return None

    supporting_techniques = ["bidirectional_index_scan"]
    supporting_facts = _collect_supporting_facts(
        {"while_loop_comparison", "opposite_direction_updates",
         "conditional_index_update"},
        facts,
    )

    confidence = _get_technique_confidence("bidirectional_index_scan", technique_evidence)

    return StrategyEvidence(
        strategy_id="two_pointers_opposite",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S1: Binary Search
# ============================================================

def _evaluate_binary_search(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S1: Binary Search

    Required techniques: boundary_narrowing, midpoint_calculation
    Required structural constraints:
    - while-loop comparing two index variables
    - midpoint calculation present
    - one index updated conditionally based on comparison result

    Must NOT classify:
    - two-pointer palindrome (no midpoint)
    - sliding window (no midpoint)
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Required facts: while_loop_comparison + midpoint_calculation
    has_comparison = "while_loop_comparison" in fact_types
    has_midpoint = "midpoint_calculation" in fact_types

    if not has_comparison or not has_midpoint:
        return None

    # Must have conditional index update (the if/elif/else branches)
    has_conditional = "conditional_index_update" in fact_types
    if not has_conditional:
        return None

    # Absence constraint: must NOT have opposite_direction_updates
    # (opposite updates without midpoint = two pointers, not binary search)
    has_opposite = "opposite_direction_updates" in fact_types
    if has_opposite:
        return None

    supporting_techniques = []
    # boundary_narrowing is not a technique yet (Phase 1 limitation);
    # we use the structural fact combination instead
    supporting_facts = _collect_supporting_facts(
        {"while_loop_comparison", "midpoint_calculation", "conditional_index_update"},
        facts,
    )

    # Confidence: high when midpoint + conditional update present
    confidence = 0.85

    return StrategyEvidence(
        strategy_id="binary_search",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S2: Sliding Window
# ============================================================

def _evaluate_sliding_window(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S2: Sliding Window

    Required techniques (either one):
    - loop_state_tracking (variable window with conditional updates)
    - fixed_window_maintenance (fixed window with constant offset)

    Required structural constraints:
    - loop (while or for)
    - for variable window: state variable used in later expression
    - for fixed window: constant window offset

    Must NOT classify:
    - two-pointer palindrome (no variable_use, unconditional updates)
    - generic loop with if statement
    - binary search (has midpoint)
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Check for variable window (existing path)
    has_loop_state = "loop_state_tracking" in tech_ids
    has_variable_use = "variable_use_in_loop_body" in fact_types

    # Check for fixed window (new path)
    has_fixed_window = "fixed_window_maintenance" in tech_ids
    has_window_constant = "window_size_constant" in fact_types

    # Must have at least one of these paths
    variable_window = has_loop_state and has_variable_use
    fixed_window = has_fixed_window and has_window_constant

    # Exclude fixed windows where the structure is also a cache (dict/hash map)
    # This prevents hash-map lookups like seen[prefix_sum - k] from being
    # classified as sliding windows
    if fixed_window:
        window_structs = {f.attributes.get("structure", "") for f in facts if f.fact_type == "window_size_constant"}
        cache_vars = {f.attributes.get("cache_variable", "") for f in facts if f.fact_type in ("cache_lookup", "cache_write")}
        if window_structs & cache_vars:
            fixed_window = False

    if not variable_window and not fixed_window:
        return None

    # Must have a loop
    has_loop = ("while_loop_comparison" in fact_types or
                "while_loop_truthiness" in fact_types or
                "for_loop_iteration" in fact_types)
    if not has_loop:
        return None

    # Absence constraint: must NOT have opposite_direction_updates in a
    # genuine two-pointer loop (where both compared variables are modified).
    # In sliding-window shrink loops, the while condition compares a state
    # expression against a threshold (e.g., while total >= target), so at
    # least one compared variable (the threshold/constant) is NOT modified.
    # The pointer update (left += 1) involves a variable NOT in the
    # comparison — only the accumulator/state is modified.
    if "opposite_direction_updates" in fact_types:
        has_genuine_opposite = False
        for wc in [f for f in facts if f.fact_type == "while_loop_comparison"]:
            compared = set(wc.attributes.get("compared_variables", []))
            modified = set(wc.attributes.get("modified_variables", []))
            if compared and compared <= modified:
                has_genuine_opposite = True
        if has_genuine_opposite:
            return None

    # Absence constraint: must NOT have midpoint_calculation
    # (midpoint = binary search, not sliding window)
    has_midpoint = "midpoint_calculation" in fact_types
    if has_midpoint:
        return None

    # Absence constraint: must NOT have all three monotonic-stack facts.
    # Monotonic-stack pop loops produce the same structural signature as
    # sliding-window shrink loops (conditional update + def-use chain),
    # but stack_operation + monotonic_comparison + conditional_pop are
    # monotonic-stack-specific facts that never co-occur with genuine
    # sliding-window implementations.
    has_stack_op = "stack_operation" in fact_types
    has_mono_comp = "monotonic_comparison" in fact_types
    has_cond_pop = "conditional_pop" in fact_types
    if has_stack_op and has_mono_comp and has_cond_pop:
        return None

    # Determine which path fired
    if fixed_window:
        supporting_techniques = ["fixed_window_maintenance"]
        supporting_facts = _collect_supporting_facts(
            {"for_loop_iteration", "window_size_constant",
             "indexed_access", "indexed_write"},
            facts,
        )
        confidence = _get_technique_confidence("fixed_window_maintenance", technique_evidence)
    else:
        supporting_techniques = ["loop_state_tracking"]
        supporting_facts = _collect_supporting_facts(
            {"conditional_index_update", "variable_use_in_loop_body",
             "for_loop_iteration", "while_loop_comparison"},
            facts,
        )
        confidence = _get_technique_confidence("loop_state_tracking", technique_evidence)

    return StrategyEvidence(
        strategy_id="sliding_window",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S4: DFS / Backtracking
# ============================================================

def _evaluate_dfs_backtracking(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S4: DFS / Backtracking

    Required technique: recursive_branching
    Required structural constraints:
    - state mutation before recursion (add/append to a collection)
    - state restoration after recursion (remove/pop from that collection)

    Must NOT classify:
    - Fibonacci (no state mutation/restoration)
    - tree recursion without state restoration
    - top-down DP with memoization (has cache, not state restoration)
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Required: recursive_branching OR self_recursive_call + early_termination
    # (backtracking functions have both recursion and base-case returns)
    has_recursive_branching = "recursive_branching" in tech_ids
    has_self_recursive = "self_recursive_call" in fact_types
    has_early_termination = "early_termination" in fact_types

    if not has_recursive_branching and not (has_self_recursive and has_early_termination):
        return None

    # Required structural constraint: state_restoration
    # This captures the add/remove or append/pop pattern of backtracking
    has_state_restoration = "state_restoration" in fact_types
    if not has_state_restoration:
        return None

    # Absence constraint: must NOT have cache_lookup or cache_write
    # (cache = DP, not backtracking)
    has_cache = "cache_lookup" in fact_types or "cache_write" in fact_types
    if has_cache:
        return None

    supporting_techniques = ["recursive_branching"] if has_recursive_branching else []
    supporting_facts = _collect_supporting_facts(
        {"self_recursive_call", "recursive_call_in_conditional",
         "multiple_recursive_paths", "state_restoration"},
        facts,
    )

    # Confidence: source from recursive_branching when detected; otherwise
    # use a default for the fallback path (self_recursive + early_termination +
    # state_restoration).  The fallback fires for backtracking patterns where
    # recursion is inside a for-loop (not in a conditional branch), so
    # recursive_branching technique doesn't fire — but the structural evidence
    # (append/pop + recursion + returns) is still strong.
    confidence = _get_technique_confidence("recursive_branching", technique_evidence)
    if confidence == 0.0:
        confidence = 0.7

    return StrategyEvidence(
        strategy_id="dfs_backtracking",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S6: DP Top-Down (Memoization)
# ============================================================

def _evaluate_dp_top_down(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S6: DP Top-Down (Memoization)

    Required technique: recursive_branching
    Required structural constraints:
    - cache_lookup (checking memo before computing)
    - cache_write (storing result in memo)

    Must NOT classify:
    - plain recursion without memoization
    - DFS/backtracking (has state restoration, not cache)
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Required technique: recursive_branching
    if "recursive_branching" not in tech_ids:
        return None

    # Required structural constraints: cache_lookup AND cache_write
    has_cache_lookup = "cache_lookup" in fact_types
    has_cache_write = "cache_write" in fact_types

    if not has_cache_lookup or not has_cache_write:
        return None

    # Absence constraint: must NOT have state_restoration
    # (state restoration = backtracking, not memoization)
    has_state_restoration = "state_restoration" in fact_types
    if has_state_restoration:
        return None

    supporting_techniques = ["recursive_branching"]
    supporting_facts = _collect_supporting_facts(
        {"self_recursive_call", "recursive_call_in_conditional",
         "multiple_recursive_paths", "cache_lookup", "cache_write"},
        facts,
    )

    confidence = _get_technique_confidence("recursive_branching", technique_evidence)

    return StrategyEvidence(
        strategy_id="dp_top_down",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S7: DP Bottom-Up
# ============================================================

def _evaluate_dp_bottom_up(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S7: DP Bottom-Up

    Required technique: iterative_table_filling
    Required structural constraints:
    - pre-initialized table (indexed_write or accumulator_update)
    - recurrence reads prior entries (index_lookback)
    - table is filled iteratively

    Must NOT classify:
    - simple prefix array without recurrence
    - arbitrary indexed assignment
    - generic sequential accumulation
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Required technique: iterative_table_filling
    if "iterative_table_filling" not in tech_ids:
        return None

    # Required structural constraints: indexed_write + index_lookback
    # (already part of iterative_table_filling, but verify)
    has_indexed_write = "indexed_write" in fact_types
    has_lookback = "index_lookback" in fact_types

    if not has_indexed_write or not has_lookback:
        return None

    # Absence constraint: must NOT have recursive_branching
    # (recursive = top-down, not bottom-up)
    has_recursive = "recursive_branching" in {t.technique_id for t in technique_evidence}
    if has_recursive:
        return None

    supporting_techniques = ["iterative_table_filling"]
    supporting_facts = _collect_supporting_facts(
        {"indexed_write", "index_lookback", "accumulator_update",
         "while_loop_comparison", "for_loop_iteration"},
        facts,
    )

    confidence = _get_technique_confidence("iterative_table_filling", technique_evidence)

    return StrategyEvidence(
        strategy_id="dp_bottom_up",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S5: BFS / Shortest Path
# ============================================================

def _evaluate_bfs_shortest_path(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S5: BFS / Shortest Path

    Required structural constraints:
    - queue_dequeue (queue creation with deque or named queue var)
    - neighbor_traversal OR linked_structure_traversal (graph or tree neighbor access)
    - visited_tracking is optional (some tree BFS doesn't need it)

    Must NOT classify:
    - queue-based non-BFS logic (no neighbor traversal)
    - graph traversal without queue (DFS)
    - deque used for other purposes
    """
    fact_types = _fact_types(facts)

    # Required structural constraints
    has_queue = "queue_dequeue" in fact_types
    has_neighbor = "neighbor_traversal" in fact_types
    has_tree_neighbor = "linked_structure_traversal" in fact_types
    has_visited = "visited_tracking" in fact_types

    # Must have queue and either graph or tree neighbor access
    if not has_queue or not (has_neighbor or has_tree_neighbor):
        return None

    # Must have a loop (traversal happens in a loop)
    has_loop = ("while_loop_comparison" in fact_types or
                "while_loop_truthiness" in fact_types or
                "for_loop_iteration" in fact_types)
    if not has_loop:
        return None

    # Absence constraint: must NOT have recursive_branching
    # (recursive = DFS, not BFS)
    has_recursive = "recursive_branching" in {t.technique_id for t in technique_evidence}
    if has_recursive:
        return None

    supporting_techniques = []
    supporting_facts = _collect_supporting_facts(
        {"queue_dequeue", "neighbor_traversal", "linked_structure_traversal",
         "visited_tracking", "while_loop_comparison", "while_loop_truthiness",
         "for_loop_iteration"},
        facts,
    )

    # BFS confidence: high when all structural elements present
    confidence = 0.8

    return StrategyEvidence(
        strategy_id="bfs_shortest_path",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S8: Union-Find
# ============================================================

def _evaluate_union_find(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S8: Union-Find

    Required structural constraints:
    - parent_pointer_chase (while parent[x] != x: x = parent[x])
    - parent_root_merge (parent[a] = b)

    Purely structural detection — no variable names, no function names.
    Must NOT classify:
    - arbitrary parent-like arrays
    - generic while loops with subscript comparisons
    - tree traversal or graph operations
    """
    fact_types = _fact_types(facts)

    # Required structural constraints
    has_chase = "parent_pointer_chase" in fact_types
    has_merge = "parent_root_merge" in fact_types

    if not has_chase or not has_merge:
        return None

    supporting_techniques = []
    supporting_facts = _collect_supporting_facts(
        {"parent_pointer_chase", "parent_root_merge"},
        facts,
    )

    confidence = 0.85

    return StrategyEvidence(
        strategy_id="union_find",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )


# ============================================================
# S9: Monotonic Stack (Phase 5A)
# ============================================================

def _evaluate_monotonic_stack_strategy(
    technique_evidence: list[TechniqueEvidence],
    facts: list[StructuralFact],
) -> Optional[StrategyEvidence]:
    """S9: Monotonic Stack

    Required technique: monotonic_stack_maintenance
    Required structural constraints:
    - stack operations (append/pop)
    - monotonic comparison with stack top
    - conditional pop based on comparison

    Must NOT classify:
    - ordinary stack usage
    - DFS stack traversal
    - queue operations
    """
    tech_ids = _technique_ids(technique_evidence)
    fact_types = _fact_types(facts)

    # Required technique: monotonic_stack_maintenance
    if "monotonic_stack_maintenance" not in tech_ids:
        return None

    # Required structural constraints (already part of the technique)
    has_stack = "stack_operation" in fact_types
    has_comparison = "monotonic_comparison" in fact_types
    has_cond_pop = "conditional_pop" in fact_types

    if not has_stack or not has_comparison or not has_cond_pop:
        return None

    supporting_techniques = ["monotonic_stack_maintenance"]
    supporting_facts = _collect_supporting_facts(
        {"stack_operation", "monotonic_comparison", "conditional_pop"},
        facts,
    )

    confidence = _get_technique_confidence("monotonic_stack_maintenance", technique_evidence)

    return StrategyEvidence(
        strategy_id="monotonic_stack_strategy",
        strategy_version=STRATEGY_VERSION,
        supporting_technique_ids=supporting_techniques,
        supporting_fact_ids=supporting_facts,
        confidence=confidence,
        problem_context_signals={},
    )
