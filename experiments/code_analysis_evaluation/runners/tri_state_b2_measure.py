"""Batch B2 measurement: tri-state evidence BEFORE B2 vs AFTER B2.

Why this does not use the recorded result artifacts as its "before"
-----------------------------------------------------------------

The obvious approach is to compare against the recorded baseline files
(``results/db_batch3/submission_eval_results.json`` and
``results/disjoint301_eval_results_BASELINE_step4.json``). Those files are NOT a
valid "before B2" reference: they were produced before other work landed on this
branch, so replaying them today already differs for reasons unrelated to B2
(added structural facts such as ``mapping_construction``/``membership_test``,
the ``sequential_accumulation`` relation extension, and reconstructed group
authority tiers). Using them would flag pre-existing drift as a B2 regression.

This script instead isolates B2 as the only variable:

1. It reconstructs the PRE-B2 implementation by stripping exactly the B2 lines
   from the current ``shadow_runner.py`` source, and reports those lines so the
   reconstruction is auditable. (The B2 change to that file is additive: one
   import, one guarded block, one dict key.)
2. It runs both implementations over the same corpora and inputs and compares
   EVERY field of the shadow result.
3. It separately replays the recorded artifacts and asserts that the drift
   against them is IDENTICAL in both arms — which is what proves B2 caused none
   of it.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/tri_state_b2_measure.py
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
OUT_PATH = RESULTS / "tri_state_b2_measurement.json"
RUNNER_PATH = ROOT / "pathforge" / "ast_analysis" / "shadow" / "shadow_runner.py"

ELAPSED_MARKER = "elapsed_ms = (time.perf_counter() - t0) * 1000"


# ---------------------------------------------------------------------------
# Reconstruct the pre-B2 runner
# ---------------------------------------------------------------------------

def reconstruct_pre_b2_runner():
    """Exec the current runner source with exactly the B2 lines removed."""
    source = RUNNER_PATH.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    kept, removed, removed_idx = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "evidence_state import build_evidence_snapshot" in line:
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if "family_coverage import build_family_coverage" in line:
            # B3 sits on top of the B2 block; the "pre-B2" reconstruction
            # removes both additive batches (it must remain runnable).
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if "primary_strategy import select_submission_primary" in line:
            # B4 is likewise additive on top of B2/B3.
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if line.strip().startswith("# Step 6 (B2)"):
            while i < len(lines) and ELAPSED_MARKER not in lines[i]:
                removed.append(lines[i].rstrip("\r\n"))
                removed_idx.append(i)
                i += 1
            continue
        if '"evidence_state": evidence_state,' in line or line.strip().startswith(
            "# B2 additive key"
        ):
            removed.append(line.rstrip("\r\n"))
            removed_idx.append(i)
            i += 1
            continue
        if '"coverage": coverage,' in line or line.strip().startswith(
            "# B3 additive key"
        ):
            removed.append(line.rstrip("\r\n"))
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
    # 1. the reconstruction is a pure deletion of the current source
    assert len(kept) + len(removed) == len(lines), "reconstruction lost or added lines"
    # 2. nothing B2-related survives
    assert "evidence_state" not in stripped, "B2 lines left behind"
    assert "coverage" not in stripped, "B3 lines left behind"
    assert "strategy_selection" not in stripped, "B4 lines left behind"
    # 3. every removed line is attributable to B2: it either names the B2
    #    symbol, or it lies inside the marker-bounded step-6 block.
    block_start = next(
        idx for idx, ln in enumerate(lines) if ln.strip().startswith("# Step 6 (B2)")
    )
    block_end = next(idx for idx, ln in enumerate(lines) if ELAPSED_MARKER in ln)
    for idx in removed_idx:
        text = lines[idx]
        assert (
            "evidence_state" in text
            or "B2" in text
            or "coverage" in text
            or "B3" in text
            or "strategy_selection" in text
            or "primary_strategy" in text
            or "B4" in text
            or block_start <= idx < block_end
        ), f"line {idx + 1} is not attributable to B2/B3/B4: {text!r}"

    namespace = {"__name__": "shadow_runner_pre_b2"}
    exec(compile(stripped, "<shadow_runner_pre_b2>", "exec"), namespace)
    return namespace["run_shadow_analysis"], removed


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------

#: ``elapsed_ms`` is a wall-clock measurement, not a behavioural output, so it
#: cannot be byte-compared. It is excluded from the equality check and its
#: before/after delta is reported separately as B2's instrumentation cost.
NONDETERMINISTIC_KEYS = frozenset({"elapsed_ms"})


def _full_fields(shadow: dict) -> dict:
    """Every deterministic key of the shadow result except the additive keys."""
    return {
        k: v
        for k, v in shadow.items()
        if k not in ("evidence_state", "coverage", "strategy_selection")
        and k not in NONDETERMINISTIC_KEYS
    }


def _tri_state_summary(evidence_state: dict) -> collections.Counter:
    summary = collections.Counter(evidence_state["counts"])
    for key, value in evidence_state["reason_counts"].items():
        summary[f"reason:{key}"] += value
    summary["contradicted_by_falsifier"] = evidence_state["reason_counts"].get(
        "structural_falsifier", 0
    )
    summary["contradicted_by_mutex"] = evidence_state["reason_counts"].get(
        "mutual_exclusion", 0
    )
    return summary


def compare_corpus(pre_run, post_run, cases) -> dict:
    """Run both implementations over ``cases`` and diff every result field."""
    before_counts, after_counts = collections.Counter(), collections.Counter()
    mismatches, tri, missing_key = [], collections.Counter(), 0
    timing_deltas = []

    for label, code, groups in cases:
        pre = pre_run(code, solution_groups=groups)
        post = post_run(code, solution_groups=groups)

        pre_outcome = (pre or {}).get("match_outcome", {}).get("outcome", "NONE")
        post_outcome = (post or {}).get("match_outcome", {}).get("outcome", "NONE")
        before_counts[pre_outcome] += 1
        after_counts[post_outcome] += 1

        if post is None:
            continue
        if pre is not None:
            timing_deltas.append(post["elapsed_ms"] - pre["elapsed_ms"])
        if post.get("evidence_state") is None:
            missing_key += 1
        else:
            tri.update(_tri_state_summary(post["evidence_state"]))

        pre_fields = _full_fields(pre or {})
        post_fields = _full_fields(post)
        for field in sorted(set(pre_fields) | set(post_fields)):
            if pre_fields.get(field) != post_fields.get(field):
                mismatches.append({
                    "case": label,
                    "field": field,
                    "before": repr(pre_fields.get(field))[:300],
                    "after": repr(post_fields.get(field))[:300],
                })

    timing_deltas.sort()

    def _pct(values, q):
        return round(values[min(len(values) - 1, int(len(values) * q))], 3) if values else None

    return {
        "cases": len(cases),
        "before_outcome_counts": dict(before_counts),
        "after_outcome_counts": dict(after_counts),
        "outcome_changed": before_counts != after_counts,
        "excluded_nondeterministic_keys": sorted(NONDETERMINISTIC_KEYS),
        "instrumentation_cost_ms": {
            "median_delta": _pct(timing_deltas, 0.5),
            "p90_delta": _pct(timing_deltas, 0.9),
            "max_delta": round(timing_deltas[-1], 3) if timing_deltas else None,
        },
        "field_mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "cases_missing_evidence_state": missing_key,
        "tri_state_totals": dict(sorted(tri.items())),
    }


def drift_vs_recorded(pre_run, post_run, cases, recorded) -> dict:
    """Compare both arms against the recorded artifact.

    If the drift is the same in both arms, B2 is provably not its cause.
    """
    pre_drift, post_drift = set(), set()
    for (label, code, groups), rec in zip(cases, recorded):
        pre = pre_run(code, solution_groups=groups)
        post = post_run(code, solution_groups=groups)
        for field, expected in rec.items():
            got_pre = _recorded_field(pre, field)
            got_post = _recorded_field(post, field)
            if got_pre != expected:
                pre_drift.add((label, field))
            if got_post != expected:
                post_drift.add((label, field))
    return {
        "pre_b2_drift_fields": len(pre_drift),
        "post_b2_drift_fields": len(post_drift),
        "drift_identical_in_both_arms": pre_drift == post_drift,
        "b2_attributable_drift": sorted(post_drift - pre_drift),
    }


_RECORDED_FIELD_MAP = {
    "outcome": ("match_outcome", "outcome"),
    "authority_tier": ("match_outcome", "authority_tier"),
    "primary_strategy": ("match_outcome", "primary_strategy"),
    "techniques": ("technique_evidence", None),
    "strategies": ("strategy_evidence", None),
    "fact_types": ("structural_facts", None),
}


def _recorded_field(shadow, field):
    """Read a recorded-artifact field out of a shadow result."""
    if shadow is None or field not in _RECORDED_FIELD_MAP:
        return None
    key, sub = _RECORDED_FIELD_MAP[field]
    value = shadow.get(key)
    if sub is not None:
        return (value or {}).get(sub)
    if key == "technique_evidence":
        return value or []
    if key == "strategy_evidence":
        return value or []
    return sorted({f["fact_type"] for f in value or []})


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------

def corpus_a():
    payload = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    cases, recorded = [], []
    for rec in payload["records"]:
        label = f"{rec.get('external_submission_id')}:{rec.get('problem_id')}"
        cases.append((label, rec["source_code"], rec.get("groups") or None))
        recorded.append({
            "outcome": rec.get("shadow_outcome"),
            "authority_tier": rec.get("shadow_authority_tier"),
            "primary_strategy": rec.get("shadow_primary_strategy"),
            "techniques": rec.get("shadow_techniques") or [],
            "strategies": rec.get("shadow_strategies") or [],
            "fact_types": sorted(rec.get("shadow_fact_types") or []),
        })
    return cases, recorded


def corpus_b():
    payload = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    cases, recorded = [], []
    for rec in payload["records"]:
        cases.append((rec.get("name"), rec["code"], None))
        recorded.append({
            "techniques": sorted(rec.get("detected_techniques") or []),
            "strategies": sorted(rec.get("detected_strategies") or []),
            "fact_types": sorted(rec.get("fact_types") or []),
        })
    return cases, recorded


def main() -> int:
    pre_run, removed_lines = reconstruct_pre_b2_runner()
    post_run = shadow_runner.run_shadow_analysis

    cases_a, recorded_a = corpus_a()
    cases_b, recorded_b = corpus_b()

    corpus_a_result = compare_corpus(pre_run, post_run, cases_a)
    corpus_b_result = compare_corpus(pre_run, post_run, cases_b)
    corpus_a_result["drift_vs_recorded_artifact"] = drift_vs_recorded(
        pre_run, post_run, cases_a, recorded_a
    )
    corpus_b_result["drift_vs_recorded_artifact"] = drift_vs_recorded(
        pre_run, post_run, cases_b, recorded_b
    )

    payload = {
        "batch": "B2",
        "instrumentation": "tri-state per-concept evidence (shadow path only)",
        "pre_b2_reconstruction": {
            "source": str(RUNNER_PATH.relative_to(ROOT)),
            "removed_line_count": len(removed_lines),
            "removed_lines": removed_lines,
        },
        "corpus_a_46_real_submissions": corpus_a_result,
        "corpus_b_301_disjoint_cases": corpus_b_result,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("=" * 72)
    print("pre-B2 reconstruction: removed", len(removed_lines), "lines")
    for line in removed_lines:
        print("   -", line)
    for name, result in (
        ("corpus_a_46_real_submissions", corpus_a_result),
        ("corpus_b_301_disjoint_cases", corpus_b_result),
    ):
        print("=" * 72)
        print(name, f"({result['cases']} cases)")
        print("  outcome before:", result["before_outcome_counts"])
        print("  outcome after :", result["after_outcome_counts"])
        print("  outcome_changed:", result["outcome_changed"])
        print("  deterministic-field mismatches:", result["mismatch_count"])
        print("  excluded (non-deterministic):", result["excluded_nondeterministic_keys"])
        print("  B2 instrumentation cost (ms):", result["instrumentation_cost_ms"])
        print("  cases missing evidence_state:", result["cases_missing_evidence_state"])
        print("  tri-state totals:", result["tri_state_totals"])
        drift = result["drift_vs_recorded_artifact"]
        print("  drift vs recorded artifact -> pre:", drift["pre_b2_drift_fields"],
              "post:", drift["post_b2_drift_fields"],
              "identical:", drift["drift_identical_in_both_arms"],
              "b2-attributable:", drift["b2_attributable_drift"])
        for m in result["field_mismatches"][:5]:
            print("   !", m)
    print("=" * 72)
    print("written:", OUT_PATH.relative_to(ROOT))

    clean = (
        corpus_a_result["mismatch_count"] == 0
        and corpus_b_result["mismatch_count"] == 0
        and not corpus_a_result["drift_vs_recorded_artifact"]["b2_attributable_drift"]
        and not corpus_b_result["drift_vs_recorded_artifact"]["b2_attributable_drift"]
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
