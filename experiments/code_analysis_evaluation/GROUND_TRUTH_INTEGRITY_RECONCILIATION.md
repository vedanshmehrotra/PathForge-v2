# Ground Truth Integrity Audit & Reconciliation Design

**Date:** August 28, 2026
**Status:** Design document — no code changes
**Scope:** Data integrity only — no architecture, detector, or frontend changes

---

## A. Current Ground-Truth Data Flow

```
                    problems.pattern                    problem_ground_truth.patterns
                    (DB column, jsonb)                   (DB column, text/jsonb)
                           │                                      │
    Source 1: CSV import   │   Source 2: GraphQL fetch            │   Source 3: LLM call
    (pathforge_problems_   │   (problem_resolver.py)              │   (ground_truth_builder.py)
     fixed.csv)            │                                      │
                           │                                      │
                           │         problem_ground_truth.solution_groups
                           │         (DB column, jsonb)
                           │                 │
                           │    Source 4: V1 vocabulary mapping
                           │    (_build_solution_groups)
                           │                 │
                           ▼                 ▼
                  ┌────────────────────────────────────┐
                  │   problem_resolver._load_ground_truth│
                  │   Returns (groups, confidence)      │
                  └────────────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              analyze route   shadow_runner   ProblemContext
              (production)    (shadow)        (API response)
```

### Source 1: CSV Import (`_seed_problem_bank` in `app.py`)

- **When:** On first Flask startup, if `problems` table is empty
- **What:** Reads `pathforge/data/pathforge_problems_fixed.csv`, populates `problems.pattern` as a JSON array string like `["hash_map_lookup"]`
- **Authority:** The CSV was curated by a human (or human-guided process). It contains the `pattern` column with manually assigned labels.
- **Limitation:** Only runs once (INSERT OR IGNORE). Later additions via GraphQL get `pattern: []`.

### Source 2: GraphQL Fetch (`_fetch_and_store_problem` in `problem_resolver.py`)

- **When:** When a problem is requested but not in the database
- **What:** Fetches problem data from LeetCode GraphQL, stores with `pattern: '[]'`
- **Limitation:** Does NOT populate the `pattern` column. Problems added this way have empty patterns forever.

### Source 3: LLM Ground Truth (`build_ground_truth` in `ground_truth_builder.py`)

