"""Phase 5a — canonical negative-control rule (spec V2 §6).

For an active group G on problem P, a candidate control solution S on problem Q
is ELIGIBLE iff ALL hold:

  1. Q != P                                       (not a derivation/held-out peer)
  2. curated_patterns(Q) ∩ curated_patterns(P) = ∅ (independent editorial metadata)
  3. PEC_set(S) ∩ PEC_set_of(G) = ∅               (structurally disjoint)
  4. S is not ZERO_EVIDENCE                        (cannot discriminate)

ALL eligible controls are tested exhaustively (no sampling).  A failure is a
control that confirms G.  Every exclusion is counted and reported.
"""
from .problem_metadata import N_MIN_CONTROLS, PROBLEMS
from .run_shadow import evaluate_with_groups


def _curated(pid):
    return set(PROBLEMS.get(pid, {}).get("curated_patterns") or [])


def _pec_of_group(group: dict, pec_concepts: set) -> set:
    return {c for c in group["required"] if c in pec_concepts}


def run(reference_artifact: dict, normalized_artifact: dict, derive_artifact: dict,
        pec_concepts: set, n_min: int = N_MIN_CONTROLS) -> dict:
    code = {s["solution_id"]: s["code_text"] for s in reference_artifact["solutions"]}
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    groups_by_problem = {int(k): v for k, v in derive_artifact["groups_by_problem"].items()}

    # candidate controls = every reference solution (any problem)
    all_ids = sorted(rows)
    curated_cache = {pid: _curated(pid) for pid in PROBLEMS}

    per_group = []
    total_eligible = total_failed = 0
    total_eligible_no_rule3 = total_failed_no_rule3 = 0
    same_family_reuse = 0
    excluded_by_rule = {"same_problem": 0, "same_curated_patterns": 0,
                        "pec_overlap": 0, "zero_evidence": 0}

    for pid, groups in sorted(groups_by_problem.items()):
        for group in groups:
            g_pec = _pec_of_group(group, pec_concepts)
            eligible, eligible_no3 = [], []
            for sid in all_ids:
                q = rows[sid]["problem_id"]
                if q == pid:
                    excluded_by_rule["same_problem"] += 1
                    continue
                if curated_cache[q] & curated_cache[pid]:
                    excluded_by_rule["same_curated_patterns"] += 1
                    continue
                if rows[sid]["zero_evidence"]:
                    excluded_by_rule["zero_evidence"] += 1
                    continue
                if set(rows[sid]["pec_set"]) & g_pec:
                    excluded_by_rule["pec_overlap"] += 1
                    same_family_reuse += 1
                    eligible_no3.append(sid)
                    continue
                eligible.append(sid)
                eligible_no3.append(sid)

            # Each group is tested IN ISOLATION: the production matcher reports
            # only the single best satisfied group id, so per-group
            # discrimination must not be answered from a group-list evaluation.
            hits = []
            for sid in eligible:
                out = evaluate_with_groups(code[sid], [group])
                if out["outcome"] == "CONFIRMED":
                    hits.append({
                        "control_solution_id": sid,
                        "control_problem_id": rows[sid]["problem_id"],
                        "control_pec_set": rows[sid]["pec_set"],
                    })
            # variant without rule 3, for OPEN-5
            hits_no3 = 0
            for sid in eligible_no3:
                out = evaluate_with_groups(code[sid], [group])
                if out["outcome"] == "CONFIRMED":
                    hits_no3 += 1

            insufficient = len(eligible) < n_min
            if not insufficient:
                total_eligible += len(eligible)
                total_failed += len(hits)
                total_eligible_no_rule3 += len(eligible_no3)
                total_failed_no_rule3 += hits_no3

            per_group.append({
                "group_id": group["id"],
                "problem_id": pid,
                "family_key": group["family_key"],
                "required": group["required"],
                "pec_set_of_group": sorted(g_pec),
                "eligible_controls": len(eligible),
                "tested_controls": len(eligible),
                "failures": len(hits),
                "failure_detail": hits,
                "same_family_reuse_count": len(eligible_no3) - len(eligible),
                "without_rule3_eligible": len(eligible_no3),
                "without_rule3_failures": hits_no3,
                "insufficient_controls": insufficient,
            })

    return {
        "phase": "5a_negative_controls",
        "rule": {
            "eligibility": [
                "different problem",
                "disjoint curated problem patterns",
                "structurally disjoint PEC set",
                "not ZERO_EVIDENCE",
            ],
            "exclusions_counted": True,
            "sampling": "exhaustive (no random draw)",
            "n_min": n_min,
            "n_min_status": "PROVISIONAL (OPEN-5)",
        },
        "excluded_by_rule": excluded_by_rule,
        "same_family_reuse_count": same_family_reuse,
        "insufficient_controls_groups": [g["group_id"] for g in per_group if g["insufficient_controls"]],
        "totals": {
            "eligible_pairs": total_eligible,
            "failing_pairs": total_failed,
            "discrimination_FP": round(total_failed / total_eligible, 4) if total_eligible else None,
            "eligible_pairs_without_rule3": total_eligible_no_rule3,
            "failing_pairs_without_rule3": total_failed_no_rule3,
            "discrimination_FP_without_rule3": (
                round(total_failed_no_rule3 / total_eligible_no_rule3, 4)
                if total_eligible_no_rule3 else None
            ),
        },
        "per_group": per_group,
    }
