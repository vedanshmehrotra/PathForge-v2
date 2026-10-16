"""Phase 4b — derivation of solution groups (spec V2 §4 + §5).

    L = approved family-label required concepts
    O = concepts observed by EVERY family member (intersection)

    if  L == empty        -> NO_GROUP
    if  L subset of O     -> required = L            (never narrowed)
    if  L disjoint from O -> NO_GROUP (UNEXPRESSIBLE)
    else (partial)        -> NO_GROUP (REVIEW_REQUIRED)

The specificity floor (V2 §4.3) is already encoded in the divergence state: a
label whose required set is entirely SUPPORT-tier is `LABEL_GENERIC` and is NOT
activated.  A partial observation is NEVER resolved by narrowing to the observed
subset — it is surfaced for review.
"""
from .labeling import ALL_STATES, STATE_LABEL_OK, STATE_ZERO_EVIDENCE
from .problem_metadata import (
    ACTIVATABLE_APPROVAL_STATES,
    LABEL_MODE_PROVISIONAL,
    LABEL_MODE_STRICT,
    PROVISIONAL_ASSUMPTION_PA1,
)

ACTIVATION_REASONS = {
    "not_approved": "family label is not in an activatable approval state for this run",
    "zero_evidence": "ZERO_EVIDENCE family can never activate a group (V2 §9)",
    "state_not_ok": "divergence state is not LABEL_OK (refusal, not narrowing)",
    "activated": "required = L (label-faithful); specificity floor passed",
}


def derive(normalized_artifact: dict, group_artifact: dict, label_artifact: dict,
           label_mode: str = LABEL_MODE_PROVISIONAL) -> dict:
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    labels = {e["family_key"]: e for e in label_artifact["entries"]}
    activatable = ACTIVATABLE_APPROVAL_STATES[label_mode]

    outcomes = []
    groups_by_problem = {}
    state_counts = {s: 0 for s in ALL_STATES}

    for fam in group_artifact["families"]:
        e = labels[fam["family_key"]]
        state_counts[e["divergence_state"]] = state_counts.get(e["divergence_state"], 0) + 1
        L = list(e["proposed_label"]["required"])
        O = observed_intersection(rows, fam["members"])
        U = observed_union(rows, fam["members"])

        entry = {
            "family_key": fam["family_key"],
            "problem_id": fam["problem_id"],
            "label_source": e["proposed_label"]["label_source"],
            "approval_state": e["approval_state"],
            "divergence_state": e["divergence_state"],
            "label_required": L,
            "observed_intersection": O,
            "observed_union": U,
            "required_expected": list(e["proposed_label"].get("required_expected") or []),
        }

        if e["approval_state"] not in activatable:
            entry.update({"activated": False, "reason": ACTIVATION_REASONS["not_approved"]})
            outcomes.append(entry)
            continue
        if fam["zero_evidence"] or e["divergence_state"] == STATE_ZERO_EVIDENCE:
            entry.update({"activated": False, "reason": ACTIVATION_REASONS["zero_evidence"]})
            outcomes.append(entry)
            continue
        if e["divergence_state"] != STATE_LABEL_OK:
            entry.update({"activated": False, "reason": ACTIVATION_REASONS["state_not_ok"]})
            outcomes.append(entry)
            continue

        # LABEL_OK -> required = L, never narrowed.
        required = sorted(L)
        label = e["proposed_label"]
        optional_pool = set(label["optional"]) | {c for c in U if _tier(rows, fam, c) == "SUPPORT"}
        optional = sorted((set(U) - set(required)) & optional_pool)
        excluded = sorted(label["excluded"])

        group = {
            "id": f"{fam['family_key']}_g0",
            "problem_id": fam["problem_id"],
            "family_key": fam["family_key"],
            "required": required,
            "optional": optional,
            "excluded": excluded,
            "threshold": 0.5,
            "authority_tier": "editorial",
        }
        groups_by_problem.setdefault(fam["problem_id"], []).append(group)
        entry.update({
            "activated": True,
            "reason": ACTIVATION_REASONS["activated"],
            "required": required,
            "optional": optional,
            "excluded": excluded,
            "group_id": group["id"],
            "narrowing": bool(set(required) != set(L)),
        })
        outcomes.append(entry)

    activated = [o for o in outcomes if o["activated"]]
    narrowing_violations = [o for o in activated if o.get("narrowing")]
    labelable = [o for o in outcomes if o["label_required"]]

    return {
        "phase": "4b_derivation",
        "label_mode": label_mode,
        "provisional_assumption": PROVISIONAL_ASSUMPTION_PA1 if label_mode == LABEL_MODE_PROVISIONAL else None,
        "activatable_approval_states": sorted(activatable),
        "rules": {
            "never_narrow": "required = L when L subset of O; never a subset of L",
            "partial_is_refusal": "L not subset of O and L intersect O non-empty -> no group",
            "disjoint_is_refusal": "L intersect O empty -> NO_GROUP / UNEXPRESSIBLE",
            "specificity_floor": "required made only of SUPPORT concepts -> LABEL_GENERIC, no group",
        },
        "divergence_state_counts": state_counts,
        "totals": {
            "families": len(outcomes),
            "activated_groups": len(activated),
            "labelable_families": len(labelable),
            "activation_rate": round(len(activated) / len(labelable), 4) if labelable else None,
            "narrowing_violations": len(narrowing_violations),
        },
        "outcomes": outcomes,
        "groups_by_problem": {str(k): v for k, v in sorted(groups_by_problem.items())},
    }


def _tier(rows: dict, fam: dict, concept: str) -> str:
    for sid in fam["members"]:
        t = rows[sid]["concept_tiers"].get(concept)
        if t:
            return t
    return "SUPPORT"


def observed_intersection(rows: dict, members: list) -> list:
    sets = [set(rows[m]["concepts"]) for m in members]
    return sorted(set.intersection(*sets)) if sets else []


def observed_union(rows: dict, members: list) -> list:
    sets = [set(rows[m]["concepts"]) for m in members]
    return sorted(set().union(*sets)) if sets else []
