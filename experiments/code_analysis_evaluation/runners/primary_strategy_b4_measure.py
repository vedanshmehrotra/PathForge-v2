"""Batch B4 measurement: BEFORE B4 vs AFTER B4 primary-strategy selection.

B4 is a presentation-layer selection batch, so it must be provably additive:

* the runner is reconstructed with ONLY the B4 lines removed (B2/B3 kept), and
  every deterministic field except the new ``strategy_selection`` key must be
  byte-identical between the two arms;
* the B3 family-coverage distribution and the old matcher's outcome distribution
  must be identical;
* only the new primary-strategy information changes.

It also reports the selection statistics the B4 brief asks for, plus every case
where the current registry cannot make a principled selection (a confidence tie
broken only by ``concept_id``).

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/primary_strategy_b4_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
OUT_PATH = RESULTS / "primary_strategy_b4_measurement.json"
RUNNER_PATH = ROOT / "pathforge" / "ast_analysis" / "shadow" / "shadow_runner.py"

ELAPSED_MARKER = "elapsed_ms = (time.perf_counter() - t0) * 1000"
NONDETERMINISTIC_KEYS = frozenset({"elapsed_ms", "strategy_selection"})


def reconstruct_pre_b4_runner():
    """Exec the current runner with exactly the B4 lines removed (B2/B3 kept)."""
    source = RUNNER_PATH.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    kept, removed, removed_idx = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "primary_strategy import select_submission_primary" in line:
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if line.strip().startswith("# Step 8 (B4)"):
            while i < len(lines) and ELAPSED_MARKER not in lines[i]:
                removed.append(lines[i].rstrip("\r\n"))
                removed_idx.append(i)
                i += 1
            continue
        if '"strategy_selection": strategy_selection,' in line or line.strip().startswith(
            "# B4 additive key"
        ):
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        kept.append(line)
        i += 1

    stripped = "".join(kept)
    assert len(kept) + len(removed) == len(lines), "reconstruction lost or added lines"
    assert "strategy_selection" not in stripped, "B4 lines left behind"
    # every removed line must be attributable to B4
    block_start = next(
        idx for idx, ln in enumerate(lines) if ln.strip().startswith("# Step 8 (B4)")
    )
    block_end = next(idx for idx, ln in enumerate(lines) if ELAPSED_MARKER in ln)
    for idx in removed_idx:
        text = lines[idx]
        assert (
            "strategy_selection" in text
            or "B4" in text
            or "primary_strategy" in text
            or block_start <= idx < block_end
        ), f"line {idx + 1} is not attributable to B4: {text!r}"

    namespace = {"__name__": "shadow_runner_pre_b4"}
    exec(compile(stripped, "<shadow_runner_pre_b4>", "exec"), namespace)
    return namespace["run_shadow_analysis"], removed


def _deterministic(shadow: dict) -> dict:
    return {
        k: v for k, v in shadow.items()
        if k not in NONDETERMINISTIC_KEYS
    }


def _case_stats(cases, pre_run, post_run) -> dict:
    """Compare the two arms and collect B4 selection statistics."""
    coverage_before = collections.Counter()
    coverage_after = collections.Counter()
    outcome_before = collections.Counter()
    outcome_after = collections.Counter()

    mismatches = []
    candidate_counts = collections.Counter()   # submissions by candidate count
    selected_distribution = collections.Counter()
    reason_distribution = collections.Counter()
    ties = 0
    ambiguities = 0
    ambiguity_cases = []
    family_candidate_counts = collections.Counter()

    for label, code, groups in cases:
        pre = pre_run(code, solution_groups=groups)
        post = post_run(code, solution_groups=groups)

        pre_cov = (pre or {}).get("coverage") or {}
        post_cov = (post or {}).get("coverage") or {}
        coverage_before[pre_cov.get("aggregate_state", "NONE")] += 1
        coverage_after[post_cov.get("aggregate_state", "NONE")] += 1
        outcome_before[((pre or {}).get("match_outcome") or {}).get("outcome", "NONE")] += 1
        outcome_after[((post or {}).get("match_outcome") or {}).get("outcome", "NONE")] += 1

        if pre is not None and post is not None:
            fields = sorted(set(pre) | set(post))
            for field in fields:
                if field in NONDETERMINISTIC_KEYS:
                    continue
                if pre.get(field) != post.get(field):
                    mismatches.append({
                        "case": label, "field": field,
                        "before": repr(pre.get(field))[:200],
                        "after": repr(post.get(field))[:200],
                    })

        selection = (post or {}).get("strategy_selection")
        if selection is None:
            continue
        sub = selection.get("submission") or {}
        n = len(sub.get("candidates") or [])
        if n == 0:
            candidate_counts["zero"] += 1
        elif n == 1:
            candidate_counts["exactly_one"] += 1
        else:
            candidate_counts["multiple"] += 1

        if sub.get("selected"):
            selected_distribution[sub["selected"]] += 1
        for reason in sub.get("reason_codes") or []:
            reason_distribution[reason] += 1
        if sub.get("tie_resolved"):
            ties += 1
        if sub.get("ambiguity"):
            ambiguities += 1
            ambiguity_cases.append({
                "case": label,
                "selected": sub.get("selected"),
                "candidates": [c["concept_id"] for c in sub.get("candidates") or []],
                "reason": (sub.get("reason_codes") or [None])[0],
            })

        for fam in selection.get("families") or []:
            fn = len(fam.get("candidates") or [])
            key = "zero" if fn == 0 else ("exactly_one" if fn == 1 else "multiple")
            family_candidate_counts[key] += 1

    return {
        "before_coverage_distribution": dict(sorted(coverage_before.items())),
        "after_coverage_distribution": dict(sorted(coverage_after.items())),
        "coverage_identical": coverage_before == coverage_after,
        "before_old_outcome_distribution": dict(sorted(outcome_before.items())),
        "after_old_outcome_distribution": dict(sorted(outcome_after.items())),
        "old_outcome_identical": outcome_before == outcome_after,
        "deterministic_field_mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "submission_candidate_counts": dict(candidate_counts),
        "family_candidate_counts": dict(family_candidate_counts),
        "selected_strategy_distribution": dict(sorted(selected_distribution.items())),
        "selection_reason_distribution": dict(sorted(reason_distribution.items())),
        "deterministic_primary_selected": sum(selected_distribution.values()),
        "unresolved_ties_broken_by_concept_id": ties,
        "ambiguity_count": ambiguities,
        "ambiguity_cases": ambiguity_cases,
    }


def corpus_a():
    payload = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    return [
        (rec.get("external_submission_id"), rec["source_code"], rec.get("groups") or None)
        for rec in payload["records"]
    ]


def corpus_b():
    payload = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    return [
        (rec.get("name"), rec["code"],
         [{"id": rec["name"], "required": list(rec.get("required_concepts") or [])}])
        for rec in payload["records"]
    ]


def main() -> int:
    pre_run, removed = reconstruct_pre_b4_runner()
    post_run = shadow_runner.run_shadow_analysis

    result_a = _case_stats(corpus_a(), pre_run, post_run)
    result_b = _case_stats(corpus_b(), pre_run, post_run)

    payload = {
        "batch": "B4",
        "layer": "specificity + primary-strategy selection (shadow/presentation only)",
        "pre_b4_reconstruction": {
            "source": str(RUNNER_PATH.relative_to(ROOT)),
            "removed_line_count": len(removed),
            "removed_lines": removed,
        },
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
        print("  coverage before/after:", result["before_coverage_distribution"],
              "==", result["after_coverage_distribution"],
              "identical:", result["coverage_identical"])
        print("  old outcome before/after:", result["before_old_outcome_distribution"],
              "==", result["after_old_outcome_distribution"],
              "identical:", result["old_outcome_identical"])
        print("  deterministic-field mismatches:", result["mismatch_count"])
        print("  submission candidate counts:", result["submission_candidate_counts"])
        print("  family candidate counts:", result["family_candidate_counts"])
        print("  selected strategies:", result["selected_strategy_distribution"])
        print("  reasons:", result["selection_reason_distribution"])
        print("  deterministic primary selected:", result["deterministic_primary_selected"])
        print("  ties broken by concept_id (ambiguity):", result["ambiguity_count"])
        for case in result["ambiguity_cases"][:10]:
            print("    !", case)
        for m in result["deterministic_field_mismatches"][:5]:
            print("    X", m)
    print("=" * 72)
    print("pre-B4 reconstruction removed", len(removed), "lines")
    print("written:", OUT_PATH.relative_to(ROOT))

    clean = (
        result_a["mismatch_count"] == 0 and result_b["mismatch_count"] == 0
        and result_a["coverage_identical"] and result_b["coverage_identical"]
        and result_a["old_outcome_identical"] and result_b["old_outcome_identical"]
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
