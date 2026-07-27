"""Tests for the Matching Engine."""

import pytest
from src.matching_engine.matching_engine import MatchingEngine, MatchResult, MATCH_THRESHOLD


def make_ast_entry(pattern_id: str, confidence: float = 0.85):
    return {
        "pattern_id": pattern_id,
        "confidence": confidence,
        "evidence": [{"type": "test", "weight": 0.5}],
    }


class TestMatchingEngineInit:
    def test_engine_initializes(self):
        engine = MatchingEngine()
        assert engine is not None

    def test_match_threshold_defined(self):
        assert MATCH_THRESHOLD == 0.6


class TestNormalizeAST:
    def test_empty_ast(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([])
        assert result == {}

    def test_single_pattern(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([make_ast_entry("dp_1d_forward", 0.85)])
        assert result == {"dp_1d_forward": 0.85}

    def test_multiple_patterns(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([
            make_ast_entry("dp_1d_forward", 0.90),
            make_ast_entry("sliding_window_variable", 0.75),
        ])
        assert result == {"dp_1d_forward": 0.90, "sliding_window_variable": 0.75}

    def test_zero_confidence_excluded(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([make_ast_entry("dp_1d_forward", 0.0)])
        assert result == {}

    def test_duplicate_pattern_highest_confidence_wins(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([
            make_ast_entry("dp_1d_forward", 0.70),
            make_ast_entry("dp_1d_forward", 0.95),
        ])
        assert result == {"dp_1d_forward": 0.95}

    def test_empty_pattern_id_skipped(self):
        engine = MatchingEngine()
        result = engine._normalize_ast([
            {"pattern_id": "", "confidence": 0.8, "evidence": []},
        ])
        assert result == {}


class TestNormalizeLLM:
    def test_empty_llm(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({"accepted_solution_groups": []})
        assert result == []

    def test_single_group(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({
            "accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence"]]
        })
        assert result == [{"dp_1d_forward", "dp_1d_sequence"}]

    def test_multiple_groups(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({
            "accepted_solution_groups": [
                ["dp_1d_forward"],
                ["sliding_window_variable", "hash_map_lookup"],
            ]
        })
        assert len(result) == 2
        assert {"dp_1d_forward"} in result
        assert {"sliding_window_variable", "hash_map_lookup"} in result

    def test_empty_strings_skipped(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({
            "accepted_solution_groups": [["", "dp_1d_forward", "  "]],
        })
        assert result == [{"dp_1d_forward"}]

    def test_empty_group_skipped(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({
            "accepted_solution_groups": [[], ["dp_1d_forward"]],
        })
        assert result == [{"dp_1d_forward"}]

    def test_missing_key(self):
        engine = MatchingEngine()
        result = engine._normalize_llm({})
        assert result == []


class TestFullMatch:
    def test_single_group_full_match(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [0]
        assert result["confidence_score"] >= MATCH_THRESHOLD

    def test_multi_pattern_group_full_match(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "sliding_window_variable"]]},
            [
                make_ast_entry("dp_1d_forward", 0.90),
                make_ast_entry("sliding_window_variable", 0.80),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [0]

    def test_one_group_full_among_multiple(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [
                ["dp_1d_forward", "unknown_pattern"],
                ["two_pointers_opposite"],
            ]},
            [
                make_ast_entry("two_pointers_opposite", 0.85),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [1]

    def test_multiple_full_groups(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [
                ["dp_1d_forward"],
                ["sliding_window_variable"],
            ]},
            [
                make_ast_entry("dp_1d_forward", 0.90),
                make_ast_entry("sliding_window_variable", 0.80),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [0, 1]


class TestPartialMatch:
    def test_partial_group_overlap(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["match_result"] == "PARTIAL_MATCH"
        assert result["matched_groups"] == []

    def test_low_confidence_full_match_is_full_match(self):
        """When all expected patterns are matched, verdict is FULL_MATCH regardless of confidence.
        Confidence reflects AST detection reliability; verdict reflects coverage completeness."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.30)],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["confidence_score"] == 0.30

    def test_multiple_groups_some_partial(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [
                ["dp_1d_forward", "dp_1d_sequence"],
                ["hash_map_lookup"],
            ]},
            [
                make_ast_entry("dp_1d_forward", 0.85),
                make_ast_entry("hash_map_lookup", 0.90),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [1]


class TestNoMatch:
    def test_no_overlap(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("sliding_window_variable", 0.85)],
        )
        assert result["match_result"] == "NO_MATCH"
        assert result["matched_groups"] == []

    def test_empty_ast(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [],
        )
        assert result["match_result"] == "NO_MATCH"
        assert result["confidence_score"] == 0.0

    def test_empty_llm(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": []},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["match_result"] == "NO_MATCH"
        assert result["confidence_score"] == 0.0

    def test_both_empty(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": []},
            [],
        )
        assert result["match_result"] == "NO_MATCH"
        assert result["confidence_score"] == 0.0

    def test_llm_pattern_not_in_ast(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["nonexistent_pattern"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["match_result"] == "NO_MATCH"
        assert result["matched_groups"] == []


class TestConfidenceScore:
    def test_perfect_confidence(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 1.0)],
        )
        assert result["confidence_score"] == 1.0
        assert result["match_result"] == "FULL_MATCH"

    def test_confidence_reflects_ast_confidence(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.60)],
        )
        assert result["confidence_score"] == 0.60

    def test_extra_ast_patterns_no_penalty_when_full_match(self):
        """Auxiliary patterns should not penalize confidence when all expected patterns are matched."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [
                make_ast_entry("dp_1d_forward", 0.85),
                make_ast_entry("sorting", 0.80),
                make_ast_entry("prefix_sum", 0.60),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["confidence_score"] == 0.85

    def test_missing_llm_pattern_penalty(self):
        """When expected patterns are missing, extra AST patterns are still penalized."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence"]]},
            [make_ast_entry("dp_1d_forward", 0.90)],
        )
        assert result["match_result"] == "PARTIAL_MATCH"
        assert result["confidence_score"] < 0.90
        assert result["confidence_score"] > 0.0
        assert "dp_1d_sequence" in result["unmatched_patterns"]


class TestUnmatchedPatterns:
    def test_unmatched_listed(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "missing_pattern"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert "missing_pattern" in result["unmatched_patterns"]

    def test_no_unmatched_when_full(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["unmatched_patterns"] == []


class TestOutputStructure:
    def test_output_has_required_fields(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert "match_result" in result
        assert "matched_groups" in result
        assert "unmatched_patterns" in result
        assert "confidence_score" in result
        assert "reasoning_signals" in result

    def test_no_extra_fields(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        expected_keys = {"match_result", "matched_groups", "unmatched_patterns",
                          "confidence_score", "reasoning_signals"}
        assert set(result.keys()) == expected_keys

    def test_match_result_values(self):
        engine = MatchingEngine()
        r1 = engine.match({"accepted_solution_groups": [["dp_1d_forward"]]},
                           [make_ast_entry("dp_1d_forward", 0.85)])
        assert r1["match_result"] in ("FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH")

        r2 = engine.match({"accepted_solution_groups": [["unknown"]]},
                           [make_ast_entry("dp_1d_forward", 0.85)])
        assert r2["match_result"] in ("FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH")

        r3 = engine.match({"accepted_solution_groups": []}, [])
        assert r3["match_result"] in ("FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH")


class TestReasoningSignals:
    def test_signals_contain_match_result(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert any("match_result=FULL_MATCH" in s for s in result["reasoning_signals"])

    def test_signals_contain_confidence(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert any("confidence=" in s for s in result["reasoning_signals"])

    def test_signals_contain_coverage(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert any("llm_coverage=" in s for s in result["reasoning_signals"])


class TestEdgeCases:
    def test_overlapping_ast_detections(self):
        """Extra patterns don't penalize when all expected patterns are matched.
        Overlapping AST detections for the same pattern use the highest confidence."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [
                make_ast_entry("dp_1d_forward", 0.70),
                make_ast_entry("dp_1d_forward", 0.95),
                make_ast_entry("sliding_window_variable", 0.80),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        # No penalty — all expected patterns matched
        assert result["confidence_score"] == 0.95

    def test_multiple_ast_patterns_same_group(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence", "dp_2d_grid"]]},
            [
                make_ast_entry("dp_1d_forward", 0.90),
                make_ast_entry("dp_1d_sequence", 0.80),
                make_ast_entry("dp_2d_grid", 0.70),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["matched_groups"] == [0]

    def test_extra_llm_patterns_not_in_ast(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "nonexistent_a", "nonexistent_b"]]},
            [make_ast_entry("dp_1d_forward", 0.85)],
        )
        assert result["match_result"] == "PARTIAL_MATCH"
        assert "nonexistent_a" in result["unmatched_patterns"]
        assert "nonexistent_b" in result["unmatched_patterns"]

    def test_ast_has_more_patterns_than_llm(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [
                make_ast_entry("dp_1d_forward", 0.85),
                make_ast_entry("dp_1d_sequence", 0.75),
                make_ast_entry("two_pointers_opposite", 0.60),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["unmatched_patterns"] == []

    def test_confidence_at_exact_threshold(self):
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", MATCH_THRESHOLD)],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["confidence_score"] == MATCH_THRESHOLD


class TestRegressionNoAuxiliaryPenalty:
    """Regression tests: auxiliary patterns should not penalize when all expected patterns are matched."""

    def test_multiple_aux_patterns_no_penalty(self):
        """Sorting, hashing, and pointer patterns should not reduce confidence
        when the primary algorithmic pattern is also matched."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["two_pointers_opposite"]]},
            [
                make_ast_entry("two_pointers_opposite", 0.85),
                make_ast_entry("sorting", 0.80),
                make_ast_entry("hash_map_lookup", 0.65),
                make_ast_entry("brute_force", 0.30),
            ],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["confidence_score"] == 0.85
        assert result["unmatched_patterns"] == []

    def test_penalty_applied_when_expected_missing(self):
        """Extra patterns ARE penalized when some expected patterns are missing.
        This tests that the penalty logic still works for true partial matches."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence"]]},
            [
                make_ast_entry("dp_1d_forward", 0.80),
                make_ast_entry("sorting", 0.90),
                make_ast_entry("hash_map_lookup", 0.70),
            ],
        )
        # dp_1d_sequence is missing → PARTIAL_MATCH
        assert result["match_result"] == "PARTIAL_MATCH"
        # best_confidence = 0.80 / 2 = 0.40 (avg across group of size 2)
        # extra penalty = (0.90 + 0.70) * 0.1 = 0.16
        # final = 0.40 - 0.16 = 0.24
        assert result["confidence_score"] == pytest.approx(0.24, rel=1e-3)

    def test_low_confidence_still_full_match(self):
        """The original inconsistent scenario: 1 expected, 1 matched, 0 unmatched,
        but confidence < 0.6. Should now be FULL_MATCH with confidence reflected."""
        engine = MatchingEngine()
        result = engine.match(
            {"accepted_solution_groups": [["dp_1d_forward"]]},
            [make_ast_entry("dp_1d_forward", 0.31)],
        )
        assert result["match_result"] == "FULL_MATCH"
        assert result["confidence_score"] == 0.31
        assert result["unmatched_patterns"] == []


class TestDeterminism:
    def test_deterministic_output(self):
        engine = MatchingEngine()
        llm = {"accepted_solution_groups": [["dp_1d_forward", "dp_1d_sequence"]]}
        ast = [
            make_ast_entry("dp_1d_forward", 0.85),
            make_ast_entry("sliding_window_variable", 0.75),
        ]
        r1 = engine.match(llm, ast)
        r2 = engine.match(llm, ast)
        assert r1 == r2

    def test_deterministic_no_match(self):
        engine = MatchingEngine()
        llm = {"accepted_solution_groups": [["unknown"]]}
        ast = [make_ast_entry("dp_1d_forward", 0.85)]
        r1 = engine.match(llm, ast)
        r2 = engine.match(llm, ast)
        assert r1 == r2


class TestMatchResultDataclass:
    def test_to_dict(self):
        mr = MatchResult(
            match_result="FULL_MATCH",
            matched_groups=[0],
            unmatched_patterns=[],
            confidence_score=0.85,
            reasoning_signals=["signal_1"],
        )
        d = mr.to_dict()
        assert d["match_result"] == "FULL_MATCH"
        assert d["matched_groups"] == [0]
        assert d["unmatched_patterns"] == []
        assert d["confidence_score"] == 0.85
        assert d["reasoning_signals"] == ["signal_1"]

    def test_various_match_results(self):
        for r in ("FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH"):
            mr = MatchResult(r, [], [], 0.0, [])
            assert mr.to_dict()["match_result"] == r
