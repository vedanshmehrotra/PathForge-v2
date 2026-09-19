# Sequential Accumulation — M2 Relation-Layer Extension Report

**Batch scope:** extend the existing `sequential_accumulation` technique with two
loop-carried container forms, using the existing M2 relation layer. No new
strategy, no new vocabulary concept, no ground-truth change, no matcher change,
no problem-ID or variable-name logic, no confidence-threshold change.

**Verdict:** implemented, measured, and **not clean enough to declare an
unqualified success** — the append-form half is a clean high-value win; the
assign-form half recovers 2 real prefix sums but also produces **1 new false
positive** whose cause is a genuine taxonomy boundary. Details and the
quantified trade-off are below; the decision on whether to keep the assign-form
half is left open.

---

## 1. Root cause of both false-negative forms

Both forms were invisible to every pre-existing evidence path:

| form | example | why it produced nothing |
|---|---|---|
| assign-form | `freq[x] = freq.get(x, 0) + 1` | `accumulator_update` only fires for **Name** targets (`_detect_equal_assignment` / `_detect_augmented_assignment` skip `Subscript`). `indexed_write` fired but carried no RHS self-reference. `def_use_pairs` is name-level and links `Name` targets only, so a `Subscript` target got no def→use join. |
| append-form | `prefix.append(prefix[-1] + x)` | no fact represented `.append` at all; `collection_ops` recorded only **Name** receivers; appends were not in `updated_in_loop`. |

The missing concept in both cases is the same: a **same-structure
self-reference inside a loop-carried update on a container**.

## 2. Existing M2 relations reused

No relation was invented; one was added and three were completed:

- **`self_referential_updates` (new, loop-scoped by construction)** — the only
  genuinely new relation datum. It records, per structure, which cumulative
  update kinds occur in a loop body: `indexed_write` and/or `append`. Being
  loop-scoped, a one-shot self-referential assignment outside a loop is never
  recorded, so the relation *cannot* fabricate accumulation on it.
- **`updated_in_loop` (completed)** — extended to record `.append(...)`
  **receivers** (previously only assignment targets), and to key `Subscript`
  targets by their **container structure** rather than the inner `Name`
  (`self.nums[k] = …` now records `nums`, matching `container_base`).
- **`collection_ops` (completed)** — extended to attribute receivers
  (`self.prefix.append` → `prefix`). It had exactly one consumer (the new
  helper), so the extension is consumer-safe.
- **`def_use_pairs` / `used_as_subscript_index` / `iterated_in_for`** — reused
  unchanged for the loop-membership and loop-variable-exclusion gates.

**Relation contract preserved:** the relation may *tighten* admissibility but
never *create* detection. The technique independently re-corroborates every
relation hit against a structural fact (`indexed_write` fact on the structure,
or a recorded `append` op). Unit-tested by
`test_relations_cannot_fabricate_*`.

