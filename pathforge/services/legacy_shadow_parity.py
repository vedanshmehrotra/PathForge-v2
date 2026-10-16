"""B7 — Legacy-vs-Shadow Verdict Parity / Migration Readiness (OBSERVATIONAL).

B7 answers one question: *if the shadow architecture were eventually made
authoritative, where would its decisions differ from the legacy system, and
why?*

It is purely observational. It does not replace or modify the legacy matcher,
does not change production behavior, does not enable the B6 feature flag, and
never executes a product consequence. Elo / gap / recommendation values in the
comparison records are **simulated** from the existing gate rules and are never
computed against a database.

Comparison model
----------------

The two pipelines are compared at the *product-conclusion* level, but every
intermediate semantic layer is preserved::

    legacy:    detection → matched group → verdict → consequence eligibility
    shadow:    facts → B2 tri-state → B3 coverage → B4 primary strategy
               → B5/B5.5 authority → B6 product eligibility

A disagreement is **categorized** (P1–P10, below), never collapsed into a
single equality test, and authority conflicts are isolated from algorithmic
disagreements.

Legacy results are captured **without reinterpretation**: the legacy verdict
type comes from exactly the rule production uses
(``evidence ∈ _AUTHORITATIVE_STATES``), recorded verbatim.

Parity categories (P1–P10)
--------------------------

``P1_EXACT_PARITY``
    Both systems arrive at materially equivalent product conclusions.
``P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED``
    Legacy authorizes; B6 blocks. Sub-categorized by reason
    (``authority_conflict`` / ``non_authoritative`` / ``coverage_not_confirmed``
    / ``no_primary_strategy`` / ``no_authority_report`` / ``one_of_unsatisfied``
    / ``other``). **Authority conflicts are recorded here as a *sub-reason* but
    also promoted to category P7** so they can never be misread as shadow
    algorithm failures.
``P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE``
    B6 would allow the consequence while legacy would not. Potentially important
    migration evidence.
``P4_LEGACY_MATCH_SHADOW_UNRESOLVED``
    Legacy identifies something; shadow cannot establish the strategy.
``P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED``
    Shadow establishes a strategy legacy did not recognize.
``P6_LEGACY_MATCH_SHADOW_CONTRADICTED``
    Legacy recognizes a family while shadow evidence actively contradicts it.
``P7_AUTHORITY_CONFLICT``
    ``authority_tier`` and ``evidence`` normalize to different canonical tiers.
    Distinct from every algorithmic category.
``P8_REPRESENTATION_DIFFERENCE``
    Semantically equivalent but represented differently (ONE_OF, family
    splitting, taxonomy differences).
``P9_NO_COMPARABLE_GT``
    Insufficient ground truth for a meaningful comparison.
``P10_ERROR``
    A pipeline genuinely failed. Never silently classified as disagreement.

ONE_OF is compared as one logical requirement; ``db-254`` remains independent.
Technique-only ONE_OF families (LC3236) are recorded as such — techniques are
never promoted to make parity look better.
"""

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import config

from pathforge.ast_analysis import authority_vocabulary as vocab
from pathforge.ast_analysis.shadow import authority_gating as ag
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import shadow_runner
from pathforge.services import product_eligibility as b6

# ============================================================================
# Parity categories
# ============================================================================

P1_EXACT_PARITY = "P1_EXACT_PARITY"
P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED = "P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED"
P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE = "P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE"
P4_LEGACY_MATCH_SHADOW_UNRESOLVED = "P4_LEGACY_MATCH_SHADOW_UNRESOLVED"
P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED = "P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED"
P6_LEGACY_MATCH_SHADOW_CONTRADICTED = "P6_LEGACY_MATCH_SHADOW_CONTRADICTED"
P7_AUTHORITY_CONFLICT = "P7_AUTHORITY_CONFLICT"
P8_REPRESENTATION_DIFFERENCE = "P8_REPRESENTATION_DIFFERENCE"
P9_NO_COMPARABLE_GT = "P9_NO_COMPARABLE_GT"
P10_ERROR = "P10_ERROR"

