"""Generalized regression tests for Vocabulary Layer 2, Step 4.

Sorting-form ``candidate_selection`` (T12 second form) — a sorting operation
plus a **bounded read of the same sequence** (``nums.sort()`` then ``nums[0]`` /
``nums[-1]`` / ``nums[len(nums) - 1]``), i.e. selecting an endpoint/order
candidate from an ordered sequence.

Structural only: no variable-name evidence, no problem IDs, no literals relied
on for the *relationship* (the pairing is by sorted-structure identity, and the
index is a bounded form rather than a specific literal).

Two new name-free facts carry the evidence:

- ``sorting_operation`` — ``x.sort(...)`` (in place; ``structure = x``) or
  ``y = sorted(x, ...)`` (functional; ``structure = y``, the target that holds
  the sorted sequence). Records ``method`` and ``reverse`` but requires neither.
- ``extremum_access`` — a **load** subscript of a sequence at a bounded index
  (``constant`` or ``length_offset``). A variable index (``arr[i]``) is
  deliberately not recorded, which is what separates endpoint selection from
  two-pointer / binary-search index movement.

The loop form of T12 is unchanged and its regression battery is pinned at the
bottom of this file.
"""
import ast
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import (
    _candidate_selection_sort_form,
    detect_techniques,
)
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


def _has_candidate(code, with_relations=True):
    return "candidate_selection" in _techs(code, with_relations)


def _attrs(code, fact_type):
    return [f.attributes for f in _facts(code) if f.fact_type == fact_type]


# ============================================================
# Code families — positives
# ============================================================

SORT_THEN_SMALLEST = '''
def f(a):
    a.sort()
    return a[0]
'''

SORT_THEN_LARGEST = '''
def f(a):
    a.sort()
    return a[-1]
'''

SORTED_THEN_EXTREMUM = '''
def f(x):
    s = sorted(x)
    return s[0]
'''

SORTED_REVERSE_THEN_EXTREMUM = '''
def f(x):
    s = sorted(x, reverse=True)
    return s[-1]
'''

NONOBVIOUS_NAMES = '''
def f(blob):
    blob.sort()
    return blob[len(blob) - 1]
'''

# Real corpus shape (no problem id encoded — the structure is the point):
# functional sorted() result then a length-relative endpoint read.
SORTED_PLUS_LENGTH_OFFSET = '''
def f(vals):
    q = sorted(vals)
    return q[len(q) - 1] - q[0]
'''

# Sort inside a conditional (normalized statement handling) then endpoint read.
SORT_THEN_SELECT_UNDER_GUARD = '''
def f(arr):
    if arr:
        arr.sort()
        return arr[-1]
    return 0
'''

# Reverse-argument equivalence: the argument is recorded but must not be needed.
SORT_REVERSE_ARGUMENT_EQUIVALENT = '''
def f(arr):
    arr.sort(reverse=True)
    return arr[0]
'''


# ============================================================
# Code families — negatives
# ============================================================

SORT_ONLY = '''
def f(a):
    a.sort()
'''

SORT_AS_OUTPUT = '''
def f(a):
    return sorted(a)
'''

SORT_THEN_TRAVERSAL = '''
def f(a):
    a.sort()
    total = 0
    for x in a:
        total += x
    return total
'''

SORT_THEN_UNRELATED_SUBSCRIPT = '''
def f(a, b):
    a.sort()
    return b[0] + len(a)
'''

TWO_POINTER_AFTER_SORT = '''
def f(a):
    a.sort()
    left, right = 0, len(a) - 1
    while left < right:
        if a[left] + a[right] == 0:
            return True
        left += 1
        right -= 1
    return False
'''

BINARY_SEARCH_AFTER_SORT = '''
def f(a, t):
    a.sort()
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == t:
            return mid
        if a[mid] < t:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''

HEAP_TOP_K = '''
import heapq

def f(a, k):
    return heapq.nlargest(k, a)
'''

SLIDING_WINDOW = '''
def f(a, k):
    window = 0
    lo = 0
    best = 0
    for hi in range(len(a)):
        window += a[hi]
        if hi - lo + 1 > k:
            window -= a[lo]
            lo += 1
        if window > best:
            best = window
    return best
'''

MONOTONIC_STACK = '''
def f(a):
    stack = []
    for i, x in enumerate(a):
        while stack and a[stack[-1]] < x:
            stack.pop()
        stack.append(i)
    return stack
'''

MAPPING_BUILD_ONLY = '''
def f(items):
    seen = {}
    for x in items:
        seen[x] = True
    return seen
