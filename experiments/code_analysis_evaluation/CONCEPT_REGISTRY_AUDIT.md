# Concept Registry — Audit Report (Batch B1)

**Batch:** B1 — Concept Registry + Classification Audit
**Source of the batch definition:** `experiments/code_analysis_evaluation/ARCHITECTURE_REDESIGN_PROPOSAL.md` §19 Step 0 / §23 Phase B1
**Date:** 2026-09-21
**Status:** complete, declaration-only, awaiting review before B2 is authorised

---

## 0. What B1 added

| Artifact | Purpose |
|---|---|
| `pathforge/ast_analysis/concepts.py` | The single declarative concept registry (96 concepts) |
| `pathforge/tests/test_concept_registry.py` | Completeness + declaration tests (48 tests) |
| `experiments/code_analysis_evaluation/concept_registry.json` | Machine-readable registry dump + stats |
| `experiments/code_analysis_evaluation/CONCEPT_REGISTRY_AUDIT.md` | This report |

**Nothing else changed.** No detector, threshold, technique, strategy, matcher, Ground
Truth, V2 POC, production runtime, database, API response or frontend file was modified,
and no later-batch behaviour (UNKNOWN/NOT_ESTABLISHED, PROVISIONAL, precedence,
zero-evidence sanity, authority gating, `brute_force`, recursive refinement) was
implemented.

Reproduce the dump:

```
python -c "import json,pathlib; from pathforge.ast_analysis import concepts as c; \
pathlib.Path('experiments/code_analysis_evaluation/concept_registry.json').write_text( \
json.dumps({'registry_stats': c.registry_stats(), 'concepts': c.registry_as_dicts()}, indent=2))"
```

---

## 1–5. Concepts discovered per source vocabulary

| # | Source vocabulary | Discovered | How B1 discovers it |
|---|---|---|---|
| 1 | Legacy detector `pattern_id`s (`src/ast_detection/detectors/`) | **36** | `get_all_detectors()` from `src/ast_detection/registry.py` (the registry the runtime actually uses) |
| 2 | `pathforge/ast_engine/patterns.py::ALL_PATTERNS` | **33** | direct import |
| 3 | Shadow techniques (`shadow/techniques.py` T1–T14) | **13 implemented + 1 documented-only = 14** | AST-scan of `technique_id=` literals ∪ `VALID_TECHNIQUES`; plus the documented-only entry |
| 4 | Shadow strategies (`shadow/strategies.py` S1–S9) | **9** | AST-scan of `strategy_id=` literals ∪ `VALID_STRATEGIES` |
| 5 | V2 POC concepts (`gt_poc_v2/problem_metadata.py`) | **22** (9 `PEC_STRATEGIES` + 8 `PEC_TECHNIQUES` + 5 `SUPPORT_TECHNIQUES`) | direct import of the three frozensets |
| + | Shadow structural fact types (`shadow/fact_extractor.py`) | **40** | AST-scan of `fact_type=` literals (the extractor is the only emitter) |
| + | Documented-only concepts | **2** (`boundary_narrowing`, `loop_shape`) | explicit list, cross-checked to be absent from every implemented vocabulary |

### 1.1 Set arithmetic (the completeness proof)

```
legacy detectors .......... 36
ALL_PATTERNS .............. 33   (all 33 are ⊆ the 36; extra detectors = 3)
shadow techniques ......... 13
shadow strategies .........  9
V2 concepts ............... 22
structural fact types ..... 40
documented-only ...........  2

union = 36 ∪ 22 − 3 shared spellings  = 36 + 22 − 3      = 55
        + 2 documented-only                              = 57
        + (40 fact types − 1 identifier collision)        = 96
```

* **The 3 shared spellings** (`two_pointers_opposite`, `bfs_shortest_path`,
  `union_find`) exist in both the legacy detector taxonomy and the V1 strategy
  vocabulary with identical spelling. They are registered **once** as the strategy they
  denote, with all four sources recorded. No rename.
* **The 3 extra detectors** are `array_traversal`, `brute_force`, `sorting`. They are
  the only registered detectors absent from `ALL_PATTERNS`
  (`set(detectors) - set(ALL_PATTERNS)` is exactly those three), so they can be detected
  and displayed but can never be an expected ground-truth pattern.
