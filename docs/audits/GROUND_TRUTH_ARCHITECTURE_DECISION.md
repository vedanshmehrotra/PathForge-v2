# GROUND TRUTH ARCHITECTURE — CRITICAL REVIEW AND REVISED DESIGN

**Status:** Architecture review and revised proposal. No code changes.
**Date:** August 20, 2026
**Basis:** Multi-solution feasibility experiment, Phase-0 adversarial evaluation, code audit

---

## 1. THE CURRENT PROBLEM

PathForge generates ground truth for algorithmic problems using a free LLM (gpt-4o-mini via OpenRouter). The LLM returns a flat pattern list. `problem_resolver.py` wraps this into a single `group_0` containing all patterns with AND semantics. The `MatchingEngine` already supports multiple groups with OR semantics, but it never receives more than one group because the upstream pipeline collapses everything.

**Impact:** 42.7% of problems in the 300-problem CSV have multiple patterns. When a problem has two valid approaches (e.g., DFS OR BFS), a user who solves it with only one approach gets a false negative because the system requires all patterns simultaneously.

**What is broken:** The ground-truth representation, not the matching engine.

---

## 2. WHAT THE EXPERIMENT ACTUALLY PROVED

### The evaluation corpus was small.

14 unique problems. 3 trials each. 42 total LLM calls per prompt design. This is a capability test, not a reliability measurement. The results are indicative but not statistically robust.

### Prompt A (current flat-list) behavior:

- Returns a single pattern list for every problem, regardless of how many valid approaches exist.
- For `valid_parentheses`: returns `["dfs_recursive"]` — which is wrong (the problem is a stack problem, not DFS).
- For `meeting_rooms_ii`: includes `greedy_interval` — this is a hallucinated pattern (meeting rooms II is not solvable with pure greedy interval).
- Consistency: 12/14 problems produce identical output across 3 trials.
- Strategy recall: 59.5% (misses valid approaches because it only outputs one set).

### Prompt B (multi-group) behavior:

- Correctly identifies multiple approaches more often (76.2% strategy recall).
- But produces 46 hallucinated patterns vs 8 for Prompt A (475% increase).
- Introduces 6 taxonomy violations (`stack`, `sorting` — not in the 33-pattern canonical set).
- Consistency: 7/14 problems produce identical output across 3 trials (vs 12/14 for A).
- Worst offenders: `clone_graph` produces 3 different outputs across 3 trials, `meeting_rooms_ii` produces 3 different outputs, `reverse_linked_list` produces 3 different outputs.

### What the experiment did NOT prove:

- That the LLM can reliably distinguish AND relationships from OR relationships within a problem.
- That multi-group output is more trustworthy than single-group output.
- That 3 runs provide meaningful stability guarantees.
- That the hallucinated patterns are always harmless extra information (some are wrong — `dfs_recursive` for `valid_parentheses` is a genuine error).

### Key insight from the raw data:

**When Prompt B hallucinates, it often invents plausible-but-wrong patterns.** For example:
- `valid_parentheses` → returns `["stack", "two_pointers_opposite"]` — the `stack` pattern doesn't exist in the taxonomy, and `two_pointers_opposite` is wrong.
- `reverse_linked_list` → sometimes returns `["linked_list_reversal", "linked_list_reversal", "dfs_recursive"]` — includes a nonsensical duplicate and an irrelevant pattern.
- `course_schedule` → includes `bfs_level_order` as a hallucinated pattern (topological sort via BFS exists, but the LLM is adding it to an already-correct group).

---

## 3. CRITIQUE OF THE PREVIOUS CANDIDATE-GENERATOR ARCHITECTURE

The previous recommendation was:

> LLM → taxonomy filtering → group structure validation → cross-group deduplication → 3-run stability check → optional AST validation

### What's wrong with this:

**A. The 3-run stability check is not justified.**

- It costs 3x LLM usage per problem.
- Consistency across runs is not a proxy for correctness. The LLM can consistently return the same wrong answer. For `valid_parentheses`, all 3 Prompt A trials consistently return `["dfs_recursive"]` — consistently wrong.
- When the LLM is consistent, it doesn't mean the output is correct. When it's inconsistent, it doesn't mean the output is wrong — it might be returning valid alternatives across different runs.
- The 50% consistency rate for Prompt B means we'd need to define what "majority vote" means across runs with different hallucinations. There's no clean way to do this.

