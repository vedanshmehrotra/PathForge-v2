# Real-submission evaluation report

- generated: 2026-09-16T14:38:59.095970+00:00
- new submissions analysed: **12**
- skipped (already in registry): **0**
- registry size: **12**
- shadow outcomes: {'UNRESOLVED': 4, 'CONFIRMED': 7, None: 1}

## Failures grouped by likely root cause

### legacy_ast_vocabulary_mismatch  —  7 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | hash_map_lookup | UNRESOLVED | — | — |
| 0 | hash_map_lookup | UNRESOLVED | — | — |
| 0 | sliding_window_fixed | CONFIRMED | sliding_window | sequential_accumulation,fixed_window_maintenance |
| 0 | sliding_window_fixed | CONFIRMED | sliding_window | sequential_accumulation,fixed_window_maintenance |
| 0 | sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 0 | two_pointers_same | CONFIRMED | — | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 0 | — | UNRESOLVED | — | — |

### ok_confirmed  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan |
| 0 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking |
| 0 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking |

### group_unmatchable_empty_required  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | hash_map_lookup | UNRESOLVED | — | — |
| 0 | hash_map_lookup | UNRESOLVED | — | — |

### group_unsatisfiable_empty_required  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | hash_map_lookup | UNRESOLVED | — | — |
| 0 | hash_map_lookup | UNRESOLVED | — | — |

### gt_missing_vocabulary_exposed  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | hash_map_lookup | UNRESOLVED | — | — |
| 0 | hash_map_lookup | UNRESOLVED | — | — |

### no_technique_evidence  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | sliding_window_variable | None | — | — |
| 0 | binary_search_standard | UNRESOLVED | — | — |

### required_concept_not_detected  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | sliding_window_variable | None | — | — |
| 0 | binary_search_standard | UNRESOLVED | — | — |

### no_ground_truth_groups  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 0 | — | UNRESOLVED | — | — |

## Per-submission detail

### problem 0 (e5501e0c4c9d)

- expected: `['hash_map_lookup']` (groups from `expected_patterns`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `FULL_MATCH` (detected ['array_traversal', 'hash_map_lookup'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=bootstrap
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'gt_missing_vocabulary_exposed', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 0 (bd752875a708)

- expected: `['hash_map_lookup']` (groups from `expected_patterns`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `FULL_MATCH` (detected ['array_traversal', 'hash_map_lookup', 'hash_map_frequency'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=bootstrap
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'gt_missing_vocabulary_exposed', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 0 (ecbf2d3d9f93)

- expected: `['sliding_window_fixed']` (groups from `expected_patterns`)
- groups: `[['sliding_window']]`
- production: `NO_MATCH` (detected ['array_traversal', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 0 (271ec916a05c)

- expected: `['sliding_window_fixed']` (groups from `expected_patterns`)
- groups: `[['sliding_window']]`
- production: `NO_MATCH` (detected ['dp_state_machine', 'array_traversal', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 0 (5b6b6e0e8103)

- expected: `['sliding_window_variable']` (groups from `expected_patterns`)
- groups: `[['sliding_window']]`
- production: `FULL_MATCH` (detected ['hash_map_lookup', 'sliding_window_variable', 'array_traversal', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.750, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 0 (3c4e8e67d169)

- expected: `['sliding_window_variable']` (groups from `expected_patterns`)
- groups: `[['sliding_window']]`
- production: `None` (detected [])
- shadow: `None` satisfaction reasoning:
- root causes: `['required_concept_not_detected', 'no_technique_evidence']`

### problem 0 (2c0fa96f65f2)

- expected: `['two_pointers_opposite']` (groups from `expected_patterns`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.900, raw_outcome=satisfied, authority=bootstrap
- root causes: `['ok_confirmed']`

### problem 0 (db6ccad0385f)

- expected: `['two_pointers_opposite']` (groups from `expected_patterns`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.900, raw_outcome=satisfied, authority=bootstrap
- root causes: `['ok_confirmed']`

### problem 0 (540f2d33d8b1)

- expected: `['two_pointers_opposite']` (groups from `expected_patterns`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.900, raw_outcome=satisfied, authority=bootstrap
- root causes: `['ok_confirmed']`

### problem 0 (99478ea1a202)

- expected: `['two_pointers_same']` (groups from `expected_patterns`)
- groups: `[['forward_pointer_advance']]`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 0 (81761b759852)

- expected: `[]` (groups from `expected_patterns`)
- groups: `[]`
- production: `NO_GROUND_TRUTH` (detected ['array_traversal', 'brute_force'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - No solution groups provided for matching
- root causes: `['legacy_ast_vocabulary_mismatch', 'no_ground_truth_groups']`

### problem 0 (3c61e61e62c3)

- expected: `['binary_search_standard']` (groups from `expected_patterns`)
- groups: `[['binary_search']]`
- production: `FULL_MATCH` (detected ['binary_search_standard'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=bootstrap
- root causes: `['required_concept_not_detected', 'no_technique_evidence']`
