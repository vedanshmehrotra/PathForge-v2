"""Phase 5 — held-out validation and cross-problem discrimination.

* 60/40 derivation/held-out split per problem, stratified by family
* groups are derived from the DERIVATION split only, and can only *narrow* the
  independent (editorial) label — the analyzer can never invent a requirement
* evaluation uses the frozen matcher READ-ONLY, on the HELD-OUT split
* a derived group must confirm its own held-out family and reject cross-problem
  negative controls

Rules are NOT adjusted when validation fails; failures are reported.
"""
from .problem_metadata import (
    DERIVATION_FRACTION,
    POC_VERSION,
    PROBLEMS,
    TAXONOMY_VERSION,
)
from .run_shadow import evaluate_with_groups
GROUPS_NOT_DERIVED = {
    "NO_INDEPENDENT_LABEL": "problem has no curated pattern metadata to author a label from",
    "EMPTY_REQUIRED": "analyzer evidence and the editorial label share no required concept",
}


def _split_family(members: list) -> tuple:
    """Deterministic stratified split: derivation / held-out by solution_id."""
    ordered = sorted(members)
    n = len(ordered)
    if n == 1:
        return ordered, []
    deriv_count = round(n * DERIVATION_FRACTION)
    deriv_count = max(1, min(n - 1, deriv_count))
    return ordered[:deriv_count], ordered[deriv_count:]


def build_split(normalized_artifact: dict, group_artifact: dict) -> dict:
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    derivation, held_out, strat = [], [], []
    for fam in group_artifact["families"]:
        d, h = _split_family(fam["members"])
        derivation.extend(d)
        held_out.extend(h)
        strat.append({
            "family_key": fam["family_key"],
            "problem_id": fam["problem_id"],
            "derivation": d,
            "held_out": h,
        })
    overlap = sorted(set(derivation) & set(held_out))
    return {
        "derivation": sorted(derivation),
        "held_out": sorted(held_out),
        "per_family": strat,
        "overlap": overlap,
        "all_members": sorted(rows),
    }


def _labels_for(problem_id: int) -> dict:
    from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING
    required, optional, excluded, unmapped = set(), set(), set(), set()
    for pattern in PROBLEMS.get(problem_id, {}).get("curated_patterns") or []:
        m = PATTERN_TO_V1_MAPPING.get(pattern)
        if m is None:
            unmapped.add(pattern)
            continue
        required.update(m.get("required") or [])
        optional.update(m.get("optional") or [])
        excluded.update(m.get("excluded") or [])
    return {
        "required": sorted(required),
        "optional": sorted(optional),
        "excluded": sorted(excluded),
        "unmapped_patterns": sorted(unmapped),
    }


def derive_groups(normalized_artifact: dict, group_artifact: dict, split: dict) -> tuple:
    """Derive solution groups from the DERIVATION split only."""
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    derivation = set(split["derivation"])
    groups_by_problem = {}
    decisions = []

    for fam in group_artifact["families"]:
        pid = fam["problem_id"]
        label = _labels_for(pid)
        deriv_members = [m for m in fam["members"] if m in derivation]
        entry = {
            "family_key": fam["family_key"],
            "problem_id": pid,
            "derivation_members": deriv_members,
            "label_required": label["required"],
            "label_optional": label["optional"],
            "label_excluded": label["excluded"],
            "unmapped_patterns": label["unmapped_patterns"],
        }
        if not label["required"]:
            entry["derived"] = False
            entry["reason"] = GROUPS_NOT_DERIVED["NO_INDEPENDENT_LABEL"]
            decisions.append(entry)
            continue
        if not deriv_members:
            entry["derived"] = False
            entry["reason"] = "no derivation-split member for this family"
            decisions.append(entry)
            continue

        concept_sets = []
        for sid in deriv_members:
            row = rows[sid]
            concept_sets.append(set(row["technique_signature"]) | set(row["strategy_signature"]))
        intersection = set.intersection(*concept_sets) if concept_sets else set()
        union = set().union(*concept_sets) if concept_sets else set()

        derived_required = sorted(intersection & set(label["required"]))
        entry["member_concepts_intersection"] = sorted(intersection)
        entry["member_concepts_union"] = sorted(union)
        if not derived_required:
            entry["derived"] = False
            entry["reason"] = GROUPS_NOT_DERIVED["EMPTY_REQUIRED"]
            decisions.append(entry)
            continue

        derived_optional = sorted((union - intersection) & set(label["optional"]))
        group = {
            "id": f"{fam['family_key']}_g0",
            "required": derived_required,
            "optional": derived_optional,
            "excluded": list(label["excluded"]),
            "threshold": 0.5,
            "authority_tier": "editorial",
            "problem_id": pid,
            "family_key": fam["family_key"],
        }
        groups_by_problem.setdefault(pid, []).append(group)
        entry["derived"] = True
        entry["reason"] = "derived from derivation split, narrowed by the editorial label"
        entry["derived_required"] = derived_required
        entry["derived_optional"] = derived_optional
        entry["derived_excluded"] = group["excluded"]
        decisions.append(entry)

    return groups_by_problem, decisions


