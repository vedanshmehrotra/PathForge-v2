# Shadow UI Implementation Report

## Summary

Implemented a simple, non-technical "Experimental Analysis" panel for the PathForge analysis view. The panel displays shadow analysis results in user-friendly language, clearly separated from the production analysis. No production scoring, verdicts, or UI was modified.

---

## Files Changed

| File | Change | Risk |
|------|--------|------|
| `pathforge-frontend/src/types/api.ts` | Added `ShadowMatchOutcome`, `ShadowAnalysisResult` interfaces; added `shadow_analysis` to `AnalyzeResponse` | None — additive types only |
| `pathforge-frontend/src/services/shadow-mapper.ts` | **NEW** — Presentation mapping layer converting internal IDs to human-readable text | None — pure function, no side effects |
| `pathforge-frontend/components/experimental-panel.tsx` | **NEW** — Visual panel component for experimental analysis display | None — new component, not wired to production |
| `pathforge-frontend/components/analysis-view.tsx` | Added import for `ExperimentalPanel`; added `<ExperimentalPanel>` at bottom of component | Minimal — 2 lines added, no existing code modified |
| `pathforge-frontend/tsconfig.json` | Added `src/services/__tests__` to exclude (no test runner installed) | None |
| `pathforge-frontend/src/services/__tests__/shadow-mapper.test.ts` | **NEW** — Unit tests for the mapper | None — test file only |

---

## UI States

### State A: CONFIRMED / Strong Evidence
```
┌─────────────────────────────────────────┐
│ 🧪 Experimental Analysis          [Beta] │
│─────────────────────────────────────────│
│ [✓ Likely match]  Confidence: High      │
│                                          │
│ LIKELY APPROACH                          │
│ [Two Pointers]                           │
│                                          │
│ WHY                                      │
│ The code exhibits Bidirectional Index    │
│ Scan patterns, consistent with a Two     │
│ Pointers approach.                       │
│                                          │
│ ▸ Developer details                      │
└─────────────────────────────────────────┘
```

### State B: UNRESOLVED / Not Enough Evidence
```
┌─────────────────────────────────────────┐
│ 🧪 Experimental Analysis          [Beta] │
│─────────────────────────────────────────│
│ [— Not enough evidence]                  │
│                                          │
│ DETECTED SIGNALS                         │
│ [Sequential Accumulation]                │
│                                          │
│ WHY                                      │
│ The code shows Sequential Accumulation   │
│ signals, but there isn't enough evidence │
│ to confirm a specific approach.          │
│                                          │
│ ▸ Developer details                      │
└─────────────────────────────────────────┘
```

### State C: CONTRADICTED / Possible Mismatch
```
┌─────────────────────────────────────────┐
│ 🧪 Experimental Analysis          [Beta] │
│─────────────────────────────────────────│
│ [? Possible mismatch]                    │
│                                          │
│ DETECTED SIGNALS                         │
│ [Approach unclear]                       │
│                                          │
│ WHY                                      │
│ The code appears to use a different      │
│ approach from the one expected for this  │
│ problem.                                 │
│                                          │
│ ▸ Developer details                      │
└─────────────────────────────────────────┘
```

### State D: No Shadow Data
Panel is completely hidden. No error, no empty state, no impact on the page.

---

## User-Facing Wording

| Internal Term | User-Facing Wording |
|---------------|-------------------|
| `CONFIRMED` | "Likely match" |
| `UNRESOLVED` | "Not enough evidence" |
| `CONTRADICTED` | "Possible mismatch" |
| `strategy_id: two_pointers_opposite` | "Two Pointers" |
| `strategy_id: binary_search` | "Binary Search" |
| `strategy_id: sliding_window` | "Sliding Window" |
| `strategy_id: dfs_backtracking` | "DFS / Backtracking" |
| `strategy_id: bfs_shortest_path` | "BFS / Shortest Path" |
| `strategy_id: dp_top_down` | "Dynamic Programming (Top-Down)" |
| `strategy_id: dp_bottom_up` | "Dynamic Programming (Bottom-Up)" |
| `strategy_id: union_find` | "Union-Find" |
| `strategy_id: monotonic_stack_strategy` | "Monotonic Stack" |
| confidence ≥ 0.8 | "High" |
| confidence 0.5–0.8 | "Medium" |
| confidence < 0.5 | "Low" |
| UNRESOLVED confidence | "—" (dash) |
| `structural_facts` | Not shown |
| `extractor_version` | Developer details only |
| `authority_tier` | Developer details only |
| `presence_confidence` | Developer details only |

---

## Developer-Only Information

The "Developer details" section (collapsed by default) shows:

- Outcome (CONFIRMED/UNRESOLVED/CONTRADICTED)
- Authority tier
- Fact count
- Latency (ms)
- Extractor version
- Strategy list with confidence percentages
- Technique list with confidence percentages
- Reasoning strings (up to 5)

---

## Tests

| Test Case | Description |
|-----------|-------------|
| `visibility — null` | Panel hidden when shadow is null |
| `visibility — undefined` | Panel hidden when shadow is undefined |
| `visibility — null outcome` | Panel hidden when match_outcome is null |
| `visibility — present` | Panel visible when match_outcome exists |
| `CONFIRMED — status` | Shows "Likely match" status |
| `CONFIRMED — approach` | Shows human-readable strategy name |
| `CONFIRMED — High confidence` | Score ≥ 0.8 → "High" |
| `CONFIRMED — Medium confidence` | Score 0.5–0.8 → "Medium" |
| `CONFIRMED — explanation` | Generates explanation with strategy + technique names |
| `UNRESOLVED — status` | Shows "Not enough evidence" |
| `UNRESOLVED — confidence dash` | Confidence shows "—" |
| `UNRESOLVED — no techniques` | Generic explanation |
| `UNRESOLVED — with techniques` | Shows technique signal names |
| `UNRESOLVED — 2 candidates` | Shows up to 2 approach names |
| `UNRESOLVED — 3+ candidates` | Shows "Approach unclear" |
| `CONTRADICTED — status` | Shows "Possible mismatch" |
| `CONTRADICTED — explanation` | Shows "different approach" explanation |
| `malformed — empty strategies` | Handles gracefully |
| `malformed — empty techniques` | Handles gracefully |
| `malformed — unknown strategy_id` | Falls back to raw ID |
| `malformed — unknown technique_id` | Shows raw ID in explanation |
| `production unchanged — no mutation` | Input object not modified |
| `production unchanged — developer details` | Raw internal data preserved for devs |

---

## Production Analysis/Scoring Unchanged

✅ **Confirmed unchanged:**

- `run_analysis()` — not modified
- `run_persistence()` — not modified
- Production verdict logic — not modified
- ELO computation — not modified
- Topic profiles — not modified
- Gap signals — not modified
- Recommendations — not modified
- Database authority behavior — not modified
- Existing user-facing result panels — not modified (only new panel added)

The ExperimentalPanel:
- Only renders when `shadow_analysis` is present in the API response
- Is visually distinct (dashed border, "Beta" badge, secondary styling)
- Does not affect any production state
- Does not send any data back to the server
- Is purely a read-only display of shadow analysis metadata
