"""B5 — authority gating (shadow path only).

These tests verify the additive authority layer introduced by B5:

* authority is evaluated **per family** from B3 coverage + B4 selection +
  the Ground-Truth group's declared authority tier;
* only ``HUMAN_APPROVED`` / ``EXTERNAL_VERIFIED`` authorize an expected-approach
  conclusion; ``STRUCTURALLY_OBSERVED`` / ``INFERRED`` do not;
* B5 never rewrites a B3 coverage state and never invents a B4 strategy;
* the submission aggregation preserves the family-level states;
* ``safe_for_product_scoring`` is false for every non-authoritative case;
* B2/B3/B4, the legacy matcher and the detectors are unchanged, and Ground
  Truth is never mutated.

Expected values were measured from the pipeline, not assumed.
"""

import ast
import copy
import json
import pathlib

import pytest

from pathforge.ast_analysis.shadow import authority_gating as ag
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
_RUNNER_PATH = _REPO_ROOT / "pathforge" / "ast_analysis" / "shadow" / "shadow_runner.py"
_CORPUS_A = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results.json"
)

_ADDITIVE_KEYS = ("evidence_state", "coverage", "strategy_selection", "authority")
_ELAPSED_MARKER = "elapsed_ms = (time.perf_counter() - t0) * 1000"


# ============================================================================
# Helpers + fixtures
# ============================================================================

def _pipeline(code):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    technique_evidence = detect_techniques(facts)
    strategy_evidence = evaluate_strategies(technique_evidence, facts)
    return facts, technique_evidence, strategy_evidence


def snapshot(code):
    return ev.build_evidence_snapshot(*_pipeline(code))


def family(required, family_id="fam", authority=None, **kwargs):
    fam = {"id": family_id, "required": list(required), **kwargs}
    if authority is not None:
        fam["authority_tier"] = authority
    return fam


def authority_for(code, groups):
    """Run the full shadow path and return the additive ``authority`` dict."""
    result = run_shadow_analysis(code, solution_groups=groups)
    assert result is not None
    return result["authority"]


def _strip_b5_lines(source: str) -> str:
    """The runner before the additive B5 batch, by deleting exactly its lines."""
    lines = source.splitlines(keepends=True)
    kept, i = [], 0
    while i < len(lines):
        line = lines[i]
        if "authority_gating import evaluate_authority" in line:
            i += 1
            continue
        if line.strip().startswith("# Step 9 (B5)"):
            while i < len(lines) and _ELAPSED_MARKER not in lines[i]:
                i += 1
            continue
        if '"authority": authority,' in line or line.strip().startswith(
            "# B5 additive key"
        ):
            i += 1
            continue
        kept.append(line)
        i += 1
    return "".join(kept)


@pytest.fixture(scope="module")
def pre_b5_shadow():
    """The shadow runner as it behaved before B5, for differential checks."""
    stripped = _strip_b5_lines(_RUNNER_PATH.read_text(encoding="utf-8"))
    assert "evaluate_authority" not in stripped, "B5 lines left behind in reconstruction"
    assert '"authority": authority,' not in stripped, "B5 key left behind"
    ns = {"__name__": "shadow_runner_pre_b5"}
    exec(compile(stripped, "<shadow_runner_pre_b5>", "exec"), ns)
    return ns["run_shadow_analysis"]


# --- real submissions -------------------------------------------------------

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

BINARY_SEARCH = """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""

BFS_102 = """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    q = deque([root])
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)
    return result
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


def _two_strategy_snapshot(confidence=0.9):
    return ev.build_evidence_snapshot(
        [], [],
        [
            StrategyEvidence(strategy_id="two_pointers_opposite", confidence=confidence),
            StrategyEvidence(strategy_id="sliding_window", confidence=confidence),
        ],
    )


# ============================================================================
# 1-2. Authorized cases
# ============================================================================

