# ARCHITECTURE PREIMPLEMENTATION AUDIT

**Status:** Final audit. No code changes.
**Date:** August 20, 2026
**Basis:** FINAL_ARCHITECTURE_VERDICT.md, all prior documents, code audit

---

## VERDICT: APPROVE WITH CHANGES

The architecture is sound in principle but contains **5 contradictions that must be resolved** and **3 missing mechanisms** that must be designed before implementation.

---

## A. CRITICAL CONTRADICTIONS

### Contradiction 1: Evidence state granularity mismatch

**The document defines:** `ProblemContext.evidence_state` (single value per problem)

**The document also says:** "verdict uses MINIMUM evidence of matched group" (per-group)

**The contradiction:** If a problem has Group A (structurally_observed) and Group B (llm_proposed), what is `ProblemContext.evidence_state`?

- If it's the MIN (llm_proposed), then `ProblemContext.evidence_state` is always pessimistic and the per-group derivation is redundant
- If it's the MAX (structurally_observed), then it misrepresents the evidence for Group B
- If it's per-group, then `ProblemContext.evidence_state` is the wrong abstraction

**The actual code path:** `run_persistence()` receives `groups` (list of solution groups) but currently does NOT receive evidence state. The document proposes adding `evidence_state` to `ProblemContext` and passing it to `run_persistence()`. But the verdict depends on the MATCHED GROUP's evidence, not the problem-level evidence.

**The correction:** `ProblemContext` should carry `solution_groups` with per-group evidence states. `run_persistence()` should receive the matched group index (from `match_result["matched_groups"]`) and use that group's evidence state, not a problem-level aggregate.

### Contradiction 2: `analysis_only` verdict violates DB schema

**The document proposes:** verdict = `analysis_only` for low-evidence states

**The actual schema:** `verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail', 'error', 'tle'))`

**The contradiction:** `analysis_only` is not in the CHECK constraint. PostgreSQL will reject the INSERT.

**The correction:** Either:
- Add `analysis_only` to the CHECK constraint (requires schema migration)
- Or use `error` as the verdict for analysis-only submissions (semantically wrong)
- Or add a new column `verdict_type` to distinguish `authoritative` vs `analysis_only` (cleaner)

**Recommended:** Add `verdict_type TEXT DEFAULT 'authoritative'` column. Keep `verdict` as `pass`/`fail` for all submissions. Use `verdict_type` to gate downstream systems.

### Contradiction 3: Cold-start conflates problem-level and group-level

**The document says:** "cold-start ends when ≥1 pattern reaches structurally_observed or externally_listed"

**The document also says:** "verdict uses MINIMUM evidence of matched group"

**The contradiction:** If a problem has Group A (structurally_observed) and Group B (llm_proposed), the problem is "out of cold-start" but a user matching Group B still gets `analysis_only`. The problem-level cold-start flag is misleading.

**The correction:** Remove the concept of "problem-level cold-start." Instead, each group independently determines whether matching against it produces authoritative or analysis-only results. There is no problem-level transition — only group-level evidence states.

### Contradiction 4: K-factor interaction unspecified

**The document proposes:** K=0.75 for structurally_observed, K=0.5 for externally_listed

**The actual code:** `_compute_k()` already adjusts K based on `gap_strength` and `recent_history_length`

**The contradiction:** The document does not specify whether evidence-state K:
- Replaces existing K logic (evidence state IS the K-factor)
- Compounds with existing K logic (evidence state multiplies the computed K)
- Overrides existing K logic (evidence state sets a ceiling on K)

**The correction:** Evidence-state K should set a CEILING on the computed K, not compound with it. If evidence is `structurally_observed`, the final K is `min(computed_k, 0.75 * DEFAULT_K)`. This prevents compounding while still reducing authority.

### Contradiction 5: Self-reinforcing promotion loop

**The document says:** "a wrong initial LLM proposal must be able to be contradicted or superseded"

**The promotion path:** `llm_proposed` → `structurally_observed` (via clustering)

**The contradiction:** Once promoted to `structurally_observed`, the pattern becomes authoritative (K=0.75). This creates a self-reinforcing loop:
1. LLM proposes wrong pattern
2. Tutorial-derived submissions detect the pattern
3. Clustering promotes to structurally_observed
4. Pattern becomes authoritative
5. More submissions match it (reinforcing the pattern)
6. Pattern never gets contradicted (because it dominates)

