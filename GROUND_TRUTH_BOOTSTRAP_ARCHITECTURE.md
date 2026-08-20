# GROUND TRUTH BOOTSTRAP ARCHITECTURE — INVESTIGATION

**Status:** Architecture investigation. No code changes.
**Date:** August 20, 2026
**Basis:** Code audit, multi-solution feasibility experiment, Phase-0 adversarial evaluation

---

## 1. CURRENT EVIDENCE AVAILABLE IN PATHFORGE

### Per-Problem Data

| Source | What it contains | Evidence quality | Circular with current GT? |
|--------|-----------------|-----------------|--------------------------|
| **Problem title** | Human-readable name (e.g., "Two Sum") | Weak — correlates with patterns but doesn't prove them | No |
| **Problem difficulty** | Easy/Medium/Hard | Weak — no direct pattern correlation | No |
| **Problem topics/tags** | LeetCode tags (Array, Hash Table, Tree, etc.) | Moderate — tags correlate with pattern families | No |
| **Problem description** | Full problem statement in HTML/markdown | Moderate — contains algorithmic hints | No (but LLM sees this too) |
| **Example test cases** | Input/output pairs from LeetCode | Weak — test cases don't reveal the algorithm | No |
| **Stored test cases** | Additional test cases from LeetCode | Weak — same as above | No |
| **Problem link** | LeetCode URL | None directly | No |
| **CSV `pattern` column** | Manually assigned pattern list (300 problems) | Moderate — but flat list, no OR/AND, may have errors | Potentially (if CSV was LLM-generated) |
| **`problems.pattern` column** | Same CSV data stored in database | Same as CSV | Same |
| **`problem_ground_truth` table** | LLM-generated patterns + confidence | THIS IS WHAT WE'RE VALIDATING | Yes — this IS the ground truth |
| **User submissions** | Code, verdict, detected pattern, confidence | Valuable — real implementations | Partially (verdict depends on current GT) |

### Critical observation:

The `problems.pattern` column (from CSV) and the `problem_ground_truth.patterns` column (from LLM) are **independent sources**. The CSV was created separately from the LLM generation. They can serve as cross-validation signals for each other.

### Submission data available:

| Column | What it stores | Usefulness for evidence |
|--------|---------------|------------------------|
| `code_text` | Full submission code (truncated to 1000 chars) | HIGH — actual implementation |
| `verdict` | pass/fail/error/tle | Moderate — but verdict depends on current GT |
| `detected_pattern` | Primary detected pattern | Moderate — but only stores ONE pattern |
| `detected_confidence` | Confidence of primary pattern | Low — only for one pattern |
| `expected_pattern` | First pattern from first GT group | Low — depends on current GT |
| `topic` | primary_pattern or expected_pattern | Derived |
| `gap_identified` | Whether unmatched patterns exist | Derived from current GT |

**Key limitation:** The submissions table stores only the `detected_pattern` (single pattern), not the full AST output. To cluster submissions, we would need to either re-analyze stored code or add a column for the full pattern set.

---

## 2. BOOTSTRAP WITHOUT FULL_MATCH CIRCULARITY

### The circularity problem:

Current flow:
```
Ground truth (LLM) → MatchingEngine → verdict (pass/fail) → submission stored
                                                      ↓
                                              "pass" = FULL_MATCH or PARTIAL_MATCH
                                                      ↓
                                              Could be used as reference implementation
                                                      ↓
                                              But reference depends on the GT we're validating
```

If we use "pass" verdicts as reference implementations, we are validating GT against itself. A wrong GT that consistently produces "pass" for a specific pattern would reinforce itself.

### Can we break the circularity?

**Yes, using one of these approaches:**

#### Approach A: Structural clustering of submissions (independent of verdict)

Instead of using verdict to select reference implementations, cluster ALL submissions for a problem by their AST-detected pattern fingerprint:

```
All submissions for Problem X
  ↓
Run AST engine on each submission's code
  ↓
Extract pattern fingerprint: {pattern_id: confidence} for each
  ↓
Cluster by fingerprint similarity
  ↓
Dominant clusters = candidate solution groups
```

**This is NOT circular because:**
- We are not using the verdict or ground truth to select submissions
- We are using the AST engine's independent analysis of each submission's code
- Multiple structurally independent implementations of the same approach form a cluster
- The cluster represents a real solution approach that actual users implemented