* **The 1 collision** is `carry_propagation`, which is *both* an emitted structural fact
  type and the T5 technique id. Registered once; see §8 and §12.

---

## 6–8. Classified / unclassified / duplicated

| Metric | Value |
|---|---|
| Concepts classified | **96** |
| Concepts unclassified | **0** |
| Duplicate registrations | **0** (the registry builder raises on a repeated `concept_id`; asserted by test) |
| Aliased / multi-source concepts | **52** (see below) |
| Shared-spelling ids across taxonomies | **3** |
| True identifier collisions (one string, two roles) | **1** (`carry_propagation`) |
| Legacy patterns declaring a `v1_image` | **29** |

**Breakdown of the 52 multi-source (aliased) concepts**

| Group | Count | Relationship |
|---|---|---|
| Legacy detector pattern that is also a curated taxonomy pattern | 36 − 3 = 33 | same id, both vocabularies |
| V1 concept that is also a V2 tier member | 22 | same id, tier attached |
| Legacy pattern that is also a V1 strategy (shared spelling) | 3 | one entry, four sources |
| Legacy pattern that is also a V1 technique (same id string) | 1 | `carry_propagation`? no — see note |
| Structural fact that is also a V1 technique | 1 | `carry_propagation` |

> Note: `carry_propagation` is counted in both the V1/V2 group and the structural-fact
> group, which is why the groups overlap and do not sum to 52 independently.

**Semantic aliasing recorded without renaming** — these are *different ids for one
semantic image*, held together by `PATTERN_TO_V1_MAPPING`:

| Legacy id(s) | V1 image |
|---|---|
| `hash_map_lookup` | `hash_lookup` |
| `hash_map_frequency` | `frequency_counting` |
| `prefix_sum` | `sequential_accumulation` |
| `two_pointers_same`, `fast_slow_pointers` | `forward_pointer_advance` |
| `dfs_recursive` | `recursive_branching` |
| `greedy_local` | `candidate_selection` |
| `sliding_window_fixed`, `sliding_window_variable` | `sliding_window` |
| `bfs_level_order`, `bfs_shortest_path` | `bfs_shortest_path` |
| `binary_search_standard`, `binary_search_rotated`, `binary_search_answer`, `binary_search_tree` | `binary_search` |
| `dp_1d_forward`, `dp_1d_sequence`, `dp_2d_grid`, `dp_2d_string`, `dp_knapsack`, `dp_interval`, `dp_state_machine` | `dp_bottom_up` |
| `backtracking_permutation`, `backtracking_subset` | `dfs_backtracking` |
| `monotonic_stack`, `monotonic_deque` | `monotonic_stack_maintenance` |
| `linked_list_reversal` | `linked_list_traversal` |
| `two_pointers_opposite`, `bfs_shortest_path`, `union_find` | themselves (shared spelling) |

---

## 9. Class distribution

| Class | Count | Meaning |
|---|---|---|
| `OBSERVATION` | **43** | Raw structural signal. rank 0, never a conclusion, never a family requirement. |
| `TECHNIQUE` | **28** | Reusable method. rank 1–2, may be *required* (even identifying), never the reported approach. |
| `STRATEGY` | **25** | Approach-level conclusion. rank 3, the only `conclusion_eligible` class. |
| **Total** | **96** | |

`conclusion_eligible` concepts: **25** (exactly the strategies).

Composition of `OBSERVATION` (43): 39 shadow structural fact types + 3 non-taxonomy
legacy detectors (`array_traversal`, `brute_force`, `sorting`) + `loop_shape`
(documented-only).

## 10. Tier distribution

| Tier | Count |
|---|---|
| `PEC` (may partition a family) | **38** |
| `SUPPORT` (never partitions) | **58** |

Resulting `specificity_rank` distribution (derived, never hand-assigned):

| class / tier | rank | Count |
|---|---|---|
| `OBSERVATION` | 0 | 43 |
| `TECHNIQUE` / `SUPPORT` | 1 | 15 |
| `TECHNIQUE` / `PEC` | 2 | 13 |
| `STRATEGY` | 3 | 25 |

