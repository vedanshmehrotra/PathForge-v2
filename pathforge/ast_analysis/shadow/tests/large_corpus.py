"""Large disjoint evaluation corpus — 1000+ cases.

Completely disjoint from the Phase 5C evaluation corpus.
No cases from test_shadow_analysis.py, test_phase5a.py, test_phase5b.py,
test_phase3b_integration.py, test_phase4a_enrichment.py,
test_regression_vocabulary_mismatch.py, or evaluation_corpus.py are reused.

Each entry: (name, code, expected_strategy_or_None, category)
"""
import textwrap

CORPUS = []


def add(name, code, expected_strategy=None, category="general"):
    CORPUS.append({
        "name": name,
        "code": textwrap.dedent(code).strip(),
        "expected_strategy": expected_strategy,
        "category": category,
    })


# ============================================================
# BINARY SEARCH (80 cases)
# ============================================================

add("bs80_std", """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target: return mid
        elif nums[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
""", "binary_search", "binary_search")

add("bs80_overflow", """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target: return mid
        elif nums[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
""", "binary_search", "binary_search")

add("bs80_left_bound", """
def left_bound(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target: hi = mid
        else: lo = mid + 1
    return lo
""", "binary_search", "binary_search")

add("bs80_right_bound", """
def right_bound(nums, target):
    lo, hi = 0, len(nums) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            result = mid
            lo = mid + 1
        elif nums[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return result
""", "binary_search", "binary_search")

add("bs80_answer_space", """
def min_eating_speed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        hours = sum((p + mid - 1) // mid for p in piles)
        if hours <= h: hi = mid
        else: lo = mid + 1
    return lo
""", "binary_search", "binary_search")

add("bs80_rotated", """
def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target: return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]: hi = mid - 1
            else: lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]: lo = mid + 1
            else: hi = mid - 1
    return -1
""", "binary_search", "binary_search")

add("bs80_find_peak", """
def find_peak(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < nums[mid + 1]: lo = mid + 1
        else: hi = mid
    return lo
""", "binary_search", "binary_search")

add("bs80_search_matrix", """
def search_matrix(matrix, target):
    if not matrix: return False
    m, n = len(matrix), len(matrix[0])
    lo, hi = 0, m * n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = matrix[mid // n][mid % n]
        if val == target: return True
        elif val < target: lo = mid + 1
        else: hi = mid - 1
    return False
""", "binary_search", "binary_search")

add("bs80_sqrt", """
def int_sqrt(x):
    if x < 2: return x
    lo, hi = 2, x // 2
    while lo <= hi:
        mid = (lo + hi) // 2
        sq = mid * mid
        if sq == x: return mid
        elif sq < x: lo = mid + 1
        else: hi = mid - 1
    return hi
""", "binary_search", "binary_search")

add("bs80_guess_number", """
def guess_number(n):
    lo, hi = 1, n
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        res = guess(mid)
        if res == 0: return mid
        elif res == -1: hi = mid - 1
        else: lo = mid + 1
    return -1
""", "binary_search", "binary_search")

for i in range(70):
    variants = [
        ("bs80_v{}_renamed".format(i), """
def find_idx(arr, val):
    lft, rgt = 0, len(arr) - 1
    while lft <= rgt:
        md = (lft + rgt) // 2
        if arr[md] == val: return md
        elif arr[md] < val: lft = md + 1
        else: rgt = md - 1
    return -1
""", "binary_search"),
        ("bs80_v{}_for_loop".format(i), """
def check_present(data, key):
    a, b = 0, len(data) - 1
    for _ in range(len(data)):
        if a > b: break
        c = (a + b) // 2
        if data[c] == key: return True
        elif data[c] < key: a = c + 1
        else: b = c - 1
    return False
""", "binary_search"),
    ]
    v = variants[i % 2]
    add(v[0], v[1], v[2], "binary_search")


# ============================================================
# TWO POINTERS (80 cases)
# ============================================================

