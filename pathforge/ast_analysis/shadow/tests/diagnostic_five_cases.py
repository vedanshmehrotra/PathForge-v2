"""Diagnostic trace for the five reported failure cases (survey only, no assertions).

Reconstructs each reported implementation, runs it through the shadow pipeline,
and prints: facts -> techniques -> strategies -> solution-group evaluation,
using the SAME group construction the production loader uses
(_split_csv_patterns_to_groups) for the expected legacy patterns.

Run:  python -m pathforge.ast_analysis.shadow.tests.diagnostic_five_cases
"""
import ast
import sys

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.services.problem_resolver import _split_csv_patterns_to_groups
from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING


# ---- Case 1: LC 21 Merge Two Sorted Lists (expected: two_pointers_same) ----
CASE_1 = """
class Solution:
    def mergeTwoLists(self, list1, list2):
        dummy = ListNode()
        tail = dummy
        while list1 and list2:
            if list1.val <= list2.val:
                tail.next = list1
                list1 = list1.next
            else:
                tail.next = list2
                list2 = list2.next
            tail = tail.next
        tail.next = list1 if list1 else list2
        return dummy.next
"""

# ---- Case 2: LC 29 Divide Two Integers (expected: brute force) ----
CASE_2 = """
class Solution:
    def divide(self, dividend, divisor):
        if dividend == -(2 ** 31) and divisor == -1:
            return 2 ** 31 - 1
        negative = (dividend < 0) != (divisor < 0)
        dividend, divisor = abs(dividend), abs(divisor)
        quotient = 0
        while dividend >= divisor:
            value = divisor
            multiple = 1
            while dividend >= (value << 1):
                value <<= 1
                multiple <<= 1
            dividend -= value
            quotient += multiple
        return -quotient if negative else quotient
"""

# ---- Case 3: LC 3903 Smallest Stable Index I (expected: two_pointers_same + prefix_sum) ----
# Reconstruction of the described structure: traverse, max(...) range condition,
# index candidate, conditional candidate update, return smallest index or -1.
CASE_3 = """
class Solution:
    def smallestStableIndex(self, nums):
        n = len(nums)
        total = sum(nums)
        best = -1
        for i in range(n):
            if max(nums[i:]) <= total - nums[i]:
                if best == -1:
                    best = i
        return best
"""

# ---- Case 4: LC 3875 Construct Uniform Parity Array I (expected: greedy_local) ----
CASE_4 = """
class Solution:
    def constructUniformParityArray(self, nums):
        candidate = -1
        for x in nums:
            if x % 2 == 1:
                candidate = x
                break
        if candidate == -1:
            return []
        for i in range(len(nums)):
            if nums[i] % 2 == 0:
                nums[i] = candidate
        return nums
"""

# ---- Case 5: LC 3876 Construct Uniform Parity Array II (expected: greedy_local) ----
CASE_5 = """
class Solution:
    def constructUniformParityArray(self, nums):
        candidate = -1
        for x in nums:
            if x % 2 == 1 and x > candidate:
                candidate = x
        for i in range(len(nums)):
            if nums[i] % 2 == 0:
                nums[i] = candidate
        return nums
"""


CASES = [
    ("CASE 1 / LC21", CASE_1, ["two_pointers_same"]),
    ("CASE 2 / LC29", CASE_2, ["brute_force"]),
    ("CASE 3 / LC3903", CASE_3, ["two_pointers_same", "prefix_sum"]),
    ("CASE 4 / LC3875", CASE_4, ["greedy_local"]),
    ("CASE 5 / LC3876", CASE_5, ["greedy_local"]),
]


def trace(label, code, expected_patterns):
    print("=" * 78)
    print(f"{label}   expected legacy patterns = {expected_patterns}")
    print("=" * 78)

    for p in expected_patterns:
        m = PATTERN_TO_V1_MAPPING.get(p)
        print(f"  mapping[{p}] = {m if m else 'UNMAPPED (not a known legacy pattern)'}")

    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    print(f"\n  [facts] {len(facts)}")
    for f in facts:
        print(f"      {f.fact_type:32} {f.attributes}")

    techs = detect_techniques(facts)
    print(f"\n  [techniques] {len(techs)}")
    for t in techs:
        print(f"      {t.technique_id:32} conf={t.presence_confidence} centrality={t.centrality}")

    strats = evaluate_strategies(techs, facts)
    print(f"\n  [strategies] {len(strats)}")
    for s in strats:
        print(f"      {s.strategy_id:32} conf={s.confidence}")

    groups = _split_csv_patterns_to_groups(expected_patterns, {}, 1.0, "llm_proposed")
    print(f"\n  [solution groups] {len(groups)}")
    for g in groups:
        print(f"      {g['id']}: required={g['required']} optional={g.get('optional')} "
              f"excluded={g['excluded']} threshold={g.get('threshold', 0.5)}")

    outcome = evaluate_solution_groups(groups, techs, strats, facts)
    print(f"\n  [match] outcome={outcome.outcome} primary_strategy={outcome.primary_strategy}")
    for r in outcome.reasoning:
        print(f"      {r}")
    print()


if __name__ == "__main__":
    for label, code, patterns in CASES:
        trace(label, code, patterns)