`family_role` distribution:

| Role | Count |
|---|---|
| `IDENTIFYING` | 31 |
| `COMPONENT` | 22 |
| `ABSENT-NOT-ALLOWED` | 43 |
| `SUPPORTING` | **0** (declared, currently no instance — see §14) |

Additional metadata: **32** concepts carry a declared `falsifier`; **29** declare a
`v1_image`.

Independently verified sums: `43+28+25 = 96`, `38+58 = 96`, `43+15+13+25 = 96`,
`31+22+0+43 = 96`.

---

## 11. Concepts that were ambiguous during classification

Each entry states the ambiguity, the decision taken, and the evidence — no certainty is
invented where the repository does not support one.

1. **`candidate_selection` — technique or strategy?**
   *Ambiguity:* it is the identifying concept of the greedy-local family, which reads
   approach-like.
   *Decision:* `TECHNIQUE` / `SUPPORT` / rank 1 / `conclusion_eligible=False`, with
   `family_role=IDENTIFYING`.
   *Evidence:* `PEC_TECHNIQUES` excludes it and `SUPPORT_TECHNIQUES` includes it; the
   brief for this batch states explicitly that a concept may help identify a family
   without becoming the final reported conclusion.
   *Consequence flagged:* under the declared model **nothing can conclude a greedy
   approach** (`greedy_local`, `greedy_interval`, `candidate_selection` are all
   non-strategy). This is the architectural shape of the observed
   `greedy_local` / `array_traversal` mismatch (proposal §6.1) and is a review item.

2. **`heap_top_k`, `topological_sort`, `dfs_iterative`, `greedy_interval` — technique or
   strategy?**
   *Ambiguity:* the names read approach-level; the taxonomy treats them as
   first-class curated patterns.
   *Decision:* `TECHNIQUE` / `SUPPORT` / rank 1 / `COMPONENT`.
   *Evidence:* all four are the `MISSING_VOCABULARY_PATTERNS` (empty `required` in
   `PATTERN_TO_V1_MAPPING`), and each mapping note describes the missing image as a
   *technique* ("Iterative DFS has no direct V1 **technique** equivalent", "No direct V1
   **technique**; uses BFS-like traversal", "No direct V1 **technique** for heap
   operations", "No direct V1 **technique** for interval greedy").
   *Consequence flagged:* all four therefore cannot be a final conclusion, although each
   has a working detector. Review item.

3. **`monotonic_stack` / `monotonic_deque` — technique or strategy?**
   *Decision:* `TECHNIQUE` / `PEC` / rank 2, because both map to
   `monotonic_stack_maintenance`, and the separate strategy `monotonic_stack_strategy`
   (S9) wraps it.
   *Evidence:* the V1 model deliberately splits maintenance (technique) from the strategy
   that uses it.

4. **`binary_search_tree` — a data-structure problem mapped onto an algorithm.**
   *Decision:* `STRATEGY` / `PEC` (its `v1_image` is `binary_search`).
   *Ambiguity:* the name denotes a structure, not an algorithm. Not renamed in B1.

5. **`dfs_recursive` — `TECHNIQUE`/`SUPPORT` via the broad `recursive_branching`.**
   *Ambiguity:* recursive DFS is an approach, but its only V1 image is the broad
   recursion-evidence concept.
   *Evidence:* five V2 families across five problems carry specific recursive labels while
   the analyzer observes only `recursive_branching` (`POC_V2_POST_HUMAN_REVIEW_REPORT.md`
   §10.1). Review item — relevant to the later recursion-refinement batch, not to B1.

6. **`prefix_sum` — a first-class curated pattern mapped to a SUPPORT technique.**
   *Decision:* `TECHNIQUE` / `SUPPORT` / rank 1 / `COMPONENT`, `conclusion_eligible=False`.
   *Evidence:* `PATTERN_TO_V1_MAPPING["prefix_sum"]["required"] == ["sequential_accumulation"]`,
   a SUPPORT technique that V2 refused as a family label six times (the `LABEL_GENERIC`
   refusals, §5.2 of the proposal). The project has separately audited prefix-sum false
   confirmations (`PREFIX_SUM_PRODUCTION_FALSE_CONFIRMATION_AUDIT.md`).
   *Consequence flagged:* `prefix_sum` cannot conclude despite being a curated pattern.

7. **`boundary_narrowing` (T2) — documented as a technique, not implemented.**
   *Decision:* `TECHNIQUE` / `SUPPORT` / `COMPONENT`, source `documented_only`.
   *Evidence:* `techniques.py` has no detector for it and
   `_evaluate_binary_search` says *"boundary_narrowing is not a technique yet (Phase 1
   limitation); we use the structural fact combination instead"*; it is absent from
   `VALID_TECHNIQUES`. Registered so the documentation/implementation gap is explicit.

