"""POC orchestrator — runs Phases 1–5 and writes the auditable JSON artifacts.

Usage (from the repository root):

    python -m experiments.code_analysis_evaluation.gt_poc.run_poc

Deterministic: no timestamps, no randomness, no network, no LLM, no DB access.
Running it twice on the same inputs produces byte-identical artifacts.
"""
import json
import os

from . import ingest, normalize, group, label, validate
from .core import PIPELINE_VERSION, sha256_hex
from .problem_metadata import (
    POC_VERSION,
    PROVISIONAL_SKELETON_TAU,
    TAXONOMY_VERSION,
)

HERE = os.path.dirname(os.path.abspath(__file__))

ARTIFACTS = {
    "reference_solutions.json": "reference",
    "normalized_solutions.json": "normalized",
    "families.json": "families",
    "label_comparison.json": "comparison",
    "validation.json": "validation",
    "run_manifest.json": "manifest",
}


def _dump(path: str, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=False) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return sha256_hex(text)


def run_all() -> dict:
    reference = ingest.run()
    normalized = normalize.run(reference)
    families = group.run(normalized)
    review = label.build(reference, families)
    comparison = label.build_comparison(normalized, families, review)
    validation = validate.run(reference, normalized, families)

    digests = {}
    digests["reference_solutions.json"] = _dump(os.path.join(HERE, "reference_solutions.json"), reference)
    digests["normalized_solutions.json"] = _dump(os.path.join(HERE, "normalized_solutions.json"), normalized)
    digests["families.json"] = _dump(os.path.join(HERE, "families.json"), families)
    digests["review_sheet.json"] = _dump(os.path.join(HERE, "review_sheet.json"), review)
    with open(os.path.join(HERE, "review_sheet.md"), "w", encoding="utf-8", newline="\n") as fh:
        md = label.render_markdown(review)
        fh.write(md)
    digests["review_sheet.md"] = sha256_hex(md)
    digests["label_comparison.json"] = _dump(os.path.join(HERE, "label_comparison.json"), comparison)
    digests["validation.json"] = _dump(os.path.join(HERE, "validation.json"), validation)

    manifest = {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "provisional_skeleton_tau": PROVISIONAL_SKELETON_TAU,
        "artifacts": {
            name: digest for name, digest in sorted(digests.items())
        },
    }
    _dump(os.path.join(HERE, "run_manifest.json"), manifest)

    return {
        "reference": reference,
        "normalized": normalized,
        "families": families,
        "review": review,
        "comparison": comparison,
        "validation": validation,
        "manifest": manifest,
    }


def summarize(result: dict) -> str:
    ing = result["reference"]["ingestion"]
    fam = result["families"]["totals"]
    val = result["validation"]
    lines = [
        "=" * 68,
        "  GROUND-TRUTH ARCHITECTURE POC (JSON-first, Phases 1-5)",
        "=" * 68,
        f"  corpus: {ing['solution_count']} solutions across {ing['problem_count']} problems",
        f"  sources: {ing['source_distribution']}",
        f"  ingestion issues: {len(ing['issues'])}",
        "",
        f"  families: {fam['family_count']} "
        f"(singletons: {fam['singleton_families']}, sizes: {fam['family_size_histogram']})",
        f"  dedup ladder: {result['normalized']['dedup_ladder_summary']['counts']}",
        "",
        f"  review: {result['review']['totals']}",
        "",
        f"  split: derivation={len(val['split']['derivation'])} held_out={len(val['split']['held_out'])}",
        f"  metrics:",
    ]
    for k, v in val["metrics"].items():
        lines.append(f"      {k}: {v}")
    lines.append("")
    lines.append(f"  failed criteria: {len(val['failed_criteria'])}")
    for f in val["failed_criteria"]:
        lines.append(f"      - {f['criterion']}: observed={f['observed']} required={f['required']}")
    lines.append("=" * 68)
    return "\n".join(lines)


def main() -> int:
    result = run_all()
    print(summarize(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
