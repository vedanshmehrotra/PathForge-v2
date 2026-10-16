# FINAL ARCHITECTURE VERDICT

**Status:** Final reconciliation. No code changes.
**Date:** August 20, 2026
**Basis:** Complete code audit, all prior documents, adversarial review

---

## A. EVERY CONTRADICTION STILL PRESENT

### Contradiction 1: K-factor for structurally_observed (UNRESOLVED)

**Documents disagree:**
- `ARCHITECTURE_FINAL_RECONCILIATION.md`: K=1.0
- `ARCHITECTURE_AUTHORITY_STRESS_TEST.md`: K=0.75
- `IMPLEMENTATION_PLAN.md`: Phase 2B says K=1.0

**Why it is dangerous:** K=1.0 means "full algorithmic authority." But `structurally_observed` only proves structural repetition, not algorithmic correctness. A tutorial-derived wrong pattern promoted to `structurally_observed` would penalize correct users at full strength.

**The code affected:** `pathforge/elo_engine.py` `_compute_k()` and `compute_updates()`.

**Smallest correction:** K=0.75 for `structurally_observed`. The 25% reduction represents the gap between structural observation and algorithmic proof. This is the minimum safe level — any higher risks systematic harm from wrong GT.

---

### Contradiction 2: Pipeline gating is incomplete (UNRESOLVED)

**Documents disagree:**
- `ARCHITECTURE_FINAL_RECONCILIATION.md`: K-factor gating only
- `ARCHITECTURE_AUTHORITY_STRESS_TEST.md`: Full pipeline gating needed
- `IMPLEMENTATION_PLAN.md`: Phase 2B/2C/2D as separate phases

**Why it is dangerous:** K-factor gating only affects ELO magnitude. The downstream cascade is not gated:

| System | Uses verdict? | Gated by K-factor? | Affected by wrong GT? |
|--------|--------------|-------------------|----------------------|
| topic_profiles.pass_count | Yes | NO | YES |
| topic_profiles.accuracy | Yes | NO | YES |
| topic_profiles.recent_failures | Yes | NO | YES |
| gap_signals | Yes | NO | YES |
| recommendations | Yes | Partially | YES |

**The code affected:** `pathforge/services/persistence.py` lines 74-110 (all downstream calls are unconditional).

**Smallest correction:** Gate the ENTIRE downstream pipeline by evidence state. When evidence is `llm_proposed` or `unobserved`, skip topic_profile updates, gap signals, ELO updates, and recommendations. Use `analysis_only` verdict instead of `pass`/`fail`.

---

### Contradiction 3: Cold-start behavior is insufficient (UNRESOLVED)

**Documents disagree:**
- `ARCHITECTURE_FINAL_RECONCILIATION.md`: K=0 until evidence exists
- `ARCHITECTURE_AUTHORITY_STRESS_TEST.md`: analysis_only verdict needed
- `IMPLEMENTATION_PLAN.md`: Phase 3B suppresses ELO

**Why it is dangerous:** K=0 suppresses ELO but does NOT suppress topic_profiles, gap signals, or recommendations. A user against wrong cold-start GT would still get wrong pass/fail counts, wrong gap signals, and wrong recommendations.

**The code affected:** `pathforge/services/persistence.py` lines 74-110 (all unconditional).

**Smallest correction:** During cold-start (no `structurally_observed` or `externally_listed` patterns), the verdict must be `analysis_only`, not `pass`/`fail`. All downstream systems must check verdict before updating.

---

### Contradiction 4: Evidence state flow is missing (MISSING FROM ALL DOCUMENTS)

**The problem:** The architecture requires evidence state to flow from `problem_ground_truth` through `ProblemContext` to `run_persistence` to downstream engines.

**But the current code has NO mechanism for this:**
- `ProblemContext` has no `evidence_state` field
- `run_persistence` has no `evidence_state` parameter
- `elo_engine` has no `authority` parameter
- `gap_engine` has no `authority` parameter