**The demotion path requires:** conflicting evidence from a different pattern. But the promoted pattern suppresses conflicting evidence by dominating the submission pool.

**The correction:** Add a mechanism for external contradiction. If the CSV lists a different pattern than the structurally_observed pattern, mark the problem as `conflicted`. This breaks the self-reinforcing loop by introducing an independent signal.

---

## B. MISSING DATA-FLOW MECHANISMS

### Missing mechanism 1: Matched group index propagation

**The problem:** `run_persistence()` needs to know which group matched to:
- Extract the correct `expected_pattern` (fixing the persistence bug)
- Determine the evidence state of the matched group
- Gate downstream systems appropriately

**The current code:** `match_result["matched_groups"]` contains the indices of fully-matched groups. But `run_persistence()` does not receive this information in a usable form.

**The correction:** `run_persistence()` must receive `match_result` (already does) and extract `matched_groups` from it. Then use `matched_groups[0]` to identify the matched group and its evidence state.

### Missing mechanism 2: Evidence state in run_persistence

**The problem:** `run_persistence()` currently has no `evidence_state` parameter.

**The correction:** Add `evidence_state` parameter (or derive it from `groups` and `match_result`). The evidence state determines:
- Whether verdict is authoritative or analysis_only
- Whether topic_profiles are updated
- Whether gap_signals are generated
- Whether ELO is updated
- Whether recommendations are generated

### Missing mechanism 3: Two ELO systems

**The problem:** The document mentions "ELO" but the codebase has TWO ELO systems:
1. `user_pattern_elo` (per-pattern, managed by `EloEngine`)
2. `topic_profiles.elo_rating` (per-topic, managed by `update_topic_profile`)

**The correction:** Both must be gated by evidence state. Skipping `update_topic_profile()` handles the topic-level ELO. Gapping `elo_engine.compute_updates()` handles the pattern-level ELO. The document must explicitly mention both.

---

## C. BROKEN INVARIANTS

### Invariant 1: "Low-evidence ground truth must never produce authoritative PASS/FAIL"

**Status:** VIOLATED by current code. The document proposes fixing this with `analysis_only` verdict, but:
- `analysis_only` violates DB schema (Contradiction 2)
- The verdict is used in `update_topic_profile()` which the document proposes skipping
- But `gap_engine` and `elo_engine` use `match_result`, not `verdict`
- So gating verdict alone is insufficient — must also gate `match_result` flow

### Invariant 2: "A matched multi-solution group must determine expected_pattern"

**Status:** VIOLATED by current code (persistence bug). The document proposes fixing this, but:
- The fix requires `matched_groups` index from `match_result`
- The document does not specify how this index flows through the pipeline
- The document does not specify what happens when multiple groups match

### Invariant 3: "Cold-start submissions must still be stored and usable as future evidence"

**Status:** PARTIALLY ADDRESSED. The document says submissions ARE stored for clustering. But:
- Current code stores truncated code and single pattern (insufficient for clustering)
- Phase 0B/0C must complete before clustering can work
- The document does not explicitly state this dependency

### Invariant 4: "The architecture must not introduce circular validation"

**Status:** VIOLATED by the self-reinforcing promotion loop (Contradiction 5). The document proposes demotion rules but:
- Demotion requires conflicting evidence
- The promoted pattern suppresses conflicting evidence
- The loop is not broken

---

## CIRCULAR DEPENDENCY RISKS

### Risk 1: GT → submission → clustering → GT reinforcement

```
LLM proposes pattern A (llm_proposed)
  -> Users submit code (influenced by pattern A or tutorial)
  -> Clustering detects pattern A in submissions
  -> Pattern A promoted to structurally_observed
  -> Pattern A becomes authoritative (K=0.75)
  -> More users match pattern A (reinforcing)
  -> Pattern A never contradicted
```

**Severity:** HIGH. This is the same circular dependency identified in prior stress tests.

**Mitigation (from document):** Demotion rules when new evidence contradicts. But the promoted pattern suppresses contradictory evidence.

**Additional mitigation needed:** External contradiction signal (CSV or reference implementations).

### Risk 2: Wrong GT → wrong verdict → wrong topic profiles → wrong recommendations

