"""B10 — strategy-specificity contract (declaration + verdict, never an approval).

One reusable, concept-agnostic gate that every future TECHNIQUE -> STRATEGY
promotion must pass. It answers a single question:

    Does this concept have evidence specific enough to justify an *algorithmic
    conclusion*, rather than merely identifying a tool, an implementation
    pattern or a family topic?

Why this exists
---------------

Two decisions of the same shape were taken ad hoc and both had to be withdrawn
after the fact: a mapping-shaped technique whose evidence deliberately covers a
static reference table as well as a dynamic lookup, and a pair of records where
the strong structural signature still described a cache and an adjacency store.
The failure is always the same — the concept is a *tool* or a *family topic*
while the conclusion it would produce claims an *approach*. This module makes
the evidence that decides such a case explicit, repeatable and reviewable.

The contract is a **metadata and evidence layer**. It promotes nothing, edits no
registry entry, reads no Ground Truth, consults no coverage/authority layer, and
writes no file. It is deliberately unreachable from every production path
(``pathforge/api``, ``pathforge/services``, ``src``, ``pathforge/ast_engine``)
and the guard test that enforces that lives with the other registry guards.

Verdict space
-------------

``NOT_EVALUABLE``
    A precondition (C0) does not hold — there is nothing to evaluate.
``BLOCKED``
    At least one clause failed; ``failing_clauses`` names them.
``READY_FOR_REVIEW``
    Every clause passed *and* the C3 review is complete (a named reviewer and
    date against every flagged record).

There is deliberately **no** ``PROMOTE`` verdict. The strongest state this
module can produce is "ready for a human decision": conclusion eligibility is
never conferred by a program, and an unreviewed record cannot be waived by any
other clause passing.

Clauses
-------

====  ==========================================================================
C0    preconditions: registered, TECHNIQUE class, real shadow producer,
      resolvable legacy namesake, present in a corpus Ground-Truth required set
C1    identity: an approach-shaped algorithmic meaning, not a mechanism
C2    discriminator: >=1 AVAILABLE discriminator with measured separation
C3    precision: native + benchmark measured, every flagged record reviewed
C4    negative controls: four classes present, incidental-usage control clear
C5    Ground-Truth compatibility: identification != conclusion, no relabel
C6    B4 safety: no redundant or duplicate conclusion path, no undeclared tie
C7    authority/product: B3 -> B6 path recorded; eligibility != authority
C8    parity: before/after classified; fewer P4 is never sufficient
C9    regression: detectors, controls, B2-B6 and the legacy path unchanged
====  ==========================================================================

Nothing in this module names a concept, a family or a detector. Candidate
evidence is supplied by the caller (see the B10 precision harness); the module
supplies only the rules, the source validation and the verdict.
"""

from dataclasses import dataclass, fields
from typing import Dict, Optional, Tuple

from pathforge.ast_analysis import concepts as concept_registry
from pathforge.ast_analysis.shadow import relations as shadow_relations

CONTRACT_VERSION = "1.0.0"

# ============================================================================
# Verdicts — there is no PROMOTE
# ============================================================================

NOT_EVALUABLE = "NOT_EVALUABLE"
BLOCKED = "BLOCKED"
READY_FOR_REVIEW = "READY_FOR_REVIEW"

VERDICTS: Tuple[str, ...] = (NOT_EVALUABLE, BLOCKED, READY_FOR_REVIEW)

# ============================================================================
# Clause ids
# ============================================================================

C0 = "C0_PRECONDITIONS"
C1 = "C1_IDENTITY"
C2 = "C2_DISCRIMINATOR"
C3 = "C3_PRECISION"
C4 = "C4_NEGATIVE_CONTROLS"
C5 = "C5_GT_COMPATIBILITY"
C6 = "C6_B4_SAFETY"
C7 = "C7_AUTHORITY"
C8 = "C8_PARITY"
C9 = "C9_REGRESSION"

CLAUSE_IDS: Tuple[str, ...] = (C0, C1, C2, C3, C4, C5, C6, C7, C8, C9)

# ============================================================================
# Discriminator availability
# ============================================================================

