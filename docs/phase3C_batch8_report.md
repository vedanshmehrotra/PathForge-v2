# Phase 3C Batch 8 — DP Detectors Implementation Report

## Summary

| Metric | Value |
|--------|-------|
| Batch | 8 |
| Focus | Dynamic Programming detectors |
| New Detectors | 7 |
| Total Detectors | 36 (33 taxonomy patterns fully covered) |
| Total Tests | +140 (DP-specific) |
| Taxonomy Coverage | 100% |

## Design Refinements Applied

1. **Space-optimized DP supported**: `dp_array_1d`/`dp_array_2d` are no longer mandatory evidence. Rolling variables, O(1) state transitions, and memoized recursion without explicit arrays are valid DP.

2. **Memoization philosophy clarified**: Cache decorator alone does not imply DP. Actual subproblem recurrence (recurrence expression combining lookback terms) is required.

3. **Interval DP emphasis**: `length_based_loop` is the primary structural signal for `dp_interval`. Weight increased from 0.25 to 0.35.

## New Detectors

| Pattern ID | Detector Class | Core Gate |
|-----------|----------------|-----------|
| `dp_1d_forward` | `DP1DForwardDetector` | `index_lookback` + at least 2 of: `dp_array_1d`, `table_fill_loop`, `cache_decorator` |
| `dp_state_machine` | `DPStateMachineDetector` | `state_variables` + `state_transition` + at least 1 secondary |
| `dp_1d_sequence` | `DP1DSequenceDetector` | `nested_fill_loops` + `inner_lookback` + at least 1 secondary |
| `dp_2d_grid` | `DP2DGridDetector` | `grid_lookback` + `nested_fill_loops` + at least 1 secondary |
| `dp_2d_string` | `DP2DStringDetector` | `string_compare` + `grid_lookback` + at least 1 secondary |
| `dp_knapsack` | `DPKnapsackDetector` | `capacity_compare` + `max_min_recurrence` + at least 1 secondary |
| `dp_interval` | `DPIntervalDetector` | `length_based_loop` + at least 2 supporting signals |

## Evidence Signals Added

| ID | Evidence Type | Default Weight | Used By |
|----|--------------|----------------|---------|
| E01 | `dp_array_1d` | 0.25 | dp_1d_forward, dp_1d_sequence, dp_state_machine |
| E02 | `dp_array_2d` | 0.25-0.30 | dp_2d_grid, dp_2d_string, dp_knapsack, dp_interval |
| E03 | `table_fill_loop` | 0.20 | dp_1d_forward, dp_state_machine |
| E04 | `nested_fill_loops` | 0.20-0.25 | dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack |
| E05 | `index_lookback` | 0.30 | dp_1d_forward |
| E06 | `grid_lookback` | 0.25-0.30 | dp_2d_grid, dp_2d_string, dp_knapsack, dp_interval |
| E07 | `inner_lookback` | 0.25 | dp_1d_sequence |
| E08 | `recurrence_expression` | 0.20-0.25 | All DP |
| E09 | `max_min_recurrence` | 0.25 | dp_knapsack |
| E10 | `string_compare` | 0.30 | dp_2d_string |
| E11 | `capacity_compare` | 0.30 | dp_knapsack |
| E12 | `length_based_loop` | 0.35 | dp_interval |
| E13 | `pair_loop` | 0.25 | dp_interval |
| E14 | `state_variables` | 0.30 | dp_state_machine |
| E15 | `state_transition` | 0.30 | dp_state_machine |
| E16 | `cache_decorator` | 0.30 | dp_1d_forward, dp_state_machine |
| E19 | `base_case_return` | 0.15 | dp_1d_forward, dp_2d_grid, dp_2d_string |
| E20 | `result_aggregation` | 0.15-0.20 | All DP |

## Test Coverage by Detector

| Detector | Positive Tests | Negative Tests | Key Patterns Tested |
|----------|---------------|----------------|---------------------|
| `dp_1d_forward` | 5 | 3 | Climbing Stairs, House Robber, Fibonacci (tab/memo), Min Cost Climbing Stairs |
| `dp_state_machine` | 5 | 3 | Stock w/ cooldown, House Robber (rolling), Paint House |
| `dp_1d_sequence` | 4 | 3 | LIS, Russian Doll, Sequence Partition |
| `dp_2d_grid` | 4 | 2 | Min Path Sum, Unique Paths, Maximal Square |
| `dp_2d_string` | 4 | 2 | LCS, Edit Distance, Distinct Subsequences |
| `dp_knapsack` | 4 | 2 | 0/1 Knapsack, Partition Equal Subset, Coin Change |
| `dp_interval` | 4 | 3 | Matrix Chain, Palindrome Partition, Longest Palindromic Subsequence |

## False Positive Prevention

Each detector includes anti-gates:
- **dp_1d_forward**: Blocks prefix sum (no max/min, single lookback), greedy local (scalar write), nested loops
- **dp_state_machine**: Blocks greedy stock (single variable), 1D forward (array tied to input)
- **dp_1d_sequence**: Blocks brute-force (reads `nums[j]`, not `dp[j]`), single-loop patterns
- **dp_2d_grid**: Blocks string compare patterns, pure 2D array creation without recurrence
- **dp_2d_string**: Blocks grid DP (no string compare), non-string patterns
- **dp_knapsack**: Blocks grid DP (no capacity compare), string DP
- **dp_interval**: Blocks grid DP (row/col loops, not length-based), string compare

## Registry Updates

- `src/ast_detection/detectors/__init__.py`: Added Batch 8 imports
- `docs/DETECTOR_COVERAGE.md`: Updated 7 rows from Pending to Implemented

## Remaining Work

None. All 33 taxonomy patterns are implemented.

Phase 3D (Matching Engine improvements) begins separately.
