# Ground-Truth POC — Human Review Sheet

POC version: `1.0.0`  •  taxonomy: `v1`

**Reviewer-facing artifact.** Analyzer detections are deliberately NOT
shown here (see `label_comparison.json` for the post-hoc comparison).
No label is auto-approved: every entry starts `PENDING_REVIEW`.

- Label source: `problems.pattern (live PostgreSQL snapshot, read-only)`
- Families: **31**  •  pending review: **29**  •  no independent label: **2**

> **Known granularity limitation (PROVISIONAL):** curated
> `problems.pattern` metadata is *problem-level*, not family-level, so the
> proposal below is not family-specific. A human reviewer must assign
> per-family concepts. Recorded as an OPEN decision in the POC report.

---

## lc1_fam1 — Two Sum (LC 1)

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0001, S0002)
- **sources:** pathforge_db
- **reference solution:** `S0001` (pathforge_db) — `submissions.id=11`
- **proposed external pattern(s):** ['hash_map_lookup']
- **proposed required (V1):** ['hash_lookup']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

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

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0003)
- **sources:** authored
- **reference solution:** `S0003` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#two_sum_brute_force`
- **proposed external pattern(s):** ['hash_map_lookup']
- **proposed required (V1):** ['hash_lookup']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def two_sum_brute_force(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc1_fam3 — Two Sum (LC 1)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0004)
- **sources:** authored
- **reference solution:** `S0004` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#two_sum_sorted_two_pointer`
- **proposed external pattern(s):** ['hash_map_lookup']
- **proposed required (V1):** ['hash_lookup']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def two_sum_sorted_two_pointer(nums, target):
    ordered = sorted(range(len(nums)), key=lambda i: nums[i])
    lo = 0
    hi = len(ordered) - 1
    while lo < hi:
        total = nums[ordered[lo]] + nums[ordered[hi]]
        if total == target:
            return [ordered[lo], ordered[hi]]
        if total < target:
            lo += 1
        else:
            hi -= 1
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc1_fam4 — Two Sum (LC 1)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0005)
- **sources:** authored
- **reference solution:** `S0005` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#two_sum_two_pass`
- **proposed external pattern(s):** ['hash_map_lookup']
- **proposed required (V1):** ['hash_lookup']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def two_sum_two_pass(nums, target):
    index_of = {}
    for i, value in enumerate(nums):
        index_of[value] = i
    for i, value in enumerate(nums):
        complement = target - value
        if complement in index_of and index_of[complement] != i:
            return [i, index_of[complement]]
    return []
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam1 — Merge Two Sorted Lists (LC 21)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0006)
- **sources:** pathforge_db
- **reference solution:** `S0006` (pathforge_db) — `submissions.id=252`
- **proposed external pattern(s):** ['two_pointers_same']
- **proposed required (V1):** ['forward_pointer_advance']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

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

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0007)
- **sources:** authored
- **reference solution:** `S0007` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#merge_collect_sort`
- **proposed external pattern(s):** ['two_pointers_same']
- **proposed required (V1):** ['forward_pointer_advance']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def merge_collect_sort(head_a, head_b):
    values = []
    while head_a is not None:
        values.append(head_a.val)
        head_a = head_a.next
    while head_b is not None:
        values.append(head_b.val)
        head_b = head_b.next
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

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0008)
- **sources:** authored
- **reference solution:** `S0008` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#merge_iter_dummy`
- **proposed external pattern(s):** ['two_pointers_same']
- **proposed required (V1):** ['forward_pointer_advance']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def merge_iter_dummy(head_a, head_b):
    dummy = ListNode(0)
    tail = dummy
    while head_a is not None and head_b is not None:
        if head_a.val < head_b.val:
            tail.next = head_a
            head_a = head_a.next
        else:
            tail.next = head_b
            head_b = head_b.next
        tail = tail.next
    if head_a is not None:
        tail.next = head_a
    else:
        tail.next = head_b
    return dummy.next
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam4 — Merge Two Sorted Lists (LC 21)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0009)
- **sources:** authored
- **reference solution:** `S0009` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#merge_recursive`
- **proposed external pattern(s):** ['two_pointers_same']
- **proposed required (V1):** ['forward_pointer_advance']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def merge_recursive(l1, l2):
    if l1 is None:
        return l2
    if l2 is None:
        return l1
    if l1.val <= l2.val:
        l1.next = merge_recursive(l1.next, l2)
        return l1
    l2.next = merge_recursive(l1, l2.next)
    return l2
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc21_fam5 — Merge Two Sorted Lists (LC 21)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0010)
- **sources:** authored
- **reference solution:** `S0010` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#merge_sentinel_swap`
- **proposed external pattern(s):** ['two_pointers_same']
- **proposed required (V1):** ['forward_pointer_advance']
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def merge_sentinel_swap(a, b):
    if a is None:
        return b
    if b is None:
        return a
    head = a if a.val <= b.val else b
    previous = None
    while a is not None and b is not None:
        if a.val <= b.val:
            chosen = a
            a = a.next
        else:
            chosen = b
            b = b.next
        if previous is not None:
            previous.next = chosen
        previous = chosen
    previous.next = a if a is not None else b
    return head
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam1 — Valid Palindrome (LC 125)

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0011, S0015)
- **sources:** authored, pathforge_db
- **reference solution:** `S0011` (pathforge_db) — `submissions.id=233`
- **proposed external pattern(s):** ['two_pointers_opposite']
- **proposed required (V1):** ['two_pointers_opposite']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['binary_search']
- **family-specific label:** False  •  **granularity:** problem_level

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
        left = 0
        right = len(s) - 1

        while left < right:
            while left < right and not s[left].isalnum():
                left += 1

            while left < right and not s[right].isalnum():
                right -= 1

            if s[left].lower() != s[right].lower():
                return False

            left += 1
            right -= 1

        return True
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam2 — Valid Palindrome (LC 125)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0012)
- **sources:** authored
- **reference solution:** `S0012` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#pal_filter_slice`
- **proposed external pattern(s):** ['two_pointers_opposite']
- **proposed required (V1):** ['two_pointers_opposite']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['binary_search']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def pal_filter_slice(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc125_fam3 — Valid Palindrome (LC 125)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0013)
- **sources:** authored
- **reference solution:** `S0013` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#pal_recursive`
- **proposed external pattern(s):** ['two_pointers_opposite']
- **proposed required (V1):** ['two_pointers_opposite']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['binary_search']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def pal_recursive(s):
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

