# GROUND TRUTH EVIDENCE MODEL — FINAL STRESS TEST

**Status:** Architecture review. No code changes.
**Date:** August 20, 2026
**Basis:** Code audit, AST engine testing, multi-solution experiment, all prior investigations

---

## A. EXECUTIVE VERDICT

**APPROVE WITH CHANGES**

The proposed evidence-based ground-truth architecture is sound in principle but contains three assumptions that must be corrected before implementation:

1. **"cluster_confirmed" overstates what clustering proves.** Repeated AST evidence shows the same *structural pattern* appears in multiple submissions, not that the pattern constitutes a *correct solution strategy*. These are different claims. The state must be renamed and its downstream permissions must be restricted.

2. **The independence model is undefined.** "Two structurally independent submissions" is vague. Without a concrete independence criterion, the system cannot distinguish between 5 users independently discovering the same approach and 5 users copying the same template.

3. **The cold-start model is missing.** The architecture describes what happens as submissions accumulate, but not what happens for a brand-new problem with zero submissions. The LLM candidate with reduced ELO impact is not sufficient — it creates a window where the system confidently judges users against unverified ground truth.

These are fixable. The architecture does not need to be rejected — it needs to be made more honest about what it knows.

---

## B. STRONGEST ASSUMPTIONS THAT COULD BREAK THE ARCHITECTURE

### Assumption 1: "Repeated AST evidence = valid solution approach"

**The claim:** If the AST detects the same pattern in 2+ submissions, that pattern is likely a correct solution strategy.

**The reality (measured):**

```
Code using set() for duplicate detection (NOT hash_map_lookup):
  → AST detects: hash_map_lookup (conf=0.8)

Code using binary search for counting (NOT searching):
  → AST detects: binary_search_standard (conf=1.0)

DFS approach for Valid Parentheses (NOT a stack solution):
  → AST detects: dfs_recursive (conf=0.6)

Buggy code with missing return statement:
  → AST detects: hash_map_lookup (conf=0.8)
```

The AST detects *structural patterns*, not *algorithmic correctness*. Code that uses a dict for any purpose gets `hash_map_lookup`. Code with a while-loop and midpoint gets `binary_search_standard`. Code with recursion gets `dfs_recursive`.

**Risk:** If 5 users all implement the same incorrect-but-structurally-detectable approach, clustering would "confirm" it.

**Severity:** HIGH. This is the foundation of the evidence model.

### Assumption 2: "Different user_id = independent submissions"

**The claim:** Submissions from different users are structurally independent.

**The reality:** Users copy solutions from LeetCode discussion, YouTube tutorials, and AI tools. Two submissions from different users can be character-for-character identical. Even without copying, popular tutorials create convergent implementations.

**Risk:** 10 "independent" submissions could all be copies of the same tutorial solution.

**Severity:** MEDIUM. This inflates confidence in evidence but doesn't create false patterns — it just makes the system overconfident in correct patterns.

### Assumption 3: "AST precision of 99.8% means patterns are trustworthy"

**What was actually measured:** Of 1596 test cases in the adversarial corpus, 1040 were true positives and only 2 were false positives. The AST does not hallucinate patterns that aren't structurally present.

**What was NOT measured:** Whether the detected pattern represents the *correct algorithmic approach for the problem*. The evaluation measured detection accuracy, not algorithmic classification accuracy.

**Risk:** `hash_map_lookup` detected in `find_duplicates()` using a set. The detection is correct (there is a hash-based membership check), but calling it "hash_map_lookup" as an *algorithmic strategy* is misleading.

**Severity:** HIGH. Precision measures detection accuracy, not classification accuracy.

### Assumption 4: "Clustering all submissions (not just FULL_MATCH) removes circularity"

**The claim:** Because clustering uses AST analysis of code, not the verdict, it's independent of ground truth.

**The partial truth:** The clustering itself is independent. But user *behavior* is not independent of ground truth. If the GT says "this is a hash_map_lookup problem," users will implement hash_map_lookup solutions. The clustering will then see many hash_map_lookup submissions and confirm it.

**Risk:** The GT shapes user behavior, which shapes the evidence, which confirms the GT. This is a slower circularity than FULL_MATCH, but it exists.

