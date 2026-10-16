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
- T11: forward_pointer_advance (same-direction two pointers)
- T12: candidate_selection (Vocabulary Layer 2)
- T13: hash_lookup (Vocabulary Layer 2)
- T14: frequency_counting (Vocabulary Layer 2)

Each detector:
1. Looks for required structural facts
2. Computes presence_confidence and centrality
3. Returns TechniqueEvidence or None
"""
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, EXTRACTOR_VERSION,
)


def detect_techniques(facts: list[StructuralFact], relations=None) -> list[TechniqueEvidence]:
    """Run all technique detectors on the given structural facts.

    Args:
        facts: Structural facts from extraction.
        relations: Optional shared relational-evidence bundle (M2). When
            provided, migrated detectors may consume it as their
            loop-membership oracle instead of re-deriving joins from fact
            attributes. Detectors without relations support ignore it.

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
        _detect_forward_pointer_advance,
        _detect_candidate_selection,
        _detect_hash_lookup,
        _detect_frequency_counting,
    ]
    results = []
    for detector in detectors:
        if detector in (_detect_sequential_accumulation, _detect_candidate_selection):
            result = detector(facts, relations)
        else:
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


def _detect_sequential_accumulation(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """T1: Sequential Accumulation

    Required evidence:
    1. A loop (``while_loop_comparison`` or ``for_loop_iteration``)
    2. A self-referential accumulator update (``accumulator_update``)
    3. The accumulator variable is distinct from the loop variable

    The accumulator must be self-referential: updated from its own prior value
    (e.g. ``total += x`` or ``x = x + 1``).  ``result.append(x)`` does NOT
    qualify because ``result`` never appears on the right-hand side.

    For-loop variant: when a ``for_loop_iteration`` fact provides the loop
    variable, the fact that the ``accumulator_update`` was extracted from the
    same function body is sufficient evidence that the update is inside the
    loop, provided the accumulator variable differs from the loop variable.

    M2 migration: when a relations bundle is supplied, loop membership of the
    accumulator update is decided by the shared relation layer
    (``updated_in_loop``) instead of being inferred from fact attributes.
    Two compatibility rules keep behavior identical for all previously
    supported inputs:

    - The original fact-join path still gates detection. The relations oracle
      can only *disambiguate which accumulator variable to join on* — it can
      never make a detection fire that the fact joins would not have allowed.
    - If the relations layer yields no admissible accumulator (or relations
      were not supplied), the original unmodified fact-join path runs as the
      fallback. Inputs the extractor supports but relations do not (e.g.
      ``ast_ref``-less hand-built facts in tests) keep their exact previous
      outputs.
    """
    types = _fact_types(facts)
    acc_facts = _facts_of_type(facts, "accumulator_update")

    has_while = "while_loop_comparison" in types
    has_for = "for_loop_iteration" in types
    if not has_while and not has_for:
        return None

    # Container path first when no scalar accumulator exists: assign-form
    # counting and append-form accumulation have no accumulator_update fact
    # at all, and the original early-return would make them unreachable.
    if not acc_facts:
        if relations is None:
            return None
        return _seq_accum_container_evidence(facts, has_while, has_for, relations)

    if relations is not None:
        evidence = _seq_accum_evidence_via_relations(
            facts, acc_facts, has_while, has_for, relations
        )
        if evidence is not None:
            return evidence
        # Relations yielded nothing admissible — fall through to the
        # container path and then the original path so previously
        # supported inputs keep their outputs.
        evidence = _seq_accum_container_evidence(
            facts, has_while, has_for, relations
        )
        if evidence is not None:
            return evidence
    return _seq_accum_evidence_fact_join(facts, acc_facts, has_while, has_for)


def _seq_accum_supporting_facts(
    facts: list[StructuralFact],
    acc: StructuralFact,
    acc_var: str,
    has_while: bool,
    has_for: bool,
) -> Optional[list]:
    """Build the supporting-fact list for one accumulator variable.

    This is the original fact-join gate, unchanged: the while path requires
    the accumulator variable in a while_loop_comparison's
    ``modified_variables``; the for path requires a ``for_loop_iteration``
    fact and a loop variable distinct from the accumulator.
    """
    supporting: list = []
    if has_while:
        for wc in _facts_of_type(facts, "while_loop_comparison"):
            if acc_var in (wc.attributes.get("modified_variables") or []):
                supporting.append(wc.fact_id)
                supporting.append(acc.fact_id)
                break
    elif has_for:
        loop_var = ""
        for fl in _facts_of_type(facts, "for_loop_iteration"):
            loop_var = fl.attributes.get("loop_variable", "")
            supporting.append(fl.fact_id)
            break
        if acc_var and acc_var != loop_var:
            supporting.append(acc.fact_id)
    return supporting or None


def _seq_accum_evidence_fact_join(
    facts: list[StructuralFact],
    acc_facts: list[StructuralFact],
    has_while: bool,
    has_for: bool,
) -> Optional[TechniqueEvidence]:
    """Original fact-attribute join, preserved byte-for-byte as the fallback."""
    supporting: list = []

    if has_while:
        # Original path: accumulator variable must appear in the while loop's
        # modified_variables list, proving it is updated inside the loop body.
        for acc in acc_facts:
            var = acc.attributes.get("variable", "")
            for wc in _facts_of_type(facts, "while_loop_comparison"):
                if var in (wc.attributes.get("modified_variables") or []):
                    supporting.append(wc.fact_id)
                    supporting.append(acc.fact_id)
                    break
    elif has_for:
        # For-loop path: the accumulator must differ from the loop variable.
        # Both ``total += x`` and ``total += i`` qualify (the accumulator is
        # self-referential and updated inside the loop body — the fact was
        # extracted from the loop body, which the extractor only visits when
        # the assignment is syntactically inside the for-loop).
        loop_var = ""
        for fl in _facts_of_type(facts, "for_loop_iteration"):
            loop_var = fl.attributes.get("loop_variable", "")
            supporting.append(fl.fact_id)
            break
        for acc in acc_facts:
            var = acc.attributes.get("variable", "")
            if var and var != loop_var:
                supporting.append(acc.fact_id)

    if not supporting:
        return None

    # Deduplicate
    supporting = list(dict.fromkeys(supporting))

    return TechniqueEvidence(
        technique_id="sequential_accumulation",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.85,
        centrality=0.6,
    )


def _seq_accum_evidence_via_relations(
    facts: list[StructuralFact],
    acc_facts: list[StructuralFact],
    has_while: bool,
    has_for: bool,
    relations,
) -> Optional[TechniqueEvidence]:
    """M2 proof-of-architecture path: loop membership from the relation layer.

    For each accumulator-update fact, check the shared ``updated_in_loop``
    relation instead of inferring loop membership from fact attributes.
    The fact-join gate (``_seq_accum_supporting_facts``) still decides
    whether the join evidence is admissible, so this path can never fire on
    inputs the original detector rejected — it only changes *which*
    accumulator variable is joined when several are present, using the
    same relation for every migrated detector going forward.
    """
    updated_in_loop = getattr(relations, "updated_in_loop", None)
    if not updated_in_loop:
        return None

    for acc in acc_facts:
        var = acc.attributes.get("variable", "")
        if not var:
            continue
        kinds = updated_in_loop.get(var) or set()
        if has_while and "while" in kinds:
            supporting = _seq_accum_supporting_facts(
                facts, acc, var, has_while, has_for
            )
            if supporting:
                supporting = list(dict.fromkeys(supporting))
                return TechniqueEvidence(
                    technique_id="sequential_accumulation",
                    technique_version="1.0.0",
                    supporting_fact_ids=supporting,
                    presence_confidence=0.85,
                    centrality=0.6,
                )
        if has_for and "for" in kinds:
            supporting = _seq_accum_supporting_facts(
                facts, acc, var, has_while, has_for
            )
            if supporting:
                supporting = list(dict.fromkeys(supporting))
                return TechniqueEvidence(
                    technique_id="sequential_accumulation",
                    technique_version="1.0.0",
                    supporting_fact_ids=supporting,
                    presence_confidence=0.85,
                    centrality=0.6,
                )
    return None


def _seq_accum_container_evidence(
    facts: list[StructuralFact],
    has_while: bool,
    has_for: bool,
    relations,
) -> Optional[TechniqueEvidence]:
    """Container-accumulation path: self-referential loop-carried updates.

    Covers two structural forms the scalar ``accumulator_update`` fact
    cannot represent (its target is a plain Name by definition):

    - **assign-form counting**: ``freq[x] = freq.get(x, 0) + 1`` — an
      indexed write (Assign/AnnAssign) whose value combines exactly one
      read of the same structure with an external value;
    - **append-form accumulation**: ``prefix.append(prefix[-1] + x)`` — an
      append whose argument combines exactly one read of the same structure.

    The join is entirely through the M2 relation layer:

    - ``self_referential_updates`` (loop-scoped by construction) provides
      the same-structure cumulative-update evidence, including the loop
      membership that gates it — a one-shot self-referential assignment
      outside a loop is never recorded, so this path cannot fire on it;
    - ``updated_in_loop`` must independently confirm loop membership of
      the structure (the append-receiver extension makes this meaningful
      for appends), keeping the loop evidence and the self-reference
      evidence from a single relation;
    - a loop fact must be present exactly as in the scalar paths, and the
      primary strategy exclusion (``distinct from the loop variable``)
      is applied by structure name.

    Supporting facts mirror the scalar paths (one loop fact + one
    container fact); identity comes from the relations, so no new fact
    type is required. No variable-name evidence is used.
    """
    if not (has_while or has_for):
        return None
    sru = getattr(relations, "self_referential_updates", None)
    if not sru:
        return None
    updated_in_loop = getattr(relations, "updated_in_loop", None)
    if not updated_in_loop:
        return None

    loop_fact_id = None
    for fl in facts:
        if fl.fact_type in ("for_loop_iteration", "while_loop_comparison"):
            loop_fact_id = fl.fact_id
            break
    if loop_fact_id is None:
        return None
    loop_var = ""
    for fl in _facts_of_type(facts, "for_loop_iteration"):
        loop_var = fl.attributes.get("loop_variable", "")
        break

    for structure, ops in sru.items():
        if not ops:
            continue
        kinds = updated_in_loop.get(structure) or set()
        if not (kinds & {"for", "while"}):
            continue
        if has_while and "while" in kinds:
            pass
        elif has_for and "for" in kinds:
            if structure and structure == loop_var:
                continue
        else:
            continue
        # Corroborate the relation with a structural fact: the assign form
        # must have a real indexed write on the structure; the append form
        # must have a recorded append operation. This keeps the relation
        # from fabricating evidence no fact supports.
        if "indexed_write" in ops:
            if not _has_fact(facts, "indexed_write", structure):
                continue
        elif "append" in ops:
            if not _has_append_op(relations, structure):
                continue
        else:
            continue
        return TechniqueEvidence(
            technique_id="sequential_accumulation",
            technique_version="1.0.0",
            supporting_fact_ids=[loop_fact_id],
            presence_confidence=0.85,
            centrality=0.6,
        )
    return None


def _has_fact(facts: list[StructuralFact], fact_type: str, structure: str) -> bool:
    """True when a fact of ``fact_type`` records ``structure``."""
    return any(
        f.fact_type == fact_type and f.attributes.get("structure") == structure
        for f in facts
    )


def _has_append_op(relations, structure: str) -> bool:
    """True when the relation layer recorded an ``append`` op on ``structure``."""
    ops = getattr(relations, "collection_ops", {}).get(structure) or set()
    return "append" in ops


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

# ============================================================
# T11: Forward Pointer Advance (same-direction two pointers)
# ============================================================

def _has_genuine_opposite_scan(facts: list[StructuralFact]) -> bool:
    """True when a loop compares two variables that are both modified in it.

    That is the opposite-direction scan shape (left += 1 / right -= 1 under
    ``while left < right``), which is bidirectional_index_scan's territory.
    """
    for wc in _facts_of_type(facts, "while_loop_comparison"):
        compared = set(wc.attributes.get("compared_variables", []))
        modified = set(wc.attributes.get("modified_variables", []))
        if compared and compared <= modified:
            return True
    return False


def _advanced_variables(facts: list[StructuralFact]) -> set:
    """Variables advanced/updated inside loops, from augmented and conditional updates."""
    advanced = set()
    for f in facts:
        if f.fact_type == "accumulator_update":
            var = f.attributes.get("variable", "")
            if var:
                advanced.add(var)
        elif f.fact_type == "conditional_index_update":
            advanced.update(f.attributes.get("updated_variables", []))
    return advanced


def _candidate_vars(facts: list[StructuralFact], index_vars: set) -> Optional[tuple]:
    """Find a candidate variable for conditional selection.

    A candidate variable appears in the ``updated_variables`` of a
    ``conditional_index_update`` fact (i.e. it is assigned inside a
    conditional branch inside a loop) and is NOT ordinary arithmetic
    accumulation: it must have no ``accumulator_update`` fact, which is
    emitted for every augmented assignment (``c += 1``) and every
    self-referential equal-sign assignment (``result = result + [x]``).
    This is the fence that separates scalar candidate replacement from
    running totals/counts/list building regardless of variable name.
    """
    accumulator_vars = {
        f.attributes.get("variable", "")
        for f in facts
        if f.fact_type == "accumulator_update"
    }
    for f in _facts_of_type(facts, "conditional_index_update"):
        updated = f.attributes.get("updated_variables") or []
        candidates = [
            v for v in updated
            if v and v not in index_vars and v not in accumulator_vars
        ]
        if candidates:
            return f, candidates
    return None


def _detect_candidate_selection(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """T12: Candidate Selection (Vocabulary Layer 2)

    Two structural forms feed the same reusable technique:

    - **Loop form** — a loop plus a conditional rebinding of a scalar candidate
      (running max/min, first-match selection, cascading top-k).
    - **Sort form** — a sorting operation plus a bounded (extremum) read of the
      *same* sequence (``nums.sort()`` then ``nums[0]`` / ``nums[-1]`` /
      ``nums[len(nums) - 1]``), i.e. selecting an endpoint candidate from an
      ordered sequence.

    The loop form is evaluated first and is unchanged; the sort form is a
    fallback, so every previously supported input keeps its exact output.

    No variable-name evidence is used: names like best/min/max carry no weight,
    and the non-name requirement is enforced by tests with deliberately
    non-obvious identifiers.
    """
    evidence = _candidate_selection_loop_form(facts, relations)
    if evidence is not None:
        return evidence
    return _candidate_selection_sort_form(facts)


def _candidate_selection_loop_form(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """Loop form of T12 (behavior unchanged).

    Reusable pattern: loop + conditional branch + replacement of a scalar
    candidate inside that branch (running max/min, first-match selection,
    cascading top-k). Built entirely from facts that already exist —
    no new fact types:

    1. Loop evidence: ``for_loop_iteration`` or ``while_loop_comparison``
       (the same loop evidence every other technique requires).
    2. A ``conditional_index_update`` fact whose ``updated_variables``
       include the candidate — the fact is only emitted for variables
       assigned inside a conditional branch inside a loop body.
    3. The candidate is a scalar selection target, not:
       - a subscript index (sliding-window/pointer state) — excluded via
         the M2 ``used_as_subscript_index`` relation (fact fallback:
         ``_collect_subscript_index_vars``), the same index-participation
         fence F4 introduced;
       - an arithmetic accumulator (``total += x``, ``count += 1``,
         ``result = result + [...]``) — excluded via absence of an
         ``accumulator_update`` fact for that variable.

    Does NOT fire for:
    - unconditional loop-carried assignment (no conditional branch);
    - ``if`` inside a loop that does not rebind a scalar candidate;
    - conditional accumulation (accumulator fence);
    - window shrink/pointer state (index-participation fence).

    No variable-name evidence is used: names like best/min/max carry no
    weight, and the non-name requirement is enforced by tests with
    deliberately non-obvious identifiers.
    """
    types = _fact_types(facts)
    has_loop = bool(
        {"for_loop_iteration", "while_loop_comparison", "while_loop_truthiness"} & types
    )
    if not has_loop:
        return None

    # Index participation: prefer the shared M2 relation when provided,
    # fall back to the equivalent fact-based collection otherwise.
    relation_index_vars = getattr(relations, "used_as_subscript_index", None)
    index_vars = (
        set(relation_index_vars)
        if relation_index_vars
        else _collect_subscript_index_vars(facts)
    )

    found = _candidate_vars(facts, index_vars)
    if not found:
        return None
    cond_fact, _candidates = found

    supporting = [cond_fact.fact_id]
    for fl in facts:
        if fl.fact_type in {"for_loop_iteration", "while_loop_comparison"}:
            supporting.append(fl.fact_id)
            break
    # Early termination corroborates selection (first-match/break-after-choose)
    # over plain state maintenance; included only when actually present.
    supporting.extend(
        f.fact_id for f in facts if f.fact_type == "early_termination"
    )
    supporting = list(dict.fromkeys(supporting))

    return TechniqueEvidence(
        technique_id="candidate_selection",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=0.8,
        centrality=0.7,
    )


def _candidate_selection_sort_form(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """Sort form of T12: sorting operation + bounded read of the same sequence.

    Required evidence, both name-free:

    1. ``sorting_operation`` — ``x.sort(...)`` (the sorted variable is ``x``) or
       ``y = sorted(x, ...)`` (the sorted variable is ``y``).
    2. ``extremum_access`` on that *same* variable — a load subscript at a
       bounded index (``arr[0]``, ``arr[-1]``, ``arr[len(arr) - 1]``).

    A bounded read is what expresses "select an endpoint candidate". A sorted
    sequence that is only returned, iterated, or read at a **variable** index
    (``arr[i]`` — two-pointer / binary-search movement) produces no
    ``extremum_access`` fact and therefore no detection.
    """
    sort_facts = [
        f for f in _facts_of_type(facts, "sorting_operation")
        if f.attributes.get("structure")
    ]
    if not sort_facts:
        return None

    reads: dict = {}
    for f in _facts_of_type(facts, "extremum_access"):
        structure = f.attributes.get("structure", "")
        if structure:
            reads.setdefault(structure, f)

    for sort_fact in sort_facts:
        read = reads.get(sort_fact.attributes["structure"])
        if read is None:
            continue
        supporting = [sort_fact.fact_id, read.fact_id]
        # Early termination corroborates selection (select-then-return).
        supporting.extend(
            f.fact_id for f in facts if f.fact_type == "early_termination"
        )
        supporting = list(dict.fromkeys(supporting))
        return TechniqueEvidence(
            technique_id="candidate_selection",
            technique_version="1.0.0",
            supporting_fact_ids=supporting,
            presence_confidence=0.8,
            centrality=0.7,
        )
    return None


# ============================================================
# T13: Hash Lookup (Vocabulary Layer 2)
# ============================================================

#: Mapping kinds that establish a key->value lookup identity. ``Counter`` is
#: deliberately absent: it is the counting identity (frequency semantics), and
#: must not automatically produce generic lookup evidence.
_LOOKUP_MAPPING_KINDS = frozenset(
    {"dict_empty", "dict_literal", "dict", "defaultdict"}
)


def _detect_hash_lookup(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """T13: Hash Lookup (Vocabulary Layer 2)

    Reusable pattern: a key->value mapping is constructed and the program
    *reads* it by key, or tests key existence on it. Both facts are name-free:

    1. ``mapping_construction`` whose ``kind`` is a dict family member
       (``dict_empty`` / ``dict_literal`` / ``dict`` / ``defaultdict``).
       ``Counter`` is excluded (it is the counting identity), and sets/
       lists never produce the fact at all, so set/list membership can never
       reach this technique.
    2. Lookup evidence *on that same variable*, either:
       - ``membership_test`` — ``key in m`` / ``key not in m`` (key-existence
         check), or
       - ``subscript_read`` — a keyed read whose result gates control flow
         (``if m[k] > x``). An ungated read used only for arithmetic or
         aggregation (e.g. a frequency counter being incremented) does not
         qualify, which keeps counting maps out of the lookup vocabulary.

    Does NOT fire for:
    - set / list / input-array membership (no mapping identity exists);
    - a mapping that is constructed but never read by key (db-193 shape:
      write-only + ``.get`` outside a decision);
    - ``Counter`` construction alone;
    - recursive memoization — a dict used as a recursion memo has the same
      construction + membership shape as a lookup map, so ``recursive_branching``
      evidence is an explicit exclusion (the same concept the GT mapping names).

    No variable-name evidence is used: names like ``dict``/``map``/``seen``/
    ``cache`` carry no weight.
    """
    types = _fact_types(facts)

    # Memoization fence: recursion means the mapping is a memo table, which
    # is the recursive_branching concept's territory, not lookup's.
    if _detect_recursive_branching(facts) is not None:
        return None

    lookup_maps: dict = {}
    for f in _facts_of_type(facts, "mapping_construction"):
        var = f.attributes.get("variable", "")
        kind = f.attributes.get("kind", "")
        if var and kind in _LOOKUP_MAPPING_KINDS:
            lookup_maps.setdefault(var, f)
    if not lookup_maps:
        return None

    membership: dict = {}
    for f in _facts_of_type(facts, "membership_test"):
        var = f.attributes.get("variable", "")
        if var:
            membership.setdefault(var, f)

    reads: dict = {}
    for f in _facts_of_type(facts, "subscript_read"):
        structure = f.attributes.get("structure", "")
        if structure:
            reads.setdefault(structure, f)

    for var, map_fact in lookup_maps.items():
        trigger = membership.get(var) or reads.get(var)
        if trigger is None:
            continue
        supporting = [map_fact.fact_id, trigger.fact_id]
        # Include any other construction fact for the same mapping so the
        # citation is complete when a variable is constructed more than once.
        for f in _facts_of_type(facts, "mapping_construction"):
            if f.attributes.get("variable") == var:
                supporting.append(f.fact_id)
        supporting = list(dict.fromkeys(supporting))
        return TechniqueEvidence(
            technique_id="hash_lookup",
            technique_version="1.0.0",
            supporting_fact_ids=supporting,
            presence_confidence=0.8,
            centrality=0.65,
        )
    return None


# ============================================================
# T14: Frequency Counting (Vocabulary Layer 2)
# ============================================================

#: Mapping kinds that can carry occurrence tallies. Every kind still needs a
#: counted update (Branch A); ``Counter`` additionally establishes counting
#: identity by construction, so a single counted read is enough for it.
_FREQUENCY_MAP_KINDS = frozenset(
    {"Counter", "defaultdict", "dict_empty", "dict_literal", "dict"}
)

#: Augmented-assignment operators that tally occurrences.
_COUNT_OPERATORS = frozenset({"Add", "Sub"})

#: Index shapes that are merely positional, not keys. A pre-sized count array
#: must be written with a *keyed* index (`cnt[ord(c) - ord('a')]`); this fence
#: also keeps an exotic `dp[i] += dp[i - 2]` table out of frequency counting.
_TRIVIAL_INDEX_TYPES = frozenset({"Name", "Constant"})


def _detect_frequency_counting(
    facts: list[StructuralFact], relations=None
) -> Optional[TechniqueEvidence]:
    """T14: Frequency Counting (Vocabulary Layer 2)

    Reusable pattern: a tally of occurrences by key/value. Two structural
    branches, both name-free and both built from existing facts plus the write
    form/operator carried by ``indexed_write``:

    **Branch A — counting map** (``Counter``/``defaultdict``/``{}``/literal/``dict()``)
    needs a **counted write**: an encoded update on that mapping variable in
    **augmented form with an Add/Sub operator** (``cnt[x] += 1``,
    ``cnt[x] -= 1``). ``Counter(data)`` establishes counting identity by its
    construction, so it needs one counted write *or* one counted read
    (``freq[i]`` in a condition) instead.

    **Branch B — pre-sized count array** needs a ``list_construction`` of kind
    ``list_mult`` (``cnt = [0] * 26``) **plus** a counted write on that variable
    with a **keyed** index (``cnt[ord(s[i]) - ord('a')] += 1``). A positional
    write (``cnt[i] += 1``) is not a frequency update.

    Does NOT fire for:
    - sets and set membership (no mapping identity, no pre-sized list);
    - ordinary scalar accumulation (``total += x`` — target is not subscripted);
    - ordinary map building (``groups[k] = v`` — assignment, not a counted
      update);
    - plain ``[0] * n`` tables without a keyed counted write (DP arrays assign,
      they do not tally);
    - memoization (``recursive_branching`` evidence is excluded).

    No variable-name evidence is used: names like ``cnt``/``freq``/``count``
    carry no weight.
    """
    # Memoization fence: recursion means a dict is a memo table, not a tally.
    if _detect_recursive_branching(facts) is not None:
        return None

    counted_writes: dict = {}
    for f in _facts_of_type(facts, "indexed_write"):
        if f.attributes.get("syntax_form") != "augmented":
            continue
        if f.attributes.get("operator") not in _COUNT_OPERATORS:
            continue
        structure = f.attributes.get("structure", "")
        if structure:
            counted_writes.setdefault(structure, f)

    reads: dict = {}
    for f in _facts_of_type(facts, "subscript_read"):
        structure = f.attributes.get("structure", "")
        if structure:
            reads.setdefault(structure, f)

    def _evidence(*fact_ids: str) -> TechniqueEvidence:
        return TechniqueEvidence(
            technique_id="frequency_counting",
            technique_version="1.0.0",
            supporting_fact_ids=list(dict.fromkeys(fact_ids)),
            presence_confidence=0.8,
            centrality=0.7,
        )

    # Branch A: counting map
    for f in _facts_of_type(facts, "mapping_construction"):
        var = f.attributes.get("variable", "")
        kind = f.attributes.get("kind", "")
        if not var or kind not in _FREQUENCY_MAP_KINDS:
            continue
        write = counted_writes.get(var)
        if write is not None:
            return _evidence(f.fact_id, write.fact_id)
        if kind == "Counter" and var in reads:
            # Counter(data) already tallied; a counted read shows it is used.
            return _evidence(f.fact_id, reads[var].fact_id)

    # Branch B: pre-sized count array
    for f in _facts_of_type(facts, "list_construction"):
        if f.attributes.get("kind") != "list_mult":
            continue
        var = f.attributes.get("variable", "")
        if not var:
            continue
        write = counted_writes.get(var)
        if write is None:
            continue
        if write.attributes.get("index_type") in _TRIVIAL_INDEX_TYPES:
            continue
        return _evidence(f.fact_id, write.fact_id)

    return None


def _detect_forward_pointer_advance(facts: list[StructuralFact]) -> Optional[TechniqueEvidence]:
    """T11: Forward Pointer Advance (same-direction two pointers)

    Two or more pointers progressing through the SAME sequence in the SAME
    direction (array indices moving right, or multiple node references
    walking .next/.left/.right). Built entirely from facts that already
    exist — no new fact types:

    Path A (linked / pointer structures): ``multiple_pointer_traversal``
        itself requires two or more distinct receivers accessing
        .next/.left/.right inside a while-loop body, which is exactly
        same-direction multi-pointer progression.

    Path B (subscripted sequences): at least two distinct variables are used
        as subscript indices (``subscript_index_access``) and at least one of
        them is advanced inside a loop (``accumulator_update`` /
        ``conditional_index_update``). That is the arr[left]/arr[right] shape
        with one pointer stepping forward.

    Absence constraint: a genuine opposite-direction scan is excluded. That
    shape belongs to ``bidirectional_index_scan``, whose behavior is
    unchanged; this technique exists because same-direction progression had
    no representation at all.

    Does NOT fire for:
    - opposite-direction scans (two pointers converging)
    - single-index iteration loops (only one index variable participates)
    - scalar accumulation loops (no index participation)
    """
    types = _fact_types(facts)
    has_loop = bool(
        {"while_loop_comparison", "while_loop_truthiness", "for_loop_iteration"} & types
    )

    # Path A: existing structural evidence of multi-pointer traversal.
    # multiple_pointer_traversal is emitted only from while-loop bodies,
    # so it already implies a loop for linked-structure code.
    has_multi_pointer = "multiple_pointer_traversal" in types

    # Path B: index participation on a subscripted sequence.
    # Union-find root chasing (while parent[x] != x: x = parent[x]) also reads
    # as "an index variable advanced inside a loop", but it is pointer chasing
    # through a parent array, not two pointers progressing through a sequence.
    # parent_pointer_chase already identifies that shape, so it excludes path B.
    index_vars = _collect_subscript_index_vars(facts)
    advanced_index_vars = index_vars & _advanced_variables(facts)
    has_index_pair = (
        has_loop
        and len(index_vars) >= 2
        and bool(advanced_index_vars)
        and "parent_pointer_chase" not in types
    )

    if not (has_multi_pointer or has_index_pair):
        return None

    if _has_genuine_opposite_scan(facts):
        return None

    wanted = {
        "multiple_pointer_traversal", "subscript_index_access",
        "accumulator_update", "conditional_index_update",
        "while_loop_comparison", "while_loop_truthiness", "for_loop_iteration",
        "linked_structure_traversal", "pointer_rewiring",
    }
    supporting = [f.fact_id for f in facts if f.fact_type in wanted]

    # Corroborated by two independent structural paths = higher confidence.
    confidence = 0.85 if (has_multi_pointer and has_index_pair) else 0.8
    centrality = 0.75

    return TechniqueEvidence(
        technique_id="forward_pointer_advance",
        technique_version="1.0.0",
        supporting_fact_ids=supporting,
        presence_confidence=confidence,
        centrality=centrality,
    )


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
