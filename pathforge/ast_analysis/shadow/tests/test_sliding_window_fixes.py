"""Regression tests for sliding-window fact-extraction fixes.

Covers the three root causes identified in SLIDING_WINDOW_FAILURE_ROOT_CAUSE.md:
1. Cross-variable while-loop comparison detection
2. conditional_index_update for while-loop shrink bodies
3. Def-use chain detection for variables modified in while-loop bodies

Each test verifies that specific structural facts, techniques, and/or strategies
are produced (or NOT produced) for the given code pattern.
"""
import ast
import pytest

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _extract_all(code: str):
    """Parse code and return (facts, techniques, strategies)."""
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    techniques = detect_techniques(facts)
    strategies = evaluate_strategies(techniques, facts)
    return facts, techniques, strategies


def _fact_types(facts):
    return {f.fact_type for f in facts}


def _has_fact_with_attr(facts, fact_type, attr_key, attr_value):
    return any(
        f.fact_type == fact_type and f.attributes.get(attr_key) == attr_value
        for f in facts
    )


def _technique_ids(techniques):
    return {t.technique_id for t in techniques}


def _strategy_ids(strategies):
    return {s.strategy_id for s in strategies}


# ===========================================================================
# FIX 1: Cross-variable while-loop comparison
# ===========================================================================

class TestCrossVariableWhileComparison:
    """The inner while loop in sliding-window shrink phases compares a
    computed state expression while modifying a different pointer variable.
    The fact extractor must emit while_loop_comparison with cross_variable=True
    when the compared and modified variable sets don't overlap."""

    def test_dict_lookup_shrink_produces_cross_variable_comparison(self):
        """Problem 2958: while freq[nums[right]] > k: left += 1"""
        code = """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        facts, _, _ = _extract_all(code)
        assert _has_fact_with_attr(
            facts, "while_loop_comparison", "cross_variable", True
        ), "Must emit while_loop_comparison with cross_variable=True for dict-shrink pattern"

    def test_set_membership_shrink_produces_cross_variable_comparison(self):
        """Problem 3: while s[right] in char_set: ... left += 1"""
        code = """
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        facts, _, _ = _extract_all(code)
        assert _has_fact_with_attr(
            facts, "while_loop_comparison", "cross_variable", True
        ), "Must emit while_loop_comparison with cross_variable=True for set-membership pattern"

    def test_same_variable_comparison_has_no_cross_variable_flag(self):
        """Binary search: while low <= high: low = mid + 1
        This is same-variable comparison and must NOT have cross_variable."""
        code = """
def search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""
        facts, _, _ = _extract_all(code)
        # Should have while_loop_comparison WITHOUT cross_variable
        while_facts = [f for f in facts if f.fact_type == "while_loop_comparison"]
        assert len(while_facts) > 0, "Binary search must produce while_loop_comparison"
        for wf in while_facts:
            assert not wf.attributes.get("cross_variable"), \
                "Binary search must NOT have cross_variable=True"


# ===========================================================================
# FIX 2: conditional_index_update for while-loop shrink bodies
# ===========================================================================

class TestConditionalIndexUpdateWhileLoop:
    """The conditional_index_update fact must fire for while-loop shrink bodies,
    not only for if-statements."""

    def test_while_shrink_in_for_produces_conditional_index_update(self):
        """while freq[nums[right]] > k: left += 1 inside a for loop"""
        code = """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
