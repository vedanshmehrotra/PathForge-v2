# Root Cause Report: Vocabulary Mismatch in Analysis Pipeline

## A. Execution Path

```
POST /analyze
├─ resolve_problem() → _load_ground_truth()
│   ├─ Reads solution_groups from DB (V1 format: required/optional/excluded)
│   ├─ BUG: Sets "patterns" field = V1 concepts (required) instead of legacy pattern IDs
│   └─ BUG: Skips groups with empty "required" entirely
│
├─ run_analysis(code, groups)
│   ├─ AST detector → detected_patterns = [legacy pattern IDs]
│   ├─ Production MatchingEngine.match() → flat pattern-ID set intersection
│   │   └─ group_patterns (V1 concepts) ∩ ast_patterns (legacy IDs) = ∅ → NO_MATCH
│   └─ Returns match_result
│
└─ run_shadow_analysis(code, solution_groups=groups)
    ├─ extract_structural_facts(tree) → facts
    ├─ detect_techniques(facts) → technique_evidence
    │   └─ carry_propagation detected ✅, sequential_accumulation detected ✅
    ├─ evaluate_strategies(techniques, facts) → strategy_evidence = []
    │   └─ No strategy evaluator for technique-only concepts (by design)
    ├─ evaluate_solution_groups(groups, techniques, strategies, facts)
    │   ├─ If groups=None/empty → UNRESOLVED, authority_tier="unknown"
    │   └─ If groups exist → checks techniques AND strategies in required
    └─ Returns shadow result
```

## B. Exact Files and Functions Responsible

| File | Function | Bug |
|------|----------|-----|
| `pathforge/services/problem_resolver.py` | `_load_ground_truth()` (line ~214) | Overwrites `patterns` field with V1 concepts; skips empty-required groups |
| `pathforge/services/ground_truth_builder.py` | `PATTERN_TO_V1_MAPPING` (line ~202) | `linked_list_reversal` has `required: []` — group always unsatisfiable |

## C. Why strategy_evidence Is Empty

`strategy_evidence` is empty because there are **no strategy evaluators** for technique-only concepts like `carry_propagation` or `sequential_accumulation`. The 9 strategy evaluators only handle:

- `two_pointers_opposite`
- `binary_search`
- `sliding_window`
- `dfs_backtracking`
- `dp_top_down`
- `dp_bottom_up`
- `bfs_shortest_path`
- `union_find`
- `monotonic_stack_strategy`

**This is NOT the root cause of UNRESOLVED.** The shadow matcher's `_evaluate_single_group()` checks BOTH techniques AND strategies:

```python
for req in required:
    if req in detected_techniques:  # ← This works!
        te = detected_techniques[req]
        if te.presence_confidence >= 0.5:
            required_met += 1
    elif req in detected_strategies:
        se = detected_strategies[req]
        if se.confidence >= 0.5:
            required_met += 1
```

The real cause is that solution groups aren't reaching the shadow matcher (Bug 2) or have wrong patterns for the production matcher (Bug 1).

## D. This Is Two Shared Bugs, Not Multiple Independent Issues

**Bug 1 — Vocabulary mismatch in `_load_ground_truth()`:**
```python
# BEFORE (broken):
required = g.get("required", g.get("patterns", []))
groups.append({
    "patterns": required,  # ← V1 concepts like "carry_propagation"
})
# Production matcher gets V1 concepts → no match with legacy AST output

# AFTER (fixed):
legacy_patterns = g.get("patterns") or required
groups.append({
    "patterns": legacy_patterns,  # ← Original legacy pattern IDs
    "required": required,         # ← V1 concepts for shadow matcher
})
```

**Bug 2 — Empty-required groups skipped:**
```python
# BEFORE (broken):
required = g.get("required", g.get("patterns", []))
if not required:
    continue  # ← linked_list_reversal (required=[]) SKIPPED entirely

# AFTER (fixed):
# Removed the skip guard — groups are always included
```

**Bug 3 — V1 mapping had empty required:**
```python
# BEFORE (broken):
"linked_list_reversal": {"required": [], "optional": ["carry_propagation"]}

# AFTER (fixed):
"linked_list_reversal": {"required": ["linked_list_traversal"], ...}
```

## E. Minimum Safe Fix

### Files Changed

| File | Change |
|------|--------|
| `pathforge/services/problem_resolver.py` | `_load_ground_truth()`: Preserve original `patterns` from stored group; remove empty-required skip guard |
| `pathforge/services/ground_truth_builder.py` | `PATTERN_TO_V1_MAPPING`: Map `linked_list_reversal` → `linked_list_traversal`, `monotonic_stack` → `monotonic_stack_maintenance`, `monotonic_deque` → `monotonic_stack_maintenance` |
| `pathforge/ast_analysis/shadow/tests/test_phase4a_enrichment.py` | Updated 2 tests to reflect new mapping |
| `pathforge/ast_analysis/shadow/tests/test_regression_vocabulary_mismatch.py` | 17 new regression tests |

### Before/After Behavior

**Before fix (LC 2 — Add Two Numbers):**
```
Shadow: techniques=[carry_propagation], strategies=[], outcome=UNRESOLVED, authority=unknown
Production: match_result=NO_MATCH, unmatched_patterns=["carry_propagation"]
```

**After fix (LC 2 — Add Two Numbers, with carry_propagation group):**
```
Shadow: techniques=[carry_propagation], strategies=[], outcome=CONFIRMED, authority=llm_proposed
Production: match_result=NO_MATCH (correct — AST doesn't detect linked_list_reversal)
```

**After fix (LC 2 — Add Two Numbers, with linked_list_traversal group):**
```
Shadow: techniques=[carry_propagation], strategies=[], outcome=UNRESOLVED (correct — wrong group)
Production: match_result=NO_MATCH (correct — AST doesn't detect linked_list_reversal)
```

### Test Results

| Suite | Passed | Failed |
|-------|--------|--------|
| Production (AST) | 482 | 0 |
| Matching Engine | 50 | 0 |
| Shadow tests | 336 | 0 |
| New regression tests | 17 | 0 |
| **Total** | **885** | **0** |

## F. What This Fix Does NOT Change

- ✅ AST detector behavior unchanged
- ✅ Shadow analysis remains observational/shadow-only
- ✅ Production verdict, ELO, gaps, recommendations unchanged
- ✅ No new techniques or strategies added
- ✅ No variable-name dependence introduced
- ✅ UNRESOLVED remains non-punitive
- ✅ No false contradictions introduced
