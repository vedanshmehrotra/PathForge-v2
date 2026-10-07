"""B4 — specificity + primary-strategy selection (shadow/presentation only).

These tests verify the selection layer introduced by B4:

* only registry ``conclusion_eligible`` concepts may become primary;
* observations and techniques never become primary — by metadata, not by a
  hand-written exclusion list;
* a strategy must be relevant to the evaluated family/submission;
* contradictions matter only when they are applicable family-level ones;
* deterministic ordering and an explicit ambiguity when the registry cannot
  distinguish equal candidates;
* family coverage and the old matcher are unchanged, and production is isolated.

Expected values were measured from the pipeline, not assumed.
"""

import ast
import json
import pathlib

import pytest

from pathforge.ast_analysis import concepts as registry
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import matching
from pathforge.ast_analysis.shadow import primary_strategy as ps
from pathforge.ast_analysis.shadow.data_structures import StrategyEvidence
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CORPUS_A = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results.json"
)
_CORPUS_B = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "disjoint301_eval_results_BASELINE_step4.json"
)


# ============================================================================
# Helpers
# ============================================================================

def _pipeline(code):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    technique_evidence = detect_techniques(facts)
    strategy_evidence = evaluate_strategies(technique_evidence, facts)
    return facts, technique_evidence, strategy_evidence


def snapshot(code):
    return ev.build_evidence_snapshot(*_pipeline(code))


def family(required, family_id="fam", **kwargs):
    return {"id": family_id, "required": list(required), **kwargs}


TWO_SUM = """
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
"""

WINDOW_209 = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    best = float('inf')
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            best = min(best, right - left + 1)
            total -= nums[left]
            left += 1
    return best if best != float('inf') else 0
"""

TWO_POINTERS = """
def isPalindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

HASH_AND_WINDOW = """
def solve(nums, target):
    seen = {}
    left = 0
    total = 0
    best = 0
    for right in range(len(nums)):
        total += nums[right]
        if target - nums[right] in seen:
            best = max(best, total)
        while total > target:
            total -= nums[left]
            left += 1
        seen[nums[right]] = right
    return best
"""


def _corpus_a_records():
    if not _CORPUS_A.exists():
        return {}
    payload = json.loads(_CORPUS_A.read_text(encoding="utf-8"))
    return {rec.get("external_submission_id"): rec for rec in payload["records"]}


def _corpus_b_records():
    if not _CORPUS_B.exists():
        return {}
    payload = json.loads(_CORPUS_B.read_text(encoding="utf-8"))
    return {rec["name"]: rec for rec in payload["records"]}


def _select_for_record(rec):
    snap = snapshot(rec["source_code"])
    groups = rec.get("groups") or None
    report = fc.build_family_coverage(groups, snap)
    return ps.select_submission_primary(groups, snap, report)


# ============================================================================
# 1-4. Eligibility
# ============================================================================

class TestEligibility:

    def test_1_strategy_present_can_be_primary(self):
        selection = ps.select_primary_strategy(["sliding_window"], snapshot(WINDOW_209))
        assert selection.selected == "sliding_window"
        assert selection.reason_codes == (ps.REASON_SINGLE_CANDIDATE,)
        assert [c.concept_id for c in selection.candidates] == ["sliding_window"]

    def test_2_observation_present_cannot_be_primary(self):
        snap = snapshot(WINDOW_209)
        # a real PRESENT raw observation (array_traversal has no shadow producer)
        assert snap.get("accumulator_update").state == ev.PRESENT
        assert registry.get_concept("accumulator_update").concept_class == \
            registry.OBSERVATION
        assert registry.get_concept("accumulator_update").conclusion_eligible is False
        selection = ps.select_primary_strategy(["accumulator_update"], snap)
        assert selection.selected is None
        assert selection.candidates == ()
        assert selection.reason_codes == (ps.REASON_NO_CONCLUSION_ELIGIBLE_PRESENT,)

    def test_3_technique_present_cannot_be_primary(self):
        snap = snapshot(TWO_SUM)
        assert snap.get("hash_lookup").state == ev.PRESENT
        assert registry.get_concept("hash_lookup").conclusion_eligible is False
        selection = ps.select_primary_strategy(["hash_lookup"], snap)
        assert selection.selected is None
        assert selection.candidates == ()

    def test_4_strategy_beats_non_conclusion_evidence(self):
        selection = ps.select_primary_strategy(
            ["sequential_accumulation", "sliding_window"], snapshot(WINDOW_209)
        )
        assert [c.concept_id for c in selection.candidates] == ["sliding_window"]
        assert selection.selected == "sliding_window"

    def test_all_generic_evidence_is_non_eligible(self):
        for concept_id in ("array_traversal", "brute_force", "sorting",
                           "recursive_branching", "sequential_accumulation",
                           "forward_pointer_advance", "candidate_selection"):
            assert registry.get_concept(concept_id).conclusion_eligible is False


