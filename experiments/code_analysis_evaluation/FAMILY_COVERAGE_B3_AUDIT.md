# Family Coverage — Batch B3 Audit

**Document type:** implementation + measurement audit (B3 only)
**Status:** B3 implemented and measured; **B4 not started**
**Date:** 2026-09-26
**Scope:** `concept evidence (B2) → family coverage → coverage state` — shadow path only.

**Invariants honoured:**

- no detector, technique, strategy, threshold, Ground-Truth row, database,
  API or frontend file was modified;
- the existing shadow matcher (`matching.evaluate_solution_groups`) is untouched;
- the B2 falsifier ledger is unchanged;
- only one already-tracked production file changed (`shadow_runner.py`), and
  the change is purely additive;
- every number below was **measured**, never tuned to a target.

---

## 1. Implementation files

| File | Kind | Change |
|---|---|---|
| `pathforge/ast_analysis/shadow/family_coverage.py` | new | the whole B3 layer (coverage model, states, rules, gate, report) |
| `pathforge/ast_analysis/shadow/shadow_runner.py` | modified | + import, + step 7 guarded block, + `"coverage"` key (additive only) |
| `pathforge/tests/test_family_coverage.py` | new | 32 B3 tests (the 14 required items + corpus regressions + isolation) |
| `pathforge/tests/test_tri_state_evidence.py` | modified (test only) | the pre-B2 reconstruction helper now also strips the additive B3 lines; the additive-key set/pop assertions include `coverage` |
| `pathforge/tests/test_concept_registry.py` | modified (test only) | registry-consumer allow-list adds the B3 module + its test |
| `experiments/code_analysis_evaluation/runners/family_coverage_b3_measure.py` | new | the B3 measurement runner |
| `experiments/code_analysis_evaluation/results/family_coverage_b3_measurement.json` | new | the measurement artifact |
| `experiments/code_analysis_evaluation/runners/tri_state_b2_measure.py` | modified (experiment only) | its pre-B2 reconstruction now strips the B3 lines too so it stays runnable |

`git diff --stat` for tracked files: **1 file changed, 39 insertions(+), 0 deletions** —
i.e. relative to the committed base the whole B2+B3 addition to `shadow_runner.py`
is additive (no pre-existing line was rewritten).

## 2. Family coverage model

A *family* is an existing Ground-Truth solution group. B3 adds one immutable
record per family:

```
FamilyCoverage(
    family_id, identifying_required, supporting_required,
    present_identifying, not_established_identifying, contradicted_identifying,
    present_supporting, not_established_supporting, contradicted_supporting,
    conclusion_eligible_present, coverage_state, reason_codes, authority_tier,
)
```

- `identifying_required` — `required` concepts whose registry `family_role` is
  `IDENTIFYING`.
- `supporting_required` — every other `required` concept (`COMPONENT`,
  `SUPPORTING`, `ABSENT-NOT-ALLOWED`, or unregistered).
- the `present_*` / `not_established_*` / `contradicted_*` triples are the B2
  states restricted to those sets.
- `conclusion_eligible_present` — the family's `required` concepts that are
  conclusion-eligible **and** `PRESENT`.
- a `CoverageReport` wraps the records and adds `no_ground_truth`, `counts`,
  `reason_counts`, and a *measurement-only* `aggregate_state` projection
  (`CONTRADICTED > CONFIRMED > PROVISIONAL > UNRESOLVED`, else `UNMATCHABLE` /
  `NO_GROUND_TRUTH`). The projection exists only so the old matcher's single
  outcome and B3's per-family coverage can be compared; it is not a new verdict.

Exactly six states exist: `CONFIRMED`, `PROVISIONAL`, `UNRESOLVED`,
`CONTRADICTED`, `NO_GROUND_TRUTH`, `UNMATCHABLE`.

## 3. Exact CONFIRMED rule

`CONFIRMED` **iff all** of:

1. a valid GT family with a non-empty `required` set;
2. at least one `IDENTIFYING` requirement exists **and every** identifying
   requirement is `PRESENT`;