8. **`loop_shape` — documented fact name that is never emitted.**
   *Decision:* `OBSERVATION` / rank 0 / `ABSENT-NOT-ALLOWED`, source `documented_only`.
   *Evidence:* it appears in the vocabulary doc §2.1 but no `fact_type="loop_shape"` is
   ever emitted; the implemented equivalents are `for_loop_iteration`,
   `while_loop_comparison`, `while_loop_truthiness`. It is *also* the name of one of the
   five V2 grouping-profile dimensions (`gt_poc_v2/core.py`) — a different concept with
   the same name.

9. **`carry_propagation` — one string, two roles.**
   *Decision:* registered once, as the technique, with `SRC_STRUCTURAL_FACT` recorded.
   *Evidence:* `fact_extractor.py` emits a `carry_propagation` fact and
   `_detect_carry_propagation` sets `technique_id="carry_propagation"`. Splitting the ids
   would require a rename, which B1 is not allowed to do. Review item.

10. **Tier for `OBSERVATION` and `STRATEGY`.**
    *Decision:* observations are declared `SUPPORT`; strategies `PEC`.
    *Rationale:* `SUPPORT` means "never partitions a family", which is exactly the
    observation guarantee; V2's `concept_tier()` already defaults an unregistered id to
    `SUPPORT`. Adding a third tier was rejected because B1 must not extend the approved
    tier model.

11. **Whether shadow structural fact types belong in this registry at all.**
    *Decision:* included (40 entries, 39 registered here).
    *Rationale:* the approved design defines `OBSERVATION` as the class that *"corresponds
    to today's shadow structural facts and to today's `array_traversal` / `brute_force` /
    `sorting`"* (proposal §8.2), and this batch's brief lists `loop_shape` — a
    documentation-level structural signal — as an `OBSERVATION` example.
    *Consequence flagged:* this is more than the five mandated vocabularies; if the
    reviewer prefers, the 39 fact types can be moved to a separate structural-fact
    registry without touching anything else. Review item.

12. **`family_role` for `SUPPORTING` could not be evidenced.**
    *Decision:* the role is declared and currently unused.
    *Evidence:* every concept that appears only in a V2 `optional` set also appears in some
    `required` set, so no concept is provably optional-only. Kept in the enum because the
    approved design defines it, and reported so its vacancy is visible.

---

## 12. Concepts whose existing naming is misleading

Reported for review; **no renaming was performed in B1.**