```
Wrong GT: binary_search_standard
  -> Correct user (hash map) gets NO_MATCH
  -> Verdict: fail (if authoritative) or analysis_only (if low evidence)
  -> If analysis_only: topic_profiles not updated (correct)
  -> If authoritative: topic_profiles updated with wrong data (incorrect)
```

**Severity:** HIGH during cold-start, MEDIUM after.

**Mitigation:** The document proposes `analysis_only` for low-evidence states. But:
- `analysis_only` violates DB schema
- The mitigation is architecturally correct but implementation-wise incomplete

---

## CORRECTED AUTHORITY MODEL

### Evidence states (final, with corrections):

| State | What it means | Evidence type | K-factor | Topic profiles | Gap signals | Recommendations | Future evidence |
|-------|--------------|---------------|---------|---------------|-------------|----------------|----------------|
| **structurally_observed** | Same structural pattern in ≥2 independent submissions | Structural | K ceiling: 0.75 * DEFAULT_K | Updated (K ceiling: 0.75) | Active (flagged) | Active (lower priority) | Yes |
| **externally_listed** | Pattern in CSV (provenance verified) | External | K ceiling: 0.5 * DEFAULT_K | Updated (K ceiling: 0.5) | Active (flagged) | Active (lower priority) | Yes |
| **llm_proposed** | LLM proposed, taxonomy valid | Computational | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | Yes |
| **unobserved** | No evidence | None | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | No |
| **conflicted** | Sources disagree | Uncertain | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | No |

### Key changes from the document:

1. **K-factor is a CEILING, not a multiplier.** `final_k = min(computed_k, evidence_ceiling)`. This prevents compounding with existing K adjustments.

2. **Evidence state is per-GROUP, not per-problem.** `ProblemContext` carries `solution_groups` with per-group evidence states. The matched group's evidence state determines authority.

3. **No problem-level cold-start.** Each group independently determines authority. There is no problem-level transition.

4. **Two ELO systems gated separately.** `user_pattern_elo` gated by evidence state. `topic_profiles.elo_rating` gated by skipping `update_topic_profile()`.

---

## CORRECTED IMPLEMENTATION ORDER

### Phase 0: Critical bug fixes

1. Fix `run_persistence()` expected_pattern bug (use matched group)
2. Add `detected_patterns_json`, `code_hash`, `verdict_type` columns to submissions
3. Schema migration: add `verdict_type` column (NOT modify verdict CHECK constraint)

### Phase 1: Evidence model foundation

4. Add `solution_groups` and `validation_status` columns to `problem_ground_truth`
5. Add `solution_groups` with per-group evidence states to `ProblemContext`
6. Add `evidence_state` derivation logic (from matched group)
7. Implement LLM candidate generation with evidence state tracking
8. Determine CSV provenance before assigning `externally_listed` status

### Phase 2: Pipeline gating (single phase)

9. Implement verdict_type gating in `run_persistence()`:
   - Derive `verdict_type` from matched group's evidence state
   - Store `verdict_type` in submissions table
   - Gate `update_topic_profile()` by `verdict_type`
   - Gate `gap_engine.compute_signals()` by evidence state
   - Gate `elo_engine.compute_updates()` by evidence state (K ceiling)
   - Gate `get_recommendation()` by evidence state

### Phase 3: Clustering

10. Implement submission clustering using stored AST outputs
11. Implement independence estimation
12. Implement promotion rules with external contradiction signal

### Phase 4: Multi-solution support

13. Update LLM prompt for multi-group output
14. Update ground_truth_builder for multi-group storage
15. Verify multi-group matching works end-to-end

---

## WHAT ASSUMPTIONS REMAIN UNPROVEN

| Assumption | Risk | How to test |
|-----------|------|-------------|
| K ceiling of 0.75 is safe for structurally_observed | Too much or too little authority | A/B test with simulated users |
| `verdict_type` column is cleaner than modifying CHECK constraint | Schema complexity | Compare migration complexity |
| CSV provenance can be determined | Unknown provenance treated as independent | Inspect CSV creation process |
| External contradiction signal breaks self-reinforcing loop | Loop may persist | Simulate wrong-GT scenario |
| 2 submissions is sufficient for structural evidence | Overconfident | Analyze submission distributions |

---

*End of Architecture Preimplementation Audit*
