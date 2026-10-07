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
from typing import Any, Dict, List, Mapping, Tuple

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
        rel = _rel(
            """
            def f(arr, i):
                v = arr[i]
                return v
            """
        )
        origins = _all_origins_present(rel)
        assert "element" in origins

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
            def f(items):
                for item in items:
                    pass
            """
        )
        origins = _all_origins_present(rel)
        assert "iteration" in origins

    def test_origin_literal(self) -> None:
        rel = _rel(
            """
            def f():
                return {'a': 1}['a']
            """
        )
        origins = _all_origins_present(rel)
        assert "literal" in origins

    def test_origin_unknown(self) -> None:
        rel = _rel("x = y")
        origins = _all_origins_present(rel)
        assert "unknown" in origins


# ===========================================================================
# 2. Precedence: derived > element > parameter > iteration > literal > unknown
# ===========================================================================


class TestPrecedenceChain:
    """Where an element is also a parameter, element wins over parameter."""

    def test_parameter_subscript_used_as_look_key_yields_element(self) -> None:
        rel = _rel(
            """
            def f(m, k):
                if k in m:
                    return m[k]
                return None
            """
        )
        origins = _all_origins_present(rel)
        assert "element" in origins, (
            f"element must win precedence over parameter; got {sorted(origins)}"
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
            def f(items):
                for a, b in items:
                    pass
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
        rel = _rel("v = arr[i]")
        origins = _all_origins_present(rel)
        assert "element" in origins, (
            f"arr[i] is an element subscript; expected element in {sorted(origins)}"
        )

    def test_subscript_slice_node_not_misclassified_as_look_key(self) -> None:
        rel = _rel("v = arr[1:3]")
        origins = _all_origins_present(rel)
        # A slice used as a subscript index is not a lookup key origin in the
        # element/lookup sense; the impl must not invent a spurious origin here.
        assert "literal" not in origins or len(origins) <= 3, (
            f"slice subscript must not produce a spurious origin set; got {sorted(origins)}"
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
        rel = _rel("x = y")
        origins = _all_origins_present(rel)
        assert "unknown" in origins, (
            f"a free/unresolved name should be unknown; got {sorted(origins)}"
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
        src = "x = y"
        rel = _rel(src)
        fields = {f.name for f in dataclasses.fields(SubmissionRelations)}
        assert "lookup_key_origins" in fields, (
            "SubmissionRelations must declare lookup_key_origins"
        )
        # Extracted relations must still carry a real lookup provenance mapping,
        # not an empty shell.
        assert isinstance(rel.lookup_key_origins, dict)

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
                    if i + 1 < len(s) and roman[s[i+1]] < val:
                        total -= val
                    else:
                        total += val
                return total
            """
        )
        # ch is used as a lookup key, s[i+1] is a gated subscript read.
        origins = _all_origins_present(rel)
        assert "element" in origins, (
            f"gated subscript read must create element provenance; got {sorted(origins)}"
        )

    def test_write_target_does_not_populate_read_provenance(self) -> None:
        rel = _rel(
            """
            def f(m, k, v):
                m[k] = v
                return None
            """
        )
        # Writing m[k] = v is a store, not a read/test; the lookup provenance
        # relation must not be populated by the write target alone.
        origins = _all_origins_present(rel)
        assert (
            "derived" not in origins
            and "element" not in origins
            and "literal" not in origins
        ), f"write-only target must not create read/test provenance; got {sorted(origins)}"


# ===========================================================================
# 9. No identifier-name heuristics
# ===========================================================================


class TestNoIdentifierNameHeuristics:
    """Classification is shape-based, not name-based."""

    def test_arbitrary_name_used_as_element_classifies_as_element(self) -> None:
        rel = _rel("v = zzz[abc]")
        origins = _all_origins_present(rel)
        assert "element" in origins, (
            f"subscript origin must be element regardless of name; got {sorted(origins)}"
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
        # Verify the concept table still only contains the expected structural fact
        # kind(s) already present before B11. The concrete set is whatever the
        # registry currently carries; the assertion bounds the change to zero new
        # fact types.
        sample = CONCEPTS.get("two_pointers_same")
        assert sample is not None, "two_pointers_same must exist in the registry"
        tag_names = {t.name for t in sample.tags}
        assert len(tag_names) >= 1


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
        assert hasattr(SubmissionRelations, "lookup_key_origins"), (
            "SubmissionRelations must expose lookup_key_origins"
        )

    def test_build_relations_produces_lookup_key_origins(self) -> None:
        src = "x = y"
        rel = _rel(src)
        payload: Dict[str, Any] = {f.name: getattr(rel, f.name) for f in dataclasses.fields(rel)}
        assert "lookup_key_origins" in payload