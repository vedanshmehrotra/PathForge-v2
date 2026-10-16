# B2 — Tri-State Evidence Model: Audit

**Batch:** B2 (tri-state evidence model)
**Reference:** `experiments/code_analysis_evaluation/ARCHITECTURE_REDESIGN_PROPOSAL.md`
**Scope:** shadow analysis path only. This is a **representation / instrumentation** batch, not a verdict migration.
**Status:** complete. Stopped before B3.

---

## 1. Exact implementation location

| Artifact | Path | Nature |
|---|---|---|
| Tri-state evidence model | `pathforge/ast_analysis/shadow/evidence_state.py` | **new** module (metadata layer + evidence builder) |
| Attachment point (only tracked file modified) | `pathforge/ast_analysis/shadow/shadow_runner.py` | +18 lines, purely additive |
| B2 tests | `pathforge/tests/test_tri_state_evidence.py` | **new**, 65 tests |
| B1 test allow-list (authorised consumer) | `pathforge/tests/test_concept_registry.py` | edited: 1 constant + 1 test name/docstring |
| Before/after measurement | `experiments/code_analysis_evaluation/runners/tri_state_b2_measure.py` | **new** |
| Measurement output | `experiments/code_analysis_evaluation/results/tri_state_b2_measurement.json` | **new** |

`evidence_state.py` imports only:

* `pathforge.ast_analysis.concepts` (the B1 registry — the metadata source of truth), and
* `pathforge.ast_analysis.shadow.coherence.STRATEGY_COMPATIBILITY` (the existing mutual-exclusion declaration, **read, not restated**).

It defines **no** new analysis semantics, thresholds, detectors or vocabularies.

### The complete change to pre-existing production code

```diff
 from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
+from pathforge.ast_analysis.shadow.evidence_state import build_evidence_snapshot
@@ run_shadow_analysis, after step 5
+        # Step 6 (B2): tri-state per-concept evidence. PURELY ADDITIVE ...
+        try:
+            evidence_state = build_evidence_snapshot(
+                facts, technique_evidence, strategy_evidence
+            ).to_dict()
+        except Exception as e:  # pragma: no cover - defensive
+            logging.getLogger(__name__).debug(...)
+            evidence_state = None
@@ return dict
+            "evidence_state": evidence_state,
```

`git diff --stat` → **1 file changed, 18 insertions(+)**, no deletions.

The snapshot is built inside its own guard so that a snapshot failure can never
remove the existing shadow result (which would itself be a behaviour change).
That guard is covered by a test.

---

## 2. State definitions

The only three semantic states. There is deliberately **no** `ABSENT`,
`NOT_USED`, `FALSE` or `MISSING` state (asserted by test).

| State | Meaning | Must never mean |
|---|---|---|
| `PRESENT` | The concept has admissible positive evidence at or above the existing shadow admissibility floor. | — |
| `NOT_ESTABLISHED` | The concept has **not been established by the current evidence system**: no positive evidence, evidence below the floor, an unsupported structural form, or plain silence. | "the solution does not use this concept" |
| `CONTRADICTED` | There is **positive structural evidence that contradicts** the concept. | "we didn't find it" |

**Priority for one concept:** `CONTRADICTED > PRESENT > NOT_ESTABLISHED`
(`STATE_PRIORITY`, asserted). On a tie the higher confidence wins.

Per-concept record (`ConceptEvidence`, frozen dataclass):
`concept_id`, `state`, `confidence`, `source`, `reason_code`,
`evidence_refs`, `contradiction_source`, `image_state`, `reason`.

### The admissibility floor

`EVIDENCE_FLOOR = 0.5` — **reused, not recalibrated**. It is the same
`confidence >= 0.5` test the shadow matcher already applies to required
concepts. No detector threshold was changed.

**Measured caveat (important for B3):** across all 347 corpus submissions the
lowest confidence the shadow layer ever *emits* is **0.75**. The below-floor
branch is therefore a **latent path**: it is reachable in the model and verified
by unit test with synthetic evidence, but **zero** real submissions exercise it.
The 0.5 floor is currently doing no work on this corpus. That is a fact about
the current producers, not a B2 decision.

### Reason codes (machine-readable, for measurement)

