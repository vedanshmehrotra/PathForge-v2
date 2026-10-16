"""POC tests (new file; no existing test is modified).

Covers the POC's contractual guarantees:
  * deterministic repeated execution, byte-identical artifacts
  * original code_text is never mutated
  * no LLM / network / database use
  * ingestion metadata + provenance + source-type checks
  * duplicate-raw-hash detection actually works
  * families partition the corpus; split has no overlap
  * reviewer artifact hides analyzer detections; nothing is auto-approved
  * derived groups come only from the derivation split and can only narrow the
    independent editorial label
"""
import hashlib
import json
import os
import re

import pytest

from experiments.code_analysis_evaluation.gt_poc import ingest, label, normalize, group, validate
from experiments.code_analysis_evaluation.gt_poc import run_poc
from experiments.code_analysis_evaluation.gt_poc.problem_metadata import (
    POC_PROBLEM_IDS,
    TARGET_CORPUS_SIZE,
    ALLOWED_SOURCE_TYPES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
POC_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.abspath(os.path.join(POC_DIR, "..", "..", ".."))

ARTIFACT_NAMES = [
    "reference_solutions.json",
    "normalized_solutions.json",
    "families.json",
    "review_sheet.json",
    "review_sheet.md",
    "label_comparison.json",
    "validation.json",
    "run_manifest.json",
]


@pytest.fixture(scope="module")
def artifacts():
    return run_poc.run_all()


def _file_bytes(name):
    with open(os.path.join(POC_DIR, name), "rb") as fh:
        return fh.read()


# ---------------------------------------------------------------- corpus shape

def test_corpus_shape(artifacts):
    ing = artifacts["reference"]["ingestion"]
    assert ing["passed"] is True
    assert ing["issues"] == []
    assert ing["solution_count"] == TARGET_CORPUS_SIZE == 40
    assert ing["problem_count"] == len(POC_PROBLEM_IDS) == 8
    assert set(ing["per_problem_counts"].values()) == {5}


def test_metadata_provenance_and_source_type(artifacts):
    for s in artifacts["reference"]["solutions"]:
        assert s["solution_id"]
        assert s["problem_id"] in POC_PROBLEM_IDS
        assert s["source_type"] in ALLOWED_SOURCE_TYPES
        assert s["source_ref"]
        assert s["language"] == "python"
        assert isinstance(s["provenance"], dict) and s["provenance"]
        assert s["raw_hash"] == hashlib.sha256(s["code_text"].encode("utf-8")).hexdigest()


def test_code_text_preserved_exactly(artifacts):
    """Every ingested code_text must equal a source snippet byte-for-byte."""
    from experiments.code_analysis_evaluation.gt_poc.corpus_authored import AUTHORED_SOLUTIONS

    authored = {code for per_problem in AUTHORED_SOLUTIONS.values() for _, code in per_problem}
    with open(os.path.join(POC_DIR, "corpus_db_snapshot.json"), "r", encoding="utf-8") as fh:
        snapshot = {row["code_text"] for row in json.load(fh)["solutions"]}

    known = authored | snapshot
    assert len(known) == 40, "expected 40 distinct source snippets"
    for s in artifacts["reference"]["solutions"]:
        assert s["code_text"] in known


def test_normalization_is_comparison_only(artifacts):
    """norm_hash is a comparison key; the stored source text must be untouched."""
    from experiments.code_analysis_evaluation.gt_poc.core import canonicalized_source

    by_id = {s["solution_id"]: s for s in artifacts["reference"]["solutions"]}
    rows = {r["solution_id"]: r for r in artifacts["normalized"]["solutions"]}
    for sid, ref in by_id.items():
        code = ref["code_text"]
        assert rows[sid]["raw_hash"] == hashlib.sha256(code.encode("utf-8")).hexdigest()
        # independently recompute the name-normalized key; deterministic
        assert rows[sid]["norm_hash"] == hashlib.sha256(
            canonicalized_source(code).encode("utf-8")
        ).hexdigest()
        assert canonicalized_source(code) == canonicalized_source(code)
        # the stored text is byte-identical to the original
        assert ref["code_text"] == code


def test_duplicate_detection_works():
    """Two byte-identical solutions for one problem must be flagged as D1."""
    code = "def f(a):\n    return a\n"
    corpus = {
        "solutions": [
            {"solution_id": "S0001", "problem_id": 1, "source_type": "authored",
             "source_ref": "x", "language": "python", "code_text": code,
             "raw_hash": hashlib.sha256(code.encode()).hexdigest(), "provenance": {"k": "v"}},
            {"solution_id": "S0002", "problem_id": 1, "source_type": "authored",
             "source_ref": "y", "language": "python", "code_text": code,
             "raw_hash": hashlib.sha256(code.encode()).hexdigest(), "provenance": {"k": "v"}},
        ]
    }
    result = ingest.validate_corpus(corpus)
    assert result["passed"] is True
    assert len(result["duplicate_raw_hashes"]) == 1
    dup = result["duplicate_raw_hashes"][0]
    assert dup["solution_id"] == "S0002" and dup["duplicate_of"] == "S0001"


def test_dedup_ladder_levels_are_valid(artifacts):
    levels = {"D1", "D2", "D3", "D4"}
    rows = artifacts["normalized"]["solutions"]
    assert len(rows) == 40
    for r in rows:
        assert r["dedup_level"] in levels
        assert r["dedup_level_name"]
        assert r["reason"]
        if r["dedup_level"] == "D4":
            assert r["related_to"] is None
        else:
            assert r["related_to"] is not None


# ------------------------------------------------------------------- grouping

def test_families_partition_the_corpus(artifacts):
    families = artifacts["families"]["families"]
    members = [m for f in families for m in f["members"]]
    assert sorted(members) == sorted(s["solution_id"] for s in artifacts["reference"]["solutions"])
    assert len(members) == len(set(members)), "a solution appears in more than one family"
    for f in families:
        assert f["member_count"] == len(f["members"])
        assert f["provisional_threshold"] == artifacts["families"]["provisional_skeleton_threshold"]
        assert f["canonical_solution_id"] in f["members"]


def test_grouping_is_deterministic_and_threshold_not_per_problem(artifacts):
    thresholds = {f["provisional_threshold"] for f in artifacts["families"]["families"]}
    assert len(thresholds) == 1, f"threshold must not vary per problem: {thresholds}"


# ------------------------------------------------------------------ labelling

def test_reviewer_artifact_hides_analyzer_detections(artifacts):
    review = artifacts["review"]
    assert review["analyzer_detection_visible_to_reviewer"] is False
    blob = json.dumps(review)
    for forbidden in ("technique_signature", "strategy_signature", "signature_class"):
        assert forbidden not in blob, f"reviewer artifact leaks {forbidden}"
    # labels may only come from the curated editorial source
    for e in review["entries"]:
        p = e["proposed_label"]
        assert p["label_source"] in (None, "curated_problems_pattern")
        assert not e["approved"]
        assert e["review_state"] in ("PENDING_REVIEW", "NO_INDEPENDENT_LABEL")


def test_nothing_is_auto_approved(artifacts):
    assert artifacts["review"]["auto_approval"] is False
    assert artifacts["review"]["totals"]["pending_review"] + artifacts["review"]["totals"][
        "no_independent_label"] == artifacts["review"]["totals"]["families"]
    assert all(not e["approved"] for e in artifacts["review"]["entries"])


def test_markdown_review_sheet_has_no_analyzer_sections(artifacts):
    md = artifacts["review"]
    text = label.render_markdown(md)
    assert "PENDING_REVIEW" in text or "NO_INDEPENDENT_LABEL" in text
    assert "technique_signature" not in text


# ----------------------------------------------------------------- validation

def test_split_has_no_overlap_and_covers_everything(artifacts):
    split = artifacts["validation"]["split"]
    assert split["overlap"] == []
    all_split = sorted(split["derivation"] + split["held_out"])
    assert all_split == sorted(s["solution_id"] for s in artifacts["reference"]["solutions"])
    for entry in split["per_family"]:
        assert not (set(entry["derivation"]) & set(entry["held_out"]))


def test_derived_groups_use_only_derivation_members(artifacts):
    """A derived group may never be justified by a held-out solution."""
    v = artifacts["validation"]
    held_out = set(v["split"]["held_out"])
    for d in v["derivation_decisions"]:
        assert not (set(d["derivation_members"]) & held_out)


def test_derived_required_can_only_narrow_the_editorial_label(artifacts):
    """Independence rule: the analyzer cannot invent a requirement."""
    v = artifacts["validation"]
    for d in v["derivation_decisions"]:
        if not d.get("derived"):
            continue
        assert d["derived_required"], "a derived group must have a non-empty required set"
        assert set(d["derived_required"]) <= set(d["label_required"])
        assert set(d["derived_required"]) <= set(d["member_concepts_intersection"])


def test_validation_reports_metrics_and_failures_honestly(artifacts):
    v = artifacts["validation"]
    m = v["metrics"]
    for key in (
        "family_coverage", "positive_confirm_rate", "discrimination_FP_raw",
        "discrimination_FP_disjoint", "label_agreement", "unresolved_rate",
        "group_satisfiability",
    ):
        assert key in m
    assert v["rules_unchanged_on_failure"] is True
    assert v["passed"] == (len(v["failed_criteria"]) == 0)


# ------------------------------------------------------------------ boundaries

def test_no_llm_network_or_db_use(artifacts):
    """The pipeline must not call the LLM, the network, or the database."""
    import pathforge.db.db as db_module
    import pathforge.llm.openrouter_client as llm
    import pathforge.services.ground_truth_builder as gtb

    def _boom(*a, **k):
        raise AssertionError("POC must not reach the LLM / network / database")

    saved = (llm.call_llm, getattr(gtb, "call_llm", None), db_module.get_connection)
    llm.call_llm = _boom
    gtb.call_llm = _boom
    db_module.get_connection = _boom
    try:
        result = run_poc.run_all()
        assert result["reference"]["ingestion"]["solution_count"] == 40
    finally:
        llm.call_llm, gtb.call_llm, db_module.get_connection = (
            saved[0],
            saved[1] if saved[1] is not None else gtb.call_llm,
            saved[2],
        )


def test_poc_sources_contain_no_network_or_db_imports():
    forbidden = re.compile(
        r"\b(openrouter|httpx|requests|urllib|socket|psycopg2|get_connection)\b"
    )
    for name in os.listdir(POC_DIR):
        if not name.endswith(".py"):
            continue
        path = os.path.join(POC_DIR, name)
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        assert not forbidden.search(source), f"{name} contains a forbidden dependency"


# ---------------------------------------------------------------- determinism

def test_repeated_execution_is_byte_identical(artifacts):
    before = {name: _file_bytes(name) for name in ARTIFACT_NAMES}
    again = run_poc.run_all()
    after = {name: _file_bytes(name) for name in ARTIFACT_NAMES}
    for name in ARTIFACT_NAMES:
        assert before[name] == after[name], f"{name} is not deterministic"
    assert again["manifest"]["artifacts"] == artifacts["manifest"]["artifacts"]
