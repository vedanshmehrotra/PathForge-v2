"""Phase 4 — independent label generation and the human-review artifact.

Label authority comes from a source OUTSIDE the analyzer under test
(spec §9 independence rule):

  precedence 1 = curated ``problems.pattern`` (editorial / externally_listed),
  mapped through the frozen ``PATTERN_TO_V1_MAPPING``.

The analyzer's own detections are **not** used to author labels and are **not**
shown in the reviewer-facing artifact.  They are written only to the separate
``label_comparison.json`` artifact.

No label is auto-approved: every family is ``PENDING_REVIEW`` (or
``NO_INDEPENDENT_LABEL`` when the problem's curated metadata is empty).
"""
from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING

from .problem_metadata import CURATED_PATTERN_SOURCE, POC_VERSION, PROBLEMS, TAXONOMY_VERSION

REVIEW_STATE_PENDING = "PENDING_REVIEW"
REVIEW_STATE_NO_LABEL = "NO_INDEPENDENT_LABEL"


def _concepts_for_patterns(patterns: list) -> dict:
    """Map curated legacy pattern names to V1 concepts via the frozen mapping."""
    required, optional, excluded, unmapped = set(), set(), set(), set()
    for pattern in patterns:
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


def build(reference_artifact: dict, group_artifact: dict) -> dict:
    solutions = {s["solution_id"]: s for s in reference_artifact["solutions"]}
    families = group_artifact["families"]

    entries = []
    for fam in families:
        pid = fam["problem_id"]
        meta = PROBLEMS.get(pid, {})
        curated = list(meta.get("curated_patterns") or [])
        concepts = _concepts_for_patterns(curated)

        if curated:
            state = REVIEW_STATE_PENDING
            proposed_label = {
                "external_patterns": curated,
                "label_source": "curated_problems_pattern",
                "label_source_detail": CURATED_PATTERN_SOURCE,
                "granularity": "problem_level",
                "family_specific": False,
                "proposed_required": concepts["required"],
                "proposed_optional": concepts["optional"],
                "proposed_excluded": concepts["excluded"],
                "unmapped_patterns": concepts["unmapped_patterns"],
            }
        else:
            state = REVIEW_STATE_NO_LABEL
            proposed_label = {
                "external_patterns": [],
                "label_source": None,
                "label_source_detail": "problem has no curated pattern metadata",
                "granularity": "none",
                "family_specific": False,
                "proposed_required": [],
                "proposed_optional": [],
                "proposed_excluded": [],
                "unmapped_patterns": [],
            }

        canon = solutions[fam["canonical_solution_id"]]
        entries.append({
            "problem_id": pid,
            "problem_title": meta.get("title", ""),
            "family_key": fam["family_key"],
            "member_count": fam["member_count"],
            "members": fam["members"],
            "reference_solution": {
                "solution_id": canon["solution_id"],
                "source_type": canon["source_type"],
                "source_ref": canon["source_ref"],
                "code_text": canon["code_text"],
            },
            "family_sources": fam["sources"],
            "proposed_label": proposed_label,
            "review_state": state,
            "reviewer_notes": "",
            "approved": False,
            # analyzer detections are intentionally ABSENT here
        })

    pending = sum(1 for e in entries if e["review_state"] == REVIEW_STATE_PENDING)
    return {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "phase": "4_label_generation",
        "independence_rule": (
            "labels are proposed only from curated editorial metadata mapped "
            "through the frozen PATTERN_TO_V1_MAPPING; the analyzer's detections "
            "are never used to author a label"
        ),
        "analyzer_detection_visible_to_reviewer": False,
        "curated_pattern_source": CURATED_PATTERN_SOURCE,
        "auto_approval": False,
        "totals": {
            "families": len(entries),
            "pending_review": pending,
            "no_independent_label": len(entries) - pending,
        },
        "entries": entries,
    }


def build_comparison(normalized_artifact: dict, group_artifact: dict, review_artifact: dict) -> dict:
    """Separate artifact: analyzer detections vs the proposed external labels.

    Generated AFTER the review sheet; never shown to the reviewer beforehand.
    """
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    entries = []
    for fam in group_artifact["families"]:
        members = [rows[s] for s in fam["members"]]
        entries.append({
            "problem_id": fam["problem_id"],
            "family_key": fam["family_key"],
            "proposed_required": next(
                e["proposed_label"]["proposed_required"]
                for e in review_artifact["entries"] if e["family_key"] == fam["family_key"]
            ),
            "analyzer_technique_signature": fam["technique_signature"],
            "analyzer_strategy_signature": fam["strategy_signature"],
            "per_member": [
                {
                    "solution_id": m["solution_id"],
                    "techniques": m["technique_signature"],
                    "strategies": m["strategy_signature"],
                    "dedup_level": m["dedup_level"],
                }
                for m in members
            ],
        })
    return {
        "poc_version": POC_VERSION,
        "phase": "4_label_comparison",
        "note": (
            "Diagnostic artifact only. Not part of the reviewer-facing review "
            "sheet; produced after it, for post-hoc agreement analysis."
        ),
        "entries": entries,
    }


def render_markdown(review_artifact: dict) -> str:
    lines = [
        "# Ground-Truth POC — Human Review Sheet",
        "",
        f"POC version: `{review_artifact['poc_version']}`  •  "
        f"taxonomy: `{review_artifact['taxonomy_version']}`",
        "",
        "**Reviewer-facing artifact.** Analyzer detections are deliberately NOT",
        "shown here (see `label_comparison.json` for the post-hoc comparison).",
        "No label is auto-approved: every entry starts `PENDING_REVIEW`.",
        "",
        f"- Label source: `{review_artifact['curated_pattern_source']}`",
        f"- Families: **{review_artifact['totals']['families']}**  •  "
        f"pending review: **{review_artifact['totals']['pending_review']}**  •  "
        f"no independent label: **{review_artifact['totals']['no_independent_label']}**",
        "",
        "> **Known granularity limitation (PROVISIONAL):** curated",
        "> `problems.pattern` metadata is *problem-level*, not family-level, so the",
        "> proposal below is not family-specific. A human reviewer must assign",
        "> per-family concepts. Recorded as an OPEN decision in the POC report.",
        "",
        "---",
        "",
    ]
    for e in review_artifact["entries"]:
        p = e["proposed_label"]
        lines += [
            f"## {e['family_key']} — {e['problem_title']} (LC {e['problem_id']})",
            "",
            f"- **review_state:** `{e['review_state']}`",
            f"- **members:** {e['member_count']} ({', '.join(e['members'])})",
            f"- **sources:** {', '.join(e['family_sources'])}",
            f"- **reference solution:** `{e['reference_solution']['solution_id']}` "
            f"({e['reference_solution']['source_type']}) — `{e['reference_solution']['source_ref']}`",
            f"- **proposed external pattern(s):** {p['external_patterns'] or '_(none — no independent label source)_'}",
            f"- **proposed required (V1):** {p['proposed_required'] or '_(none)_'}",
            f"- **proposed optional (V1):** {p['proposed_optional'] or '_(none)_'}",
            f"- **proposed excluded (V1):** {p['proposed_excluded'] or '_(none)_'}",
            f"- **family-specific label:** {p['family_specific']}  •  **granularity:** {p['granularity']}",
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
