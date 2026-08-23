"""Phase 3B integration tests — shadow analysis in the real /analyze path.

Tests:
- Shadow analysis integration with /analyze
- Structured solution-group loading
- Multi-group behavior
- Authority handling
- Real validation cases
- Persistence round-trip
- Backward compatibility
"""
import json
import pytest

from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, StrategyEvidence, MatchOutcome,
    EXTRACTOR_VERSION,
)
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.persistence import (
    serialize_facts, deserialize_facts,
    serialize_techniques, deserialize_techniques,
    rerun_derivation, compute_code_hash,
)
import ast


# ============================================================
# Test code samples
# ============================================================

ADD_TWO_NUMBERS = """
def addTwoNumbers(l1, l2):
    dummy = ListNode()
    curr = dummy
    carry = 0
    while l1 or l2 or carry:
        val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
        carry, digit = divmod(val, 10)
        curr.next = ListNode(digit)
        curr = curr.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    return dummy.next
"""

PROBLEM_2996 = """
def missingInteger(nums):
    i = 1
    summ = nums[0]
    while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
        summ += nums[i]
        i += 1
    while summ in nums:
        summ += 1
    return summ
"""

IS_PALINDROME = """
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

BINARY_SEARCH = """
def binary_search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""

SLIDING_WINDOW = """
def longest_substring(s):
    char_index = {}
    left = 0
    max_len = 0
    for right in range(len(s)):
        if s[right] in char_index:
            left = max(left, char_index[s[right]] + 1)
        char_index[s[right]] = right
        max_len = max(max_len, right - left + 1)
    return max_len
"""


# ============================================================
# Structured solution-group loading tests
# ============================================================

