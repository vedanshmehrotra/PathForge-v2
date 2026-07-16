"""Elo System — long-term skill memory layer for PathForge.

Converts Gap Signals, Matching Engine results, and AST output into
continuous per-pattern skill ratings with anti-drift protection.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

INITIAL_ELO = 1200.0
MIN_ELO = 400.0
BASELINE_OPPONENT = 1200.0

DEFAULT_K = 32
K_GAP_BOOST = 16
K_STABILITY_REDUCTION = 8
K_MIN = 8
K_MAX = 64

SCORE_FULL_MATCH = 1.0
SCORE_PARTIAL_MATCH = 0.5
SCORE_NO_MATCH = 0.0

REPEATED_SUCCESS_WINDOW = 5
REPEATED_SUCCESS_SCORE_DECAY = 0.1
REPEATED_FAILURE_SATURATION = 0.15


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _expected_score(elo: float, opponent: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((opponent - elo) / 400.0))


def match_result_to_score(match_result: str) -> float:
    if match_result == "FULL_MATCH":
        return SCORE_FULL_MATCH
    if match_result == "PARTIAL_MATCH":
        return SCORE_PARTIAL_MATCH
    return SCORE_NO_MATCH


def _compute_k(elo: float, gap_strength: float, recent_history_length: int) -> int:
    k = DEFAULT_K
    if gap_strength > 0.5:
        k += K_GAP_BOOST
    if recent_history_length >= 3:
        k = max(k - K_STABILITY_REDUCTION, K_MIN)
    return min(k, K_MAX)


def _anti_drift_adjustment(
    match_result: str,
    pattern_history: List[Dict[str, Any]],
) -> float:
    if not pattern_history:
        return 1.0
    recent = pattern_history[-REPEATED_SUCCESS_WINDOW:]
    if match_result == "FULL_MATCH":
        full_count = sum(
            1 for h in recent if h.get("match_result") == "FULL_MATCH"
        )
        if full_count >= 3:
            decay = (full_count - 2) * REPEATED_SUCCESS_SCORE_DECAY
            return max(1.0 - decay, 0.5)
    elif match_result == "NO_MATCH":
        no_match_count = sum(
            1 for h in recent if h.get("match_result") == "NO_MATCH"
        )
        if no_match_count >= 3:
            saturation = (no_match_count - 2) * REPEATED_FAILURE_SATURATION
            return max(1.0 - saturation, 0.3)
    return 1.0


class EloEngine:
    def compute_updates(
        self,
        user_id: str,
        gap_signals: List[Dict[str, Any]],
        match_result: Dict[str, Any],
        ast_output: Optional[List[Dict[str, Any]]] = None,
        current_elos: Optional[Dict[str, float]] = None,
        pattern_histories: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        match_result_str = match_result.get("match_result", "NO_MATCH")
        base_score = match_result_to_score(match_result_str)
        matched_groups = match_result.get("matched_groups", [])
        unmatched_patterns = match_result.get("unmatched_patterns", [])

        gap_map: Dict[str, float] = {}
        for gs in gap_signals:
            gap_map[gs["pattern_id"]] = gs.get("gap_strength", 0.0)

        ast_map: Dict[str, float] = {}
        for entry in ast_output or []:
            pid = entry.get("pattern_id", "")
            conf = entry.get("confidence", 0.0)
            if pid:
                ast_map[pid] = conf

        candidate_patterns = self._resolve_candidate_patterns(
            base_score, match_result_str, gap_map, ast_map,
            matched_groups, unmatched_patterns,
        )

        histories = pattern_histories or {}
        elos = dict(current_elos) if current_elos else {}

        updates = []
        total_delta = 0.0
        for pattern_id in candidate_patterns:
            old_elo = elos.get(pattern_id, INITIAL_ELO)
            gap_strength = gap_map.get(pattern_id, 0.0)
            score = self._resolve_score(
                pattern_id, base_score, match_result_str, gap_strength, ast_map,
            )
            pattern_history = histories.get(pattern_id, [])
            k = _compute_k(old_elo, gap_strength, len(pattern_history))
            drift_factor = _anti_drift_adjustment(match_result_str, pattern_history)
            adjusted_score = score * drift_factor

            opponent = self._resolve_opponent(pattern_id, ast_map)
            expected = _expected_score(old_elo, opponent)
            delta = k * (adjusted_score - expected)
            new_elo = round(max(MIN_ELO, old_elo + delta), 2)
            delta_rounded = round(new_elo - old_elo, 2)

            confidence_weight = self._compute_confidence_weight(
                match_result_str, gap_strength, ast_map.get(pattern_id, 0.0),
            )

            updates.append({
                "pattern_id": pattern_id,
                "old_elo": round(old_elo, 2),
                "new_elo": new_elo,
                "delta": delta_rounded,
                "confidence_weight": round(confidence_weight, 4),
            })
            total_delta += delta_rounded

            elos[pattern_id] = new_elo

        sorted_updates = sorted(updates, key=lambda u: u["delta"], reverse=True)
        avg_change = round(total_delta / max(len(updates), 1), 2)
        strongest = [u["pattern_id"] for u in sorted_updates[:3] if u["delta"] > 0]
        weakest = [u["pattern_id"] for u in reversed(sorted_updates[-3:]) if u["delta"] < 0]

        return {
            "user_id": user_id,
            "pattern_elo_updates": updates,
            "global_summary": {
                "average_elo_change": avg_change,
                "strongest_improvement_patterns": strongest,
                "weakest_patterns": weakest,
            },
        }

    def _resolve_candidate_patterns(
        self,
        base_score: float,
        match_result_str: str,
        gap_map: Dict[str, float],
        ast_map: Dict[str, float],
        matched_groups: List[int],
        unmatched_patterns: List[str],
    ) -> List[str]:
        patterns: List[str] = []

        patterns.extend(list(gap_map.keys()))
        patterns.extend(list(ast_map.keys()))
        patterns.extend(unmatched_patterns)

        seen: Dict[str, bool] = {}
        unique = []
        for p in patterns:
            if p and p not in seen:
                seen[p] = True
                unique.append(p)
        return unique if unique else ["default"]

    def _resolve_score(
        self,
        pattern_id: str,
        base_score: float,
        match_result_str: str,
        gap_strength: float,
        ast_map: Dict[str, float],
    ) -> float:
        score = base_score
        if gap_strength > 0.6:
            score = max(0.0, score - 0.3)
        elif gap_strength > 0.3:
            score = max(0.0, score - 0.15)

        ast_conf = ast_map.get(pattern_id, 0.0)
        if ast_conf > 0.0 and base_score < SCORE_PARTIAL_MATCH:
            score = max(score, 0.2)
        return score

    def _resolve_opponent(
        self,
        pattern_id: str,
        ast_map: Dict[str, float],
    ) -> float:
        ast_conf = ast_map.get(pattern_id, 0.0)
        if ast_conf >= 0.8:
            return BASELINE_OPPONENT + 200.0
        return BASELINE_OPPONENT

    def _compute_confidence_weight(
        self,
        match_result_str: str,
        gap_strength: float,
        ast_confidence: float,
    ) -> float:
        if match_result_str == "NO_MATCH":
            base = 0.4
        elif match_result_str == "PARTIAL_MATCH":
            base = 0.7
        else:
            base = 1.0
        gap_penalty = gap_strength * 0.3
        ast_boost = ast_confidence * 0.2
        return max(0.1, min(1.0, base - gap_penalty + ast_boost))

    def persist_elos(
        self,
        connection: Any,
        user_id: int,
        elo_output: Dict[str, Any],
    ) -> None:
        now = iso_now()
        for update in elo_output.get("pattern_elo_updates", []):
            connection.execute(
                """
                INSERT INTO user_pattern_elo (user_id, pattern_id, elo, last_updated, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, pattern_id) DO UPDATE SET
                    elo = EXCLUDED.elo,
                    last_updated = EXCLUDED.last_updated,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    user_id,
                    update["pattern_id"],
                    update["new_elo"],
                    now,
                    now,
                    now,
                ),
            )
