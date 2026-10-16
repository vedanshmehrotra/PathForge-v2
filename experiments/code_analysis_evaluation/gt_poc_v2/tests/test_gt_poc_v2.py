"""V2 POC tests (new file; no existing test is modified).

Covers the V2 POC's contractual guarantees:
  * corpus shape (12 x 8 = 96) with deliberate D1 / D2 / ZERO_EVIDENCE content
  * deterministic repeated execution, byte-identical artifacts
  * original code_text is never mutated
  * no LLM / network / database use
  * S1 concept tiers, S3 profile determinism
  * S2/S4 grouping contract (PEC partition, no skeleton split trigger)
  * never-narrow derivation + refusal states + specificity floor
  * zero-evidence first-class rules
  * canonical negative-control rule + exclusion accounting
  * reviewer artifact hides analyzer detections; nothing auto-approved
  * family-first split rules + held-out population gate
"""
import hashlib
import json
import os
import re

import pytest

from experiments.code_analysis_evaluation.gt_poc_v2 import (
    controls, derive, grouping, ingest, labeling, normalize, run_poc, validate,
)
from experiments.code_analysis_evaluation.gt_poc_v2.core import (
    concept_tier, compute_profile, profile_tuple,
)
from experiments.code_analysis_evaluation.gt_poc_v2.problem_metadata import (
    ALLOWED_SOURCE_TYPES,
    POC_PROBLEM_IDS,
    SUPPORT_TECHNIQUES,
    TARGET_CORPUS_SIZE,
)
from experiments.code_analysis_evaluation.gt_poc_v2.labeling import (
    STATE_LABEL_GENERIC, STATE_LABEL_MULTI_OVERLAP, STATE_LABEL_PARTIAL,
    STATE_LABEL_UNEXPRESSIBLE, divergence_state, screen_family,
)

HERE = os.path.dirname(os.path.abspath(__file__))
POC_DIR = os.path.dirname(HERE)
ARTIFACT_NAMES = [
    "reference_solutions.json", "normalized_solutions.json", "families.json",
    "family_labels.json", "review_sheet.json", "review_sheet.md",
    "label_comparison.json", "derivation_outcomes.json",
    "negative_controls.json", "validation.json", "run_manifest.json",
]


@pytest.fixture(scope="module")
def artifacts():
    return run_poc.run_all()


def _bytes(name):
    with open(os.path.join(POC_DIR, name), "rb") as fh:
        return fh.read()


# ------------------------------------------------------------------ corpus
def test_corpus_shape(artifacts):
    ing = artifacts["reference"]["ingestion"]
    assert ing["passed"] is True and ing["issues"] == []
    assert ing["solution_count"] == TARGET_CORPUS_SIZE == 96
    assert ing["problem_count"] == len(POC_PROBLEM_IDS) == 12
    assert set(ing["per_problem_counts"].values()) == {8}


def test_metadata_provenance_source_type_quality_evidence(artifacts):
    for s in artifacts["reference"]["solutions"]:
        assert s["solution_id"] and s["problem_id"] in POC_PROBLEM_IDS
        assert s["source_type"] in ALLOWED_SOURCE_TYPES
        assert s["source_ref"] and s["language"] == "python"
        assert isinstance(s["provenance"], dict) and s["provenance"]
        assert s["quality_state"] in {"accepted", "reported_failing", "unverified"}
        assert s["evidence_state"] in {"has_evidence", "zero_evidence", "unparseable"}
        assert s["raw_hash"] == hashlib.sha256(s["code_text"].encode("utf-8")).hexdigest()


def test_code_text_preserved_exactly(artifacts):
    from experiments.code_analysis_evaluation.gt_poc_v2.corpus_authored import AUTHORED_SOLUTIONS
    authored = {c for per in AUTHORED_SOLUTIONS.values() for _, c in per}
    with open(os.path.join(os.path.dirname(POC_DIR), "gt_poc", "corpus_db_snapshot.json"),
              encoding="utf-8") as fh:
        snapshot = {row["code_text"] for row in json.load(fh)["solutions"]}
    known = authored | snapshot
    for s in artifacts["reference"]["solutions"]:
        assert s["code_text"] in known


def test_D1_duplicates_present_and_classified(artifacts):
    ing = artifacts["reference"]["ingestion"]
    assert len(ing["duplicate_raw_hash_pairs"]) >= 3
    assert len(ing["problems_with_D1_duplicates"]) >= 3
    d1 = artifacts["normalized"]["dedup_ladder_summary"]["D1_classification"]
    assert d1["total"] >= 3
    assert d1["correct"] == d1["total"]


