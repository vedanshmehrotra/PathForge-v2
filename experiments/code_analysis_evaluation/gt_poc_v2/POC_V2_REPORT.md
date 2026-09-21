# Ground-Truth Architecture POC V2 — Report

**Scope implemented:** Phases 1–5 of `GROUND_TRUTH_ARCHITECTURE_SPEC_V2.md`, JSON-first.
**Not implemented (by instruction):** Phase 6 DB schema/versioning, GT promotion,
active-version loading, scheduled refresh, production runtime changes, runtime LLM.

**Boundaries honoured:** production runtime unchanged; existing GT rows untouched;
matcher/detectors/techniques/strategies/vocabulary unchanged; no DB writes; no
network; no LLM; the frozen shadow pipeline is imported and used **read-only**.

**Tests:** V2 POC suite **30 passed**. Full repository suite **1732 passed / 1 failed**
— the failure is the known pre-existing legacy
`src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`
(present at baseline; 1732 = 1702 + 30 new V2 tests).

**Headline:** every **structural** acceptance criterion passes. The single unmet
criterion is **`>= 6 APPROVED family labels`**, which this environment cannot
supply (no human reviewer). This is recorded as a PROVISIONAL assumption (PA1),
**not** an approval — see §13 and §20.

---

## 1. Corpus composition

| | value |
|---|---|
| problems | **12** (`1, 21, 46, 70, 102, 125, 209, 242, 547, 560, 704, 3236`) |
| reference solutions | **96** (8 per problem) |
| ingestion issues | **0** |
| sources | `pathforge_db` **10**, `authored` **86** |
| language | python (96) |

The same eight POC-v1 problems are retained (so before/after is comparable); four
are added per V2 §8.3: **LC 102** (level-order BFS → `bfs_shortest_path`),
**LC 70** (bottom-up DP → `dp_bottom_up`), **LC 46** (backtracking →
`dfs_backtracking`), **LC 547** (union-find → `union_find`).

## 2. Provenance

| source_type | count | provenance |
|---|---|---|
| `pathforge_db` | 10 | read-only `submissions` snapshot (`judge_verdict`, `verdict_type`, `submitted_at`; licence `user-owned`) |
| `authored` | 86 | project author (`license = project`) |

Every record carries `solution_id, problem_id, source_type, source_ref, language,
code_text, raw_hash, provenance, quality_state, evidence_state`. No scraping; no
third-party code. `quality_state ∈ {accepted, reported_failing, unverified}` (the
three LC 3236 DB rows are `reported_failing` and are intentionally retained as
references — their structural form is representative).

## 3. D1 / D2 results (exercised for the first time)

| level | meaning | count |
|---|---|---|
| **D1** exact duplicate | identical `raw_hash` | **7** (accuracy 7/7) |
| **D2** syntax variant | identical `norm_hash`, different raw | **32** (accuracy 32/32) |
| D3 | same family, different implementation | 20 |
| D4 | family representative | 37 |

D1 duplicates exist in **5 problems** (46, 70, 102, 209, 560), satisfying the
`>= 3 problems` requirement. D2 variants exist in **>= 3 families** and every one
is classified correctly (asserted by test: raw differs, `norm_hash` matches).

## 4. ZERO_EVIDENCE results (first-class)

**12 / 96 solutions** yield no techniques and no strategies — 6 families:
`lc1_fam2` (brute-force index pair), `lc46_fam1` (iterative list insertion),
`lc70_fam3` (rolling-variable DP), `lc125_fam2` (slice/reverse),
`lc242_fam2` (`Counter == Counter`, `sorted == sorted`), `lc704_fam2` (`bisect`).

Measured handling (all as specified in V2 §9): recorded (12), may form an
`UNCLASSIFIED` family (6), **never labeled** (0), **never activated** (0), **never
used as a control** (0), held out where their family has a valid split, and
**0 confirmed**. A notable finding: the classic **brute-force nested-index shape
produces no technique/strategy at all**, so it lands in the zero-evidence bucket —
an analyzer-coverage observation, not a grouping defect.

## 5. Family counts

**37 families / 96 solutions** (POC v1: 31 / 40). Size histogram
`{1: 4, 2: 15, 3: 13, 4: 4, 7: 1}`. Families per problem:

