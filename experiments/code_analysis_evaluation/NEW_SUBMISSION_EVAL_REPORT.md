# New-Submission Evaluation Report — Batch 2 (measurement only)

**Run date:** 2026-09-16
**Harness:** `experiments/code_analysis_evaluation/runners/real_submission_harness.py` (export-based ingestion)
**Input:** `experiments/code_analysis_evaluation/dataset/db_submissions_export.json` (real accepted submissions from the live `submissions` table, user 14)
**Ground truth:** live DB (`--groups-from-db`, i.e. the effective `_load_ground_truth()` groups, not a local copy)
**Registry:** `results/registry_db_batch1.json`
**No production analysis code was modified during this run.** Batch 1 (F1 + F2 + F4) was already committed to the working tree before the run, so these numbers *include* Batch 1.

---

## 1. Total new submissions analyzed

| | |
|---|---|
| Live `submissions` rows | 90 |
| Rows belonging to the target account | 83 |
| Unique code hashes | 48 |
| Non-code placeholder rows excluded (`"code"`, `"self-reported"`) | 2 |
| **Analysable submissions ingested** | **46** |
| **Skipped as already-tested** | **0** |
| Distinct problems covered | 34 |

Submission identity is a content fingerprint (`sha256(problem_id + normalized code)`), not a problem ID. Verified against the two pre-existing registries (`registry_beforeafter.json` = 7, `registry_live.json` = 9): **overlap with this batch = 0**, so nothing was re-analyzed. The five case submissions used earlier (`cases_live_gt.json`) were *reconstructed* code; the DB-exported versions have different fingerprints and therefore count as genuinely new.

Target range was 30–50; delivered 46.

## 2. CONFIRMED / UNRESOLVED / CONTRADICTED

**Structural (shadow) path:**

| Outcome | Count | Share |
|---|---|---|
| CONFIRMED | 29 | 63.0 % |
| UNRESOLVED | 17 | 37.0 % |
| CONTRADICTED | **0** | 0 % |

Confirmation mechanism split: **23 confirmed via a strategy**, **6 confirmed on technique evidence alone** (no strategy selected).
Authority of the ground truth behind confirmed results: `human_curated` 24, `llm_proposed` 5.

**Legacy production path (for comparison):** FULL_MATCH 22, PARTIAL_MATCH 4, NO_MATCH 20.

Cross-tab (production → shadow):

| | shadow CONFIRMED | shadow UNRESOLVED |
|---|---|---|
| production FULL_MATCH | 16 | 6 |
| production PARTIAL_MATCH | 4 | 0 |
| production NO_MATCH | 9 | 11 |

The structural path resolved **9 submissions the production matcher reported as NO_MATCH**, and was more conservative on 6 that production called FULL_MATCH.

## 3. Wrong-strategy detections

**1 real case** out of 46.

| submission | problem | strategies inferred | GT expectation | verdict |
|---|---|---|---|---|
| `db-246` | 200 Number of Islands | `union_find` ✅ + **`dp_bottom_up`** ❌ | union_find | CONFIRMED (on the correct `union_find` group) |

The verdict is right; the defect is a **spurious secondary strategy**. It does not flip the outcome because the matcher chose the group that was actually satisfied.

Per-strategy precision across the batch:

| strategy | inferred | correct | spurious |
|---|---|---|---|
| `sliding_window` | 7 | 7 | 0 |
| `two_pointers_opposite` | 5 | 5 | 0 |
| `dp_bottom_up` | 4 | 3 | 1 |
| `binary_search` | 2 | 2 | 0 |
| `dp_top_down` | 2 | 2 | 0 |
| `dfs_backtracking` | 2 | 2 | 0 |
| `monotonic_stack_strategy` | 1 | 1 | 0 |
| `union_find` | 1 | 1 | 0 |

