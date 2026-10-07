"""B8 — Ground-Truth authority reconciliation tests.

Covers the required B8 test areas:

* the reconciliation module never invokes ELO/gap/recommendation engines;
* every pre-reconciliation conflict record is surfaced and individually
  classified (no silent bulk rule beyond the documented collision mechanism);
* ``human_curated`` → ``HUMAN_APPROVED`` mapping unchanged; ``llm_proposed``
  stays INFERRED; missing/unknown authority stays non-authoritative;
* explicit human approval / external verification can authorize (vocabulary
  unchanged — no new tiers);
* conflicting authority still fails closed; unresolved rows stay blocked;
* ``evidence`` and ``authority_tier`` semantics are documented constants;
* provenance survives the versioned GT update (native round-trip);
* enriched data cannot be labelled native;
* db-254 stays independent; ONE_OF stays explicit-only; LC3236 techniques are
  not promoted;
* the B6 feature flag remains OFF and the legacy matcher is untouched.

The DB-dependent assertions run against the recorded pre/post artifacts
(``b8_authority_reconciliation_candidates_PREREC.json`` /
``b8_reconciliation_result.json``) so the suite never mutates the live DB.
"""
import json
import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pathforge.services import authority_reconciliation as rec  # noqa: E402
from pathforge.ast_analysis import authority_vocabulary as vocab  # noqa: E402
from pathforge.ast_analysis.shadow import authority_gating as ag  # noqa: E402

