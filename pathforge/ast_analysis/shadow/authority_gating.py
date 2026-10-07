"""Authority gating — SHADOW PATH ONLY (Batch B5; canonicalized in B5.5).

BATCH B5 — AUTHORITY GATING
===========================

B4 answered *"what strategy does the available structural evidence support?"*
B5 answers the next, separate question: *"how authoritative is that result?"*

It is a pure evaluation layer stacked on top of B2/B3/B4::

    B2 evidence  →  B3 family coverage  →  B4 primary strategy  →  B5 authority

Nothing upstream is rewritten here. Coverage states, the B4 candidate ordering,
and the old matcher's ``match_outcome`` are consumed read-only.

BATCH B5.5 — CANONICAL VOCABULARY + ALTERNATIVE FAMILIES
========================================================

The stored-value → canonical-tier mapping now lives in exactly one place,
:mod:`pathforge.ast_analysis.authority_vocabulary`. This module imports it
instead of restating it, and re-exports the canonical names for compatibility.

B5.5 also adds explicit **alternative (``ONE_OF``) families**. A Ground-Truth
problem may express its accepted approaches as a set of alternatives::

    ONE_OF group G
        ├── family A (required dp_bottom_up)
        └── family B (required dp_top_down)

Exactly one alternative is expected to be established; the others are
*expected* to be unresolved. Such a set is one **logical requirement**: the
group is satisfied when at least one alternative is authoritative, and an
unresolved sibling no longer forces ``MIXED_AUTHORITY``. The individual family
decisions are always preserved; only the aggregation unit changes.

The one distinction that matters
--------------------------------

Structural observation is evidence about the submitted *implementation*. It is
**not** Ground Truth about the *expected* solution. A structurally detected
strategy becomes an authoritative matching conclusion only when an
authoritative Ground Truth establishes the expected concept *and* the coverage
rules are satisfied *and* B4 selected a primary strategy.

The authority rules (evaluated per family, deterministic)
---------------------------------------------------------

1. no Ground Truth at all            → ``NO_GROUND_TRUTH`` (non-authoritative);
2. coverage not ``CONFIRMED``        → non-authoritative (``coverage_not_confirmed``),
   regardless of the authority tier: B5 never overrides a B3 state;
3. coverage ``CONFIRMED`` but B4 selected no primary strategy
                                     → non-authoritative (``no_primary_strategy``);
4. coverage ``CONFIRMED`` + B4 primary + tier in
   :data:`~pathforge.ast_analysis.authority_vocabulary.AUTHORIZING_TIERS`
                                     → **authoritative**;
5. coverage ``CONFIRMED`` + B4 primary + ``STRUCTURALLY_OBSERVED``
                                     → non-authoritative (``structural_observation_only``);
6. coverage ``CONFIRMED`` + B4 primary + ``INFERRED`` / unrecognised
                                     → non-authoritative.

``safe_for_product_scoring`` is ``False`` unless rule 4 applies to every
**logical requirement** (an independent family, or a satisfied ``ONE_OF``
group) — so structural detection plus a B4 selection can never accidentally
become an authoritative product result.

Submission-level aggregation is explicit and preserves the family states:
``NO_GROUND_TRUTH`` | ``NO_AUTHORITATIVE_FAMILY`` | ``MIXED_AUTHORITY`` |
``ALL_FAMILIES_AUTHORITATIVE``. No single arbitrary "overall confidence" score
is invented.

Not implemented here (later batches / out of scope): B6 migration, official
matcher replacement, detector improvements, new techniques/strategies,
Ground-Truth corrections or relabelling, database/API/frontend changes, Elo /
gap / recommendation changes, confidence calibration, LLM classification,
``PROVISIONAL`` user-facing UI, strategy-precedence changes.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

from pathforge.ast_analysis import authority_vocabulary as _vocab_canonical

#: B6.5: the canonical vocabulary, used directly for conflict normalization.
vocab = _vocab_canonical

# ============================================================================
# Tiers — canonical definitions, re-exported
# ============================================================================

HUMAN_APPROVED = vocab.HUMAN_APPROVED
EXTERNAL_VERIFIED = vocab.EXTERNAL_VERIFIED
STRUCTURALLY_OBSERVED = vocab.STRUCTURALLY_OBSERVED
INFERRED = vocab.INFERRED

AUTHORITY_TIERS: Tuple[str, ...] = vocab.CANONICAL_TIERS
AUTHORITY_RANK: Dict[str, int] = vocab.CANONICAL_RANK
AUTHORIZING_TIERS = vocab.AUTHORIZING_TIERS

#: Backwards-compatible aliases for the canonical vocabulary.
AUTHORITY_TIER_MAP: Dict[str, str] = vocab.SOURCE_TIER_MAP
KNOWN_SOURCE_TIERS = vocab.KNOWN_SOURCE_TIERS
BUILDER_AUTHORITY_TIERS = vocab.VALID_GT_TIERS

#: Alternative-family relation markers.
FAMILY_RELATION_ONE_OF = vocab.FAMILY_RELATION_ONE_OF
FAMILY_RELATION_INDEPENDENT = vocab.FAMILY_RELATION_INDEPENDENT
RELATION_FIELD = vocab.RELATION_FIELD
ALTERNATIVE_GROUP_FIELD = vocab.ALTERNATIVE_GROUP_FIELD

# -- aggregation kinds -------------------------------------------------------

AGG_NO_GROUND_TRUTH = "NO_GROUND_TRUTH"
AGG_NO_AUTHORITATIVE_FAMILY = "NO_AUTHORITATIVE_FAMILY"
AGG_MIXED_AUTHORITY = "MIXED_AUTHORITY"
AGG_ALL_FAMILIES_AUTHORITATIVE = "ALL_FAMILIES_AUTHORITATIVE"

AGGREGATION_KINDS: Tuple[str, ...] = (
    AGG_NO_GROUND_TRUTH,
    AGG_NO_AUTHORITATIVE_FAMILY,
    AGG_MIXED_AUTHORITY,
    AGG_ALL_FAMILIES_AUTHORITATIVE,
)

# -- reason codes (machine-readable, for measurement and audit) --------------

REASON_AUTHORITATIVE_HUMAN_APPROVED = "authoritative_human_approved"
REASON_AUTHORITATIVE_EXTERNAL_VERIFIED = "authoritative_external_verified"
REASON_NO_GROUND_TRUTH = "no_ground_truth"
REASON_COVERAGE_NOT_CONFIRMED = "coverage_not_confirmed"
REASON_NO_PRIMARY_STRATEGY = "no_primary_strategy"
REASON_STRUCTURAL_OBSERVATION_ONLY = "structural_observation_only"
REASON_INFERRED_AUTHORITY = "inferred_authority"
REASON_UNRECOGNIZED_AUTHORITY = "unrecognized_authority_tier"

#: B6.5: the stored ``authority_tier`` and legacy ``evidence`` resolve to
#: different canonical tiers. Fail-closed for product consequences.
REASON_AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"

#: Bunched-alternative reason codes (logical-requirement level).
REASON_ALTERNATIVE_SATISFIED = "alternative_satisfied"
REASON_ALTERNATIVE_MULTIPLE_SATISFIED = "alternative_multiple_satisfied"
REASON_ALTERNATIVE_UNSATISFIED = "alternative_unsatisfied"


# ============================================================================
# Tier mapping helpers — delegate to the canonical vocabulary
# ============================================================================

def map_authority_tier(declared: Optional[str]) -> str:
    """Map a declared Ground-Truth tier onto the canonical tier model."""
    return vocab.normalize_authority_tier(declared)


def is_known_authority_tier(declared: Optional[str]) -> bool:
    """Whether a declared tier is explicitly recognised by the canonical map."""
    return vocab.is_known_source_tier(declared)


def authority_data_quality(declared_tiers: Iterable[Optional[str]]) -> dict:
    """Report Ground-Truth authority fields that cannot be interpreted cleanly."""
    return vocab.authority_data_quality(declared_tiers)


# ============================================================================
# Records
# ============================================================================

@dataclass(frozen=True)
class FamilyAuthority:
    """The authority decision for exactly one evaluated family."""

    family_id: str
    #: The raw ``authority_tier`` string as stored on the Ground-Truth group.
    declared_authority_tier: str
    #: The mapped canonical tier.
    authority_tier: str
    authority_known: bool
    authoritative: bool
    safe_for_product_scoring: bool
    coverage_state: str
    #: B4's selected primary strategy for this family (``None`` if none).
    primary_strategy: Optional[str]
    #: The conclusion-eligible PRESENT concepts of the family (from B3) — the
    #: structural evidence responsible for a positive coverage state.
    supporting_concepts: Tuple[str, ...]
    reason_codes: Tuple[str, ...]
    #: B5.5: relation to sibling families (``None`` for ordinary families).
    family_relation: Optional[str] = None
    alternative_group_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "family_id": self.family_id,
            "declared_authority_tier": self.declared_authority_tier,
            "authority_tier": self.authority_tier,
            "authority_known": self.authority_known,
            "authoritative": self.authoritative,
            "safe_for_product_scoring": self.safe_for_product_scoring,
            "coverage_state": self.coverage_state,
            "primary_strategy": self.primary_strategy,
            "supporting_concepts": list(self.supporting_concepts),
            "reason_codes": list(self.reason_codes),
            "family_relation": self.family_relation,
            "alternative_group_id": self.alternative_group_id,
        }


@dataclass(frozen=True)
class AlternativeGroupAuthority:
    """The authority of one explicitly declared ``ONE_OF`` alternative set."""

    group_id: str
    family_ids: Tuple[str, ...]
    authoritative: bool
    authoritative_family_ids: Tuple[str, ...]
    reason_codes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "family_ids": list(self.family_ids),
            "authoritative": self.authoritative,
            "authoritative_family_ids": list(self.authoritative_family_ids),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class AuthorityReport:
    """Every evaluated family's authority plus the submission aggregation."""

    families: Tuple[FamilyAuthority, ...]
    no_ground_truth: bool
    aggregation: str
    alternative_groups: Tuple[AlternativeGroupAuthority, ...] = ()

    # -- derived views -------------------------------------------------------

    def get(self, family_id: str) -> FamilyAuthority:
        for family in self.families:
            if family.family_id == family_id:
                return family
        raise KeyError(f"unknown family: {family_id!r}")

    def get_alternative_group(self, group_id: str) -> AlternativeGroupAuthority:
        for group in self.alternative_groups:
            if group.group_id == group_id:
                return group
        raise KeyError(f"unknown alternative group: {group_id!r}")

    def authoritative_families(self) -> Tuple[FamilyAuthority, ...]:
        return tuple(f for f in self.families if f.authoritative)

    def non_authoritative_families(self) -> Tuple[FamilyAuthority, ...]:
        return tuple(f for f in self.families if not f.authoritative)

    def authoritative_count(self) -> int:
        return len(self.authoritative_families())

    def has_authoritative_family(self) -> bool:
        return self.authoritative_count() > 0

    def logical_requirements(self) -> Tuple[str, ...]:
        """The aggregation units: each independent family, each ONE_OF group.

        Returns stable ids (family ids, or ``alternative_group:<id>``).
        """
        grouped = {
            f.family_id for f in self.families
            if f.family_relation == FAMILY_RELATION_ONE_OF and f.alternative_group_id
        }
        requirements = []
        seen_groups = set()
        for family in self.families:
            if family.family_id in grouped:
                group_id = family.alternative_group_id
                if group_id in seen_groups:
                    continue
                seen_groups.add(group_id)
                requirements.append(f"alternative_group:{group_id}")
            else:
                requirements.append(family.family_id)
        return tuple(requirements)

    def logical_requirement_count(self) -> int:
        return len(self.logical_requirements())

    def authoritative_logical_requirement_count(self) -> int:
        return len(self.authoritative_logical_requirements())

    def authoritative_logical_requirements(self) -> Tuple[str, ...]:
        grouped = {
            f.family_id: f.alternative_group_id for f in self.families
            if f.family_relation == FAMILY_RELATION_ONE_OF and f.alternative_group_id
        }
        group_authoritative = {
            g.group_id: g.authoritative for g in self.alternative_groups
        }
        result = []
        seen_groups = set()
        for family in self.families:
            if family.family_id in grouped:
                group_id = grouped[family.family_id]
                if group_id in seen_groups:
                    continue
                seen_groups.add(group_id)
                if group_authoritative.get(group_id):
                    result.append(f"alternative_group:{group_id}")
            elif family.authoritative:
                result.append(family.family_id)
        return tuple(result)

    def safe_for_product_scoring(self) -> bool:
        """Whether the whole submission is an authoritative product result.

        True only when at least one logical requirement is evaluated **and**
        every logical requirement is authoritative. A ``ONE_OF`` group counts
        once, and is authoritative when any of its alternatives is — an
        unresolved sibling is expected and does not make the submission mixed.
        """
        requirements = self.logical_requirements()
        if not requirements:
            return False
        return len(self.authoritative_logical_requirements()) == len(requirements)

    def authority_tier_counts(self) -> Dict[str, int]:
        return {tier: sum(1 for f in self.families if f.authority_tier == tier)
                for tier in AUTHORITY_TIERS}

    def coverage_state_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for family in self.families:
            counts[family.coverage_state] = counts.get(family.coverage_state, 0) + 1
        return dict(sorted(counts.items()))

    def reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for family in self.families:
            for reason in family.reason_codes:
                counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict:
        return {
            "no_ground_truth": self.no_ground_truth,
            "aggregation": self.aggregation,
            "family_count": len(self.families),
            "authoritative_family_count": self.authoritative_count(),
            "non_authoritative_family_count": len(self.non_authoritative_families()),
            "has_authoritative_family": self.has_authoritative_family(),
            "safe_for_product_scoring": self.safe_for_product_scoring(),
            "authority_tier_counts": self.authority_tier_counts(),
            "coverage_state_counts": self.coverage_state_counts(),
            "reason_counts": self.reason_counts(),
            "logical_requirement_count": self.logical_requirement_count(),
            "authoritative_logical_requirement_count":
                self.authoritative_logical_requirement_count(),
            "alternative_group_count": len(self.alternative_groups),
            "alternative_groups": [g.to_dict() for g in self.alternative_groups],
            "families": [f.to_dict() for f in self.families],
        }


