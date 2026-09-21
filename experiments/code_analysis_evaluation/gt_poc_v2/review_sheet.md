# Ground-Truth POC V2 — Blind Family Review Sheet

**Reviewer-facing artifact.** Analyzer detections (techniques, strategies,
PEC sets, profiles) are deliberately NOT shown. See `label_comparison.json`
for the post-hoc comparison.

No label is auto-approved: every family starts `PENDING_REVIEW`.

- Families: **37**  •  APPROVED: **0**  •  PENDING_REVIEW: **37**

> **PROVISIONAL (PA1):** no human reviewer is available in the POC
> environment, so no family is APPROVED. The label channels below are
> editorial proposals only; a human must approve them before any group
> could be promoted (spec V2 §4.5).

---

## lc1_fam1 — Two Sum (LC 1)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (db_sub_11, db_sub_39, two_sum_dict_variant)
- **sources:** authored, pathforge_db
- **reference solution:** `S0001` (pathforge_db)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['hash_map_lookup']
- **proposed required:** ['hash_lookup']
- **proposed optional:** _(none)_
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python

class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc1_fam2 — Two Sum (LC 1)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 2 (two_sum_brute_range, two_sum_brute_renamed)
- **sources:** authored
- **reference solution:** `S0003` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_lookup']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc1_fam3 — Two Sum (LC 1)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 1 (two_sum_brute_while)
- **sources:** authored
- **reference solution:** `S0005` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_lookup']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def two_sum(values, goal):
    a = 0
    while a < len(values):
        b = a + 1
        while b < len(values):
            if values[a] + values[b] == goal:
                return [a, b]
            b += 1
        a += 1
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc1_fam4 — Two Sum (LC 1)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 2 (two_sum_sort_two_pointer, two_sum_sort_two_pointer_renamed)
- **sources:** authored
- **reference solution:** `S0007` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_lookup']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def two_sum(nums, target):
    order = sorted(range(len(nums)), key=lambda i: nums[i])
    lo = 0
    hi = len(order) - 1
    while lo < hi:
        total = nums[order[lo]] + nums[order[hi]]
        if total == target:
            return [order[lo], order[hi]]
        if total < target:
            lo += 1
        else:
            hi -= 1
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam1 — Merge Two Sorted Lists (LC 21)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_GENERIC`
- **members:** 1 (db_sub_252)
- **sources:** pathforge_db
- **reference solution:** `S0009` (pathforge_db)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['two_pointers_same']
- **proposed required:** ['forward_pointer_advance']
- **proposed optional:** _(none)_
- **proposed excluded:** ['two_pointers_opposite']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        dummy=ListNode(None)
        tail=dummy
        print(list1.val)
        while list1 and list2:
            if list1.val<=list2.val:
                tail.next=list1
                list1=list1.next
            else:
                tail.next=list2
                list2=list2.next
            tail=tail.next
        if list1:
            tail.next=list1
        else:
            tail.next=list2
        return dummy.next
                
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam2 — Merge Two Sorted Lists (LC 21)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 2 (merge_collect_sort, merge_collect_sort_alt)
- **sources:** authored
- **reference solution:** `S0010` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['two_pointers_same']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def merge(list1, list2):
    values = []
    while list1 is not None:
        values.append(list1.val)
        list1 = list1.next
    while list2 is not None:
        values.append(list2.val)
        list2 = list2.next
    values.sort()
    dummy = ListNode(0)
    tail = dummy
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam3 — Merge Two Sorted Lists (LC 21)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_GENERIC`
- **members:** 2 (merge_iter_dummy, merge_iter_renamed)
- **sources:** authored
- **reference solution:** `S0012` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['two_pointers_same']
- **proposed required:** ['forward_pointer_advance']
- **proposed optional:** _(none)_
- **proposed excluded:** ['two_pointers_opposite']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def merge(list1, list2):
    dummy = ListNode(0)
    tail = dummy
    while list1 and list2:
        if list1.val < list2.val:
            tail.next = list1
            list1 = list1.next
        else:
            tail.next = list2
            list2 = list2.next
        tail = tail.next
    tail.next = list1 if list1 else list2
    return dummy.next
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam4 — Merge Two Sorted Lists (LC 21)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (merge_recursive, merge_recursive_alt, merge_recursive_renamed)
- **sources:** authored
- **reference solution:** `S0014` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['two_pointers_same']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def merge(list1, list2):
    if list1 is None:
        return list2
    if list2 is None:
        return list1
    if list1.val <= list2.val:
        list1.next = merge(list1.next, list2)
        return list1
    list2.next = merge(list1, list2.next)
    return list2
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc46_fam1 — Permutations (LC 46)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 3 (permute_insert, permute_insert_alt, permute_insert_renamed)
- **sources:** authored
- **reference solution:** `S0017` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['backtracking_permutation']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def permute(nums):
    result = [[]]
    for x in nums:
        nxt = []
        for p in result:
            for i in range(len(p) + 1):
                nxt.append(p[:i] + [x] + p[i:])
        result = nxt
    return result
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc46_fam2 — Permutations (LC 46)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 2 (permute_path_membership, permute_path_membership_alt)
- **sources:** authored
- **reference solution:** `S0020` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['backtracking_permutation']
- **proposed required:** ['dfs_backtracking']
- **proposed optional:** ['recursive_branching']
- **proposed excluded:** ['dp_top_down']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def permute(nums):
    out = []

    def backtrack(path):
        if len(path) == len(nums):
            out.append(list(path))
            return
        for x in nums:
            if x in path:
                continue
            path.append(x)
            backtrack(path)
            path.pop()

    backtrack([])
    return out
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc46_fam3 — Permutations (LC 46)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (permute_used, permute_used_dup, permute_used_renamed)
- **sources:** authored
- **reference solution:** `S0022` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['backtracking_permutation']
- **proposed required:** ['dfs_backtracking']
- **proposed optional:** ['recursive_branching']
- **proposed excluded:** ['dp_top_down']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def permute(nums):
    out = []
    used = [False] * len(nums)

    def backtrack(path):
        if len(path) == len(nums):
            out.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return out
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc70_fam1 — Climbing Stairs (LC 70)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (climb_dp_array, climb_dp_array_dup, climb_dp_array_renamed)
- **sources:** authored
- **reference solution:** `S0025` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['dp_1d_forward']
- **proposed required:** ['dp_bottom_up']
- **proposed optional:** ['iterative_table_filling']
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc70_fam2 — Climbing Stairs (LC 70)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (climb_memo, climb_memo_alt, climb_memo_renamed)
- **sources:** authored
- **reference solution:** `S0028` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['dp_1d_forward']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def climb_stairs(n):
    memo = {}

    def go(k):
        if k <= 2:
            return k
        if k in memo:
            return memo[k]
        memo[k] = go(k - 1) + go(k - 2)
        return memo[k]

    return go(n)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc70_fam3 — Climbing Stairs (LC 70)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 2 (climb_rolling, climb_rolling_renamed)
