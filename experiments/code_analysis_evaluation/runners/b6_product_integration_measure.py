"""Batch B6 measurement: legacy vs canonical-shadow product eligibility.

B6 adds a controlled product-scoring gate on top of the B5/B5.5 canonical
authority model. This runner produces the migration evidence:

* B3 coverage / B4 primary strategy / B5 authority / B6 eligibility per corpus;
* authoritative families, safe submissions, blocked submissions;
* ONE_OF cases;
* the legacy/shadow comparison categories.

Two authority views are reported and clearly distinguished:

* **native** — authority metadata actually present on the groups (corpus B:
  ``llm_proposed``). Never claimed to be provenance it does not have.
* **measurement-time enrichment** — the record-level
  ``shadow_authority_tier`` re-attached to corpus A groups whose
  ``authority_tier`` was dropped by the OLD serialization. B5.5 fixed the
  serialization, but the *recorded historical corpus* still lacks the field;
  the enrichment is NOT native corpus provenance.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/b6_product_integration_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis import authority_vocabulary as vocab  # noqa: E402
from pathforge.ast_analysis.shadow import authority_gating as ag  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402
from pathforge.services import product_eligibility as b6  # noqa: E402
from pathforge.services.ground_truth_builder import (  # noqa: E402
    mark_family_relations,
)

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
OUT_PATH = RESULTS / "b6_product_integration_measurement.json"


def _sorted(counter) -> dict:
    return {str(k): counter[k] for k in sorted(counter, key=lambda k: (k is None, str(k)))}


def _analyze(code, groups):
    return shadow_runner.run_shadow_analysis(code, solution_groups=groups)


def _eligibility(result):
    authority_dict = result.get("authority")
    if authority_dict is None:
        return b6.product_eligibility(None), None
    report = b6._report_from_dict(authority_dict)
    return b6.product_eligibility(report), authority_dict


def _case(name, code, groups):
    result = _analyze(code, groups)
    if result is None:
        return None
    eligibility, authority = _eligibility(result)
    comparison = b6.classify_comparison(
        (result.get("match_outcome") or {}).get("outcome"),
        eligibility.eligible,
    )
    return {
        "case": name,
        "coverage": (result.get("coverage") or {}).get("aggregate_state"),
        "b4_selected": ((result.get("strategy_selection") or {})
                        .get("submission") or {}).get("selected"),
        "b5_aggregation": (authority or {}).get("aggregation"),
        "b5_authoritative_families": (authority or {}).get(
            "authoritative_family_count", 0),
        "canonical_authority": eligibility.canonical_authority,
        "eligible": eligibility.eligible,
        "eligibility_reasons": list(eligibility.reason_codes)[:4],
        "total_requirements": eligibility.total_requirements,
        "one_of_groups": (authority or {}).get("alternative_group_count", 0),
        "comparison_category": comparison,
    }


def _measure(label, records, authority_mode):
    coverage = collections.Counter()
    b4_selected = collections.Counter()
    b5_aggregation = collections.Counter()
    canonical_tiers = collections.Counter()
    eligibility_reasons = collections.Counter()
    comparisons = collections.Counter()
    eligible_submissions = 0
    blocked_submissions = 0
    authoritative_families = 0
    total_families = 0
    one_of_groups = 0
    one_of_submissions = 0
    safe_submissions = 0
    cases = []

    for rec in records:
        name = rec[0]
        code = rec[1]
        groups = rec[2]
        marked = None
        if groups:
            marked = [dict(g) for g in groups]
            if authority_mode == "enriched":
                fallback = rec[3] or "unknown"
                for g in marked:
                    g.setdefault("authority_tier", fallback)
            mark_family_relations(marked)

        case = _case(name, code, marked)
        if case is None:
            continue
        cases.append(case)

        coverage[case["coverage"]] += 1
        b4_selected[case["b4_selected"]] += 1
        b5_aggregation[case["b5_aggregation"]] += 1
        canonical_tiers[case["canonical_authority"]] += 1
        comparisons[case["comparison_category"]] += 1
        one_of_groups += case["one_of_groups"]
        if case["one_of_groups"]:
            one_of_submissions += 1
        if case["eligible"]:
            eligible_submissions += 1
            safe_submissions += 1
        else:
            blocked_submissions += 1
        for reason in case["eligibility_reasons"]:
            eligibility_reasons[reason] += 1

    return {
        "authority_mode": authority_mode,
        "coverage_distribution": _sorted(coverage),
        "b4_selected_distribution": _sorted(b4_selected),
        "b5_aggregation_distribution": _sorted(b5_aggregation),
        "canonical_authority_distribution": {
            t: canonical_tiers.get(t, 0) for t in vocab.CANONICAL_TIERS
        },
        "eligibility_reason_distribution": _sorted(eligibility_reasons),
        "comparison_categories": _sorted(comparisons),
        "eligible_submissions": eligible_submissions,
        "blocked_submissions": blocked_submissions,
        "safe_for_product_scoring_submissions": safe_submissions,
        "authoritative_families": authoritative_families + sum(
            c["b5_authoritative_families"] for c in cases
        ),
        "total_families": total_families + sum(c["total_requirements"] for c in cases),
        "one_of_groups": one_of_groups,
        "one_of_submissions": one_of_submissions,
        "cases": cases,
    }


def main() -> int:
    payload_a = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    records_a = [
        (rec.get("external_submission_id"), rec["source_code"],
         rec.get("groups") or None, rec.get("shadow_authority_tier"))
        for rec in payload_a["records"]
    ]
    payload_b = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    records_b = [
        (rec.get("name"), rec["code"],
         [{"id": rec["name"], "required": list(rec.get("required_concepts") or []),
           "authority_tier": "llm_proposed"}], "llm_proposed")
        for rec in payload_b["records"]
    ]

    result_a_native = _measure("corpus_a_46_real_submissions", records_a, "native")
    result_a_enriched = _measure(
        "corpus_a_46_real_submissions", records_a, "enriched"
    )
    result_b = _measure("corpus_b_301_disjoint_cases", records_b, "native")

    payload = {
        "batch": "B6",
        "layer": "controlled canonical-authority product eligibility (flag OFF by default)",
        "feature_flag": {
            "env_var": b6.FLAG_ENV_VAR,
            "default": "OFF",
            "state_at_measurement": b6.flag_state(),
            "enabled": b6.flag_enabled(),
        },
        "authority_provenance_note": (
            "corpus_a 'native' = the recorded historical corpus has NO "
            "authority_tier on groups (dropped by the pre-B5.5 serialization), "
            "so native-mode authority is absent -> everything blocked. "
            "corpus_a 'enriched' = measurement-time re-attachment of the "
            "record-level shadow_authority_tier; NOT native corpus provenance. "
            "corpus_b native = llm_proposed (the only value its GT supports)."
        ),
        "corpus_a_46_real_submissions_native": result_a_native,
        "corpus_a_46_real_submissions_authority_enriched": result_a_enriched,
        "corpus_b_301_disjoint_cases_native": result_b,
    }
    # strip bulky case lists from the JSON (kept aggregates only)
    for section in payload.values():
        if isinstance(section, dict) and "cases" in section:
            section["cases"] = section["cases"][:12]

    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for name, result in (
        ("corpus_a_46_native", result_a_native),
        ("corpus_a_46_authority_enriched", result_a_enriched),
        ("corpus_b_301_native", result_b),
    ):
        print("=" * 72)
        print(name, "| authority_mode:", result["authority_mode"])
        print("  coverage:", result["coverage_distribution"])
        print("  B4 selected:", result["b4_selected_distribution"])
        print("  B5 aggregation:", result["b5_aggregation_distribution"])
        print("  canonical authority:", result["canonical_authority_distribution"])
        print("  eligibility reasons:", result["eligibility_reason_distribution"])
        print("  comparison categories:", result["comparison_categories"])
        print("  eligible:", result["eligible_submissions"],
              "| blocked:", result["blocked_submissions"],
              "| safe:", result["safe_for_product_scoring_submissions"])
        print("  authoritative families:", result["authoritative_families"],
              "of", result["total_families"], "logical requirements")
        print("  ONE_OF groups:", result["one_of_groups"],
              "| submissions:", result["one_of_submissions"])
    print("=" * 72)
    print("written:", OUT_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
