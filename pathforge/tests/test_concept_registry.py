"""B1 — concept registry declaration tests.

These tests verify **declarations only**. They must never assert runtime
behaviour, because B1 changes no runtime behaviour.

Completeness is established by *discovering* every concept from the four source
vocabularies (plus the shadow structural fact types and the documented-only
concepts) and requiring an exact match against the registry. Adding a new
detector, taxonomy pattern, technique, strategy, V2 concept or structural fact
without registering it fails these tests.
"""

import ast
import json
import pathlib
from typing import Set

import pytest

from pathforge.ast_analysis import concepts as registry

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The only files permitted to reference the registry module.
#:
#: B1 was a declaration-only batch, so this set was just the module's own test.
#: B2 authorises exactly ONE runtime consumer — the shadow tri-state evidence
#: layer (`evidence_state.py`), which reads concept class/tier/rank/
#: family_role/falsifier metadata instead of duplicating it. B3 authorises a
#: SECOND shadow consumer — the family-coverage layer (`family_coverage.py`),
#: which reads the same registry metadata to interpret a family's requirements.
#: B4 authorises a THIRD — the primary-strategy selector (`primary_strategy.py`),
#: which reads class/rank/tier/conclusion_eligible to select a primary. Nothing
#: else may consume the registry: any additional referer still fails this test.
#:
#: B10 authorises a FOURTH — the strategy-specificity contract
#: (`strategy_contract.py`), which reads class/tier/role/sources to decide
#: whether a concept's evidence is specific enough for an algorithmic
#: conclusion. It is a metadata/evidence layer: it promotes nothing, and it is
#: the single registry consumer so the B10 harness never imports the registry
#: itself. It is required to live under `pathforge/ast_analysis/` (never under
#: `pathforge/services/`) and to leave the decision-path packages untouched.
#:
#: B11 adds NO runtime consumer. It authorises exactly one additional TEST
#: consumer — the B11 relation-contract tests — which read the registry only to
#: pin its invariants (96 concepts / 25 conclusion-eligible) and to prove the
#: relation layer introduced no fact type. It promotes nothing, and it lives
#: under `pathforge/ast_analysis/shadow/tests/`, so the decision-path guard is
#: unaffected.
_ALLOWED_REGISTRY_REFERERS = {
    "pathforge/tests/test_concept_registry.py",
    "pathforge/tests/test_tri_state_evidence.py",
    "pathforge/tests/test_family_coverage.py",
    "pathforge/tests/test_primary_strategy.py",
    "pathforge/tests/test_b8_authority_reconciliation.py",
    "pathforge/tests/test_b10_strategy_contract.py",
    "pathforge/ast_analysis/shadow/tests/test_b11_lookup_key_origins.py",
    "pathforge/ast_analysis/shadow/evidence_state.py",
    "pathforge/ast_analysis/shadow/family_coverage.py",
    "pathforge/ast_analysis/shadow/primary_strategy.py",
    "pathforge/ast_analysis/strategy_contract.py",
}

#: Concepts declared from documentation only (no implementation, no emitted
#: artifact). They cannot be discovered mechanically, so they are listed here
#: explicitly and cross-checked to be absent from every other vocabulary.
_DOCUMENTED_ONLY_IDS = {"boundary_narrowing", "loop_shape"}


# ============================================================================
# Discovery — one function per source vocabulary
# ============================================================================

def _legacy_detector_ids() -> Set[str]:
    """Every pattern_id registered in the runtime detector registry."""
    import src.ast_detection.detectors  # noqa: F401  (triggers registration)
    from src.ast_detection.registry import get_all_detectors

    return {detector.pattern_id for detector in get_all_detectors()}


def _curated_taxonomy_ids() -> Set[str]:
    """Every pattern in the curated problem taxonomy."""
    from pathforge.ast_engine.patterns import ALL_PATTERNS

    return set(ALL_PATTERNS)


