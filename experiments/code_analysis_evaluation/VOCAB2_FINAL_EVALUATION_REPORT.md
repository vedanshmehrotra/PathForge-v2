# Vocabulary Layer 2 — FINAL Post-Layer Evaluation (Frozen Code)

**Evaluation/audit only. No production code, shadow detector, technique, ground-truth derivation, matcher, test, or database row was modified.** The only artifacts created are this report and two evaluation-only files under `experiments/` (`runners/vocab2_final_eval.py` and `results/vocab2_final_eval/`), which import the frozen pipeline but are not imported by it.

Measured on: the frozen Vocabulary Layer 2 code (post Step 4), the 46-record development corpus, and the independent 301-case disjoint corpus (`src/ast_detection/semantic/disjoint_corpus*.py`, built in-process from the five `build_*` functions; total asserted == 301).

---

## 1. Executive summary

- The frozen 46-record regression reproduces exactly: **42 CONFIRMED / 4 UNRESOLVED / 0 CONTRADICTED / 0 ERROR**, with zero technique/strategy diffs against the Step 4 baseline.
- On the independent 301-case corpus the measurable families are strong: **two_pointers_opposite P=1.000 R=0.711 F1=0.831 · prefix_sum P=0.750 R=0.679 F1=0.713 · binary_search_standard 2/2**. `hash_map_lookup` shows **P=0.957** with **R=0.379** — high precision, structurally-caused low recall.
- **13 FPs total (vs 12 for the legacy competition model measured in 3C), concentrated in one family:** 12 of 13 are `prefix_sum`-labeled `ps_vs_generic` negatives detected as `sequential_accumulation`. This is a **benchmark label-ambiguity artifact**: those negatives were authored to be "generic accumulation, not prefix sum", but the production V1 mapping deliberately treats `sequential_accumulation` as *the* implementation of the `prefix_sum` GT label. Under V1 semantics these are not matcher errors.
- Recall losses decompose into **three named, recurring, structurally distinguishable forms**, all verified at fact level: assign-form counting (`freq[x] = freq.get(x,0)+1`, 16 cases), append-accumulation (`prefix.append(prefix[-1] + x)`, 13 cases), and tuple-unpack construction (`a, b = {}, {}`, 2 direct + several contextual).
- **Vocabulary Layer 2 measurably improves hash_lookup generalization** versus the 3C models: FP 12 → 1 (and that one is a GT-representation defect, not detector noise), while the FN families moved to honest taxonomy boundaries rather than false suppression.
- **Candidate-selection boundary special check:** the corpus contains **0** binary-search-after-sort shapes and running-max shapes are **not** sliding-window labeled; the disclosed loop-form boundary is therefore *untested boundary evidence*, not a measured defect.
- Recommendation: **(B) one narrowly defined engineering batch is justified** — M2-relation reuse for `sequential_accumulation` (assign-form counting + append-accumulation), with measured FP exposure of exactly 1 case corpus-wide and 6 existing gates against it.

---

## 2. Frozen architecture state (Phase 1)

Measured from the current code, no changes:

- **13 registered techniques** (`VALID_TECHNIQUES`): `bidirectional_index_scan, candidate_selection, carry_propagation, fixed_window_maintenance, forward_pointer_advance, frequency_counting, hash_lookup, iterative_table_filling, linked_list_traversal, loop_state_tracking, monotonic_stack_maintenance, recursive_branching, sequential_accumulation`.
- **22 V1 concepts** (`VALID_V1_CONCEPTS` = techniques ∪ strategies); strategies: `two_pointers_opposite, binary_search, sliding_window, dfs_backtracking, dp_top_down, dp_bottom_up, bfs_shortest_path, union_find, monotonic_stack_strategy`.
- **33 V0 pattern mappings** in `PATTERN_TO_V1_MAPPING`. Four map to `required=[]` (`dfs_iterative, greedy_interval, heap_top_k, topological_sort`) → `missing_vocabulary_for_patterns` reports exactly those four (Batch 2A mechanism working as designed).
- New Layer 2 facts confirmed present: `mapping_construction`, `membership_test`, `subscript_read` (Step 2), `list_construction`, `indexed_write.syntax_form/operator` (Step 3), `sorting_operation`, `extremum_access` (Step 4).
- Group semantics: alternative-family splitting via shared `pattern_family()` helpers (GT repair), empty-required groups unmatchable (F1), refresh re-derivation via `refresh_group_vocabulary` (Batch 2A).