def _evaluate(rows: dict, solution_id: str, groups: list) -> dict:
    row = rows[solution_id]
    outcome = evaluate_with_groups(row["code_text"], groups)
    return outcome


def run(reference_artifact: dict, normalized_artifact: dict, group_artifact: dict) -> dict:
    code_by_id = {s["solution_id"]: s["code_text"] for s in reference_artifact["solutions"]}
    rows = {
        r["solution_id"]: {**r, "code_text": code_by_id[r["solution_id"]]}
        for r in normalized_artifact["solutions"]
    }
    split = build_split(normalized_artifact, group_artifact)
    groups_by_problem, decisions = derive_groups(normalized_artifact, group_artifact, split)

    family_of = {}
    for fam in group_artifact["families"]:
        for sid in fam["members"]:
            family_of[sid] = fam["family_key"]
    group_family = {g["id"]: g["family_key"] for gs in groups_by_problem.values() for g in gs}
    families_with_group = {g["family_key"] for gs in groups_by_problem.values() for g in gs}

    # ---- held-out evaluation -------------------------------------------------
    held_out_results = []
    for sid in split["held_out"]:
        pid = rows[sid]["problem_id"]
        groups = groups_by_problem.get(pid, [])
        outcome = _evaluate(rows, sid, groups)
        held_out_results.append({
            "solution_id": sid,
            "problem_id": pid,
            "family_key": family_of.get(sid),
            "family_has_group": family_of.get(sid) in families_with_group,
            "outcome": outcome["outcome"],
            "satisfied_group_ids": outcome["satisfied_group_ids"],
            "reasoning": outcome["reasoning"],
        })

    # ---- group satisfiability on the derivation split -----------------------
    group_satisfiability = []
    for pid, groups in sorted(groups_by_problem.items()):
        for g in groups:
            fam_members = [m for m in split["derivation"] if family_of.get(m) == g["family_key"]]
            confirmed = []
            for sid in fam_members:
                out = _evaluate(rows, sid, groups)
                if out["outcome"] == "CONFIRMED":
                    confirmed.append(sid)
            group_satisfiability.append({
                "group_id": g["id"],
                "problem_id": pid,
                "family_key": g["family_key"],
                "required": g["required"],
                "derivation_members": fam_members,
                "satisfied_by": confirmed,
                "satisfied": bool(confirmed),
            })

    # ---- metrics ------------------------------------------------------------
    total_held = len(held_out_results)
    confirmed = [r for r in held_out_results if r["outcome"] == "CONFIRMED"]
    unresolved = [r for r in held_out_results if r["outcome"] == "UNRESOLVED"]
    contradicted = [r for r in held_out_results if r["outcome"] == "CONTRADICTED"]
    in_covered_families = [r for r in held_out_results if r["family_has_group"]]
    confirmed_in_covered = [r for r in in_covered_families if r["outcome"] == "CONFIRMED"]

    sat_total = len(group_satisfiability)
    sat_ok = sum(1 for g in group_satisfiability if g["satisfied"])

    # ---- label agreement ----------------------------------------------------
    agreement_rows = []
    for d in decisions:
        if not d.get("derived"):
            continue
        label_req = set(d["label_required"])
        analyzer_req = set(d.get("member_concepts_intersection") or [])
        agreement = (len(analyzer_req & label_req) / len(label_req)) if label_req else None
        agreement_rows.append({
            "family_key": d["family_key"],
            "problem_id": d["problem_id"],
            "label_required": sorted(label_req),
            "analyzer_member_intersection": sorted(analyzer_req),
            "agreement": round(agreement, 4) if agreement is not None else None,
        })
    scored = [a["agreement"] for a in agreement_rows if a["agreement"] is not None]
    label_agreement = round(sum(scored) / len(scored), 4) if scored else None

    # ---- cross-problem negative controls ------------------------------------
    canon_by_problem_family = {}
    for fam in group_artifact["families"]:
        canon_by_problem_family.setdefault(fam["problem_id"], []).append(fam["canonical_solution_id"])

    def controls_for(pid, disjoint_only):
        out = []
        this_patterns = set(PROBLEMS[pid]["curated_patterns"])
        for other_pid, ids in sorted(canon_by_problem_family.items()):
            if other_pid == pid:
                continue
            if disjoint_only and (set(PROBLEMS[other_pid]["curated_patterns"]) & this_patterns):
                continue
            out.extend(ids)
        return out

    def discrimination(disjoint_only):
        tests, hits = 0, []
        for pid, groups in sorted(groups_by_problem.items()):
            for sid in controls_for(pid, disjoint_only):
                tests += 1
                out = _evaluate(rows, sid, groups)
                if out["outcome"] == "CONFIRMED":
                    hits.append({
                        "control_solution_id": sid,
                        "control_problem_id": rows[sid]["problem_id"],
                        "tested_problem_id": pid,
                        "satisfied_group_ids": out["satisfied_group_ids"],
                    })
        return tests, hits

    raw_tests, raw_hits = discrimination(False)
    disj_tests, disj_hits = discrimination(True)

    metrics = {
        "held_out_count": total_held,
        "confirmed": len(confirmed),
        "unresolved": len(unresolved),
        "contradicted": len(contradicted),
        "positive_confirm_rate": round(len(confirmed) / total_held, 4) if total_held else None,
        "unresolved_rate": round(len(unresolved) / total_held, 4) if total_held else None,
        "family_coverage": (
            round(len(confirmed_in_covered) / len(in_covered_families), 4)
            if in_covered_families else None
        ),
        "family_coverage_scope": (
            f"{len(in_covered_families)} held-out solutions belonging to families "
            f"that produced a group (of {total_held} held-out total)"
        ),
        "label_agreement": label_agreement,
        "label_agreement_scope": f"{len(scored)} families with an independent label",
        "group_satisfiability": round(sat_ok / sat_total, 4) if sat_total else None,
        "group_satisfiability_detail": f"{sat_ok}/{sat_total} derived groups confirmed by a derivation member",
        "discrimination_FP_raw": round(len(raw_hits) / raw_tests, 4) if raw_tests else None,
        "discrimination_FP_raw_detail": f"{len(raw_hits)}/{raw_tests} cross-problem control tests",
        "discrimination_FP_disjoint": round(len(disj_hits) / disj_tests, 4) if disj_tests else None,
        "discrimination_FP_disjoint_detail": (
            f"{len(disj_hits)}/{disj_tests} controls from problems with disjoint curated patterns"
        ),
    }

    thresholds = {
        "group_satisfiability": 1.0,
        "discrimination_FP_disjoint": 0.05,
        "family_coverage": 0.85,
        "label_agreement": 0.90,
    }
    failures = []
    if metrics["group_satisfiability"] is None or metrics["group_satisfiability"] < thresholds["group_satisfiability"]:
        failures.append({
            "criterion": "group_satisfiability",
            "required": thresholds["group_satisfiability"],
            "observed": metrics["group_satisfiability"],
            "detail": metrics["group_satisfiability_detail"],
        })
    if metrics["discrimination_FP_disjoint"] is None or metrics["discrimination_FP_disjoint"] > thresholds["discrimination_FP_disjoint"]:
        failures.append({
            "criterion": "discrimination_FP_disjoint",
            "required": f"<= {thresholds['discrimination_FP_disjoint']}",
            "observed": metrics["discrimination_FP_disjoint"],
            "detail": metrics["discrimination_FP_disjoint_detail"],
        })
    if metrics["family_coverage"] is None or metrics["family_coverage"] < thresholds["family_coverage"]:
        failures.append({
            "criterion": "family_coverage",
            "required": thresholds["family_coverage"],
            "observed": metrics["family_coverage"],
            "detail": metrics["family_coverage_scope"],
        })
    if metrics["label_agreement"] is None or metrics["label_agreement"] < thresholds["label_agreement"]:
        failures.append({
            "criterion": "label_agreement",
            "required": thresholds["label_agreement"],
            "observed": metrics["label_agreement"],
            "detail": metrics["label_agreement_scope"],
        })

    return {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "phase": "5_validation",
        "derivation_fraction": DERIVATION_FRACTION,
        "rules_unchanged_on_failure": True,
        "split": {
            "derivation": split["derivation"],
            "held_out": split["held_out"],
            "per_family": split["per_family"],
            "overlap": split["overlap"],
        },
        "derived_groups": {str(k): v for k, v in sorted(groups_by_problem.items())},
        "derivation_decisions": decisions,
        "group_satisfiability": group_satisfiability,
        "held_out_results": held_out_results,
        "label_agreement_detail": agreement_rows,
        "negative_controls": {
            "raw": {"tests": raw_tests, "hits": raw_hits},
            "disjoint_patterns_only": {"tests": disj_tests, "hits": disj_hits},
            "note": (
                "Cross-problem canonical members are used as controls. Controls "
                "from problems sharing a curated pattern set are EXPECTED to "
                "confirm (the same family genuinely occurs in both). "
                "discrimination_FP_disjoint excludes those; the gap between the "
                "two numbers is the POC evidence for OPEN decision O3 "
                "(negative-control strength)."
            ),
        },
        "metrics": metrics,
        "acceptance_thresholds": thresholds,
        "failed_criteria": failures,
        "passed": not failures,
    }
