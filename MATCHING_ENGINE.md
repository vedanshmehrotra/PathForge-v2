# Matching Engine

Version: 1.0
Status: Design — Frozen for Phase 3C
Last Updated: 2026-07-03

---

## 1. Purpose

The Matching Engine compares what the AST Analysis Engine detected (the learner's actual implementation) against what the LLM Pattern Classifier determined are valid approaches (Accepted Solution Groups).

Its sole responsibility is to determine the match status. It does not produce Gap Signals, update Elo, or generate recommendations.

---

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| `accepted_solution_groups` | LLM Pattern Classifier (Phase 3A), stored in `problem_metadata_cache.classified_patterns` | `list[list[str]]` — e.g., `[["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]` |
| `detected_patterns` | AST Analysis Engine (Phase 3C) | `list[DetectionResult]` — each with `pattern_id`, `confidence`, `evidence` |

The Matching Engine receives only patterns with High confidence (≥ 0.80) from the AST output. Medium and Low confidence patterns are excluded from matching (they are handled by the Confidence Layer in Phase 5).

---

## 3. Output

```python
@dataclass
class MatchResult:
    status: MatchStatus           # FULL_MATCH, PARTIAL_MATCH, or NO_MATCH
    matched_group: list[str] | None   # The Accepted Solution Group that matched (only for FULL_MATCH)
    matched_patterns: set[str]        # All detected patterns that appear in any group
    missing_patterns: set[str]        # Patterns in the best-matching group that were not detected
    unmatched_detected: set[str]      # Detected patterns that don't appear in any accepted group
    details: str                      # Human-readable explanation


class MatchStatus(Enum):
    FULL_MATCH = "full_match"
    PARTIAL_MATCH = "partial_match"
    NO_MATCH = "no_match"
```

---

## 4. Matching Algorithm

### Step 1: Filter detected patterns

Receive `detected_patterns` from the AST Analysis Engine. Discard patterns with confidence < 0.80.

Keep only pattern IDs:
```
detected_ids = {p.pattern_id for p in all_detected_patterns if p.confidence >= 0.80}
```

### Step 2: Load Accepted Solution Groups

Load `accepted_solution_groups` from the metadata cache (populated by Phase 3A).

```
groups = metadata["classified_patterns"]
# e.g., [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

### Step 3: Evaluate each group

For each group in `accepted_solution_groups`, determine:

**Full group match:**
Every pattern in the group is present in `detected_ids`.

```
group = ["sorting", "two_pointers_opposite_direction"]
detected_ids = {"sorting", "two_pointers_opposite_direction", "array_traversal"}
Result: FULL_MATCH (all patterns in group detected)
```

**Partial group match:**
Some, but not all, patterns in the group are present in `detected_ids`.

```
group = ["sorting", "two_pointers_opposite_direction"]
detected_ids = {"sorting", "array_traversal"}
Result: PARTIAL_MATCH (sorting detected, two_pointers_opposite_direction missing)
```

**No match:**
No pattern in any group is present in `detected_ids`.

```
groups = [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
detected_ids = {"linked_list_traversal"}
Result: NO_MATCH
```

### Step 4: Determine final status

| Condition | Status | Rationale |
|-----------|--------|-----------|
| At least one group is a FULL_MATCH | `FULL_MATCH` | The learner used one of the accepted solution approaches |
| No FULL_MATCH, but at least one PARTIAL_MATCH exists | `PARTIAL_MATCH` | The learner used some elements of an accepted approach but is missing others |
| No FULL_MATCH and no PARTIAL_MATCH | `NO_MATCH` | The learner's approach does not match any accepted solution group |

---

## 5. Match Status Definitions

### 5.1 FULL_MATCH

The learner's code matches at least one Accepted Solution Group.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"hash_map_lookup", "array_traversal"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
```

**Semantic meaning:** The learner used a valid optimal solution approach. No gap is identified for this submission.

**Downstream action:** No Gap Signal is generated. The learner's Elo for the matched pattern is updated positively (via the Gap Signal Engine using repeated verification - Phase 6).

### 5.2 PARTIAL_MATCH

The learner's code includes some but not all patterns from any single group.

```
Accepted groups:    [["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"sorting"}
Result:             PARTIAL_MATCH (sorting detected, two_pointers_opposite_direction missing)
```

**Semantic meaning:** The learner started implementing an accepted approach but may not have completed it, or implemented a sub-optimal variant. This is a weak gap signal.

**Downstream action:** A partial match MAY generate a weak Gap Signal (determined by Phase 5 Confidence Layer and Phase 6 Gap Signal Engine), but only after repeated occurrences.

### 5.3 NO_MATCH

The learner's code does not match any pattern in any Accepted Solution Group.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"brute_force"}
Result:             NO_MATCH
```

**Semantic meaning:** The learner used an approach that is not listed as an accepted optimal solution. This may indicate:
- The learner used a sub-optimal approach (e.g., brute force instead of hash map)
- The LLM classification is incomplete
- The code cannot be analyzed into patterns

**Downstream action:** A no-match with high-confidence detection of a non-accepted pattern (e.g., `brute_force`) is a potential Gap Signal. A no-match where the detector returned no high-confidence patterns is inconclusive.

---

## 6. Multiple Group Matching

When multiple groups exist, the Matching Engine checks each group independently.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

**Case A: Both groups partially match**

```
Detected:  {"hash_map_lookup", "sorting"}
Group 0:   FULL_MATCH  (["hash_map_lookup"] all present)
Group 1:   PARTIAL_MATCH (["sorting"] present, ["two_pointers_opposite_direction"] missing)
Final:     FULL_MATCH
```

The final status is the best outcome across all groups. If any group is a FULL_MATCH, the overall result is FULL_MATCH.

**Case B: One group fully matches, one partially matches**

Same as Case A — best outcome wins. FULL_MATCH.

**Case C: No group fully matches, multiple partial matches**

```
Detected:  {"hash_map_lookup", "sorting"}
Group 0:   PARTIAL_MATCH (["hash_map_lookup"] present)
Group 1:   PARTIAL_MATCH (["sorting"] present, ["two_pointers_opposite_direction"] missing)
Final:     PARTIAL_MATCH
```

---

## 7. Edge Cases

### 7.1 No accepted solution groups

If `accepted_solution_groups` is empty or None, the Matching Engine cannot determine match status.

```python
MatchResult(
    status=MatchStatus.NO_MATCH,
    matched_group=None,
    matched_patterns=set(),
    missing_patterns=set(),
    unmatched_detected=detected_ids,
    details="No accepted solution groups available for this question",
)
```

### 7.2 No detected patterns (all confidence < 0.80)

```python
MatchResult(
    status=MatchStatus.NO_MATCH,
    matched_group=None,
    matched_patterns=set(),
    missing_patterns=set(),
    unmatched_detected=set(),
    details="No high-confidence patterns detected",
)
```

### 7.3 Single-pattern accepted group

```
Accepted groups:    [["hash_map_lookup"]]
Detected:           {"hash_map_lookup"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
```

Single-pattern groups are handled identically to multi-pattern groups. All patterns in the group must be detected for FULL_MATCH.

### 7.4 Multi-pattern group with redundant patterns

A group may include patterns that are not strictly algorithmic (e.g., `array_traversal` or `sorting`). These are treated as required patterns for the group.

Future implementation note: Some taxonomy patterns have `elo_affects: false` (e.g., `array_traversal`, `sorting`). The Matching Engine treats all patterns equally regardless of `elo_affects`. The distinction is relevant only at the Gap Signal and Elo stages.

### 7.5 Detected patterns that match no group

```
Accepted groups:    [["hash_map_lookup"]]
Detected:           {"hash_map_lookup", "greedy"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
Unmatched:          {"greedy"}
```

Extra detected patterns that match no group are recorded in `unmatched_detected` but do not affect the match status. A learner may implement additional algorithmic elements beyond the minimum required.

---

## 8. Determinism

The Matching Engine is deterministic:

- Same `accepted_solution_groups` + same `detected_patterns` → same `MatchResult`
- No randomness, no AI, no LLM calls
- No external dependencies
- No side effects

---

## 9. Integration Point with Phase 3A

The Matching Engine reads `accepted_solution_groups` from the metadata cache, which was populated by the LLM Pattern Classifier (Phase 3A).

```python
from src.services.metadata_cache import read_cache

metadata = read_cache(question_id)
groups = metadata.get("classified_patterns", [])
# groups = [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

If the metadata cache does not contain classification for this question, the Matching Engine returns `NO_MATCH` with an appropriate detail message. The question would need to be classified first (Phase 3A handles this lazily on first access).

---

# Matching Engine

Version: 1.0
Status: Design — Frozen for Phase 3C
Last Updated: 2026-07-03

---

## 1. Purpose

The Matching Engine compares what the AST Analysis Engine detected (the learner’s actual implementation) against what the LLM Pattern Classifier determined are valid approaches (Accepted Solution Groups). Its sole responsibility is to determine the match status. It does not produce Gap Signals, update Elo, or generate recommendations.

---

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| `accepted_solution_groups` | LLM Pattern Classifier (Phase 3A), stored in `problem_metadata_cache.classified_patterns` | `list[list[str]]` — e.g., `[["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]` |
| `detected_patterns` | AST Analysis Engine (Phase 3C) | `list[DetectionResult]` — each with `pattern_id`, `confidence`, `evidence` |

The Matching Engine receives only patterns with High confidence (≥ 0.80) from the AST output. Medium and Low confidence patterns are excluded from matching (they are handled by the Confidence Layer in Phase 5).

---

## 3. Output

```python
@dataclass
class MatchResult:
    status: MatchStatus           # FULL_MATCH, PARTIAL_MATCH, or NO_MATCH
    matched_group: list[str] | None   # The Accepted Solution Group that matched (only for FULL_MATCH)
    matched_patterns: set[str]        # All detected patterns that appear in any group
    missing_patterns: set[str]        # Patterns in the best-matching group that were not detected
    unmatched_detected: set[str]      # Detected patterns that don't appear in any accepted group
    details: str                      # Human-readable explanation


class MatchStatus(Enum):
    FULL_MATCH = "full_match"
    PARTIAL_MATCH = "partial_match"
    NO_MATCH = "no_match"
```

---

## 4. Matching Algorithm

### Step 1: Filter detected patterns

Receive `detected_patterns` from the AST Analysis Engine. Discard patterns with confidence < 0.80.

Keep only pattern IDs:
```
detected_ids = {p.pattern_id for p in all_detected_patterns if p.confidence >= 0.80}
```

### Step 2: Load Accepted Solution Groups

Load `accepted_solution_groups` from the metadata cache (populated by Phase 3A).

```
groups = metadata["classified_patterns"]
# groups = [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

### Step 3: Evaluate each group

For each group in `accepted_solution_groups`, determine:

**Full group match:**
Every pattern in the group is present in `detected_ids`.

```
group = ["sorting", "two_pointers_opposite_direction"]
detected_ids = {"sorting", "two_pointers_opposite_direction", "array_traversal"}
Result: FULL_MATCH (all patterns in group detected)
```

**Partial group match:**
Some, but not all, patterns in the group are present in `detected_ids`.

```
group = ["sorting", "two_pointers_opposite_direction"]
detected_ids = {"sorting", "array_traversal"}
Result: PARTIAL_MATCH (sorting detected, two_pointers_opposite_direction missing)
```

**No match:**
No pattern in any group is present in `detected_ids`.

```
groups = [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
detected_ids = {"linked_list_traversal"}
Result: NO_MATCH
```

### Step 4: Determine final status

| Condition | Status | Rationale |
|-----------|--------|-----------|
| At least one group is a FULL_MATCH | `FULL_MATCH` | The learner used one of the accepted solution approaches |
| No FULL_MATCH, but at least one PARTIAL_MATCH exists | `PARTIAL_MATCH` | The learner used some elements of an accepted approach but is missing others |
| No FULL_MATCH and no PARTIAL_MATCH | `NO_MATCH` | The learner’s approach does not match any accepted solution group |

---

## 5. Match Status Definitions

### 5.1 FULL_MATCH

The learner’s code matches at least one Accepted Solution Group.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"hash_map_lookup", "array_traversal"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
```

**Semantic meaning:** The learner used a valid optimal solution approach. No gap is identified for this submission.

**Downstream action:** No Gap Signal is generated. The learner’s Elo for the matched pattern is updated positively (via the Gap Signal Engine using repeated verification - Phase 6).

### 5.2 PARTIAL_MATCH

The learner’s code includes some but not all patterns from any single group.

```
Accepted groups:    [["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"sorting"}
Result:             PARTIAL_MATCH (sorting detected, two_pointers_opposite_direction missing)
```

**Semantic meaning:** The learner started implementing an accepted approach but may not have completed it, or implemented a sub-optimal variant. This is a weak gap signal.

**Downstream action:** A partial match MAY generate a weak Gap Signal (determined by Phase 5 Confidence Layer and Phase 6 Gap Signal Engine), but only after repeated occurrences.

### 5.3 NO_MATCH

The learner’s code does not match any pattern in any Accepted Solution Group.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
Detected patterns:  {"brute_force"}
Result:             NO_MATCH
```

**Semantic meaning:** The learner used an approach that is not listed as an accepted optimal solution. This may indicate:
- The learner used a sub-optimal approach (e.g., brute force instead of hash map)
- The LLM classification is incomplete
- The code cannot be analyzed into patterns

**Downstream action:** A no-match with high-confidence detection of a non-accepted pattern (e.g., `brute_force`) is a potential Gap Signal. A no-match where the detector returned no high-confidence patterns is inconclusive.

---

## 6. Multiple Group Matching

When multiple groups exist, the Matching Engine checks each group independently.

```
Accepted groups:    [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

**Case A: Both groups partially match**

```
Detected:  {"hash_map_lookup", "sorting"}
Group 0:   FULL_MATCH  (["hash_map_lookup"] all present)
Group 1:   PARTIAL_MATCH (["sorting"] present, ["two_pointers_opposite_direction"] missing)
Final:     FULL_MATCH
```

The final status is the best outcome across all groups. If any group is a FULL_MATCH, the overall result is FULL_MATCH.

**Case B: One group fully matches, one partially matches**

Same as Case A — best outcome wins. FULL_MATCH.

**Case C: No group fully matches, multiple partial matches**

```
Detected:  {"hash_map_lookup", "sorting"}
Group 0:   PARTIAL_MATCH (["hash_map_lookup"] present)
Group 1:   PARTIAL_MATCH (["sorting"] present, ["two_pointers_opposite_direction"] missing)
Final:     PARTIAL_MATCH
```

---

## 7. Edge Cases

### 7.1 No accepted solution groups

If `accepted_solution_groups` is empty or None, the Matching Engine cannot determine match status.

```python
MatchResult(
    status=MatchStatus.NO_MATCH,
    matched_group=None,
    matched_patterns=set(),
    missing_patterns=set(),
    unmatched_detected=detected_ids,
    details="No accepted solution groups available for this question",
)
```

### 7.2 No detected patterns (all confidence < 0.80)

```python
MatchResult(
    status=MatchStatus.NO_MATCH,
    matched_group=None,
    matched_patterns=set(),
    missing_patterns=set(),
    unmatched_detected=set(),
    details="No high-confidence patterns detected",
)
```

### 7.3 Single-pattern accepted group

```
Accepted groups:    [["hash_map_lookup"]]
Detected:           {"hash_map_lookup"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
```

Single-pattern groups are handled identically to multi-pattern groups. All patterns in the group must be detected for FULL_MATCH.

### 7.4 Multi-pattern group with redundant patterns

A group may include patterns that are not strictly algorithmic (e.g., `array_traversal` or `sorting`). These are treated as required patterns for the group.

Future implementation note: Some taxonomy patterns have `elo_affects: false` (e.g., `array_traversal`, `sorting`). The Matching Engine treats all patterns equally regardless of `elo_affects`. The distinction is relevant only at the Gap Signal and Elo stages.

### 7.5 Detected patterns that match no group

```
Accepted groups:    [["hash_map_lookup"]]
Detected:           {"hash_map_lookup", "greedy"}
Result:             FULL_MATCH (matched group ["hash_map_lookup"])
Unmatched:          {"greedy"}
```

Extra detected patterns that match no group are recorded in `unmatched_detected` but do not affect the match status. A learner may implement additional algorithmic elements beyond the minimum required.

---

## 8. Determinism

The Matching Engine is deterministic:

- Same `accepted_solution_groups` + same `detected_patterns` → same `MatchResult`
- No randomness, no AI, no LLM calls
- No external dependencies
- No side effects

---

## 9. Integration Point with Phase 3A

The Matching Engine reads `accepted_solution_groups` from the metadata cache, which was populated by the LLM Pattern Classifier (Phase 3A).

```python
from src.services.metadata_cache import read_cache

metadata = read_cache(question_id)
groups = metadata.get("classified_patterns", [])
# groups = [["hash_map_lookup"], ["sorting", "two_pointers_opposite_direction"]]
```

If the metadata cache does not contain classification for this question, the Matching Engine returns `NO_MATCH` with an appropriate detail message. The question would need to be classified first (Phase 3A handles this lazily on first access).

---

## 10. Out of Scope

The Matching Engine explicitly does NOT:

- Generate Gap Signals
- Update Elo ratings
- Recommend problems
- Call the LLM
- Access the database beyond reading cached metadata
- Modify any data
- Log learner performance
- Track historical patterns