## 3. Exact implementation change

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/relations.py` | new `self_referential_updates` relation + `_record_self_referential_update`; public `container_base` / `count_structure_reads` helpers; `.append` receiver recorded in `updated_in_loop`; attribute receivers recorded in `collection_ops`; `_updated_names` keys `Subscript` targets by container structure |
| `pathforge/ast_analysis/shadow/fact_extractor.py` | `indexed_write` emitted for `AnnAssign` via the existing M1 target normalizer (statement-form completion); attribute-subscript targets name the attribute structure instead of `""` |
| `pathforge/ast_analysis/shadow/techniques.py` | new `_seq_accum_container_evidence` (last-fallback path) + reordered entry so the container path runs **before** the `if not acc_facts: return None` early exit |
| `pathforge/ast_analysis/shadow/tests/test_seq_accum_relation_extension.py` | new, **41 tests** |

The scalar relation path (`_seq_accum_evidence_via_relations`) and the original
fact-join path (`_seq_accum_evidence_fact_join`) are untouched; the container
path is strictly the **last** fallback, so all previously-supported inputs keep
their outputs.

## 4. Was a new fact type needed?

**No.** The design's expectation held: the assign form rides the existing
`indexed_write` fact (completed for `AnnAssign`); the append form is corroborated
by the existing `collection_ops` relation. Verified empirically — the union of
fact types observed across the 301-case corpus is **identical** before and after:

```
fact types only in NEW: []
fact types only in BASE: []
```

## 5. Assign-form semantics

Structural predicate (name-free): an `Assign`/`AnnAssign` whose value is a
`BinOp` with `Add`/`Sub`, whose target is a `Subscript` of structure `S`, and
whose value contains **exactly one** read of `S` (subscript read or method-call
receiver). Recorded as `self_referential_updates[S] |= {"indexed_write"}` only
inside a loop body.

- `freq[x] = freq.get(x, 0) + 1` → fires (one receiver read)
- `counts[ch] = counts.get(ch, 0) - 1` → fires
- `out[i+1] = out[i] + arr[i]` → fires (one subscript read)
- `dp[i] = dp[i-1] + dp[i-2]` → **two** reads → not recorded (**DP fence holds**)
- `d[k] = v` → not a `BinOp Add/Sub` → not recorded

## 6. Append-form semantics

Structural predicate: `S.append(expr)` where `expr` is a `BinOp` with `Add`/`Sub`
containing exactly one read of `S`, inside a loop body. Recorded as
`self_referential_updates[S] |= {"append"}`.

- `prefix.append(prefix[-1] + x)` → fires
- `self.prefix.append(self.prefix[-1] + x)` → fires (attribute receiver)
- `result.append(x)` → argument not a `BinOp` → not recorded
- `copy.append(src[-1])` → reads a different structure → not recorded

## 7. Negative fences (all verified)

| fence | status |
|---|---|
| A. DP bottom-up `dp[i] = dp[i-1] + dp[i-2]` | holds — `dp_lcs_not_prefix` stayed **TN** |
| B. scalar accumulation `total += x` | unchanged (scalar path) |
| C. plain list building `result.append(x)` | not recorded (test-covered) |
| D. ordinary map replacement `d[k] = v` | not recorded (test-covered) |
| E. unrelated self-reference `d[k] = f(d2[k])` | different structure → not recorded |
| F. memoization / recursion | unchanged |
| G. candidate selection `best = max(best, x)` | unaffected |
| H. window-state updates | tested; window bodies without a cumulative self-ref stay negative |
| I. non-loop self-reference | relation is loop-scoped → not recorded |
| J. unrelated collection calls | not recorded |

## 8. Tests added

`test_seq_accum_relation_extension.py` — **41 tests**: assign-form positives
(4 parametrized + supporting-facts, name-independence, `AnnAssign`,
attribute-backed), append-form positives (7 parametrized + relation records),
container negatives (plain append, DP table, ordinary map assignment,
non-self-ref append), relation-contract tightening tests (no fabrication without
supporting fact / loop membership / collection op; real relations tighten),
container-path-is-last-fallback, disclosed window boundaries, and N3 regression
(scalar forms + loop-variable exclusion preserved).

## 9. Shadow suite

**810 passed** (769 baseline + 41 new), 0 failed.

## 10. Full repository suite

**1684 passed / 1 failed** — the failure is the known **pre-existing legacy**
`src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`,
present at the frozen baseline and untouched by this batch (legacy detector
path). No new failure.

## 11. 46-record fingerprint-matched evaluation

**42 CONFIRMED / 4 UNRESOLVED / 0 CONTRADICTED / 0 ERROR — byte-identical to the
frozen baseline.**

- fingerprint overlap 46/46
- verdict diffs: **0**
- technique diffs: **0**
- strategy diffs: **0**
- fact-type diffs: **0**, fact-count diffs: **0**

(The development corpus contains no assign-/append-form container accumulation,
so this batch is expected to be — and is — inert on it.)

## 12. 301-case independent evaluation (before → after)

| total | TP | FP | FN | TN |
|---|---|---|---|---|
| baseline | 87 | 13 | 64 | 78 |
| after | **98** | **14** | **53** | **77** |

Per family:

| family | baseline | after |
|---|---|---|
| `prefix_sum` | TP=36 FP=12 FN=17 TN=17 | **TP=47 FP=13 FN=6 TN=16** |
| `hash_map_lookup` | TP=22 FP=1 FN=36 TN=30 | **unchanged** |
| `two_pointers_opposite` | TP=27 FP=0 FN=11 TN=31 | unchanged |
| `binary_search_standard` | TP=2 FP=0 FN=0 TN=0 | unchanged |
| `array_traversal` | not measurable | not measurable |

**A design expectation did NOT materialise.** The design predicted
`hash_map_lookup` recall `0.379 → ~0.65`. It is **unchanged at 0.379**. Reason:
the corpus labels frequency-counting implementations `hash_map_lookup`, whose
bridge requires `hash_lookup`; the assign form produces `sequential_accumulation`,
not `hash_lookup`. 16 hash-family cases did acquire `sequential_accumulation`
evidence, but their verdicts are governed by `hash_lookup`, so none flipped.

## 13. Precision / recall / F1 changes

| family | metric | baseline | after |
|---|---|---|---|
| `prefix_sum` | precision | 0.750 | **0.783** |
| `prefix_sum` | recall | 0.679 | **0.887** |
| `prefix_sum` | F1 | 0.713 | **0.832** |
| `hash_map_lookup` | P/R/F1 | 0.957 / 0.379 / 0.543 | unchanged |
| `two_pointers_opposite` | P/R/F1 | 1.000 / 0.711 / 0.831 | unchanged |
| `binary_search_standard` | P/R/F1 | 1.0 / 1.0 / 1.0 | unchanged |
| all families | P/R/F1 | — | `array_traversal` remains **not measurable** (no V1 mapping) |

## 14. Every new false positive

**Exactly one verdict-level FP: `greedy_candy`** (LC 135).

```python
candies = [1] * n
for i in range(1, n):
    if ratings[i] > ratings[i-1]:
        candies[i] = candies[i-1] + 1