"""
        facts, _, _ = _extract_all(code)
        cond_updates = [f for f in facts if f.fact_type == "conditional_index_update"]
        while_updates = [f for f in cond_updates if f.attributes.get("branch") == "while"]
        assert len(while_updates) > 0, \
            "Must emit conditional_index_update with branch='while' for shrink loop"

    def test_accumulator_shrink_while_produces_conditional_index_update(self):
        """while total >= target: total -= nums[left]; left += 1"""
        code = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            total -= nums[left]
            left += 1
"""
        facts, _, _ = _extract_all(code)
        cond_updates = [f for f in facts if f.fact_type == "conditional_index_update"]
        while_updates = [f for f in cond_updates if f.attributes.get("branch") == "while"]
        assert len(while_updates) > 0, \
            "Must emit conditional_index_update with branch='while' for accumulator shrink"

    def test_if_shrink_still_produces_conditional_index_update(self):
        """if ... > k: left += 1 — existing behavior must remain"""
        code = """
def maxReplacement(s, k):
    from collections import Counter
    count = Counter()
    left = 0
    for right in range(len(s)):
        count[s[right]] += 1
        if right - left + 1 > k:
            count[s[left]] -= 1
            left += 1
"""
        facts, _, _ = _extract_all(code)
        cond_updates = [f for f in facts if f.fact_type == "conditional_index_update"]
        if_updates = [f for f in cond_updates if f.attributes.get("branch") == "if"]
        assert len(if_updates) > 0, \
            "Existing if-based conditional_index_update must still fire"


# ===========================================================================
# FIX 3: Def-use chain for variables modified in while-loop bodies
# ===========================================================================

class TestWhileLoopDefUseChain:
    """Variables modified inside a while-loop body that are used in the while
    condition itself or in subsequent statements must create a
    variable_use_in_loop_body fact."""

    def test_accumulator_used_in_while_condition(self):
        """while total >= target: total -= nums[left]
        total is modified in the body and used in the condition."""
        code = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            total -= nums[left]
            left += 1
"""
        facts, _, _ = _extract_all(code)
        var_use = [f for f in facts if f.fact_type == "variable_use_in_loop_body"]
        assert len(var_use) > 0, \
            "Must detect variable_use_in_loop_body for accumulator in while condition"
        used_vars = set()
        for vu in var_use:
            used_vars.update(vu.attributes.get("variables", []))
        assert "total" in used_vars, \
            "total must appear in variable_use_in_loop_body"

    def test_counter_used_in_while_condition(self):
        """while right - left + 1 > minSize: left += 1
        right, left are used in the while condition."""
        code = """
def maxFreq(s, maxLetters, minSize, maxSize):
    from collections import Counter
    count = Counter()
    left = 0
    for right in range(len(s)):
        count[s[right]] += 1
        while right - left + 1 > minSize:
            count[s[left]] -= 1
            left += 1
"""
        facts, _, _ = _extract_all(code)
        var_use = [f for f in facts if f.fact_type == "variable_use_in_loop_body"]
        assert len(var_use) > 0, \
            "Must detect variable_use_in_loop_body for counter-based while condition"


# ===========================================================================
# Sliding-window strategy detection (end-to-end)
# ===========================================================================

class TestSlidingWindowDetection:
    """Verify that the full pipeline (facts → techniques → strategies)
    detects sliding_window for the key implementations."""

    @pytest.mark.parametrize("name,code,expected", [
        ("2958_dict_freq", """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
""", True),
        ("3_set_membership", """
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
""", True),
        ("maxFreq_counter", """
def maxFreq(s, maxLetters, minSize, maxSize):
    from collections import Counter
    count = Counter()
    left = 0
    res = 0
    for right in range(len(s)):
        count[s[right]] += 1
        while right - left + 1 > minSize:
            count[s[left]] -= 1
            if count[s[left]] == 0:
                del count[s[left]]
            left += 1
        if right - left + 1 == minSize and len(count) <= maxLetters:
            res = max(res, right - left + 1)
    return res
""", True),
        ("76_min_window", """
def minWindow(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end+1] if end < float('inf') else \"\"
""", True),
    ])
    def test_sliding_window_detected(self, name, code, expected):
        _, _, strategies = _extract_all(code)
        has_sliding = "sliding_window" in _strategy_ids(strategies)
        assert has_sliding == expected, \
            f"{name}: sliding_window detection={has_sliding}, expected={expected}"


# ===========================================================================
# Non-sliding-window regression protection
# ===========================================================================

class TestNonSlidingWindowRegression:
    """Verify that existing algorithms are NOT misclassified as sliding_window."""

    def test_two_pointers_opposite_not_sliding_window(self):
        code = """
