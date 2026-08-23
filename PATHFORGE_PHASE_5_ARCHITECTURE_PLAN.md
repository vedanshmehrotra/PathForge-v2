# PATHFORGE_PHASE_5_ARCHITECTURE_PLAN.md

**Date:** August 22, 2026
**Status:** Planning (NOT implementation)
**Depends on:** PATHFORGE_ANALYSIS_ARCHITECTURE_V1.md, PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md, PHASE_4B_PROMOTION_READINESS_AUDIT.md

---

## 1. Current V1 Bottlenecks

| Bottleneck | Impact | Severity |
|---|---|---|
| 45% legacy pattern coverage | 62.5% unresolved rate | HIGH |
| No semantic coherence validation | Invalid groups accepted | MEDIUM |
| Fixed sliding windows not detected | Common pattern missed | MEDIUM |
| No submission-based group validation | Groups unverified | HIGH |
| No authority upgrade mechanism | LLM-proposed groups stay non-authoritative | HIGH |
| No iterative DFS detection | Common pattern missed | LOW |

**Key insight:** The system is safe (zero false confirmations/contradictions) but too often unresolved. We need to increase coverage WITHOUT sacrificing safety.

---

## 2. Ranked Coverage Priorities

Ranked by: expected frequency × educational value × implementability × low false-positive risk.

| Rank | Missing Concept | Frequency | Educational Value | Implementability | False-Positive Risk | Coverage Impact |
|---|---|---|---|---|---|---|
| 1 | **Linked-list manipulation** (not just reversal) | HIGH | HIGH | MEDIUM | LOW | +8-10% |
| 2 | **Fixed sliding window** | HIGH | MEDIUM | HIGH | LOW | +3-5% |
| 3 | **Monotonic stack** | MEDIUM | HIGH | MEDIUM | MEDIUM | +5-7% |
| 4 | **Heap/priority queue** | MEDIUM | MEDIUM | LOW | LOW | +3-5% |
| 5 | **Greedy (local choice)** | HIGH | MEDIUM | LOW | HIGH | +5-8% |
| 6 | **Iterative DFS** | MEDIUM | LOW | MEDIUM | LOW | +2-3% |
| 7 | **Topological sort** | LOW | MEDIUM | MEDIUM | LOW | +1-2% |
| 8 | **Frequency counting** | HIGH | LOW | HIGH | MEDIUM | +3-5% |

**Recommended for Phase 5 implementation:** Ranks 1-3 (linked-list, fixed window, monotonic stack)

**Deferred:** Ranks 4-8 (heap, greedy, iterative DFS, topological sort, frequency counting)

**Rationale:**
- Linked-list manipulation appears in ~10% of problems and has clear structural signals (`.next`/`.prev` traversal + pointer rewiring)
- Fixed sliding window is a common variant that can be detected with minimal new facts
- Monotonic stack has a distinct structural signature (stack + comparison + conditional pop)

---

## 3. Taxonomy Decisions

### 3.1 Linked-list manipulation

**Classification:** New technique `linked_list_traversal`

**Defense:**
- Composed from: `linked_structure_traversal` + `pointer_rewiring` (new fact) + `conditional_advance`
- Recurs across: reversal, cycle detection, merge, partition
- Not a complete algorithm label (reversal, cycle, merge are distinct strategies)
- Single fact (`linked_structure_traversal`) is insufficient

**New structural facts needed:**
- `pointer_rewiring` — assignment to `.next`/`.prev` attribute (e.g., `node.next = prev`)
- `multiple_pointer_traversal` — two or more pointers traverse linked structure simultaneously

**New technique:**
- `linked_list_traversal` — requires `linked_structure_traversal` + (`pointer_rewiring` OR `multiple_pointer_traversal`)

**Strategies that use it:**
- `linked_list_reversal` (future strategy)
- `cycle_detection` (future strategy)
- `merge_sorted_lists` (future strategy)

### 3.2 Fixed sliding window

**Classification:** New technique `fixed_window_maintenance`

**Defense:**
- Composed from: `loop_shape` (for-loop) + `window_size_constant` (new fact) + `indexed_access` with offset
- Recurs across: maximum subarray, average of subarrays, anagrams
- Not a strategy label (the strategy is `sliding_window`)
- The existing `sliding_window` strategy can be extended to accept this technique

**New structural facts needed:**
- `window_size_constant` — a loop bound or index offset that remains constant across iterations (e.g., `i + k` where `k` is constant)

**New technique:**
- `fixed_window_maintenance` — requires `for_loop_iteration` + `window_size_constant` + `indexed_access`

**Strategy update:**
- `sliding_window` strategy: add `fixed_window_maintenance` as alternative technique to `loop_state_tracking`

### 3.3 Monotonic stack

**Classification:** New technique `monotonic_stack_maintenance`

