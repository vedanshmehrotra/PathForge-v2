"""Canonical authority vocabulary — ONE source of truth (Batch B5.5).

B5 exposed several Ground-Truth / authority inconsistencies: a stored
``authority_tier`` value that the builder itself rejected, two diverging tier
vocabularies, undocumented ``unknown``/``unobserved`` values, and a production
policy that disagreed with the B5 model. B5.5 normalizes the *representation*
here and nowhere else.

This module is the single place that answers:

* what the canonical authority **tiers** are;
* how a **stored/source** value maps onto them;
* which canonical tiers **authorize** an expected-approach conclusion;
* how to **normalize** a group's declared authority;
* what the **human-approval** semantics are.

It does **not** change production behavior. The current production policy is
recorded (:data:`LEGACY_PRODUCTION_AUTHORITATIVE_STATES`,
:data:`LEGACY_PRODUCTION_AUTHORITATIVE_TIERS`) so the conflict is visible and
pinned; migrating production is a B6 concern.

Stored value vs canonical tier
------------------------------

A stored value is what a Ground-Truth row literally contains. The canonical tier
is the semantic meaning. :data:`SOURCE_TIER_MAP` is the only mapping; every other
module imports it instead of restating it.
"""

from typing import Dict, Iterable, Optional, Tuple

# ============================================================================
# Canonical tiers
# ============================================================================

HUMAN_APPROVED = "HUMAN_APPROVED"
EXTERNAL_VERIFIED = "EXTERNAL_VERIFIED"
STRUCTURALLY_OBSERVED = "STRUCTURALLY_OBSERVED"
INFERRED = "INFERRED"

#: The only four canonical authority tiers, strongest first.
CANONICAL_TIERS: Tuple[str, ...] = (
    HUMAN_APPROVED,
    EXTERNAL_VERIFIED,
    STRUCTURALLY_OBSERVED,
    INFERRED,
)

CANONICAL_RANK: Dict[str, int] = {
    HUMAN_APPROVED: 3,
    EXTERNAL_VERIFIED: 2,
    STRUCTURALLY_OBSERVED: 1,
    INFERRED: 0,
}

#: Tiers that may authorize an expected-approach conclusion.
#:
#: ``STRUCTURALLY_OBSERVED`` is deliberately absent: it denotes deterministic
#: analyzer evidence **about the submitted implementation**, never Ground Truth
#: about the expected solution (B5 policy, Part 3 of the B5.5 brief).
AUTHORIZING_TIERS = frozenset({HUMAN_APPROVED, EXTERNAL_VERIFIED})


# ============================================================================
# Stored value → canonical tier (the ONE mapping)
# ============================================================================

#: Every recognised stored value, with the canonical tier it maps to and why.
#:
#: The semantics below were established from the code that writes each value:
#:
#: * ``human_curated`` — written by CSV reconciliation in
#:   ``problem_resolver._load_ground_truth`` when the curated pattern label
#:   overrides/agrees with the stored one. Explicit human adjudication of the
#:   accepted approach => HUMAN_APPROVED.
#: * ``human_approved`` — the canonical human-approved name.
#: * ``reviewed`` — human review (``shadow/authority.py`` transition target
#:   ``editorial → reviewed``); same human adjudication => HUMAN_APPROVED.
#: * ``editorial`` — the tier the V2 review pipeline writes on derived groups
#:   (``gt_poc_v2/derive.py``) whose activation requires
#:   ``approval_state == APPROVED`` with ``granularity:
#:   family_level_human_approved``. Human-reviewed family label =>
#:   HUMAN_APPROVED. (No corpus row currently exercises it; recorded as an
#:   unresolved provenance question in the B5.5 audit.)
#: * ``externally_listed`` — trusted external/reference evidence explicitly
#:   marked as such => EXTERNAL_VERIFIED.
#: * ``structurally_observed`` — analyzer-derived evidence about the submitted
#:   code; also the tier ``scripts/seed_ground_truth.py`` writes =>
#:   STRUCTURALLY_OBSERVED (non-authorizing).
#: * ``llm_proposed`` — LLM-proposed Ground Truth => INFERRED.
#: * ``bootstrap`` — cold-start placeholder => INFERRED.
#: * ``unobserved`` — no observation was recorded => INFERRED (missing metadata).
#: * ``unknown`` — unspecified tier => INFERRED (missing metadata).
#: * ``inferred`` / ``hypothesis`` — the canonical non-authoritative names.
SOURCE_TIER_MAP: Dict[str, str] = {
    # human adjudication
    "human_curated": HUMAN_APPROVED,
    "human_approved": HUMAN_APPROVED,
    "reviewed": HUMAN_APPROVED,
    "editorial": HUMAN_APPROVED,
    # external / reference evidence
    "externally_listed": EXTERNAL_VERIFIED,
    "external_verified": EXTERNAL_VERIFIED,
    # analyzer evidence about the submitted code
    "structurally_observed": STRUCTURALLY_OBSERVED,
    # non-authoritative inference / missing metadata
    "llm_proposed": INFERRED,
    "bootstrap": INFERRED,
    "unobserved": INFERRED,
    "unknown": INFERRED,
    "inferred": INFERRED,
    "hypothesis": INFERRED,
}

