# Implementation Audit Report: Phases 0A through 2

## Verdict: APPROVED WITH 2 REQUIRED FIXES

---

## 1. Files Changed

| File | Changes |
|------|---------|
| `pathforge/services/persistence.py` | Fixed matched-group bug, added evidence state derivation, added verdict_type/code_hash/detected_patterns_json, authority gating |
| `pathforge/services/problem_resolver.py` | Updated `_load_ground_truth()` to read solution_groups with per-group evidence, backward-compatible fallback |
| `pathforge/services/ground_truth_builder.py` | Updated `_store_ground_truth()` to write structured solution_groups |
| `pathforge/elo_engine.py` | Added evidence K ceilings, applied as min-cap |
| `pathforge/db/schema_pg.sql` | Added 5 new columns (3 submissions, 2 problem_ground_truth) |
| `pathforge/tests/test_evidence_architecture.py` | 17 new tests for evidence architecture |

---

## 2. Confirmed Integration Behavior (CORRECT)

### 2.1 Matched Group Extraction
- **Group 1 matches** → `expected_pattern` = group 1's pattern, NOT group 0's ✓
- **Group 0 matches** → correct ✓
- **NO_MATCH** → fallback to group 0's evidence → analysis_only for llm_proposed ✓
- **Out-of-range index** → falls back to group 0 safely ✓
- **Missing evidence field** → defaults to "unobserved" → analysis_only ✓
- **groups=None** → analysis_only ✓
- **groups=[]** → analysis_only ✓
- **Malformed matched_groups** → safe (isinstance checks) ✓

### 2.2 Mixed Evidence Groups
- `group_0 = llm_proposed, group_1 = structurally_observed`
- Group 1 matches → `authoritative`, K ceiling 24 ✓
- Group 0 matches → `analysis_only`, K=0 ✓
- **This is the most critical integration path and it works correctly.**

### 2.3 Legacy Backward Compatibility
- Flat patterns column with NULL solution_groups → converts to single group with evidence="unobserved" ✓
- Empty solution_groups `[]` → falls through to legacy path ✓
- Per-group evidence preserved when solution_groups is populated ✓

### 2.4 Authority Gating
- `analysis_only` → topic_profiles: skipped ✓
- `analysis_only` → gap signals: skipped ✓
- `analysis_only` → ELO: skipped (entire block) ✓
- `analysis_only` → recommendations: skipped ✓
- `analysis_only` → streak: still updated ✓
- `authoritative` → all downstream systems execute ✓

### 2.5 K-Factor Ceiling
- `structurally_observed` → `min(computed_k, 24)` ✓
- `llm_proposed` → 0 (skipped entirely) ✓
- No ceiling → `min(computed_k, DEFAULT_K)` = no capping ✓

### 2.6 Code Hash
- Deterministic for identical full code ✓
- Different for different code ✓
- Handles empty code ✓

### 2.7 Legacy Pipeline
- `submission_handler.py` and `submission_persistence.py` exist but are NOT registered in FastAPI app
- NOT an active production bypass ✓

---

## 3. Bugs Found

### BUG 1 — CRITICAL: `topic_profiles` ELO not subject to evidence ceiling

**File:** `pathforge/services/persistence.py` lines 145-156 and `pathforge/db/profile_manager.py` line 70

**Description:** When evidence is `structurally_observed`, the spec requires BOTH ELO systems to be capped at 0.75×DEFAULT_K. The `user_pattern_elo` system (via `EloEngine.compute_updates()`) correctly applies the ceiling. However, `topic_profiles` ELO (via `update_topic_profile()`) runs with FULL impact because `update_elo()` has no evidence ceiling parameter.

**Impact:** `structurally_observed` evidence gets a 25% reduction on `user_pattern_elo` but 100% impact on `topic_profiles`. This violates the two-layer architecture's intent that structural evidence should not be treated as algorithmically authoritative.

**Fix required:** Either:
- (A) Pass `evidence_ceiling` to `update_topic_profile()` and scale the ELO delta, OR
- (B) Scale the `difficulty` or `verdict` parameters to reduce impact, OR
- (C) Accept that `topic_profiles` is gated only at the pipeline level (skip vs run) and document this limitation.

**Recommended:** Option (A) — add `evidence_ceiling` parameter to `update_topic_profile()`. This is a minimal change.

**Severity: MEDIUM** — Does not corrupt data for `analysis_only` (those are skipped entirely). Only affects `structurally_observed` where topic_profiles runs at full impact instead of 0.75×.

---

### BUG 2 — MEDIUM: Unknown evidence state gets DEFAULT_K ceiling

**File:** `pathforge/elo_engine.py` line 120

**Description:**
```python
evidence_ceiling = EVIDENCE_K_CEILINGS.get(evidence_state, DEFAULT_K)
```
If `evidence_state` is an unknown string (not in the enum), it gets `DEFAULT_K=32` as ceiling, meaning no capping at all. A safer default would be `0` — unknown states should not have scoring authority.