**B. Taxonomy filtering catches only the most obvious errors.**

- Removing `stack` and `sorting` prevents runtime crashes but doesn't fix the underlying problem: the LLM doesn't understand the taxonomy it's generating for.
- Filtering non-canonical patterns doesn't detect plausible-but-wrong canonical patterns (e.g., `dfs_recursive` for `valid_parentheses`).

**C. Group structure validation is limited.**

- We can check: no empty groups, no duplicate groups, patterns exist in taxonomy.
- We cannot check: whether the AND/OR grouping is correct, whether the groups represent genuinely distinct approaches, whether a required pattern is missing.

**D. The architecture assumes the LLM is a reliable starting point that needs minor cleanup.**

The data shows the LLM is an unreliable starting point that produces plausible-sounding but frequently wrong outputs. The cleanup pipeline cannot fix structural errors in the LLM's understanding of algorithms.

---

## 4. THE FUNDAMENTAL TENSION

There are two things the system needs to know:

1. **What patterns are required for each valid solution approach?** (Ground truth)
2. **Which patterns did the user's code actually implement?** (AST detection)

The LLM is being asked to solve problem (1). But problem (1) requires deep algorithmic understanding that a free model cannot reliably provide for all problems.

**The experiment showed that the LLM can identify SOME valid approaches for SOME problems, but with unacceptable error rates for a system that judges user submissions.**

---

## 5. RECOMMENDED MINIMUM ARCHITECTURE

### Core principle: The LLM generates candidates, not truth.

Every LLM output is treated as a **candidate** that must pass deterministic validation before it affects user scoring. The system must degrade gracefully when validation fails.

### The ground-truth model:

```
Problem
  └── GroundTruth (versioned)
        ├── validation_status: validated | plausible | uncertain | rejected
        ├── solution_groups: List[SolutionGroup]
        │     └── SolutionGroup
        │           ├── patterns: List[str]   (AND within group)
        │           └── provenance: "llm" | "reference" | "human" | "merged"
        ├── confidence: float
        └── metadata: {model, prompt_version, generation_date, ...}
```

### Validation states and their runtime meaning:

| State | Definition | Runtime behavior |
|-------|-----------|-----------------|
| **validated** | All patterns in all groups exist in canonical taxonomy AND were verified against at least one reference implementation (AST-analyzed known-good solution) | Full matching. ELO updates use standard K-factor. Gap detection active. |
| **plausible** | All patterns exist in canonical taxonomy, but no reference validation | Full matching. ELO updates use reduced K-factor (0.5×). Gap detection active but gap signals flagged as "uncertain". |
| **uncertain** | Patterns exist in taxonomy but group structure is unverifiable, OR the LLM was inconsistent across runs | Matching still runs. ELO updates use minimal K-factor (0.25×). Gap detection suppressed. Recommendation engine uses neutral baseline. |
| **rejected** | Patterns fail taxonomy validation, OR the LLM returned zero groups, OR reference validation contradicts the groups | System falls back to a single-group containing the most basic expected pattern for the problem category. ELO updates suppressed. Gap detection suppressed. Recommendation engine uses neutral baseline. |

**The critical rule:** Uncertain ground truth should NOT aggressively affect user scoring. A wrong ground truth that penalizes users for correct solutions is worse than no ground truth at all.

---

## 6. OFFLINE PIPELINE (once per problem)

