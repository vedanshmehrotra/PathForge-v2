"""Phase 5B tests: semantic coherence validation and authority upgrade metadata.

Tests:
- Strategy compatibility metadata
- Group coherence validation (valid/rejected/warning)
- Authority upgrade metadata infrastructure
- Regression on existing behavior
"""
import json
import pytest

from pathforge.ast_analysis.shadow.coherence import (
    STRATEGY_COMPATIBILITY,
    get_strategy_compatibility,
    check_mutual_exclusion,
    check_unsatisfiable_combinations,
)
from pathforge.ast_analysis.shadow.authority import (
    AuthorityUpgradeRecord,
    validate_upgrade_record,
    create_upgrade_record,
    serialize_upgrade_history,
    deserialize_upgrade_history,
    VALID_TIER_TRANSITIONS,
    EVIDENCE_SOURCE_TYPES,
)
from pathforge.services.ground_truth_builder import (
    _validate_group,
    validate_solution_groups,
    VALID_V1_CONCEPTS,
)


# ============================================================
# Test strategy compatibility metadata
# ============================================================

class TestStrategyCompatibility:
    """Test strategy compatibility metadata."""

    def test_all_strategies_have_metadata(self):
        """Every strategy in VALID_V1_CONCEPTS should have compatibility metadata."""
        from pathforge.services.ground_truth_builder import VALID_STRATEGIES
        for strategy_id in VALID_STRATEGIES:
            compat = get_strategy_compatibility(strategy_id)
            assert compat is not None, f"Strategy '{strategy_id}' has no compatibility metadata"
            assert "mutually_exclusive_with" in compat
            assert "compatible_with" in compat
            assert "reason" in compat

    def test_dfs_backtracking_excludes_dp_top_down(self):
        """dfs_backtracking and dp_top_down are mutually exclusive."""
        compat = get_strategy_compatibility("dfs_backtracking")
        assert "dp_top_down" in compat["mutually_exclusive_with"]

    def test_dp_top_down_excludes_dfs_backtracking(self):
        """dp_top_down and dfs_backtracking are mutually exclusive (symmetric)."""
        compat = get_strategy_compatibility("dp_top_down")
        assert "dfs_backtracking" in compat["mutually_exclusive_with"]

    def test_binary_search_not_mutually_exclusive_with_two_pointers(self):
        """binary_search and two_pointers_opposite are NOT mutually exclusive
        (they have evaluator-level conflicts, not definition contradictions)."""
        compat = get_strategy_compatibility("binary_search")
        assert "two_pointers_opposite" not in compat["mutually_exclusive_with"]

    def test_sliding_window_not_mutually_exclusive_with_anything(self):
        """sliding_window has no mutual exclusions."""
        compat = get_strategy_compatibility("sliding_window")
        assert len(compat["mutually_exclusive_with"]) == 0


# ============================================================
# Test mutual exclusion detection
# ============================================================

class TestMutualExclusion:
    """Test mutual exclusion detection in required strategies."""

    def test_dfs_backtracking_and_dp_top_down_conflict(self):
        """Requiring both dfs_backtracking and dp_top_down should conflict."""
        conflicts = check_mutual_exclusion(["dfs_backtracking", "dp_top_down"])
        assert len(conflicts) == 1
        pair = set([conflicts[0][0], conflicts[0][1]])
        assert pair == {"dfs_backtracking", "dp_top_down"}

    def test_no_conflict_for_compatible_strategies(self):
        """Requiring compatible strategies should not conflict."""
        conflicts = check_mutual_exclusion(["binary_search", "union_find"])
        assert len(conflicts) == 0

    def test_no_conflict_for_single_strategy(self):
        """Single strategy should not conflict with itself."""
        conflicts = check_mutual_exclusion(["dfs_backtracking"])
        assert len(conflicts) == 0

    def test_empty_list_no_conflict(self):
        """Empty list should not conflict."""
        conflicts = check_mutual_exclusion([])
        assert len(conflicts) == 0


# ============================================================
# Test unsatisfiable combination detection
# ============================================================

class TestUnsatisfiableCombinations:
    """Test unsatisfiable combination detection (warnings, not rejections)."""

    def test_binary_search_and_two_pointers_unsatisfiable(self):
        """binary_search + two_pointers_opposite is unsatisfiable."""
        warnings = check_unsatisfiable_combinations(["binary_search", "two_pointers_opposite"])
        assert len(warnings) >= 1
        # Should mention both strategies
        combined = " ".join([w[2] for w in warnings])
        assert "binary_search" in combined
        assert "two_pointers_opposite" in combined

    def test_binary_search_and_sliding_window_unsatisfiable(self):
        """binary_search + sliding_window is unsatisfiable."""
        warnings = check_unsatisfiable_combinations(["binary_search", "sliding_window"])
        assert len(warnings) >= 1

    def test_no_warning_for_compatible_strategies(self):
        """Compatible strategies should not produce warnings."""
        warnings = check_unsatisfiable_combinations(["binary_search", "union_find"])
        assert len(warnings) == 0


