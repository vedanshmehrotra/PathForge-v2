"""Recommendation Engine — decides what the user should solve next.

Takes user Elo, gap signals, submission history, and the problem bank
to produce ranked, diverse problem recommendations.
"""

import json
import math
from typing import List, Dict, Any, Optional, Set, Tuple

INITIAL_ELO = 1200.0
ELO_DEFICIT_MAX = 1200.0
WEAK_SCORE_GAP_WEIGHT = 0.5
WEAK_SCORE_ELO_WEIGHT = 0.5

NOVELTY_BONUS = 0.2
RECENCY_PENALTY = 0.3

DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]
DIFFICULTY_ELO_BOUNDS = [(0, 999), (1000, 1299), (1300, 9999)]

MAX_RECOMMENDATIONS = 5
MIN_DIVERSE_CATEGORIES = 2
REPEATED_PATTERN_PENALTY = 0.4

FOCUS_STRATEGIES = [
    "reinforce_weakest",
    "broaden_coverage",
    "balanced_maintenance",
    "cold_start_exploration",
]

CATEGORY_MAP = {
    "arrays": {
        "hash_map_lookup", "hash_map_frequency", "prefix_sum",
        "sliding_window_fixed", "sliding_window_variable",
        "two_pointers_opposite", "two_pointers_same",
    },
    "trees_graphs": {
        "dfs_recursive", "dfs_iterative", "bfs_level_order",
        "bfs_shortest_path", "topological_sort", "union_find",
        "binary_search_tree",
    },
    "dp": {
        "dp_1d_forward", "dp_1d_sequence", "dp_2d_grid",
        "dp_2d_string", "dp_knapsack", "dp_interval",
        "dp_state_machine",
    },
    "linked_lists": {
        "fast_slow_pointers", "linked_list_reversal",
        "monotonic_stack", "monotonic_deque",
    },
    "binary_search": {
        "binary_search_standard", "binary_search_rotated",
        "binary_search_answer",
    },
    "greedy_backtracking": {
        "heap_top_k", "greedy_local", "greedy_interval",
        "backtracking_permutation", "backtracking_subset",
    },
}

PATTERN_TO_CATEGORY: Dict[str, str] = {}
for cat, patterns in CATEGORY_MAP.items():
    for p in patterns:
        PATTERN_TO_CATEGORY[p] = cat


def _elo_deficit(elo: float) -> float:
    return max(0.0, (ELO_DEFICIT_MAX - elo) / ELO_DEFICIT_MAX)


def _weak_score(gap_strength: float, elo: float) -> float:
    return (gap_strength * WEAK_SCORE_GAP_WEIGHT) + (_elo_deficit(elo) * WEAK_SCORE_ELO_WEIGHT)


def _difficulty_for_elo(elo: float) -> str:
    if elo < 1000:
        return "Easy"
    if elo <= 1300:
        return "Medium"
    return "Hard"


def _expected_learning_gain(weak_score: float, is_unsolved: bool) -> float:
    base = weak_score * 0.7
    if is_unsolved:
        base += 0.2
    return round(min(base, 1.0), 4)


def _parse_patterns(problem: Dict[str, Any]) -> List[str]:
    raw = problem.get("pattern", "[]")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, list):
        return raw
    return []


def _category_diversity_bonus(
    pattern: str,
    selected_categories: Set[str],
) -> float:
    cat = PATTERN_TO_CATEGORY.get(pattern)
    if cat and cat not in selected_categories:
        return 0.15
    return 0.0