'''

# ============================================================
# POSITIVE: sort form fires
# ============================================================

@pytest.mark.parametrize("code", [
    SORT_THEN_SMALLEST,
    SORT_THEN_LARGEST,
    SORTED_THEN_EXTREMUM,
    SORTED_REVERSE_THEN_EXTREMUM,
    NONOBVIOUS_NAMES,
    SORTED_PLUS_LENGTH_OFFSET,
    SORT_THEN_SELECT_UNDER_GUARD,
    SORT_REVERSE_ARGUMENT_EQUIVALENT,
])
def test_sort_form_positive(code):
    assert _has_candidate(code)


def test_sort_form_fires_without_relations():
    """Fact-fallback path: no relation bundle is required for the sort form."""
    assert _has_candidate(SORT_THEN_SMALLEST, with_relations=False)
    assert _has_candidate(SORTED_PLUS_LENGTH_OFFSET, with_relations=False)


def test_sort_form_supporting_facts_are_the_sort_and_the_read():
    tree = ast.parse(SORTED_PLUS_LENGTH_OFFSET)
    facts = extract_structural_facts(tree)
    by_id = {f.fact_id: f for f in facts}
    ev = [t for t in detect_techniques(facts, build_relations(tree))
          if t.technique_id == "candidate_selection"]
    assert len(ev) == 1
    types = {by_id[i].fact_type for i in ev[0].supporting_fact_ids}
    # The sort + bounded read are the load-bearing evidence; any
    # ``early_termination`` fact is corroboration only.
    assert {"sorting_operation", "extremum_access"} <= types
    assert "conditional_index_update" not in types
    # The two primary facts lead the supporting list, in that order.
    assert [by_id[i].fact_type for i in ev[0].supporting_fact_ids[:2]] == [
        "sorting_operation", "extremum_access"
    ]


def test_sort_form_preserves_loop_form_precedence():
    """When both forms are present the loop form wins (sort form is fallback)."""
    code = '''
def f(a):
    a.sort()
    best = a[0]
    for x in a:
        if x * x > best:
            best = x
    return best, a[-1]
'''
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    ev = [t for t in detect_techniques(facts, build_relations(tree))
          if t.technique_id == "candidate_selection"]
    assert len(ev) == 1
    by_id = {f.fact_id: f for f in facts}
    types = {by_id[i].fact_type for i in ev[0].supporting_fact_ids}
    assert "conditional_index_update" in types
    assert "sorting_operation" not in types


# ============================================================
# NEGATIVE: sort form must not fire
# ============================================================

#: Shapes where no T12 form fires at all.
@pytest.mark.parametrize("code", [
    SORT_ONLY,
    SORT_AS_OUTPUT,
    SORT_THEN_TRAVERSAL,
    SORT_THEN_UNRELATED_SUBSCRIPT,
    TWO_POINTER_AFTER_SORT,
    HEAP_TOP_K,
    MONOTONIC_STACK,
    MAPPING_BUILD_ONLY,
])
def test_sort_form_negative_no_detection(code):
    assert not _has_candidate(code)


#: Shapes where a *different* (pre-existing loop) form may fire. The Step 4
#: obligation is that the **sort form** stays silent: sorting must not be
#: promoted into candidate selection by these solutions.
@pytest.mark.parametrize("code", [
    BINARY_SEARCH_AFTER_SORT,
    SLIDING_WINDOW,
])
def test_sort_form_negative_sort_form_silent(code):
    facts = extract_structural_facts(ast.parse(code))
    assert _candidate_selection_sort_form(facts) is None


def test_binary_search_sort_is_not_promoted_by_the_sort_form():
    """Binary search after a sort: the sort form must not fire. Any T12
    evidence present comes from the pre-existing loop-form path, which is
    pinned by the Step 1 suite and deliberately unchanged here."""
    tree = ast.parse(BINARY_SEARCH_AFTER_SORT)
    facts = extract_structural_facts(tree)
    assert _candidate_selection_sort_form(facts) is None
    by_id = {f.fact_id: f for f in facts}
    for t in detect_techniques(facts, build_relations(tree)):
        if t.technique_id != "candidate_selection":
            continue
        types = {by_id[i].fact_type for i in t.supporting_fact_ids}
        assert "sorting_operation" not in types
        assert "conditional_index_update" in types


def test_sliding_window_sort_form_silent():
    """Sliding window with a running max: no sorting evidence exists at all,
    so the sort form cannot be responsible for any detection."""
    facts = extract_structural_facts(ast.parse(SLIDING_WINDOW))
    assert _candidate_selection_sort_form(facts) is None
    assert [f for f in facts if f.fact_type == "sorting_operation"] == []


def test_sorted_without_target_records_nothing():
    """A bare ``sorted(x)`` expression names no sequence, so no sort fact."""
    assert _attrs("def f(a):\n    sorted(a)\n", "sorting_operation") == []


def test_sort_fact_records_sorted_structure_not_a_name_convention():
    in_place = _attrs(SORT_THEN_SMALLEST, "sorting_operation")
    functional = _attrs(SORTED_THEN_EXTREMUM, "sorting_operation")
    assert in_place and in_place[0]["structure"] == "a"
    assert in_place[0]["method"] == "sort"
    assert functional and functional[0]["structure"] == "s"
    assert functional[0]["method"] == "sorted"


def test_sort_fact_records_reverse_without_requiring_it():
    assert _attrs(SORT_REVERSE_ARGUMENT_EQUIVALENT, "sorting_operation")[0]["reverse"] is True
    assert _attrs(SORT_THEN_SMALLEST, "sorting_operation")[0]["reverse"] is False


def test_extremum_fact_ignores_variable_index_and_writes():
    """Variable index = traversal; a write is not a read."""
    assert _attrs(BINARY_SEARCH_AFTER_SORT, "extremum_access") == []
    assert _attrs(TWO_POINTER_AFTER_SORT, "extremum_access") == []
    write_only = "def f(a):\n    a[0] = 5\n    return a\n"
    assert _attrs(write_only, "extremum_access") == []


def test_extremum_fact_records_index_form():
    forms = {a["index_form"] for a in _attrs(SORTED_PLUS_LENGTH_OFFSET, "extremum_access")}
    assert forms == {"length_offset", "constant"}


# ============================================================
# RELATION CONTRACT
# ============================================================

def test_relations_cannot_fabricate_sort_form():
    """Without sorting structural evidence the technique must not fire,
    even when a full relations bundle is supplied."""
    code = '''