# ============================================================================
# 5. Family scoping
# ============================================================================

class TestFamilyScope:

    def test_5_unrelated_strategy_does_not_activate_a_family(self):
        """sliding_window is PRESENT but not required by this family."""
        snap = snapshot(WINDOW_209)
        assert snap.get("sliding_window").state == ev.PRESENT
        selection = ps.family_primary_strategy(
            family(["sequential_accumulation"]), snap
        )
        assert selection.selected is None

        report = fc.build_family_coverage(family(["sequential_accumulation"]), snap)
        submission = ps.select_submission_primary(
            family(["sequential_accumulation"]), snap, report
        )
        assert submission.submission.selected is None

    def test_relevance_is_the_scope(self):
        """Same snapshot: the strategy is selectable only where it is required."""
        snap = snapshot(WINDOW_209)
        assert ps.family_primary_strategy(family(["sliding_window"]), snap).selected \
            == "sliding_window"
        assert ps.family_primary_strategy(family(["loop_state_tracking"]), snap).selected \
            is None


# ============================================================================
# 6-11. Named real cases
# ============================================================================

class TestNamedCases:

    @pytest.mark.parametrize("submission_id", ["db-49", "db-51", "db-194"])
    def test_6_LC3236_does_not_manufacture_a_strategy(self, submission_id):
        records = _corpus_a_records()
        if submission_id not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records[submission_id])
        assert selection.submission.selected is None
        for fam in selection.families:
            assert fam.selected is None

    def test_7_LC209_selects_sliding_window(self):
        records = _corpus_a_records()
        if "db-190" not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records["db-190"])
        assert selection.submission.selected == "sliding_window"

    def test_8_LC102_selects_bfs_shortest_path(self):
        records = _corpus_a_records()
        if "db-244" not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records["db-244"])
        assert selection.submission.selected == "bfs_shortest_path"

    def test_9_LC704_selects_binary_search(self):
        records = _corpus_a_records()
        if "db-235" not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records["db-235"])
        assert selection.submission.selected == "binary_search"

    def test_10_LC1_does_not_promote_hash_lookup(self):
        records = _corpus_a_records()
        if "db-11" not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records["db-11"])
        assert selection.submission.selected is None

    def test_11_LC560_does_not_fabricate_a_strategy(self):
        """A hash-map/frequency family has no conclusion-eligible concept."""
        # synthetic: frequency_counting + sequential_accumulation are non-eligible
        canonical = family(["frequency_counting", "sequential_accumulation"])
        selection = ps.family_primary_strategy(canonical, snapshot(HASH_AND_WINDOW))
        assert selection.selected is None
        assert selection.candidates == ()

        # and the real 301 corpus case
        records = _corpus_b_records()
        rec = records.get("hm_subarray_sum_k")
        if rec is not None:
            snap = snapshot(rec["code"])
            groups = [{"id": rec["name"], "required": list(rec["required_concepts"] or [])}]
            assert ps.select_submission_primary(groups, snap).submission.selected is None

    def test_recursive_case_selects_its_strategy(self):
        records = _corpus_a_records()
        if "db-242" not in records:
            pytest.skip("corpus unavailable")
        selection = _select_for_record(records["db-242"])
        assert selection.submission.selected == "dfs_backtracking"