## lc125_fam4 — Valid Palindrome (LC 125)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0014)
- **sources:** authored
- **reference solution:** `S0014` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#pal_regex_two_ptr`
- **proposed external pattern(s):** ['two_pointers_opposite']
- **proposed required (V1):** ['two_pointers_opposite']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['binary_search']
- **family-specific label:** False  •  **granularity:** problem_level

```python
import re


def pal_regex_two_ptr(s):
    letters = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    left = 0
    right = len(letters) - 1
    while left < right:
        if letters[left] != letters[right]:
            return False
        left += 1
        right -= 1
    return True
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc209_fam1 — Minimum Size Subarray Sum (LC 209)

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0016, S0017)
- **sources:** pathforge_db
- **reference solution:** `S0016` (pathforge_db) — `submissions.id=190`
- **proposed external pattern(s):** ['prefix_sum', 'sliding_window_variable']
- **proposed required (V1):** ['sequential_accumulation', 'sliding_window']
- **proposed optional (V1):** ['iterative_table_filling', 'loop_state_tracking']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
class Solution:
    def minSubArrayLen(self, target: int, nums: List[int]) -> int:
        left = 0
        summ = 0
        ans = len(nums) + 1

        for right in range(len(nums)):
            summ += nums[right]

            while summ >= target:
                ans = min(ans, right - left + 1)
                summ -= nums[left]
                left += 1

        if ans == len(nums) + 1:
            return 0

        return ans
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc209_fam2 — Minimum Size Subarray Sum (LC 209)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0018)
- **sources:** authored
- **reference solution:** `S0018` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#min_subarray_brute`
- **proposed external pattern(s):** ['prefix_sum', 'sliding_window_variable']
- **proposed required (V1):** ['sequential_accumulation', 'sliding_window']
- **proposed optional (V1):** ['iterative_table_filling', 'loop_state_tracking']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def min_subarray_brute(target, nums):
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

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0019, S0020)
- **sources:** authored
- **reference solution:** `S0019` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#min_subarray_prefix_bs`
- **proposed external pattern(s):** ['prefix_sum', 'sliding_window_variable']
- **proposed required (V1):** ['sequential_accumulation', 'sliding_window']
- **proposed optional (V1):** ['iterative_table_filling', 'loop_state_tracking']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
import bisect


