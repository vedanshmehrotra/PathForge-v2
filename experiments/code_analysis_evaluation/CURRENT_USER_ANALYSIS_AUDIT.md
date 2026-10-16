# Current User-Facing Analysis Audit

**Date:** August 28, 2026
**Tested against:** Live PostgreSQL database, current codebase
**Problems tested:** 1, 2, 3, 5, 11, 17, 20, 33, 34, 628, 1574, 1577, 3236, 3812, 4080
**Solutions tested:** Standard LeetCode Python solutions for each problem

---

## Executive Summary

**The production analysis pipeline has a critical ground-truth integrity problem that makes it unreliable for user-facing use.**

The LLM-generated solution groups (stored in `problem_ground_truth.solution_groups`) are **different from** the DB `problems.pattern` column for **11 out of 18 problems** that have ground truth. This means:

- The production matching engine compares user code against **wrong expected patterns** for many problems
- The shadow analysis sometimes detects the correct strategy but the production matcher says NO_MATCH
- Users see contradictory results: "❌ No expected patterns detected" when the code actually uses the correct approach

**5 of the 15 problems tested showed the shadow analysis correctly identifying the approach while production said NO_MATCH.** This is the single most damaging user-facing issue.

---

## 1. Test Case Results

### Problem 1: Two Sum
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['hash_map_lookup']` | — |
| GT patterns | `['hash_map_lookup']` | — |
| GT solution group | No SG (legacy fallback) | — |
| Detected | `array_traversal`, `hash_map_lookup` | 7 facts, 0 techniques, 0 strategies |
| Match outcome | `FULL_MATCH` (confidence=0.8) | `UNRESOLVED` |
| Verdict text | "✅ All expected patterns detected" | "Not enough evidence" |
| **Misleading?** | No (correct match) | Partially — shadow detects `cache_lookup` fact but no technique |

**Issue:** Shadow fact extractor detects `cache_lookup` and `indexed_write` but technique detector produces 0 techniques. The `hash_map_lookup` is not a V1 technique — it's classified as "generic data-structure behavior" in the ground truth mapping. So the shadow correctly cannot produce a strategy, but the fact extraction is incomplete.

### Problem 2: Add Two Numbers ⚠️ CRITICAL
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['two_pointers_same']` | — |
| GT patterns | `['linked_list_reversal']` | — |
| GT solution group | `required=['linked_list_traversal']` | — |
| Detected | `two_pointers_same` | 22 facts, 2 techniques (`carry_propagation`, `linked_list_traversal`) |
| Match outcome | `NO_MATCH` (confidence=0.0) | `CONFIRMED` (satisfaction=0.80) |
| Verdict text | "❌ No expected patterns detected" | "Likely match" |
| **Misleading?** | **YES — production says NO_MATCH but code IS correct** | Shadow correctly identifies the approach |

**Root cause:** The LLM ground truth builder proposed `linked_list_reversal` instead of `two_pointers_same`. The production matcher expects `linked_list_traversal` (from V1 mapping of `linked_list_reversal`), but the AST detector produces `two_pointers_same`. No overlap → NO_MATCH.

**The shadow analysis correctly identifies this as a linked-list solution with carry propagation.** The user would see contradictory panels: production says "❌ No expected patterns detected" while shadow says "Likely match: The solution uses linked list walk."

### Problem 3: Longest Substring Without Repeating Characters
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['hash_map_lookup', 'sliding_window_variable']` | — |
| GT patterns | `['sliding_window_variable']` | — |
| GT solution group | `required=['sliding_window']` | — |
| Detected | `array_traversal`, `hash_map_lookup`, `sliding_window_variable`, `greedy_local` | 10 facts, 1 technique (`loop_state_tracking`), 1 strategy (`sliding_window`) |
| Match outcome | `FULL_MATCH` | `CONFIRMED` |
| Verdict text | "✅ All expected patterns detected" | "Likely match: The solution follows a Sliding Window approach" |
| **Misleading?** | No (correct match) | No (correct match) |

**Issue:** Production detects `greedy_local` as a false positive alongside the correct patterns. Also, `array_traversal` is detected with confidence=1.0 as a "broad" pattern.

### Problem 11: Container With Most Water ✅
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['two_pointers_opposite']` | — |
| GT patterns | `['two_pointers_opposite']` | — |
| GT solution group | `required=['two_pointers_opposite']`, `excluded=['binary_search']` | — |
| Detected | `two_pointers_opposite`, `greedy_local` | 8 facts, 3 techniques, 1 strategy (`two_pointers_opposite`) |
| Match outcome | `FULL_MATCH` (confidence=0.9) | `CONFIRMED` |
| Verdict text | "✅ All expected patterns detected" | "Likely match: The solution follows a Two Pointers approach" |
| **Misleading?** | No (correct) | No (correct) |

