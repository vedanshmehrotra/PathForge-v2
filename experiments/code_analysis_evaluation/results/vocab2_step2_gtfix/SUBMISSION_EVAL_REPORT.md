# Real-submission evaluation report

- generated: 2026-09-18T16:27:26.151430+00:00
- new submissions analysed: **46**
- skipped (already in registry): **0**
- registry size: **46**
- shadow outcomes: {'CONFIRMED': 38, 'UNRESOLVED': 8}

## Failures grouped by likely root cause

### legacy_ast_vocabulary_mismatch  —  32 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 1 | hash_map_lookup | CONFIRMED | — | hash_lookup |
| 628 | greedy_local | UNRESOLVED | — | — |
| 15 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking,candidate_selection |
| 13 | hash_map_lookup | CONFIRMED | — | sequential_accumulation,hash_lookup |
| 3 | hash_map_lookup,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,candidate_selection |
| 1574 | greedy_local | UNRESOLVED | — | — |
| 1574 | greedy_local | CONFIRMED | — | candidate_selection |
| 1 | hash_map_lookup | CONFIRMED | — | hash_lookup |
| 3812 | hash_map_frequency | UNRESOLVED | — | sequential_accumulation |
| 3225 | hash_map_frequency,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 3349 | sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 209 | prefix_sum,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 424 | hash_map_frequency,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 438 | hash_map_frequency,sliding_window_fixed | UNRESOLVED | — | — |
| 496 | hash_map_lookup,monotonic_stack | CONFIRMED | monotonic_stack_strategy | monotonic_stack_maintenance |
| 3 | hash_map_lookup,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 209 | prefix_sum,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |
| 125 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking |
| 15 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking,candidate_selection |
| 70 | dp_1d_forward | CONFIRMED | dp_bottom_up | iterative_table_filling |

_(+12 more)_

### ok_confirmed  —  12 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 2 | two_pointers_same | CONFIRMED | — | linked_list_traversal,forward_pointer_advance |
| 3236 | hash_map_lookup,prefix_sum | CONFIRMED | — | sequential_accumulation,forward_pointer_advance |
| 2 | two_pointers_same | CONFIRMED | — | carry_propagation,linked_list_traversal,forward_pointer_advance |
| 3236 | hash_map_lookup,prefix_sum | CONFIRMED | — | sequential_accumulation |
| 2 | two_pointers_same | CONFIRMED | — | linked_list_traversal,forward_pointer_advance |
| 11 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking,candidate_selection |
| 141 | fast_slow_pointers,two_pointers_same | CONFIRMED | — | linked_list_traversal,forward_pointer_advance |
| 3236 | hash_map_lookup,prefix_sum | CONFIRMED | — | sequential_accumulation,forward_pointer_advance |
| 11 | two_pointers_opposite | CONFIRMED | two_pointers_opposite | sequential_accumulation,bidirectional_index_scan,loop_state_tracking |
| 704 | binary_search_standard | CONFIRMED | binary_search | loop_state_tracking,candidate_selection |
| 35 | binary_search_standard | CONFIRMED | binary_search | loop_state_tracking,candidate_selection |
| 21 | two_pointers_same | CONFIRMED | — | linked_list_traversal,forward_pointer_advance |

### required_concept_not_detected  —  5 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 628 | greedy_local | UNRESOLVED | — | — |
| 1574 | greedy_local | UNRESOLVED | — | — |
| 2212 | two_pointers_opposite | UNRESOLVED | — | — |
| 29 | binary_search_answer | UNRESOLVED | — | sequential_accumulation,loop_state_tracking |
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | candidate_selection |

### concept_not_derived_from_patterns  —  4 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 70 | dp_1d_forward | CONFIRMED | dp_bottom_up | iterative_table_filling |
| 70 | dp_1d_forward | CONFIRMED | dp_top_down | recursive_branching |
| 322 | bfs_shortest_path,dp_1d_forward | CONFIRMED | dp_bottom_up | iterative_table_filling |
| 322 | bfs_shortest_path,dp_1d_forward | CONFIRMED | dp_top_down | sequential_accumulation,recursive_branching |

### group_unmatchable_empty_required  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 3812 | hash_map_frequency | UNRESOLVED | — | sequential_accumulation |
| 4080 | hash_map_frequency | UNRESOLVED | — | — |
| 438 | hash_map_frequency,sliding_window_fixed | UNRESOLVED | — | — |

### group_unsatisfiable_empty_required  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 3812 | hash_map_frequency | UNRESOLVED | — | sequential_accumulation |
| 4080 | hash_map_frequency | UNRESOLVED | — | — |
| 438 | hash_map_frequency,sliding_window_fixed | UNRESOLVED | — | — |