`present` · `silent` · `below_floor` · `no_producer` · `documented_only` ·
`structural_falsifier` · `mutual_exclusion`

`silent` covers both "the detector ran and produced nothing" and "the analyzer
has no observation form for this" — these are **indistinguishable from the
evidence system's point of view**, and both mean `NOT_ESTABLISHED`.

---

## 3. How `PRESENT` is determined

One entry per registered concept, produced by up to three producers, then
reduced by state priority:

| Producer | Condition | Confidence |
|---|---|---|
| raw structural fact | the concept's id appears as an observed `fact_type` | `1.0` (a fact is deterministic) |
| shadow technique evidence | `presence_confidence >= 0.5` | the emitted `presence_confidence` |
| shadow strategy evidence | `confidence >= 0.5` | the emitted `confidence` |

A concept with no producer in the shadow evidence system (legacy taxonomy ids,
documented-only concepts) is `NOT_ESTABLISHED` with `reason_code=no_producer`
or `documented_only` — never `PRESENT`, never `CONTRADICTED`. **Silence is not
absence.**

`carry_propagation` is the one triple-source concept (`structural_fact`,
`v1_technique`, `v2_pec_technique`); the reduction rule is exercised on it by
test (fact observed + technique below floor ⇒ `PRESENT` from the fact).

### Legacy aliases are projected, not claimed

For the 29 registry concepts with a `v1_image`, the snapshot reports this
concept's **own** state (usually `NOT_ESTABLISHED`, since the shadow system has
no producer for a legacy id) plus the state of the V1 concept it maps to, in a
separate clearly-labelled `image_state` field. The projection never becomes this
concept's state.

---

## 4. How `NOT_ESTABLISHED` is determined

By exhaustion: every concept that is not `PRESENT` and not `CONTRADICTED`.
Measured breakdown over 347 submissions (30,447 `NOT_ESTABLISHED` states):

| Reason | Count | Share |
|---|---:|---:|
| `silent` (producer ran, no evidence) | 18,302 | 60.1% |
| `no_producer` (legacy-only id) | 11,451 | 37.6% |
| `documented_only` | 694 | 2.3% |
| `below_floor` | **0** | 0.0% |

Every one of these remains `NOT_ESTABLISHED`. None is promoted to
`CONTRADICTED` by any path.

---

## 5. How `CONTRADICTED` is determined

Only two sources, both requiring **positive** evidence:

1. **An explicitly declared structural falsifier** — a positively observed raw
   structural fact that negates the concept.
2. **An explicitly declared mutual exclusion** whose partner is positively
   established (`PRESENT`), read from
   `coherence.STRATEGY_COMPATIBILITY[*].mutually_exclusive_with`.

Explicitly **not** contradiction sources (and tested as such): no evidence, low
confidence, unsupported syntax, a different detected concept, a different
primary strategy, an old Ground-Truth exclusion, a legacy absence rule.

---

## 6. How falsifiers are handled

B1 copied 32 concepts with non-empty falsifier metadata, in two very different
flavours. Those flavours are **not** interchangeable, and B2 classifies every
one of them into exactly one bucket — validated by
`validate_falsifier_ledger()`, which fails loudly if a new declaration is added
without being classified (tested by injection).

| Bucket | Count | Generates `CONTRADICTED`? |
|---|---:|---|
| legacy Ground-Truth exclusions | 23 | **no** |
| structural falsifiers (evaluator absence constraints on raw facts) | 4 | yes |
| deferred (concept-condition or non-decisive) | 5 | **no** |
| **total declared** | **32** | — |

### The four structural falsifiers

| Concept | Falsifying fact(s) | Trace in existing code |
|---|---|---|
| `sliding_window` | `midpoint_calculation` | `strategies.py::_evaluate_sliding_window` — `if has_midpoint: return None` |
| `binary_search` | `opposite_direction_updates` | `strategies.py::_evaluate_binary_search` — `if has_opposite: return None` |
| `dp_top_down` | `state_restoration` | `strategies.py::_evaluate_dp_top_down` — `if ...: return None` |
| `dfs_backtracking` | `cache_lookup`, `cache_write` | `strategies.py::_evaluate_dfs_backtracking` — `if has_cache: return None` |