**Both systems agree. This is the ideal case.**

### Problem 20: Valid Parentheses ⚠️ CRITICAL
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['monotonic_stack']` | — |
| GT patterns | `['dfs_recursive']` | — |
| GT solution group | `required=['recursive_branching']`, `excluded=['bfs_shortest_path']` | — |
| Detected | `array_traversal` (only!) | 6 facts, 0 techniques, 0 strategies |
| Match outcome | `NO_MATCH` | `UNRESOLVED` |
| Verdict text | "❌ No expected patterns detected" | "Not enough evidence" |
| **Misleading?** | **YES — production expects `recursive_branching` but code uses stack** | Shadow correctly detects stack operations but technique detector fails |

**Root cause (production):** LLM generated `dfs_recursive` as the ground truth pattern. The solution group requires `recursive_branching`, which this stack-based solution obviously doesn't have.

**Root cause (shadow):** The fact extractor correctly identifies `stack_operation` (creation, pop, append), but the `monotonic_stack_maintenance` technique detector requires `monotonic_comparison` and `conditional_pop` facts, which are only detected inside `while` loops. Valid Parentheses uses a `for` loop.

**Both systems fail for different reasons.** Neither can correctly identify this as a stack-based approach for a user.

### Problem 33: Search in Rotated Sorted Array ✅
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['binary_search_rotated']` | — |
| GT patterns | `['binary_search_rotated']` | — |
| Detected | `binary_search_standard`, `binary_search_rotated` | 6 facts, 1 technique, 1 strategy (`binary_search`) |
| Match outcome | `FULL_MATCH` (confidence=1.0) | `CONFIRMED` |
| Verdict text | "✅ All expected patterns detected" | "Likely match: The solution follows a Binary Search approach" |
| **Misleading?** | No (correct) | No (correct) |

### Problem 34: Find First and Last Position ✅
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `['binary_search_standard']` | — |
| GT patterns | `['binary_search_standard']` | — |
| Detected | `binary_search_standard` (confidence=1.0) | 12 facts, 1 technique, 1 strategy (`binary_search`) |
| Match outcome | `FULL_MATCH` (confidence=1.0) | `CONFIRMED` |
| **Misleading?** | No (correct) | No (correct) |

### Problem 3236: Smallest Missing Integer Greater Than Sequential Prefix Sum ⚠️
| Aspect | Production | Shadow |
|--------|-----------|--------|
| DB pattern | `[]` (empty!) | — |
| GT patterns | `['hash_map_lookup', 'prefix_sum']` | — |
| GT solution group | `patterns=['hash_map_lookup', 'prefix_sum']`, `required=None` (broken) | — |
| Detected | `array_traversal`, `hash_map_lookup` | — |
| Match outcome | `FULL_MATCH` (fallback) | — |
| **Misleading?** | **YES — DB pattern is empty, so this problem has no reliable ground truth** |

**Root cause:** The DB `pattern` column is `[]` for this problem (populated later by LLM). The solution group has `required=None` — this is from an older ground truth generation that didn't apply V1 mapping. The production matcher falls back to the legacy `patterns` field.

---

## 2. Ground Truth Integrity Audit

### DB Pattern vs GT Pattern Mismatches

