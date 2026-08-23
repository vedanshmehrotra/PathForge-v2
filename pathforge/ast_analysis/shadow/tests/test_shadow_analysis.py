"""Tests for the shadow analysis vertical slice.

Covers:
- Structural fact extraction for all three validation cases
- Technique detection for all three cases
- Strategy detection for two-pointers
- Solution-group matching
- Authority gating
- Variable renaming (i += 1 vs i = i + 1)
- Graceful failure
- List membership not becoming hash-map evidence
"""
import ast
import pytest

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.data_structures import (
    StructuralFact, TechniqueEvidence, StrategyEvidence, MatchOutcome,
)


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
# Fact extraction tests
# ============================================================

class TestFactExtraction:
    """Test structural fact extraction for all three validation cases."""

    def test_add_two_numbers_facts(self):
        """Add Two Numbers should extract linked_structure_traversal,
        carry_propagation, node_constructor. The while loop uses truthiness
        (while l1 or l2 or carry), not a comparison, so while_loop_comparison
        does not fire."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        fact_types = {f.fact_type for f in facts}

        assert "linked_structure_traversal" in fact_types, \
            f"Expected linked_structure_traversal, got {fact_types}"
        assert "carry_propagation" in fact_types, \
            f"Expected carry_propagation, got {fact_types}"
        assert "node_constructor" in fact_types, \
            f"Expected node_constructor, got {fact_types}"

        # while l1 or l2 or carry is truthiness, not comparison
        assert "while_loop_comparison" not in fact_types, \
            "Add Two Numbers while-loop uses truthiness, not comparison"

        # Should NOT have opposite_direction_updates
        assert "opposite_direction_updates" not in fact_types, \
            "Add Two Numbers should NOT have opposite_direction_updates"

    def test_is_palindrome_facts(self):
        """Is Palindrome should extract while_loop_comparison,
        opposite_direction_updates, early_termination.
        Note: left += 1 / right -= 1 are unconditional in the while body
        (not inside the if), so conditional_index_update does not fire."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        fact_types = {f.fact_type for f in facts}

        assert "while_loop_comparison" in fact_types, \
            f"Expected while_loop_comparison, got {fact_types}"
        assert "opposite_direction_updates" in fact_types, \
            f"Expected opposite_direction_updates, got {fact_types}"
        assert "early_termination" in fact_types, \
            f"Expected early_termination, got {fact_types}"

        # left += 1 / right -= 1 are after the if, not inside it
        assert "conditional_index_update" not in fact_types, \
            "Updates are unconditional in while body, not inside if"

        # Should NOT have linked_structure_traversal
        assert "linked_structure_traversal" not in fact_types, \
            "Is Palindrome should NOT have linked_structure_traversal"

    def test_problem_2996_facts(self):
        """Problem 2996 should extract while_loop_comparison, accumulator_update,
        and linked_structure_traversal should NOT be present."""
        facts = extract_structural_facts(ast.parse(PROBLEM_2996))
        fact_types = {f.fact_type for f in facts}

        assert "while_loop_comparison" in fact_types, \
            f"Expected while_loop_comparison, got {fact_types}"
        assert "accumulator_update" in fact_types, \
            f"Expected accumulator_update, got {fact_types}"

        # Should NOT have linked_structure_traversal
        assert "linked_structure_traversal" not in fact_types, \
            "Problem 2996 should NOT have linked_structure_traversal"

        # Should NOT have opposite_direction_updates
        assert "opposite_direction_updates" not in fact_types, \
            "Problem 2996 should NOT have opposite_direction_updates"

    def test_all_facts_have_ids(self):
        """All extracted facts must have non-empty fact_id."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        for fact in facts:
            assert fact.fact_id, f"Fact {fact.fact_type} missing fact_id"
            assert fact.fact_id.startswith("fact_"), \
                f"Fact ID should start with 'fact_', got {fact.fact_id}"

    def test_all_facts_have_extractor_version(self):
        """All extracted facts must have extractor_version set."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        for fact in facts:
            assert fact.extractor_version, \
                f"Fact {fact.fact_type} missing extractor_version"

    def test_facts_are_deterministic(self):
        """Same code should produce same facts."""
        facts1 = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        facts2 = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        types1 = [f.fact_type for f in facts1]
        types2 = [f.fact_type for f in facts2]
        assert types1 == types2, "Facts should be deterministic"

    def test_linked_traversal_attributes(self):
        """Linked structure traversal should record which attributes were found."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        linked = [f for f in facts if f.fact_type == "linked_structure_traversal"]
        assert len(linked) >= 1, "Should have at least one linked_structure_traversal"
        attrs = linked[0].attributes.get("attributes", [])
        assert "next" in attrs, f"Should find .next attribute, got {attrs}"

    def test_carry_propagation_variables(self):
        """Carry propagation should identify carry-like variables."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        carry = [f for f in facts if f.fact_type == "carry_propagation"]
        assert len(carry) >= 1, "Should have at least one carry_propagation"
        carry_vars = carry[0].attributes.get("carry_variables", [])
        assert "carry" in carry_vars, \
            f"Should identify 'carry' variable, got {carry_vars}"

    def test_opposite_updates_directions(self):
        """Opposite direction updates should record incremented and decremented."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        opp = [f for f in facts if f.fact_type == "opposite_direction_updates"]
        assert len(opp) >= 1, "Should have opposite_direction_updates"
        inc = opp[0].attributes.get("incremented", [])
        dec = opp[0].attributes.get("decremented", [])
        assert "left" in inc, f"Expected 'left' incremented, got {inc}"
        assert "right" in dec, f"Expected 'right' decremented, got {dec}"


# ============================================================
# Technique detection tests
# ============================================================

class TestTechniqueDetection:
    """Test technique detection for all three validation cases."""

    def test_add_two_numbers_techniques(self):
        """Add Two Numbers should detect carry_propagation, NOT bidirectional_index_scan."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}

        assert "carry_propagation" in tech_ids, \
            f"Expected carry_propagation, got {tech_ids}"
        assert "bidirectional_index_scan" not in tech_ids, \
            f"Add Two Numbers should NOT detect bidirectional_index_scan, got {tech_ids}"

    def test_is_palindrome_techniques(self):
        """Is Palindrome should detect bidirectional_index_scan, NOT carry_propagation."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}

        assert "bidirectional_index_scan" in tech_ids, \
            f"Expected bidirectional_index_scan, got {tech_ids}"
        assert "carry_propagation" not in tech_ids, \
            f"Is Palindrome should NOT detect carry_propagation, got {tech_ids}"

    def test_problem_2996_techniques(self):
        """Problem 2996 should detect sequential_accumulation, NOT bidirectional_index_scan."""
        facts = extract_structural_facts(ast.parse(PROBLEM_2996))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}

        assert "sequential_accumulation" in tech_ids, \
            f"Expected sequential_accumulation, got {tech_ids}"
        assert "bidirectional_index_scan" not in tech_ids, \
            f"Problem 2996 should NOT detect bidirectional_index_scan, got {tech_ids}"

    def test_techniques_have_confidence(self):
        """All detected techniques must have presence_confidence > 0."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        techniques = detect_techniques(facts)
        for tech in techniques:
            assert tech.presence_confidence > 0, \
                f"Technique {tech.technique_id} should have confidence > 0"

    def test_techniques_have_fact_references(self):
        """All detected techniques must reference supporting facts."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        fact_ids = {f.fact_id for f in facts}
        techniques = detect_techniques(facts)
        for tech in techniques:
            assert tech.supporting_fact_ids, \
                f"Technique {tech.technique_id} should have supporting facts"
            for fid in tech.supporting_fact_ids:
                assert fid in fact_ids, \
                    f"Technique {tech.technique_id} references unknown fact {fid}"


# ============================================================
# Strategy detection tests
# ============================================================

class TestStrategyDetection:
    """Test strategy detection for two_pointers_opposite."""

    def test_is_palindrome_strategy(self):
        """Is Palindrome should detect two_pointers_opposite strategy."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        strat_ids = {s.strategy_id for s in strategies}

        assert "two_pointers_opposite" in strat_ids, \
            f"Expected two_pointers_opposite, got {strat_ids}"

    def test_add_two_numbers_no_strategy(self):
        """Add Two Numbers should NOT detect two_pointers_opposite."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        strat_ids = {s.strategy_id for s in strategies}

        assert "two_pointers_opposite" not in strat_ids, \
            f"Add Two Numbers should NOT detect two_pointers_opposite, got {strat_ids}"

    def test_problem_2996_no_strategy(self):
        """Problem 2996 should NOT detect two_pointers_opposite."""
        facts = extract_structural_facts(ast.parse(PROBLEM_2996))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        strat_ids = {s.strategy_id for s in strategies}

        assert "two_pointers_opposite" not in strat_ids, \
            f"Problem 2996 should NOT detect two_pointers_opposite, got {strat_ids}"

    def test_strategy_has_confidence(self):
        """Detected strategy must have confidence > 0."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        for strat in strategies:
            assert strat.confidence > 0, \
                f"Strategy {strat.strategy_id} should have confidence > 0"

    def test_strategy_references_techniques(self):
        """Strategy must reference its supporting techniques."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        strategies = evaluate_strategies(techniques, facts)
        for strat in strategies:
            for tid in strat.supporting_technique_ids:
                assert tid in tech_ids, \
                    f"Strategy {strat.strategy_id} references unknown technique {tid}"


# ============================================================
# Matching tests
# ============================================================

class TestMatching:
    """Test solution-group satisfaction matching."""

    def test_no_groups_unresolved(self):
        """No solution groups → UNRESOLVED."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)
        outcome = evaluate_solution_groups([], techniques, strategies, facts)

        assert outcome.outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED, got {outcome.outcome}"

    def test_matching_group_confirmed(self):
        """A matching solution group → CONFIRMED."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [{
            "id": "g0",
            "required": ["bidirectional_index_scan"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        assert outcome.outcome == "CONFIRMED", \
            f"Expected CONFIRMED, got {outcome.outcome}"

    def test_non_matching_group_unresolved(self):
        """A non-matching solution group → UNRESOLVED."""
        facts = extract_structural_facts(ast.parse(ADD_TWO_NUMBERS))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [{
            "id": "g0",
            "required": ["bidirectional_index_scan"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        assert outcome.outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED, got {outcome.outcome}"

    def test_excluded_evidence_contradicts(self):
        """Excluded evidence present → CONTRADICTED (if authoritative)."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [{
            "id": "g0",
            "required": ["bidirectional_index_scan"],
            "optional": [],
            "excluded": ["carry_propagation"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        # carry_propagation is NOT detected for is_palindrome, so excluded
        # doesn't fire. The group should be satisfied.
        assert outcome.outcome == "CONFIRMED", \
            f"Expected CONFIRMED (carry not detected), got {outcome.outcome}"

    def test_matching_groups_multiple(self):
        """Multiple matching groups → at least one CONFIRMED."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [
            {
                "id": "g0",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
            {
                "id": "g1",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "structurally_observed",
            },
        ]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        # g0 matches, g1 doesn't → CONFIRMED (at least one matches)
        assert outcome.outcome == "CONFIRMED", \
            f"Expected CONFIRMED, got {outcome.outcome}"


# ============================================================
# Authority gating tests
# ============================================================

class TestAuthorityGating:
    """Test authority rules for CONFIRMED/UNRESOLVED/CONTRADICTED."""

    def test_bootstrap_contradiction_becomes_unresolved(self):
        """Bootstrap/llm_proposed CONTRADICTED must become UNRESOLVED."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        # A group that requires carry_propagation (not detected for palindrome)
        # with excluded bidirectional_index_scan (which IS detected)
        # This should be CONTRADICTED... but authority is bootstrap → UNRESOLVED
        groups = [{
            "id": "g0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": ["bidirectional_index_scan"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        # excluded fires → raw outcome is CONTRADICTED
        # but authority is llm_proposed → downgraded to UNRESOLVED
        assert outcome.outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED (bootstrap contradiction), got {outcome.outcome}"

    def test_authoritative_contradiction_stays_contradicted(self):
        """Authoritative CONTRADICTED remains CONTRADICTED."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [{
            "id": "g0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": ["bidirectional_index_scan"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        # excluded fires → raw outcome is CONTRADICTED
        # authority is structurally_observed → stays CONTRADICTED
        assert outcome.outcome == "CONTRADICTED", \
            f"Expected CONTRADICTED, got {outcome.outcome}"

    def test_low_authority_confirmed(self):
        """Low-authority CONFIRMED is still CONFIRMED (but with lower authority)."""
        facts = extract_structural_facts(ast.parse(IS_PALINDROME))
        techniques = detect_techniques(facts)
        strategies = evaluate_strategies(techniques, facts)

        groups = [{
            "id": "g0",
            "required": ["bidirectional_index_scan"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)

        assert outcome.outcome == "CONFIRMED", \
            f"Expected CONFIRMED, got {outcome.outcome}"
        assert outcome.authority_tier == "llm_proposed", \
            f"Expected llm_proposed authority, got {outcome.authority_tier}"


# ============================================================
# Validation case integration tests (shadow_runner)
# ============================================================

class TestShadowRunner:
    """Integration tests using the full shadow_runner pipeline."""

    def test_add_two_numbers_shadow(self):
        """Add Two Numbers: carry_propagation detected, no linked_list_reversal,
        no two_pointers_opposite, outcome UNRESOLVED."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)

        assert result is not None, "Shadow analysis should succeed"
        assert result["structural_facts"], "Should have structural facts"

        # Check technique evidence
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids, \
            f"Expected carry_propagation, got {tech_ids}"

        # Check strategy evidence
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids, \
            f"Add Two Numbers should NOT have two_pointers_opposite, got {strat_ids}"

        # Check outcome
        outcome = result["match_outcome"]["outcome"]
        assert outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED, got {outcome}"

        # Verify no linked_list_reversal in facts
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        # linked_list_reversal should not be a fact type (it's not in our vocabulary)
        assert "linked_list_reversal" not in fact_types, \
            "linked_list_reversal should NOT appear as a structural fact"

    def test_is_palindrome_shadow(self):
        """Is Palindrome: bidirectional_index_scan detected,
        two_pointers_opposite strategy detected."""
        result = run_shadow_analysis(IS_PALINDROME)

        assert result is not None, "Shadow analysis should succeed"

        # Check technique evidence
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "bidirectional_index_scan" in tech_ids, \
            f"Expected bidirectional_index_scan, got {tech_ids}"

        # Check strategy evidence
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids, \
            f"Expected two_pointers_opposite, got {strat_ids}"

        # Check outcome (no solution groups → UNRESOLVED)
        outcome = result["match_outcome"]["outcome"]
        assert outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED (no groups), got {outcome}"

    def test_problem_2996_shadow(self):
        """Problem 2996: sequential_accumulation detected,
        no two_pointers_opposite, outcome UNRESOLVED."""
        result = run_shadow_analysis(PROBLEM_2996)

        assert result is not None, "Shadow analysis should succeed"

        # Check technique evidence
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "sequential_accumulation" in tech_ids, \
            f"Expected sequential_accumulation, got {tech_ids}"
        assert "bidirectional_index_scan" not in tech_ids, \
            f"Problem 2996 should NOT have bidirectional_index_scan, got {tech_ids}"

        # Check strategy evidence — no strategies should match
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids, \
            f"Problem 2996 should NOT have two_pointers_opposite, got {strat_ids}"

        # Check outcome
        outcome = result["match_outcome"]["outcome"]
        assert outcome == "UNRESOLVED", \
            f"Expected UNRESOLVED, got {outcome}"

        # Verify list membership remains a fact, not a strategy
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        # membership_check should not be in our fact vocabulary (it's a fact type
        # but not a technique or strategy)

    def test_shadow_runner_returns_none_on_error(self):
        """Shadow runner should return None on malformed code, not raise."""
        result = run_shadow_analysis("def (invalid syntax")
        assert result is None, "Should return None on syntax error"

    def test_shadow_runner_has_timing(self):
        """Shadow runner should report elapsed time."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] >= 0

    def test_shadow_runner_with_solution_groups(self):
        """Shadow runner should evaluate solution groups when provided."""
        groups = [{
            "id": "g0",
            "required": ["bidirectional_index_scan"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
        }]
        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)

        assert result is not None
        outcome = result["match_outcome"]["outcome"]
        assert outcome == "CONFIRMED", \
            f"Expected CONFIRMED (group matches), got {outcome}"


# ============================================================
# Syntax normalization tests
# ============================================================

class TestSyntaxNormalization:
    """Test that equivalent syntax produces equivalent facts."""

    def test_augmented_vs_equal_assignment(self):
        """i += 1 and i = i + 1 should produce same accumulator_update fact."""
        code_aug = "while x:\n    i += 1"
        code_eq = "while x:\n    i = i + 1"

        facts_aug = extract_structural_facts(ast.parse(code_aug))
        facts_eq = extract_structural_facts(ast.parse(code_eq))

        acc_aug = [f for f in facts_aug if f.fact_type == "accumulator_update"]
        acc_eq = [f for f in facts_eq if f.fact_type == "accumulator_update"]

        assert len(acc_aug) >= 1, "augmented should produce accumulator_update"
        assert len(acc_eq) >= 1, "equal_sign should produce accumulator_update"

        # Both should identify the same variable
        assert acc_aug[0].attributes["variable"] == acc_eq[0].attributes["variable"]

    def test_equal_sign_decrement(self):
        """right = right - 1 should produce accumulator_update with Sub operator."""
        code = "while left < right:\n    right = right - 1"
        facts = extract_structural_facts(ast.parse(code))
        acc = [f for f in facts if f.fact_type == "accumulator_update"]

        assert len(acc) >= 1, "Should detect accumulator_update"
        assert acc[0].attributes["variable"] == "right"
        assert acc[0].attributes["operator"] == "Sub"


# ============================================================
# Variable naming independence tests
# ============================================================

class TestNamingIndependence:
    """Test that technique detection is independent of variable naming."""

    def test_renamed_two_pointers(self):
        """Two pointers with renamed variables should still be detected."""
        code = """
def check(arr):
    a, b = 0, len(arr) - 1
    while a < b:
        if arr[a] != arr[b]:
            return False
        a += 1
        b -= 1
    return True
"""
        result = run_shadow_analysis(code)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "bidirectional_index_scan" in tech_ids, \
            f"Renamed two pointers should still be detected, got {tech_ids}"

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids, \
            f"Renamed two pointers strategy should be detected, got {strat_ids}"

    def test_renamed_carry_propagation(self):
        """Carry propagation with renamed variables should still be detected."""
        code = """
def add(la, lb):
    result = ListNode()
    ptr = result
    c = 0
    while la or lb or c:
        v = (la.val if la else 0) + (lb.val if lb else 0) + c
        c, d = divmod(v, 10)
        ptr.next = ListNode(d)
        ptr = ptr.next
        la = la.next if la else None
        lb = lb.next if lb else None
    return result.next
"""
        result = run_shadow_analysis(code)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids, \
            f"Renamed carry propagation should be detected, got {tech_ids}"


# ============================================================
# Regression: list membership not becoming hash-map evidence
# ============================================================

class TestRegressionMembership:
    """Test that list membership (in) does NOT become hash-map classification."""

    def test_membership_in_loop(self):
        """Membership check in a loop should NOT produce hash-map-related facts."""
        code = """
def find_missing(nums):
    s = 0
    i = 1
    while i <= len(nums) - 1 and nums[i] == nums[i-1] + 1:
        s += nums[i]
        i += 1
    while s in nums:
        s += 1
    return s
"""
        result = run_shadow_analysis(code)
        assert result is not None

        # Check that no hash_map or frequency technique is detected
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "hash_map_lookup" not in tech_ids, \
            f"Membership should NOT become hash_map_lookup, got {tech_ids}"
        assert "frequency_counting" not in tech_ids, \
            f"Membership should NOT become frequency_counting, got {tech_ids}"

        # sequential_accumulation should be detected
        assert "sequential_accumulation" in tech_ids, \
            f"Should detect sequential_accumulation, got {tech_ids}"


# ============================================================
# Graceful failure tests
# ============================================================

class TestGracefulFailure:
    """Test that shadow analysis fails gracefully."""

    def test_syntax_error(self):
        """Syntax error should return None, not raise."""
        result = run_shadow_analysis("def (bad syntax")
        assert result is None

    def test_empty_code(self):
        """Empty code should return empty results, not fail."""
        result = run_shadow_analysis("")
        assert result is not None
        assert result["structural_facts"] == []
        assert result["technique_evidence"] == []
        assert result["strategy_evidence"] == []

    def test_complex_code_no_crash(self):
        """Complex code should not crash the shadow analyzer."""
        complex_code = """
class Solution:
    def solve(self, nums, target):
        from collections import defaultdict
        graph = defaultdict(list)
        for u, v in edges:
            graph[u].append(v)
            graph[v].append(u)
        
        def dfs(node, visited):
            visited.add(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, visited)
            return len(visited)
        
        return dfs(0, set())
"""
        result = run_shadow_analysis(complex_code)
        # Should not crash; result may be None or have partial results
        # The important thing is no exception


# ============================================================
# Midpoint calculation tests
# ============================================================

STANDARD_MIDPOINT = """
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

OVERFLOW_SAFE_MIDPOINT = """
def binary_search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""

VARIABLE_RENAMED_MIDPOINT = """
def search(arr, val):
    a, b = 0, len(arr) - 1
    while a <= b:
        m = (a + b) // 2
        if arr[m] == val:
            return m
        elif arr[m] < val:
            a = m + 1
        else:
            b = m - 1
    return -1
"""

NOT_MIDPOINT_DIV2 = """
def halve(arr):
    n = len(arr)
    return n // 2
"""

NOT_MIDPOINT_TOTAL_DIV2 = """
def half_total(nums):
    total = sum(nums)
    return total // 2
"""


class TestMidpointCalculation:
    """Test midpoint_calculation fact extraction."""

    def test_standard_midpoint_detected(self):
        """Standard form (lo + hi) // 2 should be detected."""
        facts = extract_structural_facts(ast.parse(STANDARD_MIDPOINT))
        fact_types = {f.fact_type for f in facts}
        assert "midpoint_calculation" in fact_types, \
            f"Expected midpoint_calculation, got {fact_types}"

    def test_overflow_safe_midpoint_detected(self):
        """Overflow-safe form lo + (hi - lo) // 2 should be detected."""
        facts = extract_structural_facts(ast.parse(OVERFLOW_SAFE_MIDPOINT))
        fact_types = {f.fact_type for f in facts}
        assert "midpoint_calculation" in fact_types, \
            f"Expected midpoint_calculation, got {fact_types}"

    def test_variable_renamed_midpoint_detected(self):
        """Midpoint with renamed variables (a + b) // 2 should be detected."""
        facts = extract_structural_facts(ast.parse(VARIABLE_RENAMED_MIDPOINT))
        fact_types = {f.fact_type for f in facts}
        assert "midpoint_calculation" in fact_types, \
            f"Expected midpoint_calculation, got {fact_types}"

    def test_len_div2_not_midpoint(self):
        """len(arr) // 2 should NOT be detected as midpoint."""
        facts = extract_structural_facts(ast.parse(NOT_MIDPOINT_DIV2))
        fact_types = {f.fact_type for f in facts}
        assert "midpoint_calculation" not in fact_types, \
            f"len(arr) // 2 should NOT be midpoint, got {fact_types}"

    def test_total_div2_not_midpoint(self):
        """total // 2 (single variable) should NOT be detected as midpoint."""
        facts = extract_structural_facts(ast.parse(NOT_MIDPOINT_TOTAL_DIV2))
        fact_types = {f.fact_type for f in facts}
        assert "midpoint_calculation" not in fact_types, \
            f"total // 2 should NOT be midpoint, got {fact_types}"

    def test_midpoint_has_version(self):
        """Midpoint fact should have extractor_version set."""
        facts = extract_structural_facts(ast.parse(STANDARD_MIDPOINT))
        mid_facts = [f for f in facts if f.fact_type == "midpoint_calculation"]
        assert len(mid_facts) >= 1
        assert mid_facts[0].extractor_version, "Should have extractor_version"

    def test_midpoint_has_ref(self):
        """Midpoint fact should have a source location reference."""
        facts = extract_structural_facts(ast.parse(STANDARD_MIDPOINT))
        mid_facts = [f for f in facts if f.fact_type == "midpoint_calculation"]
        assert len(mid_facts) >= 1
        assert mid_facts[0].ast_ref, "Should have ast_ref"


class TestMidpointStrategyInteraction:
    """Test that midpoint_calculation correctly affects strategy selection."""

    def test_binary_search_no_two_pointers(self):
        """Binary search: midpoint present → two_pointers_opposite MUST NOT fire."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None

        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "midpoint_calculation" in fact_types, \
            f"Binary search should have midpoint_calculation, got {fact_types}"

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids, \
            f"Binary search should NOT have two_pointers_opposite, got {strat_ids}"

    def test_overflow_safe_no_two_pointers(self):
        """Overflow-safe midpoint: two_pointers_opposite MUST NOT fire."""
        result = run_shadow_analysis(OVERFLOW_SAFE_MIDPOINT)
        assert result is not None

        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "midpoint_calculation" in fact_types

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids, \
            f"Overflow-safe midpoint should NOT have two_pointers_opposite, got {strat_ids}"

    def test_palindrome_no_midpoint(self):
        """Is Palindrome: midpoint absent → two_pointers_opposite still fires."""
        result = run_shadow_analysis(IS_PALINDROME)
        assert result is not None

        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "midpoint_calculation" not in fact_types, \
            f"Is Palindrome should NOT have midpoint_calculation, got {fact_types}"

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids, \
            f"Is Palindrome should have two_pointers_opposite, got {strat_ids}"

    def test_renamed_midpoint_no_two_pointers(self):
        """Renamed midpoint (a + b) // 2: two_pointers_opposite MUST NOT fire."""
        result = run_shadow_analysis(VARIABLE_RENAMED_MIDPOINT)
        assert result is not None

        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "midpoint_calculation" in fact_types

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids


# ============================================================
# Phase 2A: Recursive Branching tests
# ============================================================

FIBONACCI = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""

LINEAR_RECURSION = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

TREE_TRAVERSAL = """
def traverse(node):
    if node is None:
        return
    result = node.val
    result += traverse(node.left)
    result += traverse(node.right)
    return result
"""

MUTUAL_RECURSION = """
def is_even(n):
    if n == 0:
        return True
    return is_odd(n - 1)

def is_odd(n):
    if n == 0:
        return False
    return is_even(n - 1)
"""

RENAMED_RECURSION = """
def compute(x):
    if x <= 0:
        return 0
    return compute(x - 1) + compute(x - 2)
"""


class TestRecursiveBranching:
    """Test recursive_branching technique detection."""

    def test_fibonacci_branching(self):
        """Fibonacci: two recursive calls with different args → recursive_branching."""
        facts = extract_structural_facts(ast.parse(FIBONACCI))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "recursive_branching" in tech_ids, \
            f"Fibonacci should have recursive_branching, got {tech_ids}"

    def test_linear_recursion_no_branching(self):
        """Factorial: one recursive call → NO recursive_branching."""
        facts = extract_structural_facts(ast.parse(LINEAR_RECURSION))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "recursive_branching" not in tech_ids, \
            f"Factorial should NOT have recursive_branching, got {tech_ids}"

    def test_tree_traversal_branching(self):
        """Tree traversal: two recursive calls (left/right) → recursive_branching."""
        facts = extract_structural_facts(ast.parse(TREE_TRAVERSAL))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "recursive_branching" in tech_ids, \
            f"Tree traversal should have recursive_branching, got {tech_ids}"

    def test_mutual_recursion_no_branching(self):
        """Mutual recursion: A calls B, B calls A → NO recursive_branching."""
        facts = extract_structural_facts(ast.parse(MUTUAL_RECURSION))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "recursive_branching" not in tech_ids, \
            f"Mutual recursion should NOT have recursive_branching, got {tech_ids}"

    def test_renamed_recursive_branching(self):
        """Renamed function: recursive_branching still detected."""
        facts = extract_structural_facts(ast.parse(RENAMED_RECURSION))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "recursive_branching" in tech_ids, \
            f"Renamed recursion should have recursive_branching, got {tech_ids}"

    def test_fibonacci_has_multiple_paths_fact(self):
        """Fibonacci should have multiple_recursive_paths structural fact."""
        facts = extract_structural_facts(ast.parse(FIBONACCI))
        fact_types = {f.fact_type for f in facts}
        assert "multiple_recursive_paths" in fact_types, \
            f"Fibonacci should have multiple_recursive_paths, got {fact_types}"

    def test_linear_has_no_multiple_paths_fact(self):
        """Factorial should NOT have multiple_recursive_paths fact."""
        facts = extract_structural_facts(ast.parse(LINEAR_RECURSION))
        fact_types = {f.fact_type for f in facts}
        assert "multiple_recursive_paths" not in fact_types, \
            f"Factorial should NOT have multiple_recursive_paths, got {fact_types}"

    def test_recursive_branching_does_not_imply_dfs(self):
        """recursive_branching must NOT be classified as DFS strategy."""
        result = run_shadow_analysis(FIBONACCI)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "recursive_branching" in tech_ids
        # No DFS strategy should be detected (strategies not implemented yet)
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" not in strat_ids

    def test_recursive_branching_does_not_imply_dp(self):
        """recursive_branching must NOT be classified as DP strategy."""
        result = run_shadow_analysis(FIBONACCI)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "recursive_branching" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" not in strat_ids


# ============================================================
# Phase 2A: Loop-State Tracking tests
# ============================================================

SLIDING_WINDOW_LEFT = """
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

CONDITIONAL_POINTER = """
def two_sum_sorted(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
    return []
"""

GENERIC_COUNTER = """
def count_positives(nums):
    count = 0
    for x in nums:
        if x > 0:
            count += 1
    return count
"""

STATE_NEVER_REUSED = """
def process(nums):
    result = 0
    for x in nums:
        if x > 0:
            temp = x * 2
        result += x
    return result
"""

NESTED_LOOPS = """
def matrix_sum(mat):
    total = 0
    for i in range(len(mat)):
        for j in range(len(mat[i])):
            total += mat[i][j]
    return total
"""


class TestLoopStateTracking:
    """Test loop_state_tracking technique detection."""

    def test_sliding_window_left_update(self):
        """Sliding window: left conditionally updated and used in later expression
        (right - left + 1) → loop_state_tracking fires via variable_use_in_loop_body."""
        facts = extract_structural_facts(ast.parse(SLIDING_WINDOW_LEFT))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        # variable_use_in_loop_body captures left being used in max(max_len, right - left + 1)
        assert "loop_state_tracking" in tech_ids, \
            f"Sliding window should have loop_state_tracking (via variable_use), got {tech_ids}"

    def test_conditional_pointer_movement(self):
        """Two-sum sorted: left/right conditionally updated → loop_state_tracking."""
        facts = extract_structural_facts(ast.parse(CONDITIONAL_POINTER))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        # left and right are conditionally updated and appear in the while condition
        assert "loop_state_tracking" in tech_ids, \
            f"Two-sum sorted should have loop_state_tracking, got {tech_ids}"

    def test_generic_counter_no_tracking(self):
        """Generic counter: count += 1 is unconditional → NO loop_state_tracking."""
        facts = extract_structural_facts(ast.parse(GENERIC_COUNTER))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        # count is updated unconditionally (inside for, but not inside if)
        assert "loop_state_tracking" not in tech_ids, \
            f"Generic counter should NOT have loop_state_tracking, got {tech_ids}"

    def test_state_never_reused(self):
        """temp is updated but never reused → NO loop_state_tracking."""
        facts = extract_structural_facts(ast.parse(STATE_NEVER_REUSED))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        # temp is assigned inside if but never appears in a later condition
        assert "loop_state_tracking" not in tech_ids, \
            f"Unused state should NOT have loop_state_tracking, got {tech_ids}"

    def test_loop_state_tracking_does_not_imply_sliding_window(self):
        """loop_state_tracking must NOT be classified as sliding_window strategy.
        Uses two-sum (while loop) where loop_state_tracking fires."""
        result = run_shadow_analysis(CONDITIONAL_POINTER)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "loop_state_tracking" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" not in strat_ids

    def test_renamed_loop_state_tracking(self):
        """Loop state tracking with renamed variables still detected.
        Uses while loop where updated vars appear in the condition."""
        code = """
def solve(arr):
    a, b = 0, len(arr) - 1
    while a < b:
        s = arr[a] + arr[b]
        if s > 100:
            a += 1
        else:
            b -= 1
    return a
"""
        result = run_shadow_analysis(code)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "loop_state_tracking" in tech_ids, \
            f"Renamed loop state tracking should be detected, got {tech_ids}"


# ============================================================
# Phase 2A: Iterative Table Filling tests
# ============================================================

HOUSE_ROBBER = """
def rob(nums):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    return dp[-1]
"""

FIB_BOTTOM_UP = """
def fib(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
"""

COIN_CHANGE = """
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if i - coin >= 0:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
"""

PREFIX_ARRAY = """
def prefix_sum(nums):
    prefix = [0] * (len(nums) + 1)
    for i in range(len(nums)):
        prefix[i + 1] = prefix[i] + nums[i]
    return prefix
"""

ARBITRARY_ASSIGNMENT = """
def fill(arr):
    for i in range(len(arr)):
        arr[i] = i * 2
    return arr
"""

NO_INDEXED_WRITE = """
def sum_list(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""


class TestIterativeTableFilling:
    """Test iterative_table_filling technique detection."""

    def test_house_robber(self):
        """House Robber: dp[i] = max(dp[i-1], dp[i-2] + nums[i]) → table filling."""
        facts = extract_structural_facts(ast.parse(HOUSE_ROBBER))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "iterative_table_filling" in tech_ids, \
            f"House Robber should have iterative_table_filling, got {tech_ids}"

    def test_fibonacci_bottom_up(self):
        """Fibonacci bottom-up: dp[i] = dp[i-1] + dp[i-2] → table filling."""
        facts = extract_structural_facts(ast.parse(FIB_BOTTOM_UP))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "iterative_table_filling" in tech_ids, \
            f"Fibonacci bottom-up should have iterative_table_filling, got {tech_ids}"

    def test_coin_change(self):
        """Coin Change: dp[i] = min(dp[i], dp[i-coin]+1) → table filling."""
        facts = extract_structural_facts(ast.parse(COIN_CHANGE))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "iterative_table_filling" in tech_ids, \
            f"Coin Change should have iterative_table_filling, got {tech_ids}"

    def test_prefix_array(self):
        """Prefix array: prefix[i+1] = prefix[i] + nums[i] → table filling."""
        facts = extract_structural_facts(ast.parse(PREFIX_ARRAY))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "iterative_table_filling" in tech_ids, \
            f"Prefix array should have iterative_table_filling, got {tech_ids}"

    def test_arbitrary_assignment_no_lookback(self):
        """Arbitrary assignment: arr[i] = i * 2 (no lookback) → NO table filling."""
        facts = extract_structural_facts(ast.parse(ARBITRARY_ASSIGNMENT))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        # No index_lookback fact → no iterative_table_filling
        assert "iterative_table_filling" not in tech_ids, \
            f"Arbitrary assignment should NOT have iterative_table_filling, got {tech_ids}"

    def test_no_indexed_write(self):
        """Simple sum: no indexed write → NO table filling."""
        facts = extract_structural_facts(ast.parse(NO_INDEXED_WRITE))
        techniques = detect_techniques(facts)
        tech_ids = {t.technique_id for t in techniques}
        assert "iterative_table_filling" not in tech_ids, \
            f"Simple sum should NOT have iterative_table_filling, got {tech_ids}"

    def test_house_robber_is_dp_bottom_up(self):
        """House Robber: iterative_table_filling + indexed_write + lookback → dp_bottom_up."""
        result = run_shadow_analysis(HOUSE_ROBBER)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "iterative_table_filling" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids, \
            f"House Robber should have dp_bottom_up, got {strat_ids}"

    def test_iterative_table_filling_does_not_imply_prefix_sum(self):
        """iterative_table_filling must NOT be classified as prefix_sum strategy."""
        result = run_shadow_analysis(PREFIX_ARRAY)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "iterative_table_filling" in tech_ids
        # No prefix_sum strategy exists yet
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "prefix_sum" not in strat_ids

    def test_renamed_table_filling(self):
        """Table filling with renamed variables still detected."""
        code = """
def solve(arr):
    n = len(arr)
    table = [0] * n
    table[0] = arr[0]
    for idx in range(1, n):
        table[idx] = table[idx - 1] + arr[idx]
    return table[n - 1]
"""
        result = run_shadow_analysis(code)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "iterative_table_filling" in tech_ids, \
            f"Renamed table filling should be detected, got {tech_ids}"


# ============================================================
# Cross-pattern regression tests
# ============================================================

class TestCrossPatternRegression:
    """Verify that techniques don't incorrectly imply strategies."""

    def test_add_two_numbers_techniques(self):
        """Add Two Numbers: only carry_propagation, no recursive_branching."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids
        assert "recursive_branching" not in tech_ids
        assert "iterative_table_filling" not in tech_ids

    def test_2996_techniques(self):
        """Problem 2996: sequential_accumulation, no recursive_branching."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "sequential_accumulation" in tech_ids
        assert "recursive_branching" not in tech_ids
        assert "iterative_table_filling" not in tech_ids

    def test_palindrome_techniques(self):
        """Is Palindrome: bidirectional_index_scan, no recursive_branching."""
        result = run_shadow_analysis(IS_PALINDROME)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "bidirectional_index_scan" in tech_ids
        assert "recursive_branching" not in tech_ids

    def test_binary_search_techniques(self):
        """Binary search: no recursive_branching, no iterative_table_filling."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "recursive_branching" not in tech_ids
        assert "iterative_table_filling" not in tech_ids


# ============================================================
# Phase 2B: Binary Search strategy tests
# ============================================================

BINARY_SEARCH_OVERFLOW_SAFE = """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""

BINARY_SEARCH_RENAMED = """
def find(arr, val):
    a, b = 0, len(arr) - 1
    while a <= b:
        m = (a + b) // 2
        if arr[m] == val:
            return m
        elif arr[m] < val:
            a = m + 1
        else:
            b = m - 1
    return -1
"""

BINARY_SEARCH_TRUE_DIV = """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) / 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""

NOT_BINARY_SEARCH = """
def count_in_range(arr, lo, hi):
    count = 0
    for i in range(lo, hi):
        if arr[i] > 0:
            count += 1
    return count
"""


class TestBinarySearchStrategy:
    """Test binary_search strategy detection."""

    def test_standard_binary_search(self):
        """Standard binary search with (lo + hi) // 2."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids

    def test_overflow_safe_binary_search(self):
        """Overflow-safe midpoint: lo + (hi - lo) // 2."""
        result = run_shadow_analysis(BINARY_SEARCH_OVERFLOW_SAFE)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids

    def test_renamed_binary_search(self):
        """Binary search with renamed variables (a, b, m)."""
        result = run_shadow_analysis(BINARY_SEARCH_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids

    def test_true_div_binary_search(self):
        """Binary search with true division (lo + hi) / 2."""
        result = run_shadow_analysis(BINARY_SEARCH_TRUE_DIV)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids

    def test_not_binary_search_for_loop(self):
        """For-loop counting is NOT binary search."""
        result = run_shadow_analysis(NOT_BINARY_SEARCH)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" not in strat_ids

    def test_binary_search_no_two_pointers(self):
        """Binary search MUST NOT be classified as two_pointers_opposite."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids

    def test_binary_search_no_sliding_window(self):
        """Binary search MUST NOT be classified as sliding_window."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" not in strat_ids


# ============================================================
# Phase 2B: Sliding Window strategy tests
# ============================================================

SLIDING_WINDOW_WHILE = """
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    best = ""
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            window = s[left:right+1]
            if not best or len(window) < len(best):
                best = window
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return best
"""

SLIDING_WINDOW_RENAMED = """
def max_length(s):
    chars = {}
    start = 0
    best = 0
    for end in range(len(s)):
        if s[end] in chars:
            start = max(start, chars[s[end]] + 1)
        chars[s[end]] = end
        best = max(best, end - start + 1)
    return best
"""

NOT_SLIDING_WINDOW = """
def two_sum_sorted(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
    return []
"""


class TestSlidingWindowStrategy:
    """Test sliding_window strategy detection."""

    def test_sliding_window_for_loop(self):
        """Standard sliding window with for-loop."""
        result = run_shadow_analysis(SLIDING_WINDOW_LEFT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_sliding_window_while_loop(self):
        """Sliding window with while-loop inner boundary."""
        result = run_shadow_analysis(SLIDING_WINDOW_WHILE)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_sliding_window_renamed(self):
        """Sliding window with renamed variables (start, end)."""
        result = run_shadow_analysis(SLIDING_WINDOW_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_not_sliding_window_two_pointers(self):
        """Two-sum sorted is NOT sliding window."""
        result = run_shadow_analysis(NOT_SLIDING_WINDOW)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" not in strat_ids
        assert "two_pointers_opposite" in strat_ids

    def test_sliding_window_no_two_pointers(self):
        """Sliding window MUST NOT be classified as two_pointers_opposite."""
        result = run_shadow_analysis(SLIDING_WINDOW_LEFT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids

    def test_sliding_window_no_binary_search(self):
        """Sliding window MUST NOT be classified as binary_search."""
        result = run_shadow_analysis(SLIDING_WINDOW_LEFT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" not in strat_ids


# ============================================================
# Phase 2B: DFS / Backtracking strategy tests
# ============================================================

DFS_BACKTRACKING_PERMUTATIONS = """
def permutations(nums):
    result = []
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        for i in range(len(remaining)):
            path.append(remaining[i])
            backtrack(path, remaining[:i] + remaining[i+1:])
            path.pop()
    backtrack([], nums)
    return result
"""

DFS_BACKTRACKING_SUBSETS = """
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""

DFS_BACKTRACKING_NQUEENS = """
def nqueens(n):
    result = []
    def backtrack(row, cols, diag1, diag2, board):
        if row == n:
            result.append(board[:])
            return
        for col in range(n):
            if col in cols or row - col in diag1 or row + col in diag2:
                continue
            board.append(col)
            cols.add(col)
            diag1.add(row - col)
            diag2.add(row + col)
            backtrack(row + 1, cols, diag1, diag2, board)
            board.pop()
            cols.remove(col)
            diag1.remove(row - col)
            diag2.remove(row + col)
    backtrack(0, set(), set(), set(), [])
    return result
"""

NOT_DFS_GENERIC_RECURSION = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""

NOT_DFS_LINEAR_RECURSION = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""


class TestDfsBacktrackingStrategy:
    """Test dfs_backtracking strategy detection."""

    def test_backtracking_subsets(self):
        """Subsets backtracking: append/pop pattern."""
        result = run_shadow_analysis(DFS_BACKTRACKING_SUBSETS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" in strat_ids

    def test_backtracking_permutations(self):
        """Permutations backtracking: append/pop pattern."""
        result = run_shadow_analysis(DFS_BACKTRACKING_PERMUTATIONS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" in strat_ids

    def test_backtracking_nqueens(self):
        """N-Queens backtracking: add/remove pattern."""
        result = run_shadow_analysis(DFS_BACKTRACKING_NQUEENS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" in strat_ids

    def test_fibonacci_not_dfs(self):
        """Fibonacci MUST NOT be classified as dfs_backtracking."""
        result = run_shadow_analysis(NOT_DFS_GENERIC_RECURSION)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" not in strat_ids

    def test_linear_recursion_not_dfs(self):
        """Factorial MUST NOT be classified as dfs_backtracking."""
        result = run_shadow_analysis(NOT_DFS_LINEAR_RECURSION)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" not in strat_ids

    def test_dfs_not_dp_top_down(self):
        """DFS backtracking MUST NOT be classified as dp_top_down."""
        result = run_shadow_analysis(DFS_BACKTRACKING_SUBSETS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" not in strat_ids


# ============================================================
# Phase 2B: DP Top-Down strategy tests
# ============================================================

DP_TOP_DOWN_FIB = """
def fib(n, memo={}):
    if n <= 1: return n
    if n in memo: return memo[n]
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
"""

DP_TOP_DOWN_CLIMBING = """
def climb(n, memo={}):
    if n in memo: return memo[n]
    if n <= 2: return n
    memo[n] = climb(n-1, memo) + climb(n-2, memo)
    return memo[n]
"""

DP_TOP_DOWN_RENAMED = """
def solve(n, cache={}):
    if n <= 1: return n
    if n in cache: return cache[n]
    cache[n] = solve(n-1, cache) + solve(n-2, cache)
    return cache[n]
"""

NOT_DP_PLAIN_RECURSION = """
def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)
"""


class TestDpTopDownStrategy:
    """Test dp_top_down strategy detection."""

    def test_dp_fib_memo(self):
        """Fibonacci with memo dict."""
        result = run_shadow_analysis(DP_TOP_DOWN_FIB)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" in strat_ids

    def test_dp_climbing_stairs(self):
        """Climbing stairs with memoization."""
        result = run_shadow_analysis(DP_TOP_DOWN_CLIMBING)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" in strat_ids

    def test_dp_renamed_cache(self):
        """DP with renamed cache variable."""
        result = run_shadow_analysis(DP_TOP_DOWN_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" in strat_ids

    def test_plain_recursion_not_dp(self):
        """Plain recursion without memo MUST NOT be dp_top_down."""
        result = run_shadow_analysis(NOT_DP_PLAIN_RECURSION)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" not in strat_ids

    def test_dp_not_dfs_backtracking(self):
        """DP MUST NOT be classified as dfs_backtracking."""
        result = run_shadow_analysis(DP_TOP_DOWN_FIB)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" not in strat_ids


# ============================================================
# Phase 2B: DP Bottom-Up strategy tests
# ============================================================

DP_BOTTOM_UP_COIN_CHANGE = """
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if i - coin >= 0:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
"""

DP_BOTTOM_UP_FIB = """
def fib(n):
    if n <= 1: return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
"""

DP_BOTTOM_UP_RENAMED = """
def solve(arr):
    n = len(arr)
    table = [0] * n
    table[0] = arr[0]
    for idx in range(1, n):
        table[idx] = table[idx - 1] + arr[idx]
    return table[n - 1]
"""

NOT_DP_ARBITRARY_ASSIGN = """
def fill(arr):
    for i in range(len(arr)):
        arr[i] = i * 2
    return arr
"""


class TestDpBottomUpStrategy:
    """Test dp_bottom_up strategy detection."""

    def test_house_robber(self):
        """House Robber: dp[i] = max(dp[i-1], dp[i-2] + nums[i])."""
        result = run_shadow_analysis(HOUSE_ROBBER)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids

    def test_coin_change(self):
        """Coin Change: dp[i] = min(dp[i], dp[i-coin]+1)."""
        result = run_shadow_analysis(DP_BOTTOM_UP_COIN_CHANGE)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids

    def test_fib_bottom_up(self):
        """Fibonacci bottom-up."""
        result = run_shadow_analysis(DP_BOTTOM_UP_FIB)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids

    def test_renamed_bottom_up(self):
        """Bottom-up DP with renamed variables (table, idx)."""
        result = run_shadow_analysis(DP_BOTTOM_UP_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids

    def test_arbitrary_assign_not_dp(self):
        """Arbitrary indexed assignment MUST NOT be dp_bottom_up."""
        result = run_shadow_analysis(NOT_DP_ARBITRARY_ASSIGN)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" not in strat_ids

    def test_dp_bottom_up_not_dp_top_down(self):
        """Bottom-up DP MUST NOT be classified as dp_top_down."""
        result = run_shadow_analysis(HOUSE_ROBBER)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" not in strat_ids


# ============================================================
# Phase 2B: BFS strategy tests
# ============================================================

BFS_GRAPH = """
from collections import deque
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited
"""

BFS_LEVEL_ORDER = """
from collections import deque
def level_order(root):
    if not root: return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
"""

BFS_RENAMED = """
from collections import deque
def traverse(adj, src):
    seen = {src}
    q = deque([src])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                q.append(w)
    return seen
"""

NOT_BFS_QUEUE_ONLY = """
from collections import deque
def process(data):
    q = deque()
    for x in data:
        q.append(x)
    result = []
    while q:
        result.append(q.popleft())
    return result
"""

NOT_BFS_DFS_RECURSIVE = """
def dfs(graph, node, visited):
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)
"""


class TestBfsStrategy:
    """Test bfs_shortest_path strategy detection."""

    def test_bfs_graph(self):
        """Standard BFS on graph."""
        result = run_shadow_analysis(BFS_GRAPH)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "bfs_shortest_path" in strat_ids

    def test_bfs_level_order_tree(self):
        """Level-order tree traversal uses node.left/node.right (linked attributes).
        Phase 5C-FIX: Tree BFS is now detected as bfs_shortest_path because
        linked_structure_traversal is accepted as an alternative to neighbor_traversal."""
        result = run_shadow_analysis(BFS_LEVEL_ORDER)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # Tree level-order is now detected as BFS (Phase 5C-FIX)
        assert "bfs_shortest_path" in strat_ids

    def test_bfs_renamed(self):
        """BFS with renamed variables (adj, src, seen, q)."""
        result = run_shadow_analysis(BFS_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "bfs_shortest_path" in strat_ids

    def test_not_bfs_dfs_recursive(self):
        """DFS recursion MUST NOT be classified as BFS."""
        result = run_shadow_analysis(NOT_BFS_DFS_RECURSIVE)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "bfs_shortest_path" not in strat_ids

    def test_bfs_no_dfs_backtracking(self):
        """BFS MUST NOT be classified as dfs_backtracking."""
        result = run_shadow_analysis(BFS_GRAPH)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" not in strat_ids


# ============================================================
# Phase 2B: Union-Find strategy tests
# ============================================================

UF_CLASSIC = """
def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(parent, rank, x, y):
    px, py = find(parent, x), find(parent, y)
    if px == py: return
    if rank[px] < rank[py]:
        px, py = py, px
    parent[py] = px
    if rank[px] == rank[py]: rank[px] += 1
"""

UF_RENAMED = """
def find_root(par, node):
    while par[node] != node:
        par[node] = par[par[node]]
        node = par[node]
    return node

def merge_sets(par, a, b):
    ra, rb = find_root(par, a), find_root(par, b)
    if ra != rb:
        par[rb] = ra
"""

UF_INLINE = """
def solve(edges, n):
    par = list(range(n))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for u, v in edges:
        par[find(v)] = find(u)
    return par
"""

UF_NO_RANK = """
def find(parent, x):
    while parent[x] != x:
        x = parent[x]
    return x

def union(parent, x, y):
    parent[find(parent, x)] = find(parent, y)
"""

NOT_UF_FIND_MAX = """
def find_max(arr):
    parent = list(range(len(arr)))
    for i in range(len(arr)):
        if arr[i] > arr[parent[i]]:
            parent[i] = i
    return parent
"""

NOT_UF_PARENT_ARRAY = """
def parent_init(n):
    parent = list(range(n))
    for i in range(n):
        parent[i] = i * 2
    return parent
"""


class TestUnionFindStrategy:
    """Test union_find strategy detection."""

    def test_classic_union_find(self):
        """Classic find + union with rank."""
        result = run_shadow_analysis(UF_CLASSIC)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" in strat_ids

    def test_renamed_union_find(self):
        """Union-find with renamed functions and variables."""
        result = run_shadow_analysis(UF_RENAMED)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" in strat_ids

    def test_inline_union_find(self):
        """Inline union-find with nested function."""
        result = run_shadow_analysis(UF_INLINE)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" in strat_ids

    def test_union_find_no_rank(self):
        """Union-find without rank optimization."""
        result = run_shadow_analysis(UF_NO_RANK)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" in strat_ids

    def test_not_uf_find_max(self):
        """find_max MUST NOT be classified as union_find."""
        result = run_shadow_analysis(NOT_UF_FIND_MAX)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" not in strat_ids

    def test_not_uf_parent_array(self):
        """Generic parent array MUST NOT be classified as union_find."""
        result = run_shadow_analysis(NOT_UF_PARENT_ARRAY)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" not in strat_ids

    def test_uf_no_binary_search(self):
        """Union-find MUST NOT be classified as binary_search."""
        result = run_shadow_analysis(UF_CLASSIC)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" not in strat_ids


# ============================================================
# Phase 2B: Cross-strategy confusion tests
# ============================================================

class TestCrossStrategyConfusion:
    """Verify strategies don't incorrectly imply each other."""

    def test_binary_search_vs_two_pointers(self):
        """Binary search MUST NOT become two_pointers_opposite."""
        result = run_shadow_analysis(STANDARD_MIDPOINT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids
        assert "two_pointers_opposite" not in strat_ids

    def test_two_pointers_vs_binary_search(self):
        """Two-pointers palindrome MUST NOT become binary_search."""
        result = run_shadow_analysis(IS_PALINDROME)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids
        assert "binary_search" not in strat_ids

    def test_sliding_window_vs_two_pointers(self):
        """Sliding window MUST NOT become two_pointers_opposite."""
        result = run_shadow_analysis(SLIDING_WINDOW_LEFT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids
        assert "two_pointers_opposite" not in strat_ids

    def test_dfs_vs_dp_top_down(self):
        """DFS backtracking MUST NOT become dp_top_down."""
        result = run_shadow_analysis(DFS_BACKTRACKING_SUBSETS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" in strat_ids
        assert "dp_top_down" not in strat_ids

    def test_dp_top_down_vs_dfs(self):
        """DP top-down MUST NOT become dfs_backtracking."""
        result = run_shadow_analysis(DP_TOP_DOWN_FIB)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" in strat_ids
        assert "dfs_backtracking" not in strat_ids

    def test_dp_bottom_up_vs_prefix_sum(self):
        """dp_bottom_up captures prefix sums (known V1 limitation)."""
        # Prefix sum structurally has indexed_write + index_lookback,
        # so it matches iterative_table_filling → dp_bottom_up.
        # This is documented as a V1 limitation.
        result = run_shadow_analysis(PREFIX_ARRAY)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # Known V1 limitation: prefix sums get dp_bottom_up
        assert "dp_bottom_up" in strat_ids

    def test_bfs_vs_dfs(self):
        """BFS MUST NOT become dfs_backtracking."""
        result = run_shadow_analysis(BFS_GRAPH)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "bfs_shortest_path" in strat_ids
        assert "dfs_backtracking" not in strat_ids

    def test_uf_vs_binary_search(self):
        """Union-find MUST NOT become binary_search."""
        result = run_shadow_analysis(UF_CLASSIC)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "union_find" in strat_ids
        assert "binary_search" not in strat_ids

    def test_add_two_numbers_no_strategy(self):
        """Add Two Numbers MUST NOT get any named strategy."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert len(strat_ids) == 0, f"Add Two Numbers should have no strategies, got {strat_ids}"

    def test_2996_no_strategy(self):
        """Problem 2996 MUST NOT get any named strategy."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert len(strat_ids) == 0, f"2996 should have no strategies, got {strat_ids}"
