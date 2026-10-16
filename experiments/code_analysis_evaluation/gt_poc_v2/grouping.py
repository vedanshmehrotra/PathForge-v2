"""Phase 3 — V2 family grouping (spec V2 §1, stages S1–S4).

    solutions
      -> S1  concept tiers          (classify every concept PEC / SUPPORT)
      -> S2  primary partition      by PEC set  (SUPPORT never partitions)
      -> S3  structural-profile refinement  (coarse 5-tuple; NOT edit distance)
      -> S4  deterministic agglomeration + PEC_SUBSET_MERGE anti-split guard

Skeleton distance is NEVER consulted when deciding a boundary.  It is used only
for representative selection and as a diagnostic (``skeleton_spread``).
"""
from collections import Counter

from .core import PROFILE_DIMENSIONS, profile_tuple, skeleton_distance

GROUPING_ALGORITHM = {
    "S1_concept_tiers": (
        "every technique/strategy id is PEC (may partition) or SUPPORT (never "
        "partitions); ids in neither set default to SUPPORT"
    ),
    "S2_primary_partition": "bucket by (frozenset(PEC concepts), zero_evidence flag)",
    "S3_profile_refinement": (
        "within a PEC bucket, split by the coarse 5-tuple "
        "(recursion, loop_shape, container, map_kind, iterates_collection)"
    ),
    "S4_agglomeration": (
        "PEC_SUBSET_MERGE: identical profile + non-empty subset PEC relation "
        "=> merge; deterministic tie-break by smallest sorted PEC tuple"
    ),
    "skeleton_role": (
        "representative selection + skeleton_spread diagnostic ONLY; never a "
        "family split trigger (V2 §2)"
    ),
    "ordering": "members sorted by solution_id; families numbered by smallest member id",
}


def _merge_reason(pec_a, pec_b) -> str:
    if pec_a == pec_b:
        return "profile_equal"
    if pec_a and pec_a < pec_b:
        return "pec_subset"
    if pec_b and pec_b < pec_a:
        return "pec_subset"
    return "profile_equal"


def build_families(problem_id: int, members: list) -> list:
    """Group one problem's normalized rows into V2 families (deterministic)."""
    ordered = sorted(members, key=lambda m: m["solution_id"])

    # ---- S2 (+S3): candidate families -----------------------------------
    candidate = {}
    for m in ordered:
        pec = frozenset(m["pec_set"])
        key = (tuple(sorted(pec)), bool(m["zero_evidence"]), profile_tuple(m["profile"]))
        candidate.setdefault(key, []).append(m)
    cand_keys = sorted(candidate.keys(), key=lambda k: min(x["solution_id"] for x in candidate[k]))

    # ---- S4: PEC_SUBSET_MERGE across candidate families ------------------
    n = len(cand_keys)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    merges = []
    for i in range(n):
        for j in range(i + 1, n):
            ki, kj = cand_keys[i], cand_keys[j]
            pec_i, ze_i, prof_i = ki
            pec_j, ze_j, prof_j = kj
            if ze_i != ze_j or prof_i != prof_j:
                continue
            set_i, set_j = set(pec_i), set(pec_j)
            if set_i and set_i < set_j:
                union(i, j)
                merges.append({"a_pec": sorted(set_i), "b_pec": sorted(set_j),
                               "merged_because": "pec_subset"})
            elif set_j and set_j < set_i:
                union(i, j)
                merges.append({"a_pec": sorted(set_j), "b_pec": sorted(set_i),
                               "merged_because": "pec_subset"})

    buckets = {}
    for i, k in enumerate(cand_keys):
        buckets.setdefault(find(i), []).append(k)

    groups = sorted(buckets.values(), key=lambda ks: min(
        x["solution_id"] for k in ks for x in candidate[k]
    ))

    families = []
    for idx, ks in enumerate(groups, start=1):
        mem = [x for k in ks for x in candidate[k]]
        mem.sort(key=lambda m: m["solution_id"])
        pec_union = sorted({c for m in mem for c in m["pec_set"]})
        support_union = sorted({c for m in mem for c in m["support_set"]})
        profile = {d: mem[0]["profile"][d] for d in PROFILE_DIMENSIONS}
        # representative = member with smallest skeleton distance to the
        # medoid of the bucket (ties broken by solution_id)
        rep = _choose_representative(mem)
        spread = _skeleton_spread(mem)
        subset_merges = [m for m in merges if set(m["a_pec"]) & set(pec_union) or
                         set(m["b_pec"]) & set(pec_union)]
        merged_because = sorted({m["merged_because"] for m in subset_merges}) or []
        families.append({
            "problem_id": problem_id,
            "family_key": f"lc{problem_id}_fam{idx}",
            "members": [m["solution_id"] for m in mem],
            "member_count": len(mem),
            "canonical_solution_id": rep["solution_id"],
            "pec_set": pec_union,
            "support_set": support_union,
            "structural_profile": profile,
            "zero_evidence": bool(mem[0]["zero_evidence"]),
            "merged_because": merged_because,
            "grouping_reason": (
                "zero-evidence: no PEC or SUPPORT concept observed"
                if mem[0]["zero_evidence"] else
                ("merged across PEC subsets with an identical structural profile"
                 if merged_because else
                 ("singleton: no other solution shares this PEC set and profile"
                  if len(mem) == 1 else
                  "shared PEC set and identical structural profile"))
            ),
            "skeleton_spread": spread,
            "is_singleton": len(mem) == 1,
            "sources": sorted({m.get("source_type") for m in mem}),
        })
    return families


def _choose_representative(mem: list):
    """Smallest skeleton distance to the bucket medoid; ties by solution_id."""
    if len(mem) == 1:
        return mem[0]
    toks = {m["solution_id"]: m["skeleton_tokens"] for m in mem}
    best = None
    best_key = None
    for m in mem:
        total = 0.0
        for other in mem:
            if other["solution_id"] == m["solution_id"]:
                continue
            total += skeleton_distance(toks[m["solution_id"]], toks[other["solution_id"]])
        key = (round(total, 6), m["solution_id"])
        if best_key is None or key < best_key:
            best, best_key = m, key
    return best


def _skeleton_spread(mem: list) -> dict:
    """Diagnostic: pairwise normalized skeleton distance range within a family."""
    if len(mem) < 2:
        return {"min": 0.0, "max": 0.0, "pairs": 0}
    ds = []
    for i, a in enumerate(mem):
        for b in mem[i + 1:]:
            ds.append(skeleton_distance(a["skeleton_tokens"], b["skeleton_tokens"]))
    return {"min": round(min(ds), 4), "max": round(max(ds), 4), "pairs": len(ds)}


def run(normalized_artifact: dict) -> dict:
    rows = normalized_artifact["solutions"]
    families = []
    for problem_id in sorted({r["problem_id"] for r in rows}):
        members = [r for r in rows if r["problem_id"] == problem_id]
        families.extend(build_families(problem_id, members))

    sizes = Counter(f["member_count"] for f in families)
    by_problem = {}
    for f in families:
        by_problem.setdefault(str(f["problem_id"]), []).append(f["family_key"])

    return {
        "phase": "3_grouping_v2",
        "grouping_algorithm": GROUPING_ALGORITHM,
        "totals": {
            "family_count": len(families),
            "singleton_families": sum(1 for f in families if f["is_singleton"]),
            "family_size_histogram": {str(k): v for k, v in sorted(sizes.items())},
            "families_by_problem": by_problem,
        },
        "families": families,
    }