AVAILABLE = "AVAILABLE"
NEEDS_EXTRACTION = "NEEDS_EXTRACTION"
NOT_AVAILABLE = "NOT_AVAILABLE"

DISCRIMINATOR_AVAILABILITY: Tuple[str, ...] = (
    AVAILABLE, NEEDS_EXTRACTION, NOT_AVAILABLE,
)

# ============================================================================
# Justification bases — what may and may not justify a promotion
# ============================================================================

#: The only admissible basis: structural evidence specific enough to separate
#: use-as-approach from use-as-tool.
BASIS_STRUCTURAL = "structural_evidence"

#: Inadmissible bases. Recorded as constants so a caller must name them
#: deliberately, and so the clauses that reject them are testable.
BASIS_B3_CONFIRMATION = "b3_would_otherwise_not_confirm"
BASIS_PARITY = "parity_improvement"
BASIS_CONSEQUENCE = "elo_gap_recommendation_effect"

# ============================================================================
# Review classifications (C3)
# ============================================================================

LEGITIMATE_IMPROVEMENT = "LEGITIMATE_IMPROVEMENT"
FALSE_CONFIRMATION = "FALSE_CONFIRMATION"
REPRESENTATION_DIFFERENCE = "REPRESENTATION_DIFFERENCE"
UNRESOLVED = "UNRESOLVED"

REVIEW_CLASSIFICATIONS: Tuple[str, ...] = (
    LEGITIMATE_IMPROVEMENT, FALSE_CONFIRMATION, REPRESENTATION_DIFFERENCE,
    UNRESOLVED,
)

#: Classifications that block C3 outright.
BLOCKING_CLASSIFICATIONS: Tuple[str, ...] = (FALSE_CONFIRMATION, UNRESOLVED)

# ============================================================================
# Parity delta classifications (C8)
# ============================================================================

JUSTIFIED_CONFIRMATION = "JUSTIFIED_CONFIRMATION"
UNJUSTIFIED_CONFIRMATION = "UNJUSTIFIED_CONFIRMATION"
NEW_DISAGREEMENT = "NEW_DISAGREEMENT"
AUTHORITY_BLOCKED_CONFIRMATION = "AUTHORITY_BLOCKED_CONFIRMATION"
PARITY_REPRESENTATION_DIFFERENCE = "REPRESENTATION_DIFFERENCE"

PARITY_DELTA_CLASSIFICATIONS: Tuple[str, ...] = (
    JUSTIFIED_CONFIRMATION, UNJUSTIFIED_CONFIRMATION, NEW_DISAGREEMENT,
    AUTHORITY_BLOCKED_CONFIRMATION, PARITY_REPRESENTATION_DIFFERENCE,
)

# ============================================================================
# Source validation — reuses the registry's own discovery, invents no facts
# ============================================================================

#: A discriminator may cite only things the analysis layer actually produces.
SOURCE_FACT = "fact"
SOURCE_RELATION = "relation"
SOURCE_DERIVED = "derived"


def valid_fact_types() -> frozenset:
    """Every structural fact type, read from the registry.

    The registry already registers each emitted ``fact_type`` with the
    ``structural_fact`` source (B1's completeness invariant), so it *is* the
    discovery mechanism — no parallel fact list is created here.
    """
    return frozenset(
        concept.concept_id
        for concept in concept_registry.concepts_by_source(
            concept_registry.SRC_STRUCTURAL_FACT
        )
    )


def valid_relation_names() -> frozenset:
    """Every relation exposed by the shared relational layer."""
    return frozenset(f.name for f in fields(shadow_relations.SubmissionRelations))


def is_valid_discriminator_source(source: str) -> bool:
    """Whether a discriminator source names something that exists.

    ``derived:<slug>`` is accepted because a discriminator may legitimately be
    a rule composed from facts and relations beyond any single one; such a rule
    cannot be verified mechanically, so it carries no guarantee and C2 still
    requires measured separation.
    """
    if not isinstance(source, str) or ":" not in source:
        return False
    kind, _, identifier = source.partition(":")
    if not identifier:
        return False
    if kind == SOURCE_FACT:
        return identifier in valid_fact_types()
    if kind == SOURCE_RELATION:
        return identifier in valid_relation_names()
    return kind == SOURCE_DERIVED