- **When:** First time a problem's ground truth is requested (`_ensure_ground_truth`)
- **What:** Calls GPT-4o-mini with the problem description, gets back pattern labels
- **Stores:** `problem_ground_truth.patterns` (the LLM's answer) and `problem_ground_truth.solution_groups` (V1-mapped version)
- **Authority:** LLM-generated, marked as `validation_status = 'llm_proposed'`

### Source 4: V1 Vocabulary Mapping (`_build_solution_groups`)

- **When:** Part of Source 3 (builds solution groups from LLM patterns)
- **What:** Maps legacy pattern IDs to V1 technique/strategy concepts using `PATTERN_TO_V1_MAPPING`
- **Produces:** `required`, `optional`, `excluded` lists for each solution group
- **Limitation:** If the LLM produces a wrong pattern, the V1 mapping faithfully maps the wrong pattern to V1 concepts.

### The Consumption Path

`_load_ground_truth()` in `problem_resolver.py`:

1. Checks for `solution_groups` column first (Phase 4A path)
2. If solution groups exist, uses their `patterns` field as legacy patterns for the production matcher
3. If solution groups have `required` field, uses it for the shadow matcher
4. Falls back to `problem_ground_truth.patterns` if no solution groups
5. Falls back to `_map_legacy_patterns_to_v1()` to convert legacy patterns to V1 concepts

**Critical behavior:** The production matcher receives `g["patterns"]` from the solution group — which is the LLM's answer, NOT the CSV-curated pattern. This is the root of the mismatch.

---

## B. All Competing Sources

| Source | Table/Column | Populated By | Authority Level | Used By |
|--------|-------------|-------------|-----------------|---------|
| CSV import | `problems.pattern` | `_seed_problem_bank()` | Human-curated (highest) | NOT used by production matcher |
| GraphQL fetch | `problems.pattern` | `_fetch_and_store_problem()` | None (empty) | NOT used by production matcher |
| LLM generation | `problem_ground_truth.patterns` | `build_ground_truth()` | LLM-proposed | Used as fallback in `_load_ground_truth` |
| LLM generation + V1 mapping | `problem_ground_truth.solution_groups` | `_build_solution_groups()` | LLM-proposed | **Used by both production and shadow matchers** |
| Frontend display | `canonical_patterns` from API | `analyze.py` route | Derived from solution groups | Shown to user as "Expected Patterns" |

### Key Observation

**The production matcher NEVER uses `problems.pattern`.** It only uses the solution groups from `problem_ground_truth.solution_groups`, which are LLM-generated. The CSV-curated patterns exist in the database but are invisible to the matching pipeline.

---

## C. Known Conflicts

### Category 1: DB pattern ≠ GT pattern (CRITICAL)

| Problem | DB Pattern | GT Pattern | Which is correct? |
|---------|-----------|-----------|-------------------|
| 2 (Add Two Numbers) | `two_pointers_same` | `linked_list_reversal` | **Both are partially correct.** The problem involves traversing linked lists with two pointers moving in the same direction. `two_pointers_same` describes the pointer behavior; `linked_list_reversal` describes the data structure. The canonical answer for this LeetCode problem is **linked list traversal** (it's in the Linked List topic). |
| 20 (Valid Parentheses) | `monotonic_stack` | `dfs_recursive` | **DB is correct.** The canonical solution uses a stack. The LLM incorrectly classified it as `dfs_recursive` — likely because of the word "recursion" in the problem's "Recursion" topic tag (which is misleading for this problem). |
| 5 (Longest Palindromic Substring) | `dp_2d_string, two_pointers_opposite` | `dp_2d_string` | **DB is more complete.** The expand-around-center approach uses two pointers. The LLM missed this. |
| 17 (Letter Combinations) | `backtracking_subset, hash_map_lookup` | `backtracking_subset` | **DB is more complete.** The phone mapping uses a hash map. The LLM dropped it. |
| 3 (Longest Substring) | `hash_map_lookup, sliding_window_variable` | `sliding_window_variable` | **Both correct.** The hash map is used for O(1) lookups; sliding window is the primary strategy. |

### Category 2: Empty DB pattern (HIGH)

| Problem | GT Pattern | Correct? |
|---------|-----------|----------|
| 628 (Max Product Three) | `greedy_local` | **Partially correct.** The optimal solution sorts and picks the max of the two products. This is more accurately `sorting` or simple array scanning, not traditional "greedy." |
| 1574 (Max Product Two) | `greedy_local` | **Partially correct.** Similar to 628 — find two largest values. More accurately `hash_map_frequency` or simple scanning. |
| 1577 (Two Boxes) | `backtracking_subset` | **Correct.** The problem requires enumerating combinations with constraints. |
| 3236 (Prefix Sum) | `hash_map_lookup, prefix_sum` | **Partially correct.** The problem uses a prefix sum computation and a hash set for lookups. Both are valid. |
| 3812 (Palindrome) | `hash_map_frequency` | **Correct.** Count characters, build smallest palindrome. |
| 4080 (Missing Multiple) | `hash_map_frequency` | **Correct.** Build a set of existing multiples, find the missing one. |

### Category 3: Broken solution groups (MEDIUM)

| Problem | Issue |
|---------|-------|
| 2 (Add Two Numbers) | SG has `required: None` — old format without V1 mapping. Falls back to `_map_legacy_patterns_to_v1()` which correctly maps `linked_list_reversal` → `linked_list_traversal`. |
| 3236 (Prefix Sum) | SG has `required: None` — old format without V1 mapping. Falls back to `_map_legacy_patterns_to_v1()` which correctly maps to `sequential_accumulation`. |
| 4080 (Missing Multiple) | SG has `required: []` — V1-mapped but `hash_map_frequency` maps to empty required (it's "generic data-structure behavior"). |

---

## D. Root Cause

**The root cause is a single design flaw:** `problem_ground_truth.solution_groups[].patterns` is used as the legacy pattern list for the production matcher, but these patterns come from the LLM, not from the CSV-curated source.

The CSV-curated `problems.pattern` column IS the more reliable source (human-curated), but the production matcher never reads it.

**The mismatch occurs because:**
1. CSV import sets `problems.pattern = ["two_pointers_same"]`
2. LLM generates `problem_ground_truth.patterns = ["linked_list_reversal"]`
3. The production matcher uses (2), not (1)
4. The frontend displays (2) as "Expected Patterns"
5. The AST detector detects `two_pointers_same`, not `linked_list_reversal`
6. The matcher reports NO_MATCH

---

## E. Proposed Authoritative Data Model

### Current Schema

```sql
-- problems table
problems.pattern  -- jsonb, set by CSV import or empty for GraphQL additions

-- problem_ground_truth table  
problem_ground_truth.patterns       -- text/jsonb, LLM-generated
problem_ground_truth.confidence     -- text/jsonb, LLM-generated
problem_ground_truth.solution_groups -- jsonb, V1-mapped from LLM patterns
problem_ground_truth.validation_status -- text, always 'llm_proposed'
```

### Proposed Schema Changes

**None.** The existing schema is sufficient. The fix is in how data is populated and consumed.

### Proposed Data Model

```
Canonical Ground Truth = CSV-curated problems.pattern (highest authority)
Supplementary Ground Truth = LLM-generated problem_ground_truth (lower authority)

The production matcher should use the CSV-curated pattern as the primary expected set.
The LLM-generated pattern should be used ONLY when:
  1. problems.pattern is empty (new problem not in CSV)
  2. The LLM pattern is a superset of the CSV pattern (additional context)
```

---

## F. Provenance Model

Each solution group should carry explicit provenance:

```json
{
  "id": "group_0",
  "patterns": ["two_pointers_same"],
  "required": ["bidirectional_index_scan"],
  "optional": [],
  "excluded": ["two_pointers_opposite"],
  "provenance": ["csv_curated"],
  "authority_tier": "human_curated",
  "validation_status": "verified",
  "confidence": {"two_pointers_same": 0.9}
}
```

### Authority tiers (ordered):

1. `human_curated` — CSV import, manually verified
2. `editorial` — From LeetCode editorial/reference solutions
3. `llm_verified` — LLM-generated but verified by human
4. `llm_proposed` — LLM-generated, unverified
5. `unobserved` — No ground truth available

---

## G. Conflict Handling

### Rule 1: If CSV pattern exists, use it as primary

When `problems.pattern` is non-empty and `problem_ground_truth.solution_groups` exists:
- Use `problems.pattern` as the legacy pattern list for the production matcher
- Keep the LLM solution groups for the shadow matcher (V1 vocabulary)
- Mark the group provenance as `csv_curated`

### Rule 2: If only LLM ground truth exists, use it but mark unverified

When `problems.pattern` is empty and `problem_ground_truth.solution_groups` exists:
- Use the LLM solution groups
- Mark provenance as `llm_proposed`
- Display "Unverified" badge in the UI (future)

### Rule 3: If no ground truth exists, refuse to match

When neither source has data:
- The production matcher should NOT fall back to `[[hash_map_lookup]]`
- Return `NO_MATCH` with reason "No ground truth available for this problem"
- The frontend should show "No expected patterns" instead of a misleading match

### Rule 4: Conflicts are logged, not silently resolved

When CSV and LLM disagree:
- Log the conflict
- Use the CSV pattern as authoritative
- Keep the LLM pattern in a `conflicting_patterns` field for future review

---

## H. Minimum Safe Fix

### The single change that prevents bad ground-truth labels from telling a correct user their solution is wrong:

**In `problem_resolver.py:_load_ground_truth()`, when solution groups are loaded, check if `problems.pattern` exists and is non-empty. If so, replace the solution group's `patterns` field with the CSV-curated pattern.**

This means:
1. The production matcher compares against the CSV-curated pattern
2. The shadow matcher continues using V1 concepts from the LLM solution groups
3. No schema changes required
4. No frontend changes required
5. No detector changes required

### Specific change location:

```python
# In _load_ground_truth(), after building groups from solution_groups:
# Add a reconciliation step:

def _load_ground_truth(connection, problem_id):
    # ... existing code to load solution_groups ...
    
    # NEW: Reconcile with CSV-curated patterns
    csv_patterns = _load_csv_patterns(connection, problem_id)
    if csv_patterns:
        for g in groups:
            if g.get("patterns") != csv_patterns:
                # Log the conflict
                import logging
                logging.getLogger(__name__).warning(
                    "Ground truth conflict for problem %d: "
                    "CSV=%s, LLM=%s. Using CSV.",
                    problem_id, csv_patterns, g.get("patterns")
                )
                # Use CSV as authoritative
                g["patterns"] = csv_patterns
                g["provenance"] = g.get("provenance", []) + ["csv_curated_override"]
                g["authority_tier"] = "human_curated"
    
    return groups, confidence

def _load_csv_patterns(connection, problem_id):
    """Load the CSV-curated pattern from problems.pattern."""
    row = connection.execute(
        "SELECT pattern FROM problems WHERE id = %s", (problem_id,)
    ).fetchone()
    if not row:
        return None
    pattern = row["pattern"]
    if isinstance(pattern, str):
        pattern = json.loads(pattern)
    if pattern and isinstance(pattern, list):
        return pattern
    return None
```

### Why this is the minimum safe fix:

1. **Single function change** — only `problem_resolver.py` is modified
2. **No schema changes** — both columns already exist
3. **No detector changes** — the AST detectors are unchanged
4. **No frontend changes** — the API response format is unchanged
5. **No behavioral change for correct cases** — when CSV and LLM agree, nothing changes
6. **Fixes the critical bug** — when they disagree, the CSV-curated pattern is used
7. **Preserves shadow analysis** — the shadow matcher still uses V1 concepts from the LLM solution groups
8. **Adds provenance** — conflicts are logged and traceable

---

## I. Migration Plan

### Phase 1: Add reconciliation logic (IMMEDIATE)

1. Add `_load_csv_patterns()` to `problem_resolver.py`
2. Add reconciliation check in `_load_ground_truth()`
3. Add logging for conflicts
4. Update `ProblemContext` to include `pattern_source` field (for debugging)

### Phase 2: Verify all 18 problems (AFTER Phase 1)

1. Run reconciliation on all 18 problems with ground truth
2. Verify that the 11 mismatched problems now use CSV patterns
3. Verify that the 7 matching problems are unchanged
4. Verify that the 6 problems with empty DB patterns continue using LLM patterns

### Phase 3: Fix empty DB patterns (AFTER Phase 2)

For problems with empty `problems.pattern` but non-empty GT patterns:
1. If the GT pattern is clearly correct (e.g., 3812, 4080), backfill `problems.pattern` from GT
2. If the GT pattern is uncertain (e.g., 628, 1574), mark as `validation_status = 'needs_review'`

### Phase 4: Add provenance tracking (FUTURE)

1. Add `pattern_source` column to `problem_ground_truth` table
2. Track whether pattern came from CSV, LLM, or reconciliation
3. Add `conflicting_patterns` column for audit trail

---

## J. Regression Tests Required

### Test 1: CSV pattern takes precedence over LLM pattern

```python
def test_csv_pattern_overrides_llm_ground_truth():
    """When problems.pattern and GT patterns disagree, CSV wins."""
    # Setup: problem with DB pattern=['two_pointers_same']
    #        GT patterns=['linked_list_reversal']
    # Expected: production matcher uses ['two_pointers_same']
    #           shadow matcher uses V1 concepts from ['linked_list_reversal']
```

### Test 2: Empty DB pattern falls back to LLM

```python
def test_empty_db_pattern_uses_llm_ground_truth():
    """When problems.pattern is empty, GT patterns are used."""
    # Setup: problem with DB pattern=[]
    #        GT patterns=['hash_map_frequency']
    # Expected: both matchers use GT patterns
```

### Test 3: No ground truth produces clear error

```python
def test_no_ground_truth_refuses_to_match():
    """When no ground truth exists, matching is skipped."""
    # Setup: problem with DB pattern=[] and no GT record
    # Expected: match_result indicates no ground truth available
```

### Test 4: Conflict is logged

```python
def test_ground_truth_conflict_is_logged():
    """When CSV and LLM disagree, the conflict is logged."""
    # Setup: problem with DB pattern=['A'] and GT patterns=['B']
    # Expected: warning log message with both values
```

### Test 5: Existing correct cases unchanged

```python
def test_matching_cases_unchanged():
    """When CSV and LLM agree, behavior is identical."""
    # Setup: problem 11 (Container With Most Water)
    # Expected: FULL_MATCH with same confidence
```

### Test 6: Shadow matcher unaffected

```python
def test_shadow_matcher_uses_v1_concepts():
    """Shadow matcher continues using V1 vocabulary, not legacy patterns."""
    # Setup: any problem with solution groups
    # Expected: shadow uses required/optional/excluded, not patterns
```

---

## Summary

| Aspect | Current | Proposed |
|--------|---------|----------|
| Authoritative source | LLM solution groups | CSV `problems.pattern` |
| Fallback when empty | `[[hash_map_lookup]]` | Refuse to match |
| Conflict resolution | Silent (LLM wins) | Explicit (CSV wins, logged) |
| Provenance tracking | None | `provenance` field on groups |
| Schema changes | None | None |
| Code changes | — | 1 function in `problem_resolver.py` |
| Frontend changes | None | None (future: "Unverified" badge) |
| Risk | Users told wrong answers | Users told correct answers or "no ground truth" |
