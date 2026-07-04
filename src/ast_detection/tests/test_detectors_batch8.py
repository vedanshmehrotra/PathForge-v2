"""Tests for detector implementations in Batch 8 (DP detectors)."""

import ast
from src.ast_detection.detectors.dp_1d_forward import DP1DForwardDetector
from src.ast_detection.detectors.dp_state_machine import DPStateMachineDetector
from src.ast_detection.detectors.dp_1d_sequence import DP1DSequenceDetector
from src.ast_detection.detectors.dp_2d_grid import DP2DGridDetector
from src.ast_detection.detectors.dp_2d_string import DP2DStringDetector
from src.ast_detection.detectors.dp_knapsack import DPKnapsackDetector
from src.ast_detection.detectors.dp_interval import DPIntervalDetector
from src.ast_detection.detector_interface import DetectionResult


class TestDP1DForwardDetector:
    def setup_method(self):
        self.detector = DP1DForwardDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_1d_forward"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_prefix_sum(self):
        code = """
def prefix_sum(nums):
    n = len(nums)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        dp[i] = dp[i - 1] + nums[i - 1]
    return dp[n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_simple_loop(self):
        code = """
def total(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_climbing_stairs_tabulation(self):
        code = """
def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "index_lookback" for e in result.evidence)
        assert any(e.type == "dp_array_1d" for e in result.evidence)
        assert any(e.type == "table_fill_loop" for e in result.evidence)

    def test_detected_house_robber(self):
        code = """
def rob(nums):
    n = len(nums)
    if n == 0:
        return 0
    if n == 1:
        return nums[0]
    dp = [0] * n
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, n):
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])
    return dp[n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "index_lookback" for e in result.evidence)
        assert any(e.type == "recurrence_expression" for e in result.evidence)

    def test_detected_fibonacci_memoized(self):
        code = """
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "cache_decorator" for e in result.evidence)
        assert any(e.type in ("index_lookback", "recursive_lookback") for e in result.evidence)

    def test_detected_fibonacci_cache(self):
        code = """
from functools import cache

@cache
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "cache_decorator" for e in result.evidence)

    def test_detected_min_cost_climbing(self):
        code = """
def minCostClimbingStairs(cost):
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i - 1] + cost[i - 1], dp[i - 2] + cost[i - 2])
    return dp[n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDPStateMachineDetector:
    def setup_method(self):
        self.detector = DPStateMachineDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_state_machine"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_greedy_buy_sell(self):
        code = """
def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    for price in prices:
        if price < min_price:
            min_price = price
        elif price - min_price > max_profit:
            max_profit = price - min_price
    return max_profit
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_simple_loop(self):
        code = """
def sum_list(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_stock_with_cooldown(self):
        code = """
def maxProfit(prices):
    if not prices:
        return 0
    n = len(prices)
    hold = [0] * n
    sold = [0] * n
    rest = [0] * n
    hold[0] = -prices[0]
    sold[0] = 0
    rest[0] = 0
    for i in range(1, n):
        hold[i] = max(hold[i - 1], rest[i - 1] - prices[i])
        sold[i] = hold[i - 1] + prices[i]
        rest[i] = max(rest[i - 1], sold[i - 1])
    return max(hold[n - 1], sold[n - 1], rest[n - 1])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "state_variables" for e in result.evidence)
        assert any(e.type == "state_transition" for e in result.evidence)

    def test_detected_house_robber_state(self):
        code = """
def rob(nums):
    prev0 = 0
    prev1 = 0
    for num in nums:
        curr0 = max(prev0, prev1)
        curr1 = prev0 + num
        prev0, prev1 = curr0, curr1
    return max(prev0, prev1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "state_variables" for e in result.evidence)
        assert any(e.type == "state_transition" for e in result.evidence)

    def test_detected_house_robber_optimized(self):
        code = """
def rob(nums):
    prev_max = 0
    curr_max = 0
    for num in nums:
        temp = curr_max
        curr_max = max(prev_max + num, curr_max)
        prev_max = temp
    return curr_max
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_paint_house(self):
        code = """
def minCost(costs):
    n = len(costs)
    dp = [[0] * 3 for _ in range(n)]
    dp[0] = costs[0]
    for i in range(1, n):
        dp[i][0] = costs[i][0] + min(dp[i - 1][1], dp[i - 1][2])
        dp[i][1] = costs[i][1] + min(dp[i - 1][0], dp[i - 1][2])
        dp[i][2] = costs[i][2] + min(dp[i - 1][0], dp[i - 1][1])
    return min(dp[n - 1])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDP1DSequenceDetector:
    def setup_method(self):
        self.detector = DP1DSequenceDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_1d_sequence"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_single_loop(self):
        code = """
def sum_nums(nums):
    total = 0
    for i in range(len(nums)):
        total += nums[i]
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_brute_force_pairs(self):
        code = """
def count_pairs(nums):
    count = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] > nums[j]:
                count += 1
    return count
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_lis_tabulation(self):
        code = """
def lengthOfLIS(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if nums[i] > nums[j]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "nested_fill_loops" for e in result.evidence)
        assert any(e.type == "inner_lookback" for e in result.evidence)
        assert any(e.type == "result_aggregation" for e in result.evidence)

    def test_detected_russian_doll(self):
        code = """
def maxEnvelopes(envelopes):
    envelopes.sort(key=lambda x: (x[0], -x[1]))
    n = len(envelopes)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if envelopes[j][1] < envelopes[i][1]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "nested_fill_loops" for e in result.evidence)
        assert any(e.type == "recurrence_expression" for e in result.evidence)

    def test_detected_sequence_partition(self):
        code = """
