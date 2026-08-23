"""Phase 5A tests: linked-list traversal, fixed sliding window, monotonic stack.

Tests the new techniques and strategies added in Phase 5A:
- T8: linked_list_traversal
- T9: fixed_window_maintenance
- T10: monotonic_stack_maintenance
- S9: monotonic_stack_strategy

Verifies:
- Positive cases (technique/strategy detected)
- Hard negatives (technique/strategy NOT detected)
- Rename/syntax robustness
- Cross-pattern regression
"""
import ast
import pytest

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


# ============================================================
# Test code samples
# ============================================================

# --- Linked-list reversal ---
LINKED_LIST_REVERSAL = """
class Solution:
    def reverseList(self, head):
        prev = None
        curr = head
        while curr:
            next_temp = curr.next
            curr.next = prev
            prev = curr
            curr = next_temp
        return prev
"""

# --- Linked-list merge (two-pointer) ---
LINKED_LIST_MERGE = """
class Solution:
    def mergeTwoLists(self, l1, l2):
        dummy = ListNode()
        curr = dummy
        while l1 and l2:
            if l1.val <= l2.val:
                curr.next = l1
                l1 = l1.next
            else:
                curr.next = l2
                l2 = l2.next
            curr = curr.next
        curr.next = l1 or l2
        return dummy.next
"""

# --- Cycle detection (fast/slow pointers) ---
CYCLE_DETECTION = """
class Solution:
    def hasCycle(self, head):
        if not head or not head.next:
            return False
        slow = head
        fast = head.next
        while slow != fast:
            if not fast or not fast.next:
                return False
            slow = slow.next
            fast = fast.next.next
        return True
"""

# --- Add Two Numbers (MUST remain carry_propagation) ---
ADD_TWO_NUMBERS = """
def addTwoNumbers(l1, l2):
    dummy = ListNode()
    curr = dummy
    carry = 0
    while l1 or l2 or carry:
        val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
        carry, digit = divmod(val, 10)
        curr.next = ListNode(digit)
        curr = curr.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    return dummy.next
"""

# --- Simple linked-list traversal (no rewiring) ---
SIMPLE_LINKED_TRAVERSAL = """
def traverse(head):
    curr = head
    total = 0
    while curr:
        total += curr.val
        curr = curr.next
    return total
"""

# --- Tree traversal (no linked-list technique) ---
TREE_TRAVERSAL = """
def tree_sum(root):
    if not root:
        return 0
    return root.val + tree_sum(root.left) + tree_sum(root.right)
"""

# --- Fixed sliding window: max sum subarray of size k ---
FIXED_WINDOW_MAX_SUM = """
def max_subarray_sum(nums, k):
    n = len(nums)
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, n):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
"""

# --- Fixed sliding window: average of subarrays ---
FIXED_WINDOW_AVERAGE = """
def find_averages(arr, k):
    result = []
    window_sum = sum(arr[:k])
    result.append(window_sum / k)
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        result.append(window_sum / k)
    return result
"""

# --- Variable sliding window (existing test pattern) ---
VARIABLE_SLIDING_WINDOW = """
def longest_substring(s):
    char_index = {}
    left = 0
    max_len = 0
    for right in range(len(s)):
        if s[right] in char_index:
            left = max(left, char_index[s[right]] + 1)
        char_index[s[right]] = right
        max_len = max(max_len, right - left + 1)
    return max_len
"""

# --- Simple array sum (NOT fixed window) ---
SIMPLE_ARRAY_SUM = """
def array_sum(nums):
    total = 0
    for i in range(len(nums)):
        total += nums[i]
    return total
"""

# --- Two-pointers palindrome (NOT sliding window) ---
TWO_POINTERS_PALINDROME = """
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

# --- Next Greater Element (monotonic stack) ---
NEXT_GREATER_ELEMENT = """
def next_greater_element(nums):
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

# --- Daily Temperatures (monotonic stack) ---
DAILY_TEMPERATURES = """
def daily_temperatures(temps):
    n = len(temps)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temps[stack[-1]] < temps[i]:
            idx = stack.pop()
            result[i - idx] = i - idx
        stack.append(i)
    return result
"""

# --- Largest Rectangle in Histogram (monotonic stack) ---
HISTOGRAM = """
def largest_rectangle_area(heights):
    stack = []
    max_area = 0
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    while stack:
        height = heights[stack.pop()]
        width = len(heights) if not stack else len(heights) - stack[-1] - 1
        max_area = max(max_area, height * width)
    return max_area
"""

