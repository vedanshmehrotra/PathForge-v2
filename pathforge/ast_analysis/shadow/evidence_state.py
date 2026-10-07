"""Tri-state concept evidence — SHADOW PATH ONLY (Batch B2).

BATCH B2 — REPRESENTATION / INSTRUMENTATION ONLY
===============================================

This module adds an explicit three-valued evidence state per registered concept:

``PRESENT``
    The concept has admissible positive structural evidence at or above the
    existing shadow admissibility floor.

``NOT_ESTABLISHED``
    The concept has **not been established by the current evidence system**.
    This is the state for: no positive evidence; evidence below the floor; an
    unsupported structural form; and plain silence.

    It explicitly does **not** mean "the solution does not use this concept".

``CONTRADICTED``
    There is **positive structural evidence that contradicts** the concept.

**Silence is never a contradiction** (§5 of the approved proposal, rules K1/K2).
The only contradiction sources are:

1. an explicit **structural falsifier** — a positively observed raw structural
   fact that negates the concept (see ``STRUCTURAL_FALSIFIERS``); and
2. an explicit **mutual-exclusion relationship** where the excluded concept is
   positively established (see ``_mutual_exclusions``, which *reads* the
   existing declaration in ``coherence.STRATEGY_COMPATIBILITY`` rather than
   restating it).

Explicitly **not** contradiction sources: absence of evidence, low confidence,
unsupported syntax, a different detected concept, a different primary strategy,
a legacy Ground-Truth exclusion, or a legacy absence rule.

B2 does not change any verdict
------------------------------

Nothing in this module feeds a decision. ``run_shadow_analysis`` attaches the
snapshot **alongside** its existing result; ``evaluate_solution_groups`` and
every other existing shadow decision path is untouched. The legacy exclusion
semantics in ``matching.py`` therefore behave exactly as before.

Not implemented here (later batches): coverage logic, ``PROVISIONAL``,
necessity/identifying semantics, precedence, primary-strategy selection, of
zero-evidence sanity classification, authority gating, matcher replacement.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pathforge.ast_analysis import concepts as concept_registry
from pathforge.ast_analysis.shadow.coherence import STRATEGY_COMPATIBILITY

# ============================================================================
# States
# ============================================================================

PRESENT = "PRESENT"
NOT_ESTABLISHED = "NOT_ESTABLISHED"
CONTRADICTED = "CONTRADICTED"

#: The only three semantic states. There is deliberately no ABSENT / NOT_USED /
#: FALSE / MISSING state.
EVIDENCE_STATES: Tuple[str, ...] = (PRESENT, NOT_ESTABLISHED, CONTRADICTED)

#: State priority for a single concept: CONTRADICTED > PRESENT > NOT_ESTABLISHED.
STATE_PRIORITY: Dict[str, int] = {
    NOT_ESTABLISHED: 0,
    PRESENT: 1,
    CONTRADICTED: 2,
}

#: The existing shadow admissibility boundary. Reused, not recalibrated: this
#: is the same `confidence >= 0.5` test the shadow matcher already applies to
#: required concepts. No detector threshold is changed by B2.
EVIDENCE_FLOOR: float = 0.5

# -- reason codes (machine-readable, for measurement and audit) --------------

REASON_PRESENT = "present"
REASON_SILENT = "silent"
REASON_BELOW_FLOOR = "below_floor"
REASON_NO_PRODUCER = "no_producer"
REASON_DOCUMENTED_ONLY = "documented_only"
REASON_STRUCTURAL_FALSIFIER = "structural_falsifier"
REASON_MUTUAL_EXCLUSION = "mutual_exclusion"

# -- evidence producers ------------------------------------------------------

SOURCE_STRUCTURAL_FACT = "structural_fact"
SOURCE_TECHNIQUE_EVIDENCE = "technique_evidence"
SOURCE_STRATEGY_EVIDENCE = "strategy_evidence"
SOURCE_NONE = "none"


# ============================================================================
# Contradiction source 1 — explicit structural falsifiers
# ============================================================================

#: ``concept_id -> structural fact types`` whose POSITIVE observation is a
#: structural falsifier of the concept.
#:
#: Inclusion rule (recorded so this table cannot silently grow), all four of
#: which must hold:
#:
#: 1. the concept's registry ``falsifier`` metadata must already be non-empty
#:    **and must not be a legacy exclusion** — no falsifier is invented for a
#:    concept that declares none, and a legacy Ground-Truth exclusion is never
#:    reinterpreted as structural (see ``validate_falsifier_ledger``);
#: 2. every listed id must be a registered STRUCTURAL FACT — i.e. a raw
#:    observation. A condition expressed as "another *concept* is present" is
#:    NOT included (that is the forbidden "a different detected concept" case),
#:    and neither is a condition that only blocks one internal branch of a
#:    detector;
#: 3. the condition must be an **unconditional** absence constraint the
#:    implementation already applies, cited in the trace below — a constraint
#:    guarded by a further refinement of the same fact is not decisive;
#: 4. observation of the fact must actually negate the concept, not merely
#:    disqualify one path to establishing it.
#:
#: Every entry is a transcription of existing implemented behaviour. Nothing new
#: is defined about the analysis here; B2 only makes the existing condition
#: observable as a state.
STRUCTURAL_FALSIFIERS: Dict[str, Tuple[str, ...]] = {
    # trace: strategies.py::_evaluate_sliding_window
    #        `has_midpoint = "midpoint_calculation" in fact_types; if has_midpoint: return None`
    #        (only the raw-fact clause of the declared falsifier is encoded; the
    #        other two clauses are recorded in PARTIAL_FALSIFIER_NOTES)
    "sliding_window": ("midpoint_calculation",),
    # trace: strategies.py::_evaluate_binary_search
    #        `has_opposite = "opposite_direction_updates" in fact_types; if has_opposite: return None`
    "binary_search": ("opposite_direction_updates",),
    # trace: strategies.py::_evaluate_dp_top_down
    #        `has_state_restoration = "state_restoration" in fact_types; if ...: return None`
    "dp_top_down": ("state_restoration",),
    # trace: strategies.py::_evaluate_dfs_backtracking
    #        `has_cache = "cache_lookup" in fact_types or "cache_write" in fact_types; if has_cache: return None`
    "dfs_backtracking": ("cache_lookup", "cache_write"),
}

#: Registry concepts that DO declare falsifier metadata which B2 deliberately
#: does NOT turn into contradictions, with the reason. Recorded so nothing is
#: dropped silently.
DEFERRED_FALSIFIERS: Dict[str, str] = {
    "hash_lookup": (
        "registry falsifier is 'recursive_branching evidence present' — a "
        "condition on ANOTHER CONCEPT (a technique), not a raw structural fact. "
        "B2 must not infer a contradiction from a different detected concept, "
        "and coherence.STRATEGY_COMPATIBILITY declares no mutual exclusion for "
        "this pair."
    ),
    "frequency_counting": (
        "same form as hash_lookup: a concept-condition (recursive_branching), "
        "not a raw structural fact, and no explicit mutual exclusion exists."
    ),
    "dp_bottom_up": (
        "same form: a concept-condition (recursive_branching). The mutual "
        "exclusion is expressed only as an evaluator absence constraint, not as "
        "an explicit declaration, so it stays NOT_ESTABLISHED."
    ),
    "bfs_shortest_path": (
        "same form: a concept-condition (recursive_branching); no explicit "
        "mutual-exclusion declaration."
    ),
    "forward_pointer_advance": (
        "the declared condition is branch-scoped, not decisive: "
        "_detect_forward_pointer_advance excludes parent_pointer_chase only from "
        "its index-pair path, and the multi-pointer path can still establish the "
        "concept. A condition that does not negate the concept is not a "
        "falsifier."
    ),
}

#: Legacy exclusion metadata copied into the registry by B1 from
#: ``PATTERN_TO_V1_MAPPING``. These are "do not activate this concept when X is
#: present" Ground-Truth rules, NOT structural falsifiers, and they must never
#: produce CONTRADICTED. All 23 of them fall in this bucket and generate
#: NOT_ESTABLISHED at most.
LEGACY_EXCLUSION_PREFIX = "declared exclusion (PATTERN_TO_V1_MAPPING)"

#: The single most tempting legacy exclusion to misread as structural, recorded
#: so the decision is explicit rather than accidental. Not part of the falsifier
#: partition above (it is already a LEGACY exclusion).
LEGACY_EXCLUSION_NOTES: Dict[str, str] = {
    "two_pointers_opposite": (
        "this concept declares only the legacy exclusion 'declared exclusion "
        "(PATTERN_TO_V1_MAPPING): binary_search' — a Ground-Truth activation "
        "rule, not a structural falsifier. A mirror-image structural constraint "
        "does exist in the evaluator (_evaluate_two_pointers_opposite returns "
        "None on midpoint_calculation), but the registry does not declare it as "
        "this concept's falsifier, and no explicit mutual exclusion covers the "
        "pair (coherence records binary_search/two_pointers_opposite as a "
        "warning-level evaluator constraint only). B2 therefore leaves it "
        "NOT_ESTABLISHED rather than CONTRADICTED. Reinterpreting the legacy "
        "exclusion as structural is exactly what the FALSIFIER RULE forbids; "
        "encoding the undeclared mirror constraint would be inventing a "
        "falsifier. If B4 wants this pair enforced, it should be declared in the "
        "registry first."
    ),
}

#: Composite/unmodelled clauses of a declared falsifier that is only partially
#: encoded above (documentation of the partial encoding).
PARTIAL_FALSIFIER_NOTES: Dict[str, str] = {
    "sliding_window": (
        "the declared falsifier is a composite. Only its first clause "
        "(midpoint_calculation present) is an unconditional raw-fact constraint "
        "and is encoded. The second clause ('a genuine opposite-direction scan') "
        "is NOT encoded: _evaluate_sliding_window guards it behind a further "
        "refinement of the same fact (it re-checks, per while_loop_comparison, "
        "whether compared_variables <= modified_variables), so observing "
        "opposite_direction_updates alone does not negate the concept. The third "
        "clause is a three-fact monotonic-stack conjunction, which is not a "
        "single raw fact. Nothing here is dropped silently."
    ),
}


def legacy_exclusion_ids() -> frozenset:
    """Concept ids whose registry falsifier is a legacy Ground-Truth exclusion."""
    return frozenset(
        concept.concept_id
        for concept in concept_registry.all_concepts()
        if (concept.falsifier or "").startswith(LEGACY_EXCLUSION_PREFIX)
    )


def deferred_falsifier_ids() -> frozenset:
    """Concept ids whose declared falsifier B2 deliberately does not enforce."""
    return frozenset(DEFERRED_FALSIFIERS)


def structural_falsifier_ids() -> frozenset:
    """Concept ids that can be contradicted by a positively observed fact."""
    return frozenset(STRUCTURAL_FALSIFIERS)


def concepts_declaring_a_falsifier() -> frozenset:
    """Every registry concept that declares falsifier metadata."""
    return frozenset(
        concept.concept_id
        for concept in concept_registry.all_concepts()
        if concept.falsifier
    )


def validate_falsifier_ledger() -> None:
    """Assert the three falsifier buckets exactly partition the declarations.

    Raises ``ValueError`` on any drift, so a new falsifier cannot be added to
    the registry without being deliberately classified here.
    """
    structural = structural_falsifier_ids()
    deferred = deferred_falsifier_ids()
    legacy = legacy_exclusion_ids()

    overlap = (structural & deferred) | (structural & legacy) | (deferred & legacy)
    if overlap:
        raise ValueError(f"falsifier buckets overlap: {sorted(overlap)}")

    declared = concepts_declaring_a_falsifier()
    union = structural | deferred | legacy
    if union != declared:
        raise ValueError(
            "falsifier ledger does not cover every declared falsifier: "
            f"unclassified={sorted(declared - union)} "
            f"phantom={sorted(union - declared)}"
        )

    for concept_id, fact_ids in STRUCTURAL_FALSIFIERS.items():
        if not concept_registry.has_concept(concept_id):
            raise ValueError(f"structural falsifier for unregistered concept {concept_id!r}")
        declared = concept_registry.get_concept(concept_id).falsifier or ""
        if declared.startswith(LEGACY_EXCLUSION_PREFIX):
            raise ValueError(
                f"{concept_id}: a legacy exclusion must never be reinterpreted as "
                "a structural falsifier"
            )
        if not declared:
            raise ValueError(
                f"{concept_id}: structural falsifier encoded for a concept that "
                "does not declare one"
            )
        for other_id, partners in MUTUAL_EXCLUSIONS.items():
            if not concept_registry.has_concept(other_id):
                raise ValueError(
                    f"mutual-exclusion victim {other_id!r} is not a registered concept"
                )
            for partner in partners:
                if not concept_registry.has_concept(partner):
                    raise ValueError(
                        f"{other_id}: mutual-exclusion partner {partner!r} is not a "
                        "registered concept"
                    )
        for fact_id in fact_ids:
            if not concept_registry.has_concept(fact_id):
                raise ValueError(
                    f"{concept_id}: structural falsifier names unregistered "
                    f"fact {fact_id!r}"
                )
            fact = concept_registry.get_concept(fact_id)
            if concept_registry.SRC_STRUCTURAL_FACT not in fact.sources:
                raise ValueError(
                    f"{concept_id}: structural falsifier {fact_id!r} is not a "
                    "registered structural fact"
                )
            if fact.concept_class != concept_registry.OBSERVATION:
                raise ValueError(
                    f"{concept_id}: structural falsifier {fact_id!r} is not an "
                    "observation"
                )


# ============================================================================
# Contradiction source 2 — explicit mutual exclusion (read, not restated)
# ============================================================================

def _mutual_exclusions() -> Dict[str, Tuple[str, ...]]:
    """Mutual exclusions exactly as declared by the shadow coherence layer.

    ``coherence.STRATEGY_COMPATIBILITY`` documents *"Only evidence-backed
    contradictions are marked mutually exclusive"*. B2 consumes that existing
    declaration instead of duplicating it.
    """
    return {
        strategy_id: tuple(config.get("mutually_exclusive_with") or ())
        for strategy_id, config in STRATEGY_COMPATIBILITY.items()
    }


MUTUAL_EXCLUSIONS: Dict[str, Tuple[str, ...]] = _mutual_exclusions()


# ============================================================================
# Evidence record
# ============================================================================

@dataclass(frozen=True)
class ConceptEvidence:
    """The tri-state evidence for exactly one registered concept.

    ``v1_image`` / ``image_state`` carry aliasing information only. For legacy
    ids the shadow evidence system has no producer, so their own ``state`` stays
    NOT_ESTABLISHED and the state of the V1 concept they map to is reported
    separately, clearly labelled as a projection rather than as this concept's
    own evidence.
    """

    concept_id: str
    state: str
    confidence: float
    source: str
    reason_code: str
    evidence_refs: Tuple[str, ...] = ()
    contradiction_source: str = ""
    image_state: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "state": self.state,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "reason_code": self.reason_code,
            "evidence_refs": list(self.evidence_refs),
            "contradiction_source": self.contradiction_source,
            "v1_image": concept_registry.get_concept(self.concept_id).v1_image,
            "image_state": self.image_state,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EvidenceSnapshot:
    """Every registered concept's tri-state evidence for one submission."""

    evidence: Tuple[ConceptEvidence, ...]
    floor: float = EVIDENCE_FLOOR

    def get(self, concept_id: str) -> ConceptEvidence:
        for item in self.evidence:
            if item.concept_id == concept_id:
                return item
        raise KeyError(f"unregistered concept: {concept_id!r}")

    def state_of(self, concept_id: str) -> str:
        return self.get(concept_id).state

    def by_state(self, state: str) -> Tuple[ConceptEvidence, ...]:
        if state not in EVIDENCE_STATES:
            raise ValueError(f"unknown evidence state: {state!r}")
        return tuple(item for item in self.evidence if item.state == state)

    def counts(self) -> Dict[str, int]:
        return {state: len(self.by_state(state)) for state in EVIDENCE_STATES}

    def reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self.evidence:
            counts[item.reason_code] = counts.get(item.reason_code, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict:
        return {
            "floor": self.floor,
            "state_priority": dict(STATE_PRIORITY),
            "counts": self.counts(),
            "reason_counts": self.reason_counts(),
            "evidence": [item.to_dict() for item in self.evidence],
        }


# ============================================================================
# Evidence building
# ============================================================================

def _facts_by_type(facts: Sequence) -> Dict[str, Tuple[str, ...]]:
    """Map ``fact_type -> (fact_id, ...)`` in observation order."""
    grouped: Dict[str, List[str]] = {}
    for fact in facts or []:
        grouped.setdefault(fact.fact_type, []).append(fact.fact_id)
    return {fact_type: tuple(ids) for fact_type, ids in grouped.items()}


def _producer_evidence(
    concept,
    facts_by_type: Dict[str, Tuple[str, ...]],
    technique_by_id: Dict[str, object],
    strategy_by_id: Dict[str, object],
) -> Tuple[ConceptEvidence, ...]:
    """Every candidate evidence item any producer can raise for one concept."""
    candidates: List[ConceptEvidence] = []
    concept_id = concept.concept_id

    # Producer 1 — raw structural fact. A fact is a deterministic observation
    # with no confidence scale of its own, so an observed fact is confidence
    # 1.0 by construction.
    if concept_registry.SRC_STRUCTURAL_FACT in concept.sources:
        refs = facts_by_type.get(concept_id, ())
        if refs:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=PRESENT,
                confidence=1.0,
                source=SOURCE_STRUCTURAL_FACT,
                reason_code=REASON_PRESENT,
                evidence_refs=refs,
                reason=f"structural fact observed ({len(refs)} occurrence(s))",
            ))
        else:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=NOT_ESTABLISHED,
                confidence=0.0,
                source=SOURCE_STRUCTURAL_FACT,
                reason_code=REASON_SILENT,
                reason="structural fact not observed in this submission",
            ))

    # Producer 2 — shadow technique evidence.
    if concept_registry.SRC_V1_TECHNIQUE in concept.sources:
        technique = technique_by_id.get(concept_id)
        if technique is None:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=NOT_ESTABLISHED,
                confidence=0.0,
                source=SOURCE_TECHNIQUE_EVIDENCE,
                reason_code=REASON_SILENT,
                reason="no technique evidence was produced for this concept",
            ))
        elif technique.presence_confidence >= EVIDENCE_FLOOR:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=PRESENT,
                confidence=technique.presence_confidence,
                source=SOURCE_TECHNIQUE_EVIDENCE,
                reason_code=REASON_PRESENT,
                evidence_refs=tuple(technique.supporting_fact_ids),
                reason=(
                    f"technique evidence at presence_confidence "
                    f"{technique.presence_confidence:.2f} >= floor {EVIDENCE_FLOOR:.2f}"
                ),
            ))
        else:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=NOT_ESTABLISHED,
                confidence=technique.presence_confidence,
                source=SOURCE_TECHNIQUE_EVIDENCE,
                reason_code=REASON_BELOW_FLOOR,
                evidence_refs=tuple(technique.supporting_fact_ids),
                reason=(
                    f"technique evidence below the admissibility floor "
                    f"({technique.presence_confidence:.2f} < {EVIDENCE_FLOOR:.2f}); "
                    "an observation below the floor is not an absence"
                ),
            ))

    # Producer 3 — shadow strategy evidence.
    if concept_registry.SRC_V1_STRATEGY in concept.sources:
        strategy = strategy_by_id.get(concept_id)
        if strategy is None:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=NOT_ESTABLISHED,
                confidence=0.0,
                source=SOURCE_STRATEGY_EVIDENCE,
                reason_code=REASON_SILENT,
                reason="no strategy evidence was produced for this concept",
            ))
        elif strategy.confidence >= EVIDENCE_FLOOR:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=PRESENT,
                confidence=strategy.confidence,
                source=SOURCE_STRATEGY_EVIDENCE,
                reason_code=REASON_PRESENT,
                evidence_refs=tuple(strategy.supporting_fact_ids),
                reason=(
                    f"strategy evidence at confidence {strategy.confidence:.2f} "
                    f">= floor {EVIDENCE_FLOOR:.2f}"
                ),
            ))
        else:
            candidates.append(ConceptEvidence(
                concept_id=concept_id,
                state=NOT_ESTABLISHED,
                confidence=strategy.confidence,
                source=SOURCE_STRATEGY_EVIDENCE,
                reason_code=REASON_BELOW_FLOOR,
                evidence_refs=tuple(strategy.supporting_fact_ids),
                reason=(
                    f"strategy evidence below the admissibility floor "
                    f"({strategy.confidence:.2f} < {EVIDENCE_FLOOR:.2f})"
                ),
            ))

    # No producer at all in the shadow evidence system (legacy-only ids and the
    # documented-only concepts). Silence, never absence.
    if not candidates:
        documented_only = concept_registry.SRC_DOCUMENTED_ONLY in concept.sources
        candidates.append(ConceptEvidence(
            concept_id=concept_id,
            state=NOT_ESTABLISHED,
            confidence=0.0,
            source=SOURCE_NONE,
            reason_code=(
                REASON_DOCUMENTED_ONLY if documented_only else REASON_NO_PRODUCER
            ),
            reason=(
                "declared from documentation only; no runtime producer exists"
                if documented_only
                else "the shadow evidence system produces no evidence for this "
                     "concept (legacy detector taxonomy); silence, not absence"
            ),
        ))

    return tuple(candidates)