**Impact:** If a bug or data corruption introduces an unexpected evidence state, ELO would run at full authority instead of being suppressed.

**Fix required:** Change the default from `DEFAULT_K` to `0`:
```python
evidence_ceiling = EVIDENCE_K_CEILINGS.get(evidence_state, 0)
```

**Severity: LOW** — Currently unreachable because evidence states are derived from `_AUTHORITATIVE_STATES` check, but this is a defense-in-depth issue.

---

### BUG 3 — HIGH: Schema migration not auto-applied

**File:** `pathforge/db/db.py` line 118 (`init_db()`)

**Description:** `init_db()` only checks if tables exist. It does NOT run the `ALTER TABLE` statements from `schema_pg.sql`. The new columns (`verdict_type`, `detected_patterns_json`, `code_hash`, `solution_groups`, `validation_status`) will NOT exist in the database until manually applied.

If deployed without running the ALTER TABLE statements:
- The INSERT in `run_persistence()` will crash with "column verdict_type does not exist"
- The SELECT in `_load_ground_truth()` will crash with "column solution_groups does not exist"
- The entire /analyze endpoint becomes non-functional

**Impact:** Deployment will fail if schema migration is not run first.

**Fix required:** Either:
- (A) Add auto-migration to `init_db()` that runs `schema_pg.sql`, OR
- (B) Create a standalone migration script and document deployment steps, OR
- (C) Add a try/except around new column queries with fallback to legacy behavior.

**Recommended:** Option (A) — `init_db()` should execute `schema_pg.sql` (which uses `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` for idempotency).

**Severity: HIGH** — Deployment blocker.

---

### BUG 4 — LOW: Legacy pipeline bypass paths exist

**Files:**
- `pathforge/submission_handler.py` — calls `update_topic_profile()` without evidence gating
- `pathforge/services/submission_persistence.py` — runs full pipeline without evidence gating
- `pathforge/routes/submissions.py` — Flask route using legacy pipeline

**Description:** These bypass paths exist but are NOT registered in the FastAPI app. They cannot be triggered by the current production code path.

**Impact:** None currently. Maintenance risk if someone adds a new route using these paths.

**Severity: LOW** — Not active in production.

---

### BUG 5 — COSMETIC: canonical_patterns flattens all groups

**File:** `pathforge/api/routes/analyze.py` lines 73-78

**Description:** The `canonical_patterns` list in `ProblemInfo` flattens ALL solution groups into one list. The frontend cannot distinguish which patterns belong to which group.

**Impact:** Frontend display only. Does not affect scoring, matching, or persistence.

**Severity: COSMETIC**

---

## 4. Architectural Inconsistencies Found

### 4.1 Evidence-Authority Gap for topic_profiles
The architecture says "Apply ceilings to BOTH independent scoring systems" but `topic_profiles` only gets gated at the pipeline level (skip vs run), not at the K-factor level within its own ELO update.

### 4.2 Two ELO Systems Have Different K Semantics
- `user_pattern_elo` (via EloEngine): K is computed dynamically and then capped by evidence ceiling
- `topic_profiles` (via update_elo): K is hardcoded internally (uses difficulty-based K calculation) and has no evidence ceiling parameter

These are fundamentally different ELO implementations that cannot share a ceiling mechanism without modification to at least one of them.

### 4.3 Dead Code Accumulation
`submission_persistence.py` and `submission_handler.py` contain persistence logic that duplicates `run_persistence()` but without evidence gating. They should be deprecated or removed.

---

## 5. Untested Edge Cases

### 5.1 Multiple matched groups
The matching engine can return `matched_groups = [0, 1]` (both groups fully matched). The current code uses only `matched_groups[0]` and ignores the rest. This is functionally correct (it picks the first matched group) but does not leverage the fact that multiple groups matched.

### 5.2 Partial match with mixed evidence
If `match_result = "PARTIAL_MATCH"` and the partially-matched group has `llm_proposed` evidence, the verdict is "pass" (PARTIAL_MATCH counts as pass) with `analysis_only` verdict_type. This is correct per spec.

### 5.3 Evidence state transitions
The implementation does not yet support evidence state promotion (e.g., `llm_proposed` → `structurally_observed` via clustering). This is expected — it's a future phase.

### 5.4 Concurrent submissions
Two concurrent submissions for the same problem could both attempt to read/write the same ground truth row. PostgreSQL transactions handle this correctly, but the evidence state derivation could be affected by timing. Low risk.

---

## 6. Test Results

### New evidence architecture tests
- **17/17 passed** ✓

### Existing AST detector tests
- **482/482 passed** ✓ (zero regressions)

### Existing matching engine tests
- **50/50 passed** ✓ (zero regressions)

