# GROUND TRUTH VALIDATION — ARCHITECTURE STRESS TEST

**Status:** Architecture investigation. No code changes.
**Date:** August 20, 2026
**Basis:** Multi-solution feasibility experiment (14 problems, 3 trials each), code audit

---

## 1. EXECUTIVE CONCLUSION

**The proposed ground-truth validation architecture has a fundamental flaw that cannot be resolved with the data currently available in PathForge.**

The flaw: deterministic validation (taxonomy check, JSON schema, group structure) can confirm that a pattern *exists* but cannot confirm that it is *correct for this specific problem*. The LLM can return `["binary_search_standard"]` for a graph traversal problem, and every validation check would pass.

**PathForge currently has no deterministic mechanism to validate algorithmic correctness of a pattern against a specific problem.** This means:
- The word "validated" is misleading if applied to LLM output that merely passes syntax and taxonomy checks
- The ground-truth system cannot be trusted to be correct without external verification
- Every ground-truth pattern must be treated as a *candidate*, not a *fact*

The recommended architecture acknowledges this honestly and designs around it rather than pretending the problem is solvable with current data.

---

## 2. CURRENT PIPELINE TRACE

### Complete flow (verified from code):

```
Problem input (leetcode_id or title_slug)
  │
  ├─→ problem_resolver.resolve_problem()
  │     ├─→ _find_problem_in_db() — SELECT from problems table
  │     ├─→ _fetch_and_store_problem() — GraphQL → INSERT INTO problems
  │     ├─→ _ensure_ground_truth() — SELECT from problem_ground_truth
  │     │     └─→ if missing: ground_truth_builder.build_ground_truth()
  │     │           ├─→ openrouter_client.call_llm(description)
  │     │           │     ├─→ _build_prompt(description) — flat pattern list prompt
  │     │           │     ├─→ _post_request() — OpenRouter API call
  │     │           │     ├─→ _parse_llm_json() — parse JSON response
  │     │           │     └─→ returns {"patterns": [...], "confidence": {...}}
  │     │           ├─→ _normalize_patterns() — filter to ALL_PATTERNS (33 entries)
  │     │           └─→ _store_ground_truth() — INSERT INTO problem_ground_truth
  │     └─→ _load_ground_truth() — wraps flat list into group_0
  │           └─→ returns [{"id": "group_0", "patterns": [...]}]
  │
  ├─→ ProblemContext.accepted_solution_groups = [group_0]
  │
  ├─→ analyze route calls run_analysis(code, groups)
  │     ├─→ AST engine analyzes code → detected_patterns
  │     ├─→ Groups extracted: [g["patterns"] for g in groups]
  │     └─→ MatchingEngine.match(llm_input, ast_output)
  │           ├─→ _normalize_llm() — extract pattern sets from groups
  │           ├─→ _compute_group_matches() — AND within group
  │           ├─→ _decide_match_result() — FULL_MATCH if any group fully matched
  │           └─→ returns match_result, confidence, matched_groups
  │
  └─→ Persistence
        ├─→ submissions table (verdet, detected_pattern, expected_pattern)
        ├─→ gap_signals (missing patterns → gap)
        ├─→ user_pattern_elo (ELO update based on match_result)
        └─→ recommendations
```

### Exact locations of the flat-list → single-group collapse:

**File:** `pathforge/services/problem_resolver.py`, function `_load_ground_truth()`, lines ~106-115:
```python
if patterns:
    best_conf = max(confidence.values()) if confidence else 1.0
    groups = [
        {
            "id": "group_0",
            "display_name": "Primary Solution",
            "confidence": best_conf,
            "patterns": patterns,
        }
    ]
    return groups, confidence
```

This is the **only** place where the collapse happens. The MatchingEngine already accepts multiple groups.

### Database representation:

**`problem_ground_truth` table** (verified from `pathforge/db/schema_pg.sql`):
```sql
CREATE TABLE IF NOT EXISTS problem_ground_truth (
    problem_id INTEGER PRIMARY KEY,
    patterns TEXT NOT NULL DEFAULT '[]',      -- flat JSON list
    confidence TEXT NOT NULL DEFAULT '{}',     -- pattern→confidence dict
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Current schema limitation:** The `patterns` column stores a flat JSON list (`["pattern_a", "pattern_b"]`). There is no column for solution groups. To support multiple groups, the schema needs a `solution_groups` column (JSONB).

**What would need to change:**
1. Add `solution_groups` column to `problem_ground_truth`
2. Add `validation_status` column
3. Modify `_load_ground_truth()` to read groups from the new column
4. Modify `ground_truth_builder.py` to produce structured groups
5. No changes to MatchingEngine (it already accepts groups)

### What code assumes only one group:

**`run_persistence()`** in `pathforge/services/persistence.py`:
```python
expected_pattern = ""
if groups:
    for g in groups:
        patterns = g.get("patterns", [])
        if patterns:
            expected_pattern = patterns[0]
            break
```

This extracts only the first pattern from the first group for the `expected_pattern` column in submissions. With multiple groups, this should pick the pattern from the *matched* group, not always the first group. This is a real bug that would manifest with multiple groups.

**`analyze_endpoint()`** in `pathforge/api/routes/analyze.py`:
```python
canonical_patterns = [
    CanonicalPattern(name=p, confidence=ctx.ground_truth_confidence.get(p, 0.0))
    for g in (ctx.accepted_solution_groups or [])
    for p in (g.get("patterns", []) if isinstance(g, dict) else g)
]
```

This flattens all groups into one list for the response. This is acceptable for display but loses group structure information.

---

## 3. VALIDATION CAPABILITY MATRIX

### Level 1: Syntax Validity

| Check | Can do? | Evidence | Reliability |
|-------|---------|----------|-------------|
| Valid JSON | Yes | `_parse_llm_json()` already does this | 100% |
| Valid schema (patterns list, confidence dict) | Yes | `_parse_llm_json()` checks `patterns` is list | 100% |
| Valid group structure (list of groups, each with patterns) | Yes | Can be added trivially | 100% |

**What this proves:** The LLM returned parseable, well-structured data.
**What this does NOT prove:** That the data is correct for this problem.

### Level 2: Taxonomy Validity

| Check | Can do? | Evidence | Reliability |
|-------|---------|----------|-------------|
| Every pattern exists in ALL_PATTERNS | Yes | `_normalize_patterns()` already does this | 100% |
| No invented pattern names | Yes | Set membership check | 100% |
| Pattern count is reasonable (1-5 per group) | Yes | Trivial length check | 100% |

**What this proves:** Every named pattern is a real concept in PathForge's vocabulary.
**What this does NOT prove:** That the pattern is relevant to this specific problem.

**Example failure that passes this check:**
- Problem: "Number of Islands" (graph traversal)
- LLM returns: `["binary_search_standard"]`
- Taxonomy check: `binary_search_standard` is in ALL_PATTERNS ✓
- But it's algorithmically wrong

### Level 3: Internal Compatibility

| Check | Can do? | Evidence | Reliability |
|-------|---------|----------|-------------|
| No duplicate patterns within a group | Yes | Set conversion | 100% |
| No empty groups | Yes | Length check | 100% |
| No contradictory patterns in same group | Partial | Some contradictions detectable (e.g., `binary_search_standard` + `brute_force`) | ~50% |
| Max group count ≤ 5 | Yes | Trivial | 100% |

**What this proves:** The groups are structurally sane.
**What this does NOT prove:** That the groups represent valid solution strategies.

**Contradiction detection is unreliable because:**
- Many pattern pairs are legitimately complementary (e.g., `hash_map_lookup` + `two_pointers_same` for "Intersection of Two Linked Lists")
- Some pairs are contradictory in some contexts but not others
- No deterministic rule can distinguish these cases without understanding the problem

### Level 4: Problem Applicability

| Check | Can do? | Evidence | Reliability |
|-------|---------|----------|-------------|
| Pattern matches problem tags | Partial | LeetCode topics (Array, Hash Table, etc.) loosely correlate with patterns | ~40% |
| Pattern matches problem difficulty | No | Easy problems can use any pattern | 0% |
| Pattern is plausible given problem constraints | No | Requires algorithmic reasoning | 0% |
| CSV pattern list includes this pattern | Partial | CSV has flat pattern lists for 300 problems | ~60% (CSV may be incomplete or wrong) |

**What this proves:** There is a loose correlation between the pattern and the problem category.
**What this does NOT prove:** That the pattern is a valid solution strategy.

**The CSV cross-reference is the closest thing to problem-specific validation, but:**
- The CSV contains flat pattern lists, not solution groups
- The CSV was likely generated by the same or similar LLM
- 42.7% of problems have multiple patterns in the CSV, but the CSV doesn't distinguish OR from AND
- The CSV may contain its own errors

### Level 5: Algorithmic Correctness

| Check | Can do? | Evidence | Reliability |
|-------|---------|----------|-------------|
| Pattern represents a valid optimal strategy | No | Requires algorithmic reasoning about the specific problem | 0% |
| Group represents a complete solution approach | No | Requires understanding what "complete" means for this problem | 0% |
| Pattern is optimal (not just valid) | No | Requires complexity analysis | 0% |
| Reference implementation confirms pattern | Partial | If reference implementations exist, AST can detect patterns in them | ~84% (limited by AST recall) |

**This is the critical gap.** Level 5 validation is what would make ground truth trustworthy, and PathForge cannot currently perform it deterministically.

---

## 4. AVAILABLE EVIDENCE INVENTORY

### Data available in PathForge:

| Source | What it contains | Can validate patterns? |
|--------|-----------------|----------------------|
| `problems` table | title, difficulty, topics, description, test_cases | Loosely (topics correlate with patterns) |
| `problem_ground_truth` table | patterns (flat list), confidence | No (this IS what we're trying to validate) |
| CSV (`pathforge_problems_fixed.csv`) | 300 problems with manually assigned patterns | Partially (patterns exist, but flat lists, may have errors) |
| LeetCode GraphQL | title, difficulty, topics, description, hints, exampleTestcases | Loosely (same as problems table) |
| User submissions | code, verdict, detected patterns | No (these are what we're trying to evaluate) |

### Data NOT available in PathForge:

| Missing data | Why it matters |
|-------------|---------------|
| Reference implementations | Would allow AST-based validation of ground truth |
| Problem editorial/solutions | Would provide authoritative pattern labels |
| Multiple known-good solutions per problem | Would reveal actual solution diversity |
| Human-annotated pattern labels | Would serve as ground truth for ground truth |
| Problem→pattern mapping with OR/AND semantics | Would distinguish alternative vs complementary patterns |

### The fundamental problem:

**PathForge is trying to validate ground truth using the same information that was used to generate it.** The LLM sees the problem description. The validator would see the problem description. Neither can determine algorithmic correctness from the description alone.

---

## 5. REFERENCE IMPLEMENTATION INVESTIGATION

### Does PathForge have reference implementations?

**No.** There is no table, column, or file containing reference solution code. The `problems` table stores `test_cases` (input/output pairs) but not solution code.

### Could reference implementations be obtained?

**Potentially, but with significant limitations:**

1. **LeetCode editorial solutions:** The GraphQL API provides `hints` but not full editorial solutions. Full solutions require premium access.

2. **Community solutions:** Could be scraped, but this introduces legal/licensing concerns and quality variability.

3. **LLM-generated solutions:** The LLM could generate candidate solutions, but:
   - This reintroduces LLM dependency
   - Generated solutions may not be correct
   - Running the AST engine on LLM-generated code validates the AST engine, not the ground truth

4. **User submissions with FULL_MATCH:** Successful user submissions could become reference implementations over time. But:
   - This is a slow bootstrap process
   - User code quality varies
   - Requires a FULL_MATCH to have occurred first (chicken-and-egg problem)

### Could the AST engine analyze reference implementations?

**Yes, with limitations:**
- AST precision is 99.8% (very reliable for confirmed detections)
- AST recall is ~84% (misses ~16% of patterns)
- AST can detect patterns in reference code, but cannot confirm that the detected patterns constitute a *complete* solution

### Circularity analysis:

**Loop 1: LLM generates ground truth → AST validates against reference → ground truth confirmed**

```
LLM generates: ["binary_search_standard"]
AST analyzes reference solution → detects: ["binary_search_standard"]
Conclusion: ground truth is correct ✓
```

This works when the LLM is right. But:

```
LLM generates: ["binary_search_standard"]
AST analyzes reference solution → detects: ["hash_map_lookup"] (AST missed binary search)
Conclusion: ground truth is disputed ✗ (but ground truth was actually correct)
```

**The AST's false negatives would incorrectly dispute correct ground truth.** This is circular: AST weakness → incorrect ground truth → future user submissions judged against wrong ground truth.

**Loop 2: Reference implementations → AST detects patterns → patterns become ground truth**

```
Reference solution code
  ↓
