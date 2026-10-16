# Ground-Truth Architecture POC — Report

**Scope implemented:** Phases 1–5 of `GROUND_TRUTH_ARCHITECTURE_SPEC.md`, JSON-first.
**Not implemented (by instruction):** DB schema/migration, GT promotion,
active-version loading, scheduled refresh, production runtime changes, LLM
merge/split proposals, automatic approval.

**Boundaries honoured:** production runtime unchanged; existing GT rows untouched;
matcher/detectors/techniques/strategies/vocabulary unchanged; no DB writes; no
network; no LLM; the frozen shadow pipeline is imported and used **read-only**.

**Test result:** full repository suite **1702 passed / 1 failed** — the failure is
the known pre-existing legacy
`src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`
(present at baseline; 1702 = 1684 baseline + 18 new POC tests). POC tests: **18 passed**.

---

## 1. Corpus composition

| | value |
|---|---|
| problems | **8** (`1, 21, 125, 209, 242, 560, 704, 3236`) |
| reference solutions | **40** (5 per problem) |
| ingestion issues | **0** |
| sources | `pathforge_db` **10**, `authored` **30** |
| language | python (40) |

Implemented artifacts (all under `experiments/code_analysis_evaluation/gt_poc/`):

`reference_solutions.json`, `normalized_solutions.json`, `families.json`,
`review_sheet.json`, `review_sheet.md`, `label_comparison.json`,
`validation.json`, `run_manifest.json`, plus `run_manifest.json` content
digests. Modules: `ingest.py`, `normalize.py`, `group.py`, `label.py`,
`validate.py`, `core.py`, `run_shadow.py`, `run_poc.py`, `problem_metadata.py`,
`corpus_authored.py`, `corpus_db_snapshot.json`, `tests/test_gt_poc.py`.

**Mechanical execution works**: ingest → normalize → dedup → group → prepare
independent labels → hold out → validate → auditable JSON. Repeated execution is
byte-identical; the stored `code_text` is never mutated; no LLM/network/DB call
occurs (enforced by a test that patches `call_llm` and `get_connection` to raise).

## 2. Source distribution

| source_type | count | provenance kind |
|---|---|---|
| `pathforge_db` | 10 | `pathforge_submission` (read-only snapshot of `submissions`, `judge_verdict`/`verdict_type`/`submitted_at` recorded; licence `user-owned`) |
| `authored` | 30 | `authored_reference` (project author; licence `project`) |
| `user_export` | 0 | not used in this run |
| `licensed_repo` | 0 | not used (spec O9 OPEN) |

Every solution carries `problem_id`, `source_type`, `source_ref`, `language`,
`code_text`, `raw_hash`, and a non-empty `provenance` object. No scraping; no
third-party code; no editorial text copied.

## 3. Dedup results

| level | meaning | count |
|---|---|---|
| **D1** exact duplicate | identical `raw_hash` | **0** |
| **D2** syntax variant | identical `norm_hash`, different `raw_hash` | **0** |
| **D3** same family, different implementation | same signature class, skeleton distance < τ | **9** |
| **D4** distinct-family canonical | establishes a family | **31** |

The corpus was curated duplicate-free, so **D1/D2 were never exercised** — the
ladder's duplicate and syntax-variant branches are *untested* by this run
(finding F7 below; the mechanism itself is unit-tested with a synthetic
duplicate).

## 4. Families produced per problem

**31 families for 40 solutions → 23 singletons.** (A problem was expected to have
1–3 families.)

| problem | solutions | families | singleton families |
|---|---|---|---|
| 1 Two Sum | 5 | 4 | 3 |
| 21 Merge Two Sorted Lists | 5 | **5** | **5** |
| 125 Valid Palindrome | 5 | 4 | 3 |
| 209 Minimum Size Subarray Sum | 5 | 3 | 1 |
| 242 Valid Anagram | 5 | 4 | 3 |
| 560 Subarray Sum Equals K | 5 | **5** | **5** |
| 704 Binary Search | 5 | 4 | 3 |
| 3236 Sequential Prefix Sum | 5→(3 distinct) | 2 | 0 |