def test_D2_variants_present_and_classified(artifacts):
    d2 = artifacts["normalized"]["dedup_ladder_summary"]["D2_classification"]
    assert d2["total"] >= 3
    assert d2["correct"] == d2["total"]
    # a D2 variant must differ in raw text but share the name-normalized AST
    rows = {r["solution_id"]: r for r in artifacts["normalized"]["solutions"]}
    ref = {s["solution_id"]: s for s in artifacts["reference"]["solutions"]}
    checked = 0
    for r in artifacts["normalized"]["solutions"]:
        if r["dedup_level"] == "D2":
            canon = rows[r["related_to"]]
            assert r["raw_hash"] != canon["raw_hash"]
            assert r["norm_hash"] == canon["norm_hash"]
            checked += 1
    assert checked >= 3


def test_zero_evidence_present(artifacts):
    ing = artifacts["reference"]["ingestion"]
    assert ing["evidence_distribution"].get("zero_evidence", 0) >= 3


# ------------------------------------------------------------------ S1/S3
def test_concept_tiers():
    for c in ("sliding_window", "binary_search", "dp_bottom_up", "union_find",
              "dfs_backtracking", "hash_lookup", "frequency_counting",
              "linked_list_traversal", "carry_propagation", "iterative_table_filling"):
        assert concept_tier(c) == "PEC"
    for c in SUPPORT_TECHNIQUES:
        assert concept_tier(c) == "SUPPORT"
    # unknown / new vocabulary defaults to SUPPORT (safe default)
    assert concept_tier("brand_new_concept_xyz") == "SUPPORT"


def test_profile_is_deterministic_and_bounded():
    code = "def f(a):\n    s = 0\n    for x in a:\n        s += x\n    return s\n"
    p1, p2 = compute_profile(code), compute_profile(code)
    assert p1 == p2
    assert profile_tuple(p1) == ("none", "flat", "none", "none", "container")
    nested = "def f(a):\n    for i in range(len(a)):\n        for j in range(len(a)):\n            pass\n"
    assert compute_profile(nested)["loop_shape"] == "nested"


def test_iterates_collection_treats_range_len_as_container():
    a = "def f(x):\n    for i in range(len(x)):\n        pass\n"
    b = "def f(y):\n    for i, v in enumerate(y):\n        pass\n"
    assert compute_profile(a)["iterates_collection"] == "container"
    assert compute_profile(b)["iterates_collection"] == "container"


# ------------------------------------------------------------------ grouping
def test_families_partition_the_corpus(artifacts):
    families = artifacts["families"]["families"]
    members = [m for f in families for m in f["members"]]
    assert len(members) == len(set(members)) == 96
    for f in families:
        assert f["member_count"] == len(f["members"])
        assert f["canonical_solution_id"] in f["members"]
        assert set(f["pec_set"]) & set(f["support_set"]) == set()


def test_identical_PEC_solutions_are_one_family(artifacts):
    """V1 over-split LC 1's three hash_lookup solutions; V2 must keep one family."""
    rows = {r["solution_id"]: r for r in artifacts["normalized"]["solutions"]}
    hash_rows = [r for r in artifacts["normalized"]["solutions"]
                 if r["problem_id"] == 1 and r["pec_set"] == ["hash_lookup"]]
    assert len(hash_rows) >= 3
    keys = {rows[r["solution_id"]]["family_key"] for r in hash_rows}
    assert len(keys) == 1, f"identical PEC solutions split across families: {keys}"


def test_skeleton_cannot_create_a_boundary(artifacts):
    """A D1 duplicate and a D2 syntax variant never split into another family."""
    rows = {r["solution_id"]: r for r in artifacts["normalized"]["solutions"]}
    for r in artifacts["normalized"]["solutions"]:
        if r["dedup_level"] in ("D1", "D2"):
            assert rows[r["related_to"]]["family_key"] == r["family_key"]


# ------------------------------------------------------------------ derivation
def test_never_narrow(artifacts):
    d = artifacts["derivation"]
    for o in d["outcomes"]:
        if not o["activated"]:
            continue
        assert set(o["required"]) == set(o["label_required"]), "required must equal L"
        assert set(o["required"]) <= set(o["observed_intersection"])
        assert o["narrowing"] is False
    assert d["totals"]["narrowing_violations"] == 0