def min_subarray_prefix_bs(target, nums):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    best = len(nums) + 1
    for i in range(len(nums)):
        wanted = prefix[i] + target
        j = bisect.bisect_left(prefix, wanted, i + 1)
        if j <= len(nums):
            best = min(best, j - i)
    return 0 if best == len(nums) + 1 else best
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc242_fam1 — Valid Anagram (LC 242)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0021)
- **sources:** authored
- **reference solution:** `S0021` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#anagram_array26`
- **proposed external pattern(s):** ['hash_map_frequency']
- **proposed required (V1):** ['frequency_counting']
- **proposed optional (V1):** ['hash_lookup']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def anagram_array26(s, t):
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

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0022, S0025)
- **sources:** authored
- **reference solution:** `S0022` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#anagram_counter`
- **proposed external pattern(s):** ['hash_map_frequency']
- **proposed required (V1):** ['frequency_counting']
- **proposed optional (V1):** ['hash_lookup']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
from collections import Counter


def anagram_counter(s, t):
    return Counter(s) == Counter(t)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc242_fam3 — Valid Anagram (LC 242)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0023)
- **sources:** authored
- **reference solution:** `S0023` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#anagram_manual_dict`
- **proposed external pattern(s):** ['hash_map_frequency']
- **proposed required (V1):** ['frequency_counting']
- **proposed optional (V1):** ['hash_lookup']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def anagram_manual_dict(s, t):
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

## lc242_fam4 — Valid Anagram (LC 242)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0024)
- **sources:** authored
- **reference solution:** `S0024` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#anagram_set_count`
- **proposed external pattern(s):** ['hash_map_frequency']
- **proposed required (V1):** ['frequency_counting']
- **proposed optional (V1):** ['hash_lookup']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def anagram_set_count(s, t):
    if len(s) != len(t):
        return False
    for ch in set(s):
        if s.count(ch) != t.count(ch):
            return False
    return True
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc560_fam1 — Subarray Sum Equals K (LC 560)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0026)
- **sources:** authored
- **reference solution:** `S0026` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#subarray_brute`
- **proposed external pattern(s):** ['hash_map_frequency', 'prefix_sum']
- **proposed required (V1):** ['frequency_counting', 'sequential_accumulation']
- **proposed optional (V1):** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def subarray_brute(nums, k):
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

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0027)
- **sources:** authored
- **reference solution:** `S0027` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#subarray_prefix_array_nested`
- **proposed external pattern(s):** ['hash_map_frequency', 'prefix_sum']
- **proposed required (V1):** ['frequency_counting', 'sequential_accumulation']
- **proposed optional (V1):** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def subarray_prefix_array_nested(nums, k):
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

## lc560_fam3 — Subarray Sum Equals K (LC 560)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0028)
- **sources:** authored
- **reference solution:** `S0028` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#subarray_prefix_defaultdict`
- **proposed external pattern(s):** ['hash_map_frequency', 'prefix_sum']
- **proposed required (V1):** ['frequency_counting', 'sequential_accumulation']
- **proposed optional (V1):** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
from collections import defaultdict


def subarray_prefix_defaultdict(nums, k):
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

## lc560_fam4 — Subarray Sum Equals K (LC 560)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0029)
- **sources:** authored
- **reference solution:** `S0029` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#subarray_prefix_get`
- **proposed external pattern(s):** ['hash_map_frequency', 'prefix_sum']
- **proposed required (V1):** ['frequency_counting', 'sequential_accumulation']
- **proposed optional (V1):** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def subarray_prefix_get(nums, k):
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

