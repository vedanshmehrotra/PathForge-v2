"""B11 — lookup-strategy specificity (key provenance).

This module answers exactly one question about *already-detected* mapping-lookup
evidence:

    Is the evidence specific enough to support an **algorithmic strategy**
    conclusion, or does the mapping merely act as a tool — a static reference
    table, or a store keyed by an externally supplied parameter?

It is a specificity layer, not a detector
-----------------------------------------

Nothing here changes what the analysis layer detects. ``hash_lookup`` (T13)
deliberately keeps its over-covering evidence: a gated read of a static
reference table and a genuine incremental lookup share the same fact shape, so
a detector-level rule cannot separate them without deleting a pinned positive.
The separation belongs at the *strategy* level, which is where this module
lives.

This module therefore:

- consumes only public artifacts — the cited ``mapping_construction`` fact plus
  the shared relations bundle (``lookup_key_origins``, ``updated_in_loop``,
  ``collection_ops``, ``self_referential_updates``);
- never mutates a fact, a relation, a snapshot or a registry entry;
- writes no file, reads no Ground Truth, and consults no coverage/authority
  layer;
- promotes nothing. ``STRATEGY_ELIGIBLE`` is a specificity verdict, never an
  authorization, and eligibility never confers authority;
- names structural conditions only — never an algorithm, never a problem.

Rules
-----

Both rules are **suppression-only**: they can turn ``STRATEGY_ELIGIBLE`` into
``NOT_ESTABLISHED``, and can never do the reverse. An unknown or missing
mapping falls to ``NOT_ESTABLISHED`` for want of a citation, so nothing is
established by absence of evidence.

R1 — static reference table
    The cited mapping is constructed as a dict literal and carries no
    indexed-write/mutation evidence. Roman-to-Integer (db-33) is the canonical
    shape: ``hashm = {'I': 1, ...}`` is consulted for the whole run and never
    built up, so it is a reference table rather than a lookup algorithm.

R2 — parameter-keyed mapping
    Every lookup key origin on the cited mapping is ``parameter`` and the
    mapping is not updated in a loop. A store whose only keys are caller
    supplied values is a cache/memo keyed from outside the algorithm, not a
    lookup structure the algorithm builds.

Anything else — a mapping constructed empty and written inside the scan, or one
consulted with computed/element/iteration keys — stays ``STRATEGY_ELIGIBLE``.
"""

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

SPECIFICITY_VERSION = "1.0.0"

# ============================================================================
# States — an established/not-established specificity verdict
# ============================================================================

STRATEGY_ELIGIBLE = "STRATEGY_ELIGIBLE"
NOT_ESTABLISHED = "NOT_ESTABLISHED"

SPECIFICITY_STATES: Tuple[str, ...] = (STRATEGY_ELIGIBLE, NOT_ESTABLISHED)

# ============================================================================
# Reason codes (machine-readable, for measurement and audit)
# ============================================================================

#: The mapping is built and probed by the scan: specific enough to evaluate.
REASON_ALGORITHMIC_LOOKUP = "algorithmic_lookup"

#: R1 — an immutable dict literal, i.e. a reference table.
REASON_STATIC_REFERENCE_TABLE = "static_reference_table"

#: R2 — every lookup key is a function parameter and the mapping never changes.
REASON_PARAMETER_KEYED_MAPPING = "parameter_keyed_mapping"

#: The evidence cited no mapping this module can inspect.
REASON_NO_CITED_MAPPING = "no_cited_mapping"

# ============================================================================
# Structural vocabulary (fact type / attribute names, not concept names)
# ============================================================================

MAPPING_CONSTRUCTION = "mapping_construction"
INDEXED_WRITE = "indexed_write"

#: Mapping kind emitted for ``{...}`` — a fully written-out literal.
DICT_LITERAL = "dict_literal"

#: The only key origin that describes a caller supplied value.
KEY_ORIGIN_PARAMETER = "parameter"