```
Problem added to system
  │
  ├─→ Step 1: LLM candidate generation
  │     - Single call, multi-group prompt
  │     - Returns candidate solution groups
  │     - Cost: 1 LLM call per problem
  │
  ├─→ Step 2: Deterministic validation
  │     a. Taxonomy filtering (remove non-canonical patterns)
  │     b. Empty group rejection
  │     c. Duplicate group removal
  │     d. Single-pattern group validation (pattern exists in taxonomy)
  │     e. Group structure sanity (max 5 groups, max 5 patterns per group)
  │
  ├─→ Step 3: Reference validation (if reference implementations available)
  │     - Run AST engine on reference solutions
  │     - Compare detected patterns with proposed groups
  │     - Mark patterns that AST confirms as "verified"
  │     - Mark patterns that AST contradicts as "disputed"
  │
  ├─→ Step 4: Status assignment
  │     - All patterns verified → validated
  │     - All patterns in taxonomy, no reference → plausible
  │     - Some patterns disputed or unverifiable → uncertain
  │     - Structural failures → rejected
  │
  └─→ Step 5: Store versioned ground truth
        - Previous ground truth preserved (never overwritten)
        - New version becomes active
        - Old versions retained for audit trail
```

**No LLM call in the runtime path.** The LLM is called once per problem, offline, during problem preparation.

---

## 7. RUNTIME PIPELINE (per user submission)

```
User submits code
  │
  ├─→ AST analysis (deterministic, no LLM)
  │     - Detects patterns present in code
  │     - Produces DetectionResults with evidence and confidence
  │
  ├─→ Load ground truth (from database, no LLM)
  │     - Returns solution groups + validation_status
  │
  ├─→ Matching (deterministic)
  │     - Compares detected patterns against solution groups
  │     - Uses OR-semantics across groups, AND-semantics within
  │     - Produces match_result, confidence, matched_groups
  │
  ├─→ Analysis reliability scoring
  │     - HIGH: ground truth is validated, AST confidence > 0.7
  │     - MEDIUM: ground truth is plausible, or AST confidence 0.4-0.7
  │     - LOW: ground truth is uncertain, or AST confidence < 0.4
  │
  ├─→ ELO update (reliability-scaled)
  │     - HIGH reliability: standard K-factor
  │     - MEDIUM reliability: 0.5× K-factor
  │     - LOW reliability: 0.25× K-factor
  │
  ├─→ Gap detection (reliability-gated)
  │     - HIGH/MEDIUM: normal gap detection
  │     - LOW: gap detection suppressed (too unreliable to identify real gaps)
  │
  └─→ Recommendation (reliability-gated)
        - HIGH: full recommendation logic
        - MEDIUM: conservative recommendations
        - LOW: neutral baseline (no strong recommendation)
```

**No LLM call in this path.** Every step is deterministic.

---

## 8. DETERMINISTIC VALIDATION MECHANISMS

Ranked by reliability:

### 1. Taxonomy membership check — SAFE AND USEFUL

Every pattern must be in the 33-entry canonical set. This catches:
- `stack`, `sorting` (observed hallucinations)
- Any invented pattern names

**Cost:** Zero (set membership check)
**Reliability:** 100% for catching non-existent patterns
**Limitation:** Cannot catch valid patterns that the taxonomy doesn't include

### 2. Empty/duplicate group rejection — SAFE AND USEFUL

- Remove groups with zero patterns
- Remove duplicate groups (same pattern set)
- Cap at 5 groups maximum

**Cost:** Zero
**Reliability:** 100%
**Limitation:** Cannot detect when two genuinely distinct groups are incorrectly merged

### 3. Cross-reference with CSV metadata — SAFE AND USEFUL

The 300-problem CSV contains manually assigned patterns. If the LLM output is entirely disjoint from the CSV patterns for a problem, flag as uncertain.

**Cost:** Zero (lookup)
**Reliability:** Medium (CSV patterns are themselves flat lists, not solution groups)
**Limitation:** CSV may be incomplete or contain its own errors

### 4. Reference-implementation AST validation — USEFUL BUT LIMITED

Run the AST engine on known-good solutions and compare detected patterns with proposed groups.

**Cost:** One AST analysis per reference solution (deterministic, fast)
**Reliability:** Limited by AST engine's own precision (99.8%) and recall (84%)
**Circular risk:** YES — the AST engine is imperfect. If the AST misses a pattern in a reference solution, it would incorrectly dispute a valid ground-truth pattern. This creates the circular reasoning the architecture must avoid.

