"""Shared approach qualification and the conservative skill-comparison gate.

Qualification does not grant authority or select a canonical strategy. The
comparison gate can only restrict the existing legacy/B6 persistence gates.
"""
from pathforge.ast_analysis.authority_vocabulary import (
    FAMILY_RELATION_INDEPENDENT, FAMILY_RELATION_ONE_OF, normalize_group_authority,
)
from src.matching_engine.matching_engine import MatchingEngine


def qualify_approach(group):
    """Interpret existing relationship, coverage and authority metadata once."""
    patterns = group.get("patterns") or []
    declared = group.get("approach_definition")
    raw_relation = group.get("family_relation")
    raw_alternative_id = group.get("alternative_group_id")
    relation = raw_relation if raw_relation in (FAMILY_RELATION_ONE_OF, FAMILY_RELATION_INDEPENDENT) else None
    alternative_id = raw_alternative_id if isinstance(raw_alternative_id, str) and raw_alternative_id.strip() else None
    invalid_relationship = (
        (raw_relation not in (None, "") and relation is None)
        or (raw_alternative_id not in (None, "") and alternative_id is None)
        or (relation == FAMILY_RELATION_ONE_OF and alternative_id is None)
    )
    components_differ = set(patterns) != set(group.get("derivation_patterns") or patterns)
    explicit = not invalid_relationship and not components_differ and (
        declared == "EXPLICIT" or (declared is None and relation == FAMILY_RELATION_ONE_OF))
    authority = normalize_group_authority(group)
    review = "CONFLICT" if authority["conflict"] else (
        "REVIEWED" if authority["authorizing"] else "UNREVIEWED")
    usable = (explicit and review != "CONFLICT" and bool(patterns)
              and group.get("matchable", True) is True and not group.get("unmapped_patterns"))
    return {"relation": relation, "alternative_id": alternative_id,
            "invalid_relationship": invalid_relationship, "components_differ": components_differ,
            "explicit": explicit, "review": review, "usable": usable}


def skill_comparison_gate(groups, ast_output, match_result):
    """Only a complete, usable, authorizing pattern comparison may score.

    Use the first matched group, as legacy persistence does. Never borrow
    authority from an unmatched alternative or promote an inferred expectation.
    Recheck actual overlap with the existing matcher; a stale FULL_MATCH alone
    is insufficient. Canonical strategy decisions remain the optional B6 gate.
    """
    if not groups:
        return {"eligible": False, "reason": "comparison_unavailable"}
    if match_result.get("match_result") != "FULL_MATCH":
        return {"eligible": False, "reason": "comparison_incomplete"}
    indices = match_result.get("matched_groups")
    if (not isinstance(indices, list) or not indices or type(indices[0]) is not int
            or not 0 <= indices[0] < len(groups) or match_result.get("unmatched_patterns") != []):
        return {"eligible": False, "reason": "comparison_inconsistent"}
    group = groups[indices[0]]
    if not isinstance(group, dict):
        return {"eligible": False, "reason": "comparison_unavailable"}
    qualification = qualify_approach(group)
    if not qualification["usable"]:
        return {"eligible": False, "reason": "approach_unsupported_or_ambiguous"}
    if qualification["review"] != "REVIEWED":
        return {"eligible": False, "reason": "expectations_not_authorizing"}
    compared = MatchingEngine().match(
        {"accepted_solution_groups": [group["patterns"]]}, ast_output.get("detected_patterns", []))
    if compared["match_result"] != "FULL_MATCH":
        return {"eligible": False, "reason": "comparison_inconsistent"}
    return {"eligible": True, "reason": "complete_authorizing_comparison"}