**The circularity risk is reduced to:**
- The AST engine's own weaknesses (it may misclassify some implementations)
- But this is a different kind of circularity — it's the AST's limitations, not the GT's

#### Approach B: Use verdict as weak evidence, not authoritative

Treat "pass" as weak evidence that the submission implements *some* valid approach, but don't assume we know *which* approach. The clustering approach (A) determines the approach independently.

#### Approach C: Use code similarity directly (no AST)

Cluster submissions by code similarity (e.g., token overlap, AST structure similarity) without relying on pattern detection. This is fully independent of both GT and AST.

**Comparison:**

| Approach | Independence from GT | Independence from AST | Complexity | Reliability |
|----------|---------------------|----------------------|------------|-------------|
| A: AST clustering | High | Low (depends on AST) | Medium | Medium (limited by AST recall) |
| B: Verdict as weak evidence | Low (verdict depends on GT) | Low | Low | Low (circular) |
| C: Code similarity clustering | High | High | High | High (but requires implementation) |

**Recommendation:** Approach A (AST clustering) is the most practical. It leverages the AST engine's existing high precision (99.8%) while avoiding GT circularity. The AST's recall limitation means some submissions will be misclustered, but this is a manageable weakness.

---

## 3. REFERENCE IMPLEMENTATION OPTIONS

### Option 1: LLM-Generated Reference Implementations

**Process:** Ask the LLM to generate a correct solution for the problem. Run AST on it. Use detected patterns as ground truth.

**Reliability:** Low. The LLM may generate incorrect solutions. The AST would detect patterns in incorrect code.

**Circularity:** Medium. The LLM generates both the solution and the ground truth. If the LLM misunderstands the problem, both will be wrong.

**Implementation complexity:** Low (one additional LLM call per problem).

**Free model suitability:** Poor. The same free model that generates unreliable ground truth would generate unreliable reference implementations.

**Verdict:** NOT RECOMMENDED. This doesn't solve the reliability problem.

### Option 2: User Submissions (All, Clustered)

**Process:** Collect all submissions for a problem. Run AST on each. Cluster by detected patterns. Dominant clusters become candidate solution groups.

**Reliability:** Medium-High. Multiple independent implementations of the same approach provide strong evidence. The AST's high precision (99.8%) means detected patterns are almost certainly present.

**Circularity:** Low. The clustering is independent of GT. The AST analysis is independent of GT.

**Implementation complexity:** Medium (need clustering logic, need to re-analyze stored code).

**Free model suitability:** Excellent (no LLM needed).

**Verdict:** RECOMMENDED as primary evidence source.

### Option 3: User Submissions (FULL_MATCH Only)

**Process:** Use only submissions with FULL_MATCH verdict as reference implementations.

**Reliability:** Medium. FULL_MATCH means the submission matched the current GT, which may be wrong.

**Circularity:** High. FULL_MATCH depends on GT. Using it as evidence for GT is circular.

**Implementation complexity:** Low (already available).

**Free model suitability:** Excellent.

**Verdict:** NOT RECOMMENDED as primary source. Use as weak evidence only.

### Option 4: External Canonical Solutions

**Process:** Retrieve editorial solutions from LeetCode or other sources.

**Reliability:** High (editorial solutions are authoritative).

**Circularity:** None (completely external).

**Implementation complexity:** High (need to scrape/cache external solutions, licensing concerns).

**Free model suitability:** Excellent (no LLM needed, but requires external data access).

**Verdict:** IDEAL but impractical without external data access. LeetCode GraphQL does not provide full editorial solutions.

### Option 5: Problem Test Cases + Constraints

**Process:** Analyze problem constraints (input size, data types, time limits) to infer which algorithms are feasible.

**Reliability:** Low-Medium. Constraints can eliminate some approaches but cannot confirm others.

**Circularity:** None.

**Implementation complexity:** High (requires constraint parsing and algorithm feasibility analysis).

**Free model suitability:** Moderate (could use LLM for constraint analysis, but adds cost).

**Verdict:** USEFUL as supplementary evidence, not primary.

### Recommended combination:

**Primary:** Option 2 (user submission clustering)
**Supplementary:** Option 5 (constraint analysis) + CSV pattern cross-reference
**Not used:** Options 1, 3 (circular or unreliable)

---

## 4. PROPOSED EVIDENCE HIERARCHY

