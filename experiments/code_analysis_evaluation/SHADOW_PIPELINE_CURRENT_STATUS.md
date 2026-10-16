# SHADOW_PIPELINE_CURRENT_STATUS.md

**Date:** 2026-08-29
**Branch:** `architecture/strategy-evidence-spike`
**Method:** Live codebase inspection + full test suite + comprehensive pipeline trace on 25+ representative implementations

---

## 1. Current Architecture

```
Source Code
    ↓
Fact Extraction (fact_extractor.py)       ← 30+ fact types, deterministic, naming-independent
    ↓
Technique Detection (techniques.py)      ← 10 techniques, non-exclusive evidence
    ↓
Strategy Evaluation (strategies.py)      ← 9 strategy evaluators with absence constraints
    ↓
Solution-Group Matching (matching.py)    ← CONFIRMED / UNRESOLVED / CONTRADICTED
    ↓
Ground Truth (ground_truth_builder.py)   ← LLM-generated, cached in DB
    ↓
Coherence Validation (coherence.py)      ← Mutual exclusion warnings
```

### Two Parallel Paths Today

| Path | Drives Production? | Architecture |
|------|:------------------:|:-------------|
| **Legacy** | ✅ Yes | AST/semantic detection → legacy pattern matching → flat labels |
| **Shadow** | ❌ Observational | Facts → techniques → strategies → solution groups → outcome |

The legacy path produces the user-facing result. The shadow path runs alongside but its output is not shown to users or used for ELO/gap/recommendation decisions.

---

## 2. Test Suite Status

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Shadow (`pathforge/ast_analysis/shadow/`) | 417 | 0 | 417 |
| Backend (`pathforge/tests/`) | 100 | 0 | 100 |
| AST Engine (`pathforge/ast_engine/`) | 69 | 0 | 69 |
| DB (`pathforge/db/`) | 7 | 0 | 7 |
| Legacy AST (`src/ast_detection/`) | 481 | 1* | 482 |
| Legacy Semantic | 74 | 0 | 74 |
| Matching Engine | 50 | 0 | 50 |
| Frontend (vitest) | 32 | 0 | 32 |
| **Overall** | **1230** | **1** | **1231** |

\* Pre-existing: `test_detected_product_except_self` — legacy prefix-sum detector limitation.

---

## 3. Live Pipeline Trace Results

### What the shadow pipeline reliably recognizes today

| Algorithm Family | Representative Cases | Strategy Detected | Confidence | Verdict |
|---|---|---|:---:|:---:|
| **Sliding Window (variable)** | LC 209, 3, 2958, 424 (while), 76, 438 | `sliding_window` | 0.75 | **Reliable** |
| **Sliding Window (fixed)** | LC 643 | `sliding_window` | 0.80 | **Reliable** |
| **Two Pointers (opposite)** | LC 11, 15, 125, 42 | `two_pointers_opposite` | 0.90 | **Reliable** |
| **Binary Search** | LC 704, 34 (overflow-safe) | `binary_search` | 0.85 | **Reliable** |
| **DP Bottom-Up** | LC 322, 70 | `dp_bottom_up` | 0.80 | **Reliable** |
| **Monotonic Stack** | LC 496, 739, 84 | `monotonic_stack_strategy` | 0.85 | **Reliable** |
| **BFS** | LC 102 | `bfs_shortest_path` | 0.80 | **Reliable** |
| **DFS/Backtracking** | LC 46, 78 | `dfs_backtracking` | 0.00 | **Detected, but confidence broken** |
| **DP Top-Down** (direct recursion) | LC 70 top-down | `dp_top_down` | 0.85 | **Reliable** |
| **Union-Find** | LC 200 variant | `union_find` | 0.85 | **Reliable** |

### What still has coverage gaps

| Algorithm Family | Representative Cases | Strategy Detected | Issue |
|---|---|---|---|
| **DP Top-Down** (nested function) | LC 322 memo variant | **none** | `visit_FunctionDef` doesn't recurse into inner functions |
| **Sliding Window** (if-shrink) | LC 424 if-shrink variant | **none** | `variable_use_in_loop_body` misses return-outside-loop |
| **Greedy** | Various | **none** | No V1 technique for greedy (not a structural pattern) |
| **Heap/Priority Queue** | Various | **none** | No V1 technique for heap operations |
| **DFS (iterative)** | LC 94 iterative inorder | **none** | No V1 technique for iterative DFS |
| **Topological Sort** | Various | **none** | No V1 technique (maps to optional BFS in ground truth) |

