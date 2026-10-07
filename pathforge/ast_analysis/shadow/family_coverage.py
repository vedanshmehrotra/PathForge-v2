"""Family coverage — SHADOW PATH ONLY (Batch B3).

BATCH B3 — FAMILY COVERAGE + PROVISIONAL SHADOW STATE
=====================================================

B2 answered *"what is the state of each concept?"* This module answers the next
question, one layer up: *"how much of an expected family is established?"*

It sits **above** B2 and **below** the existing family matcher::

    concept evidence (B2)  →  family coverage (B3)  →  coverage state

The family definitions are the **existing** Ground-Truth solution groups
(``required`` / ``optional`` / ``excluded``). Nothing here rewrites Ground Truth,
changes a detector, changes a threshold, or edits the B2 falsifier ledger.

Roles, not new vocabulary
-------------------------

Each ``required`` concept is interpreted through the B1 registry's existing
``family_role`` metadata — the *only* place a role is declared:

``IDENTIFYING``
    May be the concept that identifies the family. These concepts are the
    family's identity anchors.
``COMPONENT`` / ``SUPPORTING``
    May appear in ``required`` but must not identify a family alone. They are the
    family's supporting/component requirements.
``ABSENT-NOT-ALLOWED``
    Must never appear in a requirement. If one does, it is treated as a
    non-identifying (supporting) requirement rather than inventing a new role.

The six states (exactly these, no additional semantic states)
-------------------------------------------------------------

``CONFIRMED``
    Valid GT + all identifying requirements ``PRESENT`` + no identifying
    contradiction + all supporting/component requirements established +
    **at least one conclusion-eligible concept PRESENT**. The last condition is
    the false-confirmation fence: a family with only TECHNIQUE/SUPPORT evidence
    can never be ``CONFIRMED`` from structural matches alone.
``PROVISIONAL``
    Valid GT + identifying requirements ``PRESENT`` + no identifying
    contradiction that rules the family out + one or more supporting/component
    requirements ``NOT_ESTABLISHED`` (or a supporting requirement
    contradicted). It means *"the family is supported by the established
    identifying evidence, but its evidence is incomplete"*. It is **not** a
    correctness verdict.
``UNRESOLVED``
    Identifying evidence (or the very existence of an identifying requirement)
    is not established sufficiently. Silence leads here, never to
    ``CONTRADICTED``.
``CONTRADICTED``
    The family itself is positively ruled out: an **applicable** identifying
    requirement is ``CONTRADICTED`` at the concept level.
``NO_GROUND_TRUTH``
    No family definitions were supplied at all.
``UNMATCHABLE``
    The family declares no requirement (empty ``required``) — the existing
    representation-gap case.

Contradiction is scoped, never escalated blindly
------------------------------------------------

B2's concept-level ``CONTRADICTED`` becomes a family-level ``CONTRADICTED``
**only** when the contradicted concept is one of the family's *identifying*
requirements. Otherwise the concept keeps its B2 state and the family is not
contradicted. This is what stops the broad ``dfs_backtracking`` contradiction
(raised by any ``cache_lookup``/``cache_write``) from ruling out families that
never required ``dfs_backtracking``. No new falsifier is invented and the B2
ledger is not touched; only the *application* of an existing contradiction to a
family is decided here.

B3 does not change the existing matcher
---------------------------------------

``evaluate_solution_groups`` (the old shadow matcher) is untouched and is still
reported as ``match_outcome``. ``run_shadow_analysis`` attaches the coverage
report **alongside** it (additively), so the two can be compared. Production is
not touched at all.

Not implemented here (later batches): specificity / precedence, primary-strategy
selection, observation demotion, authority gating, hypothesis handling, matcher
replacement, zero-evidence sanity classification, Ground-Truth changes.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pathforge.ast_analysis import concepts as concept_registry
from pathforge.ast_analysis.shadow import evidence_state as evidence

# ============================================================================
# States
# ============================================================================

CONFIRMED = "CONFIRMED"
PROVISIONAL = "PROVISIONAL"
UNRESOLVED = "UNRESOLVED"
CONTRADICTED = "CONTRADICTED"
NO_GROUND_TRUTH = "NO_GROUND_TRUTH"
UNMATCHABLE = "UNMATCHABLE"

#: The only six family-coverage states. There is deliberately no
#: ABSENT / FAILED / NO_MATCH / RECOGNIZED state.
COVERAGE_STATES: Tuple[str, ...] = (
    CONFIRMED,
    PROVISIONAL,
    UNRESOLVED,
    CONTRADICTED,
    NO_GROUND_TRUTH,
    UNMATCHABLE,
)

#: Priority used only to derive a *measurement* projection of a whole report
#: (``CoverageReport.aggregate_state``). It is NOT a replacement verdict.
#: A contradiction outranks a confirmation (proposal Rule S4).
AGGREGATE_PRIORITY: Dict[str, int] = {
    UNMATCHABLE: 0,
    NO_GROUND_TRUTH: 0,
    UNRESOLVED: 1,
    PROVISIONAL: 2,
    CONFIRMED: 3,
    CONTRADICTED: 4,
}

# -- reason codes (machine-readable, for measurement and audit) --------------

REASON_CONFIRMED = "confirmed"
REASON_NO_IDENTIFYING_REQUIREMENT = "no_identifying_requirement"
REASON_IDENTIFYING_NOT_ESTABLISHED = "identifying_not_established"
REASON_IDENTIFYING_CONTRADICTED = "identifying_contradicted"
REASON_SUPPORTING_NOT_ESTABLISHED = "supporting_not_established"
REASON_SUPPORTING_CONTRADICTED = "supporting_contradicted"
REASON_NO_CONCLUSION_ELIGIBLE = "no_conclusion_eligible"
REASON_UNMATCHABLE = "unmatchable"
REASON_NO_GROUND_TRUTH = "no_ground_truth"


# ============================================================================
# Role / eligibility helpers — all read from the B1 registry
# ============================================================================

def family_role_of(concept_id: str) -> Optional[str]:
    """The declared ``family_role`` of a concept, or ``None`` if unregistered."""
    if not concept_registry.has_concept(concept_id):
        return None
    return concept_registry.get_concept(concept_id).family_role


def is_identifying(concept_id: str) -> bool:
    """Whether a concept may identify a family (registry ``IDENTIFYING``)."""
    return family_role_of(concept_id) == concept_registry.IDENTIFYING


def is_conclusion_eligible(concept_id: str) -> bool:
    """Whether a concept may be a final reported conclusion.

    Read directly from the B1 registry's ``conclusion_eligible`` metadata — it is
    never inferred from technique/observation presence, ``v1_image`` or a legacy
    pattern name.
    """
    if not concept_registry.has_concept(concept_id):
        return False
    return concept_registry.get_concept(concept_id).conclusion_eligible


def _ordered_unique(concept_ids: Iterable[str]) -> Tuple[str, ...]:
    """Deduplicate while preserving declaration order (determinism)."""
    seen: set = set()
    ordered: List[str] = []
    for concept_id in concept_ids:
        if concept_id in seen:
            continue
        seen.add(concept_id)
        ordered.append(concept_id)
    return tuple(ordered)


def _state_of(snapshot, concept_id: str) -> str:
    """A concept's B2 state; an unregistered id can only be NOT_ESTABLISHED."""
    if snapshot is None or not concept_registry.has_concept(concept_id):
        return evidence.NOT_ESTABLISHED
    return snapshot.state_of(concept_id)


