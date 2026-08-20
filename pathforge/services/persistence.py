"""Persistence pipeline — persists analysis results after a successful /analyze.

Reuses existing engines (GapSignalEngine, EloEngine) and helpers
(submission_handler, profile_manager, recommender, pipeline helpers).
Does NOT call GraphQL or the LLM.
"""

import hashlib
import json
from typing import Any, Optional

from pathforge.db.profile_manager import iso_now, update_topic_profile
from pathforge.elo_engine import EVIDENCE_K_CEILINGS
from pathforge.submission_handler import _next_attempt_number, _update_user_streak
from pathforge.gap_signal_engine import GapSignalEngine
from pathforge.elo_engine import EloEngine
from pathforge.recommender import get_recommendation
from pathforge.pipeline import _log_recommendation, _mark_last_recommendation_acted_on
from pathforge.api.services.loader import load_submissions, load_user_pattern_elo

# Evidence states that grant authority (authoritative downstream behavior)
_AUTHORITATIVE_STATES = {"structurally_observed", "externally_listed"}


_gap_engine = GapSignalEngine()
_elo_engine = EloEngine()


def run_persistence(
    connection: Any,
    user_id: int,
    problem_id: Optional[int],
    problem_difficulty: Optional[str],
    code: str,
    ast_output: dict,
    match_result: dict,
    groups: Optional[list],
) -> dict:
    """Persist analysis results: submission, gap signals, Elo, streak, recommendation.

    Must be called inside an active transaction. The caller (analyze route) is
    responsible for connection.commit() on success and connection.rollback() on failure.
    """
    timestamp = iso_now()

    detected_patterns = ast_output.get("detected_patterns", [])
    match_result_str = match_result.get("match_result", "NO_MATCH")

    primary_pattern = ""
    primary_confidence = 0.0
    for dp in detected_patterns:
        conf = dp.get("confidence", 0.0)
        if conf > primary_confidence:
            primary_confidence = conf
            primary_pattern = dp.get("pattern_id", "")

    verdict = "pass" if match_result_str in ("FULL_MATCH", "PARTIAL_MATCH") else "fail"

    # --- Phase 0A: extract expected_pattern from the MATCHED group, not group_0 ---
    matched_groups_indices = match_result.get("matched_groups", [])
    expected_pattern = ""
    matched_group_evidence = "unobserved"
    if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
        idx = matched_groups_indices[0]
        if isinstance(idx, int) and 0 <= idx < len(groups):
            matched_group = groups[idx]
            if isinstance(matched_group, dict):
                group_patterns = matched_group.get("patterns", [])
                if group_patterns:
                    expected_pattern = group_patterns[0]
                matched_group_evidence = matched_group.get("evidence", "unobserved")
    # Fallback: no matched group — use first non-empty group (backward compat)
    if not expected_pattern and groups:
        for g in groups:
            patterns = g.get("patterns", []) if isinstance(g, dict) else []
            if patterns:
                expected_pattern = patterns[0]
                matched_group_evidence = g.get("evidence", "unobserved") if isinstance(g, dict) else "unobserved"
                break

    # Phase 0B + Phase 2: derive verdict_type from matched group evidence
    verdict_type = "authoritative" if matched_group_evidence in _AUTHORITATIVE_STATES else "analysis_only"

    # Phase 0B: compute code hash from full code (not truncated)
    code_hash = hashlib.sha256((code or "").encode("utf-8")).hexdigest()

    # Phase 0B: store full AST detection output as JSON
    detected_patterns_json = json.dumps(detected_patterns) if detected_patterns else None

    unmatched = match_result.get("unmatched_patterns", [])
    gap_identified = len(unmatched) > 0
    confidence_score = match_result.get("confidence_score", 0.0)
    topic = primary_pattern or expected_pattern or "unknown"

    attempt_number = (
        _next_attempt_number(connection, user_id, problem_id)
        if problem_id is not None
        else 1
    )
    cursor = connection.execute(
        """
        INSERT INTO submissions (
            user_id, problem_id, code_text, verdict, detected_pattern,
            detected_confidence, expected_pattern, target_pattern, gap_identified,
            diagnosis_confidence, time_taken_seconds, attempt_number, topic, submitted_at,
            verdict_type, detected_patterns_json, code_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            user_id,
            problem_id,
            code[:1000] if code else "",
            verdict,
            primary_pattern,
            primary_confidence,
            expected_pattern,
            None,
            gap_identified,
            confidence_score,
            None,
            attempt_number,
            topic,
            timestamp,
            verdict_type,
            detected_patterns_json,
            code_hash,
        ),
    )
    submission_id = cursor.fetchone()["id"]

    # Phase 2: Evidence authority gating
    # If verdict_type is analysis_only, skip ALL downstream scoring systems.
    # The submission is stored (for future clustering) but does not affect user skill models.
    is_authoritative = verdict_type == "authoritative"

    profile_update = None
    gap_output = {"gap_signals": [], "summary": {"strong_gaps": [], "moderate_gaps": [], "weak_gaps": []}}
    elo_output = {"user_id": str(user_id), "pattern_elo_updates": [], "global_summary": {}}
    recommendation_id = None

    if is_authoritative:
        # Derive evidence ceiling for both ELO systems.
        # Unknown/unrecognized evidence states default to 0 (fail-closed).
        topic_evidence_ceiling = EVIDENCE_K_CEILINGS.get(matched_group_evidence, 0)

        # Authoritative path: update topic profiles, gap signals, ELO, recommendations
        if problem_difficulty is not None:
            profile_update = update_topic_profile(
                connection,
                user_id=user_id,
                topic=topic,
                difficulty=problem_difficulty,
                verdict=verdict,
                detected_pattern=primary_pattern,
                expected_pattern=expected_pattern or primary_pattern,
                attempted_at=timestamp,
                evidence_ceiling=topic_evidence_ceiling,
            )

        submission_history = load_submissions(connection, user_id)

        gap_output = _gap_engine.compute_signals(
            ast_output=detected_patterns,
            match_result=match_result,
            user_id=user_id,
            submission_history=submission_history,
        )
        _gap_engine.persist_signals(connection, user_id, gap_output)

        current_elos = load_user_pattern_elo(connection, user_id)
        elo_output = _elo_engine.compute_updates(
            user_id=str(user_id),
            gap_signals=gap_output.get("gap_signals", []),
            match_result=match_result,
            ast_output=detected_patterns,
            current_elos=current_elos,
            evidence_state=matched_group_evidence,
        )
        _elo_engine.persist_elos(connection, user_id, elo_output)

        record = connection.execute(
            "SELECT * FROM submissions WHERE id = %s", (submission_id,)
        ).fetchone()
        submission_record = dict(record)

        problem_record = None
        if problem_id is not None:
            row = connection.execute(
                "SELECT * FROM problems WHERE id = %s", (problem_id,)
            ).fetchone()
            if row:
                problem_record = dict(row)

        gap_info = {
            "gap_detected": bool(gap_identified),
            "gap_pattern": unmatched[0] if unmatched else None,
            "matched_pattern": primary_pattern or expected_pattern,
            "diagnosis_confidence": confidence_score,
        }
        submission_result = {
            "submission": submission_record,
            "gap_info": gap_info,
        }

        _mark_last_recommendation_acted_on(connection, user_id)
        recommendation = get_recommendation(
            user_id, submission_result, problem_record, connection
        )
        recommendation_id = _log_recommendation(connection, user_id, recommendation)

    # Streak is always updated (independent of evidence authority)
    _update_user_streak(connection, user_id, timestamp)

    return {
        "submission_id": submission_id,
        "verdict_type": verdict_type,
        "profile_update": profile_update,
        "gap_signals_count": len(gap_output.get("gap_signals", [])),
        "gap_output": gap_output,
        "elo_updates_count": len(elo_output.get("pattern_elo_updates", [])),
        "elo_output": elo_output,
        "recommendation_id": recommendation_id,
    }
