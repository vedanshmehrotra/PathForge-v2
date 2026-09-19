"""Generalized regression tests for Vocabulary Layer 2, Step 2.

``hash_lookup`` (T13) — mapping identity + a lookup tied to that same mapping.

Structural only: no variable-name evidence, no problem IDs, no ground-truth
edits. The fences these tests pin:

- **Map-identity fence:** only dict-family construction
  (``dict_empty`` / ``dict_literal`` / ``dict`` / ``defaultdict``) qualifies.
  Sets, set literals, lists and ``[0] * n`` produce no ``mapping_construction``
  fact at all, so set/list membership can never satisfy ``hash_lookup``.
- **Counter fence:** ``Counter`` participates in ``mapping_construction`` but is
  excluded from lookup identity (it is the counting identity).
- **Lookup-tie fence:** the lookup must target the *same* mapping variable —
  a membership test or gated read elsewhere in the program does not count.
- **Gating fence:** a dict read used only for arithmetic/aggregation (an
  ungated subscript read) is not lookup evidence.
- **Recursion fence:** a dict used as a recursion memo is not lookup evidence.

These tests are written against structure, not problem IDs.
"""
import ast
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.services.ground_truth_builder import (
    PATTERN_TO_V1_MAPPING,
    VALID_TECHNIQUES,
    VALID_V1_CONCEPTS,
    missing_vocabulary_for_patterns,
)


# ============================================================
# Helpers
# ============================================================

def _techniques(code, with_relations=False):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree) if with_relations else None
    return {t.technique_id: t for t in detect_techniques(facts, relations)}, facts


def _has_hash_lookup(code, with_relations=False):
    techs, _ = _techniques(code, with_relations)
    return "hash_lookup" in techs


def _attrs(code, fact_type):
    tree = ast.parse(code)
    return [f.attributes for f in extract_structural_facts(tree) if f.fact_type == fact_type]


# ============================================================
# Code families
# ============================================================

DICT_MEMBERSHIP_LOOKUP = '''
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

NONOBVIOUS_NAMES = '''
class Solution:
    def solve(self, xs, t):
        q7 = {}
        for i in range(len(xs)):
            w = t - xs[i]
            if w in q7:
                return [q7[w], i]
            q7[xs[i]] = i
        return []
'''

DEFAULTDICT_MEMBERSHIP = '''
class Solution:
    def solve(self, pairs):
        zz = defaultdict(int)
        out = []
        for k, v in pairs:
            if k in zz:
                out.append(zz[k])
            zz[k] += v
        return out
'''

DICT_CONSTRUCTOR_LOOKUP = '''
class Solution:
    def solve(self, words):
        table = dict()
        for w in words:
            if w in table:
                return table[w]
            table[w] = len(w)
        return None
'''

ANNOTATED_DICT_LOOKUP = '''
class Solution:
    def solve(self, key):
        m: dict = {}
        if key in m:
            return m[key]
        return None
'''

SET_MEMBERSHIP = '''
class Solution:
    def hasDuplicate(self, nums):
        seen = set()
        for n in nums:
            if n in seen:
                return True
            seen.add(n)
        return False
'''

SET_LITERAL_MEMBERSHIP = '''
def f(nums):
    seen = {1, 2, 3}
    for n in nums:
        if n in seen:
            return n
    return -1
'''

LIST_MEMBERSHIP = '''
def f(nums):
    lst = []
    for x in nums:
        if x not in lst:
            lst.append(x)
    return lst
'''

INPUT_ARRAY_MEMBERSHIP = '''
def f(nums):
    s = nums[0]
    while s in nums:
        s += 1
    return s
'''

DICT_NO_LOOKUP = '''
class Solution:
    def nextGreaterElement(self, nums1, nums2):
        stack = []
        mp = {}
        for x in nums2:
            while stack and stack[-1] < x:
                mp[stack.pop()] = x
            stack.append(x)
        ans = []
        for x in nums1:
            ans.append(mp.get(x, -1))
        return ans
'''

DICT_UNGATED_READ_ONLY = '''
class Solution:
    def solve(self, nums):
        d = {}
        for n in nums:
            d[n] = n * 2
            v = d[n]
        return d
