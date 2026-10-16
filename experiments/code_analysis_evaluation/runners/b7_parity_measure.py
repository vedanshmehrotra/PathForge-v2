"""Batch B7: legacy-vs-shadow verdict parity / migration-readiness measurement.

Observational only. For every case the runner:

1. extracts the LEGACY matcher's actual result (``run_analysis`` — never
   reinterpreted);
2. extracts the canonical SHADOW result (B2/B3/B4/B5/B6);
3. builds one ``LegacyShadowParityRecord`` and classifies it (P1–P10).

Datasets:

* **NATIVE 46** (primary migration dataset) — GT from live
  ``problem_ground_truth`` rows via the production loader
  (``submission_eval_results_NATIVE.json``).
* **ENRICHED 46** (secondary comparison only, clearly labelled
  NON-NATIVE / MEASUREMENT-TIME ENRICHED).
* **301 benchmark** (safety/regression corpus; GT llm_proposed → INFERRED, so
  0 eligible is the expected outcome; NOT used to estimate authoritative
  migration readiness).

No consequence is ever executed: Elo/gap/recommendation values are simulated
booleans from the gate rules. No Elo mutation, no gap mutation, no
recommendation mutation. The feature flag remains OFF throughout.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/b7_parity_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.api.services.analysis import run_analysis  # noqa: E402
from pathforge.ast_analysis import authority_vocabulary as vocab  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402
from pathforge.services import legacy_shadow_parity as b7  # noqa: E402
from pathforge.services import product_eligibility as b6  # noqa: E402
from pathforge.services.ground_truth_builder import (  # noqa: E402
    mark_family_relations,
)

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
NATIVE_PATH = RESULTS / "db_batch3" / "submission_eval_results_NATIVE.json"
HISTORICAL = RESULTS / "db_batch3" / "submission_eval_results.json"
OUT_PATH = RESULTS / "b7_parity_measurement.json"


def _sorted(counter) -> dict:
    return {str(k): counter[k]
            for k in sorted(counter, key=lambda k: (k is None, str(k)))}


def _regenerate_native() -> dict:
    """Reuse the B6.5 native corpus; regenerate it if absent (provenance NATIVE)."""
    if NATIVE_PATH.exists():
        payload = json.loads(NATIVE_PATH.read_text(encoding="utf-8"))
        if payload.get("provenance") == "NATIVE" and payload.get("records"):
            return payload
    print("native corpus missing; regenerating via the B6.5 runner...")
    spec_path = (ROOT / "experiments" / "code_analysis_evaluation" / "runners" /
                 "b6_5_authority_normalization_measure.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("b6_5_measure", spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._ensure_native_corpus()


def _parity_record(rec, groups):
    code = rec["source_code"]
    legacy_failed = False
    legacy_result = None
    try:
        analysis = run_analysis(code, "python",
                                accepted_solution_groups=groups or None)
        if "error" in analysis:
            legacy_failed = True
        else:
            legacy_result = analysis.get("match_result") or {}
    except Exception:
        legacy_failed = True

    shadow_failed = False
    shadow = None
    try:
        shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups or None)
        if shadow is None:
            shadow_failed = True
    except Exception:
        shadow_failed = True

    eligibility = None
    if shadow and shadow.get("authority"):
        eligibility = b6.product_eligibility(b6._report_from_dict(shadow["authority"]))

    return b7.build_parity_record(
        rec.get("external_submission_id"), rec.get("problem_id"),
        rec.get("title"), groups, legacy_result, shadow, eligibility,
        shadow_failed=shadow_failed, legacy_failed=legacy_failed,
    )


def _measure(label, records, provenance):
    categories = collections.Counter()
    p2_reasons = collections.Counter()
    statuses = collections.Counter()
    coverage = collections.Counter()
    canonical_tiers = collections.Counter()
    conflicts = []
    technique_only = []
    examples = collections.defaultdict(list)

    legacy_authoritative_count = 0
    legacy_matched_count = 0
    eligible = 0
    blocked = 0
    elo_legacy = elo_shadow = 0
    gap_legacy = gap_shadow = 0
    rec_legacy = rec_shadow = 0

    total = 0
    for name, code, groups in records:
        total += 1
        rec = {"source_code": code, "external_submission_id": name,
               "problem_id": None, "title": None}
        record = _parity_record(rec, groups)
        d = record.to_dict()
        category = d["comparison"]["parity_category"]
        categories[category] += 1
        statuses[d["comparison"]["migration_status"]] += 1
        coverage[d["shadow"]["coverage_state"]] += 1
        canonical_tiers[d["shadow"]["authority_tier"]] += 1
        legacy_authoritative_count += 1 if b7.legacy_authoritative(
            d["legacy"]["evidence"]) else 0
        legacy_matched_count += 1 if d["legacy"]["matched"] else 0
        eligible += 1 if d["shadow"]["b6_eligible"] else 0
        blocked += 0 if d["shadow"]["b6_eligible"] else 1
        sim = d["consequence_simulation"]
        elo_legacy += sim["legacy_allows_elo"]
        elo_shadow += sim["shadow_allows_elo"]
        gap_legacy += sim["legacy_allows_gap"]
        gap_shadow += sim["shadow_allows_gap"]
        rec_legacy += sim["legacy_allows_recommendation"]
        rec_shadow += sim["shadow_allows_recommendation"]

        if category == b7.P7_AUTHORITY_CONFLICT:
            conflicts.append({
                "case": name,
                "authority_tier": d["shadow"]["authority_tier"],
                "b6_reason": d["shadow"]["b6_reasons"][:2],
            })
        if d.get("technique_only_one_of"):
            technique_only.append(name)
        if category not in (b7.P1_EXACT_PARITY,):
            reason_key = (d["comparison"]["divergence_reason"] or ["?"])[0]
            examples[(category, reason_key)].append(name)
        for reason in d["comparison"]["divergence_reason"]:
            p2_reasons[f"{category}:{reason}"] += 1

    return {
        "label": label,
        "provenance": provenance,
        "total_submissions": total,
        "legacy_authoritative": legacy_authoritative_count,
        "legacy_blocked": total - legacy_authoritative_count,
        "legacy_matched": legacy_matched_count,
        "shadow_coverage": _sorted(coverage),
        "canonical_authority": {t: canonical_tiers.get(t, 0)
                                for t in vocab.CANONICAL_TIERS},
        "b6_eligible": eligible,
        "b6_blocked": blocked,
        "parity_categories": {c: categories.get(c, 0) for c in b7.PARITY_CATEGORIES},
        "p2_sub_reasons": {r: p2_reasons.get(f"{b7.P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED}:{r}", 0)
                           for r in b7.P2_REASONS},
        "migration_statuses": {s: statuses.get(s, 0) for s in b7.MIGRATION_STATUSES},
        "authority_conflict_cases": conflicts[:20],
        "authority_conflict_count": len(conflicts),
        "technique_only_one_of_cases": technique_only,
        "migration_consequence_comparison": {
            "legacy_allows_elo": elo_legacy, "shadow_allows_elo": elo_shadow,
            "legacy_allows_gap": gap_legacy, "shadow_allows_gap": gap_shadow,
            "legacy_allows_recommendation": rec_legacy,
            "shadow_allows_recommendation": rec_shadow,
            "simulated_only": True,
        },
        "divergence_examples": {
            f"{cat}:{reason}": cases[:8]
            for (cat, reason), cases in sorted(examples.items())
        },
        "percentages": {
            "exact_parity_pct": round(100.0 * categories.get(b7.P1_EXACT_PARITY, 0) / total, 1) if total else 0.0,
            "authority_conflict_pct": round(100.0 * categories.get(b7.P7_AUTHORITY_CONFLICT, 0) / total, 1) if total else 0.0,
            "b6_eligible_pct": round(100.0 * eligible / total, 1) if total else 0.0,
        },
    }


def main() -> int:
    native = _regenerate_native()

    native_records = [
        (rec["external_submission_id"], rec["source_code"], rec["groups"])
        for rec in native["records"]
    ]
    result_native = _measure("native_46", native_records, "NATIVE")

    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    enriched_records = []
    for rec in historical["records"]:
        groups = [dict(g) for g in (rec.get("groups") or [])]
        fallback = rec.get("shadow_authority_tier") or "unknown"
        for g in groups:
            g.setdefault("authority_tier", fallback)
        mark_family_relations(groups)
        enriched_records.append((rec.get("external_submission_id"),
                                 rec["source_code"], groups))
    result_enriched = _measure("enriched_46", enriched_records,
                               "NON-NATIVE / MEASUREMENT-TIME ENRICHED")

    payload_b = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    records_b = []
    for rec in payload_b["records"]:
        groups = [{
            "id": rec["name"],
            "required": list(rec.get("required_concepts") or []),
            "authority_tier": "llm_proposed",
            # the legacy matcher consumes group['patterns']; the benchmark's
            # synthetic groups must carry the legacy representation too
            "patterns": [rec.get("expected_pattern")]
            if rec.get("expected_pattern") else [],
        }]
        mark_family_relations(groups)
        records_b.append((rec.get("name"), rec["code"], groups))
    result_b = _measure("benchmark_301_safety", records_b, "NATIVE (llm_proposed GT)")

    payload = {
        "batch": "B7",
        "layer": "legacy-vs-shadow verdict parity / migration readiness (observational)",
        "feature_flag": {
            "env_var": b6.FLAG_ENV_VAR,
            "enabled": b6.flag_enabled(),
            "state": b6.flag_state(),
        },
        "methodology": {
            "primary_dataset": "native 46 (live GT provenance)",
            "secondary_dataset": "enriched 46 (NON-NATIVE, measurement-time)",
            "safety_dataset": "301 benchmark (llm_proposed GT; not used for "
                              "authoritative migration estimates)",
            "consequences": "simulated booleans only; never executed",
        },
        "native_46": result_native,
        "enriched_46_NON_NATIVE": result_enriched,
        "benchmark_301_safety": result_b,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for result in (result_native, result_enriched, result_b):
        print("=" * 74)
        print(result["label"], "| provenance:", result["provenance"],
              "| n =", result["total_submissions"])
        print("  legacy: authoritative", result["legacy_authoritative"],
              "blocked", result["legacy_blocked"],
              "matched", result["legacy_matched"])
        print("  shadow coverage:", result["shadow_coverage"])
        print("  canonical authority:", result["canonical_authority"])
        print("  B6 eligible:", result["b6_eligible"],
              "blocked:", result["b6_blocked"],
              f"({result['percentages']['b6_eligible_pct']}%)")
        print("  parity categories:")
        for cat, count in result["parity_categories"].items():
            if count:
                pct = round(100.0 * count / result["total_submissions"], 1)
                print(f"    {cat}: {count} ({pct}%)")
        print("  P2 sub-reasons:", {k: v for k, v in
                                    result["p2_sub_reasons"].items() if v})
        print("  migration statuses:", {k: v for k, v in
                                         result["migration_statuses"].items() if v})
        print("  authority conflicts:", result["authority_conflict_count"])
        print("  technique-only ONE_OF:", result["technique_only_one_of_cases"])
        print("  consequence simulation (legacy vs shadow): ELO",
              result["migration_consequence_comparison"]["legacy_allows_elo"], "/",
              result["migration_consequence_comparison"]["shadow_allows_elo"],
              "| GAP", result["migration_consequence_comparison"]["legacy_allows_gap"],
              "/", result["migration_consequence_comparison"]["shadow_allows_gap"],
              "| REC", result["migration_consequence_comparison"]["legacy_allows_recommendation"],
              "/", result["migration_consequence_comparison"]["shadow_allows_recommendation"])
    print("=" * 74)
    print("flag:", b6.flag_state(), "| enabled:", b6.flag_enabled())
    print("written:", OUT_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
