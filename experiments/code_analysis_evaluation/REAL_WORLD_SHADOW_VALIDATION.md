# Real-World Shadow Validation Report

**Date:** 2026-08-28
**Test suite:** 1032/1032 passing (620 backend + 380 shadow + 32 frontend)
**Method:** Full shadow pipeline trace (facts → techniques → strategies → solution-group matching) on 30+ corpus entries

---

## 1. Downstream Impact Analysis: Monotonic Stack Co-Detection

### The critical test

A monotonic-stack solution (`ms_next_greater`) is matched against a sliding-window solution group (as would happen for a problem with `sliding_window` ground truth):

| Solution group | Match outcome | Primary strategy | Harmful? |
|---|---|---|:---:|
| `sliding_window` group | **CONFIRMED** | `monotonic_stack_strategy` | **YES** |
| `monotonic_stack` group | CONFIRMED | `monotonic_stack_strategy` | No |

**The monotonic stack code is CONFIRMED against the sliding-window group.** This means: if a user submits a monotonic-stack solution for a problem with `sliding_window` ground truth, the shadow system tells them their approach matches — when it doesn't.

### Cross-validation matrix

| Code type ↓ \ Solution group → | sliding_window | monotonic_stack |
|---|---|---|
| **Monotonic stack code** | **CONFIRMED (FP)** | CONFIRMED |
| **Sliding window code** | CONFIRMED | UNRESOLVED |
| **Two-pointers code** | CONTRADICTED | UNRESOLVED |

The monotonic-stack → sliding-window CONFIRMED match is a **genuine harmful false positive** at the matching layer.

### How many monotonic-stack entries are affected?