| Concept | Why the name misleads | Actual behaviour (evidence) |
|---|---|---|
| `array_traversal` | "traversal" reads as an algorithmic approach | Fires on a `for` over a Name/`range`/`enumerate` **plus any `Subscript` anywhere in the module** (`_detect_subscript_access` walks the whole file, not the loop). Measured precision 0.24–0.30, 106–183 false positives, 62 % fire rate (`reports and docs/SEMANTIC_EXPERIMENT_2A/2B/3A/3B/3C`) |
| `brute_force` | Implies a judgement about exhaustiveness | Fires when a loop body contains a loop (`has_exhaustive_core = has_nested or has_branch`). "Nested loop" has a measured 66.7 % FP exposure on the V2 corpus |
| `sorting` | A pattern-level name for a structural operation | Detects that a sort happens; the same operation appears inside many distinct approaches. Also not in `ALL_PATTERNS` |
| `frequency_counting` (detector file) registers `hash_map_frequency` | The file name and the `pattern_id` disagree | `_detect_frequency_counting` / the detector also matches a pre-sized count array (`cnt = [0]*26`), which is not a hash map |
| `binary_search_classic.py` registers `binary_search_standard` | File name ≠ `pattern_id` | registry listing |
| `monotonic_queue.py` registers `monotonic_deque` | File name ≠ `pattern_id` | registry listing |
| `heap_priority_queue.py` registers `heap_top_k` | File name ≠ `pattern_id` | registry listing |
| `recursive_branching` | "branching" implies conditional branching | It also fires for a **nested** self-recursive call (`context == "nested_function"`), i.e. memoized top-down DP; it absorbs five distinct recursive strategies |
| `prefix_sum` | Implies prefix sums specifically | Its V1 image `sequential_accumulation` is broader and is a SUPPORT-tier technique |
| `two_pointers_same` | Suggests parity with `two_pointers_opposite` | Its image is `forward_pointer_advance`, a SUPPORT technique, while `two_pointers_opposite` is a full STRATEGY |
| `boundary_narrowing` | Documented as an implemented technique T2 | Not implemented; absent from `VALID_TECHNIQUES` |
| `loop_shape` | Documented as a structural fact | Never emitted; also the name of an unrelated V2 profile dimension |
| `carry_propagation` | Looks like two distinct concepts (fact and technique) | One string used in both roles |
| `hash_map_lookup` / `hash_map_frequency` | "hash map" implies a dict | `hash_lookup`'s detector deliberately excludes `Counter`; `frequency_counting` deliberately includes pre-sized arrays |
| `greedy_interval`, `topological_sort`, `dfs_iterative` | Read as algorithmic strategies | Declared non-conclusion-eligible in this registry because no V1 concept can express them |

---

## 13. Special handling

| Concept | Class | Tier | Rank | `conclusion_eligible` | `family_role` | Notes |
|---|---|---|---|---|---|---|
| `array_traversal` | `OBSERVATION` | `SUPPORT` | 0 | **false** | `ABSENT-NOT-ALLOWED` | Detector **not modified or deleted** |
| `brute_force` | `OBSERVATION` | `SUPPORT` | 0 | **false** | `ABSENT-NOT-ALLOWED` | Detector **not modified**; not a GT activation concept; no redefinition of "brute force" implemented |
| `sorting` | `OBSERVATION` | `SUPPORT` | 0 | **false** | `ABSENT-NOT-ALLOWED` | Structural evidence; no taxonomy evidence found to the contrary |
| `recursive_branching` | `TECHNIQUE` | `SUPPORT` | 1 | **false** | `COMPONENT` | Remains broad recursion **evidence**; explicitly **not** promoted to a strategy; no recursive-strategy detectors added |
| `candidate_selection` | `TECHNIQUE` | `SUPPORT` | 1 | **false** | **`IDENTIFYING`** | The identifying-but-not-concluding distinction the batch requires; `greedy_local` mirrors it |

Supporting assertions enforced by the test suite:

* `array_traversal`, `brute_force`, `sorting` are registered detectors, are absent from
  `ALL_PATTERNS`, and are absent from the V1 and V2 vocabularies.
* `recursive_branching` is not a strategy, and the only technique-class concepts
  mentioning recursion are `recursive_branching` and `dfs_recursive` (i.e. no
  refinement was smuggled in).
* The four raw recursion fact types (`self_recursive_call`, `multiple_recursive_paths`,
  `recursive_call_in_conditional`, `recursive_depth_tracking`) are `OBSERVATION`s.
* `candidate_selection` and `greedy_local` share class/tier/role and neither is
  conclusion-eligible.

---

## 14. Confirmation that the registry is NOT consumed by runtime code

**Mechanism.** No module imports `pathforge.ast_analysis.concepts`. This is enforced by
two tests:

* `test_no_runtime_consumer_exists` — scans every `.py` file in the repository (excluding
  `.git`, `node_modules`, `__pycache__`, `.pytest_cache`, `.next`) for the tokens
  `pathforge.ast_analysis.concepts` and `from pathforge.ast_analysis import concepts`,
  and asserts the **only** match is `pathforge/tests/test_concept_registry.py`.