# ============================================================================
# The reusable conclusion-eligible gate
# ============================================================================

def conclusion_eligible_present(
    required_concepts: Sequence[str], snapshot
) -> Tuple[str, ...]:
    """The family's *required* concepts that are conclusion-eligible and PRESENT.

    This is the reusable coverage check later batches may consume. It uses the
    registry's ``conclusion_eligible`` metadata only. It is deliberately scoped
    to a family's ``required`` concepts: an unrelated conclusion-eligible
    strategy observed elsewhere in the submission (e.g. an ``optional`` boost)
    must not let a family whose own required evidence is only structural
    evidence become confirmable.
    """
    return tuple(
        concept_id
        for concept_id in _ordered_unique(required_concepts)
        if is_conclusion_eligible(concept_id) and _state_of(snapshot, concept_id) == evidence.PRESENT
    )


def family_has_conclusion_eligible_present(family: dict, snapshot) -> bool:
    """Does this family currently have a conclusion-eligible concept PRESENT?"""
    return bool(
        conclusion_eligible_present(family.get("required") or [], snapshot)
    )


# ============================================================================
# The coverage record
# ============================================================================

@dataclass(frozen=True)
class FamilyCoverage:
    """Immutable coverage of exactly one expected family for one submission."""

    family_id: str
    identifying_required: Tuple[str, ...]
    supporting_required: Tuple[str, ...]
    present_identifying: Tuple[str, ...]
    not_established_identifying: Tuple[str, ...]
    contradicted_identifying: Tuple[str, ...]
    present_supporting: Tuple[str, ...]
    not_established_supporting: Tuple[str, ...]
    contradicted_supporting: Tuple[str, ...]
    conclusion_eligible_present: Tuple[str, ...]
    coverage_state: str
    reason_codes: Tuple[str, ...]
    authority_tier: str = "unknown"
    #: B5.5 additive relation metadata. ``None`` for every ordinary family, so
    #: ordinary-family coverage semantics are unchanged. When set, the family is
    #: one alternative of an explicitly declared ``ONE_OF`` set.
    family_relation: Optional[str] = None
    alternative_group_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "family_id": self.family_id,
            "coverage_state": self.coverage_state,
            "reason_codes": list(self.reason_codes),
            "authority_tier": self.authority_tier,
            "family_relation": self.family_relation,
            "alternative_group_id": self.alternative_group_id,
            "identifying_required": list(self.identifying_required),
            "supporting_required": list(self.supporting_required),
            "present_identifying": list(self.present_identifying),
            "not_established_identifying": list(self.not_established_identifying),
            "contradicted_identifying": list(self.contradicted_identifying),
            "present_supporting": list(self.present_supporting),
            "not_established_supporting": list(self.not_established_supporting),
            "contradicted_supporting": list(self.contradicted_supporting),
            "conclusion_eligible_present": list(self.conclusion_eligible_present),
        }


