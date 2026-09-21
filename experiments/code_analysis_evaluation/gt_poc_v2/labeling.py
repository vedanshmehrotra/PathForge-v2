"""Phase 4 — V2 family-level labeling (spec V2 §3 + §5).

Core rule: ``problem label != automatic family label``.

Label channels, in precedence order (V2 §3.3):
  1. ``curated_family``  — an editorial annotation attached to *that family*
     (the POC ships a small authored set, marked ``PENDING_REVIEW``; channel 1
     otherwise requires a human reviewer).
  2. ``curated_problem`` — ``problems.pattern`` mapped through the frozen
     ``PATTERN_TO_V1_MAPPING``, applied to a family ONLY if the §3.4 consistency
     screen passes.
  (3) ``human_review`` and (4) ``llm_proposed_offline`` are not available in
      this environment and are reported as OPEN.)

Reviewer blinding (V2 §3.6): the reviewer-facing artifacts must NOT show the
analyzer's technique/strategy detections.  They are written only to the
post-hoc ``label_comparison.json``.  Nothing is auto-approved.
"""
from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING

from .problem_metadata import CURATED_PATTERN_SOURCE, PROBLEMS

# Divergence / label states (V2 §5.2 + §9).
STATE_LABEL_OK = "LABEL_OK"
STATE_LABEL_GENERIC = "LABEL_GENERIC"
STATE_LABEL_PARTIAL = "LABEL_PARTIAL"
STATE_LABEL_UNEXPRESSIBLE = "LABEL_UNEXPRESSIBLE"
STATE_LABEL_MULTI_OVERLAP = "LABEL_MULTI_OVERLAP"
STATE_NO_LABEL = "NO_INDEPENDENT_LABEL"
STATE_ZERO_EVIDENCE = "ZERO_EVIDENCE"
STATE_REVIEW_SCREEN_FAILED = "REVIEW_REQUIRED_SCREEN_FAILED"

ALL_STATES = (
    STATE_LABEL_OK, STATE_LABEL_GENERIC, STATE_LABEL_PARTIAL,
    STATE_LABEL_UNEXPRESSIBLE, STATE_LABEL_MULTI_OVERLAP,
    STATE_NO_LABEL, STATE_ZERO_EVIDENCE, STATE_REVIEW_SCREEN_FAILED,
)

APPROVAL_PENDING = "PENDING_REVIEW"

# ---------------------------------------------------------------------------
# Channel 1 — authored family proposals (editorial; family-level).
#
# Keyed by an exact sorted tuple of member ``local_key`` values so it is stable
# and cannot accidentally apply to a different family.  These are PROPOSALS
# only: ``approval_state`` stays PENDING_REVIEW, never APPROVED.
# ---------------------------------------------------------------------------
AUTHORED_FAMILY_PROPOSALS = [
    {
        "problem_id": 3236,
        "member_local_keys": [
            "db_sub_194", "db_sub_49", "db_sub_51", "missing_scalar",
            "missing_scalar_alt", "missing_scalar_renamed", "missing_set_scalar",
        ],
        "label_source": "authored_family_proposal",
        "rationale": (
            "LC 3236 has no curated problem pattern; the scalar running-total "
            "family computes a sequential prefix sum of the leading run."
        ),
        "required": ["sequential_accumulation"],
        "optional": ["forward_pointer_advance"],
        "excluded": [],
    },
    {
        "problem_id": 3236,
        "member_local_keys": ["missing_prefix_array"],
        "label_source": "authored_family_proposal",
        "rationale": (
            "LC 3236 prefix-array family builds a cumulative prefix list before "
            "locating the missing integer."
        ),
        "required": ["sequential_accumulation"],
        "optional": ["forward_pointer_advance"],
        "excluded": [],
    },
]


def map_patterns_to_concepts(patterns) -> dict:
    required, optional, excluded, unmapped = set(), set(), set(), set()
    for pattern in patterns or []:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping is None:
            unmapped.add(pattern)
            continue
        required.update(mapping.get("required") or [])
        optional.update(mapping.get("optional") or [])
        excluded.update(mapping.get("excluded") or [])
    return {
        "required": sorted(required),
        "optional": sorted(optional),
        "excluded": sorted(excluded),
        "unmapped_patterns": sorted(unmapped),
    }


def _proposal_for(problem_id, member_keys) -> dict:
    keys = sorted(member_keys)
    for p in AUTHORED_FAMILY_PROPOSALS:
        if p["problem_id"] == problem_id and sorted(p["member_local_keys"]) == keys:
            return p
    return None


def _observed(members: list) -> tuple:
    sets = [set(m["concepts"]) for m in members]
    union = set().union(*sets) if sets else set()
    inter = set.intersection(*sets) if sets else set()
    return sorted(union), sorted(inter)


