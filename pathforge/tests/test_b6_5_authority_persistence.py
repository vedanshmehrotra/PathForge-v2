"""B6.5 — canonical authority persistence normalization + native corpus.

Covers:

* the explicit evidence ↔ authority_tier normalization (mapping, round-trip);
* conflict handling — conflicting stored pairs fail closed, never silently pass;
* B6 consuming canonical authority and rejecting conflicts;
* ONE_OF / db-254 unchanged;
* flag-OFF legacy behavior unchanged;
* native vs enriched corpus provenance discipline.

Expected values were measured from the pipeline, not assumed.
"""

import copy
import json
import pathlib

import pytest

from pathforge.ast_analysis import authority_vocabulary as vocab
from pathforge.ast_analysis.shadow import authority_gating as ag
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import matching
from pathforge.ast_analysis.shadow import primary_strategy as ps
from pathforge.ast_analysis.shadow.data_structures import StrategyEvidence
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.services import product_eligibility as b6
from pathforge.services.ground_truth_builder import (
    deserialize_solution_groups,
    mark_family_relations,
    serialize_solution_groups,
)
from pathforge.services.problem_resolver import _load_ground_truth

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CORPUS_A = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results.json"
)
_NATIVE_CORPUS = (
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


def snapshot_with_strategies(*strategy_ids, confidence=0.9):
    return ev.build_evidence_snapshot(
        [], [],
        [StrategyEvidence(strategy_id=s, confidence=confidence) for s in strategy_ids],
    )


def family(family_id, required, authority=None, relation=None, alt_group=None,
           evidence=None):
    fam = {"id": family_id, "required": list(required)}
    if authority is not None:
        fam["authority_tier"] = authority
    if evidence is not None:
        fam["evidence"] = evidence
    if relation is not None:
        fam["family_relation"] = relation
    if alt_group is not None:
        fam["alternative_group_id"] = alt_group
    return fam


def eligibility_for(groups, snap):
    cov = fc.build_family_coverage(groups, snap)
    sel = ps.select_submission_primary(groups, snap, cov)
    report = ag.evaluate_authority(groups, cov, sel)
    return b6.product_eligibility(report), report


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, gt_row, curated=None):
        self._gt_row = gt_row
        self._curated = curated

    def execute(self, query, params=None):
        if "problem_ground_truth" in query:
            return _Result(self._gt_row)
        if "FROM problems" in query:
            return _Result({"pattern": self._curated}
                           if self._curated is not None else None)
        return _Result(None)


def _load(solution_groups, pid=999, curated=None, patterns=None):
    conn = _FakeConnection({
        "patterns": patterns if patterns is not None else [],
        "confidence": {},
        "solution_groups": solution_groups,
        "validation_status": "unverified",
    }, curated=curated)
    return _load_ground_truth(conn, pid)


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


# ============================================================================
# 1. Every B5.5 authority mapping (regression: unchanged)
# ============================================================================

class TestCanonicalMappings:

    @pytest.mark.parametrize("stored, expected", [
        ("human_curated", vocab.HUMAN_APPROVED),
        ("human_approved", vocab.HUMAN_APPROVED),
        ("reviewed", vocab.HUMAN_APPROVED),
        ("editorial", vocab.HUMAN_APPROVED),
        ("externally_listed", vocab.EXTERNAL_VERIFIED),
        ("external_verified", vocab.EXTERNAL_VERIFIED),
        ("structurally_observed", vocab.STRUCTURALLY_OBSERVED),
        ("llm_proposed", vocab.INFERRED),
        ("bootstrap", vocab.INFERRED),
        ("unobserved", vocab.INFERRED),
        ("unknown", vocab.INFERRED),
        ("inferred", vocab.INFERRED),
        ("hypothesis", vocab.INFERRED),
        ("", vocab.INFERRED),
        (None, vocab.INFERRED),
        ("made_up", vocab.INFERRED),
    ])
    def test_16a_every_b5_5_mapping_is_unchanged(self, stored, expected):
        assert vocab.normalize_authority_tier(stored) == expected

    def test_only_two_tiers_authorize(self):
        assert vocab.AUTHORIZING_TIERS == frozenset({
            vocab.HUMAN_APPROVED, vocab.EXTERNAL_VERIFIED,
        })