PARITY_CATEGORIES: Tuple[str, ...] = (
    P1_EXACT_PARITY,
    P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED,
    P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE,
    P4_LEGACY_MATCH_SHADOW_UNRESOLVED,
    P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED,
    P6_LEGACY_MATCH_SHADOW_CONTRADICTED,
    P7_AUTHORITY_CONFLICT,
    P8_REPRESENTATION_DIFFERENCE,
    P9_NO_COMPARABLE_GT,
    P10_ERROR,
)

# -- P2 sub-reasons ----------------------------------------------------------

P2_REASON_AUTHORITY_CONFLICT = "authority_conflict"
P2_REASON_NON_AUTHORITATIVE = "non_authoritative"
P2_REASON_COVERAGE_NOT_CONFIRMED = "coverage_not_confirmed"
P2_REASON_NO_PRIMARY_STRATEGY = "no_primary_strategy"
P2_REASON_NO_AUTHORITY_REPORT = "no_authority_report"
P2_REASON_ONE_OF_UNSATISFIED = "one_of_unsatisfied"
P2_REASON_OTHER = "other"

P2_REASONS: Tuple[str, ...] = (
    P2_REASON_AUTHORITY_CONFLICT,
    P2_REASON_NON_AUTHORITATIVE,
    P2_REASON_COVERAGE_NOT_CONFIRMED,
    P2_REASON_NO_PRIMARY_STRATEGY,
    P2_REASON_NO_AUTHORITY_REPORT,
    P2_REASON_ONE_OF_UNSATISFIED,
    P2_REASON_OTHER,
)

# -- migration statuses (diagnosis, never a single score) ---------------------

STATUS_READY_FOR_SHADOW = "READY_FOR_SHADOW"
STATUS_BLOCKED_BY_AUTHORITY = "BLOCKED_BY_AUTHORITY"
STATUS_BLOCKED_BY_GT = "BLOCKED_BY_GT"
STATUS_BLOCKED_BY_SHADOW_COVERAGE = "BLOCKED_BY_SHADOW_COVERAGE"
STATUS_BLOCKED_BY_PARITY = "BLOCKED_BY_PARITY"
STATUS_REPRESENTATION_ONLY = "REPRESENTATION_ONLY"
STATUS_ERROR = "ERROR"

MIGRATION_STATUSES: Tuple[str, ...] = (
    STATUS_READY_FOR_SHADOW,
    STATUS_BLOCKED_BY_AUTHORITY,
    STATUS_BLOCKED_BY_GT,
    STATUS_BLOCKED_BY_SHADOW_COVERAGE,
    STATUS_BLOCKED_BY_PARITY,
    STATUS_REPRESENTATION_ONLY,
    STATUS_ERROR,
)


# ============================================================================
# Records
# ============================================================================

@dataclass
class LegacyObservation:
    """The legacy pipeline's actual result, captured without reinterpretation."""

    matched: bool
    verdict_type: str
    matched_group_id: Optional[str]
    evidence: str
    expected_pattern: str
    matched_patterns: Tuple[str, ...]
    unmatched_patterns: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "verdict_type": self.verdict_type,
            "matched_group_id": self.matched_group_id,
            "evidence": self.evidence,
            "expected_pattern": self.expected_pattern,
            "matched_patterns": list(self.matched_patterns),
            "unmatched_patterns": list(self.unmatched_patterns),
        }


@dataclass
class ShadowObservation:
    """The canonical shadow result (B2–B6), captured independently."""

    coverage_state: Optional[str]
    primary_strategy: Optional[str]
    authority_tier: Optional[str]
    authority_diagnostic: Optional[str]
    logical_requirements: Tuple[str, ...]
    authoritative_requirements: Tuple[str, ...]
    b6_eligible: bool
    b6_reasons: Tuple[str, ...]
    b2_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "coverage_state": self.coverage_state,
            "primary_strategy": self.primary_strategy,
            "authority_tier": self.authority_tier,
            "authority_diagnostic": self.authority_diagnostic,
            "logical_requirements": list(self.logical_requirements),
            "authoritative_requirements": list(self.authoritative_requirements),
            "b6_eligible": self.b6_eligible,
            "b6_reasons": list(self.b6_reasons),
            "b2_counts": dict(self.b2_counts),
        }