@dataclass(frozen=True)
class CoverageReport:
    """Every expected family's coverage for one submission."""

    families: Tuple[FamilyCoverage, ...]
    no_ground_truth: bool = False

    def get(self, family_id: str) -> FamilyCoverage:
        for family in self.families:
            if family.family_id == family_id:
                return family
        raise KeyError(f"unknown family: {family_id!r}")

    def by_state(self, state: str) -> Tuple[FamilyCoverage, ...]:
        if state not in COVERAGE_STATES:
            raise ValueError(f"unknown coverage state: {state!r}")
        return tuple(f for f in self.families if f.coverage_state == state)

    def counts(self) -> Dict[str, int]:
        return {state: len(self.by_state(state)) for state in COVERAGE_STATES}

    def reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for family in self.families:
            for reason in family.reason_codes:
                counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items()))

    def aggregate_state(self) -> str:
        """A *measurement* projection of the report, not a new verdict.

        Used to compare the existing matcher's single outcome against B3's
        per-family coverage. Priority: CONTRADICTED > CONFIRMED > PROVISIONAL >
        UNRESOLVED; when no family is evaluable the report is UNMATCHABLE, and
        with no families at all it is NO_GROUND_TRUTH.
        """
        if self.no_ground_truth or not self.families:
            return NO_GROUND_TRUTH
        best = max(
            self.families,
            key=lambda f: AGGREGATE_PRIORITY[f.coverage_state],
        )
        if AGGREGATE_PRIORITY[best.coverage_state] == 0:
            return UNMATCHABLE
        return best.coverage_state

    def to_dict(self) -> dict:
        return {
            "no_ground_truth": self.no_ground_truth,
            "aggregate_state": self.aggregate_state(),
            "state_priority": dict(AGGREGATE_PRIORITY),
            "counts": self.counts(),
            "reason_counts": self.reason_counts(),
            "families": [f.to_dict() for f in self.families],
        }


# ============================================================================
# Coverage building
# ============================================================================

