"""Tests for detector implementations in Batch 7 (Greedy & Backtracking)."""

import ast
from src.ast_detection.detectors.greedy_local import GreedyLocalDetector
from src.ast_detection.detectors.greedy_interval import GreedyIntervalDetector
from src.ast_detection.detectors.backtracking_subset import BacktrackingSubsetDetector
from src.ast_detection.detectors.backtracking_permutation import BacktrackingPermutationDetector
from src.ast_detection.detector_interface import DetectionResult


class TestGreedyLocalDetector:
    def setup_method(self):
        self.detector = GreedyLocalDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "greedy_local"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_greedy(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_ordinary_for_loop(self):
        code = """
def sum_list(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_plain_sorting(self):
        code = """
def sort_nums(nums):
    return sorted(nums)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_fibonacci(self):
        code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_max_subarray_kadane(self):
        code = """
def maxSubArray(nums):
    max_sum = nums[0]
    curr_sum = nums[0]
    for i in range(1, len(nums)):
        curr_sum = max(nums[i], curr_sum + nums[i])
        max_sum = max(max_sum, curr_sum)
    return max_sum
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "local_optimum_selection" for e in result.evidence)

    def test_detected_best_time_to_buy_sell(self):
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
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "local_optimum_selection" for e in result.evidence)

    def test_detected_jump_game(self):
        code = """
def canJump(nums):
    max_reach = 0
    for i in range(len(nums)):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + nums[i])
    return True
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "local_optimum_selection" for e in result.evidence)

    def test_detected_greedy_candy(self):
        code = """
def candy(ratings):
    n = len(ratings)
    candies = [1] * n
    for i in range(1, n):
        if ratings[i] > ratings[i - 1]:
            candies[i] = candies[i - 1] + 1
    for i in range(n - 2, -1, -1):
        if ratings[i] > ratings[i + 1]:
            candies[i] = max(candies[i], candies[i + 1] + 1)
    return sum(candies)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestGreedyIntervalDetector:
    def setup_method(self):
        self.detector = GreedyIntervalDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "greedy_interval"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_interval(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_ordinary_sorting(self):
        code = """
def sort_list(nums):
    nums.sort()
    return nums
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_plain_iteration(self):
        code = """
def iterate(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_sorting_without_intervals(self):
        code = """
def sort_by_age(people):
    return sorted(people, key=lambda p: p[1])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_merge_intervals(self):
        code = """
def merge(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = []
    for interval in intervals:
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1][1] = max(merged[-1][1], interval[1])
    return merged
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "interval_sorting" for e in result.evidence)
        assert any(e.type == "interval_comparison" for e in result.evidence)
        assert any(e.type == "interval_merge_scheduling" for e in result.evidence)

    def test_detected_non_overlapping_intervals(self):
        code = """
def eraseOverlapIntervals(intervals):
    intervals.sort(key=lambda x: x[1])
    count = 0
    end = float('-inf')
    for interval in intervals:
        if interval[0] >= end:
            end = interval[1]
        else:
            count += 1
    return count
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "interval_sorting" for e in result.evidence)
        assert any(e.type == "interval_comparison" for e in result.evidence)

    def test_detected_min_arrows_burst_balloons(self):
        code = """
def findMinArrowShots(points):
    points.sort(key=lambda x: x[1])
    arrows = 1
    end = points[0][1]
    for i in range(1, len(points)):
        if points[i][0] > end:
            arrows += 1
            end = points[i][1]
    return arrows
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "interval_sorting" for e in result.evidence)
        assert any(e.type == "interval_comparison" for e in result.evidence)

    def test_detected_insert_interval(self):
        code = """
def insert(intervals, newInterval):
    intervals.sort(key=lambda x: x[0])
    result = []
    i = 0
    while i < len(intervals) and intervals[i][1] < newInterval[0]:
        result.append(intervals[i])
        i += 1
    while i < len(intervals) and intervals[i][0] <= newInterval[1]:
        newInterval[0] = min(newInterval[0], intervals[i][0])
        newInterval[1] = max(newInterval[1], intervals[i][1])
        i += 1
    result.append(newInterval)
    while i < len(intervals):
        result.append(intervals[i])
        i += 1
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_leetcode_1288_canonical_editorial(self):
        code = """
def removeCoveredIntervals(intervals):
    intervals.sort(key=lambda x: (x[0], -x[1]))
    count = 0
    prev_end = 0
    for start, end in intervals:
        if start > prev_end:
            count += 1
            prev_end = end
    return count
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.55
        assert any(e.type == "interval_sorting" for e in result.evidence)
        assert any(e.type == "interval_comparison" for e in result.evidence)

    def test_detected_leetcode_1288_indexed_implementation(self):
        code = """
