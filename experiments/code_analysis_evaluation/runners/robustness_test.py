"""Robustness testing for the evaluation benchmark.

Tests whether detection depends excessively on superficial code characteristics.
Creates equivalent implementations with different variable names, loop structures,
helper functions, and equivalent syntax, then verifies detection stability.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ast_detection.run_analysis import ASTAnalysisEngine
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


# ── Robustness test cases ──────────────────────────────────────────────
# Each test case has an original implementation and variants that should
# produce the same algorithmic detection.

ROBUSTNESS_TEST_CASES = [
    {
        "category": "two_pointers_opposite",
        "description": "Two pointers with different variable names and loop styles",
        "original": {
            "code": """def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True""",
            "expected_concepts": ["two_pointers_opposite"],
        },
        "variants": [
            {
                "name": "renamed_variables",
                "code": """def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    i, j = 0, len(s) - 1
    while i < j:
        if s[i] != s[j]:
            return False
        i += 1
        j -= 1
    return True""",
                "expected_concepts": ["two_pointers_opposite"],
                "transforms_applied": ["variable_rename"],
            },
            {
                "name": "loop_style_while_not",
                "code": """def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while not left >= right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True""",
                "expected_concepts": ["two_pointers_opposite"],
                "transforms_applied": ["loop_condition_invert"],
            },
            {
                "name": "increment_style",
                "code": """def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left = left + 1
        right = right - 1
    return True""",
                "expected_concepts": ["two_pointers_opposite"],
                "transforms_applied": ["expression_style"],
            },
        ],
    },
    {
        "category": "binary_search_standard",
        "description": "Binary search with different midpoint calculation styles",
        "original": {
            "code": """def binarySearch(nums, target):
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
            "expected_concepts": ["binary_search_standard"],
        },
        "variants": [
            {
                "name": "overflow_safe_midpoint",
                "code": """def binarySearch(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
                "expected_concepts": ["binary_search_standard"],
                "transforms_applied": ["overflow_safe_midpoint"],
            },
            {
                "name": "bitshift_midpoint",
                "code": """def binarySearch(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) >> 1
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
                "expected_concepts": ["binary_search_standard"],
                "transforms_applied": ["bitshift_division"],
            },
            {
                "name": "renamed_variables",
                "code": """def binarySearch(arr, key):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mi = (lo + hi) // 2
        if arr[mi] == key:
            return mi
        elif arr[mi] < key:
            lo = mi + 1
        else:
            hi = mi - 1
    return -1""",
                "expected_concepts": ["binary_search_standard"],
                "transforms_applied": ["variable_rename"],
            },
        ],
    },
    {
        "category": "sliding_window_fixed",
        "description": "Fixed sliding window with different loop styles",
        "original": {
            "code": """def findMaxAverage(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k""",
            "expected_concepts": ["sliding_window_fixed"],
        },
        "variants": [
            {
                "name": "renamed_variables",
                "code": """def findMaxAverage(arr, w):
    curr = sum(arr[:w])
    best = curr
    for i in range(w, len(arr)):
        curr += arr[i] - arr[i - w]
        best = max(best, curr)
    return best / w""",
                "expected_concepts": ["sliding_window_fixed"],
                "transforms_applied": ["variable_rename"],
            },
            {
                "name": "helper_function",
                "code": """def window_sum(arr, start, end):
    return sum(arr[start:end])

def findMaxAverage(nums, k):
    curr = window_sum(nums, 0, k)
    best = curr
    for i in range(k, len(nums)):
        curr = curr - nums[i - k] + nums[i]
        best = max(best, curr)
    return best / k""",
                "expected_concepts": ["sliding_window_fixed"],
                "transforms_applied": ["helper_function"],
            },
        ],
    },
    {
        "category": "monotonic_stack",
        "description": "Monotonic stack with different variable names",
        "original": {
            "code": """def dailyTemperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temperatures[i] > temperatures[stack[-1]]:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)
    return result""",
            "expected_concepts": ["monotonic_stack"],
        },
        "variants": [
            {
                "name": "renamed_variables",
                "code": """def dailyTemperatures(temps):
    n = len(temps)
    ans = [0] * n
    stk = []
    for idx in range(n):
        while stk and temps[idx] > temps[stk[-1]]:
            prev = stk.pop()
            ans[prev] = idx - prev
        stk.append(idx)
    return ans""",
                "expected_concepts": ["monotonic_stack"],
                "transforms_applied": ["variable_rename"],
            },
            {
                "name": "list_as_stack",
                "code": """def dailyTemperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    indices = []
    for i in range(n):
        while len(indices) > 0 and temperatures[i] > temperatures[indices[-1]]:
            prev_idx = indices.pop()
            result[prev_idx] = i - prev_idx
        indices.append(i)
    return result""",
                "expected_concepts": ["monotonic_stack"],
                "transforms_applied": ["explicit_length_check"],
            },
        ],
    },
    {
        "category": "backtracking_permutation",
        "description": "Backtracking with different style patterns",
        "original": {
            "code": """def permute(nums):
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
            "expected_concepts": ["backtracking_permutation"],
        },
        "variants": [
            {
                "name": "used_boolean_array",
                "code": """def permute(nums):
    result = []
    n = len(nums)
    def backtrack(path, used):
        if len(path) == n:
            result.append(path[:])
            return
        for i in range(n):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * n)
    return result""",
                "expected_concepts": ["backtracking_permutation"],
                "transforms_applied": ["used_boolean_array"],
            },
            {
                "name": "renamed_variables",
                "code": """def permute(input_nums):
    output = []
    def explore(current, remaining):
        if not remaining:
            output.append(current[:])
            return
        for i in range(len(remaining)):
            current.append(remaining[i])
            explore(current, remaining[:i] + remaining[i+1:])
            current.pop()
    explore([], input_nums)
    return output""",
                "expected_concepts": ["backtracking_permutation"],
                "transforms_applied": ["variable_rename", "remaining_list"],
            },
        ],
    },
    {
        "category": "dp_1d_forward",
        "description": "1D DP with different initialization styles",
        "original": {
            "code": """def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]""",
            "expected_concepts": ["dp_1d_forward"],
        },
        "variants": [
            {
                "name": "space_optimized",
                "code": """def climbStairs(n):
    if n <= 2:
        return n
    prev2 = 1
    prev1 = 2
    for i in range(3, n + 1):
        curr = prev1 + prev2
        prev2 = prev1
        prev1 = curr
    return prev1""",
                "expected_concepts": ["dp_1d_forward"],
                "transforms_applied": ["space_optimization"],
                "note": "Space-optimized version may not be detected as DP by AST"
            },
            {
                "name": "dict_memo",
                "code": """def climbStairs(n):
    memo = {1: 1, 2: 2}
    for i in range(3, n + 1):
        memo[i] = memo[i-1] + memo[i-2]
    return memo[n]""",
                "expected_concepts": ["dp_1d_forward"],
                "transforms_applied": ["dict_instead_of_list"],
            },
        ],
    },
]


def run_robustness_tests(output_dir: str) -> dict:
    """Run all robustness tests and generate report."""
    os.makedirs(output_dir, exist_ok=True)
    
    ast_engine = ASTAnalysisEngine()
    results = []
    
    print(f"Running {len(ROBUSTNESS_TEST_CASES)} robustness test categories...")
    
    for test_case in ROBUSTNESS_TEST_CASES:
        category = test_case["category"]
        print(f"\n  Testing: {category}")
        
        # Run on original
        original_code = test_case["original"]["code"]
        original_expected = test_case["original"]["expected_concepts"]
        
        try:
            original_ast = ast_engine.analyze(original_code)
            original_legacy = set()
            for p in original_ast.get("detected_patterns", []):
                if p.get("detected", False) and p.get("confidence", 0.0) > 0.0:
                    original_legacy.add(p["pattern_id"])
        except Exception as e:
            original_legacy = set()
            print(f"    Original analysis failed: {e}")
        
        original_shadow = run_shadow_analysis(original_code)
        original_shadow_concepts = set()
        if original_shadow:
            for t in original_shadow.get("technique_evidence", []):
                original_shadow_concepts.add(t["technique_id"])
            for s in original_shadow.get("strategy_evidence", []):
                original_shadow_concepts.add(s["strategy_id"])
        
        # Test each variant
        for variant in test_case["variants"]:
            variant_code = variant["code"]
            variant_expected = variant["expected_concepts"]
            variant_name = variant["name"]
            transforms = variant.get("transforms_applied", [])
            
            # Legacy detection
            try:
                variant_ast = ast_engine.analyze(variant_code)
                variant_legacy = set()
                for p in variant_ast.get("detected_patterns", []):
                    if p.get("detected", False) and p.get("confidence", 0.0) > 0.0:
                        variant_legacy.add(p["pattern_id"])
            except Exception as e:
                variant_legacy = set()
                print(f"    Variant {variant_name} legacy failed: {e}")
            
            # Shadow detection
            variant_shadow_result = run_shadow_analysis(variant_code)
            variant_shadow = set()
            if variant_shadow_result:
                for t in variant_shadow_result.get("technique_evidence", []):
                    variant_shadow.add(t["technique_id"])
                for s in variant_shadow_result.get("strategy_evidence", []):
                    variant_shadow.add(s["strategy_id"])
            
            # Check detection stability
            legacy_stable = original_legacy == variant_legacy
            shadow_stable = original_shadow_concepts == variant_shadow
            
            # Check if expected concepts were detected
            legacy_detected_expected = any(
                c in variant_legacy for c in variant_expected
            )
            shadow_detected_expected = any(
                c in variant_shadow for c in variant_expected
            )
            
            result = {
                "category": category,
                "variant_name": variant_name,
                "transforms": transforms,
                "note": variant.get("note", ""),
                "original_legacy_concepts": sorted(original_legacy),
                "variant_legacy_concepts": sorted(variant_legacy),
                "legacy_stable": legacy_stable,
                "legacy_detection_changed": not legacy_stable,
                "original_shadow_concepts": sorted(original_shadow_concepts),
                "variant_shadow_concepts": sorted(variant_shadow),
                "shadow_stable": shadow_stable,
                "shadow_detection_changed": not shadow_stable,
                "expected_concepts": variant_expected,
                "legacy_detected_expected": legacy_detected_expected,
                "shadow_detected_expected": shadow_detected_expected,
            }
            results.append(result)
            
            # Report
            status = "OK" if legacy_stable and shadow_stable else "CHANGED"
            print(f"    [{status}] {variant_name}: "
                  f"legacy={'stable' if legacy_stable else 'CHANGED'}, "
                  f"shadow={'stable' if shadow_stable else 'CHANGED'}")
    
    # Summary statistics
    total_variants = len(results)
    legacy_stable_count = sum(1 for r in results if r["legacy_stable"])
    shadow_stable_count = sum(1 for r in results if r["shadow_stable"])
    legacy_detected_count = sum(1 for r in results if r["legacy_detected_expected"])
    shadow_detected_count = sum(1 for r in results if r["shadow_detected_expected"])
    
    summary = {
        "total_variants_tested": total_variants,
        "legacy_stability_rate": legacy_stable_count / total_variants if total_variants else 0,
        "shadow_stability_rate": shadow_stable_count / total_variants if total_variants else 0,
        "legacy_detection_rate": legacy_detected_count / total_variants if total_variants else 0,
        "shadow_detection_rate": shadow_detected_count / total_variants if total_variants else 0,
        "categories_tested": list(set(r["category"] for r in results)),
        "transforms_tested": list(set(
            t for r in results for t in r["transforms"]
        )),
    }
    
    # Save results
    with open(os.path.join(output_dir, "robustness_results.json"), 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    with open(os.path.join(output_dir, "robustness_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Robustness Test Summary:")
    print(f"  Variants tested: {total_variants}")
    print(f"  Legacy stability: {legacy_stable_count}/{total_variants} ({summary['legacy_stability_rate']:.1%})")
    print(f"  Shadow stability: {shadow_stable_count}/{total_variants} ({summary['shadow_stability_rate']:.1%})")
    print(f"  Legacy detection rate: {legacy_detected_count}/{total_variants} ({summary['legacy_detection_rate']:.1%})")
    print(f"  Shadow detection rate: {shadow_detected_count}/{total_variants} ({summary['shadow_detection_rate']:.1%})")
    
    # Identify naming-dependent detectors
    naming_failures = [r for r in results if "variable_rename" in r["transforms"] and r["legacy_detection_changed"]]
    if naming_failures:
        print(f"\n  WARNING: Naming-dependent detectors:")
        for nf in naming_failures:
            print(f"    {nf['category']} ({nf['variant_name']}): "
                  f"original={nf['original_legacy_concepts']}, "
                  f"variant={nf['variant_legacy_concepts']}")
    
    return summary


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = str(base_dir / "results" / "robustness")
    os.makedirs(output_dir, exist_ok=True)
    
    run_robustness_tests(output_dir)