@dataclass
class ConsequenceSimulation:
    """Hypothetical consequence eligibility. **Simulation only — never executed.**"""

    legacy_allows_elo: bool
    shadow_allows_elo: bool
    legacy_allows_gap: bool
    shadow_allows_gap: bool
    legacy_allows_recommendation: bool
    shadow_allows_recommendation: bool

    def to_dict(self) -> dict:
        return {
            "legacy_allows_elo": self.legacy_allows_elo,
            "shadow_allows_elo": self.shadow_allows_elo,
            "legacy_allows_gap": self.legacy_allows_gap,
            "shadow_allows_gap": self.shadow_allows_gap,
            "legacy_allows_recommendation": self.legacy_allows_recommendation,
            "shadow_allows_recommendation": self.shadow_allows_recommendation,
            "simulated_only": True,
        }


@dataclass
class LegacyShadowParityRecord:
    """One evaluated submission/problem: legacy vs shadow, side by side."""

    submission_id: Optional[str]
    problem_id: Optional[int]
    title: Optional[str]
    legacy: LegacyObservation
    shadow: ShadowObservation
    parity_category: str
    divergence_reason: Tuple[str, ...]
    migration_status: str
    consequence_simulation: ConsequenceSimulation
    technique_only_one_of: bool = False
    one_of_group_ids: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "submission_id": self.submission_id,
            "problem_id": self.problem_id,
            "title": self.title,
            "legacy": self.legacy.to_dict(),
            "shadow": self.shadow.to_dict(),
            "comparison": {
                "parity_category": self.parity_category,
                "divergence_reason": list(self.divergence_reason),
                "migration_status": self.migration_status,
            },
            "consequence_simulation": self.consequence_simulation.to_dict(),
            "technique_only_one_of": self.technique_only_one_of,
            "one_of_group_ids": list(self.one_of_group_ids),
        }


# ============================================================================
# Legacy result extraction (no reinterpretation)
# ============================================================================

def legacy_authoritative(evidence: str) -> bool:
    """The legacy product rule, verbatim: evidence-based, not tier-based."""
    from pathforge.services import persistence as legacy_persistence
    return evidence in legacy_persistence._AUTHORITATIVE_STATES


def observe_legacy(
    groups: Optional[list],
    match_result: dict,
) -> LegacyObservation:
    """Extract the legacy matcher's actual result.

    ``match_result`` is the legacy MatchingEngine's output (from
    ``run_analysis``) — never reinterpreted into shadow vocabulary.
    """
    matched_groups = match_result.get("matched_groups") or []
    matched_idx = matched_groups[0] if isinstance(matched_groups, list) and matched_groups else None
    matched_group = None
    if isinstance(matched_idx, int) and groups and 0 <= matched_idx < len(groups):
        matched_group = groups[matched_idx]

    # Fallback: legacy "matched" also surfaces via FULL/PARTIAL_MATCH verdicts.
    verdict = match_result.get("match_result", "NO_MATCH")
    matched = bool(matched_groups) or verdict in ("FULL_MATCH", "PARTIAL_MATCH")

    evidence = ""
    expected_pattern = ""
    matched_group_id = None
    if isinstance(matched_group, dict):
        evidence = matched_group.get("evidence", "") or ""
        patterns = matched_group.get("patterns") or []
        expected_pattern = patterns[0] if patterns else ""
        matched_group_id = matched_group.get("id")
    elif groups:
        # no matched group: legacy falls back to the first non-empty group's
        # patterns for expected_pattern (same as persistence does)
        for g in groups:
            if isinstance(g, dict) and g.get("patterns"):
                expected_pattern = g["patterns"][0]
                evidence = g.get("evidence", "") or ""
                matched_group_id = g.get("id")
                break

    return LegacyObservation(
        matched=matched,
        verdict_type=verdict,
        matched_group_id=matched_group_id,
        evidence=evidence,
        expected_pattern=expected_pattern,
        matched_patterns=tuple(matched_groups) if isinstance(matched_groups, list)
        else (),
        unmatched_patterns=tuple(match_result.get("unmatched_patterns") or []),
    )


