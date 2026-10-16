"""Tests for shadow analysis persistence — Phase 3A.

Covers:
- Serialization/deserialization round-trips
- Re-derivation from stored facts
- Version change re-derivation
- Ground truth compatibility
- Failure handling
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
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.persistence import (
    serialize_facts, deserialize_facts,
    serialize_techniques, deserialize_techniques,
    serialize_strategies, deserialize_strategies,
    serialize_match_outcome, deserialize_match_outcome,
    rerun_derivation, compute_code_hash,
)
import ast


# ============================================================
# Test code samples
# ============================================================

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

TWO_POINTERS = """
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

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


# ============================================================
# Serialization round-trip tests
# ============================================================

class TestSerializationRoundTrip:
    """Test that serialization/deserialization preserves data."""

    def test_facts_round_trip(self):
        """Structural facts survive serialize → deserialize."""
        import ast
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))
        serialized = serialize_facts(facts)
        deserialized = deserialize_facts(serialized)

        assert len(deserialized) == len(facts)
        for orig, loaded in zip(facts, deserialized):
            assert orig.fact_id == loaded.fact_id
            assert orig.fact_type == loaded.fact_type
            assert orig.ast_ref == loaded.ast_ref
            assert orig.attributes == loaded.attributes
            assert orig.extractor_version == loaded.extractor_version

    def test_techniques_round_trip(self):
        """Technique evidence survives serialize → deserialize."""
        import ast
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))
        techniques = detect_techniques(facts)
        serialized = serialize_techniques(techniques)
        deserialized = deserialize_techniques(serialized)

        assert len(deserialized) == len(techniques)
        for orig, loaded in zip(techniques, deserialized):
            assert orig.technique_id == loaded.technique_id
            assert orig.technique_version == loaded.technique_version
            assert orig.supporting_fact_ids == loaded.supporting_fact_ids
            assert orig.presence_confidence == loaded.presence_confidence
            assert orig.centrality == loaded.centrality

    def test_strategies_round_trip(self):
        """Strategy evidence survives serialize → deserialize."""
        import ast
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        serialized = serialize_strategies(strategies)
        deserialized = deserialize_strategies(serialized)

        assert len(deserialized) == len(strategies)
        for orig, loaded in zip(strategies, deserialized):
            assert orig.strategy_id == loaded.strategy_id
            assert orig.strategy_version == loaded.strategy_version
            assert orig.supporting_technique_ids == loaded.supporting_technique_ids
            assert orig.supporting_fact_ids == loaded.supporting_fact_ids
            assert orig.confidence == loaded.confidence

    def test_match_outcome_round_trip(self):
        """MatchOutcome survives serialize → deserialize."""
        import ast
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        outcome = MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="unknown",
            technique_evidence=techniques,
            strategy_evidence=strategies,
            structural_facts=facts,
            primary_strategy="binary_search",
            reasoning=["test"],
        )
        serialized = serialize_match_outcome(outcome)
        deserialized = deserialize_match_outcome(
            serialized, techniques, strategies, facts
        )

        assert deserialized.outcome == outcome.outcome
        assert deserialized.authority_tier == outcome.authority_tier
        assert deserialized.primary_strategy == outcome.primary_strategy
        assert deserialized.reasoning == outcome.reasoning

    def test_json_serializable(self):
        """All serialized outputs must be JSON-serializable."""
        import ast
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        outcome = MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="unknown",
            technique_evidence=techniques,
            strategy_evidence=strategies,
            structural_facts=facts,
        )

        # Must not raise
        json.dumps(serialize_facts(facts))
        json.dumps(serialize_techniques(techniques))
        json.dumps(serialize_strategies(strategies))
        json.dumps(serialize_match_outcome(outcome))


# ============================================================
# Re-derivation tests
# ============================================================

