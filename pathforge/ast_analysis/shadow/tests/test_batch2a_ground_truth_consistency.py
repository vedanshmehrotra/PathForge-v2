"""Generalized regression tests for Batch 2A (ground-truth consistency).

Batch 2A changes only the ground-truth layer:

1. Group derivation is re-runnable and vocabulary-aware: a stored group whose
   concepts were produced by the V1 mapping can pick up the CURRENT mapping
   (e.g. ``two_pointers_same`` -> ``forward_pointer_advance``) instead of staying
   tied to an obsolete required concept forever.
2. A group with no required concept is never persisted or emitted as a normal
   (matchable) requirement. The missing vocabulary is named instead.
3. The flat pattern label and the structured solution groups are checked for
   drift, so the two representations cannot silently disagree.

These tests are written against structure and vocabulary, not problem IDs. Each
case is a minimal representative of a family (mapped pattern, pattern with no
V1 concept, vocabulary-derived group, curated alternative groups).
"""
import json

import pytest

from pathforge.services.ground_truth_builder import (
    MISSING_VOCABULARY_PATTERNS,
    PATTERN_TO_V1_MAPPING,
    VALID_V1_CONCEPTS,
    VOCABULARY_DERIVATION_MARKER,
    VOCABULARY_REFRESH_MARKER,
    _build_solution_groups,
    _store_ground_truth,
    find_ground_truth_disagreements,
    group_matchability,
    mark_group_matchability,
    missing_vocabulary_for_patterns,
    refresh_groups_vocabulary,
)
from pathforge.services.problem_resolver import (
    _finalize_derived_groups,
    _split_csv_patterns_to_groups,
)


# ============================================================
# Vocabulary fixtures (derived from the mapping, never hardcoded per problem)
# ============================================================

MAPPED_PATTERN = "prefix_sum"                  # -> sequential_accumulation
SAME_DIRECTION_PATTERN = "two_pointers_same"   # -> forward_pointer_advance
FAST_SLOW_PATTERN = "fast_slow_pointers"       # -> forward_pointer_advance
ALTERNATING_PATTERN = "dp_1d_forward"          # -> dp_bottom_up
UNMAPPED_PATTERN = "topological_sort"          # -> no V1 concept
UNMAPPED_PATTERN_2 = "heap_top_k"              # -> no V1 concept


def _group(id="group_0", patterns=None, required=None, optional=None,
           excluded=None, provenance=None):
    group = {
        "id": id,
        "version": 1,
        "required": list(required or []),
        "optional": list(optional or []),
        "excluded": list(excluded or []),
        "threshold": 0.5,
        "patterns": list(patterns or []),
    }
    if provenance is not None:
        group["provenance"] = list(provenance)
    return group


class _RecordingConnection:
    """Minimal connection double that records the parameters it was given."""

    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        return self

    def commit(self):
        pass


# ============================================================
# 1. Missing-vocabulary registry
# ============================================================

class TestMissingVocabularyRegistry:
    def test_registry_is_derived_from_the_mapping(self):
        """The registry must be exactly the patterns with no required concept."""
        expected = {
            p for p, m in PATTERN_TO_V1_MAPPING.items() if not m.get("required")
        }
        assert MISSING_VOCABULARY_PATTERNS == expected
        assert MISSING_VOCABULARY_PATTERNS, "registry should not be empty"

    def test_mapped_pattern_has_no_missing_vocabulary(self):
        assert missing_vocabulary_for_patterns([MAPPED_PATTERN]) == []
        assert missing_vocabulary_for_patterns([SAME_DIRECTION_PATTERN]) == []

    def test_unmapped_pattern_is_reported(self):
        assert missing_vocabulary_for_patterns([UNMAPPED_PATTERN]) == [
            UNMAPPED_PATTERN
        ]

    def test_mixed_patterns_report_only_the_gap(self):
        result = missing_vocabulary_for_patterns([MAPPED_PATTERN, UNMAPPED_PATTERN])
        assert result == [UNMAPPED_PATTERN]

    def test_empty_input_is_empty(self):
        assert missing_vocabulary_for_patterns([]) == []
        assert missing_vocabulary_for_patterns(None) == []