def _reduce(candidates: Iterable[ConceptEvidence]) -> ConceptEvidence:
    """Reduce a concept's candidate evidence by state priority (B2 rule)."""
    best: Optional[ConceptEvidence] = None
    for candidate in candidates:
        if best is None:
            best = candidate
            continue
        best_rank = STATE_PRIORITY[best.state]
        rank = STATE_PRIORITY[candidate.state]
        if rank > best_rank:
            best = candidate
        elif rank == best_rank and candidate.confidence > best.confidence:
            best = candidate
    assert best is not None
    return best


def _structural_contradiction(
    concept_id: str, facts_by_type: Dict[str, Tuple[str, ...]]
) -> Optional[ConceptEvidence]:
    """Contradiction from a positively observed structural falsifier."""
    falsifier_facts = STRUCTURAL_FALSIFIERS.get(concept_id)
    if not falsifier_facts:
        return None
    observed = [f for f in falsifier_facts if facts_by_type.get(f)]
    if not observed:
        return None
    refs = tuple(
        fact_id for fact_type in observed for fact_id in facts_by_type[fact_type]
    )
    return ConceptEvidence(
        concept_id=concept_id,
        state=CONTRADICTED,
        confidence=0.0,
        source=SOURCE_STRUCTURAL_FACT,
        reason_code=REASON_STRUCTURAL_FALSIFIER,
        evidence_refs=refs,
        contradiction_source=REASON_STRUCTURAL_FALSIFIER,
        reason=(
            "positively observed structural falsifier: "
            + ", ".join(observed)
        ),
    )