Based on the investigation, the appropriate evidence states are:

### State Definitions

| State | Entry criteria | What it guarantees | How it's determined |
|-------|---------------|-------------------|---------------------|
| **cluster_confirmed** | ≥2 structurally independent submissions detected with the same pattern set by AST | The pattern set is present in multiple real implementations | AST clustering of all submissions for the problem |
| **csv_confirmed** | Pattern appears in the CSV `pattern` column for this problem | A human (or prior process) assigned this pattern | CSV lookup |
| **llm_candidate** | Pattern from LLM output, passed taxonomy + structural validation | Pattern is valid vocabulary; structure is sane | LLM generation + deterministic validation |
| **unverified** | No evidence from any source | Nothing beyond vocabulary validity | Default state |
| **rejected** | Structural failure, taxonomy violation, empty groups | Output is invalid | Deterministic validation |

### State transitions:

```
unverified
  ↓ (LLM generates candidate)
llm_candidate
  ↓ (CSV confirms pattern)
csv_confirmed
  ↓ (≥2 independent submissions confirm pattern set)
cluster_confirmed
```

A pattern can move UP the hierarchy as evidence accumulates. It should not move DOWN except through explicit human review or evidence contradiction.

### Important: States apply to PATTERNS, not problems

A single problem may have multiple solution groups, each at a different state:
- Group A (DFS): cluster_confirmed (2 users submitted DFS solutions)
- Group B (BFS): llm_candidate (LLM suggested BFS, no user submissions yet)
- Group C (Sorting): unverified (LLM suggested but no other evidence)

This is more accurate than a single problem-level state.

---

## 5. CIRCULAR DEPENDENCY STRESS TEST

### Loop 1: GT → Submission → Evidence → GT update

```
Ground truth: ["hash_map_lookup"]
  ↓
User submits code → AST detects ["hash_map_lookup"] → FULL_MATCH
  ↓
Submission stored with verdict="pass"
  ↓
Submission used as evidence for "hash_map_lookup" being correct
  ↓
This reinforces the ground truth
```

**Is this circular?** Yes. But the circularity is broken if we use CLUSTERING instead of VERDICT:
- The clustering is based on AST analysis of the CODE, not the verdict
- Multiple users independently implementing hash_map_lookup provides genuine evidence
- The fact that they got FULL_MATCH is secondary — the evidence is in the code itself

**Risk:** If the ground truth is wrong (e.g., should be "two_pointers_opposite" not "hash_map_lookup"), and users implement hash_map_lookup because the GT told them to, then the clustering would confirm the wrong pattern.

**Mitigation:** This risk exists but is self-limiting:
- Users who implement the correct approach (two_pointers_opposite) will also be clustered
- Their cluster will appear alongside the hash_map_lookup cluster
- The system will eventually see both clusters and can present both as valid approaches
- The GT can be updated to include both approaches

### Loop 2: GT → ELO → Recommendations → User behavior → Submissions → Evidence

```
Ground truth: ["hash_map_lookup"]
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
This reinforces hash_map_lookup as the dominant approach
```

**Is this circular?** Yes, but this is the INTENDED behavior. The system is supposed to reinforce correct learning. The risk is when the initial GT is wrong.

**Mitigation:** The clustering approach sees ALL submissions, not just those from users who followed recommendations. New users who solve the problem independently will provide unbiased evidence. Over time, the independent evidence dominates the recommendation-influenced evidence.

### Loop 3: AST weakness → wrong detection → wrong clustering → wrong GT

```
AST consistently misses bfs_level_order in while-loop BFS implementations
  ↓
All BFS submissions are misclustered (detected as something else)
  ↓
BFS cluster never forms
  ↓
BFS is never confirmed as a valid approach
  ↓
Users who implement BFS correctly get no credit
```

**Is this circular?** This is a different kind of problem — AST weakness creating a blind spot in evidence collection.

**Mitigation:** This is a known limitation. The AST's ~84% recall means some patterns will be missed. This is acceptable because:
- The missed patterns remain as LLM candidates (not rejected)
- As AST improves (Experiment 2A/2B/2C), more patterns will be detected
- The system degrades gracefully — missed patterns get lower confidence, not zero

### Loop 4: CSV → GT → Submissions → Clustering → CSV contradiction