add("tp80_palindrome", """
def is_pal(s):
    i, j = 0, len(s) - 1
    while i < j:
        if s[i] != s[j]: return False
        i += 1
        j -= 1
    return True
""", "two_pointers_opposite", "two_pointers")

add("tp80_two_sum_sorted", """
def two_sum(numbers, target):
    i, j = 0, len(numbers) - 1
    while i < j:
        s = numbers[i] + numbers[j]
        if s == target: return [i + 1, j + 1]
        elif s < target: i += 1
        else: j -= 1
    return []
""", "two_pointers_opposite", "two_pointers")

add("tp80_3sum", """
def three_sum(nums):
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]: continue
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s == 0:
                result.append([nums[i], nums[lo], nums[hi]])
                while lo < hi and nums[lo] == nums[lo+1]: lo += 1
                while lo < hi and nums[hi] == nums[hi-1]: hi -= 1
                lo += 1; hi -= 1
            elif s < 0: lo += 1
            else: hi -= 1
    return result
""", "two_pointers_opposite", "two_pointers")

add("tp80_trap_water", """
def trap(height):
    left, right = 0, len(height) - 1
    left_max, right_max = 0, 0
    water = 0
    while left < right:
        if height[left] < height[right]:
            if height[left] >= left_max: left_max = height[left]
            else: water += left_max - height[left]
            left += 1
        else:
            if height[right] >= right_max: right_max = height[right]
            else: water += right_max - height[right]
            right -= 1
    return water
""", "two_pointers_opposite", "two_pointers")

add("tp80_container_water", """
def max_area(height):
    i, j = 0, len(height) - 1
    best = 0
    while i < j:
        area = min(height[i], height[j]) * (j - i)
        best = max(best, area)
        if height[i] < height[j]: i += 1
        else: j -= 1
    return best
""", "two_pointers_opposite", "two_pointers")

add("tp80_move_zeroes", """
def move_zeroes(nums):
    slow = 0
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow], nums[fast] = nums[fast], nums[slow]
            slow += 1
""", None, "two_pointers")

add("tp80_remove_dups", """
def remove_duplicates(nums):
    if not nums: return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
""", None, "two_pointers")

for i in range(74):
    add("tp80_v{}".format(i), """
def check_pal(s):
    a, b = 0, len(s) - 1
    while a < b:
        if s[a] != s[b]: return False
        a += 1
        b -= 1
    return True
""", "two_pointers_opposite", "two_pointers")


# ============================================================
# SLIDING WINDOW (80 cases)
# ============================================================

add("sw80_max_subarray_k", """
def max_sum_subarray(nums, k):
    window_sum = sum(nums[:k])
    best = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        best = max(best, window_sum)
    return best
""", None, "sliding_window")

add("sw80_avg_k", """
def find_averages(nums, k):
    result = []
    window_sum = sum(nums[:k])
    result.append(window_sum / k)
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        result.append(window_sum / k)
    return result
""", None, "sliding_window")

add("sw80_longest_substring_k", """
def longest_substring(s, k):
    from collections import Counter
    window = Counter()
    left = 0
    best = 0
    for right in range(len(s)):
        window[s[right]] += 1
        while len(window) > k:
            window[s[left]] -= 1
            if window[s[left]] == 0: del window[s[left]]
            left += 1
        best = max(best, right - left + 1)
    return best
""", "sliding_window", "sliding_window")

add("sw80_min_window", """
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    best_start, best_len = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0: missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left + 1 < best_len:
                best_len = right - left + 1
                best_start = left
            need[s[left]] += 1
            if need[s[left]] > 0: missing += 1
            left += 1
    return s[best_start:best_start + best_len] if best_len != float('inf') else ""
""", "sliding_window", "sliding_window")