# ============================================================================
# Shadow result extraction (canonical fields)
# ============================================================================

def observe_shadow(
    shadow_result: Optional[dict],
    groups: Optional[list],
    eligibility: Optional[b6.ProductEligibility],
) -> ShadowObservation:
    """Extract the canonical shadow result (B2/B3/B4/B5/B6)."""
    if shadow_result is None or eligibility is None:
        return ShadowObservation(
            coverage_state=None,
            primary_strategy=None,
            authority_tier=None,
            authority_diagnostic=None,
            logical_requirements=(),
            authoritative_requirements=(),
            b6_eligible=False,
            b6_reasons=("no_shadow_result",),
        )

    authority = shadow_result.get("authority") or {}
    coverage_state = (shadow_result.get("coverage") or {}).get("aggregate_state")
    primary_strategy = ((shadow_result.get("strategy_selection") or {})
                        .get("submission") or {}).get("selected")

    diagnostics = set()
    for g in (groups or []):
        if not isinstance(g, dict):
            continue
        record = g.get("authority_normalization")
        if not isinstance(record, dict):
            # groups built outside the loader are normalized here
            record = vocab.normalize_group_authority(g)
        if record.get("diagnostic"):
            diagnostics.add(record["diagnostic"])

    b2_counts = (shadow_result.get("evidence_state") or {}).get("counts") or {}

    return ShadowObservation(
        coverage_state=coverage_state,
        primary_strategy=primary_strategy,
        authority_tier=eligibility.canonical_authority,
        authority_diagnostic=(
            vocab.AUTHORITY_CONFLICT if vocab.AUTHORITY_CONFLICT in diagnostics
            else (next(iter(diagnostics)) if diagnostics else None)
        ),
        logical_requirements=tuple(
            f"alternative_group:{g['group_id']}"
            for g in (authority.get("alternative_groups") or [])
        ) + tuple(
            f["family_id"]
            for f in (authority.get("families") or [])
            if f.get("family_relation") != ag.FAMILY_RELATION_ONE_OF
        ),
        authoritative_requirements=tuple(
            f"alternative_group:{g['group_id']}"
            for g in (authority.get("alternative_groups") or [])
            if g.get("authoritative")
        ) + tuple(
            f["family_id"]
            for f in (authority.get("families") or [])
            if f.get("family_relation") != ag.FAMILY_RELATION_ONE_OF
            and f.get("authoritative")
        ),
        b6_eligible=eligibility.eligible,
        b6_reasons=tuple(eligibility.reason_codes),
        b2_counts=dict(b2_counts),
    )


# ============================================================================
# Classification
# ============================================================================

def _p2_sub_reason(shadow: ShadowObservation, groups: Optional[list]) -> str:
    reasons = shadow.b6_reasons
    if vocab.AUTHORITY_CONFLICT in reasons:
        return P2_REASON_AUTHORITY_CONFLICT
    if "coverage_not_confirmed" in reasons:
        if any(
            isinstance(g, dict) and g.get("family_relation") == ag.FAMILY_RELATION_ONE_OF
            for g in (groups or [])
        ):
            return P2_REASON_ONE_OF_UNSATISFIED
        return P2_REASON_COVERAGE_NOT_CONFIRMED
    if "no_primary_strategy" in reasons:
        return P2_REASON_NO_PRIMARY_STRATEGY
    if "no_authority_report" in reasons or "no_shadow_result" in reasons:
        return P2_REASON_NO_AUTHORITY_REPORT
    if "structural_observation_only" in reasons:
        return P2_REASON_NON_AUTHORITATIVE
    if "inferred_authority" in reasons or "missing_authority" in reasons:
        return P2_REASON_NON_AUTHORITATIVE
    return P2_REASON_OTHER


