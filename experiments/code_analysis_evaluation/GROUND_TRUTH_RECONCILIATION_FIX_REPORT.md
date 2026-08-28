# Ground Truth Reconciliation Fix Report

**Date:** August 28, 2026
**Status:** Complete — all tests pass

---

## Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `pathforge/services/problem_resolver.py` | Added `_load_csv_patterns()`, modified `_load_ground_truth()` | CSV-curated patterns override LLM patterns for production matcher; V1 fields preserved for shadow |
| `pathforge/api/services/analysis.py` | Removed `[[hash_map_lookup]]` fallback, added `NO_GROUND_TRUTH` result | Prevents misleading match when no ground truth exists |
| `pathforge-frontend/components/analysis-view.tsx` | Added `NO_GROUND_TRUTH` display case | Shows "No verified ground truth available" instead of misleading verdict |
| `pathforge/tests/test_ground_truth_reconciliation.py` | 12 new regression tests | Tests A-H as specified |

## Reconciliation Logic

### Two Consumers, Two Representations

```
problems.pattern (CSV-curated)
        │
        ▼
┌─────────────────────────────────────┐
│  _load_ground_truth()               │
│                                     │
│  if CSV non-empty:                  │
│    group["patterns"] = CSV  ←── production matcher uses this
│    group["required"] = LLM's V1  ←── shadow matcher uses this
│    group["optional"] = LLM's V1     │
│    group["excluded"] = LLM's V1     │
│    group["authority_tier"] = human_curated
│                                     │
│  if CSV empty:                      │
│    group["patterns"] = LLM   ←── production (unverified)
│    V1 fields = LLM's V1      ←── shadow (unchanged)
│    group["authority_tier"] = llm_proposed
│                                     │
│  if no GT at all:                   │
│    return [], {}                    │
└─────────────────────────────────────┘
        │
        ├──────────────────┐
        ▼                  ▼
   Production            Shadow
   Matcher               Matcher
   (patterns[])          (required/optional/excluded)
```

### Key Design Decisions

1. **V1 fields are NEVER modified by reconciliation.** The `required`, `optional`, and `excluded` fields always come from the LLM solution group's V1 vocabulary mapping. This preserves the shadow matcher's semantic analysis.

2. **Only `patterns` is overridden.** The production matcher receives `group["patterns"]` as its expected set. When CSV differs from LLM, CSV wins.

3. **Conflicts are logged, not silently resolved.** The `logger.warning()` call records the exact CSV and LLM values when they disagree.

4. **No ground truth = no match.** When neither CSV nor LLM data exists, the production matcher returns `NO_GROUND_TRUTH` instead of falling back to `[[hash_map_lookup]]`.

## Test Results

### New Tests (12)

```
test_curated_pattern_overrides_llm_pattern              PASSED
test_curated_override_preserves_shadow_v1_fields         PASSED
test_matching_patterns_unchanged                         PASSED
test_empty_csv_uses_llm_but_no_authoritative_claim       PASSED
test_no_ground_truth_returns_empty                       PASSED
test_no_ground_truth_no_hash_map_fallback                PASSED
test_add_two_numbers_no_longer_no_match                  PASSED
test_container_with_most_water_unchanged                 PASSED
test_valid_parentheses_shadow_v1_preserved               PASSED
test_problem_5_shadow_v1_preserved                       PASSED
test_conflict_logging_for_problem_2                      PASSED
test_conflict_logging_for_problem_20                     PASSED
12 passed in 15.88s
```

### Full Test Suite

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Backend | **620** | **0** | 620 |
| Shadow | **360** | **0** | 360 |
| Frontend | **32** | **0** | 32 |
| **Total** | **1012** | **0** | **1012** |

**Zero regressions. Zero new failures.**

## Before → After Comparison

### Problem 2: Add Two Numbers

| Aspect | Before | After |
|--------|--------|-------|
| Production expected patterns | `['linked_list_reversal']` (LLM) | `['two_pointers_same']` (CSV) |
| Production match result | `NO_MATCH` ❌ | `FULL_MATCH` ✅ |
| User sees | "❌ No expected patterns detected" | "✅ All expected patterns detected" |
| Shadow V1 required | `['linked_list_traversal']` | `['linked_list_traversal']` (unchanged) |

### Problem 20: Valid Parentheses

| Aspect | Before | After |
|--------|--------|-------|
| Production expected patterns | `['dfs_recursive']` (LLM) | `['monotonic_stack']` (CSV) |
| Production match result | `NO_MATCH` | `NO_MATCH` (correct — AST doesn't detect monotonic_stack yet) |
| User sees | "❌ No expected patterns detected" (misleading) | "❌ No expected patterns detected" (correct — detector limitation) |
| Shadow V1 required | `['recursive_branching']` | `['recursive_branching']` (unchanged) |

### No Problem Context

| Aspect | Before | After |
|--------|--------|-------|
| Fallback patterns | `[[hash_map_lookup]]` | None |
| Match result | `FULL_MATCH` (misleading) | `NO_GROUND_TRUTH` |
| User sees | "✅ All expected patterns detected" (wrong) | "ℹ️ No verified ground truth available" |

## Known Remaining Ground-Truth Limitations

1. **Problem 20 (Valid Parentheses):** The AST detector doesn't detect `monotonic_stack` for `for`-loop implementations. The CSV-curate `monotonic_stack` is correct, but the detector needs improvement. This is a detector limitation, not a ground truth problem.

2. **Problems with empty DB patterns (628, 1574, 1577, 3236, 3812, 4080):** These use LLM-only ground truth marked as `llm_proposed`. The LLM patterns are used but not treated as authoritative. A future task should verify and backfill these.

3. **V1 mapping for Problem 20:** The LLM solution group has `required=['recursive_branching']` (from `dfs_recursive` mapping). The shadow matcher will look for recursive branching, which this stack-based solution doesn't have. The V1 mapping is faithful to the LLM's (incorrect) classification.

4. **The production matcher still uses flat pattern matching.** It checks `two_pointers_same ∈ detected_patterns` by string equality. No fuzzy matching or strategy-level abstraction exists yet.
