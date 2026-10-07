"""B10 — strategy-specificity contract tests.

Concept-agnostic by construction: the contract's rules are exercised with
synthetic candidates, and the guards assert that no registered concept id
appears in the contract's logic at all. The four real candidates are evaluated
by the B10 precision harness, not here.
"""

import pathlib

import pytest

from pathforge.ast_analysis import strategy_contract as sc

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONTRACT_PATH = _REPO_ROOT / "pathforge" / "ast_analysis" / "strategy_contract.py"
_HARNESS_PATH = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "runners"
    / "strategy_specificity_measure.py"
)

_ANY_FACT = sorted(sc.valid_fact_types())[0]


# ============================================================================
# Builders
# ============================================================================

def _discriminator(availability=sc.AVAILABLE, separation=None) -> sc.Discriminator:
    if separation is None and availability == sc.AVAILABLE:
        separation = sc.Separation(
            positive_records=("rec-pos",), negative_records=("rec-neg",),
        )
    return sc.Discriminator(
        name="synthetic_discriminator",
        source=f"fact:{_ANY_FACT}",
        positive_form="the concept is the mechanism by which the result is produced",
        negative_form="the concept is consulted as a table/tool only",
        availability=availability,
        separates=separation,
        evidence_ref="test fixture",
    )


def _controls(incidental_confirms=False, include=("positive", "negative",
                                                  "adversarial",
                                                  "incidental_usage")):
    def control(name):
        if name not in include:
            return None
        return sc.Control(
            name=name, cases=(f"{name}-case",),
            confirms=incidental_confirms if name == "incidental_usage" else False,
        )
    return sc.NegativeControls(
        positive=control("positive"), negative=control("negative"),
        adversarial=control("adversarial"),
        incidental_usage=control("incidental_usage"),
    )


def _measurements(flag=("rec-pos",)):
    return (
        sc.CorpusMeasurement(corpus="native", shadow_only_ids=tuple(flag),
                             both_ids=("rec-both",), neither_count=1),
        sc.CorpusMeasurement(corpus="benchmark", shadow_only_ids=(),
                             legacy_only_ids=("rec-legacy",), neither_count=9),
    )


def _reviews(flag=("rec-pos",), classification=sc.LEGITIMATE_IMPROVEMENT,
             reviewer="reviewer", date="2026-01-01"):
    return tuple(
        sc.ReviewEntry(record_id=r, classification=classification,
                       reviewer=reviewer, date=date)
        for r in flag
    )


def _candidate(**overrides) -> sc.Candidate:
    """A candidate that satisfies every clause unless overridden."""
    base = dict(
        concept_id="synthetic_concept",
        identity_meaning="single-pass complement lookup that removes a nested search",
        identity_is_mechanism_only=False,
        discriminators=(_discriminator(),),
        precision=sc.PrecisionEvidence(measurements=_measurements(),
                                       reviews=_reviews()),
        negative_controls=_controls(),
        gt=sc.GTCompatibility(required_concepts=("synthetic_concept",),
                              family_role="IDENTIFYING", tier="PEC"),
        primary_strategy=sc.PrimaryStrategySafety(),
        authority=sc.AuthorityImpact(b3_coverage="CONFIRMED", b4_primary=None,
                                     authority_tier="INFERRED",
                                     path_evaluated=True),
        parity=sc.ParityImpact(baseline_ref="results/b7_parity_measurement.json"),
        regression=sc.RegressionEvidence(),
        registered=True,
        concept_class="TECHNIQUE",
        has_shadow_producer=True,
        namesakes=("synthetic_pattern",),
        appears_in_corpus_gt=True,
    )
    base.update(overrides)
    return sc.Candidate(**base)


def _failing(verdict: sc.ContractVerdict) -> set:
    return set(verdict.failing_clauses)


# ============================================================================
# T1 / T15 — the contract carries no concept-specific logic and no ledger
# ============================================================================

def test_t1_contract_names_no_registered_concept():
    source = _CONTRACT_PATH.read_text(encoding="utf-8")
    from pathforge.ast_analysis import concepts as registry

    leaked = sorted(cid for cid in registry.registry_ids() if cid in source)
    assert leaked == [], f"concept ids leaked into the contract: {leaked}"


