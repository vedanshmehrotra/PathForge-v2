"""B8 — explicit Ground-Truth authority reconciliation.

B7 isolated 28 P7 authority-conflict submissions (32 underlying group-level
conflicts). B6.5 deliberately failed them closed instead of choosing a value.
B8 resolves them **only through explicit provenance** — never by picking the
value that "looks more trustworthy".

The critical B8 finding (documented in the audit, §4–§5):

**``evidence`` is NOT a second GT-authority field — it is the *legacy
validation state* the Ground-Truth row was written with, and it is overloaded
with implementation evidence semantics by the legacy Elo reader
(``EVIDENCE_K_CEILINGS``: "structurally_observed" = how strongly the *submitted
implementation* was observed).** The stored DB rows are internally consistent
(``authority_tier == evidence`` on every seeded row, provenance
``manual_verification``); the load-time CSV reconciliation then overwrites the
emitted ``authority_tier`` to ``"human_curated"`` while leaving the stored
``evidence`` untouched. The 32 conflicts are therefore **field-semantic
collisions created at load time**, not incorrect GT and not two disagreeing
human decisions.

Reconciliation statuses (exactly one per conflict):

``RECONCILE_*``
    Explicit provenance establishes the canonical tier. The resolution is
    applied through a **versioned GT update** — the stored row is never
    silently rewritten: a ``reconciliation`` provenance marker, a bumped
    version, and an ``authority_reconciliation`` record are added.
``NEEDS_HUMAN_REVIEW``
    Available records cannot establish which authority value is correct.
    Emits a review record; the row stays **fail-closed**.

Nothing is inferred: no human approval, no external verification, no
implementation evidence promoted to GT authority. Unresolved rows remain
non-authoritative (B6.5 rule).
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pathforge.ast_analysis import authority_vocabulary as vocab

# ============================================================================
# Reconciliation statuses
# ============================================================================

RECONCILE_HUMAN_APPROVED = "RECONCILE_HUMAN_APPROVED"
RECONCILE_EXTERNAL_VERIFIED = "RECONCILE_EXTERNAL_VERIFIED"
RECONCILE_STRUCTURALLY_OBSERVED = "RECONCILE_STRUCTURALLY_OBSERVED"
RECONCILE_INFERRED = "RECONCILE_INFERRED"
NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"

RECONCILIATION_STATUSES: Tuple[str, ...] = (
    RECONCILE_HUMAN_APPROVED,
    RECONCILE_EXTERNAL_VERIFIED,
    RECONCILE_STRUCTURALLY_OBSERVED,
    RECONCILE_INFERRED,
    NEEDS_HUMAN_REVIEW,
)

RESOLVED_STATUSES = frozenset({
    RECONCILE_HUMAN_APPROVED,
    RECONCILE_EXTERNAL_VERIFIED,
    RECONCILE_STRUCTURALLY_OBSERVED,
    RECONCILE_INFERRED,
})

#: Provenance markers written by the reconciliation workflow.
RECONCILIATION_MARKER = "b8_authority_reconciliation"
#: The load-time mechanism that created the conflict (see module docstring).
CSV_RECONCILIATION_COLLISION = "csv_reconciliation_field_collision"

#: Explicit provenance markers that establish *human* adjudication of the
#: expected solution. Only these may resolve to HUMAN_APPROVED — and only when
#: the stored tier agrees. Seeded rows carry ``manual_verification``.
HUMAN_APPROVAL_PROVENANCE = frozenset({
    "manual_verification",     # seed_ground_truth.py: "manually verified"
    "csv_curated_override",    # curated CSV label replaced the stored one
    "csv_curated",
})

#: Explicit provenance markers that establish external/reference verification.
EXTERNAL_VERIFICATION_PROVENANCE = frozenset({
    "externally_listed",
    "external_verified",
})

#: Provenance markers that establish the GT was derived without human/external
#: approval (the LLM builder path).
INFERRED_PROVENANCE = frozenset({
    "llm_ground_truth",        # ground_truth_builder._build_single_group
    "vocabulary_v1",           # mechanical vocabulary derivation marker
    "vocabulary_refresh_v2",
})

#: The version bumped on reconciled GT rows.
RECONCILIATION_VERSION = 2


# ============================================================================
# Field semantics (the documented answer to B8 §5)
# ============================================================================

#: Writers of ``authority_tier`` on a stored group:
#: ``seed_ground_truth.py`` (structurally_observed, manual_verification),
#: ``ground_truth_builder._build_single_group`` (llm_proposed).
#: Load-time writer (emitted groups only): CSV reconciliation in
#: ``problem_resolver._load_ground_truth`` (human_curated).
#:
#: Readers: the shadow authority path (B5/B5.5/B6) and the vocabulary
#: reconciliation fallback in the loader.
#:
#: SEMANTICS: **GT authority — who/what established the expected solution.**
AUTHORITY_TIER_SEMANTICS = {
    "field": "authority_tier",
    "semantics": "ground_truth_authority",
    "meaning": "who/what established the expected solution family",
    "stored_row_writers": [
        "pathforge/scripts/seed_ground_truth.py (structurally_observed + "
        "provenance manual_verification)",
        "pathforge/services/ground_truth_builder.py::_build_single_group "
        "(llm_proposed + provenance llm_ground_truth)",
    ],
    "load_time_writer": (
        "problem_resolver._load_ground_truth CSV reconciliation overwrites the "
        "EMITTED authority_tier with 'human_curated' when a curated CSV "
        "pattern exists — the stored row is not modified"
    ),
    "readers": [
        "pathforge/ast_analysis/shadow/authority_gating.py (B5/B5.5)",
        "pathforge/ast_analysis/shadow/family_coverage.py (B3 passthrough)",
    ],
}

#: Writers of ``evidence`` on a stored group:
#: ``seed_ground_truth.py`` (structurally_observed) and
#: ``ground_truth_builder._build_single_group`` (llm_proposed) — always equal
#: to the row's authority tier at write time.
#:
#: Readers:
#: ``problem_resolver._load_ground_truth`` (fallback for a missing tier),
#: ``persistence.run_persistence`` (legacy verdict_type gate) and
#: ``elo_engine`` via ``EVIDENCE_K_CEILINGS``.
#:
#: SEMANTICS: the **legacy validation state**, overloaded with
#: implementation-evidence semantics by the Elo reader (a "structurally
#: observed" evidence value raises the Elo K ceiling — that is a claim about
#: how strongly the *implementation* was observed, not about who approved the
#: GT). It is NOT an independent second GT-authority field.
EVIDENCE_SEMANTICS = {
    "field": "evidence",
    "semantics": "legacy_validation_state (overloaded)",
    "meaning": (
        "the validation state the GT row was written with; the legacy Elo "
        "reader additionally treats it as implementation-evidence strength"
    ),
    "stored_row_writers": [
        "pathforge/scripts/seed_ground_truth.py (equals authority_tier)",
        "pathforge/services/ground_truth_builder.py (equals authority_tier)",
    ],
    "readers": [
        "pathforge/services/persistence.py (legacy verdict_type gate: "
        "evidence in {structurally_observed, externally_listed})",
        "pathforge/elo_engine.py (EVIDENCE_K_CEILINGS — implementation-"
        "evidence strength semantics)",
        "problem_resolver._load_ground_truth (fallback when authority_tier "
        "is absent)",
    ],
    "overloading_note": (
        "the 32 B7 conflicts are field-semantic collisions: CSV reconciliation "
        "rewrites the emitted authority_tier (GT-authority semantics) to "
        "human_curated while evidence keeps its legacy-validation value — "
        "the two fields never disagreed in the STORED rows"
    ),
}


# ============================================================================
# Conflict record
# ============================================================================

@dataclass
class AuthorityConflict:
    """One group-level authority conflict, with every available provenance."""

    problem_id: Optional[int]
    group_id: str
    concepts: List[str]
    authority_tier: Optional[str]
    evidence: Optional[str]
    canonical_from_authority_tier: Optional[str]
    canonical_from_evidence: Optional[str]
    provenance: List[str]
    version: Optional[int]
    family_relation: Optional[str]
    alternative_group_id: Optional[str]
    #: Where each field came from (as available).
    sources: Dict[str, str]
    legacy_behavior: str
    shadow_behavior: str
    b6_behavior: str
    #: The STORED row's own authority_tier (before load-time reconciliation).
    stored_authority_tier: Optional[str] = None
    #: The STORED row's own provenance list.
    stored_provenance: List[str] = None
    #: The STORED row's validation_status.
    stored_validation_status: Optional[str] = None
    #: The curated CSV pattern label, when one exists.
    csv_pattern: Optional[str] = None
    #: The reconciled status (set by :func:`classify_conflict`).
    reconciliation_status: str = NEEDS_HUMAN_REVIEW
    #: Why this status was assigned (provenance-based, never intuitive).
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "group_id": self.group_id,
            "concepts": list(self.concepts),
            "authority_tier": self.authority_tier,
            "evidence": self.evidence,
            "canonical_authority_tier_from_authority_tier":
                self.canonical_from_authority_tier,
            "canonical_authority_tier_from_evidence":
                self.canonical_from_evidence,
            "provenance": list(self.provenance),
            "version": self.version,
            "family_relation": self.family_relation,
            "alternative_group_id": self.alternative_group_id,
            "sources": dict(self.sources),
            "legacy_behavior": self.legacy_behavior,
            "shadow_behavior": self.shadow_behavior,
            "b6_behavior": self.b6_behavior,
            "stored_authority_tier": self.stored_authority_tier,
            "stored_provenance": list(self.stored_provenance or []),
            "stored_validation_status": self.stored_validation_status,
            "csv_pattern": self.csv_pattern,
            "reconciliation_status": self.reconciliation_status,
            "reason": self.reason,
        }


def conflict_from_group(group: dict, problem_id: Optional[int],
                        legacy_behavior: str = "evidence-based gate",
                        shadow_behavior: str = "canonical authority (fail-closed)",
                        b6_behavior: str = "blocked (B6.5)",
                        stored_authority_tier: Optional[str] = None,
                        stored_provenance: Optional[List[str]] = None,
                        stored_validation_status: Optional[str] = None,
                        csv_pattern: Optional[str] = None) -> AuthorityConflict:
    """Build a conflict record from one loader-annotated group.

    ``stored_*`` arguments carry the DB row's own values (before load-time
    reconciliation) — they are the explicit provenance B8 classifies on.
    """
    normalization = group.get("authority_normalization") or {}
    return AuthorityConflict(
        problem_id=problem_id,
        group_id=str(group.get("id", "")),
        concepts=list(group.get("required") or []),
        authority_tier=group.get("authority_tier"),
        evidence=group.get("evidence"),
        canonical_from_authority_tier=vocab.normalize_authority_tier(
            group.get("authority_tier")) if group.get("authority_tier") is not None
        else None,
        canonical_from_evidence=vocab.normalize_authority_tier(
            group.get("evidence")) if group.get("evidence") is not None else None,
        provenance=list(group.get("provenance") or []),
        version=group.get("version"),
        family_relation=group.get("family_relation"),
        alternative_group_id=group.get("alternative_group_id"),
        sources={
            "authority_tier": "emitted group (load-time CSV reconciliation)",
            "evidence": "stored problem_ground_truth.solution_groups row",
            "provenance": "stored problem_ground_truth.solution_groups row",
            "version": "stored problem_ground_truth.solution_groups row",
            "concepts": "stored row required (V1 vocabulary)",
        },
        legacy_behavior=legacy_behavior,
        shadow_behavior=shadow_behavior,
        b6_behavior=b6_behavior,
        stored_authority_tier=stored_authority_tier,
        stored_provenance=list(stored_provenance or []),
        stored_validation_status=stored_validation_status,
        csv_pattern=csv_pattern,
    )


# ============================================================================
# Classification (explicit provenance only)
# ============================================================================

def classify_conflict(conflict: AuthorityConflict) -> AuthorityConflict:
    """Assign exactly one reconciliation status, from explicit provenance.

    The rules, in order:

    1. **CSV-reconciliation collision** (the documented mechanism behind the 32
       conflicts): the STORED row's own ``authority_tier`` and ``evidence``
       agree canonically and carry a documented writer provenance, while the
       emitted tier was overwritten to ``human_curated`` by the loader. The
       *stored* authority is the explicit provenance — it is what the GT writer
       recorded. Resolution: the stored tier (``structurally_observed`` →
       RECONCILE_STRUCTURALLY_OBSERVED, ``llm_proposed`` →
       RECONCILE_INFERRED). Human approval is **never** inferred from the
       ``csv_curated`` marker: the curated CSV is a *pattern* label, not a
       recorded human approval of the GT family.
    2. Otherwise → ``NEEDS_HUMAN_REVIEW`` (fail-closed).
    """
    provenance = set(conflict.stored_provenance or conflict.provenance or [])

    stored_tier = (
        vocab.normalize_authority_tier(conflict.stored_authority_tier)
        if conflict.stored_authority_tier is not None else None
    )
    evidence_canon = conflict.canonical_from_evidence

    documented_writer = bool(
        provenance & (HUMAN_APPROVAL_PROVENANCE | INFERRED_PROVENANCE)
    ) or conflict.stored_validation_status in {
        "structurally_observed", "llm_proposed", "unobserved",
    }

    is_collision = (
        conflict.authority_tier == "human_curated"
        and stored_tier is not None
        and stored_tier == evidence_canon
        and conflict.evidence is not None
        and documented_writer
    )

    if is_collision:
        # The stored row is self-consistent; the emitted tier was overwritten
        # at load time. Restore the stored authority, explicitly.
        conflict.reconciliation_status = (
            RECONCILE_STRUCTURALLY_OBSERVED
            if stored_tier == vocab.STRUCTURALLY_OBSERVED
            else RECONCILE_INFERRED if stored_tier == vocab.INFERRED
            else RECONCILE_EXTERNAL_VERIFIED
            if stored_tier == vocab.EXTERNAL_VERIFIED
            else RECONCILE_HUMAN_APPROVED
            if stored_tier == vocab.HUMAN_APPROVED
            else NEEDS_HUMAN_REVIEW
        )
        conflict.reason = (
            f"load-time CSV reconciliation collision: the STORED row records "
            f"authority_tier == evidence == {conflict.evidence!r} with "
            f"provenance {sorted(provenance)}; the emitted tier was overwritten "
            f"to 'human_curated' by the curated-pattern path. Resolution "
            f"restores the stored authority explicitly (marker "
            f"{CSV_RECONCILIATION_COLLISION})."
        )
        return conflict

    # Anything else: the records cannot establish the answer.
    conflict.reconciliation_status = NEEDS_HUMAN_REVIEW
    conflict.reason = (
        "available records do not establish which authority value is correct; "
        f"authority_tier={conflict.authority_tier!r}, "
        f"evidence={conflict.evidence!r}, stored_tier="
        f"{conflict.stored_authority_tier!r}, provenance={sorted(provenance)}"
    )
    return conflict


def review_record(conflict: AuthorityConflict) -> dict:
    """The human-review artifact for an unresolved conflict (B8 §7)."""
    return {
        "problem_id": conflict.problem_id,
        "group_id": conflict.group_id,
        "current_authority_tier": conflict.authority_tier,
        "current_evidence": conflict.evidence,
        "candidate_resolution": conflict.canonical_from_authority_tier,
        "reason": conflict.reason,
        "required_reviewer": "human",
        "status": NEEDS_HUMAN_REVIEW,
    }


# ============================================================================
# Versioned GT update
# ============================================================================

def apply_resolution(group: dict, status: str) -> Optional[dict]:
    """Apply an explicit resolution to a group dict — versioned, never silent.

    Returns the change record, or ``None`` when the status does not authorize a
    stored-field change. The original ``authority_tier`` value is preserved
    under ``reconciled_from``; ``evidence`` is left untouched (legacy field).
    """
    if status not in RESOLVED_STATUSES:
        return None

    canonical = {
        RECONCILE_HUMAN_APPROVED: vocab.HUMAN_APPROVED,
        RECONCILE_EXTERNAL_VERIFIED: vocab.EXTERNAL_VERIFIED,
        RECONCILE_STRUCTURALLY_OBSERVED: vocab.STRUCTURALLY_OBSERVED,
        RECONCILE_INFERRED: vocab.INFERRED,
    }[status]

    previous = group.get("authority_tier")
    # stored values are lower-case source vocabulary
    stored_values = {
        vocab.HUMAN_APPROVED: "human_approved",
        vocab.EXTERNAL_VERIFIED: "externally_listed",
        vocab.STRUCTURALLY_OBSERVED: "structurally_observed",
        vocab.INFERRED: "llm_proposed",
    }
    resolved_stored = stored_values[canonical]

    provenance = list(group.get("provenance") or [])
    if RECONCILIATION_MARKER not in provenance:
        provenance.append(RECONCILIATION_MARKER)
    provenance.append(CSV_RECONCILIATION_COLLISION)

    group["reconciled_from"] = {
        "authority_tier": previous,
        "evidence": group.get("evidence"),
        "previous_version": group.get("version"),
    }
    group["authority_tier"] = resolved_stored
    group["provenance"] = provenance
    group["version"] = RECONCILIATION_VERSION
    # refresh the normalization annotation so downstream sees a clean pair
    group["authority_normalization"] = vocab.normalize_group_authority(group)
    return {
        "group_id": group.get("id", ""),
        "resolved_stored_tier": resolved_stored,
        "canonical_tier": canonical,
        "reconciled_from_tier": previous,
        "version": RECONCILIATION_VERSION,
    }


def reconciliation_conflict_count(groups) -> int:
    """How many groups carry an unresolved normalization conflict."""
    return sum(
        1
        for g in (groups or [])
        if isinstance(g, dict)
        and (g.get("authority_normalization") or {}).get("diagnostic")
        == vocab.AUTHORITY_CONFLICT
    )


__all__ = [
    # statuses
    "RECONCILIATION_STATUSES", "RESOLVED_STATUSES",
    "RECONCILE_HUMAN_APPROVED", "RECONCILE_EXTERNAL_VERIFIED",
    "RECONCILE_STRUCTURALLY_OBSERVED", "RECONCILE_INFERRED", "NEEDS_HUMAN_REVIEW",
    # markers
    "RECONCILIATION_MARKER", "CSV_RECONCILIATION_COLLISION",
    "RECONCILIATION_VERSION",
    # provenance sets
    "HUMAN_APPROVAL_PROVENANCE", "EXTERNAL_VERIFICATION_PROVENANCE",
    "INFERRED_PROVENANCE",
    # field semantics
    "AUTHORITY_TIER_SEMANTICS", "EVIDENCE_SEMANTICS",
    # records + functions
    "AuthorityConflict", "conflict_from_group", "classify_conflict",
    "review_record", "apply_resolution", "reconciliation_conflict_count",
]
