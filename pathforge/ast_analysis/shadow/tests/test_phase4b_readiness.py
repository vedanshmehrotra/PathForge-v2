"""Phase 4B readiness evaluation — comprehensive stress tests.

Tests:
- Solution-group semantic validation (valid + invalid combinations)
- Legacy-pattern coverage
- Disjoint evaluation corpus
- Critical user-safety cases
- Circularity checks
"""
import pytest

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.services.ground_truth_builder import (
    _validate_group, validate_solution_groups, PATTERN_TO_V1_MAPPING,
)
import ast


# ============================================================
# Test code samples — comprehensive corpus
# ============================================================

# Binary Search
BINARY_SEARCH_STANDARD = """
def binary_search(nums, target):
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

# Two Pointers
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

TWO_POINTERS_CONTAINER = """
def max_area(height):
    left, right = 0, len(height) - 1
    max_water = 0
    while left < right:
        water = min(height[left], height[right]) * (right - left)
        max_water = max(max_water, water)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_water
"""

# Sliding Window
SLIDING_WINDOW_FIXED = """
def max_subarray_sum(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
"""

SLIDING_WINDOW_VARIABLE = """
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

# DFS / Backtracking
DFS_TREE = """
def tree_sum(node):
    if node is None:
        return 0
    return node.val + tree_sum(node.left) + tree_sum(node.right)
"""

BACKTRACKING_SUBSETS = """
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

# DP
DP_BOTTOM_UP_HOUSE_ROBBER = """
def rob(nums):
    if not nums: return 0
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    return dp[-1]
"""

DP_TOP_DOWN_FIB = """
def fib(n, memo={}):
    if n <= 1: return n
    if n in memo: return memo[n]
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
"""

# BFS
BFS_GRAPH = """
from collections import deque
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited
"""

# Union-Find
UNION_FIND = """
def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(parent, rank, x, y):
    px, py = find(parent, x), find(parent, y)
    if px == py: return
    if rank[px] < rank[py]: px, py = py, px
    parent[py] = px
    if rank[px] == rank[py]: rank[px] += 1
"""

# Linked List
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

# Problem 2996
PROBLEM_2996 = """
def missingInteger(nums):
    i = 1
    summ = nums[0]
    while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
        summ += nums[i]
        i += 1
    while summ in nums:
        summ += 1
    return summ
"""

# Heap / Greedy
HEAP_TOP_K = """
import heapq
def top_k(nums, k):
    return heapq.nlargest(k, nums)
"""

GREEDY_INTERVAL = """
def erase_overlap_intervals(intervals):
    intervals.sort(key=lambda x: x[1])
    count = 0
    prev_end = float('-inf')
    for start, end in intervals:
        if start >= prev_end:
            count += 1
            prev_end = end
    return count
"""

# Prefix Sum
PREFIX_SUM = """
def prefix_sum(nums):
    prefix = [0] * (len(nums) + 1)
    for i in range(len(nums)):
        prefix[i + 1] = prefix[i] + nums[i]
    return prefix
"""

# Monotonic Stack
MONOTONIC_STACK = """
def daily_temperatures(temps):
    result = [0] * len(temps)
    stack = []
    for i, t in enumerate(temps):
        while stack and temps[stack[-1]] < t:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)
    return result
