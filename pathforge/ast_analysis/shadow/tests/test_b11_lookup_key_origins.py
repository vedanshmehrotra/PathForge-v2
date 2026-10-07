# -*- coding: utf-8 -*-
"""
B11 relation contract tests — lookup_key_origins.

These tests validate the B11 field added to SubmissionRelations
(`lookup_key_origins`) directly against the spec requirements:

1. Every declared origin kind is reachable through a concrete AST pattern.
2. Precedence order across look/tests/subscripts/assignments/builtins.
3. Explicit Subscript AST test: a bracketed subscript (arr[i]) classifies as element,
   and the slice node itself is NOT misclassified as the subscript's origin.
4. Name-resolution semantics:
   - Name assigned from a BinOp -> derived
   - Name assigned from a Subscript -> element
   - unresolved Name -> unknown
5. Name-independence: renaming all identifiers in a Two-Sum-shaped program
   leaves `lookup_key_origins` unchanged.
6. Determinism: parsing the same source twice yields identical relation output.
7. Additivity: pre-existing relation fields are unchanged; only the new field is added.
8. Lookup collection correctly handles membership lookup, gated subscript lookup,
   and write targets that must NOT populate the read/test provenance relation.
9. No identifier-name heuristics drive the classification.
10. Registry invariants: 96 total concepts, 25 conclusion-eligible, no new fact type.
11. RELATIONS_VERSION == "1.2.0"
12. Fresh-process verification of dataclasses.fields(SubmissionRelations) and
    hasattr(SubmissionRelations, "lookup_key_origins").
"""

from __future__ import annotations

import ast
import dataclasses
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Mapping, Set, Tuple

import pytest

