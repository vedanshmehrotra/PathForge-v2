"""Generalized regression tests for architecture hardening M1 + M2.

M1 — normalized statement-operation dispatch: operation-level fact
detectors run once per statement form (Expr, Assign, AnnAssign, AugAssign,
tuple-unpack), so an operation can never again be recognized in one
statement family and silently missed in another.

M2 — shared relational evidence: ``relations.py`` computes variable
relations once per submission and ``sequential_accumulation`` consumes
them as its loop-membership oracle with a byte-identical fallback.

Tests are written against structure, not problem IDs.
"""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import (
    extract_structural_facts,
    _OPERATION_STATEMENTS,
)
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.data_structures import StructuralFact
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


# ============================================================
# Helpers
# ============================================================

def _facts(code: str):
    return extract_structural_facts(ast.parse(code))


def _fact_types(code: str) -> set:
    return {f.fact_type for f in _facts(code)}


def _techs(code: str, relations=None):
    facts = _facts(code)
    return {t.technique_id for t in detect_techniques(facts, relations=relations)}


def _ops(code: str, fact_type: str):
    """(variable, operation) pairs for a given operation fact type."""
    key = {
        "queue_dequeue": "queue_variable",
        "stack_operation": "stack_variable",
    }[fact_type]
    return sorted(
        (f.attributes.get(key), f.attributes.get("operation"))
        for f in _facts(code)
        if f.fact_type == fact_type
    )


# ============================================================
# M1: statement-form parity of the dispatch layer
# ============================================================

class TestM1DispatchParity:
    def test_operation_statements_cover_the_assignment_family(self):
        # The dispatch layer must treat Expr + the full assignment family
        # as operation statements — this is the invariant that makes
        # form-enumeration bugs structurally impossible.
        assert set(_OPERATION_STATEMENTS) == {
            ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
        }

    def test_queue_dequeue_identical_across_statement_forms(self):
        code_forms = [
            "def f(q):\n    q.popleft()\n",
            "def f(q):\n    node = q.popleft()\n",
            "def f(q):\n    node: object = q.popleft()\n",
            "def f(q):\n    total = 0\n    total += q.pop(0)\n",
        ]
        baseline = _ops(code_forms[0], "queue_dequeue")
        assert baseline == [("q", "dequeue")]
        for code in code_forms[1:]:
            assert _ops(code, "queue_dequeue") == baseline, code

    def test_tuple_unpack_dequeue_same_operation(self):
        # Tuple-unpack assignment is one statement with several targets;
        # the dequeue operation itself must be recognized exactly once.
        code = "def f(q):\n    r, c, d = q.popleft()\n"
        assert _ops(code, "queue_dequeue") == [("q", "dequeue")]

    def test_augassign_carried_dequeue_recognized(self):
        # The operation is carried in an AugAssign RHS: same dequeue.
        code = "def f(q):\n    total = 0\n    total += q.pop(0)\n"
        assert _ops(code, "queue_dequeue") == [("q", "dequeue")]

    def test_stack_operation_identical_across_statement_forms(self):
        code_forms = [
            "def f(stk):\n    stk.pop()\n",
            "def f(stk):\n    node = stk.pop()\n",
            "def f(stk):\n    total = 0\n    total += stk.pop()\n",
        ]
        baseline = _ops(code_forms[0], "stack_operation")
        assert baseline == [("stk", "pop")]
        for code in code_forms[1:]:
            assert _ops(code, "stack_operation") == baseline, code

    def test_assigned_stack_pop_now_recognized(self):
        # Previously Expr-only: node = stack.pop() was invisible.
        code = "def f():\n    stack = []\n    while stack:\n        node = stack.pop()\n"
        assert ("stack", "pop") in _ops(code, "stack_operation")

    def test_dequeue_discrimination_survives_all_forms(self):
        # pop() / pop(n) are stack pops, never queue dequeues, in ANY form.
        negatives = [
            "def f(s):\n    x = s.pop()\n",
            "def f(s):\n    x = s.pop(3)\n",
            "def f(s):\n    x: object = s.pop()\n",
        ]
        for code in negatives:
            assert _ops(code, "queue_dequeue") == [], code

    def test_annassign_accumulator_recognized(self):
        # total: int = total + 1 was invisible before M1.
        code = (
            "def f(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total: int = total + 1\n"
            "    return total\n"
        )
        types = _fact_types(code)
        assert "accumulator_update" in types
        assert "for_loop_iteration" in types

    def test_multi_target_assign_accumulator(self):
        # a = b = a + 1: the self-referential target must be found via
        # the normalized target iteration (previously targets[0] only).
        code = (
            "def f(n):\n"
            "    a = b = 0\n"
            "    for i in range(n):\n"
            "        a = b = a + 1\n"
            "    return a\n"
        )
        accs = [
            f.attributes.get("variable")
            for f in _facts(code)
            if f.fact_type == "accumulator_update"
        ]
        assert "a" in accs

    def test_no_duplicate_facts_from_unified_dispatch(self):
        # A statement handled by both the Expr path (historically) and the
        # dispatch layer must not produce duplicate facts.
        code = "def f(q):\n    while q:\n        q.popleft()\n"
        facts = _facts(code)
        keys = [(f.fact_type, f.ast_ref) for f in facts]
        assert len(keys) == len(set(keys))

    def test_existing_form_outputs_unchanged(self):
        # Byte-for-byte attribute preservation for the previously
        # supported canonical forms (same type, same attributes).
        bare = _facts("def f(q):\n    q.popleft()\n")[0]
        assert bare.fact_type == "queue_dequeue"
        assert bare.attributes == {"queue_variable": "q", "operation": "dequeue"}

        assigned = [
            f for f in _facts("def f(q):\n    node = q.popleft()\n")
            if f.fact_type == "queue_dequeue"
        ][0]
        assert assigned.attributes == bare.attributes

    def test_plain_and_augmented_accumulators_unchanged(self):
        code = (
            "def f(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total = total + 1\n"
            "    return total\n"
        )
        acc = [f for f in _facts(code) if f.fact_type == "accumulator_update"][0]
        assert acc.attributes["syntax_form"] == "equal_sign"

        code2 = (
            "def f(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total += 1\n"
            "    return total\n"
        )
        acc2 = [f for f in _facts(code2) if f.fact_type == "accumulator_update"][0]
        assert acc2.attributes["syntax_form"] == "augmented"