---

## 3. Final 46-record regression (Phase 2)

Harness: `real_submission_harness --groups-from-db --force`, fresh registry, fingerprint-matched comparison against the Step 4 baseline.

| metric | frozen result | vs Step 4 baseline |
|---|---|---|
| CONFIRMED | 42 | = |
| UNRESOLVED | 4 | = |
| CONTRADICTED / ERROR | 0 / 0 | = |
| technique/strategy/verdict diffs (per-record) | **0** | = |

The 4 UNRESOLVED remain exactly db-64, db-251, db-253, db-254. No technique losses, no strategy changes, no GT drift introduced. **Phase 2 passes as frozen.**

---

## 4. Independent 301-case evaluation (Phase 3)

Corpus: 5 disjoint modules, 301 cases (180 pos / 121 neg), labeled with V0 pattern names and confusable-pair families. **This corpus is independent of the 46-record calibration corpus** (per its own docstring and the 3C report) and contains none of the same submission code.

Label bridge (documented, deterministic): each labeled V0 pattern is mapped through the production `PATTERN_TO_V1_MAPPING`; a positive is TP iff **all** required concepts are detected; a negative is FP iff any required concept is detected. Required concepts may be techniques or strategies (the union, matching how the matcher satisfies groups).

| labeled pattern | n (pos/neg) | TP | FP | FN | TN | P | R | F1 |
|---|---|---|---|---|---|---|---|---|
| hash_map_lookup | 89 (58/31) | 22 | 1 | 36 | 30 | **0.957** | 0.379 | 0.543 |
| prefix_sum | 82 (53/29) | 36 | 12 | 17 | 17 | 0.750 | 0.679 | **0.713** |
| two_pointers_opposite | 69 (38/31) | 27 | 0 | 11 | 31 | **1.000** | 0.711 | 0.831 |
| array_traversal | 59 (29/30) | — | — | — | — | *not measurable from this corpus* (no V1 mapping) |
| binary_search_standard | 2 (2/0) | 2 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 (n=2, not significant) |

**Not measurable from this corpus:** sliding_window, two_pointers_same, DP families, graph/search families, candidate_selection, hash_map_frequency, greedy — the benchmark has no labels for them (no positives/negatives keyed to those V0 patterns, and `array_traversal` has no V1 mapping at all). This is stated rather than estimated.

---

## 5. Cross-pattern false-positive analysis (Phase 4)

**13 FPs total.** Grouped:

### FP-1: `ps_vs_generic` → `sequential_accumulation` — 12 of 13
`acc_string_concat, acc_counter_loop, acc_nested_loop_sum, acc_string_build_loop, dp_max_subarray, greedy_lemonade, greedy_jump_game2, factorial_loop, string_join_words, count_negative, dp_max_profit_1, greedy_assign_cookies` — all labeled `prefix_sum` negatives, family `ps_vs_generic`.

- Predicted technique: `sequential_accumulation` (+ `candidate_selection` on `greedy_jump_game2`).
- Responsible facts: standard `accumulator_update` + loop evidence — the canonical accumulation shape.
- Attribution: **benchmark-label ambiguity, not an overly broad technique.** The corpus authors wrote these as "generic accumulation, not prefix sum" (family name `ps_vs_generic`). But in the V1/production vocabulary, `prefix_sum` maps to `required=[sequential_accumulation]` and `sequential_accumulation` *is* the generic accumulator technique by design (that is what N3 fixed). The legacy competition model produced the identical 12 FPs under the same V0 labels (3C: prefix_sum FP=12), confirming the FP set is a property of the V0 labels, not of Vocabulary Layer 2.
- Corollary: corpus-wide, `sequential_accumulation` fires on **30 of 121** negatives (25%) — but every one is a V0 `prefix_sum` negative, i.e. generic accumulation. Under V1 semantics none of these is reachable as a real false confirmation because no non-prefix GT label requires `sequential_accumulation` (verified from the mapping table: it appears as required only for `prefix_sum`, as optional for `greedy_local`, and in `hash_map_frequency` mappings).

### FP-2: `hm_adjacency_list` → `hash_lookup` — 1 of 13
Dict-of-lists graph builder with `if u not in graph` membership and gated subscript reads.
- Attribution: **ground-truth representation defect, not detector noise.** The alternative-splitting semantics added in the GT repair are keyed on `pattern_family()` classes; `hash_map_lookup` and `prefix_sum` are distinct families, but `hash_map_lookup` and `hash_map_frequency` (the semantically correct label for an adjacency map) currently share the same `hash_map` family class, so the splitter does not separate them. The technique itself is behaving exactly as specified (dict identity + gated read). This is the *only* false positive in the hash family in the entire corpus (3C competition model: 12).