def test_t15_no_candidate_ledger_is_shipped():
    source = _CONTRACT_PATH.read_text(encoding="utf-8")
    assert "CANDIDATES" not in source
    assert not hasattr(sc, "PROMOTION_LEDGER")
    assert not hasattr(sc, "CANDIDATE_LEDGER")


# ============================================================================
# T2 / T3 — discriminator sources and the availability gate
# ============================================================================

def test_t2_discriminator_source_validation():
    assert _ANY_FACT in sc.valid_fact_types()
    assert sc.valid_relation_names(), "the relations layer must expose relations"
    assert sc.is_valid_discriminator_source(f"fact:{_ANY_FACT}")
    assert sc.is_valid_discriminator_source("relation:updated_in_loop")
    assert sc.is_valid_discriminator_source("derived:some_rule")

    for bad in ("fact:not_a_fact_type", "relation:not_a_relation", "membership_test",
                "fact:", ":x", ""):
        assert not sc.is_valid_discriminator_source(bad), bad
        with pytest.raises(ValueError):
            sc.Discriminator(
                name="bad", source=bad, positive_form="p", negative_form="n",
                availability=sc.NEEDS_EXTRACTION,
            )


def test_t3_availability_gate():
    with pytest.raises(ValueError):
        sc.Discriminator(
            name="no_measurement", source=f"fact:{_ANY_FACT}",
            positive_form="p", negative_form="n", availability=sc.AVAILABLE,
        )

    for availability in (sc.NEEDS_EXTRACTION, sc.NOT_AVAILABLE):
        verdict = sc.evaluate(_candidate(
            discriminators=(_discriminator(availability=availability),),
        ))
        assert sc.C2 in _failing(verdict), availability

    misclassified = sc.Separation(
        positive_records=("rec-pos",), negative_records=("rec-neg",),
        misclassified=("rec-tool",),
    )
    verdict = sc.evaluate(_candidate(
        discriminators=(_discriminator(separation=misclassified),),
    ))
    assert sc.C2 in _failing(verdict)


# ============================================================================
# T4 — the verdict requires every clause
# ============================================================================

def test_t4_all_clauses_pass_is_ready_for_review():
    verdict = sc.evaluate(_candidate())
    assert verdict.verdict == sc.READY_FOR_REVIEW, verdict.to_dict()
    assert verdict.failing_clauses == ()
    assert [c.clause for c in verdict.clauses] == list(sc.CLAUSE_IDS)


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"identity_is_mechanism_only": True}, sc.C1),
        ({"discriminators": (_discriminator(sc.NEEDS_EXTRACTION),)}, sc.C2),
        ({"precision": sc.PrecisionEvidence(measurements=_measurements())}, sc.C3),
        ({"negative_controls": _controls(incidental_confirms=True)}, sc.C4),
        ({"gt": None}, sc.C5),
        ({"primary_strategy": sc.PrimaryStrategySafety(
            consuming_strategies=("some_strategy",))}, sc.C6),
        ({"authority": sc.AuthorityImpact()}, sc.C7),
        ({"parity": sc.ParityImpact()}, sc.C8),
        ({"regression": sc.RegressionEvidence(detector_unchanged=False)}, sc.C9),
    ],
)
def test_t4b_single_failure_blocks_and_names_the_clause(overrides, expected):
    verdict = sc.evaluate(_candidate(**overrides))
    assert verdict.verdict == sc.BLOCKED
    assert expected in _failing(verdict)
    assert expected in [c.clause for c in verdict.clauses if not c.passed]


def test_t4c_precondition_failure_is_not_evaluable():
    for overrides in (
        {"registered": False},
        {"concept_class": "STRATEGY"},
        {"has_shadow_producer": False},
        {"namesakes": ()},
        {"appears_in_corpus_gt": False},
    ):
        verdict = sc.evaluate(_candidate(**overrides))
        assert verdict.verdict == sc.NOT_EVALUABLE, overrides
        assert verdict.failing_clauses == (sc.C0,)


# ============================================================================
# T5 / T6 — the harness evidence carries ids, and every flagged record is reviewed
# ============================================================================

def test_t5_measurement_carries_ids_not_only_counts():
    measurement = sc.CorpusMeasurement(
        corpus="native", shadow_only_ids=("a",), both_ids=("b",),
        legacy_only_ids=("c",), neither_count=2,
    )
    payload = measurement.to_dict()
    assert payload["counts"] == {"both": 1, "shadow_only": 1, "legacy_only": 1,
                                 "neither": 2}
    assert payload["shadow_only_ids"] == ["a"]
    assert payload["legacy_only_ids"] == ["c"]
    with pytest.raises(ValueError):
        sc.CorpusMeasurement(corpus="native", shadow_only_ids=("a", "a"))


