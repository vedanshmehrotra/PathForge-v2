# Batch 2A Report — Ground-Truth Consistency (before/after, measurement)

**Date:** 2026-09-16
**Batch:** 2A only — ground-truth derivation / persistence / load / consistency check.
**Not implemented:** F3, N2, N4, BFS changes, single-candidate range selection, any AST detector, any strategy detector, the legacy MatchingEngine, any problem-ID logic, any ground-truth hand edit.

---

## 1. What was inspected before editing

The ground-truth layer has **four** places where a group's `required` list is produced or consumed:

| stage | location | behaviour found |
|---|---|---|
| derive (LLM) | `ground_truth_builder._build_single_group` / `_split_patterns_into_groups` | computes `required`/`optional`/`excluded` from `PATTERN_TO_V1_MAPPING` **at generation time**, tags `provenance: [llm_ground_truth, vocabulary_v1]`, and never revisits it |
| persist | `ground_truth_builder._store_ground_truth` | writes `solution_groups` JSON verbatim — including any group whose `required` came out empty |
| load (stored) | `problem_resolver._load_ground_truth` → stored-groups branch | `has_v1_required = "required" in g and g["required"]` — a **stale** non-empty `required` is used as-is forever; an empty one falls through to a re-map of the group's own patterns |
| load (fallback) | `problem_resolver._split_csv_patterns_to_groups` | re-maps legacy patterns with the *current* mapping on every load — so this path was already vocabulary-aware, while the stored-groups path was frozen |

Two producers of unsatisfiable groups exist (not one): the **write** path for newly derived groups, and the **load** path for problems with no stored groups. Both are covered.

Live footprint measured before the change: **122 stored groups, 6 with `required: []`**, and 9 distinct problems whose effective groups cannot be satisfied (`hash_map_lookup`, `hash_map_frequency`, `greedy_local` have no V1 concept at all).

No DB rows were mutated. Ground truth is never auto-regenerated, so the 6 pre-existing empty-`required` rows keep their stored value and are now *flagged* on load instead.

---

## 2. Changes made

### (1) Re-runnable, vocabulary-aware derivation
- `ground_truth_builder.refresh_group_vocabulary()` / `refresh_groups_vocabulary()` — re-derive `required`/`excluded` from a group's **own stored legacy patterns** using the *current* mapping; appends a `vocabulary_refresh` provenance marker.
- Called from `_load_ground_truth` **on the raw stored groups, before CSV reconciliation overwrites `patterns`**, so curated labels can never leak into a refresh.
- Guards (each one is a test):
  - only groups carrying the `vocabulary_v1` derivation marker (curated concepts are untouched);
  - group must have legacy patterns, all recognised by the mapping;
  - **siblings sharing identical patterns but requiring different concepts are never refreshed** — that difference is curated information the mapping cannot reproduce (this is what protects the top-down/bottom-up alternatives);
  - idempotent.
- `derivation_patterns` is now carried on loaded groups, so both representations stay visible (see (3)).

### (2) `required: []` is never persisted or emitted as a matchable group
- `MISSING_VOCABULARY_PATTERNS` — the missing vocabulary, derived from the mapping rather than hardcoded.
- `group_matchability()` / `mark_group_matchability()` — one shared rule: a group is matchable iff it has ≥1 required concept. Otherwise it is marked `matchable=False`, `validation="unmatchable"`, and `matchability_reason` **names the offending legacy pattern(s)**. No arbitrary requirement is ever substituted.
- Applied on **both** paths: `_build_solution_groups` (write) and `_finalize_derived_groups` (load fallback + stored branch).
- `_store_ground_truth` now **filters unmatchable groups out of the persisted `solution_groups`** and logs the missing vocabulary; the legacy flat `patterns` column is still written unchanged.
- Existing reconciliation tests (`test_empty_csv_uses_llm_but_no_authoritative_claim`) require such groups to still be *emitted* for diagnosis, so the loader flags rather than drops them — that constraint is preserved.

