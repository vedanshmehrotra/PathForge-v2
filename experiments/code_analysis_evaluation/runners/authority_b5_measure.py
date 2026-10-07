"""Batch B5 measurement: BEFORE B5 vs AFTER B5 authority gating.

B5 is an evaluation layer, so it must be provably additive:

* the runner is reconstructed with ONLY the B5 lines removed (B2/B3/B4 kept),
  and every field except the new ``authority`` key must be byte-identical
  between the two arms;
* B2 evidence, B3 coverage, B4 candidates + selection, and the legacy matcher's
  ``match_outcome`` (including its own nested ``primary_strategy``) must be
  unchanged.

It also reports the authority statistics the B5 brief asks for.

Corpus notes (documented data-quality findings, not repairs):

* the 46-submission corpus stores its Ground-Truth groups WITHOUT
  ``authority_tier`` — the field was dropped during serialization. The
  record-level ``shadow_authority_tier`` (which the original run recorded from
  the real groups) is re-attached for the authority analysis and is exact for
  single-family records.
* the 301-case corpus carries no authority metadata at all, so its synthetic
  groups are labelled ``llm_proposed`` (inferred / non-authoritative).

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/authority_b5_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis.shadow import authority_gating as ag  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
OUT_PATH = RESULTS / "authority_b5_measurement.json"
RUNNER_PATH = ROOT / "pathforge" / "ast_analysis" / "shadow" / "shadow_runner.py"

ELAPSED_MARKER = "elapsed_ms = (time.perf_counter() - t0) * 1000"
NONDETERMINISTIC_KEYS = frozenset({"elapsed_ms", "authority"})


def reconstruct_pre_b5_runner():
    """Exec the current runner with exactly the B5 lines removed (B2/B3/B4 kept)."""
    source = RUNNER_PATH.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    kept, removed, removed_idx = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "authority_gating import evaluate_authority" in line:
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if line.strip().startswith("# Step 9 (B5)"):
            while i < len(lines) and ELAPSED_MARKER not in lines[i]:
                removed.append(lines[i].rstrip("\r\n"))
                removed_idx.append(i)
                i += 1
            continue
        if '"authority": authority,' in line or line.strip().startswith(
            "# B5 additive key"
        ):
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        kept.append(line)
        i += 1

    stripped = "".join(kept)
    assert len(kept) + len(removed) == len(lines), "reconstruction lost or added lines"
    assert "evaluate_authority" not in stripped, "B5 lines left behind"
    assert '"authority": authority,' not in stripped, "B5 key left behind"
    block_start = next(
        idx for idx, ln in enumerate(lines) if ln.strip().startswith("# Step 9 (B5)")
    )
    block_end = next(idx for idx, ln in enumerate(lines) if ELAPSED_MARKER in ln)
    for idx in removed_idx:
        text = lines[idx]
        assert (
            "authority" in text
            or "B5" in text
            or block_start <= idx < block_end
        ), f"line {idx + 1} is not attributable to B5: {text!r}"

    namespace = {"__name__": "shadow_runner_pre_b5"}
    exec(compile(stripped, "<shadow_runner_pre_b5>", "exec"), namespace)
    return namespace["run_shadow_analysis"], removed


def _sorted(counter) -> dict:
    """Deterministic dict from a Counter whose keys may be ``None``."""
    return {str(k): counter[k] for k in sorted(counter, key=lambda k: (k is None, str(k)))}


def _deterministic(shadow: dict) -> dict:
    return {k: v for k, v in shadow.items() if k not in NONDETERMINISTIC_KEYS}


def _case_stats(cases, pre_run, post_run) -> dict:
    coverage_before = collections.Counter()
    coverage_after = collections.Counter()
    outcome_before = collections.Counter()
    outcome_after = collections.Counter()
    selection_before = collections.Counter()
    selection_after = collections.Counter()

    mismatches = []
    aggregation = collections.Counter()
    declared_tiers = collections.Counter()
    mapped_tiers = collections.Counter()
    family_states = collections.Counter()
    reasons = collections.Counter()
    authoritative_families = 0
    non_authoritative_families = 0
    safe_cases = 0
    mixed_cases = 0
    no_gt_cases = 0
    no_auth_cases = 0
    all_auth_cases = 0
    structural_only_strategy_cases = []
    unrecognized = collections.Counter()

    for label, code, groups in cases:
        pre = pre_run(code, solution_groups=groups)
        post = post_run(code, solution_groups=groups)

        pre_cov = (pre or {}).get("coverage") or {}
        post_cov = (post or {}).get("coverage") or {}
        coverage_before[pre_cov.get("aggregate_state", "NONE")] += 1
        coverage_after[post_cov.get("aggregate_state", "NONE")] += 1
        outcome_before[((pre or {}).get("match_outcome") or {}).get("outcome", "NONE")] += 1
        outcome_after[((post or {}).get("match_outcome") or {}).get("outcome", "NONE")] += 1

        pre_sel = ((pre or {}).get("strategy_selection") or {}).get("submission", {})
        post_sel = ((post or {}).get("strategy_selection") or {}).get("submission", {})
        selection_before[pre_sel.get("selected")] += 1
        selection_after[post_sel.get("selected")] += 1

        if pre is not None and post is not None:
            for field in sorted(set(pre) | set(post)):
                if field in NONDETERMINISTIC_KEYS:
                    continue
                if pre.get(field) != post.get(field):
                    mismatches.append({
                        "case": label, "field": field,
                        "before": repr(pre.get(field))[:200],
                        "after": repr(post.get(field))[:200],
                    })

        authority = (post or {}).get("authority")
        if authority is None:
            continue
        agg = authority["aggregation"]
        aggregation[agg] += 1
        safe_cases += 1 if authority["safe_for_product_scoring"] else 0
        mixed_cases += 1 if agg == ag.AGG_MIXED_AUTHORITY else 0
        no_gt_cases += 1 if agg == ag.AGG_NO_GROUND_TRUTH else 0
        no_auth_cases += 1 if agg == ag.AGG_NO_AUTHORITATIVE_FAMILY else 0
        all_auth_cases += 1 if agg == ag.AGG_ALL_FAMILIES_AUTHORITATIVE else 0

        for fam in authority["families"]:
            declared_tiers[fam["declared_authority_tier"]] += 1
            mapped_tiers[fam["authority_tier"]] += 1
            family_states[fam["coverage_state"]] += 1
            for reason in fam["reason_codes"]:
                reasons[reason] += 1
            if not fam["authority_known"]:
                unrecognized[fam["declared_authority_tier"]] += 1
            if fam["authoritative"]:
                authoritative_families += 1
            else:
                non_authoritative_families += 1
                if (fam["coverage_state"] == "CONFIRMED"
                        and fam["primary_strategy"]
                        and fam["authority_tier"] == ag.STRUCTURALLY_OBSERVED):
                    structural_only_strategy_cases.append({
                        "case": label,
                        "family_id": fam["family_id"],
                        "primary_strategy": fam["primary_strategy"],
                    })

    return {
        "before_coverage_distribution": dict(sorted(coverage_before.items())),
        "after_coverage_distribution": dict(sorted(coverage_after.items())),
        "coverage_identical": coverage_before == coverage_after,
        "before_old_outcome_distribution": dict(sorted(outcome_before.items())),
        "after_old_outcome_distribution": dict(sorted(outcome_after.items())),
        "old_outcome_identical": outcome_before == outcome_after,
        "before_selected_distribution": _sorted(selection_before),
        "after_selected_distribution": _sorted(selection_after),
        "selected_identical": selection_before == selection_after,
        "deterministic_field_mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "aggregation_distribution": dict(sorted(aggregation.items())),
        "declared_authority_tiers": dict(sorted(declared_tiers.items())),
        "mapped_authority_tiers": dict(sorted(mapped_tiers.items())),
        "family_coverage_states": dict(sorted(family_states.items())),
        "family_authority_reasons": dict(sorted(reasons.items())),
        "authoritative_families": authoritative_families,
        "non_authoritative_families": non_authoritative_families,
        "unrecognized_authority_tiers": dict(sorted(unrecognized.items())),
        "structurally_observed_with_strategy_cases": structural_only_strategy_cases[:20],
        "structurally_observed_with_strategy_count":
            len(structural_only_strategy_cases),
        "safe_for_product_scoring_submissions": safe_cases,
        "mixed_authority_submissions": mixed_cases,
        "no_ground_truth_submissions": no_gt_cases,
        "no_authoritative_family_submissions": no_auth_cases,
        "all_families_authoritative_submissions": all_auth_cases,
    }


def corpus_a():
    payload = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    cases = []
    for rec in payload["records"]:
        groups = rec.get("groups") or None
        if groups:
            fallback = rec.get("shadow_authority_tier") or "unknown"
            groups = [dict(g) for g in groups]
            for g in groups:
                g.setdefault("authority_tier", fallback)
        cases.append((rec.get("external_submission_id"), rec["source_code"], groups))
    return cases


def corpus_b():
    payload = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    return [
        (rec.get("name"), rec["code"],
         [{"id": rec["name"], "required": list(rec.get("required_concepts") or []),
           "authority_tier": "llm_proposed"}])
        for rec in payload["records"]
    ]


def main() -> int:
    pre_run, removed = reconstruct_pre_b5_runner()
    post_run = shadow_runner.run_shadow_analysis

    result_a = _case_stats(corpus_a(), pre_run, post_run)
    result_b = _case_stats(corpus_b(), pre_run, post_run)

    # Expand with multiplicity so the data-quality scan counts each family.
    all_declared = [
        tier
        for result in (result_a, result_b)
        for tier, count in result["declared_authority_tiers"].items()
        for _ in range(count)
    ]
    payload = {
        "batch": "B5",
        "layer": "authority gating (shadow evaluation only)",
        "pre_b5_reconstruction": {
            "source": str(RUNNER_PATH.relative_to(ROOT)),
            "removed_line_count": len(removed),
            "removed_lines": removed,
        },
        "corpus_notes": {
            "corpus_a": "46 real submissions; groups had authority_tier stripped at "
                        "serialization, so the record-level shadow_authority_tier is "
                        "re-attached (exact for single-family records)",
            "corpus_b": "301 disjoint cases; no authority metadata, synthetic groups "
                        "labelled llm_proposed",
        },
        "declared_tier_data_quality": ag.authority_data_quality(all_declared),
        "corpus_a_46_real_submissions": result_a,
        "corpus_b_301_disjoint_cases": result_b,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for name, result in (
        ("corpus_a_46_real_submissions", result_a),
        ("corpus_b_301_disjoint_cases", result_b),
    ):
        print("=" * 72)
        print(name)
        print("  coverage before/after:", result["before_coverage_distribution"], "==",
              result["after_coverage_distribution"],
              "identical:", result["coverage_identical"])
        print("  old outcome before/after:", result["before_old_outcome_distribution"],
              "==", result["after_old_outcome_distribution"],
              "identical:", result["old_outcome_identical"])
        print("  B4 selected identical:", result["selected_identical"])
        print("  deterministic-field mismatches:", result["mismatch_count"])
        print("  aggregation:", result["aggregation_distribution"])
        print("  declared tiers:", result["declared_authority_tiers"])
        print("  mapped tiers:", result["mapped_authority_tiers"])
        print("  family coverage states:", result["family_coverage_states"])
        print("  family reasons:", result["family_authority_reasons"])
        print("  authoritative families:", result["authoritative_families"],
              "non-authoritative:", result["non_authoritative_families"])
        print("  safe_for_product_scoring submissions:",
              result["safe_for_product_scoring_submissions"])
        print("  mixed:", result["mixed_authority_submissions"],
              "no-gt:", result["no_ground_truth_submissions"],
              "no-auth:", result["no_authoritative_family_submissions"],
              "all-auth:", result["all_families_authoritative_submissions"])
        print("  structural-only strategies:", result["structurally_observed_with_strategy_count"])
        for m in result["deterministic_field_mismatches"][:5]:
            print("    X", m)
    print("=" * 72)
    print("pre-B5 reconstruction removed", len(removed), "lines")
    print("written:", OUT_PATH.relative_to(ROOT))

    clean = (
        result_a["mismatch_count"] == 0 and result_b["mismatch_count"] == 0
        and result_a["coverage_identical"] and result_b["coverage_identical"]
        and result_a["old_outcome_identical"] and result_b["old_outcome_identical"]
        and result_a["selected_identical"] and result_b["selected_identical"]
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