def _mutual_exclusion_contradiction(
    concept_id: str, present_ids: Iterable[str]
) -> Optional[ConceptEvidence]:
    """Contradiction from an explicitly declared mutual exclusion."""
    excluded_by = MUTUAL_EXCLUSIONS.get(concept_id)
    if not excluded_by:
        return None
    present = set(present_ids)
    established = sorted(other for other in excluded_by if other in present)
    if not established:
        return None
    return ConceptEvidence(
        concept_id=concept_id,
        state=CONTRADICTED,
        confidence=0.0,
        source=SOURCE_NONE,
        reason_code=REASON_MUTUAL_EXCLUSION,
        contradiction_source=REASON_MUTUAL_EXCLUSION,
        evidence_refs=tuple(established),
        reason=(
            "explicitly declared mutual exclusion with established concept(s): "
            + ", ".join(established)
        ),
    )


def build_evidence_snapshot(
    facts: Sequence,
    technique_evidence: Sequence,
    strategy_evidence: Sequence,
) -> EvidenceSnapshot:
    """Build the tri-state evidence snapshot for one submission.

    Pure and deterministic: the same inputs always produce the same snapshot.
    Reads concept metadata from the B1 registry and mutual exclusions from the
    existing coherence declaration; it defines no new analysis semantics.
    """
    facts_by_type = _facts_by_type(facts)
    technique_by_id = {t.technique_id: t for t in (technique_evidence or [])}
    strategy_by_id = {s.strategy_id: s for s in (strategy_evidence or [])}

    # Pass 1 — producer evidence, reduced by state priority.
    reduced = [
        _reduce(_producer_evidence(concept, facts_by_type, technique_by_id, strategy_by_id))
        for concept in concept_registry.all_concepts()
    ]

    # Pass 2 — contradictions. CONTRADICTED outranks everything else, and is
    # only ever raised from a positive contradiction source.
    present_ids = {item.concept_id for item in reduced if item.state == PRESENT}
    final: List[ConceptEvidence] = []
    for item in reduced:
        contradiction = _structural_contradiction(item.concept_id, facts_by_type)
        if contradiction is None:
            contradiction = _mutual_exclusion_contradiction(
                item.concept_id, present_ids
            )
        if contradiction is not None:
            final.append(ConceptEvidence(
                concept_id=item.concept_id,
                state=CONTRADICTED,
                confidence=item.confidence,
                source=contradiction.source,
                reason_code=contradiction.reason_code,
                evidence_refs=contradiction.evidence_refs,
                contradiction_source=contradiction.contradiction_source,
                reason=contradiction.reason,
            ))
        else:
            final.append(item)

    # Pass 3 — aliasing projection for legacy ids (information only; it is NOT
    # this concept's own state).
    state_by_id = {item.concept_id: item.state for item in final}
    with_images: List[ConceptEvidence] = []
    for item in final:
        concept = concept_registry.get_concept(item.concept_id)
        image = concept.v1_image
        image_state = None
        if image and image != item.concept_id:
            image_state = state_by_id.get(image)
        with_images.append(ConceptEvidence(
            concept_id=item.concept_id,
            state=item.state,
            confidence=item.confidence,
            source=item.source,
            reason_code=item.reason_code,
            evidence_refs=item.evidence_refs,
            contradiction_source=item.contradiction_source,
            image_state=image_state,
            reason=item.reason,
        ))

    return EvidenceSnapshot(evidence=tuple(with_images))


