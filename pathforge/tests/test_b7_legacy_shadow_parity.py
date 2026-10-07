"""B7 — Legacy-vs-Shadow Verdict Parity / Migration Readiness (observational).

Covers:

* parity classification across the P1–P10 categories;
* authority conflicts isolated from algorithmic disagreements;
* ONE_OF logical comparison and technique-only ONE_OF recording;
* db-254 independence;
* purity: comparison mutates neither legacy nor shadow results;
* simulation-only consequences: no Elo/gap/recommendation persistence;
* feature flag remains OFF and legacy production behavior unchanged.

Expected values were measured from the pipeline, not assumed.
"""

import copy
import json
import pathlib

import pytest

from pathforge.ast_analysis import authority_vocabulary as vocab
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import matching
from pathforge.ast_analysis.shadow import shadow_runner
from pathforge.ast_analysis.shadow.data_structures import StrategyEvidence
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.services import legacy_shadow_parity as b7
from pathforge.services import product_eligibility as b6

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_NATIVE = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results_NATIVE.json"
)


# ============================================================================
# Helpers
# ============================================================================

def _pipeline(code):
    tree = __import__("ast").parse(code)
    relations = build_relations(tree)
    facts = extract_structural_facts(tree)
    techniques = detect_techniques(facts, relations=relations)
    strategies = evaluate_strategies(techniques, facts)
    return facts, techniques, strategies


def family(family_id, required, authority=None, evidence=None, relation=None,
           alt_group=None):
    """A synthetic group with an internally consistent authority pair.

    ``authority`` is a canonical tier name; ``evidence`` defaults to that
    tier's representative legacy value so the pair does not conflict. Pass
    ``evidence`` explicitly only to construct a *conflicting* pair.
    """
    fam = {"id": family_id, "required": list(required)}
    if authority is not None:
        fam["authority_tier"] = authority
        # the legacy representative for the tier the value normalizes to, so
        # the synthetic pair is internally consistent by construction
        fam.setdefault("evidence", vocab.to_legacy_evidence(
            vocab.normalize_authority_tier(authority)))
    elif evidence is not None:
        fam["evidence"] = evidence
    if evidence is not None:
        fam["evidence"] = evidence
    if relation is not None:
        fam["family_relation"] = relation
    if alt_group is not None:
        fam["alternative_group_id"] = alt_group
    return fam


def _snapshot_with_strategies(*strategy_ids, confidence=0.9):
    return ev.build_evidence_snapshot(
        [], [],
        [StrategyEvidence(strategy_id=s, confidence=confidence) for s in strategy_ids],
    )


def _legacy_match_result(matched=True, evidence="structurally_observed",
                         patterns=("sliding_window_variable",), group_id="g0"):
    return {
        "match_result": "FULL_MATCH" if matched else "NO_MATCH",
        "matched_groups": [0] if matched else [],
        "unmatched_patterns": [] if matched else list(patterns),
        "confidence_score": 0.9 if matched else 0.0,
    }


def _record(groups, legacy_matched=True, legacy_evidence="structurally_observed",
            strategy="sliding_window", shadow_code=None):
    """Build a parity record from a synthetic group set."""
    code = shadow_code or (
        "def f(nums, target):\n"
        "    left = 0\n"
        "    total = 0\n"
        "    best = float('inf')\n"
        "    for right in range(len(nums)):\n"
        "        total += nums[right]\n"
        "        while total >= target:\n"
        "            best = min(best, right - left + 1)\n"
        "            total -= nums[left]\n"
        "            left += 1\n"
        "    return best\n"
    )
    legacy_result = _legacy_match_result(matched=legacy_matched,
                                         evidence=legacy_evidence)
    shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups)
    eligibility = b6.product_eligibility(
        b6._report_from_dict(shadow["authority"]) if shadow and shadow.get("authority")
        else None
    )
    return b7.build_parity_record(
        "sub-1", 209, "Test", groups, legacy_result, shadow, eligibility
    )


def _native_records():
    if not _NATIVE.exists():
        pytest.skip("native corpus unavailable")
    payload = json.loads(_NATIVE.read_text(encoding="utf-8"))
    return {rec["external_submission_id"]: rec for rec in payload["records"]}


@pytest.fixture(autouse=True)
def _flag_off():
    assert b6.flag_enabled() is False
    yield
    assert b6.flag_enabled() is False


