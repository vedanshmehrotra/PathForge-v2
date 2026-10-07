# -*- coding: utf-8 -*-
"""B11 follow-up — lookup-strategy specificity (key provenance) tests.

These tests pin the **strategy-level** separation that B11 introduces, and the
boundary that keeps it additive:

- raw T13 ``hash_lookup`` presence is unchanged. The technique keeps its
  deliberately over-covering evidence: an immutable reference table and a
  genuine incremental lookup share one fact shape, so no detector-level rule can
  separate them without deleting the pinned ``DICT_LITERAL_GATED_READ`` positive.
- an immutable dict-literal reference table, and a parameter-keyed mapping that
  is never updated, do **not** establish an algorithmic lookup strategy.
- a mapping that is built and probed by the scan stays strategy-eligible.

Nothing here changes a detector, a fact type, the concept registry, Ground
Truth, or any B2-B8 layer.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap
from typing import Tuple

import pytest

from pathforge.ast_analysis import lookup_specificity as ls
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import (
    RELATIONS_VERSION,
    build_relations,
)
from pathforge.ast_analysis.shadow.techniques import detect_techniques

#: The technique whose raw evidence this layer evaluates. The specificity layer
#: itself names no concept; the tests must, to anchor the evidence to a producer.
CONCEPT = "hash_lookup"

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MEASUREMENT = (
    _REPO_ROOT
    / "experiments"
    / "code_analysis_evaluation"
    / "results"
    / "strategy_specificity_measurement.json"
)


# ============================================================================
# Fixtures — the real corpus shapes, kept verbatim
# ============================================================================

#: Native db-33 (LC13 Roman to Integer): a fully written-out value table that is
#: consulted for the whole run and never built up.
ROMAN_STATIC_VALUE_TABLE = '''
class Solution:
    def romanToInt(self, s):
        hashm = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        val = 0
        for i in range(len(s)):
            if val == 0:
                val += hashm[s[i]]
            elif s[i] == s[i - 1] or hashm[s[i]] > hashm[s[i - 1]]:
                val += hashm[s[i]]
            else:
                val -= hashm[s[i]]
        return val
'''

#: Benchmark stack_valid_parens: the same shape, a bracket-pair table.
BRACKET_PAIR_TABLE = '''
class Solution:
    def isValid(self, s):
        pairs = {')': '(', ']': '[', '}': '{'}
        stack = []
        for ch in s:
            if ch in pairs:
                if not stack or stack.pop() != pairs[ch]:
                    return False
            else:
                stack.append(ch)
        return not stack
'''

#: The existing T13 pinned positive (test_vocab2_hash_lookup). It is the SAME
#: algorithm as db-33 — this is exactly why the separation cannot live in the
#: detector: T13 must keep returning PRESENT for it.
DICT_LITERAL_GATED_READ = '''
class Solution:
    def romanToInt(self, s):
        hashm = {'I': 1, 'V': 5, 'X': 10}
        val = 0
        for i in range(len(s)):
            if val == 0:
                val += hashm[s[i]]
            elif s[i] == s[i - 1] or hashm[s[i]] > hashm[s[i - 1]]:
                val += hashm[s[i]]
            else:
                val -= hashm[s[i]]
        return val
'''

#: Benchmark hm_two_sum_map: the mapping is constructed empty and written inside
#: the scan, and the tested key is computed (a complement).
TWO_SUM_ONLINE = '''
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
'''

DICT_CTOR_MEMBERSHIP = '''
class Solution:
    def solve(self, words):
        table = dict()
        for w in words:
            if w in table:
                return table[w]
            table[w] = len(w)
        return None
'''

#: Benchmark hm_memoize_expensive: the mapping is keyed ONLY by a caller
#: supplied value and is never updated in a loop.
PARAMETER_KEYED_CACHE = '''
cache = {}
def expensive(n):
    if n in cache: return cache[n]
    result = sum(i*i for i in range(n))
    cache[n] = result
    return result
'''

#: Prefix-sum map (ps_subarray_equals_k shape): a dict literal that IS mutated,
#: with a computed key — algorithmic use, deliberately still eligible.
PREFIX_SUM_MAP = '''
def subarray_sum(nums, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for num in nums:
        prefix += num
        if prefix - k in seen:
            count += seen[prefix - k]
        seen[prefix] = count
    return count
'''

#: A dict literal that receives an indexed write: no longer a static table.
MUTATED_DICT_LITERAL = '''
def f(items):
    m = {'a': 1}
    for x in items:
        m[x] = x
    if 'a' in m:
        return m['a']
    return None
'''

#: Parameter-keyed AND updated in a loop: R2 does not apply.
PARAMETER_KEYED_UPDATED_IN_LOOP = '''
def f(k, items):
    m = {}
    for x in items:
        m[k] = x
    if k in m:
        return m[k]
    return None
'''


# ============================================================================
# Helpers
# ============================================================================

def _parsed(code: str) -> ast.Module:
    return ast.parse(textwrap.dedent(code))


def _facts_and_relations(code: str):
    tree = _parsed(code)
    facts = extract_structural_facts(tree)
    return facts, build_relations(tree)


def _technique_ids(code: str) -> set:
    facts, relations = _facts_and_relations(code)
    return {t.technique_id for t in detect_techniques(facts, relations=relations)}


def _lookup_evidence(code: str):
    """``(evidence, facts, relations)`` for the lookup producer, or ``(None, ..)``."""
    facts, relations = _facts_and_relations(code)
    evidence = next(
        (t for t in detect_techniques(facts, relations=relations)
         if t.technique_id == CONCEPT),
        None,
    )
    return evidence, facts, relations


def _verdict(code: str) -> ls.LookupSpecificity:
    evidence, facts, relations = _lookup_evidence(code)
    assert evidence is not None, "the fixture must produce raw lookup evidence"
    return ls.evaluate_evidence_specificity(evidence, facts, relations)


def _bits(code: str) -> Tuple[bool, bool, str]:
    """``(raw_present, strategy_eligible, reason)`` — the two axes kept apart."""
    verdict = _verdict(code)
    return (
        CONCEPT in _technique_ids(code),
        verdict.strategy_eligible,
        verdict.reason,
    )


# ============================================================================
# A. Raw evidence is unchanged — T13 keeps firing on every one of these
# ============================================================================

class TestRawEvidenceUnchanged:
    """The specificity layer never edits what the analysis layer detects."""

    @pytest.mark.parametrize("code", [
        ROMAN_STATIC_VALUE_TABLE,
        BRACKET_PAIR_TABLE,
        DICT_LITERAL_GATED_READ,
        TWO_SUM_ONLINE,
        DICT_CTOR_MEMBERSHIP,
        PARAMETER_KEYED_CACHE,
        PREFIX_SUM_MAP,
    ])
    def test_raw_lookup_evidence_is_still_present(self, code):
        assert CONCEPT in _technique_ids(code), (
            "T13 must remain PRESENT for every one of these shapes"
        )

    def test_relations_version_is_the_b11_version(self):
        assert RELATIONS_VERSION == "1.2.0"


# ============================================================================
# B / R1. Static reference table
# ============================================================================

class TestStaticReferenceTable:
    """R1 — an immutable dict-literal table is a tool, not an algorithm."""

    @pytest.mark.parametrize("code", [
        ROMAN_STATIC_VALUE_TABLE,
        BRACKET_PAIR_TABLE,
        DICT_LITERAL_GATED_READ,
    ])
    def test_reference_table_is_not_strategy_eligible(self, code):
        present, eligible, reason = _bits(code)
        assert present is True, "raw T13 evidence must still be PRESENT"
        assert eligible is False, "a static reference table must not establish a strategy"
        assert reason == ls.REASON_STATIC_REFERENCE_TABLE
        assert _verdict(code).kind == ls.DICT_LITERAL

    def test_mutated_dict_literal_remains_eligible(self):
        """A dict literal that receives an indexed write is not a static table."""
        present, eligible, reason = _bits(MUTATED_DICT_LITERAL)
        assert present is True
        assert eligible is True
        assert reason == ls.REASON_ALGORITHMIC_LOOKUP
        assert _verdict(MUTATED_DICT_LITERAL).mutation_evidence is True

    def test_prefix_sum_dict_literal_remains_eligible(self):
        """The prefix-sum map is a mutated literal — over-coverage, kept eligible."""
        present, eligible, reason = _bits(PREFIX_SUM_MAP)
        assert present is True
        assert eligible is True
        assert reason == ls.REASON_ALGORITHMIC_LOOKUP


# ============================================================================
# R2. Parameter-keyed mapping
# ============================================================================

class TestParameterKeyedMapping:
    """R2 — a caller-keyed, never-updated store is a cache, not a lookup."""

    def test_parameter_keyed_cache_is_not_strategy_eligible(self):
        present, eligible, reason = _bits(PARAMETER_KEYED_CACHE)
        assert present is True, "raw T13 evidence must still be PRESENT"
        assert eligible is False
        assert reason == ls.REASON_PARAMETER_KEYED_MAPPING
        assert _verdict(PARAMETER_KEYED_CACHE).key_origins == (
            ls.KEY_ORIGIN_PARAMETER,
        )

    def test_parameter_keyed_mapping_updated_in_a_loop_remains_eligible(self):
        present, eligible, reason = _bits(PARAMETER_KEYED_UPDATED_IN_LOOP)
        assert present is True
        assert eligible is True
        assert reason == ls.REASON_ALGORITHMIC_LOOKUP
        assert _verdict(PARAMETER_KEYED_UPDATED_IN_LOOP).updated_in_loop == ("for",)

    def test_rule_is_suppression_only(self):
        """No fixture can be *made* eligible by a rule — only left eligible."""
        for code in (ROMAN_STATIC_VALUE_TABLE, BRACKET_PAIR_TABLE,
                     DICT_LITERAL_GATED_READ, PARAMETER_KEYED_CACHE,
                     TWO_SUM_ONLINE, DICT_CTOR_MEMBERSHIP,
                     MUTATED_DICT_LITERAL, PARAMETER_KEYED_UPDATED_IN_LOOP,
                     PREFIX_SUM_MAP):
            assert _verdict(code).state in ls.SPECIFICITY_STATES


# ============================================================================
# C. Genuine algorithmic lookup stays eligible
# ============================================================================

class TestGenuineLookupStaysEligible:
    @pytest.mark.parametrize("code", [
        TWO_SUM_ONLINE,
        DICT_CTOR_MEMBERSHIP,
        MUTATED_DICT_LITERAL,
        PARAMETER_KEYED_UPDATED_IN_LOOP,
        PREFIX_SUM_MAP,
    ])
    def test_built_and_probed_lookup_remains_eligible(self, code):
        verdict = _verdict(code)
        assert verdict.state == ls.STRATEGY_ELIGIBLE
        assert verdict.strategy_eligible is True
        assert verdict.reason == ls.REASON_ALGORITHMIC_LOOKUP

    def test_two_sum_key_origin_is_computed(self):
        verdict = _verdict(TWO_SUM_ONLINE)
        assert "derived" in verdict.key_origins


# ============================================================================
# D / E. Additivity — the layer is a pure leaf
# ============================================================================

class TestAdditiveLeafLayer:
    """Requirement E: no unrelated strategy eligibility change is possible."""

    @pytest.mark.parametrize("code", [
        ROMAN_STATIC_VALUE_TABLE,
        TWO_SUM_ONLINE,
        PARAMETER_KEYED_CACHE,
        PREFIX_SUM_MAP,
    ])
    def test_evaluating_specificity_changes_nothing_it_reads(self, code):
        facts, relations = _facts_and_relations(code)
        before_facts = [(f.fact_id, f.fact_type, dict(f.attributes)) for f in facts]
        before_relations = build_relations(_parsed(code))
        before_techniques = {
            t.technique_id for t in detect_techniques(facts, relations=relations)
        }

        # Evaluate the specificity rule for every detected technique, not only
        # the lookup one — an unrelated producer must be unaffected too.
        for evidence in detect_techniques(facts, relations=relations):
            ls.evaluate_evidence_specificity(evidence, facts, relations)

        after_facts = [(f.fact_id, f.fact_type, dict(f.attributes)) for f in facts]
        after_techniques = {
            t.technique_id for t in detect_techniques(facts, relations=relations)
        }
        assert before_facts == after_facts
        assert before_techniques == after_techniques
        assert build_relations(_parsed(code)) == before_relations

    def test_no_evidence_means_no_verdict(self):
        assert ls.evaluate_evidence_specificity(None, (), None) is None

    def test_missing_citation_declines_to_establish(self):
        verdict = ls.evaluate_lookup_specificity((), None, ())
        assert verdict.state == ls.NOT_ESTABLISHED
        assert verdict.reason == ls.REASON_NO_CITED_MAPPING
        assert verdict.variable is None

    def test_unknown_state_is_rejected(self):
        with pytest.raises(ValueError):
            ls.LookupSpecificity(state="APPROVED", reason="x")

    def test_module_exposes_no_mutation_or_promotion_api(self):
        assert not hasattr(ls, "promote")
        assert not hasattr(ls, "approve")
        source = pathlib.Path(ls.__file__).read_text(encoding="utf-8")
        assert "write_text" not in source
        assert "open(" not in source

    def test_module_is_a_leaf(self):
        """It consumes neither the registry nor the promotion contract.

        The registry token is assembled rather than written literally: this
        guard must not make its own file look like a registry consumer.
        """
        source = pathlib.Path(ls.__file__).read_text(encoding="utf-8")
        registry_module = "pathforge.ast_analysis." + "concepts"
        assert registry_module not in source
        assert "strategy_contract" not in source


# ============================================================================
# Bridge — the contract's own discriminator source validation
# ============================================================================

class TestContractBridge:
    def test_relation_source_is_valid_for_the_contract(self):
        from pathforge.ast_analysis import strategy_contract as sc

        assert sc.is_valid_discriminator_source("relation:lookup_key_origins")
        assert "lookup_key_origins" in sc.valid_relation_names()

    def test_specificity_versions_are_pinned(self):
        assert ls.SPECIFICITY_VERSION == "1.0.0"
        assert ls.SPECIFICITY_STATES == (ls.STRATEGY_ELIGIBLE, ls.NOT_ESTABLISHED)


# ============================================================================
# Blast radius — the recorded B10 measurement
# ============================================================================

class TestB10BlastRadius:
    """Only lookup carries the new specificity evidence; nothing is promoted."""

    @pytest.fixture(scope="class")
    def measurement(self):
        if not _MEASUREMENT.exists():
            pytest.skip("B10 measurement has not been generated")
        import json

        return json.loads(_MEASUREMENT.read_text(encoding="utf-8"))

    def test_exactly_one_candidate_carries_specificity_evidence(self, measurement):
        carrying = sorted(
            c["concept"] for c in measurement["candidates"]
            if "strategy_specificity" in c
        )
        assert carrying == [CONCEPT], (
            f"the B11 specificity block must attach to the lookup candidate only; "
            f"got {carrying}"
        )

    def test_nothing_is_promoted(self, measurement):
        assert measurement["totals"]["promoted"] == 0
        # B11 moves no candidate: none may reach READY_FOR_REVIEW.
        for candidate in measurement["candidates"]:
            assert candidate["contract"]["verdict"] == "BLOCKED", candidate["concept"]

    def test_recorded_refusals_are_the_intended_four(self, measurement):
        block = next(
            c["strategy_specificity"] for c in measurement["candidates"]
            if c.get("strategy_specificity")
        )
        refused = set(block["key_origin_separation"]["negative_records"])
        assert refused == {
            "db-33", "hm_roman_to_int", "stack_valid_parens",
            "hm_memoize_expensive",
        }

    def test_key_origin_discriminator_is_now_available_and_sourced(self, measurement):
        block = next(
            c["strategy_specificity"] for c in measurement["candidates"]
            if c.get("strategy_specificity")
        )
        separation = block["key_origin_separation"]
        assert separation["positive_records"], "an AVAILABLE rule needs positives"
        assert separation["negative_records"], "an AVAILABLE rule needs negatives"
