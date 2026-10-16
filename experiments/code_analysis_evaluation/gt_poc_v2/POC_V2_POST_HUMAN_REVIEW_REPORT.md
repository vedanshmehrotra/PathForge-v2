# Ground-Truth Architecture POC V2 — Post-Human-Review Report

**Scope:** offline POC/evaluation only. No production runtime, no production GT row, no
database, no matcher, no detector, no technique, no strategy, no vocabulary, no shadow
pipeline logic, no existing V2 grouping/derivation logic was modified. `git status` shows
**zero tracked-file modifications** — every change is a new untracked artifact.

**Run:** `python -m experiments.code_analysis_evaluation.gt_poc_v2.run_post_review`

**Round:** `human_review_round_1` — the first real human review of the V2 POC's families.

---

## 1. Human-review summary

### 1.1 Artifacts discovered

The teacher returned **two PDF files**, placed in `experiments/code_analysis_evaluation/gt_poc_v2/`:

| file | role |
|---|---|
| `PathForge_V2_Review_Decisions-2.pdf` (145 KB, 3 pages) | **authoritative** reviewer decisions + remarks |
| `pathforge_v2_solutions.pdf` (47 KB) | the blind review sheet that was handed to the reviewer — one reference implementation per family, each carrying a self-documenting decision header |

They were not previously present; both have a modification time later than every pipeline
artifact. The repository `.md`/`.json` artifacts in that directory are the earlier
*pre-review* outputs, not the review.

### 1.2 How they were consumed

`pdftotext` (poppler) extracted both to text. Two new files were created for traceability —
**the raw PDFs were never modified**:

- `human_review_source.txt` — mechanical `pdftotext -layout` extraction of the decisions PDF (254 lines, sha256 `3d800508…`)
- `human_review_solutions_source.txt` — mechanical extraction of the solutions PDF (sha256 `887f0153…`)

The reviewer's decisions were then transcribed into the committed, machine-readable
`human_review.json` (the **only** input the pipeline reads), with `human_review.md` rendered
from it. The interpretation layer is not trusted: **14 verification checks** re-derive the
transcript's claims from the mechanical extractions.

### 1.3 Cross-check result — no discrepancies

| check | result |
|---|---|
| decisions vs families | **37 decisions for 37 families** — bijective, none missing, none duplicated |
| decision tally vs the PDF's summary line | `APPROVED: 16 \| CORRECTED LABEL: 20 \| REJECTED: 1` — **exact match** |
| per-family decisions re-parsed from the reviewer sheet | **37/37 agree**, 0 mismatches |
| per-family corrected labels re-parsed from the reviewer sheet | **0 mismatches** |
| member counts (3/2/1/2 … 7/1) | sum to **96**, matching the corpus |
| source digests | `decisions_pdf=verified`, `solutions_pdf=verified` |
| auditability fields | every decision carries `reviewer_reason`, `source_ref`, `review_status` |

**No missing, duplicate, malformed or silently-repaired decisions. There were no
disagreements between the teacher's two files, or between the teacher's files and the
transcript.** Every decision mapped to exactly one family, verified by family key.

### 1.4 Ingested result

- **37 reviewed families** → **16 APPROVED**, **20 CORRECTED LABEL**, **1 REJECTED**
- The review was blind: the reviewer worked only from the solutions sheet, and the POC test
  suite proves that artifact carries no technique/strategy/PEC/profile output.
- Nothing was auto-approved: the transcript's states drive activation; no code approves anything.

---

## 2. Before/after label counts

| quantity | before (pre-review) | after (human review) |
|---|---|---|
| families with a label of any kind | 16 | **36** |
| — approved as proposed | 0 | **16** |
| — human-corrected (also human-approved) | 0 | **20** |
| — rejected | 0 | **1** |
| — `PENDING_REVIEW` | 37 | **0** |
| activation-eligible (`APPROVED`) | 0 (strict) / 16 (provisional, PA1) | **36** |
| activated GT groups | 12 (provisional only) | **14** (strict **and** provisional) |
| labelable families (non-empty required) | 16 | **36** |
| `activation_rate` | 0.75 (12/16) | **0.3889** (14/36) |

Two honest readings of `activation_rate`, which would otherwise look like a regression:

1. **More groups activate** (12 → 14). The rate falls only because the human review labelled
   **36** families instead of 16, so the denominator grew 2.25×. It is a denominator effect.
2. The rate measures observability, not correctness: **23 of 37 families produce no group**
   (10 unexpressible, 6 generic-refused, 1 partial, 5 zero-evidence, 1 rejected). That is the
   dominant remaining limitation and is reported as such in §6 and §10.

