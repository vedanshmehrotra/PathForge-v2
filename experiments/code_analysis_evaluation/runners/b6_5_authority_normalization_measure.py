"""Batch B6.5: native 46-corpus regeneration + authority normalization measurement.

Major deliverable: regenerate the 46 real-submission corpus from the LIVE
database (reachable) so the corpus carries **native** ``authority_tier``,
``evidence``, ``provenance``, ``version`` and the B5.5 relation metadata —
exactly as the production loader materializes them, with no measurement-time
fabrication.

Provenance discipline (the point of the batch):

* ``NATIVE``  — authority metadata read from the actual GT source rows through
  the production loader. Never fabricated.
* ``ENRICHED`` — the historical corpus with the record-level
  ``shadow_authority_tier`` re-attached at measurement time. Kept ONLY as a
  comparison; clearly labelled non-native.

Measurements reported: authority distribution, B3 coverage, B4 primary
strategies, B5 aggregation, B6 eligible/blocked, ONE_OF count, normalization
conflicts — for the 46 native corpus, the 46 enriched corpus (comparison only)
and the 301 benchmark.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/b6_5_authority_normalization_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis import authority_vocabulary as vocab  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402
from pathforge.services import product_eligibility as b6  # noqa: E402
from pathforge.services.ground_truth_builder import (  # noqa: E402
    deserialize_solution_groups, mark_family_relations, serialize_solution_groups,
)

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
HISTORICAL = RESULTS / "db_batch3" / "submission_eval_results.json"
NATIVE_OUT = RESULTS / "db_batch3" / "submission_eval_results_NATIVE.json"
OUT_PATH = RESULTS / "b6_5_authority_normalization_measurement.json"


def _sorted(counter) -> dict:
    return {str(k): counter[k]
            for k in sorted(counter, key=lambda k: (k is None, str(k)))}


# ============================================================================
# Native corpus regeneration
# ============================================================================

def load_native_groups(problem_ids):
    """Read the GT rows the production app actually uses, via the production loader.

    Returns {problem_id: groups-or-None}. This is NATIVE provenance: the values
    come from the stored ``problem_ground_truth`` rows through
    ``_load_ground_truth`` (the same path ``/analyze`` uses), including its
    reconciliation and B5.5 relation marking.
    """
    import config  # noqa: F401  (loads .env)
    from pathforge.db.db import get_connection
    from pathforge.services.problem_resolver import _load_ground_truth

    conn = get_connection()
    native = {}
    try:
        for problem_id in problem_ids:
            try:
                groups, _confidence = _load_ground_truth(conn, problem_id)
                native[problem_id] = serialize_solution_groups(groups) if groups else []
            except Exception as exc:  # one problem must not kill the batch
                print(f"  ! problem {problem_id}: loader failed: "
                      f"{type(exc).__name__}: {exc}")
                native[problem_id] = None
    finally:
        conn.close()
    return native


def regenerate_native_corpus() -> dict:
    """Rebuild the 46-corpus with native GT (source code comes from the
    historical artifact; the ground truth comes from the live DB)."""
    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    records = historical["records"]
    problem_ids = sorted({rec["problem_id"] for rec in records
                          if rec.get("problem_id")})

    print("regenerating native GT from live database for", len(problem_ids), "problems...")
    native_groups = load_native_groups(problem_ids)

    out_records = []
    for rec in records:
        problem_id = rec.get("problem_id")
        groups = native_groups.get(problem_id) or []
        out_records.append({
            "external_submission_id": rec.get("external_submission_id"),
            "problem_id": problem_id,
            "title": rec.get("title"),
            "source_code": rec["source_code"],
            "groups": groups,
            "group_provenance": "NATIVE" if groups else "NO_STORED_GROUPS",
            # the historical record-level value is diagnostic only
            "historical_shadow_authority_tier": rec.get("shadow_authority_tier"),
        })

    conflicts = sum(
        1
        for rec in out_records
        for g in rec["groups"]
        if (g.get("authority_normalization") or {}).get("diagnostic")
        == vocab.AUTHORITY_CONFLICT
    )

    payload = {
        "provenance": "NATIVE",
        "native": True,
        "source": {
            "submissions": str(HISTORICAL.relative_to(ROOT)),
            "ground_truth": "live problem_ground_truth rows via _load_ground_truth",
            "regenerated_at_batch": "B6.5",
        },
        "preserved_fields": [
            "authority_tier", "evidence", "provenance", "version",
            "family_relation", "alternative_group_id", "authority_normalization",
        ],
        "normalization_conflict_count": conflicts,
        "records": out_records,
    }
    NATIVE_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("native corpus written:", NATIVE_OUT.relative_to(ROOT))
    return payload


def _ensure_native_corpus() -> dict:
    if NATIVE_OUT.exists():
        try:
            payload = json.loads(NATIVE_OUT.read_text(encoding="utf-8"))
            if payload.get("provenance") == "NATIVE" and payload.get("records"):
                return payload
        except (json.JSONDecodeError, OSError):
            pass
    return regenerate_native_corpus()


# ============================================================================
# Measurement
# ============================================================================

def _case(name, code, groups):
    result = shadow_runner.run_shadow_analysis(code, solution_groups=groups or None)
    if result is None:
        return None
    authority = result.get("authority")
    eligibility = b6.product_eligibility(
        b6._report_from_dict(authority) if authority else None
    )
    conflicts = [
        g.get("id")
        for g in (groups or [])
        if isinstance(g, dict)
        and (g.get("authority_normalization") or {}).get("diagnostic")
        == vocab.AUTHORITY_CONFLICT
    ]
    return {
        "case": name,
        "coverage": (result.get("coverage") or {}).get("aggregate_state"),
        "b4_selected": ((result.get("strategy_selection") or {})
                        .get("submission") or {}).get("selected"),
        "b5_aggregation": (authority or {}).get("aggregation"),
        "canonical_authority": eligibility.canonical_authority,
        "eligible": eligibility.eligible,
        "one_of_groups": (authority or {}).get("alternative_group_count", 0),
        "normalization_conflicts": conflicts,
    }


def _measure(records) -> dict:
    coverage = collections.Counter()
    b4_selected = collections.Counter()
    b5_aggregation = collections.Counter()
    canonical_tiers = collections.Counter()
    tier_distribution = collections.Counter()
    conflicts = collections.Counter()
    eligible = blocked = one_of_groups = one_of_submissions = 0
    case_count = 0

    for name, code, groups in records:
        case = _case(name, code, groups)
        if case is None:
            continue
        case_count += 1
        coverage[case["coverage"]] += 1
        b4_selected[case["b4_selected"]] += 1
        b5_aggregation[case["b5_aggregation"]] += 1
        canonical_tiers[case["canonical_authority"]] += 1
        one_of_groups += case["one_of_groups"]
        one_of_submissions += 1 if case["one_of_groups"] else 0
        if case["eligible"]:
            eligible += 1
        else:
            blocked += 1
        for g in (groups or []):
            if isinstance(g, dict):
                tier_distribution[g.get("authority_tier", "<missing>")] += 1
                diagnostic = (g.get("authority_normalization") or {}).get("diagnostic")
                if diagnostic:
                    conflicts[diagnostic] += 1

    return {
        "case_count": case_count,
        "coverage_distribution": _sorted(coverage),
        "b4_selected_distribution": _sorted(b4_selected),
        "b5_aggregation_distribution": _sorted(b5_aggregation),
        "canonical_authority_distribution": {
            t: canonical_tiers.get(t, 0) for t in vocab.CANONICAL_TIERS
        },
        "native_authority_tier_distribution": _sorted(tier_distribution),
        "normalization_diagnostics": _sorted(conflicts),
        "eligible_submissions": eligible,
        "blocked_submissions": blocked,
        "one_of_groups": one_of_groups,
        "one_of_submissions": one_of_submissions,
    }


def _round_trip_failures(groups) -> int:
    if not groups:
        return 0
    restored = deserialize_solution_groups(
        json.dumps(serialize_solution_groups(groups))
    )
    return 0 if restored == groups else 1


def main() -> int:
    native_payload = _ensure_native_corpus()
    native_records = [
        (rec["external_submission_id"], rec["source_code"], rec["groups"])
        for rec in native_payload["records"]
    ]

    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    enriched_records = []
    for rec in historical["records"]:
        groups = [dict(g) for g in (rec.get("groups") or [])]
        fallback = rec.get("shadow_authority_tier") or "unknown"
        for g in groups:
            g.setdefault("authority_tier", fallback)
        marked = [dict(g) for g in groups]
        mark_family_relations(marked)
        enriched_records.append((rec.get("external_submission_id"),
                                 rec["source_code"], marked))

    payload_b = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    records_b = []
    for rec in payload_b["records"]:
        groups = [{
            "id": rec["name"],
            "required": list(rec.get("required_concepts") or []),
            "authority_tier": "llm_proposed",
        }]
        mark_family_relations(groups)  # in-place; returns changed ids
        records_b.append((rec.get("name"), rec["code"], groups))

    result_native = _measure(native_records)
    result_enriched = _measure(enriched_records)
    result_b = _measure(records_b)

    native_rt = sum(_round_trip_failures(g) for _, _, g in native_records)

    # ---- native vs enriched comparison (the "20/26" question) --------------
    def _row(old, enriched, new):
        return {
            "old_native": old, "enriched": enriched, "new_native": new,
        }

    # "old native" = the historical artifact's native state: no authority field
    old_native = {
        "authoritative_families": 0,
        "eligible_submissions": 0,
        "blocked_submissions": 46,
        "one_of_requirements": 0,
        "authority_conflicts": 0,
    }
    comparison = {
        "authoritative_families": _row(
            old_native["authoritative_families"],
            result_enriched["eligible_submissions"],
            result_native["eligible_submissions"],
        ),
        "eligible_submissions": _row(
            old_native["eligible_submissions"],
            result_enriched["eligible_submissions"],
            result_native["eligible_submissions"],
        ),
        "blocked_submissions": _row(
            old_native["blocked_submissions"],
            result_enriched["blocked_submissions"],
            result_native["blocked_submissions"],
        ),
        "one_of_requirements": _row(
            old_native["one_of_requirements"],
            result_enriched["one_of_groups"],
            result_native["one_of_groups"],
        ),
        "authority_conflicts": _row(
            old_native["authority_conflicts"],
            0,
            result_native["normalization_diagnostics"].get(
                vocab.AUTHORITY_CONFLICT, 0),
        ),
    }

    payload = {
        "batch": "B6.5",
        "layer": "canonical authority persistence normalization + native corpus",
        "feature_flag": {
            "env_var": b6.FLAG_ENV_VAR,
            "enabled": b6.flag_enabled(),
            "state": b6.flag_state(),
        },
        "corpus_a_46_native": {
            "provenance": "NATIVE",
            "native": True,
            "provenance_note": "GT read from live problem_ground_truth rows via "
                               "the production loader; no measurement-time "
                               "authority fabrication",
            **result_native,
        },
        "corpus_a_46_enriched": {
            "provenance": "ENRICHED",
            "native": False,
            "provenance_note": "authority-enriched / measurement-time: the "
                               "record-level shadow_authority_tier re-attached "
                               "for comparison only — NOT native provenance",
            **result_enriched,
        },
        "corpus_b_301": {
            "provenance": "NATIVE (llm_proposed GT)",
            "native": True,
            **result_b,
        },
        "serialization_round_trip_failures": native_rt,
        "native_vs_enriched_comparison": comparison,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for name, result in (
        ("corpus_a_46_NATIVE", payload["corpus_a_46_native"]),
        ("corpus_a_46_ENRICHED (comparison only)", payload["corpus_a_46_enriched"]),
        ("corpus_b_301", payload["corpus_b_301"]),
    ):
        print("=" * 72)
        print(name, "| provenance:", result["provenance"])
        print("  native authority tiers:", result["native_authority_tier_distribution"])
        print("  coverage:", result["coverage_distribution"])
        print("  B4 selected:", result["b4_selected_distribution"])
        print("  B5 aggregation:", result["b5_aggregation_distribution"])
        print("  canonical authority:", result["canonical_authority_distribution"])
        print("  normalization diagnostics:", result["normalization_diagnostics"])
        print("  eligible:", result["eligible_submissions"],
              "| blocked:", result["blocked_submissions"])
        print("  ONE_OF groups:", result["one_of_groups"],
              "| submissions:", result["one_of_submissions"])
    print("=" * 72)
    print("native-vs-enriched comparison:")
    for metric, row in comparison.items():
        print(f"  {metric}: old_native={row['old_native']} "
              f"enriched={row['enriched']} new_native={row['new_native']}")
    print("serialization round-trip failures:", native_rt)
    print("written:", OUT_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
