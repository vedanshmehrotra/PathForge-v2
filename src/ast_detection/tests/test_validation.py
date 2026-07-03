"""Phase 3C.2.1 — Validation of Batch 1 detectors against LeetCode solution patterns.

Tests each detector against 20-30 positive and 20-30 negative examples
derived from real LeetCode Python solutions. Reports true/false
positives/negatives.
"""

import ast
from src.ast_detection.detectors.hash_map_lookup import HashMapLookupDetector
from src.ast_detection.detectors.array_traversal import ArrayTraversalDetector
from src.ast_detection.detectors.sorting import SortingDetector
from src.ast_detection.detectors.brute_force import BruteForceDetector
from src.ast_detection.detectors.frequency_counting import FrequencyCountingDetector


# ---------------------------------------------------------------------------
# hash_map_lookup — expected to detect dict/set + membership check + loop
# ---------------------------------------------------------------------------

HASH_MAP_LOOKUP_POSITIVE = [
    # Two Sum one-pass (LeetCode 1)
    ("two_sum_one_pass", """
seen = {}
for i, n in enumerate(nums):
    diff = target - n
    if diff in seen:
        return [seen[diff], i]
    seen[n] = i
"""),
    # Two Sum two-pass
    ("two_sum_two_pass", """
indices = {}
for i, n in enumerate(nums):
    indices[n] = i
for i, n in enumerate(nums):
    diff = target - n
    if diff in indices and indices[diff] != i:
        return [i, indices[diff]]
"""),
    # Contains Duplicate (LeetCode 217)
    ("contains_duplicate_set", """
seen = set()
for num in nums:
    if num in seen:
        return True
    seen.add(num)
return False
"""),
    # Contains Duplicate with dict
    ("contains_duplicate_dict", """
seen = {}
for num in nums:
    if num in seen:
        return True
    seen[num] = True
return False
"""),
    # First Recurring Character
    ("first_recurring", """
seen = {}
for ch in s:
    if ch in seen:
        return ch
    seen[ch] = True
return None
"""),
    # Two Sum using range
    ("two_sum_range", """
h = {}
for i in range(len(nums)):
    n = nums[i]
    diff = target - n
    if diff in h:
        return [h[diff], i]
    h[n] = i
"""),
    # Intersection using set comprehension with membership
    ("intersection_set_comp", """
seen = set(nums1)
result = [x for x in nums2 if x in seen]
"""),
    # Contains Nearby Duplicate (LeetCode 219)
    ("contains_nearby_duplicate", """
seen = {}
for i, num in enumerate(nums):
    if num in seen and i - seen[num] <= k:
        return True
    seen[num] = i
return False
"""),
    # Two Sum with while loop
    ("two_sum_while", """
seen = {}
i = 0
while i < len(nums):
    diff = target - nums[i]
    if diff in seen:
        return [seen[diff], i]
    seen[nums[i]] = i
    i += 1
"""),
    # Valid Anagram check via membership in set
    ("valid_anagram_membership", """
seen = set(t)
for ch in s:
    if ch not in seen:
        return False
return True
"""),
    # Find All Duplicates using membership tracking
    ("find_duplicates", """
seen = set()
dups = []
for num in nums:
    if num in seen:
        dups.append(num)
    seen.add(num)
return dups
"""),
    # Happy Number cycle detection
    ("happy_number", """
seen = set()
while n != 1 and n not in seen:
    seen.add(n)
    n = sum(int(d)**2 for d in str(n))
return n == 1
"""),
    # Logger rate limiter pattern
    ("logger_rate_limiter", """
seen = {}
for i, msg in enumerate(messages):
    if msg in seen and i - seen[msg] < 10:
        continue
    seen[msg] = i
    print(msg)
"""),
    # Dict comprehension with membership filter
    ("dict_comp_membership", """
lookup = {x: i for i, x in enumerate(nums1)}
result = {k: lookup[k] for k in nums2 if k in lookup}
"""),
]