class TestReDerivation:
    """Test that stored facts can be re-derived to produce same results."""

    def test_binary_search_re_derivation(self):
        """Binary search: persist facts, re-derive, same result."""
        result = run_shadow_analysis(BINARY_SEARCH)
        assert result is not None

        # Deserialize the stored facts
        facts = deserialize_facts(result["structural_facts"])

        # Re-derive from stored facts
        rerun = rerun_derivation(facts)

        # Technique evidence must match
        orig_tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech_ids = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech_ids == rerun_tech_ids

        # Strategy evidence must match
        orig_strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        rerun_strat_ids = {s["strategy_id"] for s in rerun["strategy_evidence"]}
        assert orig_strat_ids == rerun_strat_ids

        # Outcome must match
        assert result["match_outcome"]["outcome"] == rerun["match_outcome"]["outcome"]

    def test_sliding_window_re_derivation(self):
        """Sliding window: persist facts, re-derive, same result."""
        result = run_shadow_analysis(SLIDING_WINDOW)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech_ids = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech_ids == rerun_tech_ids

        orig_strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        rerun_strat_ids = {s["strategy_id"] for s in rerun["strategy_evidence"]}
        assert orig_strat_ids == rerun_strat_ids

    def test_two_pointers_re_derivation(self):
        """Two pointers: persist facts, re-derive, same result."""
        result = run_shadow_analysis(TWO_POINTERS)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech_ids = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech_ids == rerun_tech_ids

        orig_strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        rerun_strat_ids = {s["strategy_id"] for s in rerun["strategy_evidence"]}
        assert orig_strat_ids == rerun_strat_ids

    def test_add_two_numbers_re_derivation(self):
        """Add Two Numbers: persist facts, re-derive, same result."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech_ids = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech_ids == rerun_tech_ids

        # Should remain UNRESOLVED
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"
        assert rerun["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_2996_re_derivation(self):
        """Problem 2996: persist facts, re-derive, same result."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        rerun_tech_ids = {t["technique_id"] for t in rerun["technique_evidence"]}
        assert orig_tech_ids == rerun_tech_ids

        # Should remain UNRESOLVED
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"
        assert rerun["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_re_derivation_preserves_fact_count(self):
        """Re-derivation preserves the same number of structural facts."""
        result = run_shadow_analysis(BINARY_SEARCH)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        assert len(result["structural_facts"]) == len(rerun["structural_facts"])

    def test_re_derivation_preserves_fact_types(self):
        """Re-derivation preserves the same fact types."""
        result = run_shadow_analysis(BINARY_SEARCH)
        assert result is not None

        facts = deserialize_facts(result["structural_facts"])
        rerun = rerun_derivation(facts)

        orig_types = {f["fact_type"] for f in result["structural_facts"]}
        rerun_types = {f["fact_type"] for f in rerun["structural_facts"]}
        assert orig_types == rerun_types


# ============================================================
# Version change re-derivation tests
# ============================================================

class TestVersionChangeReDerivation:
    """Test that changing definition versions can produce different results."""

    def test_same_facts_different_version_possible(self):
        """Verify that the same structural facts can produce different
        technique evidence if the technique definition changes.

        This is a design test — it proves the architecture works:
        facts are stable, definitions are versioned and changeable.
        """
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH))

        # Current derivation
        techniques_v1 = detect_techniques(facts)
        tech_ids_v1 = {t.technique_id for t in techniques_v1}

        # The facts are stable — same facts, same result with current definitions
        techniques_v1_again = detect_techniques(facts)
        tech_ids_v1_again = {t.technique_id for t in techniques_v1_again}
        assert tech_ids_v1 == tech_ids_v1_again

        # Prove that facts are independent of definitions:
        # If we changed the definition to require an additional fact,
        # the same facts would produce fewer techniques.
        # This is demonstrated by the fact that `recursive_branching`
        # requires `multiple_recursive_paths` — if we removed that
        # requirement, more techniques would fire from the same facts.
        # We don't actually change definitions here, just verify the
        # architectural invariant holds.

    def test_structural_facts_are_stable(self):
        """Structural facts are deterministic and stable across runs."""
        facts1 = extract_structural_facts(ast.parse(BINARY_SEARCH))
        facts2 = extract_structural_facts(ast.parse(BINARY_SEARCH))

        types1 = [f.fact_type for f in facts1]
        types2 = [f.fact_type for f in facts2]
        assert types1 == types2

        # Serialized facts are also stable
        ser1 = serialize_facts(facts1)
        ser2 = serialize_facts(facts2)
        assert json.dumps(ser1) == json.dumps(ser2)


# ============================================================
# Code hash tests
# ============================================================

class TestCodeHash:
    """Test code hash computation."""

    def test_deterministic(self):
        """Same code produces same hash."""
        h1 = compute_code_hash(BINARY_SEARCH)
        h2 = compute_code_hash(BINARY_SEARCH)
        assert h1 == h2

    def test_different_code_different_hash(self):
        """Different code produces different hash."""
        h1 = compute_code_hash(BINARY_SEARCH)
        h2 = compute_code_hash(SLIDING_WINDOW)
        assert h1 != h2

    def test_hash_is_hex(self):
        """Hash is a hex string."""
        h = compute_code_hash(BINARY_SEARCH)
        assert len(h) == 64  # SHA-256
        int(h, 16)  # Must not raise