Family size histogram: `{1: 23, 2: 7, 3: 1}`.

Concrete over-splitting examples:

- **LC 1**: three solutions all detected with the identical signature `hash_lookup`
  (`S0001`, `S0002`, `S0005`) ended up in **two** families — the split came
  entirely from skeleton distance, not from a structural concept difference.
- **LC 21 / LC 560**: 5 solutions → 5 families. In LC 21 the families are
  `{forward_pointer_advance, linked_list_traversal}`, `{linked_list_traversal,
  sequential_accumulation}`, `{…loop_state_tracking…}`, `{recursive_branching}`,
  `{candidate_selection, …}` — the *merge* idiom is one family split five ways by
  incidental generic-technique differences.

Two independent causes (both spec-revisable, see §10):

1. **Primary partition is exact-equality on the full concept set** — one extra
   low-specificity technique (`loop_state_tracking`, `candidate_selection`)
   splits a family.
2. **Skeleton refinement splits within a signature class** — token-level edit
   distance ≥ τ over ~100-token skeletons is easily reached by ordinary
   implementation differences (one-pass vs two-pass over a dict).

## 5. Provisional skeleton threshold

- Metric: normalized token-level Levenshtein distance over skeleton tokens.
- **τ = `0.35`**, a single documented constant, identical for every problem
  (`test_grouping_is_deterministic_and_threshold_not_per_problem` asserts this).
- **PROVISIONAL, not calibrated** (spec OPEN decision O1). This run is evidence
  *against* the current choice: at τ = 0.35 the refinement is over-splitting
  (§4), so the POC does not support freezing this value.

Skeleton definition (PROVISIONAL): user identifiers abstracted to `Name`, literal
values abstracted to `Const`, control-flow/operator/call structure preserved, and
**API names kept** (`Call<append>` vs `Call<pop>`) so container operations remain
distinguishable. Excluding API names was rejected as it would collapse genuinely
different operations.

## 6. Label-source status

| | count |
|---|---|
| families total | 31 |
| `PENDING_REVIEW` (has a curated label) | **29** |
| `NO_INDEPENDENT_LABEL` | **2** (both LC 3236) |
| auto-approved | **0** |

- Label authority = curated `problems.pattern` (live DB snapshot) mapped through
  the frozen `PATTERN_TO_V1_MAPPING` (spec §9 precedence 1). The analyzer's
  detections are **not** in the reviewer-facing artifact (asserted by test) and
  are written only to `label_comparison.json`.
- **LC 3236's curated pattern list is empty in the live database** — preserved,
  not filled in. Its 2 families therefore have no independent label and derive no
  groups (spec §12 refusal).

Two label defects surfaced:

1. **Granularity (F4).** Curated metadata is *problem-level*, so every family of a
   problem receives the same proposal (`family_specific: false`). For LC 1 that
   proposes `hash_lookup` for the brute-force family as well. **The POC cannot
   label families from a problem-level source**; a per-family human assignment
   step is required.
2. **Label ↔ analyzer vocabulary divergence (F5).** 12 of 29 pending families
   produced **no group** because the analyzer's member-concepts share *no* element
   with the editorial label's required concepts, e.g.:
   - LC 21 (label `two_pointers_same` → `forward_pointer_advance`) but the
     iterative merge families detect `linked_list_traversal` /
     `sequential_accumulation`.
   - LC 704 recursive binary search → `recursive_branching` vs label
     `binary_search`.
   - LC 242 `Counter(s)==Counter(t)` and `sorted()==sorted()` → **no concepts at
     all**.
   This is not a grouping bug; it is the editorial label's V1 mapping disagreeing
   with what the frozen vocabulary can see.

## 7. Validation metrics

Split: **derivation 32 / held-out 8**, per-family stratified, overlap **0**.
(Held-out is only 8 because 23 singleton families send their single member to the
derivation side — see F9.)