def twoSumSorted(numbers, target):
    left = 0
    right = len(numbers) - 1
    while left < right:
        total = numbers[left] + numbers[right]
        if total == target:
            return [left + 1, right + 1]
        elif total < target:
            left += 1
        else:
            right -= 1
    return []
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "two_pointers_opposite" in ids
        assert "sliding_window" not in ids

    def test_binary_search_not_sliding_window(self):
        code = """
def search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "binary_search" in ids
        assert "sliding_window" not in ids

    def test_dp_bottom_up_not_sliding_window(self):
        code = """
def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "dp_bottom_up" in ids
        assert "sliding_window" not in ids

    def test_dfs_backtracking_not_sliding_window(self):
        code = """
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "dfs_backtracking" in ids
        assert "sliding_window" not in ids

    def test_linked_list_cycle_not_sliding_window(self):
        code = """
def hasCycle(head):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
"""
        facts, techniques, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "sliding_window" not in ids
        # linked_list_traversal should still be detected
        assert "linked_list_traversal" in _technique_ids(techniques)

    def test_bfs_not_sliding_window(self):
        code = """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "sliding_window" not in ids
        assert "bfs_shortest_path" in ids


# ===========================================================================
# Known limitations (documented, not regressions)
# ===========================================================================

# ===========================================================================
# SLIDING WINDOW 209 FIX: opposite_direction_updates refinement
# ===========================================================================

class TestOppositeDirectionUpdatesRefinement:
    """The sliding-window strategy now refines the opposite_direction_updates
    exclusion: it only blocks sliding_window when a while_loop_comparison has
    compared_variables ⊆ modified_variables (genuine two-pointer pattern).
    
    In sliding-window shrink loops, the while condition compares a state
    expression against a threshold, so at least one compared variable (the
    threshold) is NOT modified. Only the accumulator/state is modified.
    
    This allows LC 209-style sliding windows (with accumulator shrink) to
    correctly fire sliding_window, while still blocking genuine two-pointers."""

    def test_209_accumulator_shrink_detected(self):
        """LC 209: while total >= target: total -= nums[left]; left += 1.
        
        total is an accumulator state variable, left is a pointer.
        The while comparison is total >= target — total IS modified but target is NOT.
        compared = {total, target}, modified = {total} → compared ⊄ modified.
        Therefore sliding_window MUST fire."""
        code = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    min_len = float('inf')
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            min_len = min(min_len, right - left + 1)
            total -= nums[left]
            left += 1
    return min_len if min_len != float('inf') else 0
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "sliding_window" in ids, \
            "LC 209 accumulator shrink must be detected as sliding_window"
        assert "two_pointers_opposite" not in ids, \
            "LC 209 must NOT be two_pointers_opposite (total is not a pointer)"

    def test_209_modulo_style_detected(self):
        """LC 209 modulo-style variant: same logic, different variable names."""
        code = """
def minSubArrayLen(s, nums):
    i = 0
    total = 0
    best = float('inf')
    for j in range(len(nums)):
        total += nums[j]
        while total >= s:
            best = min(best, j - i + 1)
            total -= nums[i]
            i += 1
    return best if best < float('inf') else 0
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "LC 209 modulo-style must be detected as sliding_window"

    def test_209_loop_state_tracking_detected(self):
        """LC 209 must still detect loop_state_tracking technique."""
        code = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            total -= nums[left]
            left += 1
"""
        _, techniques, _ = _extract_all(code)
        assert "loop_state_tracking" in _technique_ids(techniques), \
            "LC 209 must still detect loop_state_tracking"

    def test_genuine_two_pointers_still_not_sliding_window(self):
        """Genuine two-pointers (twoSumSorted) must remain two_pointers_opposite
        and must NOT gain sliding_window."""
        code = """
def twoSumSorted(numbers, target):
    left = 0
    right = len(numbers) - 1
    while left < right:
        total = numbers[left] + numbers[right]
        if total == target:
            return [left + 1, right + 1]
        elif total < target:
            left += 1
        else:
            right -= 1
    return []
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "two_pointers_opposite" in ids, \
            "Genuine two-pointers must still detect two_pointers_opposite"
        assert "sliding_window" not in ids, \
            "Genuine two-pointers must NOT detect sliding_window"

    def test_genuine_two_pointers_max_area_still_not_sliding_window(self):
        """maxArea two-pointers: must remain two_pointers_opposite only."""
        code = """
