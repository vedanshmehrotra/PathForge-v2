"""Tests for pathforge.submission_handler — to_date helper and _update_user_streak."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pathforge.submission_handler import to_date, _update_user_streak


class TestToDate:
    """to_date() helper must accept datetime.date, ISO string, and None."""

    def test_accepts_date_object(self):
        """PostgreSQL DATE columns return datetime.date — pass through."""
        d = date(2026, 7, 27)
        result = to_date(d)
        assert result is d  # same object, no conversion

    def test_accepts_iso_string(self):
        """Legacy TEXT columns return ISO strings — parse."""
        result = to_date("2026-07-27")
        assert result == date(2026, 7, 27)

    def test_accepts_none(self):
        """No prior submission — return None."""
        result = to_date(None)
        assert result is None

    def test_rejects_invalid_string(self):
        """Invalid ISO strings should still raise (caller's responsibility)."""
        with pytest.raises((ValueError, TypeError)):
            to_date("not-a-date")


class TestUpdateUserStreak:
    """_update_user_streak must handle PostgreSQL date objects."""

    def _make_conn(self, last_submission_date, current_streak=0):
        """Create a mock connection whose SELECT returns the given values."""
        conn = MagicMock()
        row = {"last_submission_date": last_submission_date, "current_streak": current_streak}
        conn.execute.return_value.fetchone.return_value = row
        return conn

    def test_streak_increment_date_object(self):
        """PostgreSQL returns a date object — must not crash."""
        conn = self._make_conn(
            last_submission_date=date(2026, 7, 26),  # yesterday as date object
            current_streak=2,
        )
        _update_user_streak(conn, user_id=1, submitted_at="2026-07-27T12:00:00+00:00")

        update_call = conn.execute.call_args_list[-1]
        sql, params = update_call[0]
        assert params[0] == 3  # streak incremented to 3
        assert "UPDATE users" in sql

    def test_streak_increment_iso_string(self):
        """Legacy TEXT column returns a string — must still work."""
        conn = self._make_conn(
            last_submission_date="2026-07-26",  # yesterday as string
            current_streak=2,
        )
        _update_user_streak(conn, user_id=1, submitted_at="2026-07-27T12:00:00+00:00")

        update_call = conn.execute.call_args_list[-1]
        _, params = update_call[0]
        assert params[0] == 3

    def test_streak_same_day(self):
        """Same day — streak stays the same."""
        conn = self._make_conn(
            last_submission_date=date(2026, 7, 27),  # today
            current_streak=5,
        )
        _update_user_streak(conn, user_id=1, submitted_at="2026-07-27T12:00:00+00:00")

        update_call = conn.execute.call_args_list[-1]
        _, params = update_call[0]
        assert params[0] == 5  # unchanged

    def test_streak_reset_gap(self):
        """Multiple days gap — streak resets to 1."""
        conn = self._make_conn(
            last_submission_date=date(2026, 7, 20),  # 7 days ago
            current_streak=10,
        )
        _update_user_streak(conn, user_id=1, submitted_at="2026-07-27T12:00:00+00:00")

        update_call = conn.execute.call_args_list[-1]
        _, params = update_call[0]
        assert params[0] == 1  # reset

    def test_first_ever_submission(self):
        """No row returned (user not found) — silently returns."""
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        # Should not raise
        _update_user_streak(conn, user_id=999, submitted_at="2026-07-27T12:00:00+00:00")
        # Only the SELECT was called, no UPDATE
        selects = [call for call in conn.execute.call_args_list if "SELECT" in str(call)]
        updates = [call for call in conn.execute.call_args_list if "UPDATE" in str(call)]
        assert len(selects) >= 1
        assert len(updates) == 0

    def test_none_last_submission_date(self):
        """last_submission_date is NULL — no prior streak, start at 1."""
        conn = self._make_conn(
            last_submission_date=None,
            current_streak=0,
        )
        _update_user_streak(conn, user_id=1, submitted_at="2026-07-27T12:00:00+00:00")

        update_call = conn.execute.call_args_list[-1]
        _, params = update_call[0]
        assert params[0] == 1
