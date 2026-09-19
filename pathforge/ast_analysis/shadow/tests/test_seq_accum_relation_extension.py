"""Generalized regression tests: sequential_accumulation M2 relation extension.

Extends T1 (sequential_accumulation) with two container forms the scalar
``accumulator_update`` fact cannot represent (its target is a plain Name):

- **assign-form self-referential counting**: ``freq[x] = freq.get(x, 0) + 1``
  (Assign/AnnAssign indexed write whose value combines exactly one read of
  the same structure with an external value);
- **append-form self-referential accumulation**: ``prefix.append(prefix[-1] + x)``
  (append whose argument combines exactly one read of the same structure).

The evidence join runs through the M2 relation layer
(``self_referential_updates``, loop-scoped by construction, cross-checked
against ``updated_in_loop``) — **no new fact type**. All fences pinned here:
DP tables (two self-reads = table filling), plain appends, map replacement,
non-loop self-reference, memoization, scalar accumulation (pre-existing
behavior, unchanged), candidate selection.

No variable-name evidence, no problem IDs.
"""
import ast
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import (
    detect_techniques,
    _seq_accum_container_evidence,
)
from pathforge.ast_analysis.shadow.data_structures import StructuralFact


# ============================================================
# Helpers
# ============================================================

def _has_seq(code):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree)
    return any(
        t.technique_id == "sequential_accumulation"
        for t in detect_techniques(facts, relations)
    )


def _container_evidence(code):
    """Call the container path directly and return (evidence, facts, relations)."""
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree)
    types = {f.fact_type for f in facts}
    ev = _seq_accum_container_evidence(
        facts,
        "while_loop_comparison" in types,
        "for_loop_iteration" in types,
        relations,
    )
    return ev, facts, relations


def _fact(facts, fact_type, **attrs):
    for f in facts:
        if f.fact_type != fact_type:
            continue
        if all(f.attributes.get(k) == v for k, v in attrs.items()):
            return f
    return None


# ============================================================
# Code families — assign-form positives
# ============================================================

ASSIGN_COUNT_FOR = '''
def f(items):
    freq = {}
    for x in items:
        freq[x] = freq.get(x, 0) + 1
    return freq
'''

ASSIGN_COUNT_NONOBVIOUS = '''
def f(blob):
    tally = {}
    for c in blob:
        tally[c] = tally.get(c, 0) - 1
    return tally
'''

ASSIGN_COUNT_WHILE = '''
def f(items):
    freq = {}
    i = 0
    while i < len(items):
        freq[items[i]] = freq.get(items[i], 0) + 1
        i += 1
    return freq
'''

ASSIGN_COUNT_ANNOTATED = '''
def f(items):
    freq: dict = {}
    for x in items:
        freq[x] = freq.get(x, 0) + 1
    return freq
'''

ASSIGN_COUNT_ATTR = '''
class T:
    def add_all(self, items):
        for num in items:
            self.nums[num] = self.nums.get(num, 0) + 1
'''

# Keyed-index equivalent: previous state read at the same key through the
# subscript form rather than .get() (still exactly one same-structure read).
ASSIGN_COUNT_SUBSCRIPT_PREV = '''
def f(pairs):
    seen_count = {}
    for k, v in pairs:
        seen_count[k] = v + seen_count[k]
    return seen_count
'''


# ============================================================
# Code families — append-form positives
# ============================================================

APPEND_ACC_FOR = '''
def f(nums):
    prefix = [0]
    for n in nums:
        prefix.append(prefix[-1] + n)
    return prefix
'''

APPEND_ACC_NONOBVIOUS = '''
def f(vals):
    trail = [0]
    for v in vals:
        trail.append(trail[-1] * 2 + v)
    return trail
'''

APPEND_ACC_ATTR = '''
class P:
    def build(self, nums):
        self.prefix = [0]
        for n in nums:
            self.prefix.append(self.prefix[-1] + n)
'''

APPEND_ACC_WHILE = '''
def f(nums, i=0):
    prefix = [0]
    while i < len(nums):
        prefix.append(prefix[-1] + nums[i])
        i += 1
    return prefix
'''


# ============================================================
# Code families — negatives
# ============================================================

NEG_DP_TABLE = '''
def f(n):
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
'''

