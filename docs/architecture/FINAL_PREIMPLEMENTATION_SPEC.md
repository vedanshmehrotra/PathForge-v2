# FINAL PREIMPLEMENTATION SPECIFICATION

**Status:** Architecture freeze. Ready for implementation review.
**Date:** August 20, 2026
**Basis:** Complete code audit, all prior architecture documents

---

## 1. CURRENT ARCHITECTURE TRUTH

### What the code actually does today:

**ProblemContext** (pathforge/services/problem_resolver.py):
- Fields: `leetcode_id`, `title_slug`, `title`, `difficulty`, `topics`, `description`, `accepted_solution_groups`, `ground_truth_confidence`
- No `evidence_state` field exists
- `accepted_solution_groups` is always a single group (`[group_0]`)

**run_analysis** (pathforge/api/services/analysis.py):
- Takes: `code`, `language`, `accepted_solution_groups`
- Returns: `{ast: ast_output, match_result: match_result}`
- Passes groups to MatchingEngine as `[g["patterns"] for g in accepted_solution_groups]`

**MatchingEngine.match** (src/matching_engine/matching_engine.py):
- Takes: `llm_output` (with `accepted_solution_groups`), `ast_output`
- Returns: `{match_result, matched_groups, unmatched_patterns, confidence_score, reasoning_signals}`
- `matched_groups` is a list of indices of fully-matched groups
- Already supports OR across groups, AND within groups

**run_persistence** (pathforge/services/persistence.py):
- Takes: `connection`, `user_id`, `problem_id`, `problem_difficulty`, `code`, `ast_output`, `match_result`, `groups`
- Does NOT use `match_result["matched_groups"]`
- Uses `groups[0]["patterns"][0]` for `expected_pattern` (BUG)
- Verdict: `"pass"` if `match_result_str in ("FULL_MATCH", "PARTIAL_MATCH")` else `"fail"`
- Calls `update_topic_profile()` unconditionally
- Calls `gap_engine.compute_signals()` unconditionally
- Calls `elo_engine.compute_updates()` unconditionally
- Calls `get_recommendation()` unconditionally

**submissions table** (pathforge/db/schema_pg.sql):
- `verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail', 'error', 'tle'))`
- No `verdict_type` column
- No `detected_patterns_json` column
- No `code_hash` column
- `code_text` stored as-is (not truncated in schema, but `run_persistence` truncates to 1000 chars)

**Two ELO systems:**
1. `user_pattern_elo` (per-pattern) — managed by `EloEngine.compute_updates()`
2. `topic_profiles.elo_rating` (per-topic) — managed by `update_topic_profile()` via `outcome_from_submission()`

**K-factor computation** (pathforge/elo_engine.py `_compute_k`):
```python
def _compute_k(elo, gap_strength, recent_history_length):
    k = DEFAULT_K  # 32
    if gap_strength > 0.5:
        k += K_GAP_BOOST  # +16
    if recent_history_length >= 3:
        k = max(k - K_STABILITY_REDUCTION, K_MIN)  # -8, min 8
    return min(k, K_MAX)  # max 64
```

**CSV provenance** (pathforge/data/pathforge_problems_fixed.csv):
- 300 problems with pattern column
- All patterns are JSON lists (e.g., `["hash_map_lookup"]`)
- Consistent automated format suggests LLM generation
- No metadata about creation process in repository
- `validate_dataset.py` only validates pattern names against taxonomy, not provenance

---

## 2. CONFIRMED INVARIANTS

1. **Low-evidence groups must never produce authoritative PASS/FAIL.** Groups with evidence state `llm_proposed`, `unobserved`, or `conflicted` must produce `analysis_only` behavior. The verdict must NOT be `pass`/`fail` for these groups.

2. **Low-evidence groups must not affect user scoring.** They must not update `user_pattern_elo`, `topic_profiles`, gap signals, or recommendations.

3. **Structural repetition must not be described as algorithmic correctness.** `structurally_observed` means the pattern was detected in multiple submissions. It does NOT mean the pattern is the correct algorithmic approach.