- **sources:** authored
- **reference solution:** `S0031` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['dp_1d_forward']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def climb_stairs(n):
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc102_fam1 — Binary Tree Level Order Traversal (LC 102)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 4 (level_order_deque, level_order_deque_renamed, level_order_list_queue, level_order_list_queue_dup)
- **sources:** authored
- **reference solution:** `S0033` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['bfs_level_order']
- **proposed required:** ['bfs_shortest_path']
- **proposed optional:** ['loop_state_tracking']
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
from collections import deque


def level_order(root):
    if not root:
        return []
    out = []
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
        out.append(level)
    return out
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc102_fam2 — Binary Tree Level Order Traversal (LC 102)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 4 (level_order_dfs, level_order_dfs_alt, level_order_dfs_dup, level_order_dfs_renamed)
- **sources:** authored
- **reference solution:** `S0035` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['bfs_level_order']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def level_order(root):
    levels = []

    def walk(node, depth):
        if not node:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)

    walk(root, 0)
    return levels
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam1 — Valid Palindrome (LC 125)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (db_sub_233, pal_two_ptr_manual, pal_two_ptr_renamed)
- **sources:** authored, pathforge_db
- **reference solution:** `S0047` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['two_pointers_opposite']
- **proposed required:** ['two_pointers_opposite']
- **proposed optional:** ['bidirectional_index_scan']
- **proposed excluded:** ['binary_search']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def is_palindrome(text):
    i = 0
    j = len(text) - 1
    while i < j:
        while i < j and not text[i].isalnum():
            i += 1
        while i < j and not text[j].isalnum():
            j -= 1
        if text[i].lower() != text[j].lower():
            return False
        i += 1
        j -= 1
    return True
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam2 — Valid Palindrome (LC 125)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 2 (pal_filter_slice, pal_filter_slice_simple)
- **sources:** authored
- **reference solution:** `S0042` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['two_pointers_opposite']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam3 — Valid Palindrome (LC 125)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (pal_recursive, pal_recursive_alt, pal_recursive_renamed)
- **sources:** authored
- **reference solution:** `S0044` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['two_pointers_opposite']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]

    def check(lo, hi):
        if lo >= hi:
            return True
        if cleaned[lo] != cleaned[hi]:
            return False
        return check(lo + 1, hi - 1)

    return check(0, len(cleaned) - 1)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc209_fam1 — Minimum Size Subarray Sum (LC 209)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 4 (db_sub_190, db_sub_231, min_subarray_slide, min_subarray_slide_renamed)
