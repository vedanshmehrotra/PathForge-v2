"""B2 — tri-state concept evidence, shadow path only.

These tests verify the *tri-state evidence model* introduced by B2:

* PRESENT / NOT_ESTABLISHED / CONTRADICTED, with **silence never a
  contradiction**;
* the precedence rule CONTRADICTED > PRESENT > NOT_ESTABLISHED;
* that only positive contradiction sources (an explicitly declared structural
  falsifier, or an explicitly declared mutual exclusion whose partner is
  positively established) can produce CONTRADICTED — never a legacy Ground-Truth
  exclusion;
* that the B1 registry is *consumed* as the metadata source rather than
  duplicated;
* that B2 is instrumentation only: existing shadow verdicts are unchanged, and
  the production decision path is untouched.

Expected values here were measured from the pipeline, not assumed.
"""

import ast
import json
import pathlib

import pytest

from pathforge.ast_analysis import concepts as registry
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow.data_structures import (
    StrategyEvidence,
    StructuralFact,
    TechniqueEvidence,
)
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
_CORPUS_B = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "disjoint301_eval_results_BASELINE_step4.json"
)

_ELAPSED_MARKER = "elapsed_ms = (time.perf_counter() - t0) * 1000"


# ============================================================================
# Helpers
# ============================================================================

def _pipeline(code):
    """Facts → techniques → strategies, exactly as the shadow runner does."""
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    technique_evidence = detect_techniques(facts)
    strategy_evidence = evaluate_strategies(technique_evidence, facts)
    return facts, technique_evidence, strategy_evidence


def snapshot(code):
    return ev.build_evidence_snapshot(*_pipeline(code))


def _deterministic(shadow):
    """A shadow result minus the additive keys and the wall-clock timing."""
    return {k: v for k, v in shadow.items()
            if k not in ("evidence_state", "coverage", "strategy_selection",
                         "authority", "elapsed_ms")}


def _strip_b2_lines(source: str) -> str:
    """The runner before the additive B2/B3 batches, by deleting their lines.

    B3 added a `coverage` key on top of B2 without touching any pre-existing
    key, so the same reconstruction removes both additive batches; what remains
    is the pre-B2 behaviour the B2 tests assert is unchanged.
    """
    lines = source.splitlines(keepends=True)
    kept, i = [], 0
    while i < len(lines):
        line = lines[i]
        if "evidence_state import build_evidence_snapshot" in line:
            i += 1
            continue
        if "family_coverage import build_family_coverage" in line:
            i += 1
            continue
        if "primary_strategy import select_submission_primary" in line:
            i += 1
            continue
        if "authority_gating import evaluate_authority" in line:
            i += 1
            continue
        if line.strip().startswith("# Step 6 (B2)"):
            # The B2 step-6 block and the B3/B4 step-7/8 blocks all live between
            # the step-6 marker and the elapsed-time line, so all are removed.
            while i < len(lines) and _ELAPSED_MARKER not in lines[i]:
                i += 1
            continue
        if '"evidence_state": evidence_state,' in line or line.strip().startswith(
            "# B2 additive key"
        ):
            i += 1
            continue
        if '"coverage": coverage,' in line or line.strip().startswith(
            "# B3 additive key"
        ):
            i += 1
            continue
        if '"strategy_selection": strategy_selection,' in line or line.strip().startswith(
            "# B4 additive key"
        ):
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
def pre_b2_shadow():
    """The shadow runner as it behaved before B2, for differential checks."""
    stripped = _strip_b2_lines(_RUNNER_PATH.read_text(encoding="utf-8"))
    assert "evidence_state" not in stripped, "B2 lines left behind in reconstruction"
    namespace = {"__name__": "shadow_runner_pre_b2"}
    exec(compile(stripped, "<shadow_runner_pre_b2>", "exec"), namespace)
    return namespace["run_shadow_analysis"]


# --- real submissions used by the regression tests --------------------------

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

DP_TOPDOWN = """
def fib(n, memo=None):
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
"""