### (3) Generalized consistency check
- `find_ground_truth_disagreements(patterns, groups)` — pure, returns structured findings: `pattern_not_in_groups`, `group_pattern_not_declared`, `concept_not_derived_from_patterns`, `unmatchable_group`.
- The concept check judges against `derivation_patterns` when present, because reconciliation *intentionally* lets a curated label override the production patterns (V1 fields are never rewritten by reconciliation). Without that, every overridden problem would report false drift.
- Wired into `_load_ground_truth` (warnings, so drift is never silent), onto `ProblemContext.ground_truth_consistency`, and into the `/analyze` response as `problem_info.ground_truth_consistency` (additive, default `[]`).

### (4) Generalized regression tests
`pathforge/ast_analysis/shadow/tests/test_batch2a_ground_truth_consistency.py` — **57 tests** across 9 families: registry derivation, matchability rule, derivation annotation, persistence rejection, vocabulary refresh (incl. all four guards + idempotence), load-fallback annotation, consistency findings, end-to-end satisfaction of a refreshed group, and live-DB invariants (collected in one sweep).

---

## 3. Validation

| suite | result |
|---|---|
| new Batch 2A tests | **57 passed** |
| shadow suite | **520 passed** (was 466; all originals green) |
| full repository | **1398 passed, 1 failed** — the only failure is the known pre-existing legacy `prefix_sum` detector test (`src/ast_detection/tests/test_detectors_batch2.py`), unchanged from baseline |
| 46-submission batch (same 46, same live DB groups, re-run with `--force` because the code changed) | 31 CONFIRMED / 15 UNRESOLVED / 0 CONTRADICTED |

### Disclosure: two existing tests caught a real design error
The first implementation ran the refresh over the *reconciled* group list, so for problems where a curated label overrides the LLM patterns it re-derived concepts from the curated label (`dfs_recursive` → `monotonic_stack_maintenance`). `test_valid_parentheses_shadow_v1_preserved` and `test_problem_5_shadow_v1_preserved` failed on exactly that, and the fix was to refresh the raw stored groups before reconciliation. Final state is green; no test was modified.

---

## 4. Before/after on the 46-submission batch

### Verdicts

| | before | after |
|---|---|---|
| CONFIRMED | 29 | **31** |
| UNRESOLVED | 17 | **15** |
| CONTRADICTED | 0 | 0 |
| false confirmations | 0 real (2 classifier flags, both matcher-correct) | 0 real (same 2) |
| false contradictions | 0 | 0 |
| wrong-strategy selections | 1 real (LC 200: `union_find` correct + spurious `dp_bottom_up`) | 1 (unchanged) |
| CONFIRMED → UNRESOLVED regressions | — | **0** |

Exactly two records changed outcome, both in the intended direction, both the family B1 cases:

| record | problem | before | after | why |
|---|---|---|---|---|
| `db-252` | 21 Merge Two Sorted Lists | UNRESOLVED | **CONFIRMED** | stored group re-derived to `forward_pointer_advance`; technique fires at 0.80 |
| `db-139` | 141 Linked List Cycle | UNRESOLVED | **CONFIRMED** | same |

`db-254` (LC 4284) was also re-derived (`bidirectional_index_scan` → `forward_pointer_advance`) but stays UNRESOLVED: the technique does not fire on that submission. That is honest — the stale-required blocker is gone, and the remaining cause is missing evidence, not stale ground truth.

### Failure families

| family | before | after | disappeared? | why |
|---|---|---|---|---|
| `required_bidirectional_scan_needs_opposite_updates` | 3 | **0** | ✅ **gone** | stale `bidirectional_index_scan` replaced by the current vocabulary; 2 of the 3 then confirmed |
| `required_concept_not_detected` | 6 | **4** | ↓ by 2 | the same 2 records stopped being blocked |
| `group_unsatisfiable_empty_required` | 11 | 11 | ❌ **did not disappear** | see below |
| `group_unmatchable_empty_required` | 11 | 11 | ❌ | consumer-side labelling (F1), unchanged |
| `gt_missing_vocabulary_exposed` | 0 | **11** | new | the cause is now named, not silent |
| `concept_not_derived_from_patterns` | 0 | **4** | new detection | true positives (see below) |
| `patterns_vs_groups_drift` | 0 | **1** | new detection | true positive |
| `no_technique_evidence` | 3 | 3 | ❌ | genuine evidence gap (LC 102/2212/4284) — untouched by this batch |
| `extra_strategy_inferred` | 2 | 2 | ❌ | 1 real (LC 200), 1 naming artifact |
| `false_confirmation_label_mismatch` | 2 | 2 | ❌ | ground-truth representation issue on LC 70/322, now *reported* by the check |
| `required_accumulation_needs_while_loop` | 1 | 1 | ❌ | N3 — explicitly out of scope |

