"""Shadow analysis persistence — save and reload structural facts.

Structural facts are the canonical persisted artifact.
Technique/strategy evidence may be persisted as derived/cache data.

This module provides:
- persist_shadow_analysis(): save shadow results to submissions table
- load_shadow_facts(): reload structural facts from submissions table
- rerun_derivation(): re-derive technique/strategy evidence from stored facts
- serialize/deserialize helpers for JSONB columns

All operations are read/write to the existing submissions table.
No new tables are created.
"""
import hashlib
import json
import logging
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, StrategyEvidence, MatchOutcome,
    EXTRACTOR_VERSION,
)
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups

logger = logging.getLogger(__name__)


# ============================================================
# Serialization helpers
# ============================================================

def serialize_facts(facts: list[StructuralFact]) -> list[dict]:
    """Serialize structural facts to a JSON-serializable list."""
    return [
        {
            "fact_id": f.fact_id,
            "fact_type": f.fact_type,
            "ast_ref": f.ast_ref,
            "attributes": f.attributes,
            "extractor_version": f.extractor_version,
        }
        for f in facts
    ]


def deserialize_facts(data: list[dict]) -> list[StructuralFact]:
    """Deserialize a JSON list back to StructuralFact objects."""
    return [
        StructuralFact(
            fact_id=d.get("fact_id", ""),
            fact_type=d.get("fact_type", ""),
            ast_ref=d.get("ast_ref", ""),
            attributes=d.get("attributes", {}),
            extractor_version=d.get("extractor_version", EXTRACTOR_VERSION),
        )
        for d in data
    ]


def serialize_techniques(techniques: list[TechniqueEvidence]) -> list[dict]:
    """Serialize technique evidence to a JSON-serializable list."""
    return [
        {
            "technique_id": t.technique_id,
            "technique_version": t.technique_version,
            "supporting_fact_ids": t.supporting_fact_ids,
            "presence_confidence": t.presence_confidence,
            "centrality": t.centrality,
        }
        for t in techniques
    ]


def deserialize_techniques(data: list[dict]) -> list[TechniqueEvidence]:
    """Deserialize a JSON list back to TechniqueEvidence objects."""
    return [
        TechniqueEvidence(
            technique_id=d.get("technique_id", ""),
            technique_version=d.get("technique_version", "1.0.0"),
            supporting_fact_ids=d.get("supporting_fact_ids", []),
            presence_confidence=d.get("presence_confidence", 0.0),
            centrality=d.get("centrality", 0.0),
        )
        for d in data
    ]


def serialize_strategies(strategies: list[StrategyEvidence]) -> list[dict]:
    """Serialize strategy evidence to a JSON-serializable list."""
    return [
        {
            "strategy_id": s.strategy_id,
            "strategy_version": s.strategy_version,
            "supporting_technique_ids": s.supporting_technique_ids,
            "supporting_fact_ids": s.supporting_fact_ids,
            "confidence": s.confidence,
            "problem_context_signals": s.problem_context_signals,
        }
        for s in strategies
    ]


def deserialize_strategies(data: list[dict]) -> list[StrategyEvidence]:
    """Deserialize a JSON list back to StrategyEvidence objects."""
    return [
        StrategyEvidence(
            strategy_id=d.get("strategy_id", ""),
            strategy_version=d.get("strategy_version", "1.0.0"),
            supporting_technique_ids=d.get("supporting_technique_ids", []),
            supporting_fact_ids=d.get("supporting_fact_ids", []),
            confidence=d.get("confidence", 0.0),
            problem_context_signals=d.get("problem_context_signals", {}),
        )
        for d in data
    ]


def serialize_match_outcome(outcome: MatchOutcome) -> dict:
    """Serialize a MatchOutcome to a JSON-serializable dict."""
    return {
        "outcome": outcome.outcome,
        "satisfied_group_ids": outcome.satisfied_group_ids,
        "authority_tier": outcome.authority_tier,
        "primary_strategy": outcome.primary_strategy,
        "reasoning": outcome.reasoning,
        "technique_count": len(outcome.technique_evidence),
        "strategy_count": len(outcome.strategy_evidence),
        "fact_count": len(outcome.structural_facts),
    }


def deserialize_match_outcome(
    data: dict,
    technique_evidence: list[TechniqueEvidence],
    strategy_evidence: list[StrategyEvidence],
    structural_facts: list[StructuralFact],
) -> MatchOutcome:
    """Deserialize a JSON dict back to a MatchOutcome object."""
    return MatchOutcome(
        outcome=data.get("outcome", "UNRESOLVED"),
        satisfied_group_ids=data.get("satisfied_group_ids", []),
        authority_tier=data.get("authority_tier", "unknown"),
        technique_evidence=technique_evidence,
        strategy_evidence=strategy_evidence,
        structural_facts=structural_facts,
        primary_strategy=data.get("primary_strategy"),
        reasoning=data.get("reasoning", []),
    )


