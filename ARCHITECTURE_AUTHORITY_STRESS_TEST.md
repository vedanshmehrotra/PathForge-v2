# ARCHITECTURE AUTHORITY STRESS TEST

**Status:** Adversarial review. No code changes.
**Date:** August 20, 2026
**Basis:** Code audit, all prior investigations, implementation plan review

---

## 1. EXECUTIVE FINDING

**The implementation plan contains a critical contradiction: it gives `structurally_observed` K=1.0 (full scoring authority) while simultaneously acknowledging that structural observation does not prove algorithmic correctness.**

This is not a minor calibration issue. It is a fundamental architectural contradiction that would cause the system to confidently penalize correct users when the ground truth is wrong.

Additionally, K-factor gating alone is insufficient. The plan proposes gating only the ELO K-factor, but the downstream cascade (topic profiles, gap signals, recommendations) is not gated. Wrong GT would still corrupt these systems even with K=0.

---

## 2. AUTHORITY AUDIT FOR EACH STATE

### `structurally_observed`

**What is known:** The AST detected the same structural pattern in ≥2 submissions from different users (with code similarity below threshold).

**What is merely inferred:** That the pattern represents a valid or correct algorithmic approach for this problem.

**What is NOT known:**
- Whether the pattern is algorithmically correct for this problem
- Whether the pattern is the primary approach
- Whether the pattern is optimal
- Whether the implementations are actually independent (could share tutorial source)
- Whether the implementations are correct (could be buggy code with correct structure)

**Can it safely determine FULL_MATCH / NO_MATCH?** NO. The match result compares detected patterns against GT patterns. If the GT pattern is structurally observed but algorithmically wrong, FULL_MATCH rewards wrong behavior and NO_MATCH penalizes correct behavior.

**Can it safely affect ELO?** NO at K=1.0. The ELO system uses `match_result_to_score()` which maps FULL_MATCH to 1.0 and NO_MATCH to 0.0. If GT is wrong, FULL_MATCH means the user matched the wrong pattern, and ELO should not reward this at full strength.

**Can it safely generate gap signals?** NO. Gap signals flag patterns as "missing" from the user's code. If the GT pattern is algorithmically wrong, the gap signal is misleading — it tells the user to practice a pattern that isn't actually relevant.

**Can it safely generate recommendations?** NO. Recommendations based on wrong gap signals push users toward irrelevant practice.

**Measured evidence:**
- AST detects `hash_map_lookup` in code using `set()` for membership testing. Structural detection is correct; algorithmic label is imprecise.
- AST detects `binary_search_standard` in code using binary search for counting (not searching). Structural detection is correct; algorithmic context is wrong.
- 5 users could submit tutorial-derived binary search solutions for a problem where binary search is wrong. AST would detect `binary_search_standard` in all 5. Independence threshold could be met. Pattern promoted to `structurally_observed`. But the pattern is algorithmically wrong for this problem.

**Verdict: `structurally_observed` must NOT receive K=1.0.**

---

### `externally_listed`

**What is known:** The CSV `pattern` column contains this pattern for this problem.

**What is merely inferred:** That the pattern is a valid algorithmic approach.

**What is NOT known:**
- Whether the CSV was manually curated or LLM-generated
- Whether the CSV pattern is correct
- Whether the CSV represents alternatives (OR) or complements (AND)

**Can it safely determine FULL_MATCH / NO_MATCH?** NO. Same reasoning as above — matching against potentially wrong GT.

**Can it safely affect ELO?** NO at K=0.5. The CSV provenance is unknown. If CSV was LLM-generated, it shares biases with the LLM GT. K=0.5 still allows wrong-direction updates.

**Can it safely generate gap signals?** NO. Same reasoning as `structurally_observed`.

**Can it safely generate recommendations?** NO.

**Verdict: `externally_listed` must NOT receive K=0.5. It should receive K=0 until independence from LLM is verified.**

---

### `llm_proposed`

**What is known:** The LLM proposed this pattern, and it passed taxonomy + structural validation.

**What is merely inferred:** Nothing beyond vocabulary validity.

**What is NOT known:** Everything about algorithmic correctness.

**Can it safely determine FULL_MATCH / NO_MATCH?** NO. The LLM is unreliable (50% consistency, 46 hallucinated patterns in experiment).

**Can it safely affect ELO?** NO. K=0 is correct.