# ============================================================================
# Decision
# ============================================================================

def _decide(
    *,
    declared_tier: str,
    coverage_state: str,
    primary_strategy: Optional[str],
) -> Tuple[str, bool, bool, bool, Tuple[str, ...]]:
    """Return ``(mapped_tier, known, authoritative, safe, reasons)``.

    The branch order is the contract. Coverage is consulted before authority, so
    no authority tier can override a B3 state, and no B4 selection can invent a
    conclusion that the coverage layer did not establish.
    """
    mapped = map_authority_tier(declared_tier)
    known = is_known_authority_tier(declared_tier)

    if coverage_state != "CONFIRMED":
        return mapped, known, False, False, (REASON_COVERAGE_NOT_CONFIRMED,)

    if not primary_strategy:
        return mapped, known, False, False, (REASON_NO_PRIMARY_STRATEGY,)

    if mapped == HUMAN_APPROVED:
        return mapped, known, True, True, (REASON_AUTHORITATIVE_HUMAN_APPROVED,)
    if mapped == EXTERNAL_VERIFIED:
        return mapped, known, True, True, (REASON_AUTHORITATIVE_EXTERNAL_VERIFIED,)
    if mapped == STRUCTURALLY_OBSERVED:
        return mapped, known, False, False, (REASON_STRUCTURAL_OBSERVATION_ONLY,)

    reason = REASON_UNRECOGNIZED_AUTHORITY if not known else REASON_INFERRED_AUTHORITY
    return mapped, known, False, False, (reason,)