### The 11 `GT_EMPTY_REQUIRED` records: NOT claimed as a win
They remain UNRESOLVED, and that is correct. Their legacy patterns (`hash_map_lookup`, `hash_map_frequency`, `greedy_local`) have **no concept in the V1 vocabulary at all** — there is nothing legitimate to require. What changed:

- they are no longer *silently* unsatisfiable; each group is emitted with `matchable=False` and a reason naming the missing pattern (e.g. `missing_vocabulary: the V1 vocabulary defines no concept for legacy pattern(s) greedy_local`), and the derivation will no longer persist such a group for newly generated problems;
- the new registry `MISSING_VOCABULARY_PATTERNS` (7 patterns: `dfs_iterative`, `greedy_interval`, `greedy_local`, `hash_map_frequency`, `hash_map_lookup`, `heap_top_k`, `topological_sort`) is the exact, actionable backlog for a future vocabulary-expansion batch.

Resolving these requires **new vocabulary concepts**, which is a detector/strategy-layer change and was out of scope.

### New detections are true positives
- `concept_not_derived_from_patterns` — 4 records (LC 70 ×2, LC 322 ×2): two groups share `dp_1d_forward` but require `dp_bottom_up` and `dp_top_down`. The flat label genuinely cannot express that alternation, and the groups are deliberately *not* refreshed because of it. This is exactly the "two representations silently drifting" case the check exists to surface.
- `patterns_vs_groups_drift` — 1 record (LC 3225): the declared label contains `hash_map_frequency` but no group declares it (it is absorbed as an unmapped pattern). Verified against the loader output, not a harness artifact.

---

## 5. Files changed

| file | change |
|---|---|
| `pathforge/services/ground_truth_builder.py` | `MISSING_VOCABULARY_PATTERNS`, matchability rule + annotation, vocabulary refresh, `find_ground_truth_disagreements`, persistence filter, logger |
| `pathforge/services/problem_resolver.py` | refresh on raw stored groups, `derivation_patterns`, `_finalize_derived_groups`, disagreement logging, `ground_truth_consistency` on `ProblemContext`, `_parse_curated_patterns` refactor |
| `pathforge/api/routes/analyze.py` | `ProblemInfo.ground_truth_consistency` (additive) |
| `pathforge/ast_analysis/shadow/tests/test_batch2a_ground_truth_consistency.py` | new — 57 generalized tests |
| `experiments/code_analysis_evaluation/runners/real_submission_harness.py` | classifier now consumes the **production** consistency check instead of re-implementing it; richer group projection |

## 6. What did NOT change

No AST detector, no technique, no strategy, no matcher, no legacy MatchingEngine, no BFS, no N4, no problem-ID logic, no hand-edited ground truth. Confidence scales, thresholds and verdict semantics are untouched. `bidirectional_index_scan`, `sliding_window` (F4) and the Batch 1 pointer work are byte-identical.

**Stopping here — F3 not started.***

Reproduce:
```
python -m pytest pathforge/ast_analysis/shadow/tests -q
python -m pytest -q
python -m experiments.code_analysis_evaluation.runners.real_submission_harness \
  --input experiments/code_analysis_evaluation/dataset/db_submissions_export.json \
  --registry experiments/code_analysis_evaluation/results/registry_db_batch2a.json \
  --groups-from-db --force --out-dir experiments/code_analysis_evaluation/results/db_batch2a
```