BACKTRACKING = """
def subsets(nums):
    res = []
    path = []
    def backtrack(i):
        if i == len(nums):
            res.append(list(path))
            return
        path.append(nums[i])
        backtrack(i + 1)
        path.pop()
        backtrack(i + 1)
    backtrack(0)
    return res
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
# 1-4. State derivation
# ============================================================================

class TestStateDerivation:

    def test_positive_evidence_is_present(self):
        """Example 1: admissible positive evidence → PRESENT."""
        evidence = snapshot(TWO_SUM).get("hash_lookup")
        assert evidence.state == ev.PRESENT
        assert evidence.source == ev.SOURCE_TECHNIQUE_EVIDENCE
        assert evidence.confidence >= ev.EVIDENCE_FLOOR
        assert evidence.reason_code == ev.REASON_PRESENT
        assert evidence.evidence_refs, "PRESENT must cite its supporting facts"

    def test_observed_structural_fact_is_present(self):
        """A raw observation is deterministic evidence at confidence 1.0."""
        evidence = snapshot(MINIMAL).get("early_termination")
        assert evidence.state == ev.PRESENT
        assert evidence.source == ev.SOURCE_STRUCTURAL_FACT
        assert evidence.confidence == 1.0

    def test_no_evidence_is_not_established(self):
        """Example 2: no hash_lookup evidence → NOT_ESTABLISHED, not CONTRADICTED."""
        evidence = snapshot(MINIMAL).get("hash_lookup")
        assert evidence.state == ev.NOT_ESTABLISHED
        assert evidence.reason_code == ev.REASON_SILENT
        assert evidence.state != ev.CONTRADICTED

    def test_concept_without_a_producer_is_not_established(self):
        """Legacy-only ids have no shadow producer: silence, never absence."""
        evidence = snapshot(TWO_SUM).get("hash_map_lookup")
        assert evidence.state == ev.NOT_ESTABLISHED
        assert evidence.reason_code == ev.REASON_NO_PRODUCER

    def test_legacy_alias_is_projected_not_claimed(self):
        """The V1 image is reported separately as a projection, not as this state."""
        evidence = snapshot(TWO_SUM).get("hash_map_lookup")
        assert evidence.state == ev.NOT_ESTABLISHED
        assert evidence.image_state == ev.PRESENT  # hash_lookup was established

    def test_below_threshold_is_not_established(self):
        """Example 3: sub-floor evidence → NOT_ESTABLISHED."""
        evidence = ev.build_evidence_snapshot(
            [],
            [TechniqueEvidence(
                technique_id="hash_lookup",
                presence_confidence=0.3,
                supporting_fact_ids=["fact_000"],
            )],
            [],
        ).get("hash_lookup")
        assert evidence.state == ev.NOT_ESTABLISHED
        assert evidence.reason_code == ev.REASON_BELOW_FLOOR
        assert evidence.confidence == 0.3

    def test_admissibility_floor_boundary(self):
        """The floor is inclusive and is the existing 0.5 shadow boundary."""
        def state_at(confidence):
            return ev.build_evidence_snapshot(
                [],
                [TechniqueEvidence(
                    technique_id="hash_lookup",
                    presence_confidence=confidence,
                    supporting_fact_ids=["fact_000"],
                )],
                [],
            ).get("hash_lookup").state

        assert ev.EVIDENCE_FLOOR == 0.5
        assert state_at(0.49) == ev.NOT_ESTABLISHED
        assert state_at(0.5) == ev.PRESENT

    def test_every_registered_concept_gets_exactly_one_state(self):
        evidence = snapshot(TWO_SUM)
        ids = [item.concept_id for item in evidence.evidence]
        assert len(ids) == len(registry.all_concepts())
        assert ids == [c.concept_id for c in registry.all_concepts()]
        assert len(set(ids)) == len(ids)
        for item in evidence.evidence:
            assert item.state in ev.EVIDENCE_STATES

    def test_only_three_semantic_states_exist(self):
        assert set(ev.EVIDENCE_STATES) == {
            ev.PRESENT, ev.NOT_ESTABLISHED, ev.CONTRADICTED
        }
        # No ABSENT / NOT_USED / FALSE / MISSING state may be introduced.
        assert not [s for s in dir(ev) if s in {
            "ABSENT", "NOT_USED", "FALSE", "MISSING"
        }]

    def test_snapshot_is_deterministic(self):
        assert snapshot(TWO_POINTERS).to_dict() == snapshot(TWO_POINTERS).to_dict()


# ============================================================================
# 4-7. Contradiction sources
# ============================================================================

class TestContradiction:

    def test_positive_falsifier_contradicts(self):
        """Example 4: an observed structural falsifier → CONTRADICTED.

        binary_search declares 'opposite_direction_updates present'; the sliding
        window shrink loop emits that fact.
        """
        evidence = snapshot(WINDOW_209).get("binary_search")
        assert evidence.state == ev.CONTRADICTED
        assert evidence.contradiction_source == ev.REASON_STRUCTURAL_FALSIFIER
        assert evidence.evidence_refs, "a contradiction must cite its positive evidence"

    def test_midpoint_falsifies_sliding_window(self):
        evidence = snapshot(BINARY_SEARCH).get("sliding_window")
        assert evidence.state == ev.CONTRADICTED
        assert evidence.reason_code == ev.REASON_STRUCTURAL_FALSIFIER

    def test_cache_facts_and_state_restoration_are_the_real_recursion_pair(self):
        top_down = snapshot(DP_TOPDOWN)
        assert top_down.get("dp_top_down").state == ev.PRESENT
        assert top_down.get("dfs_backtracking").state == ev.CONTRADICTED

        backtracking = snapshot(BACKTRACKING)
        assert backtracking.get("dfs_backtracking").state == ev.PRESENT
        assert backtracking.get("dp_top_down").state == ev.CONTRADICTED

    def test_silence_never_produces_contradiction(self):
        """Example 5 / regression: a submission with almost no evidence."""
        evidence = snapshot(MINIMAL)
        assert evidence.by_state(ev.CONTRADICTED) == ()
        assert len(evidence.by_state(ev.NOT_ESTABLISHED)) == len(registry.all_concepts()) - 1

    def test_contradiction_requires_positive_evidence(self):
        """Every CONTRADICTED state must cite a positive contradiction source."""
        for code in (MINIMAL, TWO_SUM, TWO_POINTERS, BINARY_SEARCH, WINDOW_209,
                     BFS_102, DP_TOPDOWN, BACKTRACKING, NESTED_LOOP_ONLY):
            for item in snapshot(code).by_state(ev.CONTRADICTED):
                assert item.contradiction_source in {
                    ev.REASON_STRUCTURAL_FALSIFIER, ev.REASON_MUTUAL_EXCLUSION
                }
                assert item.evidence_refs, f"{item.concept_id} contradicted with no evidence"

    def test_low_confidence_never_contradicts(self):
        evidence = ev.build_evidence_snapshot(
            [],
            [TechniqueEvidence(
                technique_id="binary_search",
                presence_confidence=0.1,
                supporting_fact_ids=["fact_000"],
            )],
            [StrategyEvidence(strategy_id="binary_search", confidence=0.2)],
        ).get("binary_search")
        assert evidence.state == ev.NOT_ESTABLISHED
        assert evidence.state != ev.CONTRADICTED

    def test_legacy_exclusion_alone_never_contradicts(self):
        """The decisive rule: a legacy Ground-Truth exclusion is not a falsifier.

        two_pointers_opposite declares 'declared exclusion (PATTERN_TO_V1_MAPPING):
        binary_search'. Even with binary_search positively established, the
        victim must stay out of CONTRADICTED.
        """
        declared = registry.get_concept("two_pointers_opposite").falsifier or ""
        assert declared.startswith(ev.LEGACY_EXCLUSION_PREFIX), (
            "this test is only meaningful while the declaration is a legacy exclusion"
        )

        evidence = ev.build_evidence_snapshot(
            [],
            [TechniqueEvidence(
                technique_id="bidirectional_index_scan",
                presence_confidence=0.9,
                supporting_fact_ids=["fact_000"],
            )],
            [
                StrategyEvidence(strategy_id="binary_search", confidence=0.85),
                StrategyEvidence(strategy_id="two_pointers_opposite", confidence=0.9),
            ],
        )
        assert evidence.get("binary_search").state == ev.PRESENT
        victim = evidence.get("two_pointers_opposite")
        assert victim.state == ev.PRESENT
        assert victim.state != ev.CONTRADICTED

    def test_mutual_exclusion_requires_positive_establishment(self):
        """Only an established partner may contradict via a declared exclusion."""
        def build(*strategies):
            return ev.build_evidence_snapshot(
                [],
                [TechniqueEvidence(
                    technique_id="recursive_branching",
                    presence_confidence=0.8,
                    supporting_fact_ids=["fact_000"],
                )],
                [StrategyEvidence(strategy_id=s, confidence=0.85) for s in strategies],
            )

        assert build("dfs_backtracking").get("dfs_backtracking").state == ev.PRESENT
        contradicted = build("dfs_backtracking", "dp_top_down").get("dfs_backtracking")
        assert contradicted.state == ev.CONTRADICTED
        assert contradicted.contradiction_source == ev.REASON_MUTUAL_EXCLUSION
        assert contradicted.evidence_refs

    def test_no_legacy_exclusion_is_encoded_as_a_structural_falsifier(self):
        overlap = ev.legacy_exclusion_ids() & ev.structural_falsifier_ids()
        assert overlap == frozenset()


# ============================================================================
# 8. State precedence
# ============================================================================

class TestPrecedence:

    def test_declared_priority_order(self):
        assert ev.STATE_PRIORITY[ev.CONTRADICTED] > ev.STATE_PRIORITY[ev.PRESENT]
        assert ev.STATE_PRIORITY[ev.PRESENT] > ev.STATE_PRIORITY[ev.NOT_ESTABLISHED]

    def test_contradicted_overrides_present(self):
        """A present strategy that is structurally falsified reports CONTRADICTED."""
        evidence = ev.build_evidence_snapshot(
            [
                StructuralFact(fact_id="fact_000", fact_type="state_restoration"),
                StructuralFact(fact_id="fact_001", fact_type="cache_lookup"),
                StructuralFact(fact_id="fact_002", fact_type="cache_write"),
            ],
            [],
            [StrategyEvidence(strategy_id="dp_top_down", confidence=0.9)],
        )
        top_down = evidence.get("dp_top_down")
        assert top_down.state == ev.CONTRADICTED
        assert top_down.confidence == 0.9, "the underlying positive confidence is retained"

    def test_present_overrides_not_established(self):
        """carry_propagation has a fact source and a technique source.

        With the fact observed and the technique evidence below the floor, the
        higher-priority PRESENT wins (this is the B1 dual-source concept).
        """
        concept = registry.get_concept("carry_propagation")
        assert registry.SRC_STRUCTURAL_FACT in concept.sources
        assert registry.SRC_V1_TECHNIQUE in concept.sources

        evidence = ev.build_evidence_snapshot(
            [StructuralFact(fact_id="fact_000", fact_type="carry_propagation")],
            [TechniqueEvidence(
                technique_id="carry_propagation",
                presence_confidence=0.2,
                supporting_fact_ids=["fact_000"],
            )],
            [],
        ).get("carry_propagation")
        assert evidence.state == ev.PRESENT
        assert evidence.source == ev.SOURCE_STRUCTURAL_FACT

    def test_reduction_picks_the_highest_priority_candidate(self):
        candidates = [
            ev.ConceptEvidence("x", ev.NOT_ESTABLISHED, 0.4, ev.SOURCE_NONE, ev.REASON_SILENT),
            ev.ConceptEvidence("x", ev.PRESENT, 0.8, ev.SOURCE_NONE, ev.REASON_PRESENT),
            ev.ConceptEvidence("x", ev.CONTRADICTED, 0.0, ev.SOURCE_NONE,
                               ev.REASON_STRUCTURAL_FALSIFIER),
        ]
        assert ev._reduce(candidates).state == ev.CONTRADICTED
        assert ev._reduce(candidates[:2]).state == ev.PRESENT
        assert ev._reduce(candidates[:1]).state == ev.NOT_ESTABLISHED


# ============================================================================
# 9. Registry integration (consumed, not duplicated)
# ============================================================================

class TestRegistryIntegration:

    def test_evidence_covers_exactly_the_registry(self):
        evidence = snapshot(MINIMAL)
        assert {item.concept_id for item in evidence.evidence} == registry.registry_ids()

    def test_metadata_is_read_from_the_registry(self):
        item = snapshot(TWO_SUM).get("hash_map_lookup")
        payload = item.to_dict()
        concept = registry.get_concept("hash_map_lookup")
        assert payload["v1_image"] == concept.v1_image

    def test_falsifier_ledger_partitions_every_declared_falsifier(self):
        ev.validate_falsifier_ledger()
        declared = ev.concepts_declaring_a_falsifier()
        union = (ev.structural_falsifier_ids() | ev.deferred_falsifier_ids()
                 | ev.legacy_exclusion_ids())
        assert union == declared

    def test_ledger_is_validated_against_the_registry(self, monkeypatch):
        """A falsifier naming an unknown concept must be rejected."""
        monkeypatch.setitem(ev.STRUCTURAL_FALSIFIERS, "not_a_registered_concept",
                            ("midpoint_calculation",))
        with pytest.raises(ValueError):
            ev.validate_falsifier_ledger()

    def test_ledger_rejects_a_legacy_exclusion_as_structural(self, monkeypatch):
        monkeypatch.setitem(ev.STRUCTURAL_FALSIFIERS, "two_pointers_opposite",
                            ("midpoint_calculation",))
        with pytest.raises(ValueError):
            ev.validate_falsifier_ledger()

    def test_structural_falsifiers_are_raw_observations(self):
        for concept_id, fact_ids in ev.STRUCTURAL_FALSIFIERS.items():
            assert ev.MUTUAL_EXCLUSIONS  # sanity: the other source is present
            for fact_id in fact_ids:
                fact = registry.get_concept(fact_id)
                assert fact.concept_class == registry.OBSERVATION
                assert registry.SRC_STRUCTURAL_FACT in fact.sources

    def test_mutual_exclusions_are_read_not_restated(self):
        from pathforge.ast_analysis.shadow.coherence import STRATEGY_COMPATIBILITY
        for strategy_id, partners in ev.MUTUAL_EXCLUSIONS.items():
            assert partners == tuple(
                STRATEGY_COMPATIBILITY[strategy_id]["mutually_exclusive_with"]
            )


# ============================================================================
# 10. PRESENT observations are not strategy conclusions
# ============================================================================

class TestObservationIsNotAConclusion:

    def test_observations_are_not_conclusion_eligible(self):
        for concept_id in ("array_traversal", "brute_force", "sorting"):
            concept = registry.get_concept(concept_id)
            assert concept.concept_class == registry.OBSERVATION
            assert concept.specificity_rank == 0
            assert concept.conclusion_eligible is False

    def test_nested_loops_produce_no_strategy_conclusion(self):
        """brute-force-shaped code establishes observations only."""
        evidence = snapshot(NESTED_LOOP_ONLY)
        strategies = [
            item for item in evidence.by_state(ev.PRESENT)
            if registry.get_concept(item.concept_id).concept_class == registry.STRATEGY
        ]
        assert strategies == []

    @pytest.mark.parametrize("code", [MINIMAL, TWO_SUM, BINARY_SEARCH, WINDOW_209,
                                      BFS_102, DP_TOPDOWN, BACKTRACKING, TWO_POINTERS,
                                      NESTED_LOOP_ONLY])
    def test_a_strategy_is_present_only_with_strategy_evidence(self, code):
        _, _, strategy_evidence = _pipeline(code)
        established = {s.strategy_id for s in strategy_evidence}
        for item in snapshot(code).by_state(ev.PRESENT):
            if registry.get_concept(item.concept_id).concept_class == registry.STRATEGY:
                assert item.concept_id in established

    def test_present_observation_cannot_imply_a_strategy(self):
        """PRESENT observations (and a support technique) yield no strategy."""
        evidence = snapshot(NESTED_LOOP_ONLY)
        present = evidence.by_state(ev.PRESENT)

        observations = [
            item for item in present
            if registry.get_concept(item.concept_id).concept_class == registry.OBSERVATION
        ]
        assert observations, "expected raw observations to be present"

        # candidate_selection is a support technique: present, but not a conclusion.
        assert evidence.get("candidate_selection").state == ev.PRESENT
        assert registry.get_concept("candidate_selection").conclusion_eligible is False

        strategies = [
            item for item in present
            if registry.get_concept(item.concept_id).concept_class == registry.STRATEGY
        ]
        assert strategies == []

    def test_array_traversal_stays_an_observation(self):
        """array_traversal is rank 0 and never a strategy-class conclusion."""
        concept = registry.get_concept("array_traversal")
        assert concept.concept_class == registry.OBSERVATION
        assert concept.specificity_rank == 0
        assert concept.conclusion_eligible is False
        for item in snapshot(TWO_POINTERS).by_state(ev.PRESENT):
            if item.concept_id == "array_traversal":
                assert item.state == ev.PRESENT
                break


# ============================================================================
# 11. Existing shadow verdicts are unchanged
# ============================================================================

#: (label, corpus, key) for the previously observed cases named in the B2 brief.
_NAMED_CASES_A = (
    ("LC3236", 3236),
    ("LC209", 209),
    ("LC102", 102),
    ("LC1_hash_lookup", 1),
    ("LC15_two_pointers", 15),
)
_NAMED_CASES_B = ("ps_subarray_equals_k", "hm_valid_anagram", "tp_container_most_water")


def _corpus_a_cases():
    if not _CORPUS_A.exists():
        return []
    payload = json.loads(_CORPUS_A.read_text(encoding="utf-8"))
    selected = []
    for label, problem_id in _NAMED_CASES_A:
        for rec in payload["records"]:
            if rec["problem_id"] == problem_id:
                selected.append(pytest.param(
                    rec["source_code"],
                    rec.get("groups") or None,
                    id=f"{label}-{rec['external_submission_id']}",
                ))
    return selected


def _corpus_b_cases():
    if not _CORPUS_B.exists():
        return []
    payload = json.loads(_CORPUS_B.read_text(encoding="utf-8"))
    return [
        pytest.param(rec["code"], None, id=f"{rec['name']}")
        for rec in payload["records"] if rec["name"] in _NAMED_CASES_B
    ]


class TestExistingVerdictsUnchanged:

    @pytest.mark.parametrize("code,groups", _corpus_a_cases())
    def test_real_submissions_unchanged(self, code, groups, pre_b2_shadow):
        pre = pre_b2_shadow(code, solution_groups=groups)
        post = run_shadow_analysis(code, solution_groups=groups)
        assert _deterministic(pre) == _deterministic(post)
        assert post["match_outcome"]["outcome"] == pre["match_outcome"]["outcome"]

    @pytest.mark.parametrize("code,groups", _corpus_b_cases())
    def test_disjoint_cases_unchanged(self, code, groups, pre_b2_shadow):
        pre = pre_b2_shadow(code, solution_groups=groups)
        post = run_shadow_analysis(code, solution_groups=groups)
        assert _deterministic(pre) == _deterministic(post)

    def test_named_case_outcomes_are_stable(self, pre_b2_shadow):
        """Goldens for the CONFIRMED cases, so a silent verdict drift is caught."""
        goldens = {
            "LC209": (WINDOW_209, {"sliding_window"}),
            "LC102": (BFS_102, {"bfs_shortest_path"}),
            "LC15": (TWO_POINTERS, {"two_pointers_opposite"}),
        }
        for label, (code, expected_strategies) in goldens.items():
            pre = pre_b2_shadow(code)
            post = run_shadow_analysis(code)
            assert post is not None, label
            assert post["match_outcome"]["outcome"] == pre["match_outcome"]["outcome"]
            assert {s["strategy_id"] for s in post["strategy_evidence"]} == expected_strategies


class TestShadowWiring:

    def test_result_is_the_preexisting_keys_plus_additive_keys(self):
        result = run_shadow_analysis(TWO_SUM)
        assert result is not None
        assert set(result) == {
            "structural_facts", "technique_evidence", "strategy_evidence",
            "match_outcome", "extractor_version", "relations_version",
            "elapsed_ms", "evidence_state", "coverage", "strategy_selection",
            "authority",
        }
        assert result["evidence_state"] is not None
        assert set(result["evidence_state"]) == {
            "floor", "state_priority", "counts", "reason_counts", "evidence"
        }

    def test_evidence_state_is_attached_for_every_valid_submission(self):
        for code in (MINIMAL, TWO_SUM, BINARY_SEARCH, WINDOW_209, NESTED_LOOP_ONLY):
            result = run_shadow_analysis(code)
            assert result is not None
            assert result["evidence_state"] is not None

    def test_graceful_degradation_is_unchanged(self):
        assert run_shadow_analysis("def (invalid syntax") is None

    def test_snapshot_failure_cannot_suppress_the_shadow_result(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("simulated snapshot failure")

        monkeypatch.setattr(
            "pathforge.ast_analysis.shadow.shadow_runner.build_evidence_snapshot", boom
        )
        result = run_shadow_analysis(TWO_SUM)
        assert result is not None, "a snapshot failure must not remove the shadow result"
        assert result["evidence_state"] is None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_evidence_state_does_not_change_any_other_key(self, pre_b2_shadow):
        """With and without B2, every pre-existing key is identical."""
        for code in (TWO_SUM, BINARY_SEARCH, WINDOW_209, TWO_POINTERS, DP_TOPDOWN):
            pre = _deterministic(pre_b2_shadow(code))
            post = run_shadow_analysis(code)
            post.pop("evidence_state")
            post.pop("coverage")
            post.pop("strategy_selection")
            post.pop("authority")
            post.pop("elapsed_ms")
            assert pre == post


# ============================================================================
# 12. Production path untouched
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

    #: Tokens that can only come from the B2 module. The bare word
    #: ``evidence_state`` is deliberately NOT used: `persistence.py` already has
    #: an unrelated pre-existing keyword argument with that name. They are
    #: assembled from parts so this test file does not match its own literals.
    _MODULE_TOKENS = ("shadow." + "evidence_state", "build_evidence" + "_snapshot")
    _IMPORT_TOKEN = "shadow." + "evidence_state import"

    def test_no_production_module_references_the_evidence_model(self):
        offenders = []
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if not relative.startswith(_GUARDED_PREFIXES):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in self._MODULE_TOKENS):
                offenders.append(relative)
        assert offenders == []

    def test_only_the_shadow_path_imports_the_snapshot_builder(self):
        referers = set()
        for path in _python_sources():
            relative = path.relative_to(_REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if self._IMPORT_TOKEN in text:
                referers.add(relative)
        assert referers == {"pathforge/ast_analysis/shadow/shadow_runner.py"}

    def test_legacy_matching_does_not_consume_the_evidence_model(self):
        matching = (_REPO_ROOT / "pathforge" / "ast_analysis" / "shadow"
                    / "matching.py").read_text(encoding="utf-8")
        assert "evidence_state" not in matching
        assert "NOT_ESTABLISHED" not in matching