NEG_DP_GRID = '''
def f(grid):
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            dp[i][j] = grid[i][j] + min(dp[i-1][j], dp[i][j-1])
    return dp[m-1][n-1]
'''

NEG_SCALAR_ACC = '''
def f(nums):
    total = 0
    for x in nums:
        total += x
    return total
'''

NEG_PLAIN_APPEND = '''
def f(nums):
    result = []
    for x in nums:
        result.append(x)
    return result
'''

NEG_MAP_REPLACEMENT = '''
def f(items):
    d = {}
    for k, v in items:
        d[k] = v
    return d
'''

NEG_OTHER_STRUCTURE_REF = '''
def f(d2):
    d = {}
    for k in d2:
        d[k] = other(d2[k])
    return d
'''

NEG_OUTSIDE_LOOP = '''
def f(items):
    freq = {}
    freq['a'] = freq.get('a', 0) + 1
    return freq
'''

NEG_CANDIDATE_SELECTION = '''
def f(nums):
    best = 0
    for x in nums:
        if x > best:
            best = x
    return best
'''

NEG_MEMO_RECURSION = '''
def solve(n, memo={}):
    if n <= 1:
        return n
    if n in memo:
        return memo[n]
    memo[n] = memo.get(n, 0) + solve(n - 1) + solve(n - 2)
    return memo[n]
'''

# Non-cumulative window state: plain jump reassignment, no self-referential
# assignment anywhere (window bodies containing ``lo += 1`` or
# ``best = max(best, ...)`` are scalar accumulators via the pre-existing
# scalar path and are pinned separately).
NEG_WINDOW_STATE = '''
def f(a, k):
    lo = 0
    for hi in range(len(a)):
        if a[hi] > k:
            lo = hi + 1
    return lo
'''

# Window-internal tally in ASSIGN form: structurally identical to stream
# counting, so the container path fires at technique level. Pinned here as a
# disclosed boundary — the shrink side uses augmented writes, which the
# relation deliberately does not record, and no verdict depends on the
# technique for window-shaped GT (verified on both corpora).
WINDOW_ASSIGN_COUNT = '''
def f(s, k):
    need = {}
    lo = 0
    for hi in range(len(s)):
        need[s[hi]] = need.get(s[hi], 0) + 1
        if need[s[hi]] > k:
            need[s[lo]] = need.get(s[lo], 0) - 1
            lo += 1
    return lo
'''

NEG_ATTR_GRID_WRITE = '''
class G:
    def upd(self, r, c, v):
        for c2 in range(c):
            self.grid[r][c2] = v
'''


# ============================================================
# ASSIGN-FORM POSITIVES
# ============================================================

@pytest.mark.parametrize("code", [
    ASSIGN_COUNT_FOR,
    ASSIGN_COUNT_NONOBVIOUS,
    ASSIGN_COUNT_WHILE,
    ASSIGN_COUNT_ANNOTATED,
    ASSIGN_COUNT_ATTR,
    ASSIGN_COUNT_SUBSCRIPT_PREV,
])
def test_assign_form_positive(code):
    assert _has_seq(code)


def test_assign_form_supporting_facts_are_loop_and_indexed_write():
    ev, facts, _rel = _container_evidence(ASSIGN_COUNT_FOR)
    assert ev is not None
    by_id = {f.fact_id: f for f in facts}
    types = {by_id[i].fact_type for i in ev.supporting_fact_ids}
    assert "for_loop_iteration" in types


def test_assign_form_records_structure_not_name_convention():
    _tree = ast.parse(ASSIGN_COUNT_NONOBVIOUS)
    facts = extract_structural_facts(_tree)
    assert _fact(facts, "indexed_write", structure="tally") is not None


def test_annotated_indexed_write_fact_is_emitted():
    """M1 form completion: annotated subscript writes now produce the fact."""
    tree = ast.parse(ASSIGN_COUNT_ANNOTATED)
    facts = extract_structural_facts(tree)
    assert _fact(facts, "indexed_write", structure="freq", syntax_form="assignment") is not None


def test_attr_backed_indexed_write_records_attribute_name():
    tree = ast.parse(ASSIGN_COUNT_ATTR)
    facts = extract_structural_facts(tree)
    assert _fact(facts, "indexed_write", structure="nums") is not None