**Defense:**
- Composed from: `stack_operation` + `monotonic_comparison` + `conditional_pop`
- Recurs across: next greater element, histogram, daily temperatures
- Not a strategy label (the strategy is `monotonic_stack_strategy`)
- Single fact (`stack_operation`) is insufficient

**New structural facts needed:**
- `stack_operation` — `append()`/`pop()` on a list used as stack
- `monotonic_comparison` — comparison in while-loop condition that determines stack pops (e.g., `while stack and nums[stack[-1]] < nums[i]`)
- `conditional_pop` — pop operation inside a conditional branch

**New technique:**
- `monotonic_stack_maintenance` — requires `stack_operation` + `monotonic_comparison` + `conditional_pop`

**New strategy:**
- `monotonic_stack_strategy` — requires `monotonic_stack_maintenance` technique

---

## 4. Submission Evidence Model

### 4.1 What submissions can contribute

| Signal | What it proves | What it cannot prove | Promotion value |
|---|---|---|---|
| **Repeated structural observation** | Many independent implementations use the same structural facts | That the approach is "correct" (could be a common mistake) | MEDIUM — strengthens confidence |
| **Code independence** | Different variable names, different syntax, same structure | That the approach is optimal or even correct | HIGH — strong evidence of a real pattern |
| **Agreement across submissions** | Multiple users converge on same strategy | That the ground truth is complete | HIGH — validates group coverage |
| **Contradictions** | Some submissions don't match any group | Which group is wrong (could be incomplete ground truth) | LOW — more likely ground truth gap |
| **External/editorial evidence** | Official solution matches a group | N/A — this is human validation | HIGHEST — direct confirmation |

### 4.2 No circularity rule

```
Submission → match → evidence collection → group PROMOTION is FORBIDDEN
```

**Allowed:**
- Submission → match → evidence collection → stored as observational data
- Multiple submissions → cluster analysis → identifies coverage gaps
- External review → authority tier upgrade

**Forbidden:**
- Submission matches group → group becomes "confirmed"
- High match rate → group becomes authoritative
- User behavior → automatic ground truth promotion

### 4.3 Minimum submission evidence for authority upgrade

A solution group can be upgraded from `llm_proposed` to `structurally_observed` when:
1. **Minimum 5 independent submissions** match the group (different users, different code)
2. **No contradictions** in the last 20 submissions for this problem
3. **Structural independence** — submissions use different variable names, different syntax
4. **No obvious common mistake pattern** — not all submissions make the same error

This requires a submission clustering analysis that is OUT OF SCOPE for Phase 5.

---

## 5. Authority Upgrade Model

### 5.1 Current authority tiers

| Tier | Source | Can CONFIRM? | Can CONTRADICT? |
|---|---|---|---|
| `bootstrap` | Initial generation | ✅ | ❌ → UNRESOLVED |
| `llm_proposed` | LLM output | ✅ | ❌ → UNRESOLVED |
| `structurally_observed` | Submission analysis | ✅ | ✅ |
| `externally_listed` | External source | ✅ | ✅ |
| `editorial` | Human review | ✅ | ✅ |

### 5.2 Proposed upgrade path

```
llm_proposed → structurally_observed (requires submission evidence)
structurally_observed → editorial (requires human review)
editorial → reviewed (requires expert verification)
```

### 5.3 Minimum metadata for upgrade

Each upgrade must record:
- Previous tier
- New tier
- Evidence source (submission IDs, review date, etc.)
- Upgrade timestamp
- Reviewer (human or system)

### 5.4 Phase 5 scope

**Implement:** Upgrade metadata schema and API
**Do NOT implement:** Automatic submission-based upgrade (requires clustering analysis)
**Do NOT implement:** Human review workflow (requires UI changes)

---

## 6. Semantic Coherence Model

### 6.1 Known contradictory pairs

| Pair A | Pair B | Reason |
|---|---|---|
| `dfs_backtracking` | `dp_top_down` | One excludes memoization, other requires it |
| `binary_search` | `sliding_window` | Rarely coexist (different loop structures) |
| `two_pointers_opposite` | `binary_search` | Opposite convergence patterns |
| `bfs_shortest_path` | `recursive_branching` | BFS uses queue, not recursion |

### 6.2 Compatibility metadata

Add to strategy definitions:

```json
{
  "strategy_id": "dfs_backtracking",
  "mutually_exclusive_with": ["dp_top_down"],
  "compatible_with": ["recursive_branching", "loop_state_tracking"]
}
```

### 6.3 Validation rule

