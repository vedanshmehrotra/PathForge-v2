"""Build a representative test dataset from existing PathForge data.

Extracts submissions from the CSV dataset, creates synthetic test solutions
for various coding styles, and produces a structured dataset for evaluation.

Does NOT modify any production code.
"""

import csv
import json
import os
import random
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Canonical solution templates for each pattern ──────────────────────────
# These are representative implementations that SHOULD trigger specific detectors.
# Each template is a valid Python solution to a known LeetCode problem.

SOLUTION_TEMPLATES = {
    "hash_map_lookup": [
        # Two Sum - hash map approach
        """def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []""",
        # Valid Anagram - frequency counting
        """def isAnagram(s, t):
    if len(s) != len(t):
        return False
    count = {}
    for c in s:
        count[c] = count.get(c, 0) + 1
    for c in t:
        if c not in count:
            return False
        count[c] -= 1
        if count[c] < 0:
            return False
    return True""",
    ],
    "sliding_window_fixed": [
        # Maximum Average Subarray I
        """def findMaxAverage(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k""",
        # Maximum Average Subarray I - alternative
        """def findMaxAverage(nums, k):
    curr = sum(nums[:k])
    best = curr
    for i in range(k, len(nums)):
        curr = curr - nums[i-k] + nums[i]
        best = max(best, curr)
    return best / k""",
    ],
    "sliding_window_variable": [
        # Longest Substring Without Repeating Characters
        """def lengthOfLongestSubstring(s):
    seen = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in seen:
            seen.remove(s[left])
            left += 1
        seen.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len""",
        # Minimum Window Substring
        """def minWindow(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right, c in enumerate(s):
        if need[c] > 0:
            missing -= 1
        need[c] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end+1] if end < float('inf') else """,
    ],
    "two_pointers_opposite": [
        # Valid Palindrome
        """def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True""",
        # Two Sum II
        """def twoSum(numbers, target):
    left, right = 0, len(numbers) - 1
    while left < right:
        curr = numbers[left] + numbers[right]
        if curr == target:
            return [left + 1, right + 1]
        elif curr < target:
            left += 1
        else:
            right -= 1
    return []""",
        # Container With Most Water
        """def maxArea(height):
    left, right = 0, len(height) - 1
    max_water = 0
    while left < right:
        water = min(height[left], height[right]) * (right - left)
        max_water = max(max_water, water)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_water""",
    ],
    "two_pointers_same": [
        # Remove Duplicates from Sorted Array
        """def removeDuplicates(nums):
    if not nums:
        return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1""",
    ],
    "binary_search_standard": [
        # Binary Search
        """def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
        # Search Insert Position
        """def searchInsert(nums, target):
    left, right = 0, len(nums)
    while left < right:
        mid = (left + right) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    return left""",
    ],
    "dfs_recursive": [
        # Number of Islands (DFS)
        """def numIslands(grid):
    if not grid:
        return 0
    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                dfs(grid, i, j)
                count += 1
    return count

def dfs(grid, i, j):
    if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] != '1':
        return
    grid[i][j] = '0'
    dfs(grid, i+1, j)
    dfs(grid, i-1, j)
    dfs(grid, i, j+1)
    dfs(grid, i, j-1)""",
    ],
    "bfs_shortest_path": [
        # Rotting Oranges
        """from collections import deque
def orangesRotting(grid):
    queue = deque()
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == 2:
                queue.append((i, j))
    minutes = 0
    while queue:
        for _ in range(len(queue)):
            x, y = queue.popleft()
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 1:
                    grid[nx][ny] = 2
                    queue.append((nx, ny))
        if queue:
            minutes += 1
    for row in grid:
        if 1 in row:
            return -1
    return minutes""",
    ],
    "backtracking_permutation": [
        # Permutations
        """def permute(nums):
    result = []
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for num in nums:
            if num in path:
                continue
            path.append(num)
            backtrack(path)
            path.pop()
    backtrack([])
    return result""",
    ],
    "backtracking_subset": [
        # Subsets
        """def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result""",
    ],
    "dp_1d_forward": [
        # Climbing Stairs
        """def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]""",
    ],
    "dp_2d_grid": [
        # Unique Paths
        """def uniquePaths(m, n):
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i-1][j] + dp[i][j-1]
    return dp[m-1][n-1]""",
    ],
    "dp_knapsack": [
        # 0/1 Knapsack
        """def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
    return dp[n][capacity]""",
    ],
    "union_find": [
        # Number of Provinces
        """def findCircleNum(isConnected):
    n = len(isConnected)
    parent = list(range(n))
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for i in range(n):
        for j in range(i+1, n):
            if isConnected[i][j]:
                union(i, j)
    
    return len(set(find(i) for i in range(n)))""",
    ],
    "monotonic_stack": [
        # Daily Temperatures
        """def dailyTemperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temperatures[i] > temperatures[stack[-1]]:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)
    return result""",
    ],
    "linked_list_reversal": [
        # Reverse Linked List
        """def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_temp = curr.next
        curr.next = prev
        prev = curr
        curr = next_temp
    return prev""",
    ],
    "heap_top_k": [
        # Top K Frequent Elements
        """import heapq