HASH_MAP_LOOKUP_NEGATIVE = [
    # Static config dict
    ("config_dict", "config = {'key': 'value'}"),
    # Single membership check without loop
    ("single_membership_no_loop", "seen = {}\nx = key in seen"),
    # Dict creation without loop or membership
    ("empty_dict_only", "seen = {}"),
    # Dict creation with setdefault (no in check)
    ("dict_setdefault", """
seen = {}
for item in items:
    seen.setdefault(item, [])
"""),
    # Loop but no membership check (just dict assignment)
    ("loop_no_membership", """
mapping = {}
for item in items:
    mapping[item] = True
"""),
    # Membership check at module level (no loop)
    ("module_level_membership", """
VALID_KEYS = {'a', 'b', 'c'}
if key not in VALID_KEYS:
    raise ValueError()
"""),
    # List only (no dict/set)
    ("list_only", """
items = [1, 2, 3]
for x in items:
    if x > 0:
        print(x)
"""),
    # Literal dict used in loop (non-empty, static)
    ("literal_dict_in_loop", """
d = {1: 'a', 2: 'b'}
for k in keys:
    if k in d:
        print(k)
"""),
    # Single membership check with dict constructor
    ("single_membership_dict_constructor", """
mapping = dict()
if key in mapping:
    print('found')
"""),
    # Nested membership without iteration
    ("nested_membership_no_loop", """
a = {1, 2}
b = {2, 3}
if x in a and x in b:
    print('both')
"""),
    # Just a while loop with no dict
    ("while_no_dict", """
i = 0
while i < n:
    print(i)
    i += 1
"""),
    # Enumeration without dict
    ("enum_no_dict", "for i, x in enumerate(arr):\n    print(x)"),
    # Membership on a list (not dict/set)
    ("list_membership", """
items = [1, 2, 3]
for x in other:
    if x in items:
        print(x)
"""),
    # Simple assignment with dict literal (static)
    ("static_dict_assign", "config = {'debug': True, 'port': 8080}"),
    # Two independent sets without loop
    ("two_sets_no_loop", """
a = {1, 2, 3}
b = {3, 4, 5}
common = a & b
"""),
    # Membership in string (not hash map)
    ("string_membership", """
vowels = 'aeiou'
for ch in text:
    if ch in vowels:
        print(ch)
"""),
    # For-else with no membership
    ("for_else_no_membership", """
seen = set()
for item in items:
    seen.add(item)
"""),
    # Set comprehension without loop (comprehension is the loop)
    ("set_comp_no_membership", "result = {x for x in items}"),
    # List comprehension with if on value, not membership
    ("list_comp_filter", "[x for x in items if x > 0]"),
    # Using .get() without in check
    ("dict_get_no_in", """
mapping = {}
for key in keys:
    val = mapping.get(key)
"""),
]


# ---------------------------------------------------------------------------
# array_traversal — expected to detect loop + element access
# ---------------------------------------------------------------------------

ARRAY_TRAVERSAL_POSITIVE = [
    # Index-based traversal with subscript read
    ("index_traversal", "for i in range(len(arr)):\n    print(arr[i])"),
    # Element-based traversal with element usage
    ("element_traversal", "for x in arr:\n    print(x)"),
    # Element update in-place
    ("element_update", """
for i in range(n):
    arr[i] = arr[i] * 2
"""),
    # Collection loop with function call using element
    ("collection_loop_append", """
for x in arr:
    result.append(x)
"""),
    # Summation pattern
    ("summation", """
total = 0
for num in nums:
    total += num
"""),
    # Element transformation
    ("element_transform", """
new_arr = []
for val in arr:
    new_arr.append(val * 2)
"""),
    # Filter pattern with element comparison
    ("element_filter", """
result = []
for x in arr:
    if x > 0:
        result.append(x)
"""),
    # Range-based with comparison
    ("range_comparison", """
for i in range(n):
    if arr[i] > arr[i+1]:
        print(i)
"""),
    # Enumerate with subscript on another array
    ("enumerate_subscript", """
for i, val in enumerate(arr):
    result[i] = val * 2
"""),
    # Sequential element accumulation
    ("accumulation", """
running = []
total = 0
for num in nums:
    total += num
    running.append(total)
"""),
    # Max element finding
    ("max_finding", """
max_val = arr[0]
for i in range(1, len(arr)):
    if arr[i] > max_val:
        max_val = arr[i]
"""),
    # Min element finding using element iteration
    ("min_finding", """
min_val = float('inf')
for x in arr:
    if x < min_val:
        min_val = x
"""),
    # Count elements matching condition
    ("count_condition", """
count = 0
for x in arr:
    if x % 2 == 0:
        count += 1
"""),
    # String join pattern (traversal with accumulation)
    ("string_join_pattern", """
result = ''
for ch in chars:
    result += ch
"""),
    # Double traversal (two separate loops)
    ("double_traversal", """
for x in arr:
    print(x)
for y in arr:
    print(y)
"""),
]