# ============================================================
# M2: relations layer
# ============================================================

class TestRelationsLayer:
    def test_updated_in_loop_for_and_while(self):
        code = (
            "def f(nums):\n"
            "    total = 0\n"
            "    for i in range(len(nums)):\n"
            "        total += nums[i]\n"
            "    while total > 0:\n"
            "        total -= 1\n"
            "    return total\n"
        )
        r = build_relations(ast.parse(code))
        assert r.updated_in_loop["total"] == {"for", "while"}

    def test_updated_in_loop_covers_all_assignment_forms(self):
        code = (
            "def f(n):\n"
            "    total = 0\n"
            "    other = 0\n"
            "    for i in range(n):\n"
            "        total += 1\n"
            "        total: int = total + 1\n"
            "        other = other + 1\n"
            "        a, b = 1, 2\n"
            "    return total\n"
        )
        r = build_relations(ast.parse(code))
        assert r.updated_in_loop["total"] == {"for"}
        assert r.updated_in_loop["other"] == {"for"}
        assert r.updated_in_loop["a"] == {"for"}
        assert r.updated_in_loop["b"] == {"for"}

    def test_used_as_subscript_index(self):
        code = (
            "def f(nums, i):\n"
            "    x = nums[i - 1]\n"
            "    m = [[0, 0], [0, 0]]\n"
            "    return x, m[i][j] if False else x\n"
        )
        r = build_relations(ast.parse(code))
        assert "i" in r.used_as_subscript_index
        assert "nums" not in r.used_as_subscript_index

    def test_def_use_pairs(self):
        code = (
            "def f(nums):\n"
            "    total = 0\n"
            "    for x in nums:\n"
            "        total += x\n"
            "    return total\n"
        )
        r = build_relations(ast.parse(code))
        # def-use pairs relate a defined variable to the variable(s) whose
        # value is computed from it; bare uses are covered by used_anywhere.
        assert r.def_use_pairs["x"] == {"total"}
        assert "total" in r.used_anywhere

    def test_collection_ops_with_position(self):
        code = (
            "def f(root):\n"
            "    queue = [root]\n"
            "    stack = []\n"
            "    heap = []\n"
            "    node = queue.pop(0)\n"
            "    stack.append(node)\n"
            "    stack.pop()\n"
            "    import heapq\n"
            "    heapq.heappush(heap, node)\n"
            "    heapq.heappop(heap)\n"
            "    from collections import deque\n"
            "    dq = deque()\n"
            "    dq.popleft()\n"
            "    return node\n"
        )
        r = build_relations(ast.parse(code))
        assert r.collection_ops["queue"] == {"pop(0)"}
        assert r.collection_ops["stack"] == {"append", "pop"}
        assert r.collection_ops["heap"] == {"heappush", "heappop"}
        assert r.collection_ops["dq"] == {"popleft"}

    def test_collection_ops_pop_n_distinguished(self):
        code = "def f(lst):\n    lst.pop(2)\n"
        r = build_relations(ast.parse(code))
        assert r.collection_ops["lst"] == {"pop(n)"}

    def test_iterated_in_for(self):
        code = (
            "def f(nums):\n"
            "    total = 0\n"
            "    for x in nums:\n"
            "        total += x\n"
            "    for i in range(3):\n"
            "        total += i\n"
            "    return total\n"
        )
        r = build_relations(ast.parse(code))
        assert r.iterated_in_for == {"nums"}  # range() is not a named collection

    def test_determinism(self):
        code = (
            "def f(nums):\n"
            "    total = 0\n"
            "    for i in range(len(nums)):\n"
            "        total += nums[i]\n"
            "    return total\n"
        )
        a = build_relations(ast.parse(code))
        b = build_relations(ast.parse(code))
        assert a.updated_in_loop == b.updated_in_loop
        assert a.used_as_subscript_index == b.used_as_subscript_index
        assert a.def_use_pairs == b.def_use_pairs
        assert a.collection_ops == b.collection_ops
        assert a.iterated_in_for == b.iterated_in_for


