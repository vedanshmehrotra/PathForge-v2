"""V2 POC orchestrator — runs Phases 1–5 and writes auditable JSON artifacts.

    python -m experiments.code_analysis_evaluation.gt_poc_v2.run_poc

Deterministic: no timestamps, no randomness, no network, no LLM, no DB access.
Running it twice on the same inputs produces byte-identical artifacts.
"""
import json
import os

from . import controls, derive, grouping, ingest, labeling, normalize, validate
from .core import PIPELINE_VERSION, sha256_hex
from .problem_metadata import (
    LABEL_MODE_PROVISIONAL,
    LABEL_MODE_STRICT,
    PEC_CONCEPTS,
    POC_VERSION,
    PROVISIONAL_ASSUMPTION_PA1,
    PROVISIONAL_REPRESENTATIVE_TAU,
    TAXONOMY_VERSION,
)

HERE = os.path.dirname(os.path.abspath(__file__))

ARTIFACT_NAMES = [
    "reference_solutions.json",
    "normalized_solutions.json",
    "families.json",
    "family_labels.json",
    "review_sheet.json",
    "review_sheet.md",
    "label_comparison.json",
    "derivation_outcomes.json",
    "negative_controls.json",
    "validation.json",
    "run_manifest.json",
]


def _dump(path: str, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=False) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return sha256_hex(text)


def run_all() -> dict:
    reference = ingest.run()
    normalized = normalize.run(reference)
    families = grouping.run(normalized)
    labels = labeling.build(reference, normalized, families)
    comparison = labeling.build_comparison(normalized, families, labels)

    # primary run: provisional label mode (PA1 — no human reviewer available)
    derivation = derive.derive(normalized, families, labels, label_mode=LABEL_MODE_PROVISIONAL)
    control_result = controls.run(reference, normalized, derivation, PEC_CONCEPTS)
    validation = validate.run(reference, normalized, families, labels, derivation, control_result)

    # strict run (only APPROVED labels activate) — recorded for comparison
    strict = derive.derive(normalized, families, labels, label_mode=LABEL_MODE_STRICT)
    validation["label_mode_comparison"] = {
        "strict_human": {
            "activated_groups": strict["totals"]["activated_groups"],
            "activation_rate": strict["totals"]["activation_rate"],
            "note": "no family label is APPROVED in this environment, so strict mode activates nothing",
        },
        "provisional_unreviewed": {
            "activated_groups": derivation["totals"]["activated_groups"],
            "activation_rate": derivation["totals"]["activation_rate"],
            "assumption": PROVISIONAL_ASSUMPTION_PA1,
        },
    }

    digests = {}
    digests["reference_solutions.json"] = _dump(os.path.join(HERE, "reference_solutions.json"), reference)
    digests["normalized_solutions.json"] = _dump(os.path.join(HERE, "normalized_solutions.json"), normalized)
    digests["families.json"] = _dump(os.path.join(HERE, "families.json"), families)
    digests["family_labels.json"] = _dump(os.path.join(HERE, "family_labels.json"), labels)
    digests["review_sheet.json"] = _dump(os.path.join(HERE, "review_sheet.json"), labels)
    with open(os.path.join(HERE, "review_sheet.md"), "w", encoding="utf-8", newline="\n") as fh:
        md = labeling.render_markdown(labels)
        fh.write(md)
    digests["review_sheet.md"] = sha256_hex(md)
    digests["label_comparison.json"] = _dump(os.path.join(HERE, "label_comparison.json"), comparison)
    digests["derivation_outcomes.json"] = _dump(os.path.join(HERE, "derivation_outcomes.json"), derivation)
    digests["negative_controls.json"] = _dump(os.path.join(HERE, "negative_controls.json"), control_result)
    digests["validation.json"] = _dump(os.path.join(HERE, "validation.json"), validation)

    manifest = {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "provisional_representative_tau": PROVISIONAL_REPRESENTATIVE_TAU,
        "label_mode": LABEL_MODE_PROVISIONAL,
        "provisional_assumption": PROVISIONAL_ASSUMPTION_PA1,
        "artifacts": {name: digest for name, digest in sorted(digests.items())},
    }
    _dump(os.path.join(HERE, "run_manifest.json"), manifest)

    return {
        "reference": reference,
        "normalized": normalized,
        "families": families,
        "labels": labels,
        "comparison": comparison,
        "derivation": derivation,
        "controls": control_result,
        "validation": validation,
        "manifest": manifest,
    }


def summarize(result: dict) -> str:
    ing = result["reference"]["ingestion"]
    fam = result["families"]["totals"]
    val = result["validation"]
    m = val["metrics"]
    lines = [
        "=" * 70,
        "  GROUND-TRUTH ARCHITECTURE POC V2 (JSON-first, Phases 1-5)",
        "=" * 70,
        f"  corpus: {ing['solution_count']} solutions across {ing['problem_count']} problems",
        f"  sources: {ing['source_distribution']}",
        f"  evidence: {ing['evidence_distribution']}",
        f"  D1 duplicate pairs: {len(ing['duplicate_raw_hash_pairs'])} in problems {ing['problems_with_D1_duplicates']}",
        "",
        f"  families: {fam['family_count']} (singletons: {fam['singleton_families']}, sizes: {fam['family_size_histogram']})",
        f"  dedup ladder: {result['normalized']['dedup_ladder_summary']['counts']}",
        "",
        f"  label mode: {result['derivation']['label_mode']}",
        f"  activated groups: {m['activated_groups']} (activation_rate={m['activation_rate']})",
        f"  divergence distribution: {m['divergence_distribution']}",
        "",
        f"  split: derivation={m['derivation_population']} held_out={m['held_out_population']}"
        f" (gate {m['held_out_population_gate']}, met={m['held_out_population_gate_met']})",
        f"  discrimination_FP: {m['discrimination_FP']}",
        f"  group_satisfiability: {m['group_satisfiability']}",
        f"  family_coverage: {m['family_coverage']}",
        f"  narrowing_violations: {m['narrowing_violations']}",
        f"  overall: {val['overall_state']}",
        "",
        f"  failed criteria: {val['failed_criteria']}",
        "=" * 70,
    ]
    return "\n".join(lines)


def main() -> int:
    result = run_all()
    print(summarize(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