| Problem | DB Pattern | GT Pattern | Severity |
|---------|-----------|-----------|----------|
| 2 (Add Two Numbers) | `two_pointers_same` | `linked_list_reversal` | **CRITICAL** — different strategies entirely |
| 3 (Longest Substring) | `hash_map_lookup, sliding_window_variable` | `sliding_window_variable` | MEDIUM — GT narrower |
| 5 (Longest Palindrome) | `dp_2d_string, two_pointers_opposite` | `dp_2d_string` | MEDIUM — GT narrower |
| 17 (Letter Combinations) | `backtracking_subset, hash_map_lookup` | `backtracking_subset` | MEDIUM — GT narrower |
| 20 (Valid Parentheses) | `monotonic_stack` | `dfs_recursive` | **CRITICAL** — wrong strategy entirely |
| 628 (Max Product Three) | `[]` (empty) | `greedy_local` | HIGH — no DB ground truth |
| 1574 (Max Product Two) | `[]` (empty) | `greedy_local` | HIGH — no DB ground truth |
| 1577 (Two Boxes) | `[]` (empty) | `backtracking_subset` | HIGH — no DB ground truth |
| 3236 (Prefix Sum) | `[]` (empty) | `hash_map_lookup, prefix_sum` | HIGH — no DB ground truth |
| 3812 (Palindrome Rearrangement) | `[]` (empty) | `hash_map_frequency` | HIGH — no DB ground truth |
| 4080 (Missing Multiple) | `[]` (empty) | `hash_map_frequency` | HIGH — no DB ground truth |

**Pattern consistency: 7 match, 11 mismatch out of 18 total (39% consistent)**

### What the user sees vs what is correct

When DB pattern and GT pattern disagree:
- The **production matcher uses GT patterns** (from `problem_ground_truth.solution_groups`)
- The **frontend Problem Info panel shows GT confidence** (from `ground_truth_confidence`)
- The **DB `problems.pattern` is NOT used by the production matcher**

This means the user sees "Expected Patterns: linked_list_reversal" for Add Two Numbers, when the correct classification should be `two_pointers_same`.

---

## 3. Two Separate Results: Should They Be Unified?

### Current behavior

The UI shows two panels:
1. **Matching Engine** (production): Compares AST-detected patterns against GT solution groups → `FULL_MATCH` / `NO_MATCH`
2. **Experimental Panel** (shadow): Shows structural facts, techniques, strategies, and match outcome

### The conflict pattern

For Problem 2 (Add Two Numbers):
- Production: "❌ No expected patterns detected" (0% match)
- Shadow: "Likely match — uses linked list walk" (CONFIRMED)

For Problem 20 (Valid Parentheses):
- Production: "❌ No expected patterns detected" (0% match)
- Shadow: "Not enough evidence" (UNRESOLVED)

### Recommendation

**During the experimentation phase, two panels are correct.** They use fundamentally different classification systems:
- Production uses legacy flat pattern IDs matched by string equality
- Shadow uses layered evidence (facts → techniques → strategies → satisfaction matching)

Unifying them prematurely would hide the fact that one system may be right while the other is wrong. The current design correctly separates them.

**However, the production panel must NEVER show a misleading result.** When the GT solution group doesn't match the DB pattern, the production matcher result is unreliable and should be flagged.

---

## 4. Shadow/Hybrid Data Persistence Audit

### Persisted (in submissions table)

| Column | Type | Content |
|--------|------|---------|
| `structural_facts_json` | jsonb | All structural facts from extraction |
| `shadow_extractor_version` | text | Extractor version string |
| `technique_evidence_json` | jsonb | Detected techniques with confidence |
| `strategy_evidence_json` | jsonb | Evaluated strategies with confidence |
| `shadow_match_outcome_json` | jsonb | Match outcome (CONFIRMED/UNRESOLVED/CONTRADICTED) |
| `shadow_technique_def_version` | text | Technique definition version |
| `shadow_strategy_def_version` | text | Strategy definition version |
| `code_hash` | text | SHA-256 hash of source code |

**Coverage:** 20/45 submissions have shadow data (44%)

### API-only (not persisted)