Classifier note: an automated `extra_strategy_inferred` flag initially fired twice; `db-193` (LC 496) is a **naming artifact** — the technique id is `monotonic_stack_maintenance` while the strategy id is `monotonic_stack_strategy`, so the harness's "allowed concepts" set looked violated when it was not. Counted as 0 real.

## 4. False confirmations

**0 real false confirmations.** Two were flagged and both were investigated at the fact level:

| submission | problem | stored groups | satisfied | inferred | why the flag is wrong |
|---|---|---|---|---|---|
| `db-238` | 70 Climbing Stairs | `group_0 [dp_bottom_up]`, `group_1 [dp_top_down]` | `group_1` | `dp_top_down` | facts are `self_recursive_call`, `multiple_recursive_paths`, `cache_lookup`, `cache_write` → the code **is** recursive-with-memo. `group_1` legitimately permits it. |
| `db-240` | 322 Coin Change | same two groups | `group_1` | `dp_top_down` | same fact signature (`cache_lookup`/`cache_write`/`self_recursive_call`). |

Both are a **ground-truth representation inconsistency**, not a matcher error: the flat `problem_ground_truth.patterns` column says `dp_1d_forward` (→ `dp_bottom_up`) while the structured `solution_groups` accept *either* bottom-up or top-down. The matcher used the structured groups — which is the authoritative source — and was right. See N1 in §8.

**False contradictions: 0** (no CONTRADICTED outcomes at all).

## 5. & 6. Repeated failure categories and their frequency

Categories are defined over the 17 UNRESOLVED records; they are *not* disjoint (C is a severity marker that overlaps A and B).

| # | family | n | share of UNRESOLVED | one-line description |
|---|---|---|---|---|
| **A** | `GT_EMPTY_REQUIRED` | **11** | 64.7 % | The stored group has `required: []`, so its satisfaction is structurally capped below the 0.5 threshold. No implementation can ever confirm it. |
| **B** | `REQUIRED_CONCEPT_UNREACHABLE` | **6** | 35.3 % | A non-empty `required` concept that nothing detected. |
| B1 | ↳ forward-pointer vs bidirectional | 3 | 17.6 % | GT requires `bidirectional_index_scan`; the submission has genuine same-direction pointer evidence. |
| B2 | ↳ BFS family coverage | 1 | 5.9 % | Queue-based level-order traversal not recognised by `bfs_shortest_path`. |
| B3 | ↳ GT/impl divergence (opposite pointers) | 1 | 5.9 % | GT expects `two_pointers_opposite`; the accepted submission is a single-pass min/max index scan. |
| B4 | ↳ GT/impl divergence (binary search) | 1 | 5.9 % | GT expects `binary_search`; the submission is doubling/subtraction division. |
| **C** | `NO_EVIDENCE_AT_ALL` | 3 | 17.6 % | Zero techniques *and* zero strategies detected (LC 102, 2212, 4284). Overlaps A/B. |
| **D** | `SPURIOUS_SECONDARY_STRATEGY` | 1 | — | Extra strategy inferred on a CONFIRMED record (LC 200). |
| **E** | `FLAT_PATTERN_VS_GROUP_DISAGREEMENT` | 2 | — | `patterns` and `solution_groups` encode different accepted sets (LC 70, 322). On CONFIRMED records. |

Two further production-path observations, recorded separately because they are **not** shadow verdict failures:

- `legacy_ast_vocabulary_mismatch` fired on 32/46 — the legacy AST detector emits ids (`array_traversal` ×26, `brute_force` ×19, `sorting` ×5) that are not in the legacy `ALL_PATTERNS` taxonomy. This is a **production-path taxonomy/drift observation**, unrelated to the structural path's verdicts, and it fires even on clean FULL_MATCH records (e.g. LC 15). It should be reported as a production-layer metric, not counted as an analysis failure.
- 11 records carry groups with `required: []` across **9 distinct live problems** — a data-quality footprint, not a per-submission bug.

