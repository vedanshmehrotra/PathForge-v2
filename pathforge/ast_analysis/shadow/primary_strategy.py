"""Primary strategy selection — SHADOW / PRESENTATION LAYER ONLY (Batch B4).

BATCH B4 — SPECIFICITY + PRIMARY STRATEGY SELECTION
===================================================

B3 answered *"how much of an expected family is established?"* B4 answers the
next question: *"when several concepts are PRESENT, which conclusion-eligible
strategy should be treated as the primary approach?"*

This is a **selection** layer. It does not replace the official matcher, does not
change family coverage, and does not touch production.

The one hard principle
----------------------

A raw observation is never a primary strategy. A technique is never
automatically a primary strategy. Only a registry concept whose declared
``conclusion_eligible`` is ``True`` may become the primary strategy:

``OBSERVATION``  rank 0  → supporting evidence only
``TECHNIQUE``    rank 1/2 → supporting / family-identifying evidence only
``STRATEGY``     rank 3  → **may become the primary strategy**

The B1 registry is the sole source of truth. No precedence table is written
here: ``array_traversal``, ``brute_force``, ``sorting``, ``recursive_branching``,
``sequential_accumulation``, ``forward_pointer_advance`` and
``candidate_selection`` are excluded *because their registry metadata says so*,
never because a hand-written rule names them.

Family scope
------------

A strategy is never selected merely because it appears somewhere in the
submission. The candidate pool is exactly the family/submission's ``required``
concepts that are conclusion-eligible and ``PRESENT`` — the same principle as
B3's conclusion-eligible gate. An unrelated strategy detected elsewhere cannot
become a family's primary, and cannot make a family confirm.

Contradiction
-------------

A contradiction outranks a candidate only when it is an **applicable
family-level** contradiction (B3's rule). A concept-level ``CONTRADICTED`` never
blindly removes an otherwise-eligible candidate, and never affects an unrelated
family. Because the candidate pool is ``PRESENT`` concepts, an applicable
identifying contradiction simply leaves the family with no candidate and the
family is reported ``CONTRADICTED`` by B3 (which B4 does not rewrite).

Determinism
-----------

Candidate ordering is ``(-specificity_rank, -confidence, concept_id)``.
Specificity comes from the registry; confidence is only a secondary signal;
``concept_id`` is the final deterministic tie-break. No probabilistic model, no
LLM, no randomness, no insertion-order dependence.

Explicit ambiguity
------------------

Because every ``STRATEGY`` currently shares ``specificity_rank == 3``, two
equally-confident strategies can only be separated by ``concept_id``. That is a
deterministic tie-break, but it is **not** a principled specificity decision, so
it is reported as an explicit B4 ambiguity (``ambiguity = True``,
``reason = tie_broken_by_concept_id``) instead of inventing a ranking.

Not implemented here (later batches / out of scope): authority gating,
``PROVISIONAL`` visibility, official-matcher replacement, database/API/frontend
changes, Ground-Truth changes, detector changes, threshold tuning, new
strategies, recursive/greedy vocabulary, new falsifiers, zero-evidence
classification.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from pathforge.ast_analysis import concepts as concept_registry
from pathforge.ast_analysis.shadow import evidence_state as evidence
from pathforge.ast_analysis.shadow.family_coverage import (
    CONTRADICTED as _FAMILY_CONTRADICTED,
    is_conclusion_eligible,
)

# ============================================================================
# Reason codes (machine-readable, for measurement and audit)
# ============================================================================

REASON_SINGLE_CANDIDATE = "single_candidate"
REASON_SELECTED_BY_SPECIFICITY = "selected_by_specificity"
REASON_SELECTED_BY_CONFIDENCE = "selected_by_confidence"
REASON_TIE_BROKEN_BY_CONCEPT_ID = "tie_broken_by_concept_id"
REASON_NO_CONCLUSION_ELIGIBLE_PRESENT = "no_conclusion_eligible_present"
REASON_FAMILY_CONTRADICTED = "family_contradicted"

SCOPE_SUBMISSION = "submission"
SCOPE_FAMILY = "family"


# ============================================================================
# Records
# ============================================================================

@dataclass(frozen=True)
class StrategyCandidate:
    """One conclusion-eligible, PRESENT candidate strategy."""

    concept_id: str
    specificity_rank: int
    tier: str
    confidence: float
    evidence_source: str

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "specificity_rank": self.specificity_rank,
            "tier": self.tier,
            "confidence": round(self.confidence, 4),
            "evidence_source": self.evidence_source,
        }


@dataclass(frozen=True)
class StrategySelection:
    """A deterministic primary-strategy selection over one candidate scope."""

    scope: str
    family_id: Optional[str]
    candidates: Tuple[StrategyCandidate, ...]
    selected: Optional[str]
    reason_codes: Tuple[str, ...]
    tie_resolved: bool
    ambiguity: bool

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "family_id": self.family_id,
            "selected": self.selected,
            "reason_codes": list(self.reason_codes),
            "tie_resolved": self.tie_resolved,
            "ambiguity": self.ambiguity,
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass(frozen=True)
class SubmissionStrategySelection:
    """The submission-level selection plus the per-family selections."""

    submission: StrategySelection
    families: Tuple[StrategySelection, ...]

    def to_dict(self) -> dict:
        return {
            "submission": self.submission.to_dict(),
            "families": [f.to_dict() for f in self.families],
        }


# ============================================================================
# Candidate collection — registry + B2 snapshot only
# ============================================================================

def _ordered_unique(concept_ids: Sequence[str]) -> Tuple[str, ...]:
    seen: set = set()
    ordered = []
    for concept_id in concept_ids:
        if concept_id in seen:
            continue
        seen.add(concept_id)
        ordered.append(concept_id)
    return tuple(ordered)


def is_eligible_candidate(concept_id: str, snapshot) -> bool:
    """A concept may be a primary candidate iff it is conclusion-eligible and
    PRESENT. This is the registry gate plus the B2 state, nothing else."""
    if not is_conclusion_eligible(concept_id):
        return False
    if snapshot is None or not concept_registry.has_concept(concept_id):
        return False
    return snapshot.state_of(concept_id) == evidence.PRESENT


def candidate_strategies(
    relevant_concepts: Sequence[str], snapshot
) -> Tuple[StrategyCandidate, ...]:
    """Every eligible candidate among ``relevant_concepts``, ordered

    ``(-specificity_rank, -confidence, concept_id)`` — deterministic and derived
    only from registry metadata plus the B2 evidence."""
    candidates = []
    for concept_id in _ordered_unique(relevant_concepts):
        if not is_eligible_candidate(concept_id, snapshot):
            continue
        concept = concept_registry.get_concept(concept_id)
        item = snapshot.get(concept_id)
        candidates.append(StrategyCandidate(
            concept_id=concept_id,
            specificity_rank=concept.specificity_rank,
            tier=concept.tier,
            confidence=item.confidence,
            evidence_source=item.source,
        ))
    candidates.sort(key=lambda c: (-c.specificity_rank, -c.confidence, c.concept_id))
    return tuple(candidates)


# ============================================================================
# Selection
# ============================================================================

def select_primary_strategy(
    relevant_concepts: Sequence[str],
    snapshot,
    *,
    scope: str = SCOPE_SUBMISSION,
    family_id: Optional[str] = None,
    family_contradicted: bool = False,
) -> StrategySelection:
    """Select the primary strategy from an explicit scope of relevant concepts.

    ``relevant_concepts`` is the scope's ``required`` set (a family's, or the
    union of a submission's families'). Concepts outside it are **never**
    considered, so an unrelated detected strategy cannot become primary.

    ``family_contradicted`` is B3's applicable family-level contradiction. When
    set, the family is ruled out and no primary is reported — this is the only
    way a contradiction influences selection, and it must be the *family-level*
    one, never a mere concept-level state.
    """
    candidates = candidate_strategies(relevant_concepts, snapshot)

    if family_contradicted:
        return StrategySelection(
            scope=scope,
            family_id=family_id,
            candidates=candidates,
            selected=None,
            reason_codes=(REASON_FAMILY_CONTRADICTED,),
            tie_resolved=False,
            ambiguity=False,
        )

    if not candidates:
        return StrategySelection(
            scope=scope,
            family_id=family_id,
            candidates=(),
            selected=None,
            reason_codes=(REASON_NO_CONCLUSION_ELIGIBLE_PRESENT,),
            tie_resolved=False,
            ambiguity=False,
        )

    top = candidates[0]
    if len(candidates) == 1:
        return StrategySelection(
            scope=scope,
            family_id=family_id,
            candidates=candidates,
            selected=top.concept_id,
            reason_codes=(REASON_SINGLE_CANDIDATE,),
            tie_resolved=False,
            ambiguity=False,
        )

    runner_up = candidates[1]
    if top.specificity_rank > runner_up.specificity_rank:
        reason, tie_resolved, ambiguity = (
            REASON_SELECTED_BY_SPECIFICITY, False, False,
        )
    elif top.confidence > runner_up.confidence:
        reason, tie_resolved, ambiguity = (
            REASON_SELECTED_BY_CONFIDENCE, False, False,
        )
    else:
        # The registry cannot distinguish the leaders on specificity or
        # confidence, so concept_id decides deterministically. This is reported
        # as an explicit ambiguity rather than dressed up as a ranking.
        reason, tie_resolved, ambiguity = (
            REASON_TIE_BROKEN_BY_CONCEPT_ID, True, True,
        )

    return StrategySelection(
        scope=scope,
        family_id=family_id,
        candidates=candidates,
        selected=top.concept_id,
        reason_codes=(reason,),
        tie_resolved=tie_resolved,
        ambiguity=ambiguity,
    )


def family_primary_strategy(
    family: dict, snapshot, *, family_contradicted: bool = False
) -> StrategySelection:
    """The primary strategy of one family, scoped to its own ``required`` set."""
    family_id = str(family.get("id") or "") or None
    return select_primary_strategy(
        family.get("required") or [],
        snapshot,
        scope=SCOPE_FAMILY,
        family_id=family_id,
        family_contradicted=family_contradicted,
    )


def select_submission_primary(
    solution_groups: Optional[Sequence[dict]],
    snapshot,
    coverage_report=None,
) -> SubmissionStrategySelection:
    """The submission-level primary plus the per-family selections.

    The submission candidate pool is the **union of every family's ``required``
    concepts** — i.e. only strategies relevant to an evaluated family compete.
    A strategy detected elsewhere in the submission is not a candidate.
    """
    groups = [g for g in (solution_groups or []) if isinstance(g, dict)]

    family_selections = []
    for index, group in enumerate(groups):
        family_id = str(group.get("id") or f"family_{index}")
        contradicted = False
        if coverage_report is not None:
            try:
                contradicted = (
                    coverage_report.get(family_id).coverage_state
                    == _FAMILY_CONTRADICTED
                )
            except KeyError:  # pragma: no cover - defensive
                contradicted = False
        family_selections.append(
            family_primary_strategy(group, snapshot, family_contradicted=contradicted)
        )

    relevant = []
    for group in groups:
        relevant.extend(group.get("required") or [])

    submission = select_primary_strategy(relevant, snapshot, scope=SCOPE_SUBMISSION)
    return SubmissionStrategySelection(
        submission=submission,
        families=tuple(family_selections),
    )


__all__ = [
    # reason codes
    "REASON_SINGLE_CANDIDATE", "REASON_SELECTED_BY_SPECIFICITY",
    "REASON_SELECTED_BY_CONFIDENCE", "REASON_TIE_BROKEN_BY_CONCEPT_ID",
    "REASON_NO_CONCLUSION_ELIGIBLE_PRESENT", "REASON_FAMILY_CONTRADICTED",
    "SCOPE_SUBMISSION", "SCOPE_FAMILY",
    # helpers + records
    "is_eligible_candidate", "candidate_strategies", "select_primary_strategy",
    "family_primary_strategy", "select_submission_primary",
    "StrategyCandidate", "StrategySelection", "SubmissionStrategySelection",
]
