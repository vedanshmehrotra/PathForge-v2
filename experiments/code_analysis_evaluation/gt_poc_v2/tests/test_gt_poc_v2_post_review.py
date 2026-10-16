"""Post-human-review V2 POC tests (new file; no existing test is modified).

Covers the contract introduced by consuming a real human review round:

  * the reviewer transcript is complete, bijective with the family set, and
    mechanically consistent with the raw reviewer artifacts (per-family
    decisions, labels, and the summary tally)
  * a corrected label is a human-approved label, a rejection never activates,
    and no corrected label is added to the runtime vocabulary
  * an unregistered human label term resolves to refusal (LABEL_UNEXPRESSIBLE)
    or ZERO_EVIDENCE — never to an activated group
  * the specificity floor still refuses SUPPORT-only human labels
  * the never-narrow rule holds for human labels (LABEL_PARTIAL refuses)
  * the pre-review artifacts at the package root are not rewritten
  * deterministic repeated execution; no LLM / network / database
"""
import hashlib
import json
import os
import re

import pytest

from experiments.code_analysis_evaluation.gt_poc_v2 import (
    human_review, run_poc, run_post_review,
)
from experiments.code_analysis_evaluation.gt_poc_v2.labeling import (
    STATE_LABEL_GENERIC, STATE_LABEL_OK, STATE_LABEL_PARTIAL,
    STATE_LABEL_UNEXPRESSIBLE, STATE_ZERO_EVIDENCE,
)
from experiments.code_analysis_evaluation.gt_poc_v2.problem_metadata import (
    PEC_CONCEPTS, SUPPORT_CONCEPTS,
)

HERE = os.path.dirname(os.path.abspath(__file__))
POC_DIR = os.path.dirname(HERE)
OUT = os.path.join(POC_DIR, "post_review")
PRE_REVIEW_ARTIFACTS = [
    "reference_solutions.json", "normalized_solutions.json", "families.json",
    "family_labels.json", "review_sheet.json", "review_sheet.md",
    "label_comparison.json", "derivation_outcomes.json",
    "negative_controls.json", "validation.json", "run_manifest.json",
]
POST_REVIEW_ARTIFACTS = [
    "reference_solutions.json", "normalized_solutions.json", "families.json",
    "family_labels_post_review.json", "human_review_audit.json",
    "human_review_verification.json", "label_comparison.json",
    "derivation_outcomes.json", "negative_controls.json", "validation.json",
    "before_after.json", "vocabulary_gaps.json", "run_manifest.json",
]
NON_ACTIVATABLE_STATES = {
    STATE_LABEL_GENERIC, STATE_LABEL_UNEXPRESSIBLE,
    STATE_LABEL_PARTIAL, STATE_ZERO_EVIDENCE,
}


@pytest.fixture(scope="module")
def result():
    return run_post_review.run_all(write=True)


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


# ------------------------------------------------------------------ transcript
def test_transcript_verification_passes(result):
    v = result["human_review"]["verification"]
    assert v["passed"] is True, v["failed_checks"]
    assert v["failed_checks"] == []


def test_transcript_is_complete_and_bijective(result):
    t = result["human_review"]["transcript"]
    decisions = t["decisions"]
    fam_keys = {f["family_key"] for f in result["families"]["families"]}
    assert len(decisions) == len(fam_keys) == 37
    assert {d["family_key"] for d in decisions} == fam_keys
    assert t["summary"] == {"reviewed_families": 37, "approved": 16,
                            "corrected_label": 20, "rejected": 1}
    tally = {}
    for d in decisions:
        tally[d["human_decision"]] = tally.get(d["human_decision"], 0) + 1
    assert tally == {"APPROVED": 16, "CORRECTED_LABEL": 20, "REJECTED": 1}


def test_every_decision_is_auditable(result):
    for d in result["human_review"]["transcript"]["decisions"]:
        assert d["reviewer_reason"].strip()
        assert d["source_ref"].strip()
        assert d["review_status"] == "RECORDED"
        if d["human_decision"] != "REJECTED":
            assert d["human_label_terms"]


