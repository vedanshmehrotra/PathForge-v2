# ARCHITECTURE FINAL RECONCILIATION

**Status:** Final architecture. Pending implementation approval.
**Date:** August 20, 2026
**Basis:** Complete code audit, all stress tests, all investigations

---

## 1. FINAL END-TO-END ARCHITECTURE

### Current data flow (verified from code):

```
User submits code
  │
  ▼
POST /analyze (pathforge/api/routes/analyze.py)
  │
  ├─→ resolve_problem() (pathforge/services/problem_resolver.py)
  │     ├─→ _find_problem_in_db() → SELECT from problems
  │     ├─→ _fetch_and_store_problem() → GraphQL → INSERT INTO problems
  │     ├─→ _ensure_ground_truth() → if missing: build_ground_truth()
  │     │     ├─→ call_llm(description) → {"patterns": [...], "confidence": {...}}
  │     │     ├─→ _normalize_patterns() → filter to ALL_PATTERNS (33 entries)
  │     │     └─→ _store_ground_truth() → INSERT INTO problem_ground_truth
  │     └─→ _load_ground_truth() → wraps flat list into [group_0]
  │
  ├─→ run_analysis(code, groups) (pathforge/api/services/analysis.py)
  │     ├─→ ASTAnalysisEngine.analyze(code) → {detected_patterns: [...]}
  │     ├─→ Extract groups: [g["patterns"] for g in groups]
  │     └─→ MatchingEngine.match(llm_input, ast_output)
  │           ├─→ _normalize_llm() → extract pattern sets from groups
  │           ├─→ _compute_group_matches() → AND within group
  │           ├─→ _decide_match_result() → FULL_MATCH if any group fully matched
  │           └─→ returns {match_result, matched_groups, unmatched_patterns, confidence_score}
  │
  └─→ run_persistence() (pathforge/services/persistence.py)
        ├─→ submissions table (verdict, detected_pattern, expected_pattern)
        ├─→ gap_signals (missing patterns → gap)
        ├─→ user_pattern_elo (ELO update based on match_result)
        └─→ recommendations
```

### Proposed data flow (with two-layer model):

```
OFFLINE (once per problem):
  Problem added
    │
    ├─→ Layer B: Algorithmic Claims
    │     ├─→ LLM generates candidate solution groups
    │     ├─→ Taxonomy + structural validation
    │     ├─→ Store as llm_proposed
    │     └─→ CSV cross-reference → store as externally_listed (if matches)
    │
    └─→ Layer A: Structural Observation (accumulates over time)
          ├─→ User submissions analyzed by AST
          ├─→ Full pattern sets stored per submission
          ├─→ Batch clustering identifies repeated patterns
          └─→ Promote to structurally_observed when threshold met

RUNTIME (per user submission):
  User submits code
    │
    ├─→ AST analysis (deterministic, no LLM)
    │     └─→ detects structural patterns in code
    │
    ├─→ Load ground truth (from database, no LLM)
    │     └─→ returns solution groups + evidence states
    │
    ├─→ Matching (deterministic)
    │     └─→ compares detected patterns against solution groups
    │
    ├─→ Authority gating (NEW)
    │     ├─→ If GT is llm_proposed: match result is INFORMATIONAL ONLY
    │     ├─→ If GT is externally_listed: match result is PROVISIONAL
    │     └─→ If GT is structurally_observed: match result is AUTHORITATIVE
    │
    ├─→ ELO update (gated by authority)
    │     ├─→ llm_proposed: K=0 (no update)
    │     ├─→ externally_listed: K=0.5
    │     └─→ structurally_observed: K=1.0
    │
    ├─→ Gap detection (gated by authority)
    │     ├─→ llm_proposed: SUPPRESSED
    │     ├─→ externally_listed: ACTIVE (flagged)
    │     └─→ structurally_observed: ACTIVE
    │
    └─→ Recommendations (gated by authority)
          ├─→ llm_proposed: SUPPRESSED
          ├─→ externally_listed: ACTIVE (lower priority)
          └─→ structurally_observed: ACTIVE
```

---

## 2. WHERE STRUCTURAL OBSERVATION ENDS AND ALGORITHMIC AUTHORITY BEGINS

### Layer A: Structural Observation

**Question answered:** "What patterns does the AST repeatedly detect in user code for this problem?"

**Source:** AST analysis of user submissions + clustering

**What it proves:** The structural pattern is present in multiple real implementations