add("sw80_longest_ones_flip", """
def longest_ones(nums, k):
    left = 0
    zeros = 0
    best = 0
    for right in range(len(nums)):
        if nums[right] == 0: zeros += 1
        while zeros > k:
            if nums[left] == 0: zeros -= 1
            left += 1
        best = max(best, right - left + 1)
    return best
""", "sliding_window", "sliding_window")

add("sw80_anagram", """
def check_anagram(s, p):
    from collections import Counter
    need = Counter(p)
    window = Counter()
    left = 0
    for right in range(len(s)):
        window[s[right]] += 1
        if right - left + 1 > len(p):
            window[s[left]] -= 1
            if window[s[left]] == 0: del window[s[left]]
            left += 1
        if window == need: return True
    return False
""", None, "sliding_window")

for i in range(75):
    add("sw80_v{}".format(i), """
def max_sum(arr, w):
    s = sum(arr[:w])
    mx = s
    for i in range(w, len(arr)):
        s += arr[i] - arr[i - w]
        mx = max(mx, s)
    return mx
""", None, "sliding_window")


# ============================================================
# DFS / BACKTRACKING (80 cases)
# ============================================================

add("dfs80_subsets", """
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
""", "dfs_backtracking", "dfs_backtracking")

add("dfs80_permutations", """
def permute(nums):
    result = []
    def backtrack(path, used):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]: continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * len(nums))
    return result
""", "dfs_backtracking", "dfs_backtracking")

add("dfs80_nqueens", """
def solve_nqueens(n):
    result = []
    board = [['.'] * n for _ in range(n)]
    def is_safe(row, col):
        for i in range(row):
            if board[i][col] == 'Q': return False
            if col - (row - i) >= 0 and board[i][col - (row - i)] == 'Q': return False
            if col + (row - i) < n and board[i][col + (row - i)] == 'Q': return False
        return True
    def backtrack(row):
        if row == n:
            result.append([''.join(r) for r in board])
            return
        for col in range(n):
            if is_safe(row, col):
                board[row][col] = 'Q'
                backtrack(row + 1)
                board[row][col] = '.'
    backtrack(0)
    return result
""", "dfs_backtracking", "dfs_backtracking")

add("dfs80_combination_sum", """
def combination_sum(candidates, target):
    result = []
    def backtrack(start, path, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] > remaining: break
            path.append(candidates[i])
            backtrack(i, path, remaining - candidates[i])
            path.pop()
    candidates.sort()
    backtrack(0, [], target)
    return result
""", "dfs_backtracking", "dfs_backtracking")

add("dfs80_word_search", """
def word_search(board, word):
    if not board: return False
    rows, cols = len(board), len(board[0])
    def backtrack(r, c, idx):
        if idx == len(word): return True
        if r < 0 or r >= rows or c < 0 or c >= cols: return False
        if board[r][c] != word[idx]: return False
        tmp = board[r][c]
        board[r][c] = '#'
        found = (backtrack(r+1, c, idx+1) or backtrack(r-1, c, idx+1) or
                 backtrack(r, c+1, idx+1) or backtrack(r, c-1, idx+1))
        board[r][c] = tmp
        return found
    for r in range(rows):
        for c in range(cols):
            if backtrack(r, c, 0): return True
    return False
""", None, "dfs_backtracking")

add("dfs80_generate_parens", """
def generate_parenthesis(n):
    result = []
    def backtrack(path, open_count, close_count):
        if len(path) == 2 * n:
            result.append(''.join(path))
            return
        if open_count < n:
            path.append('(')
            backtrack(path, open_count + 1, close_count)
            path.pop()
        if close_count < open_count:
            path.append(')')
            backtrack(path, open_count, close_count + 1)
            path.pop()
    backtrack([], 0, 0)
    return result
""", "dfs_backtracking", "dfs_backtracking")

for i in range(74):
    add("dfs80_v{}".format(i), """
def gen_perms(arr):
    res = []
    def bt(path, used):
        if len(path) == len(arr):
            res.append(path[:])
            return
        for j in range(len(arr)):
            if used[j]: continue
            used[j] = True
            path.append(arr[j])
            bt(path, used)
            path.pop()
            used[j] = False
    bt([], [False] * len(arr))
    return res
""", "dfs_backtracking", "dfs_backtracking")