---

## 4. Known Failure Classes

### A. Extraction Failures (fact_extractor.py)

| Failure | Root Cause | Impact |
|---------|-----------|--------|
| **DP top-down with nested function** | `visit_FunctionDef` only visits top-level function defs. Inner `def dfs()` calls aren't detected as `recursive_call_in_conditional` or `multiple_recursive_paths` | `dp_top_down` doesn't fire for the most common memoization pattern |
| **If-shrink return outside loop** | `variable_use_in_loop_body` only checks variables used in subsequent statements within the loop body. Return statements at function level aren't checked. | `sliding_window` misses if-shrink variants |
| **DFS iterative** | No fact for iterative DFS patterns (stack-based tree traversal) | No strategy fires |
| **Stack name heuristic** | `stack_operation` requires variable name in `_STACK_LIKE_NAMES` set. Custom names like `st`, `s`, `mono_stack` work but truly arbitrary names don't. | Monotonic stack detection misses uncommonly-named stacks |

### B. Technique Inference Failures (techniques.py)

| Failure | Root Cause | Impact |
|---------|-----------|--------|
| **DFS/Backtracking confidence=0.0** | Strategy fires via fallback path (`self_recursive_call` + `early_termination` + `state_restoration`), but confidence is sourced from `recursive_branching` technique which didn't fire | User sees 0% confidence for a correctly detected strategy |
| **Recursive branching requires if/else** | `recursive_call_in_conditional` requires the recursive call to be inside an if/else. Functions where recursion is in a for-loop (like `backtrack`) don't trigger it. | `recursive_branching` technique under-fires |

### C. Strategy Evaluation Gaps

| Failure | Root Cause | Impact |
|---------|-----------|--------|
| **No greedy strategy** | No V1 technique captures greedy choice + optimal substructure | Greedy solutions always get UNRESOLVED |
| **No heap strategy** | No V1 technique captures heap/priority queue usage | Heap solutions always get UNRESOLVED |
| **Sequential accumulation over-detects** | Fires for almost any while-loop with an augmented variable, including monotonic stack and binary search | Noise — it's detected but doesn't harm matching |

### D. Ground Truth / Matching Issues

| Failure | Root Cause | Impact |
|---------|-----------|--------|
| **LLM authority gating** | Solution groups from LLM are `llm_proposed` tier. Contradictions are downgraded to UNRESOLVED. | Cannot produce authoritative CONTRADICTED for any LLM-proposed group |
| **Missing ground truth** | Most problems don't have ground truth in the DB yet | Shadow matching always returns UNRESOLVED for problems without ground truth |

---

## 5. Strengths of the Shadow Pipeline

1. **Zero false confirmations (after recent fixes).** The monotonic-stack exclusion and opposite_direction_updates refinement eliminated all known harmful false positives.

2. **Zero false contradictions.** No correct solution is ever told it's wrong.

3. **9 strategy families detected.** Covers the majority of algorithmic patterns seen on LeetCode.

4. **Deterministic fact extraction.** Same code always produces same facts. No randomness, no LLM in the hot path.

5. **Clean separation of concerns.** Facts → techniques → strategies → matching. Each layer is independently testable and replaceable.

6. **Authority gating prevents harm.** LLM-proposed groups cannot produce authoritative CONTRADICTED, preventing LLM mistakes from becoming harmful user feedback.

7. **417 shadow tests, all passing.** Strong regression coverage for the core pipeline.

8. **Correct negative results.** Binary search doesn't gain sliding_window. Monotonic stack doesn't gain two-pointers. DP doesn't gain BFS. These exclusions are structurally sound.

---

## 6. Weaknesses of the Shadow Pipeline

1. **DFS/Backtracking reports 0% confidence.** The strategy fires correctly but the confidence value is meaningless. This would confuse users if shown.

2. **DP top-down with nested functions doesn't detect.** The most common memoization pattern (inner `def dfs`) is invisible to the technique layer.

