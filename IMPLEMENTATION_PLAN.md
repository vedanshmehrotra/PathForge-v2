# IMPLEMENTATION PLAN

**Status:** Pending approval. Do not implement until reviewed.
**Date:** August 20, 2026
**Basis:** Architecture Final Reconciliation

---

## PHASE 0: CRITICAL BUG FIXES (no architecture changes)

### Phase 0A: Fix persistence expected_pattern bug

**Objective:** `expected_pattern` must use the matched group, not the first group.

**Files affected:**
- `pathforge/services/persistence.py` (lines 30-36)

**Current code:**
```python
expected_pattern = ""
if groups:
    for g in groups:
        patterns = g.get("patterns", [])
        if patterns:
            expected_pattern = patterns[0]
            break
```

**Required change:** Use `match_result["matched_groups"]` to identify the matched group index, then extract the first pattern from that group.

**Database migrations:** None.

**Tests to generate:**
- Unit test: verify `expected_pattern` matches the correct group when multiple groups exist
- Unit test: verify existing single-group behavior is preserved
- Integration test: verify full persistence flow with multi-group input

**Success metrics:** `expected_pattern` correctly reflects the matched group in all cases.

**Rollback criteria:** Any existing test failure.

**Changes user-facing behavior:** No (single-group behavior unchanged; multi-group behavior corrected).

---

### Phase 0B: Store full AST output per submission

**Objective:** Enable future clustering by storing complete pattern data.

**Files affected:**
- `pathforge/services/persistence.py` (submission INSERT)
- `pathforge/db/schema_pg.sql` (new column)

**Required changes:**
1. Add `detected_patterns_json JSONB` column to `submissions` table
2. Add `match_result_json JSONB` column to `submissions` table
3. Store full `detected_patterns` list in `detected_patterns_json`
4. Store full `match_result` dict in `match_result_json`

**Database migrations:**
```sql
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_patterns_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS match_result_json JSONB;
```

**Tests to generate:**
- Migration test: verify columns are added correctly
- Unit test: verify full AST output is stored
- Unit test: verify existing tests still pass (backward compatible)

**Success metrics:** Full AST output stored for every new submission.

**Rollback criteria:** Migration failure or existing test failure.

**Changes user-facing behavior:** No (additional storage only).

---

### Phase 0C: Store code hash per submission

**Objective:** Enable copy detection for independence estimation.

**Files affected:**
- `pathforge/services/persistence.py` (submission INSERT)
- `pathforge/db/schema_pg.sql` (new column)

**Required changes:**
1. Add `code_hash TEXT` column to `submissions` table
2. Compute SHA-256 of normalized code (strip whitespace, normalize identifiers)
3. Store hash in `code_hash`

**Database migrations:**
```sql
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS code_hash TEXT;
```

**Tests to generate:**
- Unit test: verify hash computation for identical code
- Unit test: verify different hash for different code
- Unit test: verify hash is computed and stored

**Success metrics:** Code hash stored for every new submission.

**Rollback criteria:** Migration failure.

**Changes user-facing behavior:** No.

---

## PHASE 1: TWO-LAYER EVIDENCE MODEL

### Phase 1A: Add evidence state columns to problem_ground_truth

**Objective:** Track evidence state per pattern.

**Files affected:**
- `pathforge/db/schema_pg.sql` (new columns)
- `pathforge/services/problem_resolver.py` (`_load_ground_truth`)
- `pathforge/services/ground_truth_builder.py` (`_store_ground_truth`)

**Required changes:**
1. Add `solution_groups JSONB` column (stores structured groups with evidence states)
2. Add `validation_status TEXT DEFAULT 'unobserved'` column
3. Modify `_store_ground_truth()` to write `solution_groups` and `validation_status`
4. Modify `_load_ground_truth()` to read from `solution_groups` if present, fall back to flat `patterns`

**Database migrations:**
```sql
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS solution_groups JSONB;
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'unobserved';
```

**Tests to generate:**
- Migration test: verify columns are added
- Unit test: verify `_load_ground_truth` reads from new columns
- Unit test: verify fallback to flat patterns for existing data
- Unit test: verify `_store_ground_truth` writes structured groups

**Success metrics:** Existing tests pass; new columns populated for new ground truth.

**Rollback criteria:** Migration failure or existing test failure.

**Changes user-facing behavior:** No (backward compatible).

---

### Phase 1B: Implement evidence state tracking in ground_truth_builder