**Can it safely generate gap signals?** NO. Suppression is correct.

**Can it safely generate recommendations?** NO. Suppression is correct.

**Verdict: K=0 and full suppression are correct for `llm_proposed`.**

---

### `unobserved`

**What is known:** Nothing.

**What is merely inferred:** Nothing.

**Can it safely determine FULL_MATCH / NO_MATCH?** NO.

**Can it safely affect ELO?** NO. K=0 is correct.

**Can it safely generate gap signals?** NO.

**Can it safely generate recommendations?** NO.

**Verdict: Full suppression is correct for `unobserved`.**

---

### `conflicted`

**What is known:** Multiple sources disagree on the pattern.

**What is merely inferred:** Nothing — the disagreement itself is the signal.

**Can it safely determine FULL_MATCH / NO_MATCH?** NO. The system doesn't know which source is correct.

**Can it safely affect ELO?** NO. K=0 is correct.

**Can it safely generate gap signals?** NO.

**Can it safely generate recommendations?** NO.

**Verdict: Full suppression is correct for `conflicted`.**

---

## 3. THE `structurally_observed -> K=1.0` CONTRADICTION

### The architecture's own distinction:

The architecture explicitly separates:
- **Layer A (Structural Observation):** "What patterns are structurally observed in code?"
- **Layer B (Algorithmic Claims):** "What approaches are believed to be valid for this problem?"

### The contradiction:

`structurally_observed` is a Layer A state. K=1.0 is a Layer B authority level. Giving Layer A state Layer B authority violates the architecture's own separation.

### Why this matters:

The matching engine produces `FULL_MATCH` or `NO_MATCH` based on whether detected patterns satisfy GT groups. This is a Layer B operation — it compares structural detection (Layer A) against algorithmic claims (Layer B).

If the algorithmic claim (GT) is wrong, `FULL_MATCH` means the user matched the wrong claim. `NO_MATCH` means the user didn't match the wrong claim (possibly because they implemented the correct approach).

K=1.0 says "this match result has full authority." But the match result's authority depends on the GT's reliability, not on how many users structurally exhibited the pattern.

### The measured harm:

```
Wrong GT: ["binary_search_standard"] for Contains Duplicate
Promoted to structurally_observed (3 tutorial-derived submissions)

Correct user submits: set membership solution
AST detects: nothing (too simple for current detectors)
Matching: NO_MATCH
Verdict: fail
ELO: penalty at K=1.0 (full strength)
Gap: binary_search_standard flagged as "missing"
Recommendation: practice binary search

The user is CORRECTLY solving the problem
The system PENALIZES them at full strength
```

---

## 4. ADDITIONAL CONTRADICTIONS IN THE IMPLEMENTATION PLAN

### Contradiction 1: K-factor gating is insufficient

**The plan:** Gate ELO K-factor by evidence state.

**The reality:** K-factor gating only affects ELO magnitude. The downstream cascade is not gated:

| System | Uses verdict? | Gated by K-factor? | Affected by wrong GT? |
|--------|--------------|-------------------|----------------------|
| topic_profiles.pass_count | Yes | NO | YES — wrong pass/fail counts |
| topic_profiles.accuracy | Yes | NO | YES — wrong accuracy |
| topic_profiles.recent_failures | Yes | NO | YES — wrong failure tracking |
| topic_profiles.elo | Yes | YES (K-factor) | Partially — magnitude reduced |
| gap_signals | Yes (via unmatched_patterns) | NO | YES — wrong gap identification |
| recommendations | Yes (via gap_signals + elo) | Partially | YES — wrong recommendations |

**Fix required:** Gate the ENTIRE downstream pipeline, not just K-factor. When GT is `llm_proposed` or `unobserved`, skip topic_profile updates, gap signals, and recommendations entirely.

### Contradiction 2: Verdict is not gated

**The plan:** Matching always runs and produces a verdict.

**The reality:** The verdict (`pass`/`fail`) feeds into topic_profiles, gap signals, and recommendations. If GT is wrong, the verdict is wrong. Wrong verdicts corrupt all downstream systems.

**The plan's own authority matrix says:**
- `llm_proposed`: "match result is INFORMATIONAL ONLY"

**But the code does:**
```python
verdict = "pass" if match_result_str in ("FULL_MATCH", "PARTIAL_MATCH") else "fail"
```