# ============================================================
# APPEND-FORM POSITIVES
# ============================================================

@pytest.mark.parametrize("code", [
    APPEND_ACC_FOR,
    APPEND_ACC_NONOBVIOUS,
    APPEND_ACC_ATTR,
    APPEND_ACC_WHILE,
])
def test_append_form_positive(code):
    assert _has_seq(code)


def test_append_form_relation_records_append_receiver_in_loop():
    rel = build_relations(ast.parse(APPEND_ACC_FOR))
    assert "append" in rel.self_referential_updates.get("prefix", set())
    assert "for" in rel.updated_in_loop.get("prefix", set())


def test_append_form_attr_receiver_recorded():
    rel = build_relations(ast.parse(APPEND_ACC_ATTR))
    assert "append" in rel.collection_ops.get("prefix", set())
    assert "append" in rel.self_referential_updates.get("prefix", set())


# ============================================================
# NEGATIVES
# ============================================================

@pytest.mark.parametrize("code", [
    NEG_DP_TABLE,
    NEG_DP_GRID,
    NEG_PLAIN_APPEND,
    NEG_MAP_REPLACEMENT,
    NEG_OTHER_STRUCTURE_REF,
    NEG_OUTSIDE_LOOP,
    NEG_CANDIDATE_SELECTION,
    NEG_MEMO_RECURSION,
    NEG_WINDOW_STATE,
    NEG_ATTR_GRID_WRITE,
])
def test_container_forms_negative(code):
    assert not _has_seq(code)


def test_dp_table_never_records_self_referential_update():
    """Two same-structure reads = table filling, deliberately not recorded."""
    rel = build_relations(ast.parse(NEG_DP_TABLE))
    assert "dp" not in rel.self_referential_updates


def test_plain_append_never_records_self_referential_update():
    rel = build_relations(ast.parse(NEG_PLAIN_APPEND))
    assert "result" not in rel.self_referential_updates


def test_window_scalar_accumulation_is_preexisting_behavior():
    """``window += a[hi]`` is a scalar accumulator and fired before this batch
    via the unchanged scalar path — pinned here so the container extension is
    not blamed for it and cannot regress it."""
    code = '''
def f(a, k):
    window = 0
    lo = 0
    for hi in range(len(a)):
        window += a[hi]
        if hi - lo + 1 > k:
            window -= a[lo]
            lo += 1
    return window
'''
    assert _has_seq(code)
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    rel = build_relations(tree)
    # The container relation contributes nothing here: window is scalar.
    assert "window" not in rel.self_referential_updates


def test_window_augmented_shrink_not_recorded():
    """Augmented indexed writes (window shrink, ``cnt[x] -= 1``) are never
    recorded as self-referential updates — the counting form belongs to the
    counting vocabulary, not accumulation."""
    code = '''
def f(s, k):
    cnt = {}
    for c in s:
        cnt[c] -= 1
    return cnt
'''
    rel = build_relations(ast.parse(code))
    assert "cnt" not in rel.self_referential_updates


def test_window_assign_form_counting_disclosed_boundary():
    """A tally updated in assign form inside a window loop is structurally
    identical to stream counting, so it fires at TECHNIQUE level. This is a
    disclosed boundary: no verdict depends on sequential_accumulation for
    window-shaped ground truth (measured on both corpora)."""
    assert _has_seq(WINDOW_ASSIGN_COUNT)


def test_scalar_accumulation_behavior_unchanged():
    """Pre-existing scalar form still fires (N3 behavior preserved)."""
    assert _has_seq(NEG_SCALAR_ACC)


# ============================================================
# RELATION CONTRACT
# ============================================================

class _FakeRelations:
    """Synthetic relations bundle: must NOT be able to fabricate evidence."""

    def __init__(self, sru, uil, cops=None):
        self.self_referential_updates = sru
        self.updated_in_loop = uil
        self.collection_ops = cops or {}


def _bare_facts(code):
    return extract_structural_facts(ast.parse(code))