"""


# ============================================================
# 1. Solution-group semantic validation
# ============================================================

class TestSemanticValidation:
    """Test valid and invalid solution-group combinations."""

    def test_valid_binary_search_group(self):
        """Binary search group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["binary_search"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_two_pointers_group(self):
        """Two-pointers group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["two_pointers_opposite"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_sliding_window_group(self):
        """Sliding window group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_dfs_backtracking_group(self):
        """DFS backtracking group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["dfs_backtracking"],
            "optional": ["recursive_branching"],
            "excluded": ["dp_top_down"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_dp_top_down_group(self):
        """DP top-down group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["dp_top_down"],
            "optional": ["recursive_branching"],
            "excluded": ["dfs_backtracking"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_dp_bottom_up_group(self):
        """DP bottom-up group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["dp_bottom_up"],
            "optional": ["iterative_table_filling"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_bfs_group(self):
        """BFS group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["bfs_shortest_path"],
            "optional": ["loop_state_tracking"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_union_find_group(self):
        """Union-find group is semantically valid."""
        group = {
            "id": "group_0",
            "required": ["union_find"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_valid_carry_propagation_group(self):
        """Carry propagation group (Add Two Numbers) is valid."""
        group = {
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"], f"Should be valid: {result['reason']}"

    def test_invalid_binary_search_plus_sliding_window(self):
        """binary_search + sliding_window as both required is questionable.

        These are distinct strategies that rarely coexist in the same solution.
        The validator accepts them as valid because they are both valid V1 concepts.
        The semantic incoherence is a limitation of the current validator.
        """
        group = {
            "id": "group_0",
            "required": ["binary_search", "sliding_window"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        # Current validator: ACCEPTED (both are valid V1 concepts)
        # This is a known limitation — no semantic coherence check
        assert result["valid"], f"Current validator accepts: {result['reason']}"

    def test_invalid_dfs_backtracking_plus_dp_top_down(self):
        """dfs_backtracking + dp_top_down as both required is contradictory.

        Phase 5B: These are now detected as mutually exclusive.
        DFS backtracking excludes dp_top_down (no memoization).
        DP top-down excludes dfs_backtracking (has memoization).
        Both cannot be satisfied simultaneously.
        """
        group = {
            "id": "group_0",
            "required": ["dfs_backtracking", "dp_top_down"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        # Phase 5B: validator now rejects mutually exclusive strategies
        assert not result["valid"], f"Expected rejection, got: {result['reason']}"
        assert "mutually exclusive" in result["reason"]

    def test_invalid_bfs_plus_two_pointers(self):
        """BFS + two_pointers_opposite as both required is unusual.

        These strategies are rarely combined in the same solution.
        The validator accepts them because both are valid V1 concepts.
        """
        group = {
            "id": "group_0",
            "required": ["bfs_shortest_path", "two_pointers_opposite"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        # Current validator: ACCEPTED
        assert result["valid"], f"Current validator accepts: {result['reason']}"


# ============================================================
# 2. Disjoint evaluation corpus
# ============================================================

class TestDisjointEvaluationCorpus:
    """Test a comprehensive corpus of real solutions."""

    def _test_solution(self, code, expected_strategies, unexpected_strategies,
                       group=None, expected_outcome=None):
        """Helper to test a solution against expected strategies."""
        result = run_shadow_analysis(code, solution_groups=group)
        assert result is not None, f"Shadow analysis failed for code"

        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}

        for strategy in expected_strategies:
            assert strategy in strat_ids, \
                f"Expected strategy '{strategy}' not found. Got: {strat_ids}"
        for strategy in unexpected_strategies:
            assert strategy not in strat_ids, \
                f"Unexpected strategy '{strategy}' found. Got: {strat_ids}"

        if expected_outcome is not None:
            assert result["match_outcome"]["outcome"] == expected_outcome, \
                f"Expected outcome '{expected_outcome}', got '{result['match_outcome']['outcome']}'"

        return result

    def test_binary_search_detection(self):
        """Binary search: detected correctly."""
        self._test_solution(
            BINARY_SEARCH_STANDARD,
            expected_strategies=["binary_search"],
            unexpected_strategies=["two_pointers_opposite", "sliding_window"],
        )

    def test_two_pointers_palindrome_detection(self):
        """Two-pointers palindrome: detected correctly."""
        self._test_solution(
            TWO_POINTERS_PALINDROME,
            expected_strategies=["two_pointers_opposite"],
            unexpected_strategies=["binary_search", "sliding_window"],
        )

    def test_two_pointers_container_detection(self):
        """Two-pointers container: detected correctly."""
        self._test_solution(
            TWO_POINTERS_CONTAINER,
            expected_strategies=["two_pointers_opposite"],
            unexpected_strategies=["binary_search", "sliding_window"],
        )

    def test_sliding_window_fixed_detection(self):
        """Sliding window fixed: does NOT trigger sliding_window strategy.

        Fixed-size sliding windows lack conditional boundary updates
        (the left boundary doesn't move conditionally). This is a known
        V1 limitation — the sliding_window strategy requires
        loop_state_tracking which needs conditional_index_update.
        """
        result = run_shadow_analysis(SLIDING_WINDOW_FIXED)
        assert result is not None
        # Fixed sliding window has accumulator_update + index_lookback
        # but no conditional_index_update → no loop_state_tracking
        # → no sliding_window strategy
        # This is correct structural behavior
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids
        assert "binary_search" not in strat_ids

    def test_sliding_window_variable_detection(self):
        """Sliding window variable: detected correctly."""
        self._test_solution(
            SLIDING_WINDOW_VARIABLE,
            expected_strategies=["sliding_window"],
            unexpected_strategies=["two_pointers_opposite", "binary_search"],
        )

    def test_dfs_tree_detection(self):
        """DFS tree recursion: recursive_branching detected."""
        result = run_shadow_analysis(DFS_TREE)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "recursive_branching" in tech_ids

    def test_backtracking_detection(self):
        """Backtracking subsets: dfs_backtracking detected."""
        self._test_solution(
            BACKTRACKING_SUBSETS,
            expected_strategies=["dfs_backtracking"],
            unexpected_strategies=["dp_top_down"],
        )

    def test_dp_bottom_up_detection(self):
        """DP bottom-up (House Robber): detected correctly."""
        self._test_solution(
            DP_BOTTOM_UP_HOUSE_ROBBER,
            expected_strategies=["dp_bottom_up"],
            unexpected_strategies=["dp_top_down", "recursive_branching"],
        )

    def test_dp_top_down_detection(self):
        """DP top-down (Fibonacci memo): detected correctly."""
        self._test_solution(
            DP_TOP_DOWN_FIB,
            expected_strategies=["dp_top_down"],
            unexpected_strategies=["dfs_backtracking", "dp_bottom_up"],
        )

    def test_bfs_detection(self):
        """BFS graph traversal: detected correctly."""
        self._test_solution(
            BFS_GRAPH,
            expected_strategies=["bfs_shortest_path"],
            unexpected_strategies=["dfs_backtracking", "recursive_branching"],
        )

    def test_union_find_detection(self):
        """Union-find: detected correctly."""
        self._test_solution(
            UNION_FIND,
            expected_strategies=["union_find"],
            unexpected_strategies=["binary_search"],
        )

    def test_add_two_numbers_no_strategy(self):
        """Add Two Numbers: no named strategy, carry_propagation technique."""
        result = run_shadow_analysis(ADD_TWO_NUMBERS)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "carry_propagation" in tech_ids
        assert len(strat_ids) == 0, f"Should have no strategies, got: {strat_ids}"
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_problem_2996_unresolved(self):
        """Problem 2996: UNRESOLVED, no fake strategies."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sequential_accumulation" in tech_ids
        assert "hash_map" not in strat_ids
        assert "binary_search" not in strat_ids
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_heap_top_k_no_strategy(self):
        """Heap top-k: no V1 strategy detected."""
        result = run_shadow_analysis(HEAP_TOP_K)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # heapq.nlargest is a library call, not structural
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_greedy_interval_no_strategy(self):
        """Greedy interval: no V1 strategy detected."""
        result = run_shadow_analysis(GREEDY_INTERVAL)
        assert result is not None
        # Greedy interval doesn't match any V1 strategy
        # (no technique fires that would trigger a strategy)
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_prefix_sum_no_strategy(self):
        """Prefix sum: iterative_table_filling detected, but no named strategy."""
        result = run_shadow_analysis(PREFIX_SUM)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        # Prefix sum has indexed_write + index_lookback → iterative_table_filling
        # But dp_bottom_up is the strategy that uses it
        # Since it's a simple prefix sum, dp_bottom_up may or may not fire
        # The important thing is no false strategies
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "two_pointers_opposite" not in strat_ids
        assert "binary_search" not in strat_ids

    def test_monotonic_stack_no_strategy(self):
        """Monotonic stack: no V1 strategy detected."""
        result = run_shadow_analysis(MONOTONIC_STACK)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # Monotonic stack has no direct V1 strategy
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"


# ============================================================
# 3. Critical user-safety cases
# ============================================================

class TestUserSafetyCases:
    """Test critical user-safety scenarios."""

    def test_correct_solution_wrong_ground_truth(self):
        """Correct solution + wrong ground truth → UNRESOLVED, not false contradiction."""
        # Binary search solution with wrong ground truth (two-pointers group)
        groups = [{
            "id": "group_0",
            "required": ["two_pointers_opposite"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(BINARY_SEARCH_STANDARD, solution_groups=groups)
        assert result is not None
        # Binary search has midpoint → two_pointers_opposite not detected
        # Group not satisfied → UNRESOLVED (not CONTRADICTED)
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_correct_solution_incomplete_ground_truth(self):
        """Correct solution + incomplete ground truth → UNRESOLVED."""
        # Binary search with no matching group
        groups = [{
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(BINARY_SEARCH_STANDARD, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_incorrect_solution_low_authority_no_punishment(self):
        """Incorrect solution + low-authority ground truth → no punitive contradiction."""
        # Wrong code (random) with authoritative ground truth
        wrong_code = """
def wrong():
    return 42
"""
        groups = [{
            "id": "group_0",
            "required": ["binary_search"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(wrong_code, solution_groups=groups)
        assert result is not None
        # No binary_search detected → group not satisfied → UNRESOLVED
        # Even with llm_proposed authority, CONTRADICTED would be downgraded
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_group_a_satisfied_group_b_not(self):
        """Group A satisfied, Group B not → CONFIRMED (Group A wins)."""
        groups = [
            {
                "id": "group_0",
                "required": ["binary_search"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
            {
                "id": "group_1",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(BINARY_SEARCH_STANDARD, solution_groups=groups)
        assert result is not None
        # binary_search detected → group_0 satisfied
        # carry_propagation NOT detected → group_1 not satisfied
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_multiple_valid_approaches(self):
        """Submission matches Group A, not Group B → CONFIRMED if authority permits."""
        # Palindrome matches two_pointers but not binary_search
        groups = [
            {
                "id": "group_0",
                "required": ["two_pointers_opposite"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
            {
                "id": "group_1",
                "required": ["binary_search"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(TWO_POINTERS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"


# ============================================================
# 4. Circularity check
# ============================================================

class TestCircularityCheck:
    """Verify no circular promotion occurs."""

    def test_submission_does_not_promote_group(self):
        """User submission does not automatically promote its matching group."""
        # This is a design-level check — the implementation does not
        # contain any logic that promotes groups based on submissions.
        # The ground truth builder stores groups independently of submissions.

        # Verify that run_shadow_analysis does not modify any global state
        result1 = run_shadow_analysis(BINARY_SEARCH_STANDARD)
        result2 = run_shadow_analysis(BINARY_SEARCH_STANDARD)

        # Same code produces same results (no state mutation)
        assert result1["match_outcome"]["outcome"] == result2["match_outcome"]["outcome"]
        assert len(result1["structural_facts"]) == len(result2["structural_facts"])

    def test_no_auto_promotion_in_persistence(self):
        """Persistence module does not promote groups."""
        from pathforge.ast_analysis.shadow.persistence import rerun_derivation

        # Re-derivation from facts does not modify group authority
        facts = extract_structural_facts(ast.parse(BINARY_SEARCH_STANDARD))
        rerun = rerun_derivation(facts)

        # Outcome is derived from facts, not from any promotion logic
        assert rerun["match_outcome"]["outcome"] == "UNRESOLVED"


# ============================================================
# 5. Coverage metrics
# ============================================================

class TestCoverageMetrics:
    """Measure coverage across the evaluation corpus."""

    def test_all_eight_strategies_have_positive_detection(self):
        """Each V1 strategy has at least one code sample that detects it."""
        test_cases = {
            "binary_search": BINARY_SEARCH_STANDARD,
            "two_pointers_opposite": TWO_POINTERS_PALINDROME,
            "sliding_window": SLIDING_WINDOW_VARIABLE,
            "dfs_backtracking": BACKTRACKING_SUBSETS,
            "dp_top_down": DP_TOP_DOWN_FIB,
            "dp_bottom_up": DP_BOTTOM_UP_HOUSE_ROBBER,
            "bfs_shortest_path": BFS_GRAPH,
            "union_find": UNION_FIND,
        }

        for strategy, code in test_cases.items():
            result = run_shadow_analysis(code)
            assert result is not None, f"Failed for {strategy}"
            strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
            assert strategy in strat_ids, \
                f"Strategy '{strategy}' not detected. Got: {strat_ids}"

    def test_no_false_positive_strategies(self):
        """No code sample produces a strategy it shouldn't."""
        false_positive_cases = {
            "binary_search": {
                "code": TWO_POINTERS_PALINDROME,
                "should_not_have": ["binary_search"],
            },
            "two_pointers_opposite": {
                "code": BINARY_SEARCH_STANDARD,
                "should_not_have": ["two_pointers_opposite"],
            },
            "sliding_window": {
                "code": TWO_POINTERS_PALINDROME,
                "should_not_have": ["sliding_window"],
            },
            "dp_top_down": {
                "code": BACKTRACKING_SUBSETS,
                "should_not_have": ["dp_top_down"],
            },
            "dfs_backtracking": {
                "code": DP_TOP_DOWN_FIB,
                "should_not_have": ["dfs_backtracking"],
            },
            "bfs_shortest_path": {
                "code": DFS_TREE,
                "should_not_have": ["bfs_shortest_path"],
            },
        }

        for name, case in false_positive_cases.items():
            result = run_shadow_analysis(case["code"])
            assert result is not None
            strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
            for false_strat in case["should_not_have"]:
                assert false_strat not in strat_ids, \
                    f"False positive: '{false_strat}' detected in {name} test"

    def test_unmapped_patterns_produce_unresolved(self):
        """Patterns with no V1 representation produce UNRESOLVED."""
        unmapped_codes = [
            ("hash_map", "def count(arr):\n    d = {}\n    for x in arr:\n        d[x] = d.get(x, 0) + 1\n    return d"),
            ("monotonic_stack", MONOTONIC_STACK),
            ("heap", HEAP_TOP_K),
        ]

        for name, code in unmapped_codes:
            result = run_shadow_analysis(code)
            assert result is not None, f"Failed for {name}"
            assert result["match_outcome"]["outcome"] == "UNRESOLVED", \
                f"{name} should be UNRESOLVED, got {result['match_outcome']['outcome']}"
