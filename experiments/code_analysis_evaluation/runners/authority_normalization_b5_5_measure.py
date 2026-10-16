"""Batch B5.5 measurement: Ground-Truth authority normalization + alternatives.

B5.5 normalizes representation only. For ordinary (non-alternative) families the
shadow output must be unchanged relative to the recorded B5 baseline:

* B2 evidence, B3 coverage (aggregate state), B4 selected strategy and the
  legacy ``match_outcome`` distribution must match ``authority_b5_measurement``.

For explicitly declared ONE_OF families the aggregation is *intentionally*
different, and that difference is reported separately.

Corpus notes (documented data-quality findings, not repairs):

* the 46-submission corpus stores groups WITHOUT ``authority_tier``. The
  canonical loader normalization (``mark_family_relations``) is applied, and the
  record-level ``shadow_authority_tier`` is used only to report the authority
  distribution — never to change the shadow result.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/authority_normalization_b5_5_measure.py
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
from pathforge.services.ground_truth_builder import (  # noqa: E402
    deserialize_solution_groups, mark_family_relations, serialize_solution_groups,
)

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
OUT_PATH = RESULTS / "authority_normalization_b5_5_measurement.json"
BASELINE_PATH = RESULTS / "authority_b5_measurement.json"


def _sorted(counter) -> dict:
    return {str(k): counter[k] for k in sorted(counter, key=lambda k: (k is None, str(k)))}


def _corpus_a():
    payload = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    return payload["records"]


def _corpus_b():
    payload = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    return payload["records"]


def _prepare_a_groups(rec, restore_authority=False):
    """Apply the canonical relation normalization to stored corpus groups.

    ``restore_authority`` re-attaches the record-level ``shadow_authority_tier``
    to groups whose ``authority_tier`` was dropped at corpus serialization. This
    is a *documented approximation* used ONLY for the authority-distribution
    view (exact for the single-family records); it never changes the B2/B3/B4 or
    legacy-matcher result.
    """
    groups = rec.get("groups")
    if not groups:
        return None
    groups = [dict(g) for g in groups]
    if restore_authority:
        fallback = rec.get("shadow_authority_tier") or "unknown"
        for g in groups:
            g.setdefault("authority_tier", fallback)
    mark_family_relations(groups)
    return groups


def _group_round_trip_failures(groups) -> int:
    if not groups:
        return 0
    restored = deserialize_solution_groups(
        json.dumps(serialize_solution_groups(groups))
    )
    return 0 if restored == groups else 1


def _measure(label, cases, baseline):
    coverage = collections.Counter()
    old_outcome = collections.Counter()
    selected = collections.Counter()
    aggregation = collections.Counter()
    tier_counts = collections.Counter()
    declared_counts = collections.Counter()
    family_states = collections.Counter()
    one_of_groups = 0
    one_of_submissions = 0
    safe_submissions = 0
    round_trip_failures = 0
    disagreement_count = 0
    unknown_families = 0

    for name, code, groups, declared in cases:
        if groups:
            marked = [dict(g) for g in groups]
            mark_family_relations(marked)
        else:
            marked = groups
        result = shadow_runner.run_shadow_analysis(code, solution_groups=marked)
        if result is None:
            continue

        coverage[result["coverage"]["aggregate_state"]] += 1
        old_outcome[result["match_outcome"]["outcome"]] += 1
        selected[result["strategy_selection"]["submission"]["selected"]] += 1

        authority = result["authority"]
        if authority is None:
            continue
        aggregation[authority["aggregation"]] += 1
        n_groups = authority["alternative_group_count"]
        one_of_groups += n_groups
        if n_groups:
            one_of_submissions += 1
        if authority["safe_for_product_scoring"]:
            safe_submissions += 1

        for fam in authority["families"]:
            tier_counts[fam["authority_tier"]] += 1
            declared_counts[fam["declared_authority_tier"]] += 1
            family_states[fam["coverage_state"]] += 1
            if vocab.is_missing_authority(fam["declared_authority_tier"]):
                unknown_families += 1

        if groups:
            round_trip_failures += _group_round_trip_failures(groups)
            disagreement_count += len(
                vocab.find_authority_evidence_disagreements(groups)
            )

    # baseline comparison (B5)
    base = baseline.get(label, {}) if baseline else {}
    base_coverage = base.get("after_coverage_distribution", {})
    base_outcome = base.get("after_old_outcome_distribution", {})
    base_selected = base.get("after_selected_distribution", {})

    return {
        "coverage_distribution": _sorted(coverage),
        "old_outcome_distribution": _sorted(old_outcome),
        "selected_distribution": _sorted(selected),
        "aggregation_distribution": _sorted(aggregation),
        "canonical_tier_counts": {t: tier_counts.get(t, 0) for t in vocab.CANONICAL_TIERS},
        "declared_tier_counts": _sorted(declared_counts),
        "family_coverage_states": _sorted(family_states),
        "one_of_group_count": one_of_groups,
        "one_of_submissions": one_of_submissions,
        "mixed_authority_submissions": aggregation.get("MIXED_AUTHORITY", 0),
        "safe_for_product_scoring_submissions": safe_submissions,
        "serialization_round_trip_failures": round_trip_failures,
        "authority_evidence_disagreements": disagreement_count,
        "missing_authority_families": unknown_families,
        "baseline_coverage_distribution": base_coverage,
        "coverage_matches_baseline": _sorted(coverage) == base_coverage,
        "baseline_old_outcome_distribution": base_outcome,
        "old_outcome_matches_baseline": _sorted(old_outcome) == base_outcome,
        "baseline_selected_distribution": base_selected,
        "selected_matches_baseline": _sorted(selected) == base_selected,
    }


def main() -> int:
    baseline = {}
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    records_a = _corpus_a()
    cases_a = [
        (rec.get("external_submission_id"), rec["source_code"],
         _prepare_a_groups(rec), rec.get("shadow_authority_tier"))
        for rec in records_a
    ]
    # Secondary, clearly-labelled arm: authority metadata restored from the
    # record-level value so the ONE_OF aggregation effect is visible.
    cases_a_enriched = [
        (rec.get("external_submission_id"), rec["source_code"],
         _prepare_a_groups(rec, restore_authority=True),
         rec.get("shadow_authority_tier"))
        for rec in records_a
    ]
    cases_b = [
        (rec.get("name"), rec["code"],
         [{"id": rec["name"], "required": list(rec.get("required_concepts") or []),
           "authority_tier": "llm_proposed"}], "llm_proposed")
        for rec in _corpus_b()
    ]

    result_a = _measure("corpus_a_46_real_submissions", cases_a, baseline)
    result_a_enriched = _measure(
        "corpus_a_46_real_submissions", cases_a_enriched, baseline
    )
    result_b = _measure("corpus_b_301_disjoint_cases", cases_b, baseline)

    declared = [
        tier
        for result in (result_a, result_b)
        for tier, count in result["declared_tier_counts"].items()
        for _ in range(count)
    ]

    payload = {
        "batch": "B5.5",
        "layer": "Ground-Truth authority normalization + ONE_OF alternative families",
        "canonical_vocabulary": {
            "tiers": list(vocab.CANONICAL_TIERS),
            "authorizing_tiers": sorted(vocab.AUTHORIZING_TIERS),
            "source_tier_map": dict(sorted(vocab.SOURCE_TIER_MAP.items())),
            "valid_gt_tiers": sorted(vocab.VALID_GT_TIERS),
            "legacy_production_authoritative_states":
                sorted(vocab.LEGACY_PRODUCTION_AUTHORITATIVE_STATES),
            "legacy_production_authoritative_tiers":
                sorted(vocab.LEGACY_PRODUCTION_AUTHORITATIVE_TIERS),
        },
        "declared_tier_data_quality": vocab.authority_data_quality(declared),
        "corpus_a_46_real_submissions": result_a,
        "corpus_a_authority_enriched_view": result_a_enriched,
        "corpus_b_301_disjoint_cases": result_b,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for name, result in (
        ("corpus_a_46_real_submissions", result_a),
        ("corpus_a_authority_enriched_view", result_a_enriched),
        ("corpus_b_301_disjoint_cases", result_b),
    ):
        print("=" * 72)
        print(name)
        print("  coverage:", result["coverage_distribution"],
              "matches B5 baseline:", result["coverage_matches_baseline"])
        print("  old outcome:", result["old_outcome_distribution"],
              "matches B5 baseline:", result["old_outcome_matches_baseline"])
        print("  B4 selected matches B5 baseline:", result["selected_matches_baseline"])
        print("  canonical tiers:", result["canonical_tier_counts"])
        print("  declared tiers:", result["declared_tier_counts"])
        print("  aggregation:", result["aggregation_distribution"])
        print("  ONE_OF groups:", result["one_of_group_count"],
              "| submissions affected:", result["one_of_submissions"])
        print("  mixed:", result["mixed_authority_submissions"],
              "| safe_for_scoring:", result["safe_for_product_scoring_submissions"])
        print("  round-trip failures:", result["serialization_round_trip_failures"],
              "| authority/evidence disagreements:",
              result["authority_evidence_disagreements"],
              "| missing-authority families:", result["missing_authority_families"])
    print("=" * 72)
    print("written:", OUT_PATH.relative_to(ROOT))

    clean = (
        result_a["coverage_matches_baseline"] and result_b["coverage_matches_baseline"]
        and result_a["old_outcome_matches_baseline"]
        and result_b["old_outcome_matches_baseline"]
        and result_a["selected_matches_baseline"]
        and result_b["selected_matches_baseline"]
        and result_a["serialization_round_trip_failures"] == 0
        and result_b["serialization_round_trip_failures"] == 0
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