**Objective:** Assign initial evidence state to LLM-generated patterns.

**Files affected:**
- `pathforge/services/ground_truth_builder.py`

**Required changes:**
1. After `_normalize_patterns()`, wrap output in structured format:
   ```python
   solution_groups = [
       {
           "patterns": canonical,
           "evidence": "llm_proposed",
           "confidence": filtered_confidence
       }
   ]
   ```
2. Set `validation_status = "unobserved"` (default)
3. Store in new `solution_groups` column

**Tests to generate:**
- Unit test: verify LLM output is wrapped in structured format
- Unit test: verify evidence state is set to "llm_proposed"

**Success metrics:** New ground truth stored with evidence states.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** No (matching behavior unchanged initially).

---

### Phase 1C: CSV cross-reference validation

**Objective:** Promote LLM patterns to `externally_listed` when CSV confirms.

**Files affected:**
- `pathforge/services/ground_truth_builder.py` (new validation step)
- `pathforge/data/pathforge_problems_fixed.csv` (read-only)

**Required changes:**
1. After LLM generation, check if each pattern appears in the CSV `pattern` column for this problem
2. If pattern is in CSV → promote to `externally_listed`
3. Store evidence state per pattern in `solution_groups`

**Tests to generate:**
- Unit test: verify CSV cross-reference works
- Unit test: verify pattern promoted to `externally_listed` when in CSV
- Unit test: verify pattern stays `llm_proposed` when not in CSV

**Success metrics:** Patterns confirmed by CSV are promoted.

**Rollback criteria:** CSV parsing failure.

**Changes user-facing behavior:** No (matching behavior unchanged initially).

---

## PHASE 2: AUTHORITY GATING

### Phase 2A: Modify matching to accept evidence state

**Objective:** Matching engine receives evidence state and uses it for authority decisions.

**Files affected:**
- `pathforge/api/services/analysis.py` (pass evidence state to matching)
- `src/matching_engine/matching_engine.py` (accept evidence state parameter)

**Required changes:**
1. Add `evidence_state` parameter to `MatchingEngine.match()`
2. Return evidence state in `MatchResult` output
3. No change to matching logic itself (matching always runs)

**Tests to generate:**
- Unit test: verify evidence state is passed through
- Unit test: verify existing matching behavior preserved

**Success metrics:** Evidence state available in match result.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** No (additional data returned, not used yet).

---

### Phase 2B: Implement authority-gated ELO

**Objective:** ELO updates gated by evidence state.

**Files affected:**
- `pathforge/services/persistence.py` (pass evidence state to ELO)
- `pathforge/elo_engine.py` (accept authority parameter)

**Required changes:**
1. Determine effective authority from evidence states of matched patterns
2. Pass authority to `EloEngine.compute_updates()`
3. ELO engine uses authority to set K-factor:
   - `llm_proposed` → K=0 (no update)
   - `externally_listed` → K=0.5
   - `structurally_observed` → K=1.0

**Tests to generate:**
- Unit test: verify K=0 for llm_proposed
- Unit test: verify K=0.5 for externally_listed
- Unit test: verify K=1.0 for structurally_observed
- Integration test: verify full ELO flow with different authority levels

**Success metrics:** ELO updates correctly gated by authority.

**Rollback criteria:** Any ELO test failure.

**Changes user-facing behavior:** YES — ELO updates suppressed for low-evidence patterns.

---

### Phase 2C: Implement authority-gated gap signals

**Objective:** Gap signals suppressed for low-evidence patterns.

**Files affected:**
- `pathforge/services/persistence.py` (pass evidence state to gap engine)
- `pathforge/gap_signal_engine.py` (accept authority parameter)

**Required changes:**
1. Determine effective authority from evidence states
2. If authority is `llm_proposed`: suppress gap signal generation
3. If authority is `externally_listed`: generate gap signals but flag as "externally sourced"
4. If authority is `structurally_observed`: generate gap signals normally

**Tests to generate:**
- Unit test: verify gap signals suppressed for llm_proposed
- Unit test: verify gap signals flagged for externally_listed
- Unit test: verify gap signals normal for structurally_observed

**Success metrics:** Gap signals correctly gated by authority.

**Rollback criteria:** Any gap signal test failure.

**Changes user-facing behavior:** YES — gap signals suppressed for low-evidence patterns.

---

### Phase 2D: Implement authority-gated recommendations

**Objective:** Recommendations suppressed for low-evidence patterns.