### Existing ELO engine tests
- **26/28 passed** ✓ (2 pre-existing failures: DB connection issues)

### Existing ground truth builder tests
- **6/6 passed** ✓ (zero regressions)

### Existing pathforge tests
- **48/64 passed** ✓ (16 pre-existing failures: DB connection issues in test_pipeline.py and test_diversity.py)

### Summary
- **Introduced regressions: 0**
- **Pre-existing failures: 18** (all DB connection issues in test infrastructure)
- **New tests introduced: 17** (all passing)

---

## 7. Evidence Propagation Trace

```
problem_ground_truth.solution_groups
    ↓ (per-group evidence stored as JSONB)
_load_ground_truth()
    ↓ (per-group dicts with evidence field)
ProblemContext.accepted_solution_groups
    ↓ (groups with evidence passed to analysis)
run_analysis() → stripped to [g["patterns"]] for MatchingEngine
    ↓ (MatchingEngine returns matched_groups = [0] or [1] etc.)
run_persistence() receives:
    - groups (full dicts with evidence)
    - match_result["matched_groups"] (indices)
    ↓
idx = matched_groups[0]
matched_group_evidence = groups[idx]["evidence"]
    ↓
verdict_type = "authoritative" if evidence in _AUTHORITATIVE_STATES else "analysis_only"
    ↓
is_authoritative → gates entire downstream pipeline
    ↓
EloEngine.compute_updates(evidence_state=matched_group_evidence)
    ↓
evidence_ceiling = EVIDENCE_K_CEILINGS.get(evidence_state, DEFAULT_K)
k = min(computed_k, evidence_ceiling)
```

---

## 8. K-Factor Behavior for Both ELO Systems

### user_pattern_elo (EloEngine)
- `structurally_observed`: K capped at 24 (75% of DEFAULT_K=32)
- `externally_listed`: K capped at 16 (50% of DEFAULT_K)
- `llm_proposed`: K=0 (entire block skipped)
- Unknown: K=32 (DEFAULT_K, no capping) — **BUG 2**

### topic_profiles (update_topic_profile)
- `authoritative`: Full ELO impact (no ceiling applied) — **BUG 1**
- `analysis_only`: Skipped entirely ✓

---

## 9. Required Fixes (Ordered by Priority)

### Fix 1 — Schema auto-migration (HIGH)
Add `schema_pg.sql` execution to `init_db()`. The ALTER TABLE statements use `ADD COLUMN IF NOT EXISTS` so they are safe to run repeatedly.

### Fix 2 — topic_profiles evidence ceiling (MEDIUM)
Add `evidence_ceiling` parameter to `update_topic_profile()` and scale the ELO update accordingly.

### Fix 3 — Unknown evidence default (LOW)
Change `EVIDENCE_K_CEILINGS.get(evidence_state, DEFAULT_K)` to `EVIDENCE_K_CEILINGS.get(evidence_state, 0)`.

---

## 10. Deviations from FINAL_PREIMPLEMENTATION_SPEC.md

| Spec Requirement | Implementation Status | Deviation |
|---|---|---|
| Evidence state per group | ✅ Implemented | None |
| Matched group determines expected_pattern | ✅ Implemented | None |
| Analysis_only gates all downstream | ✅ Implemented | None |
| K ceiling on BOTH ELO systems | ⚠️ Partial | topic_profiles not capped (Bug 1) |
| Evidence K is ceiling, not multiplier | ✅ Implemented | None |
| Legacy backward compat | ✅ Implemented | None |
| Schema migration | ⚠️ Manual | Not auto-applied (Bug 3) |
| Code hash from full code | ✅ Implemented | None |
| Detected patterns JSON stored | ✅ Implemented | None |
| verdict_type separate from verdict | ✅ Implemented | None |

---

## 11. Blocking Unknowns

1. **Production database state**: The ALTER TABLE statements in `schema_pg.sql` must be applied before deployment. This is a deployment requirement, not a code bug.

2. **CSV provenance**: `externally_listed` evidence state is not yet assigned anywhere. This is expected — it requires CSV provenance verification which is a future phase.

3. **Clustering**: Submission clustering for evidence promotion is a future phase. Not blocking.

---

## 12. Recommendation

**APPROVED WITH FIXES**

The implementation is architecturally sound and functionally correct for the primary code path (`analyze.py` → `run_persistence()`). The matched-group extraction, evidence propagation, and authority gating all work as specified.

**Before deployment, fix:**
1. Schema auto-migration (Bug 3) — prevents deployment crash
2. topic_profiles evidence ceiling (Bug 1) — architectural inconsistency
3. Unknown evidence default (Bug 2) — defense-in-depth

**Can be deferred:**
- Legacy pipeline cleanup (Bug 4) — not active
- canonical_patterns display (Bug 5) — cosmetic