**Severity:** MEDIUM. Self-correcting over time as new users solve the problem independently, but creates a bias window.

### Assumption 5: "LLM candidates with reduced ELO is safe during cold start"

**The claim:** New problems start with LLM-generated ground truth and reduced K-factor.

**The problem:** Even with reduced K-factor, the system is still judging users against potentially wrong ground truth. If the LLM says "binary_search_standard" for a DP problem, users who implement DP will get NO_MATCH and reduced ELO for binary_search.

**Severity:** HIGH during cold start. The system actively penalizes correct behavior.

---

## C. EVIDENCE CAPABILITY MATRIX

| Evidence source | Independence from current GT | What it supports | What it cannot prove | Main failure modes | Reliability |
|----------------|------------------------------|-----------------|---------------------|-------------------|-------------|
| **AST clustering** (≥2 submissions with same pattern fingerprint) | High (analyzes code, not verdict) | Same structural pattern appears in multiple real implementations | That the pattern is algorithmically correct for this problem; that different implementations are independent; that the implementation is correct | Same incorrect approach clustered; copied code counted as independent; incidental patterns detected | Medium-High (limited by AST precision boundary) |
| **CSV pattern column** (300 problems) | High (created separately from LLM) | A human or prior process assigned this pattern | That the assignment is correct; OR vs AND relationships; that the pattern is optimal | CSV may contain errors; flat list loses group structure; may be LLM-generated itself | Medium |
| **LLM candidate generation** | Low (same model that may be wrong) | Pattern is in the vocabulary; structure is valid | Algorithmic correctness; completeness of solution coverage; correct group structure | Hallucination (46/42 problems in experiment); inconsistency (50% across runs); taxonomy violations | Low |
| **Problem metadata** (title, difficulty, topics) | High (independent) | Loose correlation between topic tags and patterns | Specific pattern assignment; algorithmic approach | Tags are too coarse (e.g., "Array" doesn't distinguish hash from sort) | Low |
| **Constraint analysis** (input size, time limits) | High (independent) | Eliminates infeasible approaches; confirms feasible ones | Specific algorithm choice; optimal approach | Constraints are often too loose to distinguish between O(n log n) approaches | Low-Medium |
| **Test cases** (input/output pairs) | High (independent) | Code that passes test cases is likely correct | That the approach is optimal; that the pattern is the primary strategy | Tests don't reveal the algorithm; partial solutions can pass some tests | Low |
| **FULL_MATCH submissions** | LOW (depends on current GT) | Code that matched the current GT | That the GT is correct; that the match is algorithmically meaningful | Circular — validates GT against itself | Low (circular) |
| **GraphQL problem data** (description, hints) | High (independent) | Problem context for LLM generation | Algorithmic correctness; solution strategies | Hints don't always reveal the intended approach | Low-Medium |

---

## D. FEEDBACK-LOOP ANALYSIS

### Loop 1: GT → Matching → Verdict → Submission → Clustering → GT evidence

```
GT: ["hash_map_lookup"]
  ↓
User submits hash map solution → FULL_MATCH
  ↓
Submission stored
  ↓
Clustering sees hash_map_lookup in submission
  ↓
Reinforces hash_map_lookup as evidence
```

**Circularity level:** MEDIUM. The clustering is based on code analysis (independent of GT), but user *choice* to implement hash_map_lookup is influenced by GT (or by learning platform conventions). This is a soft circularity — it reinforces existing patterns but doesn't create new ones.

**Mitigation:** Clustering sees ALL submissions, including those from users who solved the problem before GT existed (if any). Over time, independent evidence dominates.

### Loop 2: GT → ELO → Recommendations → User behavior → Submissions → Evidence

```
GT: ["hash_map_lookup"]
  ↓
User gets FULL_MATCH → ELO increases for hash_map_lookup
  ↓
Recommendation suggests more hash_map_lookup problems
  ↓
User practices hash_map_lookup more
  ↓
User submits more hash_map_lookup solutions
  ↓
Clustering sees many hash_map_lookup submissions
  ↓
hash_map_lookup confirmed
```

**Circularity level:** HIGH if GT is wrong. The recommendation system amplifies the initial GT signal. If GT incorrectly labels a problem as hash_map_lookup, the system will push users toward hash_map_lock solutions, creating evidence that confirms the wrong GT.

**Mitigation:** The recommendation engine uses gap signals (patterns the user is weak at). If a user is strong at hash_map_lookup but weak at other patterns, the recommendation will push toward other patterns, not more hash_map_lookup. This partially breaks the loop.

### Loop 3: AST weakness → wrong detection → wrong clustering → wrong GT

```
AST consistently misses bfs_level_order in while-loop BFS
  ↓
All BFS submissions detected as something else
  ↓
BFS cluster never forms
  ↓
BFS never confirmed as valid approach
  ↓
Users who implement BFS correctly get no credit
```

**Circularity level:** This is not circular — it's a systematic blind spot. The AST's ~84% recall means some patterns will be missed. This is a known limitation, not a feedback loop.

**Mitigation:** LLM candidates remain as unverified evidence even when clustering doesn't confirm them. Users still get partial credit through the matching engine.

### Loop 4: CSV patterns → GT generation → Submissions → Clustering → CSV "confirmation"

```
CSV: ["hash_map_lookup", "two_pointers_opposite"]
  ↓
LLM generates GT including hash_map_lookup (sees CSV influence?)
  ↓
No — CSV is not passed to the LLM prompt
  ↓
LLM generates independently
  ↓
But CSV and LLM may agree by coincidence or shared training data
  ↓
Clustering confirms one of them
  ↓
System appears to have multiple confirming sources
```

**Circularity level:** LOW. The CSV is not passed to the LLM, so they are independent. But they may share biases from their respective creation processes.

**Mitigation:** Treat CSV and LLM as independent weak signals. Neither is authoritative alone.

### The critical loop that IS dangerous:

```
Wrong GT → Users implement wrong approach → Clustering confirms wrong approach → GT "validated"
```

This loop is slow (requires multiple users) but self-reinforcing. Once a wrong GT is "confirmed" by clustering, it becomes very hard to correct.

**Breaking mechanism:** The system must detect when a NEW cluster appears that contradicts existing evidence. If 3 users submit DFS solutions and 2 users submit BFS solutions, both clusters should be presented as valid approaches, even if the original GT only listed DFS. The system must be able to ADD evidence, not just confirm it.

---

## E. REVISED EVIDENCE MODEL

### State definitions (honest terminology):

| State | Exact meaning | What it guarantees | What it does NOT guarantee |
|-------|--------------|-------------------|---------------------------|
| **structurally_repeated** | ≥2 submissions from different users detected with the same primary pattern by the AST engine | The structural pattern is present in multiple real codebases | That the pattern is algorithmically correct; that the implementations are independent; that the implementation is correct; that the pattern is the primary strategy |
| **externally_supported** | Pattern appears in the CSV `pattern` column for this problem | A prior process assigned this pattern | That the assignment is correct; that the pattern is optimal; OR vs AND relationships |
| **llm_suggested** | Pattern from LLM output, passed taxonomy + structural validation | Pattern is valid vocabulary; structure is sane | Algorithmic correctness; completeness; correct group structure |
| **unverified** | No evidence from any source | Nothing beyond the problem existing | Anything |
| **contradicted** | Multiple independent sources disagree on the pattern for this problem | The pattern assignment is uncertain | Which source is correct |

### Key change from previous proposal:

**"structurally_repeated" instead of "cluster_confirmed"**

The word "confirmed" implies correctness. The word "repeated" accurately describes what was observed: the same structural pattern appeared multiple times. This is evidence, not proof.

### State granularity:

States apply to **individual patterns within solution groups**, not to entire problems or groups.

Example:
```
Problem: "Two Sum"
  Group A: [
    hash_map_lookup (structurally_repeated — 8 users)
  ]
  Group B: [
    two_pointers_opposite (externally_supported — in CSV)
  ]
  Group C: [
    sorting (llm_suggested — LLM proposed, no other evidence)
  ]
```

### Promotion rules:

| From | To | Required evidence |
|------|----|-------------------|
| unverified | llm_suggested | LLM output passes taxonomy + structural validation |
| unverified | externally_supported | Pattern appears in CSV for this problem |
| llm_suggested | structurally_repeated | ≥2 submissions from different users detected with this pattern |
| externally_supported | structurally_repeated | ≥2 submissions from different users detected with this pattern |
| any | contradicted | Two or more independent sources disagree on pattern assignment |

### Demotion rules:

| From | To | Trigger |
|------|----|---------|
| structurally_repeated | contradicted | A new cluster appears with a different pattern for the same approach |
| llm_suggested | contradicted | Clustering shows a different dominant pattern |
| any | unverified | Evidence source retracted (e.g., CSV corrected) |

**No automatic demotion from structurally_repeated.** Once structural evidence exists, it persists until contradicted by new evidence. This prevents oscillation.

---

## F. DOWNSTREAM DECISION MATRIX

| Evidence state | Participate in matching | Affect ELO | Generate gap signals | Influence recommendations | Display to users |
|---------------|------------------------|------------|---------------------|--------------------------|-----------------|
| **structurally_repeated** | Yes | Yes (K=1.0) | Yes | Yes | Yes — show as "verified approach" |
| **externally_supported** | Yes | Yes (K=0.75) | Yes (flagged as "externally sourced") | Yes (lower priority) | Yes — show as "likely approach" |
| **llm_suggested** | Yes | Yes (K=0.5) | No (too unreliable for gap signals) | No (don't recommend based on unverified GT) | Yes — show as "possible approach" |
| **unverified** | Yes | Yes (K=0.25) | No | No | No — don't display unverified patterns |
| **contradicted** | Yes (all candidate patterns) | No (K=0) | No | No | Show as "uncertain — multiple approaches possible" |

### Key design decisions:

1. **Matching always runs.** Even unverified patterns participate in matching. The user should know if their code matches *any* candidate approach. But the *verdict* should reflect confidence.

2. **ELO is always updated, but scaled by confidence.** K=0 means no ELO change, which is different from K=0.25 (minimal change). The "contradicted" state uses K=0 because the system genuinely doesn't know which pattern is correct.

3. **Gap signals require structural evidence.** Telling a user "you're weak at X" requires confidence that X is actually relevant. LLM suggestions are too unreliable for this.

4. **Recommendations require structural evidence.** Don't recommend problems based on unverified GT. Wait for at least `externally_supported` status.

5. **User display is honest.** Show "verified approach" for structurally_repeated, "likely approach" for externally_supported, "possible approach" for llm_suggested. Don't hide uncertainty from the user.

---

## G. COLD-START STRATEGY

### New problem with zero submissions:

```
Problem added to system
  ↓
Step 1: LLM generates candidate solution groups
  ↓
Step 2: Taxonomy + structural validation
  ↓
Step 3: Store as "llm_suggested" status
  ↓
Step 4: MatchingEngine uses groups (all status levels participate)
  ↓
Step 5: ELO updates use K=0.5 (reduced but not zero)
  ↓
Step 6: Gap signals: SUPPRESSED (too unreliable)
  ↓
Step 7: Recommendations: SUPPRESSED (don't recommend based on unverified GT)
  ↓
Step 8: User-facing display: show "analysis in progress — patterns not yet verified"
```

### What this means for users:

- If a user submits code and the LLM's ground truth is correct: they get FULL_MATCH, reduced ELO update, no gap signals, no recommendation impact.
- If a user submits code and the LLM's ground truth is wrong: they get NO_MATCH or wrong FULL_MATCH, reduced ELO update (mitigated by K=0.5), no gap signals (mitigated by suppression), no recommendation impact (mitigated by suppression).

**The cold-start penalty is asymmetric:** Users on new problems get less benefit from correct analysis (reduced ELO) but are also less harmed by incorrect analysis (reduced ELO + suppressed gaps/recommendations). This is the correct tradeoff.

### When cold-start ends:

The problem transitions out of cold-start when:
- ≥2 submissions from different users are detected with the same primary pattern → first pattern promoted to `structurally_repeated`
- OR the CSV provides external support → pattern promoted to `externally_supported`

**Minimum submissions for first promotion:** 2 (from different users, different time periods, with code similarity below a threshold).

---

## H. WHAT AST PRECISION ACTUALLY ALLOWS US TO CLAIM

### Precise definition of the 99.8% precision measurement:

The Phase-0 evaluation measured: "When the AST engine reports that pattern X is present in code, what fraction of the time is pattern X actually structurally present?"

Answer: 99.8%. The AST almost never reports a pattern that isn't structurally detectable in the code.

### What this allows us to claim:

- "The AST correctly identifies structural patterns in code" ✓
- "If the AST says hash_map_lookup is present, there is a hash-based membership check in the code" ✓
- "If the AST says binary_search_standard is present, there is a binary search structure in the code" ✓

### What this does NOT allow us to claim:

- "hash_map_lookup is the correct algorithmic strategy for this problem" ✗
- "The user implemented the intended solution" ✗
- "The pattern represents an optimal approach" ✗
- "The pattern is the primary algorithmic technique" ✗

### The precision-relevance gap:

The AST can detect that code *contains* a binary search structure. It cannot determine whether binary search is the *intended or correct* approach for the problem. A user might use binary search as a subroutine in a larger algorithm, or might use it for an auxiliary purpose.

**This is why clustering alone cannot prove algorithmic correctness.** Clustering shows that multiple users implemented the same *structural pattern*. It does not show that the pattern is the *correct solution strategy*.

---

## I. UNPROVEN ASSUMPTIONS REQUIRING EMPIRICAL TESTING

Before implementation, these assumptions need measurement:

| Assumption | How to test | Risk if wrong |
|-----------|-------------|---------------|
| ≥2 submissions from different users with same pattern = genuine evidence | Analyze existing submissions (if any) for pattern distribution | Overconfident in wrong patterns |
| Code similarity below threshold = independent | Compute code similarity (token overlap, AST structure) for submission pairs | Copy-paste counted as independent |
| Cold-start K=0.5 is sufficient reduction | Compare ELO stability for new vs mature problems | Wrong GT causes excessive ELO noise |
| CSV patterns are accurate enough to serve as evidence | Compare CSV patterns against clustering results for problems with many submissions | CSV errors reinforced |
| LLM candidates that are never confirmed should be demoted | Track unconfirmed candidates over time | Stale wrong patterns persist |
| "contradicted" state with K=0 prevents ELO corruption | Simulate conflicting evidence scenarios | User scoring becomes meaningless |

---

## J. FINAL RECOMMENDATION

### Should we proceed to implementation?

**YES, with the following corrections:**

1. Rename "cluster_confirmed" to "structurally_repeated" (honest terminology)
2. Define a concrete independence model (different user + code similarity threshold)
3. Implement cold-start suppression for gap signals and recommendations
4. Do NOT display unverified patterns to users as "expected solutions"
5. Fix the persistence bug (expected_pattern must use matched group)
6. Add submission clustering infrastructure as a separate batch process

### Exact implementation order:

**Phase 0 (mandatory, no architecture change):**
1. Fix `run_persistence()` expected_pattern bug
2. Add `solution_groups` and `validation_status` columns to `problem_ground_truth`

**Phase 1 (evidence model):**
3. Implement LLM candidate generation with multi-group prompt
4. Implement taxonomy + structural validation
5. Implement CSV cross-reference validation
6. Store ground truth with evidence states

**Phase 2 (clustering):**
7. Store full AST pattern set per submission (not just primary pattern)
8. Implement batch clustering analysis
9. Implement promotion rules (unverified → llm_suggested → structurally_repeated)

**Phase 3 (downstream safety):**
10. Implement ELO K-factor scaling by evidence state
11. Implement gap signal suppression for low-evidence states
12. Implement recommendation suppression for low-evidence states
13. Implement user-facing evidence labels

### What should NOT be implemented:

- Multi-run LLM consistency checks
- Runtime LLM verification of user submissions
- Human review workflows
- Automatic GT correction based on AST output
- Single-source "validation" (no evidence source alone is sufficient)

### What remains uncertain:

- Whether 2 submissions is sufficient for structural evidence (may need 3+)
- Whether code similarity can be reliably computed from truncated code_text (1000 chars)
- Whether the cold-start window (0-2 submissions) creates unacceptable user experience
- Whether CSV patterns are accurate enough to serve as independent evidence

These should be measured during implementation, not assumed.

---

*End of Ground Truth Evidence Model Stress Test*