**Files affected:**
- `pathforge/services/persistence.py` (pass evidence state to recommendation)
- `pathforge/api/services/recommend_service.py` (accept authority parameter)

**Required changes:**
1. Determine effective authority from evidence states
2. If authority is `llm_proposed`: suppress recommendation generation
3. If authority is `externally_listed`: generate recommendations with lower priority
4. If authority is `structurally_observed`: generate recommendations normally

**Tests to generate:**
- Unit test: verify recommendations suppressed for llm_proposed
- Unit test: verify recommendations lower priority for externally_listed
- Unit test: verify recommendations normal for structurally_observed

**Success metrics:** Recommendations correctly gated by authority.

**Rollback criteria:** Any recommendation test failure.

**Changes user-facing behavior:** YES — recommendations suppressed for low-evidence patterns.

---

## PHASE 3: COLD-START BEHAVIOR

### Phase 3A: Implement cold-start detection

**Objective:** Detect problems with insufficient evidence.

**Files affected:**
- `pathforge/services/problem_resolver.py` (new function)

**Required changes:**
1. Add `is_cold_start(problem_id)` function
2. Check if any pattern has `structurally_observed` or `externally_listed` status
3. Return True if no pattern meets threshold

**Tests to generate:**
- Unit test: verify cold-start detection for new problems
- Unit test: verify cold-start ends when evidence exists

**Success metrics:** Cold-start correctly detected.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** No.

---

### Phase 3B: Implement cold-start suppression

**Objective:** Suppress ELO/gaps/recommendations during cold-start.

**Files affected:**
- `pathforge/services/persistence.py` (cold-start check)

**Required changes:**
1. Before calling ELO/gap/recommendation engines, check cold-start status
2. If cold-start: skip ELO update, skip gap signals, skip recommendations
3. Return cold-start status in response

**Tests to generate:**
- Unit test: verify ELO suppressed during cold-start
- Unit test: verify gap signals suppressed during cold-start
- Unit test: verify recommendations suppressed during cold-start
- Integration test: verify full flow during cold-start

**Success metrics:** Cold-start suppression works correctly.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** YES — no scoring during cold-start.

---

### Phase 3C: Implement cold-start user display

**Objective:** Show appropriate message during cold-start.

**Files affected:**
- `pathforge/api/routes/analyze.py` (response)
- Frontend (display message)

**Required changes:**
1. Add `cold_start: bool` to `AnalyzeResponse`
2. Frontend shows "Analysis in progress — patterns not yet validated" when `cold_start` is True

**Tests to generate:**
- Unit test: verify cold_start flag in response
- Frontend test: verify message displayed

**Success metrics:** User sees appropriate message during cold-start.

**Rollback criteria:** Frontend build failure.

**Changes user-facing behavior:** YES — new message during cold-start.

---

## PHASE 4: MULTI-SOLUTION SUPPORT

### Phase 4A: Update LLM prompt for multi-group output

**Objective:** LLM generates candidate solution groups instead of flat list.

**Files affected:**
- `pathforge/llm/openrouter_client.py` (prompt modification)

**Required changes:**
1. New prompt template requesting explicit solution groups
2. Post-processing to validate group structure
3. Fallback to flat-list prompt if multi-group fails

**Tests to generate:**
- Unit test: verify new prompt format
- Unit test: verify post-processing validates structure
- Unit test: verify fallback to flat-list
- Integration test: verify LLM output is parsed correctly

**Success metrics:** LLM produces structured groups.

**Rollback criteria:** LLM output parsing failure.

**Changes user-facing behavior:** No (offline only).

---

### Phase 4B: Update ground_truth_builder for multi-group storage

**Objective:** Store multi-group LLM output with evidence states.

**Files affected:**
- `pathforge/services/ground_truth_builder.py`

**Required changes:**
1. Parse multi-group LLM output
2. Apply taxonomy validation per group
3. Apply CSV cross-reference per pattern
4. Store structured groups with evidence states

**Tests to generate:**
- Unit test: verify multi-group parsing
- Unit test: verify per-group validation
- Unit test: verify evidence state assignment

**Success metrics:** Multi-group ground truth stored correctly.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** No (matching behavior unchanged until Phase 5).

---

## PHASE 5: CLUSTERING

### Phase 5A: Implement submission clustering

**Objective:** Identify repeated structural patterns across submissions.

**Files affected:**
- New file: `pathforge/services/submission_clustering.py`
- `pathforge/services/persistence.py` (batch trigger)

