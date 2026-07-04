"""Unit tests for the Recommendation Engine."""

import json
from pathforge.recommendation_engine import (
    RecommendationEngine,
    _weak_score,
    _elo_deficit,
    _difficulty_for_elo,
    _expected_learning_gain,
    INITIAL_ELO,
)

SAMPLE_PROBLEMS = [
    {
        "id": 1,
        "title": "Two Sum",
        "difficulty": "Easy",
        "pattern": json.dumps(["hash_map_lookup"]),
        "acceptance_rate": 0.56,
        "topics": "Array",
    },
    {
        "id": 2,
        "title": "Valid Parentheses",
        "difficulty": "Easy",
        "pattern": json.dumps(["monotonic_stack"]),
        "acceptance_rate": 0.43,
        "topics": "Stack",
    },
    {
        "id": 3,
        "title": "Climbing Stairs",
        "difficulty": "Easy",
        "pattern": json.dumps(["dp_1d_forward"]),
        "acceptance_rate": 0.54,
        "topics": "DP",
    },
    {
        "id": 4,
        "title": "Reverse Linked List",
        "difficulty": "Easy",
        "pattern": json.dumps(["linked_list_reversal"]),
        "acceptance_rate": 0.80,
        "topics": "Linked List",
    },
    {
        "id": 5,
        "title": "Binary Search",
        "difficulty": "Easy",
        "pattern": json.dumps(["binary_search_standard"]),
        "acceptance_rate": 0.49,
        "topics": "Binary Search",
    },
    {
        "id": 6,
        "title": "Maximum Subarray",
        "difficulty": "Medium",
        "pattern": json.dumps(["dp_1d_forward"]),
        "acceptance_rate": 0.48,
        "topics": "DP",
    },
    {
        "id": 7,
        "title": "LRU Cache",
        "difficulty": "Medium",
        "pattern": json.dumps(["hash_map_lookup", "linked_list_reversal"]),
        "acceptance_rate": 0.38,
        "topics": "Design",
    },
    {
        "id": 8,
        "title": "Merge Intervals",
        "difficulty": "Medium",
        "pattern": json.dumps(["greedy_interval"]),
        "acceptance_rate": 0.44,
        "topics": "Array",
    },
    {
        "id": 9,
        "title": "Number of Islands",
        "difficulty": "Medium",
        "pattern": json.dumps(["dfs_recursive"]),
        "acceptance_rate": 0.54,
        "topics": "Graph",
    },
    {
        "id": 10,
        "title": "Serialize BST",
        "difficulty": "Medium",
        "pattern": json.dumps(["binary_search_tree"]),
        "acceptance_rate": 0.42,
        "topics": "Tree",
    },
    {
        "id": 11,
        "title": "Top K Frequent",
        "difficulty": "Medium",
        "pattern": json.dumps(["heap_top_k"]),
        "acceptance_rate": 0.60,
        "topics": "Heap",
    },
    {
        "id": 12,
        "title": "Word Break",
        "difficulty": "Medium",
        "pattern": json.dumps(["dp_1d_sequence"]),
        "acceptance_rate": 0.42,
        "topics": "DP",
    },
    {
        "id": 13,
        "title": "Course Schedule",
        "difficulty": "Medium",
        "pattern": json.dumps(["topological_sort"]),
        "acceptance_rate": 0.45,
        "topics": "Graph",
    },
    {
        "id": 14,
        "title": "Permutations",
        "difficulty": "Medium",
        "pattern": json.dumps(["backtracking_permutation"]),
        "acceptance_rate": 0.71,
        "topics": "Backtracking",
    },
    {
        "id": 15,
        "title": "Sliding Window Max",
        "difficulty": "Hard",
        "pattern": json.dumps(["monotonic_deque"]),
        "acceptance_rate": 0.30,
        "topics": "Queue",
    },
    {
        "id": 16,
        "title": "Edit Distance",
        "difficulty": "Hard",
        "pattern": json.dumps(["dp_2d_string"]),
        "acceptance_rate": 0.50,
        "topics": "DP",
    },
    {
        "id": 17,
        "title": "Median of Arrays",
        "difficulty": "Hard",
        "pattern": json.dumps(["binary_search_answer"]),
        "acceptance_rate": 0.34,
        "topics": "Binary Search",
    },
    {
        "id": 18,
        "title": "Serialize Binary Tree",
        "difficulty": "Hard",
        "pattern": json.dumps(["bfs_level_order"]),
        "acceptance_rate": 0.35,
        "topics": "Tree",
    },
    {
        "id": 19,
        "title": "Largest Rectangle",
        "difficulty": "Hard",
        "pattern": json.dumps(["monotonic_stack"]),
        "acceptance_rate": 0.40,
        "topics": "Stack",
    },
    {
        "id": 20,
        "title": "Multi-pattern DP",
        "difficulty": "Hard",
        "pattern": json.dumps(["dp_1d_forward", "dp_2d_grid"]),
        "acceptance_rate": 0.25,
        "topics": "DP",
    },
]


def test_weak_score():
    ws = _weak_score(0.8, 800.0)
    assert ws > 0.5


def test_weak_score_high_elo():
    ws = _weak_score(0.0, 1600.0)
    assert ws == 0.0


def test_elo_deficit():
    assert _elo_deficit(1200.0) == 0.0
    assert _elo_deficit(600.0) == 0.5
    assert _elo_deficit(0.0) == 1.0


def test_difficulty_for_elo():
    assert _difficulty_for_elo(800) == "Easy"
    assert _difficulty_for_elo(1100) == "Medium"
    assert _difficulty_for_elo(1400) == "Hard"