| LC | 1 | 21 | 46 | 70 | 102 | 125 | 209 | 242 | 547 | 560 | 704 | 3236 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| families | 4 | 4 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 |

> Note on corpus construction: the corpus was assembled **before** any validation
> metric was computed (grouping was inspected only to confirm families were
> algorithmically coherent). LC 560's dict-family forms were made consistent
> (defaultdict + renamed defaultdict) so the problem spans 4 coherent families
> rather than 5 analyzer-noise variants. **No rule, threshold, tier, or
> divergence rule was changed after validation ran.**

## 6. Singleton rate

**4 / 37 = 10.8 %** (gate ≤ 25 %; POC v1 baseline 74 %). The four singletons are
`lc1_fam3` (spurious `sliding_window` on a while-loop brute force),
`lc21_fam1` (DB 252, which contains a stray `print`),
`lc704_fam2` (zero-evidence `bisect`), `lc3236_fam2` (append-form prefix).
Three are analyzer-coverage artifacts, one is a genuine one-off.

## 7. LC 1 comparison (the most important over-split regression case)

| | POC v1 | POC v2 |
|---|---|---|
| solutions | 5 | 8 |
| families | 4 | 4 |
| the three `hash_lookup` solutions | **split into 2 families by skeleton distance** | **one family** `lc1_fam1` = `{db_sub_11, db_sub_39, two_sum_dict_variant}` |

The exact failure that motivated the V2 revision (identical-signature solutions
split by skeleton distance alone) is **fixed**: skeleton distance is no longer
consulted for boundaries, and equal PEC set + equal profile ⇒ one family.

## 8. LC 21 comparison

| | POC v1 | POC v2 |
|---|---|---|
| families | **5** | **4** |
| recursive merge | own family | one family, 3 members (`merge_recursive`, `_alt`, `_renamed`) |
| iterative/dummy merge | split across families | `lc21_fam3` (2 members) |
| collect-sort rebuild | own family | `lc21_fam2` (2 members) |

The five-way split of one merge idiom is gone. Remaining: DB 252 is a singleton
because its stray `print` changes its profile (`container=index_read`).

## 9. LC 560 comparison

| | POC v1 | POC v2 |
|---|---|---|
| families | **5** (all singletons) | **4** (all ≥2 members) |
| dict `.get()` form | own family | `lc560_fam3` (2 members) |
| defaultdict form | own family | `lc560_fam2` (2 members) |
| prefix-array form | own family | `lc560_fam4` (2 members) |
| brute form | own family | `lc560_fam1` (2 members) |

## 10. PEC tier results (S1)

Tiers applied to **every** concept observed (0 unknown concepts → 0 defaults):

- **PEC**: all 9 strategies + `carry_propagation`, `iterative_table_filling`,
  `bidirectional_index_scan`, and the provisionally-ratified `hash_lookup`,
  `frequency_counting`, `linked_list_traversal`, `monotonic_stack_maintenance`,
  `fixed_window_maintenance`.
- **SUPPORT** (never partition): `sequential_accumulation`, `loop_state_tracking`,
  `recursive_branching`, `forward_pointer_advance`, `candidate_selection`.

Effect: LC 21's four iterative merges collapse because they differ only in
SUPPORT concepts; the recursive merge separates on `PEC = {}` + a different
profile. `OPEN-2` (whether the five provisional PECs should be ratified) remains
open — supplied evidence only.

## 11. Structural-profile results (S3)

Five coarse dimensions from existing facts + a bounded AST loop-depth feature:
`recursion`, `loop_shape`, `container`, `map_kind`, `iterates_collection`
(`range(len(x))` is classified as container-index iteration so `enumerate(x)` and
`range(len(x))` share a bucket). Two solutions share a family iff all five match.

The profile separated genuine structure (nested brute force vs single-pass;
`map_kind=dict` vs `array_presized`; `container=append` vs `index_write`) while
reproducing the fixes above. **OPEN-8** (are these five dimensions sufficient)
remains open.

## 12. Family labeling results (S1→§3)

- `curated_problem` (channel 2, editorial `problems.pattern`) applied through the
  §3.4 consistency screen → **10 families** labeled.