### gt_missing_vocabulary_exposed  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 3812 | hash_map_frequency | UNRESOLVED | — | sequential_accumulation |
| 4080 | hash_map_frequency | UNRESOLVED | — | — |
| 438 | hash_map_frequency,sliding_window_fixed | UNRESOLVED | — | — |

### no_technique_evidence  —  3 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 628 | greedy_local | UNRESOLVED | — | — |
| 1574 | greedy_local | UNRESOLVED | — | — |
| 2212 | two_pointers_opposite | UNRESOLVED | — | — |

### confirmed_on_unexpected_strategy  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 70 | dp_1d_forward | CONFIRMED | dp_top_down | recursive_branching |
| 322 | bfs_shortest_path,dp_1d_forward | CONFIRMED | dp_top_down | sequential_accumulation,recursive_branching |

### extra_strategy_inferred  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 496 | hash_map_lookup,monotonic_stack | CONFIRMED | monotonic_stack_strategy | monotonic_stack_maintenance |
| 200 | bfs_shortest_path,dfs_recursive,union_find | CONFIRMED | dp_bottom_up,union_find | sequential_accumulation,iterative_table_filling |

### false_confirmation_label_mismatch  —  2 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 70 | dp_1d_forward | CONFIRMED | dp_top_down | recursive_branching |
| 322 | bfs_shortest_path,dp_1d_forward | CONFIRMED | dp_top_down | sequential_accumulation,recursive_branching |

### patterns_vs_groups_drift  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 3225 | hash_map_frequency,sliding_window_variable | CONFIRMED | sliding_window | sequential_accumulation,loop_state_tracking,forward_pointer_advance |

### required_accumulation_needs_acc_update  —  1 submission(s)

| problem | expected | outcome | strategies | techniques |
|---|---|---|---|---|
| 4284 | two_pointers_same,prefix_sum | UNRESOLVED | — | candidate_selection |

## Per-submission detail

### problem 1 (6fc48782b6f5)