# ============================================================
# 2. Matchability rule
# ============================================================

class TestGroupMatchability:
    def test_group_with_required_concept_is_matchable(self):
        matchable, reason = group_matchability(
            _group(patterns=[MAPPED_PATTERN], required=["sequential_accumulation"])
        )
        assert matchable is True
        assert reason == ""

    def test_group_without_required_concept_is_not_matchable(self):
        matchable, reason = group_matchability(
            _group(patterns=[UNMAPPED_PATTERN], required=[])
        )
        assert matchable is False
        assert UNMAPPED_PATTERN in reason

    def test_reason_names_the_missing_vocabulary_not_an_invented_requirement(self):
        """The rule must expose the gap, never substitute an arbitrary concept."""
        _, reason = group_matchability(_group(patterns=[UNMAPPED_PATTERN_2]))
        assert UNMAPPED_PATTERN_2 in reason
        assert not (set(reason.split()) & VALID_V1_CONCEPTS), (
            f"reason must not name a V1 concept as if it were required: {reason}"
        )

    def test_group_with_no_patterns_is_not_matchable(self):
        matchable, reason = group_matchability(_group(patterns=[], required=[]))
        assert matchable is False
        assert "no legacy patterns" in reason

    def test_mark_adds_explicit_annotation(self):
        group = mark_group_matchability(
            _group(patterns=[UNMAPPED_PATTERN], required=[])
        )
        assert group["matchable"] is False
        assert group["validation"] == "unmatchable"
        assert group["matchability_reason"]
        assert group["patterns"] == [UNMAPPED_PATTERN]  # gap stays visible

    def test_mark_is_idempotent_and_clears_stale_reason(self):
        group = _group(patterns=[MAPPED_PATTERN], required=["sequential_accumulation"])
        group["matchability_reason"] = "stale"
        mark_group_matchability(group)
        mark_group_matchability(group)
        assert group["matchable"] is True
        assert "matchability_reason" not in group


# ============================================================
# 3. Derivation emits explicit matchability
# ============================================================

class TestDerivationExposesMissingVocabulary:
    def test_derived_group_for_unmapped_pattern_is_flagged(self):
        groups = _build_solution_groups([UNMAPPED_PATTERN], {})
        assert groups, "the group must still be produced for diagnosis"
        assert groups[0]["matchable"] is False
        assert groups[0]["validation"] == "unmatchable"
        assert UNMAPPED_PATTERN in groups[0]["matchability_reason"]
        assert groups[0]["required"] == []

    def test_derived_group_for_mapped_pattern_stays_matchable(self):
        groups = _build_solution_groups([MAPPED_PATTERN], {})
        assert groups and groups[0]["matchable"] is True
        assert groups[0]["required"] == ["sequential_accumulation"]

    def test_derived_groups_are_always_annotated(self):
        """Every derived group carries the explicit matchability flag."""
        for patterns in ([MAPPED_PATTERN], [UNMAPPED_PATTERN], [UNMAPPED_PATTERN_2]):
            groups = _build_solution_groups(patterns, {})
            for group in groups:
                assert "matchable" in group

    def test_mixed_patterns_keep_the_gap_visible(self):
        """A mapped and an unmapped pattern must never produce an unsatisfiable
        group, and the gap must not be silently dropped."""
        groups = _build_solution_groups([MAPPED_PATTERN, UNMAPPED_PATTERN], {})
        assert groups
        for group in groups:
            if not group["required"]:
                assert group["matchable"] is False
                assert group["matchability_reason"]
        recorded = {p for group in groups for p in (group.get("unmapped_patterns") or [])}
        assert UNMAPPED_PATTERN in recorded, (
            f"the unmapped pattern must stay recorded for diagnosis: {groups}"
        )


# ============================================================
# 4. Persistence rejects unsatisfiable groups
# ============================================================

