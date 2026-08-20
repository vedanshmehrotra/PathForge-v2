# GROUND TRUTH AUTHORITY RECONCILIATION

**Status:** Architecture reconciliation. No code changes.
**Date:** August 20, 2026
**Basis:** All prior investigations, code audit, stress tests

---

## EXECUTIVE VERDICT

**APPROVE WITH CHANGES**

The architecture contains one critical contradiction and two significant design errors that must be corrected before implementation. The evidence model is sound in principle but currently assigns more authority to evidence than it actually supports.

---

## 1. EVERY INTERNAL CONTRADICTION FOUND

### Contradiction 1: CRITICAL — Evidence vs Authority mismatch

**The claim:** `structurally_repeated` "does NOT guarantee that a pattern is algorithmically correct or primary."

**The action:** The downstream matrix gives it full ELO impact (K=1.0), gap signals, recommendation influence, and displays it as "verified approach."

**The contradiction:** If we know the evidence doesn't prove correctness, we cannot give it the maximum authority level. The word "verified" is particularly dishonest — it implies we have checked and confirmed correctness, which we have not.

**Measured evidence from the codebase:**

The AST engine detects `hash_map_lookup` in code that uses a `set()` for duplicate detection. The detection is structurally accurate (there is a membership check), but calling it "hash_map_lookup" as an *algorithmic strategy* is misleading. If 5 users submit similar `set()`-based duplicate detection code, clustering would "verify" `hash_map_lookup` as the approach — but the actual algorithmic strategy is "set membership," not "hash map lookup."

Similarly, the AST detects `binary_search_standard` in code that uses binary search for counting (not searching). The structural detection is correct; the algorithmic classification is wrong.

**Fix required:** `structurally_repeated` must NOT be called "verified" and must NOT receive K=1.0 authority. It represents observed structural repetition, not confirmed algorithmic correctness.

### Contradiction 2: HIGH — Matching authority vs GT reliability

**The claim:** LLM-generated ground truth may be wrong.

**The action:** The matching engine treats GT as authoritative. `FULL_MATCH` means "all patterns in at least one GT group are detected by AST." This produces a `pass` verdict that feeds into ELO, gap signals, and recommendations.

**The contradiction:** If GT may be wrong, then `FULL_MATCH` against wrong GT is meaningless. A user who implements the correct approach gets `NO_MATCH` and is penalized. A user who implements the wrong approach (matching wrong GT) gets `FULL_MATCH` and is rewarded.

**The specific failure path (verified from code):**

```
Wrong GT: ["binary_search_standard"] for Two Sum
User implements hash map solution (correct)
AST detects: hash_map_lookup
Matching: NO_MATCH (hash_map_lookup not in GT)
Verdict: fail
ELO: score = 0.0 (NO_MATCH)
Gap signals: hash_map_lookup flagged as "missing"
Topic profile: pattern_match_count NOT incremented
```

The system penalizes the correct user and would eventually flag `hash_map_lookup` as a weakness — because the GT is wrong, not because the user is weak.

**Fix required:** The matching engine must know whether GT is reliable before assigning verdict authority.

### Contradiction 3: HIGH — Cold-start ELO vs GT uncertainty

**The claim:** Cold-start problems use LLM-generated GT with K=0.5.

**The action:** K=0.5 means the ELO update is half the normal magnitude, but the DIRECTION is still determined by the match result against potentially wrong GT.

**The contradiction:** Reducing K doesn't prevent wrong-direction updates. If GT is wrong and K=0.5, the user still gets penalized for correct behavior — just less. Over multiple submissions, this accumulates into a systematic bias.

**The specific failure path:**

```
New problem with wrong LLM GT
10 users submit correct solutions → all get NO_MATCH
Each gets ELO penalty (reduced by K=0.5)
After 10 submissions: users have accumulated ELO deficit
Clustering sees 10 submissions with same pattern → promotes to structurally_repeated
But users already have damaged ELO scores
```

**Fix required:** Cold-start should suppress ELO updates entirely until evidence exists, not merely reduce them.

