# GROUND_TRUTH_SEEDING_REPORT.md

**Date:** 2026-08-29
**Branch:** `architecture/strategy-evidence-spike`

---

## 1. Phase 1: Extended CSV → V1 Mapping

### Changes

**File:** `pathforge/services/problem_resolver.py`

1. Added `_get_v1_excluded_for_patterns()` — extracts excluded V1 concepts from `PATTERN_TO_V1_MAPPING` for a list of legacy patterns.

2. Updated `_load_ground_truth()` fallback path — now includes `excluded` strategies when building solution groups from CSV patterns via `_map_legacy_patterns_to_v1()`.

### What Changed in the Fallback Path

Before:
```python
groups = [{
    "id": "group_0",
    "required": required,
    "optional": [],
    "excluded": [],  # ← was always empty
    ...
}]
```

After:
```python
excluded = _get_v1_excluded_for_patterns(patterns)
groups = [{
    "id": "group_0",
    "required": required,
    "optional": [],
    "excluded": excluded,  # ← now carries correct exclusions
    ...
}]
```

### Exclusion Rules (from existing PATTERN_TO_V1_MAPPING)

| Pattern | Required | Excluded |
|---------|----------|----------|
| `sliding_window_fixed` | `sliding_window` | `two_pointers_opposite` |
| `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` |
| `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` |
| `two_pointers_same` | `bidirectional_index_scan` | `two_pointers_opposite` |
| `binary_search_standard` | `binary_search` | `two_pointers_opposite` |
| `binary_search_rotated` | `binary_search` | `two_pointers_opposite` |
| `binary_search_answer` | `binary_search` | `two_pointers_opposite` |
| `binary_search_tree` | `binary_search` | `two_pointers_opposite` |
| `dp_1d_forward` | `dp_bottom_up` | `recursive_branching` |
| `dp_1d_sequence` | `dp_bottom_up` | `recursive_branching` |
| `dp_2d_grid` | `dp_bottom_up` | `recursive_branching` |
| `dp_2d_string` | `dp_bottom_up` | `recursive_branching` |
| `dp_knapsack` | `dp_bottom_up` | `recursive_branching` |
| `dp_interval` | `dp_bottom_up` | `recursive_branching` |
| `dp_state_machine` | `dp_bottom_up` | `recursive_branching` |
| `bfs_level_order` | `bfs_shortest_path` | `recursive_branching` |
| `bfs_shortest_path` | `bfs_shortest_path` | `recursive_branching` |
| `dfs_recursive` | `recursive_branching` | `bfs_shortest_path` |
| `dfs_iterative` | — | `recursive_branching` |
| `linked_list_reversal` | `linked_list_traversal` | `two_pointers_opposite` |
| `backtracking_permutation` | `dfs_backtracking` | `dp_top_down` |
| `backtracking_subset` | `dfs_backtracking` | `dp_top_down` |

---

## 2. Phase 2: Seeded Problems

### 15 Problems Inserted (2958 skipped — not in problems table)

| # | ID | Title Slug | CSV Pattern | V1 Required | V1 Excluded | Groups |
|---|-----|-----------|-------------|-------------|-------------|:------:|
| 1 | 3 | longest-substring-without-repeating-characters | `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` | 1 |
| 2 | 209 | minimum-size-subarray-sum | `sliding_window_variable` | `sliding_window` | `two_pointers_opposite` | 1 |
| 3 | 2958 | max-subarray-length-of-length-k | — | — | — | skipped |
| 4 | 11 | container-with-most-water | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` | 1 |
| 5 | 125 | valid-palindrome | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` | 1 |
| 6 | 15 | 3sum | `two_pointers_opposite` | `two_pointers_opposite` | `binary_search` | 1 |
| 7 | 704 | binary-search | `binary_search_standard` | `binary_search` | `two_pointers_opposite` | 1 |
| 8 | 35 | search-insert-position | `binary_search_standard` | `binary_search` | `two_pointers_opposite` | 1 |
| 9 | 70 | climbing-stairs | `dp_1d_forward` | `dp_bottom_up` | `recursive_branching` | 2 |
| 10 | 322 | coin-change | `dp_1d_forward` | `dp_bottom_up` | `recursive_branching` | 2 |
| 11 | 62 | unique-paths | `dp_2d_grid` | `dp_bottom_up` | `recursive_branching` | 1 |
| 12 | 70 (top-down) | climbing-stairs | `dp_1d_forward` | `dp_top_down` | `dfs_backtracking` | (group_1) |
| 13 | 322 (top-down) | coin-change | `dp_1d_forward` | `dp_top_down` | `dfs_backtracking` | (group_1) |
| 14 | 46 | permutations | `backtracking_permutation` | `dfs_backtracking` | `dp_top_down` | 1 |
| 15 | 78 | subsets | `backtracking_subset` | `dfs_backtracking` | `dp_top_down` | 1 |
| 16 | 102 | binary-tree-level-order-traversal | `bfs_level_order` | `bfs_shortest_path` | `recursive_branching` | 1 |
| 17 | 496 | next-greater-element-i | `monotonic_stack` | `monotonic_stack_maintenance` | `sliding_window` | 1 |
| 18 | 200 | number-of-islands | `union_find` | `union_find` | — | 1 |