There is no check for evidence state. The verdict is always computed. If the plan says match result is "informational only" for `llm_proposed`, then the verdict must NOT be `pass`/`fail` — it must be something like `analysis_only` that doesn't feed into downstream systems.

### Contradiction 3: `externally_listed` gets K=0.5 without provenance verification

**The plan:** CSV patterns get K=0.5.

**The reality:** The CSV provenance is unknown. If the CSV was LLM-generated (likely, given the consistent JSON format), it is NOT independent of the LLM ground truth. Treating it as independent evidence with K=0.5 authority is misleading.

**Fix required:** Determine CSV provenance before assigning authority. If provenance is unknown, treat CSV as `llm_proposed` equivalent (K=0).

### Contradiction 4: Evidence state is per-pattern but verdict is per-submission

**The plan:** Evidence states apply to individual patterns.

**The reality:** The verdict is computed per-submission, not per-pattern. A submission matching ANY pattern in the GT gets `pass`. The evidence state of the matched pattern determines K-factor, but the verdict itself is not gated.

**Example:**
```
Problem has:
  pattern A: structurally_observed (K=1.0)
  pattern B: llm_proposed (K=0)

User implements pattern A -> FULL_MATCH -> verdict=pass
ELO for pattern A updated at K=1.0

But what if pattern A is structurally observed but algorithmically wrong?
The user matched the wrong pattern and got rewarded at full strength
```

### Contradiction 5: Clustering promotes patterns without algorithmic verification

**The plan:** ≥2 independent submissions with same pattern → promote to `structurally_observed`.

**The reality:** The promotion criteria are purely structural. There is no check for:
- Whether the pattern is algorithmically correct
- Whether the pattern is the primary approach
- Whether the pattern is optimal

The plan correctly states this ("structurally_observed does NOT prove algorithmic correctness") but then gives it K=1.0, which implies full algorithmic authority.

---

## 5. THE FUNDAMENTAL PROBLEM

**The architecture cannot distinguish between:**

A. "Multiple users implemented the correct approach, and the AST correctly detected the pattern" (good evidence)

B. "Multiple users copied a tutorial that implements the wrong approach, and the AST correctly detected the structural pattern" (bad evidence)

Both produce identical structural observation. The architecture has no mechanism to distinguish them.

**This means: No evidence state below human verification can safely claim full algorithmic authority.**

K=1.0 implies "we are confident this is correct." The architecture cannot be confident without human verification. Therefore, no evidence state should receive K=1.0.

---

## 6. REVISED AUTHORITY MATRIX

### Core principle: No evidence state below human verification receives full authority

| Evidence state | Match result | ELO K-factor | Gap signals | Recommendations | User display |
|---------------|-------------|-------------|-------------|----------------|-------------|
| **structurally_observed** | Authoritative | K=0.75 | Active (flagged as "structurally common") | Active (lower priority) | "Common approach" |
| **externally_listed** | Provisional | K=0.5 | Active (flagged as "externally listed") | Active (lower priority) | "Listed approach" |
| **llm_proposed** | Informational | **K=0** | **Suppressed** | **Suppressed** | "Possible approach" |
| **unobserved** | Informational | **K=0** | **Suppressed** | **Suppressed** | Hidden |
| **conflicted** | Informational | **K=0** | **Suppressed** | **Suppressed** | "Uncertain" |

### Why K=0.75 for `structurally_observed` (not K=1.0):

- K=1.0 implies "we are sure this is correct"
- We are NOT sure — structural observation does not prove algorithmic correctness
- K=0.75 says "this is strong evidence, but we acknowledge uncertainty"
- The 25% reduction represents the gap between structural observation and algorithmic proof

### Why K=0.5 for `externally_listed` (not K=0.5 as previously proposed):

Actually, K=0.5 was already proposed. But with the additional requirement: CSV provenance must be verified before assigning this level. If CSV provenance is unknown, use K=0.

### Why K=0 for `llm_proposed`, `unobserved`, `conflicted`:

These states have no reliable evidence. Any scoring would be noise.

---

## 7. REVISED COLD-START BEHAVIOR

### The correction:

The previous plan said "cold-start: K=0 until evidence exists." But the revised authority matrix already gives K=0 to `llm_proposed`. So cold-start is automatically handled — new problems start with `llm_proposed` patterns, which already have K=0.