## lc560_fam5 — Subarray Sum Equals K (LC 560)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0030)
- **sources:** authored
- **reference solution:** `S0030` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#subarray_prefix_ifelse`
- **proposed external pattern(s):** ['hash_map_frequency', 'prefix_sum']
- **proposed required (V1):** ['frequency_counting', 'sequential_accumulation']
- **proposed optional (V1):** ['hash_lookup', 'iterative_table_filling']
- **proposed excluded (V1):** ['recursive_branching']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def subarray_prefix_ifelse(nums, k):
    seen = {0: 1}
    total = 0
    count = 0
    for value in nums:
        total += value
        target = total - k
        if target in seen:
            count += seen[target]
        if total in seen:
            seen[total] += 1
        else:
            seen[total] = 1
    return count
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam1 — Binary Search (LC 704)

- **review_state:** `PENDING_REVIEW`
- **members:** 2 (S0031, S0034)
- **sources:** authored, pathforge_db
- **reference solution:** `S0031` (pathforge_db) — `submissions.id=235`
- **proposed external pattern(s):** ['binary_search_standard']
- **proposed required (V1):** ['binary_search']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        left = 0
        right = len(nums) - 1

        while left <= right:
            mid = (left + right) // 2

            if nums[mid] == target:
                return mid

            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1

        return -1
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam2 — Binary Search (LC 704)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0032)
- **sources:** authored
- **reference solution:** `S0032` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#bs_bisect`
- **proposed external pattern(s):** ['binary_search_standard']
- **proposed required (V1):** ['binary_search']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
import bisect


def bs_bisect(nums, target):
    position = bisect.bisect_left(nums, target)
    if position < len(nums) and nums[position] == target:
        return position
    return -1
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam3 — Binary Search (LC 704)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0033)
- **sources:** authored
- **reference solution:** `S0033` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#bs_lo_hi`
- **proposed external pattern(s):** ['binary_search_standard']
- **proposed required (V1):** ['binary_search']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def bs_lo_hi(nums, target):
    lo = 0
    hi = len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if lo < len(nums) and nums[lo] == target:
        return lo
    return -1
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc704_fam4 — Binary Search (LC 704)

- **review_state:** `PENDING_REVIEW`
- **members:** 1 (S0035)
- **sources:** authored
- **reference solution:** `S0035` (authored) — `experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#bs_recursive`
- **proposed external pattern(s):** ['binary_search_standard']
- **proposed required (V1):** ['binary_search']
- **proposed optional (V1):** ['bidirectional_index_scan']
- **proposed excluded (V1):** ['two_pointers_opposite']
- **family-specific label:** False  •  **granularity:** problem_level

```python
def bs_recursive(nums, target):
    def search(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            return search(mid + 1, hi)
        return search(lo, mid - 1)

    return search(0, len(nums) - 1)
```

_reviewer notes:_ _(to be completed by the reviewer)_

---

## lc3236_fam1 — Smallest Missing Integer Greater Than Sequential Prefix Sum (LC 3236)

- **review_state:** `NO_INDEPENDENT_LABEL`
- **members:** 2 (S0036, S0037)
- **sources:** pathforge_db
- **reference solution:** `S0036` (pathforge_db) — `submissions.id=194`
- **proposed external pattern(s):** _(none — no independent label source)_
- **proposed required (V1):** _(none)_
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** _(none)_
- **family-specific label:** False  •  **granularity:** none

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

- **review_state:** `NO_INDEPENDENT_LABEL`
- **members:** 3 (S0038, S0039, S0040)
- **sources:** authored, pathforge_db
- **reference solution:** `S0038` (pathforge_db) — `submissions.id=51`
- **proposed external pattern(s):** _(none — no independent label source)_
- **proposed required (V1):** _(none)_
- **proposed optional (V1):** _(none)_
- **proposed excluded (V1):** _(none)_
- **family-specific label:** False  •  **granularity:** none

```python
def missingInteger(nums):
    i = 1
    summ = nums[0]

    while i <= len(nums) - 1 and nums[i] == nums[i - 1] + 1:
        summ += nums[i]
        i += 1

    while summ in nums:
        summ += 1

    return summ
```

_reviewer notes:_ _(to be completed by the reviewer)_

---