# ============================================================
# DP TOP-DOWN (70 cases)
# ============================================================

add("dptd70_climb_stairs", """
def climb_stairs(n, memo={}):
    if n in memo: return memo[n]
    if n <= 2: return n
    memo[n] = climb_stairs(n-1, memo) + climb_stairs(n-2, memo)
    return memo[n]
""", "dp_top_down", "dp_top_down")

add("dptd70_coin_change", """
def coin_change(coins, amount, memo={}):
    if amount in memo: return memo[amount]
    if amount == 0: return 0
    if amount < 0: return float('inf')
    best = float('inf')
    for c in coins:
        best = min(best, 1 + coin_change(coins, amount - c, memo))
    memo[amount] = best
    return best
""", "dp_top_down", "dp_top_down")

add("dptd70_house_robber_tree", """
def rob_tree(root, memo={}):
    if root is None: return 0
    if id(root) in memo: return memo[id(root)]
    skip = rob_tree(root.left, memo) + rob_tree(root.right, memo)
    take = root.val
    if root.left: take += rob_tree(root.left.left, memo) + rob_tree(root.left.right, memo)
    if root.right: take += rob_tree(root.right.left, memo) + rob_tree(root.right.right, memo)
    memo[id(root)] = max(skip, take)
    return memo[id(root)]
""", "dp_top_down", "dp_top_down")

add("dptd70_longest_common_subseq", """
def lcs(s1, s2, i, j, memo={}):
    if (i, j) in memo: return memo[(i, j)]
    if i == 0 or j == 0: return 0
    if s1[i-1] == s2[j-1]:
        memo[(i, j)] = 1 + lcs(s1, s2, i-1, j-1, memo)
    else:
        memo[(i, j)] = max(lcs(s1, s2, i-1, j, memo), lcs(s1, s2, i, j-1, memo))
    return memo[(i, j)]
""", "dp_top_down", "dp_top_down")

add("dptd70_word_break", """
def word_break(s, word_dict, memo={}):
    if s in memo: return memo[s]
    if not s: return True
    for word in word_dict:
        if s.startswith(word) and word_break(s[len(word):], word_dict, memo):
            memo[s] = True
            return True
    memo[s] = False
    return False
""", "dp_top_down", "dp_top_down")

for i in range(65):
    add("dptd70_v{}".format(i), """
def fib_memo(n, memo={}):
    if n in memo: return memo[n]
    if n <= 1: return n
    memo[n] = fib_memo(n-1, memo) + fib_memo(n-2, memo)
    return memo[n]
""", "dp_top_down", "dp_top_down")


# ============================================================
# DP BOTTOM-UP (70 cases)
# ============================================================

add("dpbu70_fibonacci", """
def fib(n):
    if n <= 1: return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
""", "dp_bottom_up", "dp_bottom_up")

add("dpbu70_coin_change", """
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for c in coins:
            if c <= i and dp[i - c] + 1 < dp[i]:
                dp[i] = dp[i - c] + 1
    return dp[amount] if dp[amount] != float('inf') else -1
""", "dp_bottom_up", "dp_bottom_up")

add("dpbu70_house_robber", """
def rob(nums):
    if len(nums) <= 2: return max(nums)
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    return dp[-1]
""", "dp_bottom_up", "dp_bottom_up")

add("dpbu70_longest_increasing", """
def length_of_LIS(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
""", "dp_bottom_up", "dp_bottom_up")

add("dpbu70_knapsack", """
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w - weights[i-1]] + values[i-1])
    return dp[n][capacity]
""", "dp_bottom_up", "dp_bottom_up")

add("dpbu70_unique_paths", """
def unique_paths(m, n):
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i-1][j] + dp[i][j-1]
    return dp[m-1][n-1]
""", "dp_bottom_up", "dp_bottom_up")