3. **No greedy/heap/iterative-DFS strategies.** These are common algorithm families that always get UNRESOLVED.

4. **Ground truth coverage is sparse.** Most problems have no solution groups in the DB, making the matching layer return UNRESOLVED for everything.

5. **Sequential accumulation is noisy.** It fires for almost every loop with augmentation, including monotonic stack and binary search loops. It doesn't cause harm but adds noise.

6. **Confidence values are not calibrated.** Different strategies have different confidence baselines (0.75, 0.80, 0.85, 0.90) that aren't grounded in measured accuracy.

---

## 7. Legacy vs Shadow Comparison

| Dimension | Legacy | Shadow |
|-----------|--------|--------|
| **False confirmations** | Known (monotonic stack → SW was 7/9) | **0** (after fixes) |
| **False contradictions** | Accumulator windows → CONTRADICTED | **0** |
| **Coverage** | AST/semantic patterns from `src/` | 9 strategy families |
| **Extensibility** | Adding patterns requires modifying detection code + tests | Adding strategies = new evaluator function |
| **Confidence** | Not available | Available (but needs calibration) |
| **Production status** | Drives user-facing results | Observational only |
| **Test coverage** | 555 legacy tests + 417 shadow tests | Shadow has stronger structural guarantees |

### Is shadow safer than legacy?

**Yes, for two reasons:**
1. Shadow has zero known false confirmations after recent fixes. Legacy had 7 harmful monotonic-stack → SW false confirmations.
2. Shadow never produces false contradictions. Legacy produced CONTRADICTED for correct accumulator-window solutions.

### Is shadow more useful than legacy?

**Not yet, because:**
1. Shadow output is not shown to users.
2. Ground truth coverage is too sparse for the matching layer to produce CONFIRMED for most problems.
3. Confidence values need calibration before display.

---

## 8. CONFIRMED / UNRESOLVED / CONTRADICTED Behavior

### Is it behaving as intended?

**Yes, with one issue.**

- **CONFIRMED:** Fires when a solution group's required strategies are all detected with sufficient confidence. Works correctly.
- **UNRESOLVED:** Fires when no solution group is satisfied or when the only match is against a non-authoritative (LLM-proposed) group that contradicts. Works correctly.
- **CONTRADICTED:** Only fires for authoritative solution groups (`structurally_observed`, `externally_listed`, `editorial`). Since all current ground truth is `llm_proposed`, **CONTRADICTED never fires in practice.** This is by design — it prevents LLM mistakes from being authoritative.

### The one issue

When a solution group contradicts but has `llm_proposed` authority, the outcome is downgraded to UNRESOLVED. The `reasoning` field documents this, but there's no way for the user to know *why* it's unresolved. This is acceptable for now but will need UX attention when shadow becomes primary.

---

## 9. Confidence Values: Are They Meaningful?

**Partially.**

- **Strategies with `confidence > 0`:** The confidence comes from the supporting technique's `presence_confidence`. These are hand-tuned values (0.75, 0.80, 0.85, 0.90) that reflect our structural confidence, not measured accuracy.
- **DFS/Backtracking:** confidence = 0.0 because the strategy fires via a fallback path that doesn't source confidence from `recursive_branching`. This is a bug.
- **Binary Search:** confidence = 0.85 (hardcoded, not technique-sourced). This is fine but would be better if derived from evidence strength.

**Recommendation:** Fix the DFS/Backtracking confidence bug. Don't invest in calibrating confidence values until shadow is showing output to real users.

---

## 10. What Prevents Shadow From Being Primary Today

| Blocker | Severity | Fixable Now? |
|---------|:--------:|:---:|
| Ground truth coverage too sparse | **HIGH** | Partially (can generate for top 100 problems) |
| DFS/Backtracking confidence = 0.0 | MEDIUM | Yes (small fix) |
| DP top-down nested function not detected | MEDIUM | Yes (fact extractor change) |
| No greedy/heap strategies | MEDIUM | No (needs V1 vocabulary extension) |
| Confidence not calibrated | LOW | No (needs user testing first) |
| Frontend not showing shadow output | LOW | Yes (but premature) |

