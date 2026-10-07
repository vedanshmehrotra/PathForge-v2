# Matching Engine Report — Phase 3D

**Date:** 2026-07-04  
**Status:** COMPLETE  
**Reference:** Phase 3D Objective Specification

---

## Files

| File | Path |
|------|------|
| Matching Engine | `src/matching_engine/matching_engine.py` |
| Package Init | `src/matching_engine/__init__.py` |
| Tests | `src/matching_engine/tests/test_matching_engine.py` |
| Test Init | `src/matching_engine/tests/__init__.py` |

---

## Architecture

The Matching Engine is the FIRST system layer that interprets AST outputs.
It sits downstream of the AST detection system and upstream of any future
(Gap Signal Engine, Elo system, Recommendations).

```
LLM Output ─┐
             ├──→ MatchingEngine → structured decision
AST Output ──┘
```

It is:
- Deterministic (same inputs → same outputs)
- Pattern-level only (no problem-specific logic)
- Stateless (no mutable state between calls)

---

## Matching Algorithm

### Step 1: Normalize AST
- Convert `ast_output` list into `{pattern_id: max_confidence}` dict
- Drop entries with zero confidence or empty pattern_id
- Duplicate pattern IDs use the highest confidence seen

### Step 2: Normalize LLM
- Convert `accepted_solution_groups` into `list[set[str]]`
- Drop empty strings and empty groups

### Step 3: Compute Group Matches
For each LLM group:
- Compute `matched = group ∩ ast_patterns`
- Compute `missing = group - ast_patterns`
- `coverage = len(matched) / len(group)`
- `is_fully_matched = coverage == 1.0`
- `avg_confidence = Σ ast_confidence(matched_patterns) / len(matched)`

### Step 4: Compute Confidence
- Find the best group (highest confidence) among all groups
- `confidence = best_group.weighted_sum / best_group.size`
- Penalty: extra AST patterns (not in any LLM group) reduce score by `0.1 × Σ(extra_ast_confidence)`
- Clamped to [0.0, 1.0]

### Step 5: Decide Match Result
- **FULL_MATCH**: At least one group fully matched AND confidence >= 0.6
- **PARTIAL_MATCH**: Some overlap exists but no full group match, or confidence < 0.6
- **NO_MATCH**: No overlap, or empty input on either side

### Step 6: Build Output
- `match_result`: str
- `matched_groups`: list of indices of fully matched groups
- `unmatched_patterns`: list of LLM patterns not found in AST
- `confidence_score`: float (rounded to 4 decimal places)
- `reasoning_signals`: list of signal strings for diagnostics

---

## Decision Threshold

| Constant | Value | Purpose |
|----------|-------|---------|
| `MATCH_THRESHOLD` | 0.6 | Minimum confidence for FULL_MATCH |
| `EXTRA_PATTERN_PENALTY` | 0.1 | Per-unit penalty multiplier for extra AST patterns |

---

## Edge Cases Handled

### Multiple AST detections per solution
- Duplicate pattern entries in AST output use the highest confidence
- Extra patterns not in any LLM group incur a small penalty

### Overlapping patterns
- Patterns that appear in multiple LLM groups are evaluated independently
- Each group is matched independently; multiple groups can be fully matched

### Weak confidence signals
- Low-confidence AST detections produce proportionally lower match confidence
- If confidence falls below 0.6, even a fully matched group becomes PARTIAL

### Missing AST coverage
- LLM patterns not found in AST reduce group coverage
- Groups without full coverage cannot trigger FULL_MATCH

### Extra LLM patterns not detected by AST
- Listed in `unmatched_patterns`
- Reduce confidence through lower group coverage
- Do not prevent other groups from matching fully

### Empty inputs
- Empty LLM groups or empty AST output → `NO_MATCH`, confidence 0.0
- Both empty → `NO_MATCH`, confidence 0.0

### Zero-confidence AST patterns
- Filtered out during normalization (treated as not detected)

---

## Mismatch Behavior

| Scenario | Match Result | Confidence | Reasoning |
|----------|-------------|------------|-----------|
| All LLM patterns detected, high confidence | FULL_MATCH | ≥0.6 | Group fully matched |
| One group fully matched, others partial | FULL_MATCH | Best group confidence | Strong structural alignment exists |
| Some overlap, no full group match | PARTIAL_MATCH | < 0.6 | Missing key patterns |
| Fully matched but low confidence | PARTIAL_MATCH | < 0.6 | Weak structural signal |
| No overlapping patterns | NO_MATCH | 0.0 | No structural alignment |
| Empty AST output | NO_MATCH | 0.0 | No signals generated |
| Empty LLM input | NO_MATCH | 0.0 | No expectations to match against |

---

## Partial Match Logic

Partial match is the default when:
1. Some AST patterns overlap with some LLM group patterns, but NO group is fully covered
2. OR a group is fully covered but at confidence < 0.6 (weak alignment)
3. OR multiple groups have partial overlap and none are fully matched

Partial match signals:
- `unmatched_patterns` lists specific LLM patterns not detected
- Reasoning signals include per-group coverage ratios

---

## Performance Notes

- O(n × m) where n = LLM groups, m = patterns per group (typically very small: n ≤ 3, m ≤ 5)
- No external dependencies beyond Python stdlib
- Stateless: no caching, no mutable state
- Safe for concurrent use (pure function per `match()` call)

---

## Regression Tests

All 519 tests pass:
- 472 AST detection tests (unchanged)
- 47 Matching Engine tests (new)

Test breakdown:
- Initialization: 2 tests
- AST normalization: 6 tests
- LLM normalization: 6 tests
- FULL_MATCH: 4 tests
- PARTIAL_MATCH: 3 tests
- NO_MATCH: 5 tests
- Confidence score: 5 tests
- Unmatched patterns: 2 tests
- Output structure: 3 tests
- Reasoning signals: 3 tests
- Edge cases: 5 tests
- Determinism: 2 tests
- MatchResult dataclass: 1 test (parametrized to 3)

---

## AST System Invariant

The Matching Engine treats AST as a **signal generator only**.
It does NOT:
- Call any detector
- Access any AST internals
- Modify detector outputs
- Evaluate correctness of AST patterns

AST remains complete and frozen.

---

## Stop Condition

Phase 3D Matching Engine implementation complete.
Do NOT proceed to Gap Signal Engine, Elo system, or Recommendations.