4. **The matched group determines expected_pattern.** `run_persistence()` must use `match_result["matched_groups"][0]` to identify the matched group, then extract `expected_pattern` from that group.

5. **Evidence state is per-group, not per-problem.** Each solution group has its own evidence state. The matched group's evidence state determines downstream authority.

6. **K-factor ceilings are ceilings, not multipliers.** `final_k = min(computed_k, evidence_ceiling)`. This prevents compounding with existing K adjustments.

7. **Cold-start is per-group, not per-problem.** There is no problem-level cold-start. Each group independently determines whether matching against it produces authoritative or analysis-only results.

8. **Submissions must be stored for future clustering.** Full AST output and code hash must be stored per submission.

---

## 3. REMAINING CONTRADICTIONS

### Contradiction 1: `analysis_only` vs DB schema

**Description:** The proposed `analysis_only` verdict violates `CHECK (verdict IN ('pass', 'fail', 'error', 'tle'))`.

**Affected files:** `pathforge/db/schema_pg.sql`, `pathforge/services/persistence.py`

**Resolution:** Add `verdict_type TEXT DEFAULT 'authoritative'` column to submissions table. Keep `verdict` as `pass`/`fail` for all submissions. Use `verdict_type` to gate downstream systems. This avoids modifying the CHECK constraint.

### Contradiction 2: Evidence state not in ProblemContext

**Description:** `ProblemContext` has no field for evidence state or per-group evidence.

**Affected files:** `pathforge/services/problem_resolver.py`

**Resolution:** `ProblemContext` does NOT need a single `evidence_state` field. It already carries `accepted_solution_groups`. Each group should carry its own evidence state. The evidence state is looked up from the matched group during persistence.

### Contradiction 3: CSV provenance unknown

**Description:** `externally_listed` requires provenance verification. The CSV may be LLM-generated.

**Affected files:** `pathforge/data/pathforge_problems_fixed.csv`

**Resolution:** Mark this as an **unresolved dependency**. Until provenance is verified, treat CSV patterns as `llm_proposed` equivalent (K=0). Do not assign `externally_listed` status until provenance is established.

### Contradiction 4: Self-reinforcing promotion loop

**Description:** Wrong patterns promoted to `structurally_observed` can self-reinforce.

**Affected files:** Future clustering logic

**Resolution:** Add external contradiction signal. If CSV lists a different pattern than the structurally_observed pattern, mark the problem as `conflicted`. This breaks the loop. Implement in Phase 3 (clustering).

---

## 4. FINAL DATA MODEL

### Schema changes (submissions table):

```sql
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT DEFAULT 'authoritative';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_patterns_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS code_hash TEXT;
```

### Schema changes (problem_ground_truth table):

```sql
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS solution_groups JSONB;
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'unobserved';
```

### Data structures:

**solution_groups** (JSONB in problem_ground_truth):
```json
[
  {
    "patterns": ["hash_map_lookup"],
    "evidence": "structurally_observed",
    "confidence": {"hash_map_lookup": 0.8}
  },
  {
    "patterns": ["sorting"],
    "evidence": "llm_proposed",
    "confidence": {"sorting": 0.6}
  }
]
```

**accepted_solution_groups** (in ProblemContext):
```python
[
  {
    "id": "group_0",
    "patterns": ["hash_map_lookup"],
    "evidence": "structurally_observed",
    "confidence": {"hash_map_lookup": 0.8}
  },
  {
    "id": "group_1",
    "patterns": ["sorting"],
    "evidence": "llm_proposed",
    "confidence": {"sorting": 0.6}
  }
]
```

**verdict_type** (in submissions table):
- `"authoritative"` — match result is authoritative (evidence is structurally_observed or externally_listed)
- `"analysis_only"` — match result is informational only (evidence is llm_proposed, unobserved, or conflicted)

---

## 5. EXACT EVIDENCE PROPAGATION FLOW