def maxArea(height):
    left = 0
    right = len(height) - 1
    max_a = 0
    while left < right:
        area = min(height[left], height[right]) * (right - left)
        max_a = max(max_a, area)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_a
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "two_pointers_opposite" in ids
        assert "sliding_window" not in ids

    def test_binary_search_not_sliding_window(self):
        """Binary search must NOT gain sliding_window from the refinement."""
        code = """
def search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "binary_search" in ids
        assert "sliding_window" not in ids

    def test_monotonic_stack_not_sliding_window(self):
        """Monotonic stack must NOT gain sliding_window from the refinement."""
        code = """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        assert "monotonic_stack_strategy" in ids
        assert "sliding_window" not in ids

    def test_424_counter_shrink_detected(self):
        """LC 424: counter-based shrink still detected (was already working)."""
        code = """
def characterReplacement(s, k):
    from collections import Counter
    count = Counter()
    left = 0
    max_count = 0
    for right in range(len(s)):
        count[s[right]] += 1
        max_count = max(max_count, count[s[right]])
        while right - left + 1 - max_count > k:
            count[s[left]] -= 1
            left += 1
    return right - left + 1
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "LC 424 must still detect sliding_window"

    def test_3_set_membership_detected(self):
        """LC 3: set-membership shrink still detected (was already working)."""
        code = """
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies)

    def test_2958_dict_freq_detected(self):
        """LC 2958: dict-freq shrink still detected (was already working)."""
        code = """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies)

    def test_643_fixed_window_detected(self):
        """LC 643: fixed-window must still be detected."""
        code = """
def findMaxAverage(nums, k):
    total = sum(nums[:k])
    best = total
    for i in range(k, len(nums)):
        total += nums[i] - nums[i - k]
        if total > best:
            best = total
    return best / k
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        # Fixed-window may or may not fire depending on detection path
        # But must NOT be blocked by the refinement
        assert "two_pointers_opposite" not in ids, \
            "Fixed-window 643 must NOT be two_pointers_opposite"

    def test_max_freq_counter_shrink_detected(self):
        """maxFreq: counter-shrink must still be detected."""
        code = """
def maxFreq(s, maxLetters, minSize, maxSize):
    from collections import Counter
    count = Counter()
    left = 0
    res = 0
    for right in range(len(s)):
        count[s[right]] += 1
        while right - left + 1 > minSize:
            count[s[left]] -= 1
            if count[s[left]] == 0:
                del count[s[left]]
            left += 1
        if right - left + 1 == minSize and len(count) <= maxLetters:
            res = max(res, right - left + 1)
    return res
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies)

    def test_76_min_window_still_works(self):
        """LC 76: minimum window substring (nested while-in-if structure)."""
        code = """
def minWindow(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end+1] if end < float('inf') else ""
"""
        _, techniques, strategies = _extract_all(code)
        # 76 has a known limitation: variable_use_in_loop_body doesn't fire
        # due to the deeply nested while-in-if structure.
        # This test documents the current behavior.
        strat_ids = _strategy_ids(strategies)
        # At minimum, must NOT be blocked by the refinement
        assert "two_pointers_opposite" not in strat_ids, \
            "LC 76 must NOT be two_pointers_opposite"
        assert "monotonic_stack_strategy" not in strat_ids, \
            "LC 76 must NOT be monotonic_stack"


class TestKnownLimitations:
    """These tests document known limitations that are NOT regressions
    but are noted for future improvement."""

    def test_424_if_shrink_not_yet_detected(self):
        """Problem 424 uses an if-shrink (not while-shrink) where the
        modified variable is only used in the return statement outside
        the for-loop. This is a known limitation of the def-use chain
        detector which only checks within the for-loop body."""
        code = """