3. no identifying requirement is `CONTRADICTED`;
4. every supporting/component requirement is `PRESENT` (none `NOT_ESTABLISHED`,
   none `CONTRADICTED`);
5. `conclusion_eligible_present` is non-empty.

Condition 5 is the false-confirmation fence: a family whose only evidence is
`TECHNIQUE`/`OBSERVATION` can never be `CONFIRMED` from structural matches alone.

## 4. Exact PROVISIONAL rule

`PROVISIONAL` iff all of:

1. a valid GT family with an identifying requirement;
2. every identifying requirement is `PRESENT`;
3. no identifying requirement is `CONTRADICTED`;
4. and either a supporting/component requirement is `NOT_ESTABLISHED`
   (`reason = supporting_not_established`) or silently absent, **or** a
   supporting/component requirement is `CONTRADICTED`
   (`reason = supporting_contradicted`), **or** condition 5 of §3 fails because
   no conclusion-eligible concept is `PRESENT` (`reason = no_conclusion_eligible`).

`PROVISIONAL` is *"the family is supported by the established identifying
evidence, but its evidence is incomplete"*. It is explicitly **not** a
correctness verdict (right/wrong).

## 5. Exact UNRESOLVED rule

`UNRESOLVED` when identifying evidence is not established sufficiently:

- **no `IDENTIFYING` requirement exists** (`reason = no_identifying_requirement`)
  — a family made only of `COMPONENT`/`SUPPORTING` concepts has no identity
  anchor, so it can neither confirm nor be ruled out; **or**
- **some identifying requirement is `NOT_ESTABLISHED`** and none is
  `CONTRADICTED` (`reason = identifying_not_established`).

Silence therefore leads to `UNRESOLVED`, never to `CONTRADICTED`.

## 6. Exact CONTRADICTED escalation rule

`CONTRADICTED` **iff** one of the family's **identifying requirements** is
`CONTRADICTED` at the concept level by B2 (a positively observed structural
falsifier, or a declared mutual exclusion whose partner is `PRESENT`).

- A concept-level `CONTRADICTED` is escalated **only** when the concept is an
  applicable (identifying) requirement of that family.
- It is **not** escalated for supporting/component concepts, for `optional`
  concepts, or for concepts the family does not require.
- The `excluded` set is deliberately **not** reinterpreted as a falsifier
  (proposal §9 Rule K4; the conservative default). No falsifier was invented and
  the B2 ledger is unchanged.

## 7. Conclusion-eligible gate

`conclusion_eligible_present(required_concepts, snapshot)` is the reusable gate.
It reads `concept_registry.concept.conclusion_eligible` **only** — never
technique/observation presence, `v1_image`, or a legacy pattern name — and is
scoped to a family's `required` concepts (an unrelated strategy observed
elsewhere in the submission must not let a structurally-matched family confirm).

## 8. Role handling

Roles come from the B1 registry `family_role` metadata; no role is invented.

- `IDENTIFYING` → the family's identity anchors (`identifying_required`).
- `COMPONENT` / `SUPPORTING` → supporting/component requirements.
- `ABSENT-NOT-ALLOWED` (an observation appearing in a requirement) → treated as
  a non-identifying supporting requirement rather than inventing a new role.
- Unregistered required concepts → non-identifying, and their state can only be
  `NOT_ESTABLISHED`.

## 9. LC3236 / db-49 analysis

Recorded Ground Truth (`db-49`, also `db-51`, `db-194`): one family whose
`required` is `["sequential_accumulation"]`.

- `sequential_accumulation` is a `TECHNIQUE` / `COMPONENT` — it is **not**
  conclusion-eligible (registry `family_role = COMPONENT`), so it may not
  identify the family.
- B2 reports `sequential_accumulation = PRESENT` and
  `forward_pointer_advance = PRESENT`; neither is conclusion-eligible.
- **B3 result:** `identifying_required = []` →
  `UNRESOLVED (no_identifying_requirement)`. The old matcher's `CONFIRMED`
  remains present as `match_outcome` for cross-checking, but the B3 coverage is
  not `CONFIRMED` and `conclusion_eligible_present` is empty.