def evaluate_family_authority(
    family_id: str,
    *,
    declared_authority_tier: str,
    coverage,
    primary_strategy: Optional[str],
) -> FamilyAuthority:
    """Evaluate one family's authority from its B3 coverage and B4 selection."""
    mapped, known, authoritative, safe, reasons = _decide(
        declared_tier=declared_authority_tier,
        coverage_state=coverage.coverage_state,
        primary_strategy=primary_strategy,
    )
    relation = getattr(coverage, "family_relation", None)
    group_id = getattr(coverage, "alternative_group_id", None)
    return FamilyAuthority(
        family_id=family_id,
        declared_authority_tier=declared_authority_tier,
        authority_tier=mapped,
        authority_known=known,
        authoritative=authoritative,
        safe_for_product_scoring=safe,
        coverage_state=coverage.coverage_state,
        primary_strategy=primary_strategy,
        supporting_concepts=tuple(coverage.conclusion_eligible_present),
        reason_codes=reasons,
        family_relation=relation,
        alternative_group_id=group_id,
    )


# ============================================================================
# Report building
# ============================================================================

def _build_alternative_groups(
    families: Sequence[FamilyAuthority],
) -> Tuple[AlternativeGroupAuthority, ...]:
    """One record per explicitly declared ``ONE_OF`` set with >= 2 members."""
    members: Dict[str, list] = {}
    for family in families:
        if (family.family_relation == FAMILY_RELATION_ONE_OF
                and family.alternative_group_id):
            members.setdefault(family.alternative_group_id, []).append(family)

    groups = []
    for group_id in sorted(members):
        group_families = members[group_id]
        if len(group_families) < 2:
            # A ONE_OF set of one is not an alternative set; leave it
            # independent rather than inventing a group.
            continue
        authoritative = tuple(
            f.family_id for f in group_families if f.authoritative
        )
        if not authoritative:
            reasons = (REASON_ALTERNATIVE_UNSATISFIED,)
        elif len(authoritative) == 1:
            reasons = (REASON_ALTERNATIVE_SATISFIED,)
        else:
            reasons = (REASON_ALTERNATIVE_MULTIPLE_SATISFIED,)
        groups.append(AlternativeGroupAuthority(
            group_id=group_id,
            family_ids=tuple(f.family_id for f in group_families),
            authoritative=bool(authoritative),
            authoritative_family_ids=authoritative,
            reason_codes=reasons,
        ))
    return tuple(groups)