# ============================================================================
# Discriminator
# ============================================================================

@dataclass(frozen=True)
class Separation:
    """Measured separation of approach-use from tool-use."""

    positive_records: Tuple[str, ...] = ()
    negative_records: Tuple[str, ...] = ()
    #: Records where the positive form holds but the concept is used as a tool.
    #: Any entry blocks C2 — this is the db-33 class of error.
    misclassified: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "positive_records": list(self.positive_records),
            "negative_records": list(self.negative_records),
            "misclassified": list(self.misclassified),
        }


@dataclass(frozen=True)
class Discriminator:
    """One candidate structural discriminator.

    Shape is validated on construction; *adequacy* is decided by C2.
    """

    name: str
    source: str
    positive_form: str
    negative_form: str
    availability: str
    separates: Optional[Separation] = None
    evidence_ref: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("discriminator name must be non-empty")
        if not is_valid_discriminator_source(self.source):
            raise ValueError(
                f"{self.name}: unknown discriminator source {self.source!r} "
                "(expected fact:<structural fact type>, relation:<relation>, "
                "or derived:<rule>)"
            )
        if self.availability not in DISCRIMINATOR_AVAILABILITY:
            raise ValueError(
                f"{self.name}: unknown availability {self.availability!r}"
            )
        if not self.positive_form.strip() or not self.negative_form.strip():
            raise ValueError(
                f"{self.name}: positive_form and negative_form are both required"
            )
        if self.availability == AVAILABLE and self.separates is None:
            raise ValueError(
                f"{self.name}: an AVAILABLE discriminator must carry its "
                "measured separation"
            )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": self.source,
            "positive_form": self.positive_form,
            "negative_form": self.negative_form,
            "availability": self.availability,
            "separates": self.separates.to_dict() if self.separates else None,
            "evidence_ref": self.evidence_ref,
            "note": self.note,
        }


# ============================================================================
# Negative controls
# ============================================================================

@dataclass(frozen=True)
class Control:
    """One control class: named cases plus the measured outcome."""

    name: str
    cases: Tuple[str, ...] = ()
    #: True when the concept fires on this control. For the incidental-usage
    #: control that is a failure, not a success.
    confirms: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cases": list(self.cases),
            "confirms": self.confirms,
        }


@dataclass(frozen=True)
class NegativeControls:
    """The four required control classes (B10 clause C4)."""

    positive: Optional[Control] = None
    negative: Optional[Control] = None
    adversarial: Optional[Control] = None
    #: Mandatory: an example where the tool is present but not the approach.
    incidental_usage: Optional[Control] = None

    def all_present(self) -> bool:
        return all(
            control is not None and control.cases
            for control in (
                self.positive, self.negative, self.adversarial,
                self.incidental_usage,
            )
        )

    def to_dict(self) -> dict:
        return {
            "positive": self.positive.to_dict() if self.positive else None,
            "negative": self.negative.to_dict() if self.negative else None,
            "adversarial": self.adversarial.to_dict() if self.adversarial else None,
            "incidental_usage": (
                self.incidental_usage.to_dict() if self.incidental_usage else None
            ),
        }


# ============================================================================
# Precision evidence
# ============================================================================

@dataclass(frozen=True)
class CorpusMeasurement:
    """One corpus's shadow-vs-namesake breadth comparison.

    Record ids are mandatory: an aggregate-only measurement is rejected, so no
    review can be decided from counts alone.
    """

    corpus: str
    both_ids: Tuple[str, ...] = ()
    shadow_only_ids: Tuple[str, ...] = ()
    legacy_only_ids: Tuple[str, ...] = ()
    neither_count: int = 0
    error_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.corpus.strip():
            raise ValueError("corpus name must be non-empty")
        for label, ids in (
            ("both_ids", self.both_ids),
            ("shadow_only_ids", self.shadow_only_ids),
            ("legacy_only_ids", self.legacy_only_ids),
        ):
            if len(set(ids)) != len(ids):
                raise ValueError(f"{self.corpus}: duplicate ids in {label}")

    @property
    def both(self) -> int:
        return len(self.both_ids)

    @property
    def shadow_only(self) -> int:
        return len(self.shadow_only_ids)

    @property
    def legacy_only(self) -> int:
        return len(self.legacy_only_ids)

    @property
    def neither(self) -> int:
        return self.neither_count

    def to_dict(self) -> dict:
        return {
            "corpus": self.corpus,
            "counts": {
                "both": self.both, "shadow_only": self.shadow_only,
                "legacy_only": self.legacy_only, "neither": self.neither,
            },
            "both_ids": list(self.both_ids),
            "shadow_only_ids": list(self.shadow_only_ids),
            "legacy_only_ids": list(self.legacy_only_ids),
            "error_ids": list(self.error_ids),
        }