#: Values that are explicit human adjudication of the accepted approach.
HUMAN_APPROVAL_SOURCES = frozenset(
    {"human_curated", "human_approved", "reviewed", "editorial"}
)

#: All recognised stored values.
KNOWN_SOURCE_TIERS = frozenset(SOURCE_TIER_MAP)

#: Stored values that mean "authority metadata is absent/unspecified" rather
#: than "a weaker authority tier". They still map conservatively to ``INFERRED``
#: — absence never becomes authority.
MISSING_AUTHORITY_VALUES = frozenset({"unknown", "unobserved", ""})


# ============================================================================
# Ground-Truth builder vocabulary
# ============================================================================

#: The stored values the Ground-Truth builder accepts as valid.
#:
#: B5.5 adds ``human_curated`` (written by CSV reconciliation but previously
#: absent from the builder's accepted set) and ``reviewed`` (accepted by
#: ``shadow/authority.py`` but not by the builder). ``unknown``/``unobserved``
#: remain *loader* fallbacks and are intentionally not builder-accepted.
VALID_GT_TIERS = frozenset({
    "bootstrap",
    "llm_proposed",
    "structurally_observed",
    "externally_listed",
    "editorial",
    "human_curated",
    "reviewed",
})


# ============================================================================
# Legacy production policy (recorded, NOT applied here)
# ============================================================================

#: ``pathforge/services/persistence.py::_AUTHORITATIVE_STATES`` — the evidence
#: values that currently grant authoritative downstream behavior (Elo/gaps).
#: NOTE: this is the *existing production contract*; it conflicts with the
#: canonical policy (it trusts ``structurally_observed`` and ignores
#: ``human_curated``). B5.5 records it and pins it with a test; B6 migrates it.
LEGACY_PRODUCTION_AUTHORITATIVE_STATES = frozenset({
    "structurally_observed",
    "externally_listed",
})

#: ``pathforge/ast_analysis/shadow/matching.py::_AUTHORITATIVE_TIERS`` — the
#: tiers the old shadow matcher treats as authoritative. Same conflict.
LEGACY_PRODUCTION_AUTHORITATIVE_TIERS = frozenset({
    "structurally_observed",
    "externally_listed",
    "editorial",
})


# ============================================================================
# Alternative-family representation
# ============================================================================

#: A family's relation to its siblings in the same Ground-Truth problem.
FAMILY_RELATION_ONE_OF = "ONE_OF"
FAMILY_RELATION_INDEPENDENT = "INDEPENDENT"

#: The key that marks a group as one alternative in a ONE_OF set, and the key
#: that ties sibling alternatives together.
RELATION_FIELD = "family_relation"
ALTERNATIVE_GROUP_FIELD = "alternative_group_id"


# ============================================================================
# Helpers
# ============================================================================

def normalize_authority_tier(declared: Optional[str]) -> str:
    """Map any stored/declared value onto a canonical tier.

    Unrecognised or missing values map to ``INFERRED`` — never to an
    authorizing tier. Absence of authority is never promoted to authority.
    """
    key = (declared or "").strip().lower()
    return SOURCE_TIER_MAP.get(key, INFERRED)


def is_known_source_tier(declared: Optional[str]) -> bool:
    """Whether a declared value is explicitly recognised."""
    return (declared or "").strip().lower() in SOURCE_TIER_MAP


def is_missing_authority(declared: Optional[str]) -> bool:
    """Whether a declared value denotes absent/unspecified authority metadata."""
    return (declared or "").strip().lower() in MISSING_AUTHORITY_VALUES


def is_authorizing(declared: Optional[str]) -> bool:
    """Whether a declared value authorizes an expected-approach conclusion."""
    return normalize_authority_tier(declared) in AUTHORIZING_TIERS