### Contradiction 4: MEDIUM — Independence claim vs data availability

**The claim:** "≥2 submissions from different users with same pattern = structural evidence."

**The reality:** The submissions table stores `code_text` truncated to 1000 chars and only the primary `detected_pattern` (single string). There is no stored code fingerprint, no full AST output, no code similarity metric.

**The contradiction:** The architecture claims to use "structurally independent" submissions but has no mechanism to verify structural independence. Different `user_id` values are the only available independence signal, which is weak (users copy from tutorials).

**Fix required:** Either store full AST output per submission (enabling re-analysis) or accept that independence cannot be reliably established with current data storage.

### Contradiction 5: MEDIUM — "externally_supported" vs CSV reliability

**The claim:** CSV patterns provide independent external evidence.

**The question:** Is the CSV actually independent? The CSV was created as `pathforge_problems_fixed.csv` — was it manually curated or LLM-generated?

**The evidence:** The CSV contains 300 problems with pattern assignments in JSON list format. The format is consistent (all `["pattern_name"]` lists). This looks like it was generated by a process, possibly LLM-based. If the CSV was generated by the same or similar LLM, it is NOT independent of the LLM ground truth.

**The contradiction:** If CSV and LLM share biases (from similar training data or generation processes), treating them as independent evidence is misleading.

**Fix required:** Determine CSV provenance before treating it as independent evidence. If CSV provenance is unknown, treat it as weak supplementary evidence, not independent confirmation.

---

## 2. REVISED EVIDENCE MODEL

### Core principle: Separate what was observed from what can be inferred

The architecture must distinguish between:
- **Observation:** "The AST detected pattern X in this code" (high confidence)
- **Inference:** "Pattern X is the correct algorithmic approach for this problem" (lower confidence)

These are different epistemic states and must have different authority levels.

### Revised state definitions:

| State | What was observed | What can be inferred | What CANNOT be inferred |
|-------|------------------|---------------------|------------------------|
| **structurally_observed** | ≥2 submissions from different users detected with the same primary pattern by the AST engine | The structural pattern is present in multiple real implementations | That the pattern is algorithmically correct; that implementations are independent; that the implementation is correct; that the pattern is the primary strategy |
| **externally_listed** | Pattern appears in the CSV `pattern` column for this problem | A prior process assigned this pattern | That the assignment is correct; that the pattern is optimal; OR vs AND relationships; CSV provenance is known |
| **llm_proposed** | Pattern from LLM output, passed taxonomy + structural validation | Pattern is valid vocabulary; structure is sane | Algorithmic correctness; completeness; correct group structure |
| **unobserved** | No evidence from any source | Nothing beyond the problem existing | Anything |
| **conflicted** | Multiple independent sources disagree on the pattern for this problem | The pattern assignment is uncertain | Which source is correct |

### Key terminology changes:

- `structurally_repeated` → `structurally_observed` (we observed repetition, not confirmation)
- `externally_supported` → `externally_listed` (it appears in a list, not that it's supported)
- `llm_suggested` → `llm_proposed` (it was proposed, not suggested — "suggested" implies more authority)
- `unverified` → `unobserved` (nothing was observed, not that verification was attempted)
- `contradicted` → `conflicted` (sources conflict, we don't know who's right)

### State granularity:

States apply to **individual patterns**, not to problems or groups. A problem may have:
```
hash_map_lookup: structurally_observed (3 users)
two_pointers_opposite: externally_listed (CSV)
sorting: llm_proposed (LLM only)
```

---

## 3. WHETHER STRUCTURAL EVIDENCE AND ALGORITHMIC GT MUST BE SEPARATE LAYERS

**Yes. They must be separate.**

The current architecture collapses two fundamentally different questions into one evidence state:

**Question 1 (Structural):** "What patterns does the AST repeatedly detect in user code for this problem?"

**Question 2 (Algorithmic):** "What algorithmic approaches are valid optimal solutions for this problem?"

These questions have different answers, different evidence sources, and different reliability levels.

### Why they must be separate:

1. **Structural observation can be wrong about algorithmic correctness.** The AST detects `hash_map_lookup` in code using a `set()`. The structural observation is correct; the algorithmic label is misleading.

2. **Algorithmic ground truth can be wrong about structural presence.** The LLM may say "this problem requires `binary_search_standard`" but no user has ever submitted a binary search solution. The algorithmic claim is unverified.

3. **Matching requires both layers.** The matching engine needs to know:
   - What patterns are algorithmically valid for this problem (GT layer)
   - What patterns the user's code actually implements (AST layer)
   
   But the GT layer's reliability varies. The architecture must account for this.

### Proposed two-layer model:

**Layer 1: Structural Evidence** (what the AST observes in user code)
- `structurally_observed`: Pattern detected in ≥2 submissions
- `structurally_absent`: Pattern never detected in any submission
- `structurally_rare`: Pattern detected in exactly 1 submission

**Layer 2: Algorithmic Claims** (what sources say is valid for this problem)
- `llm_proposed`: LLM says this is a valid approach
- `externally_listed`: CSV says this is a valid approach
- `conflicted`: Sources disagree
- `unclaimed`: No source says this is valid

### How the layers interact:

The matching engine should consider BOTH layers:
- If a pattern is in the GT (any algorithmic claim level) AND detected by AST → match
- If a pattern is NOT in any algorithmic claim BUT is structurally observed → the system should note this but not penalize the user
- If a pattern IS in the algorithmic claim BUT structurally absent → the system should note this as potential GT weakness

---

## 4. REVISED DOWNSTREAM AUTHORITY MATRIX

### The key principle: Authority must match evidence reliability

| Evidence state | Matching | Match verdict | ELO | Gap signals | Recommendations | User display |
|---------------|----------|--------------|-----|-------------|----------------|-------------|
| **structurally_observed** | Yes | Informative only (not authoritative) | K=0.5 (not 1.0) | Yes (but flagged) | Yes (lower priority) | "Common approach" |
| **externally_listed** | Yes | Informative only | K=0.5 | Yes (flagged) | Yes (lower priority) | "Listed approach" |
| **llm_proposed** | Yes | Informative only | K=0 (no update) | No | No | "Possible approach" |
| **unobserved** | Yes | Informative only | K=0 | No | No | Hidden |
| **conflicted** | Yes (all candidates) | K=0 | No | No | No | "Uncertain" |

### What "informative only" means for match verdicts:

The match result should be returned to the user as information, but should NOT automatically determine the `pass`/`fail` verdict that feeds into ELO.

Instead, the verdict should be:

```python
if gt_reliability == "high":
    verdict = "pass" if match_result in ("FULL_MATCH", "PARTIAL_MATCH") else "fail"
elif gt_reliability == "medium":
    verdict = "provisional_pass" if match_result == "FULL_MATCH" else "uncertain"
else:  # low or unknown
    verdict = "analysis_only"  # no pass/fail, just structural information
```

### Why K=0 for `llm_proposed`:

If the only evidence for a pattern is the LLM's proposal, the system knows nothing about whether that pattern is correct. Updating ELO based on matching against unverified GT is worse than not updating at all — it creates systematic bias.

### Why `structurally_observed` gets K=0.5 (not K=1.0):

Structural observation shows the pattern exists in real code. But it doesn't prove the pattern is the correct algorithmic approach for the problem. K=0.5 acknowledges this uncertainty while still allowing skill modeling to progress.

---

## 5. REVISED COLD-START BEHAVIOR

### Current proposal (problematic):

```
New problem → LLM generates candidates → stored as llm_proposed
→ Matching runs with K=0.5 → users get provisional verdicts
→ Gap signals suppressed → Recommendations suppressed
```

**Problem:** K=0.5 still allows wrong-direction ELO updates. Over 10+ submissions, this accumulates bias.

### Revised cold-start:

```
New problem → LLM generates candidates → stored as llm_proposed
→ Matching runs → match result returned as INFORMATION ONLY
→ ELO: NO UPDATE (K=0) until ≥1 pattern reaches structurally_observed
→ Gap signals: SUPPRESSED
→ Recommendations: SUPPRESSED
→ User display: "Analysis in progress — patterns not yet validated"
```

### When cold-start ends:

The problem transitions out of cold-start when:
- ≥2 submissions from different users detected with the same primary pattern → first pattern promoted to `structurally_observed`

OR

- CSV provides external listing → pattern promoted to `externally_listed`

**Minimum evidence threshold:** At least one pattern must have `structurally_observed` or `externally_listed` status before ELO updates begin.

### What this means for users:

- **During cold start:** Users receive structural analysis (what patterns their code contains) but no skill rating impact. This is honest — the system doesn't know enough to judge.
- **After cold start:** Users receive full analysis with appropriate authority levels.

---

## 6. CONCRETE INDEPENDENCE CRITERIA

### What is available in current data:

| Data | Available? | Independence signal |
|------|-----------|-------------------|
| `user_id` | Yes | Weak (users can copy) |
| `code_text` (1000 chars) | Yes | Moderate (can detect exact/near-exact copies) |
| `detected_pattern` | Yes | None (single pattern, not a fingerprint) |
| `submitted_at` | Yes | Weak (temporal separation doesn't prove independence) |
| Full AST output | **NO** | Would be strong (structural fingerprint) |
| Code hash | **NO** | Would detect exact copies |
| Code similarity score | **NO** | Would measure structural divergence |

### What would need to be stored for reliable independence:

**Minimum viable addition:**
1. Store full AST pattern set (not just primary pattern) per submission
2. Store a code hash (SHA-256 of normalized code) per submission

**With these additions, independence can be estimated as:**
- Different `user_id` + different code hash + different primary pattern = likely independent
- Same code hash = definitely copied (not independent)
- Same `user_id` = not independent (same person)

**Without these additions, independence must be conservatively estimated as:**
- Different `user_id` + submitted >24 hours apart = weakly independent
- Same `user_id` = not independent
- Everything else = unknown

### Concrete independence model (conservative):

```python
def estimate_independence(submission_a, submission_b):
    """Returns confidence that two submissions are independent."""
    if submission_a.user_id == submission_b.user_id:
        return 0.0  # Same person, definitely not independent
    
    if submission_a.code_hash == submission_b.code_hash:
        return 0.0  # Exact copy
    
    # Different users, different code
    confidence = 0.5  # Base: different users is weak signal
    
    # Temporal separation adds signal
    hours_apart = abs(submission_a.timestamp - submission_b.timestamp).hours
    if hours_apart > 24:
        confidence += 0.2
    if hours_apart > 168:  # 1 week
        confidence += 0.1
    
    # Different detected patterns adds signal (different approaches = more independent)
    if submission_a.primary_pattern != submission_b.primary_pattern:
        confidence += 0.1
    
    return min(confidence, 1.0)

# Threshold: confidence >= 0.7 to count as "independent"
```

**This is imperfect but honest about what the data supports.**

---

## 7. PERSISTENCE AND DATA-MODEL IMPLICATIONS

### Mandatory storage additions:

| What to store | Why | Priority |
|--------------|-----|----------|
| Full AST pattern set per submission (JSONB) | Enable clustering without re-analysis | MANDATORY |
| Code hash (SHA-256 of normalized code) | Detect exact copies for independence | MANDATORY |
| Evidence state per pattern in GT | Track what evidence exists | MANDATORY |
| Match result details (not just pass/fail) | Enable audit trail | MANDATORY |

### What the current persistence discards that must be kept:

Currently `run_persistence()` discards:
- Full `ast_output["detected_patterns"]` (all patterns, not just primary)
- Full `match_result` (matched_groups, unmatched_patterns, reasoning_signals)
- All `elo_updates` details
- All `gap_signals` details

**These must be stored** for the evidence model to function. Without them, the system cannot:
- Cluster submissions by structural similarity
- Audit why a particular match result was produced
- Track how evidence states evolved over time

### Schema changes required:

**`submissions` table additions:**
```sql
ALTER TABLE submissions ADD COLUMN detected_patterns_json JSONB;
ALTER TABLE submissions ADD COLUMN match_result_json JSONB;
ALTER TABLE submissions ADD COLUMN code_hash TEXT;
```

**`problem_ground_truth` table additions:**
```sql
ALTER TABLE problem_ground_truth ADD COLUMN solution_groups JSONB;
ALTER TABLE problem_ground_truth ADD COLUMN evidence_states JSONB;
ALTER TABLE problem_ground_truth ADD COLUMN validation_status TEXT DEFAULT 'unobserved';
```

---

## 8. WHAT ASSUMPTIONS REMAIN UNPROVEN

| Assumption | Risk if wrong | How to test |
|-----------|--------------|-------------|
| 2 structurally independent submissions provide meaningful evidence | Overconfident in wrong patterns | Analyze existing submissions for pattern distribution |
| Code hash can reliably detect copies from truncated code_text | Copies counted as independent | Compute hashes on full code vs truncated code |
| K=0.5 for structurally_observed is the right calibration | Too much or too little ELO impact | A/B test with simulated users |
| Cold-start suppression doesn't degrade user experience | New problems feel broken | Monitor user engagement during cold-start period |
| CSV patterns are accurate enough to serve as evidence | Wrong CSV patterns reinforced | Compare CSV against clustering results |
| The two-layer model (structural + algorithmic) is actually implementable | Architecture too complex | Prototype the separation and measure complexity |

---

## 9. REVISED IMPLEMENTATION ORDER

**Phase 0 (mandatory, no architecture change):**
1. Fix `run_persistence()` expected_pattern bug
2. Add `detected_patterns_json` and `code_hash` columns to submissions
3. Store full AST output and code hash per submission

**Phase 1 (evidence model):**
4. Add `solution_groups` and `evidence_states` columns to `problem_ground_truth`
5. Implement LLM candidate generation with multi-group prompt
6. Implement taxonomy + structural validation
7. Store ground truth with evidence states

**Phase 2 (clustering):**
8. Implement batch clustering analysis using stored AST outputs
9. Implement independence estimation using code hash + user_id + temporal separation
10. Implement promotion rules (unobserved → llm_proposed → structurally_observed)

**Phase 3 (downstream safety):**
11. Implement match verdict separation (informative vs authoritative)
12. Implement ELO suppression for unobserved/llm_proposed states
13. Implement gap signal suppression for low-evidence states
14. Implement recommendation suppression for low-evidence states
15. Implement user-facing evidence labels

**Phase 4 (cold-start):**
16. Implement cold-start detection (no structurally_observed patterns)
17. Implement ELO suppression during cold-start
18. Implement "analysis in progress" user display

### What should NOT be implemented:

- Multi-run LLM consistency checks
- Runtime LLM verification of user submissions
- Human review workflows
- Automatic GT correction based on AST output
- Single-source "validation"
- K=1.0 authority for any evidence state below full human verification

---

## 10. SUMMARY OF CHANGES FROM PREVIOUS PROPOSAL

| Aspect | Previous proposal | Revised proposal | Reason |
|--------|------------------|-----------------|--------|
| `structurally_repeated` | K=1.0, "verified approach" | `structurally_observed`, K=0.5, "common approach" | Doesn't prove correctness |
| `externally_supported` | K=0.75 | `externally_listed`, K=0.5 | CSV provenance unknown |
| `llm_suggested` | K=0.5, participates in matching | `llm_proposed`, K=0, informative only | Too unreliable for ELO |
| Cold-start | K=0.5 for all states | K=0 until evidence exists | Wrong-direction updates accumulate |
| Match verdict | Automatic pass/fail | Informative vs authoritative | GT reliability varies |
| Independence | "Different user_id" | user_id + code_hash + temporal separation | Copies must be detected |
| Evidence layers | Single layer | Two layers (structural + algorithmic) | Different questions, different evidence |
| Persistence | Discards full AST output | Stores full AST output + code hash | Required for clustering |

---

*End of Ground Truth Authority Reconciliation*