__all__ = [
    # states
    "PRESENT", "NOT_ESTABLISHED", "CONTRADICTED",
    "EVIDENCE_STATES", "STATE_PRIORITY", "EVIDENCE_FLOOR",
    # reason codes
    "REASON_PRESENT", "REASON_SILENT", "REASON_BELOW_FLOOR",
    "REASON_NO_PRODUCER", "REASON_DOCUMENTED_ONLY",
    "REASON_STRUCTURAL_FALSIFIER", "REASON_MUTUAL_EXCLUSION",
    # producers
    "SOURCE_STRUCTURAL_FACT", "SOURCE_TECHNIQUE_EVIDENCE",
    "SOURCE_STRATEGY_EVIDENCE", "SOURCE_NONE",
    # contradictions
    "STRUCTURAL_FALSIFIERS", "DEFERRED_FALSIFIERS", "MUTUAL_EXCLUSIONS",
    "LEGACY_EXCLUSION_PREFIX", "LEGACY_EXCLUSION_NOTES", "PARTIAL_FALSIFIER_NOTES",
    "legacy_exclusion_ids", "deferred_falsifier_ids", "structural_falsifier_ids",
    "concepts_declaring_a_falsifier", "validate_falsifier_ledger",
    # records
    "ConceptEvidence", "EvidenceSnapshot", "build_evidence_snapshot",
]