### The additional requirement:

During cold-start (no `structurally_observed` or `externally_listed` patterns), the system must also suppress:
- Topic profile updates (pass_count, accuracy, recent_failures)
- Gap signals
- Recommendations
- Any verdict that feeds into downstream systems

### The verdict during cold-start:

Instead of `pass`/`fail`, the verdict should be `analysis_only` for submissions against `llm_proposed` GT. This verdict is stored in the submissions table but does NOT feed into topic_profiles, gap_signals, or recommendations.

---

## 8. REVISED IMPLEMENTATION PLAN CORRECTIONS

### Phase 2B must be rewritten:

**Previous:** Gate ELO K-factor by evidence state.

**Corrected:** Gate the ENTIRE downstream pipeline by evidence state:
1. If evidence is `llm_proposed` or `unobserved`:
   - Verdict = `analysis_only` (not `pass`/`fail`)
   - Skip topic_profile updates
   - Skip gap signal generation
   - Skip ELO updates
   - Skip recommendation generation
2. If evidence is `externally_listed`:
   - Verdict = `pass`/`fail` (provisional)
   - Topic_profile updates with K=0.5
   - Gap signals active (flagged)
   - ELO updates with K=0.5
   - Recommendations active (lower priority)
3. If evidence is `structurally_observed`:
   - Verdict = `pass`/`fail` (authoritative)
   - Topic_profile updates with K=0.75
   - Gap signals active
   - ELO updates with K=0.75
   - Recommendations active

### Phase 2C and 2D must be merged into 2B:

Gap signals and recommendations are already gated by the evidence state in the revised 2B. Separate phases are unnecessary.

### Phase 5A clustering must include algorithmic verification:

**Previous:** ≥2 independent submissions → promote to `structurally_observed`.

**Corrected:** ≥2 independent submissions → promote to `structurally_observed` BUT with a flag indicating "structural observation only, not algorithmically verified."

The flag is already implicit in the state name (`structurally_observed` vs `validated`), but the implementation must ensure no downstream system treats it as algorithmic proof.

---

## 9. WHAT ASSUMPTIONS REMAIN UNPROVEN

| Assumption | Risk if wrong | How to test |
|-----------|--------------|-------------|
| K=0.75 is the right calibration for structurally_observed | Too much or too little authority | A/B test with simulated users |
| `analysis_only` verdict correctly prevents downstream corruption | Topic profiles still corrupted | Verify all downstream paths check verdict |
| CSV provenance can be determined | Unknown provenance treated as independent | Inspect CSV creation process |
| Code similarity threshold correctly identifies copies | Copies counted as independent | Test with known copied submissions |
| 2 submissions is sufficient for structural evidence | Overconfident in weak evidence | Analyze submission distributions |

---

## 10. FINAL CORRECTED AUTHORITY MATRIX

| Evidence state | What it means | Match result authority | ELO K-factor | Topic profiles | Gap signals | Recommendations | User display |
|---------------|--------------|----------------------|-------------|---------------|-------------|----------------|-------------|
| **structurally_observed** | Same structural pattern in ≥2 independent submissions | Authoritative | K=0.75 | Updated (K=0.75) | Active (flagged) | Active (lower priority) | "Common approach" |
| **externally_listed** | Pattern in CSV (provenance verified) | Provisional | K=0.5 | Updated (K=0.5) | Active (flagged) | Active (lower priority) | "Listed approach" |
| **llm_proposed** | LLM proposed, taxonomy valid | Informational only | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | "Possible approach" |
| **unobserved** | No evidence | Informational only | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | Hidden |
| **conflicted** | Sources disagree | Informational only | K=0 | **SKIPPED** | **SUPPRESSED** | **SUPPRESSED** | "Uncertain" |

### The key change from the previous proposal:

**`structurally_observed` gets K=0.75, not K=1.0.** This 25% reduction represents the architectural acknowledgment that structural observation does not prove algorithmic correctness. No evidence state below human verification receives full authority.

**Topic profiles, gap signals, and recommendations are gated by evidence state, not just K-factor.** Wrong GT must not corrupt any downstream system.

**`llm_proposed` verdict is `analysis_only`, not `pass`/`fail`.** The verdict itself must be gated, not just its downstream effects.

---

*End of Architecture Authority Stress Test*