class TestAuthorized:

    def test_1_human_approved_confirmed_is_authoritative(self):
        groups = [family(["sliding_window"], authority="human_curated",
                         optional=["loop_state_tracking"],
                         excluded=["two_pointers_opposite"])]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["declared_authority_tier"] == "human_curated"
        assert fam["authority_tier"] == ag.HUMAN_APPROVED
        assert fam["coverage_state"] == "CONFIRMED"
        assert fam["primary_strategy"] == "sliding_window"
        assert fam["authoritative"] is True
        assert fam["reason_codes"] == [ag.REASON_AUTHORITATIVE_HUMAN_APPROVED]
        assert authority["aggregation"] == ag.AGG_ALL_FAMILIES_AUTHORITATIVE
        assert authority["safe_for_product_scoring"] is True

    def test_2_external_verified_confirmed_is_authoritative(self):
        groups = [family(["binary_search"], authority="externally_listed")]
        authority = authority_for(BINARY_SEARCH, groups)
        fam = authority["families"][0]
        assert fam["authority_tier"] == ag.EXTERNAL_VERIFIED
        assert fam["coverage_state"] == "CONFIRMED"
        assert fam["authoritative"] is True
        assert fam["reason_codes"] == [ag.REASON_AUTHORITATIVE_EXTERNAL_VERIFIED]
        assert authority["safe_for_product_scoring"] is True

    def test_editorial_tier_maps_to_human_approved(self):
        # The V2 Ground-Truth work writes human-approved family labels as
        # `editorial`; B5 must treat that as human adjudication, explicitly.
        groups = [family(["sliding_window"], authority="editorial")]
        fam = authority_for(WINDOW_209, groups)["families"][0]
        assert fam["declared_authority_tier"] == "editorial"
        assert fam["authority_tier"] == ag.HUMAN_APPROVED
        assert fam["authoritative"] is True


# ============================================================================
# 3-8. Non-authoritative cases
# ============================================================================