def test_transcript_matches_raw_reviewer_artifact_per_family(result):
    """The per-family decisions parsed from the reviewer sheet must agree."""
    v = result["human_review"]["verification"]
    names = {c["check"]: c for c in v["checks"]}
    assert names["extraction_decisions_match"]["passed"] is True
    assert names["extraction_labels_match"]["passed"] is True
    assert names["extraction_summary_match"]["passed"] is True
    assert names["extraction_family_keys_match"]["passed"] is True


def test_source_digests_not_mismatched(result):
    v = result["human_review"]["verification"]
    assert all(s["state"] != "mismatch" for s in v["source_status"])
    by_name = {s["name"]: s for s in v["source_status"]}
    assert by_name["decisions_pdf"]["state"] == "verified"
    assert by_name["solutions_pdf"]["state"] == "verified"


# ------------------------------------------------------------------ approvals
def test_approval_states(result):
    t = result["labels"]["totals"]
    assert t["approved_as_proposed"] == 16
    assert t["approved_corrected"] == 20
    assert t["approved"] == 36
    assert t["rejected"] == 1
    assert t["approval_states"] == {"APPROVED": 36, "REJECTED": 1}


def test_corrected_label_is_approved_not_pending(result):
    by_key = {e["family_key"]: e for e in result["labels"]["entries"]}
    for key, d in [(d["family_key"], d) for d in result["human_review"]["transcript"]["decisions"]]:
        want = "REJECTED" if d["human_decision"] == "REJECTED" else "APPROVED"
        assert by_key[key]["approval_state"] == want
        assert by_key[key]["human_decision"] == d["human_decision"]


def test_rejected_family_never_activates(result):
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    rej = [d["family_key"] for d in result["human_review"]["transcript"]["decisions"]
           if d["human_decision"] == "REJECTED"]
    assert rej == ["lc242_fam2"]
    for key in rej:
        assert outcomes[key]["activated"] is False
        assert outcomes[key]["approval_state"] == "REJECTED"


def test_nothing_is_auto_approved(result):
    assert result["labels"]["auto_approval"] is False
    assert result["labels"]["analyzer_detection_visible_to_reviewer"] is False
    assert result["labels"]["corrected_labels_added_to_runtime_vocabulary"] is False


# --------------------------------------------- vocabulary gaps / no invention
def test_unregistered_labels_never_become_activated_groups(result):
    """A human label term outside the frozen taxonomy must refuse, not invent."""
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    entries = {e["family_key"]: e for e in result["labels"]["entries"]}
    for key, e in entries.items():
        if e["unregistered_label_terms"]:
            assert e["divergence_state"] in (STATE_LABEL_UNEXPRESSIBLE, STATE_ZERO_EVIDENCE)
            assert outcomes[key]["activated"] is False


def test_vocabulary_gaps_are_recorded_not_added(result):
    gaps = result["vocabulary_gap_evidence"]
    unregistered = {t for t, e in gaps.items() if not e["registered_in_frozen_taxonomy"]}
    assert unregistered == {
        "brute_force", "sort_and_rebuild", "recursive_merge", "iterative_insertion",
        "recursive_dfs_by_depth", "recursive_dfs_traversal", "clean_and_compare_reverse",
    }
    for term in unregistered:
        assert term not in PEC_CONCEPTS and term not in SUPPORT_CONCEPTS
    # no gap term leaked into an activated group's required set
    for o in result["derivation"]["outcomes"]:
        if o["activated"]:
            assert not (set(o["required"]) & unregistered)


def test_observed_but_unregistered_terms_are_reported(result):
    gaps = result["vocabulary_gap_evidence"]
    assert gaps["brute_force"]["occurrences"] == 4
    assert gaps["brute_force"]["observed_in_families"] == []


# ------------------------------------------------ specificity floor / narrowing
def test_specificity_floor_refuses_support_only_human_labels(result):
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    generic = [k for k, o in outcomes.items() if o["divergence_state"] == STATE_LABEL_GENERIC]
    assert generic, "expected human-approved generic labels to be refused"
    for key in generic:
        assert outcomes[key]["activated"] is False
        assert outcomes[key]["label_required"] in (
            ["sequential_accumulation"], ["forward_pointer_advance"],
        )
    assert len(generic) == 6