| metric | value | threshold | status |
|---|---|---|---|
| `group_satisfiability` | **1.0** (17/17) | = 1.00 | pass |
| `family_coverage` | **1.0** (5/5 in covered families) | ≥ 0.85 | pass (small scope) |
| `positive_confirm_rate` | 0.625 (5/8 held-out) | — | informational |
| `unresolved_rate` | 0.375 (3/8) | — | informational |
| `label_agreement` | **0.8529** (17 families) | ≥ 0.90 | **FAIL** |
| `discrimination_FP_disjoint` | **0.1228** (21/171) | ≤ 0.05 | **FAIL** |
| `discrimination_FP_raw` | 0.1702 (32/188) | — | informational |
| `contradicted` | 0 | — | pass |

Held-out outcomes: **5 CONFIRMED, 3 UNRESOLVED, 0 CONTRADICTED**.
The 3 UNRESOLVED are exactly the held-out members of unlabelable families
(LC 242 `Counter`/`sorted`, and both LC 3236 families).

`label_agreement` fails on **5 families** where the analyzer's concept
intersection covers only half the editorial label — e.g. LC 209
`label_required=[sequential_accumulation, sliding_window]` but the prefix-sum /
nested-loop / brute families only yield `{sequential_accumulation}`; LC 560
`[frequency_counting, sequential_accumulation]` vs `{sequential_accumulation}`.
Those families' derived groups then require **only the generic concept**, which
is precisely what drives the discrimination failure.

## 8. Negative-control results

Controls = canonical member of each family of every *other* problem; each derived
group is tested against all of them.

| variant | tests | wrongly confirmed | rate |
|---|---|---|---|
| raw (all cross-problem controls) | 188 | 32 | **0.1702** |
| disjoint curated patterns only | 171 | 21 | **0.1228** |

Hits cluster in groups whose `required` narrowed to a single generic concept:

```
tested LC 560  lc560_fam1_g0  (required=[sequential_accumulation])   8 control hits
tested LC 209  lc209_fam2_g0  (required=[sequential_accumulation])   6 control hits
tested LC 21   lc21_fam1_g0   (required=[forward_pointer_advance])   4 control hits
tested LC 1    lc1_fam1_g0    (required=[hash_lookup])               2 control hits
tested LC 125  lc125_fam1_g0  (required=[two_pointers_opposite])     1 control hit
```

**Interpretation (PROVISIONAL):** the disjoint variant is more meaningful, but the
raw-vs-disjoint gap (17.0% → 12.3%) shows the *control-set definition* materially
changes the measurement — evidence for OPEN decision O3 (negative-control
strength/definition). Same-family solvers in different problems (e.g. LC 560 and
LC 242 both have dict-family solutions) legitimately confirm, so raw controls
overstate the error rate; the disjoint variant is the fairer reading and still
fails.

## 9. Every failed validation criterion

1. **`discrimination_FP_disjoint` = 0.1228, required ≤ 0.05.** Root cause:
   derived groups are too broad. `required` is the intersection of the family's
   detected concepts *narrowed by the editorial label*; when that intersection is
   a single low-specificity technique, the group accepts unrelated problems'
   solutions. Contributing causes: over-splitting (singleton families produce
   narrow, generic groups) and the label-vocabulary divergence (§6).
2. **`label_agreement` = 0.8529, required ≥ 0.90.** Root cause: 5 families whose
   analyzer-visible concepts cover only part of the editorial label's required
   set. This is a vocabulary/mapping gap, not a grouping defect: no grouping
   change can raise it while `derived_required ⊆ label_required`.

Rules were **not** adjusted on failure; both criteria are reported as observed.

## 10. Open decisions discovered during the POC

All are **PROVISIONAL**; none is silently resolved.