* `test_registry_is_not_referenced_by_analysis_or_matching_modules` — an explicit guard
  over `pathforge/api/`, `pathforge/services/`, `src/` and `pathforge/ast_engine/`,
  asserting zero references.

**Structural reason it cannot be consumed accidentally.** `pathforge/ast_analysis/` has
no `__init__.py`, so importing the subpackage does not import the registry; and the
registry imports nothing from the project (only `dataclasses`/`typing`), so it cannot
create an import cycle.

**Behavioural consequence.** Because nothing reads the registry, B1 cannot change any
runtime output: no analysis, matching, persistence, API or UI behaviour differs from
before this batch. The test suite confirms this (see §15).

---

## 15. Test results

### 15.1 B1 tests

```
python -m pytest pathforge/tests/test_concept_registry.py -q
→ 48 passed in 3.21s
```

Coverage of the required test list:

| Required test | Test name(s) | Result |
|---|---|---|
| Registry completeness | `test_every_discovered_concept_is_registered`, `test_registry_has_no_unknown_concepts`, `test_registry_matches_discovered_vocabularies_exactly`, `test_per_source_coverage_is_exact` | pass |
| Registry field validity | `test_no_duplicate_registration`, `test_concept_fields_are_valid`, `test_family_role_values_are_restricted_to_the_approved_set`, `test_every_concept_uses_the_registry_key_as_its_id`, `test_observations_never_identify_or_component_a_family`, `test_only_strategies_may_conclude` | pass |
| Rank derivation | `test_rank_is_consistent_with_class_and_tier`, `test_conclusion_eligibility_is_consistent_with_class`, `test_rank_scheme_matches_the_approved_derivation`, `test_rank_derivation_rejects_unknown_inputs` | pass |
| `array_traversal` classification | 4 parameterised tests + `test_array_traversal_is_never_conclusion_eligible` | pass |
| `brute_force` classification | 4 parameterised tests + `test_brute_force_has_no_ground_truth_activation_role` | pass |
| `sorting` classification | 4 parameterised tests | pass |
| `recursive_branching` classification | `test_recursive_branching_is_broad_supporting_evidence`, `test_recursive_branching_is_not_a_strategy_and_no_recursive_strategy_was_added` | pass |
| `candidate_selection` role | `test_candidate_selection_identifies_but_does_not_conclude`, `test_greedy_local_mirrors_candidate_selection` | pass |
| No runtime consumer exists | `test_no_runtime_consumer_exists`, `test_registry_is_not_referenced_by_analysis_or_matching_modules` | pass |

Also: duplicate/invalid-value detection (`test_concept_fields_are_valid`,
`test_no_duplicate_registration`), collision and documented-only handling
(`test_carry_propagation_collision_is_registered_once_and_documented`,
`test_boundary_narrowing_is_documented_but_unimplemented`,
`test_loop_shape_is_documented_but_not_an_emitted_fact`,
`test_shared_legacy_and_v1_strategy_ids_are_single_entries`), and stats consistency
(`test_registry_stats_and_projection_are_consistent`, `test_registry_lookup_helpers`).
No existing test was modified to make anything pass.

### 15.2 Shadow tests

```
python -m pytest pathforge/ast_analysis/shadow/tests -q
→ 810 passed in 62.22s
```

### 15.3 Full repository suite

The suite cannot be run as one command in this environment: `pathforge/tests/test_pipeline.py`
alone takes ~6 minutes because two of its tests wait on a remote PostgreSQL connection.
It was therefore run as complete, non-overlapping chunks (nothing skipped, nothing
deselected):

