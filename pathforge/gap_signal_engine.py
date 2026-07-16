"""Gap Signal Engine — first learning layer of PathForge.

Connects AST detections + Matching Engine results + user performance history
into structured learning signals identifying what patterns a user is missing.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

GAP_STRENGTH_MISS_FREQ_WEIGHT = 0.5
GAP_STRENGTH_RECENCY_WEIGHT = 0.3
GAP_STRENGTH_CONFIDENCE_PENALTY_WEIGHT = 0.2

STRONG_GAP_THRESHOLD = 0.7
MODERATE_GAP_THRESHOLD = 0.4
WEAK_GAP_THRESHOLD = 0.0

LOW_CONFIDENCE_THRESHOLD = 0.6
RECENT_WINDOW = 5

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_ts(ts: str) -> datetime:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return EPOCH


def _recency_weight(submission_timestamps: List[str]) -> float:
    if not submission_timestamps:
        return 0.0
    now = datetime.now(timezone.utc).replace(microsecond=0)
    recent = submission_timestamps[-RECENT_WINDOW:]
    if not recent:
        return 0.0
    weighted = 0.0
    total = len(recent)
    for i, ts in enumerate(recent):
        age_hours = (now - _parse_ts(ts)).total_seconds() / 3600.0
        decay = max(0.0, 1.0 - (age_hours / (24.0 * 30.0)))
        position_weight = (i + 1) / total
        weighted += decay * position_weight
    return min(weighted / max(len(recent), 1), 1.0)


def _confidence_penalty(confidence: float) -> float:
    if confidence >= LOW_CONFIDENCE_THRESHOLD:
        return 0.0
    return (LOW_CONFIDENCE_THRESHOLD - confidence) / LOW_CONFIDENCE_THRESHOLD


def _classify_gap_level(gap_strength: float) -> str:
    if gap_strength >= STRONG_GAP_THRESHOLD:
        return "strong_gaps"
    if gap_strength >= MODERATE_GAP_THRESHOLD:
        return "moderate_gaps"
    return "weak_gaps"


class GapSignalEngine:
    def compute_signals(
        self,
        ast_output: List[Dict[str, Any]],
        match_result: Dict[str, Any],
        user_id: Optional[int] = None,
        submission_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        ast_patterns = self._extract_ast_patterns(ast_output)
        missing_patterns = self._extract_missing_patterns(match_result, ast_patterns)
        weak_signals = self._detect_weak_signals(ast_output, submission_history)

        history_by_pattern = self._index_history_by_pattern(submission_history)

        all_candidate_patterns = set(missing_patterns)
        all_candidate_patterns.update(weak_signals.keys())

        for pid in list(all_candidate_patterns):
            if self._anti_bias_check(pid, history_by_pattern, match_result):
                all_candidate_patterns.discard(pid)

        gap_signals = []
        for pattern_id in sorted(all_candidate_patterns):
            freq = len(history_by_pattern.get(pattern_id, []))
            miss_frequency = min(freq / max(len(submission_history or []), 1), 1.0) if submission_history else 0.0

            timestamps = []
            for sub in history_by_pattern.get(pattern_id, []):
                ts = sub.get("submitted_at") or sub.get("timestamp", "")
                timestamps.append(ts)
            recency = _recency_weight(timestamps)

            penalty = weak_signals.get(pattern_id, 0.0)
            if not penalty and pattern_id in missing_patterns:
                from_match = match_result.get("unmatched_patterns", [])
                if pattern_id in from_match:
                    penalty = 0.5

            gap_strength = (
                miss_frequency * GAP_STRENGTH_MISS_FREQ_WEIGHT
                + recency * GAP_STRENGTH_RECENCY_WEIGHT
                + penalty * GAP_STRENGTH_CONFIDENCE_PENALTY_WEIGHT
            )
            gap_strength = round(min(max(gap_strength, 0.0), 1.0), 4)

            if gap_strength < 0.01:
                continue

            last_ts = timestamps[-1] if timestamps else iso_now()
            gap_signals.append({
                "pattern_id": pattern_id,
                "gap_strength": gap_strength,
                "frequency": freq,
                "recency_score": round(recency, 4),
                "confidence_penalty": round(penalty, 4),
            })

        strong = []
        moderate = []
        weak = []
        for gs in gap_signals:
            level = _classify_gap_level(gs["gap_strength"])
            if level == "strong_gaps":
                strong.append(gs["pattern_id"])
            elif level == "moderate_gaps":
                moderate.append(gs["pattern_id"])
            else:
                weak.append(gs["pattern_id"])

        return {
            "gap_signals": gap_signals,
            "summary": {
                "strong_gaps": strong,
                "moderate_gaps": moderate,
                "weak_gaps": weak,
            },
        }

    def _extract_ast_patterns(self, ast_output: List[Dict[str, Any]]) -> Dict[str, float]:
        result = {}
        for entry in ast_output or []:
            pid = entry.get("pattern_id", "")
            conf = entry.get("confidence", 0.0)
            if pid and conf > 0.0:
                existing = result.get(pid, 0.0)
                result[pid] = max(existing, conf)
        return result

    def _extract_missing_patterns(
        self, match_result: Dict[str, Any], ast_patterns: Dict[str, float]
    ) -> List[str]:
        raw = match_result.get("unmatched_patterns", [])
        if not raw:
            return []
        result = []
        for pid in raw:
            if pid not in ast_patterns:
                result.append(pid)
        return result

    def _detect_weak_signals(
        self,
        ast_output: List[Dict[str, Any]],
        submission_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        result: Dict[str, float] = {}

        seen = {}
        for entry in ast_output or []:
            pid = entry.get("pattern_id", "")
            conf = entry.get("confidence", 0.0)
            if not pid:
                continue
            if pid not in seen or conf > seen[pid]:
                seen[pid] = conf

        for pid, conf in seen.items():
            if conf < LOW_CONFIDENCE_THRESHOLD:
                result[pid] = _confidence_penalty(conf)

        if submission_history and len(submission_history) >= 2:
            history_by_pattern = self._index_history_by_pattern(submission_history)
            for pid, subs in history_by_pattern.items():
                if len(subs) < 2:
                    continue
                confs = []
                for s in subs:
                    dc = s.get("detected_confidence", s.get("confidence", 0.0))
                    if isinstance(dc, (int, float)):
                        confs.append(float(dc))
                if not confs:
                    continue
                mean_conf = sum(confs) / len(confs)
                variances = [(c - mean_conf) ** 2 for c in confs]
                std_dev = (sum(variances) / len(variances)) ** 0.5
                inconsistent = std_dev > 0.2
                if inconsistent and pid not in result:
                    result[pid] = max(result.get(pid, 0.0), 0.3)

        return result

    def _index_history_by_pattern(
        self, submission_history: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for sub in submission_history or []:
            pid = sub.get("detected_pattern") or sub.get("pattern_id")
            if not pid:
                continue
            result.setdefault(pid, []).append(sub)
        return result

    def _anti_bias_check(
        self,
        pattern_id: str,
        history_by_pattern: Dict[str, List[Dict[str, Any]]],
        match_result: Dict[str, Any],
    ) -> bool:
        if match_result.get("match_result") == "FULL_MATCH":
            return True
        subs = history_by_pattern.get(pattern_id, [])
        if not subs:
            return False
        recent = subs[-RECENT_WINDOW:]
        if not recent:
            return False
        high_conf = 0
        for s in recent:
            dc = s.get("detected_confidence", s.get("confidence", 0.0))
            if isinstance(dc, (int, float)) and float(dc) >= LOW_CONFIDENCE_THRESHOLD:
                high_conf += 1
        return high_conf == len(recent)

    def persist_signals(
        self,
        connection: Any,
        user_id: int,
        gap_output: Dict[str, Any],
    ) -> None:
        now = iso_now()
        for gs in gap_output.get("gap_signals", []):
            connection.execute(
                """
                INSERT INTO gap_signals (user_id, pattern_id, gap_strength, frequency, last_seen, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, pattern_id) DO UPDATE SET
                    gap_strength = EXCLUDED.gap_strength,
                    frequency = EXCLUDED.frequency,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    user_id,
                    gs["pattern_id"],
                    gs["gap_strength"],
                    gs["frequency"],
                    now,
                    now,
                    now,
                ),
            )
