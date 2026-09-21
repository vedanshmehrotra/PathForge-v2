"""Post-human-review orchestrator for the V2 Ground-Truth POC (offline only).

    python -m experiments.code_analysis_evaluation.gt_poc_v2.run_post_review

Re-runs Phases 1-5 with the reviewer's family decisions as the approved
family-label input and writes a separate, self-contained artifact set under
``post_review/``.  The pre-review artifacts at the package root are NOT
rewritten (they remain the frozen PA1 baseline).

The frozen modules are used unchanged:
  ingest -> normalize -> grouping -> labeling (blind, pending)
  -> human_review.overlay (reviewer decisions)
  -> derive / controls / validate

Deterministic: no timestamps, no randomness, no network, no LLM, no DB access.
"""
import json
import os

from . import controls, derive, grouping, human_review, ingest, labeling, normalize, validate
from .core import PIPELINE_VERSION, sha256_hex
from .problem_metadata import (
    LABEL_MODE_PROVISIONAL,
    LABEL_MODE_STRICT,
    PEC_CONCEPTS,
    POC_VERSION,
    PROVISIONAL_ASSUMPTION_PA1,
    PROVISIONAL_REPRESENTATIVE_TAU,
    SUPPORT_CONCEPTS,
    TAXONOMY_VERSION,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "post_review")


def _dump(path: str, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=False) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return sha256_hex(text)


def _activation_map(derivation: dict) -> dict:
    return {
        o["family_key"]: {
            "activated": o["activated"],
            "reason": o["reason"],
            "divergence_state": o["divergence_state"],
            "approval_state": o["approval_state"],
            "label_required": o["label_required"],
            "required": o.get("required"),
            "observed_intersection": o["observed_intersection"],
            "label_source": o["label_source"],
        }
        for o in derivation["outcomes"]
    }


def _vocabulary_gap_evidence(reference_artifact, normalized_artifact, group_artifact,
                             transcript, post_labels, post_derivation) -> dict:
    """Per human label term: registry status + corpus evidence (no new rules)."""
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    families = {f["family_key"]: f for f in group_artifact["families"]}
    act = _activation_map(post_derivation)
    by_family = {e["family_key"]: e for e in post_labels["entries"]}

    terms = {}
    for d in transcript["decisions"]:
        for t in d["human_label_terms"]:
            terms.setdefault(t, {"term": t, "families": []})
            terms[t]["families"].append(d["family_key"])

    out = {}
    for term, info in sorted(terms.items()):
        registered = term in PEC_CONCEPTS or term in SUPPORT_CONCEPTS
        observed_in = []
        for fk in info["families"]:
            unions = set()
            for sid in families[fk]["members"]:
                unions |= set(rows[sid]["concepts"])
            if term in unions:
                observed_in.append(fk)
        out[term] = {
            "term": term,
            "registered_in_frozen_taxonomy": registered,
            "tier": "PEC" if term in PEC_CONCEPTS else ("SUPPORT" if term in SUPPORT_CONCEPTS else None),
            "occurrences": len(info["families"]),
            "families": info["families"],
            "observed_in_families": observed_in,
            "activation_outcomes": sorted({
                act[fk]["reason"] for fk in info["families"]
            }),
            "post_review_states": sorted({
                by_family[fk]["divergence_state"] for fk in info["families"]
            }),
        }
    return out