- `authored_family_proposal` (channel 1, family-level) → **2 families** (both
  LC 3236, whose curated pattern list is genuinely empty in the live DB).
- No applicable label → **25 families** (10 `NO_INDEPENDENT_LABEL`,
  5 `REVIEW_REQUIRED_SCREEN_FAILED`, 6 `ZERO_EVIDENCE`, plus 4 `LABEL_GENERIC`).
- The problem label is **not** copied to every family: LC 1's brute-force,
  while-brute and sort-two-pointer families did **not** inherit `hash_map_lookup`.

Every family's `approval_state` is `PENDING_REVIEW`; the reviewer-facing artifacts
(`review_sheet.json/md`) provably omit techniques, strategies, PEC sets and
profiles (asserted by test).

## 13. Number of APPROVED labels

**0.** No human reviewer is available in this environment, so no label is
APPROVED (and none was self-approved). Recorded as **PA1**:

> PA1: the POC runs with `label_mode = 'provisional_unreviewed'`. A family label
> that passes the §3.4 screen is treated as *provisionally activatable*. This makes
> `activation_rate` and the derivation measurable. It is **not** an approval and
> does not satisfy `>= 6 APPROVED labels` (OPEN-3 / OPEN-4).

For transparency the run also computes **strict mode** (only APPROVED may
activate): `activated_groups = 0`.

## 14. Divergence distribution

| state | count |
|---|---|
| `LABEL_OK` | **12** |
| `LABEL_GENERIC` | **4** |
| `LABEL_PARTIAL` | 0 |
| `LABEL_UNEXPRESSIBLE` | 0 |
| `LABEL_MULTI_OVERLAP` | 0 |
| `NO_INDEPENDENT_LABEL` | **10** |
| `ZERO_EVIDENCE` | **6** |
| `REVIEW_REQUIRED_SCREEN_FAILED` | **5** |

`activation_rate = 12/16 = 0.75` (activated ÷ labelable families). The three
"partial" states did not occur naturally because the §3.4 screen already refuses
families that do not observe every required concept; their code paths are
exercised by unit tests instead.

## 15. Required / optional / excluded derivation

For all **12** activated groups `required == L` **exactly** — never narrowed —
and `required ⊆ observed_intersection`, so every group is satisfiable by every
derivation member. `optional` is restricted to observed concepts the label marks
optional or that are SUPPORT-tier; `excluded` is the label's set carried through
verbatim. `required_expected` (informational) is recorded on the review artifact
only when a label is refused, and is never written into a group.

## 16. Negative-control definition and counts (canonical rule)

Eligibility: (1) different problem, (2) disjoint curated pattern sets,
(3) structurally disjoint PEC set, (4) not ZERO_EVIDENCE. All eligible controls
tested **exhaustively** (`N_min = 5`, PROVISIONAL).

| metric | value |
|---|---|
| eligible pairs tested | **881** |
| failing pairs | **0** |
| **`discrimination_FP`** | **0.0** (gate ≤ 0.05) |
| without rule 3 (same-family reuse counted) | 10 / 891 = **0.0112** |
| excluded: same problem / same curated patterns / PEC-overlap / zero-evidence | 96 / 40 / 10 / 125 |
| `same_family_reuse_count` | 10 |
| groups with `INSUFFICIENT_CONTROLS` | 0 |

Every exclusion is reported. Even with rule 3 disabled the metric stays under the
gate, so **OPEN-5** (is rule 3 the right exclusion) now has a data point: rule 3
removes 10 same-family pairs and changes the rate from 1.12 % to 0 % — both pass.

## 17. Validation split

Family-first, deterministic, no overlap (asserted):
`n >= 3 → held_out = ceil(0.4·n), derivation ≥ 1`; `n == 2 → 1/1`;
`n == 1 → derivation only, VALIDATION_LIMITED`. **4 limited families**.
`derivation = 44`, `held_out = 52`, overlap = 0.

## 18. Held-out population

**52** — above the `3 × problems = 36` gate (POC v1: 8/40, below its gate). No
criterion is claimed met unless this gate holds; it holds.

## 19. Every validation metric