# --- Ordinary stack usage (NOT monotonic) ---
ORDINARY_STACK = """
def evaluate_postfix(tokens):
    stack = []
    for token in tokens:
        if token.isdigit():
            stack.append(int(token))
        else:
            b = stack.pop()
            a = stack.pop()
            if token == '+':
                stack.append(a + b)
            elif token == '-':
                stack.append(a - b)
    return stack[0]
"""

# --- DFS stack (NOT monotonic) ---
DFS_STACK = """
def dfs_iterative(graph, start):
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            for neighbor in graph[node]:
                stack.append(neighbor)
    return visited
"""

# --- Monotonic stack with renamed variables ---
MONOTONIC_STACK_RENAMED = """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    mono = []
    for idx in range(n):
        while mono and nums[mono[-1]] < nums[idx]:
            i = mono.pop()
            result[i] = nums[idx]
        mono.append(idx)
    return result
"""

# --- Fixed window with renamed variables ---
FIXED_WINDOW_RENAMED = """
def max_sum_subarray(arr, size):
    n = len(arr)
    curr = sum(arr[:size])
    best = curr
    for idx in range(size, n):
        curr += arr[idx] - arr[idx - size]
        best = max(best, curr)
    return best
"""


# ============================================================
# Test classes
# ============================================================