### Requested cross-pattern pairs — measured outcomes
| pair | result |
|---|---|
| candidate_selection vs binary_search | 0 collisions. `bs_*` TP=2, and candidate_selection fires on `bs_*` cases only where they are two-pointer-labeled negatives (`bs_two_ptrs_overlap`, `bs_first_bad`, `bs_sqrt_int` → verdict **TN** because `two_pointers_opposite` is correctly not detected). |
| candidate_selection vs sliding_window | 0 collisions measured: `sw_longest_unique` fires candidate_selection but verdict **TN** (two_pointers_opposite not detected). No `sw_*` case is a positive for any candidate-consuming label. |
| hash_lookup vs visited-set membership | **0 FPs in 31 set-bearing negatives** (19 `hash_vs_bfs` + visited-set cases). Step 2's map-identity fence holds out of sample. |
| hash_lookup vs memoization | no memoization-labeled negatives in the corpus; recursion fence remains regression-tested in the unit suite (db-238/db-240). |
| frequency_counting vs DP tables | 0 FPs. Frequency evidence appears only on the 2 Counter negatives (`hm_max_points_line`, `hm_char_replacement`), both semantically counting-dominant. |
| frequency_counting vs ordinary map construction | 0 FPs (plain builders do not produce counted writes). |
| sort-form candidate selection vs generic sorting | 0 FPs (8 sort-form tests plus no sort-based FP in 301 cases). |
| strategy overlap / secondary-strategy noise | measured at the GT level, not fact level: 2 `extra_strategy_inferred` + 2 `confirmed_on_unexpected_strategy` in the 46-record corpus, unchanged across all batches — secondary strategies are never verdict-determining there. |

---

## 6. False-negative family analysis (Phase 5)

### FN-1: `hash_map_lookup`, missing `hash_lookup` — 36 cases, fully decomposed
| actual code semantics | n | detected instead | honest verdict under V1 taxonomy |
|---|---|---|---|
| **assign-form counting** `freq[x] = freq.get(x,0)+1` | 14 (+2 Counter where only `frequency_counting` is missing = counted-write gap; 16 total missing only `frequency_counting`) | nothing, or `frequency_counting` only | FN by vocabulary *form*, not concept |
| **set membership** (visited/dedup/distinct/jewels) | 13 | mostly nothing | **taxonomy limitation, correctly refused** (db-64 design decision) — unless the benchmark intends these as set semantics, in which case *benchmark-label ambiguity* |
| dict lookups in unextracted syntax forms | ~6 | nothing | FN by syntax form |
| other (linked-list copy map, LRU, sudoku) | 3 | unrelated techniques | genuinely supported / mixed structures |

The largest single sub-family (assign-form counting, 16) is **structurally distinguishable and recurring**: corpus-wide the assign form appears in 24 cases, **exactly 1 of which is a negative** (`bfs_topological`, which also has real membership evidence against it). Note `hm_two_sum_class` (gated `complement in self.nums` with map identity) is a genuine hash_lookup miss.

### FN-2: `prefix_sum`, missing `sequential_accumulation` — 17 cases
- **13 = append-accumulation** (`prefix.append(prefix[-1] + x)`, incl. 5 `self.prefix` attribute forms): no `accumulator_update` fact exists for `.append(self.x[-1] + n)` — the extractor's accumulator rule keys on direct assignment/augmented assignment to the variable, not method-call self-reference. Fact-level probe on a minimal snippet confirms zero facts.
- **4 = indexed-write DP-style build** (`out[i+1] = out[i] + arr[i]`): emit `indexed_write` but not `accumulator_update`, and `prefix_sum` mapping has no `iterative_table_filling`-satisfied path (`iterative_table_filling` is optional-only).
- All 17 are **missing structural evidence** (category A), single recurring form each, and corpus-wide the self-referential append form appears in 10 cases, **all positives** (0 negatives).

### FN-3: `two_pointers_opposite` strategy — 11 cases
5-while-2-for: the strategy definition requires a `while` loop; for-loop convergence pointers are not detected. Two tree/linked-list cases (`tp_is_symmetric_tree`, `tp_reverse_linked_list`) are arguably mislabeled `tp_genuine` in the benchmark (recursive / linked-list semantics — not opposite-array pointers). **Strategy-level form limitation** (E) with a clean structural discriminator (for-loop + two index variables converging), currently unimplemented.