@dataclass(frozen=True)
class ReviewEntry:
    """One human review of one flagged record. An empty reviewer is not a sign-off."""

    record_id: str
    classification: str = ""
    reviewer: str = ""
    date: str = ""
    note: str = ""

    def is_complete(self) -> bool:
        return bool(
            self.classification and self.reviewer.strip() and self.date.strip()
        )

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "classification": self.classification,
            "reviewer": self.reviewer,
            "date": self.date,
            "note": self.note,
        }


@dataclass(frozen=True)
class PrecisionEvidence:
    """Per-corpus breadth measurements plus the human review of flagged records."""

    measurements: Tuple[CorpusMeasurement, ...] = ()
    reviews: Tuple[ReviewEntry, ...] = ()

    def corpora(self) -> Tuple[str, ...]:
        return tuple(m.corpus for m in self.measurements)

    def flagged_ids(self) -> Tuple[str, ...]:
        flagged = []
        for measurement in self.measurements:
            for record_id in measurement.shadow_only_ids:
                if record_id not in flagged:
                    flagged.append(record_id)
        return tuple(flagged)

    def review_for(self, record_id: str) -> Optional[ReviewEntry]:
        for entry in self.reviews:
            if entry.record_id == record_id:
                return entry
        return None

    def to_dict(self) -> dict:
        return {
            "measurements": [m.to_dict() for m in self.measurements],
            "flagged_ids": list(self.flagged_ids()),
            "reviews": [r.to_dict() for r in self.reviews],
        }


# ============================================================================
# The remaining clause evidence
# ============================================================================

@dataclass(frozen=True)
class GTCompatibility:
    """C5: identification is not a conclusion, and nothing is relabelled."""

    required_concepts: Tuple[str, ...]
    family_role: str
    tier: str
    one_of_memberships: Tuple[str, ...] = ()
    identification_preserved: bool = True
    gt_relabel_required: bool = False
    family_semantics_preserved: bool = True
    #: A family whose identity concept becomes conclusion-eligible changes what
    #: its CONFIRMED state means. That shift is not itself a violation — an
    #: undeclared one is.
    semantic_change_declared: bool = False
    justification_basis: str = BASIS_STRUCTURAL


@dataclass(frozen=True)
class PrimaryStrategySafety:
    """C6: no redundant or duplicate conclusion path."""

    #: Strategies that already produce this conclusion from the technique.
    consuming_strategies: Tuple[str, ...] = ()
    #: Other concepts with the same algorithmic meaning.
    duplicate_meaning_of: Tuple[str, ...] = ()
    #: Familiy conclusions that would tie at rank 3.
    rank3_conflicts: Tuple[str, ...] = ()
    declared_ambiguity: bool = False


@dataclass(frozen=True)
class AuthorityImpact:
    """C7: the recorded B3 -> B6 path and the authority standing."""

    b3_coverage: str = ""
    b4_primary: Optional[str] = None
    b5_authoritative: bool = False
    b6_eligible: bool = False
    authority_tier: str = ""
    path_evaluated: bool = False
    justification_basis: str = BASIS_STRUCTURAL


@dataclass(frozen=True)
class ParityDelta:
    """One classified before/after parity movement."""

    category: str
    count: int
    classification: str
    evidence_ref: str = ""
    #: True when the delta is a projection rather than a measured outcome of an
    #: applied change (nothing is applied while the contract blocks the change).
    projected: bool = False

    def __post_init__(self) -> None:
        if self.classification not in PARITY_DELTA_CLASSIFICATIONS:
            raise ValueError(
                f"unknown parity delta classification {self.classification!r}"
            )