def test_t6_every_flagged_record_requires_a_signed_review():
    unreviewed = sc.PrecisionEvidence(measurements=_measurements(), reviews=())
    assert sc.C3 in _failing(sc.evaluate(_candidate(precision=unreviewed)))

    unsigned = sc.PrecisionEvidence(
        measurements=_measurements(), reviews=_reviews(reviewer="", date=""))
    assert sc.C3 in _failing(sc.evaluate(_candidate(precision=unsigned)))

    for classification in sc.BLOCKING_CLASSIFICATIONS:
        blocking = sc.PrecisionEvidence(
            measurements=_measurements(),
            reviews=_reviews(classification=classification),
        )
        assert sc.C3 in _failing(sc.evaluate(_candidate(precision=blocking)))

    representation = sc.PrecisionEvidence(
        measurements=_measurements(),
        reviews=_reviews(classification=sc.REPRESENTATION_DIFFERENCE),
    )
    assert sc.C3 not in _failing(sc.evaluate(_candidate(precision=representation)))

    missing_corpus = sc.PrecisionEvidence(
        measurements=(sc.CorpusMeasurement(corpus="native"),),
        reviews=_reviews(flag=()),
    )
    assert sc.C3 in _failing(sc.evaluate(_candidate(precision=missing_corpus)))


# ============================================================================
# T7 — neither the contract nor the harness can approve
# ============================================================================

def test_t7a_contract_has_no_promotion_api():
    assert "PROMOTE" not in sc.VERDICTS
    assert sc.VERDICTS == (sc.NOT_EVALUABLE, sc.BLOCKED, sc.READY_FOR_REVIEW)
    source = _CONTRACT_PATH.read_text(encoding="utf-8")
    assert "write_text" not in source
    assert not hasattr(sc, "promote")
    assert not hasattr(sc, "approve")


def test_t7b_harness_is_evidence_only():
    if not _HARNESS_PATH.exists():
        pytest.skip("B10 harness not present")
    source = _HARNESS_PATH.read_text(encoding="utf-8")
    # It may read the registry only through the contract module.
    assert "pathforge.ast_analysis import concepts" not in source
    assert "from pathforge.ast_analysis import concepts" not in source
    # It must never execute a product consequence or mutate Ground Truth.
    for forbidden in ("run_persistence", "gating_decision", "ground_truth_builder"
                      " .save", "update_problem_ground_truth", "INSERT ", "UPDATE "):
        assert forbidden not in source, forbidden


# ============================================================================
# T8 / T14 — negative controls
# ============================================================================

def test_t8_incidental_usage_control_required_and_clear():
    assert sc.C4 in _failing(sc.evaluate(_candidate(
        negative_controls=_controls(include=("positive", "negative",
                                             "adversarial")))))
    assert sc.C4 in _failing(sc.evaluate(_candidate(
        negative_controls=_controls(incidental_confirms=True))))
    assert sc.C4 not in _failing(sc.evaluate(_candidate()))


@pytest.mark.parametrize("missing", ["positive", "negative", "adversarial",
                                     "incidental_usage"])
def test_t14_all_four_control_classes_are_required(missing):
    include = tuple(name for name in ("positive", "negative", "adversarial",
                                      "incidental_usage") if name != missing)
    verdict = sc.evaluate(_candidate(
        negative_controls=_controls(include=include)))
    assert sc.C4 in _failing(verdict)


# ============================================================================
# T9 — identification is not a conclusion
# ============================================================================

def test_t9_identifying_without_conclusion_is_a_legal_state():
    from pathforge.ast_analysis import concepts as registry

    such = [
        c.concept_id for c in registry.all_concepts()
        if c.family_role == registry.IDENTIFYING and not c.conclusion_eligible
    ]
    assert such, "the registry must contain at least one identifying non-conclusion"
    for concept_id in such:
        assert sc.identification_without_conclusion(concept_id) is True
    assert sc.identification_without_conclusion("not_a_concept") is False
    # The state is never a contract violation: a candidate carrying it still
    # passes C5 and C6 when nothing else is wrong.
    verdict = sc.evaluate(_candidate(
        gt=sc.GTCompatibility(required_concepts=("x",), family_role="IDENTIFYING",
                              tier="PEC")))
    assert sc.C5 not in _failing(verdict)
    assert sc.C6 not in _failing(verdict)