def _aggregate(
    families: Sequence[FamilyAuthority],
    alternative_groups: Sequence[AlternativeGroupAuthority],
    no_ground_truth: bool,
) -> str:
    if no_ground_truth or not families:
        return AGG_NO_GROUND_TRUTH

    grouped = {
        f.family_id for f in families
        if f.family_relation == FAMILY_RELATION_ONE_OF and f.alternative_group_id
    }
    group_authoritative = {g.group_id: g.authoritative for g in alternative_groups}

    total = 0
    authoritative = 0
    seen_groups = set()
    for family in families:
        if family.family_id in grouped:
            group_id = family.alternative_group_id
            if group_id in seen_groups:
                continue
            seen_groups.add(group_id)
            # A ONE_OF set of one is not in alternative_groups; fall back to
            # the family's own decision so nothing is silently dropped.
            if group_id in group_authoritative:
                total += 1
                authoritative += 1 if group_authoritative[group_id] else 0
            else:
                total += 1
                authoritative += 1 if family.authoritative else 0
        else:
            total += 1
            authoritative += 1 if family.authoritative else 0

    if total == 0 or authoritative == 0:
        return AGG_NO_AUTHORITATIVE_FAMILY
    if authoritative == total:
        return AGG_ALL_FAMILIES_AUTHORITATIVE
    return AGG_MIXED_AUTHORITY