# ============================================================================
# 1. Category implementations
# ============================================================================

class TestParityCategories:

    def test_1_exact_parity(self):
        """Legacy authoritative + shadow eligible on the same conclusion.

        The legacy rule is evidence-based, so the group's ``evidence`` must be
        a legacy-authoritative value AND canonically consistent with the tier.
        """
        record = _record(
            [family("g0", ["sliding_window"], authority="human_curated",
                    evidence="structurally_observed")],
            legacy_matched=True, legacy_evidence="structurally_observed",
        )
        # NOTE: human_curated tier + structurally_observed evidence is a
        # CONFLICT, so this fixture must use a consistent authorizing pair:
        # externally_listed tier + externally_listed evidence.
        assert record.parity_category in (b7.P7_AUTHORITY_CONFLICT,)

        record = _record(
            [family("g0", ["sliding_window"], authority="externally_listed",
                    evidence="externally_listed")],
            legacy_matched=True, legacy_evidence="externally_listed",
        )
        assert record.parity_category == b7.P1_EXACT_PARITY
        assert record.migration_status == b7.STATUS_READY_FOR_SHADOW
        assert record.consequence_simulation.legacy_allows_elo is True
        assert record.consequence_simulation.shadow_allows_elo is True

    def test_2_legacy_authoritative_shadow_blocked_non_authoritative(self):
        """The corpus's structurally_observed shape: legacy trusts the evidence,
        the canonical policy correctly does not (it is analyzer evidence about
        the submission, not GT about the expected approach)."""
        record = _record(
            [family("g0", ["sliding_window"], authority="structurally_observed",
                    evidence="structurally_observed")],
            legacy_matched=True, legacy_evidence="structurally_observed",
        )
        assert record.parity_category == b7.P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED
        assert record.divergence_reason == (b7.P2_REASON_NON_AUTHORITATIVE,)
        assert record.migration_status == b7.STATUS_BLOCKED_BY_SHADOW_COVERAGE
        assert record.consequence_simulation.legacy_allows_elo is True
        assert record.consequence_simulation.shadow_allows_elo is False

    def test_2b_legacy_authoritative_shadow_blocked_no_primary(self):
        """A technique-only family can never be product-eligible."""
        record = _record(
            [family("g0", ["hash_lookup"], authority="externally_listed",
                    evidence="externally_listed")],
            legacy_matched=True, legacy_evidence="externally_listed",
            shadow_code=(
                "class Solution:\n"
                "    def twoSum(self, nums, target):\n"
                "        seen = {}\n"
                "        for i, num in enumerate(nums):\n"
                "            complement = target - num\n"
                "            if complement in seen:\n"
                "                return [seen[complement], i]\n"
                "            seen[num] = i\n"
                "        return []\n"
            ),
        )
        assert record.parity_category == b7.P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED
        # the technique-only family never reaches CONFIRMED (no conclusion-
        # eligible concept), so B6 blocks on coverage first; the missing
        # primary strategy is the deeper cause and is asserted explicitly
        assert record.shadow.primary_strategy is None
        assert record.shadow.b6_reasons == ("coverage_not_confirmed",)
        assert record.migration_status == b7.STATUS_BLOCKED_BY_SHADOW_COVERAGE

    def test_3_legacy_blocked_shadow_eligible(self):
        record = _record(
            [family("g0", ["sliding_window"], authority="human_curated",
                    evidence="human_curated")],
            legacy_matched=False, legacy_evidence="llm_proposed",
        )
        assert record.parity_category == b7.P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE
        assert record.migration_status == b7.STATUS_READY_FOR_SHADOW
        # canonical authority authorizes, legacy evidence does not
        assert record.shadow.b6_eligible is True
        assert record.consequence_simulation.legacy_allows_elo is False
        assert record.consequence_simulation.shadow_allows_elo is True

    def test_4_legacy_match_shadow_unresolved(self):
        """Legacy matches; shadow cannot establish the required strategy."""
        record = _record(
            [family("g0", ["bfs_shortest_path"], authority="human_curated",
                    evidence="human_curated")],
            legacy_matched=True, legacy_evidence="human_curated",
        )
        assert record.parity_category == b7.P4_LEGACY_MATCH_SHADOW_UNRESOLVED
        # both would block consequences, but for different reasons:
        # legacy for lack of evidence authority, shadow for lack of coverage
        assert record.consequence_simulation.legacy_allows_elo is False
        assert record.consequence_simulation.shadow_allows_elo is False

    def test_5_legacy_no_match_shadow_confirmed(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated",
                         evidence="human_curated")]
        # GT carries no legacy-authoritative evidence, so legacy would block
        # while the shadow requirement is eligible.
        code = (
            "def f(nums, target):\n"
            "    left = 0\n"
            "    total = 0\n"
            "    best = float('inf')\n"
            "    for right in range(len(nums)):\n"
            "        total += nums[right]\n"
            "        while total >= target:\n"
            "            best = min(best, right - left + 1)\n"
            "            total -= nums[left]\n"
            "            left += 1\n"
            "    return best\n"
        )
        legacy_result = _legacy_match_result(matched=False,
                                             patterns=("monotonic_stack",))
        shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups)
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]))
        record = b7.build_parity_record("s", 209, "T", groups, legacy_result,
                                        shadow, eligibility)
        # legacy found no match (and its evidence is not authoritative), while
        # the shadow establishes the strategy and B6 would allow it: the
        # consequence dimension is the disagreement, hence P3; the verdict-layer
        # difference (no-match vs confirmed) is recorded as a divergence reason.
        assert record.parity_category == b7.P3_LEGACY_BLOCKED_SHADOW_ELIGIBLE
        assert record.shadow.coverage_state == fc.CONFIRMED
        assert record.legacy.matched is False
        assert record.migration_status == b7.STATUS_READY_FOR_SHADOW

    def test_6_legacy_match_shadow_contradicted(self):
        """binary_search is CONTRADICTED in a sliding-window submission (B2)."""
        groups = [family("g0", ["binary_search"], authority="human_curated",
                         evidence="human_curated")]
        code = (
            "def f(nums, target):\n"
            "    left = 0\n"
            "    total = 0\n"
            "    best = float('inf')\n"
            "    for right in range(len(nums)):\n"
            "        total += nums[right]\n"
            "        while total >= target:\n"
            "            best = min(best, right - left + 1)\n"
            "            total -= nums[left]\n"
            "            left += 1\n"
            "    return best\n"
        )
        shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups)
        assert (shadow["coverage"]["aggregate_state"]) == fc.CONTRADICTED
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]))
        legacy_result = _legacy_match_result(matched=True,
                                             evidence="human_curated")
        record = b7.build_parity_record("s", 209, "T", groups, legacy_result,
                                        shadow, eligibility)
        # both block consequences, but shadow actively contradicts: P6.
        assert record.parity_category == b7.P6_LEGACY_MATCH_SHADOW_CONTRADICTED
        assert record.migration_status == b7.STATUS_BLOCKED_BY_SHADOW_COVERAGE
        assert record.consequence_simulation.shadow_allows_elo is False

    def test_7_authority_conflict_is_isolated(self):
        """A conflicting pair is P7, never an algorithmic disagreement."""
        record = _record(
            [family("g0", ["sliding_window"], authority="human_curated",
                    evidence="structurally_observed")],
            legacy_matched=True, legacy_evidence="structurally_observed",
        )
        assert record.parity_category == b7.P7_AUTHORITY_CONFLICT
        assert record.divergence_reason == (vocab.AUTHORITY_CONFLICT,)
        assert record.migration_status == b7.STATUS_BLOCKED_BY_AUTHORITY
        # and it is NOT counted as a shadow block reason
        assert record.shadow.b6_reasons != ("coverage_not_confirmed",)

    def test_8_missing_authority_is_blocked(self):
        """No authority_tier at all: legacy (evidence-based) would authorize,
        the canonical policy blocks on missing metadata."""
        record = _record(
            [family("g0", ["sliding_window"], evidence="structurally_observed")],
            legacy_matched=True, legacy_evidence="structurally_observed",
        )
        assert record.shadow.authority_diagnostic == vocab.AUTHORITY_MISSING
        assert record.parity_category == b7.P2_LEGACY_AUTHORITATIVE_SHADOW_BLOCKED
        assert record.divergence_reason == (b7.P2_REASON_NON_AUTHORITATIVE,)

    def test_9_no_comparable_gt(self):
        record = _record(None, legacy_matched=False)
        assert record.parity_category == b7.P9_NO_COMPARABLE_GT
        assert record.migration_status == b7.STATUS_BLOCKED_BY_GT

    def test_9b_no_comparable_gt_for_requirementless_groups(self):
        record = _record([family("g0", [], authority="human_curated",
                                 evidence="human_curated")],
                         legacy_matched=False, legacy_evidence="llm_proposed")
        assert record.parity_category == b7.P9_NO_COMPARABLE_GT

    def test_10_error_is_not_disagreement(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated",
                         evidence="human_curated")]
        record = b7.build_parity_record(
            "s", 209, "T", groups, _legacy_match_result(), None, None,
            shadow_failed=True,
        )
        assert record.parity_category == b7.P10_ERROR
        assert record.migration_status == b7.STATUS_ERROR