@dataclass(frozen=True)
class ParityImpact:
    """C8: parity is evidence, never the objective."""

    baseline_ref: str = ""
    deltas: Tuple[ParityDelta, ...] = ()
    justification_basis: str = BASIS_STRUCTURAL


@dataclass(frozen=True)
class RegressionEvidence:
    """C9: what must not move."""

    detector_unchanged: bool = True
    negative_controls_unchanged: bool = True
    b2_unchanged: bool = True
    b3_unchanged: bool = True
    b4_unchanged: bool = True
    b5_unchanged: bool = True
    b6_unchanged: bool = True
    legacy_unchanged: bool = True
    unrelated_strategies_unchanged: bool = True

    def all_hold(self) -> bool:
        return all(
            getattr(self, f.name) for f in fields(self)
        )

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


# ============================================================================
# Candidate + verdict
# ============================================================================

@dataclass(frozen=True)
class Candidate:
    """Everything the contract needs about one promotion candidate."""

    concept_id: str
    identity_meaning: str
    #: Declared judgement: does the meaning describe a mechanism/tool rather
    #: than an approach?
    identity_is_mechanism_only: bool
    discriminators: Tuple[Discriminator, ...] = ()
    precision: PrecisionEvidence = PrecisionEvidence()
    negative_controls: NegativeControls = NegativeControls()
    gt: Optional[GTCompatibility] = None
    primary_strategy: PrimaryStrategySafety = PrimaryStrategySafety()
    authority: AuthorityImpact = AuthorityImpact()
    parity: ParityImpact = ParityImpact()
    regression: RegressionEvidence = RegressionEvidence()
    #: C0 preconditions, measured by the harness.
    registered: bool = False
    concept_class: str = ""
    has_shadow_producer: bool = False
    namesakes: Tuple[str, ...] = ()
    appears_in_corpus_gt: bool = False


@dataclass(frozen=True)
class ClauseResult:
    """One clause's outcome with a machine-readable detail."""

    clause: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"clause": self.clause, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class ContractVerdict:
    """The contract's outcome. Never an authorization."""

    concept_id: str
    verdict: str
    clauses: Tuple[ClauseResult, ...]
    failing_clauses: Tuple[str, ...]
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "verdict": self.verdict,
            "failing_clauses": list(self.failing_clauses),
            "contract_version": self.contract_version,
            "clauses": [c.to_dict() for c in self.clauses],
        }


# ============================================================================
# Registry access — the only place this module touches the registry
# ============================================================================

def concept_metadata(concept_id: str) -> Dict[str, object]:
    """Registry metadata for one concept (empty when unregistered).

    Exposed so a caller (the B10 harness) can report concept metadata without
    importing the registry itself, keeping this module the single registry
    consumer.
    """
    if not concept_registry.has_concept(concept_id):
        return {}
    concept = concept_registry.get_concept(concept_id)
    return {
        "concept_id": concept.concept_id,
        "class": concept.concept_class,
        "tier": concept.tier,
        "specificity_rank": concept.specificity_rank,
        "conclusion_eligible": concept.conclusion_eligible,
        "family_role": concept.family_role,
        "sources": list(concept.sources),
        "v1_image": concept.v1_image,
        "falsifier": concept.falsifier,
    }


def has_shadow_producer(concept_id: str) -> bool:
    """Whether a shadow producer (technique/strategy/fact) can raise this concept."""
    if not concept_registry.has_concept(concept_id):
        return False
    sources = concept_registry.get_concept(concept_id).sources
    return any(
        source in sources
        for source in (
            concept_registry.SRC_V1_TECHNIQUE,
            concept_registry.SRC_V1_STRATEGY,
            concept_registry.SRC_STRUCTURAL_FACT,
        )
    )


def identification_without_conclusion(concept_id: str) -> bool:
    """Whether a concept may identify a family while never concluding one.

    This is a legal, expected state (identification and conclusion are separate
    permissions), not a defect, and the contract must never report it as one.
    """
    if not concept_registry.has_concept(concept_id):
        return False
    concept = concept_registry.get_concept(concept_id)
    return (
        concept.family_role == concept_registry.IDENTIFYING
        and not concept.conclusion_eligible
    )