**The code affected:** `pathforge/services/problem_resolver.py` (ProblemContext dataclass), `pathforge/services/persistence.py` (run_persistence function), `pathforge/elo_engine.py`, `pathforge/gap_signal_engine.py`.

**Smallest correction:** Add `evidence_state` field to `ProblemContext`. Add `evidence_state` parameter to `run_persistence`. Each downstream engine checks evidence state before updating.

---

### Contradiction 5: `externally_listed` gets authority without provenance verification (UNRESOLVED)

**The problem:** The CSV `pattern` column may be LLM-generated. If so, it is NOT independent of the LLM ground truth. Giving it K=0.5 authority is misleading.

**The code affected:** `pathforge/data/pathforge_problems_fixed.csv` (source data), `pathforge/services/ground_truth_builder.py` (CSV cross-reference logic).

**Smallest correction:** Determine CSV provenance before assigning authority. If provenance is unknown, treat CSV as `llm_proposed` equivalent (K=0). Only promote to `externally_listed` (K=0.5) after provenance is verified as independent.

---

### Contradiction 6: Evidence state is per-pattern but verdict is per-submission (STRUCTURAL)

**The problem:** Evidence states apply to individual patterns. But the verdict is computed per-submission. A submission matching ANY pattern in the GT gets `pass`. The evidence state of the matched pattern determines K-factor, but the verdict itself is not gated.

**The code affected:** `pathforge/services/persistence.py` line 28 (verdict computation).

**Smallest correction:** The verdict must consider the MINIMUM evidence state of all patterns in the matched group. If any pattern in the matched group is `llm_proposed`, the verdict is `analysis_only`.

---

### Contradiction 7: Clustering promotes without algorithmic verification (STRUCTURAL)

**The problem:** ≥2 independent submissions promotes to `structurally_observed` with no check for algorithmic correctness. The architecture correctly names this state to imply structural observation only, but the downstream permissions (K=0.75, gap signals, recommendations) imply algorithmic authority.

**The code affected:** Future clustering logic (not yet implemented).

**Smallest correction:** Ensure `structurally_observed` permissions are calibrated to reflect structural-only evidence. K=0.75 (not K=1.0) and gap signals flagged as "structurally common" (not "confirmed approach").

---

## B. CORRECTED AUTHORITY MODEL

### Evidence states (final):

| State | What it means | Evidence type |
|-------|--------------|---------------|
| **structurally_observed** | Same structural pattern in ≥2 independent submissions | Structural (not algorithmic) |
| **externally_listed** | Pattern in CSV (provenance verified as independent) | External (not algorithmic) |
| **llm_proposed** | LLM proposed, taxonomy valid | Computational (not reliable) |
| **unobserved** | No evidence | None |
| **conflicted** | Sources disagree | Uncertain |

### Key principle:

**No evidence state below human verification receives full algorithmic authority.**

---

## C. CORRECTED DOWNSTREAM PERMISSION MATRIX

| Evidence state | Show analysis? | Produce PASS/FAIL? | Affect ELO? | Affect topic profiles? | Generate gap signals? | Generate recommendations? | Use as future evidence? |
|---------------|---------------|-------------------|-------------|----------------------|----------------------|--------------------------|----------------------|
| **structurally_observed** | Yes | Yes (authoritative) | Yes (K=0.75) | Yes (K=0.75) | Yes (flagged) | Yes (lower priority) | Yes |
| **externally_listed** | Yes | Yes (provisional) | Yes (K=0.5) | Yes (K=0.5) | Yes (flagged) | Yes (lower priority) | Yes |
| **llm_proposed** | Yes | **NO (analysis_only)** | **NO (K=0)** | **NO (skipped)** | **NO (suppressed)** | **NO (suppressed)** | Yes |
| **unobserved** | Yes | **NO (analysis_only)** | **NO (K=0)** | **NO (skipped)** | **NO (suppressed)** | **NO (suppressed)** | No |
| **conflicted** | Yes | **NO (analysis_only)** | **NO (K=0)** | **NO (skipped)** | **NO (suppressed)** | **NO (suppressed)** | No |

### What "analysis_only" means:

