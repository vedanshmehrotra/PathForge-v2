"""Phase 2 — V2 normalization + dedup ladder.

For every reference solution this computes:

  raw_hash, norm_hash, fact_signature, technique_signature, strategy_signature,
  skeleton, structural_profile, PEC set, SUPPORT set, evidence_state

and assigns a dedup level (D1/D2/D3/D4) relative to its family's canonical
member.  The stored ``code_text`` is never modified; normalization produces
comparison keys only.  The frozen analyzer is used READ-ONLY.
"""
from collections import Counter

from .core import (
    analyze,
    canonicalized_source,
    classify_concepts,
    compute_profile,
    fact_signature,
    profile_tuple,
    sha256_hex,
    skeleton_for,
    strategy_ids,
    technique_ids,
    unknown_concepts,
)
from .grouping import build_families

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
    "structural_profile": "V2 §1.5 coarse 5-tuple (recursion, loop_shape, container, map_kind, iterates_collection)",
    "never_normalized_away": [
        "operators", "control flow", "loop nesting", "subscript/index structure",
        "call targets", "literal values",
    ],
    "code_text_mutation": "none",
}


def compute_keys(solution: dict) -> dict:
    code = solution["code_text"]
    analysis = analyze(code)
    techs = technique_ids(analysis)
    strats = strategy_ids(analysis)
    concepts = sorted(set(techs) | set(strats))
    tiers = classify_concepts(concepts)
    profile = compute_profile(code)

    row = {
        "solution_id": solution["solution_id"],
        "problem_id": solution["problem_id"],
        "local_key": solution.get("local_key"),
        "source_type": solution["source_type"],
        "language": solution["language"],
        "raw_hash": solution["raw_hash"],
        "quality_state": solution["quality_state"],
        "evidence_state": solution["evidence_state"],
        "analysis_failed": analysis is None,
        "technique_signature": techs,
        "strategy_signature": strats,
        "concepts": concepts,
        "pec_set": tiers["PEC"],
        "support_set": tiers["SUPPORT"],
        "concept_tiers": tiers["tiers"],
        "unknown_concepts": unknown_concepts(concepts),
        "structural_profile": {k: v for k, v in profile.items() if not k.startswith("_")},
        "zero_evidence": (not techs and not strats),
    }
    try:
        row["norm_hash"] = sha256_hex(canonicalized_source(code))
    except Exception as exc:  # pragma: no cover - defensive
        row["norm_hash"] = None
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

    # Internal aliases used by the grouping/profile machinery.
    row["profile"] = profile
    return row


def assign_ladder(rows: list, families: list) -> None:
    by_id = {r["solution_id"]: r for r in rows}
    for fam in families:
        canon = by_id[fam["canonical_solution_id"]]
        for sid in fam["members"]:
            row = by_id[sid]
            row["family_key"] = fam["family_key"]
            if sid == canon["solution_id"]:
                row["dedup_level"] = "D4"
                row["related_to"] = None
                row["reason"] = "establishes a family (family representative)"
            elif row["raw_hash"] == canon["raw_hash"]:
                row["dedup_level"] = "D1"
                row["related_to"] = canon["solution_id"]
                row["reason"] = "identical raw_hash to the family representative"
            elif row["norm_hash"] is not None and row["norm_hash"] == canon["norm_hash"]:
                row["dedup_level"] = "D2"
                row["related_to"] = canon["solution_id"]
                row["reason"] = "identical name-normalized source (syntax variant only)"
            else:
                row["dedup_level"] = "D3"
                row["related_to"] = canon["solution_id"]
                row["reason"] = (
                    "same PEC set and identical structural profile as the family "
                    "representative (same algorithm family, different implementation)"
                )
            row["dedup_level_name"] = DEDUP_LEVELS[row["dedup_level"]]


def run(reference_artifact: dict) -> dict:
    solutions = reference_artifact["solutions"]
    rows = [compute_keys(s) for s in solutions]
    rows.sort(key=lambda r: r["solution_id"])

    families = []
    for problem_id in sorted({r["problem_id"] for r in rows}):
        members = [r for r in rows if r["problem_id"] == problem_id]
        families.extend(build_families(problem_id, members))
    assign_ladder(rows, families)

    ladder = Counter(r["dedup_level"] for r in rows)
    # D1/D2 classification accuracy: ladder level must agree with hash evidence.
    d1_ok = d2_ok = d1_total = d2_total = 0
    by_id = {r["solution_id"]: r for r in rows}
    for fam in families:
        canon = by_id[fam["canonical_solution_id"]]
        for sid in fam["members"]:
            r = by_id[sid]
            if sid == canon["solution_id"]:
                continue
            if r["raw_hash"] == canon["raw_hash"]:
                d1_total += 1
                d1_ok += (r["dedup_level"] == "D1")
            elif r["norm_hash"] and r["norm_hash"] == canon["norm_hash"]:
                d2_total += 1
                d2_ok += (r["dedup_level"] == "D2")

    return {
        "phase": "2_normalization",
        "normalization_contract": NORMALIZATION_CONTRACT,
        "dedup_ladder_summary": {
            "counts": {k: ladder.get(k, 0) for k in sorted(DEDUP_LEVELS)},
            "level_names": DEDUP_LEVELS,
            "D1_classification": {"correct": d1_ok, "total": d1_total},
            "D2_classification": {"correct": d2_ok, "total": d2_total},
        },
        "solutions": rows,
    }