| Chunk | Command | Result |
|---|---|---|
| Shadow | `pytest pathforge/ast_analysis/shadow/tests` | **810 passed** |
| `src/` | `pytest src` | **605 passed, 1 failed** |
| Top-level + db + ast_engine | `pytest tests pathforge/db/tests pathforge/ast_engine/tests` | **76 passed** |
| `pathforge/tests` (8 files) | per-file (see §15.3.1) | **149 passed** |
| `pathforge/tests/test_pipeline.py` | `pytest pathforge/tests/test_pipeline.py` | **6 passed, 2 failed** |
| `experiments/` | `pytest experiments` | **79 passed** |
| Standalone `*_test.py` (3 of 5) | `pytest pathforge/elo_engine_test.py pathforge/gap_signal_engine_test.py pathforge/recommendation_engine_test.py` | **54 passed** |
| Standalone `api_test.py`, `auth_test.py` | `pytest pathforge/api_test.py pathforge/auth_test.py` | **2 collection errors** |
| **Total** | | **1779 passed / 3 failed / 2 collection errors** (1812 collected) |

#### 15.3.1 `pathforge/tests` per file

| File | Result | Time |
|---|---|---|
| `test_boolean_persistence.py` | 6 passed | 0.5 s |
| `test_diversity.py` | 8 passed | 61.8 s |
| `test_evidence_architecture.py` | 41 passed | 0.6 s |
| `test_ground_truth_builder.py` | 6 passed | 0.5 s |
| `test_ground_truth_reconciliation.py` | 21 passed | 15.4 s |
| `test_submission_handler.py` | 10 passed | 0.5 s |
| `test_concept_registry.py` (new) | 48 passed | 3.1 s |
| `test_llm_client.py` | 9 passed | 2.4 s |
| `test_pipeline.py` | 6 passed, 2 failed | 368.7 s |

### 15.4 Failures — classification

**F1 — the known pre-existing legacy failure (still present, unaddressed).**

```
src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self
assert result.detected == True  →  DetectionResult(pattern_id=prefix_sum, confidence=0.0, evidence=0)
```