def screen_family(label_required: list, observed_union: list, observed_intersection: list,
                  family_count_for_problem: int) -> dict:
    """V2 §3.4 deterministic consistency screen."""
    L = set(label_required)
    if not L:
        return {"passed": False, "reason": "empty_label"}
    if not (set(observed_union) & L):
        return {"passed": False, "reason": "disjoint_from_label"}
    every_member_observes_all = L <= set(observed_intersection)
    only_family = family_count_for_problem == 1
    if every_member_observes_all:
        return {"passed": True, "reason": "all_required_observed_by_every_member"}
    if only_family:
        return {"passed": True, "reason": "only_family_for_problem"}
    return {"passed": False, "reason": "partial_problem_label"}


def divergence_state(L: list, O: list, tier_of, zero_evidence: bool) -> str:
    """V2 §5.2 state machine."""
    if zero_evidence:
        return STATE_ZERO_EVIDENCE
    L, O = set(L), set(O)
    if not L:
        return STATE_NO_LABEL
    if L <= O:
        if all(tier_of(c) == "SUPPORT" for c in L):
            return STATE_LABEL_GENERIC
        return STATE_LABEL_OK
    if not (L & O):
        return STATE_LABEL_UNEXPRESSIBLE
    # partial: some, but not all, of the label is observed
    covered = L & O
    if len(covered) >= 2:
        return STATE_LABEL_MULTI_OVERLAP
    return STATE_LABEL_PARTIAL


def build(reference_artifact: dict, normalized_artifact: dict, group_artifact: dict) -> dict:
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    solutions = {s["solution_id"]: s for s in reference_artifact["solutions"]}
    families = group_artifact["families"]

    families_per_problem = {}
    for f in families:
        families_per_problem[f["problem_id"]] = families_per_problem.get(f["problem_id"], 0) + 1

    entries = []
    for fam in families:
        pid = fam["problem_id"]
        members = [rows[m] for m in fam["members"]]
        member_keys = [m.get("local_key") for m in members]
        observed_union, observed_intersection = _observed(members)
        tier_map = rows[fam["members"][0]]["concept_tiers"]

        def tier_of(concept, _t=tier_map):
            return _t.get(concept, "SUPPORT")

        # ---- channel 1: authored family proposal -------------------------
        proposal = _proposal_for(pid, member_keys)
        # ---- channel 2: curated problem label (§3.4 screen) --------------
        problem_patterns = list(PROBLEMS.get(pid, {}).get("curated_patterns") or [])
        problem_concepts = map_patterns_to_concepts(problem_patterns)
        screen = screen_family(
            problem_concepts["required"], observed_union, observed_intersection,
            families_per_problem[pid],
        )

        if proposal is not None:
            label = {
                "label_source": proposal["label_source"],
                "label_source_detail": "authored family-level editorial proposal (channel 1)",
                "granularity": "family_level",
                "problem_patterns": problem_patterns,
                "required": proposal["required"],
                "optional": proposal["optional"],
                "excluded": proposal["excluded"],
                "required_expected": [],
                "rationale": proposal["rationale"],
            }
        elif screen["passed"]:
            label = {
                "label_source": "curated_problems_pattern",
                "label_source_detail": CURATED_PATTERN_SOURCE,
                "granularity": "problem_level_screened",
                "problem_patterns": problem_patterns,
                "required": problem_concepts["required"],
                "optional": problem_concepts["optional"],
                "excluded": problem_concepts["excluded"],
                "required_expected": [],
                "rationale": f"problem label applied: screen={screen['reason']}",
            }
        else:
            label = {
                "label_source": None,
                "label_source_detail": "no channel produced an applicable label",
                "granularity": "none",
                "problem_patterns": problem_patterns,
                "required": [],
                "optional": [],
                "excluded": [],
                "required_expected": [],
                "rationale": f"screen failed: {screen['reason']}",
            }

        state = divergence_state(
            label["required"], observed_intersection, tier_of, fam["zero_evidence"]
        )
        if state == STATE_NO_LABEL and not label["required"] and not screen["passed"] \
                and screen["reason"] == "partial_problem_label":
            state = STATE_REVIEW_SCREEN_FAILED

        # required_expected is informational only (V2 §4.4)
        if state in (STATE_LABEL_PARTIAL, STATE_LABEL_UNEXPRESSIBLE, STATE_LABEL_MULTI_OVERLAP):
            label["required_expected"] = list(problem_concepts["required"])

        canon = solutions[fam["canonical_solution_id"]]
        entries.append({
            "problem_id": pid,
            "problem_title": PROBLEMS.get(pid, {}).get("title", ""),
            "family_key": fam["family_key"],
            "member_count": fam["member_count"],
            "members": fam["members"],
            "member_local_keys": member_keys,
            "reference_solution": {
                "solution_id": canon["solution_id"],
                "source_type": canon["source_type"],
                "source_ref": canon["source_ref"],
                "code_text": canon["code_text"],
            },
            "family_sources": fam["sources"],
            "proposed_label": label,
            "label_screen": screen,
            "divergence_state": state,
            "approval_state": APPROVAL_PENDING,
            "reviewer": None,
            "reviewed_at": None,
            "reviewer_notes": "",
            "approved": False,
            # analyzer detections intentionally ABSENT from the reviewer view
        })

    states = {}
    for e in entries:
        states[e["divergence_state"]] = states.get(e["divergence_state"], 0) + 1

    return {
        "phase": "4_family_labeling",
        "independence_rule": (
            "labels come from editorial metadata (curated problems.pattern) or an "
            "authored family-level proposal; the analyzer's detections never "
            "author a label"
        ),
        "analyzer_detection_visible_to_reviewer": False,
        "auto_approval": False,
        "provisional_assumption": (
            "PA1: no human reviewer is available in this environment; every label "
            "stays PENDING_REVIEW (never APPROVED). See POC_V2_REPORT.md."
        ),
        "totals": {
            "families": len(entries),
            "approval_states": {APPROVAL_PENDING: len(entries)},
            "approved": 0,
            "divergence_state_counts": states,
        },
        "entries": entries,
    }


