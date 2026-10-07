"""B6 — controlled integration of canonical shadow authority into product eligibility.

This is the first batch allowed to touch product-consequence code. It does NOT
replace the legacy matcher and does NOT change any scoring algorithm. It
establishes a single, explicit product-scoring eligibility decision that the
persistence path consults **only when the B6 feature flag is ON**.

Canonical authority flow (B1 → B6)::

    shadow evidence → B2 tri-state → B3 family coverage → B4 primary strategy
        → B5/B5.5 canonical authority → B6 product eligibility
        → ELO / gaps / recommendations

Policy (B5/B5.5, unchanged)
---------------------------

Only ``HUMAN_APPROVED`` and ``EXTERNAL_VERIFIED`` authorize product scoring.
``STRUCTURALLY_OBSERVED`` (analyzer evidence about the submitted implementation)
and ``INFERRED`` (LLM-proposed / bootstrap / missing / unrecognised) never
authorize. The canonical helpers in
:mod:`pathforge.ast_analysis.authority_vocabulary` are the only vocabulary used
here — no second mapping exists.

Eligibility rule
----------------

A logical requirement (an independent family, or an explicitly declared
``ONE_OF`` group) is **eligible** iff:

* B3 coverage is ``CONFIRMED``, **and**
* B4 selected a primary strategy, **and**
* the canonical authority tier is ``HUMAN_APPROVED`` or ``EXTERNAL_VERIFIED``.

Everything else is ineligible: ``PROVISIONAL``, ``UNRESOLVED``, ``CONTRADICTED``,
``NO_GROUND_TRUTH``, ``UNMATCHABLE``, missing/unrecognised authority,
``STRUCTURALLY_OBSERVED``, ``INFERRED``, or a missing primary strategy.
``PROVISIONAL`` is never treated as confirmed.

``ONE_OF`` semantics (B5.5, explicit metadata only)
---------------------------------------------------

* one authoritative alternative satisfies the logical requirement;
* an unresolved sibling does not downgrade an authoritative one to "mixed";
* all alternatives non-authoritative → the requirement is ineligible;
* multiple authoritative alternatives are all preserved.

Unmarked groups remain independent; ``db-254`` (different patterns, no explicit
provenance) is intentionally NOT treated as ``ONE_OF``.

Feature flag
------------

``SHADOW_AUTHORITY_PRODUCT_GATING`` (default **OFF**).

* **OFF** — the legacy product flow behaves exactly as before B6; nothing here
  is consulted.
* **ON** — the persistence path runs the shadow analysis, evaluates canonical
  authority + eligibility, and lets *that* decision gate ELO / gaps /
  recommendations. The legacy result is still computed and stored unchanged
  (never overwritten), so legacy-vs-shadow comparison remains possible.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import os

from pathforge.ast_analysis import authority_vocabulary as vocab
from pathforge.ast_analysis.shadow import authority_gating as ag

# ============================================================================
# Feature flag
# ============================================================================

#: Environment variable consulted once per import; tests monkeypatch
#: :func:`flag_enabled` instead of the environment.
FLAG_ENV_VAR = "SHADOW_AUTHORITY_PRODUCT_GATING"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag() -> str:
    return (os.environ.get(FLAG_ENV_VAR) or "").strip().lower()


def flag_enabled() -> bool:
    """Whether B6 product gating is enabled. **Default OFF.**"""
    return _env_flag() in _TRUE_VALUES


def flag_state() -> str:
    """The raw flag value, for audit output."""
    return _env_flag() or "<unset>"


# ============================================================================
# Records
# ============================================================================

@dataclass(frozen=True)
class ProductEligibility:
    """The single explicit product-scoring eligibility decision for a submission."""

    eligible: bool
    #: Why the decision was made (machine-readable reason codes).
    reason_codes: Tuple[str, ...]
    #: The canonical authority of the submission's logical requirements.
    canonical_authority: str
    #: The B5 aggregation kind (``ALL_FAMILIES_AUTHORITATIVE`` etc.).
    aggregation: str
    #: Per-logical-requirement decisions, in evaluation order.
    requirements: Tuple[dict, ...]
    #: B5's authoritative-vs-total logical-requirement counts.
    authoritative_requirements: int
    total_requirements: int
    #: True when every logical requirement is authoritative.
    safe_for_product_scoring: bool

    def to_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "reason_codes": list(self.reason_codes),
            "canonical_authority": self.canonical_authority,
            "aggregation": self.aggregation,
            "requirements": list(self.requirements),
            "authoritative_requirements": self.authoritative_requirements,
            "total_requirements": self.total_requirements,
            "safe_for_product_scoring": self.safe_for_product_scoring,
        }


@dataclass(frozen=True)
class LegacyShadowComparison:
    """Migration evidence: what legacy did vs what the canonical shadow would do.

    Purely informational. It never changes production behavior and never
    mutates either result.
    """

    legacy_outcome: Optional[str]
    legacy_authority: Optional[str]
    shadow_eligible: Optional[bool]
    shadow_authority: Optional[str]
    category: str

    def to_dict(self) -> dict:
        return {
            "legacy_outcome": self.legacy_outcome,
            "legacy_authority": self.legacy_authority,
            "shadow_eligible": self.shadow_eligible,
            "shadow_authority": self.shadow_authority,
            "category": self.category,
        }


# -- comparison categories (migration evidence, not behavior) ----------------

CATEGORY_CONFIRMED_AUTHORIZED = "LEGACY_CONFIRMED_SHADOW_AUTHORIZED"
CATEGORY_CONFIRMED_NOT_AUTHORIZED = "LEGACY_CONFIRMED_SHADOW_NOT_AUTHORIZED"
CATEGORY_UNRESOLVED_AUTHORIZED = "LEGACY_UNRESOLVED_SHADOW_AUTHORIZED"
CATEGORY_UNRESOLVED_NOT_AUTHORIZED = "LEGACY_UNRESOLVED_SHADOW_NOT_AUTHORIZED"
CATEGORY_CONTRADICTED_AUTHORIZED = "LEGACY_CONTRADICTED_SHADOW_AUTHORIZED"
CATEGORY_CONTRADICTED_NOT_AUTHORIZED = "LEGACY_CONTRADICTED_SHADOW_NOT_AUTHORIZED"
CATEGORY_OTHER = "LEGACY_OTHER"

COMPARISON_CATEGORIES: Tuple[str, ...] = (
    CATEGORY_CONFIRMED_AUTHORIZED,
    CATEGORY_CONFIRMED_NOT_AUTHORIZED,
    CATEGORY_UNRESOLVED_AUTHORIZED,
    CATEGORY_UNRESOLVED_NOT_AUTHORIZED,
    CATEGORY_CONTRADICTED_AUTHORIZED,
    CATEGORY_CONTRADICTED_NOT_AUTHORIZED,
    CATEGORY_OTHER,
)


def classify_comparison(
    legacy_outcome: Optional[str],
    shadow_eligible: Optional[bool],
) -> str:
    """Classify a legacy/shadow comparison case deterministically."""
    if legacy_outcome == "CONFIRMED":
        return (CATEGORY_CONFIRMED_AUTHORIZED if shadow_eligible
                else CATEGORY_CONFIRMED_NOT_AUTHORIZED)
    if legacy_outcome == "UNRESOLVED":
        return (CATEGORY_UNRESOLVED_AUTHORIZED if shadow_eligible
                else CATEGORY_UNRESOLVED_NOT_AUTHORIZED)
    if legacy_outcome == "CONTRADICTED":
        return (CATEGORY_CONTRADICTED_AUTHORIZED if shadow_eligible
                else CATEGORY_CONTRADICTED_NOT_AUTHORIZED)
    return CATEGORY_OTHER


# ============================================================================
# Eligibility decision
# ============================================================================

def product_eligibility(authority_report: ag.AuthorityReport) -> ProductEligibility:
    """The single product-scoring eligibility decision for a submission.

    Consumes the B5 :class:`AuthorityReport` read-only. The decision is
    ``eligible`` iff **every** logical requirement is authoritative — exactly
    B5.5's ``safe_for_product_scoring`` semantics, with ``ONE_OF`` groups
    counting once.
    """
    if authority_report is None:
        return ProductEligibility(
            eligible=False,
            reason_codes=("no_authority_report",),
            canonical_authority=vocab.INFERRED,
            aggregation=ag.AGG_NO_GROUND_TRUTH,
            requirements=(),
            authoritative_requirements=0,
            total_requirements=0,
            safe_for_product_scoring=False,
        )

    authoritative_ids = set(authority_report.authoritative_logical_requirements())
    requirements = []
    conflict = False
    for requirement_id in authority_report.logical_requirements():
        authoritative = requirement_id in authoritative_ids
        if authoritative:
            reason = "authorized"
        elif requirement_id.startswith("alternative_group:"):
            reason = "no_authoritative_alternative"
        else:
            family = _family_by_id(authority_report, requirement_id)
            reason = _blocked_reason(family)
            if reason == "authority_conflict":
                conflict = True
        requirements.append({
            "requirement_id": requirement_id,
            "eligible": authoritative,
            "reason_codes": [reason],
        })

    # B6.5: an authority normalization conflict is the headline reason —
    # reported first so it is never buried under the generic coverage reason.
    if conflict:
        submission_reasons = (vocab.AUTHORITY_CONFLICT,)
    else:
        submission_reasons = tuple(
            reason
            for requirement in requirements
            for reason in requirement["reason_codes"]
        ) or ("eligible",)

    return ProductEligibility(
        eligible=authority_report.safe_for_product_scoring(),
        reason_codes=submission_reasons,
        canonical_authority=_submission_authority(authority_report),
        aggregation=authority_report.aggregation,
        requirements=tuple(requirements),
        authoritative_requirements=len(authoritative_ids),
        total_requirements=len(requirements),
        safe_for_product_scoring=authority_report.safe_for_product_scoring(),
    )


def _family_by_id(authority_report, family_id):
    for family in authority_report.families:
        if family.family_id == family_id:
            return family
    return None


def _blocked_reason(family) -> str:
    if family is None:
        return "unknown_requirement"
    if family.authoritative:
        return "authorized"
    if any(code == "AUTHORITY_CONFLICT" for code in family.reason_codes):
        return "authority_conflict"
    if family.coverage_state == "CONFIRMED" and not family.primary_strategy:
        return "no_primary_strategy"
    if family.authority_tier == vocab.STRUCTURALLY_OBSERVED:
        return "structural_observation_only"
    if family.authority_tier == vocab.INFERRED and not family.authority_known:
        return "missing_authority"
    if family.authority_tier == vocab.INFERRED:
        return "inferred_authority"
    return "coverage_not_confirmed"


def _submission_authority(authority_report) -> str:
    """The strongest canonical tier present among the evaluated families."""
    tiers = [family.authority_tier for family in authority_report.families]
    if not tiers:
        return vocab.INFERRED
    return max(tiers, key=lambda tier: vocab.CANONICAL_RANK.get(tier, 0))


# ============================================================================
# Persistence integration (flag ON only)
# ============================================================================

def evaluate_submission(
    code: str,
    groups: Optional[list],
) -> Optional[dict]:
    """Run the shadow path end-to-end and produce the B6 records.

    Returns ``None`` when the shadow analysis fails (graceful degradation —
    production behavior is unchanged). The dict carries the shadow result, the
    B5 authority report and the B6 eligibility decision, kept **separate** from
    the legacy result.
    """
    from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

    shadow = run_shadow_analysis(code, solution_groups=groups)
    if shadow is None:
        return None

    authority_dict = shadow.get("authority")
    authority_report = None
    if authority_dict is not None:
        authority_report = _report_from_dict(authority_dict)

    eligibility = product_eligibility(authority_report)
    return {
        "shadow_result": shadow,
        "authority": authority_dict,
        "eligibility": eligibility,
    }


def _report_from_dict(data: dict) -> ag.AuthorityReport:
    """Rebuild an :class:`AuthorityReport` from its serialized form."""
    families = tuple(
        ag.FamilyAuthority(
            family_id=f["family_id"],
            declared_authority_tier=f["declared_authority_tier"],
            authority_tier=f["authority_tier"],
            authority_known=f["authority_known"],
            authoritative=f["authoritative"],
            safe_for_product_scoring=f["safe_for_product_scoring"],
            coverage_state=f["coverage_state"],
            primary_strategy=f["primary_strategy"],
            supporting_concepts=tuple(f["supporting_concepts"]),
            reason_codes=tuple(f["reason_codes"]),
            family_relation=f.get("family_relation"),
            alternative_group_id=f.get("alternative_group_id"),
        )
        for f in data.get("families", [])
    )
    alternative_groups = tuple(
        ag.AlternativeGroupAuthority(
            group_id=g["group_id"],
            family_ids=tuple(g["family_ids"]),
            authoritative=g["authoritative"],
            authoritative_family_ids=tuple(g["authoritative_family_ids"]),
            reason_codes=tuple(g["reason_codes"]),
        )
        for g in data.get("alternative_groups", [])
    )
    return ag.AuthorityReport(
        families=families,
        no_ground_truth=data.get("no_ground_truth", False),
        aggregation=data.get("aggregation", ag.AGG_NO_GROUND_TRUTH),
        alternative_groups=alternative_groups,
    )


def gating_decision(
    conn,
    user_id: int,
    code: str,
    groups: Optional[list],
    match_result: dict,
    *,
    shadow_evaluation: Optional[dict],
) -> dict:
    """Decide whether product consequences (ELO/gaps/recommendations) may run.

    The decision itself:

    * flag **OFF** → legacy behavior (gate passes iff the legacy verdict_type is
      ``authoritative`` — the pre-B6 contract, unchanged);
    * flag **ON** → the B6 eligibility decision gates, fail-closed. A missing
      or failed shadow evaluation can never enable scoring.

    Returns a dict with ``allow``, ``verdict_type``, ``source`` and the
    comparison record. It does **not** mutate either result.
    """
    legacy_outcome_data = match_result.get("match_result") if isinstance(
        match_result, dict
    ) else None
    # The legacy MatchOutcome analogue: the route computes it from the legacy
    # matcher; here we reuse the shadow match_outcome only for comparison.
    comparison = None
    if shadow_evaluation is not None:
        eligibility: ProductEligibility = shadow_evaluation["eligibility"]
        authority = shadow_evaluation.get("authority") or {}
        shadow_outcome = ((shadow_evaluation.get("shadow_result") or {})
                          .get("match_outcome") or {}).get("outcome")
        comparison = LegacyShadowComparison(
            legacy_outcome=shadow_outcome,
            legacy_authority=((shadow_evaluation.get("shadow_result") or {})
                              .get("match_outcome") or {}).get("authority_tier"),
            shadow_eligible=eligibility.eligible,
            shadow_authority=eligibility.canonical_authority,
            category=classify_comparison(shadow_outcome, eligibility.eligible),
        ).to_dict()

    if not flag_enabled():
        return {
            "allow_legacy": True,
            "allow_shadow": False,
            "source": "legacy",
            "verdict_type": "legacy",
            "comparison": comparison,
            "eligibility": None,
        }

    # Flag ON — canonical gate, fail-closed.
    eligibility = (shadow_evaluation or {}).get("eligibility")
    if eligibility is None:
        return {
            "allow_legacy": True,
            "allow_shadow": False,
            "source": "b6_gate",
            "verdict_type": "analysis_only",
            "comparison": comparison,
            "eligibility": None,
        }

    return {
        "allow_legacy": True,
        "allow_shadow": eligibility.eligible,
        "source": "b6_gate",
        "verdict_type": "authoritative" if eligibility.eligible else "analysis_only",
        "comparison": comparison,
        "eligibility": eligibility.to_dict(),
    }


__all__ = [
    # flag
    "FLAG_ENV_VAR", "flag_enabled", "flag_state",
    # records
    "ProductEligibility", "LegacyShadowComparison",
    # comparison
    "COMPARISON_CATEGORIES", "classify_comparison",
    "CATEGORY_CONFIRMED_AUTHORIZED", "CATEGORY_CONFIRMED_NOT_AUTHORIZED",
    "CATEGORY_UNRESOLVED_AUTHORIZED", "CATEGORY_UNRESOLVED_NOT_AUTHORIZED",
    "CATEGORY_CONTRADICTED_AUTHORIZED", "CATEGORY_CONTRADICTED_NOT_AUTHORIZED",
    "CATEGORY_OTHER",
    # decision
    "product_eligibility", "evaluate_submission", "gating_decision",
]