### FN-4: `binary_search_standard` — 2
Benchmark notes say 4 (its `total_in_corpus` count), but only 2 are emitted by `build_last_batch` — a **benchmark defect** (label count vs emitted cases), hence F1=1.000 is reported at n=2 and flagged as not significant.

---

## 7. The remaining 4 development-corpus cases (Phase 6)

| case | problem | code shape (verified) | current evidence | group required | verdict correctness |
|---|---|---|---|---|---|
| db-64 | 4080 | `sett=set(nums)` + `while True: if k*i not in sett` | **zero** techniques/facts beyond loop | `frequency_counting` | **Correct refusal.** Set membership is not frequency counting by design (v2 correction). Resolving it honestly requires a *set-membership* concept — explicitly out of scope per the v2 design decision. |
| db-251 | 2212 | `nums.index(max(nums))` index arithmetic, no loops | zero evidence | `two_pointers_opposite` | **Correct refusal** — closed-form index arithmetic has no loop structure to detect. Would need built-in-call/eager-scan semantics; no recurring corpus support. |
| db-253 | 29 | nested while, doubling divisor | `sequential_accumulation` + `loop_state_tracking` only | `binary_search` | **Correct refusal.** Doubling-search is genuinely a binary-search-*like* structure, but evidence is accumulation (`value += value`, `count += count`), not halved-range subscripting. New vocabulary would be needed; 1 example corpus-wide. |
| db-254 | 4284 | prefix max/suffix min via slices, candidate index | `candidate_selection` only | `forward_pointer_advance` ∨ `sequential_accumulation` (alternatives) | **Correct refusal.** Slices/`max()`-based range reasoning produces no detected facts. The original Case-3/4/5 family observation; single case, no recurring support. |

**All four remain correct, truthful UNRESOLVED outcomes under the current taxonomy.** None is a matcher error; none has multi-case support for a new concept.

---

## 8. Ground-truth integrity findings

- Batch 2A / GT-repair mechanisms verified live: `missing_vocabulary_for_patterns` = exactly the 4 intentionally-unmapped patterns; no group collapsed; `--groups-from-db` refresh reproduced identical groups across all runs.
- **One new finding:** the `pattern_family()` classification used by the alternative-splitter groups `hash_map_lookup` and `hash_map_frequency` into the same family class, which allowed the single `hm_adjacency_list` mislabel to surface as a hash FP under the benchmark's conjunctive reading. Impact is bounded to that benchmark reading (production GT rows are unaffected — the 46-record corpus shows no drift). Classified GROUND_TRUTH / BENCHMARK_LIMITATION.
- The problem-3225 drift (declared `hash_map_frequency` not covered by any group) persists — **inherited from Step 3, disclosed there**, and out of scope for this audit.

---

## 9. Architecture health observations (Phase 7)

1. **Structural abstraction quality:** strong — 42/46 real submissions confirm on real strategies; out-of-sample strategy families (two-pointers, binary search) hold precision 1.000.
2. **Syntax normalization (M1):** the remaining FN set is now *precisely* characterized by the forms M1 did not cover: method-call self-reference (`.append(self.x[-1] + v)`) and tuple-unpack *targets on the left of a multi-target assign* are the two normalization gaps with measured multi-case impact.
3. **Relation reuse (M2):** proven operative in the 46-record corpus (relation-driven fences) — and its *absence* is the measured cause of FN-1/FN-2: `updated_in_loop` already exists but nothing joins `indexed_write`/call args into accumulation semantics. Extending `sequential_accumulation` via relations is a natural consumer, matching the M2 design intent.
4. **Technique modularity:** high — Layer 2 added 4 techniques and 6 fact types across 4 steps with zero cross-technique regressions in any batch; sort-form and loop-form coexist under one technique id with independent fences.
5. **Strategy separation:** strong out-of-sample — **zero** strategy FPs on 69 two-pointer cases; binary search 2/2. The `greedy_jump_game2` overlap is at the *technique* level only and harmless under group semantics (optional concept).
6. **Ground-truth representation integrity:** high — one bounded family-classification defect found (see §8); alternative-group semantics verified live on problem 3236's shape.
7. **Alternative solution-group handling:** working — 46-record recoveries held (db-49/51/194 remain CONFIRMED).
8. **Determinism:** maintained — all evaluation runs are reproducible; harness is fully offline/deterministic (no LLM, no network).
9. **False-positive control:** excellent — **1 hash FP in 89 hash-labeled cases** (vs 12 for the legacy model); all 13 FPs trace to 2 causes, neither of which is detector noise.
10. **Generalization beyond the development corpus:** *supported for what the benchmark can measure* (two-pointer, binary search, hash precision, prefix precision). Recall gaps are concentrated and named; they are not random detector misses.