AST engine analyzes → detects: ["dfs_recursive", "hash_map_lookup"]
  ↓
These patterns become candidate ground truth
```

This is **not circular** because:
- The AST engine is analyzing *code*, not *generating* ground truth
- The AST's high precision (99.8%) means detected patterns are almost certainly present in the code
- The AST's recall limitation means some patterns will be missed, but no incorrect patterns will be added

**This is the safer approach:** Start from reference implementations, use AST to detect what patterns are present, and treat those as the *minimum confirmed* ground truth. The LLM can then be used to *suggest additional* patterns that the AST may have missed.

---

## 6. CIRCULAR VALIDATION ANALYSIS

### The specific circular reasoning risk:

If we use the same AST engine to:
1. Validate ground truth (confirm patterns in reference implementations)
2. Analyze user submissions (detect patterns in user code)

Then any systematic AST weakness affects both sides:
- If the AST consistently misses `bfs_level_order` in while-loop BFS implementations
- Then `bfs_level_order` would be excluded from validated ground truth
- Then a user who implements BFS correctly would not get credit for `bfs_level_order`
- The system would appear consistent but would be consistently wrong

### Is this actually a problem?

**Yes, but it's a manageable one.** The key insight:

> AST validation of reference implementations can only CONFIRM patterns, never DISPROVE them.

If we adopt the rule:
- Pattern detected in reference → add to confirmed set
- Pattern NOT detected in reference → do NOT remove from candidate set

Then AST weakness reduces the *confirmed* set but does not introduce false negatives. The unconfirmed patterns remain as candidates with lower confidence.

**This is legitimate validation, not circular reasoning,** as long as the rule is enforced.

### The remaining risk:

If the LLM generates a pattern that is genuinely wrong (e.g., `binary_search_standard` for "Number of Islands"), and the AST validation doesn't detect it in any reference implementation, the pattern remains as an unconfirmed candidate. It would still be included in the ground truth (just with lower confidence). This means wrong patterns can persist.

**This is an acceptable tradeoff** because:
- Wrong patterns in ground truth cause false positives (user gets credit for a pattern they didn't implement), not false negatives
- False positives are less harmful than false negatives in a learning system
- The matching engine's extra-pattern penalty already handles this partially

---

## 7. CONFIDENCE STATE STRESS TEST

### Original proposed states:

| State | Proposed meaning | Problem |
|-------|-----------------|---------|
| VALIDATED | All patterns confirmed by reference implementations | Misleading — "validated" implies correctness, but AST only confirms presence, not correctness |
| PLAUSIBLE | All patterns in taxonomy, no reference | This is just "passed Level 2 validation" — not meaningfully "plausible" |
| UNCERTAIN | Some patterns unverifiable | Reasonable, but what triggers this state? |
| REJECTED | Structural failures | Reasonable, but too aggressive — most LLM outputs are structurally valid |

### Stress test: What does "VALIDATED" actually guarantee?

If we define VALIDATED as "all patterns detected in at least one reference implementation":

**Guarantees:**
- Every pattern is present in some known-good solution ✓
- Every pattern exists in the canonical taxonomy ✓
- The pattern set is not empty ✓

**Does NOT guarantee:**
- That the pattern set is complete (may miss valid approaches) ✗
- That the group structure is correct (AND vs OR may be wrong) ✗
- That the patterns are optimal (may include suboptimal approaches) ✗
- That the patterns are correct for this specific problem (reference may use a different approach) ✗

**The word "VALIDATED" overpromises.** A better name would be "reference_confirmed" or "partially_verified."

### Stress test: What triggers UNCERTAIN?

If the LLM output passes taxonomy checks but has no reference implementations:

- Is every such problem "uncertain"? That would be most problems.
- What makes one problem's ground truth more uncertain than another's?
- Without a clear trigger, UNCERTAIN becomes the default state for everything, which degrades ELO usefulness.

### Revised state definitions:

| State | Entry criteria | What it guarantees | Runtime effect |
|-------|---------------|-------------------|----------------|
| **reference_confirmed** | All patterns in at least one reference implementation; AST detects them | Patterns are present in known-good code | Standard ELO (K=1.0) |
| **candidate** | All patterns in taxonomy; passed structural checks | Patterns are valid vocabulary; structure is sane | Reduced ELO (K=0.5) |
| **unverified** | No reference implementations; patterns are valid vocabulary | Nothing beyond vocabulary validity | Minimal ELO (K=0.25) |
| **rejected** | Structural failures, taxonomy violations, empty groups | Nothing — output is invalid | No ELO update |

The key change: **eliminate "VALIDATED" and "PLAUSIBLE"** — these names imply a level of correctness that the system cannot deliver. Replace with honest names that describe what was actually checked.

---

## 8. ARCHITECTURE OPTIONS

### Option A: LLM-First with Weak Validation

```
Problem description
  ↓