def _literal_ids(module_path: str, keyword: str) -> Set[str]:
    """String literals passed as ``keyword=`` inside a module's source.

    Mechanical and implementation-derived: this reads what the shadow detectors
    actually emit, not what a document claims they emit.
    """
    source = (_REPO_ROOT / module_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == keyword and isinstance(kw.value, ast.Constant):
                    found.add(kw.value.value)
    return found


def _shadow_technique_ids() -> Set[str]:
    """Implemented shadow techniques, plus the production-declared list."""
    from pathforge.services.ground_truth_builder import VALID_TECHNIQUES

    emitted = _literal_ids(
        "pathforge/ast_analysis/shadow/techniques.py", "technique_id"
    )
    return emitted | set(VALID_TECHNIQUES)


def _shadow_strategy_ids() -> Set[str]:
    """Implemented shadow strategies, plus the production-declared list."""
    from pathforge.services.ground_truth_builder import VALID_STRATEGIES

    emitted = _literal_ids(
        "pathforge/ast_analysis/shadow/strategies.py", "strategy_id"
    )
    return emitted | set(VALID_STRATEGIES)


def _v2_concept_ids() -> Set[str]:
    """Every concept the V2 Ground-Truth POC taxonomy declares."""
    from experiments.code_analysis_evaluation.gt_poc_v2.problem_metadata import (
        PEC_STRATEGIES,
        PEC_TECHNIQUES,
        SUPPORT_TECHNIQUES,
    )

    return set(PEC_STRATEGIES) | set(PEC_TECHNIQUES) | set(SUPPORT_TECHNIQUES)


def _structural_fact_ids() -> Set[str]:
    """Every fact_type the shadow fact extractor emits."""
    return _literal_ids(
        "pathforge/ast_analysis/shadow/fact_extractor.py", "fact_type"
    )


def _discovered_ids() -> Set[str]:
    return (
        _legacy_detector_ids()
        | _curated_taxonomy_ids()
        | _shadow_technique_ids()
        | _shadow_strategy_ids()
        | _v2_concept_ids()
        | _structural_fact_ids()
        | set(_DOCUMENTED_ONLY_IDS)
    )


# ============================================================================
# 1. Completeness
# ============================================================================

def test_every_discovered_concept_is_registered():
    """Every concept from every source vocabulary has exactly one entry."""
    missing = sorted(_discovered_ids() - registry.registry_ids())
    assert missing == [], (
        "unclassified concepts (register them in "
        "pathforge/ast_analysis/concepts.py): " + ", ".join(missing)
    )


def test_registry_has_no_unknown_concepts():
    """The registry declares nothing outside the discovered vocabularies."""
    unexpected = sorted(registry.registry_ids() - _discovered_ids())
    assert unexpected == [], (
        "registered concepts that no source vocabulary declares: "
        + ", ".join(unexpected)
    )


def test_registry_matches_discovered_vocabularies_exactly():
    """Completeness in both directions, stated as one assertion."""
    assert registry.registry_ids() == _discovered_ids()


@pytest.mark.parametrize(
    "source,discover",
    [
        (registry.SRC_LEGACY_DETECTOR, _legacy_detector_ids),
        (registry.SRC_CURATED_TAXONOMY, _curated_taxonomy_ids),
        (registry.SRC_V1_TECHNIQUE, _shadow_technique_ids),
        (registry.SRC_V1_STRATEGY, _shadow_strategy_ids),
        (registry.SRC_V2_PEC_STRATEGY, None),
        (registry.SRC_V2_PEC_TECHNIQUE, None),
        (registry.SRC_V2_SUPPORT_TECHNIQUE, None),
        (registry.SRC_STRUCTURAL_FACT, _structural_fact_ids),
    ],
)
def test_per_source_coverage_is_exact(source, discover):
    """Each source vocabulary is covered exactly, not approximately."""
    if discover is None:
        from experiments.code_analysis_evaluation.gt_poc_v2.problem_metadata import (
            PEC_STRATEGIES,
            PEC_TECHNIQUES,
            SUPPORT_TECHNIQUES,
        )

        expected = {
            registry.SRC_V2_PEC_STRATEGY: set(PEC_STRATEGIES),
            registry.SRC_V2_PEC_TECHNIQUE: set(PEC_TECHNIQUES),
            registry.SRC_V2_SUPPORT_TECHNIQUE: set(SUPPORT_TECHNIQUES),
        }[source]
    else:
        expected = discover()

    declared = {c.concept_id for c in registry.concepts_by_source(source)}
    assert declared == expected, (
        f"{source}: missing={sorted(expected - declared)} "
        f"extra={sorted(declared - expected)}"
    )


def test_documented_only_ids_are_absent_from_every_implemented_vocabulary():
    """The two documentation-only concepts are genuinely unimplemented."""
    implemented = (
        _legacy_detector_ids()
        | _curated_taxonomy_ids()
        | _shadow_technique_ids()
        | _shadow_strategy_ids()
        | _v2_concept_ids()
        | _structural_fact_ids()
    )
    assert _DOCUMENTED_ONLY_IDS & implemented == set()
    for concept_id in _DOCUMENTED_ONLY_IDS:
        concept = registry.get_concept(concept_id)
        assert concept.sources == (registry.SRC_DOCUMENTED_ONLY,)


# ============================================================================
# 2. Field validity
# ============================================================================

def test_no_duplicate_registration():
    """Declaration order contains no repeated concept_id."""
    ids = [c.concept_id for c in registry.all_concepts()]
    assert len(ids) == len(set(ids))
    assert len(ids) == len(registry.CONCEPTS)


def test_every_concept_uses_the_registry_key_as_its_id():
    for concept_id, concept in registry.CONCEPTS.items():
        assert concept.concept_id == concept_id


def test_concept_fields_are_valid():
    for concept in registry.all_concepts():
        assert concept.concept_class in registry.CONCEPT_CLASSES, concept.concept_id
        assert concept.tier in registry.CONCEPT_TIERS, concept.concept_id
        assert concept.family_role in registry.FAMILY_ROLES, concept.concept_id
        assert concept.sources, f"{concept.concept_id} declares no source"
        assert isinstance(concept.sources, tuple)
        for source in concept.sources:
            assert source in registry.CONCEPT_SOURCES, concept.concept_id
        assert concept.falsifier is None or (
            isinstance(concept.falsifier, str) and concept.falsifier.strip()
        ), concept.concept_id
        assert isinstance(concept.rationale, str)
        assert concept.v1_image is None or isinstance(concept.v1_image, str)


def test_family_role_values_are_restricted_to_the_approved_set():
    assert registry.FAMILY_ROLES == (
        "IDENTIFYING",
        "COMPONENT",
        "SUPPORTING",
        "ABSENT-NOT-ALLOWED",
    )


def test_observations_never_identify_or_component_a_family():
    """An observation may not be part of a family requirement."""
    for concept in registry.concepts_by_class(registry.OBSERVATION):
        assert concept.family_role in (
            registry.ABSENT_NOT_ALLOWED,
            registry.SUPPORTING,
        ), concept.concept_id


def test_only_strategies_may_conclude():
    for concept in registry.all_concepts():
        expected = concept.concept_class == registry.STRATEGY
        assert concept.conclusion_eligible is expected, concept.concept_id
        if concept.concept_class != registry.STRATEGY:
            assert concept.family_role != registry.IDENTIFYING or (
                # A non-strategy may be IDENTIFYING (it can name a family) but it
                # must never be conclusion-eligible — asserted above.
                concept.conclusion_eligible is False
            )


# ============================================================================
# 3. Rank derivation
# ============================================================================

def test_rank_is_consistent_with_class_and_tier():
    for concept in registry.all_concepts():
        expected = registry.derive_specificity_rank(
            concept.concept_class, concept.tier
        )
        assert concept.specificity_rank == expected, (
            f"{concept.concept_id}: rank {concept.specificity_rank} != {expected}"
        )


def test_conclusion_eligibility_is_consistent_with_class():
    for concept in registry.all_concepts():
        expected = registry.derive_conclusion_eligible(concept.concept_class)
        assert concept.conclusion_eligible is expected, concept.concept_id


def test_rank_scheme_matches_the_approved_derivation():
    assert registry.derive_specificity_rank(registry.OBSERVATION, registry.PEC) == 0
    assert registry.derive_specificity_rank(registry.OBSERVATION, registry.SUPPORT) == 0
    assert registry.derive_specificity_rank(registry.TECHNIQUE, registry.SUPPORT) == 1
    assert registry.derive_specificity_rank(registry.TECHNIQUE, registry.PEC) == 2
    assert registry.derive_specificity_rank(registry.STRATEGY, registry.SUPPORT) == 3
    assert registry.derive_specificity_rank(registry.STRATEGY, registry.PEC) == 3


def test_rank_derivation_rejects_unknown_inputs():
    with pytest.raises(ValueError):
        registry.derive_specificity_rank("NOT_A_CLASS", registry.PEC)
    with pytest.raises(ValueError):
        registry.derive_specificity_rank(registry.TECHNIQUE, "NOT_A_TIER")
    with pytest.raises(ValueError):
        registry.derive_conclusion_eligible("NOT_A_CLASS")


# ============================================================================
# 4-6. array_traversal / brute_force / sorting
# ============================================================================

@pytest.mark.parametrize("concept_id", ["array_traversal", "brute_force", "sorting"])
def test_non_taxonomy_detectors_are_observations(concept_id):
    concept = registry.get_concept(concept_id)
    assert concept.concept_class == registry.OBSERVATION
    assert concept.tier == registry.SUPPORT
    assert concept.specificity_rank == 0
    assert concept.conclusion_eligible is False
    assert concept.family_role == registry.ABSENT_NOT_ALLOWED
    assert concept.sources == (registry.SRC_LEGACY_DETECTOR,)
    assert concept.v1_image is None


@pytest.mark.parametrize("concept_id", ["array_traversal", "brute_force", "sorting"])
def test_non_taxonomy_detectors_are_registered_detectors(concept_id):
    assert concept_id in _legacy_detector_ids()


@pytest.mark.parametrize("concept_id", ["array_traversal", "brute_force", "sorting"])
def test_non_taxonomy_detectors_are_outside_the_curated_taxonomy(concept_id):
    assert concept_id not in _curated_taxonomy_ids()


@pytest.mark.parametrize("concept_id", ["array_traversal", "brute_force", "sorting"])
def test_non_taxonomy_detectors_are_outside_the_v1_and_v2_vocabularies(concept_id):
    assert concept_id not in _shadow_technique_ids()
    assert concept_id not in _shadow_strategy_ids()
    assert concept_id not in _v2_concept_ids()


def test_array_traversal_is_never_conclusion_eligible():
    assert "array_traversal" not in registry.conclusion_eligible_ids()


def test_brute_force_has_no_ground_truth_activation_role():
    concept = registry.get_concept("brute_force")
    assert concept.family_role == registry.ABSENT_NOT_ALLOWED
    assert concept.conclusion_eligible is False


# ============================================================================
# 7. recursive_branching
# ============================================================================

def test_recursive_branching_is_broad_supporting_evidence():
    concept = registry.get_concept("recursive_branching")
    assert concept.concept_class == registry.TECHNIQUE
    assert concept.tier == registry.SUPPORT
    assert concept.specificity_rank == 1
    assert concept.conclusion_eligible is False
    assert concept.family_role == registry.COMPONENT
    assert concept.conclusion_eligible is False


def test_recursive_branching_is_not_a_strategy_and_no_recursive_strategy_was_added():
    assert "recursive_branching" not in {
        c.concept_id for c in registry.concepts_by_class(registry.STRATEGY)
    }
    # No recursive-strategy refinement was implemented in B1: the only
    # technique-class concepts mentioning recursion are the pre-existing broad
    # concept and the pre-existing legacy pattern that maps to it.
    recursive_techniques = {
        c.concept_id
        for c in registry.concepts_by_class(registry.TECHNIQUE)
        if "recursive" in c.concept_id
    }
    assert recursive_techniques == {"recursive_branching", "dfs_recursive"}
    # The raw recursion fact types are observations, not conclusions.
    for fact_id in (
        "self_recursive_call",
        "multiple_recursive_paths",
        "recursive_call_in_conditional",
        "recursive_depth_tracking",
    ):
        assert registry.get_concept(fact_id).concept_class == registry.OBSERVATION


# ============================================================================
# 8. candidate_selection role
# ============================================================================

def test_candidate_selection_identifies_but_does_not_conclude():
    concept = registry.get_concept("candidate_selection")
    assert concept.concept_class == registry.TECHNIQUE
    assert concept.tier == registry.SUPPORT
    assert concept.specificity_rank == 1
    assert concept.family_role == registry.IDENTIFYING
    assert concept.conclusion_eligible is False


def test_greedy_local_mirrors_candidate_selection():
    greedy = registry.get_concept("greedy_local")
    candidate = registry.get_concept("candidate_selection")
    assert greedy.v1_image == candidate.concept_id
    assert greedy.concept_class == candidate.concept_class
    assert greedy.tier == candidate.tier
    assert greedy.family_role == candidate.family_role
    assert greedy.conclusion_eligible is False


# ============================================================================
# Special cases: identifier collision and documented-only concepts
# ============================================================================

def test_carry_propagation_collision_is_registered_once_and_documented():
    concept = registry.get_concept("carry_propagation")
    assert concept.sources == (
        registry.SRC_STRUCTURAL_FACT,
        registry.SRC_V1_TECHNIQUE,
        registry.SRC_V2_PEC_TECHNIQUE,
    )
    assert "carry_propagation" in _structural_fact_ids()
    assert "carry_propagation" in _shadow_technique_ids()
    assert concept.rationale, "the dual role must be documented in the registry"
    # registered exactly once
    assert sum(
        1 for c in registry.all_concepts() if c.concept_id == "carry_propagation"
    ) == 1


def test_boundary_narrowing_is_documented_but_unimplemented():
    concept = registry.get_concept("boundary_narrowing")
    assert concept.concept_class == registry.TECHNIQUE
    assert concept.sources == (registry.SRC_DOCUMENTED_ONLY,)
    from pathforge.services.ground_truth_builder import VALID_TECHNIQUES

    assert "boundary_narrowing" not in VALID_TECHNIQUES


def test_loop_shape_is_documented_but_not_an_emitted_fact():
    concept = registry.get_concept("loop_shape")
    assert concept.concept_class == registry.OBSERVATION
    assert concept.family_role == registry.ABSENT_NOT_ALLOWED
    assert "loop_shape" not in _structural_fact_ids()


def test_shared_legacy_and_v1_strategy_ids_are_single_entries():
    for concept_id in ("two_pointers_opposite", "bfs_shortest_path", "union_find"):
        concept = registry.get_concept(concept_id)
        assert concept.concept_class == registry.STRATEGY
        assert registry.SRC_LEGACY_DETECTOR in concept.sources
        assert registry.SRC_CURATED_TAXONOMY in concept.sources
        assert registry.SRC_V1_STRATEGY in concept.sources


# ============================================================================
# 9. No runtime consumer
# ============================================================================

def _python_sources():
    skip_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache", ".next"}
    for path in _REPO_ROOT.rglob("*.py"):
        if any(part in skip_dirs for part in path.parts):
            continue
        yield path


def test_only_authorised_registry_consumers_exist():
    """Only the B2-authorised shadow evidence layer may consume the registry."""
    tokens = (
        "pathforge.ast_analysis.concepts",
        "from pathforge.ast_analysis import concepts",
    )
    referers = set()
    for path in _python_sources():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(token in text for token in tokens):
            referers.add(path.relative_to(_REPO_ROOT).as_posix())

    assert referers == _ALLOWED_REGISTRY_REFERERS, (
        "unexpected registry consumer(s): "
        + ", ".join(sorted(referers - _ALLOWED_REGISTRY_REFERERS))
    )


def test_registry_is_not_referenced_by_analysis_or_matching_modules():
    """Explicit guard over the decision-path packages."""
    guarded = ("pathforge/api/", "pathforge/services/", "src/", "pathforge/ast_engine/")
    offenders = sorted(
        p for p in _ALLOWED_REGISTRY_REFERERS if p.startswith(guarded)
    )
    assert offenders == []
    for source in _python_sources():
        relative = source.relative_to(_REPO_ROOT).as_posix()
        if not relative.startswith(guarded):
            continue
        text = source.read_text(encoding="utf-8", errors="ignore")
        assert "pathforge.ast_analysis.concepts" not in text, relative


# ============================================================================
# Audit support
# ============================================================================

def test_registry_stats_and_projection_are_consistent():
    stats = registry.registry_stats()
    assert stats["total"] == len(registry.all_concepts())
    assert sum(stats["by_class"].values()) == stats["total"]
    assert sum(stats["by_tier"].values()) == stats["total"]
    assert sum(stats["by_family_role"].values()) == stats["total"]
    assert sum(stats["by_specificity_rank"].values()) == stats["total"]
    assert stats["conclusion_eligible"] == len(registry.conclusion_eligible_ids())

    rows = registry.registry_as_dicts()
    assert len(rows) == stats["total"]
    assert json.loads(json.dumps(rows)) == rows
    assert {row["concept_id"] for row in rows} == set(registry.registry_ids())


def test_registry_lookup_helpers():
    assert registry.has_concept("hash_lookup")
    assert not registry.has_concept("not_a_real_concept")
    with pytest.raises(KeyError):
        registry.get_concept("not_a_real_concept")
    with pytest.raises(ValueError):
        registry.concepts_by_class("NOT_A_CLASS")
    with pytest.raises(ValueError):
        registry.concepts_by_tier("NOT_A_TIER")
    with pytest.raises(ValueError):
        registry.concepts_by_family_role("NOT_A_ROLE")
    with pytest.raises(ValueError):
        registry.concepts_by_source("NOT_A_SOURCE")
