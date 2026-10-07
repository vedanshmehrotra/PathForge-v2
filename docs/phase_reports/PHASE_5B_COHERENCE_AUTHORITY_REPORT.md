# PHASE_5B_COHERENCE_AUTHORITY_REPORT.md

**Date:** August 22, 2026
**Status:** Complete
**Depends on:** PATHFORGE_PHASE_5_ARCHITECTURE_PLAN.md, PATHFORGE_PHASE_5A_IMPLEMENTATION_REPORT.md

---

## 1. Strategy Compatibility Metadata

### 1.1 Metadata structure

Each strategy has a compatibility entry with:
- `mutually_exclusive_with`: strategies that CANNOT coexist as required
- `compatible_with`: techniques/concepts that are compatible
- `reason`: why the relationship holds

### 1.2 Defined relationships

| Strategy | Mutually Exclusive With | Reason |
|---|---|---|
| `dfs_backtracking` | `dp_top_down` | Requires state_restoration, excludes cache; DP requires cache, excludes state_restoration |
| `dp_top_down` | `dfs_backtracking` | Symmetric |
| `binary_search` | — | No mutual exclusions (evaluator-level conflicts are warnings) |
| `two_pointers_opposite` | — | No mutual exclusions |
| `sliding_window` | — | No mutual exclusions |
| `bfs_shortest_path` | — | No mutual exclusions |
| `dp_bottom_up` | — | No mutual exclusions |
| `union_find` | — | No mutual exclusions |
| `monotonic_stack_strategy` | — | No mutual exclusions |

### 1.3 Design decision

**Only `dfs_backtracking ↔ dp_top_down` is marked mutually exclusive.**

Rationale:
- These strategies have **structural contradictions** in their definitions:
  - DFS backtracking: requires `state_restoration`, excludes `cache_lookup`/`cache_write`
  - DP top-down: requires `cache_lookup`/`cache_write`, excludes `state_restoration`
- A solution group requiring both would **never be satisfied** by any submission
- This is a definition-level contradiction, not just an evaluator constraint

**Other pairs (binary_search ↔ two_pointers, etc.) are NOT marked mutually exclusive** because:
- Their conflicts are evaluator-level absence constraints, not definition contradictions
- The group validator warns about unsatisfiable combinations but does not reject them
- The original group is preserved rather than silently rewritten

---

## 2. Group Coherence Validation

### 2.1 Validation outcomes

| Outcome | Meaning | Action |
|---|---|---|
| `accepted` | Group passes all checks | Group is stored as-is |
| `warning` | Group has non-fatal issues (unsatisfiable combinations) | Group is stored with warnings |
| `rejected` | Group has fatal errors (invalid IDs, mutual exclusion, conflicts) | Group is stored but marked rejected |

### 2.2 What is checked

| Check | Severity | Example |
|---|---|---|
| Invalid concept ID | Rejected | `required: ["nonexistent"]` |
| Required/excluded conflict | Rejected | `required: ["X"], excluded: ["X"]` |
| Optional/excluded conflict | Rejected | `optional: ["X"], excluded: ["X"]` |
| Threshold out of bounds | Rejected | `threshold: 1.5` |
| Invalid authority tier | Rejected | `authority_tier: "invalid"` |
| Mutually exclusive strategies | Rejected | `required: ["dfs_backtracking", "dp_top_down"]` |
| Unsatisfiable combinations | Warning | `required: ["binary_search", "two_pointers_opposite"]` |

### 2.3 Validation examples

**Valid:**
- `binary_search` alone → accepted
- `binary_search` + `union_find` → accepted
- `dfs_backtracking` with `dp_top_down` in excluded → accepted

**Rejected:**
- `dfs_backtracking` + `dp_top_down` as required → rejected (mutually exclusive)
- `binary_search` as both required and excluded → rejected (conflict)

**Warning:**
- `binary_search` + `two_pointers_opposite` as required → warning (unsatisfiable)
- `binary_search` + `sliding_window` as required → warning (unsatisfiable)

---

## 3. Authority Upgrade Metadata

### 3.1 Record structure

```json
{
  "group_id": "group_0",
  "problem_id": 42,
  "previous_tier": "llm_proposed",
  "new_tier": "structurally_observed",
  "evidence_sources": ["submission_cluster", "submission_independence"],
  "timestamp": "2026-08-22T12:00:00",
  "actor": "system",
  "reason": "5 independent submissions match"
}
```

### 3.2 Valid transitions

| From | To | Allowed |
|---|---|---|
| `llm_proposed` | `structurally_observed` | ✅ |
| `llm_proposed` | `externally_listed` | ✅ |
| `llm_proposed` | `editorial` | ✅ |
| `bootstrap` | `structurally_observed` | ✅ |
| `bootstrap` | `externally_listed` | ✅ |
| `bootstrap` | `editorial` | ✅ |
| `structurally_observed` | `editorial` | ✅ |
| `structurally_observed` | `reviewed` | ✅ |
| `externally_listed` | `editorial` | ✅ |
| `externally_listed` | `reviewed` | ✅ |
| `editorial` | `reviewed` | ✅ |
| Any downward transition | — | ❌ Rejected |

### 3.3 Evidence source types (for Phase 6)