LLM generates candidate groups
  ↓
Taxonomy filtering (Level 2)
  ↓
Structural validation (Level 3)
  ↓
Store as "candidate" status
  ↓
MatchingEngine uses groups as-is
```

**LLM calls:** 1 per problem
**Deterministic guarantees:** Levels 1-3 only
**Failure modes:** Algorithmically wrong patterns pass validation
**False negative risk:** Low (if LLM identifies valid approaches)
**False positive risk:** High (LLM invents plausible-but-wrong patterns)
**Works with free model:** Yes
**Implementation complexity:** Low
**Database changes:** Add `solution_groups` and `validation_status` columns

**Assessment:** This is essentially the current system with better structure. It does not solve the core problem of correctness validation.

### Option B: Reference-Solution-First with LLM Augmentation

```
Problem description + test cases
  ↓
Obtain reference implementations (user submissions, community, or LLM-generated)
  ↓
AST engine analyzes each reference → detected patterns per solution
  ↓
Patterns detected in references become "reference_confirmed" ground truth
  ↓
LLM generates additional candidate patterns
  ↓
LLM patterns that match reference patterns → merged into confirmed groups
  ↓
LLM patterns not in any reference → stored as "candidate" with lower confidence
  ↓
Store with appropriate status
```

**LLM calls:** 1 per problem (for augmentation only)
**Deterministic guarantees:** Reference-confirmed patterns are known to exist in working code
**Failure modes:** AST misses patterns in references (recall limitation)
**False negative risk:** Medium (AST recall limits confirmed patterns)
**False positive risk:** Low for confirmed patterns; Medium for LLM-augmented patterns
**Works with free model:** Yes
**Implementation complexity:** Medium (need to obtain/reference implementations)
**Database changes:** Same as Option A

**Assessment:** This is the most reliable option, but requires a source of reference implementations. The bootstrap problem is real: where do the first reference implementations come from?

**Bootstrap strategy:** Use FULL_MATCH user submissions as reference implementations. This is slow but guaranteed to produce correct references (the user's code passed matching). Over time, the reference set grows.

### Option C: Multi-Source Evidence Model

```
Problem description
  ↓