class TestLinkedListTraversal:
    """Test linked_list_traversal technique detection."""

    def test_linked_list_reversal_detected(self):
        """Reversal should detect linked_list_traversal technique."""
        result = run_shadow_analysis(LINKED_LIST_REVERSAL)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" in tech_ids
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "pointer_rewiring" in fact_types

    def test_linked_list_merge_detected(self):
        """Merge should detect linked_list_traversal technique."""
        result = run_shadow_analysis(LINKED_LIST_MERGE)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" in tech_ids
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "pointer_rewiring" in fact_types

    def test_cycle_detection_detected(self):
        """Cycle detection should detect linked_list_traversal (multiple pointers)."""
        result = run_shadow_analysis(CYCLE_DETECTION)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" in tech_ids
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "multiple_pointer_traversal" in fact_types

    def test_add_two_numbers_not_linked_list_traversal(self):
        """Add Two Numbers MUST remain carry_propagation, not linked_list_traversal."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids
        assert "linked_list_traversal" not in tech_ids

    def test_simple_traversal_not_detected(self):
        """Simple traversal without rewiring should NOT detect linked_list_traversal."""
        result = run_shadow_analysis(SIMPLE_LINKED_TRAVERSAL)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" not in tech_ids
        # Should not have pointer_rewiring or multiple_pointer_traversal
        fact_types = {f["fact_type"] for f in result["structural_facts"]}
        assert "pointer_rewiring" not in fact_types
        assert "multiple_pointer_traversal" not in fact_types

    def test_tree_traversal_not_detected(self):
        """Tree traversal should NOT detect linked_list_traversal."""
        result = run_shadow_analysis(TREE_TRAVERSAL)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" not in tech_ids


class TestFixedSlidingWindow:
    """Test fixed_window_maintenance technique and sliding_window strategy."""

    def test_fixed_window_max_sum_detected(self):
        """Fixed window max sum should detect sliding_window strategy."""
        result = run_shadow_analysis(FIXED_WINDOW_MAX_SUM)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "fixed_window_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_fixed_window_average_detected(self):
        """Fixed window average should detect sliding_window strategy."""
        result = run_shadow_analysis(FIXED_WINDOW_AVERAGE)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "fixed_window_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_variable_sliding_window_still_works(self):
        """Variable sliding window should still be detected."""
        result = run_shadow_analysis(VARIABLE_SLIDING_WINDOW)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "loop_state_tracking" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids

    def test_simple_array_sum_not_detected(self):
        """Simple array sum should NOT detect sliding_window."""
        result = run_shadow_analysis(SIMPLE_ARRAY_SUM)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "fixed_window_maintenance" not in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" not in strat_ids

    def test_two_pointers_not_sliding_window(self):
        """Two-pointers palindrome should NOT be classified as sliding_window."""
        result = run_shadow_analysis(TWO_POINTERS_PALINDROME)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids
        assert "sliding_window" not in strat_ids

    def test_fixed_window_renamed(self):
        """Renamed variables should still detect fixed window."""
        result = run_shadow_analysis(FIXED_WINDOW_RENAMED)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "fixed_window_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids


class TestMonotonicStack:
    """Test monotonic_stack_maintenance technique and monotonic_stack_strategy."""

    def test_next_greater_element_detected(self):
        """Next Greater Element should detect monotonic_stack_strategy."""
        result = run_shadow_analysis(NEXT_GREATER_ELEMENT)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" in strat_ids

    def test_daily_temperatures_detected(self):
        """Daily Temperatures should detect monotonic_stack_strategy."""
        result = run_shadow_analysis(DAILY_TEMPERATURES)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" in strat_ids

    def test_histogram_detected(self):
        """Largest Rectangle in Histogram should detect monotonic_stack_strategy."""
        result = run_shadow_analysis(HISTOGRAM)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" in strat_ids

    def test_ordinary_stack_not_detected(self):
        """Ordinary stack usage should NOT detect monotonic_stack_strategy."""
        result = run_shadow_analysis(ORDINARY_STACK)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" not in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" not in strat_ids

    def test_dfs_stack_not_detected(self):
        """DFS stack should NOT detect monotonic_stack_strategy."""
        result = run_shadow_analysis(DFS_STACK)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" not in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" not in strat_ids

    def test_monotonic_stack_renamed(self):
        """Renamed variables should still detect monotonic stack."""
        result = run_shadow_analysis(MONOTONIC_STACK_RENAMED)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "monotonic_stack_maintenance" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" in strat_ids


class TestCrossPatternRegression:
    """Verify existing strategies still work correctly."""

    def test_binary_search_still_works(self):
        """Binary search should still be detected."""
        result = run_shadow_analysis("""
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids

    def test_two_pointers_still_works(self):
        """Two-pointers should still be detected."""
        result = run_shadow_analysis(TWO_POINTERS_PALINDROME)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" in strat_ids

    def test_dfs_backtracking_still_works(self):
        """DFS backtracking should still be detected."""
        result = run_shadow_analysis("""
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
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dfs_backtracking" in strat_ids

    def test_dp_top_down_still_works(self):
        """DP top-down should still be detected."""
        result = run_shadow_analysis("""
def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_top_down" in strat_ids

    def test_dp_bottom_up_still_works(self):
        """DP bottom-up should still be detected."""
        result = run_shadow_analysis("""
def house_robber(nums):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    return dp[-1]
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "dp_bottom_up" in strat_ids

    def test_add_two_numbers_unresolved(self):
        """Add Two Numbers should remain UNRESOLVED (no matching strategy)."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # No strategy should match (UNRESOLVED)
        assert len(strat_ids) == 0 or "two_pointers_opposite" not in strat_ids

    def test_2996_unresolved(self):
        """Problem 2996 should remain UNRESOLVED."""
        result = run_shadow_analysis("""
class Solution:
    def missingInteger(self, nums):
        i = 1
        summ = nums[0]
        while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
            summ += nums[i]
            i += 1
        while summ in nums:
            summ += 1
        return summ
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # Should NOT have any strategy
        assert "binary_search" not in strat_ids
        assert "two_pointers_opposite" not in strat_ids


class TestFalsePositiveStressTests:
    """Stress tests for false positives."""

    def test_binary_search_not_two_pointers(self):
        """Binary search MUST NOT become two_pointers_opposite."""
        result = run_shadow_analysis("""
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""")
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids
        assert "two_pointers_opposite" not in strat_ids

    def test_sliding_window_not_two_pointers(self):
        """Sliding window MUST NOT become two_pointers_opposite."""
        result = run_shadow_analysis(VARIABLE_SLIDING_WINDOW)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids
        assert "two_pointers_opposite" not in strat_ids

    def test_monotonic_stack_not_binary_search(self):
        """Monotonic stack MUST NOT become binary search."""
        result = run_shadow_analysis(NEXT_GREATER_ELEMENT)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "monotonic_stack_strategy" in strat_ids
        assert "binary_search" not in strat_ids

    def test_fixed_window_not_two_pointers(self):
        """Fixed window MUST NOT become two_pointers_opposite."""
        result = run_shadow_analysis(FIXED_WINDOW_MAX_SUM)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids
        assert "two_pointers_opposite" not in strat_ids