def authority_data_quality(declared_values: Iterable[Optional[str]]) -> dict:
    """Report stored authority values that cannot be interpreted cleanly.

    Surfaces (never repairs):

    * ``unrecognized`` — values absent from :data:`SOURCE_TIER_MAP`
      (including missing / empty);
    * ``missing_metadata`` — values that mean "authority unspecified";
    * ``not_builder_accepted`` — values the GT builder itself would reject.
    """
    unrecognized: Dict[str, int] = {}
    missing: Dict[str, int] = {}
    not_accepted: Dict[str, int] = {}
    for declared in declared_values:
        label = declared if declared is not None else "<missing>"
        key = (declared or "").strip().lower()
        if key not in SOURCE_TIER_MAP:
            unrecognized[label] = unrecognized.get(label, 0) + 1
        if key in MISSING_AUTHORITY_VALUES:
            missing[label] = missing.get(label, 0) + 1
        if key not in VALID_GT_TIERS:
            not_accepted[label] = not_accepted.get(label, 0) + 1
    return {
        "unrecognized": dict(sorted(unrecognized.items())),
        "missing_metadata": dict(sorted(missing.items())),
        "not_builder_accepted": dict(sorted(not_accepted.items())),
    }


def canonical_authority_of_group(group: dict) -> Tuple[str, str]:
    """``(stored_value, canonical_tier)`` for a Ground-Truth group dict."""
    stored = group.get("authority_tier")
    if stored is None:
        stored = group.get("evidence", "unknown")
    return str(stored), normalize_authority_tier(stored)


def authority_evidence_agreement(group: dict) -> dict:
    """Compare a group's ``authority_tier`` and its legacy ``evidence`` field.

    They are two stored representations of the same authority concept
    (``_load_ground_truth`` writes ``authority_tier`` and keeps ``evidence``).
    When both are present they must resolve to the same canonical tier; a
    disagreement is reported rather than overwritten.
    """
    authority = group.get("authority_tier")
    evidence = group.get("evidence")
    a_canon = normalize_authority_tier(authority) if authority is not None else None
    e_canon = normalize_authority_tier(evidence) if evidence is not None else None
    agree = (
        a_canon is None or e_canon is None or a_canon == e_canon
    )
    return {
        "authority_tier": authority,
        "evidence": evidence,
        "authority_canonical": a_canon,
        "evidence_canonical": e_canon,
        "authorizing": bool(a_canon in AUTHORIZING_TIERS) if a_canon else False,
        "agree": agree,
    }


def find_authority_evidence_disagreements(groups) -> list:
    """Report groups whose ``authority_tier`` and ``evidence`` disagree."""
    findings = []
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        result = authority_evidence_agreement(group)
        if not result["agree"]:
            findings.append({
                "group_id": group.get("id", ""),
                **result,
            })
    return findings


# ============================================================================
# Canonical normalization (B6.5) — one direction, explicit, fail-closed
# ============================================================================

#: Diagnostic emitted when a group's two stored authority representations
#: resolve to different canonical tiers. No precedence is invented: the pair is
#: reported and consumers must fail closed.
AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"

#: Diagnostic for a group whose ``authority_tier`` is absent entirely.
AUTHORITY_MISSING = "AUTHORITY_MISSING"

#: Diagnostic for a group whose ``authority_tier`` is present but unrecognised.
AUTHORITY_UNKNOWN = "AUTHORITY_UNKNOWN"

#: All normalization diagnostics.
AUTHORITY_DIAGNOSTICS = (AUTHORITY_CONFLICT, AUTHORITY_MISSING, AUTHORITY_UNKNOWN)

#: The field B6.5 designates the canonical semantic authority representation.
CANONICAL_AUTHORITY_FIELD = "authority_tier"

#: The legacy compatibility representation (never deleted, never canonical).
LEGACY_AUTHORITY_FIELD = "evidence"