- No strategy was manufactured; neither `sequential_accumulation` nor
  `forward_pointer_advance` was promoted.

## 10. `dfs_backtracking` contradiction handling

B2 raises `dfs_backtracking = CONTRADICTED` whenever `cache_lookup` /
`cache_write` is observed (the known-broad structural distinction). In the
46-corpus, `TWO_SUM`-shaped submissions satisfy this.

- `dfs_backtracking` is only a family contradiction when it is an **identifying
  requirement** of that family.
- For every family that does not require `dfs_backtracking` (e.g. the Two Sum
  hash family), the concept keeps its B2 `CONTRADICTED` state and the family is
  **not** contradicted.
- Measured: 46-corpus has 18 concept-level contradictions and only **1**
  family-level contradiction (an identifying one, see §12); 17 were intentionally
  not escalated. The 301 corpus has **70** concept contradictions, **0** family
  contradictions, and **0** family-level escalations.

## 11. Old-vs-B3 measurements

The recorded artifacts are stale relative to the current pipeline (a fact B2
already established), so the primary comparison is the **fresh** old matcher
(`match_outcome.outcome`) versus B3 coverage on the same inputs; the recorded
distribution is reported too. Agreement is **not** forced.

## 12. 46-case results

46 real submissions, 51 families. Distribution:

| | CONFIRMED | PROVISIONAL | UNRESOLVED | CONTRADICTED | UNMATCHABLE |
|---|---|---|---|---|---|
| recorded old artifact | 31 | – | 15 | – | – |
| fresh old matcher | 32 | – | 14 | – | – |
| **B3 coverage** (per submission, aggregate) | **23** | **0** | **11** | **1** | **11** |

Per-family records (51 total): CONFIRMED 23, UNRESOLVED 16, CONTRADICTED 1,
UNMATCHABLE 11 — the two submissions with two families are why per-submission
`UNRESOLVED` (11) is lower than per-family `UNRESOLVED` (16).

Enumerated transitions (fresh old → B3):

| # | transition | count |
|---|---|---|
| 1 | CONFIRMED → CONFIRMED | 23 |
| 2 | CONFIRMED → PROVISIONAL | 0 |
| 3 | CONFIRMED → UNRESOLVED | 9 |
| 4 | CONFIRMED → CONTRADICTED | 0 |
| 5 | UNRESOLVED → PROVISIONAL | 0 |
| 6 | UNRESOLVED → CONFIRMED | 0 |
| 7 | UNRESOLVED → UNRESOLVED | 2 |
| 8 | UNRESOLVED → UNMATCHABLE (unexpected/other) | 11 |
| | UNRESOLVED → CONTRADICTED | 1 |

Other required counts:

- confirmed families **with** a conclusion-eligible `PRESENT` concept: **23**;
- confirmed families **without** one: **0** (hard invariant, asserted);
- provisional families: **0** (explanation below);
- family-level contradictions: **1** (`db-253`, LC29 `binary_search_answer` —
  `binary_search` is the family identity and is contradicted by
  `opposite_direction_updates`: an *applicable* contradiction, so the family is
  ruled out);
- concept contradictions intentionally not escalated: **17 of 18**.

The 9 `CONFIRMED → UNRESOLVED` are exactly the false-confirmation shapes the
brief targets, all `no_identifying_requirement`:

| submission | problem | family `required` (all COMPONENT) |
|---|---|---|
| db-48, db-50, db-135 | LC2 | `linked_list_traversal` |
| db-49, db-51, db-194 | LC3236 | `sequential_accumulation` |
| db-139 | LC141 | `forward_pointer_advance` |
| db-193 | LC496 | `monotonic_stack_maintenance` |
| db-252 | LC21 | `forward_pointer_advance` |

The 11 `UNMATCHABLE` are the stored groups with an empty `required` (the
existing representation gap: LC1, LC13, LC628, LC1574 ×2, LC3812, LC4080,
LC438, LC4256, LC4258): the old matcher already reported these as `UNRESOLVED`
via its `unmatchable` handling, and B3 labels them explicitly.

