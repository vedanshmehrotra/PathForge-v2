"""Before/after comparison for Batch 1 (F1 + F2 + F4).

Evaluates the five reported cases against:
  BEFORE = the HEAD revision of techniques.py / strategies.py / matching.py
  AFTER  = the current working tree

The working tree is not modified: HEAD sources are read with `git show` and
executed as standalone modules that import the (unchanged) data structures.
The fact extractor is identical in both runs, so facts are extracted once.

Solution groups come from the live DB via _load_ground_truth (the honest
production view) and, for problems without a ground-truth row, from the
CSV->V1 mapping path.

Run: python -m pathforge.ast_analysis.shadow.tests.diagnostic_before_after
"""
import ast
import subprocess
import sys
import types

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques as after_tech
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies as after_strat
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups as after_match
from pathforge.services.problem_resolver import (
    _load_ground_truth, _split_csv_patterns_to_groups,
)

SHADOW = "pathforge/ast_analysis/shadow"


def _load_head_module(rel_path: str, name: str):
    src = subprocess.check_output(["git", "show", f"HEAD:{rel_path}"], text=True)
    mod = types.ModuleType(name)
    mod.__file__ = f"HEAD:{rel_path}"
    exec(compile(src, f"HEAD:{rel_path}", "exec"), mod.__dict__)
    return mod


head_techniques = _load_head_module(f"{SHADOW}/techniques.py", "head_techniques")
head_strategies = _load_head_module(f"{SHADOW}/strategies.py", "head_strategies")
head_matching = _load_head_module(f"{SHADOW}/matching.py", "head_matching")


# ---------------------------------------------------------------
# Cases: live problem IDs + reconstructed implementations
# ---------------------------------------------------------------
CASES = [
    (21, "LC21 Merge Two Sorted Lists (two_pointers_same)", """
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
"""),
    (29, "LC29 Divide Two Integers (binary_search_answer)", """
class Solution:
    def divide(self, dividend, divisor):
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
        return quotient
"""),
    (4284, "LC4284 Smallest Stable Index I (two_pointers_same + prefix_sum)", """
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
"""),
    (4256, "LC4256 Construct Uniform Parity Array I (greedy_local)", """
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
"""),
    (4258, "LC4258 Construct Uniform Parity Array II (greedy_local)", """
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
"""),
    (283, "LC283 Move Zeroes (two_pointers_same, CSV only, no GT row)", """
class Solution:
    def moveZeroes(self, nums):
        left = 0
        for right in range(len(nums)):
            if nums[right] != 0:
                nums[left], nums[right] = nums[right], nums[left]
                left += 1
"""),
    (724, "LC724 Find Pivot Index (prefix_sum, CSV only, no GT row)", """
class Solution:
    def pivotIndex(self, nums):
        total = sum(nums)
        left = 0
        for i, x in enumerate(nums):
            if left == total - left - x:
                return i
            left += x
        return -1
"""),
]

REGRESSION_CASES = [
    (167, "LC167 Two Sum II (two_pointers_opposite)", """
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
"""),
    (209, "LC209 Min Size Subarray Sum (sliding_window_variable)", """
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
"""),
    (200, "LC200 BFS/DFS family (unrelated, must not become window)", """
class Solution:
    def numIslands(self, grid):
        count = 0
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == '1':
                    count += 1
                    grid[i][j] = '0'
        return count
"""),
]


def _run(tech_fn, strat_fn, match_fn, facts, groups):
    techs = tech_fn(facts)
    strats = strat_fn(techs, facts)
    out = match_fn(groups, techs, strats, facts)
    return {
        "techniques": sorted(t.technique_id for t in techs),
        "strategies": sorted(s.strategy_id for s in strats),
        "outcome": out.outcome,
        "unmatchable": getattr(out, "unmatchable_group_ids", []),
        "reasoning": out.reasoning,
    }


def _live_groups(conn, pid):
    if conn is None:
        return []
    groups, _ = _load_ground_truth(conn, pid)
    return groups


# CSV-curated patterns for problems that have no ground-truth row yet.
# For 283/724 these two lists are what /analyze would receive once ground
# truth is prepared (and they exercise the mapping path directly).
csv_patterns_for = {
    283: ["two_pointers_same"],
    724: ["prefix_sum"],
    167: ["two_pointers_opposite"],
    209: ["sliding_window_variable"],
    200: ["bfs_shortest_path", "dfs_recursive", "union_find"],
}


def main():
    try:
        import config  # noqa: F401
        from pathforge.db.db import get_connection
        conn = get_connection()
    except Exception as exc:
        print(f"(live DB unavailable: {type(exc).__name__}: {exc})")
        conn = None

    try:
        for pid, label, code in CASES + REGRESSION_CASES:
            facts = extract_structural_facts(ast.parse(code))
            live = _live_groups(conn, pid)
            header = f"{label}   (problem_id={pid})"
            print("=" * 78)
            print(header)
            print("=" * 78)
            if live:
                for g in live:
                    print(f"  live group {g['id']}: required={g.get('required')} "
                          f"optional={g.get('optional')} authority={g.get('authority_tier')} "
                          f"patterns={g.get('patterns')}")
            else:
                print("  live groups: NONE (no ground-truth row -> analyze runs group-less)")

            group_sets = []
            if live:
                group_sets.append(("live_db", live))
            csv_patterns = list(csv_patterns_for.get(pid, []))
            for g in live or []:
                csv_patterns.extend(g.get("patterns") or [])
            csv_patterns = sorted(set(csv_patterns))
            if csv_patterns:
                group_sets.append(
                    ("csv_mapping", _split_csv_patterns_to_groups(csv_patterns, {}, 1.0, "llm_proposed"))
                )

            for source, groups in group_sets:
                print(f"\n  [{source}] groups required={[g.get('required') for g in groups]}")
                before = _run(head_techniques.detect_techniques, head_strategies.evaluate_strategies,
                              head_matching.evaluate_solution_groups, facts, groups)
                after = _run(after_tech, after_strat, after_match, facts, groups)
                for tag, res in (("BEFORE", before), ("AFTER ", after)):
                    print(f"    {tag} techniques={res['techniques']}")
                    print(f"           strategies={res['strategies']}")
                    print(f"           outcome={res['outcome']} unmatchable={res['unmatchable']}")
                changed = (before["outcome"] != after["outcome"]
                           or before["strategies"] != after["strategies"]
                           or before["techniques"] != after["techniques"])
                print(f"    DELTA  changed={changed}   "
                      f"outcome {before['outcome']} -> {after['outcome']}")
            print()
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