class TestPersistenceRejectsUnmatchableGroups:
    def _stored_groups(self, patterns):
        conn = _RecordingConnection()
        _store_ground_truth(conn, 12345, patterns, {})
        assert conn.executed, "storage should have been attempted"
        _query, params = conn.executed[-1]
        return json.loads(params[3])

    def test_unmatchable_group_is_not_persisted(self):
        assert self._stored_groups([UNMAPPED_PATTERN]) == []

    def test_unmatchable_group_is_not_persisted_but_flat_patterns_are(self):
        conn = _RecordingConnection()
        _store_ground_truth(conn, 12345, [UNMAPPED_PATTERN], {})
        _query, params = conn.executed[-1]
        assert json.loads(params[1]) == [UNMAPPED_PATTERN]
        assert json.loads(params[3]) == []

    def test_matchable_group_is_persisted_unchanged(self):
        stored = self._stored_groups([MAPPED_PATTERN])
        assert len(stored) == 1
        assert stored[0]["required"] == ["sequential_accumulation"]
        assert stored[0]["matchable"] is True

    def test_no_persisted_group_is_ever_unsatisfiable(self):
        """The invariant: nothing stored with an empty required list."""
        for patterns in ([MAPPED_PATTERN], [UNMAPPED_PATTERN],
                         [MAPPED_PATTERN, UNMAPPED_PATTERN]):
            for group in self._stored_groups(patterns):
                assert group["required"], group


# ============================================================
# 5. Vocabulary-aware re-derivation of stored groups
# ============================================================

