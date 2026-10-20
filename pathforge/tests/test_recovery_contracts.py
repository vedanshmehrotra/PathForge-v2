"""Recovery contracts frozen from the user report and recommendation audit.

Run through scripts.verify_foundation.offline before importing backend modules.
Sources are parsed or supplied as data; no submitted solution is executed.
"""
import copy
import json
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_calendar_practice import BANK, event, plan


def test_generation_uses_approaches_as_its_only_requirement_source():
    from pathforge.services import ground_truth_builder as builder
    raw = {"approach_contract_version": 3, "approaches": [
        {"name": "Sort and scan", "patterns": ["sorting", "array_traversal"],
         "confidence": {"sorting": .9, "array_traversal": .8}},
        {"name": "Lookup", "patterns": ["hash_map_lookup"], "confidence": {"hash_map_lookup": .85}},
    ]}
    before = copy.deepcopy(raw)
    connection = Mock(spec=["execute", "commit", "rollback"])
    with patch.object(builder, "call_llm", return_value=raw):
        assert builder.build_ground_truth(7, "Synthetic source", connection) == [
            "array_traversal", "hash_map_lookup", "sorting"]
    groups = json.loads(connection.execute.call_args.args[1][3])
    assert [g["patterns"] for g in groups] == [["array_traversal", "sorting"], ["hash_map_lookup"]]
    assert all(g["authority_tier"] == "llm_proposed" for g in groups)
    assert all(g["family_relation"] == "ONE_OF" for g in groups)
    assert raw == before
    connection.commit.assert_not_called()


@pytest.mark.parametrize("change", [
    {"approaches": []}, {"patterns": ["sorting"]},
    {"approaches": [{"name": "Unknown", "patterns": ["sorting", "invented"]}]},
    {"approaches": [{"name": "Invalid", "patterns": [None]}]},
])
def test_new_generation_contract_cannot_silently_repair_bad_requirements(change):
    from pathforge.services import ground_truth_builder as builder
    raw = {"approach_contract_version": 3,
           "approaches": [{"name": "Scan", "patterns": ["array_traversal"]}], **change}
    connection = Mock(spec=["execute", "commit", "rollback"])
    with patch.object(builder, "call_llm", return_value=raw), pytest.raises(builder.GroundTruthError):
        builder.build_ground_truth(7, "Synthetic source", connection)
    connection.execute.assert_not_called()


def test_legacy_conflicting_lists_still_fail_closed():
    from pathforge.services import ground_truth_builder as builder
    with pytest.raises(builder.GroundTruthError, match="flat patterns disagree"):
        builder.normalize_ground_truth_response({"patterns": ["sorting"],
            "approaches": [{"name": "Scan", "patterns": ["array_traversal"]}]})


@pytest.mark.parametrize("topic", ["Math", "Hash Table", "Simulation", "Design", "Invented Topic"])
def test_broad_or_unknown_tags_cannot_claim_targeted_continuation(topic):
    bank = [{**BANK[2], "topics": topic}, {**BANK[3], "topics": topic}]
    out = plan([event(704)], bank=bank)
    assert out["recommendations"][0]["practice_kind"] == "explore"
    assert "reason_evidence" not in out["recommendations"][0]


def test_default_difficulty_does_not_jump_from_easy_to_hard():
    bank = [BANK[2], {**BANK[3], "difficulty": "Hard"}, BANK[6]]
    out = plan([event(704)], bank=bank)
    assert all(r["difficulty"] != "Hard" for r in out["recommendations"])
    explicit = plan([event(704)], bank=bank, difficulty="Hard")
    assert explicit["recommendations"][0]["difficulty"] == "Hard"


def test_a_review_never_fills_every_slot_and_latest_cooldown_expires():
    out = plan([event(704), event(1, 10), event(20, 11), event(3, 12)],
               bank=[BANK[2], BANK[0], BANK[6], BANK[4]])
    assert len(out["recommendations"]) == 1
    assert out["recommendations"][0]["practice_kind"] == "revisit"
    assert plan([event(1, 365)], bank=BANK[:1])["recommendations"][0]["practice_kind"] == "revisit"


def test_skipping_the_only_eligible_choice_explains_how_to_recover():
    assert plan([event(704)], bank=[BANK[2], BANK[3]], excluded_ids=[35])["state"] == "session_exhausted"


def test_equal_timestamps_retain_newest_first_history_order():
    out = plan([event(704, 10), event(20, 10)], bank=[BANK[2], BANK[6]])
    assert out["context"]["latest_problem_id"] == "704"


def test_unknown_topics_do_not_displace_available_known_variety():
    bank = [BANK[2], BANK[3], BANK[6],
            {**BANK[0], "id": 99, "topics": "", "link": "https://leetcode.com/problems/aaa/"},
            {**BANK[0], "id": 98, "topics": "", "link": "https://leetcode.com/problems/aab/"}]
    out = plan([event(704)], bank=bank)
    assert "20" in [r["problem_id"] for r in out["recommendations"]]


def test_paid_candidates_and_json_encoded_topic_accidents_are_handled():
    assert plan(bank=[{**BANK[3], "premium_only": True}])["recommendations"] == []
    out = plan([event(704)], bank=[{**BANK[2], "topics": '["Array"]'},
                                   {**BANK[3], "topics": '["Array"]'}])
    assert out["recommendations"][0]["practice_kind"] == "explore"


def test_case_only_aliases_are_the_same_problem_not_catalog_conflicts():
    alias = {**BANK[0], "id": 999, "title": BANK[0]["title"].upper()}
    assert plan([event(999)], bank=[BANK[0], alias])["history"]["mapped_problems"] == 1