```
CSV says: ["hash_map_lookup"]
LLM says: ["hash_map_lookup", "two_pointers_opposite"]
Clustering shows: {"hash_map_lookup": 5 submissions, "two_pointers_opposite": 3 submissions}
```

**Is this circular?** No. The CSV and LLM are independent sources. The clustering provides independent evidence. If CSV and clustering agree, that's strong confirmation. If they disagree, that's useful information.

---

## 6. PERSISTENCE BUG ANALYSIS

### Current behavior (verified from code):

**File:** `pathforge/services/persistence.py`, function `run_persistence()`

```python
expected_pattern = ""
if groups:
    for g in groups:
        patterns = g.get("patterns", [])
        if patterns:
            expected_pattern = patterns[0]
            break
```

This extracts `patterns[0]` from the FIRST group, regardless of which group actually matched.

### How this manifests:

With the current single-group architecture, there's only one group, so this always picks the first pattern from that group. This is a latent bug that becomes visible with multiple groups.

**Example with multiple groups:**
```
Group 0: ["binary_search_answer"]  (matched by user)
Group 1: ["dp_1d_forward"]         (not matched)
```

Current behavior: `expected_pattern = "binary_search_answer"` (correct by accident, since it's the first pattern of the first group)

But if groups are ordered differently:
```
Group 0: ["dp_1d_forward"]         (not matched)
Group 1: ["binary_search_answer"]  (matched by user)
```

Current behavior: `expected_pattern = "dp_1d_forward"` (WRONG — user matched group 1, not group 0)

### Affected downstream systems:

1. **`submissions.expected_pattern`** — stores the wrong expected pattern
2. **`topic_profiles`** — `pattern_match_count` compares `detected_pattern == expected_pattern`, which would be wrong
3. **`gap_signals`** — gap detection compares detected patterns against expected patterns
4. **Recommendations** — use topic profile data which depends on correct expected_pattern

### What would need to change conceptually:

The `expected_pattern` should be derived from the MATCHED group, not the first group. The matching engine already returns `matched_groups` (list of indices). The persistence code should use this:

```python
# Correct approach (conceptual):
matched_indices = match_result.get("matched_groups", [])
if matched_indices and groups:
    matched_group = groups[matched_indices[0]]
    expected_pattern = matched_group.get("patterns", [""])[0]
else:
    expected_pattern = ""
```

This is a real bug that must be fixed before multi-group support is implemented.

---

## 7. RECOMMENDED ARCHITECTURE

### Core principle: Evidence-based ground truth with honest confidence

Ground truth should be built from multiple independent evidence sources, each contributing to a confidence level. No single source is authoritative.

### Evidence sources (ordered by independence from current GT):

1. **AST clustering of user submissions** — most independent, most reliable
2. **CSV pattern cross-reference** — independent (created separately from LLM)
3. **Constraint analysis** — independent (based on problem properties)
4. **LLM candidate generation** — least independent (same model that may be wrong)

### Architecture:

```
Problem enters system
  ↓
Step 1: LLM generates candidate solution groups (offline, once)
  ↓
Step 2: Deterministic validation (taxonomy, structure)
  ↓
Step 3: Store as "llm_candidate" status
  ↓
Step 4: Over time, user submissions accumulate
  ↓
Step 5: Periodic clustering analysis (offline, batch)
  ↓
Step 6: Clusters that match LLM candidates → upgrade to "cluster_confirmed"
  ↓
Step 7: Clusters that don't match LLM candidates → add as new groups
  ↓
Step 8: MatchingEngine uses all confirmed + candidate groups
  ↓
Step 9: ELO/gap/recommendation behavior scaled by evidence level
```

### The bootstrap sequence:

**Phase 1 (initial):**
- LLM generates candidates → stored as "llm_candidate"
- No user submissions yet
- ELO uses reduced K-factor (0.5×) for all patterns
- Gap detection active but flagged as "uncertain"

**Phase 2 (after first FULL_MATCH submissions):**
- User submissions with "pass" verdict are analyzed
- AST clustering begins to form evidence groups
- Patterns confirmed by ≥2 independent submissions → "cluster_confirmed"
- ELO uses standard K-factor for confirmed patterns

**Phase 3 (mature):**
- Multiple confirmed solution groups per problem
- Recommendations based on confirmed patterns
- LLM candidates that were never confirmed can be demoted or removed

---

## 8. REJECTED ARCHITECTURES AND WHY

### Rejected: "LLM output is validated by taxonomy checks"

**Why:** Taxonomy validation proves the pattern *exists*, not that it's *correct*. `binary_search_standard` passes taxonomy validation for "Number of Islands" but is algorithmically wrong.

### Rejected: "FULL_MATCH submissions are reference implementations"

**Why:** Circular. FULL_MATCH depends on the GT we're trying to validate. Using it as evidence for GT is self-reinforcing.

### Rejected: "3-run LLM consistency = validation"

**Why:** Consistent wrong answers exist. The free model consistently returns `dfs_recursive` for "Valid Parentheses" across all 3 trials. Consistency is not correctness.

### Rejected: "LLM generates reference solutions"

**Why:** The same unreliable model generates both the solution and the ground truth. If the LLM misunderstands the problem, both will be wrong.

### Rejected: "AST validates LLM ground truth against reference implementations"

**Why:** The AST has ~84% recall. It would miss patterns in references and incorrectly dispute correct GT. This creates the circular reasoning the architecture must avoid.

### Rejected: "Human review of all ground truth"

**Why:** Not scalable. No human review team available. The system must operate autonomously.

---

## 9. REQUIRED CHANGES

### Mandatory (before multi-group support):

1. **Fix `run_persistence()` expected_pattern bug** — must use matched group, not first group
2. **Add `solution_groups` column to `problem_ground_truth`** — store structured groups
3. **Add `validation_status` column** — track evidence level per pattern
4. **Modify `_load_ground_truth()`** — read from new columns, fall back to flat patterns
5. **Modify `ground_truth_builder.py`** — produce structured groups from LLM output

### Optional (improve evidence quality):

6. **Store full AST output per submission** — enable clustering without re-analysis
7. **Add clustering analysis pipeline** — batch process submissions to identify solution groups
8. **Add CSV cross-reference validation** — compare LLM output against CSV patterns
9. **Add constraint analysis** — use problem properties to validate pattern plausibility

### Experimental (measure effectiveness):

10. **Add evaluation framework** — measure whether evidence-based GT improves accuracy
11. **Add evidence audit trail** — track how each pattern's state changed over time
12. **Add recommendation impact measurement** — track whether evidence-based GT improves learning outcomes

---

## 10. RISKS AND FAILURE MODES

### Risk 1: Insufficient submissions for clustering

If a problem has few submissions (<5), clustering cannot form reliable evidence groups. The system would remain in "llm_candidate" state indefinitely.

**Mitigation:** Set a minimum submission threshold (e.g., 5 submissions) before clustering is attempted. Below threshold, use LLM candidates with reduced confidence.

### Risk 2: AST clustering creates spurious groups

The AST's ~84% recall means some submissions will be misclustered. Two submissions implementing the same approach might be placed in different clusters if the AST detects different patterns.

**Mitigation:** Use pattern overlap (Jaccard similarity) for clustering, not exact match. Allow partial overlaps to form clusters.

### Risk 3: CSV patterns are wrong

If the CSV contains incorrect pattern assignments, cross-referencing against it would reinforce errors.

**Mitigation:** Use CSV as weak evidence only (one of multiple sources). Never treat CSV as authoritative. Flag disagreements between CSV and clustering for review.

### Risk 4: LLM candidates that are never confirmed

If the LLM suggests a pattern that no user ever implements, it remains as "llm_candidate" indefinitely. This could cause false positives if the matching engine treats it as valid.

**Mitigation:** Demote unconfirmed LLM candidates after a threshold (e.g., 20 submissions with no cluster confirmation). Or require ≥1 submission with the pattern detected before it affects scoring.

### Risk 5: ELO instability during bootstrap

During Phase 1 (no confirmed patterns), all ELO updates use reduced K-factor. This may slow skill modeling to the point where recommendations are unhelpful.

**Mitigation:** Monitor the distribution of evidence states over time. If >80% of problems remain "llm_candidate", consider using CSV-confirmed patterns as an additional evidence source.

### Risk 6: Recommendation feedback loop

If recommendations suggest problems based on unconfirmed patterns, users may practice patterns that aren't actually valid. Their submissions would then reinforce those patterns through clustering.

**Mitigation:** Only recommend problems with at least one "cluster_confirmed" pattern. This ensures users practice patterns that have been validated by real implementations.

---

*End of Ground Truth Bootstrap Architecture Investigation*