**What it does NOT prove:**
- That the pattern is algorithmically correct for this problem
- That the implementations are independent (could be copies)
- That the implementation is correct (could be buggy code with correct structure)
- That the pattern is the primary algorithmic strategy

**Example:** 5 users submit code that uses `set()` for membership testing. AST detects `hash_map_lookup` in all 5. Structural observation: `hash_map_lookup` is structurally repeated. Algorithmic claim: NOT established — `set()` membership is not the same as hash map lookup as an algorithmic strategy.

### Layer B: Algorithmic Claims

**Question answered:** "What approaches are believed to be valid for this specific problem?"

**Sources:** LLM proposal, CSV listing, (future: reference implementations)

**What it proves:** At least one source claims this pattern is relevant

**What it does NOT prove:**
- That the source is correct
- That the pattern is optimal
- That the pattern is the primary approach
- That OR vs AND relationships are correct

**Example:** LLM proposes `["binary_search_standard"]` for Two Sum. This is an algorithmic claim. It is not verified. The matching engine should treat this claim as provisional, not authoritative.

### The boundary:

The matching engine sits at the boundary. It takes:
- Layer A output (detected patterns from AST)
- Layer B output (solution groups from GT)

And produces a match result. But the match result's AUTHORITY depends on Layer B's evidence state:
- If Layer B is weak (llm_proposed): match result is informational
- If Layer B is moderate (externally_listed): match result is provisional
- If Layer B is strong (structurally_observed): match result is authoritative

---

## 3. AUTHORITY STATES AND EXACT MEANINGS

| State | What was observed | What can be inferred | Authority level |
|-------|------------------|---------------------|----------------|
| **structurally_observed** | ≥2 submissions from different users (with code similarity below threshold) detected with the same primary pattern by AST | The structural pattern appears in multiple independent implementations | AUTHORITATIVE for matching; PROVISIONAL for algorithmic correctness |
| **externally_listed** | Pattern appears in the CSV `pattern` column | A prior process assigned this pattern | PROVISIONAL for matching; UNVERIFIED for algorithmic correctness |
| **llm_proposed** | Pattern from LLM output, passed taxonomy + structural validation | Pattern is valid vocabulary; structure is sane | INFORMATIONAL only |
| **unobserved** | No evidence from any source | Nothing | NONE |
| **conflicted** | Multiple sources disagree on pattern assignment | The assignment is uncertain | NONE (all candidates considered) |

### Promotion rules:

| From | To | Required evidence |
|------|----|-------------------|
| unobserved | llm_proposed | LLM output passes taxonomy + structural validation |
| unobserved | externally_listed | Pattern appears in CSV for this problem |
| llm_proposed | structurally_observed | ≥2 independent submissions detected with this pattern |
| externally_listed | structurally_observed | ≥2 independent submissions detected with this pattern |
| any | conflicted | Two or more independent sources disagree |

### Demotion rules:

| From | To | Trigger |
|------|----|---------|
| structurally_observed | conflicted | New evidence contradicts (e.g., CSV says different pattern) |
| llm_proposed | unobserved | Evidence source retracted |
| any | conflicted | Explicit human review marks as uncertain |

**No automatic demotion from structurally_observed.** Once structural evidence exists, it persists until contradicted.

### Granularity:

States apply to **individual patterns**, not problems or groups.

```
Problem: "Two Sum"
  hash_map_lookup: structurally_observed (8 independent submissions)
  two_pointers_opposite: externally_listed (CSV)
  sorting: llm_proposed (LLM only)
```

---

## 4. DOWNSTREAM PERMISSION MATRIX

| Evidence state | Can affect match result? | Can affect ELO? | Can affect gap detection? | Can affect recommendations? | User display |
|---------------|------------------------|----------------|--------------------------|----------------------------|-------------|
| **structurally_observed** | Yes (authoritative) | Yes (K=1.0) | Yes | Yes | "Common approach" |
| **externally_listed** | Yes (provisional) | Yes (K=0.5) | Yes (flagged as "externally sourced") | Yes (lower priority) | "Listed approach" |
| **llm_proposed** | Yes (informational only) | **No (K=0)** | **No** | **No** | "Possible approach" |
| **unobserved** | Yes (informational only) | **No (K=0)** | **No** | **No** | Hidden |
| **conflicted** | Yes (all candidates) | **No (K=0)** | **No** | **No** | "Uncertain" |

### What "informational only" means:

The match result is returned to the user as structural information ("your code contains pattern X"), but it does NOT determine the `pass`/`fail` verdict that feeds into ELO, gap signals, or recommendations.

### What "provisional" means:

The match result CAN affect ELO and gaps, but with reduced authority (K=0.5). The system is saying "we think this is right, but we're not sure."

### What "authoritative" means:

The match result has full authority. The system has sufficient evidence to make confident judgments.

---

## 5. COLD-START BEHAVIOR

### New problem with zero submissions:

```
Problem added to system
  │
  ├─→ Layer B: LLM generates candidate groups
  │     └─→ Stored as llm_proposed
  │
  └─→ Runtime behavior:
        ├─→ Matching: runs (informational only)
        ├─→ Match verdict: informational (no pass/fail)
        ├─→ ELO: NO UPDATE (K=0)
        ├─→ Gap signals: SUPPRESSED
        ├─→ Recommendations: SUPPRESSED
        └─→ User display: "Analysis in progress — patterns not yet validated"
```

### When cold-start ends:

The problem transitions out of cold-start when:
- ≥1 pattern reaches `structurally_observed` OR `externally_listed` status

### What this means for users:

- **During cold start:** Users receive structural analysis (what patterns their code contains) but no skill rating impact. This is honest — the system doesn't know enough to judge.
- **After cold start:** Users receive full analysis with appropriate authority levels.

### Cold-start duration estimate:

With the CSV providing external listings for 300 problems, most existing problems would immediately have `externally_listed` status. Only new problems not in the CSV would experience cold-start.

---

## 6. MULTI-SOLUTION GROUP MODEL

### Current state:

- MatchingEngine supports OR across groups, AND within groups
- LLM prompt produces flat pattern list
- `_load_ground_truth()` wraps into single group_0
- `run_persistence()` has bug: uses first pattern from first group

### Proposed model:

```
Problem: "Binary Tree Level Order Traversal"
  solution_groups: [
    {patterns: ["bfs_level_order"], evidence: "structurally_observed"},
    {patterns: ["dfs_recursive"], evidence: "externally_listed"}
  ]
```

Semantics: `(bfs_level_order)` OR `(dfs_recursive)`

A user matching either group gets FULL_MATCH against that group.

### Matching behavior with multiple groups:

```
User implements BFS → detects bfs_level_order
  → Group 0 fully matched → FULL_MATCH (authoritative if structurally_observed)
  → User gets pass, ELO update for bfs_level_order

User implements DFS → detects dfs_recursive
  → Group 1 fully matched → FULL_MATCH (provisional if externally_listed)
  → User gets pass, ELO update for dfs_recursive (K=0.5)
```

### Evidence state per group:

Each group inherits the MINIMUM evidence state of its patterns:
- If any pattern in the group is `llm_proposed` → group is `llm_proposed`
- If all patterns are `externally_listed` → group is `externally_listed`
- If all patterns are `structurally_observed` → group is `structurally_observed`

---

## 7. INDEPENDENCE CRITERIA FOR REPEATED SUBMISSIONS

### What is available:

| Data | Available? | Independence signal |
|------|-----------|-------------------|
| `user_id` | Yes | Weak (users can copy) |
| `code_text` (1000 chars) | Yes | Moderate (can detect exact copies) |
| `detected_pattern` (single) | Yes | None (not a fingerprint) |
| `submitted_at` | Yes | Weak (temporal separation) |
| Full AST output | **NO** | Would be strong |
| Code hash | **NO** | Would detect exact copies |

### Independence model:

```python
def estimate_independence(sub_a, sub_b):
    """Returns 0.0-1.0 confidence that submissions are independent."""
    if sub_a.user_id == sub_b.user_id:
        return 0.0  # Same person
    
    if sub_a.code_hash == sub_b.code_hash:
        return 0.0  # Exact copy
    
    confidence = 0.5  # Base: different users
    
    # Temporal separation
    hours_apart = abs(sub_a.timestamp - sub_b.timestamp).hours
    if hours_apart > 24:
        confidence += 0.2
    if hours_apart > 168:  # 1 week
        confidence += 0.1
    
    # Different primary patterns (different approaches = more independent)
    if sub_a.primary_pattern != sub_b.primary_pattern:
        confidence += 0.1
    
    return min(confidence, 1.0)

# Threshold: confidence >= 0.7 to count as "independent"
```

### What needs to be stored:

- `code_hash` (SHA-256 of normalized code) per submission
- Full `detected_patterns_json` (all patterns, not just primary) per submission