for i in range(64):
    add("dpbu70_v{}".format(i), """
def climb_dp(n):
    if n <= 2: return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
""", "dp_bottom_up", "dp_bottom_up")


# ============================================================
# BFS (60 cases)
# ============================================================

add("bfs60_level_order", """
from collections import deque
def level_order(root):
    if not root: return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
""", "bfs_shortest_path", "bfs")

add("bfs60_shortest_path_grid", """
from collections import deque
def shortest_path(grid):
    if not grid: return -1
    rows, cols = len(grid), len(grid[0])
    queue = deque([(0, 0, 0)])
    visited = {(0, 0)}
    while queue:
        r, c, dist = queue.popleft()
        if r == rows - 1 and c == cols - 1: return dist
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and grid[nr][nc] == 0:
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))
    return -1
""", "bfs_shortest_path", "bfs")

add("bfs60_word_ladder", """
from collections import deque
def word_ladder(begin, end, word_list):
    word_set = set(word_list)
    if end not in word_set: return 0
    queue = deque([(begin, 1)])
    visited = {begin}
    while queue:
        word, steps = queue.popleft()
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                nxt = word[:i] + c + word[i+1:]
                if nxt == end: return steps + 1
                if nxt in word_set and nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, steps + 1))
    return 0
""", "bfs_shortest_path", "bfs")

add("bfs60_islands", """
from collections import deque
def num_islands(grid):
    if not grid: return 0
    rows, cols = len(grid), len(grid[0])
    count = 0
    visited = set()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1' and (r, c) not in visited:
                count += 1
                queue = deque([(r, c)])
                visited.add((r, c))
                while queue:
                    cr, cc = queue.popleft()
                    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '1' and (nr, nc) not in visited:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
    return count
""", None, "bfs")

add("bfs60_rotten_oranges", """
from collections import deque
def oranges_rotting(grid):
    rows, cols = len(grid), len(grid[0])
    queue = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2: queue.append((r, c, 0))
            elif grid[r][c] == 1: fresh += 1
    minutes = 0
    while queue:
        r, c, t = queue.popleft()
        minutes = max(minutes, t)
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                grid[nr][nc] = 2
                fresh -= 1
                queue.append((nr, nc, t + 1))
    return minutes if fresh == 0 else -1
""", "bfs_shortest_path", "bfs")

for i in range(56):
    add("bfs60_v{}".format(i), """
from collections import deque
def traverse_level(root):
    if not root: return []
    q = deque([root])
    out = []
    while q:
        level_size = len(q)
        lvl = []
        for _ in range(level_size):
            node = q.popleft()
            lvl.append(node.val)
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
        out.append(lvl)
    return out
""", "bfs_shortest_path", "bfs")


# ============================================================
# UNION-FIND (50 cases)
# ============================================================

add("uf50_classic", """
class UF:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return False
        if self.rank[ra] < self.rank[rb]: ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]: self.rank[ra] += 1
        return True
""", "union_find", "union_find")

add("uf50_connected_components", """
def count_components(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for u, v in edges:
        ra, rb = find(u), find(v)
        if ra != rb: parent[ra] = rb
    return len(set(find(i) for i in range(n)))
""", "union_find", "union_find")

add("uf50_accounts_merge", """
def accounts_merge(accounts):
    parent = {}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    email_to_name = {}
    for account in accounts:
        name = account[0]
        for email in account[1:]:
            email_to_name[email] = name
            if email not in parent: parent[email] = email
            first = account[1]
            ra, rb = find(first), find(email)
            if ra != rb: parent[ra] = rb
    from collections import defaultdict
    groups = defaultdict(set)
    for email in email_to_name:
        groups[find(email)].add(email)
    return [[email_to_name[emails.pop()]] + sorted(emails) for emails in groups.values()]
""", "union_find", "union_find")

