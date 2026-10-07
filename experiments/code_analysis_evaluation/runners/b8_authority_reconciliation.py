"""Batch B8: Ground-Truth authority reconciliation (provenance-first).

Pipeline (per the B8 brief):

    live DB → B8 extraction → reconciliation artifact → explicit decision
        → versioned GT update

Steps:

1. read the STORED problem_ground_truth rows for every conflicted problem;
2. build one :class:`AuthorityConflict` record per conflicted group, carrying
   the stored row's own tier/provenance/validation_status (the explicit
   provenance) alongside the loader-emitted values;
3. classify each conflict individually (no bulk rule beyond the documented
   collision mechanism);
4. write ``results/b8_authority_reconciliation_candidates.json``;
5. apply only explicitly-resolved changes as **versioned GT updates** to the
   live stored rows (bumped version + reconciliation provenance marker +
   reconciled_from record); NEEDS_HUMAN_REVIEW rows are written to the report
   and left fail-closed in the DB;
6. regenerate the native 46 corpus (provenance NATIVE, no enrichment);
7. re-run the B7 parity measurement and record before/after.

ELO/gap/recommendation engines are never invoked. The B6 flag stays OFF.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/b8_authority_reconciliation.py
"""
import collections
import copy
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import List

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis import authority_vocabulary as vocab  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402
from pathforge.services import authority_reconciliation as rec  # noqa: E402
from pathforge.services import product_eligibility as b6  # noqa: E402
from pathforge.services.ground_truth_builder import (  # noqa: E402
    mark_family_relations, serialize_solution_groups,
)
from pathforge.services.problem_resolver import _load_ground_truth  # noqa: E402

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
NATIVE_PATH = RESULTS / "db_batch3" / "submission_eval_results_NATIVE.json"
HISTORICAL = RESULTS / "db_batch3" / "submission_eval_results.json"
CANDIDATES_PATH = RESULTS / "b8_authority_reconciliation_candidates.json"
B7_PATH = RESULTS / "b7_parity_measurement.json"
B7_AFTER_PATH = RESULTS / "b7_parity_measurement_after_b8.json"


# ============================================================================
# Live-DB extraction
# ============================================================================

def _fetch_stored_rows(problem_ids):
    import config  # noqa: F401
    from pathforge.db.db import get_connection

    conn = get_connection()
    try:
        conn.execute(
            "SELECT problem_id, validation_status, solution_groups "
            "FROM problem_ground_truth WHERE problem_id = ANY(%s) ORDER BY problem_id",
            (sorted(problem_ids),),
        )
        rows = {r["problem_id"]: r for r in conn.fetchall()}
        conn.execute(
            "SELECT id, pattern FROM problems WHERE id = ANY(%s)",
            (sorted(problem_ids),),
        )
        csv = {r["id"]: r["pattern"] for r in conn.fetchall()}
        return rows, csv
    finally:
        conn.close()