**Mitigation:** AST validation should only ADD confidence (pattern confirmed), never REMOVE it. If the AST detects a pattern that ground truth doesn't include, that's information. If the AST fails to detect a pattern that ground truth includes, that's an AST limitation, not a ground-truth error.

### 5. Multi-run consistency — USEFUL BUT EXPENSIVE

Run the LLM 2-3 times. If the output is consistent, higher confidence.

**Cost:** 2-3× LLM usage per problem
**Reliability:** Low (consistent wrong answers exist — `valid_parentheses` → `dfs_recursive` was consistent across all 3 trials)
**Verdict:** NOT worth the cost for a free model. Consistency is neither necessary nor sufficient for correctness.

### 6. Group-structure semantic check — UNSAFE / MISLEADING

Trying to validate whether the AND/OR grouping is algorithmically correct requires understanding the problem domain. This is exactly what the LLM is bad at. Automating this would require another LLM call or a knowledge base that doesn't exist.

**Verdict:** Do not attempt.

---

## 9. REFERENCE IMPLEMENTATION ANALYSIS

### Can reference implementations serve as the main validator?

**The idea:**
1. Obtain known-good solutions for a problem (e.g., from LeetCode editorial, community solutions)
2. Run the AST engine on each solution
3. The patterns the AST detects in reference solutions become the validated ground truth

**Advantages:**
- Completely deterministic (no LLM needed for validation)
- Leverages the AST engine's existing high precision (99.8%)
- Produces directly measurable ground truth

**Disadvantages:**
- The AST engine has 84% recall. It would miss ~16% of patterns in reference solutions.
- This creates the circular problem: AST weakness → missing pattern → pattern excluded from ground truth → user who implements that pattern gets false negative.
- Requires obtaining reference implementations (not currently automated)
- Reference implementations may use non-standard coding styles that the AST doesn't recognize

**Critical question: Can we use reference implementations WITHOUT circular reasoning?**

Yes, with a specific rule:

> AST validation of reference implementations can only CONFIRM patterns, never DISPROVE them.

If the AST detects `dfs_recursive` in a reference solution, we can add it to the validated set. If the AST fails to detect `bfs_level_order` in a reference solution that actually uses BFS, we do NOT remove `bfs_level_order` from the ground truth — we just don't get the confirmation.

This means reference implementations increase confidence in patterns they confirm, but their failures to detect don't reduce confidence. The ground truth can only be strengthened, never weakened, by reference validation.

**Practical limitation:** This requires obtaining reference implementations. Options:
- Use the user's own submissions that received FULL_MATCH as reference implementations (bootstrapping)
- Use the LLM to generate candidate solutions, then validate them with the AST (but this reintroduces LLM dependency)
- Use LeetCode editorial solutions if accessible via GraphQL

---

## 10. COMPARISON OF OPTIONS A, B, C

### Option A: Single LLM generation → validation → store

| Aspect | Assessment |
|--------|-----------|
| LLM usage | 1 call per problem |
| Cost | Low (free model) |
| Latency | ~3-5 seconds per problem |
| Reliability | Limited by single-shot LLM accuracy |
| Complexity | Low |
| Failure mode | Single bad generation → uncertain ground truth |
| Free-model suitability | Good |

### Option B: Single generation → validate → second generation if uncertain

| Aspect | Assessment |
|--------|-----------|
| LLM usage | 1-2 calls per problem |
| Cost | Low-medium |
| Latency | 3-10 seconds per problem |
| Reliability | Better than A (second chance) |
| Complexity | Medium (need "uncertain" detection logic) |
| Failure mode | Two bad generations → still uncertain |
| Free-model suitability | Acceptable |

### Option C: Always 3 runs → stability → validation

| Aspect | Assessment |
|--------|-----------|
| LLM usage | 3 calls per problem |
| Cost | 3× higher |
| Latency | 10-15 seconds per problem |
| Reliability | Not meaningfully better (consistent wrong answers exist) |
| Complexity | High (majority voting, conflict resolution) |
| Failure mode | Consistent hallucination across all 3 runs |
| Free-model suitability | Poor (3× API usage on free tier) |

### Recommendation: Option A with selective escalation to Option B.

