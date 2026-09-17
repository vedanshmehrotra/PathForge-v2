# Real-submission evaluation report

- generated: 2026-09-16T13:00:24.053436+00:00
- new submissions analysed: **9**
- skipped (already in registry): **0**
- registry size: **9**
- shadow outcomes: {'UNRESOLVED': 6, 'CONFIRMED': 3}

## Failures grouped by likely root cause

### legacy_ast_vocabulary_mismatch  —  6 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 29 | binary_search_answer | UNRESOLVED | — | sequential_accumulation,loop_state_tracking |
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | — |
| 4256 | greedy_local | UNRESOLVED | — | — |
| 4258 | greedy_local | UNRESOLVED | — | — |
| 283 | two_pointers_same | CONFIRMED | — | loop_state_tracking,forward_pointer_advance |
| 209 | sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |

### required_concept_not_detected  —  4 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 21 | two_pointers_same | UNRESOLVED | — | linked_list_traversal,forward_pointer_advance |
| 29 | binary_search_answer | UNRESOLVED | — | sequential_accumulation,loop_state_tracking |
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | — |
| 141 | fast_slow_pointers | UNRESOLVED | — | linked_list_traversal,forward_pointer_advance |

### required_bidirectional_scan_needs_opposite_updates  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 21 | two_pointers_same | UNRESOLVED | — | linked_list_traversal,forward_pointer_advance |
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | — |
| 141 | fast_slow_pointers | UNRESOLVED | — | linked_list_traversal,forward_pointer_advance |

### group_unmatchable_empty_required  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 4256 | greedy_local | UNRESOLVED | — | — |
| 4258 | greedy_local | UNRESOLVED | — | — |

### group_unsatisfiable_empty_required  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 4256 | greedy_local | UNRESOLVED | — | — |
| 4258 | greedy_local | UNRESOLVED | — | — |

### no_technique_evidence  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | — |

### ok_confirmed  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 167 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking |

### required_accumulation_needs_while_loop  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | — |

## Per-submission detail

### problem 21 (d709a8fb5837)

- expected: `['two_pointers_same']` (groups from `live_db`)
- groups: `[['bidirectional_index_scan']]`
- production: `FULL_MATCH` (detected ['two_pointers_same'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=human_curated
- root causes: `['required_bidirectional_scan_needs_opposite_updates', 'required_concept_not_detected']`

### problem 29 (f3d760f52b9c)

- expected: `['binary_search_answer']` (groups from `live_db`)
- groups: `[['binary_search']]`
- production: `NO_MATCH` (detected ['brute_force'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_concept_not_detected']`

### problem 4284 (b1f13e0c5c4e)

- expected: `['two_pointers_same', 'prefix_sum']` (groups from `live_db`)
- groups: `[['bidirectional_index_scan'], ['sequential_accumulation']]`
- production: `NO_MATCH` (detected ['array_traversal', 'greedy_local'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
    - Group group_1: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_accumulation_needs_while_loop', 'required_bidirectional_scan_needs_opposite_updates', 'required_concept_not_detected', 'no_technique_evidence']`

### problem 4256 (02caf086a1f1)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=llm_proposed
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 4258 (8021ca7e1ff5)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=llm_proposed
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 283 (044e6795f195)

- expected: `['two_pointers_same']` (groups from `expected_patterns`)
- groups: `[['forward_pointer_advance']]`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 167 (ba9010e396da)

- expected: `['two_pointers_opposite']` (groups from `expected_patterns`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.900, raw_outcome=satisfied, authority=bootstrap
- root causes: `['ok_confirmed']`

### problem 209 (545a40a02519)

- expected: `['sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `PARTIAL_MATCH` (detected ['sliding_window_variable', 'array_traversal', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 141 (e7700a550862)

- expected: `['fast_slow_pointers']` (groups from `live_db`)
- groups: `[['bidirectional_index_scan']]`
- production: `FULL_MATCH` (detected ['fast_slow_pointers', 'two_pointers_same'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=human_curated
- root causes: `['required_bidirectional_scan_needs_opposite_updates', 'required_concept_not_detected']`
