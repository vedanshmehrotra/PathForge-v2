# Vocabulary Layer 2 — Step 4: Sorting-Form `candidate_selection`

**Scope honored:** sorting-form `candidate_selection` only (second structural form on the existing T12 technique). No greedy strategy, no problem-ID logic, no name allowlists, no manual ground-truth edits, no changes to `hash_lookup` or `frequency_counting` semantics, loop-form semantics untouched, legacy matcher untouched.

---

## 1. Files changed

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | 2 new name-free facts: `sorting_operation`, `extremum_access`; `visit_Call` hook for the sort operation, `visit_Subscript` hook for bounded reads |
| `pathforge/ast_analysis/shadow/techniques.py` | `_detect_candidate_selection` split into `_candidate_selection_loop_form` (byte-identical) + `_candidate_selection_sort_form` (new fallback) |
| `pathforge/services/ground_truth_builder.py` | `greedy_local` mapping `note` updated to describe both forms (mapping `required`/`optional`/`excluded` **unchanged**) |
| `pathforge/ast_analysis/shadow/tests/test_vocab2_sort_form_candidate_selection.py` | **new, 38 tests** |

No change to `VALID_TECHNIQUES` — `candidate_selection` was already registered in Step 1, so no vocabulary-count tripwire moved. No new technique, no new strategy, no concept-hierarchy change.

---

## 2. Exact semantics of `sorting_operation`

A structural **sort operation**, dispatched through the M1 normalized statement-operation layer (`Expr` / `Assign` / `AnnAssign` / `AugAssign`), so the same operation is recognized regardless of statement form.

| form | recorded `structure` | `method` |
|---|---|---|
| `x.sort(...)` (in place) | `x` — the receiver | `"sort"` |
| `y = sorted(x, ...)` (functional) | `y` — the target holding the sorted sequence | `"sorted"` |

Attributes: `structure`, `method`, `reverse` (structural: `reverse=True` keyword). `reverse` is **recorded but never required**. A bare `sorted(x)` expression statement records **nothing** — no variable names the sorted result. Name-free: no identifier, no sort argument, and no problem identity participates.

## 3. Exact sort-form predicate

Requires **both**, joined by sorted-sequence identity:

1. a `sorting_operation` fact with a `structure`, **and**
2. an `extremum_access` fact on the **same** `structure`.

`extremum_access` = a **load** subscript of a sequence at a **bounded index**:
- `constant` (`arr[0]`, `arr[-1]`, `arr[k]` — a bounded/order-statistic position), or
- `length_offset` (`arr[len(arr) - 1]` — requires the `len(...)` argument to be the *same* structure, so the relationship is structural, not a name match).

A **variable** index (`arr[i]`, `arr[mid]`, `arr[left]`) is deliberately **not recorded** — that is traversal / pointer movement, and is the discriminator against two-pointer and binary-search shapes. Writes (`arr[0] = x`) and annotations are never reads and are never recorded.

The loop form is evaluated **first** and is unchanged; the sort form is a fallback, so every previously supported input keeps its exact output.

## 4. Was a new fact type necessary?

**Yes — two**, and both are genuinely absent before this step:
- nothing in the fact layer represented `.sort()` / `sorted(...)` at all;
- nothing represented a bounded/endpoint read. `subscript_index_access` records *index variables* (the write/index side), `index_lookback` records `arr[i±k]` with a **variable** base, and `cache_lookup`/`visited_tracking` are name-gated. A sorted-sequence identity join needs an explicit sorted-structure fact and an explicit bounded-read fact; deriving either from existing facts would have required name heuristics, which are prohibited.

---

## 5. Tests added

**38 new tests** in `test_vocab2_sort_form_candidate_selection.py`.

Positives (8 families + 5 invariants): `.sort()` + smallest, `.sort()` + largest, `sorted()` + extremum, `sorted(..., reverse=True)` + extremum, non-obvious variable names, length-offset functional form, sort under a conditional guard, reverse-argument equivalence; sort form without relations (fact fallback); supporting-fact shape (sort + read lead the evidence); loop-form precedence when both forms are present.

Negatives, split into two precise groups:
- **No T12 form fires** (8): sort-only, `return sorted(a)` as output, sort + ordinary traversal, sort + unrelated subscript on a *different* structure, two-pointer-after-sort, heap `nlargest` top-k, monotonic stack, mapping-build-only.
- **Sort form must stay silent** (2): binary-search-after-sort, sliding-window-with-running-max. These assert `_candidate_selection_sort_form(...) is None` and that any T12 evidence present carries `conditional_index_update` and **not** `sorting_operation` — proving the residual detection belongs to the pre-existing Step 1 loop form, not to Step 4.

Fact-level invariants (5): bare `sorted()` records nothing; `structure`/`method` recorded correctly for both forms; `reverse` recorded without being required; variable index and write forms produce no `extremum_access`; `index_form` values.

Relation contract (3): relations cannot fabricate the sort form (full relations bundle present, no sort fact → no detection); relation presence does not change sort-form output; the sort form is relation-free by construction (`sort_form([]) is None`).

Loop-form regression (3): still fires; accumulator fence and index-participation fence intact; evidence shape unchanged (`conditional_index_update`, no `sorting_operation`).

GT/vocabulary integration (4): `candidate_selection` registered and still a technique; no `greedy` strategy introduced; `greedy_local` mapping unchanged; every mapping reference is a valid V1 concept; `greedy_local` has no missing vocabulary.