def f(a):
    return a[0]
'''
    assert not _has_candidate(code, with_relations=True)
    assert _attrs(code, "sorting_operation") == []
    # ...and relations exist and are non-trivial for this input.
    rel = build_relations(ast.parse(code))
    assert rel is not None


def test_relation_presence_does_not_change_sort_form_output():
    """The sort form is fact-driven; supplying relations neither adds nor
    removes a detection. (The loop form's relation fence is covered by the
    Step 1 suite.)"""
    for code in (SORT_THEN_SMALLEST, SORTED_PLUS_LENGTH_OFFSET, TWO_POINTER_AFTER_SORT):
        assert _has_candidate(code, True) == _has_candidate(code, False)


def test_sort_form_implementation_is_relation_free_by_construction():
    """Documenting the honest contract: the sort form takes only facts. It can
    therefore neither be fabricated by relations nor tightened by them; the
    'cannot fabricate' direction is what matters and is asserted above."""
    facts = extract_structural_facts(ast.parse(SORT_THEN_SMALLEST))
    assert _candidate_selection_sort_form(facts) is not None
    assert _candidate_selection_sort_form([]) is None


# ============================================================
# LOOP-FORM REGRESSION (T12 form 1 must be unchanged)
# ============================================================

LOOP_FORM_RUNNING_MAX = '''
def f(nums):
    best = nums[0]
    for x in nums:
        if x > best:
            best = x
    return best
'''

LOOP_FORM_ACCUMULATOR_NEGATIVE = '''
def f(nums):
    total = 0
    for x in nums:
        if x > 0:
            total += x
    return total
'''

LOOP_FORM_WINDOW_NEGATIVE = '''
def f(grid):
    best = 0
    left = 0
    for right in range(len(grid)):
        if grid[right] > 0:
            grid[left] = grid[right]
            left += 1
        best = max(best, left)
    return best
'''


def test_loop_form_still_fires():
    assert _has_candidate(LOOP_FORM_RUNNING_MAX)


def test_loop_form_fences_intact():
    assert not _has_candidate(LOOP_FORM_ACCUMULATOR_NEGATIVE)
    assert not _has_candidate(LOOP_FORM_WINDOW_NEGATIVE)


def test_loop_form_evidence_shape_unchanged():
    tree = ast.parse(LOOP_FORM_RUNNING_MAX)
    facts = extract_structural_facts(tree)
    ev = [t for t in detect_techniques(facts, build_relations(tree))
          if t.technique_id == "candidate_selection"]
    assert len(ev) == 1
    by_id = {f.fact_id: f for f in facts}
    types = {by_id[i].fact_type for i in ev[0].supporting_fact_ids}
    assert "conditional_index_update" in types
    assert "sorting_operation" not in types


# ============================================================
# GROUND TRUTH / VOCABULARY INTEGRATION
# ============================================================

def test_candidate_selection_registered_and_remains_a_technique():
    assert "candidate_selection" in VALID_TECHNIQUES
    # No greedy *strategy* is introduced: the concept stays a technique.
    assert "greedy" not in VALID_V1_CONCEPTS


def test_greedy_local_mapping_unchanged():
    mapping = PATTERN_TO_V1_MAPPING["greedy_local"]
    assert mapping["required"] == ["candidate_selection"]
    assert "sliding_window" in mapping["excluded"]


def test_mapping_references_only_valid_concepts():
    for pattern, mapping in PATTERN_TO_V1_MAPPING.items():
        for concept in mapping.get("required", []) + mapping.get("optional", []):
            assert concept in VALID_V1_CONCEPTS, f"{pattern} references unknown {concept}"


def test_greedy_local_has_no_missing_vocabulary():
    assert "greedy_local" not in missing_vocabulary_for_patterns(["greedy_local"])