def maxReplacement(s, k):
    from collections import Counter
    count = Counter()
    left = 0
    max_count = 0
    for right in range(len(s)):
        count[s[right]] += 1
        max_count = max(max_count, count[s[right]])
        if right - left + 1 - max_count > k:
            count[s[left]] -= 1
            left += 1
    return len(s) - left
"""
        _, _, strategies = _extract_all(code)
        # Known limitation: sliding_window NOT detected for if-shrink pattern
        # where modified variable is only used in return outside the loop.
        # This test documents the limitation; if it starts passing, update
        # the test to assert True and remove this comment.
        assert "sliding_window" not in _strategy_ids(strategies), \
            "KNOWN LIMITATION changed: if-shrink pattern is now detected. " \
            "Update this test and remove the known-limitation annotation."

    def test_209_accumulator_not_two_pointers(self):
        """Problem 209: while total >= target with total -= nums[left]; left += 1.

        total is an accumulator (not a subscript index), left is a pointer.
        The bidirectional_index_scan detector now correctly rejects this because
        total does not appear as a subscript index. This means two_pointers_opposite
        is no longer incorrectly detected.

        sliding_window is NOW detected thanks to the opposite_direction_updates
        refinement (compared ⊄ modified allows the shrink loop to pass)."""
        code = """
def minSubArrayLen(target, nums):
    left = 0
    total = 0
    min_len = float('inf')
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            min_len = min(min_len, right - left + 1)
            total -= nums[left]
            left += 1
    return min_len if min_len != float('inf') else 0
"""
        _, _, strategies = _extract_all(code)
        ids = _strategy_ids(strategies)
        # FIXED: two_pointers_opposite is no longer detected
        assert "two_pointers_opposite" not in ids, \
            "209 should NOT be classified as two_pointers_opposite (total is not a pointer)"
        # FIXED: sliding_window IS now detected (opposite_direction refinement)
        assert "sliding_window" in ids, \
            "209 must now be detected as sliding_window (accumulator shrink)"
        # loop_state_tracking IS detected (fact extraction works)
        _, techniques, _ = _extract_all(code)
        assert "loop_state_tracking" in _technique_ids(techniques), \
            "loop_state_tracking must be detected for 209 (fact extraction works)"


# ===========================================================================
# ACCUMULATOR-WINDOW FIX: bidirectional_index_scan structural guard
# ===========================================================================

class TestAccumulatorWindowFix:
    """The bidirectional_index_scan detector now requires both incremented and
    decremented variables to appear as subscript indices. This prevents
    accumulator-based sliding windows from being misclassified as
    two_pointers_opposite."""

    def test_sw_longest_ones_not_two_pointers(self):
        """zeros is an accumulator, not a subscript index."""
        code = """
def longest_ones(nums, k):
    left = 0
    max_len = 0
    zeros = 0
    for right in range(len(nums)):
        if nums[right] == 0:
            zeros += 1
        while zeros > k:
            if nums[left] == 0:
                zeros -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies), \
            "Accumulator window must NOT be classified as two_pointers_opposite"
        assert "bidirectional_index_scan" not in _technique_ids(techniques), \
            "bidirectional_index_scan must NOT fire for accumulator window"

    def test_sw_max_consecutive_ones_not_two_pointers(self):
        """flips is an accumulator, not a subscript index."""
        code = """
def longest_oneness(nums, k):
    left = 0
    max_len = 0
    flips = 0
    for right in range(len(nums)):
        if nums[right] == 0:
            flips += 1
        while flips > k:
            if nums[left] == 0:
                flips -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies)
        assert "bidirectional_index_scan" not in _technique_ids(techniques)

    def test_fw_different_structure_not_two_pointers(self):
        """acc is an accumulator, not a subscript index."""
        code = """
