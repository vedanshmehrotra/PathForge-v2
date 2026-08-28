"""Authority upgrade metadata infrastructure.

Phase 5B: Adds metadata infrastructure for recording authority tier upgrades
on solution groups. This module supports:
- Creating upgrade records
- Serializing/deserializing upgrade records
- Validating upgrade records
- Storing upgrade history

CRITICAL: This module does NOT perform automatic upgrades.
It only provides the infrastructure for recording them.
Automatic upgrades are deferred to Phase 6+.
"""
import json
from datetime import datetime, timezone
from typing import Optional


# Valid authority tiers (matching ground_truth_builder.py)
VALID_AUTHORITY_TIERS = {
    "bootstrap",
    "llm_proposed",
    "structurally_observed",
    "externally_listed",
    "editorial",
    "reviewed",
}

# Valid tier transitions (from → to)
# Only these transitions are allowed
VALID_TIER_TRANSITIONS = {
    ("llm_proposed", "structurally_observed"),
    ("llm_proposed", "externally_listed"),
    ("llm_proposed", "editorial"),
    ("bootstrap", "structurally_observed"),
    ("bootstrap", "externally_listed"),
    ("bootstrap", "editorial"),
    ("structurally_observed", "editorial"),
    ("structurally_observed", "reviewed"),
    ("externally_listed", "editorial"),
    ("externally_listed", "reviewed"),
    ("editorial", "reviewed"),
}


class AuthorityUpgradeRecord:
    """Record of an authority tier upgrade for a solution group."""

    def __init__(
        self,
        group_id: str,
        problem_id: int,
        previous_tier: str,
        new_tier: str,
        evidence_sources: list[str] = None,
        timestamp: str = None,
        actor: str = "",
        reason: str = "",
    ):
        self.group_id = group_id
        self.problem_id = problem_id
        self.previous_tier = previous_tier
        self.new_tier = new_tier
        self.evidence_sources = evidence_sources or []
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.actor = actor
        self.reason = reason

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "group_id": self.group_id,
            "problem_id": self.problem_id,
            "previous_tier": self.previous_tier,
            "new_tier": self.new_tier,
            "evidence_sources": self.evidence_sources,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorityUpgradeRecord":
        """Deserialize from dictionary."""
        return cls(
            group_id=data.get("group_id", ""),
            problem_id=data.get("problem_id", 0),
            previous_tier=data.get("previous_tier", ""),
            new_tier=data.get("new_tier", ""),
            evidence_sources=data.get("evidence_sources", []),
            timestamp=data.get("timestamp", ""),
            actor=data.get("actor", ""),
            reason=data.get("reason", ""),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "AuthorityUpgradeRecord":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


def validate_upgrade_record(record: AuthorityUpgradeRecord) -> dict:
    """Validate an authority upgrade record.

    Returns {"valid": True/False, "reason": "..."}.
    """
    # Check required fields
    if not record.group_id:
        return {"valid": False, "reason": "group_id is required"}
    if not record.problem_id:
        return {"valid": False, "reason": "problem_id is required"}
    if not record.previous_tier:
        return {"valid": False, "reason": "previous_tier is required"}
    if not record.new_tier:
        return {"valid": False, "reason": "new_tier is required"}

    # Check tier validity
    if record.previous_tier not in VALID_AUTHORITY_TIERS:
        return {"valid": False, "reason": f"previous_tier '{record.previous_tier}' not valid"}
    if record.new_tier not in VALID_AUTHORITY_TIERS:
        return {"valid": False, "reason": f"new_tier '{record.new_tier}' not valid"}

    # Check transition validity
    transition = (record.previous_tier, record.new_tier)
    if transition not in VALID_TIER_TRANSITIONS:
        return {
            "valid": False,
            "reason": f"transition {record.previous_tier} → {record.new_tier} not allowed",
        }

    # Check evidence sources are provided
    if not record.evidence_sources:
        return {"valid": False, "reason": "evidence_sources cannot be empty"}

    # Check reason is provided
    if not record.reason:
        return {"valid": False, "reason": "reason is required"}

    return {"valid": True, "reason": ""}


def create_upgrade_record(
    group_id: str,
    problem_id: int,
    previous_tier: str,
    new_tier: str,
    evidence_sources: list[str],
    actor: str,
    reason: str,
    timestamp: str = None,
) -> AuthorityUpgradeRecord:
    """Create and validate an authority upgrade record.

    Returns the record if valid, raises ValueError if invalid.
    """
    record = AuthorityUpgradeRecord(
        group_id=group_id,
        problem_id=problem_id,
        previous_tier=previous_tier,
        new_tier=new_tier,
        evidence_sources=evidence_sources,
        timestamp=timestamp,
        actor=actor,
        reason=reason,
    )

    validation = validate_upgrade_record(record)
    if not validation["valid"]:
        raise ValueError(f"Invalid upgrade record: {validation['reason']}")

    return record


def serialize_upgrade_history(records: list[AuthorityUpgradeRecord]) -> str:
    """Serialize a list of upgrade records to JSON."""
    return json.dumps([r.to_dict() for r in records])


def deserialize_upgrade_history(json_str: str) -> list[AuthorityUpgradeRecord]:
    """Deserialize a JSON string to a list of upgrade records."""
    if not json_str:
        return []
    data = json.loads(json_str)
    return [AuthorityUpgradeRecord.from_dict(r) for r in data]


# ============================================================
# Evidence source types (for future Phase 6 use)
# ============================================================

EVIDENCE_SOURCE_TYPES = {
    "submission_cluster",      # Multiple independent submissions match
    "submission_independence", # Submissions use different variable names/syntax
    "submission_agreement",    # Independent implementations agree
    "contradiction_absence",   # No contradictions in recent submissions
    "external_source",         # External validation (e.g., editorial solution)
    "human_review",            # Human expert reviewed
    "structural_observation",  # Structural analysis confirms pattern
}


def validate_evidence_source(source: str) -> bool:
    """Check if an evidence source type is recognized."""
    return source in EVIDENCE_SOURCE_TYPES