# ============================================================================
# T10 / T11 / T12 / T13 — inadmissible justifications and ambiguity
# ============================================================================

def test_t10_b3_confirmation_failure_is_not_a_justification():
    verdict = sc.evaluate(_candidate(
        gt=sc.GTCompatibility(required_concepts=("x",), family_role="IDENTIFYING",
                              tier="PEC",
                              justification_basis=sc.BASIS_B3_CONFIRMATION)))
    assert sc.C5 in _failing(verdict)


def test_t11_redundant_or_undeclared_paths_are_blocked():
    for overrides in (
        {"primary_strategy": sc.PrimaryStrategySafety(
            consuming_strategies=("existing_strategy",))},
        {"primary_strategy": sc.PrimaryStrategySafety(
            duplicate_meaning_of=("other_concept",))},
        {"primary_strategy": sc.PrimaryStrategySafety(
            rank3_conflicts=("other_concept",))},
    ):
        assert sc.C6 in _failing(sc.evaluate(_candidate(**overrides)))
    declared = _candidate(primary_strategy=sc.PrimaryStrategySafety(
        rank3_conflicts=("other_concept",), declared_ambiguity=True))
    assert sc.C6 not in _failing(sc.evaluate(declared))


def test_t12_authority_is_not_implied_by_eligibility():
    assert sc.AUTHORITY_CONFERRED_BY_ELIGIBILITY is False
    unsigned = _candidate(authority=sc.AuthorityImpact(
        b3_coverage="CONFIRMED", b4_primary="synthetic_concept",
        b5_authoritative=False, b6_eligible=False,
        authority_tier="INFERRED", path_evaluated=True,
    ))
    verdict = sc.evaluate(unsigned)
    assert sc.C7 not in _failing(verdict)
    assert sc.C7 in _failing(sc.evaluate(_candidate(authority=sc.AuthorityImpact())))
    consequence = _candidate(authority=sc.AuthorityImpact(
        b3_coverage="CONFIRMED", authority_tier="INFERRED", path_evaluated=True,
        justification_basis=sc.BASIS_CONSEQUENCE,
    ))
    assert sc.C7 in _failing(sc.evaluate(consequence))


def test_t13_parity_deltas_are_classified_and_parity_is_not_the_objective():
    assert sc.NEW_DISAGREEMENT in sc.PARITY_DELTA_CLASSIFICATIONS
    assert sc.NEW_DISAGREEMENT != sc.JUSTIFIED_CONFIRMATION

    # A regression is classified as a disagreement, never as improvement.
    regression = sc.ParityDelta(category="P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED",
                                count=1, classification=sc.NEW_DISAGREEMENT,
                                projected=True)
    assert regression.classification == sc.NEW_DISAGREEMENT
    with pytest.raises(ValueError):
        sc.ParityDelta(category="P4", count=1, classification="IMPROVEMENT")

    # Parity cannot justify a promotion.
    verdict = sc.evaluate(_candidate(
        parity=sc.ParityImpact(baseline_ref="ref",
                               justification_basis=sc.BASIS_PARITY)))
    assert sc.C8 in _failing(verdict)

    # Fewer P4 is not a sufficient basis either: the classification decides.
    fewer_p4 = sc.ParityImpact(
        baseline_ref="results/b7_parity_measurement.json",
        deltas=(sc.ParityDelta(category="P4", count=-2,
                               classification=sc.NEW_DISAGREEMENT),),
    )
    assert sc.C8 not in _failing(sc.evaluate(_candidate(parity=fewer_p4)))


# ============================================================================
# T16 — the contract is unreachable from production paths
# ============================================================================

def test_t16_contract_not_reachable_from_production():
    guarded = ("pathforge/api/", "pathforge/services/", "src/",
               "pathforge/ast_engine/")
    offenders = []
    for path in _REPO_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or "node_modules" in path.parts:
            continue
        relative = path.relative_to(_REPO_ROOT).as_posix()
        if not relative.startswith(guarded):
            continue
        if "strategy_contract" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(relative)
    assert offenders == []