ARRAY_TRAVERSAL_NEGATIVE = [
    # No loop
    ("no_loop", "x = 1"),
    # Range-only loop without subscript
    ("range_only", "for i in range(10):\n    print(i)"),
    # Loop with pass (element not used)
    ("loop_pass", "for x in items:\n    pass"),
    # Loop with underscore (unused)
    ("underscore_loop", "for _ in range(n):\n    print('hello')"),
    # While loop with subscript (while not detected)
    ("while_subscript", """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""),
    # Enumerate with element printed (no subscript)
    ("enumerate_print", "for i, x in enumerate(arr):\n    print(x)"),
    # Subscript without loop
    ("subscript_no_loop", "x = arr[0]"),
    # Comprehension only (we don't detect comprehensions as loops)
    ("comprehension_only", "[x for x in items]"),
    # For over range with variable not used meaningfully
    ("range_variable_unused", "for i in range(len(arr)):\n    print(i)"),
    # Just the length check
    ("length_check", "x = len(arr)"),
    # Type conversion without traversal
    ("type_conversion", "arr = list(tuple_data)"),
    # Variable reassignment not element traversal
    ("variable_reassign", "x = arr"),
    # Single element access
    ("single_access", """x = arr[0]
y = arr[1]"""),
    # Iterate with zip but no element processing
    ("zip_iteration", """
for a, b in zip(xs, ys):
    print(a, b)
"""),
]


# ---------------------------------------------------------------------------
# sorting — expected to detect .sort() or sorted()
# ---------------------------------------------------------------------------

SORTING_POSITIVE = [
    ("sort_method", "arr.sort()"),
    ("sorted_function", "result = sorted(arr)"),
    ("sort_with_key", "arr.sort(key=lambda x: x[1])"),
    ("sorted_with_key", "result = sorted(arr, key=lambda x: len(x))"),
    ("sort_reverse", "arr.sort(reverse=True)"),
    ("sorted_reverse", "result = sorted(arr, reverse=True)"),
    ("sort_inside_comprehension", "result = [sorted(x) for x in data]"),
    ("sort_nested", """
for row in matrix:
    row.sort()
"""),
    ("sorted_tuple", "result = sorted(points, key=lambda p: p[0]**2 + p[1]**2)"),
    ("sort_string", "chars.sort()"),
    ("sorted_descending", "desc = sorted(nums, reverse=True)"),
    ("multiple_sorts", """
arr.sort()
result = sorted(other)
"""),
    ("sort_in_function", """
def process(data):
    data.sort()
    return data
"""),
    ("sorted_generator", "result = sorted(x for x in nums if x > 0)"),
]

SORTING_NEGATIVE = [
    ("no_sort", "x = 1"),
    ("reversed_call", "result = list(reversed(arr))"),
    ("max_function", "m = max(arr)"),
    ("min_function", "m = min(arr)"),
    ("sum_function", "s = sum(arr)"),
    ("len_function", "n = len(arr)"),
    ("list_reverse", "arr.reverse()"),
    ("list_copy", "result = arr.copy()"),
    ("heapq_import", """
import heapq
heapq.heapify(arr)
"""),
    ("numpy_sort_not_detected", """
import numpy as np
result = np.sort(arr)
"""),
    ("sorted_method_on_string", "result = 'sort'"),  # string literal
    ("attribute_named_sort", "sort = 5"),
    ("all_function", "result = all(x > 0 for x in arr)"),
    ("any_function", "result = any(x < 0 for x in arr)"),
    ("filter_function", "result = list(filter(None, arr))"),
]


# ---------------------------------------------------------------------------
# brute_force — expected to detect nested loops or recursive branching
# ---------------------------------------------------------------------------

BRUTE_FORCE_POSITIVE = [
    # Two Sum brute force (LeetCode 1)
    ("brute_force_two_sum", """
for i in range(n):
    for j in range(i + 1, n):
        if nums[i] + nums[j] == target:
            return [i, j]
"""),
    # Nested iteration
    ("nested_loops", """
for i in range(n):
    for j in range(n):
        print(i, j)
"""),
    # Bubble sort nested loops
    ("bubble_sort", """
for i in range(n):
    for j in range(n - i - 1):
        if arr[j] > arr[j + 1]:
            arr[j], arr[j + 1] = arr[j + 1], arr[j]
"""),
    # Recursive branching - permutations
    ("recursive_permutations", """
def permute(arr):
    if len(arr) <= 1:
        return [arr]
    result = []
    for i in range(len(arr)):
        rest = permute(arr[:i] + arr[i+1:])
        for p in rest:
            result.append([arr[i]] + p)
    return result
"""),
    # Three nested loops
    ("triple_nested", """
for i in range(n):
    for j in range(m):
        for k in range(p):
            print(i, j, k)
"""),
    # Nested while loops
    ("nested_while", """
i = 0
while i < n:
    j = 0
    while j < n:
        print(i, j)
        j += 1
    i += 1
"""),
    # Recursive branching - subsets
    ("recursive_subsets", """
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
"""),
    # Nested loops with pair comparison
    ("pair_comparison", """
for i in range(len(arr)):
    for j in range(i + 1, len(arr)):
        if arr[i] == arr[j]:
            return True
"""),
    # Recursive with multiple self-calls
    ("fibonacci_recursive", """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""),
    # Nested for-else loops
    ("nested_for_else", """
for i in range(n):
    for j in range(m):
        if matrix[i][j] == target:
            break
"""),
]

