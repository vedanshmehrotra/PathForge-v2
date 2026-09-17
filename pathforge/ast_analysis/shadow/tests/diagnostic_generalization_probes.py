"""Diagnostic probes for generalized weakness hypotheses (survey only).

Probes whether the failures are family-level rather than case-level:
  P1 canonical for-loop prefix sum  -> prefix_sum group
  P2 canonical same-direction array two pointers -> two_pointers_same group
  P3 fast/slow linked-list cycle    -> fast_slow_pointers group
  P4 plain while summation loop      -> does sliding_window fire?
  P5 plain while loop w/ nested doubling (LC 50-style pow) -> sliding_window?
  P6 canonical sliding window (LC 209) -> should stay sliding_window (no regression)
  P7 canonical opposite two pointers (LC 167) -> should stay two_pointers_opposite
"""
import ast
import sys

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies

PROBES = {
    "P1 for-loop prefix sum": (
        """
class Solution:
    def runningSum(self, nums):
        out = []
        total = 0
        for x in nums:
            total += x
            out.append(total)
        return out
""",
        ["prefix_sum"],
    ),
    "P2 same-direction two pointers (move zeroes)": (
        """
class Solution:
    def moveZeroes(self, nums):
        left = 0
        for right in range(len(nums)):
            if nums[right] != 0:
                nums[left], nums[right] = nums[right], nums[left]
                left += 1
""",
        ["two_pointers_same"],
    ),
    "P3 fast/slow cycle detection": (
        """
class Solution:
    def hasCycle(self, head):
        slow = head
        fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow == fast:
                return True
        return False
""",
        ["fast_slow_pointers"],
    ),
    "P4 plain while summation loop": (
        """
class Solution:
    def f(self, nums):
        total = 0
        i = 0
        while i < len(nums):
            if nums[i] > 0:
                total += nums[i]
            i += 1
        return total
""",
        ["prefix_sum"],
    ),
    "P5 nested doubling loop (fast pow)": (
        """
class Solution:
    def f(self, base, exp):
        result = 1
        while exp > 0:
            if exp % 2 == 1:
                result *= base
            base *= base
            exp //= 2
        return result
""",
        ["none"],
    ),
    "P6 canonical variable sliding window (LC209)": (
        """
class Solution:
    def minSubArrayLen(self, target, nums):
        left = 0
        total = 0
        best = float('inf')
        for right in range(len(nums)):
            total += nums[right]
            while total >= target:
                best = min(best, right - left + 1)
                total -= nums[left]
                left += 1
        return best if best != float('inf') else 0
""",
        ["sliding_window_variable"],
    ),
    "P7 canonical opposite two pointers (LC167)": (
        """
class Solution:
    def twoSum(self, numbers, target):
        left = 0
        right = len(numbers) - 1
        while left < right:
            cur = numbers[left] + numbers[right]
            if cur == target:
                return [left + 1, right + 1]
            elif cur < target:
                left += 1
            else:
                right -= 1
        return []
""",
        ["two_pointers_opposite"],
    ),
}


def run(label, code, patterns):
    print("=" * 78)
    print(f"{label}   (expected group: {patterns})")
    facts = extract_structural_facts(ast.parse(code))
    techs = detect_techniques(facts)
    strats = evaluate_strategies(techs, facts)
    print("  facts     :", sorted({f.fact_type for f in facts}))
    print("  techniques:", [f"{t.technique_id}@{t.presence_confidence}" for t in techs])
    print("  strategies:", [f"{s.strategy_id}@{s.confidence}" for s in strats])
    print()


if __name__ == "__main__":
    for label, (code, patterns) in PROBES.items():
        run(label, code, patterns)