class TestVocabularyRefresh:
    def _stale_group(self, patterns, stale_required, **kwargs):
        return _group(
            patterns=patterns,
            required=stale_required,
            provenance=[VOCABULARY_DERIVATION_MARKER],
            **kwargs,
        )

    def test_stale_same_direction_concept_is_refreshed(self):
        stale, expected = PATTERN_TO_V1_MAPPING[SAME_DIRECTION_PATTERN]["required"], None
        group = self._stale_group([SAME_DIRECTION_PATTERN], stale)
        assert group["required"] == stale
        refreshed = refresh_groups_vocabulary([group])
        expected = PATTERN_TO_V1_MAPPING[SAME_DIRECTION_PATTERN]["required"]
        assert group["required"] == expected
        assert refreshed == ["group_0"]

    def test_stale_fast_slow_concept_is_refreshed(self):
        group = self._stale_group([FAST_SLOW_PATTERN], ["bidirectional_index_scan"])
        refresh_groups_vocabulary([group])
        assert group["required"] == PATTERN_TO_V1_MAPPING[FAST_SLOW_PATTERN]["required"]

    def test_refresh_records_provenance(self):
        group = self._stale_group([SAME_DIRECTION_PATTERN], ["bidirectional_index_scan"])
        refresh_groups_vocabulary([group])
        assert VOCABULARY_REFRESH_MARKER in group["provenance"]

    def test_refresh_is_idempotent(self):
        group = self._stale_group([SAME_DIRECTION_PATTERN], ["bidirectional_index_scan"])
        assert refresh_groups_vocabulary([group]) == ["group_0"]
        assert refresh_groups_vocabulary([group]) == []

    def test_refresh_applies_current_exclusions(self):
        group = self._stale_group([SAME_DIRECTION_PATTERN], ["bidirectional_index_scan"])
        refresh_groups_vocabulary([group])
        expected = sorted(PATTERN_TO_V1_MAPPING[SAME_DIRECTION_PATTERN]["excluded"])
        assert sorted(group["excluded"]) == expected

    def test_refresh_removes_concepts_that_became_excluded(self):
        group = self._stale_group(
            [SAME_DIRECTION_PATTERN],
            ["bidirectional_index_scan"],
            optional=["two_pointers_opposite"],
        )
        refresh_groups_vocabulary([group])
        assert "bidirectional_index_scan" not in group["optional"]
        assert "two_pointers_opposite" not in group["optional"]

    def test_up_to_date_group_is_not_refreshed(self):
        group = _group(
            patterns=[MAPPED_PATTERN],
            required=PATTERN_TO_V1_MAPPING[MAPPED_PATTERN]["required"],
            excluded=PATTERN_TO_V1_MAPPING[MAPPED_PATTERN]["excluded"],
            provenance=[VOCABULARY_DERIVATION_MARKER],
        )
        assert refresh_groups_vocabulary([group]) == []
        assert VOCABULARY_REFRESH_MARKER not in group["provenance"]

    def test_curated_group_without_derivation_marker_is_never_refreshed(self):
        """Concepts that were not produced by the mapping must be left alone."""
        group = _group(
            patterns=[SAME_DIRECTION_PATTERN],
            required=["hand_written_concept"],
            provenance=["human_curated"],
        )
        assert refresh_groups_vocabulary([group]) == []
        assert group["required"] == ["hand_written_concept"]

    def test_group_without_patterns_is_never_refreshed(self):
        group = self._stale_group([], ["sequential_accumulation"])
        assert refresh_groups_vocabulary([group]) == []

    def test_group_with_unknown_pattern_is_never_refreshed(self):
        group = self._stale_group(["not_a_real_pattern"], ["sequential_accumulation"])
        assert refresh_groups_vocabulary([group]) == []
        assert group["required"] == ["sequential_accumulation"]

    def test_curated_alternatives_sharing_patterns_are_preserved(self):
        """Two groups over the same pattern with different concepts are curated.

        The mapping cannot reproduce that difference, so both must be left
        byte-identical instead of being collapsed into one requirement.
        """
        g0 = _group(
            id="group_0",
            patterns=[ALTERNATING_PATTERN],
            required=["dp_bottom_up"],
            provenance=[VOCABULARY_DERIVATION_MARKER],
        )
        g1 = _group(
            id="group_1",
            patterns=[ALTERNATING_PATTERN],
            required=["dp_top_down"],
            provenance=[VOCABULARY_DERIVATION_MARKER],
        )
        assert refresh_groups_vocabulary([g0, g1]) == []
        assert g0["required"] == ["dp_bottom_up"]
        assert g1["required"] == ["dp_top_down"]

    def test_distinct_patterns_are_refreshed_independently(self):
        g0 = self._stale_group([SAME_DIRECTION_PATTERN], ["bidirectional_index_scan"])
        g1 = _group(
            patterns=[MAPPED_PATTERN],
            required=["sequential_accumulation"],
            provenance=[VOCABULARY_DERIVATION_MARKER],
        )
        refreshed = refresh_groups_vocabulary([g0, g1])
        assert refreshed == ["group_0"]
        assert g1["required"] == ["sequential_accumulation"]

    def test_refresh_cannot_create_an_unsatisfiable_group(self):
        """Refreshing must never empty a required list."""
        for pattern in PATTERN_TO_V1_MAPPING:
            group = self._stale_group([pattern], ["bidirectional_index_scan"])
            refresh_groups_vocabulary([group])
            if pattern in MISSING_VOCABULARY_PATTERNS:
                continue
            assert group["required"], pattern


# ============================================================
# 6. Derived (fallback) groups carry the same annotation
# ============================================================

class TestDerivedGroupsAreAnnotated:
    def test_finalize_marks_derived_groups(self):
        groups = _finalize_derived_groups([
            _group(patterns=[UNMAPPED_PATTERN], required=[]),
            _group(id="group_1", patterns=[MAPPED_PATTERN],
                   required=["sequential_accumulation"]),
        ])
        assert groups[0]["matchable"] is False
        assert groups[0]["matchability_reason"]
        assert groups[1]["matchable"] is True

    def test_csv_split_marks_every_group(self):
        for patterns in ([MAPPED_PATTERN], [UNMAPPED_PATTERN],
                         [SAME_DIRECTION_PATTERN], [UNMAPPED_PATTERN_2]):
            for group in _split_csv_patterns_to_groups(patterns, {}, 1.0, "test"):
                assert "matchable" in group

    def test_csv_split_never_emits_unflagged_empty_required(self):
        for patterns in ([UNMAPPED_PATTERN], [UNMAPPED_PATTERN_2]):
            for group in _split_csv_patterns_to_groups(patterns, {}, 1.0, "test"):
                if not group["required"]:
                    assert group["matchable"] is False
                    assert group["matchability_reason"]

    def test_csv_split_uses_current_vocabulary(self):
        """The same-direction pattern must resolve to the current concept."""
        groups = _split_csv_patterns_to_groups(
            [SAME_DIRECTION_PATTERN], {}, 1.0, "test"
        )
        expected = PATTERN_TO_V1_MAPPING[SAME_DIRECTION_PATTERN]["required"]
        assert groups[0]["required"] == expected