def classify(
    legacy: LegacyObservation,
    shadow: ShadowObservation,
    groups: Optional[list] = None,
    shadow_failed: bool = False,
    legacy_failed: bool = False,
    has_groups: bool = False,
    groups_have_requirements: bool = False,
) -> Tuple[str, Tuple[str, ...], str]:
    """Return ``(parity_category, divergence_reasons, migration_status)``.

    The category order is the contract: pipeline errors first, then
    GT-insufficiency, then authority conflicts (never counted as algorithmic
    disagreement), then the verdict-comparison categories.
    """
    if shadow_failed or legacy_failed:
        return (P10_ERROR, ("pipeline_error",), STATUS_ERROR)

    if not has_groups or not groups_have_requirements:
        return (P9_NO_COMPARABLE_GT, ("no_comparable_gt",), STATUS_BLOCKED_BY_GT)

    conflict = shadow.authority_diagnostic == vocab.AUTHORITY_CONFLICT
    legacy_would_authorize = legacy_authoritative(legacy.evidence)
    b6_would_allow = shadow.b6_eligible and not conflict

    # P7 first among verdict comparisons: conflicts are provenance problems,
    # not algorithmic disagreements.
    if conflict:
        return (P7_AUTHORITY_CONFLICT, (vocab.AUTHORITY_CONFLICT,),
                STATUS_BLOCKED_BY_AUTHORITY)

    # P2: legacy authorizes, shadow blocks.
    if legacy_would_authorize and not b6_would_allow:
        sub = _p2_sub_reason(shadow, groups)
        if sub == P2_REASON_AUTHORITY_CONFLICT:  # defensive; handled by P7 above
            return (P7_AUTHORITY_CONFLICT, (vocab.AUTHORITY_CONFLICT,),
                    STATUS_BLOCKED_BY_AUTHORITY)
        status = STATUS_BLOCKED_BY_SHADOW_COVERAGE
        if sub in (P2_REASON_NON_AUTHORITATIVE, P2_REASON_NO_PRIMARY_STRATEGY,
                   P2_REASON_ONE_OF_UNSATISFIED):
            status = STATUS_BLOCKED_BY_SHADOW_COVERAGE
        return (P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED, (sub,), status)

    # P3: shadow eligible, legacy blocked.
    if b6_would_allow and not legacy_would_authorize:
        return (P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE,
                ("legacy_evidence_not_authoritative",), STATUS_READY_FOR_SHADOW)

    # Product-conclusion parity in the consequence dimension...
    if legacy_would_authorize == b6_would_allow:
        # ...but the verdict layer may still disagree.
        shadow_confirmed = shadow.coverage_state == fc.CONFIRMED
        legacy_match = legacy.matched

        if legacy_match and not shadow_confirmed:
            if shadow.coverage_state == fc.CONTRADICTED:
                return (P6_LEGACY_MATCH_SHADOW_CONTRADICTED,
                        ("shadow_contradiction",), STATUS_BLOCKED_BY_SHADOW_COVERAGE)
            return (P4_LEGACY_MATCH_SHADOW_UNRESOLVED,
                    ("shadow_not_confirmed",), STATUS_BLOCKED_BY_SHADOW_COVERAGE)

        if shadow_confirmed and not legacy_match:
            return (P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED,
                    ("legacy_no_match",), STATUS_BLOCKED_BY_PARITY)

        # Both systems agree in the consequence dimension AND the verdict
        # layer (matched/confirmed, or blocked/blocked): exact parity. ONE_OF
        # groups are compared as logical requirements upstream, so a satisfied
        # alternative set lands here rather than in a disagreement category.
        return (P1_EXACT_PARITY, (), STATUS_READY_FOR_SHADOW)

    # Unreachable by construction; kept for exhaustiveness.
    return (P8_REPRESENTATION_DIFFERENCE, ("unclassified",),
            STATUS_REPRESENTATION_ONLY)