---

## 6–7. Suite results

| suite | result |
|---|---|
| Step 4 tests | **38 passed** |
| full shadow suite | **769 passed** (731 + 38, originals green) |
| full repository suite | **1643 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` failure (`src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`) |

Zero movement in the baseline failure. No test was weakened.

---

## 8–9. 46-record before → after (fingerprint-matched, live DB groups)

| | BEFORE (Step 3) | AFTER (Step 4) |
|---|---|---|
| CONFIRMED | 40 | **42** |
| UNRESOLVED | 6 | **4** |
| CONTRADICTED | 0 | **0** |
| ERROR | 0 | **0** |

**Verdict changes — exactly 2, both predicted:**

| record | problem | verdict | expected | evidence that caused it |
|---|---|---|---|---|
| db-18 | 628 | UNRESOLVED → CONFIRMED | `greedy_local` | `nums.sort()` + `nums[0]`/`nums[len(nums)-1]` → `sorting_operation` + `extremum_access` paired on `nums` → `candidate_selection` |
| db-36 | 1574 | UNRESOLVED → CONFIRMED | `greedy_local` | `nums.sort()` + `nums[len(nums)-1]`/`nums[len(nums)-2]` → same paired evidence → `candidate_selection` |

db-18 satisfies the `greedy_local` group at 0.800 exactly as the loop-form records do. No group was forced and no threshold was touched.

**New facts, by record:**

- `sorting_operation` (+4): db-18, db-36 (both fire), **db-20, db-234** (sort present but no bounded read on the same structure → no detection, verdicts unchanged).
- `extremum_access` (+9): db-18, db-36 (fire), and **db-49, db-51, db-193, db-194, db-241, db-246, db-254** (unpaired — `stack[-1]` monotonic peeks, `dp[0]`, `grid[0]`, `nums[0]` non-sorted endpoint reads). Zero technique effect; all verdicts unchanged.

Precision is therefore structural: 9 records acquired bounded-read facts, 4 acquired sort facts, and **only the 2 where the two facts share a structure fired**.

## 10. Evidence-only changes

**None.** Not a single record gained or lost a technique other than the 2 flips. This is the strictest possible outcome for this batch.

## 11–14. Change classes

| class | count |
|---|---|
| strategy changes | **0** |
| false confirmations | **0** |
| false contradictions | **0** |
| unrelated changes | **0** |

Zero-change batteries all held: db-64 (UNRESOLVED, set semantics — truthful refusal), db-238/db-240 (recursion fence), db-193 (monotonic stack), db-35/db-230 (map builders), db-49/db-51/db-194 (alternative-group recovery from the GT repair), db-11/db-33/db-39 (hash flips), db-41/db-192 (frequency flips), db-138/db-189/db-191 (frequency evidence-only). No sliding-window, two-pointer, binary-search, DP, or monotonic-stack submission acquired frequency or candidate evidence.

**GT consistency checks:** no stored group became malformed, no alternative group was collapsed, no single-family/conjunctive group changed. The only reported representation drift (`problem 3225`, `hash_map_frequency` not covered by any group) is **inherited** — it appears identically in the Step 3 report, and Step 4 changed no mapping, no derivation, and no loader.

## 15. Does the sort-form generalize beyond db-18/db-36?

**Yes, structurally.** The predicate is keyed on sorted-*structure identity* and bounded-*index form*, not on any identifier or literal:
- it fires on 8 independently written code families (in-place and functional sorts, `reverse=True`, annotated/non-obvious names, conditionally-executed sorts, length-offset and constant endpoints);
- db-36 uses **only** the `length_offset` form while db-18 uses both, and both fire — so the rule is not tuned to one index literal;
- across all 46 real submissions it produced exactly 2 detections while 7 unrelated records gained bounded-read facts with zero effect, which is what a well-fenced structural predicate looks like.

**Disclosed boundary (honest, not a defect claim):** any **constant**-index read of a sorted sequence counts as bounded selection — so `arr.sort()` then `arr[k]` (k-th smallest, an order statistic) also fires, not only `[0]`/`[-1]`. This is the generalization the design asked for ("do not rely on literals 0/-1 alone"), and reads at *variable* indices — the shapes that actually appear in two-pointer/binary-search code — remain fenced out.

**Disclosed pre-existing behavior (not caused by Step 4):** two shapes in the negative battery — binary-search-after-sort and sliding-window-with-running-max — still produce `candidate_selection` through the **Step 1 loop form**: `hi = mid - 1` under a branch and `best = window` under `if window > best` are structurally conditional scalar rebindings of non-index, non-accumulator variables. The sort form is provably silent on both (`_candidate_selection_sort_form(...) is None`), these shapes do not occur in the 46-record corpus, and tightening them would mean modifying loop-form semantics — explicitly out of scope for this batch. Flagged for a future batch rather than patched here.

---

## Verdict

Step 4 lands with the exact designed blast radius: **2 flips, 0 losses, 0 evidence-only changes, 0 strategy changes, 0 false confirmations/contradictions**, suites green except the known legacy failure. The sort form is a genuinely reusable structural predicate with two new name-free facts, and the loop form is byte-identical. **No further vocabulary work is needed for this layer** — remaining UNRESOLVED (db-64 set semantics; db-251/db-253/db-254 non-vocabulary causes; db-18/db-36 now resolved) are not vocabulary gaps.

Stopped as instructed. No additional vocabulary implemented.