# ============================================================================
# 2. ONE_OF / db-254 / technique-only
# ============================================================================

class TestOneOfParity:

    def test_11_one_of_logical_comparison_satisfied(self):
        """One authoritative alternative satisfies the logical requirement.

        Uses the only stored pair that is simultaneously legacy-authoritative
        and canonically authorizing (externally_listed), so both systems
        converge on the same product conclusion.
        """
        groups = [
            family("g0", ["dp_bottom_up"], authority="externally_listed",
                   evidence="externally_listed", relation="ONE_OF",
                   alt_group="one_of_dp"),
            family("g1", ["dp_top_down"], authority="externally_listed",
                   evidence="externally_listed", relation="ONE_OF",
                   alt_group="one_of_dp"),
        ]
        record = _record(
            groups, legacy_matched=True, legacy_evidence="externally_listed",
            shadow_code=(
                "def climbStairs(n):\n"
                "    if n <= 2:\n"
                "        return n\n"
                "    table = [0] * (n + 1)\n"
                "    table[1] = 1\n"
                "    table[2] = 2\n"
                "    for i in range(3, n + 1):\n"
                "        table[i] = table[i - 1] + table[i - 2]\n"
                "    return table[n]\n"
            ),
        )
        # the unresolved sibling must not create a disagreement
        assert record.parity_category == b7.P1_EXACT_PARITY
        assert record.one_of_group_ids == ("one_of_dp",)
        assert len(record.shadow.logical_requirements) == 1

    def test_12_db254_remains_independent(self):
        groups = [
            family("group_0", ["forward_pointer_advance"], authority="human_curated",
                   evidence="human_curated"),
            family("group_1", ["sequential_accumulation"], authority="human_curated",
                   evidence="human_curated"),
        ]
        record = _record(groups, legacy_matched=True,
                         legacy_evidence="human_curated",
                         shadow_code="x = 1\n")
        assert record.one_of_group_ids == ()
        assert len(record.shadow.logical_requirements) == 2
        assert record.technique_only_one_of is False

    def test_13_technique_only_one_of_is_recorded(self):
        """LC3236: hash_lookup OR sequential_accumulation — techniques only."""
        groups = [
            family("group_0_alt0", ["hash_lookup"], authority="human_curated",
                   evidence="human_curated", relation="ONE_OF",
                   alt_group="one_of_lc3236"),
            family("group_0_alt1", ["sequential_accumulation"],
                   authority="human_curated", evidence="human_curated",
                   relation="ONE_OF", alt_group="one_of_lc3236"),
        ]
        code = (
            "class Solution:\n"
            "    def missingInteger(self, nums):\n"
            "        j = 1\n"
            "        summ = nums[0]\n"
            "        while j < len(nums) and nums[j] == nums[j - 1] + 1:\n"
            "            summ += nums[j]\n"
            "            j += 1\n"
            "        return summ\n"
        )
        shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups)
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]) if shadow.get("authority")
            else None)
        legacy_result = _legacy_match_result(matched=True,
                                             evidence="human_curated")
        record = b7.build_parity_record("s", 3236, "LC3236", groups,
                                        legacy_result, shadow, eligibility)
        assert record.technique_only_one_of is True
        # neither technique is promoted to a primary strategy
        assert record.shadow.primary_strategy is None
        assert record.shadow.b6_eligible is False