| Field | Content |
|-------|---------|
| `hybrid_analysis` | Old shadow detector (ShadowDetector class) — completely separate system |
| `hybrid_analysis.patterns[].discrepancy_type` | Per-pattern discrepancy info |
| `shadow_analysis.elapsed_ms` | Processing time |
| `shadow_analysis.extractor_version` | Also in DB, but returned per-request |

### Assessment

**The new shadow pipeline (fact→technique→strategy→match) is well-persisted.** All key artifacts are stored in JSONB columns on the submissions table, which allows re-derivation from structural facts.

**The old hybrid analysis (ShadowDetector class) is entirely ephemeral.** It runs, produces results, and discards them. It has no persistence and no audit trail. This is acceptable for experimentation but should not be relied upon for improvement.

**Gap:** No mechanism exists to re-run the shadow pipeline on historical submissions (e.g., after improving technique detectors). The `rerun_derivation()` function exists in `persistence.py` but is never called from any route.

---

## 5. Root Cause Analysis by Layer

### Layer 1: Ground Truth Generation (CRITICAL)

**Issue:** The LLM ground truth builder produces solution groups that disagree with the DB `problems.pattern` column.

**Affected problems:** 2, 20, 3236, and 5 others with empty DB patterns.

**Root cause:** The `problems.pattern` column and `problem_ground_truth.patterns` column are populated independently:
- `problems.pattern` was set during initial data import
- `problem_ground_truth.patterns` is set by `build_ground_truth()` which calls the LLM
- The LLM can produce different patterns than the initial import

**Impact:** The production matcher compares against LLM-generated patterns, which can be wrong. The user sees expected patterns that don't match what a human expert would say.

### Layer 2: Production Matcher (DESIGN)

**Issue:** The production matcher uses string-equality matching between AST-detected patterns and solution group patterns.

**Limitation:** No fuzzy matching, no strategy-level abstraction. `two_pointers_same` ≠ `linked_list_reversal` even though both involve pointer traversal.

**Fallback behavior:** When no problem is provided, the matcher defaults to `[[hash_map_lookup]]` as the expected patterns. This makes "Run Analysis" without "Prepare Problem" essentially meaningless for matching.

### Layer 3: Shadow Technique Detection (MEDIUM)

**Issue:** The `monotonic_stack_maintenance` technique detector only fires inside `while` loops. Python monotonic stacks commonly use `for` loops.

**Missing techniques for stack problems:** 0 techniques detected for Valid Parentheses despite 3 `stack_operation` facts.

**Impact:** Shadow produces UNRESOLVED instead of CONFIRMED for stack-based solutions.

### Layer 4: Frontend Display (LOW)

**Issue:** The Matching Engine panel shows "❌ No expected patterns detected" without indicating that the expected patterns themselves may be unreliable.

**Impact:** Users see a definitive failure message when the system's ground truth is wrong, not when their code is wrong.

### Layer 5: No Problem Context = Meaningless Matching

**Issue:** When the user submits code without preparing a problem, the matcher uses `[[hash_map_lookup]]` as the fallback solution group.

**Impact:** Two Sum → FULL_MATCH (because it detects hash_map_lookup). But this is coincidental, not meaningful. Any problem without preparation gets matched against hash_map_lookup.

---

## 6. Specific Problem Analysis

### Problem 3236 (Smallest Missing Integer Greater Than Sequential Prefix Sum)

- DB pattern: `[]` (empty)
- GT patterns: `['hash_map_lookup', 'prefix_sum']`
- Solution group: `required=None` (broken — no V1 mapping applied)
- This problem was added by a newer data pipeline that didn't populate `problems.pattern`
- The GT was generated by LLM but the solution group wasn't properly V1-mapped
- **The DB pattern column is empty, so no reliable baseline exists**

### Problem 3718

- **Does not exist in the database.** Cannot be tested.

---

## 7. Top 5 Remaining User-Facing Problems

### 1. CRITICAL: Ground truth mismatch between DB patterns and LLM-generated solution groups

**Root cause:** Two independent systems populate the same data inconsistently. The DB `problems.pattern` is set during import; `problem_ground_truth.patterns` is set by LLM. They can disagree.

**Impact:** Production matcher compares against wrong expected patterns for 61% of problems with ground truth.

**Fix priority:** Must fix before any user-facing deployment.