**The biggest blocker is ground truth coverage.** Without solution groups in the DB, the matching layer always returns UNRESOLVED. The shadow pipeline can detect strategies, but without knowing which strategies the problem expects, it can't confirm or contradict.

---

## 11. Issues Ranked by User Impact

### A. Problems worth fixing now

1. **DFS/Backtracking confidence = 0.0** — Users see 0% confidence for a correctly detected strategy. Simple fix: use strategy-level confidence or fallback to a default when technique isn't detected.

2. **DP top-down with nested function** — The most common memoization pattern doesn't detect. Affects a significant fraction of DP problems users encounter.

3. **Generate ground truth for top problems** — Without this, the matching layer is useless.

### B. Problems that can remain limitations

4. **LC 424 if-shrink** — A single structural variant that misses. The while-shrink variant works. Users can learn the working pattern.

5. **Greedy/heap/iterative-DFS** — These require new V1 vocabulary entries. Acceptable limitation for Phase 1.

6. **Sequential accumulation noise** — Fires for too many things but doesn't cause harm. Leave it.

7. **Stack name heuristic** — Works for all common names. Truly arbitrary names are edge cases.

### C. Problems caused by the legacy matcher that should NOT be fixed in shadow

8. **Legacy false contradictions on accumulator windows** — This is a legacy bug. Fix it in the legacy path if needed, but the shadow path already handles it correctly.

9. **Legacy monotonic-stack → SW false confirmations** — Already fixed in shadow. The legacy path's issue is separate.

10. **Legacy prefix-sum detection failure** — The pre-existing test failure is in `src/` legacy code. Shadow doesn't have this problem.

---

## 12. Top 3 Fixes Worth Doing Next

### Fix 1: DFS/Backtracking confidence fallback
**Effort:** Small (5-10 lines in `strategies.py`)
**Impact:** Corrects misleading 0% confidence display
**Risk:** None — only affects confidence value, not strategy detection

### Fix 2: DP top-down nested function detection
**Effort:** Medium (extend `visit_FunctionDef` or add `visit_FunctionDef` to inner function detection)
**Impact:** Enables detection of the most common memoization pattern
**Risk:** Low — needs careful testing to avoid false positives on non-DP inner functions

### Fix 3: Generate ground truth for top 50 problems
**Effort:** Medium (run LLM generation pipeline)
**Impact:** Enables the matching layer to produce CONFIRMED/CONTRADICTED for real problems
**Risk:** Low — existing ground truth builder + validation pipeline handles this

---

## 13. What Should NOT Be Fixed

- **Do NOT add new strategy families** (greedy, heap, etc.) until the existing 9 are fully validated in production.
- **Do NOT calibrate confidence values** until shadow is showing output to real users.
- **Do NOT wire shadow output to the frontend** until ground truth coverage is sufficient.
- **Do NOT modify the fact extractor for edge cases** that affect <5% of problems.
- **Do NOT add exclusion rules for patterns that already produce UNRESOLVED** — UNRESOLVED is safe.

---

## 14. Recommendation

### **Option A: Continue targeted shadow improvements**

**This is the right choice.** Here's why:

1. The shadow architecture is sound. The 3-layer pipeline (facts → techniques → strategies) produces correct structural distinctions for 9 algorithm families. The matching layer correctly gates outcomes with authority tiers.

2. The remaining issues are specific and fixable: DFS confidence bug (5 lines), DP top-down inner function detection (medium), ground truth generation (run existing pipeline).

3. Making shadow primary without fixing the DFS confidence bug would show 0% confidence to users for correctly detected backtracking solutions. Making shadow primary without ground truth would show UNRESOLVED for everything.

4. The project is a third-year student project. The right move is to make the existing architecture reliable for the 9 strategies it supports, then demonstrate it with real problems. Adding new strategy families or calibration infrastructure is premature.

**Immediate next steps:**
1. Fix DFS/Backtracking confidence (1 hour)
2. Fix DP top-down inner function detection (half day)
3. Generate ground truth for top 50 problems (run existing pipeline, 1 day)
4. Show shadow output alongside legacy in a feature flag (1 day)
5. Collect feedback and decide on full cutover

**Estimated effort to shadow-as-primary:** 3-4 days of targeted work.