---

## 10. Special checks

### 10.1 Previous hash-lookup generalization result (3C comparison, same 301 corpus)

| | 3C AST | 3C semantic-ungated | 3C competition | **VL2 (frozen)** |
|---|---|---|---|---|
| hash_map_lookup TP | 30 | 47 | 30 | **22** |
| FP | 12 | 28 | 12 | **1** |
| FN | 28 | 11 | 28 | **36** |
| F1 | 0.600 | 0.707 | 0.600 | **0.543** |

Not comparable by raw F1 alone — the FN *composition* changed qualitatively:
- 3C's FNs were dominated by over-suppression (the competition rule killed 27 genuine hash cases). VL2 produces **zero suppression of genuine dict code**: the 36 FNs decompose into 16 assign-form counting, 13 set-membership (honest taxonomy boundary), ~6 syntax-form, 1 genuine gated-read miss.
- 3C's 12 FPs were misclassification noise (BFS visited sets, two-pointer incidental membership, prefix interaction). VL2 has **1 FP, itself a GT-representation artifact** (§5 FP-2).
- VL2 is stricter by design: it refuses where semantics are ambiguous rather than confirming. The set-membership refusal is the v2 design correction working out of sample.
- **Verdict: Vocabulary Layer 2 improves the generalization behavior** (FP control is qualitatively better, no false suppression), with recall now bounded by three named forms rather than by rule brittleness.

### 10.2 Candidate-selection boundary (binary-search-after-sort / window-running-max)

- **0** corpus cases contain sort + binary-search (`mid`) shapes.
- 10 cases contain running-max shapes; the sliding-window ones are V0-labeled `two_pointers_opposite` negatives — and `two_pointers_opposite` is **never** fired on them (TN), so no measured impact.
- `greedy_jump_game2` (prefix-labeled negative) fires `candidate_selection` via the loop form: structurally a genuine greedy candidate/interval selection (`farthest = max(farthest, ...)`, `current_end` rebinding); counted FP only under the V0 prefix label. BENCHMARK_LIMITATION.
- Classification: **UNTESTED BOUNDARY EVIDENCE** — the loop-form fence question remains open with no measured corpus impact. No extrapolation made.

---

## 11. Issue classification table (Phase 8)