# ============================================================
# 7. Consistency check between flat patterns and groups
# ============================================================

class TestGroundTruthConsistency:
    def test_agreeing_representations_report_nothing(self):
        groups = [_group(patterns=[MAPPED_PATTERN],
                         required=["sequential_accumulation"])]
        assert find_ground_truth_disagreements([MAPPED_PATTERN], groups) == []

    def test_declared_pattern_missing_from_groups_is_reported(self):
        groups = [_group(patterns=[MAPPED_PATTERN],
                         required=["sequential_accumulation"])]
        findings = find_ground_truth_disagreements(
            [MAPPED_PATTERN, SAME_DIRECTION_PATTERN], groups
        )
        assert [f["kind"] for f in findings] == ["pattern_not_in_groups"]
        assert findings[0]["pattern"] == SAME_DIRECTION_PATTERN

    def test_group_pattern_missing_from_label_is_reported(self):
        groups = [_group(patterns=[MAPPED_PATTERN, SAME_DIRECTION_PATTERN],
                         required=["sequential_accumulation"])]
        findings = find_ground_truth_disagreements([MAPPED_PATTERN], groups)
        assert [f["kind"] for f in findings] == ["group_pattern_not_declared"]
        assert findings[0]["pattern"] == SAME_DIRECTION_PATTERN

    def test_concept_not_derivable_from_patterns_is_reported(self):
        """Alternative groups the flat label cannot express must be surfaced."""
        groups = [
            _group(id="group_0", patterns=[ALTERNATING_PATTERN],
                   required=["dp_bottom_up"]),
            _group(id="group_1", patterns=[ALTERNATING_PATTERN],
                   required=["dp_top_down"]),
        ]
        findings = find_ground_truth_disagreements([ALTERNATING_PATTERN], groups)
        kinds = {f["kind"] for f in findings}
        assert "concept_not_derived_from_patterns" in kinds
        missing = [f for f in findings
                   if f["kind"] == "concept_not_derived_from_patterns"]
        assert missing[0]["group_id"] == "group_1"
        assert missing[0]["concept"] == "dp_top_down"
        assert missing[0]["derivable_concepts"] == ["dp_bottom_up"]

    def test_derivable_group_does_not_fire_the_concept_check(self):
        groups = [_group(patterns=[ALTERNATING_PATTERN], required=["dp_bottom_up"])]
        findings = find_ground_truth_disagreements([ALTERNATING_PATTERN], groups)
        assert findings == []

    def test_unmatchable_group_is_reported_with_its_reason(self):
        findings = find_ground_truth_disagreements(
            [UNMAPPED_PATTERN], [_group(patterns=[UNMAPPED_PATTERN], required=[])]
        )
        kinds = [f["kind"] for f in findings]
        assert "unmatchable_group" in kinds
        finding = next(f for f in findings if f["kind"] == "unmatchable_group")
        assert UNMAPPED_PATTERN in finding["detail"]
        assert finding["patterns"] == [UNMAPPED_PATTERN]

    def test_stale_vocabulary_group_does_not_report_drift_after_refresh(self):
        """The check verifies agreement with the CURRENT vocabulary."""
        group = _group(patterns=[SAME_DIRECTION_PATTERN],
                       required=PATTERN_TO_V1_MAPPING[SAME_DIRECTION_PATTERN]["required"])
        assert find_ground_truth_disagreements([SAME_DIRECTION_PATTERN], [group]) == []

    def test_stale_vocabulary_group_reports_drift_before_refresh(self):
        group = _group(patterns=[SAME_DIRECTION_PATTERN],
                       required=["bidirectional_index_scan"])
        findings = find_ground_truth_disagreements([SAME_DIRECTION_PATTERN], [group])
        assert any(f["kind"] == "concept_not_derived_from_patterns" for f in findings)

    def test_empty_inputs_report_nothing(self):
        assert find_ground_truth_disagreements([], []) == []
        assert find_ground_truth_disagreements(None, None) == []

    def test_curated_label_override_does_not_report_false_drift(self):
        """A curated pattern label may override the production patterns while the
        group keeps the concepts derived from the original ones. That is by
        design, so it must not be reported as drift."""
        group = _group(patterns=["monotonic_stack"], required=["recursive_branching"])
        group["derivation_patterns"] = ["dfs_recursive"]
        assert find_ground_truth_disagreements(["monotonic_stack"], [group]) == []

    def test_concept_check_prefers_derivation_patterns(self):
        group = _group(patterns=[MAPPED_PATTERN], required=["unrelated_strategy"])
        group["derivation_patterns"] = [MAPPED_PATTERN]
        findings = find_ground_truth_disagreements([MAPPED_PATTERN], [group])
        assert any(f["kind"] == "concept_not_derived_from_patterns" for f in findings)

        group["required"] = ["sequential_accumulation"]
        assert find_ground_truth_disagreements([MAPPED_PATTERN], [group]) == []

    def test_unrecognised_patterns_are_not_judged(self):
        """Derivability cannot be judged for patterns outside the mapping."""
        group = _group(patterns=["not_a_real_pattern"], required=["dp_bottom_up"])
        assert find_ground_truth_disagreements(["not_a_real_pattern"], [group]) == []

    def test_findings_are_json_serializable(self):
        groups = [_group(patterns=[UNMAPPED_PATTERN], required=[])]
        findings = find_ground_truth_disagreements([UNMAPPED_PATTERN], groups)
        json.dumps(findings)


