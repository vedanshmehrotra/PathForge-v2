"""B3 — family coverage + PROVISIONAL state (shadow path only).

These tests verify the layer B3 adds *above* B2:

* one immutable coverage record per expected family, built from the existing
  Ground-Truth groups and the B2 concept snapshot;
* the six family states and their exact rules;
* the conclusion-eligible gate (a family with only TECHNIQUE/SUPPORT evidence
  can never be CONFIRMED);
* that a concept-level CONTRADICTED is escalated to the family only when it is
  an *applicable* (identifying) requirement — never blindly;
* that the existing matcher and the production paths remain untouched.

Expected states here were measured from the pipeline, not assumed.
"""

import ast
import json
import pathlib

import pytest

from pathforge.ast_analysis import concepts as registry
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import matching
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


def cover(required, code, **kwargs):
    return fc.coverage_for_family(family(required, **kwargs), snapshot(code))


# --- real submissions (same fixtures B2 uses) --------------------------------

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

NESTED_LOOP_ONLY = """
def maxProduct(nums):
    best = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] * nums[j] > best:
                best = nums[i] * nums[j]
    return best
"""

MINIMAL = "def f(x):\n    return x\n"


# ============================================================================
# 1-6. The coverage rules
# ============================================================================

class TestCoverageRules:

    def test_1_all_identifying_present_is_confirmed(self):
        """All identifying requirements PRESENT + a conclusion-eligible concept."""
        cov = cover(["sliding_window"], WINDOW_209)
        assert cov.identifying_required == ("sliding_window",)
        assert cov.present_identifying == ("sliding_window",)
        assert cov.conclusion_eligible_present == ("sliding_window",)
        assert cov.coverage_state == fc.CONFIRMED
        assert cov.reason_codes == (fc.REASON_CONFIRMED,)

    def test_2_identifying_present_supporting_not_established_is_provisional(self):
        """Case B: identity established, a component unobserved → PROVISIONAL."""
        cov = cover(["sliding_window", "linked_list_traversal"], WINDOW_209)
        assert cov.present_identifying == ("sliding_window",)
        assert cov.supporting_required == ("linked_list_traversal",)
        assert cov.not_established_supporting == ("linked_list_traversal",)
        assert cov.coverage_state == fc.PROVISIONAL
        assert cov.reason_codes == (fc.REASON_SUPPORTING_NOT_ESTABLISHED,)

    def test_3_identifying_not_established_is_unresolved(self):
        """Case C: the family's identity is not established → UNRESOLVED."""
        cov = cover(["sliding_window"], TWO_SUM)
        assert cov.not_established_identifying == ("sliding_window",)
        assert cov.coverage_state == fc.UNRESOLVED
        assert cov.reason_codes == (fc.REASON_IDENTIFYING_NOT_ESTABLISHED,)

    def test_4_silence_never_becomes_contradiction(self):
        """Silence is NOT_ESTABLISHED and can only ever yield UNRESOLVED."""
        cov = cover(["hash_lookup"], MINIMAL)
        assert cov.not_established_identifying == ("hash_lookup",)
        assert cov.contradicted_identifying == ()
        assert cov.coverage_state == fc.UNRESOLVED
        assert cov.coverage_state != fc.CONTRADICTED

    def test_5_supporting_not_established_never_becomes_contradiction(self):
        """Case D: a missing component is PROVISIONAL, never CONTRADICTED."""
        cov = cover(["sliding_window", "linked_list_traversal"], WINDOW_209)
        assert cov.coverage_state == fc.PROVISIONAL
        assert cov.coverage_state != fc.CONTRADICTED
        assert cov.contradicted_identifying == ()
        assert cov.contradicted_supporting == ()

    def test_6_no_conclusion_eligible_present_cannot_confirm(self):
        """The false-confirmation fence.

        ``hash_lookup`` is IDENTIFYING (it may identify a family) but it is a
        TECHNIQUE, so it is not conclusion-eligible. Even with it PRESENT the
        family cannot be CONFIRMED.
        """
        assert registry.get_concept("hash_lookup").conclusion_eligible is False
        cov = cover(["hash_lookup"], TWO_SUM)
        assert cov.present_identifying == ("hash_lookup",)
        assert cov.conclusion_eligible_present == ()
        assert cov.coverage_state == fc.PROVISIONAL
        assert cov.reason_codes == (fc.REASON_NO_CONCLUSION_ELIGIBLE,)
        assert fc.family_has_conclusion_eligible_present(
            family(["hash_lookup"]), snapshot(TWO_SUM)
        ) is False

    def test_no_identifying_requirement_is_unresolved(self):
        """A family of components only has no identity anchor → UNRESOLVED.

        This is the LC3236 shape: the recorded Ground Truth requires only
        ``sequential_accumulation`` (a COMPONENT).
        """
        cov = cover(["sequential_accumulation"], WINDOW_209)
        assert cov.identifying_required == ()
        assert cov.supporting_required == ("sequential_accumulation",)
        assert cov.coverage_state == fc.UNRESOLVED
        assert cov.reason_codes == (fc.REASON_NO_IDENTIFYING_REQUIREMENT,)