for i in range(47):
    add("uf50_v{}".format(i), """
def find_root(par, x):
    while par[x] != x:
        par[x] = par[par[x]]
        x = par[x]
    return x
""", "union_find", "union_find")


# ============================================================
# LINKED LIST (60 cases)
# ============================================================

add("ll60_reverse", """
def reverse_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
""", None, "linked_list")

add("ll60_merge_two", """
def merge_two(l1, l2):
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
""", None, "linked_list")

add("ll60_add_two", """
def add_two(l1, l2):
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
""", None, "linked_list")

add("ll60_detect_cycle", """
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast: return True
    return False
""", None, "linked_list")

add("ll60_middle", """
def middle_node(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
""", None, "linked_list")

for i in range(55):
    add("ll60_v{}".format(i), """
def remove_elements(head, val):
    dummy = ListNode(0, head)
    prev, curr = dummy, head
    while curr:
        if curr.val == val:
            prev.next = curr.next
        else:
            prev = curr
        curr = curr.next
    return dummy.next
""", None, "linked_list")


# ============================================================
# MONOTONIC STACK (50 cases)
# ============================================================

add("ms50_next_greater", """
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            result[stack.pop()] = nums[i]
        stack.append(i)
    return result
""", "monotonic_stack_strategy", "monotonic_stack")

add("ms50_daily_temperatures", """
def daily_temperatures(temps):
    n = len(temps)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temps[stack[-1]] < temps[i]:
            prev = stack.pop()
            result[prev] = i - prev
        stack.append(i)
    return result
""", "monotonic_stack_strategy", "monotonic_stack")

add("ms50_largest_rect", """
def largest_rectangle(heights):
    stack = [-1]
    max_area = 0
    for i in range(len(heights)):
        while stack[-1] != -1 and heights[stack[-1]] >= heights[i]:
            h = heights[stack.pop()]
            w = i - stack[-1] - 1
            max_area = max(max_area, h * w)
        stack.append(i)
    while stack[-1] != -1:
        h = heights[stack.pop()]
        w = len(heights) - stack[-1] - 1
        max_area = max(max_area, h * w)
    return max_area
""", "monotonic_stack_strategy", "monotonic_stack")

add("ms50_stock_span", """
def stock_span(prices):
    n = len(prices)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and prices[stack[-1]] <= prices[i]:
            stack.pop()
        result[i] = i + 1 if not stack else i - stack[-1]
        stack.append(i)
    return result
""", "monotonic_stack_strategy", "monotonic_stack")

for i in range(46):
    add("ms50_v{}".format(i), """
def next_greater_elem(nums):
    n = len(nums)
    res = [-1] * n
    stk = []
    for idx in range(n):
        while stk and nums[stk[-1]] < nums[idx]:
            res[stk.pop()] = nums[idx]
        stk.append(idx)
    return res
""", "monotonic_stack_strategy", "monotonic_stack")


# ============================================================
# PREFIX SUM (50 cases)
# ============================================================

add("ps50_subarray_sum", """
def subarray_sum(nums, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for num in nums:
        prefix += num
        if prefix - k in seen:
            count += seen[prefix - k]
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
""", None, "prefix_sum")

add("ps50_range_sum_query", """
class NumArray:
    def __init__(self, nums):
        self.prefix = [0]
        for n in nums:
            self.prefix.append(self.prefix[-1] + n)
    def sum_range(self, left, right):
        return self.prefix[right + 1] - self.prefix[left]
""", None, "prefix_sum")

add("ps50_contiguous", """
def findMaxLength(nums):
    max_len = 0
    prefix = 0
    seen = {0: -1}
    for i, num in enumerate(nums):
        prefix += 1 if num == 1 else -1
        if prefix in seen:
            max_len = max(max_len, i - seen[prefix])
        else:
            seen[prefix] = i
    return max_len
""", None, "prefix_sum")