---

## 8. ALL KNOWN CIRCULAR REASONING RISKS

### Risk 1: GT shapes user behavior → user submissions reinforce GT

```
GT: ["hash_map_lookup"]
  → Users implement hash_map_lookup (influenced by GT or learning conventions)
  → Clustering sees many hash_map_lookup submissions
  → Promotes to structurally_observed
  → GT appears "confirmed"
```

**Severity:** MEDIUM. Self-correcting over time as new users solve independently. But creates a bias window.

**Mitigation:** Clustering should note when all observed submissions have similar structure (possible tutorial copying). The independence model helps here.

### Risk 2: Wrong GT → correct users penalized → wrong GT appears correct

```
Wrong GT: ["binary_search_standard"] for Two Sum
  → Correct users (hash map) get NO_MATCH → ELO penalty
  → Wrong users (binary search) get FULL_MATCH → ELO reward
  → ELO data suggests binary search is the correct approach
  → System appears to "confirm" wrong GT through ELO signals
```

**Severity:** HIGH during cold-start. Mitigated by K=0 for llm_proposed.

**Mitigation:** Cold-start ELO suppression prevents this entirely. After cold-start, the risk is lower because structurally_observed patterns are more reliable.

### Risk 3: Clustering merges different algorithms

```
Algorithm A: hash map lookup
Algorithm B: set membership (structurally similar)
  → Both detected as hash_map_lookup by AST
  → Clustering merges them into one group
  → Appears as strong evidence for hash_map_lookup
```

**Severity:** LOW-MEDIUM. The structural detection is correct (both use membership checks). The algorithmic label may be imprecise, but the matching behavior is reasonable.

**Mitigation:** Accept that AST-level pattern classification is approximate. The matching engine works at the pattern level, not the algorithm level.

### Risk 4: CSV patterns share biases with LLM

```
CSV: ["hash_map_lookup"] (possibly LLM-generated)
LLM: ["hash_map_lookup"] (definitely LLM-generated)
  → Both agree → appears as two independent sources
  → But they may share the same bias
```

**Severity:** LOW. The CSV and LLM are independent processes, even if they share training data biases.

**Mitigation:** Track CSV provenance. If CSV is known to be LLM-generated, treat it as supplementary evidence only.

---

## 9. EXACT INVARIANTS THE IMPLEMENTATION MUST NEVER VIOLATE

### Invariant 1: Wrong GT must never silently punish correct users

**Statement:** If the ground truth is wrong, users who implement the correct approach must not receive authoritative negative judgments.

**Implementation:** ELO updates require `structurally_observed` or `externally_listed` status. `llm_proposed` patterns produce K=0 (no ELO update).

### Invariant 2: Structural observation must not be called "validated"

**Statement:** No evidence state below full human verification may use words like "validated," "confirmed," or "verified" in user-facing displays or internal logic.

**Implementation:** Use `structurally_observed`, `externally_listed`, `llm_proposed` consistently.

### Invariant 3: The matching engine must know GT reliability

**Statement:** The matching engine must receive the evidence state of the GT and use it to determine match result authority.

**Implementation:** Pass `evidence_state` alongside `accepted_solution_groups` to `run_analysis()`.

### Invariant 4: Cold-start must suppress scoring

**Statement:** Problems with no `structurally_observed` or `externally_listed` patterns must not update ELO, gap signals, or recommendations.

**Implementation:** Check evidence state before calling ELO/gap/recommendation engines.

### Invariant 5: Persistence must store enough evidence for clustering

**Statement:** Every submission must store enough data to enable future clustering analysis without re-analyzing code.

**Implementation:** Store full AST pattern set and code hash per submission.

### Invariant 6: The persistence bug must be fixed before multi-group support

**Statement:** `expected_pattern` must be derived from the matched group, not the first group.

**Implementation:** Use `match_result["matched_groups"]` to identify the matched group.

### Invariant 7: No single evidence source is authoritative alone

**Statement:** No pattern may reach `structurally_observed` status based on a single source. At least two independent sources (or two independent submissions) are required.

**Implementation:** Enforce minimum evidence threshold in promotion logic.

### Invariant 8: The AST engine must not be bypassed by LLM verification

**Statement:** The LLM must not be called during runtime submission analysis. The AST engine is the sole runtime analysis mechanism.

**Implementation:** LLM calls remain offline only (problem preparation).

---

*End of Architecture Final Reconciliation*