# ============================================================
# Test group validation with coherence
# ============================================================

class TestGroupCoherenceValidation:
    """Test group validation with semantic coherence checks."""

    def test_valid_single_strategy(self):
        """Single strategy group should be valid."""
        group = {
            "required": ["binary_search"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True
        assert len(result.get("warnings", [])) == 0

    def test_valid_compatible_strategies(self):
        """Compatible strategies should be valid."""
        group = {
            "required": ["binary_search", "union_find"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True

    def test_rejected_mutually_exclusive(self):
        """Mutually exclusive strategies should be rejected."""
        group = {
            "required": ["dfs_backtracking", "dp_top_down"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "mutually exclusive" in result["reason"]

    def test_warning_unsatisfiable_combination(self):
        """Unsatisfiable combination should produce warning, not rejection."""
        group = {
            "required": ["binary_search", "two_pointers_opposite"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True
        assert len(result.get("warnings", [])) >= 1
        assert "unsatisfiable" in result["warnings"][0].lower()

    def test_invalid_id_still_rejects(self):
        """Invalid concept ID should still be rejected."""
        group = {
            "required": ["nonexistent_concept"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "not in V1 vocabulary" in result["reason"]

    def test_required_excluded_conflict_still_rejects(self):
        """Required/excluded conflict should still be rejected."""
        group = {
            "required": ["binary_search"],
            "optional": [],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "both required and excluded" in result["reason"]

    def test_optional_excluded_conflict_still_rejects(self):
        """Optional/excluded conflict should still be rejected."""
        group = {
            "required": [],
            "optional": ["binary_search"],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "both optional and excluded" in result["reason"]

    def test_validate_solution_groups_with_warnings(self):
        """validate_solution_groups should mark warnings correctly."""
        groups = [
            {
                "required": ["binary_search", "two_pointers_opposite"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]
        validated = validate_solution_groups(groups)
        assert len(validated) == 1
        assert validated[0]["validation"] == "warning"
        assert "validation_warnings" in validated[0]

    def test_validate_solution_groups_with_rejections(self):
        """validate_solution_groups should mark rejections correctly."""
        groups = [
            {
                "required": ["dfs_backtracking", "dp_top_down"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]
        validated = validate_solution_groups(groups)
        assert len(validated) == 1
        assert validated[0]["validation"] == "rejected"


# ============================================================
# Test authority upgrade metadata
# ============================================================

class TestAuthorityUpgradeMetadata:
    """Test authority upgrade metadata infrastructure."""

    def test_create_valid_upgrade_record(self):
        """Creating a valid upgrade record should succeed."""
        record = create_upgrade_record(
            group_id="group_0",
            problem_id=42,
            previous_tier="llm_proposed",
            new_tier="structurally_observed",
            evidence_sources=["submission_cluster"],
            actor="system",
            reason="5 independent submissions match",
        )
        assert record.group_id == "group_0"
        assert record.problem_id == 42
        assert record.previous_tier == "llm_proposed"
        assert record.new_tier == "structurally_observed"

    def test_create_upgrade_record_invalid_tier(self):
        """Creating upgrade with invalid tier should raise ValueError."""
        with pytest.raises(ValueError, match="not valid"):
            create_upgrade_record(
                group_id="group_0",
                problem_id=42,
                previous_tier="invalid_tier",
                new_tier="structurally_observed",
                evidence_sources=["submission_cluster"],
                actor="system",
                reason="test",
            )

    def test_create_upgrade_record_invalid_transition(self):
        """Creating upgrade with invalid transition should raise ValueError."""
        with pytest.raises(ValueError, match="not allowed"):
            create_upgrade_record(
                group_id="group_0",
                problem_id=42,
                previous_tier="reviewed",
                new_tier="llm_proposed",
                evidence_sources=["submission_cluster"],
                actor="system",
                reason="downgrade not allowed",
            )

    def test_create_upgrade_record_no_evidence(self):
        """Creating upgrade without evidence should raise ValueError."""
        with pytest.raises(ValueError, match="evidence_sources cannot be empty"):
            create_upgrade_record(
                group_id="group_0",
                problem_id=42,
                previous_tier="llm_proposed",
                new_tier="structurally_observed",
                evidence_sources=[],
                actor="system",
                reason="test",
            )

    def test_create_upgrade_record_no_reason(self):
        """Creating upgrade without reason should raise ValueError."""
        with pytest.raises(ValueError, match="reason is required"):
            create_upgrade_record(
                group_id="group_0",
                problem_id=42,
                previous_tier="llm_proposed",
                new_tier="structurally_observed",
                evidence_sources=["submission_cluster"],
                actor="system",
                reason="",
            )

    def test_upgrade_record_serialize_deserialize(self):
        """Upgrade record should survive JSON round-trip."""
        record = AuthorityUpgradeRecord(
            group_id="group_0",
            problem_id=42,
            previous_tier="llm_proposed",
            new_tier="structurally_observed",
            evidence_sources=["submission_cluster", "submission_independence"],
            timestamp="2026-08-22T12:00:00",
            actor="system",
            reason="5 independent submissions match",
        )
        json_str = record.to_json()
        restored = AuthorityUpgradeRecord.from_json(json_str)

        assert restored.group_id == record.group_id
        assert restored.problem_id == record.problem_id
        assert restored.previous_tier == record.previous_tier
        assert restored.new_tier == record.new_tier
        assert restored.evidence_sources == record.evidence_sources
        assert restored.timestamp == record.timestamp
        assert restored.actor == record.actor
        assert restored.reason == record.reason

    def test_upgrade_history_serialize_deserialize(self):
        """Upgrade history should survive JSON round-trip."""
        records = [
            AuthorityUpgradeRecord(
                group_id="group_0",
                problem_id=42,
                previous_tier="llm_proposed",
                new_tier="structurally_observed",
                evidence_sources=["submission_cluster"],
                timestamp="2026-08-22T12:00:00",
                actor="system",
                reason="first upgrade",
            ),
            AuthorityUpgradeRecord(
                group_id="group_0",
                problem_id=42,
                previous_tier="structurally_observed",
                new_tier="editorial",
                evidence_sources=["human_review"],
                timestamp="2026-08-22T13:00:00",
                actor="admin",
                reason="second upgrade",
            ),
        ]
        json_str = serialize_upgrade_history(records)
        restored = deserialize_upgrade_history(json_str)

        assert len(restored) == 2
        assert restored[0].previous_tier == "llm_proposed"
        assert restored[1].previous_tier == "structurally_observed"

    def test_empty_history_serialize(self):
        """Empty history should serialize to empty JSON array."""
        json_str = serialize_upgrade_history([])
        assert json_str == "[]"

    def test_empty_history_deserialize(self):
        """Empty/None history should deserialize to empty list."""
        assert deserialize_upgrade_history("") == []
        assert deserialize_upgrade_history("[]") == []

    def test_valid_transitions_all_allowed(self):
        """All defined transitions should be valid."""
        for from_tier, to_tier in VALID_TIER_TRANSITIONS:
            record = AuthorityUpgradeRecord(
                group_id="g",
                problem_id=1,
                previous_tier=from_tier,
                new_tier=to_tier,
                evidence_sources=["test"],
                reason="test",
            )
            result = validate_upgrade_record(record)
            assert result["valid"], f"Transition {from_tier} → {to_tier} should be valid"

    def test_no_automatic_upgrade_from_submission(self):
        """Verify that no automatic upgrade logic exists in the codebase.

        This is a structural test — we verify that the authority module
        does not contain any function that takes a submission and returns
        an upgrade record without explicit external evidence.
        """
        import pathforge.ast_analysis.shadow.authority as auth_module
        # The module should not have any function named 'auto_upgrade' or similar
        public_functions = [f for f in dir(auth_module) if not f.startswith('_')]
        auto_functions = [f for f in public_functions if 'auto' in f.lower() or 'promote' in f.lower()]
        assert len(auto_functions) == 0, f"Found auto-promotion functions: {auto_functions}"

    def test_evidence_source_types_defined(self):
        """Evidence source types should be defined for future use."""
        assert len(EVIDENCE_SOURCE_TYPES) > 0
        assert "submission_cluster" in EVIDENCE_SOURCE_TYPES
        assert "human_review" in EVIDENCE_SOURCE_TYPES


# ============================================================
# Test cross-pattern regression
# ============================================================

class TestPhase5BCrossPatternRegression:
    """Verify existing behavior is unchanged after Phase 5B changes."""

    def test_binary_search_still_validates(self):
        """binary_search group should still validate as accepted."""
        group = {
            "required": ["binary_search"],
            "optional": [],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True
        assert len(result.get("warnings", [])) == 0

    def test_dfs_backtracking_with_dp_excluded_validates(self):
        """dfs_backtracking + dp_top_down in excluded should still work."""
        group = {
            "required": ["dfs_backtracking"],
            "optional": ["recursive_branching"],
            "excluded": ["dp_top_down"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True

    def test_monotonic_stack_validates(self):
        """monotonic_stack_strategy should validate."""
        group = {
            "required": ["monotonic_stack_strategy"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True

    def test_linked_list_traversal_validates(self):
        """linked_list_traversal technique should validate."""
        group = {
            "required": ["linked_list_traversal"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True
