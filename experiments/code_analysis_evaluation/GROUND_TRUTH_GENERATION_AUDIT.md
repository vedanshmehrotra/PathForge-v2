# GROUND_TRUTH_GENERATION_AUDIT.md

**Date:** 2026-08-29
**Branch:** `architecture/strategy-evidence-spike`

---

## 1. Current Ground Truth Pipeline Architecture

### Data Flow

```
CSV (pathforge_problems_fixed.csv)
  ↓ seed_problems()
problems table (pattern column = JSON array of legacy pattern IDs)
  ↓
_resolve_problem() → _load_csv_patterns()
  ↓
_load_ground_truth() → reconciliation: CSV overrides LLM
  ↓
problem_ground_truth table (solution_groups JSONB)
  ↓
Shadow matcher: evaluate_solution_groups(solution_groups, techniques, strategies, facts)
```

### Two Source Layers

| Layer | Storage | Authority | Used By |
|-------|---------|-----------|---------|
| **CSV-curated** | `problems.pattern` (JSON array) | `human_curated` | Production matcher (legacy), reconciliation override |
| **LLM-generated** | `problem_ground_truth.solution_groups` (JSONB) | `llm_proposed` | Shadow matcher (V1 required/optional/excluded) |

### Reconciliation Logic (problem_resolver.py)

1. If `problems.pattern` (CSV) is non-empty → use as production matcher's pattern list
2. If `problem_ground_truth.solution_groups` exists → use for shadow matcher
3. If CSV and LLM conflict → CSV wins for production, LLM fields preserved for shadow
4. If no ground truth exists → LLM generates on first access (`_ensure_ground_truth`)

### Validation Pipeline

| Stage | What it checks | Failure mode |
|-------|---------------|-------------|
| `_normalize_patterns()` | Pattern IDs in `ALL_PATTERNS` set (33 patterns) | Drops unknown patterns |
| `_build_single_group()` | Maps legacy patterns → V1 required/optional/excluded | Unmapped patterns preserved in metadata |
| `_validate_group()` | V1 concept IDs valid, no required∩excluded overlap, authority tier valid | Rejects invalid groups |
| `check_mutual_exclusion()` | dfs_backtracking ↔ dp_top_down conflict | Rejects groups with both |
| `check_unsatisfiable_combinations()` | binary_search + two_pointers, binary_search + sliding_window | Warns (not rejected) |
| Authority gating (matching.py) | `llm_proposed` cannot produce authoritative CONTRADICTED | Downgrades to UNRESOLVED |

### What the Shadow Matcher Needs

The shadow matcher (`evaluate_solution_groups`) needs solution groups where:
- `required` field contains V1 strategy/technique IDs (e.g., `["sliding_window"]`)
- `excluded` field contains strategies that contradict (e.g., `["two_pointers_opposite"]`)
- `threshold` is 0.5 (default)
- `authority_tier` determines whether outcomes can be authoritative

---

## 2. Current Coverage Analysis

### CSV Data: 300 Problems, All Have Patterns

The CSV has 300 problems with curated patterns. All map through `PATTERN_TO_V1_MAPPING` to V1 concepts.

### Strategy Coverage from CSV

| Strategy | Problems in CSV | Can Shadow Detect? |
|----------|:---------------:|:------------------:|
| `dp_bottom_up` | 60 | ✅ Yes |
| `bfs_shortest_path` | 35 | ✅ Yes |
| `binary_search` | 31 | ✅ Yes |
| `two_pointers_opposite` | 26 | ✅ Yes |
| `dfs_backtracking` | 20 | ✅ Yes |
| `sliding_window` | 13 | ✅ Yes |
| `monotonic_stack_strategy` | 23 | ✅ Yes |
| `union_find` | 7 | ✅ Yes |
| `dp_top_down` | 0 in CSV* | ✅ Yes (direct recursion) |
| `sequential_accumulation` | 12 (technique) | ✅ Yes |
| `recursive_branching` | 60 (technique) | ✅ Yes |
| `bidirectional_index_scan` | 34 (technique) | ✅ Yes |

*Note: `dp_top_down` patterns (`backtracking_permutation`, `backtracking_subset`) map to `dfs_backtracking`, not `dp_top_down`. Top-down DP is typically labeled as `dp_1d_forward` or `dp_2d_grid` in the CSV, which map to `dp_bottom_up`.

