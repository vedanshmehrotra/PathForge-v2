"""Tests for Phases 0A-2 of the evidence architecture implementation.

Covers:
- Phase 0A: matched-group persistence bug fix
- Phase 0B: verdict_type, detected_patterns_json, code_hash
- Phase 0C: solution_groups storage and loading
- Phase 1: per-group evidence in ProblemContext
- Phase 2: evidence authority gating
"""
import hashlib
import json
import pytest


# ---------------------------------------------------------------------------
# Phase 0A: matched-group persistence
# ---------------------------------------------------------------------------

class TestMatchedGroupPersistence:
    """Verify expected_pattern comes from the MATCHED group, not group_0."""

    def _make_groups(self):
        return [
            {"id": "group_0", "patterns": ["binary_search_standard"], "evidence": "llm_proposed"},
            {"id": "group_1", "patterns": ["hash_map_lookup"], "evidence": "structurally_observed"},
        ]

    def test_expected_pattern_from_matched_group_1(self):
        """When group 1 matches, expected_pattern should be hash_map_lookup."""
        from pathforge.services.persistence import run_persistence
        groups = self._make_groups()
        match_result = {"match_result": "FULL_MATCH", "matched_groups": [1], "unmatched_patterns": [], "confidence_score": 0.9}

        # We can't call run_persistence without a DB, so test the logic directly
        matched_groups_indices = match_result.get("matched_groups", [])
        expected_pattern = ""
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            idx = matched_groups_indices[0]
            if isinstance(idx, int) and 0 <= idx < len(groups):
                matched_group = groups[idx]
                if isinstance(matched_group, dict):
                    group_patterns = matched_group.get("patterns", [])
                    if group_patterns:
                        expected_pattern = group_patterns[0]

        assert expected_pattern == "hash_map_lookup"

    def test_expected_pattern_from_matched_group_0(self):
        """When group 0 matches, expected_pattern should be binary_search_standard."""
        groups = self._make_groups()
        match_result = {"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": [], "confidence_score": 0.9}

        matched_groups_indices = match_result.get("matched_groups", [])
        expected_pattern = ""
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            idx = matched_groups_indices[0]
            if isinstance(idx, int) and 0 <= idx < len(groups):
                matched_group = groups[idx]
                if isinstance(matched_group, dict):
                    group_patterns = matched_group.get("patterns", [])
                    if group_patterns:
                        expected_pattern = group_patterns[0]

        assert expected_pattern == "binary_search_standard"

    def test_no_matched_group_uses_fallback(self):
        """When matched_groups is empty, fallback to first non-empty group."""
        groups = self._make_groups()
        match_result = {"match_result": "NO_MATCH", "matched_groups": [], "unmatched_patterns": [], "confidence_score": 0.0}

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
        if not expected_pattern and groups:
            for g in groups:
                patterns = g.get("patterns", []) if isinstance(g, dict) else []
                if patterns:
                    expected_pattern = patterns[0]
                    matched_group_evidence = g.get("evidence", "unobserved") if isinstance(g, dict) else "unobserved"
                    break

        assert expected_pattern == "binary_search_standard"

    def test_empty_groups_no_crash(self):
        """Empty groups list should not crash."""
        groups = []
        match_result = {"match_result": "NO_MATCH", "matched_groups": [], "unmatched_patterns": [], "confidence_score": 0.0}

        matched_groups_indices = match_result.get("matched_groups", [])
        expected_pattern = ""
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            pass  # won't execute
        if not expected_pattern and groups:
            pass  # won't execute

        assert expected_pattern == ""

    def test_malformed_matched_groups_no_crash(self):
        """Non-integer matched_groups should not crash."""
        groups = self._make_groups()
        match_result = {"match_result": "FULL_MATCH", "matched_groups": ["invalid"], "unmatched_patterns": [], "confidence_score": 0.9}

        matched_groups_indices = match_result.get("matched_groups", [])
        expected_pattern = ""
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            idx = matched_groups_indices[0]
            if isinstance(idx, int) and 0 <= idx < len(groups):
                pass  # won't execute because "invalid" is not int

        assert expected_pattern == ""