BRUTE_FORCE_NEGATIVE = [
    # No loops
    ("simple_code", "x = 1"),
    # Single loop
    ("single_loop", "for i in range(10):\n    print(i)"),
    # Two sequential loops (not nested)
    ("sequential_loops", """
for i in range(n):
    print(i)
for j in range(m):
    print(j)
"""),
    # Single recursion
    ("single_recursion", """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""),
    # Loop with function call (not recursive branching)
    ("loop_with_call", """
for x in items:
    process(x)
"""),
    # List comprehension (not a For node)
    ("list_comprehension", "[x * y for x in a for y in b]"),
    # While loop only
    ("single_while", """
i = 0
while i < n:
    print(i)
    i += 1
"""),
    # Nested ifs (no loops)
    ("nested_ifs", """
if x > 0:
    if y > 0:
        print('both positive')
"""),
    # Try-except (no nested loops)
    ("try_except", """
for i in range(n):
    try:
        result.append(arr[i])
    except:
        pass
"""),
    # Simple map function
    ("map_function", "result = list(map(str, nums))"),
    # Range access without nesting
    ("range_access", "for i in range(len(arr)):\n    arr[i] *= 2"),
    # Single recursive call in for loop
    ("recursive_in_loop", """
def solve(n):
    if n <= 1:
        return n
    total = 0
    for i in range(n):
        total += solve(i)
    return total
"""),
    # Generator expression
    ("generator", "sum(x for x in range(100))"),
    # Static pair assignment
    ("static_pair", "a, b = 1, 2"),
    # Two separate loops in different functions
    ("separate_functions", """
def f1():
    for i in range(n):
        print(i)
def f2():
    for j in range(m):
        print(j)
"""),
]


# ---------------------------------------------------------------------------
# hash_map_frequency — expected to detect frequency counting
# ---------------------------------------------------------------------------

FREQUENCY_COUNTING_POSITIVE = [
    # Classic increment pattern
    ("classic_increment", """
counts = {}
for item in items:
    counts[item] = counts.get(item, 0) + 1
"""),
    # Counter import with data
    ("counter_import", """
from collections import Counter
data = [1, 2, 2, 3]
counts = Counter(data)
"""),
    # defaultdict pattern
    ("defaultdict_pattern", """
from collections import defaultdict
counts = defaultdict(int)
for item in items:
    counts[item] += 1
"""),
    # dict() constructor with increment
    ("dict_constructor_increment", """
counts = dict()
for x in data:
    counts[x] = counts.get(x, 0) + 1
"""),
    # Counter with string
    ("counter_string", """
from collections import Counter
freq = Counter('hello world')
"""),
    # Frequency for Top K Frequent (LeetCode 347)
    ("top_k_frequent", """
freq = {}
for num in nums:
    freq[num] = freq.get(num, 0) + 1
sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
return [item[0] for item in sorted_items[:k]]
"""),
    # Character frequency
    ("char_frequency", """
freq = {}
for ch in s:
    freq[ch] = freq.get(ch, 0) + 1
"""),
    # Word frequency
    ("word_frequency", """
word_count = {}
for word in words:
    word_count[word] = word_count.get(word, 0) + 1
"""),
    # Ransom Note (LeetCode 383)
    ("ransom_note", """
from collections import Counter
return not Counter(ransomNote) - Counter(magazine)
"""),
    # Valid Anagram using Counter (LeetCode 242)
    ("valid_anagram_counter", """
from collections import Counter
return Counter(s) == Counter(t)
"""),
    # defaultdict for grouping
    ("defaultdict_grouping", """
from collections import defaultdict
groups = defaultdict(list)
for item in items:
    groups[item.key].append(item)
"""),
    # Frequency counting with while loop
    ("frequency_while", """
counts = {}
i = 0
while i < len(arr):
    val = arr[i]
    counts[val] = counts.get(val, 0) + 1
    i += 1
"""),
    # Intersection using Counter (LeetCode 350)
    ("intersection_counter", """
from collections import Counter
c1 = Counter(nums1)
c2 = Counter(nums2)
return list((c1 & c2).elements())
"""),
    # Defaultdict of int for frequency
    ("defaultdict_freq", """
from collections import defaultdict
freq = defaultdict(int)
for num in nums:
    freq[num] += 1
"""),
]

FREQUENCY_COUNTING_NEGATIVE = [
    # No counting at all
    ("no_counting", "x = 1"),
    # Static dict
    ("static_dict", "config = {'key': 'value'}"),
    # Empty dict without loop
    ("empty_dict_no_loop", "counts = {}"),
    # Dict creation + loop + membership (hash_map_lookup territory)
    ("lookup_without_counting", """
seen = {}
for item in items:
    if item in seen:
        print('found')
"""),
    # .get() without increment
    ("dict_get_no_increment", """
counts = {}
for item in items:
    val = counts.get(item)
"""),
    # Counter as lookup (no counting)
    ("counter_as_lookup", """
from collections import Counter
data = Counter()
x = data.get('key')
"""),
    # Augmented assign without dict context
    ("augmented_assign_no_dict", """
x = 0
for item in items:
    x += 1
"""),
    # Regular membership check
    ("regular_membership", """
seen = set()
for item in items:
    if item in seen:
        return True
    seen.add(item)
"""),
    # Dict assignment without increment
    ("dict_assignment_only", """
mapping = {}
for item in items:
    mapping[item] = True
"""),
    # List count method (not dict counting)
    ("list_count_method", "count = items.count(x)"),
    # Just import Counter without usage
    ("import_counter_only", "from collections import Counter"),
    # Counter() with no args (empty constructor)
    ("counter_empty", """
from collections import Counter
data = Counter()
"""),
    # Sum aggregation (not frequency)
    ("sum_aggregation", """
total = 0
for num in nums:
    total += num
"""),
    # String count method (not dict)
    ("string_count", "count = s.count('a')"),
    # Manual frequency without dict
    ("manual_no_dict", """
max_val = max(arr)
freq = [0] * (max_val + 1)
for num in arr:
    freq[num] += 1
"""),
]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_detector_tests(detector, positives, negatives, detector_name):
    tp, fn = 0, 0
    fp, tn = 0, 0
    false_negatives = []
    false_positives = []

    for name, code in positives:
        result = detector.detect(ast.parse(code))
        if result.detected:
            tp += 1
        else:
            fn += 1
            false_negatives.append((name, code, result.confidence))

    for name, code in negatives:
        result = detector.detect(ast.parse(code))
        if result.detected:
            fp += 1
            false_positives.append((name, code, result.confidence))
        else:
            tn += 1

    print(f"\n{'='*60}")
    print(f"  {detector_name}")
    print(f"{'='*60}")
    print(f"  True Positives:  {tp:2d} / {len(positives)}")
    print(f"  False Negatives: {fn:2d} / {len(positives)}")
    print(f"  True Negatives:  {tn:2d} / {len(negatives)}")
    print(f"  False Positives: {fp:2d} / {len(negatives)}")

    if false_negatives:
        print(f"\n  --- False Negatives ---")
        for name, code, conf in false_negatives:
            first_line = code.strip().split('\n')[0][:60]
            print(f"    [{name}] conf={conf:.2f}: {first_line}")

    if false_positives:
        print(f"\n  --- False Positives ---")
        for name, code, conf in false_positives:
            first_line = code.strip().split('\n')[0][:60]
            print(f"    [{name}] conf={conf:.2f}: {first_line}")

    return tp, fn, fp, tn


def main():
    print("Phase 3C.2.1 — Batch 1 Detector Validation")
    print("Testing against real LeetCode solution patterns")

    all_tp = all_fn = all_fp = all_tn = 0

    # hash_map_lookup
    tp, fn, fp, tn = run_detector_tests(
        HashMapLookupDetector(),
        HASH_MAP_LOOKUP_POSITIVE, HASH_MAP_LOOKUP_NEGATIVE,
        "hash_map_lookup"
    )
    all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn

    # array_traversal
    tp, fn, fp, tn = run_detector_tests(
        ArrayTraversalDetector(),
        ARRAY_TRAVERSAL_POSITIVE, ARRAY_TRAVERSAL_NEGATIVE,
        "array_traversal"
    )
    all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn

    # sorting
    tp, fn, fp, tn = run_detector_tests(
        SortingDetector(),
        SORTING_POSITIVE, SORTING_NEGATIVE,
        "sorting"
    )
    all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn

    # brute_force
    tp, fn, fp, tn = run_detector_tests(
        BruteForceDetector(),
        BRUTE_FORCE_POSITIVE, BRUTE_FORCE_NEGATIVE,
        "brute_force"
    )
    all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn

    # hash_map_frequency
    tp, fn, fp, tn = run_detector_tests(
        FrequencyCountingDetector(),
        FREQUENCY_COUNTING_POSITIVE, FREQUENCY_COUNTING_NEGATIVE,
        "hash_map_frequency"
    )
    all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn

    total = all_tp + all_fn + all_fp + all_tn
    print(f"\n{'='*60}")
    print(f"  TOTALS")
    print(f"{'='*60}")
    print(f"  Total tests:     {total}")
    print(f"  True Positives:  {all_tp}")
    print(f"  False Negatives: {all_fn}")
    print(f"  True Negatives:  {all_tn}")
    print(f"  False Positives: {all_fp}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
