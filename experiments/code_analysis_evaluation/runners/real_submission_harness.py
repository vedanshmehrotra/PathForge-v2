"""Submission-level evaluation harness for real (non-templated) submissions.

Purpose
-------
Process NEW accepted submissions through the PathForge pipeline without manual
copy/paste, dedupe them by content hash, and group failures by likely root
cause so that fixes are judged on many implementations instead of a handful.

It is deliberately NOT a crawler. Submissions are supplied by the user
(browser-collected export, JSON file or directory of JSON files) because no
browser-automation dependency is available in this environment.

Input format (list of objects, or {"submissions": [...]})
---------------------------------------------------------
[
  {
    "problem_id": 21,                        # required
    "expected_patterns": ["two_pointers_same"],  # legacy pattern IDs from the UI
    "code": "class Solution: ...",           # required
    "language": "python",                    # optional, default python
    "title": "Merge Two Sorted Lists",       # optional
    "submission_id": "lc-21-abc",            # optional external identity
    "submitted_at": "2026-09-01T10:00:00Z"   # optional
  }
]

Usage
-----
    python -m experiments.code_analysis_evaluation.runners.real_submission_harness \
        --input path/to/new_submissions.json

    # re-run everything, ignoring the registry
    ... --force

    # smoke test a running instance instead of the in-process pipeline
    ... --endpoint http://localhost:8000 --token "$PATHFORGE_JWT"

Outputs
-------
    results/submission_eval_results.json    machine-readable, per submission
    results/SUBMISSION_EVAL_REPORT.md       human-readable, grouped by root cause
    results/submission_registry.json        fingerprints already analysed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from pathforge.api.services.analysis import run_analysis
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.data_structures import StructuralFact
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.services.ground_truth_builder import (
    PATTERN_TO_V1_MAPPING, find_ground_truth_disagreements,
)
from pathforge.services.problem_resolver import _split_csv_patterns_to_groups
from pathforge.ast_engine.patterns import ALL_PATTERNS
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies

import ast as _ast

DEFAULT_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
DEFAULT_REGISTRY = os.path.join(DEFAULT_OUT_DIR, "submission_registry.json")


# ----------------------------------------------------------------------
# Fingerprinting
# ----------------------------------------------------------------------

def normalize_code(code: str) -> str:
    """Normalize line endings, trailing whitespace and blank lines."""
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in code.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def fingerprint(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------
# Loading submissions
# ----------------------------------------------------------------------

def load_submissions(path: str) -> list[dict]:
    if os.path.isdir(path):
        items: list[dict] = []
        for name in sorted(os.listdir(path)):
            if name.endswith(".json"):
                items.extend(load_submissions(os.path.join(path, name)))
        return items

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("submissions", [])
    return [d for d in data if isinstance(d, dict) and d.get("code")]


# ----------------------------------------------------------------------
# Pipeline execution
# ----------------------------------------------------------------------

def allowed_concepts_for(expected_patterns: list[str]) -> set:
    """V1 concepts the expected legacy patterns may legitimately produce."""
    allowed = set()
    for pattern in expected_patterns:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping:
            allowed.update(mapping.get("required", []))
    return allowed


def build_groups(expected_patterns: list[str]) -> list[dict]:
    """Same group construction the production loader uses for curated patterns."""
    if not expected_patterns:
        return []
    return _split_csv_patterns_to_groups(expected_patterns, {}, 1.0, "llm_proposed")


def load_groups_from_db(problem_id: int | None) -> list[dict]:
    """Load the groups the running application actually uses for a problem.

    This is the honest production view: stored solution_groups (with their
    V1 required/optional/excluded and authority tier) when present, and
    nothing at all when the problem has no ground-truth row.
    """
    if not problem_id:
        return []
    try:
        import config  # noqa: F401  (loads .env)
        from pathforge.db.db import get_connection
        from pathforge.services.problem_resolver import _load_ground_truth

        conn = get_connection()
        try:
            groups, _confidence = _load_ground_truth(conn, problem_id)
            return groups
        finally:
            conn.close()
    except Exception:
        return []


def run_in_process(code: str, groups: list[dict]) -> dict:
    t0 = time.perf_counter()
    production = run_analysis(code, "python", accepted_solution_groups=groups or None)
    shadow = run_shadow_analysis(code, solution_groups=groups or None)
    return {
        "production": production,
        "shadow": shadow,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def run_endpoint(code: str, groups: list[dict], endpoint: str, token: str,
                 problem_id: int | None) -> dict:
    import httpx

    payload = {
        "user_id": int(os.environ.get("PATHFORGE_EVAL_USER_ID", "1")),
        "code": code,
        "language": "python",
        "problem": {"leetcode_id": problem_id} if problem_id else None,
    }
    resp = httpx.post(
        endpoint.rstrip("/") + "/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    return {
        "production": {"ast": body.get("ast", {}), "match_result": body.get("match_result", {})},
        "shadow": body.get("shadow_analysis"),
        "elapsed_ms": 0.0,
    }


# ----------------------------------------------------------------------
# Root-cause classification (derived from the architectural survey)
# ----------------------------------------------------------------------

def classify(sub: dict, result: dict, groups: list[dict],
             gt_findings: list | None = None) -> list[str]:
    causes: list[str] = []
    production = result.get("production") or {}
    shadow = result.get("shadow") or {}
    expected = sub.get("expected_patterns") or []

    ast_out = production.get("ast", {}) or {}
    detections = ast_out.get("detected_patterns", []) or []
    detected_ids = [
        d.get("pattern_id", d.get("name", ""))
        for d in detections
        if isinstance(d, dict) and d.get("detected", True)
    ]

    # --- Ground truth / vocabulary layer ---
    unmapped = [p for p in expected if p not in PATTERN_TO_V1_MAPPING]
    if unmapped:
        causes.append("ground_truth_pattern_unmapped")

    ast_off_taxonomy = [p for p in detected_ids if p and p not in ALL_PATTERNS]
    if ast_off_taxonomy:
        causes.append("legacy_ast_vocabulary_mismatch")

    if not groups:
        causes.append("no_ground_truth_groups")
        return causes

    # Ground-truth health. Reported by the PRODUCTION consistency check so the
    # harness measures the real code path rather than re-implementing it.
    if gt_findings is None:
        gt_findings = find_ground_truth_disagreements(expected, groups)

    if any(f["kind"] == "unmatchable_group" for f in gt_findings):
        # Batch 2A: an unsatisfiable group is now explicitly flagged and its
        # missing vocabulary named, instead of looking like a normal group.
        causes.append("gt_missing_vocabulary_exposed")
        causes.append("group_unsatisfiable_empty_required")
    unmatchable_ids = (shadow.get("match_outcome") or {}).get("unmatchable_group_ids") or []
    if unmatchable_ids:
        causes.append("group_unmatchable_empty_required")

    if any(f["kind"] in ("pattern_not_in_groups", "group_pattern_not_declared")
           for f in gt_findings):
        causes.append("patterns_vs_groups_drift")

    if any(f["kind"] == "concept_not_derived_from_patterns" for f in gt_findings):
        causes.append("concept_not_derived_from_patterns")

    # --- Structural layer ---
    fact_types = set()
    if shadow:
        fact_types = {f["fact_type"] for f in shadow.get("structural_facts", [])}
    elif production:
        try:
            fact_types = {f.fact_type for f in extract_structural_facts(_ast.parse(sub["code"]))}
        except Exception:
            fact_types = set()

    required_concepts = {c for g in groups for c in g.get("required", [])}
    techniques = set()
    strategies = set()
    outcome = "UNKNOWN"
    if shadow:
        techniques = {t["technique_id"] for t in shadow.get("technique_evidence", [])}
        strategies = {s["strategy_id"] for s in shadow.get("strategy_evidence", [])}
        outcome = (shadow.get("match_outcome") or {}).get("outcome", "UNKNOWN")

    # sequential_accumulation now fires for either while_loop_comparison or
    # for_loop_iteration, but always requires accumulator_update.
    if "sequential_accumulation" in required_concepts:
        has_acc_update = "accumulator_update" in fact_types
        has_loop = "while_loop_comparison" in fact_types or "for_loop_iteration" in fact_types
        if not has_acc_update:
            causes.append("required_accumulation_needs_acc_update")
        elif not has_loop:
            causes.append("required_accumulation_needs_loop")

    if "bidirectional_index_scan" in required_concepts and "opposite_direction_updates" not in fact_types:
        causes.append("required_bidirectional_scan_needs_opposite_updates")

    missing_required = sorted(c for c in required_concepts if c not in techniques and c not in strategies)
    if missing_required and outcome != "CONFIRMED":
        causes.append("required_concept_not_detected")

    if required_concepts and not strategies and not techniques:
        causes.append("no_technique_evidence")

    # --- Strategy inference layer ---
    if "sliding_window" in strategies and not (
        {"subscript_index_access", "window_size_constant"} & fact_types
    ):
        causes.append("generic_loop_state_promoted_to_sliding_window")

    # --- Outcome layer ---
    #
    # Solution groups are ALTERNATIVES, not a conjunction: satisfying one group
    # is the intended success condition. So expected-vs-detected comparisons use
    # the union of concepts the expected patterns can legitimately produce
    # (the "allowed" set), never the union of every group's requirements.
    allowed = set()
    for pattern in expected:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping:
            allowed.update(mapping.get("required", []))

    if outcome == "CONFIRMED":
        if allowed and not (allowed & (techniques | strategies)):
            causes.append("false_confirmation_label_mismatch")
            extra_strategies = sorted(strategies)
            if extra_strategies:
                causes.append("confirmed_on_unexpected_strategy")
        else:
            if allowed and (strategies - allowed):
                causes.append("extra_strategy_inferred")
            if not causes:
                causes.append("ok_confirmed")
    elif outcome == "UNRESOLVED":
        if allowed and (strategies - allowed):
            causes.append("wrong_strategy_inferred")
        if not any(c.startswith(("ground_truth", "group_unsatisfiable", "required_",
                                 "no_technique", "legacy_ast", "false_", "generic_",
                                 "no_ground_truth", "wrong_strategy")) for c in causes):
            causes.append("unresolved_insufficient_evidence")
    elif outcome == "CONTRADICTED":
        causes.append("contradicted")

    return causes


_KNOWN_STRATEGIES = {
    "binary_search", "sliding_window", "two_pointers_opposite", "dfs_backtracking",
    "dp_top_down", "dp_bottom_up", "bfs_shortest_path", "union_find",
    "monotonic_stack_strategy",
}


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------

def load_registry(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_registry(path: str, registry: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Submission-level PathForge evaluation harness")
    ap.add_argument("--input", required=True, help="JSON file or directory of JSON files")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--force", action="store_true", help="re-analyse submissions already in the registry")
    ap.add_argument("--endpoint", default=None, help="optional live /analyze endpoint")
    ap.add_argument("--token", default=os.environ.get("PATHFORGE_EVAL_TOKEN", ""))
    ap.add_argument("--groups-from-db", action="store_true",
                    help="use the live ground-truth groups for each problem_id "
                         "(falls back to expected_patterns when absent)")
    args = ap.parse_args()

    submissions = load_submissions(args.input)
    registry = load_registry(args.registry)

    records = []
    skipped = 0
    for sub in submissions:
        code = sub["code"]
        fp = fingerprint(code)
        if fp in registry and not args.force:
            skipped += 1
            continue

        groups = []
        group_source = "expected_patterns"
        if args.groups_from_db:
            groups = load_groups_from_db(sub.get("problem_id"))
            group_source = "live_db" if groups else "expected_patterns"
        if not groups:
            groups = build_groups(sub.get("expected_patterns") or [])
        try:
            if args.endpoint:
                result = run_endpoint(code, groups, args.endpoint, args.token,
                                      sub.get("problem_id"))
            else:
                result = run_in_process(code, groups)
        except Exception as exc:  # never let one submission kill the batch
            result = {"production": {}, "shadow": None, "elapsed_ms": 0.0,
                      "error": f"{type(exc).__name__}: {exc}"}

        gt_findings = find_ground_truth_disagreements(
            sub.get("expected_patterns") or [], groups
        )
        causes = classify(sub, result, groups, gt_findings)
        shadow = result.get("shadow") or {}
        match_outcome = shadow.get("match_outcome") or {}
        production = result.get("production") or {}

        record = {
            "fingerprint": fp,
            "external_submission_id": sub.get("submission_id"),
            "problem_id": sub.get("problem_id"),
            "title": sub.get("title"),
            "expected_patterns": sub.get("expected_patterns") or [],
            "group_source": group_source,
            "gt_findings": gt_findings,
            "expected_allowed_concepts": sorted(allowed_concepts_for(sub.get("expected_patterns") or [])),
            "groups": [
                {"id": g["id"], "required": g.get("required"),
                 "optional": g.get("optional"), "excluded": g.get("excluded"),
                 "patterns": g.get("patterns"),
                 "derivation_patterns": g.get("derivation_patterns"),
                 "matchable": g.get("matchable")}
                for g in groups
            ],
            "source_code": code,
            "error": result.get("error"),
            # production path
            "production_detected_patterns": [
                d.get("pattern_id", d.get("name", ""))
                for d in (production.get("ast", {}) or {}).get("detected_patterns", [])
                if isinstance(d, dict) and d.get("detected", True)
            ],
            "production_match_result": (production.get("match_result") or {}).get("match_result"),
            "production_confidence_score": (production.get("match_result") or {}).get("confidence_score"),
            "production_unmatched_patterns": (production.get("match_result") or {}).get("unmatched_patterns"),
            # shadow path
            "shadow_outcome": match_outcome.get("outcome"),
            "shadow_authority_tier": match_outcome.get("authority_tier"),
            "shadow_primary_strategy": match_outcome.get("primary_strategy"),
            "shadow_satisfied_group_ids": match_outcome.get("satisfied_group_ids"),
            "shadow_unmatchable_group_ids": match_outcome.get("unmatchable_group_ids") or [],
            "shadow_reasoning": match_outcome.get("reasoning"),
            "shadow_strategies": shadow.get("strategy_evidence", []),
            "shadow_techniques": shadow.get("technique_evidence", []),
            "shadow_fact_count": len(shadow.get("structural_facts", [])),
            "shadow_fact_types": sorted({f["fact_type"] for f in shadow.get("structural_facts", [])}),
            "analysed_at": datetime.now(timezone.utc).isoformat(),
            "root_causes": causes,
        }
        records.append(record)
        registry[fp] = {
            "problem_id": sub.get("problem_id"),
            "outcome": record["shadow_outcome"],
            "root_causes": causes,
            "analysed_at": record["analysed_at"],
        }

    if not records:
        print(f"nothing new to analyse ({skipped} submission(s) already in registry)")
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    results_path = os.path.join(args.out_dir, "submission_eval_results.json")
    report_path = os.path.join(args.out_dir, "SUBMISSION_EVAL_REPORT.md")

    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "analysed": len(records), "skipped_already_seen": skipped,
                   "records": records}, fh, indent=2)
    save_registry(args.registry, registry)
    write_report(report_path, records, skipped, registry)

    print(f"analysed {len(records)} new submission(s); skipped {skipped} already in registry")
    print(f"  {results_path}")
    print(f"  {report_path}")

    _print_console_summary(records)
    return 0


def write_report(path: str, records: list[dict], skipped: int, registry: dict) -> None:
    by_cause = defaultdict(list)
    for rec in records:
        for cause in rec["root_causes"] or ["unclassified"]:
            by_cause[cause].append(rec)

    outcome_counts = Counter(r["shadow_outcome"] for r in records)

    lines = [
        "# Real-submission evaluation report",
        "",
        f"- generated: {datetime.now(timezone.utc).isoformat()}",
        f"- new submissions analysed: **{len(records)}**",
        f"- skipped (already in registry): **{skipped}**",
        f"- registry size: **{len(registry)}**",
        f"- shadow outcomes: {dict(outcome_counts)}",
        "",
        "## Failures grouped by likely root cause",
        "",
    ]
    for cause, recs in sorted(by_cause.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"### {cause}  —  {len(recs)} submission(s)")
        lines.append("")
        lines.append("| problem | expected | outcome | strategies | techniques |")
        lines.append("|---|---|---|---|---|")
        for r in recs[:20]:
            lines.append(
                f"| {r['problem_id']} | {','.join(r['expected_patterns']) or '—'} | "
                f"{r['shadow_outcome']} | "
                f"{','.join(s['strategy_id'] for s in r['shadow_strategies']) or '—'} | "
                f"{','.join(t['technique_id'] for t in r['shadow_techniques']) or '—'} |"
            )
        if len(recs) > 20:
            lines.append(f"\n_(+{len(recs) - 20} more)_")
        lines.append("")

    lines.append("## Per-submission detail")
    lines.append("")
    for r in records:
        lines.append(f"### problem {r['problem_id']} ({r['fingerprint'][:12]})")
        lines.append("")
        lines.append(f"- expected: `{r['expected_patterns']}` (groups from `{r.get('group_source', 'n/a')}`)")
        lines.append(f"- groups: `{[g['required'] for g in r['groups']]}`")
        if r.get("shadow_unmatchable_group_ids"):
            lines.append(f"- unmatchable groups: `{r['shadow_unmatchable_group_ids']}`")
        lines.append(f"- production: `{r['production_match_result']}` "
                     f"(detected {r['production_detected_patterns']})")
        lines.append(f"- shadow: `{r['shadow_outcome']}` satisfaction reasoning:")
        for reason in (r["shadow_reasoning"] or []):
            lines.append(f"    - {reason}")
        lines.append(f"- root causes: `{r['root_causes']}`")
        lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _print_console_summary(records: list[dict]) -> None:
    if not records:
        print("nothing new to analyse")
        return
    print()
    print(f"{'=' * 70}")
    print("  SUBMISSION EVAL SUMMARY")
    print(f"{'=' * 70}")
    outcomes = Counter(r["shadow_outcome"] for r in records)
    for outcome, count in outcomes.most_common():
        print(f"  {outcome:14} {count}")
    print()
    causes = Counter(c for r in records for c in (r["root_causes"] or ["unclassified"]))
    for cause, count in causes.most_common():
        print(f"  {count:3d}  {cause}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    raise SystemExit(main())