def test_partial_and_disjoint_labels_refuse_not_narrow():
    # partial: L = {a, b}, O = {a, c} -> exactly one label concept covered
    assert divergence_state(["a", "b"], ["a", "c"], lambda c: "PEC", False) == STATE_LABEL_PARTIAL
    # multi overlap: L = {a, b, c}, O = {a, b} -> several concepts partially cover
    assert divergence_state(["a", "b", "c"], ["a", "b"], lambda c: "PEC", False) == STATE_LABEL_MULTI_OVERLAP
    # unexpressible: disjoint
    assert divergence_state(["a"], ["b"], lambda c: "PEC", False) == STATE_LABEL_UNEXPRESSIBLE
    # L subset of O is the only activatable state (given a PEC in L)
    assert divergence_state(["a", "b"], ["a", "b", "c"], lambda c: "PEC", False) == "LABEL_OK"


def test_specificity_floor_is_support_only_generic():
    assert divergence_state(["sequential_accumulation"], ["sequential_accumulation"],
                            lambda c: "SUPPORT", False) == STATE_LABEL_GENERIC
    assert divergence_state(["hash_lookup"], ["hash_lookup"],
                            lambda c: "PEC", False) == "LABEL_OK"


def test_screen_rejects_partial_problem_label():
    L = ["sequential_accumulation", "sliding_window"]
    # union intersects but not every member observes every required concept
    s = screen_family(L, observed_union=["sequential_accumulation"],
                      observed_intersection=["sequential_accumulation"], family_count_for_problem=3)
    assert s["passed"] is False and s["reason"] == "partial_problem_label"
    # all required observed by every member -> pass
    s2 = screen_family(L, L, L, family_count_for_problem=3)
    assert s2["passed"] is True


def test_generic_families_never_activate(artifacts):
    d = artifacts["derivation"]
    for o in d["outcomes"]:
        if o["divergence_state"] == STATE_LABEL_GENERIC:
            assert o["activated"] is False


def test_partial_refusal_produces_no_group():
    """Synthetic: a LABEL_PARTIAL family must not yield an activated group."""
    label = {
        "family_key": "lc9_fam1", "problem_id": 9,
        "proposed_label": {"required": ["a", "b"], "optional": [], "excluded": [],
                           "required_expected": ["a", "b"], "label_source": "x"},
        "approval_state": "PENDING_REVIEW", "divergence_state": STATE_LABEL_PARTIAL,
    }
    fam = {"family_key": "lc9_fam1", "problem_id": 9, "members": ["S1"],
           "zero_evidence": False, "pec_set": ["a"], "support_set": []}
    rows = {"S1": {"concepts": ["a"], "concept_tiers": {"a": "PEC"}}}
    out = derive.derive({"solutions": [{"solution_id": "S1", **rows["S1"]}]},
                        {"families": [fam]}, {"entries": [label]})
    assert out["totals"]["activated_groups"] == 0
    assert out["totals"]["narrowing_violations"] == 0


# ------------------------------------------------------------------ zero evidence
def test_zero_evidence_rules(artifacts):
    m = artifacts["validation"]["metrics"]
    assert m["zero_evidence_solutions"] >= 3
    assert m["zero_evidence_confirmed"] == 0
    assert m["zero_evidence_labeled"] == 0
    assert m["zero_evidence_controls"] == 0
    # a zero-evidence family can never activate a group
    for o in artifacts["derivation"]["outcomes"]:
        if o["divergence_state"] == "ZERO_EVIDENCE":
            assert o["activated"] is False


# ------------------------------------------------------------------ controls
def test_control_exhaustive_and_exclusions_counted(artifacts):
    c = artifacts["controls"]
    assert c["totals"]["eligible_pairs"] > 0
    assert c["excluded_by_rule"]["same_problem"] > 0
    assert c["excluded_by_rule"]["zero_evidence"] > 0
    for g in c["per_group"]:
        assert g["eligible_controls"] == g["tested_controls"]
        assert g["failures"] <= g["eligible_controls"]
        # rule 3 removes same-family reuse from the denominator
        assert g["eligible_controls"] <= g["without_rule3_eligible"]