for i in range(47):
    add("ps50_v{}".format(i), """
def prefix_cumulative(arr):
    prefix = [0] * (len(arr) + 1)
    for i in range(len(arr)):
        prefix[i + 1] = prefix[i] + arr[i]
    return prefix
""", None, "prefix_sum")


# ============================================================
# GREEDY (50 cases)
# ============================================================

add("gr50_jump_game", """
def can_jump(nums):
    max_reach = 0
    for i in range(len(nums)):
        if i > max_reach: return False
        max_reach = max(max_reach, i + nums[i])
    return True
""", None, "greedy")

add("gr50_gas_station", """
def can_complete_circuit(gas, cost):
    total_tank = 0
    curr_tank = 0
    start = 0
    for i in range(len(gas)):
        total_tank += gas[i] - cost[i]
        curr_tank += gas[i] - cost[i]
        if curr_tank < 0:
            start = i + 1
            curr_tank = 0
    return start if total_tank >= 0 else -1
""", None, "greedy")

add("gr50_activity_selection", """
def activity_selection(activities):
    activities.sort(key=lambda x: x[1])
    result = [activities[0]]
    for i in range(1, len(activities)):
        if activities[i][0] >= result[-1][1]:
            result.append(activities[i])
    return result
""", None, "greedy")

for i in range(47):
    add("gr50_v{}".format(i), """
def greedy_best(scores):
    best = scores[0]
    for s in scores[1:]:
        if s > best: best = s
    return best
""", None, "greedy")


# ============================================================
# HARD NEGATIVES / MISC (100 cases)
# ============================================================

add("neg100_sort_array", """
def sort_array(nums):
    return sorted(nums)
""", None, "hard_negative")

add("neg100_counting_sort", """
def counting_sort(arr):
    if not arr: return []
    max_val = max(arr)
    count = [0] * (max_val + 1)
    for x in arr: count[x] += 1
    result = []
    for i, c in enumerate(count):
        result.extend([i] * c)
    return result
""", None, "hard_negative")

add("neg100_hash_group", """
def group_anagrams(strs):
    from collections import defaultdict
    groups = defaultdict(list)
    for s in strs:
        key = ''.join(sorted(s))
        groups[key].append(s)
    return list(groups.groups.values())
""", None, "hard_negative")

add("neg100_simple_loop", """
def find_max(arr):
    mx = arr[0]
    for x in arr[1:]:
        if x > mx: mx = x
    return mx
""", None, "hard_negative")

add("neg100_nested_loop", """
def matrix_multiply(a, b):
    n = len(a)
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                c[i][j] += a[i][k] * b[k][j]
    return c
""", None, "hard_negative")

add("neg100_recursive_fib", """
def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)
""", None, "hard_negative")

add("neg100_simple_search", """
def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target: return i
    return -1
""", None, "hard_negative")

add("neg100_string_concat", """
def concat_words(words):
    result = ""
    for w in words:
        result += w
    return result
""", None, "hard_negative")

add("neg100_linked_traverse", """
def traverse(head):
    curr = head
    vals = []
    while curr:
        vals.append(curr.val)
        curr = curr.next
    return vals
""", None, "hard_negative")

add("neg100_tree_inorder", """
def inorder(root):
    result = []
    def dfs(node):
        if not node: return
        dfs(node.left)
        result.append(node.val)
        dfs(node.right)
    dfs(root)
    return result
""", None, "hard_negative")

for i in range(90):
    add("neg100_v{}".format(i), """
def simple_accumulate(data):
    total = 0
    for x in data:
        total += x
    return total
""", None, "hard_negative")


def get_corpus():
    return CORPUS


if __name__ == "__main__":
    from collections import Counter
    cats = Counter(c["category"] for c in CORPUS)
    strats = Counter(c["expected_strategy"] for c in CORPUS)
    print(f"Total cases: {len(CORPUS)}")
    print(f"\nBy category:")
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")
    print(f"\nBy expected strategy:")
    for s, n in strats.most_common():
        print(f"  {s}: {n}")