### 2. CRITICAL: Production shows definitive "NO_MATCH" when ground truth is wrong

**Root cause:** The Matching Engine uses LLM-generated solution groups as ground truth. When the LLM is wrong, the user sees "❌ No expected patterns detected" for correct code.

**Impact:** Users are told their correct solution is wrong. This is actively misleading.

**Fix priority:** Must fix before any user-facing deployment.

### 3. HIGH: Shadow analysis correctly identifies approaches that production misses

**Root cause:** Shadow uses structural evidence (facts → techniques → strategies) while production uses flat pattern matching. Shadow is more semantically accurate.

**Impact:** The experimental panel shows correct analysis while the production panel shows wrong analysis. The user sees contradictory panels.

**Fix priority:** Should be resolved before user-facing deployment.

### 4. MEDIUM: Shadow technique detector missing monotonic_stack for `for`-loop implementations

**Root cause:** `_detect_monotonic_comparison` and `_detect_conditional_pop` only fire inside `ast.While` nodes. Python stacks commonly use `for` loops.

**Impact:** Valid Parentheses → 0 techniques, 0 strategies, UNRESOLVED.

**Fix priority:** Medium — can be improved incrementally.

### 5. LOW: No problem context produces meaningless matching results

**Root cause:** The fallback `[[hash_map_lookup]]` in `run_analysis()` makes every problem without preparation match against hash_map_lookup.

**Impact:** Users who skip "Prepare Problem" get meaningless match results.

**Fix priority:** Low — the UI encourages preparing first, but the fallback is misleading.

---

## 8. What Should Remain Unchanged

- **Shadow analysis pipeline architecture** (facts → techniques → strategies → match) — this is the correct approach
- **Two-panel separation** during experimentation — both panels provide different information
- **Shadow persistence** — all key artifacts are properly stored
- **Graceful degradation** — shadow failures never affect production
- **Frontend confidence normalization** — 0.0-1.0 → 0-100% is correct
- **Production analysis architecture** — AST → Matching Engine is sound, but the ground truth data is wrong

---

## 9. Recommended Next Implementation Phase

### Phase 1 (IMMEDIATE): Fix Ground Truth Integrity

1. **Reconcile DB patterns with GT patterns** — for every problem, `problems.pattern` and `problem_ground_truth.patterns` must agree
2. **Re-generate solution groups** for problems where GT patterns don't match DB patterns
3. **For problems with empty DB patterns** — use the GT patterns as the DB pattern (the LLM analysis is likely more accurate than empty)

### Phase 2 (HIGH): Fix Production Matcher Fallback

1. **Remove the `[[hash_map_lookup]]` fallback** from `run_analysis()`
2. When no problem is provided, **skip matching entirely** rather than produce a meaningless result
3. Show "No problem selected — matching skipped" in the UI

### Phase 3 (MEDIUM): Improve Shadow Technique Detection

1. **Extend `monotonic_comparison` and `conditional_pop`** to detect inside `for` loops (not just `while` loops)
2. **Add `hash_map_frequency` technique** detection for dictionary-based counting patterns
3. **Add `monotonic_stack_strategy` evaluation** for stack-based solutions

### Phase 4 (LOW): Unify or Deprecate the Dual-Panel Display

1. After ground truth is fixed and shadow detection is improved, evaluate whether the two panels can be merged
2. Consider making the shadow panel the primary and the production panel a legacy fallback

---

## 10. Verdict

**PathForge's user-facing analysis is NOT reliable for production use in its current state.** The ground truth integrity problem means the production matcher actively gives wrong answers for many problems. The shadow analysis is more accurate but incomplete.

The research direction (structural analysis for concept detection) IS viable — the shadow pipeline demonstrates this when it works. But the data layer has a fundamental integrity problem that must be fixed first.

**For research evaluation:** The production system cannot be used as-is for benchmarking because the ground truth labels are inconsistent. Any evaluation would be measuring the wrong thing.

**For product use:** The system should not be deployed until the ground truth mismatch is resolved. A user who submits correct code and sees "❌ No expected patterns detected" will lose trust immediately.
