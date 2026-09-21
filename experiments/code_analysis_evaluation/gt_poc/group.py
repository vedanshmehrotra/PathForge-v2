"""Phase 3 — deterministic solution-family grouping.

Implementation of spec §8 steps 1–4:

  1. primary partition by technique/strategy signature class
  2. skeleton refinement (token-level distance < tau)
  3. deterministic tie-break — none required (no randomness in 1–2)
  4. anti-split guard — realized as component connectivity: any D1/D2/D3 link
     merges members, so a pure D2/D3 difference can never create a split.

The LLM merge/split proposal stage (spec §8 step 5) is deliberately NOT
implemented in this POC.
"""
from collections import Counter

from .core import PIPELINE_VERSION, build_families
from .problem_metadata import POC_VERSION, PROVISIONAL_SKELETON_TAU, PROVISIONAL_TAU_RATIONALE, TAXONOMY_VERSION

GROUPING_ALGORITHM = {
    "primary_partition": "exact equality of signature_class = sorted(technique_ids | strategy_ids)",
    "refinement": "split when normalized skeleton token distance >= tau",
    "tie_break": "none needed (deterministic; no randomness, no clustering pass invoked)",
    "anti_split_guard": "union-find connectivity: a D1/D2/D3 link always merges",
    "llm_proposals": "NOT run in this POC (spec §8 step 5 deferred)",
    "ordering": "members sorted by solution_id; families numbered by smallest member id",
}


def run(normalized_artifact: dict, tau: float = PROVISIONAL_SKELETON_TAU) -> dict:
    rows = normalized_artifact["solutions"]
    families = []
    for problem_id in sorted({r["problem_id"] for r in rows}):
        members = [r for r in rows if r["problem_id"] == problem_id]
        families.extend(build_families(problem_id, members, tau))

    by_id = {r["solution_id"]: r for r in rows}
    out_families = []
    for fam in families:
        canon = by_id[fam["canonical_solution_id"]]
        member_rows = [by_id[s] for s in fam["members"]]
        # pairwise link detail, for auditability of every grouping decision
        links = []
        for i, a in enumerate(member_rows):
            for b in member_rows[i + 1:]:
                from .core import skeleton_distance
                links.append({
                    "a": a["solution_id"],
                    "b": b["solution_id"],
                    "same_signature_class": a["signature_class"] == b["signature_class"],
                    "skeleton_distance": round(
                        skeleton_distance(a["skeleton_tokens"], b["skeleton_tokens"]), 4
                    ),
                })
        singleton = len(member_rows) == 1
        out_families.append({
            "problem_id": fam["problem_id"],
            "family_key": fam["family_key"],
            "members": fam["members"],
            "member_count": fam["member_count"],
            "canonical_solution_id": fam["canonical_solution_id"],
            "technique_signature": fam["technique_signature"],
            "strategy_signature": fam["strategy_signature"],
            "signature_class": fam["signature_class"],
            "skeleton_metadata": {
                "canonical_skeleton": canon["skeleton"],
                "canonical_token_count": len(canon["skeleton_tokens"]),
                "max_intra_skeleton_distance": fam["max_intra_skeleton_distance"],
            },
            "provisional_threshold": tau,
            "grouping_reason": (
                "singleton: no other solution shares this signature class within "
                "the threshold, so it forms its own family"
                if singleton else
                "connected by signature-class equality plus at least one "
                "skeleton distance below the threshold; no D2/D3-only split "
                "was allowed (anti-split guard)"
            ),
            "is_singleton": singleton,
            "sources": sorted({by_id[s]["source_type"] for s in fam["members"]}),
            "member_relations": links,
        })

    sizes = Counter(f["member_count"] for f in out_families)
    by_problem = {}
    for f in out_families:
        by_problem.setdefault(str(f["problem_id"]), []).append(f["family_key"])

    return {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "phase": "3_grouping",
        "provisional_skeleton_threshold": tau,
        "provisional_threshold_rationale": PROVISIONAL_TAU_RATIONALE,
        "grouping_algorithm": GROUPING_ALGORITHM,
        "totals": {
            "family_count": len(out_families),
            "singleton_families": sum(1 for f in out_families if f["is_singleton"]),
            "family_size_histogram": {str(k): v for k, v in sorted(sizes.items())},
            "families_by_problem": by_problem,
        },
        "families": out_families,
    }