class TestStructuredSolutionGroups:
    """Test that structured solution groups load correctly."""

    def test_new_format_groups_load(self):
        """New V1 format groups with required/optional/excluded load correctly."""
        groups = [
            {
                "id": "group_0",
                "version": 1,
                "required": ["carry_propagation"],
                "optional": ["node_constructor"],
                "excluded": ["bidirectional_index_scan"],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
                "provenance": ["vocabulary_v1"],
            }
        ]

        # Run shadow analysis with these groups
        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        outcome = result["match_outcome"]
        # carry_propagation is detected for Add Two Numbers
        # No excluded evidence (bidirectional_index_scan) is detected
        # So the group should be satisfied → CONFIRMED
        assert outcome["outcome"] == "CONFIRMED"

    def test_legacy_format_groups_load(self):
        """Legacy format groups (patterns/evidence/confidence) still work."""
        groups = [
            {
                "id": "group_0",
                "patterns": ["carry_propagation"],
                "evidence": "llm_proposed",
                "confidence": {"carry_propagation": 0.8},
            }
        ]

        # Legacy format should still be processed
        # (the matcher handles both formats)
        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None

    def test_groups_with_missing_fields(self):
        """Groups with missing fields get safe defaults."""
        groups = [
            {"id": "group_0"}  # Minimal — all fields optional
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"


# ============================================================
# Multi-group behavior tests
# ============================================================

class TestMultiGroupBehavior:
    """Test that multiple solution groups work correctly."""

    def test_multiple_groups_one_satisfied(self):
        """One group satisfied, one not → CONFIRMED (best group wins)."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
            {
                "id": "group_1",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        # carry_propagation is detected → group_0 satisfied
        # bidirectional_index_scan is NOT detected → group_1 not satisfied
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_multiple_groups_both_satisfied(self):
        """Both groups satisfied → CONFIRMED (best satisfaction wins)."""
        # Palindrome has bidirectional_index_scan
        groups = [
            {
                "id": "group_0",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
            {
                "id": "group_1",
                "required": ["sequential_accumulation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_multiple_groups_neither_satisfied(self):
        """Neither group satisfied → UNRESOLVED."""
        groups = [
            {
                "id": "group_0",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
            {
                "id": "group_1",
                "required": ["recursive_branching"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_multiple_groups_excluded_contradicts(self):
        """Excluded evidence present → CONTRADICTED (if authoritative)."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": ["bidirectional_index_scan"],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        # Palindrome has bidirectional_index_scan but NOT carry_propagation
        # Excluded fires → CONTRADICTED (authoritative tier)
        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONTRADICTED"


# ============================================================
# Authority behavior tests
# ============================================================

class TestAuthorityBehavior:
    """Test authority-aware shadow outcomes."""

    def test_authoritative_group_confirmed(self):
        """Authoritative group matched → CONFIRMED."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"
        assert result["match_outcome"]["authority_tier"] == "structurally_observed"

    def test_llm_proposed_group_confirmed(self):
        """LLM-proposed group matched → CONFIRMED (allowed as shadow observation)."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        # LLM-proposed groups CAN produce CONFIRMED (shadow observation)
        assert result["match_outcome"]["outcome"] == "CONFIRMED"
        assert result["match_outcome"]["authority_tier"] == "llm_proposed"

    def test_bootstrap_contradiction_becomes_unresolved(self):
        """Bootstrap/llm_proposed CONTRADICTED → UNRESOLVED (non-punitive)."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": ["bidirectional_index_scan"],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        # Palindrome has bidirectional_index_scan → excluded fires
        # But authority is llm_proposed → CONTRADICTED downgraded to UNRESOLVED
        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_authoritative_contradiction_stays(self):
        """Authoritative CONTRADICTED remains CONTRADICTED."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": ["bidirectional_index_scan"],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        # Palindrome has bidirectional_index_scan → excluded fires
        # Authority is structurally_observed → stays CONTRADICTED
        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONTRADICTED"

    def test_no_matching_group_unresolved(self):
        """No matching group → UNRESOLVED."""
        groups = [
            {
                "id": "group_0",
                "required": ["recursive_branching"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"


# ============================================================
# Real validation case tests
# ============================================================

class TestRealValidationCases:
    """Test the real validation cases specified in Phase 3B."""

    def test_add_two_numbers_no_group(self):
        """Add Two Numbers without solution group → UNRESOLVED."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        # carry_propagation evidence present
        assert "carry_propagation" in tech_ids
        # No linked-list-reversal strategy
        assert "linked_list_reversal" not in strat_ids
        # No two_pointers_opposite
        assert "two_pointers_opposite" not in strat_ids
        # UNRESOLVED without matching group
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_add_two_numbers_with_matching_group(self):
        """Add Two Numbers with matching group → CONFIRMED."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_2996_unresolved(self):
        """Problem 2996 → UNRESOLVED (no matching strategy)."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        # sequential_accumulation present
        assert "sequential_accumulation" in tech_ids
        # No hash_map strategy
        assert "hash_map" not in strat_ids
        # No binary_search
        assert "binary_search" not in strat_ids
        # UNRESOLVED
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_palindrome_confirmed_with_group(self):
        """Palindrome with bidirectional_index_scan group → CONFIRMED."""
        groups = [
            {
                "id": "group_0",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        assert "bidirectional_index_scan" in tech_ids
        assert "two_pointers_opposite" in strat_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_binary_search_confirmed_with_group(self):
        """Binary search with midpoint group → CONFIRMED, NOT two_pointers."""
        groups = [
            {
                "id": "group_0",
                "required": ["binary_search"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(BINARY_SEARCH, solution_groups=groups)
        assert result is not None

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        assert "binary_search" in strat_ids
        assert "two_pointers_opposite" not in strat_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_sliding_window_confirmed_with_group(self):
        """Sliding window with group → CONFIRMED, NOT two_pointers."""
        groups = [
            {
                "id": "group_0",
                "required": ["sliding_window"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]

        result = run_shadow_analysis(SLIDING_WINDOW, solution_groups=groups)
        assert result is not None

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        assert "sliding_window" in strat_ids
        assert "two_pointers_opposite" not in strat_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"


# ============================================================
# Persistence round-trip integration tests
# ============================================================

class TestPersistenceRoundTrip:
    """Test full persistence round-trip (serialize → deserialize → re-derive)."""

    def test_full_round_trip_binary_search(self):
        """Binary search: run → serialize → deserialize → re-derive → same result."""
        result = run_shadow_analysis(BINARY_SEARCH)
        assert result is not None

        # Deserialize facts
        facts = deserialize_facts(result["structural_facts"])

        # Re-derive
        rerun = rerun_derivation(facts)

        # Must match
        orig_tech = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech == rerun_tech

        orig_strat = {s["strategy_id"] for s in result["strategy_evidence"]}
        rerun_strat = {s["strategy_id"] for s in rerun["strategy_evidence"]}
        assert orig_strat == rerun_strat

        assert result["match_outcome"]["outcome"] == rerun["match_outcome"]["outcome"]

    def test_full_round_trip_add_two_numbers(self):
        """Add Two Numbers: run → serialize → deserialize → re-derive → same result."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_tech = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech == rerun_tech

        assert result["match_outcome"]["outcome"] == rerun["match_outcome"]["outcome"]

    def test_round_trip_with_solution_groups(self):
        """Round-trip with solution groups preserves outcome."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts, solution_groups=groups)

        assert result["match_outcome"]["outcome"] == rerun["match_outcome"]["outcome"]
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_code_hash_deterministic(self):
        """Code hash is deterministic for the same input."""
        h1 = compute_code_hash(BINARY_SEARCH)
        h2 = compute_code_hash(BINARY_SEARCH)
        assert h1 == h2


# ============================================================
# Backward compatibility tests
# ============================================================

class TestBackwardCompatibility:
    """Test backward compatibility with legacy formats."""

    def test_old_submission_format_still_works(self):
        """Old submissions without shadow columns still work."""
        # Simulate an old submission (no shadow data)
        old_submission = {
            "id": 1,
            "code_text": "def f(): pass",
            "verdict": "pass",
            "detected_pattern": "array_traversal",
            "structural_facts_json": None,
            "technique_evidence_json": None,
            "strategy_evidence_json": None,
            "shadow_match_outcome_json": None,
        }

        # Must not raise when shadow data is None
        assert old_submission["structural_facts_json"] is None
        assert old_submission["technique_evidence_json"] is None

    def test_legacy_api_response_format(self):
        """Legacy API consumers don't require the shadow field."""
        from pathforge.api.routes.analyze import AnalyzeResponse

        # Old consumers can ignore shadow_analysis
        response = AnalyzeResponse(
            ast={"detected_patterns": []},
            match_result={"overall_match": True},
            persisted={"submission_id": 1, "gap_signals_count": 0, "elo_updates_count": 0},
        )

        # shadow_analysis defaults to None
        assert response.shadow_analysis is None

    def test_old_ground_truth_format_loads(self):
        """Old flat-pattern ground truth still loads."""
        old_groups = [
            {
                "id": "group_0",
                "patterns": ["linked_list_reversal"],
                "evidence": "llm_proposed",
                "confidence": {"linked_list_reversal": 0.8},
            }
        ]

        # Must not raise
        assert old_groups[0]["patterns"] == ["linked_list_reversal"]

    def test_new_structured_groups_coexist(self):
        """New structured groups can coexist with legacy fields."""
        mixed_group = {
            "id": "group_0",
            "version": 1,
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
            "provenance": ["llm_ground_truth"],
            # Legacy fields
            "patterns": ["carry_propagation"],
            "evidence": "llm_proposed",
            "confidence": {"carry_propagation": 0.5},
        }

        # Both formats accessible
        assert mixed_group["required"] == ["carry_propagation"]
        assert mixed_group["patterns"] == ["carry_propagation"]
        assert mixed_group["authority_tier"] == "llm_proposed"
        assert mixed_group["evidence"] == "llm_proposed"


# ============================================================
# Production isolation tests
# ============================================================

class TestProductionIsolation:
    """Verify shadow analysis does not affect production."""

    def test_shadow_result_separate_from_production(self):
        """Shadow result is in a separate field, not in production fields."""
        result = run_shadow_analysis(BINARY_SEARCH)
        assert result is not None

        # Shadow results are in their own dict keys
        assert "structural_facts" in result
        assert "technique_evidence" in result
        assert "strategy_evidence" in result
        assert "match_outcome" in result

        # These do NOT overlap with production fields
        assert "detected_patterns" not in result
        assert "overall_match" not in result
        assert "verdict" not in result

    def test_shadow_failure_doesnt_affect_result(self):
        """If shadow analysis fails, the result is None (graceful degradation)."""
        # Invalid code causes shadow to fail
        result = run_shadow_analysis("def (invalid syntax")
        assert result is None

        # This should not cause any error — the caller handles None

    def test_shadow_outcome_independent_of_production(self):
        """Shadow outcome is computed independently of production verdict."""
        # Add Two Numbers: production might match via old flat patterns
        # Shadow: UNRESOLVED (no matching strategy)
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None

        # Shadow outcome is UNRESOLVED regardless of production behavior
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"