**PA1 is retired.** Pre-review the POC ran under `PA1` (`provisional_unreviewed` — "no human
reviewer exists"). Post-review, strict mode (`APPROVED` only) and provisional mode activate
the **same 14 groups**, so the review has removed the assumption rather than worked around it.

---

## 3. Family-level decision table

`APPROVED` = proposed label confirmed. `CORRECTED` = the reviewer supplied the family's label.
`→` = the divergence state the frozen V2 state machine then produced. Divergence states:
`OK`=LABEL_OK, `UNEX`=LABEL_UNEXPRESSIBLE, `GEN`=LABEL_GENERIC, `PART`=LABEL_PARTIAL,
`ZE`=ZERO_EVIDENCE.

| family | n | decision | human label | → state | group? |
|---|---|---|---|---|---|
| lc1_fam1 | 3 | APPROVED | `hash_lookup` | OK | **yes** |
| lc1_fam2 | 2 | CORRECTED | `brute_force` | ZE | no |
| lc1_fam3 | 1 | CORRECTED | `brute_force` | UNEX | no |
| lc1_fam4 | 2 | CORRECTED | `two_pointers_opposite` | OK | **yes** |
| lc21_fam1 | 1 | APPROVED | `forward_pointer_advance` | GEN | no |
| lc21_fam2 | 2 | CORRECTED | `sort_and_rebuild` | UNEX | no |
| lc21_fam3 | 2 | APPROVED | `forward_pointer_advance` | GEN | no |
| lc21_fam4 | 3 | CORRECTED | `recursive_merge` | UNEX | no |
| lc46_fam1 | 3 | CORRECTED | `iterative_insertion` | ZE | no |
| lc46_fam2 | 2 | APPROVED | `dfs_backtracking` | OK | **yes** |
| lc46_fam3 | 3 | APPROVED | `dfs_backtracking` | OK | **yes** |
| lc70_fam1 | 3 | APPROVED | `dp_bottom_up` | OK | **yes** |
| lc70_fam2 | 3 | CORRECTED | `dp_top_down` | OK | **yes** |
| lc70_fam3 | 2 | CORRECTED | `dp_bottom_up` | ZE | no |
| lc102_fam1 | 4 | APPROVED | `bfs_shortest_path` | OK | **yes** |
| lc102_fam2 | 4 | CORRECTED | `recursive_dfs_by_depth` | UNEX | no |
| lc125_fam1 | 3 | APPROVED | `two_pointers_opposite` | OK | **yes** |
| lc125_fam2 | 2 | CORRECTED | `clean_and_compare_reverse` | ZE | no |
| lc125_fam3 | 3 | CORRECTED | `two_pointers_opposite` *(recursive)* | UNEX | no |
| lc209_fam1 | 4 | APPROVED | `sequential_accumulation + sliding_window` | OK | **yes** |
| lc209_fam2 | 2 | CORRECTED | `brute_force` | UNEX | no |
| lc209_fam3 | 2 | CORRECTED | `sequential_accumulation` | GEN | no |
| lc242_fam1 | 3 | APPROVED | `frequency_counting` | OK | **yes** |
| lc242_fam2 | 2 | **REJECTED** | — | ZE | no |
| lc242_fam3 | 3 | APPROVED | `frequency_counting` | OK | **yes** |
| lc547_fam1 | 2 | CORRECTED | `bfs_shortest_path` | UNEX | no |
| lc547_fam2 | 3 | CORRECTED | `recursive_dfs_traversal` | UNEX | no |
| lc547_fam3 | 3 | APPROVED | `union_find` | OK | **yes** |
| lc560_fam1 | 2 | CORRECTED | `brute_force` | UNEX | no |
| lc560_fam2 | 2 | APPROVED | `frequency_counting + sequential_accumulation` | OK | **yes** |
| lc560_fam3 | 2 | CORRECTED | `frequency_counting + sequential_accumulation` | PART | no |
| lc560_fam4 | 2 | CORRECTED | `sequential_accumulation` | GEN | no |
| lc704_fam1 | 4 | APPROVED | `binary_search` | OK | **yes** |
| lc704_fam2 | 1 | CORRECTED | `binary_search` *(library-based)* | ZE | no |
| lc704_fam3 | 3 | CORRECTED | `binary_search` *(recursive)* | UNEX | no |
| lc3236_fam1 | 7 | APPROVED | `sequential_accumulation` | GEN | no |
| lc3236_fam2 | 1 | APPROVED | `sequential_accumulation` | GEN | no |

**14 groups activate**, required sets exactly as the reviewer labelled them:
`hash_lookup`, `two_pointers_opposite` (×2), `dfs_backtracking` (×2), `dp_bottom_up`,
`dp_top_down`, `bfs_shortest_path`, `sequential_accumulation + sliding_window`,
`frequency_counting` (×2), `union_find`,
`frequency_counting + sequential_accumulation`, `binary_search`.

**Blinding was preserved end-to-end.** The reviewer never saw a detected technique or
strategy; the analyzer's view remains confined to the post-hoc `label_comparison.json`.

---

## 4. Corrected-label analysis

20 families were corrected. They fall into four distinct causes — the distinction matters
because only two of them are vocabulary problems.

### 4.1 Corrected to a registered concept the analyzer *does* observe → group activated (1)

| family | correction | note |
|---|---|---|
| `lc70_fam2` | — → `dp_top_down` | the analyzer already detects `dp_top_down`; the family previously had **no independent label** because the curated problem pattern (`dp_1d_forward`) could not screen against a non-`dp_bottom_up` family. This is a **coverage gain from the labeling channel**, not from any detector change. |
| `lc1_fam4` | — → `two_pointers_opposite` | same shape: sorted two-pointer was previously unlabelled. |

### 4.2 Corrected to a registered concept the analyzer *cannot observe* (2)

| family | correction | analyzer observes |
|---|---|---|
| `lc125_fam3` | `two_pointers_opposite` *(recursive)* | `recursive_branching` only |
| `lc704_fam3` | `binary_search` *(recursive)* | `recursive_branching` only |

Both are **observation gaps, not vocabulary gaps** — the concept exists, the implementation
form (recursive rather than iterative) is not recognized. V2 correctly refuses rather than
narrowing or forcing a group.

### 4.3 Corrected to a concept outside the frozen vocabulary (7 terms / 10 families)

Registered nowhere in `PEC_CONCEPTS` ∪ `SUPPORT_TECHNIQUES` (verified by test *and* by a
repository grep): `brute_force` (4 families), `sort_and_rebuild`, `recursive_merge`,
`iterative_insertion`, `recursive_dfs_by_depth`, `recursive_dfs_traversal`,
`clean_and_compare_reverse`. Each family resolves to `LABEL_UNEXPRESSIBLE` or
`ZERO_EVIDENCE`; **none activates, and none was added to the runtime vocabulary.**

### 4.4 Corrected to a SUPPORT-only concept → refused by the specificity floor (6)

| family | correction | why refused |
|---|---|---|
| `lc21_fam1`, `lc21_fam3` | `forward_pointer_advance` | SUPPORT tier |
| `lc209_fam3`, `lc560_fam4` | `sequential_accumulation` | SUPPORT tier |
| `lc3236_fam1`, `lc3236_fam2` | `sequential_accumulation` | SUPPORT tier |

**This is the single most consequential finding of the round.** These are labels the *human
approved as correct* — several of them (LC 21 forward-pointer merge, LC 3236 running prefix
sum) describe the intended algorithm faithfully — yet V2 §4.3 refuses to turn them into a GT
group, because a group whose `required` is made only of low-specificity concepts cannot
distinguish its own family from anything else. The floor is doing its stated job; the tension
is that **human label approval and group activation are different acts**, and the review round
supplied the former. This is direct, measured evidence for OPEN-2 (§11).

### 4.5 Summary of corrected labels

| cause | families |
|---|---|
| registered + observed → group activated | 2 |
| registered but not observed (observation gap) | 2 |
| unregistered (vocabulary gap) | 10 |
| registered but SUPPORT-only (specificity floor) | 6 |
| **total corrected** | **20** |

---

## 5. Rejected-family analysis

**`lc242_fam2` — LC 242 (Valid Anagram), 2 members: `anagram_counter_eq`, `anagram_sorted_eq`.**
The rejection was **upheld, not overridden**, and the family remains a refused/rejected family
in the post-review artifact (`approval_state = REJECTED`, no label, no group, never a control).

- **Original V2 classification:** `ZERO_EVIDENCE` — both members produce zero techniques and
  zero strategies, so they were grouped together by the *absence* of evidence
  (`observed_intersection = []`, `pec_set = []`).
- **Why coherence could not be verified:** the family was formed not by a shared algorithm but
  by a shared *lack* of one. `Counter(a) == Counter(b)` and `sorted(a) == sorted(b)` are two
  genuinely different approaches. From the sheet alone the reviewer could not establish that
  the members represent one approach — and they do not.
- **Consistency with V2's refusal-first principle:** fully consistent, and *independently
  corroborated by it*. V2 §9 already forbids a `ZERO_EVIDENCE` family from being labelled,
  activated or used as a control. The reviewer's criterion ("family coherence cannot be
  established") and V2's §9 rule are the same rule reached from two directions.

**New finding — NEW-2.** The ZERO_EVIDENCE bucket is a **partition by absence, not by
similarity**, so it can merge algorithmically distinct approaches into a single "family". The
family count therefore slightly *understates* the true number of distinct approaches whenever
a ZERO_EVIDENCE bucket has ≥2 members. V2 §9's never-label rule already contains the risk;
this is the first instance where it was observed to matter, and it should be recorded (see §11).

**Coverage was not increased to compensate.** The rejection costs one family a label and one
(already-impossible) group; nothing was forced to raise a metric.

---

## 6. Derivation results

### 6.1 Divergence distribution (post-review)

| state | count |
|---|---|
| `LABEL_OK` | **14** |
| `LABEL_UNEXPRESSIBLE` | **10** |
| `LABEL_GENERIC` | **6** |
| `ZERO_EVIDENCE` | **6** |
| `LABEL_PARTIAL` | **1** |
| `LABEL_MULTI_OVERLAP` | 0 |
| `NO_INDEPENDENT_LABEL` | 0 |
| `REVIEW_REQUIRED_SCREEN_FAILED` | 0 |

Pre-review the same measure was: `LABEL_OK` **12**, `LABEL_GENERIC` **4**,
`ZERO_EVIDENCE` **6**, `REVIEW_REQUIRED_SCREEN_FAILED` **5**, `NO_INDEPENDENT_LABEL` **10**,
`LABEL_UNEXPRESSIBLE` **0**, `LABEL_PARTIAL` **0**.
The screen-failure and no-label states (15 families) are now empty because every family has a
human label; `LABEL_UNEXPRESSIBLE` grew from **0 to 10** because the human labels reach the
vocabulary frontier that the curated problem patterns never probed. `LABEL_GENERIC` grew 4 → 6
and `LABEL_PARTIAL` 0 → 1 for the same reason.

### 6.2 Activation outcomes

| reason | families |
|---|---|
| activated (`required = L`, floor passed) | **14** |
| refused: state not `LABEL_OK` (UNEXPRESSIBLE + GENERIC + PARTIAL) | 17 |
| refused: `ZERO_EVIDENCE` | 5 |
| refused: not in an activatable approval state (`REJECTED`) | 1 |

### 6.3 Never-narrow

**`narrowing_violations = 0`.** Every activated group satisfies `required == L`, and every
refusal is a refusal — no label was silently reduced to the subset the analyzer happened to see.

The clearest instance is **`lc560_fam3`** (`LABEL_PARTIAL`). The reviewer labelled it
`frequency_counting + sequential_accumulation` and explicitly noted it is "the same core
algorithm as fam2". The analyzer observes **only** `sequential_accumulation` in all its
members. V2 therefore refuses a group rather than narrowing `["frequency_counting",
"sequential_accumulation"]` → `["sequential_accumulation"]`. **This is exactly the failure the
never-narrow rule exists to prevent, observed on real data.** Its cost is honest: a correct
family gets no group because the analyzer cannot express half of its algorithm.

### 6.4 Required / optional / excluded

All 14 groups carry `excluded = []`. Human labels are family-level and independent, so a
problem-level exclusion set is **not** attributed to a family the reviewer labelled on its own
evidence. `optional` is derived as before (observed SUPPORT concepts not in `required`), e.g.
`hash_lookup → []`, `binary_search → [candidate_selection, loop_state_tracking]`,
`dp_bottom_up → []`, `union_find → [sequential_accumulation]`.

**This mechanism change is reported prominently because it is the cause of the CONTRADICTED
change below — not a discrimination improvement.** Pre-review, groups inherited `excluded`
sets from the curated problem patterns (`PATTERN_TO_V1_MAPPING`); where a problem has
alternative families, the exclusion derived for one family fired on a *sibling* family's
members. Removing it resolves NEW-1 for this corpus. It does **not** prove exclusions are
unnecessary — see §11 (NEW-1 is partly resolved, not closed).

---

## 7. Validation results

| metric | value | gate | met |
|---|---|---|---|
| `singleton_families` | 4 / 37 = **0.1081** | ≤ 0.25 | **yes** |
| `families_per_problem` | **4** (max) | ≤ 4 | **yes** |
| `held_out_population` | **52** | ≥ 36 (3 × 12) | **yes** |
| `discrimination_FP` | **0.0** (0/1034 canonical pairs) | ≤ 0.05 | **yes** |
| `group_satisfiability` | **1.0** (14/14) | = 1.00 | **yes** |
| `narrowing_violations` | **0** | = 0 | **yes** |
| `family_coverage` | **1.0** (25/25) | ≥ 0.85 | **yes** |
| D1 classification | **7/7** | ≥ 3 correct | **yes** |
| D2 classification | **32/32** | ≥ 3 correct | **yes** |
| ZERO_EVIDENCE handling | 12 solutions, 0 confirmed / 0 labelled / 0 controls | 3 cases, clean | **yes** |
| `approved_family_labels` | **36** (16 as-proposed + 20 corrected) | ≥ 6 | **yes** |

**Overall state: `VALIDATED`. `failed_criteria = []`.**

Supporting figures, stated with their scope so nothing is overclaimed:

- `positive_confirm_rate` **0.4808** (25/52 held-out solutions CONFIRMED)
- `unresolved_rate` **0.5192** (27/52)
- `contradicted` **0** (0/52)
- `family_coverage` **1.0 is measured only over the 25 held-out solutions that sit in an
  activated family and are not zero-evidence** — it is *not* a whole-corpus coverage figure.
  Half the held-out population (27/52) is outside that scope.
- `discrimination_FP` is **0.0 on 1034 eligible control pairs**, with **0 groups below
  `N_min = 5`** — every activated group had at least five canonical controls.
- ZERO_EVIDENCE: 12 solutions; **0** confirmed, **0** labelled, **0** used as a control.

---

## 8. Before-vs-after metrics

| metric | before (PA1, provisional) | after (human review, strict) | change |
|---|---|---|---|
| activated groups | 12 | **14** | +2 |
| `activation_rate` | 0.75 (12/16) | 0.3889 (14/36) | denominator-driven ↓ — see §2 |
| `divergence_state_counts` | see §6.1 | see §6.1 | 17 no-label/screen-failed → 0 |
| `discrimination_FP` | 0.0 (0/881) | **0.0 (0/1034)** | unchanged (more pairs tested) |
| `group_satisfiability` | 1.0 (12/12) | **1.0 (14/14)** | unchanged |
| `family_coverage` | 1.0 (22/22) | **1.0 (25/25)** | unchanged; population +3 |
| `narrowing_violations` | 0 | **0** | unchanged |
| held-out CONFIRMED | 22 | **25** | +3 |
| held-out UNRESOLVED | 26 | **27** | +1 |
| held-out CONTRADICTED | 4 | **0** | −4 |
| `positive_confirm_rate` | 0.4231 | **0.4808** | +5.77 pp |
| `approved_family_labels` | 0 | **36** | +36 |
| overall state | `VALIDATION_FAILED` | **`VALIDATED`** | |
| failed criteria | `['approved_family_labels']` | **`[]`** | |

### 8.1 Every verdict that changed (5 solutions, 3 families)

| solution | problem | family | before → after | cause |
|---|---|---|---|---|
| `S0008` | 1 | `lc1_fam4` | UNRESOLVED → **CONFIRMED** | human label `two_pointers_opposite`; the analyzer observes it. **Caused by the human label.** |
| `S0028` | 70 | `lc70_fam2` | CONTRADICTED → **CONFIRMED** | human label `dp_top_down`; required no longer SUPPORT-only, and no inherited `excluded` contradicts. **Human label + `excluded` change.** |
| `S0029` | 70 | `lc70_fam2` | CONTRADICTED → **CONFIRMED** | same as `S0028` |
| `S0035` | 102 | `lc102_fam2` | CONTRADICTED → **UNRESOLVED** | human label `recursive_dfs_by_depth` is unexpressible → no group → nothing to contradict. **Refusal, not a correctness gain.** |
| `S0036` | 102 | `lc102_fam2` | CONTRADICTED → **UNRESOLVED** | same as `S0035` |

**What did *not* change:** 47 of 52 held-out verdicts, all 14 activated groups' `required`
sets except the two new ones, `discrimination_FP`, `group_satisfiability`, `family_coverage`,
`narrowing_violations`, the grouping (37 families, 4 singletons, max 4/problem), D1/D2, and
every ZERO_EVIDENCE rule.

### 8.2 Honest interpretation of the CONTRADICTED change

`CONTRADICTED 4 → 0` is **not** evidence of better discrimination:

- Two of the four became CONFIRMED through a genuinely new, reviewer-supplied group
  (`dp_top_down`) — a real coverage gain.
- Two became `UNRESOLVED` purely because their family is now correctly refused — a
  *reclassification*, which is the right conservative outcome but not an improvement in
  detection.
- All four previously contradicted because groups carried inherited `excluded` concepts that
  fired across alternative families of the same problem (NEW-1). The human label channel
  supplies no exclusions, so the mechanism disappeared.

`discrimination_FP` was already 0.0 before the review; the review did not improve it.

---

## 9. Brute-Force Taxonomy Finding

*(Diagnosis only. Nothing was implemented; no detector, threshold or vocabulary was touched.)*

### 9.1 Does `brute_force` exist as a formal vocabulary concept?

**No — it is currently only a human descriptive label.** Verified three ways:

- not present in `PEC_CONCEPTS` / `SUPPORT_CONCEPTS` (asserted by a test);
- **zero** occurrences of "brute" in `pathforge/ast_analysis/shadow/*.py`;
- absent from `PATTERN_TO_V1_MAPPING` in `ground_truth_builder.py`.

The reviewer used it for **4 families across 3 problems** (LC 1 `lc1_fam2`/`lc1_fam3`,
LC 209 `lc209_fam2`, LC 560 `lc560_fam1`), and the review guide explicitly sanctioned it.

### 9.2 Where it would fit in the V2 tier model

If `brute_force` were added as vocabulary, `concept_tier()` defaults **unknown → `SUPPORT`**,
and `SUPPORT` concepts **never create a family boundary** and **never satisfy the specificity
floor**. So the V2 default is already protective: a new `brute_force` concept would
**not** be able to activate a group on its own, and could not fragment families.
Promoting it to `PEC` would be the harmful choice: it would partition genuine families
whenever a specific strategy happens to contain a nested loop.

### 9.3 What must take precedence over it

At minimum the specific strategies the corpus shows inside loop-shaped code:
`two_pointers_opposite`, `bfs_shortest_path`, `sliding_window`, `union_find`,
`dfs_backtracking`, `binary_search`, `dp_bottom_up`/`dp_top_down`, and any recursion-shaped
refinement (§10). A `brute_force` claim is only meaningful when no such specific claim holds.

### 9.4 Measured danger of making it too broad

The POC gives three independent measurements.

**(a) "Has nested loop" is not brute force — 66.7 % of nested-loop families are something else.**

| loop_shape = `nested` families | 12 |
|---|---|
| actually labelled `brute_force` | **4** (`lc1_fam2`, `lc1_fam3`, `lc209_fam2`, `lc560_fam1`) |
| legitimately something else | **8** |

| labelled | n | families |
|---|---|---|
| `bfs_shortest_path` | 2 | `lc102_fam1`, `lc547_fam1` |
| `sequential_accumulation` | 2 | `lc209_fam3`, `lc560_fam4` |
| `iterative_insertion` | 1 | `lc46_fam1` |
| `two_pointers_opposite` | 1 | `lc125_fam1` |
| `sequential_accumulation + sliding_window` | 1 | `lc209_fam1` |
| `union_find` | 1 | `lc547_fam3` |

Defining `brute_force` as "contains a nested loop" yields **8 false positives out of 12 =
66.7 % FP exposure**, and it would falsely claim `two_pointers_opposite`, `bfs_shortest_path`,
`sliding_window` and `union_find` implementations.

**(b) The analyzer already over-fires generic concepts on brute-force code** — measured, not
hypothesised. Of the 15 families where the human label has **no overlap** with any observed
concept, the brute-force and adjacent cases are:

| family | human label | analyzer's observed concepts |
|---|---|---|
| `lc1_fam3` | `brute_force` (nested `while` pair search) | `sliding_window`, `forward_pointer_advance`, `sequential_accumulation`, `loop_state_tracking` |
| `lc547_fam1` | `bfs_shortest_path` | `sliding_window`, `loop_state_tracking`, `sequential_accumulation` |
| `lc209_fam2` | `brute_force` | `sequential_accumulation` |
| `lc560_fam1` | `brute_force` | `sequential_accumulation` |

`sliding_window` on a brute-force pairwise scan (`lc1_fam3`) and on a BFS
(`lc547_fam1`) are **human-adjudicated false positives**. Adding an overly broad `brute_force`
would be compounding one generic over-claim with another, on the same code.

**(c) This error family is already documented in-repo**, independently of this POC:
`SEMANTIC_EXPERIMENT_1E_REPORT.md` records `cross_brute_force_two_sum 0.55` ("nested loops
with indexed access — ambiguous") and `cross_brute_force_nested 0.30` ("nested for-range —
borderline"); `SEMANTIC_EXPERIMENT_2A/2B` conclude that `array_traversal`-style generic
concepts are "indistinguishable from any code that iterates a collection" and that this
produces ~25 cross-pattern false positives on brute-force code. The teacher's concern
reproduces a failure the project has hit before.

### 9.5 Should it stay a family-level GT label without becoming a runtime concept?

**Yes — keep it label-only (class D, §10).** It earns its keep as a *label*: it is what let the
reviewer correctly deny `hash_map_lookup` (`lc1_fam2`), `sliding_window` (`lc209_fam2`) and
`prefix_sum`/`hash_map_frequency` (`lc560_fam1`) to three over-claimed families. It carries no
runtime authority, and the V2 tier default means it could not acquire any silently.

**Taxonomy decision required before implementation** (see the final answers): whether
`brute_force` becomes vocabulary at all, and if so at which tier, with which precedence
relation to the specific strategies, and over what evidence — **not** "contains a loop".

---

## 10. Vocabulary gaps / future candidates

Every human label term classified. Classes: **A** already supported by existing vocabulary;
**B** useful family-level GT label, not runtime-recognized, no expansion justified on current
evidence; **C** candidate for future vocabulary expansion (≥2 independent occurrences across
≥2 problems plus a plausible general structural definition); **D** ambiguous — requires a
taxonomy decision before it can be classified.

| class | term(s) / concept | families | occurrences / problems | status |
|---|---|---|---|---|
| **A** | 12 registered terms: `hash_lookup`, `two_pointers_opposite`, `forward_pointer_advance`, `dfs_backtracking`, `dp_bottom_up`, `dp_top_down`, `bfs_shortest_path`, `binary_search`, `frequency_counting`, `sequential_accumulation`, `sliding_window`, `union_find` | **26** | — | already expressible; outcomes governed by observation + the specificity floor |
| **B** | `sort_and_rebuild`, `iterative_insertion`, `clean_and_compare_reverse` | **3** | 1 each / 1 problem each | descriptive restatements; single occurrence; no general form needed yet |
| **C** | **recursive-strategy refinement** (`recursive_merge`, `recursive_dfs_by_depth`, `recursive_dfs_traversal`) | **3**, corroborated by 2 more | 3 terms / 3 problems; **5 families / 5 problems** when the two registered-but-unobserved recursion cases are included | strongest expansion candidate |
| **D** | `brute_force` | **4** | **4 / 3 problems** | taxonomy/precedence decision required first (§9) |

### 10.1 Why C is the strongest candidate — and why it is still not a decision for this task

Five families across five different problems are labelled with a *specific recursive strategy*
while the analyzer observes only `recursive_branching`:

| family | problem | human label | analyzer |
|---|---|---|---|
| `lc21_fam4` | 21 | `recursive_merge` | `recursive_branching` |
| `lc102_fam2` | 102 | `recursive_dfs_by_depth` | `recursive_branching` |
| `lc125_fam3` | 125 | `two_pointers_opposite` (recursive) | `recursive_branching` |
| `lc547_fam2` | 547 | `recursive_dfs_traversal` | `recursive_branching` |
| `lc704_fam3` | 704 | `binary_search` (recursive) | `recursive_branching` |

`recursive_branching` is a single SUPPORT-tier concept absorbing merge, depth-recording
traversal, visited-marking traversal, recursive two-pointer and recursive binary search. Two
of the five are not vocabulary gaps at all (the label term is registered — the *observation*
is missing), which means a narrower recursive concept plus observation would convert those
into expressible groups. This is recurring, structurally distinguishable and supported by
five independent problems — it *would* satisfy the evidence bar.

It is nevertheless **out of scope here** and is recorded as a candidate only: this task is an
evaluation of the human-review round, and the instruction is explicit — no new runtime
vocabulary, no detector work, no threshold tuning. No gap was implemented.

### 10.2 What the human labels reveal about the analyzer (adjudicated, not self-assessed)

15 of 37 families have a human label with **zero overlap** with any observed concept. Beyond
the cases already discussed, the recurring adjudicated over-claims are:

- `sliding_window` reported for a brute-force pairwise scan (`lc1_fam3`) and for a BFS
  (`lc547_fam1`) — **2 human-adjudicated false positives**.
- `sequential_accumulation` reported for two brute-force nested-loop families
  (`lc209_fam2`, `lc560_fam1`) — consistent with the earlier prefix-sum taxonomy audit's
  finding that the technique is intentionally low-specificity.
- `recursive_branching` as a catch-all (5 families, §10.1).

These are recorded as **evidence**, not as a work queue. No detector was modified.

---

## 11. Updated OPEN decisions

Conservative classification. Nothing is marked resolved merely because the review happened.

| ID | decision | status after this round | evidence / what is still missing |
|---|---|---|---|
| **OPEN-1** | skeleton distance as representative-selection parameter (metric + value) | **STILL OPEN — not exercised** | No reported metric responded to the parameter. It remained cosmetic, as the V2 prediction anticipated; the value is still unratified. |
| **OPEN-2** | ratification of the provisional PEC list | **PARTIALLY INFORMED — STILL OPEN, now top priority** | The review exercised the PEC/SUPPORT boundary and produced **hard evidence**: 6 human-approved labels (`forward_pointer_advance` ×2, `sequential_accumulation` ×4) are refused by the specificity floor *only* because their concepts are SUPPORT-tier. The reviewer was **not** asked to ratify the tier list, so ratification is outstanding. |
| **OPEN-3** | human blinding in practice | **PARTIALLY INFORMED — STILL OPEN** | A real review round occurred and was artifact-blind (test-proven: the sheet carries no analyzer output). Procedural blindness outside the artifact is still asserted, not proven: we cannot verify from artifacts what else the reviewer saw. |
| **OPEN-4** | `activation_rate` floor | **INFORMED — STILL OPEN** | Measured on real labels: **0.3889** (14/36) strict, identical in provisional mode. No floor has been agreed, and the denominator definition (36 labelable, including the 6 floor-refused and 5 zero-evidence) itself needs ratifying before a rate can mean anything. |
| **OPEN-5** | `N_min = 5`, and rule 3 (PEC-disjointness) as the right exclusion | **PARTIALLY INFORMED — STILL OPEN** | All 14 groups cleared `N_min` (0 `INSUFFICIENT_CONTROLS`). Rule 3 on → `0/1034`; off → `13/1047` = **0.0124**. Both are under the 0.05 gate, so this round **cannot discriminate** between the two choices; the difference narrowed to 1.24 pp. |
| **OPEN-6** | whether an offline LLM label-proposal stage ships at all | **NOT EXERCISED** | No LLM stage was run (correctly — the sequence is human labels first). Still open. |
| **OPEN-7** | label-source conflict rule on disagreement | **NOT EXERCISED as a conflict** | Human labels *replaced* the curated-problem channel rather than disagreeing with it per family. Channel precedence was applied without a genuine multi-channel disagreement. Still open. |
| **OPEN-8** | profile discriminant set (are the five dimensions sufficient?) | **PARTIALLY INFORMED — STILL OPEN** | Grouping held: 37 families, 4 singletons (10.8 %), max 4/problem. The reviewer reported **no** over-split family; the single rejection was a ZERO_EVIDENCE artifact (NEW-2), not a profile error. But the reviewer was never asked to ratify the dimensions. Still open. |
| **OPEN-9** | corpus saturation point | **NOT EXERCISED** | The "5 further solutions add nothing" test was not run. Still open. |
| **OPEN-10** | cross-problem same-family controls | **PARTIALLY INFORMED — STILL OPEN** | Rule 3 excluded 13 same-family pairs that would otherwise be counted (all 13 were same-family reuse). Both variants stay under the gate. Still open. |
| **OPEN-11** | `LABEL_MULTI_OVERLAP`: refuse or split into sub-labels | **NOT EXERCISED** | **0** natural instances; covered by unit tests only. Still open. |
| **OPEN-12** | minimum corpus size before GT may be **promoted** (not merely derived) | **PARTIALLY INFORMED — STILL OPEN** | All 12 problems now have ≥2 families and ≥1 human-approved label; **10 of 12** have ≥1 activatable group. No minimum has been agreed, and 2 problems (LC 21, LC 3236) still produce no group at all. Still open. |
| **NEW-1** | `excluded` semantics across alternative families | **PARTIALLY RESOLVED — make this an explicit decision** | Mechanism confirmed as the cause of all 4 held-out CONTRADICTED cases: human labels carry no `excluded` set, so cross-family contradiction vanished (4 → 0). That is a *consequence of the label channel*, not proof exclusions are unnecessary. The rule for how a problem-level exclusion should apply per family is still open and must be decided before Phase 6 stores `excluded` in schema. |
| **NEW-2** | *(new this round)* the ZERO_EVIDENCE bucket partitions by **absence**, so it can merge algorithmically distinct approaches | **NEW — needs a decision** | `lc242_fam2` merged `Counter(a)==Counter(b)` with `sorted(a)==sorted(b)`. V2 §9 already forbids labelling/activating/controlling such a family, so the risk is contained, but the family count understates distinct approaches. Decide: split ZERO_EVIDENCE buckets by available structural signal, or keep and document. |
| **NEW-3** | *(new this round)* should family labels with `required` made only of SUPPORT concepts remain permanently unactivatable, or should a reviewed "low-specificity but human-verified" group exist? | **NEW — needs a decision** | 6 human-approved labels are refused solely by the specificity floor (§4.4). This is the concrete form of OPEN-2 and it blocks 6 families from GP coverage. |

---

## 12. Are all V2 Final-5 conditions now satisfied?

The six conditions from `GROUND_TRUTH_ARCHITECTURE_SPEC_V2.md` §"Conditions required before
Phase 6":

| # | condition | status | evidence |
|---|---|---|---|
| 1 | POC runs end-to-end and meets §12.5 structural criteria | **SATISFIED** | all 11 acceptance criteria pass; 37 families, 4 singletons (10.8 %), max 4/problem, D1 7/7, D2 32/32 |
| 2 | `discrimination_FP ≤ 0.05` under the canonical §6 rule | **SATISFIED** | **0.0** (0/1034), 0 groups below `N_min` |
| 3 | `family_coverage ≥ 0.85` on a population meeting the §7.4 gate | **SATISFIED** | **1.0** (25/25); gate 52 ≥ 36 met |
| 4 | **a real human review round has produced `APPROVED` family labels** | **SATISFIED** | **36** human-approved (16 as-proposed + 20 corrected); 1 rejected; verification 14/14 |
| 5 | **OPEN-2 (PEC list) and OPEN-8 (profile discriminants) ratified by a human** | **NOT SATISFIED** | the round was a *label* review. The teacher approved/corrected family algorithms; the teacher was **never asked** to ratify the PEC/SUPPORT tier assignment or the five profile dimensions. Not inferable from the label decisions. |
| 6 | **§11 corrections accepted so the schema is designed from consistent text** | **NOT SATISFIED (not formally)** | the corrections exist and are written up in V2 §11 (I1–I7: five tables/three columns, the `approval_state` vs `validation_status` duplication, etc.), but no acceptance is recorded by a human. |

**Verdict: 4 of 6 satisfied.** The condition that blocked the previous round — the human-review
gate (condition 4) — is now **fully satisfied** with real, verified, auditable evidence. Two
conditions (5, 6) remain, and neither can be discharged by running code.

---

## 13. Exact recommendation for what should happen next

**Do not begin Phase 6.** Conditions 5 and 6 are unmet, and this round produced new evidence
that makes condition 5 *more* consequential, not less:

1. **Settle the taxonomy questions that the review round exposed — before any schema work.**
   - **OPEN-2 / NEW-3 (highest priority).** 6 human-approved labels are refused *purely*
     because `forward_pointer_advance` and `sequential_accumulation` are SUPPORT-tier. Decide
     explicitly: keep the specificity floor absolute (accepting that low-specificity but
     human-verified families can never activate a group), or define a reviewed
     low-specificity group class with its own separation requirement. This decision changes
     what `solution_families`/`gt_versions` must store.
   - **NEW-1.** Decide the per-family `excluded` rule before persisting `excluded`. The 4 → 0
     CONTRADICTED change was produced by *not* propagating problem-level exclusions; that
     behaviour must be a recorded decision, not an implementation side-effect.
   - **NEW-2.** Decide how a ZERO_EVIDENCE bucket is represented once it has ≥2 members.

2. **Then ask the human for the two missing ratifications in one round** (condition 5 + 6):
   - ratify or amend the PEC/SUPPORT tier list — now backed by concrete evidence (the 6
     refused labels, the 5-technique over-claiming of `recursive_branching`, the
     `sliding_window` false positives on `lc1_fam3`/`lc547_fam1`);
   - ratify or amend the five profile dimensions;
   - accept/reject the §11 corrections (I1–I7).

3. **Do not implement `brute_force` yet.** It needs a taxonomy decision first (§9). If it is
   ever added, it must be **SUPPORT-tier and precedence-subordinate** to every specific
   strategy — defining it as "contains a loop / nested loop" has a **measured 66.7 % FP
   exposure** on this corpus and reproduces a false-positive family the project already
   documented in `SEMANTIC_EXPERIMENT_1E/2A/2B`.

4. **Do not implement the C candidate (`recursive_strategy_refinement`) in the same batch as
   the above.** It has strong evidence (5 families / 5 problems) but it is a vocabulary
   expansion, and the instruction for this task is evaluation-only. Record it; scope it
   separately once OPEN-2 is ratified.

5. **Keep everything else frozen.** No detector, threshold, matcher, grouping, derivation or
   vocabulary change was made in this round, and none is justified by its results.

**Bottom line: the V2 human-review gate is closed with real evidence, the architecture is
validated on this corpus, and Phase 6 remains blocked — not by missing data, but by two
human taxonomy/ratification decisions that this round has now made unavoidable.**

### Coverage caveat, stated plainly

Validation passing does **not** mean the GT layer now covers the corpus. Post-review:

- **14 of 37 families (38 %) produce a GT group; 23 do not.**
- **10 of those 23** are unexpressible with the frozen vocabulary, **6** are refused by the
  specificity floor, **5** are zero-evidence, **1** is partial, **1** was rejected.
- **10 of 12 problems** have ≥1 group; LC 21 and LC 3236 have none.
- **25 of 52 held-out solutions are CONFIRMED; 27 remain UNRESOLVED (52 %).**

The dominant remaining failure family is therefore **an under-expressive vocabulary / taxonomy
boundary**, not a grouping, derivation, control or validation defect — which is exactly why the
next step is a taxonomy decision and not more code.

---

## Appendix — the five required answers

**1. Is the V2 human-review gate now satisfied?**
**Yes.** 36 families carry a genuine human-approved label (16 APPROVED as proposed, 20
human-corrected — a corrected label *is* the reviewer's approval of that label), against a gate
of ≥6. The transcript was verified 14/14 against the raw reviewer artifacts, covering 37/37
families bijectively with per-family decisions and labels re-parsed from the reviewer's own
sheet. Nothing was fabricated: no family was marked APPROVED by the pipeline, and the one
family the reviewer rejected stays rejected. *(This closes condition 4 of six; conditions 5
and 6 remain open.)*

**2. What changed after the human review?**
Activated GT groups **12 → 14**; labelable families **16 → 36**; `approved_family_labels`
**0 → 36**; overall state `VALIDATION_FAILED` → **`VALIDATED`** with `failed_criteria = []`;
held-out CONFIRMED **22 → 25**, UNRESOLVED **26 → 27**, CONTRADICTED **4 → 0**; **5 held-out
solutions changed verdict** across 3 families (`lc1_fam4`, `lc70_fam2`, `lc102_fam2`); PA1
retired (strict and provisional modes now converge); `activation_rate` fell 0.75 → 0.3889
**only because the denominator grew 2.25×**. Unchanged: the grouping (37 families, 4
singletons, max 4/problem), `discrimination_FP` (0.0), `group_satisfiability` (1.0),
`family_coverage` (1.0), `narrowing_violations` (0), D1/D2, and all ZERO_EVIDENCE rules. The
CONTRADICTED 4 → 0 is a consequence of human labels carrying no `excluded` set plus two
correct refusals — **not** an improvement in discrimination.

**3. Which corrected labels are currently unsupported by runtime vocabulary?**
**7 terms across 10 families:** `brute_force` (4 families: LC 1 `lc1_fam2`/`lc1_fam3`, LC 209
`lc209_fam2`, LC 560 `lc560_fam1`), `sort_and_rebuild` (lc21_fam2), `recursive_merge`
(lc21_fam4), `iterative_insertion` (lc46_fam1), `recursive_dfs_by_depth` (lc102_fam2),
`recursive_dfs_traversal` (lc547_fam2), `clean_and_compare_reverse` (lc125_fam2). None was
added to the vocabulary; all resolve to `LABEL_UNEXPRESSIBLE` or `ZERO_EVIDENCE` and none
activates. **Two further families are observation gaps, not vocabulary gaps** — the term is
registered but the analyzer cannot see the recursive form (`lc125_fam3`
`two_pointers_opposite`, `lc704_fam3` `binary_search`). Separately, **6** human-approved
families are refused by the specificity floor because their terms are registered but
SUPPORT-tier only (`forward_pointer_advance` ×2, `sequential_accumulation` ×4).

**4. Does the brute-force concern require a taxonomy decision before implementation?**
**Yes.** `brute_force` is currently a human label only — not in the taxonomy, absent from the
analyzer entirely. It is high-recurrence (4 families / 3 problems) and therefore not
dismissible, but implementing it is unsafe without a decision, because the measurements are
explicit: "contains a nested loop" has **66.7 % false-positive exposure** (8 of 12 nested-loop
families are legitimately `two_pointers_opposite`, `bfs_shortest_path`, `sliding_window`,
`union_find`, etc.); the analyzer **already** produces human-adjudicated false positives of
exactly this kind (`sliding_window` on a brute-force pairwise scan and on a BFS); and the
project's own `SEMANTIC_EXPERIMENT_1E/2A/2B` reports documented this same error family. The
decision required is: whether `brute_force` becomes vocabulary at all, at which tier (SUPPORT
by default, which is the protective choice), and with what precedence over specific
strategies. Recommendation: **keep it label-only for now.**

**5. Is Phase 6 now justified, or are there still specific architectural decisions to resolve first?**
**Phase 6 is not justified yet.** Four of the six preconditions are met, including the
human-review gate, so the blocker is no longer data. It is two decisions that only a human can
make: **(5)** ratify the PEC/SUPPORT tier list and the five profile dimensions, and **(6)**
accept the §11 schema corrections. Additionally this round produced three newly identified
decisions that would otherwise be frozen into schema (NEW-1 per-family `excluded` semantics,
NEW-2 ZERO_EVIDENCE bucket representation, NEW-3 whether reviewed low-specificity families may
ever activate). Proceeding now would persist a grouping/labeling/derivation contract whose
tier semantics the human has not ratified and whose low-specificity behaviour is demonstrably
undecided — precisely the failure mode the V1 → V2 revision existed to prevent. **No Phase 6
implementation was begun.**
