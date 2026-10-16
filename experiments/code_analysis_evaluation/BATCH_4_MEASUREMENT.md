# Measurement Report — Batch 4 (12 newly supplied submissions)

**Date:** 2026-09-16
**Submissions:** 12 from `selected_submissions/submissions.json` (not in any prior registry)
**Code:** Batch 3 (current, unmodified)
**Note:** these are template/buggy code samples, not live LeetCode submissions from the DB. They validate specific algorithmic families under controlled conditions.

---

## 1. CONFIRMED / UNRESOLVED / CONTRADICTED

| outcome | count |
|---|---|
| CONFIRMED | 7 |
| UNRESOLVED | 4 |
| error (truncated code) | 1 |
| CONTRADICTED | 0 |

## 2. Real false confirmations

**0.** All 7 CONFIRMED records match their expected concepts correctly.

## 3. False contradictions

**0.**

## 4. Wrong strategy selections

**0.** No spurious secondary strategies. No extra strategies inferred.

## 5. Per-record results

| id | title | outcome | techniques | strategies | groups required | flags |
|---|---|---|---|---|---|---|
| sub_0001 | Template: hash_map_lookup | UNRESOLVED | — | — | [] | gt_missing_vocabulary_exposed |
| sub_0002 | Template: hash_map_lookup | UNRESOLVED | — | — | [] | gt_missing_vocabulary_exposed |
| sub_0003 | Template: sliding_window_fixed | **CONFIRMED** | sequential_accumulation, fixed_window_maintenance | sliding_window | [sliding_window] | — |
| sub_0004 | Template: sliding_window_fixed | **CONFIRMED** | sequential_accumulation, fixed_window_maintenance | sliding_window | [sliding_window] | — |
| sub_0005 | Template: sliding_window_variable | **CONFIRMED** | sequential_accumulation, loop_state_tracking, **forward_pointer_advance** | sliding_window | [sliding_window] | — |
| sub_0006 | Template: sliding_window_variable | error | — | — | [sliding_window] | code truncated |
| sub_0007 | Template: two_pointers_opposite | **CONFIRMED** | sequential_accumulation, bidirectional_index_scan | two_pointers_opposite | [two_pointers_opposite] | — |
| sub_0008 | Template: two_pointers_opposite | **CONFIRMED** | sequential_accumulation, bidirectional_index_scan, loop_state_tracking | two_pointers_opposite | [two_pointers_opposite] | — |
| sub_0009 | Template: two_pointers_opposite | **CONFIRMED** | sequential_accumulation, bidirectional_index_scan, loop_state_tracking | two_pointers_opposite | [two_pointers_opposite] | — |
| sub_0010 | Template: two_pointers_same | **CONFIRMED** | sequential_accumulation, loop_state_tracking, **forward_pointer_advance** | — | [forward_pointer_advance] | — |
| sub_0011 | Incorrect Two Sum (O(n²)) | UNRESOLVED | — | — | [] | no_ground_truth_groups |
| sub_0012 | Buggy Binary Search | UNRESOLVED | — | — | [binary_search] | required_concept_not_detected |

## 6. Failure families (12 submissions)

| family | count | records |
|---|---|---|
| gt_missing_vocabulary_exposed | 2 (16.7%) | sub_0001, sub_0002 |
| required_concept_not_detected | 2 (16.7%) | sub_0012, sub_0006 |
| no_technique_evidence | 2 (16.7%) | sub_0006, sub_0012 |
| no_ground_truth_groups | 1 (8.3%) | sub_0011 |

### Tracked items

| item | count | notes |
|---|---|---|
| **missing vocabulary** | 2 | hash_map_lookup templates (same as baseline) |
| **unreachable required concept** | 2 | 1 buggy code (expected), 1 truncated code (expected) |
| **no technique evidence** | 2 | same 2 records as unreachable |
| **extra/spurious strategies** | 0 | — |
| **patterns-vs-groups drift** | 0 | — |
| **required_accumulation_needs_acc_update** | 0 | — |
| **no ground truth** | 1 | incorrect submission, no expected patterns (expected) |

## 7. Comparison with previous 46-submission batch

| family | 46 DB submissions | 12 new submissions | note |
|---|---|---|---|
| gt_missing_vocabulary_exposed | 23.9% | 16.7% | same root cause (hash_map_lookup) |
| required_concept_not_detected | 8.7% | 16.7% | higher rate (buggy + truncated code) |
| no_technique_evidence | 6.5% | 16.7% | same records as unreachable |
| extra_strategy_inferred | 4.3% | **0%** | no spurious strategies on clean templates |
| false_confirmation_label_mismatch | 4.3% | **0%** | no GT-representation issues |
| concept_not_derived_from_patterns | 8.7% | **0%** | no alternation drift on templates |
| patterns_vs_groups_drift | 2.2% | **0%** | — |
| required_accumulation_needs_acc_update | 2.2% | **0%** | — |
| no_ground_truth_groups | 0% | 8.3% | expected for incorrect submissions |

**No new recurring failure family emerged.** The 12 new submissions reproduce the same patterns seen in the 46-submission baseline: missing vocabulary for `hash_map_lookup`, no technique evidence when code is buggy/truncated. The clean templates confirm that all Batch 1–3 fixes work correctly:

- **F2** (forward_pointer_advance): sub_0005 and sub_0010 both detect `forward_pointer_advance` for same-direction pointer code. ✅
- **F4** (sliding window index participation): sub_0003–0005 all correctly detect `sliding_window`. ✅
- **N3** (for-loop accumulation): sub_0005 detects `sequential_accumulation` in a for-loop window. ✅

## 8. Strongest generalized engineering candidate

**Missing vocabulary remains the dominant failure across both datasets** (23.9% on the 46-submission baseline, 16.7% on the 12 new submissions). The actionable backlog is the 7 patterns in `MISSING_VOCABULARY_PATTERNS`: `hash_map_lookup`, `hash_map_frequency`, `greedy_local`, `greedy_interval`, `dfs_iterative`, `heap_top_k`, `topological_sort`. Adding even 2–3 of these concepts (e.g. `frequency_counting`, `greedy_local_decision`) would resolve several UNRESOLVED records.

However, vocabulary expansion is a **data quality** task, not an architecture fix. If the goal is to improve the structural analysis pipeline's ability to detect algorithms it *already has concepts for*, the next candidate is:

**BFS family coverage** (N2): queue-based level-order traversal (LC 102) has 12 facts but zero techniques and zero strategies. The `bfs_shortest_path` strategy requires distance-relaxation evidence, which level-order traversal lacks. A `queue_traversal` technique or broadened BFS strategy would cover this family. This is the only remaining case where the pipeline has adequate structural evidence but produces nothing — the facts are sufficient, but the abstraction gap prevents recognition.

---

*No production code was modified. All numbers from the Batch 3 code applied to 12 newly supplied submissions, using the production consistency check.*
