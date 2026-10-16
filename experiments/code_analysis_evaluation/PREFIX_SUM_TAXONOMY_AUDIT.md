# Taxonomy Audit — `prefix_sum` ↔ `sequential_accumulation`

**Type:** evaluation-only taxonomy audit. No code, test, DB, detector, technique,
strategy, or ground-truth change was made.

**Scope:** decide whether the V1 mapping
`prefix_sum → required = ["sequential_accumulation"]`
is semantically too broad for PathForge.

**Evidence base:** frozen code, the 46-record corpus, the 301-case disjoint corpus
(`results/vocab2_final_eval/disjoint301_eval_results.json`), and
`PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md`.

**Conclusion (bottom of report): A — keep the current mapping; the ambiguity is
inherent at the structural level.**

---

## 1. What `sequential_accumulation` structurally represents

The V1 doc (`§3.1 T1`) defines it as:

> A loop iterates over a sequence, and a running accumulator variable is updated
> each iteration by combining its prior value with the current element or an
> index-derived value.

and states explicitly:

> **What it DOES NOT imply:** Any specific algorithm (not prefix sum, not DP, not
> binary search) … **Confidence / specificity assessment:** Low specificity. This
> is a common idiom. By itself, it implies very little about the algorithm.

> **False-positive concern:** A simple `for x in arr: total += x` without any
> conditional would fire. *This is correct — it IS sequential accumulation. The
> technique does not claim to identify an algorithm; it claims to identify a
> computational pattern.*

In the current implementation it is produced by **three** paths:

| path | evidence | fires on |
|---|---|---|
| scalar (original) | `accumulator_update` (`x += e` / `x = x + e` / `x = f(x)`) + loop fact | any self-referential scalar update in a loop |
| relations | loop membership + accumulator join | same, relation-backed |
| container (extension) | `self_referential_updates[S]` (`indexed_write`/`append`) + loop membership | `S[i] = S[i-1] + e`, `S.append(S[-1] + e)` |

Measured on the 301 corpus, the **scalar path is the only source of FPs**; the
container path produced **0 FPs in the append form** and 1 in the assign form.

## 2. What `prefix_sum` requires semantically

There is no V1 `prefix_sum` **strategy**; `prefix_sum` is a *pattern label* whose
V1 representation is `required=["sequential_accumulation"]`,
`optional=["iterative_table_filling"]`.

Semantically, the label is used for algorithms whose core is a **cumulative
running value that is materialized per position or consumed for positional/range
reasoning**: prefix-array construction, range-sum queries, running min/max-as-prefix,
subarray-sum counting with a running total keyed into a map, difference arrays.

It excludes: **terminal scalar aggregates** (a counter that is only returned) and
**greedy / DP state** (feasibility counters, Kadane-style resets).

## 3. Classification of the current corpus examples

`prefix_sum` family = **82 cases** (53 positives, 29 negatives). Evidence feature
counts (measured directly from the frozen pipeline):

| | positives (53) | negatives (29) |
|---|---|---|
| has scalar `accumulator_update` | 36 | 13 |
| has container self-ref (`self_referential_updates`) | 16 | 1 |
| → of which `append` / `indexed_write` | 11 / 5 | 0 / 1 |
| detected as `sequential_accumulation` | 47 | 13 |
| detected as `iterative_table_filling` | 7 | 2 |

Evidence→verdict signatures:

- positives: `acc+sru`→TP 5, `sru`-only→TP 11, `acc`-only→TP 31, none→**FN 6**
- negatives: `acc`→**FP 12**, `acc`→TN 1, `acc+sru`→**FP 1**, none→TN 15

Grouped by structure:

| group | examples | label | pipeline |
|---|---|---|---|
| **A. Materialized prefix arrays** (running value written per position) | `ps_prefix_sum_manual` (`out[i+1]=out[i]+arr[i]`), `ps_range_query_build`, `ps_range_sum_*`, `ps_two_prefix_arrays`, `ps_while_prefix`, `ps_min_subarray_len`, `ps_cumulative_sum`, `ps_running_count`, `ps_running_max`, `ps_running_product`, `ps_2d_prefix`, `ps_prefix_xor` | positive | detected, except `*`/`^`/2-D forms (FN) |
| **B. Materialized running value via append** | `prefix.append(prefix[-1] + x)` across 9 independent implementations | positive | **clean: +9 TP, 0 FP** |
| **C. Scalar running value, consumed for ranged/positional reasoning** (no per-position container write) | `ps_find_pivot_index` (`left_sum += nums[i]`), `ps_min_prefix` (`running += nums[i]`) | positive | detected |
| **D. Scalar running value + hash map** | `ps_subarray_equals_k`, `ps_subarray_count_k`, `ps_subarray_divisible_k`, `ps_max_subarray_len`, `ps_zero_sum_subarrays`, `ps_contiguous_subarray_sum` | positive | detected |
| **E. Generic scalar aggregates** (terminal only) | `acc_counter_loop` (`count += 1`), `acc_nested_loop_sum`, `count_negative`, `factorial_loop`, `acc_string_concat`, `string_join_words`, `acc_string_build_loop` | **negative** | detected → **FP (7)** |
| **F. Greedy / DP scalar state** | `greedy_lemonade` (`five -= 1`), `greedy_assign_cookies` (`child += 1`), `greedy_jump_game2` (`jumps += 1`), `dp_max_subarray` (Kadane), `dp_max_profit_1` | **negative** | detected → **FP (5)** |
| **G. Greedy propagation into an array** | `greedy_candy` (`candies[i] = candies[i-1] + 1`) | **negative** | detected → **FP (1, the batch's new FP)** |
| **H. Other cumulative forms** | `ps_running_diff` (`result.append(x - prev)`), `ps_running_prod_prefix` (append `*`), `ps_prefix_xor` / `ps_running_xor` (append `^`), `ps_2d_prefix`, `ps_range_sum_2d` | positive | **FN (6)** |

Total label FPs: **13** = 12 pre-existing (E+F) + 1 new (G).

## 4. Can the distinction be made structurally?

**No — not for the category that matters.** This was verified at the fact layer,
not assumed.

### 4.1 The decisive counter-example pair

```
ps_min_prefix   (LABELLED POSITIVE)        acc_counter_loop (LABELLED NEGATIVE)
for i in range(1, len(nums)):              for val in arr:
    running += nums[i]                         if val > threshold:
    best = min(best, running)                      count += 1
```

Both produce **byte-identical evidence**:

```
accumulator_update{variable, operator='Add', syntax_form='augmented'}
for_loop_iteration
→ sequential_accumulation
```

Same for `ps_cumulative_sum` (`acc += x`, positive) vs `acc_counter_loop`
(`count += 1`, negative), and `ps_find_pivot_index` (`left_sum += nums[i]`,
positive) vs `count_negative` (`count += 1`, negative).

There is no fact, relation, or attribute that differs. The distinction between
"prefix" and "aggregate" is the **role of the result** (fed to a range/positional
computation vs merely returned), which the structural layer does not represent.

### 4.2 Every candidate separator fails

| candidate rule | positives lost | FPs removed | verdict |
|---|---|---|---|
| require per-position container materialization | ~12 (all of groups C, D) | 12 (E+F) | **not clean** — group D is legitimately `prefix_sum`; still leaves G |
| require unconditional (non-`if`) update | `ps_running_count`, `ps_prefix_ones`, `ps_prefix_count_*`, `ps_cumulative_bool` are conditional positives | `greedy_candy` | **fails** |
| require `Add`/`Sub` (exclude `Mult`) | `ps_running_product`, `ps_cumulative_product` | `factorial_loop` | **fails** |
| require plain additive self-ref (exclude `max`/`min`-mediated resets) | 0 | `dp_max_subarray`, `dp_max_profit_1`, `greedy_jump_game2` | removes 3/13; the other 9 (plain `count += 1`) remain |
| same-key self-reference only | 2 (`ps_prefix_sum_manual`, `ps_suffix_sum`) | 0 | removes neither group G nor E |

No single predicate — and no conjunction of them — reproduces the corpus's
positive/negative split. The benchmark's `prefix_sum` label partitions by
**algorithm identity**, while the pipeline partitions by **structural pattern**;
the two partitions are not a refinement of one another.

### 4.3 The one genuinely irreducible case

```
ps_prefix_sum_manual (POSITIVE)   out[i+1] = out[i] + arr[i]
greedy_candy         (NEGATIVE)   candies[i] = candies[i-1] + 1
```

Structurally identical (single displaced-index self-read, `+`, loop-carried).
`dp[i] = dp[i-1] + dp[i-2]` is separated only because it has **two** self-reads.
No problem-ID-free, name-free, constant-free rule distinguishes the first two.

## 5. Would a narrower concept (`prefix_accumulation` / `prefix_state_build`) be justified?

**No.** Two independent lines of evidence:

1. **This was already decided in V1.** `PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md`
   §4 (Rejected Technique Candidates) lists:

   > `prefix_sum_accumulation` — … this is really the `dp_bottom_up` strategy in
   > its simplest form. It is too specific — it implies a particular data structure
   > (prefix array). `sequential_accumulation` covers the general case.

2. **Measured trade-off of the only plausible narrower definition.**
   `prefix_state_build` = "running value materialized at each position
   (`indexed_write`/`append`)":

   - removes the 12 scalar FPs (groups E+F) ✔
   - loses ~12 legitimate positives (groups C+D — `ps_min_prefix`, `ps_find_pivot_index`,
     `ps_subarray_equals_k`, `ps_subarray_count_k`, …) ✘
   - still fires on `greedy_candy` (group G) ✘
   - is not "prefix vs not", it is "materialized vs scalar" — a data-structure
     distinction, which is exactly the reason V1 rejected it

   Net effect: precision up, recall down, one FP unchanged, plus a new technique
   and a new mapping — i.e. taxonomy expansion with negative return.

## 6. Should the current V1 mapping remain unchanged?

**Yes.** `prefix_sum → required=["sequential_accumulation"]` is semantically
**lossy but correctly scoped for its purpose**: `sequential_accumulation` is
documented as a low-specificity *pattern*, and the mapping exists to give
`prefix_sum`-labelled problems structural coverage, not to certify that a
submission *is* a prefix sum. The breadth is the documented, intended behaviour.

Bounded residual risk (stated honestly): for a problem whose GT includes
`prefix_sum`, `required=["sequential_accumulation"]` is a weak bar — a submission
that merely contains a loop accumulator satisfies it. In the 46-record corpus
this produced **0 false confirmations** (LC 3236/209/4284 all behave as designed).

### One documentation inconsistency to reconcile (not a reason to narrow)

V1 doc §3.1 states as a `sequential_accumulation` exclusion:

> If the accumulator update involves a subscript lookback on an array
> (e.g., `prefix[i] = prefix[i-1] + nums[i]`), this is `iterative_table_filling`
> … not this technique.

The current container path emits **both** `sequential_accumulation` and
`iterative_table_filling` for that shape (`ps_prefix_sum_manual` shows
`['iterative_table_filling','sequential_accumulation']`). Honouring the doc
strictly would **reduce** coverage (it would re-break exactly the assign-form
positives the extension recovered), so the mapping is not what should change —
either the doc's exclusion note or the intent should be reconciled. Recorded as
an open documentation item, not a defect.

## 7. What evidence would be required before changing it

A mapping change should require **all** of:

1. **Real (non-synthetic) evidence of harm** — false confirmations in the
   production submission stream (problems whose GT includes `prefix_sum` and
   submissions confirmed on an aggregate), not benchmark negatives. The 301
   corpus cannot supply this: its negatives are constructed confusable pairs and
   their only "problem" is the shared structural pattern.
2. **A structural predicate that separates a labelled positive from a labelled
   negative with multiple independent examples and zero counterexamples in *both*
   corpora.** §4.1–4.3 show none exists today; a future predicate would have to
   represent the *role* of the running value (positional/range consumption vs
   terminal/control), which is a value-role/def-use capability the layer lacks.
3. **A curated ground-truth review** — not benchmark labels — establishing that
   the narrower concept's lost positives (groups C+D) are not genuinely
   prefix-sum implementations PathForge must accept.
4. **Bounded FP benefit**: at least as many true FPs removed as positives lost
   (the materialization rule fails this 12↔12 test, and leaves `greedy_candy`).

Until 1–4 hold, changing the mapping would be tuning to a synthetic label.

---

## Recommendation

### A. Keep the current mapping; the ambiguity is inherent at the structural level.

Backing evidence:

- **13 FPs, 0 from the append form.** The clean part of the extension
  (`prefix.append(prefix[-1] + x)`, +9 TP, 0 FP) is settled.
- **All 13 FPs are fired by the low-specificity scalar `accumulator_update`
  path** (12) or by the single irreducible displaced-index container self-ref (1).
- **A labelled positive and a labelled negative produce byte-identical structural
  evidence** (`running += nums[i]` vs `count += 1`), so no structural rule can
  separate the families without losing legitimate coverage.
- **The narrower concept was explicitly evaluated and rejected in V1**, and its
  measured cost is −12 TP for −12 FP with one FP unchanged.

**Not B or C**, because the audit found no reusable structural distinction with
multiple independent examples and bounded FP risk. If production data later
shows real false confirmations on `prefix_sum`-labelled problems, the correct
next step would then be **B** — a dedicated value-role/taxonomy experiment
(does the running value feed a positional/range computation?) — before any
coding. That precondition is not met by the available evidence.

**Explicitly not recommended now:** narrowing the mapping, adding a
`prefix_accumulation`/`prefix_state_build` technique, restricting the assign form
to same-key self-reference, or adding operator/index special cases.