The match result is returned to the user as structural information, but:
- The verdict is `analysis_only`, not `pass`/`fail`
- Topic profiles are NOT updated
- Gap signals are NOT generated
- ELO is NOT updated
- Recommendations are NOT generated
- The submission IS stored (for future clustering)

### What "flagged" means for gap signals:

Gap signals are generated but marked with `source: "structurally_observed"` or `source: "externally_listed"`. The user sees "this pattern is structurally common" not "you are weak at this pattern."

---

## D. COLD-START BEHAVIOR (CORRECTED)

### New problem with zero submissions:

```
Problem added
  -> LLM generates candidates -> stored as llm_proposed
  -> User submits code
  -> AST analysis runs
  -> Matching runs (informational only)
  -> Verdict: analysis_only (not pass/fail)
  -> Topic profiles: NOT updated
  -> Gap signals: NOT generated
  -> ELO: NOT updated
  -> Recommendations: NOT generated
  -> Submission stored (for future clustering)
  -> User sees: "Analysis in progress - patterns not yet validated"
```

### When cold-start ends:

When ≥1 pattern reaches `structurally_observed` or `externally_listed` status, the problem transitions out of cold-start. All subsequent submissions use the appropriate authority level.

---

## E. EVIDENCE STATE FLOW (CORRECTED)

The missing architectural link must be explicitly designed:

```
problem_ground_truth
  -> validation_status (evidence state)
  -> solution_groups (with per-pattern evidence states)
       |
       v
ProblemContext
  -> evidence_state (derived from solution_groups)
       |
       v
run_persistence(evidence_state=ctx.evidence_state)
  -> verdict = "analysis_only" if evidence_state in ("llm_proposed", "unobserved", "conflicted")
  -> verdict = "pass"/"fail" if evidence_state in ("structurally_observed", "externally_listed")
  -> topic_profiles: skipped if analysis_only
  -> gap_signals: suppressed if analysis_only
  -> elo: K=0 if analysis_only
  -> recommendations: suppressed if analysis_only
```

---

## F. CORRECTED IMPLEMENTATION ORDER

### Phase 0: Critical bug fixes (no architecture change)

1. Fix `run_persistence()` expected_pattern bug (use matched group, not first group)
2. Add `detected_patterns_json` and `code_hash` columns to submissions

### Phase 1: Evidence model foundation

3. Add `solution_groups` and `validation_status` columns to `problem_ground_truth`
4. Add `evidence_state` field to `ProblemContext`
5. Add `evidence_state` parameter to `run_persistence()`
6. Implement LLM candidate generation with evidence state tracking
7. Implement CSV cross-reference validation (after provenance verification)

### Phase 2: Pipeline gating (single phase, not separate)

8. Implement full pipeline gating in `run_persistence()`:
   - Check evidence_state before computing verdict
   - Check verdict before updating topic_profiles
   - Check evidence_state before generating gap_signals
   - Check evidence_state before updating ELO
   - Check evidence_state before generating recommendations
9. Implement `analysis_only` verdict for low-evidence states
10. Implement cold-start detection and suppression

### Phase 3: Clustering

11. Implement submission clustering using stored AST outputs
12. Implement independence estimation using code_hash + user_id + temporal separation
13. Implement promotion rules (unobserved -> llm_proposed -> structurally_observed)

### Phase 4: Multi-solution support

14. Update LLM prompt for multi-group output
15. Update ground_truth_builder for multi-group storage
16. Enable multi-group matching (MatchingEngine already supports this)

---

## G. FINAL VERDICT

**The architecture is sound in principle but has 7 contradictions that must be resolved before implementation.**

The most critical corrections are:
1. K=0.75 for `structurally_observed` (not K=1.0)
2. Full pipeline gating (not just K-factor)
3. `analysis_only` verdict for low-evidence states
4. Explicit evidence state flow through the entire pipeline
5. CSV provenance verification before authority assignment

**The architecture should NOT be implemented until these contradictions are resolved in a single, authoritative document.**

---

*End of Final Architecture Verdict*