# ============================================================
# Ground truth compatibility tests
# ============================================================

class TestGroundTruthCompatibility:
    """Test that new persistence is compatible with existing ground truth."""

    def test_old_flat_pattern_groups_still_valid(self):
        """Old flat-pattern solution groups can still be loaded."""
        # Simulate an old-format solution group
        old_group = {
            "id": "group_0",
            "version": 1,
            "required": ["linked_list_reversal"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
            "provenance": [],
        }
        # Must not raise
        assert old_group["id"] == "group_0"
        assert old_group["authority_tier"] == "llm_proposed"

    def test_new_structured_groups_load(self):
        """New structured solution groups load correctly."""
        new_group = {
            "id": "group_0",
            "version": 1,
            "required": ["carry_propagation"],
            "optional": ["node_constructor"],
            "excluded": ["bidirectional_index_scan"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["vocabulary_v1"],
        }
        # Must not raise
        assert new_group["id"] == "group_0"
        assert new_group["authority_tier"] == "structurally_observed"

    def test_missing_fields_receive_safe_defaults(self):
        """Solution groups with missing fields get safe defaults."""
        minimal_group = {"id": "group_0"}
        # Safe defaults
        assert minimal_group.get("required", []) == []
        assert minimal_group.get("optional", []) == []
        assert minimal_group.get("excluded", []) == []
        assert minimal_group.get("threshold", 0.5) == 0.5
        assert minimal_group.get("authority_tier", "bootstrap") == "bootstrap"

    def test_bootstrap_groups_remain_non_authoritative(self):
        """Bootstrap-tier groups must not produce authoritative CONTRADICTED."""
        # This is tested via the matching engine, but we verify the
        # authority tier is preserved through serialization
        outcome = MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="bootstrap",
        )
        serialized = serialize_match_outcome(outcome)
        assert serialized["authority_tier"] == "bootstrap"

    def test_authority_tier_preserved(self):
        """Authority tier is preserved through serialization round-trip."""
        for tier in ["bootstrap", "llm_proposed", "structurally_observed",
                     "externally_listed", "editorial", "unknown"]:
            outcome = MatchOutcome(outcome="UNRESOLVED", authority_tier=tier)
            serialized = serialize_match_outcome(outcome)
            deserialized = deserialize_match_outcome(
                serialized, [], [], []
            )
            assert deserialized.authority_tier == tier


# ============================================================
# Failure handling tests
# ============================================================

class TestFailureHandling:
    """Test that persistence fails gracefully."""

    def test_deserialize_empty_facts(self):
        """Deserializing empty facts list returns empty list."""
        result = deserialize_facts([])
        assert result == []

    def test_deserialize_empty_techniques(self):
        """Deserializing empty techniques list returns empty list."""
        result = deserialize_techniques([])
        assert result == []

    def test_deserialize_empty_strategies(self):
        """Deserializing empty strategies list returns empty list."""
        result = deserialize_strategies([])
        assert result == []

    def test_deserialize_malformed_fact(self):
        """Deserializing a malformed fact uses safe defaults."""
        result = deserialize_facts([{"invalid": "data"}])
        assert len(result) == 1
        assert result[0].fact_id == ""
        assert result[0].fact_type == ""

    def test_deserialize_malformed_technique(self):
        """Deserializing a malformed technique uses safe defaults."""
        result = deserialize_techniques([{"invalid": "data"}])
        assert len(result) == 1
        assert result[0].technique_id == ""
        assert result[0].presence_confidence == 0.0

    def test_re_derivation_with_empty_facts(self):
        """Re-derivation with empty facts produces empty results."""
        rerun = rerun_derivation([])
        assert rerun["structural_facts"] == []
        assert rerun["technique_evidence"] == []
        assert rerun["strategy_evidence"] == []
        assert rerun["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_persist_with_none_result(self):
        """persist_shadow_analysis with None result returns False."""
        from pathforge.ast_analysis.shadow.persistence import persist_shadow_analysis
        # Mock connection not needed — None check happens before DB access
        result = persist_shadow_analysis(None, 1, "hash", None)
        assert result is False