def run_all(write: bool = True) -> dict:
    reference = ingest.run()
    normalized = normalize.run(reference)
    families = grouping.run(normalized)
    labels = labeling.build(reference, normalized, families)

    # ---------------------------------------------------------------- before
    pre_derivation = derive.derive(normalized, families, labels,
                                   label_mode=LABEL_MODE_PROVISIONAL)
    pre_controls = controls.run(reference, normalized, pre_derivation, PEC_CONCEPTS)
    pre_validation = validate.run(reference, normalized, families, labels,
                                 pre_derivation, pre_controls)
    pre_test = derive.derive(normalized, families, labels, label_mode=LABEL_MODE_STRICT)

    # ------------------------------------------------------------ human review
    hr = human_review.run(families, reference, normalized, labels, write=write)
    post_labels = hr["labels"]

    post_provisional = derive.derive(normalized, families, post_labels,
                                     label_mode=LABEL_MODE_PROVISIONAL)
    post_derivation = derive.derive(normalized, families, post_labels,
                                    label_mode=LABEL_MODE_STRICT)
    post_controls = controls.run(reference, normalized, post_derivation, PEC_CONCEPTS)
    post_validation = validate.run(reference, normalized, families, post_labels,
                                  post_derivation, post_controls)
    comparison = labeling.build_comparison(normalized, families, post_labels)
    gap_evidence = _vocabulary_gap_evidence(reference, normalized, families,
                                            hr["transcript"], post_labels, post_derivation)

    # ------------------------------------------------------------ before/after
    pre_metrics = pre_validation["metrics"]
    post_metrics = post_validation["metrics"]
    before_after = {
        "phase": "5c_before_after",
        "pre_review": {
            "label_mode": LABEL_MODE_PROVISIONAL,
            "provisional_assumption": PROVISIONAL_ASSUMPTION_PA1,
            "active_groups": pre_derivation["totals"]["activated_groups"],
            "activation_rate": pre_derivation["totals"]["activation_rate"],
            "strict_groups": pre_test["totals"]["activated_groups"],
            "divergence_state_counts": pre_derivation["divergence_state_counts"],
            "metrics": pre_metrics,
            "overall_state": pre_validation["overall_state"],
            "failed_criteria": pre_validation["failed_criteria"],
        },
        "post_review": {
            "label_mode": LABEL_MODE_STRICT,
            "provisional_assumption": None,
            "active_groups": post_derivation["totals"]["activated_groups"],
            "activation_rate": post_derivation["totals"]["activation_rate"],
            "provisional_mode_groups": post_provisional["totals"]["activated_groups"],
            "divergence_state_counts": post_derivation["divergence_state_counts"],
            "metrics": post_metrics,
            "overall_state": post_validation["overall_state"],
            "failed_criteria": post_validation["failed_criteria"],
        },
        "changed_verdicts": [],
        "unchanged_verdicts": [],
        "changed_families": [],
        "unchanged_families": [],
        "activation_reason_counts": {},
    }

    pre_act = _activation_map(pre_derivation)
    post_act = _activation_map(post_derivation)
    for fk in sorted(pre_act):
        if pre_act[fk]["activated"] != post_act[fk]["activated"] or \
                pre_act[fk]["required"] != post_act[fk]["required"]:
            before_after["changed_families"].append({
                "family_key": fk,
                "before": pre_act[fk],
                "after": post_act[fk],
            })
        else:
            before_after["unchanged_families"].append(fk)
        reason = post_act[fk]["reason"]
        before_after["activation_reason_counts"][reason] = \
            before_after["activation_reason_counts"].get(reason, 0) + 1

    pre_ho = {r["solution_id"]: r for r in pre_validation["held_out_results"]}
    post_ho = {r["solution_id"]: r for r in post_validation["held_out_results"]}
    for sid in sorted(post_ho):
        if pre_ho[sid]["outcome"] != post_ho[sid]["outcome"]:
            before_after["changed_verdicts"].append({
                "solution_id": sid,
                "problem_id": post_ho[sid]["problem_id"],
                "family_key": post_ho[sid]["family_key"],
                "before": pre_ho[sid]["outcome"],
                "after": post_ho[sid]["outcome"],
            })
        else:
            before_after["unchanged_verdicts"].append(sid)

    result = {
        "reference": reference,
        "normalized": normalized,
        "families": families,
        "labels": post_labels,
        "human_review": hr,
        "comparison": comparison,
        "derivation": post_derivation,
        "controls": post_controls,
        "validation": post_validation,
        "before_after": before_after,
        "vocabulary_gap_evidence": gap_evidence,
    }

    if not write:
        return result

    os.makedirs(OUT, exist_ok=True)
    digests = {}
    digests["reference_solutions.json"] = _dump(os.path.join(OUT, "reference_solutions.json"), reference)
    digests["normalized_solutions.json"] = _dump(os.path.join(OUT, "normalized_solutions.json"), normalized)
    digests["families.json"] = _dump(os.path.join(OUT, "families.json"), families)
    digests["family_labels_post_review.json"] = _dump(
        os.path.join(OUT, "family_labels_post_review.json"), post_labels)
    digests["human_review_audit.json"] = _dump(
        os.path.join(OUT, "human_review_audit.json"), hr["audit"])
    digests["human_review_verification.json"] = _dump(
        os.path.join(OUT, "human_review_verification.json"), hr["verification"])
    digests["label_comparison.json"] = _dump(
        os.path.join(OUT, "label_comparison.json"), comparison)
    digests["derivation_outcomes.json"] = _dump(
        os.path.join(OUT, "derivation_outcomes.json"), post_derivation)
    digests["negative_controls.json"] = _dump(
        os.path.join(OUT, "negative_controls.json"), post_controls)
    digests["validation.json"] = _dump(os.path.join(OUT, "validation.json"), post_validation)
    digests["before_after.json"] = _dump(os.path.join(OUT, "before_after.json"), before_after)
    digests["vocabulary_gaps.json"] = _dump(
        os.path.join(OUT, "vocabulary_gaps.json"), gap_evidence)
    digests["human_review.md"] = sha256_hex(hr["markdown"])

    manifest = {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "provisional_representative_tau": PROVISIONAL_REPRESENTATIVE_TAU,
        "label_mode": LABEL_MODE_STRICT,
        "provisional_assumption": None,
        "human_review_round": hr["transcript"]["round"],
        "human_review_verification_passed": hr["verification"]["passed"],
        "artifacts": {name: digest for name, digest in sorted(digests.items())},
    }
    _dump(os.path.join(OUT, "run_manifest.json"), manifest)
    result["manifest"] = manifest
    return result