### Multi-Approach Problems

**Problem 70 (Climbing Stairs):**
- `group_0`: `dp_bottom_up` (iterative table filling)
- `group_1`: `dp_top_down` (memoized recursion)

**Problem 322 (Coin Change):**
- `group_0`: `dp_bottom_up` (iterative table filling)
- `group_1`: `dp_top_down` (memoized recursion)

### Authority Tier

All seeded groups use `structurally_observed` authority. This means:
- Contradictions CAN be authoritative (unlike `llm_proposed`)
- The shadow matcher can produce CONFIRMED and CONTRADICTED outcomes
- The matching layer trusts these groups as verified ground truth

---

## 3. Validation Results

### Pre-Insert Validation

All 18 solution groups passed `_validate_group()`:
- ✅ All required/optional/excluded IDs are valid V1 concepts
- ✅ No required∩excluded overlap
- ✅ No optional∩excluded overlap
- ✅ Authority tier is valid
- ✅ No mutually exclusive required strategies (dfs_backtracking ↔ dp_top_down)

### Post-Insert Shadow Analysis Verification

| Test | Strategy Detected | Outcome | Expected | Status |
|------|-------------------|---------|----------|:------:|
| LC 3 SW (correct) | `sliding_window` | CONFIRMED | CONFIRMED | ✅ |
| LC 11 TP (correct) | `two_pointers_opposite` | CONFIRMED | CONFIRMED | ✅ |
| LC 704 BS (correct) | `binary_search` | CONFIRMED | CONFIRMED | ✅ |
| LC 70 DP-BU (correct) | `dp_bottom_up` | CONFIRMED | CONFIRMED | ✅ |
| LC 46 BT (correct) | `dfs_backtracking` | CONFIRMED | CONFIRMED | ✅ |
| LC 102 BFS (correct) | `bfs_shortest_path` | CONFIRMED | CONFIRMED | ✅ |
| LC 496 MS (correct) | `monotonic_stack_strategy` | CONFIRMED | CONFIRMED | ✅ |
| LC 11 TP vs SW group | `sliding_window` | UNRESOLVED | UNRESOLVED | ✅ |
| LC 3 SW vs MS group | `monotonic_stack_strategy` | UNRESOLVED | UNRESOLVED | ✅ |
| LC 11 TP vs BS group | `binary_search` | UNRESOLVED | UNRESOLVED | ✅ |

**Key results:**
- ✅ All correct strategies → CONFIRMED
- ✅ Cross-strategy tests → UNRESOLVED (not false CONFIRMED)
- ✅ No false CONTRADICTED
- ✅ Existing production behavior unchanged

---

## 4. Complete Test Results

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Shadow (`pathforge/ast_analysis/shadow/`) | 426 | 0 | 426 |
| Backend (`pathforge/tests/`) | 109 | 0 | 109 |
| DB (`pathforge/db/`) | 7 | 0 | 7 |
| AST Engine (`pathforge/ast_engine/`) | 69 | 0 | 69 |
| Frontend (vitest) | 32 | 0 | 32 |
| Legacy AST (`src/ast_detection/`) | 481 | 1* | 482 |
| Legacy Semantic | 74 | 0 | 74 |
| Matching Engine | 50 | 0 | 50 |
| **Overall** | **1248** | **1** | **1249** |

\* Pre-existing: `test_detected_product_except_self` — unchanged.

### Net Change

- **+9 new tests** (V1 mapping exclusion tests in test_ground_truth_reconciliation.py)
- **+109 backend tests** (was 100, now 109 with new exclusion tests)
- **0 regressions**
- **0 new failures**

---

## 5. What Was NOT Modified

- ✅ Frontend — no changes
- ✅ ELO — no changes
- ✅ Recommendations — no changes
- ✅ AST/fact extraction — no changes
- ✅ Strategy logic — no changes
- ✅ Ground truth builder (LLM pipeline) — no changes
- ✅ Existing solution groups for other problems — preserved
- ✅ Production behavior — unchanged (legacy matcher still uses CSV patterns)

---

## 6. Files Changed

| File | Change |
|------|--------|
| `pathforge/services/problem_resolver.py` | Added `_get_v1_excluded_for_patterns()`, updated fallback path |
| `pathforge/tests/test_ground_truth_reconciliation.py` | Added 9 V1 mapping exclusion tests |
| `pathforge/scripts/seed_ground_truth.py` | New — seeding script for 18 problems |
| `pathforge/db/problem_ground_truth` table | 15 new/updated rows (structurally_observed) |

---

## 7. Confirmation

- ✅ LLM generation was NOT used — all groups built from CSV patterns + manual V1 mapping
- ✅ Unrelated ground truth was NOT modified — only the 15 seeded problems were touched
- ✅ Problem 2958 was skipped (not in problems table)
- ✅ Multi-approach problems (70, 322) have separate solution groups for bottom-up and top-down
- ✅ All groups validated before insert
- ✅ All groups pass shadow analysis verification