```
1. problem_ground_truth.solution_groups
   -> [{patterns: [...], evidence: "llm_proposed", confidence: {...}}, ...]
       |
2. ProblemContext.accepted_solution_groups
   -> same structure, loaded from DB
       |
3. run_analysis(code, groups)
   -> groups passed to MatchingEngine as [g["patterns"] for g in groups]
   -> MatchingEngine.match() returns:
      {match_result, matched_groups: [0], unmatched_patterns, confidence_score}
       |
4. analyze_endpoint()
   -> receives: result (with match_result), ctx (with accepted_solution_groups)
   -> calls run_persistence(groups=ctx.accepted_solution_groups, match_result=result["match_result"])
       |
5. run_persistence(groups, match_result)
   -> matched_index = match_result["matched_groups"][0]  (NEW: extract matched group)
   -> matched_group = groups[matched_index]  (NEW: use matched group)
   -> expected_pattern = matched_group["patterns"][0]  (FIX: use matched group, not groups[0])
   -> evidence_state = matched_group.get("evidence", "unobserved")  (NEW: extract evidence)
   -> verdict_type = "authoritative" if evidence_state in ("structurally_observed", "externally_listed") else "analysis_only"
   -> verdict = "pass" if match_result_str in ("FULL_MATCH", "PARTIAL_MATCH") else "fail"
   -> INSERT INTO submissions (..., verdict_type, ...)
       |
6. Downstream gating:
   if verdict_type == "analysis_only":
       -> SKIP update_topic_profile()
       -> SKIP gap_engine.compute_signals()
       -> SKIP elo_engine.compute_updates()
       -> SKIP get_recommendation()
   else:
       -> update_topic_profile() with evidence-weighted K ceiling
       -> gap_engine.compute_signals() normally
       -> elo_engine.compute_updates() with evidence K ceiling
       -> get_recommendation() normally
```

---

## 6. FINAL AUTHORITY MATRIX

| Evidence state | verdict | verdict_type | user_pattern_elo | topic_profiles | gap signals | recommendations |
|---------------|---------|-------------|-----------------|---------------|-------------|----------------|
| **structurally_observed** | pass/fail | authoritative | K ceiling: 0.75 * DEFAULT_K | Updated (K ceiling: 0.75) | Active (flagged) | Active (lower priority) |
| **externally_listed** | pass/fail | authoritative | K ceiling: 0.5 * DEFAULT_K | Updated (K ceiling: 0.5) | Active (flagged) | Active (lower priority) |
| **llm_proposed** | pass/fail | **analysis_only** | **SKIPPED** | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** |
| **unobserved** | pass/fail | **analysis_only** | **SKIPPED** | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** |
| **conflicted** | pass/fail | **analysis_only** | **SKIPPED** | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** |

**Note:** `verdict` is always `pass`/`fail` (satisfies DB constraint). `verdict_type` is the gate for downstream systems.

---

## 7. K-FACTOR SEMANTICS

### Existing K computation:

```python
k = DEFAULT_K  # 32
if gap_strength > 0.5:
    k += K_GAP_BOOST  # +16 = 48
if recent_history_length >= 3:
    k = max(k - K_STABILITY_REDUCTION, K_MIN)  # -8, min 8
k = min(k, K_MAX)  # max 64
```

### Evidence ceiling application:

```python
EVIDENCE_CEILINGS = {
    "structurally_observed": 0.75 * DEFAULT_K,  # 24
    "externally_listed": 0.5 * DEFAULT_K,        # 16
    "llm_proposed": 0,
    "unobserved": 0,
    "conflicted": 0,
}

# After existing K computation:
evidence_ceiling = EVIDENCE_CEILINGS.get(evidence_state, DEFAULT_K)
final_k = min(k, evidence_ceiling)
```

### Interaction with both ELO systems:

**user_pattern_elo** (EloEngine):
- `final_k` applied in `compute_updates()` via `_compute_k()` modification
- Evidence ceiling applied as final cap