# ============================================================================
# 12-13. Contradiction
# ============================================================================

class TestContradiction:

    def test_12_concept_contradiction_does_not_blindly_eliminate_strategy(self):
        """binary_search is CONTRADICTED in a sliding-window submission; the
        unrelated sliding_window candidate is unaffected."""
        snap = snapshot(WINDOW_209)
        assert snap.get("binary_search").state == ev.CONTRADICTED
        selection = ps.select_primary_strategy(["sliding_window"], snap)
        assert selection.selected == "sliding_window"

    def test_13_applicable_family_contradiction_is_respected(self):
        snap = snapshot(WINDOW_209)  # binary_search CONTRADICTED
        report = fc.build_family_coverage([family(["binary_search"])], snap)
        assert report.families[0].coverage_state == fc.CONTRADICTED

        selection = ps.family_primary_strategy(
            family(["binary_search"]), snap, family_contradicted=True
        )
        assert selection.selected is None
        assert selection.reason_codes == (ps.REASON_FAMILY_CONTRADICTED,)

        submission = ps.select_submission_primary(
            [family(["binary_search"])], snap, report
        )
        assert submission.submission.selected is None
        assert submission.families[0].reason_codes == (ps.REASON_FAMILY_CONTRADICTED,)


# ============================================================================
# 14. Deterministic tie-breaking / ambiguity
# ============================================================================

class TestTieBreaking:

    def _two_strategy_snapshot(self, confidence=0.9):
        return ev.build_evidence_snapshot(
            [],
            [],
            [
                StrategyEvidence(strategy_id="two_pointers_opposite", confidence=confidence),
                StrategyEvidence(strategy_id="sliding_window", confidence=confidence),
            ],
        )

    def test_14_tie_is_broken_deterministically_and_flagged(self):
        snap = self._two_strategy_snapshot()
        assert snap.get("sliding_window").state == ev.PRESENT
        assert snap.get("two_pointers_opposite").state == ev.PRESENT

        first = ps.select_primary_strategy(
            ["two_pointers_opposite", "sliding_window"], snap
        )
        second = ps.select_primary_strategy(
            ["sliding_window", "two_pointers_opposite"], snap
        )
        # concept_id lexicographic decides; input order must not matter
        assert first.selected == "sliding_window"
        assert second.selected == "sliding_window"
        assert first.reason_codes == (ps.REASON_TIE_BROKEN_BY_CONCEPT_ID,)
        assert first.tie_resolved is True
        assert first.ambiguity is True

    def test_confidence_breaks_a_tie_before_concept_id(self):
        snap = self._two_strategy_snapshot()
        # make two_pointers_opposite clearly stronger
        snap = ev.build_evidence_snapshot(
            [],
            [],
            [
                StrategyEvidence(strategy_id="two_pointers_opposite", confidence=0.95),
                StrategyEvidence(strategy_id="sliding_window", confidence=0.7),
            ],
        )
        selection = ps.select_primary_strategy(
            ["sliding_window", "two_pointers_opposite"], snap
        )
        assert selection.selected == "two_pointers_opposite"
        assert selection.reason_codes == (ps.REASON_SELECTED_BY_CONFIDENCE,)
        assert selection.ambiguity is False


# ============================================================================
# 15-16. Coverage and the old matcher are unchanged
# ============================================================================

_WINDOW_GROUPS = [{"id": "group_0", "required": ["sliding_window"]}]