**Why 0 provisional in the 46 corpus:** every one of its 51 families has a
*single* `required` concept, so there is no compound family whose identity is
established while a component is not. `PROVISIONAL` is exercised by the 301
corpus (23 cases) and by unit tests. This is reported, not "fixed".

## 13. 301-case results

301 disjoint cases. Each case's `required_concepts` is treated as a single
family requirement (documented interpretation of a detector-level corpus).

| | TP | FP | TN | FN | UNMAPPED_LABEL |
|---|---|---|---|---|---|
| recorded verdict | 87 | 13 | 78 | 64 | 59 |

| B3 aggregate | count |
|---|---|
| CONFIRMED | 29 |
| PROVISIONAL | 23 |
| UNRESOLVED | 190 |
| UNMATCHABLE | 59 |
| CONTRADICTED | 0 |

- The 29 `CONFIRMED` families require conclusion-eligible strategies
  (`two_pointers_opposite`, `binary_search`) that are `PRESENT`.
- The 23 `PROVISIONAL` are all `hash_map_lookup` families: `hash_lookup` is
  `IDENTIFYING` but a `TECHNIQUE` (not conclusion-eligible), so identity is
  established and the final conclusion is not → `PROVISIONAL`. This is the
  technique-vs-strategy distinction made visible (an architectural consequence,
  not a regression).
- The 190 `UNRESOLVED` are `prefix_sum` / `hash_map_lookup` /
  `two_pointers_opposite` families whose identifying evidence is not established
  (or, for `prefix_sum`, whose `required` is the `COMPONENT`
  `sequential_accumulation`, so `no_identifying_requirement`).
- The 59 `UNMATCHABLE` carry an empty `required` set.
- 70 concept contradictions were retained at concept level; **0** families were
  contradicted.

The previously recorded `metrics` precision/recall block is preserved verbatim
in `family_coverage_b3_measurement.json` (`preserved_recorded_metrics`); B3
tunes no detector, so it is unchanged.

## 14. Tests

- `pathforge/tests/test_family_coverage.py` — **32 passed**: the 14 required
  items (all-identifying-present; identifying+supporting-NE → PROVISIONAL;
  identifying-NE → UNRESOLVED; silence ≠ contradiction; supporting-NE ≠
  contradiction; no-conclusion-eligible → cannot confirm; identifying TECHNIQUE
  identifies but does not conclude (`candidate_selection`); non-applicable
  concept contradiction not escalated (`binary_search` / `dfs_backtracking`);
  applicable identifying contradiction escalated; `NO_GROUND_TRUTH`;
  `UNMATCHABLE`; existing shadow output present; old matcher untouched;
  production untouched) plus corpus regressions (`db-49/51/194` never confirm;
  LC209 confirms without escalation; a real non-escalated concept contradiction).
- `pathforge/tests/test_concept_registry.py` — 48 passed.
- `pathforge/tests/test_tri_state_evidence.py` — 65 passed.
- `pathforge/ast_analysis/shadow/tests` — 810 passed.
- `experiments` — 79 passed.
- `src` — 605 passed, 1 pre-existing failure
  (`test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`,
  unrelated legacy detector).
- `pathforge/tests`, `pathforge/ast_engine`, `pathforge/db`, `tests` — all
  passed (the 2 `pathforge/tests/test_pipeline.py` cases need a live Supabase
  connection and are the known environmental failures).
- B2's differential measurement runner still passes: 0 deterministic-field
  mismatches on both corpora, identical outcomes, 0 B2-attributable drift — with
  B3 fully stripped from the pre-B2 arm.

## 15. Production isolation confirmation

- `git diff --stat` (tracked files): `shadow_runner.py | 39 +`, 0 deletions.
- `TestProductionIsolation` asserts no module under `pathforge/api/`,
  `pathforge/services/`, `src/`, `pathforge/ast_engine/`, `pathforge/llm/`,
  `pathforge/db/` references `family_coverage` / `build_family_coverage`.
- `matching.py` contains no `family_coverage` / `coverage_state` reference; the
  coverage model is imported by exactly one runtime module (`shadow_runner.py`).
