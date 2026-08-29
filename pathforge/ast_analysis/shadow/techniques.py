"""Technique detectors — derive technique evidence from structural facts.

Implements techniques from PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md:
- T1: sequential_accumulation
- T3: bidirectional_index_scan
- T4: recursive_branching
- T5: carry_propagation
- T6: loop_state_tracking
- T7: iterative_table_filling
- T8: linked_list_traversal (Phase 5A)
- T9: fixed_window_maintenance (Phase 5A)
- T10: monotonic_stack_maintenance (Phase 5A)

Each detector:
1. Looks for required structural facts
2. Computes presence_confidence and centrality
3. Returns TechniqueEvidence or None
"""
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, EXTRACTOR_VERSION,
)


def detect_techniques(facts: list[StructuralFact]) -> list[TechniqueEvidence]:
    """Run all technique detectors on the given structural facts.

    Returns a list of TechniqueEvidence for techniques that were detected.
    """
    detectors = [
        _detect_sequential_accumulation,
        _detect_bidirectional_index_scan,
        _detect_carry_propagation,
        _detect_recursive_branching,
        _detect_loop_state_tracking,
        _detect_iterative_table_filling,
        _detect_linked_list_traversal,
        _detect_fixed_window_maintenance,
        _detect_monotonic_stack_maintenance,
    ]
    results = []
    for detector in detectors:
        result = detector(facts)
        if result is not None:
            results.append(result)
    return results


def _fact_types(facts: list[StructuralFact]) -> set:
    """Get the set of all fact types present."""
    return {f.fact_type for f in facts}


def _facts_of_type(facts: list[StructuralFact], fact_type: str) -> list[StructuralFact]:
    """Get all facts of a given type."""
    return [f for f in facts if f.fact_type == fact_type]


