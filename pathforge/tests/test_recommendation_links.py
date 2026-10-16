from unittest.mock import Mock, patch

import pytest

from pathforge.recommendation_links import problem_url
from pathforge.tests.test_shadow_display_contract import isolated_services


@pytest.mark.parametrize("raw", [None, "", 704, "javascript:alert(1)",
    "http://leetcode.com/problems/two-sum/", "https://leetcode.com.evil.invalid/problems/two-sum/",
    "https://user:secret@leetcode.com/problems/two-sum/", "https://leetcode.com:8443/problems/two-sum/",
    "https://leetcode.com/problems/two-sum/?next=elsewhere", "https://leetcode.com/problems/two-sum/#details",
    "https://leetcode.com/problemset/", "https://leetcode.com\\@evil.invalid/problems/two-sum/",
    "https://leetcode.com/problems/two-\nsum/"])
def test_unusable_problem_links_are_not_exposed(raw):
    assert problem_url(raw) is None


def test_known_problem_link_is_canonicalized_without_inferring_from_id():
    assert problem_url("https://www.leetcode.com/problems/two-sum") == "https://leetcode.com/problems/two-sum/"


@pytest.mark.parametrize("link,expected", [
    ("https://leetcode.com/problems/two-sum/", "https://leetcode.com/problems/two-sum/"),
    ("https://example.invalid/problems/two-sum/", None),
    (None, None),
])
def test_actual_recommendation_service_adds_stored_link_without_changing_policy(link, expected):
    with isolated_services():
        from pathforge.api.services import recommend_service as service
        connection = Mock()
        problems = [{"id": 999, "title": "Two Sum", "difficulty": "Easy", "pattern": ["hash_map_lookup"],
                     "link": link, "acceptance_rate": 0.5}]
        with patch.object(service, "get_connection", return_value=connection), \
             patch.object(service, "load_user_info", return_value={"id": 7}), \
             patch.object(service, "load_problem_bank", return_value=problems), \
             patch.object(service, "load_user_pattern_elo", return_value={}), \
             patch.object(service, "load_gap_signals", return_value=[]), \
             patch.object(service, "load_submissions", return_value=[]):
            result = service.get_recommendations(7)
        item = result["recommendations"][0]
        assert item["problem_id"] == "999"  # Internal ID must not become a guessed LeetCode ID.
        assert item["problem_url"] == expected
        assert item["pattern"] == "hash_map_lookup"
        assert item["score"] == 20.0  # Legacy field remains API-compatible, not displayed as gain.
        assert result["summary"]["recommendation_strategy"] == "cold_start_exploration"
        connection.execute.assert_not_called()
        connection.close.assert_called_once()