def build_comparison(normalized_artifact: dict, group_artifact: dict, label_artifact: dict) -> dict:
    """Post-hoc artifact: analyzer detections vs the proposed labels."""
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    label_by_family = {e["family_key"]: e for e in label_artifact["entries"]}
    entries = []
    for fam in group_artifact["families"]:
        e = label_by_family[fam["family_key"]]
        entries.append({
            "problem_id": fam["problem_id"],
            "family_key": fam["family_key"],
            "proposed_required": e["proposed_label"]["required"],
            "divergence_state": e["divergence_state"],
            "analyzer_pec_set": fam["pec_set"],
            "analyzer_support_set": fam["support_set"],
            "analyzer_structural_profile": fam["structural_profile"],
            "per_member": [
                {
                    "solution_id": sid,
                    "techniques": rows[sid]["technique_signature"],
                    "strategies": rows[sid]["strategy_signature"],
                    "dedup_level": rows[sid]["dedup_level"],
                }
                for sid in fam["members"]
            ],
        })
    return {
        "phase": "4_label_comparison",
        "note": (
            "Diagnostic artifact only; produced AFTER the blind review sheet. "
            "Never shown to the reviewer."
        ),
        "entries": entries,
    }


def render_markdown(label_artifact: dict) -> str:
    t = label_artifact["totals"]
    lines = [
        "# Ground-Truth POC V2 — Blind Family Review Sheet",
        "",
        "**Reviewer-facing artifact.** Analyzer detections (techniques, strategies,",
        "PEC sets, profiles) are deliberately NOT shown. See `label_comparison.json`",
        "for the post-hoc comparison.",
        "",
        "No label is auto-approved: every family starts `PENDING_REVIEW`.",
        "",
        f"- Families: **{t['families']}**  •  APPROVED: **{t['approved']}**  •  "
        f"PENDING_REVIEW: **{t['approval_states'].get('PENDING_REVIEW', 0)}**",
        "",
        "> **PROVISIONAL (PA1):** no human reviewer is available in the POC",
        "> environment, so no family is APPROVED. The label channels below are",
        "> editorial proposals only; a human must approve them before any group",
        "> could be promoted (spec V2 §4.5).",
        "",
        "---",
        "",
    ]
    for e in label_artifact["entries"]:
        p = e["proposed_label"]
        req = p["required"] or "_(none — no applicable independent label)_"
        lines += [
            f"## {e['family_key']} — {e['problem_title']} (LC {e['problem_id']})",
            "",
            f"- **approval_state:** `{e['approval_state']}`  •  "
            f"**divergence_state:** `{e['divergence_state']}`",
            f"- **members:** {e['member_count']} ({', '.join(e['member_local_keys'])})",
            f"- **sources:** {', '.join(e['family_sources'])}",
            f"- **reference solution:** `{e['reference_solution']['solution_id']}` "
            f"({e['reference_solution']['source_type']})",
            f"- **label source:** `{p['label_source']}` ({p['granularity']})",
            f"- **problem patterns:** {p['problem_patterns'] or '_(none)_'}",
            f"- **proposed required:** {req}",
            f"- **proposed optional:** {p['optional'] or '_(none)_'}",
            f"- **proposed excluded:** {p['excluded'] or '_(none)_'}",
            f"- **rationale:** {p['rationale']}",
            "",
            "```python",
            e["reference_solution"]["code_text"].rstrip("\n"),
            "```",
            "",
            f"_reviewer notes:_ {e['reviewer_notes'] or '_(to be completed by the reviewer)_'}",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)