def _parse_groups(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return None
    return raw if isinstance(raw, list) else None


def extract_conflicts(native_payload):
    """One conflict record per conflicted group, with stored-row provenance."""
    problem_ids = sorted({rec["problem_id"] for rec in native_payload["records"]
                          if rec.get("problem_id")})
    stored_rows, csv_patterns = _fetch_stored_rows(problem_ids)

    conflicts = []
    for rec_ in native_payload["records"]:
        problem_id = rec_.get("problem_id")
        row = stored_rows.get(problem_id) or {}
        stored_groups = _parse_groups(row.get("solution_groups")) or []
        stored_by_id = {g.get("id"): g for g in stored_groups if isinstance(g, dict)}
        csv_pattern = csv_patterns.get(problem_id)

        for group in rec_["groups"]:
            normalization = group.get("authority_normalization") or {}
            if normalization.get("diagnostic") != vocab.AUTHORITY_CONFLICT:
                continue
            # stored rows may carry the base id while emitted ids gained
            # _altN suffixes
            base_id = str(group.get("id") or "").split("_alt")[0]
            stored_group = stored_by_id.get(str(group.get("id"))) \
                or stored_by_id.get(base_id) or {}
            conflict = rec.conflict_from_group(
                group, problem_id,
                stored_authority_tier=stored_group.get("authority_tier"),
                stored_provenance=stored_group.get("provenance") or [],
                stored_validation_status=row.get("validation_status"),
                csv_pattern=csv_pattern,
            )
            conflicts.append(rec.classify_conflict(conflict))
    return conflicts


# ============================================================================
# Versioned GT update (stored rows only)
# ============================================================================

def apply_to_stored_rows(conflicts) -> List[dict]:
    """Apply explicitly-resolved authorities to the STORED GT rows, versioned."""
    import config  # noqa: F401
    from pathforge.db.db import get_connection

    resolved = [c for c in conflicts
                if c.reconciliation_status in rec.RESOLVED_STATUSES]
    if not resolved:
        print("no explicitly resolved conflicts; stored rows untouched")
        return []

    by_problem = collections.defaultdict(list)
    for c in resolved:
        by_problem[c.problem_id].append(c)

    now = datetime.now(timezone.utc).isoformat()
    changes = []
    conn = get_connection()
    try:
        for problem_id, problem_conflicts in sorted(by_problem.items()):
            conn.execute(
                "SELECT validation_status, solution_groups FROM problem_ground_truth "
                "WHERE problem_id = %s",
                (problem_id,),
            )
            row = conn.fetchone()
            if not row:
                continue
            groups = _parse_groups(row["solution_groups"]) or []
            updated = copy.deepcopy(groups)
            row_changes = []
            for group in updated:
                if not isinstance(group, dict):
                    continue
                for c in problem_conflicts:
                    if str(group.get("id")) == c.group_id:
                        change = rec.apply_resolution(
                            group, c.reconciliation_status)
                        if change:
                            change["problem_id"] = problem_id
                            change["reconciliation_status"] = \
                                c.reconciliation_status
                            row_changes.append(change)
            if not row_changes:
                continue
            conn.execute(
                """
                UPDATE problem_ground_truth SET
                    solution_groups = %s,
                    updated_at = COALESCE(updated_at, %s)
                WHERE problem_id = %s
                """,
                (json.dumps(updated), now, problem_id),
            )
            changes.extend(row_changes)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return changes


# ============================================================================
# Native corpus regeneration (post-reconciliation)
# ============================================================================

def regenerate_native_corpus():
    spec_path = (ROOT / "experiments" / "code_analysis_evaluation" / "runners" /
                 "b6_5_authority_normalization_measure.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("b6_5_measure", spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # force regeneration (do not reuse the pre-reconciliation cache)
    if NATIVE_PATH.exists():
        NATIVE_PATH.unlink()
    return module._ensure_native_corpus()


# ============================================================================
# B7 before/after
# ============================================================================

def run_b7_after():
    spec_path = (ROOT / "experiments" / "code_analysis_evaluation" / "runners" /
                 "b7_parity_measure.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("b7_measure", spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # run its main() but capture the returned payload from the file
    module.main()
    return json.loads(B7_PATH.read_text(encoding="utf-8"))


def main() -> int:
    if not NATIVE_PATH.exists():
        raise SystemExit("native corpus missing; run the B6.5 runner first")
    native_before = json.loads(NATIVE_PATH.read_text(encoding="utf-8"))
    b7_before = (json.loads(B7_PATH.read_text(encoding="utf-8"))
                 if B7_PATH.exists() else {})

    print("1) extracting conflicts from the live DB...")
    conflicts = extract_conflicts(native_before)
    print(f"   {len(conflicts)} group-level conflicts found")

    status_counts = collections.Counter(c.reconciliation_status
                                        for c in conflicts)
    print("   classification:", dict(status_counts))

    # -- 2) candidates artifact (BEFORE any modification) --------------------
    by_problem = collections.defaultdict(list)
    for c in conflicts:
        by_problem[c.problem_id].append(c)

    human_review = [rec.review_record(c) for c in conflicts
                    if c.reconciliation_status == rec.NEEDS_HUMAN_REVIEW]

    # Do not clobber a pre-reconciliation inventory when re-running after the
    # GT updates have been applied — the before-state is migration evidence.
    if CANDIDATES_PATH.exists():
        existing = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        if existing.get("summary", {}).get("total_conflicts", 0) \
                >= len(conflicts):
            print("   candidates report already present — preserving it")
            candidates = existing

    candidates = {
        "batch": "B8",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_semantics": {
            "authority_tier": rec.AUTHORITY_TIER_SEMANTICS,
            "evidence": rec.EVIDENCE_SEMANTICS,
        },
        "summary": {
            "total_conflicts": len(conflicts),
            "by_status": dict(status_counts),
            "conflicted_problems": sorted(by_problem),
        },
        "conflicts": [c.to_dict() for c in conflicts],
        "human_review_records": human_review,
    }
    CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    print("   candidates written:", CANDIDATES_PATH.relative_to(ROOT))

    # -- 3) apply versioned GT updates for explicitly-resolved rows ----------
    print("2) applying versioned GT updates...")
    changes = apply_to_stored_rows(conflicts)
    print(f"   {len(changes)} stored group(s) updated (versioned)")

    # -- 4) regenerate native corpus ----------------------------------------
    print("3) regenerating the native corpus...")
    native_after = regenerate_native_corpus()
    conflicts_after = native_after.get("normalization_conflict_count")
    print(f"   native conflicts after reconciliation: {conflicts_after}")

    # -- 5) re-run B7 --------------------------------------------------------
    print("4) re-running the B7 parity measurement...")
    b7_after = run_b7_after()

    def _cats(payload, key):
        return (payload.get(key) or {}).get("parity_categories") or {}

    comparison = {
        "b7_native_parity_before": _cats(b7_before, "native_46"),
        "b7_native_parity_after": _cats(b7_after, "native_46"),
        "b7_native_b6_eligible_before":
            (b7_before.get("native_46") or {}).get("b6_eligible"),
        "b7_native_b6_eligible_after":
            (b7_after.get("native_46") or {}).get("b6_eligible"),
    }

    # -- 6) B6 eligibility after (measurement only; flag untouched) ---------
    eligible_after = blocked_after = 0
    for rec_ in native_after["records"]:
        result = shadow_runner.run_shadow_analysis(
            rec_["source_code"], solution_groups=rec_["groups"] or None)
        authority_dict = (result or {}).get("authority")
        authority_report = (b6._report_from_dict(authority_dict)
                            if authority_dict is not None else None)
        if b6.product_eligibility(authority_report).eligible:
            eligible_after += 1
        else:
            blocked_after += 1

    payload = {
        "batch": "B8",
        "summary": candidates["summary"],
        "gt_changes_applied": changes,
        "native_conflict_count_before": native_before.get(
            "normalization_conflict_count"),
        "native_conflict_count_after": conflicts_after,
        "b7_before_after": comparison,
        "b6_eligibility": {
            "before (B7 native)": comparison["b7_native_b6_eligible_before"],
            "after": eligible_after,
            "blocked_after": blocked_after,
            "measurement_only": True,
            "flag": b6.flag_state(),
        },
        "human_approved_corpus": {
            "note": "computed from the regenerated native corpus",
        },
    }
    OUT = RESULTS / "b8_reconciliation_result.json"
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("5) result written:", OUT.relative_to(ROOT))

    print("=" * 72)
    print("statuses:", dict(status_counts))
    print("GT changes applied:", len(changes))
    print("native conflicts before/after:",
          native_before.get("normalization_conflict_count"), "/", conflicts_after)
    print("B7 native P7 before/after:",
          comparison["b7_native_parity_before"].get("P7_AUTHORITY_CONFLICT"),
          "/", comparison["b7_native_parity_after"].get("P7_AUTHORITY_CONFLICT"))
    print("B6 eligible before/after:",
          comparison["b7_native_b6_eligible_before"], "/", eligible_after)
    print("flag:", b6.flag_state(), "| enabled:", b6.flag_enabled())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