def registry_invariants() -> Dict[str, int]:
    """The registry counts the contract must never move."""
    return {
        "total": len(concept_registry.all_concepts()),
        "conclusion_eligible": len(concept_registry.conclusion_eligible_ids()),
    }


#: Conclusion eligibility never confers Ground-Truth authority. Stated as a
#: value so C7's cross-clause rule is explicit and testable.
AUTHORITY_CONFERRED_BY_ELIGIBILITY = False


# ============================================================================
# Clause evaluation
# ============================================================================

def _c0(candidate: Candidate) -> ClauseResult:
    missing = []
    if not candidate.registered:
        missing.append("unregistered concept")
    if candidate.concept_class != concept_registry.TECHNIQUE:
        missing.append(f"class is {candidate.concept_class or 'unknown'}, not TECHNIQUE")
    if not candidate.has_shadow_producer:
        missing.append("no shadow producer")
    if not candidate.namesakes:
        missing.append("no resolvable legacy namesake")
    if not candidate.appears_in_corpus_gt:
        missing.append("absent from every corpus Ground-Truth required set")
    if missing:
        return ClauseResult(C0, False, "; ".join(missing))
    return ClauseResult(C0, True, "preconditions hold")


def _c1(candidate: Candidate) -> ClauseResult:
    if not candidate.identity_meaning.strip():
        return ClauseResult(C1, False, "no algorithmic meaning stated")
    if candidate.identity_meaning.strip() == candidate.concept_id:
        return ClauseResult(C1, False, "the meaning restates the concept id")
    if candidate.identity_is_mechanism_only:
        return ClauseResult(
            C1, False,
            "the stated meaning describes a mechanism/tool rather than an approach",
        )
    return ClauseResult(C1, True, "approach-shaped meaning stated")


def _c2(candidate: Candidate) -> ClauseResult:
    if not candidate.discriminators:
        return ClauseResult(C2, False, "no discriminator supplied")
    best = []
    for discriminator in candidate.discriminators:
        if discriminator.availability != AVAILABLE:
            best.append(f"{discriminator.name}={discriminator.availability}")
            continue
        separation = discriminator.separates
        assert separation is not None  # constructor guarantees this
        if not separation.positive_records or not separation.negative_records:
            best.append(f"{discriminator.name}=unmeasured")
            continue
        if separation.misclassified:
            best.append(
                f"{discriminator.name}=misclassifies "
                f"{len(separation.misclassified)} tool-use record(s): "
                + ", ".join(separation.misclassified[:5])
            )
            continue
        return ClauseResult(
            C2, True,
            f"{discriminator.name} separates approach-use from tool-use "
            f"({len(separation.positive_records)} positive, "
            f"{len(separation.negative_records)} negative)",
        )
    return ClauseResult(
        C2, False,
        "no AVAILABLE discriminator with measured separation: " + "; ".join(best),
    )


def _c3(candidate: Candidate) -> ClauseResult:
    corpora = candidate.precision.corpora()
    missing_corpora = [
        name for name in ("native", "benchmark")
        if not any(name in corpus.lower() for corpus in corpora)
    ]
    if missing_corpora or not corpora:
        return ClauseResult(
            C3, False,
            "precision measurement missing corpus: "
            + ", ".join(missing_corpora or ["none measured"]),
        )

    problem = []
    flagged = candidate.precision.flagged_ids()
    for record_id in flagged:
        entry = candidate.precision.review_for(record_id)
        if entry is None:
            problem.append(f"{record_id}: no review entry")
            continue
        if entry.classification in BLOCKING_CLASSIFICATIONS:
            problem.append(f"{record_id}: {entry.classification}")
            continue
        if not entry.is_complete():
            problem.append(f"{record_id}: unsigned (reviewer/date required)")
    if problem:
        shown = problem[:8]
        return ClauseResult(
            C3, False,
            f"{len(problem)} of {len(flagged)} flagged record(s) unresolved "
            f"({', '.join(problem[:3])}{', ...' if len(problem) > 3 else ''}); "
            "first entries: " + "; ".join(shown),
        )
    if not flagged:
        return ClauseResult(
            C3, True, "no flagged records; both corpora measured",
        )
    return ClauseResult(
        C3, True, f"all {len(flagged)} flagged record(s) reviewed and signed off",
    )