def build_parity_record(
    submission_id: Optional[str],
    problem_id: Optional[int],
    title: Optional[str],
    groups: Optional[list],
    match_result: Optional[dict],
    shadow_result: Optional[dict],
    eligibility: Optional[b6.ProductEligibility],
    *,
    shadow_failed: bool = False,
    legacy_failed: bool = False,
) -> LegacyShadowParityRecord:
    """Build one observational parity record. Mutates neither input."""
    groups = copy.deepcopy(groups) if groups else groups

    legacy = observe_legacy(groups, match_result or {})
    shadow = observe_shadow(shadow_result, groups, eligibility)

    has_groups = bool(groups)
    groups_have_requirements = any(
        isinstance(g, dict) and (g.get("required") or g.get("family_relation"))
        for g in (groups or [])
    )

    category, reasons, status = classify(
        legacy, shadow, groups,
        shadow_failed=shadow_failed,
        legacy_failed=legacy_failed,
        has_groups=has_groups,
        groups_have_requirements=groups_have_requirements,
    )

    # ONE_OF metadata (explicit declarations only)
    one_of_ids = tuple(sorted({
        g.get("alternative_group_id")
        for g in (groups or [])
        if isinstance(g, dict)
        and g.get("family_relation") == ag.FAMILY_RELATION_ONE_OF
        and g.get("alternative_group_id")
    }))
    technique_only_one_of = any(
        isinstance(g, dict)
        and g.get("family_relation") == ag.FAMILY_RELATION_ONE_OF
        and all(
            not fc.is_conclusion_eligible(concept)
            for concept in (g.get("required") or [])
        )
        for g in (groups or [])
    )

    simulation = ConsequenceSimulation(
        legacy_allows_elo=legacy_authoritative(legacy.evidence),
        shadow_allows_elo=shadow.b6_eligible,
        legacy_allows_gap=legacy_authoritative(legacy.evidence),
        shadow_allows_gap=shadow.b6_eligible,
        legacy_allows_recommendation=legacy_authoritative(legacy.evidence),
        shadow_allows_recommendation=shadow.b6_eligible,
    )

    return LegacyShadowParityRecord(
        submission_id=submission_id,
        problem_id=problem_id,
        title=title,
        legacy=legacy,
        shadow=shadow,
        parity_category=category,
        divergence_reason=reasons,
        migration_status=status,
        consequence_simulation=simulation,
        technique_only_one_of=technique_only_one_of,
        one_of_group_ids=one_of_ids,
    )


__all__ = [
    # categories
    "PARITY_CATEGORIES", "P1_EXACT_PARITY", "P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED",
    "P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE", "P4_LEGACY_MATCH_SHADOW_UNRESOLVED",
    "P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED", "P6_LEGACY_MATCH_SHADOW_CONTRADICTED",
    "P7_AUTHORITY_CONFLICT", "P8_REPRESENTATION_DIFFERENCE", "P9_NO_COMPARABLE_GT",
    "P10_ERROR",
    # P2 sub-reasons
    "P2_REASONS", "P2_REASON_AUTHORITY_CONFLICT", "P2_REASON_NON_AUTHORITATIVE",
    "P2_REASON_COVERAGE_NOT_CONFIRMED", "P2_REASON_NO_PRIMARY_STRATEGY",
    "P2_REASON_NO_AUTHORITY_REPORT", "P2_REASON_ONE_OF_UNSATISFIED",
    "P2_REASON_OTHER",
    # statuses
    "MIGRATION_STATUSES", "STATUS_READY_FOR_SHADOW", "STATUS_BLOCKED_BY_AUTHORITY",
    "STATUS_BLOCKED_BY_GT", "STATUS_BLOCKED_BY_SHADOW_COVERAGE",
    "STATUS_BLOCKED_BY_PARITY", "STATUS_REPRESENTATION_ONLY", "STATUS_ERROR",
    # observation + records
    "LegacyObservation", "ShadowObservation", "ConsequenceSimulation",
    "LegacyShadowParityRecord",
    # functions
    "legacy_authoritative", "observe_legacy", "observe_shadow", "classify",
    "build_parity_record",
]