# ============================================================================
# 2. Canonical round-trip
# ============================================================================

class TestCanonicalRoundTrip:

    GROUP = {
        "id": "group_0", "required": ["sliding_window"],
        "authority_tier": "human_curated", "evidence": "human_curated",
        "provenance": ["csv_curated"], "version": 1,
        "family_relation": "ONE_OF", "alternative_group_id": "one_of_x",
    }

    def test_16b_canonical_authority_round_trip(self):
        restored = deserialize_solution_groups(
            json.dumps(serialize_solution_groups([self.GROUP]))
        )
        assert restored == [self.GROUP]
        stored, canonical = vocab.canonical_authority_of_group(restored[0])
        assert stored == "human_curated"
        assert canonical == vocab.HUMAN_APPROVED

    def test_16c_evidence_to_authority_normalization(self):
        for evidence, tier in [
            ("structurally_observed", vocab.STRUCTURALLY_OBSERVED),
            ("externally_listed", vocab.EXTERNAL_VERIFIED),
            ("human_curated", vocab.HUMAN_APPROVED),
            ("editorial", vocab.HUMAN_APPROVED),
            ("llm_proposed", vocab.INFERRED),
            ("bootstrap", vocab.INFERRED),
            ("unobserved", vocab.INFERRED),
            ("unknown", vocab.INFERRED),
        ]:
            record = vocab.normalize_group_authority({"evidence": evidence})
            assert record["evidence_canonical_tier"] == tier, evidence

    def test_16d_authority_to_compatibility_representation(self):
        assert vocab.to_legacy_evidence(vocab.HUMAN_APPROVED) == "human_curated"
        assert vocab.to_legacy_evidence(vocab.EXTERNAL_VERIFIED) == "externally_listed"
        assert vocab.to_legacy_evidence(vocab.STRUCTURALLY_OBSERVED) == \
            "structurally_observed"
        assert vocab.to_legacy_evidence(vocab.INFERRED) == "llm_proposed"
        # the representative round-trips canonically
        for tier in vocab.CANONICAL_TIERS:
            representative = vocab.to_legacy_evidence(tier)
            assert vocab.normalize_authority_tier(representative) == tier


# ============================================================================
# 3. Matching / conflicting / missing / unknown pairs
# ============================================================================

class TestNormalizationDiagnostics:

    def test_17a_matching_canonical_pair_is_valid(self):
        record = vocab.normalize_group_authority({
            "authority_tier": "structurally_observed",
            "evidence": "structurally_observed",
        })
        assert record["diagnostic"] is None
        assert record["conflict"] is False
        assert record["canonical_tier"] == vocab.STRUCTURALLY_OBSERVED

        record = vocab.normalize_group_authority({
            "authority_tier": "externally_listed",
            "evidence": "externally_listed",
        })
        assert record["diagnostic"] is None
        assert record["canonical_tier"] == vocab.EXTERNAL_VERIFIED

    def test_17b_conflicting_pair_is_REPORTED_not_silently_passed(self):
        # structurally_observed evidence cannot back a HUMAN_APPROVED tier
        record = vocab.normalize_group_authority({
            "authority_tier": "human_curated",
            "evidence": "structurally_observed",
        })
        assert record["diagnostic"] == vocab.AUTHORITY_CONFLICT
        assert record["conflict"] is True
        assert record["authorizing"] is False  # fail closed

        # externally_listed evidence cannot back an INFERRED tier
        record = vocab.normalize_group_authority({
            "authority_tier": "llm_proposed",
            "evidence": "externally_listed",
        })
        assert record["diagnostic"] == vocab.AUTHORITY_CONFLICT
        assert record["authorizing"] is False

    def test_17c_conflicts_never_invent_precedence(self):
        """The canonical tier is reported, but the conflict blocks authority."""
        record = vocab.normalize_group_authority({
            "authority_tier": "human_curated",
            "evidence": "structurally_observed",
        })
        # even though authority_tier alone would authorize...
        assert vocab.normalize_authority_tier("human_curated") == vocab.HUMAN_APPROVED
        # ...the conflict record is not authorizing
        assert record["authorizing"] is False

    def test_17d_missing_authority_is_reported(self):
        record = vocab.normalize_group_authority({"evidence": "llm_proposed"})
        assert record["diagnostic"] == vocab.AUTHORITY_MISSING
        assert record["canonical_tier"] == vocab.INFERRED
        assert record["authorizing"] is False

        record = vocab.normalize_group_authority({})
        assert record["diagnostic"] == vocab.AUTHORITY_MISSING
        assert record["canonical_tier"] == vocab.INFERRED

    def test_17e_unknown_authority_is_reported(self):
        record = vocab.normalize_group_authority({"authority_tier": "mystery"})
        assert record["diagnostic"] == vocab.AUTHORITY_UNKNOWN
        assert record["canonical_tier"] == vocab.INFERRED
        assert record["authorizing"] is False

    def test_17f_find_normalization_conflicts(self):
        groups = [
            {"id": "ok", "authority_tier": "llm_proposed",
             "evidence": "llm_proposed"},
            {"id": "conflict", "authority_tier": "human_curated",
             "evidence": "structurally_observed"},
            {"id": "missing", "evidence": "llm_proposed"},
        ]
        records = vocab.find_normalization_conflicts(groups)
        assert [r["group_id"] for r in records] == ["conflict", "missing"]
        assert records[0]["diagnostic"] == vocab.AUTHORITY_CONFLICT
        assert records[1]["diagnostic"] == vocab.AUTHORITY_MISSING