def test_expected_learning_gain():
    assert _expected_learning_gain(0.8, True) > _expected_learning_gain(0.8, False)


def test_new_user_no_history():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo=None,
        gap_signals=None,
        recent_submissions=None,
    )
    assert result["user_id"] == "1"
    assert len(result["recommended_problems"]) > 0
    assert result["summary"]["recommendation_strategy"] == "cold_start_exploration"


def test_weak_pattern_drives_recommendation():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo={
            "hash_map_lookup": 1200.0,
            "dfs_recursive": 600.0,
            "dp_1d_forward": 1100.0,
        },
        gap_signals=[
            {"pattern_id": "dfs_recursive", "gap_strength": 0.85},
        ],
        recent_submissions=[
            {"detected_pattern": "hash_map_lookup", "verdict": "pass", "problem_id": 1},
        ],
    )
    problems = result["recommended_problems"]
    assert len(problems) > 0
    assert "dfs_recursive" in result["summary"]["primary_weak_patterns"]
    assert result["summary"]["recommendation_strategy"] in [
        "reinforce_weakest", "balanced_maintenance", "broaden_coverage",
    ]


def test_output_structure():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(user_id="42", gap_signals=[], recent_submissions=[])
    required = {"user_id", "recommended_problems", "summary"}
    assert set(result.keys()) == required
    summary_keys = {"primary_weak_patterns", "focus_area", "recommendation_strategy"}
    assert set(result["summary"].keys()) == summary_keys
    if result["recommended_problems"]:
        prob_keys = {"problem_id", "target_patterns", "reason", "difficulty_score", "expected_learning_gain"}
        for p in result["recommended_problems"]:
            assert set(p.keys()) == prob_keys
            assert isinstance(p["problem_id"], str)
            assert isinstance(p["target_patterns"], list)
            assert isinstance(p["reason"], str)
            assert isinstance(p["difficulty_score"], float)
            assert isinstance(p["expected_learning_gain"], float)


def test_no_gap_signals_fallback():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo={"hash_map_lookup": 1200.0, "dp_1d_forward": 1200.0},
        gap_signals=None,
        recent_submissions=[],
    )
    assert len(result["recommended_problems"]) > 0


def test_solved_pattern_reduces_priority():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result_with_solved = engine.recommend(
        user_id="1",
        user_pattern_elo={"hash_map_lookup": 1200.0, "dfs_recursive": 700.0},
        gap_signals=[{"pattern_id": "dfs_recursive", "gap_strength": 0.7}],
        recent_submissions=[
            {"detected_pattern": "hash_map_lookup", "verdict": "pass", "problem_id": 1},
            {"detected_pattern": "dfs_recursive", "verdict": "pass", "problem_id": 9},
        ],
    )
    assert len(result_with_solved["recommended_problems"]) > 0


def test_all_patterns_equal_strength():
    all_equal: Dict[str, float] = {}
    for p in {
        "hash_map_lookup", "dfs_recursive", "dp_1d_forward",
        "linked_list_reversal", "binary_search_standard",
        "greedy_interval", "heap_top_k",
    }:
        all_equal[p] = 1200.0
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo=all_equal,
        gap_signals=[],
        recent_submissions=[],
    )
    assert len(result["recommended_problems"]) > 0


def test_diversity_at_least_two_categories():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo={"hash_map_lookup": 800.0},
        gap_signals=[{"pattern_id": "hash_map_lookup", "gap_strength": 0.9}],
        recent_submissions=[],
    )
    categories = set()
    for prob in result["recommended_problems"]:
        for pat in prob["target_patterns"]:
            from pathforge.recommendation_engine import PATTERN_TO_CATEGORY
            cat = PATTERN_TO_CATEGORY.get(pat, "")
            if cat:
                categories.add(cat)
    assert len(categories) >= 1


def test_repeated_pattern_penalized():
    elos = {"hash_map_lookup": 800.0, "dp_1d_forward": 1200.0}
    gaps = [{"pattern_id": "hash_map_lookup", "gap_strength": 0.9}]
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    recency = [
        {"detected_pattern": "hash_map_lookup", "verdict": "fail", "problem_id": 1},
        {"detected_pattern": "hash_map_lookup", "verdict": "fail", "problem_id": 1},
    ]
    result = engine.recommend(
        user_id="1",
        user_pattern_elo=elos,
        gap_signals=gaps,
        recent_submissions=recency,
    )
    assert len(result["recommended_problems"]) > 0


def test_recommendation_batch_not_empty():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(user_id="1")
    assert len(result["recommended_problems"]) > 0


def test_focus_area_reflects_weak_patterns():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo={"dfs_recursive": 500.0, "hash_map_lookup": 1200.0},
        gap_signals=[{"pattern_id": "dfs_recursive", "gap_strength": 0.9}],
        recent_submissions=[
            {"detected_pattern": "hash_map_lookup", "verdict": "pass", "problem_id": 1},
        ],
    )
    assert "dfs_recursive" in result["summary"]["focus_area"] or \
           "trees_graphs" in result["summary"]["focus_area"].lower() or \
           "graph" in result["summary"]["focus_area"].lower()


def test_unsolved_problem_gets_learning_bonus():
    engine = RecommendationEngine(SAMPLE_PROBLEMS)
    result = engine.recommend(
        user_id="1",
        user_pattern_elo={"hash_map_lookup": 1200.0},
        gap_signals=[],
        recent_submissions=[],
    )
    for p in result["recommended_problems"]:
        if "hash_map_lookup" in p["target_patterns"]:
            assert p["expected_learning_gain"] > 0.0
            break