def compute_code_hash(code: str) -> str:
    """Compute a SHA-256 hash of the source code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# ============================================================
# Persistence operations
# ============================================================

def persist_shadow_analysis(
    conn,
    submission_id: int,
    code_hash: str,
    shadow_result: dict,
) -> bool:
    """Persist shadow analysis results to the submissions table.

    Args:
        conn: Database connection (PgConnection)
        submission_id: The submission ID to update
        code_hash: SHA-256 hash of the source code
        shadow_result: Output from run_shadow_analysis()

    Returns:
        True if persistence succeeded, False otherwise.
    """
    if shadow_result is None:
        return False

    try:
        conn.execute(
            """
            UPDATE submissions SET
                structural_facts_json = %s,
                shadow_extractor_version = %s,
                technique_evidence_json = %s,
                strategy_evidence_json = %s,
                shadow_match_outcome_json = %s,
                shadow_technique_def_version = %s,
                shadow_strategy_def_version = %s
            WHERE id = %s
            """,
            (
                json.dumps(shadow_result.get("structural_facts", [])),
                shadow_result.get("extractor_version", EXTRACTOR_VERSION),
                json.dumps(shadow_result.get("technique_evidence", [])),
                json.dumps(shadow_result.get("strategy_evidence", [])),
                json.dumps(shadow_result.get("match_outcome", {})),
                "1.0.0",  # technique definition version
                "1.0.0",  # strategy definition version
                submission_id,
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to persist shadow analysis: %s", e)
        conn.rollback()
        return False


def load_shadow_facts(conn, submission_id: int) -> Optional[list[StructuralFact]]:
    """Load structural facts from the submissions table.

    Args:
        conn: Database connection (PgConnection)
        submission_id: The submission ID to load from

    Returns:
        List of StructuralFact objects, or None if not found.
    """
    try:
        conn.execute(
            "SELECT structural_facts_json FROM submissions WHERE id = %s",
            (submission_id,),
        )
        row = conn.fetchone()
        if not row or not row.get("structural_facts_json"):
            return None
        return deserialize_facts(row["structural_facts_json"])
    except Exception as e:
        logger.error("Failed to load shadow facts: %s", e)
        return None


def load_shadow_techniques(conn, submission_id: int) -> Optional[list[TechniqueEvidence]]:
    """Load technique evidence from the submissions table."""
    try:
        conn.execute(
            "SELECT technique_evidence_json FROM submissions WHERE id = %s",
            (submission_id,),
        )
        row = conn.fetchone()
        if not row or not row.get("technique_evidence_json"):
            return None
        return deserialize_techniques(row["technique_evidence_json"])
    except Exception as e:
        logger.error("Failed to load shadow techniques: %s", e)
        return None


def load_shadow_strategies(conn, submission_id: int) -> Optional[list[StrategyEvidence]]:
    """Load strategy evidence from the submissions table."""
    try:
        conn.execute(
            "SELECT strategy_evidence_json FROM submissions WHERE id = %s",
            (submission_id,),
        )
        row = conn.fetchone()
        if not row or not row.get("strategy_evidence_json"):
            return None
        return deserialize_strategies(row["strategy_evidence_json"])
    except Exception as e:
        logger.error("Failed to load shadow strategies: %s", e)
        return None


def load_shadow_outcome(conn, submission_id: int) -> Optional[dict]:
    """Load shadow match outcome from the submissions table."""
    try:
        conn.execute(
            "SELECT shadow_match_outcome_json FROM submissions WHERE id = %s",
            (submission_id,),
        )
        row = conn.fetchone()
        if not row or not row.get("shadow_match_outcome_json"):
            return None
        return row["shadow_match_outcome_json"]
    except Exception as e:
        logger.error("Failed to load shadow outcome: %s", e)
        return None


# ============================================================
# Re-derivation
# ============================================================

def rerun_derivation(
    facts: list[StructuralFact],
    solution_groups: Optional[list] = None,
) -> dict:
    """Re-derive technique/strategy evidence from stored structural facts.

    This is the critical re-derivation function. It takes persisted
    structural facts (the canonical artifact) and re-runs the technique
    and strategy derivation pipeline.

    Args:
        facts: Structural facts loaded from the database
        solution_groups: Optional solution groups for matching

    Returns:
        Dict with technique_evidence, strategy_evidence, match_outcome.
    """
    # Re-run technique detection from facts
    technique_evidence = detect_techniques(facts)

    # Re-run strategy evaluation from techniques + facts
    strategy_evidence = evaluate_strategies(technique_evidence, facts)

    # Re-run matching if solution groups provided
    if solution_groups:
        match_outcome = evaluate_solution_groups(
            solution_groups, technique_evidence, strategy_evidence, facts
        )
    else:
        match_outcome = MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="unknown",
            technique_evidence=technique_evidence,
            strategy_evidence=strategy_evidence,
            structural_facts=facts,
            reasoning=["No solution groups provided for re-derivation"],
        )

    return {
        "structural_facts": serialize_facts(facts),
        "technique_evidence": serialize_techniques(technique_evidence),
        "strategy_evidence": serialize_strategies(strategy_evidence),
        "match_outcome": serialize_match_outcome(match_outcome),
    }