Inclusion rule, recorded in the module so the table cannot silently grow: (1)
the registry must already declare a falsifier **and it must not be a legacy
exclusion**; (2) every listed id must be a registered structural fact (a raw
observation), not another concept; (3) the constraint must be **unconditional**
in the implementation; (4) observing the fact must actually negate the concept.

### The five deferred declarations, and why

| Concept | Declared form | Why not encoded |
|---|---|---|
| `hash_lookup` | `recursive_branching evidence present` | condition on **another concept**, not a raw fact; B2 must not infer contradiction from a different detected concept |
| `frequency_counting` | same | same |
| `dp_bottom_up` | same | same (mutual exclusion exists only as an evaluator constraint, never declared) |
| `bfs_shortest_path` | same | same |
| `forward_pointer_advance` | `genuine opposite-direction scan …, or parent_pointer_chase present` | branch-scoped, not decisive: the exclusion applies to the index-pair path only and the multi-pointer path can still establish the concept |

### Deliberate partial encodings (nothing dropped silently)

* `sliding_window` — only the first clause of its composite falsifier
  (`midpoint_calculation`) is encoded. The second clause ("a genuine
  opposite-direction scan") is **not**: the evaluator guards it behind a further
  refinement of the same fact (it re-checks, per `while_loop_comparison`,
  whether `compared_variables <= modified_variables`), so observing
  `opposite_direction_updates` alone does **not** negate the concept. The third
  clause is a three-fact monotonic-stack conjunction, not a single raw fact.
* `two_pointers_opposite` — the mirror structural constraint **exists** in the
  evaluator (`_evaluate_two_pointers_opposite` returns `None` on
  `midpoint_calculation`), but the registry declares only a **legacy
  Ground-Truth exclusion** for this concept. Encoding the undeclared mirror
  would be inventing a falsifier; reinterpreting the legacy exclusion as
  structural is exactly what the rule forbids. B2 therefore leaves it
  `NOT_ESTABLISHED`. **If B4 wants this pair enforced, declare it in the registry
  first.**

---

## 7. How legacy exclusions are prevented from becoming false contradictions

Four independent mechanisms:

1. **Bucket separation by declaration text.** The 23 legacy exclusions are
   identified as those whose registry `falsifier` begins with
   `"declared exclusion (PATTERN_TO_V1_MAPPING)"`. They are placed in their own
   bucket and are never consulted by the contradiction pass.
2. **A validator that refuses the conversion.** `validate_falsifier_ledger()`
   raises if any concept in `STRUCTURAL_FALSIFIERS` has a registry falsifier
   starting with the legacy prefix — i.e. reinterpreting a legacy exclusion as
   structural is a hard error, not a judgement call. Covered by a test that
   monkeypatches exactly that case.
3. **A mutual-exclusion gate on positive establishment.** The only
   non-falsifier contradiction source requires the partner concept to be
   `PRESENT`. An exclusion naming a merely *detected* or *not-established*
   concept produces nothing.
4. **A test on the most tempting case.** `two_pointers_opposite` declares
   `declared exclusion (PATTERN_TO_V1_MAPPING): binary_search`. The test asserts
   that even with `binary_search` positively `PRESENT`, the victim stays
   `PRESENT` — not `CONTRADICTED`.

Measured result: across 347 submissions, legacy exclusions produced **zero**
`CONTRADICTED` states.

---

## 8. Examples from real submissions

Real corpus rows (problem ids are the stored `problem_id`).

**LC1 (Two Sum) — hash lookup with a legacy alias** — `db-11`,
verdict `UNRESOLVED`, counts `PRESENT 9 / NOT_ESTABLISHED 86 / CONTRADICTED 1`:

* `hash_lookup` → **PRESENT**, source `technique_evidence`, confidence `0.80`.
* `hash_map_lookup` (legacy id) → **NOT_ESTABLISHED** with `image_state=PRESENT`.
  The V1 image is reported as a projection; the legacy id is not claimed.
* `dfs_backtracking` → **CONTRADICTED**, `positively observed structural
  falsifier: cache_lookup`, citing `fact_004`, `fact_008` (`seen[num] = i`).

**LC209 — sliding window** — `db-190`, verdict `CONFIRMED` (unchanged),
counts `12 / 83 / 1`:

* `sliding_window` → **PRESENT** (the only conclusion-eligible `PRESENT`).
* `binary_search` → **CONTRADICTED**, `positively observed structural
  falsifier: opposite_direction_updates`. The shrink loop emits that fact, and
  `binary_search` declares it as a falsifier.
* This is a *correct* contradiction: the prediction is negated by positive
  evidence, and the model still reports `sliding_window` as the established
  strategy rather than being confused by the shared facts.

**LC102 — BFS** — `db-244`, verdict `CONFIRMED` (unchanged), counts `8 / 88 / 0`:
`bfs_shortest_path` **PRESENT**, no contradictions.

**LC3236** — `db-49`, verdict `CONFIRMED` (unchanged), counts `10 / 86 / 0`.
Note for B3: this submission is `CONFIRMED` while **no** concept is
conclusion-eligible `PRESENT` (`forward_pointer_advance` +
`sequential_accumulation` only). That is the known false-confirmation shape and
is a **coverage** question for B3, not a B2 behaviour.

**LC560-equivalent — `ps_subarray_equals_k`** (prefix sum + hash, 301-corpus),
counts `12 / 83 / 1`: `hash_lookup` **PRESENT** (0.80),
`hash_map_lookup` projection `PRESENT`, `dfs_backtracking` **CONTRADICTED** via
`cache_lookup`. The greedy-style identity of this case stays `NOT_ESTABLISHED`.

**Recursion pair (synthetic but from real structural facts):**

| Submission | `dfs_backtracking` | `dp_top_down` |
|---|---|---|
| `subsets`-style (`state_restoration`) | **PRESENT** | **CONTRADICTED** |
| memoised `fib` (`cache_lookup`/`cache_write`) | **CONTRADICTED** | **PRESENT** |

**Silence:** a two-line `def f(x): return x` yields `NOT_ESTABLISHED` for 95 of
96 concepts and **zero** `CONTRADICTED`. (The single `PRESENT` is the
`early_termination` fact — an observation, not conclusion-eligible.)

---

## 9. Before/after shadow verdict comparison

### Method

The recorded result artifacts (`db_batch3/submission_eval_results.json`,
`disjoint301_eval_results_BASELINE_step4.json`) are **not** a valid "before B2"
reference: they predate other merged work, so replaying them today already
differs for reasons unrelated to B2 (added facts such as
`mapping_construction`/`membership_test`, the `sequential_accumulation`
extension, reconstructed group authority tiers). The measurement therefore
isolates B2 as the only variable by **reconstructing the pre-B2 runner** from
the current source (deleting exactly the 18 B2 lines, which the script prints
and asserts are attributable to B2), then running both implementations over the
same inputs and comparing **every** field of the shadow result.

`elapsed_ms` is a wall-clock measurement, not a behavioural output; it is
excluded from the equality check and reported separately as B2's cost.

### Result — ZERO change

| Corpus | Cases | Deterministic-field mismatches | `outcome` changed |
|---|---:|---:|---|
| A — 46 real DB submissions (with stored groups) | 46 | **0** | no |
| B — 301 disjoint evaluation cases | 301 | **0** | no |

`outcome` distribution, before → after:

* Corpus A: `{UNRESOLVED: 14, CONFIRMED: 32}` → `{UNRESOLVED: 14, CONFIRMED: 32}`
* Corpus B (no solution groups supplied, so by construction): `{UNRESOLVED: 301}` → `{UNRESOLVED: 301}`

`CONFIRMED` / `UNRESOLVED` / `CONTRADICTED` / `ERROR` counts are therefore
**byte-identical**. No `CONTRADICTED` or `ERROR` outcome exists in either corpus
before or after, and the shadow matcher still makes its own decisions from its
own logic — B2's `CONTRADICTED` **state** is a separate axis from the matcher's
`CONTRADICTED` **outcome**, and the tests assert the two are not coupled.

### Drift against the recorded artifacts, and its attribution

| Corpus | pre-B2 drift fields | post-B2 drift fields | identical in both arms | B2-attributable |
|---|---:|---:|---|---:|
| A | 119 | 119 | **yes** | **0** |
| B | 345 | 345 | **yes** | **0** |

Because the drift is *identical* with and without B2, none of it is attributable
to B2. This is the strongest available statement: the pre-existing drift is real
but belongs to earlier work, and B2 adds nothing to it.

### Instrumentation cost

| Corpus | median Δ | p90 Δ | max Δ |
|---|---:|---:|---:|
| A (46) | +0.70 ms | +1.88 ms | +2.62 ms |
| B (301) | +0.73 ms | +1.30 ms | +3.96 ms |

---

## 10. Test results

| Suite | Command | Result |
|---|---|---|
| **B2 tests (new)** | `pytest pathforge/tests/test_tri_state_evidence.py -q` | ✅ **65 passed** |
| B1 registry tests | `pytest pathforge/tests/test_concept_registry.py -q` | ✅ **48 passed** |
| Shadow suite | `pytest pathforge/ast_analysis/shadow/tests -q` | ✅ **810 passed** |
| `src/` (legacy detectors, matching engine) | `pytest src -q` | ⚠️ **605 passed, 1 failed** (pre-existing, §below) |
| `experiments/` | `pytest experiments -q` | ✅ **79 passed** |
| `pathforge` minus shadow | `pytest pathforge --ignore=pathforge/ast_analysis/shadow/tests -q` | ⚠️ **380 passed, 2 failed** (environmental, §below) |
| **Whole repository** | 1877 tests collected; covered by the chunks above | 1877/1877 accounted for |

The B2 tests cover all twelve required areas: positive evidence; no evidence;
below-threshold evidence; positive falsifier; silence never contradicting; low
confidence never contradicting; legacy exclusion alone never contradicting;
state precedence; registry metadata consumed rather than duplicated; observations
not becoming strategy conclusions; existing shadow verdicts unchanged (via the
reconstructed pre-B2 runner over the named real cases LC3236, LC209, LC102, LC1,
LC15 plus the 301-corpus `ps_subarray_equals_k`, `hm_valid_anagram`,
`tp_container_most_water`); and production path isolation.

### Pre-existing failures (NOT caused by B2, not fixed, not hidden)

1. `src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`
   — assertion failure in the **legacy** detector layer. That file contains
   **zero** references to `pathforge.ast_analysis` / shadow, and no file under
   `src/` was modified by B2.
2. `pathforge/tests/test_pipeline.py::test_full_pipeline_with_mocked_submission_handler`
   and `::test_no_elo_loss_on_duplicate_attempt` — `psycopg2.OperationalError:
   connection to server at "db.rrriujagbpfhrqzjcxfa.supabase.co" … Connection
   timed out`. These tests require a live Supabase PostgreSQL instance, which is
   unavailable in this environment. This is also why a single full-suite run
   exceeds the command timeout and the suite had to be run in chunks.

No existing test was modified to make it pass, with one **authorised** exception:

### The one existing-test edit, and why

`pathforge/tests/test_concept_registry.py` asserted (B1 §9) that **no runtime
consumer of the registry exists yet**, with an allow-list of exactly one file.
B2 is the batch that *authorises* the first consumer, so the allow-list was
extended to `pathforge/ast_analysis/shadow/evidence_state.py` (and to this
batch's test file, which imports the registry directly), and the test was renamed
from `test_no_runtime_consumer_exists` to
`test_only_authorised_registry_consumers_exist`. The assertion remains equally
strict — **any other** consumer still fails it — and the separate guard that no
module under `pathforge/api/`, `pathforge/services/`, `src/` or
`pathforge/ast_engine/` may reference the registry is untouched and still passes.

---

## 11. Corpus / regression measurements

Both existing corpora were run, plus the recorded-artifact drift described in §9.

**347 submissions total** (46 real DB submissions with stored groups + 301
disjoint evaluation cases). Each yields exactly one state per registered
concept: 347 × 96 = **33,312** evidence entries.

### Distribution

| State | Count | Share |
|---|---:|---:|
| `PRESENT` | 2,777 | 8.3% |
| `NOT_ESTABLISHED` | 30,447 | 91.4% |
| `CONTRADICTED` | 88 | 0.26% |

Per corpus:

| Corpus | `PRESENT` | `NOT_ESTABLISHED` | `CONTRADICTED` |
|---|---:|---:|---:|
| A (46 real submissions) | 459 | 3,939 | 18 |
| B (301 disjoint cases) | 2,318 | 26,508 | 70 |

### Contradictions — genuine positive contradictions only

* Contradictions from an **explicit structural falsifier**: **88**.
* Contradictions from **mutual exclusion**: **0**. (The only declared pair is
  `dfs_backtracking ↔ dp_top_down`, which cannot co-occur: each declares the
  other's required fact as its own falsifier, so the structural falsifier fires
  first. The mutex path is therefore exercised by unit test rather than by
  corpus data — reported as measured, not assumed.)
* **Legacy-exclusion contradictions: 0.**

Unique concepts ever contradicted across both corpora — four, all strategies
with declared evaluator absence constraints:

| Concept | Times | Dominant trigger |
|---|---:|---|
| `binary_search` | 43 | `opposite_direction_updates` (window/pointer scans) |
| `dfs_backtracking` | 32 | `cache_lookup`/`cache_write` (hash maps and memos) |
| `sliding_window` | 11 | `midpoint_calculation` |
| `dp_top_down` | 2 | `state_restoration` |

88 of 347 submissions (25.4%) contain at least one contradiction.

**Precision caveat to carry into B3:** `dfs_backtracking` is contradicted on
essentially every hash-map solution, because the fact layer cannot distinguish a
hash map from a recursion memo (`cache_lookup`/`cache_write` come from
`seen[x] = ...` and `if x in seen`). The contradiction is faithful to the
declared semantics, but its *interpretation* depends on a vocabulary conflation
B1 already flagged. It must not be read as "this solution is not a backtracking
solution" without that caveat.

### `NOT_ESTABLISHED` by cause

| Cause | Count |
|---|---:|
| silence (`silent`) | 18,302 |
| no producer for the concept (`no_producer`) | 11,451 |
| documented-only concept | 694 |
| below the admissibility floor (`below_floor`) | 0 |

### Other observations

* **No submission in either corpus had zero `PRESENT` concepts** (`PRESENT` per
  submission: min 1, median 8, max 18). The raw fact layer always fires at least
  one observation (typically `early_termination`). B3's zero-evidence sanity
  classification cannot key off "all concepts `NOT_ESTABLISHED`" alone — that
  state does not occur; it must look at what *kind* of evidence is present.
* `array_traversal` is `PRESENT` only when a subscript is observed; it stays an
  `OBSERVATION` (rank 0, `conclusion_eligible=False`) and never becomes a
  strategy conclusion.

---

## 12. Confirmation that production behaviour is unchanged

1. **Only one tracked file changed:** `pathforge/ast_analysis/shadow/shadow_runner.py`,
   `1 file changed, 18 insertions(+)`, zero deletions. The change appends a key
   to the shadow result dictionary.
2. **`git diff --name-only` filtered to everything except that file → NONE.**
   Nothing under `pathforge/api/`, `pathforge/services/`, `pathforge/llm/`,
   `pathforge/db/`, `pathforge/ast_engine/`, `src/`, or the frontend was touched.
3. **No Ground Truth, database, API, frontend, detector, threshold, technique,
   strategy, vocabulary or matcher change.** In particular
   `pathforge/ast_analysis/shadow/matching.py` does not mention
   `evidence_state`, `NOT_ESTABLISHED` or the new module (asserted by test), so
   the existing shadow family matcher still makes its old decisions including its
   legacy exclusion semantics.
4. **Structurally enforced isolation:** tests assert that no module under the
   production prefixes references the evidence model, that
   `build_evidence_snapshot` is imported by `shadow_runner.py` alone, and that
   `matching.py` is untouched. The pre-existing `evidence_state=` keyword
   argument in `pathforge/services/persistence.py` is an unrelated older name and
   is deliberately not matched by the scan.
5. **Empirically verified:** 347/347 submissions produce identical deterministic
   shadow output with and without B2.
6. **Failure containment:** if snapshot construction raises, the shadow result is
   still returned with `evidence_state = None`, and invalid syntax still returns
   `None` (graceful degradation preserved) — both tested.
7. **Not implemented, per the scope limit:** B3 coverage logic, `PROVISIONAL`,
   identifying/supporting necessity, generic-vs-specific precedence, primary
   strategy selection, zero-evidence sanity classification, authority gating,
   hypothesis handling, matcher replacement, Ground Truth changes, detector or
   threshold changes, database/API/frontend changes.

---

## Final answers

**A. Is tri-state implemented?**
Yes. `pathforge/ast_analysis/shadow/evidence_state.py` implements `PRESENT` /
`NOT_ESTABLISHED` / `CONTRADICTED` with an immutable per-concept record
(`concept_id`, `state`, `confidence`, `source`, `reason_code`, `evidence_refs`,
`contradiction_source`, `image_state`, `reason`) and a per-submission
`EvidenceSnapshot` attached to the shadow result as the additive
`evidence_state` key.

**B. Is silence treated as `NOT_ESTABLISHED`?**
Yes, in all its forms — no evidence, below-floor evidence, unsupported form, and
concepts with no producer at all. 18,302 `NOT_ESTABLISHED` states across the
corpora are silence alone, and 12,145 more are no-producer / documented-only.

**C. Can silence ever become `CONTRADICTED`?**
No. `CONTRADICTED` requires a positively observed structural falsifier or an
explicitly declared mutual exclusion whose partner is `PRESENT`. Zero
contradictions in 347 submissions arose from absence.

**D. Are legacy exclusions prevented from creating false contradictions?**
Yes — four mechanisms (§7): separate bucket, validator that hard-errors on the
conversion, a mutual-exclusion gate requiring positive establishment, and a
direct test on the most tempting case. Measured: 0 legacy-exclusion
contradictions.

**E. Did existing shadow verdicts remain unchanged?**
Yes. 0 deterministic-field mismatches across all 347 submissions;
`CONFIRMED`/`UNRESOLVED`/`CONTRADICTED`/`ERROR` counts identical. Drift against
the older recorded artifacts is identical with and without B2 (119/119 and
345/345), so none of it is B2-attributable.

**F. Did production behaviour remain unchanged?**
Yes. One tracked file, +18 additive lines; no backend, Ground Truth, API,
database, detector, threshold, technique, strategy, vocabulary, matcher or
frontend change.

**G. How many genuine positive contradictions were observed?**
**88** structurally-grounded contradictions, across 4 concepts
(`binary_search` 43, `dfs_backtracking` 32, `sliding_window` 11, `dp_top_down`
2), in 88 of 347 submissions (25.4%). **0** from mutual exclusion and **0** from
legacy exclusions.

**H. Tests passed?**
Yes. 65 new B2 tests pass; 48 B1 tests pass; 810 shadow tests pass; 79
`experiments/` tests pass; `src` 605/606 (the 1 failure is a pre-existing legacy
`prefix_sum` detector test that does not reference the shadow path); `pathforge`
minus shadow 380/382 (the 2 failures need a live Supabase connection that is
unavailable here). One existing test was edited — the B1 "no runtime consumer"
allow-list — because B2 is the batch that authorises that consumer, and the
assertion was tightened rather than loosened.

**I. What decisions are required before B3?**
1. **The 0.5 floor is currently inert** — the producers emit nothing between
   0.25 and 0.75. Decide whether B3 keeps it as a declaration-only guard or
   whether sub-floor evidence must actually occur for coverage to mean anything.
2. **`dfs_backtracking` vs hash maps** — confirm B3 treats this contradiction as
   "not a memoised recursion" rather than "not backtracking", given the
   `cache_*` conflation; or register an explicit falsifier that separates the
   two forms.
3. **Should `CONTRADICTED` be user-visible or matcher input only?** It is
   currently reported per concept and consumed by nothing.
4. **`two_pointers_opposite`'s mirror falsifier** — B4 may want it declared in
   the registry; it is not encoded now, by design.
5. **Zero-evidence cannot be detected by "all `NOT_ESTABLISHED`"** — every real
   submission had ≥1 `PRESENT` observation. Confirm B3 keys its sanity
   classification off the *kind* of evidence (e.g. observation-only with no
   technique) rather than off emptiness.
6. **`carry_propagation`'s dual/triple-source entry** and the other 9 open B1
   review items remain as they were; B2 changed none of them.
