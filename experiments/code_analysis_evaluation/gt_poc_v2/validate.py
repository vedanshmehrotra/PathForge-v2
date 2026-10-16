"""Phase 5b — V2 validation (spec V2 §7).

Family-first, problem-scoped, deterministic split:

    n >= 3 : held_out = ceil(0.4 * n), derivation >= 1
    n == 2 : 1 derivation, 1 held-out
    n == 1 : derivation only, family flagged VALIDATION_LIMITED

Groups are derived from the derivation split; evaluation uses the frozen matcher
READ-ONLY on the held-out split.  No solution appears in both sets.

A `held_out_population >= 3 * problems` gate is enforced before any acceptance
criterion may be claimed met (V2 §7.4).
"""
import math

from .labeling import ALL_STATES
from .problem_metadata import HELD_OUT_FRACTION, HELD_OUT_POPULATION_MULTIPLIER
from .run_shadow import evaluate_with_groups


def build_split(group_artifact: dict) -> dict:
    derivation, held_out, per_family = [], [], []
    for fam in group_artifact["families"]:
        members = sorted(fam["members"], key=lambda s: (fam["members"], s))  # stable fallback
        # order by raw_hash deterministically
        members = sorted(fam["members"])
        n = len(members)
        if n == 1:
            d, h = members, []
            state = "VALIDATION_LIMITED"
        elif n == 2:
            d, h = [members[0]], [members[1]]
            state = "OK"
        else:
            k = math.ceil(HELD_OUT_FRACTION * n)
            k = max(1, min(n - 1, k))
            h = members[:k]
            d = members[k:]
            state = "OK"
        derivation.extend(d)
        held_out.extend(h)
        per_family.append({
            "family_key": fam["family_key"],
            "problem_id": fam["problem_id"],
            "n": n,
            "derivation": d,
            "held_out": h,
            "state": state,
        })
    overlap = sorted(set(derivation) & set(held_out))
    return {
        "derivation": sorted(derivation),
        "held_out": sorted(held_out),
        "per_family": per_family,
        "overlap": overlap,
        "limited_families": [f["family_key"] for f in per_family if f["state"] == "VALIDATION_LIMITED"],
    }