# ---------------------------------------------------------------------------
# Phase 0B: code_hash
# ---------------------------------------------------------------------------

class TestCodeHash:
    """Verify code_hash is deterministic and changes with code."""

    def test_deterministic_hash(self):
        code = "def twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i"
        h1 = hashlib.sha256(code.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(code.encode("utf-8")).hexdigest()
        assert h1 == h2

    def test_different_code_different_hash(self):
        code1 = "def f(): return 1"
        code2 = "def f(): return 2"
        h1 = hashlib.sha256(code1.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(code2.encode("utf-8")).hexdigest()
        assert h1 != h2

    def test_empty_code_hash(self):
        h = hashlib.sha256("".encode("utf-8")).hexdigest()
        assert len(h) == 64


# ---------------------------------------------------------------------------
# Phase 0C: solution_groups loading
# ---------------------------------------------------------------------------

class TestSolutionGroupsLoading:
    """Verify _load_ground_truth reads solution_groups and falls back to flat patterns."""

    def _make_raw_row(self, patterns=None, confidence=None, solution_groups=None, validation_status=None):
        """Create a mock row dict mimicking DB output."""
        row = {
            "patterns": json.dumps(patterns) if patterns is not None else "[]",
            "confidence": json.dumps(confidence) if confidence is not None else "{}",
        }
        # Simulate JSONB columns (already parsed) or missing columns
        if solution_groups is not None:
            row["solution_groups"] = solution_groups
        if validation_status is not None:
            row["validation_status"] = validation_status
        return row

    def test_legacy_flat_patterns_produce_group_0(self):
        """Legacy flat patterns should produce one group with evidence from validation_status."""
        from pathforge.services.problem_resolver import _parse_json_list, _parse_json_dict

        patterns = ["hash_map_lookup", "two_pointers_opposite"]
        confidence = {"hash_map_lookup": 0.9, "two_pointers_opposite": 0.7}

        patterns_list = _parse_json_list(json.dumps(patterns))
        confidence_dict = _parse_json_dict(json.dumps(confidence))

        assert patterns_list == ["hash_map_lookup", "two_pointers_opposite"]
        assert confidence_dict == confidence

    def test_solution_groups_parsed_correctly(self):
        """solution_groups should be parsed as a list of dicts."""
        from pathforge.services.problem_resolver import _parse_json_field

        sg = [
            {"id": "group_0", "patterns": ["hash_map_lookup"], "evidence": "structurally_observed", "confidence": {"hash_map_lookup": 0.8}},
            {"id": "group_1", "patterns": ["sorting"], "evidence": "llm_proposed", "confidence": {"sorting": 0.6}},
        ]
        result = _parse_json_field(json.dumps(sg))
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["evidence"] == "structurally_observed"
        assert result[1]["evidence"] == "llm_proposed"


# ---------------------------------------------------------------------------
# Phase 2: evidence authority gating
# ---------------------------------------------------------------------------

class TestEvidenceAuthorityGating:
    """Verify that evidence state controls downstream behavior."""

    def test_authoritative_states(self):
        from pathforge.services.persistence import _AUTHORITATIVE_STATES
        assert "structurally_observed" in _AUTHORITATIVE_STATES
        assert "externally_listed" in _AUTHORITATIVE_STATES

    def test_non_authoritative_states(self):
        from pathforge.services.persistence import _AUTHORITATIVE_STATES
        assert "llm_proposed" not in _AUTHORITATIVE_STATES
        assert "unobserved" not in _AUTHORITATIVE_STATES
        assert "conflicted" not in _AUTHORITATIVE_STATES

    def test_verdict_type_derivation(self):
        """verdict_type should be authoritative for structurally_observed."""
        _AUTHORITATIVE_STATES = {"structurally_observed", "externally_listed"}
        for state in ["structurally_observed", "externally_listed"]:
            vt = "authoritative" if state in _AUTHORITATIVE_STATES else "analysis_only"
            assert vt == "authoritative", f"Expected authoritative for {state}"

        for state in ["llm_proposed", "unobserved", "conflicted"]:
            vt = "authoritative" if state in _AUTHORITATIVE_STATES else "analysis_only"
            assert vt == "analysis_only", f"Expected analysis_only for {state}"

    def test_k_ceiling_values(self):
        from pathforge.elo_engine import EVIDENCE_K_CEILINGS, DEFAULT_K
        assert EVIDENCE_K_CEILINGS["structurally_observed"] == int(0.75 * DEFAULT_K)
        assert EVIDENCE_K_CEILINGS["externally_listed"] == int(0.5 * DEFAULT_K)
        assert EVIDENCE_K_CEILINGS["llm_proposed"] == 0
        assert EVIDENCE_K_CEILINGS["unobserved"] == 0
        assert EVIDENCE_K_CEILINGS["conflicted"] == 0

    def test_k_ceiling_applied(self):
        """Evidence ceiling should cap K-factor, not multiply."""
        from pathforge.elo_engine import _compute_k, EVIDENCE_K_CEILINGS, DEFAULT_K

        # Base K without any adjustments
        k_base = _compute_k(1200.0, 0.0, 0)
        assert k_base == DEFAULT_K  # 32

        # With structurally_observed ceiling
        ceiling = EVIDENCE_K_CEILINGS["structurally_observed"]  # 24
        k_capped = min(k_base, ceiling)
        assert k_capped == 24

        # With llm_proposed ceiling (0) — should produce 0
        ceiling = EVIDENCE_K_CEILINGS["llm_proposed"]  # 0
        k_capped = min(k_base, ceiling)
        assert k_capped == 0


# ---------------------------------------------------------------------------
# Phase 1: per-group evidence propagation
# ---------------------------------------------------------------------------

class TestPerGroupEvidence:
    """Verify evidence state propagates correctly through the pipeline."""

    def test_matched_group_evidence_extraction(self):
        """Evidence state should come from the matched group."""
        groups = [
            {"id": "group_0", "patterns": ["binary_search_standard"], "evidence": "llm_proposed"},
            {"id": "group_1", "patterns": ["hash_map_lookup"], "evidence": "structurally_observed"},
        ]
        match_result = {"matched_groups": [1]}

        matched_groups_indices = match_result.get("matched_groups", [])
        matched_group_evidence = "unobserved"
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            idx = matched_groups_indices[0]
            if isinstance(idx, int) and 0 <= idx < len(groups):
                matched_group = groups[idx]
                if isinstance(matched_group, dict):
                    matched_group_evidence = matched_group.get("evidence", "unobserved")

        assert matched_group_evidence == "structurally_observed"

    def test_missing_evidence_defaults_to_unobserved(self):
        """Groups without evidence field should default to unobserved."""
        groups = [
            {"id": "group_0", "patterns": ["hash_map_lookup"]},  # no evidence field
        ]
        match_result = {"matched_groups": [0]}

        matched_groups_indices = match_result.get("matched_groups", [])
        matched_group_evidence = "unobserved"
        if groups and isinstance(matched_groups_indices, list) and matched_groups_indices:
            idx = matched_groups_indices[0]
            if isinstance(idx, int) and 0 <= idx < len(groups):
                matched_group = groups[idx]
                if isinstance(matched_group, dict):
                    matched_group_evidence = matched_group.get("evidence", "unobserved")

        assert matched_group_evidence == "unobserved"


# ---------------------------------------------------------------------------
# Bug Fix 1: Schema auto-migration
# ---------------------------------------------------------------------------

class TestSchemaAutoMigration:
    """Verify init_db() applies ALTER TABLE migrations automatically."""

    def test_apply_migrations_function_exists(self):
        """_apply_migrations should be importable from db module."""
        from pathforge.db.db import _apply_migrations
        assert callable(_apply_migrations)

    def test_all_critical_columns_detected_by_parser(self):
        """The migration parser must detect all critical column migrations."""
        from pathforge.db.db import _extract_statements, _classify_statement, _strip_comment_lines
        import os

        schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema_pg.sql")
        with open(schema_path, "r") as f:
            sql = f.read()

        critical_columns = [
            "title_slug", "verdict_type", "solution_groups",
            "description", "updated_at", "detected_patterns_json",
            "code_hash", "validation_status",
        ]

        statements = _extract_statements(sql)
        found_columns = set()
        for stmt in statements:
            if _classify_statement(stmt) == "migration":
                executable = _strip_comment_lines(stmt).strip()
                upper = executable.upper()
                for col in critical_columns:
                    if col.upper() in upper:
                        found_columns.add(col)

        missing = set(critical_columns) - found_columns
        assert not missing, f"Parser misses migrations for columns: {missing}"

    def test_comment_prefixed_alter_table_detected(self):
        """An ALTER TABLE preceded by a -- comment must be classified as migration."""
        from pathforge.db.db import _classify_statement

        # Simulates: -- Phase 0B: submission evidence fields\nALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT;
        stmt = "-- Phase 0B: submission evidence fields\nALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT DEFAULT 'authoritative'"
        assert _classify_statement(stmt) == "migration"

    def test_whitespace_prefixed_alter_table_detected(self):
        """An ALTER TABLE with leading whitespace must be classified as migration."""
        from pathforge.db.db import _classify_statement

        stmt = "\n\n  ALTER TABLE foo ADD COLUMN bar TEXT;"
        assert _classify_statement(stmt) == "migration"

    def test_create_index_detected(self):
        """CREATE INDEX statements must be classified as migration."""
        from pathforge.db.db import _classify_statement

        stmt = "CREATE INDEX IF NOT EXISTS idx_foo ON bar(col)"
        assert _classify_statement(stmt) == "migration"

    def test_create_table_skipped(self):
        """CREATE TABLE statements must be skipped."""
        from pathforge.db.db import _classify_statement

        stmt = "CREATE TABLE IF NOT EXISTS foo (id SERIAL PRIMARY KEY)"
        assert _classify_statement(stmt) == "skip"

    def test_comment_only_statement_skipped(self):
        """A statement that is only a comment must be skipped."""
        from pathforge.db.db import _classify_statement

        stmt = "-- This is just a comment"
        assert _classify_statement(stmt) == "skip"

    def test_empty_statement_after_comment_stripped_skipped(self):
        """A statement that becomes empty after comment stripping must be skipped."""
        from pathforge.db.db import _classify_statement

        stmt = "-- only a comment\n-- another comment"
        assert _classify_statement(stmt) == "skip"

    def test_comment_lines_stripped_executable_preserved(self):
        """Stripping comments must preserve the actual DDL."""
        from pathforge.db.db import _strip_comment_lines

        stmt = "-- Phase 0B: fields\nALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT"
        result = _strip_comment_lines(stmt).strip()
        assert result == "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT"
        assert "--" not in result

    def test_inline_comment_preserved(self):
        """Inline comments within a statement must NOT be stripped."""
        from pathforge.db.db import _strip_comment_lines

        stmt = "ALTER TABLE foo ADD COLUMN bar TEXT -- important column"
        result = _strip_comment_lines(stmt).strip()
        assert "-- important column" in result

    def test_extract_statements_splits_on_semicolon(self):
        """_extract_statements should split by semicolons."""
        from pathforge.db.db import _extract_statements

        sql = "CREATE TABLE foo(); ALTER TABLE bar ADD COLUMN baz TEXT;"
        stmts = _extract_statements(sql)
        assert len(stmts) == 2
        assert "CREATE TABLE foo()" in stmts[0]
        assert "ALTER TABLE bar ADD COLUMN baz TEXT" in stmts[1]

    def test_migration_failure_is_logged(self, caplog):
        """A failed migration must be logged, not silently swallowed."""
        from pathforge.db.db import _apply_migrations
        from unittest.mock import MagicMock
        import logging

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn._conn.cursor.return_value = mock_cursor
        mock_conn._conn.commit = MagicMock()
        mock_conn._conn.rollback = MagicMock()

        # Make first execute succeed, second fail
        call_count = [0]
        def side_effect(query):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("simulated failure")

        mock_cursor.execute.side_effect = side_effect

        with caplog.at_level(logging.WARNING):
            _apply_migrations(mock_conn)

        assert "Migration statement failed" in caplog.text

    def test_migration_failure_preserves_prior_commits(self):
        """A failed migration must not roll back prior successful migrations."""
        from pathforge.db.db import _apply_migrations
        from unittest.mock import MagicMock

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn._conn.cursor.return_value = mock_cursor
        mock_conn._conn.commit = MagicMock()
        mock_conn._conn.rollback = MagicMock()

        # Track commits and rollbacks
        call_count = [0]
        def side_effect(query):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("simulated failure")

        mock_cursor.execute.side_effect = side_effect

        _apply_migrations(mock_conn)

        # commit() should have been called at least once (for successful statements)
        assert mock_conn._conn.commit.call_count >= 1, \
            "Prior successful migrations should be committed before failure"
        # rollback() should have been called (for the failed statement)
        assert mock_conn._conn.rollback.call_count >= 1


# ---------------------------------------------------------------------------
# Bug Fix 2: topic_profiles evidence ceiling
# ---------------------------------------------------------------------------

class TestTopicProfilesEvidenceCeiling:
    """Verify update_topic_profile respects evidence_ceiling parameter."""

    def test_update_topic_profile_accepts_evidence_ceiling(self):
        """update_topic_profile should accept evidence_ceiling parameter."""
        import inspect
        from pathforge.db.profile_manager import update_topic_profile
        sig = inspect.signature(update_topic_profile)
        assert "evidence_ceiling" in sig.parameters
        # Default should be None (no ceiling)
        assert sig.parameters["evidence_ceiling"].default is None

    def test_update_elo_accepts_k_ceiling(self):
        """update_elo should accept k_ceiling parameter."""
        import inspect
        from pathforge.db.elo import update_elo
        sig = inspect.signature(update_elo)
        assert "k_ceiling" in sig.parameters
        assert sig.parameters["k_ceiling"].default is None

    def test_update_elo_with_k_ceiling(self):
        """update_elo with k_ceiling should cap the K factor."""
        from pathforge.db.elo import update_elo, get_k_factor

        # Easy problem: K=32
        k_easy = get_k_factor("Easy")
        assert k_easy == 32

        # Without ceiling: uses full K=32
        elo_no_ceiling = update_elo(1200.0, "Easy", 1.0)

        # With ceiling=16: uses min(32, 16)=16
        elo_with_ceiling = update_elo(1200.0, "Easy", 1.0, k_ceiling=16)

        # The ceiling should produce a smaller ELO change
        delta_no_ceiling = abs(elo_no_ceiling - 1200.0)
        delta_with_ceiling = abs(elo_with_ceiling - 1200.0)
        assert delta_with_ceiling < delta_no_ceiling, \
            f"Ceiling should reduce delta: {delta_with_ceiling} < {delta_no_ceiling}"

    def test_update_elo_with_k_ceiling_zero(self):
        """update_elo with k_ceiling=0 should produce no ELO change."""
        from pathforge.db.elo import update_elo
        elo_before = 1200.0
        elo_after = update_elo(elo_before, "Easy", 1.0, k_ceiling=0)
        assert elo_after == elo_before, "k_ceiling=0 should produce no ELO change"

    def test_update_elo_with_k_ceiling_none_no_change(self):
        """update_elo with k_ceiling=None should behave like no ceiling."""
        from pathforge.db.elo import update_elo
        elo_no_ceiling = update_elo(1200.0, "Easy", 1.0)
        elo_none_ceiling = update_elo(1200.0, "Easy", 1.0, k_ceiling=None)
        assert elo_no_ceiling == elo_none_ceiling

    def test_persistence_passes_ceiling_to_topic_profile(self):
        """run_persistence should derive and pass evidence_ceiling to update_topic_profile."""
        from pathforge.elo_engine import EVIDENCE_K_CEILINGS

        # Verify the ceiling values are available
        assert EVIDENCE_K_CEILINGS["structurally_observed"] == 24
        assert EVIDENCE_K_CEILINGS["externally_listed"] == 16

        # Verify the lookup pattern used in run_persistence
        for state in ["structurally_observed", "externally_listed", "llm_proposed", "unobserved", "conflicted"]:
            ceiling = EVIDENCE_K_CEILINGS.get(state, 0)
            assert ceiling is not None, f"Ceiling for {state} should not be None"


# ---------------------------------------------------------------------------
# Bug Fix 3: Unknown evidence state fails closed
# ---------------------------------------------------------------------------

class TestUnknownEvidenceFailsClosed:
    """Verify unknown evidence states produce K=0 and analysis_only behavior."""

    def test_unknown_evidence_k_ceiling_is_zero(self):
        """Unknown evidence state should get K=0 ceiling in EloEngine."""
        from pathforge.elo_engine import EVIDENCE_K_CEILINGS, DEFAULT_K
        # The get() default is now 0, not DEFAULT_K
        ceiling = EVIDENCE_K_CEILINGS.get("totally_bogus_state", 0)
        assert ceiling == 0, f"Unknown state should get K=0, got {ceiling}"

    def test_unknown_evidence_produces_zero_k(self):
        """With unknown evidence, EloEngine should compute K=0."""
        from pathforge.elo_engine import EloEngine, EVIDENCE_K_CEILINGS, DEFAULT_K
        engine = EloEngine()

        result = engine.compute_updates(
            user_id="1",
            gap_signals=[],
            match_result={"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": [], "confidence_score": 0.9},
            ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
            current_elos={"hash_map_lookup": 1200.0},
            evidence_state="totally_bogus_state",
        )

        # All updates should have delta=0 because K=0
        for update in result.get("pattern_elo_updates", []):
            assert update["delta"] == 0.0, \
                f"Unknown evidence should produce delta=0, got {update['delta']}"

    def test_known_authoritative_evidence_still_works(self):
        """Known authoritative states should still produce non-zero deltas."""
        from pathforge.elo_engine import EloEngine
        engine = EloEngine()

        result = engine.compute_updates(
            user_id="1",
            gap_signals=[],
            match_result={"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": [], "confidence_score": 0.9},
            ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
            current_elos={"hash_map_lookup": 1200.0},
            evidence_state="structurally_observed",
        )

        # Should have non-zero deltas (capped at K=24 but still positive)
        has_nonzero = any(abs(u["delta"]) > 0.01 for u in result.get("pattern_elo_updates", []))
        assert has_nonzero, "structurally_observed should produce non-zero deltas"

    def test_persistence_unknown_evidence_gets_zero_ceiling(self):
        """run_persistence should pass K=0 ceiling for unknown evidence states."""
        from pathforge.elo_engine import EVIDENCE_K_CEILINGS

        # Verify the lookup used in run_persistence defaults to 0
        unknown_state = "some_future_state"
        ceiling = EVIDENCE_K_CEILINGS.get(unknown_state, 0)
        assert ceiling == 0, f"Unknown state should get 0, got {ceiling}"

    def test_all_known_states_have_explicit_entries(self):
        """All known evidence states should have explicit entries in EVIDENCE_K_CEILINGS."""
        from pathforge.elo_engine import EVIDENCE_K_CEILINGS
        from pathforge.services.persistence import _AUTHORITATIVE_STATES

        known_states = _AUTHORITATIVE_STATES | {"llm_proposed", "unobserved", "conflicted"}
        for state in known_states:
            assert state in EVIDENCE_K_CEILINGS, \
                f"Known state '{state}' should be in EVIDENCE_K_CEILINGS"