| Entry | Co-detection | Match vs SW group |
|---|---|---|
| `ms_next_greater` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_daily_temperatures` | sliding_window + monotonic_stack + dp_bottom_up | CONFIRMED ❌ |
| `ms_histogram` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_next_greater_renamed` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_largest_hist_renamed` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_trap_rain_water_stack` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_sum_subarray_mins` | sliding_window + monotonic_stack | CONFIRMED ❌ |
| `ms_stock_span` | monotonic_stack only | UNRESOLVED ✓ |
| `ms_next_greater_circular` | monotonic_stack only | UNRESOLVED ✓ |

**7 out of 9 monotonic-stack entries** produce a false CONFIRMED match against sliding-window groups. The remaining 2 (`ms_stock_span`, `ms_next_greater_circular`) do not trigger the co-detection because their while-loop body doesn't modify a variable used in a subsequent statement.

---

## 2. Accumulator-Window Failures

Three sliding-window implementations are misclassified as `two_pointers_opposite`:

| Entry | Expected | Detected | Match vs SW group |
|---|---|---|---|
| `sw_longest_ones` | sliding_window | two_pointers_opposite | **CONTRADICTED** |
| `sw_max_consecutive_ones` | sliding_window | two_pointers_opposite | **CONTRADICTED** |
| `fw_different_structure` | sliding_window | two_pointers_opposite | **CONTRADICTED** |

**Impact:** These are the **most harmful** failures. A correct sliding-window solution is actively told it contradicts the expected strategy. The `excluded: ["two_pointers_opposite"]` rule in the solution group fires because `two_pointers_opposite` is detected.

**Why it happens:** The while-loop body has both an increment (`left += 1`) and a decrement (`zeros -= 1` or `acc -= nums[i-size]`), which triggers `opposite_direction_updates` → `bidirectional_index_scan` → `two_pointers_opposite`.

---

## 3. Index-Arithmetic Window Failures

Four sliding-window implementations produce no strategy detection:

| Entry | Expected | Detected | Match vs SW group |
|---|---|---|---|
| `sw_permutation_in_string` | sliding_window | (none) | UNRESOLVED |
| `sw_max_points_from_cards` | sliding_window | (none) | UNRESOLVED |
| `sw_with_counter` | sliding_window | (none) | UNRESOLVED |
| `fw_not_k_parameter` | sliding_window | (none) | UNRESOLVED |

**Impact:** Moderate. The user gets no feedback about their approach. The system reports UNRESOLVED rather than a wrong answer, so it doesn't actively mislead — but it fails to confirm a correct approach.

---

## 4. If-Shrink Miss

Problem 424-style if-shrink pattern:

| Entry | Expected | Detected | Match vs SW group |
|---|---|---|---|
| 424 pattern | sliding_window | (none) | UNRESOLVED |

**Impact:** Moderate. Same as index-arithmetic — UNRESOLVED rather than wrong.

---

## 5. Summary of Real-World Harm

| Failure mode | Count | Severity | Harm type |
|---|:---:|:---:|---|
| **Monotonic stack → SW CONFIRMED** | 7 | **HIGH** | False confirmation (user told wrong approach matches) |
| **Accumulator window → CONTRADICTED** | 3 | **CRITICAL** | False contradiction (user told correct approach is wrong) |
| **Index-arithmetic → UNRESOLVED** | 4 | MEDIUM | No feedback (correct approach not confirmed) |
| **If-shrink → UNRESOLVED** | 1+ | MEDIUM | No feedback (correct approach not confirmed) |

---

## 6. Comparison With Previous Baseline

| Metric | Pre-fix | Post-fix | Change |
|---|:---:|:---:|:---:|
| SW detection rate (corpus) | ~30% (est.) | 76.7% | +47pp |
| Monotonic stack FP (new) | 0 | 7 | +7 |
| Accumulator CONTRADICTED (new) | 0 | 0 | unchanged |
| Index-arithmetic UNRESOLVED (pre-existing) | 4 | 4 | unchanged |
| If-shrink UNRESOLVED (pre-existing) | 1+ | 1+ | unchanged |

The fix improved detection rate significantly but introduced 7 new high-severity false confirmations on monotonic stack cases.

---

## 7. Answers to Required Questions

### 1. Does monotonic_stack → sliding_window co-detection cause actual harmful matches?

**Yes.** 7 out of 9 monotonic-stack entries produce a CONFIRMED match against sliding-window solution groups. This means a user submitting a monotonic-stack solution for a problem with sliding-window ground truth is told their approach matches — when it fundamentally doesn't.

### 2. How often does it change the final shadow outcome?

**7 out of 9 monotonic-stack cases** (78%). The co-detection causes CONFIRMED where the correct outcome should be UNRESOLVED (monotonic stack technique is not required by the sliding-window group, but the co-detected sliding_window strategy satisfies the required field).

### 3. How often are sliding-window misses seen in realistic code?

**3 out of 30 corpus entries** produce CONTRADICTED (accumulator-window pattern). **4 out of 30** produce UNRESOLVED (index-arithmetic/if-shrink). Total: **7 out of 30 (23%)** of sliding-window implementations fail to produce a correct CONFIRMED match.

### 4. Which remaining issue has the highest real-world impact?

**The accumulator-window CONTRADICTED failures** (3 cases) are the highest impact. These actively mislead users by telling them their correct sliding-window approach contradicts the expected strategy. The monotonic-stack CONFIRMED failures (7 cases) are the second highest — they don't actively mislead but confirm an incorrect match.

### 5. Should we implement another change now, or continue observing?

**The accumulator-window CONTRADICTED failures warrant immediate attention.** They are the only failures that actively produce incorrect negative feedback to users. The fix would be in the strategy evaluator's absence constraint (`must NOT have opposite_direction_updates`), which is too strict for accumulator-based windows.

The monotonic-stack CONFIRMED failures are also concerning but less urgent — they produce false confirmation rather than false contradiction. A potential fix would use the existing `monotonic_comparison` + `stack_operation` facts to suppress the sliding_window co-detection, but this requires strategy-evaluator changes.

The index-arithmetic and if-shrink UNRESOLVED cases are the lowest priority — they produce no feedback rather than wrong feedback.