| # | decision | evidence from this POC |
|---|---|---|
| **F1** | **Primary partition key is too fine (over-splitting).** | 31 families / 40 solutions, 23 singletons; LC 21 and LC 560 split 5/5. Spec §8 step 1 needs a *reduced* concept set (drop low-specificity techniques) or a similarity agglomeration, not exact equality. |
| **F2** | **Skeleton refinement splits within a signature class.** | LC 1: three `hash_lookup` solutions split into 2 families purely by skeleton distance. τ and/or the distance metric must be re-derived, or the refinement demoted to a tie-break. |
| **F3** | **`derived_required = concepts ∩ label.required` makes `label_agreement` structurally capped at 1 and can produce over-broad single-concept groups.** | `label_agreement` is measured against a construction that partly defines it; and single-concept groups cause the discrimination failure. A **minimum-specificity rule** (or a "generic technique cannot be the sole requirement" rule) is needed. |
| **F4** | **Label-source precedence 1 (problem-level curated patterns) cannot label families.** | 12/29 families got no group; every family of a problem receives the same proposal. Spec §9 needs an explicit per-family human assignment step and the review artifact must support it. |
| **F5** | **Editorial label's V1 mapping disagrees with the analyzer vocabulary.** | LC 21, LC 704 (recursive BS), LC 242 — no shared concept. `label_agreement ≥ 0.90` is unreachable for these families regardless of grouping quality. |
| **F6** | **"No evidence" solutions are common, not an edge case.** | **6/40 (15%)** produce zero techniques/strategies (`bisect` use, `Counter(a)==Counter(b)`, `sorted()==sorted()`, brute force). Spec §12's refusal path needs to be a first-class, quantified outcome. |
| **F7** | **D1/D2 untested.** | 0 D1 / 0 D2 because the corpus is duplicate-free. The ingestion/duplicate mechanism is unit-tested synthetically, but spec §6's D1/D2 behaviour needs a corpus that genuinely contains duplicates. |
| **F8** | **Negative-control definition (O3) materially changes the metric.** | raw 17.0% vs disjoint 12.3%. Spec must define the control-selection rule, not leave it to the harness. |
| **F9** | **The 60/40 split degenerates under over-splitting.** | 23 singletons → held-out falls to 8/40. Split should be defined per *problem* (or grouping fixed first). |
| **F10** | **Tiny held-out set ⇒ weak evidence.** | `family_coverage = 1.0` is measured over just 5 held-out solutions in covered families. Not sufficient to freeze anything. |
| **F11** | **Corpus saturation unknown (O2).** | 5/problem was enough to reveal families but not to claim exhaustiveness; LC 21/560 suggest these families need more members. |
| **F12** | Reviewer blinding (O10) not exercised. | The artifact *hides* analyzer output (verified), but no human review occurred, so blinding is untested end-to-end. |

## 11. Is the architecture ready for Phase 6?

**No — not yet.** The pipeline is mechanically complete, deterministic, and
auditable, and there are genuine positives: **0 ingestion issues**, **0 CONTRADICTED**,
**`group_satisfiability` 1.0**, **no code mutation**, **no LLM/DB/network**, and a
reviewer artifact that provably withholds analyzer detections and auto-approval.

But the POC **fails two of its four acceptance criteria** and, more importantly,
shows that the *grouping layer's design* (not just its parameters) produces
over-split families, which in turn produces over-broad single-concept groups and
the discrimination failure. Proceeding to DB/versioning work would freeze a
defective grouping contract into schema.

**Required before Phase 6 (in order):**
1. Revise spec §8: primary partition key (F1) and the role/metric of skeleton
   refinement (F2).
2. Revise spec §9: per-family label assignment (F4) and a minimum-specificity
   rule for `required` (F3); define how label↔vocabulary divergence (F5) is
   handled.
3. Define the negative-control selection rule (F8) and re-measure.
4. Re-run this POC with a duplicate-containing corpus (F7) and a larger held-out
   set (F9/F10).

---

## Conclusion

### B. POC exposes specific design flaw(s); revise the specification before coding further.

The mechanical pipeline is validated, but two acceptance criteria fail
(`discrimination_FP_disjoint` 0.1228 > 0.05; `label_agreement` 0.8529 < 0.90) and
the failures trace to spec-level design issues — over-fine primary partitioning
(F1/F2), a label model that is problem-level rather than family-level (F4) and
structurally cannot cover the editorial vocabulary (F3/F5), and an undefined
negative-control rule (F8) — not to tunable parameters. Conclusion A ("proceed to
Phase 6") is not supported; conclusion C ("collect more data") is insufficient
because the flaws are reproducible with the existing 40 solutions.

**Nothing was changed in the production system, existing GT, the matcher, the
detectors/techniques/strategies/vocabulary, or the database.**