| Source | Description |
|---|---|
| `submission_cluster` | Multiple independent submissions match |
| `submission_independence` | Submissions use different variable names/syntax |
| `submission_agreement` | Independent implementations agree |
| `contradiction_absence` | No contradictions in recent submissions |
| `external_source` | External validation (editorial solution) |
| `human_review` | Human expert reviewed |
| `structural_observation` | Structural analysis confirms pattern |

---

## 4. Authority Safety Behavior

### 4.1 Rules preserved

| Rule | Status |
|---|---|
| `bootstrap` / `llm_proposed` can CONFIRM in shadow | ✅ Preserved |
| `bootstrap` / `llm_proposed` cannot produce CONTRADICTED | ✅ Preserved |
| Authoritative tiers may CONFIRM | ✅ Preserved |
| Authoritative tiers may CONTRADICT | ✅ Preserved |
| UNRESOLVED remains non-punitive | ✅ Preserved |

### 4.2 Automatic promotion verification

**No automatic upgrade logic exists in the codebase.**

The authority module provides:
- `create_upgrade_record()` — creates and validates a record
- `validate_upgrade_record()` — validates a record
- `serialize_upgrade_history()` / `deserialize_upgrade_history()` — persistence

It does NOT provide:
- Any function that takes a submission and returns an upgrade
- Any automatic promotion logic
- Any submission-triggered tier changes

---

## 5. Automatic-Promotion Verification

| Check | Result |
|---|---|
| No `auto_upgrade` function exists | ✅ VERIFIED |
| No `promote` function exists | ✅ VERIFIED |
| No submission-match → tier-up logic | ✅ VERIFIED |
| Upgrade records require explicit external evidence | ✅ VERIFIED |
| Evidence sources must be non-empty | ✅ VERIFIED |
| Transitions are validated | ✅ VERIFIED |

---

## 6. Full Regression Results

### 6.1 Test counts

| Suite | Passed | Failed |
|---|---|---|
| src/ast_detection/tests/ | 482 | 0 |
| pathforge/ast_analysis/shadow/tests/ | 336 | 0 |
| pathforge/services/ | 0 | 0 (no tests) |
| **Total** | **818** | **0** |

### 6.2 Phase 5B specific tests

| Test class | Tests | Passed |
|---|---|---|
| TestStrategyCompatibility | 5 | 5 |
| TestMutualExclusion | 4 | 4 |
| TestUnsatisfiableCombinations | 3 | 3 |
| TestGroupCoherenceValidation | 9 | 9 |
| TestAuthorityUpgradeMetadata | 12 | 12 |
| TestPhase5BCrossPatternRegression | 4 | 4 |
| **Total** | **37** | **37** |

### 6.3 Regression on existing tests

| Test | Status |
|---|---|
| Phase 4B readiness: dfs_backtracking + dp_top_down | ✅ Updated to expect rejection |
| All existing shadow tests | ✅ PASS |
| All existing persistence tests | ✅ PASS |
| All existing enrichment tests | ✅ PASS |
| All existing integration tests | ✅ PASS |

---

## 7. Known Limitations

### 7.1 Limited mutual-exclusion pairs

Only `dfs_backtracking ↔ dp_top_down` is marked mutually exclusive. Other potentially conflicting pairs (e.g., `binary_search ↔ two_pointers_opposite`) are only warned about, not rejected.

**Justification:** The conflicts are evaluator-level absence constraints, not definition contradictions. A group requiring both would never be satisfied, but the group is structurally valid.

**Phase 6 consideration:** If more pairs are identified as genuinely contradictory, they can be added to `STRATEGY_COMPATIBILITY`.

### 7.2 No schema persistence for upgrade records

The authority upgrade metadata is in-memory only. Schema changes for persisting upgrade history are deferred to Phase 6 when automatic upgrades may be implemented.

### 7.3 Deprecation warning

`datetime.utcnow()` is deprecated in Python 3.12+. The authority module uses it for backward compatibility. Should be updated to `datetime.now(datetime.UTC)` in a future cleanup.

---

## 8. Files Changed

| File | Changes |
|---|---|
| `pathforge/ast_analysis/shadow/coherence.py` | NEW — Strategy compatibility metadata, mutual exclusion, unsatisfiable detection |
| `pathforge/ast_analysis/shadow/authority.py` | NEW — Authority upgrade record infrastructure |
| `pathforge/services/ground_truth_builder.py` | Extended `_validate_group()` with coherence checks, added `warnings` to return |
| `pathforge/ast_analysis/shadow/tests/test_phase5b.py` | NEW — 37 Phase 5B tests |
| `pathforge/ast_analysis/shadow/tests/test_phase4b_readiness.py` | Updated dfs_backtracking + dp_top_down test to expect rejection |

---

## 9. Phase 5B Verdict

### **APPROVED**

**Justification:**
1. ✅ Strategy compatibility metadata implemented for all 9 strategies
2. ✅ Group coherence validation detects mutual exclusion (rejected) and unsatisfiable combinations (warning)
3. ✅ Authority upgrade metadata infrastructure implemented
4. ✅ No automatic promotion logic exists
5. ✅ Authority safety rules preserved
6. ✅ 818 tests pass, 0 failures
7. ✅ Production behavior unchanged
8. ✅ Shadow-only isolation maintained

**Next steps:**
- Phase 5C: Evaluation and tuning
- Phase 5D: Canary preparation