```

- predicted: `sequential_accumulation` (via `prefix_sum` → **FP**)
- actual labeled family: `prefix_sum` **negative** (confusable pair)
- structural facts responsible: `indexed_write` on `candies`; the assign-form
  predicate (`candies[i] = candies[i-1] + 1` — one self-read, `Add`)
- cause classification: **taxonomy boundary**, not a detector defect — see §18.

**Latent (verdict-neutral) evidence additions — disclosed:**

- `bfs_topological` (negative) acquired `sequential_accumulation` but stayed
  **TN** because its label is `hash_map_lookup`. The design predicted this case
  as the FP exposure; it is safe *under its own label* but is a real latent FP
  surface on any `prefix_sum`-labeled problem.
- 19 positives acquired `sequential_accumulation` with no verdict change
  (16 `hash_map_lookup`, 2 `array_traversal` `UNMAPPED_LABEL`, 1 other).

## 15. Every remaining FN family

| family | count | cause |
|---|---|---|
| append-form with non-`Add`/`Sub` operators (`ps_running_xor` `^`, `ps_running_prod_prefix` `*`, `ps_prefix_xor`) | 3 | predicate restricted to `Add`/`Sub` (as specified) — cumulative XOR/product out of scope |
| hash-labeled frequency counting (`freq[x]=freq.get(x,0)+1` family) | 16 | bridge requires `hash_lookup`; assign form yields `sequential_accumulation` |
| tuple-unpack dict construction | 2 | explicitly out of scope |
| pre-existing prefix_sum FNs | 3 | benchmark label artifact (unchanged) |
| `two_pointers_opposite` FNs | 11 | out of scope (for-loop two-pointers deferred) |

No previously-passing case became an FN.

## 16. Strategy changes

**Zero.** No case changed primary strategy or gained a new strategy across
either corpus.

## 17. False confirmations / contradictions

- 46-record corpus: **0** new false confirmations, **0** false contradictions.
- 301-case corpus: **0** new false confirmations, **0** false contradictions;
  one new *false positive* (`greedy_candy`, §14), which is a false positive on a
  negative case, not a false confirmation of a positive.

## 18. Does it generalize across names and forms?

**Yes, with one honest boundary.**

- Fires on 11 independently-written prefix-sum implementations across 5 class
  and 3 function forms, including attribute-backed (`self.prefix`,
  `self.prefix_totals`), tuple-unpack loop variables, `[0]`-seeded lists, and
  non-obvious names (`pa`, `pb`, `p`, `out`, `result`, `prefix_totals`). No name
  is referenced.
- The container predicate never fires on the `UNMAPPED`/`TN` DP, sort, stack,
  monotone-stack, or two-pointer negatives that share the shape.

**The boundary (and why it is disclosed rather than patched):** the assign form
cannot distinguish two structurally identical programs held on opposite sides of
the benchmark:

```
prefix sum (positive)  ps_prefix_sum_manual:  out[i+1] = out[i] + arr[i]
greedy propagation     greedy_candy:          candies[i]  = candies[i-1] + 1
```

Both are a single `Subscript` self-read at a **displaced** index combined with an
external value via `+`. There is **no structural rule** at this abstraction level
that separates them without problem-identity or variable-name knowledge — the
only distinguishing property is semantic (one computes a range-sum table, the
other a constrained greedy pass). `dp[i] = dp[i-1] + dp[i-2]` is separated only
because it has **two** self-reads.

**Quantified trade-off if the assign form is restricted to same-key
self-reference (the design's canonical `freq[key] = freq.get(key,0)+1`):**

| option | prefix_sum TP | new FP |
|---|---|---|
| current (single self-read, any index) | +2 (`ps_prefix_sum_manual`, `ps_suffix_sum`) | +1 (`greedy_candy`) |
| same-key only | 0 | 0 |

Neither is "correct": the benchmark itself labels the identical shape both ways.

## 19. Is further engineering justified?

- The **append-form** half is a clean, reusable, name-free generalization:
  +9 TPs, 0 new FPs, 0 strategy changes, 0 corpus regressions. Keep.
- The **assign-form** half, as specified, cannot avoid the greedy/prefix-sum
  ambiguity. Any tightening is a benchmark-label-driven trade (2 TPs for 1 FP),
  not a fix of an underlying cause, so it is **not** recommended within this
  batch.
- Remaining recoverable, principled FN family: **operator coverage** for the
  append/assign forms (`*`, `^`, and other cumulative operators) — 3 corpus
  cases, zero FP exposure measured, but out of this batch's scope.
- No further engineering is required to make this batch safe; the one open
  decision is whether to keep or restrict the assign-form half.

---

## Frozen baseline vs this batch (summary)

| artifact | baseline | this batch |
|---|---|---|
| 46-record | 42 / 4 / 0 / 0 | **42 / 4 / 0 / 0 (identical)** |
| 301-case totals | TP 87 FP 13 FN 64 TN 78 | **TP 98 FP 14 FN 53 TN 77** |
| `prefix_sum` F1 | 0.713 | **0.832** |
| `hash_map_lookup` | unchanged | unchanged |
| shadow suite | 769 passed | **810 passed** |
| full repo | 1643 passed / 1 known legacy failure | **1684 passed / 1 known legacy failure** |
| new fact types | — | **0** |
| strategy changes / false confirmations / false contradictions | — | **0 / 0 / 0** |

**Stopped after this batch as instructed.** No tuple-unpack construction work, no
for-loop two-pointer strategy work, no GT-mapping edits, no 3225 drift fix, no
benchmark bookkeeping, no confidence-threshold or matcher changes.