# ============================================================
# 8. End-to-end: a refreshed group can be satisfied
# ============================================================

SAME_DIRECTION_MERGE = '''
class Solution:
    def mergeTwoLists(self, a, b):
        dummy = tail = None
        while a and b:
            if a.val <= b.val:
                tail.next = a
                a = a.next
            else:
                tail.next = b
                b = b.next
            tail = tail.next
        return dummy
'''


class TestRefreshedGroupIsSatisfiable:
    def _run(self, groups):
        from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

        return run_shadow_analysis(SAME_DIRECTION_MERGE, solution_groups=groups)

    def test_stale_stored_group_blocks_confirmation(self):
        stale = [_group(patterns=[SAME_DIRECTION_PATTERN],
                        required=["bidirectional_index_scan"],
                        excluded=["two_pointers_opposite"])]
        assert self._run(stale)["match_outcome"]["outcome"] != "CONFIRMED"

    def test_refreshed_group_confirms(self):
        groups = [_group(patterns=[SAME_DIRECTION_PATTERN],
                         required=["bidirectional_index_scan"],
                         excluded=["two_pointers_opposite"],
                         provenance=[VOCABULARY_DERIVATION_MARKER])]
        refresh_groups_vocabulary(groups)
        assert groups[0]["required"] == ["forward_pointer_advance"]
        outcome = self._run(groups)["match_outcome"]
        assert outcome["outcome"] == "CONFIRMED"
        assert outcome["satisfied_group_ids"] == ["group_0"]

    def test_refresh_does_not_grant_confirmation_to_unrelated_code(self):
        """Refreshing vocabulary must not manufacture evidence."""
        from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

        scalar_loop = """
class Solution:
    def count(self, nums):
        total = 0
        while total < 10:
            total = total + 1
        return total
"""
        groups = [_group(patterns=[SAME_DIRECTION_PATTERN],
                         required=["bidirectional_index_scan"],
                         provenance=[VOCABULARY_DERIVATION_MARKER])]
        refresh_groups_vocabulary(groups)
        outcome = run_shadow_analysis(scalar_loop, solution_groups=groups)["match_outcome"]
        assert outcome["outcome"] != "CONFIRMED"