def _c4(candidate: Candidate) -> ClauseResult:
    controls = candidate.negative_controls
    if not controls.all_present():
        absent = [
            name for name, control in (
                ("positive", controls.positive),
                ("negative", controls.negative),
                ("adversarial", controls.adversarial),
                ("incidental_usage", controls.incidental_usage),
            )
            if control is None or not control.cases
        ]
        return ClauseResult(
            C4, False, "missing control class(es): " + ", ".join(absent),
        )
    assert controls.incidental_usage is not None
    if controls.incidental_usage.confirms:
        return ClauseResult(
            C4, False,
            "the incidental-usage control confirms (the concept fires where it "
            "is demonstrably a tool, not the approach): "
            + ", ".join(controls.incidental_usage.cases),
        )
    return ClauseResult(C4, True, "all four control classes present and clear")


def _c5(candidate: Candidate) -> ClauseResult:
    gt = candidate.gt
    if gt is None:
        return ClauseResult(C5, False, "no Ground-Truth inspection recorded")
    problems = []
    if not gt.required_concepts:
        problems.append("family required set not inspected")
    if not gt.identification_preserved:
        problems.append("identification no longer distinct from conclusion")
    if gt.gt_relabel_required:
        problems.append("Ground-Truth relabelling required")
    if not gt.family_semantics_preserved and not gt.semantic_change_declared:
        problems.append(
            "the family's meaning would change (identity -> conclusion) without "
            "being declared"
        )
    if gt.justification_basis == BASIS_B3_CONFIRMATION:
        problems.append(
            "justified by B3 otherwise failing to confirm, which is not a reason"
        )
    if problems:
        return ClauseResult(C5, False, "; ".join(problems))
    shift = "" if gt.family_semantics_preserved else (
        "; identity -> conclusion shift declared"
    )
    one_of = (
        f", one-of {list(gt.one_of_memberships)}" if gt.one_of_memberships else ""
    )
    return ClauseResult(
        C5, True,
        f"family role {gt.family_role}/{gt.tier}, required "
        f"{list(gt.required_concepts)}, no relabel required{one_of}{shift}",
    )


def _c6(candidate: Candidate) -> ClauseResult:
    safety = candidate.primary_strategy
    problems = []
    if safety.consuming_strategies:
        problems.append(
            "redundant: already concluded by "
            + ", ".join(safety.consuming_strategies)
        )
    if safety.duplicate_meaning_of:
        problems.append(
            "duplicate meaning of " + ", ".join(safety.duplicate_meaning_of)
        )
    if safety.rank3_conflicts and not safety.declared_ambiguity:
        problems.append(
            "undeclared rank-3 ambiguity with "
            + ", ".join(safety.rank3_conflicts)
        )
    if problems:
        return ClauseResult(C6, False, "; ".join(problems))
    return ClauseResult(C6, True, "no redundant, duplicate or undeclared path")


def _c7(candidate: Candidate) -> ClauseResult:
    if not candidate.authority.path_evaluated:
        return ClauseResult(C7, False, "B3 -> B4 -> B5 -> B6 path not evaluated")
    if not candidate.authority.authority_tier:
        return ClauseResult(C7, False, "authority tier not recorded")
    if candidate.authority.justification_basis in (BASIS_CONSEQUENCE, BASIS_PARITY):
        return ClauseResult(
            C7, False,
            f"justified by {candidate.authority.justification_basis}, which is "
            "not admissible",
        )
    return ClauseResult(
        C7, True,
        f"path recorded (coverage {candidate.authority.b3_coverage}, primary "
        f"{candidate.authority.b4_primary}, authoritative "
        f"{candidate.authority.b5_authoritative}, B6 eligible "
        f"{candidate.authority.b6_eligible}, tier "
        f"{candidate.authority.authority_tier}); eligibility does not confer "
        "authority",
    )