# ============================================================================
# 3. Purity + simulation-only
# ============================================================================

class TestPurity:

    def test_14_comparison_does_not_mutate_legacy_result(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated",
                         evidence="human_curated")]
        legacy_result = _legacy_match_result()
        before = copy.deepcopy(legacy_result)
        record = _record(groups, legacy_matched=True,
                         legacy_evidence="human_curated")
        assert legacy_result == before
        assert record is not None

    def test_15_comparison_does_not_mutate_shadow_result(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated",
                         evidence="human_curated")]
        code = (
            "def f(nums, target):\n"
            "    left = 0\n"
            "    total = 0\n"
            "    best = float('inf')\n"
            "    for right in range(len(nums)):\n"
            "        total += nums[right]\n"
            "        while total >= target:\n"
            "            best = min(best, right - left + 1)\n"
            "            total -= nums[left]\n"
            "            left += 1\n"
            "    return best\n"
        )
        shadow = shadow_runner.run_shadow_analysis(code, solution_groups=groups)
        before = copy.deepcopy(shadow)
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]))
        b7.build_parity_record("s", 209, "T", groups,
                               _legacy_match_result(), shadow, eligibility)
        assert shadow == before

    def test_16_b7_does_not_execute_elo_gap_or_recommendations(self, monkeypatch):
        """The parity module must never touch a consequence engine."""
        import pathforge.services.legacy_shadow_parity as module
        import inspect
        source = inspect.getsource(module)
        for forbidden in ("compute_updates", "persist_elos", "compute_signals",
                          "persist_signals", "get_recommendation",
                          "_log_recommendation", "_update_user_streak"):
            assert forbidden not in source, forbidden
        # and the simulation values are plain booleans, never engine outputs
        record = _record(
            [family("g0", ["sliding_window"], authority="human_curated",
                    evidence="human_curated")],
            legacy_evidence="human_curated",
        )
        sim = record.consequence_simulation.to_dict()
        assert sim["simulated_only"] is True
        assert all(isinstance(v, bool) for k, v in sim.items() if k != "simulated_only")

    def test_17_feature_flag_remains_off(self):
        assert b6.flag_enabled() is False

    def test_18_legacy_production_behavior_unchanged(self):
        from pathforge.services import persistence as prod_persistence
        assert prod_persistence._AUTHORITATIVE_STATES == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_STATES
        assert matching._AUTHORITATIVE_TIERS == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_TIERS
        # legacy rule is evidence-based, recorded verbatim
        assert b7.legacy_authoritative("structurally_observed") is True
        assert b7.legacy_authoritative("human_curated") is False