def run(reference_artifact: dict, normalized_artifact: dict, group_artifact: dict,
        label_artifact: dict, derive_artifact: dict, controls_artifact: dict) -> dict:
    code = {s["solution_id"]: s["code_text"] for s in reference_artifact["solutions"]}
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    families = group_artifact["families"]
    groups_by_problem = {int(k): v for k, v in derive_artifact["groups_by_problem"].items()}
    family_of = {sid: fam["family_key"] for fam in families for sid in fam["members"]}
    active_family_keys = {o["family_key"] for o in derive_artifact["outcomes"] if o["activated"]}
    group_family = {g["id"]: g["family_key"] for gs in groups_by_problem.values() for g in gs}

    split = build_split(group_artifact)
    held_out_population = len(split["held_out"])
    problems = sorted({r["problem_id"] for r in rows.values()})

    group_by_family = {g["family_key"]: g for gs in groups_by_problem.values() for g in gs}

    # ---- held-out evaluation -------------------------------------------------
    held_out_results = []
    for sid in split["held_out"]:
        pid = rows[sid]["problem_id"]
        fam_key = family_of.get(sid)
        groups = groups_by_problem.get(pid, [])
        # production-style outcome against the whole group list for the problem
        out = evaluate_with_groups(code[sid], groups)
        # own-family group, tested in isolation (correct per-group coverage test)
        own_group = group_by_family.get(fam_key)
        own_confirmed = False
        if own_group is not None:
            own_out = evaluate_with_groups(code[sid], [own_group])
            own_confirmed = own_out["outcome"] == "CONFIRMED"
        held_out_results.append({
            "solution_id": sid,
            "problem_id": pid,
            "family_key": fam_key,
            "family_active": fam_key in active_family_keys,
            "own_group_id": own_group["id"] if own_group else None,
            "own_group_confirmed": own_confirmed,
            "zero_evidence": rows[sid]["zero_evidence"],
            "outcome": out["outcome"],
            "satisfied_group_ids": out["satisfied_group_ids"],
        })

    # ---- group satisfiability on the derivation split -----------------------
    group_satisfiability = []
    for pid, groups in sorted(groups_by_problem.items()):
        for g in groups:
            fam_members = [m for m in split["derivation"] if family_of.get(m) == g["family_key"]]
            confirmed = []
            for sid in fam_members:
                # Test the group IN ISOLATION: the production matcher reports
                # only the single best satisfied group id, so a group-list
                # evaluation cannot answer "is THIS group satisfied?".
                out = evaluate_with_groups(code[sid], [g])
                if out["outcome"] == "CONFIRMED":
                    confirmed.append(sid)
            group_satisfiability.append({
                "group_id": g["id"],
                "problem_id": pid,
                "family_key": g["family_key"],
                "required": g["required"],
                "derivation_members": fam_members,
                "satisfied_by": confirmed,
                "satisfied_by_all": bool(fam_members) and len(confirmed) == len(fam_members),
            })

    # ---- metrics ------------------------------------------------------------
    total_held = held_out_population
    confirmed = [r for r in held_out_results if r["outcome"] == "CONFIRMED"]
    unresolved = [r for r in held_out_results if r["outcome"] == "UNRESOLVED"]
    contradicted = [r for r in held_out_results if r["outcome"] == "CONTRADICTED"]
    covered = [r for r in held_out_results if r["family_active"]]
    covered_non_zero = [r for r in covered if not r["zero_evidence"]]
    confirmed_covered = [r for r in covered_non_zero if r["own_group_confirmed"]]

    sat_total = len(group_satisfiability)
    sat_ok = sum(1 for g in group_satisfiability if g["satisfied_by_all"])

    singleton = sum(1 for f in families if f["is_singleton"])
    fam_per_problem = {}
    for f in families:
        fam_per_problem[f["problem_id"]] = fam_per_problem.get(f["problem_id"], 0) + 1
    max_fam_per_problem = max(fam_per_problem.values()) if fam_per_problem else 0

    # ZERO_EVIDENCE handling
    zero_ids = [sid for sid, r in rows.items() if r["zero_evidence"]]
    zero_held = [r for r in held_out_results if r["zero_evidence"]]
    zero_confirmed = [r for r in zero_held if r["outcome"] == "CONFIRMED"]
    zero_labeled = [f for f in families if f["zero_evidence"] and f["family_key"] in active_family_keys]
    zero_controls = [c for c in controls_artifact["per_group"]
                     if any(d["control_solution_id"] in zero_ids for d in c["failure_detail"])]

    d1 = normalized_artifact["dedup_ladder_summary"]["D1_classification"]
    d2 = normalized_artifact["dedup_ladder_summary"]["D2_classification"]

    state_distribution = derive_artifact["divergence_state_counts"]
    for s in ALL_STATES:
        state_distribution.setdefault(s, 0)

    held_out_gate = held_out_population >= HELD_OUT_POPULATION_MULTIPLIER * len(problems)

    metrics = {
        "singleton_families": singleton,
        "family_count": len(families),
        "singleton_rate": round(singleton / len(families), 4) if families else None,
        "families_per_problem": fam_per_problem,
        "max_families_per_problem": max_fam_per_problem,
        "held_out_population": held_out_population,
        "held_out_population_gate": HELD_OUT_POPULATION_MULTIPLIER * len(problems),
        "held_out_population_gate_met": held_out_gate,
        "derivation_population": len(split["derivation"]),
        "limited_families": len(split["limited_families"]),
        "confirmed": len(confirmed),
        "unresolved": len(unresolved),
        "contradicted": len(contradicted),
        "positive_confirm_rate": round(len(confirmed) / total_held, 4) if total_held else None,
        "unresolved_rate": round(len(unresolved) / total_held, 4) if total_held else None,
        "family_coverage": (
            round(len(confirmed_covered) / len(covered_non_zero), 4)
            if covered_non_zero else None
        ),
        "family_coverage_scope": (
            f"{len(confirmed_covered)} confirmed of {len(covered_non_zero)} non-zero-evidence "
            f"held-out solutions in families that activated a group"
        ),
        "group_satisfiability": round(sat_ok / sat_total, 4) if sat_total else None,
        "group_satisfiability_detail": f"{sat_ok}/{sat_total} active groups confirmed by all derivation members",
        "activation_rate": derive_artifact["totals"]["activation_rate"],
        "activated_groups": derive_artifact["totals"]["activated_groups"],
        "narrowing_violations": derive_artifact["totals"]["narrowing_violations"],
        "discrimination_FP": controls_artifact["totals"]["discrimination_FP"],
        "discrimination_FP_detail": (
            f"{controls_artifact['totals']['failing_pairs']}/"
            f"{controls_artifact['totals']['eligible_pairs']} eligible control pairs"
        ),
        "D1_classification": d1,
        "D2_classification": d2,
        "zero_evidence_solutions": len(zero_ids),
        "zero_evidence_held_out": len(zero_held),
        "zero_evidence_confirmed": len(zero_confirmed),
        "zero_evidence_labeled": len(zero_labeled),
        "zero_evidence_controls": len(zero_controls),
        "divergence_distribution": state_distribution,
        "approved_family_labels": label_artifact["totals"]["approved"],
    }

    # ---- acceptance criteria (V2 §12.5) -------------------------------------
    crit = []

    def add(name, gate, observed, ok, detail=""):
        crit.append({"criterion": name, "gate": gate, "observed": observed,
                     "met": bool(ok), "detail": detail})

    add("singleton_families_rate", "<= 0.25", metrics["singleton_rate"],
        metrics["singleton_rate"] is not None and metrics["singleton_rate"] <= 0.25,
        f"{singleton} of {len(families)}")
    add("families_per_problem", "<= 4", max_fam_per_problem, max_fam_per_problem <= 4,
        f"max {max_fam_per_problem}")
    add("held_out_population", f">= {HELD_OUT_POPULATION_MULTIPLIER * len(problems)}",
        held_out_population, held_out_gate)
    add("discrimination_FP", "<= 0.05", metrics["discrimination_FP"],
        metrics["discrimination_FP"] is not None and metrics["discrimination_FP"] <= 0.05,
        metrics["discrimination_FP_detail"])
    add("group_satisfiability", "= 1.00", metrics["group_satisfiability"],
        metrics["group_satisfiability"] == 1.0, metrics["group_satisfiability_detail"])
    add("narrowing_violations", "= 0", metrics["narrowing_violations"],
        metrics["narrowing_violations"] == 0)
    add("family_coverage", ">= 0.85", metrics["family_coverage"],
        metrics["family_coverage"] is not None and metrics["family_coverage"] >= 0.85,
        metrics["family_coverage_scope"])
    add("D1_exercised", ">= 3 correct", d1, d1["total"] >= 3 and d1["correct"] == d1["total"])
    add("D2_exercised", ">= 3 correct", d2, d2["total"] >= 3 and d2["correct"] == d2["total"])
    add("ZERO_EVIDENCE_handled", "3 cases, none confirmed/labeled/control",
        {"solutions": len(zero_ids), "confirmed": len(zero_confirmed),
         "labeled": len(zero_labeled), "controls": len(zero_controls)},
        len(zero_ids) >= 3 and not zero_confirmed and not zero_labeled and not zero_controls)
    add("approved_family_labels", ">= 6", metrics["approved_family_labels"],
        metrics["approved_family_labels"] >= 6,
        "human review unavailable in this environment (PA1)")

    if not held_out_gate:
        for c in crit:
            c["met_under_gate"] = False
        overall_state = "INSUFFICIENT_VALIDATION"
    else:
        for c in crit:
            c["met_under_gate"] = c["met"]
        overall_state = "VALIDATED" if all(c["met"] for c in crit) else "VALIDATION_FAILED"

    return {
        "phase": "5b_validation",
        "overall_state": overall_state,
        "rules_unchanged_on_failure": True,
        "split": {"derivation": split["derivation"], "held_out": split["held_out"],
                  "per_family": split["per_family"], "overlap": split["overlap"],
                  "limited_families": split["limited_families"]},
        "held_out_results": held_out_results,
        "group_satisfiability": group_satisfiability,
        "metrics": metrics,
        "acceptance_criteria": crit,
        "failed_criteria": [c["criterion"] for c in crit if not c["met"]],
    }
