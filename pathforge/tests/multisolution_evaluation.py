"""Multi-solution ground truth feasibility evaluation.

Tests whether the free OpenRouter model (gpt-4o-mini) can reliably
generate multi-solution ground truth for algorithmic problems.

Does NOT modify production code. Produces metrics and a report.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"
TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 2.0
TEMPERATURE = 0.1
TRIALS_PER_PROBLEM = 3  # Run each problem 3 times for stability

# ============================================================================
# EVALUATION CORPUS
# ============================================================================

@dataclass
class Problem:
    id: str
    title: str
    description: str
    category: str  # 'single', 'two_approaches', 'three_plus', 'same_pattern_different_impl', 'different_patterns'
    expected_groups: List[List[str]]  # Expected solution groups (OR of AND groups)
    notes: str = ""


# Hand-curated problems with known multiple valid optimal approaches
CORPUS = [
    # --- Single dominant approach (control group) ---
    Problem(
        id="two_sum",
        title="Two Sum",
        description="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.",
        category="single",
        expected_groups=[["hash_map_lookup"]],
        notes="Hash map is the standard O(n) approach. Brute force exists but is not optimal."
    ),
    Problem(
        id="valid_parentheses",
        title="Valid Parentheses",
        description="Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type of brackets and in the correct order.",
        category="single",
        expected_groups=[["monotonic_stack"]],
        notes="Stack is the only standard approach."
    ),

    # --- Two distinct optimal approaches ---
    Problem(
        id="binary_tree_level_order",
        title="Binary Tree Level Order Traversal",
        description="Given the root of a binary tree, return the level order traversal of its nodes' values (i.e., from left to right, level by level).",
        category="two_approaches",
        expected_groups=[
            ["bfs_level_order"],       # BFS with queue
            ["dfs_recursive"],          # DFS with level tracking
        ],
        notes="Both BFS and DFS are O(n) optimal. BFS is more natural but DFS with level parameter is equally valid."
    ),
    Problem(
        id="clone_graph",
        title="Clone Graph",
        description="Given a reference of a node in a connected undirected graph, return a deep copy of the graph. Each node contains a value and a list of its neighbors.",
        category="two_approaches",
        expected_groups=[
            ["dfs_recursive"],          # DFS with visited map
            ["bfs_level_order"],        # BFS with visited map
        ],
        notes="Both DFS and BFS traversal with a visited/hashmap for cloning are equally optimal."
    ),
    Problem(
        id="number_of_islands",
        title="Number of Islands",
        description="Given an m x n 2D binary grid grid which represents a map of '1's (land) and '0's (water), return the number of islands. An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically.",
        category="two_approaches",
        expected_groups=[
            ["dfs_recursive"],          # DFS flood fill
            ["bfs_level_order"],        # BFS flood fill
        ],
        notes="Both DFS and BFS for grid traversal/flood fill are equally valid."
    ),
    Problem(
        id="max_subarray",
        title="Maximum Subarray",
        description="Given an integer array nums, find the subarray with the largest sum, and return its sum.",
        category="two_approaches",
        expected_groups=[
            ["dp_1d_forward"],          # Kadane's algorithm (DP)
            ["greedy_local"],           # Greedy single-pass
        ],
        notes="Kadane's DP and greedy are essentially the same algorithm expressed differently. May or may not be separated."
    ),
    Problem(
        id="course_schedule",
        title="Course Schedule",
        description="There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take course bi first if you want to take course ai. Return true if you can finish all courses.",
        category="two_approaches",
        expected_groups=[
            ["topological_sort"],       # Topological sort (Kahn's)
            ["dfs_recursive"],          # Cycle detection via DFS
        ],
        notes="Both topological sort and DFS-based cycle detection are O(V+E) optimal."
    ),
    Problem(
        id="word_ladder",
        title="Word Ladder",
        description="A transformation sequence from word beginWord to word endWord is a sequence of words beginWord -> s1 -> s2 -> ... -> sk such that every adjacent pair of words differs by a single letter. Given two words beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence.",
        category="two_approaches",
        expected_groups=[
            ["bfs_shortest_path"],      # BFS for shortest path
            ["bidirectional_search"],   # Bidirectional BFS (if in taxonomy)
        ],
        notes="BFS is standard. Bidirectional BFS is faster but may not map to current taxonomy."
    ),

    # --- Three or more approaches ---
    Problem(
        id="climbing_stairs",
        title="Climbing Stairs",
        description="You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
        category="three_plus",
        expected_groups=[
            ["dp_1d_forward"],          # Bottom-up DP
            ["dp_1d_sequence"],         # Fibonacci sequence recognition
        ],
        notes="DP, recursion+memo, and fibonacci recognition are all valid. Top-down DP is also valid."
    ),
    Problem(
        id="combination_sum",
        title="Combination Sum",
        description="Given an array of distinct integers candidates and a target integer target, return a list of all unique combinations of candidates where the chosen numbers sum to target. The same number may be chosen from candidates an unlimited number of times.",
        category="three_plus",
        expected_groups=[
            ["backtracking_subset"],    # Backtracking with reuse
        ],
        notes="Only one canonical approach (backtracking). Included as control."
    ),

    # --- Same pattern, different implementation style ---
    Problem(
        id="reverse_linked_list",
        title="Reverse Linked List",
        description="Given the head of a singly linked list, reverse the list, and return the reversed list.",
        category="same_pattern_different_impl",
        expected_groups=[
            ["linked_list_reversal"],   # Iterative reversal
        ],
        notes="Iterative and recursive both work. Both are linked_list_reversal pattern."
    ),
    Problem(
        id="valid_anagram",
        title="Valid Anagram",
        description="Given two strings s and t, return true if t is an anagram of s, and false otherwise.",
        category="same_pattern_different_impl",
        expected_groups=[
            ["hash_map_frequency"],     # Character frequency counting
        ],
        notes="Sorting is also valid but O(n log n). Frequency counting is O(n)."
    ),

    # --- Different optimal patterns for same problem ---
    Problem(
        id="meeting_rooms_ii",
        title="Meeting Rooms II",
        description="Given an array of meeting time intervals intervals where intervals[i] = [starti, endi], return the minimum number of conference rooms required.",
        category="different_patterns",
        expected_groups=[
            ["sorting", "monotonic_stack"],  # Sort + sweep with heap/stack
            ["heap_top_k"],                  # Min-heap approach
        ],
        notes="Both sweep line with heap and direct heap approach are O(n log n)."
    ),
    Problem(
        id="lru_cache",
        title="LRU Cache",
        description="Design a data structure that follows the constraints of a Least Recently Used (LRU) cache. Implement the LRUCache class with get and put operations in O(1) average time complexity.",
        category="different_patterns",
        expected_groups=[
            ["hash_map_lookup", "linked_list_reversal"],  # HashMap + Doubly Linked List
        ],
        notes="Only one optimal approach: hashmap + doubly linked list."
    ),
]


# ============================================================================
# LLM INTERFACE
# ============================================================================

def call_llm(prompt: str) -> Optional[dict]:
    """Call the OpenRouter API and return parsed JSON response."""
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        print("  ERROR: No OPENROUTER_API_KEY found")
        return None

    for attempt in range(MAX_RETRIES + 1):
        try:
            data = json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": 500,
            }).encode("utf-8")

            req = urllib.request.Request(OPENROUTER_URL, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("HTTP-Referer", "https://pathforge.app")

            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()

            payload = json.loads(raw)
            content = payload["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            cleaned = content.strip()
            if cleaned.startswith("```"):
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start != -1 and end != -1:
                    cleaned = cleaned[start:end+1]

            return json.loads(cleaned)

        except (json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError,
                OSError, KeyError, IndexError) as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            print(f"  LLM call failed after {MAX_RETRIES+1} attempts: {e}")
            return None

    return None


# ============================================================================
# PROMPT DESIGNS
# ============================================================================

PROMPT_A_TEMPLATE = (
    "You are a precise algorithm classification assistant. "
    "Given a programming problem description, identify the algorithmic patterns "
    "required to solve it. Return ONLY valid JSON with no markdown, no explanation.\n\n"
    "Output format:\n"
    '{"patterns": ["pattern_1", "pattern_2"], "confidence": {"pattern_1": 0.9}}\n\n'
    "Use exactly one of these canonical pattern names (all lowercase, snake_case):\n"
    "hash_map_lookup, hash_map_frequency, prefix_sum, sliding_window_fixed, "
    "sliding_window_variable, two_pointers_opposite, two_pointers_same, "
    "dfs_recursive, dfs_iterative, bfs_level_order, bfs_shortest_path, "
    "topological_sort, union_find, binary_search_tree, "
    "dp_1d_forward, dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack, "
    "dp_interval, dp_state_machine, "
    "fast_slow_pointers, linked_list_reversal, monotonic_stack, monotonic_deque, "
    "binary_search_standard, binary_search_rotated, binary_search_answer, "
    "heap_top_k, greedy_local, greedy_interval, "
    "backtracking_permutation, backtracking_subset\n\n"
    "Problem:\n"
)


PROMPT_B_TEMPLATE = (
    "You are a precise algorithm classification assistant. "
    "Given a programming problem description, identify ALL distinct optimal solution strategies.\n\n"
    "IMPORTANT: Many problems have multiple valid optimal approaches. "
    "You must identify each distinct approach SEPARATELY.\n\n"
    "For each distinct approach:\n"
    "1. Think about what algorithmic strategy it uses\n"
    "2. Identify which patterns from the canonical list apply WITHIN that strategy\n"
    "3. List them as a group (AND semantics: all patterns in a group must be present in that strategy)\n\n"
    "Between different approaches, use OR semantics (any one approach is sufficient).\n\n"
    "Output format:\n"
    '{"reasoning": "Brief explanation",'
    ' "solution_groups": [{"patterns": ["a", "b"], "approach_name": "name"}],'
    ' "confidence": {"a": 0.9}}\n\n'
    "Canonical pattern names (all lowercase, snake_case):\n"
    "hash_map_lookup, hash_map_frequency, prefix_sum, sliding_window_fixed, "
    "sliding_window_variable, two_pointers_opposite, two_pointers_same, "
    "dfs_recursive, dfs_iterative, bfs_level_order, bfs_shortest_path, "
    "topological_sort, union_find, binary_search_tree, "
    "dp_1d_forward, dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack, "
    "dp_interval, dp_state_machine, "
    "fast_slow_pointers, linked_list_reversal, monotonic_stack, monotonic_deque, "
    "binary_search_standard, binary_search_rotated, binary_search_answer, "
    "heap_top_k, greedy_local, greedy_interval, "
    "backtracking_permutation, backtracking_subset\n\n"
    "Problem:\n"
)


# ============================================================================
# EVALUATION METRICS
# ============================================================================

@dataclass
class TrialResult:
    problem_id: str
    prompt_design: str
    trial_num: int
    raw_response: Optional[dict]
    parsed_groups: List[List[str]]  # Extracted solution groups
    all_patterns: List[str]         # Flat list of all patterns mentioned
    reasoning: str
    parse_success: bool


@dataclass
class EvaluationMetrics:
    problem_id: str
    prompt_design: str
    
    # Strategy recall
    expected_groups_found: int  # How many expected groups were represented
    total_expected_groups: int
    strategy_recall: float
    
    # Hallucination
    hallucinated_patterns: List[str]  # Patterns not in expected groups
    hallucinated_group_count: int
    
    # Taxonomy mapping
    taxonomy_violations: List[str]  # Patterns not in canonical list
    
    # Group structure
    correct_group_structure: bool  # Does the group structure match expected?
    group_count_match: bool       # Does the number of groups match?
    
    # Consistency
    consistent_across_trials: bool  # Same result across repeated runs?


def normalize_pattern(p: str) -> str:
    """Normalize a pattern name to canonical form."""
    return p.lower().strip().replace("-", "_").replace(" ", "_")


def extract_groups_from_response(response: Optional[dict], prompt_design: str) -> Tuple[List[List[str]], List[str], str]:
    """Extract solution groups from LLM response."""
    if response is None:
        return [], [], ""
    
    if prompt_design == "A_current":
        # Current format: flat pattern list
        patterns = response.get("patterns", [])
        groups = [[normalize_pattern(p)] for p in patterns] if patterns else []
        return groups, [normalize_pattern(p) for p in patterns], ""
    
    elif prompt_design == "B_multi_solution":
        # New format: explicit solution groups
        reasoning = response.get("reasoning", "")
        raw_groups = response.get("solution_groups", [])
        
        groups = []
        all_patterns = []
        for g in raw_groups:
            patterns = [normalize_pattern(p) for p in g.get("patterns", [])]
            if patterns:
                groups.append(patterns)
                all_patterns.extend(patterns)
        
        # Fallback: if no solution_groups, try flat patterns
        if not groups:
            patterns = response.get("patterns", [])
            groups = [[normalize_pattern(p)] for p in patterns] if patterns else []
            all_patterns = [normalize_pattern(p) for p in patterns]
        
        return groups, all_patterns, reasoning
    
    return [], [], ""


def evaluate_single_result(
    result: TrialResult,
    expected_groups: List[List[str]],
    canonical_patterns: set,
) -> EvaluationMetrics:
    """Evaluate a single trial result against expected groups."""
    
    # Strategy recall: how many expected groups are represented?
    expected_patterns_flat = set()
    for g in expected_groups:
        expected_patterns_flat.update(g)
    
    found_patterns = set(result.all_patterns)
    
    # Check if each expected group has at least one pattern detected
    groups_found = 0
    for eg in expected_groups:
        if any(p in found_patterns for p in eg):
            groups_found += 1
    
    strategy_recall = groups_found / len(expected_groups) if expected_groups else 1.0
    
    # Hallucination: patterns in response but not in any expected group
    hallucinated = [p for p in result.all_patterns if p not in expected_patterns_flat]
    
    # Taxonomy violations: patterns not in canonical list
    violations = [p for p in result.all_patterns if p not in canonical_patterns]
    
    # Group structure
    correct_structure = len(result.parsed_groups) == len(expected_groups)
    group_count_match = len(result.parsed_groups) == len(expected_groups)
    
    return EvaluationMetrics(
        problem_id=result.problem_id,
        prompt_design=result.prompt_design,
        expected_groups_found=groups_found,
        total_expected_groups=len(expected_groups),
        strategy_recall=strategy_recall,
        hallucinated_patterns=hallucinated,
        hallucinated_group_count=len(hallucinated),
        taxonomy_violations=violations,
        correct_group_structure=correct_structure,
        group_count_match=group_count_match,
        consistent_across_trials=True,  # Set later
    )


# ============================================================================
# MAIN EXPERIMENT
# ============================================================================

CANONICAL_PATTERNS = {
    "hash_map_lookup", "hash_map_frequency", "prefix_sum", "sliding_window_fixed",
    "sliding_window_variable", "two_pointers_opposite", "two_pointers_same",
    "dfs_recursive", "dfs_iterative", "bfs_level_order", "bfs_shortest_path",
    "topological_sort", "union_find", "binary_search_tree",
    "dp_1d_forward", "dp_1d_sequence", "dp_2d_grid", "dp_2d_string", "dp_knapsack",
    "dp_interval", "dp_state_machine",
    "fast_slow_pointers", "linked_list_reversal", "monotonic_stack", "monotonic_deque",
    "binary_search_standard", "binary_search_rotated", "binary_search_answer",
    "heap_top_k", "greedy_local", "greedy_interval",
    "backtracking_permutation", "backtracking_subset",
}


def build_prompt_a(problem: Problem) -> str:
    return PROMPT_A_TEMPLATE + problem.description


def build_prompt_b(problem: Problem) -> str:
    return PROMPT_B_TEMPLATE + problem.description


def run_experiment():
    """Run the full evaluation experiment."""
    print("=" * 70)
    print("MULTI-SOLUTION GROUND TRUTH FEASIBILITY EVALUATION")
    print("=" * 70)
    
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        return
    
    all_results: List[TrialResult] = []
    all_metrics: List[EvaluationMetrics] = []
    
    for problem in CORPUS:
        print(f"\n--- {problem.id} ({problem.category}) ---")
        print(f"  Expected groups: {problem.expected_groups}")
        
        for prompt_design, build_fn, label in [
            ("A_current", build_prompt_a, "Prompt A (flat)"),
            ("B_multi_solution", build_prompt_b, "Prompt B (multi-group)"),
        ]:
            trial_groups_sets = []
            
            for trial in range(TRIALS_PER_PROBLEM):
                prompt = build_fn(problem)
                response = call_llm(prompt)
                groups, all_patterns, reasoning = extract_groups_from_response(response, prompt_design)
                
                result = TrialResult(
                    problem_id=problem.id,
                    prompt_design=prompt_design,
                    trial_num=trial,
                    raw_response=response,
                    parsed_groups=groups,
                    all_patterns=all_patterns,
                    reasoning=reasoning,
                    parse_success=response is not None,
                )
                all_results.append(result)
                trial_groups_sets.append(frozenset(frozenset(g) for g in groups))
                
                metrics = evaluate_single_result(result, problem.expected_groups, CANONICAL_PATTERNS)
                all_metrics.append(metrics)
                
                status = "OK" if response else "FAIL"
                print(f"  {label} trial {trial+1}: {status} groups={groups}")
                
                time.sleep(1)  # Rate limiting
            
            # Check consistency across trials
            consistent = len(set(trial_groups_sets)) == 1
            # Update metrics for this problem/prompt combination
            for m in all_metrics:
                if m.problem_id == problem.id and m.prompt_design == prompt_design:
                    m.consistent_across_trials = consistent
    
    # ============================================================================
    # AGGREGATE METRICS
    # ============================================================================
    print("\n" + "=" * 70)
    print("AGGREGATE METRICS")
    print("=" * 70)
    
    for design in ["A_current", "B_multi_solution"]:
        design_metrics = [m for m in all_metrics if m.prompt_design == design]
        
        print(f"\n--- {design} ---")
        
        # Strategy recall
        avg_recall = sum(m.strategy_recall for m in design_metrics) / len(design_metrics) if design_metrics else 0
        print(f"  Strategy recall: {avg_recall:.1%}")
        
        # By category
        for cat in ["single", "two_approaches", "three_plus", "same_pattern_different_impl", "different_patterns"]:
            cat_metrics = [m for m in design_metrics if any(
                p.category == cat and p.id == m.problem_id for p in CORPUS
            )]
            if cat_metrics:
                cat_recall = sum(m.strategy_recall for m in cat_metrics) / len(cat_metrics)
                print(f"    {cat}: {cat_recall:.1%} ({len(cat_metrics)} problems)")
        
        # Hallucination
        total_hallucinated = sum(m.hallucinated_group_count for m in design_metrics)
        problems_with_hallucination = sum(1 for m in design_metrics if m.hallucinated_group_count > 0)
        print(f"  Hallucinated patterns: {total_hallucinated} total, {problems_with_hallucination} problems affected")
        
        # Taxonomy violations
        all_violations = []
        for m in design_metrics:
            all_violations.extend(m.taxonomy_violations)
        print(f"  Taxonomy violations: {len(all_violations)} total")
        if all_violations:
            from collections import Counter
            for p, c in Counter(all_violations).most_common(5):
                print(f"    {p}: {c}")
        
        # Group structure
        correct_structure = sum(1 for m in design_metrics if m.correct_group_structure)
        print(f"  Correct group structure: {correct_structure}/{len(design_metrics)}")
        
        # Consistency
        consistent = sum(1 for m in design_metrics if m.consistent_across_trials)
        print(f"  Consistent across trials: {consistent}/{len(design_metrics)}")
        
        # Parse success
        design_results = [r for r in all_results if r.prompt_design == design]
        parse_success = sum(1 for r in design_results if r.parse_success)
        print(f"  Parse success: {parse_success}/{len(design_results)}")
    
    # ============================================================================
    # DETAILED PROBLEM-BY-PROBLEM COMPARISON
    # ============================================================================
    print("\n" + "=" * 70)
    print("PROBLEM-BY-PROBLEM COMPARISON")
    print("=" * 70)
    
    for problem in CORPUS:
        print(f"\n{problem.id} ({problem.category}):")
        print(f"  Expected: {problem.expected_groups}")
        
        for design in ["A_current", "B_multi_solution"]:
            p_metrics = [m for m in all_metrics if m.problem_id == problem.id and m.prompt_design == design]
            if p_metrics:
                m = p_metrics[0]  # Use first trial's metrics
                p_results = [r for r in all_results if r.problem_id == problem.id and r.prompt_design == design]
                print(f"  {design}:")
                print(f"    Groups found: {m.expected_groups_found}/{m.total_expected_groups} (recall={m.strategy_recall:.0%})")
                print(f"    Hallucinated: {m.hallucinated_patterns}")
                print(f"    Consistent: {m.consistent_across_trials}")
                if p_results and p_results[0].reasoning:
                    reasoning_short = p_results[0].reasoning[:120].replace('\n', ' ')
                    print(f"    Reasoning: {reasoning_short}...")
    
    # Save detailed results
    output = {
        "summary": {},
        "per_problem": [],
        "raw_results": [],
    }
    
    for design in ["A_current", "B_multi_solution"]:
        design_metrics = [m for m in all_metrics if m.prompt_design == design]
        avg_recall = sum(m.strategy_recall for m in design_metrics) / len(design_metrics) if design_metrics else 0
        total_hallucinated = sum(m.hallucinated_group_count for m in design_metrics)
        consistent = sum(1 for m in design_metrics if m.consistent_across_trials)
        parse_ok = sum(1 for r in all_results if r.prompt_design == design and r.parse_success)
        
        output["summary"][design] = {
            "strategy_recall": round(avg_recall, 3),
            "hallucinated_patterns": total_hallucinated,
            "consistent_across_trials": consistent,
            "total_problems": len(design_metrics),
            "parse_success": parse_ok,
        }
    
    for problem in CORPUS:
        entry = {"id": problem.id, "category": problem.category, "expected": problem.expected_groups}
        for design in ["A_current", "B_multi_solution"]:
            p_results = [r for r in all_results if r.problem_id == problem.id and r.prompt_design == design]
            p_metrics = [m for m in all_metrics if m.problem_id == problem.id and m.prompt_design == design]
            if p_results:
                entry[design] = {
                    "groups": p_results[0].parsed_groups,
                    "all_patterns": p_results[0].all_patterns,
                    "reasoning": p_results[0].reasoning,
                    "hallucinated": p_metrics[0].hallucinated_patterns if p_metrics else [],
                    "strategy_recall": p_metrics[0].strategy_recall if p_metrics else 0,
                    "consistent": p_metrics[0].consistent_across_trials if p_metrics else False,
                }
        output["per_problem"].append(entry)
    
    for r in all_results:
        output["raw_results"].append({
            "problem_id": r.problem_id,
            "prompt_design": r.prompt_design,
            "trial": r.trial_num,
            "parse_success": r.parse_success,
            "groups": r.parsed_groups,
            "all_patterns": r.all_patterns,
            "reasoning": r.reasoning,
        })
    
    with open("multisolution_evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nDetailed results saved to multisolution_evaluation_results.json")


if __name__ == "__main__":
    run_experiment()
