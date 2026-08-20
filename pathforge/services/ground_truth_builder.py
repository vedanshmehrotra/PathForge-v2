import json

from pathforge.ast_engine.patterns import ALL_PATTERNS
from pathforge.db.profile_manager import iso_now
from pathforge.llm.openrouter_client import call_llm


class GroundTruthError(Exception):
    """Raised when ground truth generation fails (LLM unavailable, bad response, etc.)."""


def build_ground_truth(problem_id: int, problem_description: str, connection) -> list[str]:
    raw = call_llm(problem_description)

    if raw is None:
        raise GroundTruthError(
            "Ground truth generation failed: OpenRouter/LLM unavailable or returned no valid output"
        )

    patterns = raw.get("patterns", [])
    confidence = raw.get("confidence", {})

    canonical, filtered_confidence = _normalize_patterns(patterns, confidence)

    _store_ground_truth(connection, problem_id, canonical, filtered_confidence)

    return canonical


def _normalize_patterns(
    patterns: list,
    confidence: dict,
) -> tuple[list[str], dict]:
    canonical_set = {p.lower().replace("-", "_").replace(" ", "_") for p in patterns}

    canonical = []
    filtered_confidence = {}
    for p in canonical_set:
        if p in ALL_PATTERNS:
            canonical.append(p)
            if p in confidence:
                filtered_confidence[p] = _clamp_confidence(confidence[p])
            elif any(k.replace("-", "_").replace(" ", "_") == p for k in confidence):
                key = next(k for k in confidence if k.replace("-", "_").replace(" ", "_") == p)
                filtered_confidence[p] = _clamp_confidence(confidence[key])

    return canonical, filtered_confidence


def _clamp_confidence(value) -> float:
    try:
        v = float(value)
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return 0.5


def _store_ground_truth(connection, problem_id: int, patterns: list[str], confidence: dict):
    """Store ground truth with both legacy flat columns and new solution_groups."""
    now = iso_now()
    patterns_json = json.dumps(patterns)
    confidence_json = json.dumps(confidence) if confidence else "{}"

    # Phase 0C: also store as structured solution_groups with evidence state
    solution_groups = [
        {
            "id": "group_0",
            "patterns": patterns,
            "evidence": "llm_proposed",
            "confidence": {p: confidence.get(p, 0.5) for p in patterns},
        }
    ]
    solution_groups_json = json.dumps(solution_groups)

    connection.execute(
        """
        INSERT INTO problem_ground_truth (problem_id, patterns, confidence, solution_groups, validation_status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'llm_proposed', COALESCE((SELECT created_at FROM problem_ground_truth WHERE problem_id = %s), %s), %s)
        ON CONFLICT(problem_id) DO UPDATE SET
            patterns = EXCLUDED.patterns,
            confidence = EXCLUDED.confidence,
            solution_groups = EXCLUDED.solution_groups,
            updated_at = EXCLUDED.updated_at
        """,
        (problem_id, patterns_json, confidence_json, solution_groups_json, problem_id, now, now),
    )