def minCost(nums):
    n = len(nums)
    dp = [float('inf')] * n
    for i in range(n):
        for j in range(i + 1):
            cost = abs(nums[i] - nums[j])
            if j == 0:
                dp[i] = min(dp[i], cost)
            else:
                dp[i] = min(dp[i], dp[j - 1] + cost)
    return dp[n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDP2DGridDetector:
    def setup_method(self):
        self.detector = DP2DGridDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_2d_grid"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_simple_nested_loops(self):
        code = """
def print_matrix(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            print(matrix[i][j])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_min_path_sum(self):
        code = """
def minPathSum(grid):
    m = len(grid)
    n = len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "grid_lookback" for e in result.evidence)
        assert any(e.type == "nested_fill_loops" for e in result.evidence)
        assert any(e.type == "dp_array_2d" for e in result.evidence)

    def test_detected_unique_paths(self):
        code = """
def uniquePaths(m, n):
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m - 1][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "grid_lookback" for e in result.evidence)
        assert any(e.type == "nested_fill_loops" for e in result.evidence)

    def test_detected_maximal_square(self):
        code = """
def maximalSquare(matrix):
    m = len(matrix)
    n = len(matrix[0])
    dp = [[0] * n for _ in range(m)]
    max_side = 0
    for i in range(m):
        for j in range(n):
            if matrix[i][j] == '1':
                if i == 0 or j == 0:
                    dp[i][j] = 1
                else:
                    dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
                max_side = max(max_side, dp[i][j])
    return max_side * max_side
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDP2DStringDetector:
    def setup_method(self):
        self.detector = DP2DStringDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_2d_string"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_grid_dp(self):
        code = """
def minPathSum(grid):
    m = len(grid)
    n = len(grid[0])
    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            if i == 0 and j == 0:
                dp[i][j] = grid[i][j]
            elif i == 0:
                dp[i][j] = dp[i][j - 1] + grid[i][j]
            elif j == 0:
                dp[i][j] = dp[i - 1][j] + grid[i][j]
            else:
                dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_longest_common_subsequence(self):
        code = """
def longestCommonSubsequence(text1, text2):
    m = len(text1)
    n = len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "string_compare" for e in result.evidence)
        assert any(e.type == "grid_lookback" for e in result.evidence)

    def test_detected_edit_distance(self):
        code = """
def minDistance(word1, word2):
    m = len(word1)
    n = len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
    return dp[m][n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "string_compare" for e in result.evidence)
        assert any(e.type == "grid_lookback" for e in result.evidence)

    def test_detected_distinct_subsequences(self):
        code = """
def numDistinct(s, t):
    m = len(s)
    n = len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = 1
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + dp[i - 1][j]
            else:
                dp[i][j] = dp[i - 1][j]
    return dp[m][n]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDPKnapsackDetector:
    def setup_method(self):
        self.detector = DPKnapsackDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_knapsack"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_grid_dp(self):
        code = """
def minPathSum(grid):
    m = len(grid)
    n = len(grid[0])
    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            if i == 0 and j == 0:
                dp[i][j] = grid[i][j]
            elif i == 0:
                dp[i][j] = dp[i][j - 1] + grid[i][j]
            else:
                dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_knapsack_01(self):
        code = """
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(1, capacity + 1):
            if w >= weights[i - 1]:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
            else:
                dp[i][w] = dp[i - 1][w]
    return dp[n][capacity]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "capacity_compare" for e in result.evidence)
        assert any(e.type == "max_min_recurrence" for e in result.evidence)

    def test_detected_partition_equal_subset_sum(self):
        code = """
def canPartition(nums):
    total = sum(nums)
    if total % 2 != 0:
        return False
    target = total // 2
    n = len(nums)
    dp = [[False] * (target + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = True
    for i in range(1, n + 1):
        for w in range(1, target + 1):
            if w >= nums[i - 1]:
                dp[i][w] = dp[i - 1][w] or dp[i - 1][w - nums[i - 1]]
            else:
                dp[i][w] = dp[i - 1][w]
    return dp[n][target]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_coin_change_knapsack(self):
        code = """
def coinChange(coins, amount):
    n = len(coins)
    dp = [[float('inf')] * (amount + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = 0
    for i in range(1, n + 1):
        for w in range(1, amount + 1):
            if w >= coins[i - 1]:
                dp[i][w] = min(dp[i - 1][w], dp[i][w - coins[i - 1]] + 1)
            else:
                dp[i][w] = dp[i - 1][w]
    return dp[n][amount] if dp[n][amount] != float('inf') else -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDPIntervalDetector:
    def setup_method(self):
        self.detector = DPIntervalDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dp_interval"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_empty(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_grid_dp(self):
        code = """
def minPathSum(grid):
    m = len(grid)
    n = len(grid[0])
    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_simple_nested_loops(self):
        code = """
def print_matrix(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            print(matrix[i][j])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_matrix_chain(self):
        code = """
def matrixChainOrder(p):
    n = len(p) - 1
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1]
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "length_based_loop" for e in result.evidence)
        assert any(e.type == "pair_loop" for e in result.evidence)
        assert any(e.type == "recurrence_expression" for e in result.evidence)

    def test_detected_palindrome_partitioning(self):
        code = """
def minCut(s):
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j] and (length <= 2 or dp[i + 1][j - 1] == 0):
                dp[i][j] = 0
            else:
                dp[i][j] = float('inf')
                for k in range(i, j):
                    dp[i][j] = min(dp[i][j], dp[i][k] + dp[k + 1][j] + 1)
    return dp[0][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "length_based_loop" for e in result.evidence)

    def test_detected_longest_palindromic_subsequence(self):
        code = """
def longestPalindromeSubseq(s):
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = 1
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                dp[i][j] = dp[i + 1][j - 1] + 2
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "length_based_loop" for e in result.evidence)
        assert any(e.type == "grid_lookback" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