- expected: `['hash_map_lookup']` (groups from `live_db`)
- groups: `[['hash_lookup']]`
- production: `FULL_MATCH` (detected ['array_traversal', 'hash_map_lookup'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 628 (38407905af10)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[['candidate_selection']]`
- production: `FULL_MATCH` (detected ['sorting', 'greedy_local'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_concept_not_detected', 'no_technique_evidence']`

### problem 15 (1e56bd619a6a)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'array_traversal', 'brute_force', 'sorting'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=1.000, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 13 (b00751c158e1)

- expected: `['hash_map_lookup']` (groups from `live_db`)
- groups: `[['hash_lookup']]`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 3 (70892ffe851e)

- expected: `['hash_map_lookup', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `PARTIAL_MATCH` (detected ['array_traversal', 'brute_force', 'sliding_window_variable'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 1574 (688f965f177f)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[['candidate_selection']]`
- production: `NO_MATCH` (detected ['sorting'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_concept_not_detected', 'no_technique_evidence']`

### problem 1574 (2a26e03d345f)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[['candidate_selection']]`
- production: `NO_MATCH` (detected ['array_traversal', 'sliding_window_variable'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 1 (32dc01fe7a5c)

- expected: `['hash_map_lookup']` (groups from `live_db`)
- groups: `[['hash_lookup']]`
- production: `FULL_MATCH` (detected ['array_traversal', 'hash_map_lookup'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=bootstrap
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 3812 (15313c250834)

- expected: `['hash_map_frequency']` (groups from `live_db`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `NO_MATCH` (detected ['sorting', 'prefix_sum'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=bootstrap
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'gt_missing_vocabulary_exposed', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 2 (37194757c939)

- expected: `['two_pointers_same']` (groups from `live_db`)
- groups: `[['linked_list_traversal']]`
- production: `FULL_MATCH` (detected ['two_pointers_same'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 3236 (b26eadf89ed4)

- expected: `['hash_map_lookup', 'prefix_sum']` (groups from `live_db`)
- groups: `[['hash_lookup'], ['sequential_accumulation']]`
- production: `NO_MATCH` (detected [])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0_alt0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
    - Group group_0_alt1: satisfaction=0.850, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['ok_confirmed']`

### problem 2 (febb0ad9073f)

- expected: `['two_pointers_same']` (groups from `live_db`)
- groups: `[['linked_list_traversal']]`
- production: `FULL_MATCH` (detected ['two_pointers_same'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 3236 (2335c1c88e76)

- expected: `['hash_map_lookup', 'prefix_sum']` (groups from `live_db`)
- groups: `[['hash_lookup'], ['sequential_accumulation']]`
- production: `NO_MATCH` (detected [])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0_alt0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
    - Group group_0_alt1: satisfaction=0.850, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['ok_confirmed']`

### problem 4080 (1300f5ec6730)

- expected: `['hash_map_frequency']` (groups from `live_db`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `NO_MATCH` (detected ['hash_map_lookup'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=llm_proposed
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['gt_missing_vocabulary_exposed', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 2 (f49c8a50a25e)

- expected: `['two_pointers_same']` (groups from `live_db`)
- groups: `[['linked_list_traversal']]`
- production: `FULL_MATCH` (detected ['two_pointers_same'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 11 (5e2d002d1e79)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=1.000, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 3225 (b01d927a6555)

- expected: `['hash_map_frequency', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `FULL_MATCH` (detected ['array_traversal', 'greedy_local', 'brute_force', 'sliding_window_variable'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch', 'patterns_vs_groups_drift']`

### problem 141 (7d8f3a4785a7)

- expected: `['fast_slow_pointers', 'two_pointers_same']` (groups from `live_db`)
- groups: `[['forward_pointer_advance']]`
- production: `FULL_MATCH` (detected ['fast_slow_pointers', 'two_pointers_same'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 3349 (5456a5792915)

- expected: `['sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `FULL_MATCH` (detected ['array_traversal', 'sliding_window_variable', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 209 (ec6b6a90ae0b)

- expected: `['prefix_sum', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `PARTIAL_MATCH` (detected ['sliding_window_variable', 'array_traversal', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 424 (6b05482b3e3c)

- expected: `['hash_map_frequency', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `PARTIAL_MATCH` (detected ['array_traversal', 'hash_map_frequency', 'dp_state_machine', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 438 (a0b510c738b5)

- expected: `['hash_map_frequency', 'sliding_window_fixed']` (groups from `live_db`)
- groups: `[[]]`
- unmatchable groups: `['group_0']`
- production: `NO_MATCH` (detected ['array_traversal', 'prefix_sum'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unmatchable, authority=human_curated
    - Group group_0: required is empty — group is unmatchable (no concept can satisfy it; expected-approach vocabulary gap)
- root causes: `['legacy_ast_vocabulary_mismatch', 'gt_missing_vocabulary_exposed', 'group_unsatisfiable_empty_required', 'group_unmatchable_empty_required']`

### problem 496 (0be5e5ae23da)

- expected: `['hash_map_lookup', 'monotonic_stack']` (groups from `live_db`)
- groups: `[['monotonic_stack_maintenance']]`
- production: `NO_MATCH` (detected ['array_traversal', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'extra_strategy_inferred']`

### problem 3236 (2f28974476a2)

- expected: `['hash_map_lookup', 'prefix_sum']` (groups from `live_db`)
- groups: `[['hash_lookup'], ['sequential_accumulation']]`
- production: `NO_MATCH` (detected [])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0_alt0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
    - Group group_0_alt1: satisfaction=0.850, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['ok_confirmed']`

### problem 3 (d1414cdbdb5c)

- expected: `['hash_map_lookup', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `FULL_MATCH` (detected ['hash_map_lookup', 'sliding_window_variable', 'array_traversal', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 209 (0d202422a57c)

- expected: `['prefix_sum', 'sliding_window_variable']` (groups from `live_db`)
- groups: `[['sliding_window']]`
- production: `PARTIAL_MATCH` (detected ['sliding_window_variable', 'array_traversal', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.863, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 11 (7f893cd0d1cb)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=1.000, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 125 (cfe77884ff46)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=1.000, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 15 (5710e0ae4bf7)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `FULL_MATCH` (detected ['two_pointers_opposite', 'array_traversal', 'brute_force', 'sorting'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=1.000, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 704 (c2265ffb2ef1)

- expected: `['binary_search_standard']` (groups from `live_db`)
- groups: `[['binary_search']]`
- production: `FULL_MATCH` (detected ['binary_search_standard'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 35 (fc5b9f132e21)

- expected: `['binary_search_standard']` (groups from `live_db`)
- groups: `[['binary_search']]`
- production: `FULL_MATCH` (detected ['binary_search_standard'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 70 (108a6edad7f7)

- expected: `['dp_1d_forward']` (groups from `live_db`)
- groups: `[['dp_bottom_up'], ['dp_top_down']]`
- production: `FULL_MATCH` (detected ['array_traversal', 'dp_1d_forward'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.920, raw_outcome=satisfied, authority=human_curated
    - Group group_1: satisfaction=0.000, raw_outcome=unsatisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'concept_not_derived_from_patterns']`

### problem 70 (a6e62bcf0c5c)

- expected: `['dp_1d_forward']` (groups from `live_db`)
- groups: `[['dp_bottom_up'], ['dp_top_down']]`
- production: `NO_MATCH` (detected ['brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=contradicted, authority=human_curated
    - Group group_0: CONTRADICTED downgraded to UNRESOLVED (authority=human_curated is not authoritative)
    - Group group_1: satisfaction=0.978, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'concept_not_derived_from_patterns', 'false_confirmation_label_mismatch', 'confirmed_on_unexpected_strategy']`

### problem 322 (14ee52845dd9)

- expected: `['bfs_shortest_path', 'dp_1d_forward']` (groups from `live_db`)
- groups: `[['dp_bottom_up'], ['dp_top_down']]`
- production: `NO_MATCH` (detected ['array_traversal', 'brute_force', 'greedy_local'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.920, raw_outcome=satisfied, authority=human_curated
    - Group group_1: satisfaction=0.000, raw_outcome=unsatisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'concept_not_derived_from_patterns']`

### problem 322 (8e793f5c8c4f)

- expected: `['bfs_shortest_path', 'dp_1d_forward']` (groups from `live_db`)
- groups: `[['dp_bottom_up'], ['dp_top_down']]`
- production: `NO_MATCH` (detected ['array_traversal', 'hash_map_lookup', 'greedy_local', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=contradicted, authority=human_curated
    - Group group_0: CONTRADICTED downgraded to UNRESOLVED (authority=human_curated is not authoritative)
    - Group group_1: satisfaction=0.978, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'concept_not_derived_from_patterns', 'false_confirmation_label_mismatch', 'confirmed_on_unexpected_strategy']`

### problem 62 (a17ebb69bf9b)

- expected: `['dp_2d_grid']` (groups from `live_db`)
- groups: `[['dp_bottom_up']]`
- production: `FULL_MATCH` (detected ['brute_force', 'array_traversal', 'dp_interval', 'dp_2d_grid'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.920, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 46 (39190fb8fbe4)

- expected: `['backtracking_permutation']` (groups from `live_db`)
- groups: `[['dfs_backtracking']]`
- production: `NO_MATCH` (detected ['dfs_recursive', 'backtracking_subset', 'array_traversal', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.978, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 78 (c7122a128f99)

- expected: `['backtracking_subset']` (groups from `live_db`)
- groups: `[['dfs_backtracking']]`
- production: `FULL_MATCH` (detected ['backtracking_subset', 'array_traversal', 'dfs_recursive', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.978, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 102 (05cca89710e6)

- expected: `['bfs_level_order']` (groups from `live_db`)
- groups: `[['bfs_shortest_path']]`
- production: `FULL_MATCH` (detected ['bfs_level_order', 'array_traversal', 'brute_force'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 200 (d08ae2cd80f4)

- expected: `['bfs_shortest_path', 'dfs_recursive', 'union_find']` (groups from `live_db`)
- groups: `[['union_find']]`
- production: `NO_MATCH` (detected ['brute_force', 'array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.850, raw_outcome=satisfied, authority=human_curated
- root causes: `['legacy_ast_vocabulary_mismatch', 'extra_strategy_inferred']`

### problem 2212 (ccaac0a1ba6b)

- expected: `['two_pointers_opposite']` (groups from `live_db`)
- groups: `[['two_pointers_opposite']]`
- production: `NO_MATCH` (detected ['greedy_local'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
- root causes: `['required_concept_not_detected', 'no_technique_evidence']`

### problem 21 (1e5d34f5cb4d)

- expected: `['two_pointers_same']` (groups from `live_db`)
- groups: `[['forward_pointer_advance']]`
- production: `FULL_MATCH` (detected ['two_pointers_same'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=human_curated
- root causes: `['ok_confirmed']`

### problem 29 (6826590f694a)

- expected: `['binary_search_answer']` (groups from `live_db`)
- groups: `[['binary_search']]`
- production: `NO_MATCH` (detected ['brute_force'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_concept_not_detected']`

### problem 4284 (0708fbdb8a53)

- expected: `['two_pointers_same', 'prefix_sum']` (groups from `live_db`)
- groups: `[['forward_pointer_advance'], ['sequential_accumulation']]`
- production: `NO_MATCH` (detected ['array_traversal', 'greedy_local'])
- shadow: `UNRESOLVED` satisfaction reasoning:
    - Group group_0: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
    - Group group_1: satisfaction=0.000, raw_outcome=unsatisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch', 'required_accumulation_needs_acc_update', 'required_concept_not_detected']`

### problem 4256 (8f05fbb9b09e)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[['candidate_selection']]`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch']`

### problem 4258 (24f5e7a9982c)

- expected: `['greedy_local']` (groups from `live_db`)
- groups: `[['candidate_selection']]`
- production: `NO_MATCH` (detected ['array_traversal'])
- shadow: `CONFIRMED` satisfaction reasoning:
    - Group group_0: satisfaction=0.800, raw_outcome=satisfied, authority=llm_proposed
- root causes: `['legacy_ast_vocabulary_mismatch']`