This is the exact failure recorded as pre-existing at baseline in
`gt_poc_v2/POC_V2_REPORT.md` ("the known pre-existing legacy failure … present at
baseline"). It is a `prefix_sum` detector-message issue; B1 touched no detector, and the
test file has no relationship to the registry. **Not fixed** — the batch scope forbids
detector changes.

**F2 — environment-dependent failures (remote PostgreSQL unreachable).**

| Test | Error |
|---|---|
| `pathforge/tests/test_pipeline.py::test_race_condition_atomicity_all_or_nothing` | `psycopg2.OperationalError: SSL error: unexpected eof while reading` |
| `pathforge/tests/test_pipeline.py::test_no_elo_loss_on_duplicate_attempt` | same (288 s of retrying) |
| `pathforge/api_test.py` (collection) | `psycopg2.OperationalError: connection to server …` |
| `pathforge/auth_test.py` (collection) | same |

All four call `get_connection()` and fail while connecting to the configured production
PostgreSQL, not in application logic. **None of the four references the registry**
(`grep -c concept` → `0` in `test_pipeline.py`, `api_test.py`, `auth_test.py`), so B1
cannot be their cause. They require a reachable database and are reported as
environment limitations, unmodified.

### 15.5 Regression verdict

* **No pre-existing passing test became failing.** Every failure is either the documented
  legacy `prefix_sum` failure (F1) or a remote-database connection error (F2).
* **No test was modified** to accommodate B1.
* **New tests:** 48, all passing.

---

## 16. Zero production behaviour change — confirmation

1. **Three new files only.** `pathforge/ast_analysis/concepts.py`,
   `pathforge/tests/test_concept_registry.py`,
   `experiments/code_analysis_evaluation/concept_registry.json`,
   plus this report. `git status` shows no modification to any tracked file.
2. **Nothing imports the registry** (§14), so no code path can read a classification.
3. **The registry module imports nothing from the project** — only `dataclasses` and
   `typing` — so it cannot participate in any runtime import graph.
4. **No detector, threshold, vocabulary, matcher, Ground-Truth, V2 POC, database, API or
   frontend file was touched.**
5. **No later-batch behaviour was implemented:** no UNKNOWN/NOT_ESTABLISHED, no
   PROVISIONAL, no precedence, no zero-evidence sanity handling, no authority gating,
   no `brute_force` implementation, no recursive-strategy refinement.

---

## 17. Classification decisions to review before B2

Ordered by importance to B2.

**G1 — Greedy approaches have no conclusion.** `greedy_local`, `greedy_interval` and
`candidate_selection` are all non-strategy, so under the approved Rule S1
(`conclusion_eligible == STRATEGY`) a greedy solution's primary approach would be
`UNRECOGNIZED`. **Decision needed:** either a later batch declares a greedy
strategy-class concept, or the precedence rule gains an explicit
"IDENTIFYING technique may conclude when no strategy does" clause. The registry already
records `family_role=IDENTIFYING` for this case; which way it resolves is *not* a
precedence implementation detail — it changes whether proposal §6.1's mismatch can be
fixed by precedence alone.

**G2 — 14 legacy detector patterns cannot be conclusion-eligible.** These are the
non-strategy entries of the 33-pattern curated taxonomy: 5 PEC techniques (`hash_map_lookup`, `hash_map_frequency`,
`linked_list_reversal`, `monotonic_stack`, `monotonic_deque`), 5 SUPPORT techniques
(`prefix_sum`, `two_pointers_same`, `dfs_recursive`, `fast_slow_pointers`,
`greedy_local`) and the 4 unmapped patterns (`dfs_iterative`, `topological_sort`,
`heap_top_k`, `greedy_interval`).
**Decision needed:** confirm this is intended, or approve V1 images / strategy-class
concepts for them. Today each has a working detector and can become `primary_pattern`;
after the conclusion layer (B4) lands, they cannot — this is a *coverage* consequence
that a reviewer should accept explicitly.

**G3 — `NEW-3` interaction.** The six human-approved SUPPORT-only labels
(`forward_pointer_advance` ×2, `sequential_accumulation` ×4) interact directly with
`family_role`. If a reviewed low-specificity family may activate, their role changes from
`COMPONENT` to `IDENTIFYING`. This must be decided before B2 assigns
`identifying` components.

**G4 — Legacy falsifiers are not yet structural falsifiers.** 29 legacy patterns carry a
`falsifier` transcribed from `PATTERN_TO_V1_MAPPING["excluded"]`, which today fires on
mere presence. Proposal §9 rules K3/K4 require a positive structural falsifier.
**Decision needed:** approve the transcription as "declared exclusion" metadata, or
schedule real falsifiers before the tri-state work.

**G5 — `carry_propagation` identifier collision.** One string, two roles. B1 registers it
once. Splitting requires a rename, which is not permitted in B1. **Decision needed:**
accept the single entry with dual sources, or authorise a rename in the batch that is
allowed to touch vocabulary.

**G6 — `boundary_narrowing` and `loop_shape`.** Registered as documented-only so the
documentation cannot silently diverge from the implementation. **Decision needed:** keep
them as registry entries (recommended) or correct the vocabulary document instead.

**G7 — 40 structural fact types in this registry.** 39 fact types make up 41 % of the
registry. They are included because the approved design equates `OBSERVATION` with the
shadow structural facts. **Decision needed:** keep them here, or split them into a
separate structural-fact registry that this one references.

**G8 — Observation tier is declared `SUPPORT`.** A consequence of not extending the
approved tier model. **Decision needed:** confirm, or introduce an explicit third tier
for observations in a later batch.

**G9 — `array_traversal` / `brute_force` / `sorting` remain registered detectors.**
B1 only demotes them at the *declaration* layer. Their runtime demotion is B4.
**Decision needed:** confirm they must not be deleted or retuned when B4 lands.

**G10 — `SUPPORTING` is declared but unused.** **Decision needed:** keep reserved, or
remove from the role enum in a later batch.

---

## 18. Batch status

B1 is complete and the repository is clean and reviewable:

* registry created — 96 concepts, 100 % classified, 0 duplicates;
* 48 new declaration tests pass; 810 shadow tests pass;
* full-suite result 1779 passed / 3 failed / 2 collection errors, with every failure
  classified as pre-existing legacy or remote-database environment;
* zero production behaviour change.

**B2 has not been started.** The registry is presented for inspection first; §17 lists
the decisions that should be settled before the tri-state work begins.