# ============================================================================
# 7. Identification is not a conclusion
# ============================================================================

class TestIdentificationIsNotAConclusion:

    def test_7_identifying_technique_identifies_without_concluding(self):
        """``candidate_selection`` identifies the greedy family but is a TECHNIQUE.

        It may satisfy the family's identity requirement and still must never be
        reported as a strategy conclusion, and the family must not CONFIRM.
        """
        concept = registry.get_concept("candidate_selection")
        assert concept.concept_class == registry.TECHNIQUE
        assert concept.family_role == registry.IDENTIFYING
        assert concept.conclusion_eligible is False

        snap = snapshot(NESTED_LOOP_ONLY)
        assert snap.get("candidate_selection").state == ev.PRESENT

        cov = cover(["candidate_selection"], NESTED_LOOP_ONLY)
        assert cov.present_identifying == ("candidate_selection",)
        assert cov.coverage_state == fc.PROVISIONAL
        assert cov.coverage_state != fc.CONFIRMED

        # and it is not a reported strategy conclusion
        _, _, strategy_evidence = _pipeline(NESTED_LOOP_ONLY)
        assert "candidate_selection" not in {s.strategy_id for s in strategy_evidence}


# ============================================================================
# 8-9. Contradiction escalation
# ============================================================================

class TestContradictionEscalation:

    def test_8_non_applicable_concept_contradiction_is_not_escalated(self):
        """A broad B2 contradiction on a non-required concept stays concept-level.

        ``WINDOW_209`` structurally contradicts ``binary_search`` (via
        ``opposite_direction_updates``). A sliding-window family does not require
        ``binary_search``, so the family is confirmed and NOT contradicted.
        """
        assert snapshot(WINDOW_209).get("binary_search").state == ev.CONTRADICTED
        cov = cover(["sliding_window"], WINDOW_209)
        assert cov.coverage_state == fc.CONFIRMED
        assert cov.coverage_state != fc.CONTRADICTED

    def test_8b_dfs_backtracking_contradiction_is_not_escalated(self):
        """The B2 audit's decisive case: ``cache_lookup`` contradicts
        ``dfs_backtracking`` in essentially every hash-map solution, but a
        family that does not require ``dfs_backtracking`` is unaffected."""
        assert snapshot(TWO_SUM).get("dfs_backtracking").state == ev.CONTRADICTED
        cov = cover(["hash_lookup"], TWO_SUM)
        assert cov.coverage_state != fc.CONTRADICTED
        assert cov.contradicted_identifying == ()

    def test_9_applicable_identifying_contradiction_is_escalated(self):
        """When the contradicted concept IS the family's identity → CONTRADICTED."""
        cov = cover(["binary_search"], WINDOW_209)
        assert cov.contradicted_identifying == ("binary_search",)
        assert cov.coverage_state == fc.CONTRADICTED
        assert cov.reason_codes == (fc.REASON_IDENTIFYING_CONTRADICTED,)

    def test_contradiction_outranks_an_unestablished_identifying_requirement(self):
        """A contradiction is decisive even if another identifying concept is NE."""
        snap = snapshot(TWO_SUM)  # dfs_backtracking CONTRADICTED, binary_search NE
        cov = fc.coverage_for_family(
            family(["binary_search", "dfs_backtracking"]), snap
        )
        assert cov.coverage_state == fc.CONTRADICTED


# ============================================================================
# 10-11. NO_GROUND_TRUTH / UNMATCHABLE
# ============================================================================

class TestNoGroundTruthAndUnmatchable:

    def test_10_no_ground_truth(self):
        report = fc.build_family_coverage([], snapshot(TWO_SUM))
        assert report.no_ground_truth is True
        assert report.families == ()
        assert report.aggregate_state() == fc.NO_GROUND_TRUTH
        assert report.counts()[fc.NO_GROUND_TRUTH] == 0  # no family record exists

        report_none = fc.build_family_coverage(None, snapshot(TWO_SUM))
        assert report_none.no_ground_truth is True

    def test_11_unmatchable(self):
        cov = cover([], TWO_SUM)
        assert cov.coverage_state == fc.UNMATCHABLE
        assert cov.reason_codes == (fc.REASON_UNMATCHABLE,)
        report = fc.build_family_coverage(
            [{"id": "g", "required": []}], snapshot(TWO_SUM)
        )
        assert report.aggregate_state() == fc.UNMATCHABLE


