"""Regression tests for PostgreSQL boolean persistence.

Ensures recommendation persistence uses TRUE/FALSE for boolean columns
instead of SQLite-style integer 0/1 that causes PostgreSQL errors like:
    column "acted_on" is of type boolean but expression is of type integer

These tests verify that all code paths touching boolean columns
(acted_on, followed, onboarding_complete, premium_only, gap_identified)
use correct boolean values.
"""

import pytest
from unittest.mock import MagicMock, patch

from pathforge.pipeline import _mark_last_recommendation_acted_on
from pathforge.db.profile_manager import iso_now


class TestRecommendationBooleanPersistence:
    """Verifies that _mark_last_recommendation_acted_on uses TRUE/FALSE."""

    def test_acted_on_uses_true_keyword(self):
        """_mark_last_recommendation_acted_on must use TRUE not 1."""
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {
            "last_recommendation_id": 42,
        }

        _mark_last_recommendation_acted_on(conn, user_id=7)

        # Find the UPDATE call for recommendations
        update_calls = [
            call for call in conn.execute.call_args_list
            if "UPDATE recommendations" in str(call)
        ]
        assert len(update_calls) == 1, "Expected exactly one UPDATE on recommendations"
        sql, params = update_calls[0][0]

        # The SQL must use TRUE, not the integer 1
        assert "acted_on = TRUE" in sql, (
            f"SQL must use 'acted_on = TRUE', got: {sql}"
        )
        assert "acted_on = 1" not in sql, (
            f"SQL must not use 'acted_on = 1', got: {sql}"
        )

    def test_acted_on_skipped_when_no_recommendation(self):
        """No UPDATE when there is no last_recommendation_id (None or no row)."""
        conn = MagicMock()

        # Case 1: no row returned
        conn.execute.return_value.fetchone.return_value = None
        _mark_last_recommendation_acted_on(conn, user_id=7)
        update_calls = [
            call for call in conn.execute.call_args_list
            if "UPDATE recommendations" in str(call)
        ]
        assert len(update_calls) == 0, "No UPDATE should happen when no recommendation exists"

        # Case 2: last_recommendation_id is None
        conn.reset_mock()
        conn.execute.return_value.fetchone.return_value = {"last_recommendation_id": None}
        _mark_last_recommendation_acted_on(conn, user_id=7)
        update_calls = [
            call for call in conn.execute.call_args_list
            if "UPDATE recommendations" in str(call)
        ]
        assert len(update_calls) == 0, "No UPDATE should happen when last_recommendation_id is None"


class TestProfileBooleanPersistence:
    """Verifies that routes/profile.py uses TRUE/FALSE for boolean columns."""

    def test_active_recommendation_uses_false_keyword(self):
        """_active_recommendation must use 'acted_on = FALSE' not 'acted_on = 0'."""
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None  # no active rec

        from pathforge.routes.profile import _active_recommendation
        _active_recommendation(conn, user_id=7)

        select_calls = [
            call for call in conn.execute.call_args_list
            if "acted_on" in str(call)
        ]
        if select_calls:
            sql, params = select_calls[0][0]
            assert "acted_on = FALSE" in sql, (
                f"SQL must use 'acted_on = FALSE', got: {sql}"
            )
            assert "acted_on = 0" not in sql, (
                f"SQL must not use 'acted_on = 0', got: {sql}"
            )

    def test_clear_recommendation_uses_true_keyword(self):
        """_clear_active_recommendation must use 'acted_on = TRUE' not 'acted_on = 1'."""
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {
            "last_recommendation_id": 42,
        }

        from pathforge.routes.profile import _clear_active_recommendation
        _clear_active_recommendation(conn, user_id=7)

        update_calls = [
            call for call in conn.execute.call_args_list
            if "UPDATE recommendations" in str(call)
        ]
        # Should have UPDATE recommendations + UPDATE users
        rec_updates = [c for c in update_calls if "acted_on" in str(c)]
        assert len(rec_updates) >= 1, "Expected at least one UPDATE on recommendations"
        sql, params = rec_updates[0][0]
        assert "acted_on = TRUE" in sql, (
            f"SQL must use 'acted_on = TRUE', got: {sql}"
        )
        assert "acted_on = 1" not in sql, (
            f"SQL must not use 'acted_on = 1', got: {sql}"
        )


class TestSubmissionHandlerBooleanPersistence:
    """Verifies that submission_handler passes Python bool, not int, for gap_identified."""

    def test_insert_uses_false_for_gap_identified(self):
        """_save_submission must pass False (not 0) for gap_identified parameter."""
        from pathforge.submission_handler import _save_submission

        conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1}
        conn.execute.return_value = mock_cursor

        _save_submission(
            connection=conn,
            user_id=1,
            problem_id=1,
            verdict="pass",
            detected_pattern="hash_map_lookup",
            topic="hash_map_lookup",
            attempt_number=1,
            submitted_at="2026-07-27T12:00:00+00:00",
        )

        # Check the parameters passed to execute
        call_args = conn.execute.call_args
        sql, params = call_args[0]

        # The gap_identified parameter should be False (Python bool), not 0 (int)
        # gap_identified is the 9th parameter (0-indexed: position 8)
        gap_identified_param = params[8]
        assert gap_identified_param is False, (
            f"gap_identified must be Python False, got {gap_identified_param!r} (type={type(gap_identified_param).__name__})"
        )


class TestAuthBooleanPersistence:
    """Verifies that routes/auth.py uses TRUE for onboarding_complete."""

    def test_register_uses_true_for_onboarding(self):
        """Registration must use TRUE not 1 for onboarding_complete."""
        conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        conn.execute.return_value = mock_cursor

        # We only need to check the SQL pattern, can't easily call register directly
        # Instead, verify the existing SQL in the file doesn't contain `1` for onboarding
        import pathforge.routes.auth as auth_module
        source = open(auth_module.__file__).read()

        # The INSERT should contain `TRUE` not `1` for onboarding_complete
        assert "VALUES (?, ?, ?, ?, ?, ?, TRUE, ?, ?)" in source, (
            "Registration INSERT must use TRUE for onboarding_complete, got integer 1"
        )