def evaluate_authority(
    solution_groups: Optional[Sequence[dict]],
    coverage_report,
    strategy_selection,
) -> Optional[AuthorityReport]:
    """Evaluate authority for a submission from B3 coverage + B4 selection.

    Pure and deterministic. Reads the existing Ground-Truth groups (for the
    declared authority tier and alternative-family relation), B3's
    :class:`CoverageReport` and B4's :class:`SubmissionStrategySelection`.
    Family alignment is positional: all three are built by enumerating the same
    ``solution_groups`` list.

    Returns ``None`` when the required upstream layers are unavailable — an
    authority decision is always *derived from* B3/B4, never invented.
    """
    groups = [g for g in (solution_groups or []) if isinstance(g, dict)]

    if coverage_report is None or strategy_selection is None:
        return None

    if not groups:
        return AuthorityReport(
            families=(), no_ground_truth=True, aggregation=AGG_NO_GROUND_TRUTH
        )

    coverage_families = list(getattr(coverage_report, "families", ()) or ())
    selection_families = list(getattr(strategy_selection, "families", ()) or ())

    families = []
    for index, group in enumerate(groups):
        if index >= len(coverage_families):
            break
        coverage = coverage_families[index]
        primary = None
        if index < len(selection_families):
            primary = selection_families[index].selected
        declared = getattr(coverage, "authority_tier", None)
        if declared is None:
            declared = group.get("authority_tier", "unknown")
        family = evaluate_family_authority(
            str(getattr(coverage, "family_id", None) or f"family_{index}"),
            declared_authority_tier=str(declared),
            coverage=coverage,
            primary_strategy=primary,
        )
        # B6.5: an unresolved normalization conflict fails closed. No precedence
        # is invented between the two stored representations; the family simply
        # cannot be authoritative while the conflict stands. The loader attaches
        # the normalization record; groups built directly are normalized here.
        normalization = group.get("authority_normalization")
        if not isinstance(normalization, dict):
            normalization = vocab.normalize_group_authority(group)
        if normalization.get("conflict"):
            family = FamilyAuthority(
                family_id=family.family_id,
                declared_authority_tier=family.declared_authority_tier,
                authority_tier=family.authority_tier,
                authority_known=family.authority_known,
                authoritative=False,
                safe_for_product_scoring=False,
                coverage_state=family.coverage_state,
                primary_strategy=family.primary_strategy,
                supporting_concepts=family.supporting_concepts,
                reason_codes=(REASON_AUTHORITY_CONFLICT,),
                family_relation=family.family_relation,
                alternative_group_id=family.alternative_group_id,
            )
        families.append(family)

    alternative_groups = _build_alternative_groups(families)
    no_gt = bool(getattr(coverage_report, "no_ground_truth", False)) and not families
    return AuthorityReport(
        families=tuple(families),
        no_ground_truth=no_gt,
        aggregation=_aggregate(families, alternative_groups, no_gt),
        alternative_groups=alternative_groups,
    )


