"""Batch B3 measurement: old shadow verdict vs B3 family coverage.

Reports, without tuning anything:

* the old shadow matcher's outcome distribution vs B3's aggregate coverage
  distribution over the 46 real submissions and the 301-case corpus;
* the exact transition counts the B3 brief asks for (1-8);
* how many concept-level contradictions are deliberately NOT escalated and how
  many family-level contradictions exist;
* the confirmation split with/without a conclusion-eligible PRESENT concept;
* the previously recorded precision/recall (`metrics`) is preserved verbatim for
  comparison — B3 tunes no detector.

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/family_coverage_b3_measure.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis.shadow import evidence_state as ev  # noqa: E402
from pathforge.ast_analysis.shadow import family_coverage as fc  # noqa: E402
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis  # noqa: E402

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
OUT_PATH = RESULTS / "family_coverage_b3_measurement.json"

#: The problem ids named in the B3 brief that appear in the 46-submission corpus.
NAMED_PROBLEM_IDS = (3236, 209, 102, 1, 21, 125, 46, 70, 704)


def _transition(old: str, new: str) -> str:
    return f"{old}->{new}"


def measure_corpus_a() -> dict:
    payload = json.loads(
        (RESULTS / "db_batch3" / "submission_eval_results.json").read_text(encoding="utf-8")
    )
    records = payload["records"]

    recorded_counts = collections.Counter()
    fresh_old_counts = collections.Counter()
    k3_counts = collections.Counter()
    transitions_recorded_to_k3 = collections.Counter()
    transitions_fresh_to_k3 = collections.Counter()

    confirmed_with_eligible = 0
    confirmed_without_eligible = 0
    provisional_total = 0
    family_contradictions = 0
    concept_contradictions_total = 0
    non_escalated_contradictions = 0
    per_family_states = collections.Counter()
    named_cases = {}

    for rec in records:
        label = rec.get("external_submission_id")
        groups = rec.get("groups") or None
        result = run_shadow_analysis(rec["source_code"], solution_groups=groups)
        if result is None:
            continue
        recorded = rec.get("shadow_outcome") or "NONE"
        fresh_old = (result.get("match_outcome") or {}).get("outcome", "NONE")
        coverage = result.get("coverage") or {}
        k3 = coverage.get("aggregate_state", "NONE")

        recorded_counts[recorded] += 1
        fresh_old_counts[fresh_old] += 1
        k3_counts[k3] += 1
        transitions_recorded_to_k3[_transition(recorded, k3)] += 1
        transitions_fresh_to_k3[_transition(fresh_old, k3)] += 1

        families = coverage.get("families") or []
        for fam in families:
            state = fam["coverage_state"]
            per_family_states[state] += 1
            if state == fc.CONFIRMED:
                if fam.get("conclusion_eligible_present"):
                    confirmed_with_eligible += 1
                else:
                    confirmed_without_eligible += 1
            elif state == fc.PROVISIONAL:
                provisional_total += 1
            elif state == fc.CONTRADICTED:
                family_contradictions += 1

        # Concept-level contradictions that were deliberately not escalated
        # (the contradicted concept is not an identifying requirement of a family
        # that became CONTRADICTED).
        contradicted_identifying = {
            c for fam in families for c in fam.get("contradicted_identifying") or []
        }
        for item in (result.get("evidence_state") or {}).get("evidence", []):
            if item["state"] != ev.CONTRADICTED:
                continue
            concept_contradictions_total += 1
            if item["concept_id"] not in contradicted_identifying:
                non_escalated_contradictions += 1

        if rec.get("problem_id") in NAMED_PROBLEM_IDS:
            named_cases.setdefault(str(rec.get("problem_id")), []).append({
                "submission_id": label,
                "recorded_old": recorded,
                "fresh_old": fresh_old,
                "b3_aggregate": k3,
                "families": [
                    {
                        "family_id": fam["family_id"],
                        "state": fam["coverage_state"],
                        "reasons": fam["reason_codes"],
                        "identifying_required": fam["identifying_required"],
                        "conclusion_eligible_present": fam["conclusion_eligible_present"],
                        "contradicted_identifying": fam["contradicted_identifying"],
                    }
                    for fam in families
                ],
            })

    # The transitions the brief enumerates (1-8), for the FRESH old matcher.
    t = transitions_fresh_to_k3
    enumerated = {
        "1_old_CONFIRMED_to_b3_CONFIRMED": t["CONFIRMED->CONFIRMED"],
        "2_old_CONFIRMED_to_b3_PROVISIONAL": t["CONFIRMED->PROVISIONAL"],
        "3_old_CONFIRMED_to_b3_UNRESOLVED": t["CONFIRMED->UNRESOLVED"],
        "4_old_CONFIRMED_to_b3_CONTRADICTED": t["CONFIRMED->CONTRADICTED"],
        "5_old_UNRESOLVED_to_b3_PROVISIONAL": t["UNRESOLVED->PROVISIONAL"],
        "6_old_UNRESOLVED_to_b3_CONFIRMED": t["UNRESOLVED->CONFIRMED"],
        "7_old_UNRESOLVED_to_b3_UNRESOLVED": t["UNRESOLVED->UNRESOLVED"],
        "8_unexpected_or_error": sum(
            v for k, v in t.items()
            if k.split("->")[0] not in {"CONFIRMED", "UNRESOLVED"}
            or k.split("->")[1] in {"NO_GROUND_TRUTH", "UNMATCHABLE", "NONE"}
        ),
    }

    return {
        "cases": len(records),
        "recorded_old_distribution": dict(sorted(recorded_counts.items())),
        "fresh_old_distribution": dict(sorted(fresh_old_counts.items())),
        "b3_distribution": dict(sorted(k3_counts.items())),
        "transitions_recorded_old_to_b3": dict(sorted(transitions_recorded_to_k3.items())),
        "transitions_fresh_old_to_b3": dict(sorted(transitions_fresh_to_k3.items())),
        "enumerated_transitions": enumerated,
        "per_family_b3_states": dict(sorted(per_family_states.items())),
        "confirmed_families_with_conclusion_eligible_present": confirmed_with_eligible,
        "confirmed_families_without_conclusion_eligible_present": confirmed_without_eligible,
        "provisional_families": provisional_total,
        "family_contradictions": family_contradictions,
        "concept_contradictions_total": concept_contradictions_total,
        "concept_contradictions_not_escalated": non_escalated_contradictions,
        "named_cases": named_cases,
    }


def measure_corpus_b() -> dict:
    payload = json.loads(
        (RESULTS / "disjoint301_eval_results_BASELINE_step4.json").read_text(encoding="utf-8")
    )
    records = payload["records"]

    old_counts = collections.Counter()
    k3_counts = collections.Counter()
    transitions = collections.Counter()
    per_expected_pattern = collections.defaultdict(collections.Counter)
    non_escalated = 0
    family_contradictions = 0

    for rec in records:
        name = rec.get("name")
        required = rec.get("required_concepts") or []
        # The 301 corpus is a detector-level corpus with an expected family per
        # case; its `required_concepts` is that family's requirement. B3 coverage
        # is evaluated against that family (documented interpretation).
        groups = [{"id": name, "required": list(required)}]
        result = run_shadow_analysis(rec["code"], solution_groups=groups)
        if result is None:
            continue
        coverage = result.get("coverage") or {}
        k3 = coverage.get("aggregate_state", "NONE")
        old = rec.get("verdict", "NONE")

        old_counts[old] += 1
        k3_counts[k3] += 1
        transitions[_transition(old, k3)] += 1
        per_expected_pattern[rec.get("expected_pattern")][k3] += 1

        families = coverage.get("families") or []
        contradicted_identifying = {
            c for fam in families for c in fam.get("contradicted_identifying") or []
        }
        for fam in families:
            if fam["coverage_state"] == fc.CONTRADICTED:
                family_contradictions += 1
        for item in (result.get("evidence_state") or {}).get("evidence", []):
            if item["state"] == ev.CONTRADICTED and item["concept_id"] not in contradicted_identifying:
                non_escalated += 1

    return {
        "cases": len(records),
        "recorded_verdict_distribution": dict(sorted(old_counts.items())),
        "b3_distribution": dict(sorted(k3_counts.items())),
        "transitions_recorded_verdict_to_b3": dict(sorted(transitions.items())),
        "per_expected_pattern_b3_states": {
            pattern: dict(sorted(counts.items()))
            for pattern, counts in sorted(per_expected_pattern.items())
        },
        "family_contradictions": family_contradictions,
        "concept_contradictions_not_escalated": non_escalated,
        "preserved_recorded_metrics": payload.get("metrics", {}),
    }


def main() -> int:
    corpus_a = measure_corpus_a()
    corpus_b = measure_corpus_b()

    payload = {
        "batch": "B3",
        "layers": "concept evidence (B2) -> family coverage -> coverage state",
        "corpus_a_46_real_submissions": corpus_a,
        "corpus_b_301_disjoint_cases": corpus_b,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("=" * 72)
    print("corpus A — 46 real submissions")
    print("  recorded old :", corpus_a["recorded_old_distribution"])
    print("  fresh old    :", corpus_a["fresh_old_distribution"])
    print("  B3 aggregate :", corpus_a["b3_distribution"])
    print("  transitions (fresh old -> B3):", corpus_a["transitions_fresh_old_to_b3"])
    print("  enumerated   :", corpus_a["enumerated_transitions"])
    print("  per-family states:", corpus_a["per_family_b3_states"])
    print("  confirmed with eligible:", corpus_a["confirmed_families_with_conclusion_eligible_present"])
    print("  confirmed WITHOUT eligible:", corpus_a["confirmed_families_without_conclusion_eligible_present"])
    print("  provisional:", corpus_a["provisional_families"])
    print("  family contradictions:", corpus_a["family_contradictions"])
    print("  concept contradictions:", corpus_a["concept_contradictions_total"],
          "not escalated:", corpus_a["concept_contradictions_not_escalated"])
    print("  named cases:", {k: [(c["submission_id"], c["recorded_old"], c["fresh_old"], c["b3_aggregate"]) for c in v]
                              for k, v in sorted(corpus_a["named_cases"].items())})
    print("=" * 72)
    print("corpus B — 301 disjoint cases")
    print("  recorded verdict:", corpus_b["recorded_verdict_distribution"])
    print("  B3 aggregate    :", corpus_b["b3_distribution"])
    print("  family contradictions:", corpus_b["family_contradictions"])
    print("  non-escalated concept contradictions:", corpus_b["concept_contradictions_not_escalated"])
    print("=" * 72)
    print("written:", OUT_PATH.relative_to(ROOT))

    # Hard invariant: CONFIRMED may never exist without a conclusion-eligible
    # concept PRESENT (the false-confirmation fence).
    assert corpus_a["confirmed_families_without_conclusion_eligible_present"] == 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