class RecommendationEngine:
    def __init__(self, problem_bank: List[Dict[str, Any]]):
        self._problems = problem_bank
        self._build_index()

    def _build_index(self) -> None:
        self._by_pattern: Dict[str, List[Dict[str, Any]]] = {}
        for prob in self._problems:
            patterns = _parse_patterns(prob)
            for p in patterns:
                self._by_pattern.setdefault(p, []).append(prob)

    def recommend(
        self,
        user_id: str,
        user_pattern_elo: Optional[Dict[str, float]] = None,
        gap_signals: Optional[List[Dict[str, Any]]] = None,
        recent_submissions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        elos = user_pattern_elo or {}
        gaps_list = gap_signals or []
        subs = recent_submissions or []

        gap_map: Dict[str, float] = {}
        for gs in gaps_list:
            gap_map[gs["pattern_id"]] = gs.get("gap_strength", 0.0)

        solved_patterns, recent_patterns = self._analyze_submissions(subs)

        weak_patterns = self._compute_weak_patterns(elos, gap_map, solved_patterns)
        if not weak_patterns:
            weak_patterns = self._cold_start_fallback(elos, gap_map)

        recency_set = set(recent_patterns)

        strategy = self._determine_strategy(weak_patterns, elos, gap_map, len(subs))

        recommendations: List[Dict[str, Any]] = []
        selected_categories: Set[str] = set()
        selected_patterns: List[str] = []

        for pattern_id, wscore in weak_patterns:
            if len(recommendations) >= MAX_RECOMMENDATIONS:
                break

            category = PATTERN_TO_CATEGORY.get(pattern_id)

            novelty = NOVELTY_BONUS if pattern_id not in recency_set else 0.0
            diversity_bonus = _category_diversity_bonus(pattern_id, selected_categories)
            recency_penalty = RECENCY_PENALTY if pattern_id in recency_set else 0.0

            priority = wscore + novelty + diversity_bonus - recency_penalty

            problem = self._select_best_problem(
                pattern_id, solved_patterns, subs, priority,
            )
            if not problem:
                continue

            is_unsolved = problem["id"] not in {s.get("problem_id") for s in subs if s.get("verdict") == "pass"}

            difficulty = _difficulty_for_elo(elos.get(pattern_id, INITIAL_ELO))
            learning_gain = _expected_learning_gain(wscore, is_unsolved)
            reason = self._build_reason(pattern_id, wscore, category, is_unsolved)

            recommendations.append({
                "problem_id": str(problem["id"]),
                "target_patterns": _parse_patterns(problem),
                "reason": reason,
                "difficulty_score": DIFFICULTY_ORDER.index(difficulty) / max(len(DIFFICULTY_ORDER) - 1, 1),
                "expected_learning_gain": learning_gain,
            })
            selected_categories.add(category or "")
            selected_patterns.append(pattern_id)

        if len(selected_categories) < MIN_DIVERSE_CATEGORIES:
            recommendations = self._enforce_diversity(
                recommendations, selected_categories, weak_patterns,
                solved_patterns, subs, recency_set,
            )

        primary_weak = [wp[0] for wp in weak_patterns[:3]]
        focus_area = self._resolve_focus_area(strategy, primary_weak)

        return {
            "user_id": user_id,
            "recommended_problems": recommendations[:MAX_RECOMMENDATIONS],
            "summary": {
                "primary_weak_patterns": primary_weak,
                "focus_area": focus_area,
                "recommendation_strategy": strategy,
            },
        }

    def _analyze_submissions(
        self,
        submissions: List[Dict[str, Any]],
    ) -> Tuple[Set[str], List[str]]:
        solved: Set[str] = set()
        recent_patterns: List[str] = []
        for sub in submissions:
            pattern = sub.get("detected_pattern") or sub.get("pattern_id") or sub.get("topic", "")
            if pattern:
                recent_patterns.append(pattern)
                if sub.get("verdict") == "pass":
                    solved.add(pattern)
        return solved, recent_patterns

    def _compute_weak_patterns(
        self,
        elos: Dict[str, float],
        gap_map: Dict[str, float],
        solved_patterns: Set[str],
    ) -> List[Tuple[str, float]]:
        all_patterns: Set[str] = set()
        all_patterns.update(elos.keys())
        all_patterns.update(gap_map.keys())
        all_patterns.update(self._by_pattern.keys())

        scored: List[Tuple[str, float]] = []
        for pattern in all_patterns:
            elo = elos.get(pattern, INITIAL_ELO)
            gap = gap_map.get(pattern, 0.0)
            ws = _weak_score(gap, elo)

            if pattern in solved_patterns:
                ws *= 0.5

            has_problem = pattern in self._by_pattern
            if not has_problem:
                continue

            scored.append((pattern, ws))

        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored

    def _cold_start_fallback(
        self,
        elos: Dict[str, float],
        gap_map: Dict[str, float],
    ) -> List[Tuple[str, float]]:
        scored: List[Tuple[str, float]] = []
        for pattern in sorted(self._by_pattern.keys()):
            elo = elos.get(pattern, INITIAL_ELO)
            gap = gap_map.get(pattern, 0.0)
            ws = _weak_score(gap, elo)
            scored.append((pattern, ws))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored[:10] if scored else []

    def _select_best_problem(
        self,
        pattern_id: str,
        solved_patterns: Set[str],
        submissions: List[Dict[str, Any]],
        priority: float,
    ) -> Optional[Dict[str, Any]]:
        candidates = self._by_pattern.get(pattern_id, [])
        if not candidates:
            return None

        solved_ids = {
            s.get("problem_id") for s in submissions
            if s.get("verdict") == "pass" and s.get("problem_id")
        }

        unsolved = [p for p in candidates if p["id"] not in solved_ids]
        if unsolved:
            unsolved.sort(key=lambda x: -(x.get("acceptance_rate") or 0.0))
            return unsolved[0]

        candidates.sort(key=lambda x: -(x.get("acceptance_rate") or 0.0))
        return candidates[0]

    def _build_reason(
        self,
        pattern_id: str,
        weak_score: float,
        category: Optional[str],
        is_unsolved: bool,
    ) -> str:
        label = pattern_id.replace("_", " ")
        if weak_score >= 0.7:
            return f"Significant weakness detected in {label}. High priority for improvement."
        if weak_score >= 0.4:
            return f"Moderate gap identified in {label}. Regular practice recommended."
        if is_unsolved:
            return f"Unfamiliar territory: {label}. Start building foundational skills."
        return f"Balanced practice opportunity in {label}."

    def _determine_strategy(
        self,
        weak_patterns: List[Tuple[str, float]],
        elos: Dict[str, float],
        gap_map: Dict[str, float],
        total_submissions: int,
    ) -> str:
        if total_submissions == 0:
            return "cold_start_exploration"
        high_gaps = sum(1 for _, ws in weak_patterns if ws >= 0.7)
        if high_gaps >= 2:
            return "reinforce_weakest"
        moderate = sum(1 for _, ws in weak_patterns if ws >= 0.4)
        if moderate >= 3:
            return "reinforce_weakest"
        all_solved = all(
            elos.get(p, INITIAL_ELO) >= INITIAL_ELO for p, _ in weak_patterns[:5]
        )
        if all_solved:
            return "broaden_coverage"
        return "balanced_maintenance"

    def _resolve_focus_area(
        self,
        strategy: str,
        primary_weak: List[str],
    ) -> str:
        if strategy == "cold_start_exploration":
            return "Exploration — building initial skill profile"
        if not primary_weak:
            return "Maintenance — all patterns at adequate level"
        areas = []
        seen_cats: Set[str] = set()
        for p in primary_weak:
            cat = PATTERN_TO_CATEGORY.get(p, "general")
            if cat not in seen_cats:
                seen_cats.add(cat)
                areas.append(cat.replace("_", " ").title())
        if areas:
            return f"Focus on {', '.join(areas[:2])}"
        return "General algorithmic improvement"

    def _enforce_diversity(
        self,
        recommendations: List[Dict[str, Any]],
        selected_categories: Set[str],
        weak_patterns: List[Tuple[str, float]],
        solved_patterns: Set[str],
        submissions: List[Dict[str, Any]],
        recency_set: List[str],
    ) -> List[Dict[str, Any]]:
        if len(selected_categories) >= MIN_DIVERSE_CATEGORIES:
            return recommendations
        for pattern_id, wscore in weak_patterns:
            if len(recommendations) >= MAX_RECOMMENDATIONS:
                break
            cat = PATTERN_TO_CATEGORY.get(pattern_id, "")
            if cat in selected_categories:
                continue
            problem = self._select_best_problem(
                pattern_id, solved_patterns, submissions, wscore,
            )
            if not problem:
                continue
            is_unsolved = problem["id"] not in {s.get("problem_id") for s in submissions if s.get("verdict") == "pass"}
            difficulty = _difficulty_for_elo(INITIAL_ELO)
            learning_gain = _expected_learning_gain(wscore, is_unsolved)
            reason = self._build_reason(pattern_id, wscore, cat, is_unsolved)
            recommendations.append({
                "problem_id": str(problem["id"]),
                "target_patterns": _parse_patterns(problem),
                "reason": reason,
                "difficulty_score": DIFFICULTY_ORDER.index(difficulty) / max(len(DIFFICULTY_ORDER) - 1, 1),
                "expected_learning_gain": learning_gain,
            })
            selected_categories.add(cat)
        return recommendations