When validating a solution group:
1. Check that no two required strategies are mutually exclusive
2. Check that required strategies are compatible with each other
3. Log warnings for unusual combinations (but don't reject)

### 6.4 Phase 5 scope

**Implement:** Compatibility metadata in strategy definitions
**Implement:** Mutual-exclusion check in group validator
**Do NOT implement:** Full constraint language or complex coherence rules

---

## 7. Fixed Sliding-Window Decision

### 7.1 Can the current architecture handle fixed windows?

**YES** — with minimal additions.

**Current limitation:**
- `loop_state_tracking` requires `conditional_index_update` (if/else updating left boundary)
- Fixed windows don't have conditional updates — the window slides every iteration

**Solution:**
- Add new technique `fixed_window_maintenance` (Section 3.2)
- Extend `sliding_window` strategy to accept `fixed_window_maintenance` OR `loop_state_tracking`
- No weakening of current precision — fixed windows are structurally distinct

### 7.2 Implementation complexity

**LOW** — only needs:
- New fact: `window_size_constant` (detect constant offset in loop bound)
- New technique: `fixed_window_maintenance` (for-loop + constant window + indexed access)
- Strategy update: accept alternative technique

### 7.3 False-positive risk

**LOW** — fixed windows have a clear structural signature:
- For-loop with range
- Constant window size (e.g., `i + k`)
- No conditional boundary updates

**Hard negative:** `for i in range(n): result += arr[i]` (no window, just iteration) — doesn't fire because no constant offset.

---

## 8. Phase-5 Evaluation Corpus

### 8.1 Positive implementations

| Category | Code Pattern | Expected Strategy |
|---|---|---|
| Binary search | Standard + overflow-safe + rotated | `binary_search` |
| Two pointers | Palindrome + container + 3Sum | `two_pointers_opposite` |
| Sliding window | Fixed window + variable window | `sliding_window` |
| DFS backtracking | Subsets + permutations + N-queens | `dfs_backtracking` |
| DP top-down | Fibonacci memo + climbing stairs | `dp_top_down` |
| DP bottom-up | House robber + coin change + LCS | `dp_bottom_up` |
| BFS | Graph shortest path + level order | `bfs_shortest_path` |
| Union-find | Classic + inline + with rank | `union_find` |
| Linked list | Reversal + cycle detection + merge | `linked_list_traversal` (technique) |
| Monotonic stack | Next greater element + histogram | `monotonic_stack_strategy` |
| Fixed sliding window | Max sum subarray of size k | `sliding_window` |
| Greedy | Interval scheduling + task assignment | UNRESOLVED (no V1 strategy) |

### 8.2 Hard negatives

| Category | Code Pattern | Expected Result |
|---|---|---|
| Binary search vs two-pointers | Standard binary search | `binary_search`, NOT `two_pointers_opposite` |
| Sliding window vs two-pointers | Variable window | `sliding_window`, NOT `two_pointers_opposite` |
| DFS vs DP | Backtracking without memo | `dfs_backtracking`, NOT `dp_top_down` |
| DP vs prefix sum | Simple prefix array | UNRESOLVED (or `dp_bottom_up` if structured) |
| BFS vs DFS | Queue-based traversal without level tracking | UNRESOLVED |
| Union-find vs parent array | Generic parent traversal | UNRESOLVED |
| Monotonic stack vs simple stack | Stack without monotonic comparison | UNRESOLVED |
| Fixed window vs iteration | Simple for-loop sum | UNRESOLVED |

### 8.3 Renamed variants

For each positive case, test with:
- Renamed variables (e.g., `left` → `start`, `right` → `end`)
- Equivalent syntax (e.g., `i += 1` ↔ `i = i + 1`)
- Equivalent midpoint (e.g., `(lo+hi)//2` ↔ `lo + (hi-lo)//2`)
- For ↔ while where structurally reasonable

### 8.4 Real-world style code

Include 5-10 examples from actual LeetCode solutions (not textbook examples):
- Multiple variables
- Helper functions
- Edge-case handling
- Unusual but valid structures

---

## 9. Success Metrics

### 9.1 Primary metrics (must improve over V1)

| Metric | V1 Baseline | Phase 5 Target | Priority |
|---|---|---|---|
| False authoritative confirmation | 0% | 0% | CRITICAL |
| False contradiction | 0% | 0% | CRITICAL |
| Unresolved rate | 62.5% | <50% | HIGH |
| Confirmation rate | 37.5% | >50% | HIGH |
| Precision of confirmation | 100% | >95% | HIGH |

### 9.2 Secondary metrics (nice to have)

| Metric | V1 Baseline | Phase 5 Target | Priority |
|---|---|---|---|
| Legacy pattern coverage | 45% | >60% | MEDIUM |
| Cross-pattern false positives | 0% | <2% | MEDIUM |
| Variable-renamed false negatives | Unknown | <10% | LOW |

### 9.3 Evaluation methodology

- Run Phase 5 corpus (Section 8) against the updated system
- Compare metrics to V1 baseline
- **Block Phase 5 completion if:**
  - False authoritative confirmation > 0%
  - False contradiction > 0%
  - Precision drops below 90%

---

## 10. Promotion Gates

### 10.1 Gate 1: Safety (must pass)

- [ ] Zero false authoritative confirmations in evaluation corpus
- [ ] Zero false contradictions in evaluation corpus
- [ ] All existing 551 tests pass
- [ ] All shadow tests pass
- [ ] No production behavior changed

### 10.2 Gate 2: Coverage (must pass)

- [ ] Unresolved rate < 50% on evaluation corpus
- [ ] Confirmation rate > 50% on evaluation corpus
- [ ] Legacy pattern coverage > 60%

### 10.3 Gate 3: Robustness (must pass)

- [ ] Variable-renamed variants: < 10% false negatives
- [ ] Equivalent syntax variants: < 5% false negatives
- [ ] Cross-pattern false positives: < 2%

### 10.4 Gate 4: Infrastructure (must pass)

- [ ] Semantic coherence validation implemented
- [ ] Authority upgrade metadata schema implemented
- [ ] Re-derivation test passes (persist → reload → re-derive)

### 10.5 Gate 5: Limited canary (final gate)

- [ ] All Gates 1-4 pass
- [ ] Manual review of 20+ real-world examples
- [ ] No critical issues found in shadow mode
- [ ] Documentation complete for canary rollout

---

## 11. Exact Implementation Phases

### Phase 5A: Structural facts and techniques (Week 1)

**Goal:** Add linked-list, fixed-window, and monotonic-stack techniques

1. Add new structural facts:
   - `pointer_rewiring`
   - `multiple_pointer_traversal`
   - `window_size_constant`
   - `stack_operation`
   - `monotonic_comparison`
   - `conditional_pop`

2. Add new techniques:
   - `linked_list_traversal`
   - `fixed_window_maintenance`
   - `monotonic_stack_maintenance`

3. Update strategies:
   - `sliding_window` — accept `fixed_window_maintenance` as alternative

4. Add strategy:
   - `monotonic_stack_strategy`

5. Write tests for each new technique/strategy

6. Run full regression (551 + shadow tests)

### Phase 5B: Semantic coherence and authority (Week 2)

**Goal:** Add validation and upgrade infrastructure

1. Add compatibility metadata to strategy definitions
2. Implement mutual-exclusion check in group validator
3. Add authority upgrade metadata schema
4. Add upgrade API endpoint (metadata only, no automatic upgrades)
5. Write tests for coherence validation and authority metadata

### Phase 5C: Evaluation and tuning (Week 3)

**Goal:** Validate against comprehensive corpus

1. Build Phase 5 evaluation corpus (Section 8)
2. Run evaluation and collect metrics
3. Tune technique/strategy thresholds if needed (minimal changes)
4. Document false positives and false negatives
5. Fix critical issues if any

### Phase 5D: Canary preparation (Week 4)

**Goal:** Prepare for limited canary rollout

1. Verify all promotion gates pass
2. Write canary rollout documentation
3. Create monitoring dashboards for shadow metrics
4. Prepare rollback plan if issues arise
5. Final review and sign-off

---

## 12. Explicitly Deferred Work

| Item | Reason | Target Phase |
|---|---|---|
| Heap/priority queue technique | Low frequency, complex structural signals | Phase 6 |
| Greedy strategy class | Multiple subtypes, hard to unify | Phase 6 |
| Iterative DFS technique | Overlaps with BFS detection, low priority | Phase 6 |
| Topological sort strategy | Low frequency, uses BFS-like traversal | Phase 6 |
| Frequency counting technique | Generic data-structure behavior, not reusable | Phase 6 |
| Submission-based group validation | Requires clustering analysis, out of scope | Phase 6 |
| Automatic authority upgrades | Requires human review workflow | Phase 6 |
| Full constraint language for coherence | Over-engineering for V1 | Phase 6+ |
| Runtime LLM verification | Explicitly deferred in architecture | Never |
| Production ELO redesign | Explicitly deferred in architecture | Phase 7+ |

---

## Final Verdict

### **READY TO IMPLEMENT**

**Rationale:**
1. **Clear bottlenecks identified** — 62.5% unresolved rate is the primary issue
2. **Targeted solutions exist** — linked-list, fixed-window, monotonic-stack techniques are implementable with current architecture
3. **Safety preserved** — zero false confirmations/contradictions maintained
4. **Scope controlled** — only 3 new techniques, 1 new strategy, minimal fact additions
5. **Measurable gates** — clear success criteria before production promotion
6. **Minimal risk** — shadow-only mode means no production impact

**Key risk:** If new techniques introduce false positives, we can remove them without affecting production. The shadow-only guarantee is the safety net.

**Recommended next step:** Begin Phase 5A implementation (structural facts and techniques).