# ============================================================================
# States are complete and the report is deterministic
# ============================================================================

class TestCoverageModel:

    def test_exactly_six_states_exist(self):
        assert set(fc.COVERAGE_STATES) == {
            fc.CONFIRMED, fc.PROVISIONAL, fc.UNRESOLVED,
            fc.CONTRADICTED, fc.NO_GROUND_TRUTH, fc.UNMATCHABLE,
        }
        assert not [s for s in dir(fc) if s in {"ABSENT", "FAILED", "NO_MATCH"}]

    def test_report_is_deterministic(self):
        groups = [
            {"id": "a", "required": ["sliding_window"]},
            {"id": "b", "required": ["binary_search"]},
        ]
        first = fc.build_family_coverage(groups, snapshot(WINDOW_209)).to_dict()
        second = fc.build_family_coverage(groups, snapshot(WINDOW_209)).to_dict()
        assert first == second
        assert first["aggregate_state"] == fc.CONTRADICTED

    def test_every_family_gets_exactly_one_state(self):
        groups = [{"id": f"g{i}", "required": req} for i, req in enumerate(
            [["sliding_window"], ["hash_lookup"], [], ["binary_search"]]
        )]
        report = fc.build_family_coverage(groups, snapshot(WINDOW_209))
        assert len(report.families) == 4
        for cov in report.families:
            assert cov.coverage_state in fc.COVERAGE_STATES

    def test_role_and_eligibility_come_from_the_registry(self):
        assert fc.is_identifying("sliding_window") is True
        assert fc.is_identifying("sequential_accumulation") is False
        assert fc.is_conclusion_eligible("sliding_window") is True
        assert fc.is_conclusion_eligible("hash_lookup") is False
        assert fc.family_role_of("not_a_concept") is None


# ============================================================================
# 12. Existing shadow output remains present
# ============================================================================

_WINDOW_GROUPS = [{"id": "group_0", "required": ["sliding_window"]}]