**Default:** Single LLM generation with deterministic validation.
**Escalation:** If deterministic validation flags the output as `uncertain`, run a second generation with a modified prompt that asks the model to reconsider. If the second generation agrees with the first, promote to `plausible`. If it disagrees, remain `uncertain`.

This gives us:
- 1 LLM call for ~70-80% of problems (those that pass validation on first try)
- 2 LLM calls for ~20-30% of problems (those that need reconsideration)
- Total: ~1.2-1.3 LLM calls per problem on average
- No 3-run consistency check

---

## 11. INTERACTION WITH AST IMPROVEMENT WORK

### Separation of responsibility:

| Layer | Responsibility | Does NOT do |
|-------|---------------|-------------|
| **AST engine** | Detect what code structures are present | Determine whether those structures constitute a valid algorithmic approach |
| **Ground truth** | Define which alternative optimal approaches are valid for this problem | Detect anything in user code |
| **Matching engine** | Check whether detected structures satisfy at least one valid approach | Generate ground truth or detect patterns |
| **LLM** | Generate candidate solution groups (offline only) | Verify user submissions at runtime |

### The LLM must not become a substitute for a weak AST detector.

If the AST engine misses `bfs_level_order` in a user's BFS solution, the correct response is:
1. Improve the AST detector (Experiment 2B/2C)
2. Accept the false negative with appropriate observability

The incorrect response is:
1. Send the code to an LLM to "check" whether it's BFS
2. Use the LLM result to override the AST result

The second approach creates a system where the LLM becomes the real analyzer and the AST becomes a latency optimization. This contradicts the architectural goal of deterministic-first analysis.

### The ground-truth architecture must not hide AST weaknesses.

If the AST engine has 84% recall, then ~16% of correct solutions will receive false negatives. Making ground truth more accurate does not fix this. The correct fix is improving AST recall (which is happening in parallel).

The ground-truth architecture and the AST architecture are independent improvements that happen to interact at the matching layer. They should be developed and evaluated independently.

---

## 12. WHAT SHOULD REMAIN DETERMINISTIC

Everything in the runtime path:
- AST analysis
- Pattern detection
- Matching
- Confidence calculation
- Match result determination
- ELO updates (with reliability scaling)
- Gap detection (with reliability gating)
- Recommendations (with reliability gating)
- Persistence

The only non-deterministic component is offline ground-truth generation, which happens once per problem and is validated before activation.

---

## 13. EXPLICIT NON-GOALS

1. **No runtime LLM verification of user submissions.** The LLM does not check whether a user's code implements a specific algorithm.
2. **No LLM-as-judge.** The LLM does not evaluate the quality or correctness of user solutions.
3. **No human review requirement.** The system must operate without manual review of every problem's ground truth.
4. **No paid API dependency.** The system must work with the free OpenRouter model.
5. **No generic semantic equivalence engine.** We do not build a system that understands what code "means" — we build systems that detect structural patterns.
6. **No overconfident ground truth.** The system must know when it doesn't know, and must not penalize users for the system's uncertainty.

---

## 14. RISKS AND UNRESOLVED QUESTIONS

### Risk 1: The free LLM may not improve enough.

If gpt-4o-mini consistently produces wrong ground truth for a significant fraction of problems, the system will have many problems in `uncertain` or `rejected` state. This means those problems cannot effectively contribute to user skill modeling.

**Mitigation:** Bootstrap ground truth from user submissions (FULL_MATCH results become reference implementations). This is slow but deterministic.

### Risk 2: The 33-pattern taxonomy may be too small.

Some problems require patterns not in the taxonomy (e.g., `bidirectional_search` for word ladder). The LLM may correctly identify a valid approach but have no taxonomy entry for it.

**Mitigation:** This is a taxonomy expansion decision, not a ground-truth architecture decision. It should be handled separately.

### Risk 3: Reference validation requires reference implementations.

Currently, no reference implementations are available in the system. Without them, the `validated` state is unreachable.

**Mitigation:** Start with `plausible` as the default state for LLM-generated ground truth. Upgrade to `validated` only when reference implementations become available. This is honest about the system's actual confidence level.

