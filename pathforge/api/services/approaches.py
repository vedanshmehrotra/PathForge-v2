"""Observational approach comparisons; never controls scoring or authority."""
from typing import Optional

from pydantic import BaseModel, Field

from pathforge.ast_analysis.authority_vocabulary import (
    FAMILY_RELATION_INDEPENDENT, FAMILY_RELATION_ONE_OF, normalize_group_authority,
)
from src.matching_engine.matching_engine import MatchingEngine


class SolutionApproach(BaseModel):
    id: str
    name: str
    patterns: list[str]
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    family_relation: Optional[str] = None
    alternative_group_id: Optional[str] = None
    provenance: list[str] = Field(default_factory=list)
    authority_tier: Optional[str] = None
    definition_state: str
    review_state: str
    comparison_state: str = "NOT_EVALUATED"
    observed_patterns: list[str] = Field(default_factory=list)
    unobserved_patterns: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def describe_approaches(groups, ast_output=None) -> list[SolutionApproach]:
    """Describe legacy pattern comparisons, separately from strategy conclusions.

    Review metadata uses existing fail-closed authority normalization; this
    function does not grant product eligibility or select canonical strategies.
    """
    engine = MatchingEngine()
    detections = (ast_output or {}).get("detected_patterns", [])
    detected = engine._normalize_ast(detections)
    descriptions = []
    for index, group in enumerate(groups or []):
        patterns = list(group.get("patterns") or [])
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
        explicit = not invalid_relationship and (
            declared == "EXPLICIT" or (declared is None and relation == FAMILY_RELATION_ONE_OF))
        normalization = normalize_group_authority(group)
        review = "CONFLICT" if normalization["conflict"] else (
            "REVIEWED" if normalization["authorizing"] else "UNREVIEWED")
        limitations = []
        if invalid_relationship:
            limitations.append("Family relationship metadata is incomplete or unsupported; its structure is not verified.")
        if not explicit:
            limitations.append("Stored labels do not establish the relationship between complete approaches.")
        if review != "REVIEWED":
            limitations.append("These expectations are unreviewed or have conflicting authority metadata.")
        if set(patterns) != set(group.get("derivation_patterns") or patterns):
            explicit = False
            limitations.append("Legacy labels and canonical component definitions differ.")
        if group.get("matchable") is False or group.get("unmapped_patterns"):
            limitations.append("Some components lack canonical vocabulary coverage.")
        limitations.append("Unobserved evidence may reflect detector coverage; pattern alignment does not verify correctness or optimality.")
        compared = engine.match({"accepted_solution_groups": [patterns]}, detections) if ast_output is not None else None
        descriptions.append(SolutionApproach(
            id=str(group.get("id", f"group_{index}")),
            name=group.get("approach_name") if isinstance(group.get("approach_name"), str) and group["approach_name"] else f"Stored group {index + 1}",
            patterns=patterns, required=group.get("required") or [],
            optional=group.get("optional") or [], excluded=group.get("excluded") or [],
            family_relation=relation, alternative_group_id=alternative_id,
            provenance=group.get("provenance") or [], authority_tier=group.get("authority_tier"),
            definition_state="EXPLICIT" if explicit else "LEGACY_UNSPECIFIED", review_state=review,
            comparison_state=compared["match_result"] if compared else "NOT_EVALUATED",
            observed_patterns=sorted(set(patterns) & detected.keys()) if compared else [],
            unobserved_patterns=compared["unmatched_patterns"] if compared else [], limitations=limitations,
        ))
    return descriptions