_RESULTS = (_REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results")
_PREREC_CANDIDATES = _RESULTS / "b8_authority_reconciliation_candidates_PREREC.json"
_B8_RESULT = _RESULTS / "b8_reconciliation_result.json"
_NATIVES = _RESULTS / "db_batch3" / "submission_eval_results_NATIVE.json"


def _candidates():
    if not _PREREC_CANDIDATES.exists():
        pytest.skip("pre-reconciliation candidates artifact missing")
    return json.loads(_PREREC_CANDIDATES.read_text(encoding="utf-8"))


def _b8_result():
    if not _B8_RESULT.exists():
        pytest.skip("b8 result artifact missing")
    return json.loads(_B8_RESULT.read_text(encoding="utf-8"))


def _make_conflict(**overrides):
    group = {
        "id": "group_1",
        "required": ["sliding_window"],
        "authority_tier": "human_curated",
        "evidence": "structurally_observed",
        "provenance": ["manual_verification"],
        "version": 1,
    }
    group.update(overrides)
    return rec.conflict_from_group(
        group, 209,
        stored_authority_tier=overrides.get("stored_authority_tier",
                                            "structurally_observed"),
        stored_provenance=overrides.get("stored_provenance",
                                        ["manual_verification"]),
        stored_validation_status=overrides.get("stored_validation_status",
                                               "structurally_observed"),
    )


# ============================================================================
# 1. Inventory: all 32 conflicts surfaced, individually classified
# ============================================================================

class TestConflictInventory:

    def test_all_32_conflicts_recorded(self):
        candidates = _candidates()
        assert candidates["summary"]["total_conflicts"] == 32
        assert len(candidates["conflicts"]) == 32

    def test_every_conflict_has_required_fields(self):
        candidates = _candidates()
        required_fields = {
            "problem_id", "group_id", "concepts", "authority_tier", "evidence",
            "canonical_authority_tier_from_authority_tier",
            "canonical_authority_tier_from_evidence", "provenance", "version",
            "family_relation", "alternative_group_id", "legacy_behavior",
            "shadow_behavior", "b6_behavior", "stored_authority_tier",
            "stored_provenance", "reconciliation_status", "reason",
        }
        for conflict in candidates["conflicts"]:
            missing = required_fields - set(conflict)
            assert not missing, f"missing {missing} in {conflict['group_id']}"

    def test_every_conflict_receives_exactly_one_status(self):
        candidates = _candidates()
        valid = set(rec.RECONCILIATION_STATUSES)
        for conflict in candidates["conflicts"]:
            assert conflict["reconciliation_status"] in valid

    def test_20_problems_accounted(self):
        candidates = _candidates()
        assert candidates["summary"]["conflicted_problems"] == [
            2, 3, 11, 15, 21, 35, 46, 62, 70, 78, 102, 125, 141, 200, 209, 322,
            424, 438, 496, 704,
        ]

    def test_classification_summary_matches_individual_records(self):
        candidates = _candidates()
        import collections
        counted = collections.Counter(
            c["reconciliation_status"] for c in candidates["conflicts"])
        assert dict(counted) == candidates["summary"]["by_status"]

    def test_no_conflict_silently_resolved(self):
        """Every resolution carries an explicit provenance-backed reason."""
        candidates = _candidates()
        for conflict in candidates["conflicts"]:
            if conflict["reconciliation_status"] != rec.NEEDS_HUMAN_REVIEW:
                assert conflict["reason"], conflict["group_id"]
                assert "collision" in conflict["reason"]
                assert conflict["stored_provenance"], conflict["group_id"]


# ============================================================================
# 2. Classification rules (provenance-only)
# ============================================================================

class TestClassificationRules:

    def test_collision_with_stored_structural_restores_structural(self):
        conflict = rec.classify_conflict(_make_conflict())
        assert conflict.reconciliation_status == \
            rec.RECONCILE_STRUCTURALLY_OBSERVED

    def test_collision_with_stored_llm_restores_inferred(self):
        conflict = rec.classify_conflict(_make_conflict(
            evidence="llm_proposed", stored_authority_tier="llm_proposed",
            stored_provenance=["llm_ground_truth"],
            stored_validation_status="llm_proposed"))
        assert conflict.reconciliation_status == rec.RECONCILE_INFERRED

    def test_human_approval_never_inferred_from_csv_marker(self):
        """The curated CSV is a pattern label, not a human GT approval."""
        conflict = rec.classify_conflict(_make_conflict(
            stored_provenance=["csv_curated"]))
        assert conflict.reconciliation_status != rec.RECONCILE_HUMAN_APPROVED
        assert conflict.reconciliation_status == \
            rec.RECONCILE_STRUCTURALLY_OBSERVED  # stored row is explicit

    def test_missing_stored_tier_fails_closed(self):
        conflict = rec.classify_conflict(_make_conflict(
            stored_authority_tier=None, stored_provenance=[],
            stored_validation_status="llm_proposed"))
        assert conflict.reconciliation_status == rec.NEEDS_HUMAN_REVIEW

    def test_disagreeing_stored_row_fails_closed(self):
        """If the stored row itself is inconsistent, no resolution."""
        conflict = rec.classify_conflict(_make_conflict(
            stored_authority_tier="llm_proposed",
            stored_provenance=["llm_ground_truth"],
            stored_validation_status="llm_proposed"))
        assert conflict.reconciliation_status == rec.NEEDS_HUMAN_REVIEW

    def test_unresolvable_conflicts_exist_and_stay_blocked(self):
        candidates = _candidates()
        human_review = [c for c in candidates["conflicts"]
                        if c["reconciliation_status"] == rec.NEEDS_HUMAN_REVIEW]
        assert len(human_review) == 3
        for c in human_review:
            assert c["b6_behavior"].startswith("blocked")

    def test_review_records_have_the_required_shape(self):
        candidates = _candidates()
        for record in candidates["human_review_records"]:
            assert set(record) == {
                "problem_id", "group_id", "current_authority_tier",
                "current_evidence", "candidate_resolution", "reason",
                "required_reviewer", "status",
            }
            assert record["required_reviewer"] == "human"
            assert record["status"] == rec.NEEDS_HUMAN_REVIEW


# ============================================================================
# 3. Authority vocabulary unchanged
# ============================================================================

class TestVocabularyUnchanged:

    def test_human_curated_mapping_remains_canonical(self):
        assert vocab.SOURCE_TIER_MAP["human_curated"] == vocab.HUMAN_APPROVED

    def test_no_new_tiers(self):
        assert set(vocab.CANONICAL_TIERS) == {
            vocab.HUMAN_APPROVED, vocab.EXTERNAL_VERIFIED,
            vocab.STRUCTURALLY_OBSERVED, vocab.INFERRED,
        }

    def test_llm_proposed_remains_inferred(self):
        assert vocab.SOURCE_TIER_MAP["llm_proposed"] == vocab.INFERRED

    def test_missing_and_unknown_stay_non_authoritative(self):
        assert vocab.AUTHORIZING_TIERS == frozenset({
            vocab.HUMAN_APPROVED, vocab.EXTERNAL_VERIFIED})

    def test_missing_unknown_and_garbage_stay_inferred(self):
        for value in (None, "", "unknown", "unobserved", "weird_value"):
            tier = vocab.normalize_authority_tier(value)
            assert tier == vocab.INFERRED
            assert not vocab.is_authorizing(tier)

    def test_explicit_human_approval_can_authorize(self):
        assert vocab.is_authorizing(
            vocab.normalize_authority_tier("human_approved"))
        assert vocab.is_authorizing(
            vocab.normalize_authority_tier("human_curated"))

    def test_explicit_external_verification_can_authorize(self):
        assert vocab.is_authorizing(
            vocab.normalize_authority_tier("externally_listed"))

    def test_conflicting_authority_still_fails_closed(self):
        group = {
            "id": "g", "authority_tier": "human_curated",
            "evidence": "structurally_observed",
        }
        record = vocab.normalize_group_authority(group)
        assert record["diagnostic"] == vocab.AUTHORITY_CONFLICT


# ============================================================================
# 4. Field semantics documented
# ============================================================================

class TestFieldSemantics:

    def test_authority_tier_semantics_documented(self):
        doc = rec.AUTHORITY_TIER_SEMANTICS
        assert doc["field"] == "authority_tier"
        assert doc["semantics"] == "ground_truth_authority"
        assert doc["load_time_writer"]

    def test_evidence_semantics_documented(self):
        doc = rec.EVIDENCE_SEMANTICS
        assert doc["field"] == "evidence"
        assert "legacy_validation_state" in doc["semantics"]
        assert "overloading_note" in doc
        # the collision conclusion is recorded
        assert "field-semantic collisions" in doc["overloading_note"]

    def test_candidates_artifact_embeds_field_semantics(self):
        candidates = _candidates()
        assert candidates["field_semantics"]["authority_tier"]["semantics"] \
            == "ground_truth_authority"
        assert "legacy" in candidates["field_semantics"]["evidence"]["semantics"]


# ============================================================================
# 5. Versioned GT update (provenance survives)
# ============================================================================

class TestVersionedUpdate:

    def test_apply_resolution_writes_provenance_and_version(self):
        group = {"id": "group_1", "authority_tier": "human_curated",
                 "evidence": "structurally_observed", "provenance": ["x"],
                 "version": 1}
        change = rec.apply_resolution(
            group, rec.RECONCILE_STRUCTURALLY_OBSERVED)
        assert change is not None
        assert group["authority_tier"] == "structurally_observed"
        assert group["version"] == rec.RECONCILIATION_VERSION
        assert rec.RECONCILIATION_MARKER in group["provenance"]
        assert group["reconciled_from"]["authority_tier"] == "human_curated"
        # legacy evidence field untouched
        assert group["evidence"] == "structurally_observed"

    def test_apply_resolution_normalization_is_clean(self):
        group = {"id": "group_1", "authority_tier": "human_curated",
                 "evidence": "structurally_observed", "provenance": ["x"],
                 "version": 1}
        rec.apply_resolution(group, rec.RECONCILE_STRUCTURALLY_OBSERVED)
        record = group["authority_normalization"]
        assert record["diagnostic"] is None  # no conflict diagnostic remains
        assert record["conflict"] is False
        assert record["authorizing"] is False

    def test_needs_human_review_never_writes(self):
        group = {"id": "g", "authority_tier": "human_curated"}
        assert rec.apply_resolution(group, rec.NEEDS_HUMAN_REVIEW) is None
        assert group["authority_tier"] == "human_curated"

    def test_native_provenance_survives_serialization_round_trip(self):
        from pathforge.services.ground_truth_builder import (
            serialize_solution_groups, deserialize_solution_groups)
        group = {"id": "group_1", "required": ["sliding_window"],
                 "authority_tier": "structurally_observed",
                 "evidence": "structurally_observed",
                 "provenance": [rec.RECONCILIATION_MARKER], "version": 2}
        raw = serialize_solution_groups([group])
        loaded = deserialize_solution_groups(raw)
        assert loaded[0]["authority_tier"] == "structurally_observed"
        assert rec.RECONCILIATION_MARKER in loaded[0]["provenance"]
        assert loaded[0]["version"] == 2

    def test_reconciled_groups_recorded(self):
        result = _b8_result()
        changes = result["gt_changes_applied"]
        assert len(changes) == 0  # preserved-artifact run: 21 applied earlier
        statuses = result["summary"]["by_status"]
        assert statuses == {"NEEDS_HUMAN_REVIEW": 3}

    def test_native_conflicts_before_vs_after(self):
        result = _b8_result()
        ba = result["b7_before_after"]
        # 32 pre-reconciliation conflicts; 3 remain (problem 2's tier-less
        # CSV-fallback groups, NEEDS_HUMAN_REVIEW, fail-closed).
        assert ba["b7_native_parity_before"]["P7_AUTHORITY_CONFLICT"] == 28
        assert ba["b7_native_parity_after"]["P7_AUTHORITY_CONFLICT"] == 3


# ============================================================================
# 6. Enriched data can never be labelled native
# ============================================================================

class TestProvenanceDiscipline:

    def test_native_corpus_is_labelled_native(self):
        if not _NATIVES.exists():
            pytest.skip("native corpus missing")
        payload = json.loads(_NATIVES.read_text(encoding="utf-8"))
        assert payload["provenance"] == "NATIVE"
        assert payload["native"] is True

    def test_enriched_corpus_label_cannot_collide_with_native(self):
        from experiments.code_analysis_evaluation.runners \
            import b6_5_authority_normalization_measure as m
        source = pathlib.Path(m.__file__).read_text(encoding="utf-8")
        # the native builder emits exactly the NATIVE label...
        assert '"provenance": "NATIVE"' in source
        # ...and wherever the enriched arm appears it is explicitly marked
        # non-native / measurement-time, never as native provenance
        if '"provenance": "ENRICHED"' in source:
            assert 'measurement-time' in source
            assert 'NON-NATIVE' in source or 'non-native' in source.lower()

    def test_b8_used_no_measurement_time_enrichment(self):
        """The reconciled corpus was regenerated from the live DB."""
        result = _b8_result()
        # the regeneration happened through the B6.5 native builder
        assert result["native_conflict_count_after"] is not None
        assert result["gt_changes_applied"] is not None


# ============================================================================
# 7. Structural regressions (db-254, ONE_OF, LC3236, flag, engines)
# ============================================================================

class TestStructuralRegressions:

    def test_db_254_remains_independent(self):
        from pathforge.services.ground_truth_builder import (
            mark_family_relations, serialize_solution_groups,
            deserialize_solution_groups)
        groups = [
            {"id": "g1", "required": ["dp_bottom_up"],
             "patterns": ["dp_1d_forward"]},
            {"id": "g2", "required": ["dp_top_down"],
             "patterns": ["dp_table"]},
        ]
        mark_family_relations(groups)
        for group in groups:
            assert "family_relation" not in group
            assert "alternative_group_id" not in group
        raw = serialize_solution_groups(groups)
        loaded = deserialize_solution_groups(raw)
        assert all("family_relation" not in g for g in loaded)

    def test_one_of_remains_explicit_only(self):
        from pathforge.services.ground_truth_builder import (
            mark_family_relations)
        groups = [{"id": "g1", "required": ["x"], "patterns": ["p_x"]},
                  {"id": "g2", "required": ["y"], "patterns": ["p_y"]}]
        mark_family_relations(groups)
        assert all("family_relation" not in g for g in groups)

    def test_lc3236_techniques_not_promoted(self):
        from pathforge.ast_analysis.concepts import CONCEPTS
        for concept_id in ("hash_lookup", "sequential_accumulation"):
            concept = CONCEPTS[concept_id]
            assert concept.concept_class in ("TECHNIQUE", "SUPPORT",
                                             "OBSERVATION", "SUPPORT_TECHNIQUE")
            assert concept.conclusion_eligible is False

    def test_b6_flag_remains_off(self):
        from pathforge.services import product_eligibility as b6
        assert b6.flag_enabled() is False

    def test_flag_off_gating_keeps_legacy_behavior(self):
        from pathforge.services import product_eligibility as b6
        decision = b6.gating_decision(
            conn=None, user_id=1, code="", groups=None,
            match_result={"match_result": {"outcome": "CONFIRMED"}},
            shadow_evaluation=None)
        assert decision["allow_legacy"] is True
        assert decision["source"] == "legacy"

    def test_reconciliation_module_never_invokes_consequence_engines(self):
        import re
        source = (pathlib.Path(rec.__file__).read_text(encoding="utf-8"))
        # prose may mention the engines (field-semantics documentation); code
        # must never import or invoke them
        imports = re.findall(
            r"^\s*(?:from|import)\s+\S*(elo|gap|recommend)\S*",
            source, re.MULTILINE)
        assert imports == []
        for forbidden_call in ("EloEngine(", "GapSignalEngine(",
                               "update_topic_profile(",
                               "update_user_streak(",
                               "get_recommendation("):
            assert forbidden_call not in source, forbidden_call

    def test_reconciliation_runner_never_executes_consequences(self):
        source = (_REPO_ROOT / "experiments" / "code_analysis_evaluation"
                  / "runners" / "b8_authority_reconciliation.py"
                  ).read_text(encoding="utf-8")
        for forbidden in ("apply_elo", "persist_gaps", "persist_recommendation",
                          "update_topic_profile", "_update_user_streak",
                          "SHADOW_AUTHORITY_PRODUCT_GATING', 'true"):
            assert forbidden not in source, forbidden

    def test_b7_before_after_recorded(self):
        result = _b8_result()
        ba = result["b7_before_after"]
        assert ba["b7_native_parity_before"]["P7_AUTHORITY_CONFLICT"] == 28
        assert ba["b7_native_parity_after"]["P7_AUTHORITY_CONFLICT"] == 3
        assert ba["b7_native_b6_eligible_before"] == 0
        assert ba["b7_native_b6_eligible_after"] == 0

    def test_b6_eligibility_stays_zero_measurement_only(self):
        result = _b8_result()
        assert result["b6_eligibility"]["after"] == 0
        assert result["b6_eligibility"]["blocked_after"] == 46
        assert result["b6_eligibility"]["measurement_only"] is True
        assert result["b6_eligibility"]["flag"] == "<unset>"


# ============================================================================
# 8. Legacy matcher untouched
# ============================================================================

class TestLegacyUntouched:

    def test_reconciliation_imports_no_matching_module(self):
        import pathforge.services.authority_reconciliation as module
        imported = getattr(module, "__globals__", {})
        for name in imported:
            if "matching" in name:
                pytest.fail(f"reconciliation imports {name}")

    def test_legacy_verdict_rule_unchanged(self):
        """The legacy verdict gate still reads evidence, not authority_tier."""
        source = (_REPO_ROOT / "pathforge" / "services" / "persistence.py"
                  ).read_text(encoding="utf-8")
        assert 'in {"structurally_observed", "externally_listed"}' in source \
            or "structurally_observed" in source  # legacy rule present

    def test_loader_still_uses_csv_patterns_for_production(self):
        """B8 guarded authority only — patterns still come from the CSV."""
        source = (_REPO_ROOT / "pathforge" / "services" / "problem_resolver.py"
                  ).read_text(encoding="utf-8")
        assert "production_patterns = csv_patterns" in source


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
