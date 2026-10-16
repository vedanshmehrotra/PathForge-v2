"""Phase 2 — normalization + dedup ladder (D1/D2/D3/D4).

For every reference solution this computes:
  raw_hash, norm_hash, fact_signature, technique_signature, strategy_signature,
  skeleton, skeleton_tokens

and assigns a dedup level relative to its family's canonical member.

The stored ``code_text`` is never modified; normalization produces comparison
keys only.  The frozen analyzer is used READ-ONLY.
"""
from collections import Counter

from .core import (
    PIPELINE_VERSION,
    analyze,
    build_families,
    canonicalized_source,
    fact_signature,
    sha256_hex,
    signature_class,
    skeleton_for,
    strategy_ids,
    technique_ids,
)
from .problem_metadata import POC_VERSION, PROVISIONAL_SKELETON_TAU, TAXONOMY_VERSION

DEDUP_LEVELS = {
    "D1": "exact_duplicate",
    "D2": "syntax_variant",
    "D3": "same_family_different_implementation",
    "D4": "distinct_family_canonical",
}

NORMALIZATION_CONTRACT = {
    "raw_hash": "sha256 of exact source text",
    "norm_hash": "sha256 of name-normalized AST rendering (comparison only)",
    "fact_signature": "name-free multiset of structural-fact types",
    "technique_signature": "sorted technique ids from the frozen pipeline",
    "strategy_signature": "sorted strategy ids from the frozen pipeline",
    "skeleton": "control-flow shape; user identifiers abstracted to Name, API names kept",
    "never_normalized_away": [
        "operators", "control flow", "loop nesting", "subscript/index structure",
        "call targets", "literal values",
    ],
    "code_text_mutation": "none",
}


def compute_keys(solution: dict) -> dict:
    code = solution["code_text"]
    analysis = analyze(code)
    row = {
        "solution_id": solution["solution_id"],
        "problem_id": solution["problem_id"],
        "source_type": solution["source_type"],
        "language": solution["language"],
        "raw_hash": solution["raw_hash"],
        "analysis_failed": analysis is None,
    }
    try:
        row["norm_hash"] = sha256_hex(canonicalized_source(code))
    except Exception as exc:  # pragma: no cover - defensive
        row["norm_hash"] = None
        row["analysis_failed"] = True
        row["normalization_error"] = f"{type(exc).__name__}: {exc}"
    try:
        sk = skeleton_for(code)
        row["skeleton"] = sk["skeleton"]
        row["skeleton_tokens"] = sk["skeleton_tokens"]
    except Exception as exc:  # pragma: no cover - defensive
        row["skeleton"] = ""
        row["skeleton_tokens"] = []
        row["normalization_error"] = f"{type(exc).__name__}: {exc}"

    row["fact_signature"] = fact_signature(analysis)
    row["technique_signature"] = technique_ids(analysis)
    row["strategy_signature"] = strategy_ids(analysis)
    row["signature_class"] = signature_class(row["technique_signature"], row["strategy_signature"])
    return row


def assign_ladder(rows: list, families: list) -> None:
    """Annotate each row with its dedup level relative to its family canonical."""
    by_id = {r["solution_id"]: r for r in rows}
    for fam in families:
        canon = by_id[fam["canonical_solution_id"]]
        for sid in fam["members"]:
            row = by_id[sid]
            row["family_key"] = fam["family_key"]
            if sid == canon["solution_id"]:
                row["dedup_level"] = "D4"
                row["related_to"] = None
                row["reason"] = "establishes a new family (no same-family prior solution)"
            elif row["raw_hash"] == canon["raw_hash"]:
                row["dedup_level"] = "D1"
                row["related_to"] = canon["solution_id"]
                row["reason"] = "identical raw_hash to the family canonical"
            elif row["norm_hash"] is not None and row["norm_hash"] == canon["norm_hash"]:
                row["dedup_level"] = "D2"
                row["related_to"] = canon["solution_id"]
                row["reason"] = "identical name-normalized source (syntax variant only)"
            else:
                row["dedup_level"] = "D3"
                row["related_to"] = canon["solution_id"]
                row["reason"] = (
                    "same signature class and skeleton distance < tau from the "
                    "family canonical (same algorithm, different implementation)"
                )
            row["dedup_level_name"] = DEDUP_LEVELS[row["dedup_level"]]


def run(reference_artifact: dict, tau: float = PROVISIONAL_SKELETON_TAU) -> dict:
    solutions = reference_artifact["solutions"]
    rows = [compute_keys(s) for s in solutions]
    rows.sort(key=lambda r: r["solution_id"])

    families = []
    for problem_id in sorted({r["problem_id"] for r in rows}):
        members = [r for r in rows if r["problem_id"] == problem_id]
        families.extend(build_families(problem_id, members, tau))

    assign_ladder(rows, families)

    ladder = Counter(r["dedup_level"] for r in rows)
    per_problem = {}
    for fam in families:
        per_problem.setdefault(str(fam["problem_id"]), []).append(len(fam["members"]))

    return {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "phase": "2_normalization",
        "provisional_skeleton_tau": tau,
        "normalization_contract": NORMALIZATION_CONTRACT,
        "dedup_ladder_summary": {
            "counts": {k: ladder.get(k, 0) for k in sorted(DEDUP_LEVELS)},
            "level_names": DEDUP_LEVELS,
        },
        "family_sizes_by_problem": per_problem,
        "solutions": rows,
    }