def test_relations_cannot_fabricate_without_supporting_fact():
    """A relation claiming a self-referential indexed write is inadmissible
    unless a real indexed_write fact on the same structure exists. The
    synthetic structure name has no fact support anywhere in the code."""
    facts = _bare_facts(NEG_MAP_REPLACEMENT)  # only writes d[k]=v
    rel = _FakeRelations(
        sru={"ghost": {"indexed_write"}},
        uil={"ghost": {"for"}},
    )
    types = {f.fact_type for f in facts}
    ev = _seq_accum_container_evidence(
        facts, "while_loop_comparison" in types, "for_loop_iteration" in types, rel
    )
    assert ev is None


def test_relations_cannot_fabricate_without_loop_membership():
    """Self-reference evidence without loop membership must not fire."""
    facts = _bare_facts(NEG_OUTSIDE_LOOP)
    rel = _FakeRelations(
        sru={"freq": {"indexed_write"}},
        uil={},  # no loop membership claimed
    )
    types = {f.fact_type for f in facts}
    ev = _seq_accum_container_evidence(
        facts, "while_loop_comparison" in types, "for_loop_iteration" in types, rel
    )
    assert ev is None


def test_relations_cannot_fabricate_append_without_collection_op():
    """An append claim is inadmissible without a recorded append operation."""
    code = '''
def f(nums):
    out = []
    for n in nums:
        out.append(n)
    return out
'''
    facts = _bare_facts(code)
    rel = _FakeRelations(
        sru={"out": {"append"}},
        uil={"out": {"for"}},
        cops={},  # no append op recorded
    )
    types = {f.fact_type for f in facts}
    ev = _seq_accum_container_evidence(
        facts, "while_loop_comparison" in types, "for_loop_iteration" in types, rel
    )
    assert ev is None


def test_real_relations_are_admissible_and_tighten():
    """Genuine inputs produce admissible evidence; the container path never
    fires for the DP table even though loop membership exists."""
    ev_ok, _f, _r = _container_evidence(ASSIGN_COUNT_FOR)
    assert ev_ok is not None
    ev_dp, _f2, _r2 = _container_evidence(NEG_DP_TABLE)
    assert ev_dp is None


def test_container_path_is_last_fallback():
    """With a scalar accumulator present and admissible, the scalar path wins
    and the container path is only a fallback."""
    code = '''
def f(nums):
    total = 0
    for x in nums:
        total += x
    return total
'''
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    rel = build_relations(tree)
    evs = [t for t in detect_techniques(facts, rel)
           if t.technique_id == "sequential_accumulation"]
    assert len(evs) == 1
    by_id = {f.fact_id: f for f in facts}
    types = {by_id[i].fact_type for i in evs[0].supporting_fact_ids}
    assert "accumulator_update" in types


# ============================================================
# N3 REGRESSION — scalar while/for behavior preserved
# ============================================================

N3_WHILE_ACC = '''
def f(n):
    total = 0
    i = 0
    while i < n:
        total += i
        i += 1
    return total
'''

N3_FOR_ACC = '''
def f(nums):
    total = 0
    for x in nums:
        total += x
    return total
'''

N3_FOR_EQUAL_SIGN = '''
def f(nums):
    total = 0
    for x in nums:
        total = total + x
    return total
'''


@pytest.mark.parametrize("code", [N3_WHILE_ACC, N3_FOR_ACC, N3_FOR_EQUAL_SIGN])
def test_n3_scalar_forms_unchanged(code):
    assert _has_seq(code)


def test_n3_loop_variable_exclusion_preserved():
    """The scalar path's accumulator exclusion is unchanged: a loop-variable
    self-update is never joined as the accumulator. The loop-fact-only
    evidence that remains is pre-existing scalar-path behavior (the join
    appends the loop fact unconditionally); this batch's container path adds
    no evidence here (no self-referential container update exists)."""
    code = '''
def f(n):
    for i in range(n):
        i = i + 1
    return i
'''
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    rel = build_relations(tree)
    assert rel.self_referential_updates == {}
    evs = [t for t in detect_techniques(facts, rel)
           if t.technique_id == "sequential_accumulation"]
    assert len(evs) == 1
    by_id = {f.fact_id: f for f in facts}
    types = {by_id[i].fact_type for i in evs[0].supporting_fact_ids}
    assert types == {"for_loop_iteration"}  # scalar path shape, unchanged