class TestShadowWiring:

    def test_12_coverage_is_attached_alongside_the_existing_output(self):
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result is not None
        assert "coverage" in result
        assert "match_outcome" in result  # the OLD matcher is still present
        assert "evidence_state" in result
        assert result["coverage"] is not None
        assert result["coverage"]["aggregate_state"] == fc.CONFIRMED
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_coverage_does_not_overwrite_the_old_matcher(self):
        """The old matcher's outcome is independent of B3 coverage."""
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(
            _WINDOW_GROUPS, techniques, strategies, facts
        )
        assert result["match_outcome"]["outcome"] == direct.outcome
        # B3 can legitimately differ from the old matcher; it must not overwrite it.
        # A required=[binary_search] family is contradicted by the old matcher too,
        # but a required=[sequential_accumulation] family is old-CONFIRMED and
        # B3-UNRESOLVED (no identifying requirement) — proving they are separate.
        groups = [{"id": "g", "required": ["sequential_accumulation"]}]
        res = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert res["match_outcome"]["outcome"] == "CONFIRMED"
        assert res["coverage"]["families"][0]["coverage_state"] == fc.UNRESOLVED

    def test_no_groups_is_no_ground_truth_but_shadow_still_runs(self):
        result = run_shadow_analysis(WINDOW_209, solution_groups=None)
        assert result is not None
        assert result["coverage"]["no_ground_truth"] is True
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"  # unchanged

    def test_coverage_failure_cannot_suppress_the_shadow_result(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("simulated coverage failure")

        monkeypatch.setattr(
            "pathforge.ast_analysis.shadow.shadow_runner.build_family_coverage", boom
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result is not None
        assert result["coverage"] is None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"
        assert result["evidence_state"] is not None

    def test_graceful_degradation_is_unchanged(self):
        assert run_shadow_analysis("def (invalid syntax") is None


# ============================================================================
# 13. The old matcher is untouched
# ============================================================================

class TestOldMatcherUntouched:

    def test_13_matching_module_does_not_reference_coverage(self):
        source = (
            _REPO_ROOT / "pathforge" / "ast_analysis" / "shadow" / "matching.py"
        ).read_text(encoding="utf-8")
        assert "family_coverage" not in source
        assert "coverage_state" not in source

    def test_matching_still_produces_its_declared_outcomes(self):
        facts, techniques, strategies = _pipeline(WINDOW_209)
        outcome = matching.evaluate_solution_groups(
            _WINDOW_GROUPS, techniques, strategies, facts
        )
        assert outcome.outcome in {"CONFIRMED", "UNRESOLVED", "CONTRADICTED"}
        assert outcome.satisfied_group_ids == ["group_0"]


# ============================================================================
# 14. Production paths remain untouched
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

    def test_14_no_production_module_references_family_coverage(self):
        """Production must not run family coverage — except the explicitly
        authorized B6 consumers (eligibility/parity read coverage results via
        the B5 authority report; neither executes analysis itself)."""
        authorized = {
            # B6: reads the B3-derived authority report for the product gate
            "pathforge/services/product_eligibility.py",
            # B7: observational parity only; never executes a pipeline
            "pathforge/services/legacy_shadow_parity.py",
            # B8: GT-authority metadata reconciliation; never runs analysis
            "pathforge/services/authority_reconciliation.py",
        }
        offenders = []
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if not relative.startswith(_GUARDED_PREFIXES):
                continue
            if relative in authorized:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "family_coverage" in text or "build_family_coverage" in text:
                offenders.append(relative)
        assert offenders == []

    def test_only_the_shadow_runner_references_family_coverage(self):
        referers = set()
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "build_family_coverage" in text:
                referers.add(relative)
        assert referers <= {
            "pathforge/ast_analysis/shadow/shadow_runner.py",
            "pathforge/ast_analysis/shadow/family_coverage.py",
            "pathforge/tests/test_family_coverage.py",
            # the B2 reconstruction helper strips the B3 lines by name
            "pathforge/tests/test_tri_state_evidence.py",
            # the B4 test consumes the coverage report for its scoping checks
            "pathforge/tests/test_primary_strategy.py",
            # the B5 authority tests build coverage to evaluate authority
            "pathforge/tests/test_authority_gating.py",
            # the B5.5 normalization tests build coverage for alternative sets
            "pathforge/tests/test_gt_authority_normalization.py",
            # the B6 eligibility tests build coverage to decide product gating
            "pathforge/tests/test_b6_product_eligibility.py",
            # the B6.5 normalization tests build coverage for conflict gating
            "pathforge/tests/test_b6_5_authority_persistence.py",
            "experiments/code_analysis_evaluation/runners/family_coverage_b3_measure.py",
            # the B2 measurement runner strips the B3 lines by name too
            "experiments/code_analysis_evaluation/runners/tri_state_b2_measure.py",
        }


# ============================================================================
# Required regression cases (real corpus submissions)
# ============================================================================

def _corpus_records():
    if not _CORPUS_A.exists():
        return {}
    payload = json.loads(_CORPUS_A.read_text(encoding="utf-8"))
    return {rec.get("external_submission_id"): rec for rec in payload["records"]}


def _coverage_for_record(rec):
    snap = snapshot(rec["source_code"])
    return fc.build_family_coverage(rec.get("groups") or [], snap)


class TestRequiredRegressions:

    @pytest.mark.parametrize("submission_id", ["db-49", "db-51", "db-194"])
    def test_LC3236_never_confirms_without_a_conclusion_eligible_concept(
        self, submission_id
    ):
        """The critical false-confirmation case must not remain CONFIRMED.

        The recorded family requires only ``sequential_accumulation`` — a
        COMPONENT technique that is not conclusion-eligible — so B3 must not
        confirm it.
        """
        records = _corpus_records()
        if submission_id not in records:
            pytest.skip("corpus unavailable")
        rec = records[submission_id]
        report = _coverage_for_record(rec)
        for cov in report.families:
            assert cov.coverage_state != fc.CONFIRMED, cov.family_id
            assert cov.conclusion_eligible_present == ()
        assert report.aggregate_state() != fc.CONFIRMED

    def test_LC209_sliding_window_confirms_and_contradiction_is_not_escalated(self):
        records = _corpus_records()
        if "db-190" not in records:
            pytest.skip("corpus unavailable")
        rec = records["db-190"]
        report = _coverage_for_record(rec)
        states = {c.family_id: c.coverage_state for c in report.families}
        assert fc.CONFIRMED in states.values()
        assert fc.CONTRADICTED not in states.values()

    def test_concept_contradictions_are_retained_at_concept_level(self):
        """At least one real submission has a concept CONTRADICTED while no
        family is contradicted."""
        records = _corpus_records()
        if not records:
            pytest.skip("corpus unavailable")
        found = False
        for rec in records.values():
            snap = snapshot(rec["source_code"])
            if not snap.by_state(ev.CONTRADICTED):
                continue
            report = fc.build_family_coverage(rec.get("groups") or [], snap)
            if report.families and not report.by_state(fc.CONTRADICTED):
                found = True
                break
        assert found, "expected a non-escalated concept contradiction in the corpus"