def removeCoveredIntervals(intervals):
    intervals.sort(key=lambda x: (x[0], -x[1]))
    count = 1
    prev_end = intervals[0][1]
    for i in range(1, len(intervals)):
        if intervals[i][0] > prev_end:
            count += 1
            prev_end = intervals[i][1]
    return count
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "interval_sorting" for e in result.evidence)
        assert any(e.type == "interval_comparison" for e in result.evidence)

    def test_not_detected_brute_force_interval(self):
        code = """
def removeCoveredIntervals(intervals):
    n = len(intervals)
    result = 0
    for i in range(n):
        covered = False
        for j in range(n):
            if i != j:
                a, b = intervals[i][0], intervals[i][1]
                c, d = intervals[j][0], intervals[j][1]
                if c <= a and b <= d:
                    covered = True
                    break
        if not covered:
            result += 1
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBacktrackingSubsetDetector:
    def setup_method(self):
        self.detector = BacktrackingSubsetDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "backtracking_subset"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_recursion(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_fibonacci(self):
        code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_factorial(self):
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_tree_dfs(self):
        code = """
def dfs(root):
    if not root:
        return
    print(root.val)
    dfs(root.left)
    dfs(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_subsets(self):
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
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "choose_recurse_unchoose" for e in result.evidence)

    def test_detected_combination_sum(self):
        code = """
def combinationSum(candidates, target):
    result = []
    def backtrack(remaining, path, start):
        if remaining == 0:
            result.append(path[:])
            return
        if remaining < 0:
            return
        for i in range(start, len(candidates)):
            path.append(candidates[i])
            backtrack(remaining - candidates[i], path, i)
            path.pop()
    backtrack(target, [], 0)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "choose_recurse_unchoose" for e in result.evidence)

    def test_detected_combinations(self):
        code = """
def combine(n, k):
    result = []
    def backtrack(start, path):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(start, n + 1):
            path.append(i)
            backtrack(i + 1, path)
            path.pop()
    backtrack(1, [])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_subset_ii(self):
        code = """
def subsetsWithDup(nums):
    nums.sort()
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i - 1]:
                continue
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_letter_combinations(self):
        code = """
def letterCombinations(digits):
    if not digits:
        return []
    phone = {'2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
             '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'}
    result = []
    def backtrack(index, path):
        if index == len(digits):
            result.append(''.join(path))
            return
        for letter in phone[digits[index]]:
            path.append(letter)
            backtrack(index + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBacktrackingPermutationDetector:
    def setup_method(self):
        self.detector = BacktrackingPermutationDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "backtracking_permutation"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_recursion(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_fibonacci(self):
        code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_subset_generation(self):
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
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_tree_dfs(self):
        code = """
def dfs(root):
    if not root:
        return
    dfs(root.left)
    dfs(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_permutations_swap(self):
        code = """
def permute(nums):
    result = []
    def backtrack(start):
        if start == len(nums):
            result.append(nums[:])
            return
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]
    backtrack(0)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "swap_recurse_swap" for e in result.evidence)

    def test_detected_permutations_visited(self):
        code = """
def permute(nums):
    result = []
    used = [False] * len(nums)
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if not used[i]:
                used[i] = True
                path.append(nums[i])
                backtrack(path)
                path.pop()
                used[i] = False
    backtrack([])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "visited_array" for e in result.evidence)
        assert any(e.type == "permutation_generation" for e in result.evidence)

    def test_detected_permutations_ii(self):
        code = """
def permuteUnique(nums):
    nums.sort()
    result = []
    used = [False] * len(nums)
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False
    backtrack([])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "visited_array" for e in result.evidence)
        assert any(e.type == "permutation_generation" for e in result.evidence)

    def test_detected_n_queens_style(self):
        code = """
def solveNQueens(n):
    result = []
    cols = [False] * n
    def backtrack(row, path):
        if row == n:
            result.append(path[:])
            return
        for col in range(n):
            if not cols[col]:
                cols[col] = True
                path.append(col)
                backtrack(row + 1, path)
                path.pop()
                cols[col] = False
    backtrack(0, [])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "visited_array" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