- **sources:** authored, pathforge_db
- **reference solution:** `S0055` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['prefix_sum', 'sliding_window_variable']
- **proposed required:** ['sequential_accumulation', 'sliding_window']
- **proposed optional:** ['iterative_table_filling', 'loop_state_tracking']
- **proposed excluded:** ['two_pointers_opposite']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def min_sub_array_len(target, nums):
    left = 0
    summ = 0
    ans = len(nums) + 1
    for right in range(len(nums)):
        summ += nums[right]
        while summ >= target:
            ans = min(ans, right - left + 1)
            summ -= nums[left]
            left += 1
    return 0 if ans == len(nums) + 1 else ans
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc209_fam2 — Minimum Size Subarray Sum (LC 209)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `REVIEW_REQUIRED_SCREEN_FAILED`
- **members:** 2 (min_subarray_brute, min_subarray_brute_dup)
- **sources:** authored
- **reference solution:** `S0051` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['prefix_sum', 'sliding_window_variable']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: partial_problem_label

```python
def min_sub_array_len(target, nums):
    best = len(nums) + 1
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total >= target:
                best = min(best, j - i + 1)
                break
    return 0 if best == len(nums) + 1 else best
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc209_fam3 — Minimum Size Subarray Sum (LC 209)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `REVIEW_REQUIRED_SCREEN_FAILED`
- **members:** 2 (min_subarray_prefix_nested, min_subarray_prefix_nested_dup)
- **sources:** authored
- **reference solution:** `S0053` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['prefix_sum', 'sliding_window_variable']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: partial_problem_label

```python
def min_sub_array_len(target, nums):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    best = len(nums) + 1
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] >= target:
                best = min(best, j - i)
                break
    return 0 if best == len(nums) + 1 else best
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc242_fam1 — Valid Anagram (LC 242)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (anagram_array26, anagram_array26_alt, anagram_array26_renamed)
- **sources:** authored
- **reference solution:** `S0057` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['hash_map_frequency']
- **proposed required:** ['frequency_counting']
- **proposed optional:** ['hash_lookup']
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    slots = [0] * 26
    for ch in s:
        slots[ord(ch) - ord("a")] += 1
    for ch in t:
        slots[ord(ch) - ord("a")] -= 1
    return all(v == 0 for v in slots)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc242_fam2 — Valid Anagram (LC 242)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 2 (anagram_counter_eq, anagram_sorted_eq)