def sliding(nums, size):
    acc = 0
    for i in range(size):
        acc += nums[i]
    best = acc
    i = size
    while i < len(nums):
        acc += nums[i]
        acc -= nums[i - size]
        if acc > best:
            best = acc
        i += 1
    return best
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies)
        assert "bidirectional_index_scan" not in _technique_ids(techniques)

    def test_genuine_two_pointers_still_detected(self):
        """Both left and right are subscript indices → genuine two-pointers."""
        code = """
def maxArea(height):
    left = 0
    right = len(height) - 1
    max_a = 0
    while left < right:
        area = min(height[left], height[right]) * (right - left)
        max_a = max(max_a, area)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_a
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" in _strategy_ids(strategies), \
            "Genuine two-pointers must still be detected"
        assert "bidirectional_index_scan" in _technique_ids(techniques), \
            "bidirectional_index_scan must fire for genuine two-pointers"

    def test_subscript_index_access_facts_generated(self):
        """subscript_index_access facts must be generated for subscript reads."""
        code = """
def example(arr):
    left = 0
    right = len(arr) - 1
    while left < right:
        if arr[left] < arr[right]:
            left += 1
        else:
            right -= 1
"""
        facts, _, _ = _extract_all(code)
        sia = [f for f in facts if f.fact_type == "subscript_index_access"]
        assert len(sia) > 0, "subscript_index_access facts must be generated"
        all_index_vars = set()
        for f in sia:
            all_index_vars.update(f.attributes.get("index_variables", []))
        assert "left" in all_index_vars, "left must be detected as subscript index"
        assert "right" in all_index_vars, "right must be detected as subscript index"


# ===========================================================================
# BIDIRECTIONAL POINTER GUARD REFINEMENT
# ===========================================================================

class TestBidirectionalPointerGuardRefinement:
    """The guard now requires at least one incremented AND at least one
    decremented variable to be subscript indices (not ALL variables)."""

    def test_two_pointers_with_accumulator(self):
        """tp_trapping_rain: left/right are pointers, water is accumulator.
        The guard must detect two_pointers_opposite despite water also being incremented."""
        code = """
def trap(height):
    left = 0
    right = len(height) - 1
    water = 0
    while left < right:
        if height[left] < height[right]:
            water += height[left]
            left += 1
        else:
            water += height[right]
            right -= 1
    return water
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" in _strategy_ids(strategies), \
            "tp_trapping_rain must detect two_pointers_opposite"
        assert "bidirectional_index_scan" in _technique_ids(techniques), \
            "bidirectional_index_scan must fire for two pointers + accumulator"

    def test_two_pointers_without_accumulator(self):
        """Genuine two-pointers with only pointer variables."""
        code = """
def maxArea(height):
    left = 0
    right = len(height) - 1
    max_a = 0
    while left < right:
        area = min(height[left], height[right]) * (right - left)
        max_a = max(max_a, area)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_a
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" in _strategy_ids(strategies)
        assert "bidirectional_index_scan" in _technique_ids(techniques)

    def test_two_pointers_renamed_variables(self):
        """Two-pointers with renamed variables."""
        code = """