| metric | value | gate | status |
|---|---|---|---|
| singleton_rate | 0.1081 | ≤ 0.25 | **pass** |
| max families/problem | 4 | ≤ 4 | **pass** |
| held_out_population | 52 | ≥ 36 | **pass** |
| discrimination_FP | 0.0 | ≤ 0.05 | **pass** |
| group_satisfiability | 1.0 (12/12) | = 1.00 | **pass** |
| narrowing_violations | 0 | = 0 | **pass** |
| family_coverage | 1.0 (22/22) | ≥ 0.85 | **pass** |
| D1 exercised | 7/7 | ≥ 3 | **pass** |
| D2 exercised | 32/32 | ≥ 3 | **pass** |
| ZERO_EVIDENCE handling | 12 cases; 0 confirmed/labeled/control | — | **pass** |
| approved_family_labels | **0** | ≥ 6 | **FAIL** |
| positive_confirm_rate | 0.4231 (22/52) | — | informational |
| unresolved_rate | 0.5 (26/52) | — | informational |
| contradicted | 4 | — | informational |

The 26 UNRESOLVED held-out members are overwhelmingly members of families with
**no applicable independent label** (the honest refusal path), not matcher errors.
The 4 CONTRADICTED are all attributable to a group's `excluded` concept firing on
an *alternative* family: `lc70_fam2` (memoised recursion) contradicted by the
`dp_1d_forward` group's `excluded=[recursive_branching]`, and `lc102_fam2`
(recursive DFS) contradicted by `bfs_level_order`'s exclusion. This is carried-over
V1 `excluded` semantics, not a V2 grouping/derivation defect; recorded as an OPEN
consideration (see §22).

## 20. Every failed acceptance criterion

**1 of 11 fails.**

1. **`approved_family_labels >= 6` — observed 0.** Cause: **environment
   limitation, not a design flaw.** This environment cannot supply a human
   reviewer, and the design correctly forbids auto-approval. Classification:
   *human-review gate* (OPEN-3 / OPEN-4). No rule was weakened, no label was
   fabricated, and no threshold was adjusted to pass.

No other criterion failed. `rules_unchanged_on_failure` is recorded `true`.

## 21. Comparison against POC V1

| dimension | POC v1 | POC v2 | cause of change |
|---|---|---|---|
| corpus | 8 × 5 = 40 | 12 × 8 = 96 | V2 §8 (F2/F10/F11/F12) |
| families | 31 | 37 | larger corpus, coarser partition |
| singleton rate | **74 %** | **10.8 %** | concept tiers + profile + anti-split (F1–F4) |
| families/problem | up to **5** | max **4** | same |
| held-out population | **8 / 40** (gate unmet) | **52 / 96** (gate met) | family-first split + lower singleton rate (F10) |
| `discrimination_FP` | **0.1228** (disjoint) / 0.1702 (raw) | **0.0** (canonical) / 0.0112 (no rule 3) | never-narrow + specificity floor (F7/F8); canonical rule (F14) |
| `group_satisfiability` | 1.0 | 1.0 | preserved |
| `narrowing_violations` | n/a | **0** | new hard gate (F7) |
| `label_agreement` | 0.8529 (FAIL) | **replaced** by divergence distribution + `activation_rate` | metric was 1.0-by-construction; V2 §5.4 (F9) |
| families w/ no label | 12/29 | 25/37 (all refusal states) | label model made honest, not forced |
| D1 / D2 | **0 / 0** (untested) | **7 / 32** (all correct) | duplicate-containing corpus (F11) |
| ZERO_EVIDENCE | 6/40, edge case | **12/96, first-class** | V2 §9 (F12) |
| LC 1 identical `hash_lookup` | split (2 families) | **one family** | skeleton demoted (F4) |
| LC 21 / LC 560 | 5 families each | **4 each** | PEC partition (F3) |

**The two V1 failures are fixed, and one V2 criterion introduces a gate the
environment cannot satisfy.**

## 22. Remaining OPEN decisions

Carried from V2 §10, updated with this run's evidence:

| ID | status after this POC |
|---|---|
| OPEN-1 skeleton/τ as representative parameter | still OPEN; τ never affected a boundary; representative choice changed no metric in this run |
| OPEN-2 PEC ratification of the 5 provisional concepts | **still OPEN** (human/taxonomy); no split/merge error attributable to them observed |
| OPEN-3 human blinding | **still OPEN** — no human review ran |
| OPEN-4 `activation_rate` floor | **still OPEN** — provisional `activation_rate = 0.75` measured; a human round is required to interpret it |
| OPEN-5 negative-control strength / rule 3 | **new evidence**: with rule 3 = 0.0, without = 0.0112; both under gate. `N_min = 5` untested (0 groups below it) |
| OPEN-6 offline LLM proposals | **still OPEN** — not shipped |
| OPEN-7 label-source conflict rule | **still OPEN** — no conflict instance |
| OPEN-8 profile discriminant set | **still OPEN**; 4 singletons remain, 3 of them analyzer-coverage artifacts |
| OPEN-9 corpus saturation | **still OPEN**; the "5 more add nothing" test has not been run |
| OPEN-10 cross-problem same-family controls | **still OPEN**; 10 such pairs measured (`same_family_reuse_count`) |
| OPEN-11 `LABEL_MULTI_OVERLAP` handling | **still OPEN** — 0 instances observed |
| OPEN-12 minimum corpus size before promotion | **still OPEN** |
| **NEW-1** `excluded` contradicts alternative families | 4 held-out CONTRADICTED, all from carried-over V1 `excluded` semantics; decide whether a problem-level `excluded` should apply across all families or only the labeled family |

## 23. Is the V2 design validated?

**The mechanism is validated. The full acceptance set is not met, solely on the
human-approval gate.**

Validated by measurement:

- Over-splitting is fixed: singleton rate 74 % → **10.8 %**, families/problem
  ≤ 4, and the exact LC 1 skeleton-split is gone.
- The never-narrow rule removes the false-positive family: **881** eligible
  controls, **0** failures, `narrowing_violations = 0`, `group_satisfiability = 1.0`.
- Labels are family-level and honest: problem labels are screened, not copied;
  refusals (`LABEL_GENERIC`, `NO_INDEPENDENT_LABEL`, `REVIEW_REQUIRED_SCREEN_FAILED`)
  are recorded rather than forced.
- Zero-evidence is first-class and cannot confirm, be labeled, or act as a control.
- The pipeline is deterministic (byte-identical artifacts on re-run), auditable,
  read-only over the analyzer, and has no LLM/network/DB path.

Not validated here:

- Reviewer blinding in practice and `activation_rate`/`N_min` calibration — both
  require the human review round that this environment cannot provide.

---

## Conclusion

**A. The V2 architecture is validated by the mechanism; proceed to Phase 6 *design*
only after the human-review precondition is met.**

This is not a forced A. Every structural acceptance criterion passes on measured
values, and the two POC-v1 failures are demonstrably fixed. The only failing
criterion — `>= 6 APPROVED family labels` — fails because **no human reviewer
exists in this environment**, and the design (correctly) forbids auto-approval;
it is an environment limitation, not a design flaw (so **not B**), and the
mechanism was fully measured on this corpus (so **not C**).

Per V2 §Final-5, **Phase 6 remains blocked** until all six conditions hold. Five
are now satisfied by this POC (end-to-end execution, structural criteria,
`discrimination_FP ≤ 0.05` under the canonical rule, `family_coverage ≥ 0.85` on a
population above the gate, and §11 corrections accepted). **Condition 4 — a real
human review round producing `>= 6 APPROVED` family labels — is NOT met** and is
the required next step. `review_sheet.md` / `review_sheet.json` are the artifacts
to hand to that reviewer.

**Nothing in the production system, existing GT, the matcher, the
detectors/techniques/strategies/vocabulary, or the database was modified.**

## Files

`experiments/code_analysis_evaluation/gt_poc_v2/`: `problem_metadata.py`,
`corpus_authored.py`, `core.py`, `ingest.py`, `normalize.py`, `grouping.py`,
`labeling.py`, `derive.py`, `controls.py`, `validate.py`, `run_shadow.py`,
`run_poc.py`, `tests/test_gt_poc_v2.py`, and the artifacts
`reference_solutions.json`, `normalized_solutions.json`, `families.json`,
`family_labels.json`, `review_sheet.json`, `review_sheet.md`,
`label_comparison.json`, `derivation_outcomes.json`, `negative_controls.json`,
`validation.json`, `run_manifest.json`.