# ============================================================
# M2: sequential_accumulation migration (behavioral equivalence)
# ============================================================

WHILE_ACC = (
    "def f(n):\n"
    "    total = 0\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
)

FOR_ACC = (
    "def f(nums):\n"
    "    total = 0\n"
    "    for x in nums:\n"
    "        total += x\n"
    "    return total\n"
)

FOR_ACC_INDEXED = (
    "def f(nums):\n"
    "    total = 0\n"
    "    for i in range(len(nums)):\n"
    "        total += nums[i]\n"
    "    return total\n"
)

NO_LOOP = "def f(n):\n    total = 0\n    total += n\n    return total\n"
NO_ACCUM = "def f(nums):\n    res = []\n    for x in nums:\n        res.append(x)\n    return res\n"
TRIVIAL_COUNTER = (
    "def f(n):\n"
    "    for i in range(n):\n"
    "        i += 1\n"
    "    return i\n"
)


class TestSequentialAccumulationMigration:
    def test_while_behavior_unchanged_without_relations(self):
        # Original call convention (facts only) keeps firing.
        assert "sequential_accumulation" in _techs(WHILE_ACC)
        assert "sequential_accumulation" not in _techs(NO_LOOP)
        assert "sequential_accumulation" not in _techs(NO_ACCUM)

    def test_while_behavior_unchanged_with_relations(self):
        r = build_relations(ast.parse(WHILE_ACC))
        assert "sequential_accumulation" in _techs(WHILE_ACC, relations=r)

    def test_for_behavior_unchanged_n3_preserved(self):
        r = build_relations(ast.parse(FOR_ACC))
        assert "sequential_accumulation" in _techs(FOR_ACC, relations=r)
        r2 = build_relations(ast.parse(FOR_ACC_INDEXED))
        assert "sequential_accumulation" in _techs(FOR_ACC_INDEXED, relations=r2)

    def test_trivial_counter_behavioral_parity(self):
        # A for-loop counter (i += 1) firing is pre-existing pinned behavior
        # (Batch 3 asserts it deliberately: the loop variable is itself
        # self-referentially updated). The migration must preserve exactly
        # that — parity across HEAD-style fallback and the relations path,
        # with identical supporting facts.
        facts = _facts(TRIVIAL_COUNTER)
        without = detect_techniques(facts)
        r = build_relations(ast.parse(TRIVIAL_COUNTER))
        with_rel = detect_techniques(facts, relations=r)
        ids_without = {t.technique_id for t in without}
        ids_with = {t.technique_id for t in with_rel}
        assert ids_without == ids_with
        seq_without = [t for t in without if t.technique_id == "sequential_accumulation"]
        seq_with = [t for t in with_rel if t.technique_id == "sequential_accumulation"]
        assert [t.supporting_fact_ids for t in seq_without] == [
            t.supporting_fact_ids for t in seq_with
        ]

    def test_relations_path_equals_fallback_path(self):
        # For every previously supported input, the migrated detector must
        # produce the identical technique (same supporting facts) whether
        # relations are supplied or not — that is the acceptance criterion
        # "behaviorally equivalent".
        codes = [WHILE_ACC, FOR_ACC, FOR_ACC_INDEXED]
        for code in codes:
            facts = _facts(code)
            without = detect_techniques(facts)
            r = build_relations(ast.parse(code))
            with_rel = detect_techniques(facts, relations=r)
            ids_without = {t.technique_id for t in without}
            ids_with = {t.technique_id for t in with_rel}
            assert ids_without == ids_with, code
            seq_without = [t for t in without if t.technique_id == "sequential_accumulation"]
            seq_with = [t for t in with_rel if t.technique_id == "sequential_accumulation"]
            assert [t.supporting_fact_ids for t in seq_without] == [
                t.supporting_fact_ids for t in seq_with
            ], code
            assert [t.presence_confidence for t in seq_without] == [
                t.presence_confidence for t in seq_with
            ], code

    def test_relations_oracle_cannot_create_new_detections(self):
        # Even with an adversarially permissive relations bundle, no
        # detection may fire that the fact-join gate rejects.
        class PermissiveRelations:
            updated_in_loop = {"total": {"for", "while"}, "anything": {"for", "while"}}

        facts = _facts(NO_LOOP)  # no loop facts -> detector must return None
        assert detect_techniques(facts, relations=PermissiveRelations()) == [] or (
            "sequential_accumulation"
            not in {t.technique_id for t in detect_techniques(facts, relations=PermissiveRelations())}
        )

        # NO_ACCUM has a for-loop fact but no accumulator_update fact.
        facts2 = _facts(NO_ACCUM)
        assert "sequential_accumulation" not in {
            t.technique_id for t in detect_techniques(facts2, relations=PermissiveRelations())
        }

    def test_relations_without_membership_falls_back(self):
        # Relations that know nothing must not break detection: the
        # fallback path keeps previously supported outputs.
        class EmptyRelations:
            updated_in_loop = {}

        assert "sequential_accumulation" in _techs(WHILE_ACC, relations=EmptyRelations())
        assert "sequential_accumulation" in _techs(FOR_ACC, relations=EmptyRelations())

    def test_annassign_accumulator_now_reaches_technique(self):
        # M1 x M2 integration: the newly extracted AnnAssign accumulator
        # form flows through to the technique on the relations path.
        code = (
            "def f(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total: int = total + 1\n"
            "    return total\n"
        )
        r = build_relations(ast.parse(code))
        assert "sequential_accumulation" in _techs(code, relations=r)