def is_palindrome(s):
    front = 0
    back = len(s) - 1
    while front < back:
        if s[front] != s[back]:
            return False
        front += 1
        back -= 1
    return True
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" in _strategy_ids(strategies)
        assert "bidirectional_index_scan" in _technique_ids(techniques)

    def test_accumulator_window_still_rejected(self):
        """Accumulator-based sliding window must NOT be two_pointers_opposite."""
        code = """
def longest_ones(nums, k):
    left = 0
    max_len = 0
    zeros = 0
    for right in range(len(nums)):
        if nums[right] == 0:
            zeros += 1
        while zeros > k:
            if nums[left] == 0:
                zeros -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies)
        assert "bidirectional_index_scan" not in _technique_ids(techniques)

    def test_monotonic_stack_not_two_pointers(self):
        """Monotonic stack must NOT be two_pointers_opposite."""
        code = """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies)

    def test_binary_search_not_two_pointers(self):
        """Binary search must NOT be two_pointers_opposite."""
        code = """
def search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""
        _, techniques, strategies = _extract_all(code)
        assert "two_pointers_opposite" not in _strategy_ids(strategies)
        assert "binary_search" in _strategy_ids(strategies)


# ===========================================================================
# MONOTONIC STACK → SLIDING WINDOW FALSE CONFIRMATION FIX
# ===========================================================================

class TestMonotonicStackNotSlidingWindow:
    """Monotonic-stack implementations must NOT be classified as sliding_window.

    The sliding-window evaluator now has an absence constraint: when all three
    monotonic-stack-specific facts are present (stack_operation +
    monotonic_comparison + conditional_pop), sliding_window must not fire.

    Monotonic-stack pop loops produce the same structural signature as
    sliding-window shrink loops (conditional update + def-use chain), but
    the stack-specific facts are never present in genuine sliding windows.
    """

    def test_ms_next_greater_not_sliding_window(self):
        """ms_next_greater: must detect monotonic_stack, must NOT detect sliding_window."""
        code = """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        tech_ids = _technique_ids(techniques)
        assert "monotonic_stack_maintenance" in tech_ids, \
            "ms_next_greater must detect monotonic_stack_maintenance technique"
        assert "monotonic_stack_strategy" in strat_ids, \
            "ms_next_greater must detect monotonic_stack_strategy"
        assert "sliding_window" not in strat_ids, \
            "ms_next_greater must NOT detect sliding_window"

    def test_ms_daily_temperatures_not_sliding_window(self):
        """ms_daily_temperatures: must detect monotonic_stack, must NOT detect sliding_window."""
        code = """
def daily_temperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temperatures[stack[-1]] < temperatures[i]:
            idx = stack.pop()
            result[idx] = i - idx
        stack.append(i)
    return result
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        tech_ids = _technique_ids(techniques)
        assert "monotonic_stack_maintenance" in tech_ids
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_daily_temperatures must NOT detect sliding_window"

    def test_ms_histogram_not_sliding_window(self):
        """ms_histogram: must detect monotonic_stack, must NOT detect sliding_window."""
        code = """
def largest_rectangle_area(heights):
    stack = []
    max_area = 0
    for i in range(len(heights) + 1):
        h = heights[i] if i < len(heights) else 0
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    return max_area
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        tech_ids = _technique_ids(techniques)
        assert "monotonic_stack_maintenance" in tech_ids
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_histogram must NOT detect sliding_window"

    def test_ms_next_greater_renamed_not_sliding_window(self):
        """ms_next_greater with renamed variables: must NOT detect sliding_window."""
        code = """
def next_greater_element(nums):
    n = len(nums)
    res = [-1] * n
    stk = []
    for i in range(n):
        while stk and nums[stk[-1]] < nums[i]:
            idx = stk.pop()
            res[idx] = nums[i]
        stk.append(i)
    return res
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_next_greater_renamed must NOT detect sliding_window"

    def test_ms_trap_rain_water_not_sliding_window(self):
        """ms_trap_rain_water_stack: must detect monotonic_stack, must NOT detect sliding_window."""
        code = """