class TestNonAuthoritative:

    def test_3_structural_observation_only_is_not_authoritative(self):
        # Coverage CONFIRMED and B4 selects a primary, but the expectation was
        # only structurally observed: analyzer evidence, not Ground Truth.
        groups = [family(["sliding_window"], authority="structurally_observed")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "CONFIRMED"
        assert fam["primary_strategy"] == "sliding_window"
        assert fam["authority_tier"] == ag.STRUCTURALLY_OBSERVED
        assert fam["authoritative"] is False
        assert fam["reason_codes"] == [ag.REASON_STRUCTURAL_OBSERVATION_ONLY]
        assert authority["safe_for_product_scoring"] is False

    def test_3b_inferred_llm_proposed_is_not_authoritative(self):
        groups = [family(["sliding_window"], authority="llm_proposed")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["authority_tier"] == ag.INFERRED
        assert fam["authoritative"] is False
        assert fam["reason_codes"] == [ag.REASON_INFERRED_AUTHORITY]

    def test_3c_unrecognized_tier_is_flagged_and_inferred(self):
        groups = [family(["sliding_window"], authority="mystery_tier")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["authority_tier"] == ag.INFERRED
        assert fam["authority_known"] is False
        assert fam["authoritative"] is False
        assert fam["reason_codes"] == [ag.REASON_UNRECOGNIZED_AUTHORITY]

    def test_4_provisional_is_not_upgraded(self):
        # identifying PRESENT + a supporting/component requirement NOT_ESTABLISHED
        groups = [family(["sliding_window", "prefix_sum"], authority="human_curated")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "PROVISIONAL"
        assert fam["primary_strategy"] == "sliding_window"  # B4 still selects
        assert fam["authoritative"] is False
        assert fam["reason_codes"] == [ag.REASON_COVERAGE_NOT_CONFIRMED]
        assert authority["safe_for_product_scoring"] is False

    def test_5_unresolved_is_not_authoritative(self):
        groups = [family(["bfs_shortest_path"], authority="human_curated")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "UNRESOLVED"
        assert fam["authoritative"] is False

    def test_6_contradicted_is_not_authoritative(self):
        # binary_search is CONTRADICTED in a sliding-window submission (B2).
        groups = [family(["binary_search"], authority="human_curated")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "CONTRADICTED"
        assert fam["authoritative"] is False
        assert fam["reason_codes"] == [ag.REASON_COVERAGE_NOT_CONFIRMED]

    def test_7_no_ground_truth_is_not_authoritative(self):
        result = run_shadow_analysis(WINDOW_209, solution_groups=None)
        authority = result["authority"]
        assert authority["no_ground_truth"] is True
        assert authority["aggregation"] == ag.AGG_NO_GROUND_TRUTH
        assert authority["families"] == []
        assert authority["safe_for_product_scoring"] is False

    def test_8_unmatchable_is_not_authoritative(self):
        groups = [family([], authority="human_curated")]
        authority = authority_for(WINDOW_209, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "UNMATCHABLE"
        assert fam["authoritative"] is False
        assert authority["safe_for_product_scoring"] is False

    def test_8b_technique_family_is_never_authoritative(self):
        """LC1 shape: hash_lookup is a technique — identification != conclusion."""
        groups = [family(["hash_lookup"], authority="human_curated")]
        authority = authority_for(TWO_SUM, groups)
        fam = authority["families"][0]
        assert fam["primary_strategy"] is None
        assert fam["coverage_state"] == "PROVISIONAL"  # no conclusion-eligible present
        assert fam["authoritative"] is False


# ============================================================================
# 9-11. Coverage/selection interaction, family-level preservation
# ============================================================================

class TestInteraction:

    def test_9_b4_selection_cannot_bypass_b3(self):
        """A selected primary on a PROVISIONAL family stays non-authoritative."""
        snap = snapshot(WINDOW_209)
        groups = [family(["sliding_window", "prefix_sum"], authority="human_curated")]
        cov = fc.build_family_coverage(groups, snap)
        sel = ps.select_submission_primary(groups, snap, cov)
        assert sel.submission.selected == "sliding_window"  # B4 did select
        report = ag.evaluate_authority(groups, cov, sel)
        assert report.get("fam").primary_strategy == "sliding_window"
        assert report.get("fam").authoritative is False

    def test_10_no_primary_strategy_means_not_authoritative(self):
        # CONFIRMED is impossible without a conclusion-eligible concept, but a
        # family can be CONFIRMED while B4 reports no candidate only via a
        # mismatch — assert the guard directly.
        snap = snapshot(WINDOW_209)
        groups = [family(["sliding_window"], authority="human_curated")]
        cov = fc.build_family_coverage(groups, snap)
        # simulate a B4 layer that declined to select
        empty_sel = ps.SubmissionStrategySelection(
            submission=ps.select_primary_strategy([], snap),
            families=(ps.select_primary_strategy([], snap, scope=ps.SCOPE_FAMILY,
                                                 family_id="fam"),),
        )
        report = ag.evaluate_authority(groups, cov, empty_sel)
        fam = report.get("fam")
        assert fam.coverage_state == "CONFIRMED"
        assert fam.primary_strategy is None
        assert fam.authoritative is False
        assert fam.reason_codes == (ag.REASON_NO_PRIMARY_STRATEGY,)

    def test_11_family_level_authority_is_preserved(self):
        groups = [
            family(["sliding_window"], family_id="fam_a", authority="human_curated"),
            family(["bfs_shortest_path"], family_id="fam_b", authority="llm_proposed"),
        ]
        authority = authority_for(WINDOW_209, groups)
        assert len(authority["families"]) == 2
        by_id = {f["family_id"]: f for f in authority["families"]}
        assert by_id["fam_a"]["authoritative"] is True
        assert by_id["fam_b"]["authoritative"] is False
        assert authority["authoritative_family_count"] == 1
        assert authority["non_authoritative_family_count"] == 1

    def test_12_mixed_authority_submission_aggregation(self):
        groups = [
            family(["sliding_window"], family_id="fam_a", authority="human_curated"),
            family(["bfs_shortest_path"], family_id="fam_b", authority="llm_proposed"),
        ]
        authority = authority_for(WINDOW_209, groups)
        assert authority["aggregation"] == ag.AGG_MIXED_AUTHORITY
        assert authority["has_authoritative_family"] is True
        assert authority["safe_for_product_scoring"] is False

    def test_12b_no_authoritative_family_aggregation(self):
        groups = [family(["sliding_window"], authority="llm_proposed")]
        authority = authority_for(WINDOW_209, groups)
        assert authority["aggregation"] == ag.AGG_NO_AUTHORITATIVE_FAMILY
        assert authority["safe_for_product_scoring"] is False


# ============================================================================
# 13-14. Determinism + scoring safety
# ============================================================================

class TestDeterminismAndSafety:

    def test_13_aggregation_is_deterministic(self):
        groups = [
            family(["sliding_window"], family_id="fam_a", authority="human_curated"),
            family(["bfs_shortest_path"], family_id="fam_b", authority="llm_proposed"),
        ]
        first = authority_for(WINDOW_209, groups)
        second = authority_for(WINDOW_209, copy.deepcopy(groups))
        assert first == second
        assert ag._aggregate([], [], False) == ag.AGG_NO_GROUND_TRUTH

    def test_14_safe_for_product_scoring_is_false_for_all_non_authoritative(self):
        cases = [
            ([family(["sliding_window"], authority="llm_proposed")], WINDOW_209),
            ([family(["sliding_window"], authority="structurally_observed")], WINDOW_209),
            ([family(["binary_search"], authority="human_curated")], WINDOW_209),
            ([family([], authority="human_curated")], WINDOW_209),
            ([family(["bfs_shortest_path"], authority="human_curated")], WINDOW_209),
        ]
        for groups, code in cases:
            authority = authority_for(code, groups)
            assert authority["safe_for_product_scoring"] is False

    def test_14b_tier_map_never_promotes_unknown_to_authorizing(self):
        for raw in (None, "", "unknown", "unobserved", "bootstrap", "llm_proposed",
                    "structurally_observed", "made_up"):
            mapped = ag.map_authority_tier(raw)
            assert mapped not in ag.AUTHORIZING_TIERS


# ============================================================================
# Known cases
# ============================================================================

class TestKnownCases:

    def _record_groups(self, submission_id, authority):
        records = _corpus_a_records()
        rec = records[submission_id]
        groups = copy.deepcopy(rec["groups"])
        for g in groups:
            g.setdefault("authority_tier", authority)
        return rec["source_code"], groups

    def test_lc209_sliding_window_authority_follows_gt(self):
        code, groups = self._record_groups("db-190", "human_curated")
        authority = authority_for(code, groups)
        fam = authority["families"][0]
        assert fam["primary_strategy"] == "sliding_window"
        assert fam["coverage_state"] == "CONFIRMED"
        assert fam["authoritative"] is True

    def test_lc102_bfs_unknown_authority_is_structural_only(self):
        code, groups = self._record_groups("db-244", "unknown")
        authority = authority_for(code, groups)
        fam = authority["families"][0]
        assert fam["primary_strategy"] == "bfs_shortest_path"
        assert fam["coverage_state"] == "CONFIRMED"
        assert fam["authority_tier"] == ag.INFERRED
        assert fam["authoritative"] is False

    def test_lc704_binary_search_authoritative_when_gt_authorized(self):
        code, groups = self._record_groups("db-235", "human_curated")
        authority = authority_for(code, groups)
        fam = authority["families"][0]
        assert fam["primary_strategy"] == "binary_search"
        assert fam["authoritative"] is True

    @pytest.mark.parametrize("submission_id", ["db-49", "db-51", "db-194"])
    def test_lc3236_stays_non_authoritative(self, submission_id):
        # B3 is UNRESOLVED (no identifying requirement) and B4 has no candidate;
        # even a human-approved tier cannot manufacture a conclusion here.
        code, groups = self._record_groups(submission_id, "human_curated")
        authority = authority_for(code, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "UNRESOLVED"
        assert fam["primary_strategy"] is None
        assert fam["authoritative"] is False
        assert authority["safe_for_product_scoring"] is False

    def test_lc1_no_authoritative_conclusion(self):
        code, groups = self._record_groups("db-11", "human_curated")
        authority = authority_for(code, groups)
        fam = authority["families"][0]
        assert fam["coverage_state"] == "UNMATCHABLE"  # required == []
        assert fam["authoritative"] is False

    def test_lc560_no_fabricated_authority(self):
        snap = snapshot(HASH_AND_WINDOW)
        groups = [family(["frequency_counting", "sequential_accumulation"],
                         authority="human_curated")]
        cov = fc.build_family_coverage(groups, snap)
        sel = ps.select_submission_primary(groups, snap, cov)
        report = ag.evaluate_authority(groups, cov, sel)
        fam = report.get("fam")
        assert fam.primary_strategy is None
        assert fam.authoritative is False
        assert report.safe_for_product_scoring() is False


# ============================================================================
# 15-20. Invariants: legacy matcher, B2/B3/B4, detectors, Ground Truth
# ============================================================================

_WINDOW_GROUPS = [family(["sliding_window"], authority="human_curated")]


def _deterministic(shadow, drop_authority=True):
    keys = set(_ADDITIVE_KEYS) | {"elapsed_ms"}
    if not drop_authority:
        keys.discard("authority")
    return {k: v for k, v in shadow.items() if k not in keys}


class TestInvariants:

    def test_15_legacy_matcher_is_unchanged(self, pre_b5_shadow):
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(
            _WINDOW_GROUPS, techniques, strategies, facts
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result["match_outcome"]["outcome"] == direct.outcome
        assert result["match_outcome"]["primary_strategy"] == direct.primary_strategy

    def test_16_17_18_b2_b3_b4_are_byte_identical(self, pre_b5_shadow):
        for code, groups in (
            (WINDOW_209, _WINDOW_GROUPS),
            (TWO_SUM, None),
            (BINARY_SEARCH, [family(["binary_search"], authority="human_curated")]),
            (BFS_102, [family(["bfs_shortest_path"], authority="llm_proposed")]),
        ):
            pre = pre_b5_shadow(code, solution_groups=groups)
            post = run_shadow_analysis(code, solution_groups=groups)
            assert _deterministic(pre, drop_authority=False) == \
                _deterministic(post), code[:20]
            for key in ("evidence_state", "coverage", "strategy_selection",
                        "match_outcome", "technique_evidence", "strategy_evidence",
                        "structural_facts"):
                assert pre[key] == post[key], (code[:20], key)

    def test_19_detectors_and_strategies_are_unchanged(self, pre_b5_shadow):
        for code in (TWO_SUM, WINDOW_209, BINARY_SEARCH, BFS_102, HASH_AND_WINDOW):
            pre = pre_b5_shadow(code)
            post = run_shadow_analysis(code)
            assert pre["technique_evidence"] == post["technique_evidence"]
            assert pre["strategy_evidence"] == post["strategy_evidence"]
            assert pre["structural_facts"] == post["structural_facts"]

    def test_20_ground_truth_is_never_mutated(self):
        groups = [
            family(["sliding_window"], family_id="fam_a", authority="human_curated",
                   optional=["loop_state_tracking"],
                   excluded=["two_pointers_opposite"]),
        ]
        before = copy.deepcopy(groups)
        run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert groups == before

        snap = snapshot(WINDOW_209)
        cov = fc.build_family_coverage(groups, snap)
        sel = ps.select_submission_primary(groups, snap, cov)
        ag.evaluate_authority(groups, cov, sel)
        assert groups == before

    def test_authority_is_attached_and_additive(self):
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert set(result) == {
            "structural_facts", "technique_evidence", "strategy_evidence",
            "match_outcome", "extractor_version", "relations_version",
            "elapsed_ms", "evidence_state", "coverage", "strategy_selection",
            "authority",
        }
        assert set(result["authority"]) == {
            "no_ground_truth", "aggregation", "family_count",
            "authoritative_family_count", "non_authoritative_family_count",
            "has_authoritative_family", "safe_for_product_scoring",
            "authority_tier_counts", "coverage_state_counts", "reason_counts",
            "logical_requirement_count", "authoritative_logical_requirement_count",
            "alternative_group_count", "alternative_groups", "families",
        }

    def test_authority_failure_cannot_suppress_the_shadow_result(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("simulated authority failure")

        monkeypatch.setattr(
            "pathforge.ast_analysis.shadow.shadow_runner.evaluate_authority", boom
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=_WINDOW_GROUPS)
        assert result is not None
        assert result["authority"] is None
        assert result["coverage"] is not None
        assert result["strategy_selection"]["submission"]["selected"] == "sliding_window"

    def test_graceful_degradation_is_unchanged(self):
        assert run_shadow_analysis("def (invalid syntax") is None


# ============================================================================
# Production isolation
# ============================================================================

_GUARDED_PREFIXES = ("pathforge/api/", "src/",
                     "pathforge/ast_engine/", "pathforge/llm/", "pathforge/db/")
#: Services may import the canonical vocabulary/eligibility for B6 gating, but
#: must never run analysis through it.
_ALLOWED_SERVICE_IMPORTS = {"pathforge/services/product_eligibility.py"}


def _python_sources():
    skip = {".git", "node_modules", "__pycache__", ".pytest_cache", ".next"}
    for path in _REPO_ROOT.rglob("*.py"):
        if any(part in skip for part in path.parts):
            continue
        yield path


def test_production_modules_do_not_import_authority_gating():
    offenders = []
    for path in _python_sources():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        if not relative.startswith(_GUARDED_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "authority_gating" in text or "shadow.authority" in text:
            offenders.append(relative)
    assert offenders == [], offenders