# ------------------------------------------------------------------ labeling / blinding
def test_review_artifact_hides_analyzer_detections(artifacts):
    labels = artifacts["labels"]
    assert labels["analyzer_detection_visible_to_reviewer"] is False
    blob = json.dumps(labels)
    for forbidden in ("technique_signature", "strategy_signature", "pec_set",
                      "structural_profile", "analyzer_pec_set"):
        assert forbidden not in blob, f"reviewer artifact leaks {forbidden}"
    for e in labels["entries"]:
        assert e["proposed_label"]["label_source"] in (
            None, "curated_problems_pattern", "authored_family_proposal")


def test_nothing_is_auto_approved(artifacts):
    labels = artifacts["labels"]
    assert labels["auto_approval"] is False
    assert labels["totals"]["approved"] == 0
    assert all(not e["approved"] and e["approval_state"] == "PENDING_REVIEW"
               for e in labels["entries"])


def test_label_comparison_carries_analyzer_view(artifacts):
    cmp = artifacts["comparison"]
    assert any(e["analyzer_pec_set"] for e in cmp["entries"])


# ------------------------------------------------------------------ split / validation
def test_family_first_split_rules(artifacts):
    split = artifacts["validation"]["split"]
    assert split["overlap"] == []
    all_split = sorted(split["derivation"] + split["held_out"])
    assert all_split == sorted(s["solution_id"] for s in artifacts["reference"]["solutions"])
    for f in split["per_family"]:
        assert not (set(f["derivation"]) & set(f["held_out"]))
        if f["n"] == 1:
            assert f["state"] == "VALIDATION_LIMITED" and f["held_out"] == []
        elif f["n"] == 2:
            assert len(f["derivation"]) == 1 and len(f["held_out"]) == 1
        else:
            assert len(f["derivation"]) >= 1


def test_held_out_population_gate(artifacts):
    m = artifacts["validation"]["metrics"]
    assert m["held_out_population"] == 52
    assert m["held_out_population_gate"] == 36
    assert m["held_out_population_gate_met"] is True
    assert artifacts["validation"]["overall_state"] != "INSUFFICIENT_VALIDATION"


def test_validation_metrics_and_honest_failures(artifacts):
    v = artifacts["validation"]
    for key in ("family_coverage", "positive_confirm_rate", "discrimination_FP",
                "group_satisfiability", "narrowing_violations", "activation_rate",
                "divergence_distribution"):
        assert key in v["metrics"]
    assert v["rules_unchanged_on_failure"] is True
    # structural criteria all pass; only the human-approval gate fails (PA1)
    assert v["failed_criteria"] == ["approved_family_labels"]
    assert v["overall_state"] == "VALIDATION_FAILED"


def test_structural_acceptance_criteria_met(artifacts):
    v = artifacts["validation"]
    for c in v["acceptance_criteria"]:
        if c["criterion"] == "approved_family_labels":
            assert c["met"] is False
            continue
        assert c["met"] is True, f"{c['criterion']} not met: {c}"


# ------------------------------------------------------------------ boundaries
def test_no_llm_network_or_db_use():
    import pathforge.db.db as db_module
    import pathforge.llm.openrouter_client as llm
    import pathforge.services.ground_truth_builder as gtb

    def _boom(*a, **k):
        raise AssertionError("POC must not reach the LLM / network / database")

    saved = (llm.call_llm, getattr(gtb, "call_llm", None), db_module.get_connection)
    llm.call_llm = _boom
    if saved[1] is not None:
        gtb.call_llm = _boom
    db_module.get_connection = _boom
    try:
        result = run_poc.run_all()
        assert result["reference"]["ingestion"]["solution_count"] == 96
    finally:
        llm.call_llm = saved[0]
        if saved[1] is not None:
            gtb.call_llm = saved[1]
        db_module.get_connection = saved[2]


def test_poc_sources_contain_no_network_or_db_imports():
    forbidden = re.compile(r"\b(openrouter|httpx|requests|urllib|socket|psycopg2|get_connection)\b")
    for name in os.listdir(POC_DIR):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(POC_DIR, name), encoding="utf-8") as fh:
            assert not forbidden.search(fh.read()), f"{name} contains a forbidden dependency"


# ------------------------------------------------------------------ determinism
def test_repeated_execution_is_byte_identical(artifacts):
    before = {n: _bytes(n) for n in ARTIFACT_NAMES}
    again = run_poc.run_all()
    after = {n: _bytes(n) for n in ARTIFACT_NAMES}
    for n in ARTIFACT_NAMES:
        assert before[n] == after[n], f"{n} is not deterministic"
    assert again["manifest"]["artifacts"] == artifacts["manifest"]["artifacts"]