Three independent sources:
  1. CSV patterns (static, manually assigned)
  2. LLM candidate generation (dynamic, one call)
  3. User FULL_MATCH submissions (accumulated over time)
  ↓
For each pattern, count how many sources agree:
  - 3 sources agree → "high_confidence"
  - 2 sources agree → "medium_confidence"
  - 1 source only → "low_confidence"
  - 0 sources → not included
  ↓
Store with confidence level
  ↓
MatchingEngine uses groups with confidence weighting
```

**LLM calls:** 1 per problem
**Deterministic guarantees:** Multi-source agreement is a strong signal
**Failure modes:** If LLM and CSV both make the same error, it appears confirmed
**False negative risk:** Low (multiple sources catch most valid patterns)
**False positive risk:** Low (patterns need at least 2 sources)
**Works with free model:** Yes
**Implementation complexity:** Medium-high (need to reconcile three sources)
**Database changes:** Same as Option A plus confidence levels

**Assessment:** This is the most robust option in theory, but requires the CSV to be reliable and the LLM to be partially correct. The CSV has its own limitations (flat lists, no OR/AND distinction, possible errors).

---

## 9. COMPARISON TABLE

| Aspect | Option A | Option B | Option C |
|--------|----------|----------|----------|
| LLM calls per problem | 1 | 1 | 1 |
| Deterministic guarantees | Levels 1-3 | Levels 1-3 + reference confirmation | Levels 1-3 + multi-source agreement |
| False positive risk | High | Low (confirmed) / Medium (augmented) | Low |
| False negative risk | Low | Medium (AST recall) | Low |
| Free model suitability | Good | Good | Good |
| Implementation complexity | Low | Medium | Medium-high |
| Database changes | Minimal | Minimal | Minimal |
| Works without references | Yes | No (bootstrap required) | Partially (CSV + LLM) |
| ELO reliability | Low (unverified patterns) | High (confirmed patterns) | High (multi-source) |
| Scalability | Good | Good (references accumulate) | Good |
| Maintenance burden | Low | Medium | Medium |

---

## 10. RECOMMENDED ARCHITECTURE

**Option B (Reference-Solution-First) with Option C's multi-source confidence model as a fallback when references are unavailable.**

### Why Option B wins:

1. **It has the strongest ground truth guarantee.** A pattern detected in a reference implementation is known to be present in working code. No other validation method provides this guarantee.

2. **It avoids circular reasoning** by using the rule: reference validation can only confirm, never disprove.

3. **It scales over time.** As users submit solutions and receive FULL_MATCH, reference implementations accumulate automatically.

4. **It keeps LLM usage minimal.** The LLM is used only for augmentation (suggesting patterns the AST might have missed in references), not as the primary source.

5. **It degrades gracefully.** If no references exist, the system falls back to "candidate" status with reduced ELO impact.

### The bootstrap problem:

The first reference implementations must come from somewhere. Options:
- **Fastest:** Use the LLM to generate candidate solutions, then filter by AST detection. This is somewhat circular but practical.
- **Safest:** Wait for user FULL_MATCH submissions. This is slow but guaranteed correct.
- **Practical:** Use both — LLM-generated references for initial population, user-submitted references for long-term accuracy.

### Honest naming:

| State | Meaning | ELO K-factor |
|-------|---------|-------------|
| **reference_confirmed** | All patterns detected in ≥1 reference implementation | 1.0 |
| **llm_candidate** | Patterns from LLM, not yet confirmed by references | 0.5 |
| **unverified** | No LLM output or references available | 0.25 |
| **rejected** | Invalid output (structural/taxonomy failures) | 0.0 (no update) |

---

## 11. EXPLICIT ASSUMPTIONS

1. The 33-pattern taxonomy is sufficient for the current problem set. (May need expansion later.)
2. The AST engine's 99.8% precision means confirmed patterns are almost always correct.
3. The AST engine's ~84% recall means ~16% of patterns in reference implementations will be missed. This is acceptable because missed patterns remain as candidates, not removed.
4. User FULL_MATCH submissions are trustworthy reference implementations.
5. The free OpenRouter model (gpt-4o-mini) is reliable enough for candidate generation, but not for authoritative ground truth.
6. The CSV pattern data is a useful consistency signal but not authoritative.
7. The MatchingEngine's existing OR/AND semantics are correct and do not need modification.

---

## 12. KNOWN UNSOLVED PROBLEMS

1. **Group structure validation.** The system cannot determine whether patterns should be ANDed within a group or ORed across groups. The LLM makes this determination, and it's frequently wrong (50% consistency in the experiment).

2. **Complete solution coverage.** The system cannot verify that a group of patterns represents a *complete* solution approach. A group might list patterns that are present but miss a critical pattern that makes the approach work.

3. **Optimality verification.** The system cannot verify that the listed patterns represent *optimal* approaches. It can only verify that they are *valid* approaches.

4. **Pattern granularity.** Some problems require patterns at different levels of abstraction. The current taxonomy may be too coarse (e.g., `dfs_recursive` doesn't distinguish DFS for traversal vs DFS for path-finding) or too fine (e.g., `binary_search_standard` vs `binary_search_rotated` may be unnecessary distinctions for some problems).

5. **Cross-pattern dependencies.** Some patterns only make sense in combination (e.g., `two_pointers_same` often requires `linked_list_reversal` first). The current group structure doesn't capture these dependencies.

---

## 13. RISKS THAT REMAIN EVEN AFTER IMPLEMENTATION

1. **Reference implementations may be insufficient.** If a problem has 3 valid optimal approaches but only 1 reference implementation exists, the other 2 approaches will not be reference-confirmed. Users who use those approaches will receive reduced ELO impact.

2. **AST recall limitations compound.** The AST's ~84% recall means that even with reference implementations, ~16% of patterns will remain unconfirmed. Over many problems, this creates a systematic bias against patterns that the AST consistently misses.

3. **LLM augmentation introduces noise.** When the LLM suggests patterns beyond what the reference implementations show, some of those suggestions will be wrong. The system must tolerate this without overreacting.

4. **Free model availability.** If the OpenRouter API is unavailable, ground truth generation fails entirely. The system must handle this gracefully (current behavior: raise GroundTruthError → HTTP 502).

5. **Evaluation remains difficult.** Even with reference-confirmed ground truth, measuring whether the system correctly evaluates user submissions requires a labeled evaluation corpus that doesn't exist yet.

---

## 14. PHASED IMPLEMENTATION ORDER

### Phase G1: Schema + Multi-Group Support
**Objective:** Store multiple solution groups per problem.
**Files:** `problem_ground_truth` table, `problem_resolver.py`, `ground_truth_builder.py`
**Changes:**
- Add `solution_groups` JSONB column
- Add `validation_status` TEXT column (default: 'unverified')
- Modify `_load_ground_truth()` to read from `solution_groups` if present
- No changes to MatchingEngine

### Phase G2: Reference Implementation Storage
**Objective:** Store reference implementations for problems.
**Files:** New `problem_references` table, new `reference_manager.py`
**Changes:**
- New table: `problem_references (problem_id, solution_code, source, detected_patterns, created_at)`
- Logic to accept FULL_MATCH submissions as reference implementations
- Logic to run AST engine on reference code to detect patterns

### Phase G3: Reference-Based Ground Truth Generation
**Objective:** Generate ground truth from reference implementations instead of (or in addition to) LLM.
**Files:** New `ground_truth_generator.py`, modified `ground_truth_builder.py`
**Changes:**
- For each problem, analyze all reference implementations with AST
- Union of detected patterns becomes the confirmed pattern set
- Group structure: patterns detected in the same reference = same group
- LLM used only to suggest patterns beyond what AST detected

### Phase G4: Reliability-Aware Scoring
**Objective:** Scale ELO and gap behavior based on ground-truth confidence.
**Files:** `persistence.py`, `elo_engine.py`, `gap_signal_engine.py`
**Changes:**
- ELO K-factor scaled by validation_status
- Gap detection gated by validation_status
- Recommendation engine gated by validation_status

### Phase G5: Evaluation Framework
**Objective:** Measure whether the new ground-truth system actually improves accuracy.
**Files:** New evaluation infrastructure
**Changes:**
- Labeled evaluation corpus (known-correct patterns per problem)
- Precision/recall measurement of ground truth generation
- End-to-end accuracy measurement

---

*End of Ground Truth Validation Stress Test*