- The registry-consumer allow-list is still exact; B3 adds exactly one new
  authorised consumer (`family_coverage.py`) plus its test.

## 16. Remaining architecture decisions before B4

Recorded, not decided:

1. **Family identity for component-only families.** B3 reads a family whose
   `required` has no `IDENTIFYING` concept as `UNRESOLVED`. Whether Ground Truth
   should instead declare an identifying strategy for these (LC2/LC21/LC3236)
   families is a GT-vocabulary decision (`NEW-3`).
2. **Technique-only family conclusions.** `hash_lookup` families are
   `PROVISIONAL` because no `STRATEGY` represents them. Whether a strategy
   concept is added, or these families remain permanently `PROVISIONAL`, is a
   vocabulary decision that precedes any B4 precedence work.
3. **`PROVISIONAL` visibility/scoring.** B3 keeps it non-scoring and internal;
   whether it is persisted or user-visible is unresolved (proposal §24.2).
4. **`excluded` semantics.** B3 does not reinterpret `excluded` as a falsifier.
   Whether per-family exclusions should require structural falsifiers (`NEW-1`)
   must be settled before precedence/authority work.
5. **Authority of contradictory identifying evidence.** B3 escalated one 46-case
   family on an identifying `binary_search` contradiction even though the old
   matcher stayed `UNRESOLVED`; B4/B5 must decide how `PROVISIONAL`/`CONTRADICTED`
   interact with `authority_tier` (currently not gating coverage).
6. **Specificity/primary selection** — explicitly B4 and not started.

---

## Final report (A–L)

**A. B3 implemented?** Yes. `family_coverage.py` + one additive `coverage` key
on the shadow result; B4 not started.

**B. New family coverage states?** `CONFIRMED`, `PROVISIONAL`, `UNRESOLVED`,
`CONTRADICTED`, `NO_GROUND_TRUTH`, `UNMATCHABLE` (exactly these six).

**C. Does CONFIRMED require conclusion-eligible PRESENT evidence?** Yes. It is
condition 5 and is enforced by a reusable gate; measured
confirmed-without-eligible = 0 in both corpora.

**D. Does missing supporting evidence become PROVISIONAL?** Yes — an
identifying-established family with a `NOT_ESTABLISHED` (or contradicted)
component requirement becomes `PROVISIONAL`, never `CONTRADICTED`.

**E. Does silence remain NOT_ESTABLISHED?** Yes; silence yields `UNRESOLVED` at
family level and is never a contradiction.

**F. Are concept contradictions prevented from blindly becoming family
contradictions?** Yes. Escalation happens only for an identifying requirement:
17/18 (46-corpus) and 70/70 (301-corpus) concept contradictions were not
escalated.

**G. What happened to LC3236/db-49?** `CONFIRMED` → `UNRESOLVED`
(`no_identifying_requirement`); no conclusion-eligible concept was promoted.

**H. What happened to `dfs_backtracking`/`cache_lookup` cases?** The concept
stays `CONTRADICTED`; families that do not require `dfs_backtracking` are
unaffected and are not contradicted.

**I. 46-submission measurements.** Fresh old `{CONFIRMED 32, UNRESOLVED 14}` vs
B3 `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}`; transitions
23/0/9/0 and 0/0/2/11 as tabulated in §12.

**J. 301-case measurements.** B3 `{CONFIRMED 29, PROVISIONAL 23, UNRESOLVED 190,
UNMATCHABLE 59, CONTRADICTED 0}`; recorded precision/recall preserved unchanged;
no detector tuned.

**K. Tests.** B3 32, B1 48, B2 65, shadow 810, experiments 79, src 605/606
(1 pre-existing), remaining suites green except the 2 known live-DB
environmental cases.

**L. Decisions genuinely required before B4.** Itemised in §16 — chiefly the
identity of component-only families, whether technique-only families ever
confirm, `PROVISIONAL` visibility, `excluded`/falsifier semantics, and how
authority gates coverage.

**STOP — B3 complete. B4 not started.**