**topic_profiles** (update_topic_profile):
- Skipped entirely if `verdict_type == "analysis_only"`
- If authoritative, `outcome_from_submission()` uses verdict to compute outcome
- `update_elo()` inside `update_topic_profile()` uses its own K-factor
- Evidence ceiling applied to topic-level ELO as well

---

## 8. MINIMUM REQUIRED CODE CHANGES

### Required changes:

| File | Function/Section | Change |
|------|-----------------|--------|
| `pathforge/db/schema_pg.sql` | submissions table | Add `verdict_type`, `detected_patterns_json`, `code_hash` columns |
| `pathforge/db/schema_pg.sql` | problem_ground_truth table | Add `solution_groups`, `validation_status` columns |
| `pathforge/services/persistence.py` | `run_persistence()` | Extract `matched_groups[0]`, use matched group for `expected_pattern`, derive `evidence_state`, gate all downstream calls |
| `pathforge/services/problem_resolver.py` | `_load_ground_truth()` | Read from `solution_groups` column if present, fall back to flat patterns; attach evidence state to each group |
| `pathforge/services/ground_truth_builder.py` | `_store_ground_truth()` | Write structured `solution_groups` with evidence states |
| `pathforge/elo_engine.py` | `_compute_k()` or `compute_updates()` | Accept `evidence_state` parameter, apply K ceiling |
| `pathforge/db/profile_manager.py` | `update_topic_profile()` | Accept `evidence_state` parameter, skip if analysis_only |

### Optional future improvements:

| File | Change | Priority |
|------|--------|----------|
| `pathforge/llm/openrouter_client.py` | Multi-group prompt | Phase 4 |
| `pathforge/services/submission_clustering.py` | New file for clustering | Phase 3 |
| `pathforge/data/pathforge_problems_fixed.csv` | Provenance documentation | Phase 1 |

---

## 9. DEPENDENCY ORDER

```
Phase 0A: Fix persistence expected_pattern bug
  (no new columns, just fix groups[0] -> matched group)
  Depends on: nothing
  Unlocks: correctness of expected_pattern

Phase 0B: Add verdict_type, detected_patterns_json, code_hash to submissions
  Depends on: nothing
  Unlocks: Phase 1, Phase 2, Phase 3

Phase 0C: Add solution_groups, validation_status to problem_ground_truth
  Depends on: nothing
  Unlocks: Phase 1

Phase 1: Update problem_resolver to read solution_groups
  Depends on: Phase 0C
  Unlocks: Phase 2

Phase 2: Update persistence to gate by evidence state
  Depends on: Phase 0A, Phase 0B, Phase 1
  Unlocks: evidence-gated downstream behavior

Phase 3: Implement clustering
  Depends on: Phase 0B (needs detected_patterns_json, code_hash)
  Unlocks: structurally_observed status

Phase 4: Multi-solution LLM prompt
  Depends on: Phase 1 (needs solution_groups storage)
  Unlocks: multi-group ground truth
```

---

## 10. BLOCKING UNKNOWNS

1. **CSV provenance.** Cannot verify whether CSV patterns are LLM-generated or manually curated. Until resolved, `externally_listed` status should not be assigned. **Impact:** Low — `llm_proposed` is sufficient for initial implementation.

2. **K-factor ceiling calibration.** K=0.75 for `structurally_observed` is an estimate. May need adjustment based on real-world behavior. **Impact:** Low — ceiling can be tuned without architectural changes.

3. **Clustering independence threshold.** The exact code similarity threshold for independence estimation is unknown. **Impact:** Low — can be tuned after Phase 3 implementation.

---

## 11. FINAL VERDICT

**READY WITH BLOCKING UNKNOWN**

The architecture is internally consistent and implementable. The one blocking unknown is CSV provenance, which affects whether `externally_listed` can be used. However, this does not block initial implementation — the system can operate with `llm_proposed` and `structurally_observed` only.

**Recommended action:** Proceed with implementation of Phases 0A-2. Mark CSV provenance as a follow-up investigation. Do not assign `externally_listed` status until provenance is verified.

---

*End of Final Preimplementation Specification*