def test_never_narrow_holds_for_human_labels(result):
    d = result["derivation"]
    assert d["totals"]["narrowing_violations"] == 0
    for o in d["outcomes"]:
        if o["activated"]:
            assert set(o["required"]) == set(o["label_required"])
            assert set(o["required"]) <= set(o["observed_intersection"])


def test_partial_human_label_refuses_instead_of_narrowing(result):
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    o = outcomes["lc560_fam3"]
    assert o["label_required"] == ["frequency_counting", "sequential_accumulation"]
    assert o["observed_intersection"] == ["sequential_accumulation"]
    assert o["divergence_state"] == STATE_LABEL_PARTIAL
    assert o["activated"] is False


def test_all_non_activated_human_labels_carry_a_refusal_reason(result):
    for o in result["derivation"]["outcomes"]:
        if o["activated"]:
            continue
        assert o["divergence_state"] in NON_ACTIVATABLE_STATES or \
            o["approval_state"] == "REJECTED"


def test_intended_new_activations_present(result):
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    assert outcomes["lc70_fam2"]["activated"] is True
    assert outcomes["lc70_fam2"]["required"] == ["dp_top_down"]
    assert outcomes["lc1_fam4"]["activated"] is True
    assert outcomes["lc1_fam4"]["required"] == ["two_pointers_opposite"]
    assert result["derivation"]["totals"]["activated_groups"] == 14


# ------------------------------------------------------------------- controls
def test_negative_controls_with_human_groups(result):
    c = result["controls"]
    assert c["totals"]["eligible_pairs"] > 0
    assert c["totals"]["discrimination_FP"] == 0.0
    assert c["totals"]["failing_pairs"] == 0
    assert c["insufficient_controls_groups"] == []
    assert c["per_group"] and all(g["tested_controls"] == g["eligible_controls"]
                                  for g in c["per_group"])
    # OPEN-5 evidence: rule 3 (PEC disjointness) is what removes the same-family reuse
    assert c["totals"]["eligible_pairs_without_rule3"] >= c["totals"]["eligible_pairs"]


def test_no_group_carries_a_problem_level_excluded_set(result):
    """Human labels are family-independent, so no inherited `excluded` may remain."""
    for g in result["derivation"]["groups_by_problem"].values():
        for group in g:
            assert group["excluded"] == []


# ----------------------------------------------------------------- validation
def test_post_review_validation_is_validated(result):
    v = result["validation"]
    assert v["overall_state"] == "VALIDATED"
    assert v["failed_criteria"] == []
    for c in v["acceptance_criteria"]:
        assert c["met"] is True, f"{c['criterion']} not met: {c}"


def test_metrics_before_and_after(result):
    ba = result["before_after"]
    pre, post = ba["pre_review"], ba["post_review"]
    assert pre["active_groups"] == 12 and post["active_groups"] == 14
    assert pre["metrics"]["discrimination_FP"] == post["metrics"]["discrimination_FP"] == 0.0
    assert post["metrics"]["group_satisfiability"] == 1.0
    assert post["metrics"]["narrowing_violations"] == 0
    assert post["metrics"]["family_coverage"] == 1.0
    assert post["metrics"]["contradicted"] == 0
    assert post["metrics"]["approved_family_labels"] == 36
    # activation_rate must be reported as a denominator change, not a regression claim
    assert pre["activation_rate"] == 0.75
    assert post["activation_rate"] == 0.3889


def test_pre_review_failed_only_the_human_approval_gate(result):
    ba = result["before_after"]
    assert ba["pre_review"]["failed_criteria"] == ["approved_family_labels"]
    assert ba["post_review"]["failed_criteria"] == []


def test_verdict_changes_are_enumerated(result):
    changed = {c["solution_id"]: (c["before"], c["after"])
               for c in result["before_after"]["changed_verdicts"]}
    assert changed["S0008"] == ("UNRESOLVED", "CONFIRMED")
    assert changed["S0028"] == ("CONTRADICTED", "CONFIRMED")
    assert changed["S0029"] == ("CONTRADICTED", "CONFIRMED")
    assert changed["S0035"] == ("CONTRADICTED", "UNRESOLVED")
    assert changed["S0036"] == ("CONTRADICTED", "UNRESOLVED")
    assert len(changed) == 5