# ============================================================================
# 4. Loader annotation (additive)
# ============================================================================

class TestLoaderAnnotation:

    def test_loader_attaches_normalization_record(self):
        groups, _ = _load([{
            "id": "group_0", "required": ["sliding_window"],
            "patterns": ["sliding_window_variable"],
            "authority_tier": "human_curated",
        }], pid=209)
        record = groups[0]["authority_normalization"]
        assert record["diagnostic"] is None
        assert record["canonical_tier"] == vocab.HUMAN_APPROVED
        # additive: the stored fields are untouched
        assert groups[0]["authority_tier"] == "human_curated"

    def test_loader_conflict_is_recorded_and_fail_closed(self):
        groups, _ = _load([{
            "id": "group_0", "required": ["sliding_window"],
            "patterns": ["sliding_window_variable"],
            "authority_tier": "human_curated",
            "evidence": "structurally_observed",
        }], pid=209)
        assert groups[0]["authority_normalization"]["diagnostic"] == \
            vocab.AUTHORITY_CONFLICT
        # the canonical authority path fails closed for this family
        snap = snapshot_with_strategies("sliding_window")
        eligibility, report = eligibility_for(groups, snap)
        assert report.get("group_0").authoritative is False
        assert report.get("group_0").reason_codes == (ag.REASON_AUTHORITY_CONFLICT,)
        assert eligibility.eligible is False


# ============================================================================
# 5. B6 consumes canonical authority + rejects conflicts
# ============================================================================

class TestB6CanonicalConsumption:

    def test_16e_b6_eligibility_rule_unchanged(self):
        # CONFIRMED + primary + HUMAN_APPROVED -> eligible (B6 regression)
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is True

        groups = [family("g0", ["sliding_window"], authority="externally_listed")]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is True

        # CONFIRMED + primary + STRUCTURALLY_OBSERVED -> blocked
        groups = [family("g0", ["sliding_window"], authority="structurally_observed")]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is False

        # PROVISIONAL / UNRESOLVED / INFERRED / missing -> blocked
        groups = [family("g0", ["sliding_window", "prefix_sum"],
                         authority="human_curated")]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is False

        groups = [family("g0", ["sliding_window"], authority="unknown")]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is False

    def test_b6_rejects_authority_conflicts(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated",
                         evidence="structurally_observed")]
        eligibility, report = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert eligibility.eligible is False
        assert eligibility.reason_codes == (vocab.AUTHORITY_CONFLICT,)

    def test_conflict_does_not_leak_into_unrelated_families(self):
        groups = [
            family("g0", ["sliding_window"], authority="human_curated"),
            family("g1", ["bfs_shortest_path"], authority="human_curated",
                   evidence="structurally_observed"),
        ]
        snap = snapshot_with_strategies("sliding_window")
        eligibility, report = eligibility_for(groups, snap)
        assert report.get("g0").authoritative is True
        assert report.get("g1").reason_codes == (ag.REASON_AUTHORITY_CONFLICT,)
        assert eligibility.eligible is False  # all-requirements rule