### Unmapped Patterns (129 problems)

Patterns like `hash_map_lookup`, `hash_map_frequency`, `greedy_local`, `heap_top_k`, `dfs_iterative` have empty V1 required lists. These produce solution groups with no required strategies → shadow matcher always returns UNRESOLVED.

---

## 3. Key Finding: CSV Patterns Already Provide Shadow Coverage

**The CSV data already contains the patterns needed for the shadow matcher.** The `_map_legacy_patterns_to_v1()` function in `problem_resolver.py` converts CSV patterns to V1 concepts on the fly.

When a problem has CSV patterns but no `problem_ground_truth` row:
1. `_load_ground_truth()` enters the fallback path (line 318-340)
2. It reads CSV patterns via `_load_csv_patterns()`
3. It calls `_map_legacy_patterns_to_v1()` to convert to V1 required concepts
4. It returns a single solution group with the mapped V1 concepts

**This means: for any problem in the CSV, the shadow matcher already has V1 concepts available — even without generating LLM ground truth.**

### What's Missing

The fallback path creates a single solution group with:
- `required`: V1-mapped concepts from CSV patterns
- `optional`: empty
- `excluded`: empty (V1 mapping doesn't propagate exclusions)
- `authority_tier`: from validation_status or "unobserved"

The LLM pipeline would add:
- `excluded` strategies (e.g., `two_pointers_opposite` for sliding window)
- Multiple approach groups (if LLM proposes multiple solutions)
- Confidence scores per pattern

---

## 4. Recommended 15-20 Problems

Selected to cover all 9 strategy families the shadow system detects, with canonical solutions that are well-understood and unambiguous.

### Sliding Window (3 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 1 | 3 | Longest Substring Without Repeating Characters | Medium | `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` |
| 2 | 209 | Minimum Size Subarray Sum | Medium | `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` |
| 3 | 2958 | Max Subarray Length of Length K | Medium | `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` |

### Two Pointers (3 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 4 | 11 | Container With Most Water | Medium | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` |
| 5 | 125 | Valid Palindrome | Easy | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` |
| 6 | 15 | 3Sum | Medium | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` |

### Binary Search (2 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 7 | 704 | Binary Search | Easy | `binary_search_standard` | `binary_search` | `two_pointers_opposite` |
| 8 | 35 | Search Insert Position | Easy | `binary_search_standard` | `binary_search` | `two_pointers_opposite` |

### DP Bottom-Up (3 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 9 | 70 | Climbing Stairs | Easy | `dp_1d_forward` | `dp_bottom_up` | `recursive_branching` |
| 10 | 322 | Coin Change | Medium | `dp_1d_forward` | `dp_bottom_up` | `recursive_branching` |
| 11 | 62 | Unique Paths | Medium | `dp_2d_grid` | `dp_bottom_up` | `recursive_branching` |

### DP Top-Down (2 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 12 | 70 | Climbing Stairs (top-down variant) | Easy | `dp_1d_forward` | `dp_top_down` | `dfs_backtracking` |
| 13 | 322 | Coin Change (top-down variant) | Medium | `dp_1d_forward` | `dp_top_down` | `dfs_backtracking` |

*Note: These are the same problems as #9-10 but with memoized recursive solutions. The shadow matcher must handle both approaches for the same problem.*

### DFS/Backtracking (2 problems)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 14 | 46 | Permutations | Medium | `backtracking_permutation` | `dfs_backtracking` | `dp_top_down` |
| 15 | 78 | Subsets | Medium | `backtracking_subset` | `dfs_backtracking` | `dp_top_down` |

### BFS (1 problem)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 16 | 102 | Binary Tree Level Order Traversal | Medium | `bfs_level_order` | `bfs_shortest_path` | `recursive_branching` |

### Monotonic Stack (1 problem)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 17 | 496 | Next Greater Element I | Easy | `monotonic_stack` | `monotonic_stack_strategy` | `sliding_window` |

### Union-Find (1 problem)

| # | ID | Title | Difficulty | CSV Pattern | V1 Required | V1 Excluded |
|---|-----|-------|:----------:|-------------|-------------|-------------|
| 18 | 200 | Number of Islands | Medium | `union_find` | `union_find` | — |

---

## 5. Source Decision for Each Problem

| Problem | Source | Reason |
|---------|--------|--------|
| All 18 | **CSV patterns + manual V1 mapping** | CSV already has verified patterns. No LLM call needed. |

**Why not use the LLM pipeline?**
1. The LLM pipeline produces `llm_proposed` authority → cannot produce authoritative CONTRADICTED
2. CSV patterns are already human-curated and verified
3. The V1 mapping is deterministic and already implemented
4. LLM calls cost money and add latency
5. The only thing missing from CSV is `excluded` strategies — which can be added manually

**What the LLM pipeline would add:**
- Multiple approach groups (e.g., "DP bottom-up" and "DP top-down" as separate groups)
- Confidence scores per pattern
- These are nice-to-have but not required for the shadow matcher to function

---

## 6. Validation Required

### Pre-generation checks (already exist)
- ✅ V1 concept IDs are valid (`VALID_V1_CONCEPTS`)
- ✅ No required∩excluded overlap
- ✅ Authority tier is valid
- ✅ Mutual exclusion check (dfs_backtracking ↔ dp_top_down)
- ✅ Unsatisfiable combination warnings

### Manual verification needed
1. **Pattern correctness**: Each problem's CSV pattern matches the canonical solution approach
2. **V1 mapping correctness**: The `PATTERN_TO_V1_MAPPING` produces the right required/optional/excluded for each pattern
3. **Excluded strategies**: Manually add excluded strategies that the V1 mapping doesn't include
4. **Multi-approach problems**: Problems like Coin Change (DP bottom-up + top-down) need two solution groups

### Post-generation smoke test
- Run shadow analysis on representative code for each problem
- Verify CONFIRMED outcome when code matches the expected strategy
- Verify UNRESOLVED when code uses a different strategy
- Verify no false CONTRADICTED

---

## 7. Exact Next Implementation Step

### Option A: Direct SQL INSERT (smallest, safest)

Write a Python script that:
1. For each of the 18 problems, builds a solution group dict with:
   - `required`: V1-mapped concepts from CSV patterns
   - `excluded`: manually specified contradicting strategies
   - `authority_tier`: `"structurally_observed"` (higher than `llm_proposed`)
   - `threshold`: 0.5
2. Inserts into `problem_ground_truth` with `ON CONFLICT DO UPDATE`
3. Runs the existing validation pipeline (`_validate_group`) before insert
4. Prints before/after for manual review

**Estimated effort:** 1-2 hours
**Risk:** Low — uses existing storage path, validated by existing tests
**Reversible:** Yes — DELETE FROM problem_ground_truth WHERE problem_id IN (...)

### Option B: Enhance CSV → V1 mapping (medium effort)

Extend `_load_ground_truth()` to automatically populate `excluded` strategies based on the V1 mapping. This would make ALL 300 CSV problems shadow-ready without any new data.

**Estimated effort:** Half day
**Risk:** Low — extends existing reconciliation path
**Reversible:** Yes — code change only, no data changes

### Option C: Run LLM pipeline on 18 problems (full pipeline test)

Call `build_ground_truth()` for each problem. This tests the full LLM → validation → storage path.

**Estimated effort:** 2-3 hours (including LLM API calls)
**Risk:** Medium — depends on LLM availability and quality
**Reversible:** Yes — DELETE FROM problem_ground_truth

### Recommendation: **Option A + B combined**

1. First implement Option B (extend V1 mapping to include exclusions) — this makes ALL 300 CSV problems shadow-ready
2. Then implement Option A for the 18 recommended problems — this gives us `structurally_observed` authority for the most important problems
3. Skip Option C — the LLM pipeline adds `llm_proposed` authority which is weaker than `structurally_observed`

---

## 8. What Should NOT Be Done

- **Do NOT redesign the schema** — the existing `problem_ground_truth` table with `solution_groups` JSONB is sufficient
- **Do NOT add provenance infrastructure** — the `provenance` field in solution groups already tracks source
- **Do NOT generate ground truth for all 300 problems** — start with 18, validate, then expand
- **Do NOT use `llm_proposed` authority for manually verified patterns** — use `structurally_observed` or `externally_listed`
- **Do NOT add new V1 concepts** — the current 9 strategies + 10 techniques cover the shadow system's detection capabilities