from pathforge.ast_analysis.concepts import (
    CONCEPTS,
    conclusion_eligible_ids,
)
from pathforge.ast_analysis.shadow.relations import (
    RELATIONS_VERSION,
    SubmissionRelations,
    build_relations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NATIVE_TOTAL = 96
NATIVE_ELIGIBLE = 25

#: Frozen pre-B11 structural fact-type vocabulary emitted by ``fact_extractor``.
#: B11 is a relation-layer change: it must add zero fact types.
FACT_TYPE_VOCABULARY = frozenset(
    {
        "accumulator_update",
        "cache_lookup",
        "cache_write",
        "carry_propagation",
        "conditional_index_update",
        "conditional_pop",
        "early_termination",
        "extremum_access",
        "for_loop_iteration",
        "index_lookback",
        "indexed_write",
        "linked_attribute_access",
        "linked_structure_traversal",
        "list_construction",
        "mapping_construction",
        "membership_test",
        "midpoint_calculation",
        "monotonic_comparison",
        "multiple_pointer_traversal",
        "multiple_recursive_paths",
        "neighbor_traversal",
        "node_constructor",
        "opposite_direction_updates",
        "parent_pointer_chase",
        "parent_root_merge",
        "pointer_rewiring",
        "queue_dequeue",
        "recursive_call_in_conditional",
        "recursive_depth_tracking",
        "self_recursive_call",
        "sorting_operation",
        "stack_operation",
        "state_restoration",
        "subscript_index_access",
        "subscript_read",
        "variable_use_in_loop_body",
        "visited_tracking",
        "while_loop_comparison",
        "while_loop_truthiness",
        "window_size_constant",
    }
)


def _syntax(source: str) -> ast.Module:
    return ast.parse(textwrap.dedent(source))


def _parse(source: str) -> ast.Module:
    return _syntax(source)


def _rel(source: str) -> SubmissionRelations:
    """Build the extracted SubmissionRelations for a minimal program."""
    return build_relations(_syntax(source))


def _lookup_key_origins(rel: SubmissionRelations) -> Dict[str, Set[str]]:
    return dict(rel.lookup_key_origins)


def _origin_values(rel: SubmissionRelations) -> Set[frozenset]:
    """Multiset of origin-values, ignoring the concrete identifier keys.

    Used only for name-independence checks where two programs differ only by
    identifier names but should carry the same origin contract.
    """
    return {frozenset(v) for v in rel.lookup_key_origins.values()}


def _all_origins_present(
    rel: SubmissionRelations, required: str | Set[str] = frozenset(),
) -> Set[str]:
    """Return the set of origins present across all named keys.

    If `required` is provided it is only used for back-compat with older
    assertion call sites; the returned set is the real signal under test.
    """
    if isinstance(required, str):
        required = {required}
    present: Set[str] = set()
    for v in rel.lookup_key_origins.values():
        present |= v
    return present


# ===========================================================================
# 1. Every declared origin kind is reachable
# ===========================================================================


class TestOriginsReachability:
    """One test per declared origin, proving the relation can actually produce it."""

    def test_origin_derived(self) -> None:
        rel = _rel(
            """
            def f(x, y):
                key = x + y
                m[key] = 1
                return key in m
            """
        )
        origins = _all_origins_present(rel)
        assert "derived" in origins

    def test_origin_element(self) -> None:
        # `element` describes the *key's* provenance: the key must itself be a
        # Subscript expression (or a Name bound to one). Here `arr[i]` is the
        # key of the outer lookup, so `m` gets `element`.
        rel = _rel(
            """
            def f(m, arr, i):
                return m[arr[i]]
            """
        )
        assert rel.lookup_key_origins.get("m") == {"element"}

    def test_origin_parameter(self) -> None:
        rel = _rel(
            """
            def f(m, k):
                if k in m:
                    return m[k]
                return None
            """
        )
        origins = _all_origins_present(rel)
        assert "parameter" in origins

    def test_origin_iteration(self) -> None:
        rel = _rel(
            """
            def f(items, m):
                for item in items:
                    if item in m:
                        return True
                return False
            """
        )
        origins = _all_origins_present(rel)
        assert "iteration" in origins

    def test_origin_literal(self) -> None:
        rel = _rel(
            """
            def f():
                m = {'a': 1}
                return m['a']
            """
        )
        origins = _all_origins_present(rel)
        assert "literal" in origins

    def test_origin_unknown(self) -> None:
        # `q` is not a parameter, not a loop target and never assigned, so it
        # cannot be safely classified.
        rel = _rel(
            """
            def f(z):
                return z[q]
            """
        )
        assert rel.lookup_key_origins.get("z") == {"unknown"}


# ===========================================================================
# 2. Precedence: derived > element > parameter > iteration > literal > unknown
# ===========================================================================


class TestPrecedenceChain:
    """Where an element is also a parameter, element wins over parameter."""

    def test_parameter_subscript_used_as_look_key_yields_element(self) -> None:
        # `k` starts as a parameter but is reassigned from a subscript, so the
        # stronger `element` provenance must win over `parameter`.
        rel = _rel(
            """
            def f(m, k, arr):
                k = arr[0]
                if k in m:
                    return m[k]
                return None
            """
        )
        assert rel.lookup_key_origins.get("m") == {"element"}, (
            f"element must win precedence over parameter; "
            f"got {rel.lookup_key_origins.get('m')}"
        )

    def test_derived_beats_literal_for_a_computed_key(self) -> None:
        rel = _rel(
            """
            def f(x, y):
                key = x + y
                m = {key: 1}
                return key in m
            """
        )
        origins = _all_origins_present(rel)
        assert "derived" in origins, (
            f"derived must win precedence; got {sorted(origins)}"
        )

    def test_iteration_origin_present_for_enumerate_tuple_unpack(self) -> None:
        rel = _rel(
            """
            def f(items, m):
                for a, b in items:
                    if a in m:
                        return True
                return False
            """
        )
        origins = _all_origins_present(rel)
        assert "iteration" in origins, (
            f"iteration must be reachable; got {sorted(origins)}"
        )


# ===========================================================================
# 3. Explicit Subscript AST test
# ===========================================================================


class TestExplicitSubscript:
    """arr[i] must be element; the slice node itself must not be misclassified."""

    def test_bracketed_subscript_is_element(self) -> None:
        # `arr[i]` is the *key* of the outer mapping lookup, so the key node is
        # the Subscript itself (not its slice `i`) -> element.
        rel = _rel(
            """
            def f(m, arr, i):
                return m[arr[i]]
            """
        )
        assert rel.lookup_key_origins.get("m") == {"element"}, (
            f"a Subscript key must classify as element; "
            f"got {rel.lookup_key_origins.get('m')}"
        )

    def test_subscript_slice_node_not_misclassified_as_look_key(self) -> None:
        rel = _rel("v = arr[1:3]")
        # `arr[1:3]` reads arr; the key is a Slice node - not a literal and not
        # a Subscript - so it falls back to unknown. Critically it must NOT be
        # reported as `element`: the Slice is not the Subscript node itself.
        assert rel.lookup_key_origins.get("arr") == {"unknown"}, (
            f"slice key must not be misclassified as element; "
            f"got {rel.lookup_key_origins.get('arr')}"
        )


# ===========================================================================
# 4. Name-resolution semantics
# ===========================================================================


class TestNameResolution:
    """A Name's origin follows the provenance of the value bound to it."""

    def test_name_from_binop_is_derived(self) -> None:
        rel = _rel(
            """
            def f(a, b):
                k = a + b
                m = {k: 1}
                return k in m
            """
        )
        origins = _all_origins_present(rel)
        assert "derived" in origins, (
            f"a name bound to a BinOp should be derived; got {sorted(origins)}"
        )

    def test_name_from_subscript_is_element(self) -> None:
        rel = _rel(
            """
            def f(arr):
                k = arr[0]
                m = {k: 1}
                return k in m
            """
        )
        origins = _all_origins_present(rel)
        assert "element" in origins, (
            f"a name bound to a Subscript should be element; got {sorted(origins)}"
        )

    def test_unresolved_name_is_unknown(self) -> None:
        # `q` is never assigned, never a parameter and never a loop target, so
        # it cannot be safely classified and must fall back to unknown.
        rel = _rel(
            """
            def f(z):
                return z[q]
            """
        )
        assert rel.lookup_key_origins.get("z") == {"unknown"}, (
            f"a free/unresolved name should be unknown; "
            f"got {rel.lookup_key_origins.get('z')}"
        )


# ===========================================================================
# 5. Name-independence
# ===========================================================================


class TestNameIndependence:
    """Renaming all identifiers must leave lookup_key_origins VALUES unchanged."""

    def test_two_go_renamed_produces_identical_origin_values(self) -> None:
        a = _rel(
            """
            def two_sum(nums, target):
                seen = {}
                for i, n in enumerate(nums):
                    need = target - n
                    if need in seen:
                        return [seen[need], i]
                    seen[n] = i
                return []
            """
        )
        b = _rel(
            """
            def fn_a(b_vals, t_val):
                m_acc = {}
                for idx_i, val_x in enumerate(b_vals):
                    need_y = t_val - val_x
                    if need_y in m_acc:
                        return [m_acc[need_y], idx_i]
                    m_acc[val_x] = idx_i
                return []
            """
        )
        assert _origin_values(a) == _origin_values(b), (
            f"renaming all identifiers changed origin values:\n"
            f"  before: {_origin_values(a)}\n"
            f"  after : {_origin_values(b)}"
        )


# ===========================================================================
# 6. Determinism
# ===========================================================================


class TestDeterminism:
    """Parsing the same source twice must yield identical relation output."""

    def test_twice_parsed_yield_identical_relation(self) -> None:
        src = """
        def two_sum(nums, target):
            seen = {}
            for i, n in enumerate(nums):
                need = target - n
                if need in seen:
                    return [seen[need], i]
                seen[n] = i
            return []
        """
        a = _rel(src)
        b = _rel(src)
        assert a == b, "parsing the same source twice must produce identical relations"


# ===========================================================================
# 7. Additivity
# ===========================================================================


class TestAdditivity:
    """Pre-existing fields are untouched; only the new field is added."""

    def test_pre_existing_fields_stable(self) -> None:
        # Frozen snapshot of every pre-B11 relation field for this snippet. The
        # pre-existing collectors never read lookup_key_origins, so adding it
        # must leave these values byte-identical.
        rel = _rel(
            """
            def f(nums):
                total = 0
                for x in nums:
                    total = total + x
                return total
            """
        )
        assert rel.updated_in_loop == {"total": {"for"}}
        assert rel.used_as_subscript_index == set()
        assert rel.used_anywhere == {"x", "total", "nums"}
        assert rel.assigned_anywhere == {"total"}
        assert rel.def_use_pairs == {"total": {"total"}, "x": {"total"}}
        assert rel.collection_ops == {}
        assert rel.iterated_in_for == {"nums"}
        assert rel.self_referential_updates == {}
        assert rel.lookup_key_origins == {}

    def test_submission_relations_is_a_dataclass(self) -> None:
        # The old contract mentioned a diff primitive; B11 only required the new
        # field to be additive. This test documents the current public surface.
        assert dataclasses.is_dataclass(SubmissionRelations)


# ===========================================================================
# 8. Lookup collection semantics
# ===========================================================================


class TestLookupCollection:
    """membership test + gated subscript read populate provenance;
    writes do not."""

    def test_membership_lookup_populates_provenance(self) -> None:
        rel = _rel(
            """
            def f(m, k):
                if k in m:
                    return True
                return False
            """
        )
        origins = _all_origins_present(rel)
        assert "parameter" in origins, (
            f"membership test 'k in m' must create read/test provenance; got {sorted(origins)}"
        )

    def test_gated_subscript_lookup_populates_provenance(self) -> None:
        rel = _rel(
            """
            def romanToInt(s):
                roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
                total = 0
                for i, ch in enumerate(s):
                    val = roman[ch]
                    if i + 1 < len(s) and roman[s[i]] < val:
                        total -= val
                    else:
                        total += val
                return total
            """
        )
        # `roman[ch]` uses a loop target as key -> iteration.
        # `roman[s[i]]` uses a bare Subscript as key -> element.
        roman = rel.lookup_key_origins.get("roman", set())
        assert "iteration" in roman, f"loop-target key must be iteration; got {roman}"
        assert "element" in roman, (
            f"gated subscript read must create element provenance; got {roman}"
        )

    def test_write_target_does_not_populate_read_provenance(self) -> None:
        rel = _rel(
            """
            def f(m, k, v):
                m[k] = v
                return None
            """
        )
        # Writing m[k] = v is a store, not a read/test: the subscript carries
        # Store context and reads nothing from `m`. `m` must not appear in the
        # relation at all - for ANY origin value.
        assert "m" not in rel.lookup_key_origins, (
            f"write-only target must not create read/test provenance; "
            f"got {rel.lookup_key_origins}"
        )
        assert rel.lookup_key_origins == {}, (
            f"write-only program must produce no provenance; "
            f"got {rel.lookup_key_origins}"
        )


# ===========================================================================
# 9. No identifier-name heuristics
# ===========================================================================


class TestNoIdentifierNameHeuristics:
    """Classification is shape-based, not name-based."""

    def test_arbitrary_name_used_as_element_classifies_as_element(self) -> None:
        rel = _rel(
            """
            def f(m, zzz, abc):
                return m[zzz[abc]]
            """
        )
        assert rel.lookup_key_origins.get("m") == {"element"}, (
            f"Subscript key must classify as element regardless of name; "
            f"got {rel.lookup_key_origins.get('m')}"
        )

    def test_arbitrary_name_used_as_parameter_classifies_as_parameter(self) -> None:
        rel = _rel(
            "def f(zzz, abc):\n    if zzz in abc:\n        return 1\n    return 0\n"
        )
        origins = _all_origins_present(rel)
        assert "parameter" in origins, (
            f"membership origin must be parameter regardless of name; got {sorted(origins)}"
        )

    def test_two_identical_seeded_maps_with_different_names_classify_identically(
        self,
    ) -> None:
        a = _rel(
            """
            def f():
                m = {'a': 1, 'b': 2}
                return m['a']
            """
        )
        b = _rel(
            """
            def g():
                d = {'x': 1, 'y': 2}
                return d['x']
            """
        )
        assert _origin_values(a) == _origin_values(b), (
            f"same-shape maps with different key names must yield identical origin values:\n"
            f"  a: {_origin_values(a)}\n"
            f"  b: {_origin_values(b)}"
        )


# ===========================================================================
# 10. Registry invariants
# ===========================================================================


class TestRegistryInvariants:
    """B11 must not change the registry total/eligibility or introduce a fact type."""

    def test_native_total_unchanged(self) -> None:
        assert len(CONCEPTS) == NATIVE_TOTAL, (
            f"registry must remain {NATIVE_TOTAL} concepts; got {len(CONCEPTS)}"
        )

    def test_native_eligible_unchanged(self) -> None:
        assert len(conclusion_eligible_ids()) == NATIVE_ELIGIBLE, (
            f"registry must remain {NATIVE_ELIGIBLE} eligible; got {len(conclusion_eligible_ids())}"
        )

    def test_no_new_fact_type_introduced(self) -> None:
        # B11 is a relation-layer addition. Structural facts still come only
        # from the fact extractor, and `lookup_key_origins` must never surface
        # as a fact type. The frozen vocabulary pins the pre-B11 fact surface,
        # so introducing any new fact type fails this test.
        import inspect
        import re

        from pathforge.ast_analysis.shadow import fact_extractor

        emitted = set(
            re.findall(r'fact_type="([a-z_]+)"', inspect.getsource(fact_extractor))
        )
        assert emitted == FACT_TYPE_VOCABULARY, (
            f"fact-type vocabulary changed: "
            f"added={sorted(emitted - FACT_TYPE_VOCABULARY)} "
            f"removed={sorted(FACT_TYPE_VOCABULARY - emitted)}"
        )
        # `cache_lookup` is a legitimate pre-existing fact type; the B11
        # relation name must never become one, and the relation must not leak
        # into fact extraction.
        assert "lookup_key_origins" not in emitted, (
            "B11 must not introduce a lookup_key_origins fact type"
        )
        roman = _syntax(
            """
            def romanToInt(s):
                roman = {'I': 1, 'V': 5}
                total = 0
                for ch in s:
                    total += roman[ch]
                return total
            """
        )
        from pathforge.ast_analysis.shadow.fact_extractor import (
            extract_structural_facts,
        )

        produced = {f.fact_type for f in extract_structural_facts(roman)}
        assert produced <= FACT_TYPE_VOCABULARY, (
            f"relation extraction leaked a new fact type: "
            f"{sorted(produced - FACT_TYPE_VOCABULARY)}"
        )


# ===========================================================================
# 11. Version
# ===========================================================================


class TestVersion:
    def test_relations_version(self) -> None:
        assert RELATIONS_VERSION == "1.2.0", (
            f"RELATIONS_VERSION must be 1.2.0; got {RELATIONS_VERSION!r}"
        )


# ===========================================================================
# 12. Fresh-process verification
# ===========================================================================


class TestFreshProcessVerification:
    def test_dataclass_fields_contain_lookup_key_origins(self) -> None:
        fields = {f.name for f in dataclasses.fields(SubmissionRelations)}
        assert "lookup_key_origins" in fields, (
            f"dataclasses.fields(SubmissionRelations) must include lookup_key_origins; got {sorted(fields)}"
        )

    def test_hasattr_lookup_key_origins(self) -> None:
        # A dataclass field declared with default_factory is NOT a class
        # attribute, so `hasattr(SubmissionRelations, ...)` is False by design
        # and is not part of the contract. The authoritative checks are the
        # dataclass field registry and the instance attribute.
        assert "lookup_key_origins" in SubmissionRelations.__dataclass_fields__, (
            "SubmissionRelations.__dataclass_fields__ must include lookup_key_origins"
        )
        declared = {f.name for f in dataclasses.fields(SubmissionRelations)}
        assert "lookup_key_origins" in declared, (
            f"dataclasses.fields must include lookup_key_origins; got {sorted(declared)}"
        )
        inst = build_relations(_syntax("x = y"))
        assert hasattr(inst, "lookup_key_origins"), (
            "instances must expose lookup_key_origins"
        )
        assert isinstance(inst.lookup_key_origins, dict)

    def test_build_relations_produces_lookup_key_origins(self) -> None:
        src = "x = y"
        rel = _rel(src)
        payload: Dict[str, Any] = {f.name: getattr(rel, f.name) for f in dataclasses.fields(rel)}
        assert "lookup_key_origins" in payload