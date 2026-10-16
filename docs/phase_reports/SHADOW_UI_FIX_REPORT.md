# Shadow UI Presentation Fix Report

## Summary

Fixed contradictory UI state, stale problem selection bug, and technical wording in the Experimental Analysis panel. Added vitest infrastructure and 32 regression tests.

---

## Root Cause: Problem ID 2996 Mismatch

**Finding:** The `problemInput` state and `prep.result` state are decoupled in `analysis-view.tsx`.

**Mechanism:**
1. User enters problem ID (e.g., 3718) and clicks Prepare → `prep.result` stores { leetcode_id: 3718, title: "Smallest Missing Multiple of K" }
2. User changes the input text to "2996" but does NOT click Prepare again
3. `prep.result` still holds the OLD problem data (problem 3718)
4. User clicks Run Analysis → `handleRun()` sends `leetcode_id: 3718` (not 2996)
5. UI shows the stale title "Smallest Missing Multiple of K" even though the input says "2996"

**Classification:** Frontend stale state bug (not a backend data issue, not a wrong problem lookup, not a GraphQL issue).

**Fix:** Added `handleProblemInputChange()` that clears `prep.result` whenever the input text changes after a prepare has been completed. The user must click Prepare again for any changed input.

---

## UI Changes

### 1. Contradictory State Fix (`shadow-mapper.ts`)

**Before:** CONFIRMED + no strategies + no techniques → approaches = `['Approach unclear']` → contradictory with "Likely match" status.

**After:**
- CONFIRMED with no strategies → falls back to technique names (e.g., "Running total")
- CONFIRMED with no strategies AND no techniques → shows `['Approach detected']`
- Never shows "Approach unclear" for CONFIRMED outcomes

**Confidence for non-CONFIRMED:** UNRESOLVED and CONTRADICTED now always show `'—'` instead of numeric values.

### 2. Stale State Fix (`analysis-view.tsx`)

Added `handleProblemInputChange()` that:
- Clears `prep.result` when the user edits the input after a prepare
- Ensures the displayed problem always matches the input field
- Prevents sending stale problem IDs to `/analyze`

### 3. Plain Language (`shadow-mapper.ts`)

**Technique name mapping (before → after):**
- `sequential_accumulation` → "Running total"
- `bidirectional_index_scan` → "Two-way scan"
- `recursive_branching` → "Recursive branching"
- `carry_propagation` → "Carry propagation"
- `loop_state_tracking` → "State tracking in loops"
- `iterative_table_filling` → "Table building"
- `linked_list_traversal` → "Linked list walk"
- `fixed_window_maintenance` → "Fixed window"
- `monotonic_stack_maintenance` → "Monotonic stack"

**Explanation text (before → after):**
- "The code exhibits X patterns, consistent with a Y approach." → "The solution follows a Y approach for this problem."
- "The code shows X signals, but there isn't enough evidence..." → "The code contains some relevant patterns, but there isn't enough information..."
- Removed all internal technique jargon from user-facing explanations

### 4. Panel Label Fix (`experimental-panel.tsx`)

**Before:** Three different labels depending on status/approach combination, including "Detected signals" (technical).

**After:** Two simple labels:
- "Likely approach" when a concrete approach is shown
- "Approach" when showing "Approach unclear"

### 5. Developer Details

Already collapsed by default (`useState(false)`). No change needed — the initial report of "expanded by default" was likely from clicking the section during testing.

---

## Files Changed

| File | Change |
|------|--------|
| `pathforge-frontend/components/analysis-view.tsx` | Added `handleProblemInputChange()` to clear stale `prep.result` |
| `pathforge-frontend/src/services/shadow-mapper.ts` | Fixed CONFIRMED approach fallback, plain language, confidence for non-CONFIRMED |
| `pathforge-frontend/components/experimental-panel.tsx` | Simplified approach label logic |
| `pathforge-frontend/src/services/__tests__/shadow-mapper.test.ts` | 32 regression tests covering all states and edge cases |
| `pathforge-frontend/vitest.config.ts` | New: vitest configuration for frontend tests |
| `pathforge-frontend/package.json` | Added vitest dev dependency |

---

## Tests

**32 tests passing** covering:
- Visibility (null, undefined, null match_outcome, present match_outcome)
- CONFIRMED: status, approach names, confidence levels, explanations, technique fallback
- UNRESOLVED: status, dash confidence, generic explanation, candidate approaches, >2 candidates
- CONTRADICTED: status, approach unclear, explanation, dash confidence
- Status/approach consistency: CONFIRMED never shows "Approach unclear"
- Malformed data: empty strategies, empty techniques, unknown IDs
- Production unchanged: input object not mutated, developerDetails raw data
- Plain language: no internal IDs or jargon in user-facing text

---

## Production Behavior Verification

- **Backend:** 132 shadow tests passing, zero compilation errors
- **Frontend:** TypeScript compiles clean, 32 vitest tests passing
- **Production paths:** Zero changes to verdict, ELO, topics, gaps, recommendations, matching engine
- **Database:** No schema changes, no query changes
- **API contracts:** No request/response shape changes