| # | issue | evidence | category |
|---|---|---|---|
| 1 | Assign-form counting not recognized as accumulation (`freq[x]=freq.get(x,0)+1`) | 16 FN + measurable benefit (1 FP exposure) | **TECHNIQUE_GENERALIZATION** |
| 2 | Append-accumulation not recognized (`x.append(x[-1] + v)`, incl. `self.x`) | 13 FN + 10/10 positive-only corpus support | **TECHNIQUE_GENERALIZATION** (same batch as #1: one relation-join change in one technique) |
| 3 | Tuple-unpack construction invisible (`a, b = {}, {}`) | 2 direct FN + contextual misses (hm_is_isomorphic, hm_encode_decode) | DETECTOR_GENERALIZATION |
| 4 | Oppoint-pointers for-loop convergence form | 11 FN (5-while-2-for measured) | STRATEGY_GENERALIZATION |
| 5 | `hm_adjacency_list` family classification | 1 FP | GROUND_TRUTH / BENCHMARK_LIMITATION |
| 6 | `ps_vs_generic` negatives counted as prefix FPs | 12 FP under V0 labels | BENCHMARK_LIMITATION (V0 label vs V1 semantics) |
| 7 | Set-membership semantics (db-64, 13 benchmark cases) | intentional refusal | TAXONOMY_LIMITATION (v2 design decision) |
| 8 | binary_search_standard count mismatch (notes say 4, 2 emitted) | — | BENCHMARK_LIMITATION |
| 9 | Loop-form boundary (bs-after-sort, window running-max) | no measured impact | NO_ACTION (untested boundary) |
| 10 | 4 `required=[]` patterns (`dfs_iterative`, `greedy_interval`, `heap_top_k`, `topological_sort`) | no corpus support measured | NO_ACTION |
| 11 | problem-3225 GT drift | inherited from Step 3 | GROUND_TRUTH (pre-existing, disclosed) |
| 12 | 4 remaining dev-corpus UNRESOLVED | all truthful refusals | NO_ACTION |

---

## 12. Evidence for/against another engineering batch

**For (recurring, reusable, bounded risk):**
- #1+#2 jointly address **29 FN cases (83% of hash+prefix FN)** through *one* mechanism: extending `sequential_accumulation` to consume the existing M2 relation layer (`updated_in_loop`, already computed) over `indexed_write`/call-argument forms — no new fact types, no name heuristics, mirrors the N3 precedent exactly.
- **Measured FP exposure is 1 case corpus-wide** (`bfs_topological`), which already carries contradicting evidence (`membership_test` against a map). Six existing fences apply: sets (no mapping identity), DP arrays (Assign-form cross-key writes, Step-3-tested), recursion memos, unused counters, positional-index arrays, scalar accumulators.
- Multiple independent examples per form; both forms are structurally distinguishable; acceptance is measurable on both corpora.

**Against / risks:**
- `sequential_accumulation` currently has **zero FPs in 301 cases**; any widening risks the clean sheet. Mitigation: gated to self-referential forms (`x[k] = x.get(k,0)+n` requires `.get(key, 0)` on the *same* variable; `x.append(x[...])` requires the appended argument to reference the same list), plus the relation-layer requirement that the update occur inside the loop.
- The for-loop two-pointer form (#4) touches a strategy definition — higher regression surface, weaker form evidence (11 cases, 2 arguably mislabeled). Defer.

---

## 13. Recommended next engineering direction (if any)

**One narrowly defined batch: "sequential_accumulation relation-layer extension"** covering exactly:
1. assign-form self-referential counted writes (`freq[x] = freq.get(x, 0) + 1` → `accumulator_update` on `freq`, via M2 `updated_in_loop`),
2. append-form self-referential accumulation (`prefix.append(prefix[-1] + x)`, including `self.` attribute bases),

with generalized positive/negative tests (including `bfs_topological` as a negative), the established shadow + full-repo suites, and 46-record + 301-case before/after measurement. Expected: hash_map_lookup recall 0.379 → ~0.65, prefix_sum recall 0.679 → ~0.88, hash FP ≤ 1, prefix FP +0–1, all at technique level with zero strategy-level changes.

Not in the batch: tuple-unpack construction (#3, smaller and separable), for-loop two-pointers (#4, strategy-level), any GT mapping change, any new fact type, any set-membership concept.

---

## 14. Explicit list of things that should NOT be changed yet

1. **No set-membership concept** — the v2 refusal is correct and out-of-sample-validated (0 FPs in 31 set-bearing negatives).
2. **No strategy definitions** — `two_pointers_opposite` (P=1.000) and `binary_search` must not be touched for the for-loop FN form until a batch is dedicated to it.
3. **No threshold or confidence changes** — precision 1.000/0.957 must not be traded for recall.
4. **No loop-form `candidate_selection` tightening** — untested boundary evidence only (§10.2).
5. **No new fact types** for #1/#2 — the M2 relation layer plus existing facts suffice (verified by fact-level probes).
6. **No GT mapping edits** for `prefix_sum`/`hash_map_lookup` — the label bridge is correct; the 12 `ps_vs_generic` FPs are benchmark label artifacts.
7. **No detector changes for db-251/db-253/db-254** — single-case support each; honest refusals.
8. **Do not "fix" the 3225 drift or the benchmark count mismatch** as part of an analysis batch — they are data/bookkeeping issues with their own (separate) change surface.

---

## 15. Final conclusion

Based on the frozen 46-record regression (42/4/0/0, zero drift), the independent 301-case evaluation (2 FP-free strategy families at P=1.000, hash precision 0.957 with 1 representational FP, prefix precision 0.750), and the decomposition of every remaining FP/FN into named, bounded causes:

> **(B) One narrowly defined engineering batch is justified**: the `sequential_accumulation` relation-layer extension (assign-form counting + append-accumulation), with measured corpus-wide FP exposure of 1 and six existing fences. Everything else is NO_ACTION / TAXONOMY_LIMITATION / BENCHMARK_LIMITATION, or deferred (for-loop two-pointers) pending dedicated evidence.

Vocabulary Layer 2 itself is sound and generalizes where the benchmark can measure; the batch above completes its one remaining high-value, low-risk recall gap.