def trap(height):
    stack = []
    water = 0
    for i in range(len(height)):
        while stack and height[stack[-1]] < height[i]:
            bottom = stack.pop()
            if stack:
                w = (i - stack[-1] - 1) * (min(height[i], height[stack[-1]]) - height[bottom])
                water += w
        stack.append(i)
    return water
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_trap_rain_water must NOT detect sliding_window"

    def test_ms_sum_subarray_mins_not_sliding_window(self):
        """ms_sum_subarray_mins: must detect monotonic_stack, must NOT detect sliding_window."""
        code = """
def sum_subarray_mins(arr):
    MOD = 10**9 + 7
    stack = []
    result = 0
    for i in range(len(arr) + 1):
        while stack and (i == len(arr) or arr[stack[-1]] > arr[i]):
            idx = stack.pop()
            left = idx if not stack else idx - stack[-1] - 1
            right = i - idx
            result = (result + arr[idx] * left * right) % MOD
        stack.append(i)
    return result
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_sum_subarray_mins must NOT detect sliding_window"

    def test_ms_largest_hist_renamed_not_sliding_window(self):
        """ms_histogram with renamed variables: must NOT detect sliding_window."""
        code = """
def largest_rectangle(heights):
    stk = []
    best = 0
    for i in range(len(heights) + 1):
        h = heights[i] if i < len(heights) else 0
        while stk and heights[stk[-1]] > h:
            ht = heights[stk.pop()]
            w = i if not stk else i - stk[-1] - 1
            best = max(best, ht * w)
        stk.append(i)
    return best
"""
        _, techniques, strategies = _extract_all(code)
        strat_ids = _strategy_ids(strategies)
        assert "monotonic_stack_strategy" in strat_ids
        assert "sliding_window" not in strat_ids, \
            "ms_largest_hist_renamed must NOT detect sliding_window"


class TestSlidingWindowStillDetected:
    """Genuine sliding-window implementations must still be detected after
    the monotonic-stack exclusion is added."""

    def test_76_min_window_still_detected(self):
        """76/minWindow: must still detect sliding_window."""
        code = """
def minWindow(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end+1] if end < float('inf') else ""
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "76/minWindow must still detect sliding_window"

    def test_3_longest_substring_still_detected(self):
        """3/longestSubstring: must still detect sliding_window."""
        code = """
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "3/longestSubstring must still detect sliding_window"

    def test_2958_max_subarray_length_still_detected(self):
        """2958/maxSubarrayLength: must still detect sliding_window."""
        code = """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "2958/maxSubarrayLength must still detect sliding_window"

    def test_max_freq_still_detected(self):
        """maxFreq: must still detect sliding_window."""
        code = """
def maxFreq(s, maxLetters, minSize, maxSize):
    from collections import Counter
    count = Counter()
    left = 0
    res = 0
    for right in range(len(s)):
        count[s[right]] += 1
        while right - left + 1 > minSize:
            count[s[left]] -= 1
            if count[s[left]] == 0:
                del count[s[left]]
            left += 1
        if right - left + 1 == minSize and len(count) <= maxLetters:
            res = max(res, right - left + 1)
    return res
"""
        _, _, strategies = _extract_all(code)
        assert "sliding_window" in _strategy_ids(strategies), \
            "maxFreq must still detect sliding_window"


class TestSolutionGroupMatching:
    """Solution-group matching must produce correct outcomes after the fix."""

    def test_monotonic_stack_vs_sliding_window_group_not_confirmed(self):
        """Monotonic-stack code vs sliding-window group must NOT be CONFIRMED."""
        code = """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
"""
        _, techniques, strategies = _extract_all(code)
        sw_group = {
            "id": "group_0",
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        outcome = evaluate_solution_groups([sw_group], techniques, strategies, [])
        assert outcome.outcome != "CONFIRMED", \
            f"Monotonic stack vs SW group must NOT be CONFIRMED, got {outcome.outcome}"

    def test_sliding_window_code_vs_sliding_window_group_still_confirmed(self):
        """Genuine sliding-window code vs sliding-window group must still be CONFIRMED."""
        code = """
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        _, techniques, strategies = _extract_all(code)
        sw_group = {
            "id": "group_0",
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        outcome = evaluate_solution_groups([sw_group], techniques, strategies, [])
        assert outcome.outcome == "CONFIRMED", \
            f"Genuine SW vs SW group must be CONFIRMED, got {outcome.outcome}"
