"""Generalized regression tests for Vocabulary Layer 2, Step 3.

``frequency_counting`` (T14) — structural evidence of tallying occurrences.

Two branches:
- **A, counting map:** a mapping identity (``Counter``/``defaultdict``/``{}``/
  literal/``dict()``) plus a **counted write** — an augmented Add/Sub indexed
  update. ``Counter(data)`` establishes counting by construction, so one counted
  read (a gated subscript read) or counted write is enough for it.
- **B, pre-sized count array:** ``list_construction`` of kind ``list_mult``
  (``[0] * 26``) plus an augmented Add/Sub indexed write with a **keyed** index.

Fences pinned here: sets, scalar accumulators, plain map building, DP arrays,
recursion memos, unused Counters, positional-index pre-sized arrays.

No variable-name evidence, no problem IDs. Only 1 new fact type
(``list_construction``) plus backward-compatible ``syntax_form``/``operator``
attributes on the existing ``indexed_write`` fact.
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

def _facts(code):
    return extract_structural_facts(ast.parse(code))


def _techs(code, with_relations=True):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree) if with_relations else None
    return {t.technique_id for t in detect_techniques(facts, relations)}


def _has_freq(code):
    return "frequency_counting" in _techs(code)


def _attrs(code, fact_type):
    return [f.attributes for f in _facts(code) if f.fact_type == fact_type]


# ============================================================
# Code families — positives
# ============================================================

COUNTER_WITH_COUNTED_READ = '''
class Solution:
    def solve(self, s):
        freq = Counter(s)
        for i in sorted(freq):
            if freq[i] % 2 != 0:
                return i
        return -1
'''

COUNTER_WITH_COUNTED_WRITE = '''
def f(s):
    n = Counter()
    for c in s:
        n[c] += 1
    return n
'''

DEFAULTDICT_COUNT = '''
def f(pairs):
    d = defaultdict(int)
    for a, b in pairs:
        d[a] += b
    return d
'''

PLAIN_DICT_COUNT = '''
def f(items):
    c = {}
    for x in items:
        c[x] += 1
    return c
'''

DICT_LITERAL_COUNT = '''
def f(words):
    counts = {'a': 0, 'b': 0}
    for w in words:
        counts[w] += 1
    return counts
'''

LIST_MULT_KEYED_COUNT = '''
def f(s):
    cnt = [0] * 26
    for ch in s:
        cnt[ord(ch) - ord('a')] += 1
    return cnt
'''

LIST_MULT_KEYED_SUB = '''
def f(s):
    cnt = [0] * 26
    for ch in s:
        cnt[ord(ch) - 97] -= 1
    return cnt
'''

NONOBVIOUS_NAMES = '''
def f(s):
    z9 = Counter()
    for q in s:
        z9[q] += 1
    return z9
'''

LIST_MULT_CALL_INDEX = '''
def f(items):
    cnt = [0] * 64
    for x in items:
        cnt[len(x)] += 1
    return cnt
'''

ANNOTATED_LIST_MULT = '''
def f(s):
    cnt: list = [0] * 26
    for ch in s:
        cnt[ord(ch) - 97] += 1
    return cnt
'''

# ============================================================
# Code families — negatives
# ============================================================

SET_CONSTRUCTION_AND_MEMBERSHIP = '''
def f(nums):
    seen = set(nums)
    for n in nums:
        if n in seen:
            return n
    return -1
'''

ORDINARY_DICT_ASSIGN = '''
def f(items, key_fn):
    groups = {}
    for item in items:
        k = key_fn(item)
        if k not in groups:
            groups[k] = []
        groups[k].append(item)
    return groups
'''

SCALAR_ACCUMULATION = '''
def f(nums):
    total = 0
    count = 0
    for x in nums:
        total += x
        count += 1
    return total, count
'''

DP_BOTTOM_UP_ARRAY = '''
def f(n):
    dp = [0] * (n + 1)
    dp[0] = 0
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
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

PLAIN_LIST_MULT_NO_UPDATE = '''
def f(n):
    cnt = [0] * n
    for i in range(n):
        cnt[i] = i
    return cnt
'''

INDEXED_ASSIGN_NO_AUG = '''
def f(s):
    cnt = [0] * 26
    for ch in s:
        cnt[ord(ch) - 97] = 1
    return cnt
'''

UNRELATED_MEMBERSHIP_READ = '''
def f(nums, target):
    seen = {}
    for n in nums:
        seen[n] = n
    for n in nums:
        if target - n in nums:
            return True
    return False
'''

UNUSED_COUNTER = '''
def f(s):
    freq = Counter(s)
    return len(s)
'''

LIST_ACCUMULATION = '''
def f(items):
    result = []
    for x in items:
        result = result + [x]
    return result
'''

POSITIONAL_INDEX_PRE_SIZED = '''
def f(n):
    cnt = [0] * n
    for i in range(n):
        cnt[i] += 1
    return cnt
'''


# ============================================================
# Positives
# ============================================================

class TestFrequencyCountingPositives:
    def test_counter_data_with_counted_read(self):
        assert _has_freq(COUNTER_WITH_COUNTED_READ)

    def test_counter_with_counted_write(self):
        assert _has_freq(COUNTER_WITH_COUNTED_WRITE)

    def test_defaultdict_with_counted_write(self):
        assert _has_freq(DEFAULTDICT_COUNT)

    def test_plain_dict_with_counted_write(self):
        assert _has_freq(PLAIN_DICT_COUNT)

    def test_dict_literal_with_counted_write(self):
        assert _has_freq(DICT_LITERAL_COUNT)

    def test_list_mult_with_keyed_count(self):
        assert _has_freq(LIST_MULT_KEYED_COUNT)

    def test_add_and_sub_forms(self):
        assert _has_freq(LIST_MULT_KEYED_COUNT)
        assert _has_freq(LIST_MULT_KEYED_SUB)

    def test_nonobvious_variable_names(self):
        assert _has_freq(NONOBVIOUS_NAMES)

    def test_different_index_expressions(self):
        assert _has_freq(LIST_MULT_KEYED_COUNT)
        assert _has_freq(LIST_MULT_CALL_INDEX)

    def test_annotated_assignment_construction(self):
        """M1 normalized forms: AnnAssign list construction is the same evidence."""
        assert _has_freq(ANNOTATED_LIST_MULT)

    def test_evidence_cites_construction_and_counted_write(self):
        tree = ast.parse(LIST_MULT_KEYED_COUNT)
        facts = extract_structural_facts(tree)
        evidence = {t.technique_id: t for t in detect_techniques(facts)}["frequency_counting"]
        cited = {f.fact_id: f.fact_type for f in facts if f.fact_id in evidence.supporting_fact_ids}
        assert "list_construction" in cited.values()
        assert "indexed_write" in cited.values()

    def test_counter_evidence_cites_read_when_no_write(self):
        tree = ast.parse(COUNTER_WITH_COUNTED_READ)
        facts = extract_structural_facts(tree)
        evidence = {t.technique_id: t for t in detect_techniques(facts)}["frequency_counting"]
        cited = {f.fact_id: f.fact_type for f in facts if f.fact_id in evidence.supporting_fact_ids}
        assert "mapping_construction" in cited.values()
        assert "subscript_read" in cited.values()


# ============================================================
# Negatives
# ============================================================

class TestFrequencyCountingNegatives:
    def test_set_construction_and_membership(self):
        assert not _has_freq(SET_CONSTRUCTION_AND_MEMBERSHIP)

    def test_ordinary_dict_assignment(self):
        assert not _has_freq(ORDINARY_DICT_ASSIGN)

    def test_scalar_accumulation(self):
        assert not _has_freq(SCALAR_ACCUMULATION)

    def test_dp_bottom_up_array(self):
        assert not _has_freq(DP_BOTTOM_UP_ARRAY)

    def test_recursive_memo(self):
        assert not _has_freq(RECURSIVE_MEMO)

    def test_plain_list_mult_without_count_update(self):
        assert not _has_freq(PLAIN_LIST_MULT_NO_UPDATE)

    def test_indexed_assignment_without_augassign(self):
        assert not _has_freq(INDEXED_ASSIGN_NO_AUG)

    def test_unrelated_membership_and_read(self):
        assert not _has_freq(UNRELATED_MEMBERSHIP_READ)

    def test_unused_counter(self):
        assert not _has_freq(UNUSED_COUNTER)

    def test_list_accumulation(self):
        assert not _has_freq(LIST_ACCUMULATION)

    def test_positional_index_pre_sized_array(self):
        """`cnt[i] += 1` on `[0] * n` is positional, not a keyed tally."""
        assert not _has_freq(POSITIONAL_INDEX_PRE_SIZED)


# ============================================================
# Fact-layer semantics
# ============================================================

class TestFrequencyFactSemantics:
    def test_indexed_write_carries_form_and_operator(self):
        aug = [a for a in _attrs(LIST_MULT_KEYED_SUB, "indexed_write") if a.get("syntax_form") == "augmented"]
        assert aug and aug[0]["operator"] == "Sub"
        assert aug[0]["index_type"] == "BinOp"

    def test_plain_assignment_write_form_is_not_augmented(self):
        writes = _attrs(INDEXED_ASSIGN_NO_AUG, "indexed_write")
        assert writes and all(a["syntax_form"] == "assignment" for a in writes)

    def test_list_construction_only_for_list_mult(self):
        assert _attrs(LIST_MULT_KEYED_COUNT, "list_construction") == [
            {"variable": "cnt", "kind": "list_mult"}
        ]
        assert _attrs(LIST_ACCUMULATION, "list_construction") == []
        assert _attrs(SET_CONSTRUCTION_AND_MEMBERSHIP, "list_construction") == []

    def test_lists_still_produce_no_mapping_construction(self):
        """Step 2 invariant preserved: a list is never a map identity."""
        assert _attrs(LIST_MULT_KEYED_COUNT, "mapping_construction") == []
        assert _attrs(PLAIN_LIST_MULT_NO_UPDATE, "mapping_construction") == []


# ============================================================
# Relation contract
# ============================================================

class TestFrequencyRelationContract:
    @pytest.mark.parametrize("code", [
        COUNTER_WITH_COUNTED_READ, COUNTER_WITH_COUNTED_WRITE, DEFAULTDICT_COUNT,
        PLAIN_DICT_COUNT, DICT_LITERAL_COUNT, LIST_MULT_KEYED_COUNT,
        LIST_MULT_KEYED_SUB, SET_CONSTRUCTION_AND_MEMBERSHIP, DP_BOTTOM_UP_ARRAY,
    ])
    def test_relations_neither_create_nor_change_frequency(self, code):
        assert ("frequency_counting" in _techs(code, True)) == ("frequency_counting" in _techs(code, False))

    def test_synthetic_relations_cannot_fabricate_frequency(self):
        """A relations bundle alone must not create frequency_counting."""
        from pathforge.ast_analysis.shadow.relations import SubmissionRelations

        relations = SubmissionRelations()
        relations.updated_in_loop = {"cnt": {"for"}}
        relations.used_as_subscript_index = {"i"}
        relations.collection_ops = {"cnt": {"append"}}
        facts = _facts(ORDINARY_DICT_ASSIGN)
        techs = {t.technique_id for t in detect_techniques(facts, relations)}
        assert "frequency_counting" not in techs


# ============================================================
# Vocabulary registration / mapping
# ============================================================

class TestFrequencyVocabulary:
    def test_technique_registered(self):
        assert "frequency_counting" in VALID_TECHNIQUES

    def test_mapping_matches_design(self):
        mapping = PATTERN_TO_V1_MAPPING["hash_map_frequency"]
        assert mapping["required"] == ["frequency_counting"]
        assert mapping["optional"] == ["hash_lookup"]
        assert mapping["excluded"] == ["recursive_branching"]

    def test_pattern_no_longer_missing_vocabulary(self):
        assert missing_vocabulary_for_patterns(["hash_map_frequency"]) == []

    def test_every_mapping_concept_is_registered(self):
        invalid = {}
        for pattern, mapping in PATTERN_TO_V1_MAPPING.items():
            for key in ("required", "optional", "excluded"):
                for concept in mapping.get(key, []):
                    if concept not in VALID_V1_CONCEPTS:
                        invalid.setdefault(pattern, []).append(concept)
        assert not invalid, f"mapping references unregistered concepts: {invalid}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