'''

COUNTER_ONLY = '''
def f(s):
    freq = Counter(s)
    for i in sorted(freq):
        print(i, freq[i])
    return freq
'''

COUNTER_MEMBERSHIP = '''
def f(s):
    n = Counter()
    for c in s:
        n[c] += 1
        if c in n:
            pass
    return n
'''

RECURSIVE_MEMO = '''
class Solution:
    def climbStairs(self, n):
        memo = {}
        def dfs(x):
            if x <= 2:
                return x
            if x in memo:
                return memo[x]
            memo[x] = dfs(x - 1) + dfs(x - 2)
            return memo[x]
        return dfs(n)
'''

RECURSION_NO_MAP = '''
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
'''

MAP_LIKE_NAME_NO_MAP = '''
def f(nums):
    seen = []
    cache = set()
    for n in nums:
        if n in seen or n in cache:
            return n
        seen.append(n)
    return -1
'''

UNRELATED_MEMBERSHIP_PLUS_MAP = '''
def f(nums, target):
    seen = {}
    for n in nums:
        seen[n] = n
    for n in nums:
        if target - n in nums:
            return True
    return False
'''


# ============================================================
# Positive evidence
# ============================================================

class TestHashLookupPositives:
    def test_dict_membership_lookup(self):
        assert _has_hash_lookup(DICT_MEMBERSHIP_LOOKUP)

    def test_dict_literal_gated_read(self):
        assert _has_hash_lookup(DICT_LITERAL_GATED_READ)

    def test_nonobvious_variable_names(self):
        assert _has_hash_lookup(NONOBVIOUS_NAMES)

    def test_defaultdict_membership(self):
        assert _has_hash_lookup(DEFAULTDICT_MEMBERSHIP)

    def test_dict_constructor_lookup(self):
        assert _has_hash_lookup(DICT_CONSTRUCTOR_LOOKUP)

    def test_annotated_assignment_form(self):
        """M1 named forms: AnnAssign construction is the same evidence."""
        assert _has_hash_lookup(ANNOTATED_DICT_LOOKUP)

    def test_consistent_with_and_without_relations(self):
        """Relations must not be required for hash_lookup, and must not change it."""
        for code in (DICT_MEMBERSHIP_LOOKUP, DICT_LITERAL_GATED_READ, ANNOTATED_DICT_LOOKUP):
            with_r, _ = _techniques(code, True)
            without_r, _ = _techniques(code, False)
            assert ("hash_lookup" in with_r) == ("hash_lookup" in without_r)

    def test_evidence_cites_map_construction_and_lookup(self):
        techs, facts = _techniques(DICT_MEMBERSHIP_LOOKUP)
        evidence = techs["hash_lookup"]
        cited = {f.fact_id: f.fact_type for f in facts if f.fact_id in evidence.supporting_fact_ids}
        assert "mapping_construction" in cited.values()
        assert "membership_test" in cited.values()

    def test_gated_read_is_the_cited_trigger(self):
        techs, facts = _techniques(DICT_LITERAL_GATED_READ)
        evidence = techs["hash_lookup"]
        cited = {f.fact_id: f.fact_type for f in facts if f.fact_id in evidence.supporting_fact_ids}
        assert "subscript_read" in cited.values()


# ============================================================
# Negative evidence
# ============================================================

class TestHashLookupNegatives:
    def test_set_membership_is_not_lookup(self):
        assert not _has_hash_lookup(SET_MEMBERSHIP)

    def test_set_literal_membership_is_not_lookup(self):
        assert not _has_hash_lookup(SET_LITERAL_MEMBERSHIP)

    def test_list_membership_is_not_lookup(self):
        assert not _has_hash_lookup(LIST_MEMBERSHIP)

    def test_input_array_membership_is_not_lookup(self):
        assert not _has_hash_lookup(INPUT_ARRAY_MEMBERSHIP)

    def test_mapping_construction_without_lookup(self):
        """db-193 shape: dict written by key and read only via .get(), never gated."""
        assert not _has_hash_lookup(DICT_NO_LOOKUP)

    def test_ungated_read_is_not_lookup(self):
        assert not _has_hash_lookup(DICT_UNGATED_READ_ONLY)

    def test_counter_alone_is_not_lookup(self):
        assert not _has_hash_lookup(COUNTER_ONLY)

    def test_counter_membership_is_not_lookup(self):
        assert not _has_hash_lookup(COUNTER_MEMBERSHIP)

    def test_recursive_memo_is_not_lookup(self):
        """The dict is a memo table; recursive_branching owns this shape."""
        techs, _ = _techniques(RECURSIVE_MEMO)
        assert "hash_lookup" not in techs
        assert "recursive_branching" in techs, "fence must be the recursion concept"

    def test_recursion_without_map_is_not_lookup(self):
        assert not _has_hash_lookup(RECURSION_NO_MAP)

    def test_map_like_names_without_map_structure(self):
        """`seen`/`cache` names over list/set carry no map identity."""
        assert not _has_hash_lookup(MAP_LIKE_NAME_NO_MAP)

    def test_unrelated_membership_is_not_tied_to_map(self):
        """A dict exists, and an unrelated input-array membership exists — no tie."""
        assert not _has_hash_lookup(UNRELATED_MEMBERSHIP_PLUS_MAP)


# ============================================================
# Fact-layer semantics
# ============================================================

class TestHashLookupFactSemantics:
    def test_sets_and_lists_produce_no_mapping_construction(self):
        for code in (SET_MEMBERSHIP, SET_LITERAL_MEMBERSHIP, LIST_MEMBERSHIP):
            assert _attrs(code, "mapping_construction") == []

    def test_dict_family_kinds(self):
        assert {"variable": "seen", "kind": "dict_empty"} in _attrs(DICT_MEMBERSHIP_LOOKUP, "mapping_construction")
        assert {"variable": "hashm", "kind": "dict_literal"} in _attrs(DICT_LITERAL_GATED_READ, "mapping_construction")
        assert any(a["kind"] == "defaultdict" for a in _attrs(DEFAULTDICT_MEMBERSHIP, "mapping_construction"))
        assert any(a["kind"] == "dict" for a in _attrs(DICT_CONSTRUCTOR_LOOKUP, "mapping_construction"))

    def test_counter_has_its_own_kind(self):
        kinds = {a["kind"] for a in _attrs(COUNTER_ONLY, "mapping_construction")}
        assert kinds == {"Counter"}

    def test_subscript_read_is_gated_only(self):
        """Only control-flow-gating reads are recorded as subscript_read."""
        assert _attrs(DICT_UNGATED_READ_ONLY, "subscript_read") == []
        assert any(a["structure"] == "hashm" for a in _attrs(DICT_LITERAL_GATED_READ, "subscript_read"))

    def test_membership_test_records_container_and_negation(self):
        assert {"variable": "seen", "negated": False} in _attrs(DICT_MEMBERSHIP_LOOKUP, "membership_test")
        assert {"variable": "lst", "negated": True} in _attrs(LIST_MEMBERSHIP, "membership_test")


# ============================================================
# Vocabulary registration / GT mapping
# ============================================================

class TestHashLookupVocabulary:
    def test_technique_registered(self):
        assert "hash_lookup" in VALID_TECHNIQUES

    def test_mapping_matches_design(self):
        mapping = PATTERN_TO_V1_MAPPING["hash_map_lookup"]
        assert mapping["required"] == ["hash_lookup"]
        assert mapping["excluded"] == ["recursive_branching"]

    def test_pattern_no_longer_missing_vocabulary(self):
        assert missing_vocabulary_for_patterns(["hash_map_lookup"]) == []

    def test_lookup_and_frequency_are_distinct_concepts(self):
        """hash_map_frequency must stay a *different* concept from hash_lookup."""
        assert PATTERN_TO_V1_MAPPING["hash_map_frequency"]["required"] == ["frequency_counting"]
        assert missing_vocabulary_for_patterns(["hash_map_frequency"]) == []

    def test_every_mapping_concept_is_registered(self):
        """No mapping may reference an ID outside the V1 vocabulary."""
        invalid = {}
        for pattern, mapping in PATTERN_TO_V1_MAPPING.items():
            for key in ("required", "optional", "excluded"):
                for concept in mapping.get(key, []):
                    if concept not in VALID_V1_CONCEPTS:
                        invalid.setdefault(pattern, []).append(concept)
        assert not invalid, f"mapping references unregistered concepts: {invalid}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