## 7. Relation to F1 / F2 / F3 / F4

| fix | attribution in this batch | evidence |
|---|---|---|
| **F1** (empty-`required` ⇒ explicitly unmatchable) | **FAM-A, 11 records.** Changes *visibility* only — 0 verdict changes. | `shadow_unmatchable_group_ids` is populated on all 11; the 11 are exactly the `group_unsatisfiable_empty_required` set. The remaining 6 UNRESOLVED have non-empty `required`. |
| **F2** (`forward_pointer_advance`, same-direction pointer evidence) | **FAM-B1, 3 records** (LC 141 `db-139`, LC 21 `db-252`, LC 4284 `db-254`). | On real code, `forward_pointer_advance` **fires at 0.80** together with `linked_list_traversal` 0.85 on both LC 141 and LC 21. But the stored group still says `bidirectional_index_scan`, so the verdict is unchanged. **F2 is verified working and is being blocked downstream.** LC 4284 does *not* fire: its only index participation is `nums[0]` plus a scalar candidate `ind`, so the ≥2-index-participation requirement is not met. |
| **F3** (ground-truth layer: derivation/refresh + `patterns` vocabulary) | **No direct attribution in this batch**, but it is the single blocker for F2's 3 cases and the root of FAM-A, FAM-E and N5. | See §10. |
| **F4** (variable-window sliding window requires index participation) | **0 failures. Verified fixed, with 0 false positives.** | All 7 `sliding_window` inferences in the batch are on genuine window expectations (LC 3 ×2, 209 ×2, 424, 3225, 3349). Critically, LC 29 (`db-253`) — the CASE 2 false positive that previously produced *SLIDING WINDOW 75 %* — now infers **no strategy at all** (techniques: `sequential_accumulation` 0.85, `loop_state_tracking` 0.75). |

**F4 is the clearest win of Batch 1**: the previously-observed semantic false positive is gone and sliding-window precision across 7 real submissions is 7/7.

## 8. New generalized root causes not covered by F1–F4

**N1 — dual, disagreeing ground-truth representations.** `problem_ground_truth.patterns` (flat legacy ids) and `solution_groups` (structured `required/optional/excluded`) encode different accepted sets for the same problem. 2 records (LC 70, LC 322). Impact: any consumer of `patterns` (legacy matcher, UI "expected patterns", evaluation classifiers) will disagree with the structural matcher. Generalized, not problem-specific.

**N2 — BFS family coverage gap.** `bfs_shortest_path` does not accept queue-based level-order traversal. LC 102 (`db-244`) has 12 facts including `while_loop_truthiness`, `for_loop_iteration`, `linked_structure_traversal`, `linked_attribute_access`, `subscript_index_access`, and yet yields **zero** techniques and zero strategies. This is not a fact-extraction gap — the facts are present — it is a **technique/strategy vocabulary gap** for the queue-traversal shape. Same family as B3 in spirit: the strategy set is narrower than the algorithmic family it names.

**N3 — over-narrow loop gate in a technique detector.** `sequential_accumulation` (T1) hard-requires the `while_loop_comparison` fact, so accumulation performed in a `for` loop never registers even when `for_loop_iteration` + `accumulator_update` are both present. Observed on LC 4284 (`db-254`, `for` loop, candidate index selected). This is a defect in the **fact → technique abstraction**, one level below strategies, and it plausibly suppresses accumulation evidence on any `for`-based prefix/sum/DP-seed implementation.

**N4 — F2's two-index requirement vs single-candidate selection.** LC 4284 uses `ind = i` guarded by `max(nums[0:i+1]) - min(nums[i:])`. F2 was deliberately specified as "≥2 subscript-index variables with one advanced", so it correctly does not fire. Whether a *candidate-selection-over-range* technique is warranted is a design call; the current evidence is **1 submission**, which is not enough to generalize (see §10).