__all__ = [
    # tiers
    "HUMAN_APPROVED", "EXTERNAL_VERIFIED", "STRUCTURALLY_OBSERVED", "INFERRED",
    "AUTHORITY_TIERS", "AUTHORITY_RANK", "AUTHORIZING_TIERS",
    "AUTHORITY_TIER_MAP", "KNOWN_SOURCE_TIERS", "BUILDER_AUTHORITY_TIERS",
    # relations
    "FAMILY_RELATION_ONE_OF", "FAMILY_RELATION_INDEPENDENT",
    "RELATION_FIELD", "ALTERNATIVE_GROUP_FIELD",
    # aggregation
    "AGG_NO_GROUND_TRUTH", "AGG_NO_AUTHORITATIVE_FAMILY", "AGG_MIXED_AUTHORITY",
    "AGG_ALL_FAMILIES_AUTHORITATIVE", "AGGREGATION_KINDS",
    # reason codes
    "REASON_AUTHORITATIVE_HUMAN_APPROVED", "REASON_AUTHORITATIVE_EXTERNAL_VERIFIED",
    "REASON_NO_GROUND_TRUTH", "REASON_COVERAGE_NOT_CONFIRMED",
    "REASON_NO_PRIMARY_STRATEGY", "REASON_STRUCTURAL_OBSERVATION_ONLY",
    "REASON_INFERRED_AUTHORITY", "REASON_UNRECOGNIZED_AUTHORITY",
    "REASON_ALTERNATIVE_SATISFIED", "REASON_ALTERNATIVE_MULTIPLE_SATISFIED",
    "REASON_ALTERNATIVE_UNSATISFIED", "REASON_AUTHORITY_CONFLICT",
    # helpers
    "map_authority_tier", "is_known_authority_tier", "authority_data_quality",
    "evaluate_family_authority", "evaluate_authority",
    # records
    "FamilyAuthority", "AlternativeGroupAuthority", "AuthorityReport",
]
