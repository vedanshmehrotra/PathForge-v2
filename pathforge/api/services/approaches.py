"""Observational approach comparisons; never controls scoring or authority."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from pathforge.services.approach_policy import qualify_approach
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
    # Listed-pattern overlap only; never a strategy, correctness or authority decision.
    pattern_evidence_state: Literal[
        "NOT_EVALUATED", "ALL_OBSERVED", "SOME_OBSERVED", "NONE_OBSERVED", "UNAVAILABLE"
    ] = "NOT_EVALUATED"
    observed_patterns: list[str] = Field(default_factory=list)
    unobserved_patterns: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class UnscoredApproach(BaseModel):
    """A descriptive proposal; never a matchable or rated skill requirement."""
    id: str
    name: str
    description: str
    coverage_limit: str
    comparison_support: Literal["UNSUPPORTED"]
    patterns: list[str] = Field(default_factory=list)
    contract_version: Literal[2]
    source_sha256: str
    provenance: list[str]
    authority_tier: Literal["llm_proposed"]


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
        qualification = qualify_approach(group)
        explicit, review = qualification["explicit"], qualification["review"]
        limitations = []
        if qualification["invalid_relationship"]:
            limitations.append("Family relationship metadata is incomplete or unsupported; its structure is not verified.")
        if not explicit:
            limitations.append("Stored labels do not establish the relationship between complete approaches.")
        if review != "REVIEWED":
            limitations.append("These expectations are unreviewed or have conflicting authority metadata.")
        if qualification["components_differ"]:
            limitations.append("Legacy labels and canonical component definitions differ.")
        if group.get("matchable") is False or group.get("unmapped_patterns"):
            limitations.append("Some components lack canonical vocabulary coverage.")
        limitations.append("Unobserved evidence may reflect detector coverage; pattern alignment does not verify correctness or optimality.")
        compared = engine.match({"accepted_solution_groups": [patterns]}, detections) if ast_output is not None else None
        observed = sorted(set(patterns) & detected.keys()) if compared else []
        unobserved = compared["unmatched_patterns"] if compared else []
        usable = qualification["usable"]
        evidence_state = "NOT_EVALUATED"
        if not usable:
            evidence_state = "UNAVAILABLE"
        elif compared is not None:
            if compared["match_result"] == "FULL_MATCH" and not unobserved and set(patterns) <= set(observed):
                evidence_state = "ALL_OBSERVED"
            elif compared["match_result"] == "PARTIAL_MATCH" and observed:
                evidence_state = "SOME_OBSERVED"
            elif compared["match_result"] == "NO_MATCH" and not observed:
                evidence_state = "NONE_OBSERVED"
            else:
                evidence_state = "UNAVAILABLE"
        descriptions.append(SolutionApproach(
            id=str(group.get("id", f"group_{index}")),
            name=group.get("approach_name") if isinstance(group.get("approach_name"), str) and group["approach_name"] else f"Stored group {index + 1}",
            patterns=patterns, required=group.get("required") or [],
            optional=group.get("optional") or [], excluded=group.get("excluded") or [],
            family_relation=qualification["relation"], alternative_group_id=qualification["alternative_id"],
            provenance=group.get("provenance") or [], authority_tier=group.get("authority_tier"),
            definition_state="EXPLICIT" if explicit else "LEGACY_UNSPECIFIED", review_state=review,
            comparison_state=compared["match_result"] if compared else "NOT_EVALUATED",
            pattern_evidence_state=evidence_state,
            observed_patterns=observed, unobserved_patterns=unobserved, limitations=limitations,
        ))
    return descriptions