def _partition(
    concept_ids: Tuple[str, ...], snapshot
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    """Split concepts into (present, not_established, contradicted) by B2 state."""
    present = tuple(c for c in concept_ids if _state_of(snapshot, c) == evidence.PRESENT)
    not_established = tuple(
        c for c in concept_ids if _state_of(snapshot, c) == evidence.NOT_ESTABLISHED
    )
    contradicted = tuple(
        c for c in concept_ids if _state_of(snapshot, c) == evidence.CONTRADICTED
    )
    return present, not_established, contradicted


def coverage_for_family(
    family: dict, snapshot, index: int = 0
) -> FamilyCoverage:
    """Derive the coverage of one existing Ground-Truth family.

    The rule order is the contract; each branch is a single, documented case:

    1. no requirement at all -> UNMATCHABLE;
    2. no IDENTIFYING requirement -> UNRESOLVED (a component cannot identify a
       family on its own, so the family has no identity anchor);
    3. an identifying requirement is CONTRADICTED -> CONTRADICTED (the one
       applicable family-level contradiction);
    4. an identifying requirement is NOT_ESTABLISHED -> UNRESOLVED (silence is
       never a contradiction);
    5. otherwise every identifying requirement is PRESENT:
       a. a supporting/component requirement is not established (or is
          contradicted) -> PROVISIONAL;
       b. otherwise, if no conclusion-eligible concept is PRESENT -> PROVISIONAL
          (the false-confirmation fence);
       c. otherwise -> CONFIRMED.
    """
    family_id = str(family.get("id") or f"family_{index}")
    authority_tier = family.get("authority_tier", "unknown")
    family_relation = family.get("family_relation")
    alternative_group_id = family.get("alternative_group_id")

    required = _ordered_unique(family.get("required") or [])
    identifying_required = tuple(c for c in required if is_identifying(c))
    supporting_required = tuple(c for c in required if not is_identifying(c))

    present_id, not_est_id, contra_id = _partition(identifying_required, snapshot)
    present_sup, not_est_sup, contra_sup = _partition(supporting_required, snapshot)

    eligible_present = conclusion_eligible_present(required, snapshot)

    if not required:
        state, reasons = UNMATCHABLE, (REASON_UNMATCHABLE,)
    elif not identifying_required:
        # A family whose requirement set is composed only of COMPONENT /
        # SUPPORTING concepts declares no identity. This is the LC3236 shape:
        # structural evidence matches, but nothing may identify the family.
        state, reasons = UNRESOLVED, (REASON_NO_IDENTIFYING_REQUIREMENT,)
    elif contra_id:
        state, reasons = CONTRADICTED, (REASON_IDENTIFYING_CONTRADICTED,)
    elif not_est_id:
        state, reasons = UNRESOLVED, (REASON_IDENTIFYING_NOT_ESTABLISHED,)
    else:
        # Every identifying requirement is PRESENT.
        reasons_list: List[str] = []
        if not_est_sup:
            reasons_list.append(REASON_SUPPORTING_NOT_ESTABLISHED)
        if contra_sup:
            reasons_list.append(REASON_SUPPORTING_CONTRADICTED)
        if reasons_list:
            state, reasons = PROVISIONAL, tuple(reasons_list)
        elif not eligible_present:
            state, reasons = PROVISIONAL, (REASON_NO_CONCLUSION_ELIGIBLE,)
        else:
            state, reasons = CONFIRMED, (REASON_CONFIRMED,)

    return FamilyCoverage(
        family_id=family_id,
        identifying_required=identifying_required,
        supporting_required=supporting_required,
        present_identifying=present_id,
        not_established_identifying=not_est_id,
        contradicted_identifying=contra_id,
        present_supporting=present_sup,
        not_established_supporting=not_est_sup,
        contradicted_supporting=contra_sup,
        conclusion_eligible_present=eligible_present,
        coverage_state=state,
        reason_codes=reasons,
        authority_tier=authority_tier,
        family_relation=family_relation,
        alternative_group_id=alternative_group_id,
    )


def build_family_coverage(
    solution_groups: Optional[Sequence[dict]], snapshot
) -> CoverageReport:
    """Build the coverage report for one submission.

    Pure and deterministic. Reads family requirements from the supplied groups
    (the existing Ground Truth) and concept states from the supplied B2
    snapshot. It defines no new analysis semantics.
    """
    groups = [g for g in (solution_groups or []) if isinstance(g, dict)]
    if not groups:
        return CoverageReport(families=(), no_ground_truth=True)
    return CoverageReport(
        families=tuple(
            coverage_for_family(group, snapshot, index) for index, group in enumerate(groups)
        ),
        no_ground_truth=False,
    )


__all__ = [
    # states
    "CONFIRMED", "PROVISIONAL", "UNRESOLVED", "CONTRADICTED",
    "NO_GROUND_TRUTH", "UNMATCHABLE",
    "COVERAGE_STATES", "AGGREGATE_PRIORITY",
    # reason codes
    "REASON_CONFIRMED", "REASON_NO_IDENTIFYING_REQUIREMENT",
    "REASON_IDENTIFYING_NOT_ESTABLISHED", "REASON_IDENTIFYING_CONTRADICTED",
    "REASON_SUPPORTING_NOT_ESTABLISHED", "REASON_SUPPORTING_CONTRADICTED",
    "REASON_NO_CONCLUSION_ELIGIBLE", "REASON_UNMATCHABLE",
    "REASON_NO_GROUND_TRUTH",
    # helpers
    "family_role_of", "is_identifying", "is_conclusion_eligible",
    "conclusion_eligible_present", "family_has_conclusion_eligible_present",
    # records
    "FamilyCoverage", "CoverageReport",
    "coverage_for_family", "build_family_coverage",
]