- **sources:** authored
- **reference solution:** `S0060` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_frequency']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
from collections import Counter


def is_anagram(s, t):
    return Counter(s) == Counter(t)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc242_fam3 — Valid Anagram (LC 242)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (anagram_manual_dict, anagram_manual_dict_renamed, anagram_manual_ifelse)
- **sources:** authored
- **reference solution:** `S0061` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['hash_map_frequency']
- **proposed required:** ['frequency_counting']
- **proposed optional:** ['hash_lookup']
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        if ch not in counts:
            return False
        counts[ch] -= 1
        if counts[ch] < 0:
            return False
    return True
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc547_fam1 — Number of Provinces (LC 547)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 2 (provinces_bfs, provinces_bfs_alt)
- **sources:** authored
- **reference solution:** `S0065` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['union_find']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
from collections import deque


def find_circle_num(is_connected):
    n = len(is_connected)
    seen = [False] * n
    count = 0
    for i in range(n):
        if seen[i]:
            continue
        count += 1
        queue = deque([i])
        seen[i] = True
        while queue:
            node = queue.popleft()
            for j in range(n):
                if is_connected[node][j] and not seen[j]:
                    seen[j] = True
                    queue.append(j)
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc547_fam2 — Number of Provinces (LC 547)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (provinces_dfs, provinces_dfs_alt, provinces_dfs_renamed)
- **sources:** authored
- **reference solution:** `S0067` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['union_find']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def find_circle_num(is_connected):
    n = len(is_connected)
    seen = [False] * n

    def dfs(i):
        seen[i] = True
        for j in range(n):
            if is_connected[i][j] and not seen[j]:
                dfs(j)

    count = 0
    for i in range(n):
        if not seen[i]:
            count += 1
            dfs(i)
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc547_fam3 — Number of Provinces (LC 547)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 3 (provinces_union_find, provinces_union_find_alt, provinces_union_find_renamed)
- **sources:** authored
- **reference solution:** `S0070` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['union_find']
- **proposed required:** ['union_find']
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def find_circle_num(is_connected):
    n = len(is_connected)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    count = n
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
                    count -= 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc560_fam1 — Subarray Sum Equals K (LC 560)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `REVIEW_REQUIRED_SCREEN_FAILED`
- **members:** 2 (subarray_brute, subarray_brute_dup)
- **sources:** authored
- **reference solution:** `S0073` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_frequency', 'prefix_sum']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: partial_problem_label

```python
def subarray_sum(nums, k):
    count = 0
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total == k:
                count += 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc560_fam2 — Subarray Sum Equals K (LC 560)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 2 (subarray_defaultdict, subarray_defaultdict_alt)
- **sources:** authored
- **reference solution:** `S0075` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['hash_map_frequency', 'prefix_sum']
- **proposed required:** ['frequency_counting', 'sequential_accumulation']
- **proposed optional:** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded:** ['recursive_branching']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
from collections import defaultdict


def subarray_sum(nums, k):
    seen = defaultdict(int)
    seen[0] = 1
    total = 0
    count = 0
    for value in nums:
        total += value
        count += seen[total - k]
        seen[total] += 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc560_fam3 — Subarray Sum Equals K (LC 560)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `REVIEW_REQUIRED_SCREEN_FAILED`
- **members:** 2 (subarray_get_form, subarray_get_renamed)
- **sources:** authored
- **reference solution:** `S0077` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_frequency', 'prefix_sum']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: partial_problem_label

```python
def subarray_sum(nums, k):
    seen = {0: 1}
    total = 0
    count = 0
    for value in nums:
        total += value
        count += seen.get(total - k, 0)
        seen[total] = seen.get(total, 0) + 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc560_fam4 — Subarray Sum Equals K (LC 560)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `REVIEW_REQUIRED_SCREEN_FAILED`
- **members:** 2 (subarray_prefix_nested, subarray_prefix_nested_dup)
- **sources:** authored
- **reference solution:** `S0079` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['hash_map_frequency', 'prefix_sum']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: partial_problem_label