@dataclass(frozen=True)
class LookupSpecificity:
    """The specificity verdict for one mapping-lookup evidence citation."""

    state: str
    reason: str
    variable: Optional[str] = None
    kind: str = ""
    key_origins: Tuple[str, ...] = ()
    updated_in_loop: Tuple[str, ...] = ()
    mutation_evidence: bool = False

    def __post_init__(self) -> None:
        if self.state not in SPECIFICITY_STATES:
            raise ValueError(f"unknown specificity state {self.state!r}")

    @property
    def strategy_eligible(self) -> bool:
        """Whether the evidence may support an algorithmic strategy conclusion."""
        return self.state == STRATEGY_ELIGIBLE


def cited_mapping(facts: Sequence, supporting_fact_ids: Sequence[str]):
    """The ``(variable, kind)`` of the mapping fact the evidence cites.

    Returns ``(None, "")`` when the citation contains no ``mapping_construction``
    fact — the module then declines to establish anything rather than guessing.
    """
    cited = set(supporting_fact_ids or ())
    for fact in facts:
        if fact.fact_type != MAPPING_CONSTRUCTION:
            continue
        if fact.fact_id not in cited:
            continue
        variable = fact.attributes.get("variable") or ""
        if variable:
            return variable, fact.attributes.get("kind") or ""
    return None, ""


def has_mutation_evidence(facts: Sequence, relations, variable: str) -> bool:
    """Whether ``variable`` is ever written or mutated after construction.

    An indexed write, an append/pop, or a self-referential cumulative update all
    mean the structure changes during the run — so it is not a static table.
    """
    for fact in facts:
        if fact.fact_type != INDEXED_WRITE:
            continue
        if fact.attributes.get("structure") == variable:
            return True
    if relations is None:
        return False
    for relation_name in ("collection_ops", "self_referential_updates"):
        mapping = getattr(relations, relation_name, None) or {}
        if mapping.get(variable):
            return True
    return False


def evaluate_lookup_specificity(
    facts: Sequence, relations, supporting_fact_ids: Sequence[str]
) -> LookupSpecificity:
    """Classify one mapping-lookup citation as strategy-specific or not.

    Suppression-only: every early return either declines to establish
    eligibility (no citation, R1, R2) or leaves the evidence as it stands.
    """
    variable, kind = cited_mapping(facts, supporting_fact_ids)
    if not variable:
        return LookupSpecificity(
            state=NOT_ESTABLISHED, reason=REASON_NO_CITED_MAPPING,
        )

    origins = frozenset(
        (getattr(relations, "lookup_key_origins", None) or {}).get(variable) or ()
    )
    updated = frozenset(
        (getattr(relations, "updated_in_loop", None) or {}).get(variable) or ()
    )
    mutated = has_mutation_evidence(facts, relations, variable)

    def verdict(state: str, reason: str) -> LookupSpecificity:
        return LookupSpecificity(
            state=state, reason=reason, variable=variable, kind=kind,
            key_origins=tuple(sorted(origins)),
            updated_in_loop=tuple(sorted(updated)),
            mutation_evidence=mutated,
        )

    # R1 — an immutable, fully written-out literal is a reference table.
    if kind == DICT_LITERAL and not mutated:
        return verdict(NOT_ESTABLISHED, REASON_STATIC_REFERENCE_TABLE)

    # R2 — keys supplied entirely from outside, and the mapping never changes.
    if origins == frozenset({KEY_ORIGIN_PARAMETER}) and not updated:
        return verdict(NOT_ESTABLISHED, REASON_PARAMETER_KEYED_MAPPING)

    return verdict(STRATEGY_ELIGIBLE, REASON_ALGORITHMIC_LOOKUP)


def evaluate_evidence_specificity(
    evidence, facts: Sequence, relations
) -> Optional[LookupSpecificity]:
    """Specificity for a technique-evidence citation, or ``None`` if absent.

    ``evidence`` is any object exposing ``supporting_fact_ids`` (the analysis
    layer's ``TechniqueEvidence``); this module never inspects technique ids.
    """
    if evidence is None:
        return None
    return evaluate_lookup_specificity(
        facts, relations, getattr(evidence, "supporting_fact_ids", ()) or ()
    )