def _c8(candidate: Candidate) -> ClauseResult:
    impact = candidate.parity
    if not impact.baseline_ref.strip():
        return ClauseResult(C8, False, "no before/baseline parity reference")
    if impact.justification_basis == BASIS_PARITY:
        return ClauseResult(
            C8, False, "justified by parity improvement, which is not admissible",
        )
    unclassified = [
        f"{d.category}={d.classification}"
        for d in impact.deltas
        if d.classification not in PARITY_DELTA_CLASSIFICATIONS
    ]
    if unclassified:
        return ClauseResult(C8, False, "unclassified delta(s): " + ", ".join(unclassified))
    if not impact.deltas:
        return ClauseResult(
            C8, True, "baseline recorded; no parity movement while blocked",
        )
    summary = ", ".join(
        f"{d.category}:{d.classification}"
        + ("(projected)" if d.projected else "")
        for d in impact.deltas
    )
    return ClauseResult(C8, True, f"deltas classified: {summary}")


def _c9(candidate: Candidate) -> ClauseResult:
    if not candidate.regression.all_hold():
        broken = [
            name for name, value in candidate.regression.to_dict().items()
            if not value
        ]
        return ClauseResult(C9, False, "regression invariants broken: " + ", ".join(broken))
    return ClauseResult(C9, True, "all regression invariants hold")


_CLAUSE_FUNCTIONS = (
    _c1, _c2, _c3, _c4, _c5, _c6, _c7, _c8, _c9,
)


def evaluate(candidate: Candidate) -> ContractVerdict:
    """Evaluate every clause and return the verdict.

    The contract can never return a promotion: ``READY_FOR_REVIEW`` means the
    evidence is complete and a human decision is still outstanding.
    """
    c0 = _c0(candidate)
    if not c0.passed:
        return ContractVerdict(
            concept_id=candidate.concept_id,
            verdict=NOT_EVALUABLE,
            clauses=(c0,),
            failing_clauses=(C0,),
        )

    clauses = tuple(function(candidate) for function in _CLAUSE_FUNCTIONS)
    failing = tuple(result.clause for result in clauses if not result.passed)
    verdict = BLOCKED if failing else READY_FOR_REVIEW
    return ContractVerdict(
        concept_id=candidate.concept_id,
        verdict=verdict,
        clauses=(c0,) + clauses,
        failing_clauses=failing,
    )


__all__ = [
    # version + verdicts
    "CONTRACT_VERSION", "NOT_EVALUABLE", "BLOCKED", "READY_FOR_REVIEW",
    "VERDICTS",
    # clauses
    "C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "CLAUSE_IDS",
    # discriminator
    "AVAILABLE", "NEEDS_EXTRACTION", "NOT_AVAILABLE",
    "DISCRIMINATOR_AVAILABILITY",
    "Discriminator", "Separation",
    "SOURCE_FACT", "SOURCE_RELATION", "SOURCE_DERIVED",
    "valid_fact_types", "valid_relation_names", "is_valid_discriminator_source",
    # bases
    "BASIS_STRUCTURAL", "BASIS_B3_CONFIRMATION", "BASIS_PARITY",
    "BASIS_CONSEQUENCE",
    # reviews + parity classifications
    "LEGITIMATE_IMPROVEMENT", "FALSE_CONFIRMATION", "REPRESENTATION_DIFFERENCE",
    "UNRESOLVED", "REVIEW_CLASSIFICATIONS", "BLOCKING_CLASSIFICATIONS",
    "JUSTIFIED_CONFIRMATION", "UNJUSTIFIED_CONFIRMATION", "NEW_DISAGREEMENT",
    "AUTHORITY_BLOCKED_CONFIRMATION", "PARITY_REPRESENTATION_DIFFERENCE",
    "PARITY_DELTA_CLASSIFICATIONS",
    # evidence records
    "Control", "NegativeControls", "CorpusMeasurement", "ReviewEntry",
    "PrecisionEvidence", "GTCompatibility", "PrimaryStrategySafety",
    "AuthorityImpact", "ParityDelta", "ParityImpact", "RegressionEvidence",
    "Candidate", "ClauseResult", "ContractVerdict",
    # registry access + guards
    "concept_metadata", "has_shadow_producer", "identification_without_conclusion",
    "registry_invariants", "AUTHORITY_CONFERRED_BY_ELIGIBILITY",
    "evaluate",
]