**Required changes:**
1. Batch process: for each problem, load all submissions with full AST output
2. Cluster by primary pattern + code similarity
3. Identify patterns with ≥2 independent submissions
4. Promote to `structurally_observed`

**Tests to generate:**
- Unit test: verify clustering logic
- Unit test: verify independence estimation
- Unit test: verify promotion rules
- Integration test: verify end-to-end clustering

**Success metrics:** Clustering correctly identifies repeated patterns.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** No (batch process only).

---

### Phase 5B: Integrate clustering with evidence model

**Objective:** Clustering results update evidence states.

**Files affected:**
- `pathforge/services/submission_clustering.py`
- `pathforge/services/problem_resolver.py` (evidence state lookup)

**Required changes:**
1. After clustering, update `problem_ground_truth.solution_groups` with new evidence states
2. Problem resolver reads updated evidence states
3. Matching engine receives updated authority levels

**Tests to generate:**
- Unit test: verify evidence state updates from clustering
- Unit test: verify problem resolver reads updated states
- Integration test: verify full flow from clustering to matching

**Success metrics:** Clustering results affect matching authority.

**Rollback criteria:** Any test failure.

**Changes user-facing behavior:** YES — matching authority increases as evidence accumulates.

---

## PHASE 6: MULTI-SOLUTION MATCHING

### Phase 6A: Enable multi-group matching

**Objective:** MatchingEngine uses multiple solution groups.

**Files affected:**
- `pathforge/api/services/analysis.py` (pass multi-group to matching)
- `pathforge/services/problem_resolver.py` (load multi-group GT)

**Required changes:**
1. `_load_ground_truth()` returns multiple groups from `solution_groups` column
2. `run_analysis()` passes all groups to MatchingEngine
3. MatchingEngine already supports this — verify it works

**Tests to generate:**
- Unit test: verify multi-group matching
- Unit test: verify OR semantics across groups
- Unit test: verify AND semantics within groups
- Integration test: verify full flow with multi-group GT

**Success metrics:** Multi-group matching works correctly.

**Rollback criteria:** Any matching test failure.

**Changes user-facing behavior:** YES — users matching alternative approaches get FULL_MATCH.

---

## DEPENDENCY GRAPH

```
Phase 0A (persistence bug fix)
Phase 0B (store full AST) ─────────┐
Phase 0C (store code hash) ────────┤
                                    ▼
Phase 1A (evidence columns) ──────→ Phase 1B (evidence tracking)
                                    │
Phase 1C (CSV cross-reference) ────┤
                                    ▼
Phase 2A (matching evidence) ─────→ Phase 2B (authority ELO)
                                    │
Phase 2C (authority gaps) ─────────┤
Phase 2D (authority recommendations)┤
                                    ▼
Phase 3A (cold-start detection) ──→ Phase 3B (cold-start suppression)
                                    │
Phase 3C (cold-start display) ─────┤
                                    ▼
Phase 4A (multi-group prompt) ────→ Phase 4B (multi-group storage)
                                    │
                                    ▼
Phase 5A (clustering) ────────────→ Phase 5B (clustering integration)
                                    │
                                    ▼
Phase 6A (multi-group matching) ───┘
```

## PRIORITY ORDER

1. **Phase 0A** (persistence bug) — CRITICAL, no architecture change
2. **Phase 0B** (store full AST) — Required for clustering
3. **Phase 0C** (store code hash) — Required for independence
4. **Phase 1A** (evidence columns) — Required for evidence model
5. **Phase 1B** (evidence tracking) — Core evidence model
6. **Phase 1C** (CSV cross-reference) — Easy win
7. **Phase 2A** (matching evidence) — Prerequisite for authority gating
8. **Phase 2B** (authority ELO) — Critical safety gate
9. **Phase 2C** (authority gaps) — Safety gate
10. **Phase 2D** (authority recommendations) — Safety gate
11. **Phase 3A** (cold-start detection) — Safety gate
12. **Phase 3B** (cold-start suppression) — Safety gate
13. **Phase 3C** (cold-start display) — User experience
14. **Phase 4A** (multi-group prompt) — Feature
15. **Phase 4B** (multi-group storage) — Feature
16. **Phase 5A** (clustering) — Evidence accumulation
17. **Phase 5B** (clustering integration) — Evidence accumulation
18. **Phase 6A** (multi-group matching) — Feature

---

*End of Implementation Plan*