**N5 — ground truth describes an approach the accepted submission does not use.** LC 2212 (`db-251`, 2 facts: pure `min`/`max` index arithmetic) requires `two_pointers_opposite`. LC 29 requires `binary_search`. In both cases **UNRESOLVED is the correct behaviour** under the stated design principle ("prefer UNRESOLVED over confidently assigning an incorrect strategy"). The defect is in GT derivation/quality, and it inflates the apparent UNRESOLVED rate — 2 of the 17 UNRESOLVED are GT problems, not matcher problems.

**N6 — GT derivation coverage.** 11 records / 9 live problems have `required: []` groups. Evidence suggests the derivation path can emit a group with no required concept (only `optional`), which is unmatchable by construction. This is a *systemic producer-side* defect, distinct from F1's *consumer-side* handling.

## 9. Representative submissions per family

| family | submission | problem | facts | techniques | strategies | stored `required` | verdict |
|---|---|---|---|---|---|---|---|
| A | `db-11` | 1 Two Sum | 9 | — | — | `[]` | UNRESOLVED |
| A | `db-192` | 438 Find All Anagrams | 13 | — | — | `[]` (patterns: `hash_map_frequency`, `sliding_window_variable`) | UNRESOLVED |
| A | `db-255` / `db-256` | 4256 / 4258 Uniform Parity Array I/II | 6 / 7 | — | — | `[]` | UNRESOLVED |
| B1 | `db-252` | 21 Merge Two Sorted Lists | 23 | `linked_list_traversal` 0.85, **`forward_pointer_advance` 0.80** | — | `bidirectional_index_scan` | UNRESOLVED |
| B1 | `db-139` | 141 Linked List Cycle | 10 | `linked_list_traversal` 0.85, **`forward_pointer_advance` 0.80** | — | `bidirectional_index_scan` | UNRESOLVED |
| B1 / C / N3 / N4 | `db-254` | 4284 Smallest Stable Index I | 6 | — | — | `bidirectional_index_scan` + `sequential_accumulation` | UNRESOLVED |
| B2 / C | `db-244` | 102 Binary Tree Level Order | 12 | — | — | `bfs_shortest_path` | UNRESOLVED |
| B3 / C | `db-251` | 2212 Removing Min & Max | 2 | — | — | `two_pointers_opposite` | UNRESOLVED *(arguably correct)* |
| B4 | `db-253` | 29 Divide Two Integers | 14 | `sequential_accumulation` 0.85, `loop_state_tracking` 0.75 | — | `binary_search` | UNRESOLVED *(arguably correct; former false SLIDING WINDOW is gone)* |
| D | `db-246` | 200 Number of Islands | 35 | — | `union_find` ✅, `dp_bottom_up` ❌ | union_find family | CONFIRMED |
| E / N1 | `db-238` | 70 Climbing Stairs | 14 | `dp_top_down` | `dp_top_down` | `dp_bottom_up` **or** `dp_top_down` | CONFIRMED (correct) |

Also worth noting from the batch: LC 200 `db-246` and LC 496 `db-193` are both cases where **production said NO_MATCH and the structural path CONFIRMED correctly**, and LC 102 is a case where production said FULL_MATCH (on `bfs_level_order`) while the structural path returned UNRESOLVED — i.e. the shadow path is currently the more conservative of the two on BFS.

## 10. Does F3 now appear important enough to implement next?

**Yes — the distribution points at the ground-truth layer as the dominant remaining blocker, and there is now real-data evidence rather than the earlier reconstructed-code argument.**

Argument from the numbers:

1. **16 of 17 UNRESOLVED have a ground-truth-layer blocker.** FAM-A (11) is a GT shape defect; FAM-B1 (3) is blocked only because stored groups were derived before F2's vocabulary existed; FAM-E (2) is on CONFIRMED records but is a pure GT-consistency defect; N5 identifies 2 more UNRESOLVED where GT, not the matcher, is wrong.
2. **F2 is proven at the detection layer but inert at the verdict layer.** On real LC 21 and LC 141 code the new technique fires at 0.80 — the abstraction works. The only reason the verdict does not move is that stored `solution_groups.required` still contains `bidirectional_index_scan`. Until groups can be re-derived, any technique/strategy vocabulary improvement is invisible in production. That is the definition of a blocking architectural issue.
3. **The unmatchable-group footprint is systemic, not incidental:** 9 distinct live problems carry `required: []`. F1 (labelling) makes this visible; only F3 can fix it.
4. **The remaining genuine matcher/abstraction gaps are small:** 1 BFS-family coverage case (N2), 1 loop-gate case (N3), and 1 under-specified pointer case (N4). Those are worth a small follow-up batch, but they are not where most of the loss is.
5. **F4 proves the Batch 1 approach works**: one generalized rule removed a false semantic inference (LC 29) with zero regressions and 7/7 sliding-window precision.

Caveat, stated plainly: this report cannot change any verdict on the 3 B1 cases by itself, because stored groups are derived once and the loader prefers stored values. Re-deriving them is exactly the F3 change.

---

## Recommendation — next engineering step

**Implement F3 (the ground-truth derivation/refresh layer) as Batch 2 — nothing else first.** Concretely, in order of value:

1. **Make group derivation vocabulary-aware and re-runnable.** A mechanism to (re)derive `solution_groups` from the curated/LLM source such that stored groups pick up the current technique/strategy vocabulary. This is what converts the 3 FAM-B1 cases and makes F2 (and any future vocabulary work) actually reachable in production. It must remain idempotent and must not auto-regenerate on every request (ground truth is generated once per problem).
2. **Reject/repair empty-`required` groups at derivation time** (N6), rather than only labelling them unmatchable at match time (F1). A group whose only content is `optional` cannot be satisfied by construction; it should never be persisted. Success criterion: `required: []` count goes 9 → 0 in the live DB, and the 11 FAM-A records either confirm correctly or fail for an *explicit* reason.
3. **Reconcile `patterns` with `solution_groups`** (N1/E): either derive the flat label from the structured groups, or treat groups as authoritative and mark the flat label derived-only. Success criterion: the 2 disagreement cases disappear from the harness's false-confirmation flags without touching the matcher.
4. **As a small, separate follow-up batch (not now):** N3 (`sequential_accumulation` should accept `for_loop_iteration`) and N2 (queue-based BFS family coverage). Both are one-to-two-line generality fixes with clear generalized tests; keep them out of the F3 change so the regression signal stays clean.
5. **Do not implement N4 yet.** One submission is not a generalized signal; keep collecting.

Two permanent evaluation guards worth adding while doing this:

- A **GT-consistency check** in the harness comparing `patterns` against the union/alternatives of `solution_groups` (catches N1-style drift automatically).
- **Separate the production-path taxonomy flag** (`legacy_ast_vocabulary_mismatch`) from shadow-verdict failure families in the harness report, so production taxonomy noise never again dominates the failure distribution (it accounted for 32/46 raw flags).

Suggested acceptance criteria for the F3 batch: shadow suite green (466+ tests, originals untouched), full repo suite at the 874/1 baseline, re-run of this same 46-submission export showing FAM-A → 0, FAM-B1 → 0 (i.e. the 3 pointer cases move from UNRESOLVED to CONFIRMED), FAM-E → 0, and **no new false confirmations, no new spurious strategies, no CONTRADICTED outcomes**.

---

*No production analysis code was modified for this evaluation pass. All numbers are reproducible via:*
`python -m experiments.code_analysis_evaluation.runners.real_submission_harness --input experiments/code_analysis_evaluation/dataset/db_submissions_export.json --registry experiments/code_analysis_evaluation/results/registry_db_batch1.json --groups-from-db --out-dir experiments/code_analysis_evaluation/results/db_batch`