from collections import Counter
def topKFrequent(nums, k):
    count = Counter(nums)
    return [x for x, _ in heapq.nlargest(k, count.items(), key=lambda x: x[1])""",
    ],
    "greedy_local": [
        # Best Time to Buy and Sell Stock
        """def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    for price in prices:
        min_price = min(min_price, price)
        max_profit = max(max_profit, price - min_price)
    return max_profit""",
    ],
    "prefix_sum": [
        # Subarray Sum Equals K
        """def subarraySum(nums, k):
    count = 0
    prefix_sum = 0
    seen = {0: 1}
    for num in nums:
        prefix_sum += num
        if prefix_sum - k in seen:
            count += seen[prefix_sum - k]
        seen[prefix_sum] = seen.get(prefix_sum, 0) + 1
    return count""",
    ],
    "dp_top_down_shadow": [
        # Fibonacci with memoization
        """def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]""",
        # Climbing stairs with memo
        """def climbStairs(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 2:
        return n
    memo[n] = climbStairs(n-1, memo) + climbStairs(n-2, memo)
    return memo[n]""",
    ],
    "dp_bottom_up_shadow": [
        # Coin Change
        """def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for i in range(coin, amount + 1):
            if dp[i - coin] + 1 < dp[i]:
                dp[i] = dp[i - coin] + 1
    return dp[amount] if dp[amount] != float('inf') else -1""",
    ],
}

# ── Stylized variants for robustness testing ──────────────────────────────

VARIANT_TRANSFORMS = {
    "rename_variables": {
        "description": "Rename variables to different names",
        "pairs": [
            ("left, right = 0, n - 1", "i, j = 0, len(arr) - 1"),
            ("seen = {}", "visited = {}"),
            ("result = []", "output = []"),
            ("max_len = 0", "longest = 0"),
        ]
    },
    "loop_style": {
        "description": "Change loop structures",
        "pairs": [
            ("for i in range(n):", "i = 0\nwhile i < n:"),
            ("while left < right:", "while not left >= right:"),
        ]
    },
    "expression_style": {
        "description": "Equivalent expressions",
        "pairs": [
            ("i += 1", "i = i + 1"),
            ("x // 2", "x >> 1"),
            ("x * 2", "x << 1"),
        ]
    },
}


def load_problems_csv(csv_path: str) -> list:
    """Load problems from the CSV dataset."""
    problems = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            problems.append(row)
    return problems


def create_submission_entry(
    submission_id: int,
    problem_id: int,
    source_code: str,
    language: str = "python",
    correctness: str = "correct",
    style: str = "standard",
    variant: str = None,
    target_concepts: list = None,
    problem_title: str = "",
    problem_difficulty: str = "",
    problem_topics: str = "",
) -> dict:
    """Create a structured submission entry."""
    return {
        "submission_id": f"sub_{submission_id:04d}",
        "problem_id": problem_id,
        "problem_title": problem_title,
        "problem_difficulty": problem_difficulty,
        "problem_topics": problem_topics,
        "language": language,
        "source_code": source_code,
        "solution_correctness": correctness,
        "style": style,
        "variant": variant,
        "target_concepts": target_concepts or [],
    }


def build_dataset(problems_csv: str, output_dir: str, max_submissions: int = 200) -> dict:
    """Build the evaluation dataset from template solutions.
    
    Returns a summary of what was created.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    problems = load_problems_csv(problems_csv)
    submissions = []
    submission_id = 0
    
    # Map problem patterns to concepts
    pattern_to_concepts = {
        '"hash_map_lookup"': ["hash_map_lookup"],
        '"two_pointers_opposite"': ["two_pointers_opposite"],
        '"two_pointers_same"': ["two_pointers_same"],
        '"sliding_window_fixed"': ["sliding_window_fixed"],
        '"sliding_window_variable"': ["sliding_window_variable"],
        '"binary_search_standard"': ["binary_search_standard"],
        '"binary_search_rotated"': ["binary_search_rotated"],
        '"binary_search_answer"': ["binary_search_answer"],
        '"dfs_recursive"': ["dfs_recursive"],
        '"dfs_iterative"': ["dfs_iterative"],
        '"bfs_level_order"': ["bfs_level_order"],
        '"bfs_shortest_path"': ["bfs_shortest_path"],
        '"topological_sort"': ["topological_sort"],
        '"union_find"': ["union_find"],
        '"binary_search_tree"': ["binary_search_tree"],
        '"dp_1d_forward"': ["dp_1d_forward"],
        '"dp_1d_sequence"': ["dp_1d_sequence"],
        '"dp_2d_grid"': ["dp_2d_grid"],
        '"dp_2d_string"': ["dp_2d_string"],
        '"dp_knapsack"': ["dp_knapsack"],
        '"dp_interval"': ["dp_interval"],
        '"dp_state_machine"': ["dp_state_machine"],
        '"fast_slow_pointers"': ["fast_slow_pointers"],
        '"linked_list_reversal"': ["linked_list_reversal"],
        '"monotonic_stack"': ["monotonic_stack"],
        '"monotonic_deque"': ["monotonic_deque"],
        '"heap_top_k"': ["heap_top_k"],
        '"greedy_local"': ["greedy_local"],
        '"greedy_interval"': ["greedy_interval"],
        '"backtracking_permutation"': ["backtracking_permutation"],
        '"backtracking_subset"': ["backtracking_subset"],
        '"prefix_sum"': ["prefix_sum"],
    }
    
    # Create submissions from templates
    for concept_id, templates in SOLUTION_TEMPLATES.items():
        for i, template in enumerate(templates):
            if submission_id >= max_submissions:
                break
            
            submission_id += 1
            entry = create_submission_entry(
                submission_id=submission_id,
                problem_id=0,  # Synthetic
                source_code=template.strip(),
                correctness="correct",
                style="standard" if i == 0 else "variant_1",
                target_concepts=[concept_id],
                problem_title=f"Template: {concept_id}",
                problem_difficulty="N/A",
                problem_topics=concept_id,
            )
            submissions.append(entry)
    
    # Add some synthetic variants for robustness testing
    for concept_id, template in list(SOLUTION_TEMPLATES.items())[:5]:
        if submission_id >= max_submissions:
            break
        
        # Create a renamed-variable variant
        variant_code = template[0].strip()
        # Simple variable renames
        renames = [
            ("left", "i"), ("right", "j"), ("nums", "arr"),
            ("seen", "visited"), ("result", "output"), ("max_len", "longest"),
        ]
        for old, new in renames:
            variant_code = variant_code.replace(old, new)
        
        submission_id += 1
        entry = create_submission_entry(
            submission_id=submission_id,
            problem_id=0,
            source_code=variant_code,
            correctness="correct",
            style="renamed_variables",
            variant="variable_rename",
            target_concepts=[concept_id],
            problem_title=f"Variant: {concept_id} (renamed)",
            problem_difficulty="N/A",
            problem_topics=concept_id,
        )
        submissions.append(entry)
    
    # Add some incorrect solutions
    incorrect_examples = [
        {
            "code": """def twoSum(nums, target):
    # Bug: always returns first pair
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []""",
            "concepts": [],  # Intended: hash_map_lookup, but implemented as brute force
            "title": "Incorrect Two Sum (O(n^2))",
        },
        {
            "code": """def binarySearch(nums, target):
    # Bug: infinite loop - doesn't narrow search space
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        # Bug: missing else-if
        left = mid + 1
    return -1""",
            "concepts": ["binary_search_standard"],  # Has the structure but is buggy
            "title": "Buggy Binary Search",
        },
    ]
    
    for ex in incorrect_examples:
        submission_id += 1
        entry = create_submission_entry(
            submission_id=submission_id,
            problem_id=0,
            source_code=ex["code"].strip(),
            correctness="incorrect",
            style="incorrect",
            target_concepts=ex["concepts"],
            problem_title=ex["title"],
            problem_difficulty="N/A",
            problem_topics="",
        )
        submissions.append(entry)
    
    # Save dataset
    dataset_path = os.path.join(output_dir, "submissions.json")
    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(submissions, f, indent=2, ensure_ascii=False)
    
    # Create summary
    summary = {
        "total_submissions": len(submissions),
        "by_concept": {},
        "by_correctness": {},
        "by_style": {},
        "concepts_covered": set(),
    }
    
    for sub in submissions:
        for concept in sub["target_concepts"]:
            summary["by_concept"][concept] = summary["by_concept"].get(concept, 0) + 1
            summary["concepts_covered"].add(concept)
        summary["by_correctness"][sub["solution_correctness"]] = \
            summary["by_correctness"].get(sub["solution_correctness"], 0) + 1
        summary["by_style"][sub["style"]] = \
            summary["by_style"].get(sub["style"], 0) + 1
    
    summary["concepts_covered"] = sorted(summary["concepts_covered"])
    
    # Save summary
    summary_path = os.path.join(output_dir, "dataset_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    return summary


if __name__ == "__main__":
    csv_path = str(PROJECT_ROOT / "pathforge" / "data" / "pathforge_problems_fixed.csv")
    output_dir = str(Path(__file__).resolve().parent.parent / "dataset" / "selected_submissions")
    
    print(f"Loading problems from: {csv_path}")
    summary = build_dataset(csv_path, output_dir, max_submissions=200)
    
    print(f"\nDataset created:")
    print(f"  Total submissions: {summary['total_submissions']}")
    print(f"  Concepts covered: {len(summary['concepts_covered'])}")
    print(f"  By correctness: {summary['by_correctness']}")
    print(f"  By style: {summary['by_style']}")