def test_zero_evidence_rules_survive_the_review(result):
    m = result["validation"]["metrics"]
    assert m["zero_evidence_confirmed"] == 0
    assert m["zero_evidence_labeled"] == 0
    assert m["zero_evidence_controls"] == 0
    outcomes = {o["family_key"]: o for o in result["derivation"]["outcomes"]}
    for o in outcomes.values():
        if o["divergence_state"] == STATE_ZERO_EVIDENCE:
            assert o["activated"] is False


def test_reviewer_artifact_still_hides_analyzer_detections(result):
    blob = json.dumps(result["labels"])
    for forbidden in ("technique_signature", "strategy_signature",
                      "analyzer_pec_set", "structural_profile"):
        assert forbidden not in blob


def test_provisional_and_strict_modes_converge_after_review(result):
    """With real approvals, PA1 is no longer needed: both modes activate the same groups."""
    ba = result["before_after"]
    assert ba["post_review"]["active_groups"] == ba["post_review"]["provisional_mode_groups"]
    assert ba["post_review"]["provisional_assumption"] is None


# ---------------------------------------------------------------- boundaries
def test_pre_review_root_artifacts_untouched(result):
    """The post-review run must not rewrite the frozen PA1 baseline artifacts."""
    before = {n: _bytes(os.path.join(POC_DIR, n)) for n in PRE_REVIEW_ARTIFACTS}
    fresh = run_poc.run_all()
    after = {n: _bytes(os.path.join(POC_DIR, n)) for n in PRE_REVIEW_ARTIFACTS}
    for n in PRE_REVIEW_ARTIFACTS:
        assert before[n] == after[n], f"{n} was rewritten by a later run"
    post = {n: _bytes(os.path.join(OUT, n)) for n in POST_REVIEW_ARTIFACTS}
    again = run_post_review.run_all(write=True)
    post2 = {n: _bytes(os.path.join(OUT, n)) for n in POST_REVIEW_ARTIFACTS}
    for n in POST_REVIEW_ARTIFACTS:
        assert post[n] == post2[n], f"post_review/{n} is not deterministic"
    assert again["manifest"]["artifacts"] == result["manifest"]["artifacts"]
    assert fresh["manifest"]["artifacts"] == run_poc.run_all()["manifest"]["artifacts"]


def test_human_review_markdown_is_deterministic(result):
    path = os.path.join(POC_DIR, "human_review.md")
    first = _bytes(path)
    run_post_review.run_all(write=True)
    assert _bytes(path) == first
    assert hashlib.sha256(first).hexdigest() == result["manifest"]["artifacts"]["human_review.md"]


def test_no_llm_network_or_db_use():
    import pathforge.db.db as db_module
    import pathforge.llm.openrouter_client as llm
    import pathforge.services.ground_truth_builder as gtb

    def _boom(*a, **k):
        raise AssertionError("post-review POC must not reach the LLM / network / database")

    saved = (llm.call_llm, getattr(gtb, "call_llm", None), db_module.get_connection)
    llm.call_llm = _boom
    if saved[1] is not None:
        gtb.call_llm = _boom
    db_module.get_connection = _boom
    try:
        out = run_post_review.run_all(write=False)
        assert out["validation"]["metrics"]["activated_groups"] == 14
    finally:
        llm.call_llm = saved[0]
        if saved[1] is not None:
            gtb.call_llm = saved[1]
        db_module.get_connection = saved[2]


def test_post_review_sources_contain_no_network_or_db_imports():
    forbidden = re.compile(
        r"\b(openrouter|httpx|urllib|socket|psycopg2|get_connection)\b")
    for name in ("human_review.py", "run_post_review.py"):
        with open(os.path.join(POC_DIR, name), encoding="utf-8") as fh:
            assert not forbidden.search(fh.read()), f"{name} contains a forbidden dependency"


# --------------------------------------------------- brute-force audit guard
def test_brute_force_is_not_a_runtime_vocabulary_concept(result):
    """The taxonomy audit depends on brute_force being label-only today."""
    gaps = result["vocabulary_gap_evidence"]
    assert gaps["brute_force"]["registered_in_frozen_taxonomy"] is False
    assert "brute_force" not in PEC_CONCEPTS
    assert "brute_force" not in SUPPORT_CONCEPTS