```python
def subarray_sum(nums, k):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    count = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] == k:
                count += 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam1 — Binary Search (LC 704)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_OK`
- **members:** 4 (db_sub_235, bs_lo_hi, bs_lo_hi_renamed, bs_mid_variant)
- **sources:** authored, pathforge_db
- **reference solution:** `S0083` (authored)
- **label source:** `curated_problems_pattern` (problem_level_screened)
- **problem patterns:** ['binary_search_standard']
- **proposed required:** ['binary_search']
- **proposed optional:** ['bidirectional_index_scan']
- **proposed excluded:** ['two_pointers_opposite']
- **rationale:** problem label applied: screen=all_required_observed_by_every_member

```python
def search(nums, target):
    lo = 0
    hi = len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam2 — Binary Search (LC 704)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `ZERO_EVIDENCE`
- **members:** 1 (bs_bisect)
- **sources:** authored
- **reference solution:** `S0082` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['binary_search_standard']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
import bisect


def search(nums, target):
    position = bisect.bisect_left(nums, target)
    if position < len(nums) and nums[position] == target:
        return position
    return -1
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam3 — Binary Search (LC 704)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (bs_recursive, bs_recursive_alt, bs_recursive_renamed)
- **sources:** authored
- **reference solution:** `S0086` (authored)
- **label source:** `None` (none)
- **problem patterns:** ['binary_search_standard']
- **proposed required:** _(none — no applicable independent label)_
- **proposed optional:** _(none)_
- **proposed excluded:** _(none)_
- **rationale:** screen failed: disjoint_from_label

```python
def search(nums, target):
    def lookup(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            return lookup(mid + 1, hi)
        return lookup(lo, mid - 1)

    return lookup(0, len(nums) - 1)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc3236_fam1 — Smallest Missing Integer Greater Than Sequential Prefix Sum (LC 3236)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_GENERIC`
- **members:** 7 (db_sub_194, db_sub_49, db_sub_51, missing_scalar, missing_scalar_alt, missing_scalar_renamed, missing_set_scalar)
- **sources:** authored, pathforge_db
- **reference solution:** `S0089` (pathforge_db)
- **label source:** `authored_family_proposal` (family_level)
- **problem patterns:** _(none)_
- **proposed required:** ['sequential_accumulation']
- **proposed optional:** ['forward_pointer_advance']
- **proposed excluded:** _(none)_
- **rationale:** LC 3236 has no curated problem pattern; the scalar running-total family computes a sequential prefix sum of the leading run.

```python
class Solution:
    def missingInteger(self, nums: List[int]) -> int:
        i = 1
        summ = nums[0]

        while i < len(nums) and nums[i] == nums[i - 1] + 1:
            summ += nums[i]
            i += 1

        while summ in nums:
            summ += 1

        return summ
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc3236_fam2 — Smallest Missing Integer Greater Than Sequential Prefix Sum (LC 3236)

- **approval_state:** `PENDING_REVIEW`  •  **divergence_state:** `LABEL_GENERIC`
- **members:** 1 (missing_prefix_array)
- **sources:** authored
- **reference solution:** `S0092` (authored)
- **label source:** `authored_family_proposal` (family_level)
- **problem patterns:** _(none)_
- **proposed required:** ['sequential_accumulation']
- **proposed optional:** ['forward_pointer_advance']
- **proposed excluded:** _(none)_
- **rationale:** LC 3236 prefix-array family builds a cumulative prefix list before locating the missing integer.

```python
def missing_integer(nums):
    n = len(nums)
    prefix = [nums[0]]
    j = 1
    while j < n and nums[j] == nums[j - 1] + 1:
        prefix.append(prefix[-1] + nums[j])
        j += 1
    candidate = prefix[-1]
    present = set(nums)
    while candidate in present:
        candidate += 1
    return candidate
```

_reviewer notes:_ _(to be completed by the reviewer)_

---