# ============================================================================
# 6. ONE_OF + db-254 unchanged
# ============================================================================

class TestOneOfUnchanged:

    def test_16f_explicit_one_of_one_authoritative_is_eligible(self):
        groups = [
            family("g0", ["dp_bottom_up"], authority="human_curated",
                   relation="ONE_OF", alt_group="one_of_dp"),
            family("g1", ["dp_top_down"], authority="human_curated",
                   relation="ONE_OF", alt_group="one_of_dp"),
        ]
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("dp_bottom_up")
        )
        assert eligibility.eligible is True
        assert eligibility.total_requirements == 1

    def test_16g_db254_remains_independent(self):
        groups = [
            family("group_0", ["forward_pointer_advance"], authority="human_curated"),
            family("group_1", ["sequential_accumulation"], authority="human_curated"),
        ]
        assert mark_family_relations(copy.deepcopy(groups)) == []
        eligibility, report = eligibility_for(
            groups, snapshot_with_strategies("sliding_window")
        )
        assert report.alternative_groups == ()
        assert eligibility.total_requirements == 2
        assert eligibility.eligible is False


# ============================================================================
# 7. Flag OFF legacy behavior
# ============================================================================

class TestLegacyUnchanged:

    def test_16h_flag_defaults_off_and_legacy_constants_unchanged(self):
        assert b6.flag_enabled() is False
        from pathforge.services import persistence as prod_persistence
        assert prod_persistence._AUTHORITATIVE_STATES == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_STATES
        assert matching._AUTHORITATIVE_TIERS == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_TIERS

    def test_legacy_matcher_unchanged(self):
        groups = [family("group_0", ["sliding_window"], authority="human_curated")]
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(groups, techniques, strategies, facts)
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["match_outcome"]["outcome"] == direct.outcome
        assert result["match_outcome"]["primary_strategy"] == direct.primary_strategy

    def test_legacy_evidence_gate_meaning_unchanged(self):
        """human_curated is still NOT legacy-authoritative; structurally_observed
        still IS — the deliberate B6 conflict is preserved."""
        legacy_states = {"structurally_observed", "externally_listed"}
        assert "human_curated" not in legacy_states
        assert "structurally_observed" in legacy_states
        assert prod_authoritative_states() == legacy_states


def prod_authoritative_states():
    from pathforge.services import persistence as prod_persistence
    return prod_persistence._AUTHORITATIVE_STATES


# ============================================================================
# 8. Native corpus provenance discipline
# ============================================================================

class TestNativeCorpus:

    def _native_records(self):
        if not _NATIVE_CORPUS.exists():
            pytest.skip("native corpus not regenerated")
        payload = json.loads(_NATIVE_CORPUS.read_text(encoding="utf-8"))
        return payload

    def test_18a_46_native_corpus_retains_authority(self):
        payload = self._native_records()
        assert payload["provenance"] == "NATIVE"
        records = payload["records"]
        assert len(records) == 46
        with_tier = sum(
            1
            for rec in records
            for g in (rec.get("groups") or [])
            if "authority_tier" in g
        )
        assert with_tier > 0, "native corpus must carry native authority_tier"
        # every group carries the normalization record
        for rec in records:
            for g in (rec.get("groups") or []):
                assert "authority_normalization" in g

    def test_18b_enriched_corpuse_is_clearly_marked_non_native(self):
        payload = json.loads(
            (_REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
             / "b6_5_authority_normalization_measurement.json")
            .read_text(encoding="utf-8")
        )
        enriched = payload["corpus_a_46_enriched"]
        assert enriched["provenance"] == "ENRICHED"
        assert enriched["native"] is False
        assert "measurement-time" in enriched["provenance_note"]
        assert payload["corpus_a_46_native"]["provenance"] == "NATIVE"
        assert payload["corpus_a_46_native"]["native"] is True

    def test_18c_301_remains_non_authoritative(self):
        payload = json.loads(
            (_REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
             / "b6_5_authority_normalization_measurement.json")
            .read_text(encoding="utf-8")
        )
        result = payload["corpus_b_301"]
        assert result["eligible_submissions"] == 0
        assert result["canonical_authority_distribution"]["INFERRED"] == \
            result["case_count"]