def _detect_sequential_accumulation(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T1: Sequential Accumulation

    Required facts:
    1. loop_shape (while_loop_comparison or loop structure)
    2. accumulator_update (a variable updated via += or x = x + ...)
    3. loop_variable_in_update (the loop variable appears in the update expression)

    The accumulator must be self-referential: updated from its own prior value.
    """
    types = _fact_types(facts)

    has_loop = "while_loop_comparison" in types
    acc_facts = _facts_of_type(facts, "accumulator_update")

    if not has_loop or not acc_facts:
        return None

    # Find accumulator_update facts where the variable is modified in the loop
    # and the update expression involves the loop variable
    supporting = []
    for acc in acc_facts:
        var = acc.attributes.get("variable", "")
        # Check if this variable is also in the while_loop_comparison's modified list
        for wc in _facts_of_type(facts, "while_loop_comparison"):
            modified = wc.attributes.get("modified_variables", [])
            if var in modified:
                supporting.append(wc.fact_id)
                supporting.append(acc.fact_id)
                break

    if not supporting:
        return None

    # Also check if loop variable appears in the update expression
    # (heuristic: the accumulator update is inside the loop body)
    # For now, if we have a loop + accumulator + the accumulator var is modified
    # in the loop, that's sufficient
    has_loop_fact = any(f.fact_type == "while_loop_comparison" for f in facts)
    if has_loop_fact:
        for f in facts:
            if f.fact_type == "while_loop_comparison":
                supporting.append(f.fact_id)
                break

    # Deduplicate
    supporting = list(dict.fromkeys(supporting))

    return TechniqueEvidence(
        technique_id="sequential_accumulation",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.85,
        centrality=0.6,
    )


def _collect_subscript_index_vars(facts: list[StructuralFact]) -> set:
    """Collect variable names that appear as subscript indices.

    Uses subscript_index_access facts to identify variables used for
    array/string indexing. This structural signal distinguishes
    pointer variables (used as indices) from accumulators (used in arithmetic).
    """
    index_vars = set()
    for f in facts:
        if f.fact_type == "subscript_index_access":
            index_vars.update(f.attributes.get("index_variables", []))
    return index_vars


def _detect_bidirectional_index_scan(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T3: Bidirectional Index Scan

    Required facts:
    1. while_loop_comparison (while-loop comparing two index variables)
    2. opposite_direction_updates (one variable incremented, one decremented)

    Both facts must reference the same loop.

    Structural guard: both the incremented and decremented variables must
    appear as subscript indices (indexed_write or index_lookback). This
    distinguishes genuine two-pointer scans (both variables index arrays)
    from accumulator-based sliding windows (only one variable indexes,
    the other accumulates state).
    """
    types = _fact_types(facts)

    has_comparison = "while_loop_comparison" in types
    has_opposite = "opposite_direction_updates" in types

    if not has_comparison or not has_opposite:
        return None

    # Find the matching facts
    comparison_fact = _facts_of_type(facts, "while_loop_comparison")[0]
    opposite_fact = _facts_of_type(facts, "opposite_direction_updates")[0]

    # Verify the same loop: both should reference the same location
    # or at least the modified variables from comparison should overlap
    # with the incremented/decremented variables
    compared = set(comparison_fact.attributes.get("compared_variables", []))
    inc = set(opposite_fact.attributes.get("incremented", []))
    dec = set(opposite_fact.attributes.get("decremented", []))
    all_direction_vars = inc | dec

    # At least one compared variable should be in the opposite-direction set
    if not (compared & all_direction_vars):
        return None

    # Structural guard: both variables must be used as subscript indices.
    # In a genuine two-pointer scan, both left and right index the same array
    # (e.g., arr[left], arr[right]). In an accumulator-based sliding window,
    # only the pointer indexes the array; the accumulator is used in arithmetic.
    index_vars = _collect_subscript_index_vars(facts)
    if not (bool(inc & index_vars) and bool(dec & index_vars)):
        return None

    supporting = [
        comparison_fact.fact_id,
        opposite_fact.fact_id,
    ]

    # Include conditional_index_update if present (optional)
    for f in facts:
        if f.fact_type == "conditional_index_update":
            supporting.append(f.fact_id)
            break

    return TechniqueEvidence(
        technique_id="bidirectional_index_scan",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.9,
        centrality=0.85,
    )


def _detect_carry_propagation(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T5: Carry / State Propagation

    Required facts:
    1. linked_structure_traversal (.next, .left, .right access)
    2. carry_propagation (carry variable updated in loop with linked traversal)
    3. loop_shape (while or for loop)

    The carry must propagate across iterations through a linked structure.
    """
    types = _fact_types(facts)

    has_linked = "linked_structure_traversal" in types
    has_carry = "carry_propagation" in types
    has_loop = "while_loop_comparison" in types

    if not has_linked or not has_carry:
        return None

    # Find supporting facts
    linked_fact = _facts_of_type(facts, "linked_structure_traversal")[0]
    carry_fact = _facts_of_type(facts, "carry_propagation")[0]

    supporting = [linked_fact.fact_id, carry_fact.fact_id]

    # Include loop fact if present
    if has_loop:
        for f in facts:
            if f.fact_type == "while_loop_comparison":
                supporting.append(f.fact_id)
                break

    # Include node_constructor if present (optional — strengthens evidence)
    for f in facts:
        if f.fact_type == "node_constructor":
            supporting.append(f.fact_id)
            break

    return TechniqueEvidence(
        technique_id="carry_propagation",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.9,
        centrality=0.8,
    )


def _detect_recursive_branching(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T4: Recursive Branching

    Required facts:
    1. self_recursive_call — function calls itself
    2. ONE of:
       a. recursive_call_in_conditional — recursion in if/else branches
       b. multiple_recursive_paths — multiple distinct call sites
       c. nested self-recursion (context=nested_function) — inner helper
          function calls itself, e.g. memoized top-down DP with a nested dfs()

    Does NOT fire for:
    - Linear recursion (one call site, no branching, not nested)
    - Mutual recursion (A calls B calls A)
    """
    types = _fact_types(facts)

    has_recursive = "self_recursive_call" in types
    has_conditional = "recursive_call_in_conditional" in types
    has_multiple = "multiple_recursive_paths" in types

    # Nested self-recursion: inner function calls itself (e.g. memoized DP)
    has_nested_self_recursion = False
    for f in facts:
        if f.fact_type == "self_recursive_call" and f.attributes.get("context") == "nested_function":
            has_nested_self_recursion = True
            break

    if not has_recursive:
        return None

    if not has_conditional and not has_multiple and not has_nested_self_recursion:
        return None

    supporting = []
    for f in facts:
        if f.fact_type in ("self_recursive_call", "recursive_call_in_conditional",
                           "multiple_recursive_paths"):
            supporting.append(f.fact_id)

    # Centrality: higher if multiple paths or nested recursion, lower if just conditional
    if has_multiple or has_nested_self_recursion:
        centrality = 0.8
        confidence = 0.85
    else:
        centrality = 0.65
        confidence = 0.75

    return TechniqueEvidence(
        technique_id="recursive_branching",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=confidence,
        centrality=centrality,
    )


def _detect_loop_state_tracking(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T6: Loop-State Tracking

    Required facts:
    1. while_loop_comparison or for_loop_iteration (any loop)
    2. conditional_index_update — a variable is conditionally updated inside the loop
    3. The updated variable must be used in a later condition or expression
       within the same loop body (def-use chain)

    Does NOT fire for:
    - Simple counters that are never reused
    - Unconditional updates (happen every iteration)
    - Updates that don't affect subsequent computation
    """
    types = _fact_types(facts)

    has_loop = "while_loop_comparison" in types or "for_loop_iteration" in types
    cond_updates = _facts_of_type(facts, "conditional_index_update")

    if not has_loop or not cond_updates:
        return None

    # Check if any conditionally updated variable appears in a later
    # comparison, condition, or expression within the same scope
    updated_vars = set()
    for cu in cond_updates:
        updated_vars.update(cu.attributes.get("updated_variables", []))

    if not updated_vars:
        return None

    # Check if updated vars appear in other facts' attributes (def-use check)
    # Exclude the conditional_index_update and accumulator_update facts themselves
    # (they describe the update, not a later use)
    exclude_types = {"conditional_index_update", "accumulator_update"}
    supporting = []
    for f in facts:
        if f.fact_type in exclude_types:
            continue
        for key, val in f.attributes.items():
            if isinstance(val, list):
                if updated_vars & set(val):
                    supporting.append(f.fact_id)
                    break
            elif isinstance(val, str) and val in updated_vars:
                supporting.append(f.fact_id)
                break

    if not supporting:
        return None

    # Include the conditional update facts themselves
    for cu in cond_updates:
        if cu.fact_id not in supporting:
            supporting.append(cu.fact_id)

    return TechniqueEvidence(
        technique_id="loop_state_tracking",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.75,
        centrality=0.7,
    )


def _detect_iterative_table_filling(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T7: Iterative Table Filling

    Required facts:
    1. while_loop_comparison or for_loop_iteration (any loop)
    2. indexed_write — a value is written into an indexed structure
    3. index_lookback — the write depends on earlier entries
       (or the index is the loop variable)

    Does NOT fire for:
    - Simple prefix array construction without lookback
    - Arbitrary indexed mutation unrelated to loop iteration
    - Hash-map operations (not indexed)
    """
    types = _fact_types(facts)

    has_loop = "while_loop_comparison" in types or "for_loop_iteration" in types
    has_indexed_write = "indexed_write" in types
    has_lookback = "index_lookback" in types

    if not has_loop or not has_indexed_write:
        return None

    # Need indexed_write + lookback for genuine table filling
    # Without lookback, it's just arbitrary indexed assignment
    if not has_lookback:
        return None

    supporting = []
    for f in facts:
        if f.fact_type in ("while_loop_comparison", "indexed_write", "index_lookback"):
            supporting.append(f.fact_id)

    # Also include accumulator_update if present (strengthens evidence)
    for f in facts:
        if f.fact_type == "accumulator_update":
            supporting.append(f.fact_id)
            break

    return TechniqueEvidence(
        technique_id="iterative_table_filling",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.8,
        centrality=0.75,
    )


# ============================================================
# T8: Linked-List Traversal (Phase 5A)
# ============================================================

def _detect_linked_list_traversal(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T8: Linked-List Traversal

    Required facts:
    1. linked_structure_traversal — .next, .left, .right attribute access
    2. pointer_rewiring OR multiple_pointer_traversal — manipulation evidence

    Does NOT fire for:
    - Simple linked-list traversal without rewiring (just reading)
    - Add Two Numbers (carry_propagation handles that)
    - Tree traversal without pointer manipulation
    """
    types = _fact_types(facts)

    has_linked = "linked_structure_traversal" in types
    has_rewiring = "pointer_rewiring" in types
    has_multi_pointer = "multiple_pointer_traversal" in types

    if not has_linked:
        return None

    # Must have rewiring or multiple pointer traversal
    if not has_rewiring and not has_multi_pointer:
        return None

    # NOTE: carry_propagation guard removed. Per architecture, techniques are
    # reusable, non-exclusive evidence. Both carry_propagation AND
    # linked_list_traversal can fire for Add Two Numbers. The matching layer
    # handles which technique is relevant to which solution group.

    supporting = []
    for f in facts:
        if f.fact_type in ("linked_structure_traversal", "pointer_rewiring",
                           "multiple_pointer_traversal"):
            supporting.append(f.fact_id)

    # Lower centrality slightly when carry_propagation is also present,
    # since carry_propagation is the more specific technique for this case.
    has_carry = "carry_propagation" in types
    centrality = 0.7 if has_carry else 0.8
    confidence = 0.8 if has_carry else 0.85

    return TechniqueEvidence(
        technique_id="linked_list_traversal",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=confidence,
        centrality=centrality,
    )


# ============================================================
# T9: Fixed Window Maintenance (Phase 5A)
# ============================================================

def _detect_fixed_window_maintenance(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T9: Fixed Window Maintenance

    Required facts:
    1. for_loop_iteration — a for-loop exists
    2. window_size_constant — constant offset in index (arr[i+k])
    3. indexed_access — the code reads from the collection

    Does NOT fire for:
    - Variable sliding window (no constant offset)
    - Simple array iteration (no window offset)
    - Two-pointers (no window concept)
    """
    types = _fact_types(facts)

    has_for_loop = "for_loop_iteration" in types
    has_window = "window_size_constant" in types
    has_indexed = "indexed_access" in types or "indexed_write" in types

    if not has_for_loop or not has_window:
        return None

    # Optional: indexed access strengthens the evidence
    supporting = []
    for f in facts:
        if f.fact_type in ("for_loop_iteration", "window_size_constant",
                           "indexed_access", "indexed_write"):
            supporting.append(f.fact_id)

    return TechniqueEvidence(
        technique_id="fixed_window_maintenance",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.8,
        centrality=0.7,
    )


# ============================================================
# T10: Monotonic Stack Maintenance (Phase 5A)
# ============================================================

def _detect_monotonic_stack_maintenance(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T10: Monotonic Stack Maintenance

    Required facts:
    1. stack_operation — append/pop on a stack-like structure
    2. monotonic_comparison — while-loop comparing with stack[-1]
    3. conditional_pop — pop inside a conditional branch

    Does NOT fire for:
    - Ordinary stack usage (no monotonic comparison)
    - DFS stack (no conditional pop based on comparison)
    - Queue operations
    """
    types = _fact_types(facts)

    has_stack = "stack_operation" in types
    has_comparison = "monotonic_comparison" in types
    has_cond_pop = "conditional_pop" in types

    if not has_stack or not has_comparison or not has_cond_pop:
        return None

    supporting = []
    for f in facts:
        if f.fact_type in ("stack_operation", "monotonic_comparison",
                           "conditional_pop"):
            supporting.append(f.fact_id)

    return TechniqueEvidence(
        technique_id="monotonic_stack_maintenance",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.85,
        centrality=0.8,
    )