### Risk 4: The CSV patterns may not represent solution groups.

The CSV contains flat pattern lists. Some entries may contain patterns that are alternatives (OR) rather than complementary (AND), but the CSV doesn't distinguish.

**Mitigation:** Do not treat CSV patterns as ground truth. Use them only as a consistency signal. If the LLM output is entirely disjoint from the CSV, flag for review.

### Risk 5: ELO reliability scaling may be too conservative.

If most ground truth is `plausible` (not `validated`), the 0.5× K-factor may slow skill modeling to the point where recommendations are unhelpful.

**Mitigation:** Monitor the distribution of validation states over time. If >80% of problems remain `plausible`, consider relaxing the K-factor scaling.

---

## 15. PHASED IMPLEMENTATION PLAN

### Phase G1: Ground-truth schema + multi-group support

**Objective:** Store multiple solution groups per problem.
**Files:** `problem_ground_truth` table, `problem_resolver.py`, `ground_truth_builder.py`
**Changes:**
- Add `solution_groups` column (JSONB) to `problem_ground_truth`
- Add `validation_status` column (TEXT, default 'plausible')
- Modify `_load_ground_truth()` to read from `solution_groups` if present, fall back to flat `patterns`
- Modify `_normalize_patterns()` in `ground_truth_builder.py` to produce structured groups
- No changes to MatchingEngine (it already accepts multiple groups)

**Validation:** Existing tests pass. New ground truth with groups matches the same matching behavior as before.

### Phase G2: Multi-group LLM prompt

**Objective:** Generate candidate solution groups instead of flat pattern lists.
**Files:** `openrouter_client.py` (prompt modification only)
**Changes:**
- New prompt template requesting explicit solution groups
- Post-processing to validate group structure
- Fallback to flat-list prompt if multi-group prompt fails

**Validation:** Run the 14-problem evaluation corpus. Compare strategy recall and hallucination rates. Target: ≥70% strategy recall, ≤15 hallucinated patterns.

### Phase G3: Deterministic validation

**Objective:** Classify ground truth into validated/plausible/uncertain/rejected.
**Files:** New `pathforge/services/ground_truth_validator.py`, `ground_truth_builder.py`
**Changes:**
- Taxonomy membership check
- Empty/duplicate group rejection
- CSV cross-reference check
- Status assignment logic

**Validation:** Run against the 300-problem CSV. Measure distribution of validation states. Target: ≥60% `plausible` or better.

### Phase G4: Reliability-aware scoring

**Objective:** Scale ELO, gap, and recommendation behavior based on ground-truth confidence.
**Files:** `pathforge/services/persistence.py`, `pathforge/elo_engine.py`, `pathforge/gap_signal_engine.py`
**Changes:**
- ELO K-factor scaling by validation status
- Gap detection gating by validation status
- Recommendation gating by validation status

**Validation:** Existing tests pass. ELO values for uncertain ground truth are less extreme than for validated ground truth.

### Phase G5: Reference validation (optional, requires reference implementations)

**Objective:** Upgrade `plausible` ground truth to `validated` using AST analysis of reference solutions.
**Files:** New `pathforge/services/reference_validator.py`
**Changes:**
- Run AST engine on reference solutions
- Confirm (never disprove) patterns in ground truth
- Upgrade validation status

**Validation:** Number of `validated` problems increases. No patterns are removed by reference validation.

### NOT in this plan:

- Multi-run consistency checks
- Runtime LLM verification
- Human review workflows
- Taxonomy expansion
- AST engine improvements (separate track)

---

## 16. SUMMARY

| Aspect | Recommendation |
|--------|---------------|
| LLM usage | 1 call per problem, offline only |
| Multi-run | Not recommended (cost > benefit) |
| Validation | Deterministic (taxonomy, structure, CSV cross-reference) |
| Reference validation | Optional, confirm-only |
| Runtime path | Fully deterministic |
| Uncertain ground truth | Allowed to exist; reduces ELO impact |
| ELO safety | K-factor scaled by validation status |
| AST/ground truth separation | Independent improvements, no circular reasoning |

---

*End of Ground Truth Architecture Decision Document*