# ============================================================
# Runner integration
# ============================================================

class TestRunnerIntegration:
    def test_run_shadow_analysis_exports_relations_version(self):
        result = run_shadow_analysis(FOR_ACC)
        assert result is not None
        assert "relations_version" in result
        assert result["technique_evidence"], "expected technique evidence"

    def test_runner_outcome_unchanged_for_accumulation_code(self):
        result = run_shadow_analysis(FOR_ACC)
        assert result["match_outcome"]["outcome"] in {"CONFIRMED", "UNRESOLVED", "CONTRADICTED"}

    def test_graceful_degradation_preserved(self):
        # Runner-level failure isolation must survive the new wiring.
        assert run_shadow_analysis("def broken(:\n    pass\n") is None


# ============================================================
# Hand-built fact fallback (test-suite compatibility contract)
# ============================================================

class TestFallbackContract:
    def test_hand_built_facts_still_detect_via_fallback(self):
        # Facts without ast_ref/relations (as built by older tests) must
        # keep detecting through the original fact-join path.
        facts = [
            StructuralFact(fact_type="while_loop_comparison",
                           attributes={"compared_variables": ["i"],
                                       "modified_variables": ["total"]}),
            StructuralFact(fact_type="accumulator_update",
                           attributes={"variable": "total"}),
        ]
        techs = detect_techniques(facts)
        assert "sequential_accumulation" in {t.technique_id for t in techs}

        # With an empty relations bundle the fallback must also fire.
        class EmptyRelations:
            updated_in_loop = {}

        techs2 = detect_techniques(facts, relations=EmptyRelations())
        assert "sequential_accumulation" in {t.technique_id for t in techs2}