# ============================================================
# 9. Live ground-truth invariants (integration)
# ============================================================

@pytest.fixture(scope="module")
def live_group_pairs():
    """Every (problem_id, group) pair the live loader actually returns.

    Collected once per module — the sweep is a full DB round trip.
    """
    import config  # noqa: F401  (loads .env)
    from pathforge.db.db import get_connection
    from pathforge.services.problem_resolver import _load_ground_truth

    pairs = []
    conn = get_connection()
    try:
        conn.execute("SELECT problem_id FROM problem_ground_truth ORDER BY problem_id")
        pids = [r["problem_id"] for r in conn.fetchall()]
        for pid in pids:
            groups, _ = _load_ground_truth(conn, pid)
            for group in groups:
                pairs.append((pid, group))
    finally:
        conn.close()
    if not pairs:
        pytest.skip("no ground-truth groups available in this database")
    return pairs


class TestLiveGroundTruthInvariants:
    """Invariants that must hold for every problem's effective groups.

    These assert the general contract, not a per-problem expectation.
    """

    def test_loaded_groups_always_carry_matchability(self, live_group_pairs):
        for pid, group in live_group_pairs:
            assert "matchable" in group, f"problem {pid}: {group}"

    def test_loaded_groups_without_required_explain_themselves(self, live_group_pairs):
        for pid, group in live_group_pairs:
            if not group.get("required"):
                assert group["matchable"] is False, f"problem {pid}: {group}"
                assert group.get("matchability_reason"), f"problem {pid}: {group}"

    def test_matchable_groups_have_required_concepts(self, live_group_pairs):
        for pid, group in live_group_pairs:
            if group["matchable"]:
                assert group["required"], f"problem {pid}: {group}"

    def test_no_stale_group_without_an_explanation(self, live_group_pairs):
        """Every group that disagrees with the current vocabulary must carry a
        refresh marker or a curated authority tier.

        Judged against the patterns the concepts were derived from, since a
        curated label may deliberately override the production patterns.
        """
        for pid, group in live_group_pairs:
            patterns = group.get("derivation_patterns") or group.get("patterns") or []
            if not patterns or any(p not in PATTERN_TO_V1_MAPPING for p in patterns):
                continue
            derivable = set()
            for pattern in patterns:
                derivable.update(PATTERN_TO_V1_MAPPING[pattern]["required"])
            if not derivable:
                continue
            if set(group.get("required") or []) == derivable:
                continue
            provenance = group.get("provenance") or []
            assert group.get("authority_tier") or VOCABULARY_REFRESH_MARKER in provenance, (
                f"problem {pid}: unexplained vocabulary drift for {group}"
            )

    def test_loaded_groups_keep_derivation_patterns_when_label_differs(
        self, live_group_pairs
    ):
        """When the curated label overrides the production patterns, the
        derivation patterns must still be carried so drift stays detectable."""
        for pid, group in live_group_pairs:
            if "derivation_patterns" not in group:
                continue
            assert isinstance(group["derivation_patterns"], list), \
                f"problem {pid}: {group}"
            if group["derivation_patterns"] != group.get("patterns"):
                assert group["derivation_patterns"], (
                    f"problem {pid}: override without recorded derivation "
                    f"patterns: {group}"
                )

    def test_consistency_findings_use_known_kinds(self, live_group_pairs):
        known = {
            "pattern_not_in_groups", "group_pattern_not_declared",
            "concept_not_derived_from_patterns", "unmatchable_group",
        }
        for pid, group in live_group_pairs:
            for finding in find_ground_truth_disagreements(
                group.get("patterns") or [], [group]
            ):
                assert finding["kind"] in known, f"problem {pid}: {finding}"
                json.dumps(finding)