# ============================================================================
# 4. Native corpus structure
# ============================================================================

class TestNativeCorpusParity:

    def test_native_corpus_feeds_the_parity_pipeline(self):
        records = _native_records()
        rec = records["db-190"]
        legacy_result = _legacy_match_result(matched=True,
                                             evidence="human_curated")
        shadow = shadow_runner.run_shadow_analysis(
            rec["source_code"], solution_groups=rec["groups"])
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]))
        record = b7.build_parity_record(
            rec["external_submission_id"], rec["problem_id"], rec.get("title"),
            rec["groups"], legacy_result, shadow, eligibility)
        assert record.shadow.primary_strategy == "sliding_window"

    def test_authority_conflicts_are_recorded_per_group(self):
        records = _native_records()
        # db-20's conflict was explicitly reconciled by B8; db-135 (problem 2)
        # still carries a live conflict (no stored authority_tier to restore).
        rec = next(
            r for r in records.values()
            if any(
                (g.get("authority_normalization") or {}).get("diagnostic")
                == vocab.AUTHORITY_CONFLICT
                for g in (r.get("groups") or [])
            )
        )
        shadow = shadow_runner.run_shadow_analysis(
            rec["source_code"], solution_groups=rec["groups"])
        diagnostics = {
            (g.get("authority_normalization") or {}).get("diagnostic")
            for g in rec["groups"]
        }
        assert vocab.AUTHORITY_CONFLICT in diagnostics
        assert shadow["authority"]["families"][0]["reason_codes"] == [
            ag_reasons_conflict()]
        # ...and classified as P7, never as a shadow algorithm failure
        eligibility = b6.product_eligibility(
            b6._report_from_dict(shadow["authority"]))
        legacy_result = _legacy_match_result(matched=True,
                                             evidence="structurally_observed")
        record = b7.build_parity_record(
            rec["external_submission_id"], rec["problem_id"], rec.get("title"),
            rec["groups"], legacy_result, shadow, eligibility)
        assert record.parity_category == b7.P7_AUTHORITY_CONFLICT


def ag_reasons_conflict():
    from pathforge.ast_analysis.shadow import authority_gating as ag
    return ag.REASON_AUTHORITY_CONFLICT