def normalize_group_authority(group: dict) -> dict:
    """Normalize one group's authority, explicitly and without invention.

    Returns a diagnostic record (never mutates the group):

    * ``diagnostic`` — ``None`` when the pair is consistent and present;
      otherwise one of :data:`AUTHORITY_DIAGNOSTICS`;
    * ``authority_tier`` / ``evidence`` — the two stored values;
    * ``canonical_tier`` — the canonical interpretation of ``authority_tier``
      (falling back to ``evidence`` only when ``authority_tier`` is absent);
    * ``evidence_canonical_tier`` — the canonical interpretation of ``evidence``;
    * ``conflict`` — whether the two stored values disagree canonically.

    Rules (B6.5, narrowest-safe):

    * both present and canonically equal → no diagnostic;
    * both present and canonically different → ``AUTHORITY_CONFLICT``;
    * ``authority_tier`` absent → ``AUTHORITY_MISSING`` (canonical tier comes
      from ``evidence`` as the legacy compatibility fallback, and is reported);
    * ``authority_tier`` unrecognised → ``AUTHORITY_UNKNOWN``.
    """
    authority_value = group.get(CANONICAL_AUTHORITY_FIELD)
    evidence_value = group.get(LEGACY_AUTHORITY_FIELD)

    authority_known = is_known_source_tier(authority_value)
    authority_canon = (
        normalize_authority_tier(authority_value)
        if authority_value is not None else None
    )
    evidence_canon = (
        normalize_authority_tier(evidence_value)
        if evidence_value is not None else None
    )

    if authority_value is None:
        diagnostic = AUTHORITY_MISSING
        canonical_tier = evidence_canon if evidence_canon else INFERRED
    elif not authority_known:
        diagnostic = AUTHORITY_UNKNOWN
        canonical_tier = INFERRED  # unrecognised never becomes authority
    elif evidence_value is not None and evidence_canon != authority_canon:
        diagnostic = AUTHORITY_CONFLICT
        canonical_tier = authority_canon
    else:
        diagnostic = None
        canonical_tier = authority_canon

    # B6.5 fail-closed rule: a conflicting pair never authorizes, regardless of
    # which single representation would authorize on its own. No precedence is
    # invented between the two stored representations.
    conflicted = diagnostic == AUTHORITY_CONFLICT
    authorizing = (
        canonical_tier in AUTHORIZING_TIERS and not conflicted
        if canonical_tier else False
    )

    return {
        "group_id": group.get("id", ""),
        "diagnostic": diagnostic,
        CANONICAL_AUTHORITY_FIELD: authority_value,
        LEGACY_AUTHORITY_FIELD: evidence_value,
        "canonical_tier": canonical_tier,
        "evidence_canonical_tier": evidence_canon,
        "conflict": conflicted,
        "authorizing": authorizing,
    }


def find_normalization_conflicts(groups) -> list:
    """All ``AUTHORITY_CONFLICT`` records among the supplied groups."""
    return [
        record
        for record in (normalize_group_authority(g) for g in groups or []
                       if isinstance(g, dict))
        if record["diagnostic"] is not None
    ]


def to_legacy_evidence(tier: str) -> str:
    """Canonical tier → a representative legacy ``evidence`` value.

    The explicit, tested inverse of :func:`normalize_authority_tier` for
    compatibility writing. Several stored values map to one canonical tier, so
    the representative is the value the production code actually writes:

    * ``HUMAN_APPROVED`` → ``human_curated`` (CSV reconciliation's value);
    * ``EXTERNAL_VERIFIED`` → ``externally_listed``;
    * ``STRUCTURALLY_OBSERVED`` → ``structurally_observed``;
    * ``INFERRED`` → ``llm_proposed`` (the builder's normal value).
    """
    representatives = {
        HUMAN_APPROVED: "human_curated",
        EXTERNAL_VERIFIED: "externally_listed",
        STRUCTURALLY_OBSERVED: "structurally_observed",
        INFERRED: "llm_proposed",
    }
    return representatives[tier]


__all__ = [
    # canonical tiers
    "HUMAN_APPROVED", "EXTERNAL_VERIFIED", "STRUCTURALLY_OBSERVED", "INFERRED",
    "CANONICAL_TIERS", "CANONICAL_RANK", "AUTHORIZING_TIERS",
    # vocabularies
    "SOURCE_TIER_MAP", "KNOWN_SOURCE_TIERS", "HUMAN_APPROVAL_SOURCES",
    "MISSING_AUTHORITY_VALUES", "VALID_GT_TIERS",
    # legacy production policy
    "LEGACY_PRODUCTION_AUTHORITATIVE_STATES",
    "LEGACY_PRODUCTION_AUTHORITATIVE_TIERS",
    # alternative-family representation
    "FAMILY_RELATION_ONE_OF", "FAMILY_RELATION_INDEPENDENT",
    "RELATION_FIELD", "ALTERNATIVE_GROUP_FIELD",
    # helpers
    "normalize_authority_tier", "is_known_source_tier", "is_missing_authority",
    "is_authorizing", "authority_data_quality", "canonical_authority_of_group",
    "authority_evidence_agreement", "find_authority_evidence_disagreements",
    # B6.5 normalization
    "AUTHORITY_CONFLICT", "AUTHORITY_MISSING", "AUTHORITY_UNKNOWN",
    "AUTHORITY_DIAGNOSTICS", "CANONICAL_AUTHORITY_FIELD", "LEGACY_AUTHORITY_FIELD",
    "normalize_group_authority", "find_normalization_conflicts", "to_legacy_evidence",
]