class TestNoSideEffects:

    def test_15_family_coverage_is_not_changed_by_b4(self):
        snap = snapshot(WINDOW_209)
        expected = fc.build_family_coverage(_WINDOW_GROUPS, snap).to_dict()
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result["coverage"] == expected

    def test_16_old_matcher_output_is_unchanged(self):
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(
            _WINDOW_GROUPS, techniques, strategies, facts
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result["match_outcome"]["outcome"] == direct.outcome
        # the old matcher's own nested primary_strategy is retained, not replaced
        assert "primary_strategy" in result["match_outcome"]
        assert result["strategy_selection"]["submission"]["selected"] == "sliding_window"

    def test_b4_output_is_attached_and_additive(self):
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert set(result) == {
            "structural_facts", "technique_evidence", "strategy_evidence",
            "match_outcome", "extractor_version", "relations_version",
            "elapsed_ms", "evidence_state", "coverage", "strategy_selection",
            "authority",
        }
        selection = result["strategy_selection"]
        assert set(selection) == {"submission", "families"}
        assert set(selection["submission"]) == {
            "scope", "family_id", "selected", "reason_codes", "tie_resolved",
            "ambiguity", "candidates",
        }

    def test_selection_failure_cannot_suppress_the_shadow_result(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("simulated selection failure")

        monkeypatch.setattr(
            "pathforge.ast_analysis.shadow.shadow_runner.select_submission_primary",
            boom,
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result is not None
        assert result["strategy_selection"] is None
        assert result["coverage"] is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_graceful_degradation_is_unchanged(self):
        assert run_shadow_analysis("def (invalid syntax") is None


# ============================================================================
# 17. Production isolation
# ============================================================================

_GUARDED_PREFIXES = ("pathforge/api/", "pathforge/services/", "src/",
                     "pathforge/ast_engine/", "pathforge/llm/", "pathforge/db/")


def _python_sources():
    skip = {".git", "node_modules", "__pycache__", ".pytest_cache", ".next"}
    for path in _REPO_ROOT.rglob("*.py"):
        if any(part in skip for part in path.parts):
            continue
        yield path


class TestProductionIsolation:

    #: Tokens that can only come from the B4 module. The bare word
    #: ``primary_strategy`` is deliberately NOT used: it is a pre-existing field
    #: of the old matcher's ``MatchOutcome`` and appears in production modules.
    _B4_TOKENS = ("shadow." + "primary_strategy", "select_submission_primary")

    def test_17_no_production_module_references_primary_strategy(self):
        offenders = []
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if not relative.startswith(_GUARDED_PREFIXES):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in self._B4_TOKENS):
                offenders.append(relative)
        assert offenders == []

    def test_only_the_shadow_runner_references_the_selector(self):
        referers = set()
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "select_submission_primary" in text:
                referers.add(relative)
        assert referers <= {
            "pathforge/ast_analysis/shadow/shadow_runner.py",
            "pathforge/ast_analysis/shadow/primary_strategy.py",
            "pathforge/tests/test_primary_strategy.py",
            # reconstruction helpers strip the B4 lines by name
            "pathforge/tests/test_tri_state_evidence.py",
            # the B5 authority tests drive the selector to evaluate authority
            "pathforge/tests/test_authority_gating.py",
            # the B5.5 normalization tests drive the selector for ONE_OF sets
            "pathforge/tests/test_gt_authority_normalization.py",
            # the B6 eligibility tests drive the selector for product gating
            "pathforge/tests/test_b6_product_eligibility.py",
            # the B6.5 normalization tests drive the selector for conflict gating
            "pathforge/tests/test_b6_5_authority_persistence.py",
            "experiments/code_analysis_evaluation/runners/tri_state_b2_measure.py",
            "experiments/code_analysis_evaluation/runners/primary_strategy_b4_measure.py",
        }

    def test_legacy_matching_does_not_consume_the_selector(self):
        source = (
            _REPO_ROOT / "pathforge" / "ast_analysis" / "shadow" / "matching.py"
        ).read_text(encoding="utf-8")
        # `primary_strategy` is a pre-existing old-matcher field and must remain;
        # the B4 selector must not be consumed here.
        assert "select_primary_strategy" not in source
        assert "select_submission_primary" not in source
        assert "shadow.primary_strategy" not in source
