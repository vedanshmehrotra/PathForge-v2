"""Actual analysis/persistence feedback with isolated storage and no submitted-code execution."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_shadow_display_contract import isolated_services


BRACKET_CODE = '''class Solution:
    def isValid(self, s: str) -> bool:
        stack=[]
        if len(s)==0:
                    return False
        for i in s:
            if i=="(" or i=="{" or i=="[":
                stack.append(i)
            else:
                if len(stack)==0:
                    return False
                tos=stack.pop()
                if i==")" and tos!="(":
                    return False
                if i=="]" and tos!="[":
                    return False
                if i=="}" and tos!="{":
                    return False
        return len(stack)==0
'''


def build_bracket_case():
    with isolated_services():
        import config
        from pathforge.api.routes import analyze
        from pathforge.services import persistence, product_eligibility as b6
        from pathforge.ast_analysis.shadow import persistence as shadow_persistence
        from pathforge.tests.test_problem_preparation_boundary import MemoryConnection, PROBLEM
        from src.ast_detection.semantic.shadow_detector import ShadowDetector

        group = {"id": "g0", "patterns": ["monotonic_stack"], "required": ["monotonic_stack_maintenance"],
                 "approach_name": "recursive_branching", "authority_tier": "llm_proposed",
                 "evidence": "llm_proposed", "optional": [], "excluded": []}
        ground_truth = {"patterns": ["monotonic_stack"], "confidence": {},
                        "solution_groups": [group], "validation_status": "llm_proposed"}
        forbidden = Mock(side_effect=AssertionError("Scoring forbidden for analysis-only evidence"))

        class Connection(MemoryConnection):
            def execute(self, sql, params):
                if any(fragment in sql for fragment in ("pg_advisory_xact_lock", "analysis_key =", "skill_updates_applied =")):
                    return SimpleNamespace(fetchone=lambda: None)
                if "INSERT INTO submissions" in sql:
                    self.writes.append("submission")
                    return SimpleNamespace(fetchone=lambda: {"id": 123})
                return super().execute(sql, params)

        connection = Connection(problem={**PROBLEM, "id": 20, "title": "Valid Parentheses"},
                                ground_truth=ground_truth)
        before = copy.deepcopy(connection.ground_truth)
        with patch.object(analyze, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
             patch.object(analyze, "get_connection", return_value=connection), \
             patch.object(persistence, "_next_attempt_number", return_value=1), \
             patch.object(persistence, "_update_user_streak"), \
             patch.object(persistence, "update_topic_profile", forbidden), \
             patch.object(persistence, "_gap_engine", SimpleNamespace(
                 compute_signals=forbidden, persist_signals=forbidden)), \
             patch.object(persistence, "_elo_engine", SimpleNamespace(
                 compute_updates=forbidden, persist_elos=forbidden)), \
             patch.object(persistence, "get_recommendation", forbidden), \
             patch.object(b6, "flag_enabled", return_value=False), \
             patch.object(config, "SHADOW_AUTHORITY_PRODUCT_GATING", False), \
             patch.object(shadow_persistence, "persist_shadow_analysis"), \
             patch.object(ShadowDetector, "analyze_safe", return_value=None):
            response = analyze.analyze_endpoint(analyze.AnalyzeRequest(
                user_id=999, code=BRACKET_CODE, problem={"leetcode_id": 20}), None).model_dump()
        forbidden.assert_not_called()
        assert connection.ground_truth == before
        assert connection.writes == ["submission"]
        connection.commit.assert_called_once()
        return {"code": BRACKET_CODE, "response": response}


@pytest.fixture(scope="module")
def bracket_case():
    return build_bracket_case()


def test_bracket_stack_is_not_relabelled_monotonic(bracket_case):
    response = bracket_case["response"]
    assert "monotonic_stack" not in [p["pattern_id"] for p in response["ast"]["detected_patterns"]]
    assert response["match_result"]["match_result"] == "NO_MATCH"
    assert response["problem_info"]["solution_groups"][0]["review_state"] == "UNREVIEWED"
    assert response["shadow_analysis"]["strategy_selection"]["submission"]["selected"] is None


def test_actual_analysis_only_path_reports_no_skill_consequences(bracket_case):
    response = bracket_case["response"]
    assert response["persisted"]["skill_updates_skipped"] is True
    assert response["elo_updates"] == []
    assert response["persisted"]["gap_signals_count"] == 0
    assert response["persisted"]["elo_updates_count"] == 0


if __name__ == "__main__":
    print(json.dumps(build_bracket_case()))