def summarize(result: dict) -> str:
    ba = result["before_after"]
    pre, post = ba["pre_review"], ba["post_review"]
    pm, qm = pre["metrics"], post["metrics"]
    lines = [
        "=" * 74,
        "  GROUND-TRUTH POC V2 — POST HUMAN REVIEW (offline, deterministic)",
        "=" * 74,
        f"  reviewer: {result['human_review']['transcript']['reviewer']}",
        f"  transcript verification passed: {result['human_review']['verification']['passed']}",
        f"  decisions: approved={result['labels']['totals']['approved_as_proposed']} "
        f"corrected={result['labels']['totals']['approved_corrected']} "
        f"rejected={result['labels']['totals']['rejected']}",
        "",
        f"  active groups:   before={pre['active_groups']} (provisional)  after={post['active_groups']} (strict human)",
        f"  activation_rate: before={pre['activation_rate']}  after={post['activation_rate']}",
        f"  divergence:      after={post['divergence_state_counts']}",
        "",
        f"  discrimination_FP:   {pm['discrimination_FP']} -> {qm['discrimination_FP']}",
        f"  group_satisfiability: {pm['group_satisfiability']} -> {qm['group_satisfiability']}",
        f"  family_coverage:     {pm['family_coverage']} -> {qm['family_coverage']}",
        f"  narrowing_violations:{pm['narrowing_violations']} -> {qm['narrowing_violations']}",
        f"  verdicts (held-out): confirmed={pm['confirmed']}->{qm['confirmed']} "
        f"unresolved={pm['unresolved']}->{qm['unresolved']} "
        f"contradicted={pm['contradicted']}->{qm['contradicted']}",
        "",
        f"  overall: {pre['overall_state']} -> {post['overall_state']}",
        f"  failed criteria before: {pre['failed_criteria']}",
        f"  failed criteria after:  {post['failed_criteria']}",
        "=" * 74,
    ]
    return "\n".join(lines)


def main() -> int:
    print(summarize(run_all()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
