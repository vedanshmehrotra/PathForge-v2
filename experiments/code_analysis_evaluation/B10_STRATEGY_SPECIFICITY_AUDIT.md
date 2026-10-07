# B10 — Strategy-Specificity Contract + Precision Harness (audit)

**Batch:** B10
**Layer:** infrastructure / measurement (evidence only)
**Status:** complete — **no technique was promoted**
**Contract version:** `1.0.0`

---

## 1. Purpose

B9 and B10's predecessors decided two TECHNIQUE → STRATEGY promotions ad hoc, and
both had to be withdrawn after the fact:

* a mapping-shaped technique whose evidence deliberately covers a **static
  reference table** (`hash_lookup` on db-33 / LC13 *Roman to Integer*) as well as
  a dynamic lookup;
* a pair of records where a strong structural signature described a **cache**
  (`hm_memoize_expensive`) and an **adjacency store** (`hm_adjacency_list`).

The failure is always the same shape: the concept is a *tool* or a *family topic*
while the conclusion it would produce claims an *approach*. B10 makes the evidence
that decides such a case **explicit, repeatable and reviewable**, so the next
promotion decision is measured rather than argued.

B10 deliberately promotes nothing. Its expected and actual outcome is that all
four nominated candidates are **BLOCKED** by the contract.

---

## 2. Implementation surface

Created (nothing else in the repository was touched):

| file | role |
| --- | --- |
| `pathforge/ast_analysis/strategy_contract.py` | the concept-agnostic contract (clauses C0–C9, discriminator model, verdict) |
| `pathforge/tests/test_b10_strategy_contract.py` | T1–T16 contract and guard tests |
| `experiments/code_analysis_evaluation/runners/strategy_specificity_measure.py` | the precision harness |
| `experiments/code_analysis_evaluation/results/strategy_specificity_measurement.json` | measurement artifact |
| `experiments/code_analysis_evaluation/results/strategy_specificity_review.md` | human review queue (253 rows, all pending) |
| `experiments/code_analysis_evaluation/B10_STRATEGY_SPECIFICITY_AUDIT.md` | this document |

Modified (allow-list only):

| file | change |
| --- | --- |
| `pathforge/tests/test_concept_registry.py` | added `pathforge/ast_analysis/strategy_contract.py` and `pathforge/tests/test_b10_strategy_contract.py` to `_ALLOWED_REGISTRY_REFERERS`, with a justification block |

The contract must live under `pathforge/ast_analysis/` (not
`pathforge/services/`) because `test_concept_registry.py` guards
`pathforge/api/`, `pathforge/services/`, `src/` and `pathforge/ast_engine/`
against reaching the registry through the decision path. It reads **only** the
registry metadata layer; it does **not** import B3 `family_coverage`, so
`test_family_coverage.py::test_only_the_shadow_runner_references_family_coverage`
still holds.

---

## 3. Contract behaviour

`strategy_contract.py` models C0–C9 and returns one of three verdicts:

| verdict | meaning |
| --- | --- |
| `NOT_EVALUABLE` | C0 preconditions failed — there is nothing to evaluate |
| `BLOCKED` | at least one clause failed; `failing_clauses` names them |
| `READY_FOR_REVIEW` | every clause passed **and** the C3 review is complete (named reviewer + date on every flagged record) |

There is **no** `PROMOTE` verdict. The strongest state the module can produce is
"ready for a human decision"; conclusion eligibility is never conferred by a
program. A `READY_FOR_REVIEW` record that no human has signed still cannot
advance, because C3 requires a reviewer and a date per flagged record.

Clause semantics as implemented:

* **C0 preconditions** — registered concept, class `TECHNIQUE`, a real shadow
  producer, a resolvable legacy namesake, presence in a corpus Ground-Truth
  required set. Any miss ⇒ `NOT_EVALUABLE`.
* **C1 identity** — an explicit algorithmic meaning that is not merely a
  mechanism/tool/data-structure description, and not a restatement of the id.
* **C2 discriminator** — at least one **AVAILABLE** discriminator with a valid
  source, both forms declared, and a *measured* separation that misclassifies no
  tool-use record. `NEEDS_EXTRACTION` and `NOT_AVAILABLE` always fail.
* **C3 precision** — native **and** benchmark measured; every `shadow_only` record
  carries a review entry; an absent, unsigned, `UNRESOLVED` or
  `FALSE_CONFIRMATION` entry blocks.
* **C4 negative controls** — four classes required (positive, negative,
  adversarial, incidental-usage). A missing class blocks; an incidental-usage
  control that **confirms** blocks.
* **C5 GT compatibility** — identification ≠ conclusion, required set and family
  role inspected, ONE_OF memberships recorded, no GT relabel, and an
  identity→conclusion shift must be **declared** rather than silent. A promotion
  justified by "B3 would otherwise not confirm" is rejected.
* **C6 B4 safety** — no redundant consuming strategy, no duplicate meaning, no
  undeclared rank-3 ambiguity.
* **C7 authority/product** — the B3 → B4 → B5 → B6 path must be recorded and an
  authority tier named. Eligibility does not confer authority
  (`AUTHORITY_CONFERRED_BY_ELIGIBILITY = False`), and parity/Elo/gap/recommendation
  effects are not admissible bases.
* **C8 parity** — a before/baseline reference is required and every delta must be
  classified; fewer P4 is never sufficient on its own. P5/P6 regressions are
  classified as `NEW_DISAGREEMENT`, never as improvement.
* **C9 regression** — detectors, controls, B2–B6, the legacy path and unrelated
  strategies must all be unchanged.

Concept-agnosticism is enforced, not merely intended: `test_t1` asserts that no
registered concept id appears anywhere in the contract's source, and `test_t2`
dispatches source validation to the registry's own `structural_fact` inventory
and the shared `SubmissionRelations` dataclass — B10 invents no fact system.

---

## 4. Harness behaviour

`strategy_specificity_measure.py` is evidence-only. For each candidate it
produces concept metadata, producer/sources, resolved namesakes, the four breadth
buckets **with the actual record ids in every bucket**, mismatch evidence
samples, the four negative-control classes (with the incidental-usage control
evaluated for real), the recorded B3 → B6 path, the contract verdict and its
failing clauses, and a `SAFE` / `UNSAFE` / `UNKNOWN` recommendation.

It never modifies GT, never modifies the registry or `concepts.py`, never
promotes, and never invokes a product consequence (no Elo, gap or recommendation
path is imported). `SAFE` means "the evidence is complete enough for a human
decision", never "approved".

Measurement conventions:

* **Shadow axis** — B2 tri-state `PRESENT` for the candidate concept.
* **Legacy axis** — the candidate's namesake detectors, using the legacy system's
  own answer (`result.evidence and result.detected`, matching
  `src/ast_detection/coordinator.py::aggregate_and_filter`). The softer signal
  (evidence with confidence > 0 but `detected` false) is reported separately as
  `legacy_evidence_only` and never enters a bucket, so the two can never be
  confused.
* Namesakes are validated, not trusted: a declared namesake must carry the
  concept in its V1 mapping (`required` or `optional`), otherwise the harness
  aborts.

Corpora: **native 46** (`results/db_batch3/submission_eval_results_NATIVE.json`,
provenance `NATIVE`) and **benchmark 301**
(`results/disjoint301_eval_results_BASELINE_step4.json`, `llm_proposed` GT, used
as a breadth cross-check only).

---

## 5. Candidate results (measured, not asserted)

All four candidates: `recommendation = UNSAFE`, `verdict = BLOCKED`.

| candidate | class | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | failing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `hash_lookup` | TECHNIQUE | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | C2, C3, C4 |
| `sequential_accumulation` | TECHNIQUE | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | C1, C2, C3, C4 |
| `candidate_selection` | TECHNIQUE | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | C2, C3, C4 |
| `forward_pointer_advance` | TECHNIQUE | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | C2, C3, C4 |

### Breadth (shadow B2 PRESENT vs legacy namesake `detected`)

| candidate | corpus | both | shadow_only | legacy_only | neither | legacy_evidence_only |
| --- | --- | --- | --- | --- | --- | --- |
| `hash_lookup` | native 46 | 2 | 1 | 3 | 40 | 0 |
| `hash_lookup` | benchmark 301 | 20 | 13 | 22 | 246 | 0 |
| `sequential_accumulation` | native 46 | 1 | 19 | 1 | 25 | 0 |
| `sequential_accumulation` | benchmark 301 | 21 | 152 | 1 | 127 | 0 |
| `candidate_selection` | native 46 | 3 | 9 | 10 | 24 | 9 |
| `candidate_selection` | benchmark 301 | 5 | 13 | 55 | 228 | 37 |
| `forward_pointer_advance` | native 46 | 5 | 8 | 0 | 33 | 39 |
| `forward_pointer_advance` | benchmark 301 | 4 | 38 | 1 | 258 | 176 |

`hash_lookup`'s single native `shadow_only` record is **db-33** — the Roman
numeral translation table that motivated this batch.

### Why each candidate blocks

* **C2 (all four)** — the best available discriminator is `NEEDS_EXTRACTION` or
  `NOT_AVAILABLE` (key provenance, sequence-question shape, greedy
  choice-continuation, pointer velocity, two-sequence merge shape), and the one
  discriminator that is nominally `AVAILABLE` is measured to **misclassify** real
  tool-use records:
  * `hash_lookup` / `incremental_keyed_lookup` — misclassifies
    `hm_memoize_expensive` (a cache) and `hm_adjacency_list` (an adjacency store),
    both of which carry the full dynamic signature.
  * `sequential_accumulation` / `prefix_index_lookback` — misclassifies db-33 and
    `hm_roman_to_int`; `index_lookback` is PRESENT on a Roman subtractive scan, so
    the fact does not separate a prefix-sum approach from a running total.
* **C3 (all four)** — every `shadow_only` record is unreviewed. 14 / 171 / 22 / 46
  flagged records respectively (253 rows total), all `_(pending human review)_`.
* **C4 (all four)** — the incidental-usage control **confirms** in every case: the
  concept fires where it is demonstrably a tool, not the approach —
  `roman_static_value_table`, `bracket_pair_table` (hash_lookup),
  `digit_sum`, `bare_counter` (sequential_accumulation),
  `sorted_extremal_read` (candidate_selection),
  `floyd_cycle_detection` (forward_pointer_advance).
* **C1 (sequential_accumulation only)** — the declared meaning is a running
  accumulator, but the producer fires on any loop that accumulates; the meaning is
  therefore a mechanism (a bare counter, a digit sum) rather than the approach of
  the 82 benchmark families that require it.

### Recorded B3 → B6 path

For each candidate the harness recorded the current path *without applying any
change*: no family is identified by the concept, B4 selects no primary strategy,
nothing is authoritative, and B6 is not eligible. Authority tier is `INFERRED`
throughout. This is the "current path, not a post-promotion forecast" note carried
in the artifact.

---

## 6. Measurement totals

From `results/strategy_specificity_measurement.json`:

```
candidates            : 4
unsafe                : 4
safe                  : 0
unknown               : 0
shadow_only_records   : 253
reviewed_and_signed   : 0
promoted              : 0
```

Artifact metadata: `batch=B10`, `contract_version=1.0.0`,
`extractor`/`relations` versions recorded from the shadow layer,
`feature_flag.SHADOW_AUTHORITY_PRODUCT_GATING = <unset>` (disabled),
`coverage_states = {}` for all four candidates, and the review file reference
`results/strategy_specificity_review.md`.

`error_ids` is empty for every candidate/corpus (every record parsed, every
record produced a shadow evidence item for the named concept).

---

## 7. Shadow-only records and review status

`results/strategy_specificity_review.md` contains **253 rows** — one per
`(candidate, corpus, record)` where the concept is `PRESENT` and its legacy
namesake is absent. Each row carries a classification slot
(`LEGITIMATE_IMPROVEMENT` / `FALSE_CONFIRMATION` / `REPRESENTATION_DIFFERENCE` /
`UNRESOLVED`) plus `reviewer` and `date` fields.

**All 253 rows are pending.** No reviewer sign-off has been fabricated, and
therefore C3 remains blocked for all four candidates. The harness creates the
file on first run and reads it back on every later run; only a human edits it.
Any `UNRESOLVED` or `FALSE_CONFIRMATION` classification blocks C3 even after a
reviewer signs.

---

## 8. Regression verification

| check | result |
| --- | --- |
| B10 focused tests | **30 passed** (`pathforge/tests/test_b10_strategy_contract.py`) |
| full `pathforge/tests` suite | **551 passed** in 178.9 s |
| registry total | **96** (unchanged) |
| conclusion-eligible | **25** (unchanged) |
| `hash_lookup` | **TECHNIQUE**, non-eligible |
| `sequential_accumulation` | **TECHNIQUE**, non-eligible |
| `candidate_selection` | **TECHNIQUE**, non-eligible |
| `forward_pointer_advance` | **TECHNIQUE**, non-eligible |
| B6 flag `SHADOW_AUTHORITY_PRODUCT_GATING` | **OFF** (`<unset>`) |
| `results/b7_parity_measurement.json` | unchanged (never written by the harness) |
| B1–B8 architecture tests | green (`test_concept_registry`, `test_tri_state_evidence`, `test_family_coverage`, `test_primary_strategy`, `test_authority_gating`, `test_gt_authority_normalization`, `test_b6_product_eligibility`, `test_b6_5_authority_persistence`, `test_b7_legacy_shadow_parity`, `test_b8_authority_reconciliation`) |
| Ground Truth data/provenance files | unchanged (nothing under `experiments/code_analysis_evaluation/ground_truth/` is modified) |
| `pathforge/services/ground_truth_builder.py` | carries a **pre-existing** uncommitted change (last modified 2026-09-27, the earlier `GroundTruthError` work); its diff contains no B10 reference |
| detector files (`src/ast_detection/detectors/`, `src/ast_detection/coordinator.py`) | unchanged |
| B3/B4/B5/B6 logic | unchanged |
| production imports reaching `strategy_contract` | none (T16) |

**Pre-existing, unrelated failure (not caused by B10):**
`src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`
fails with `confidence=0.0, detected=False`. The same failure reproduces in a
pristine `git worktree` at `HEAD`, and `src/` has no uncommitted changes, so it
predates B10. `src/` is outside B10's blast radius; it is reported here rather
than silently omitted.

### Blast radius

`git status --porcelain` shows the six new B10 files plus
`pathforge/tests/test_concept_registry.py`. The tracked-file modifications in the
tree (`config.py`, `experiments/.../real_submission_harness.py`,
`pathforge/ast_analysis/shadow/authority.py`,
`pathforge/ast_analysis/shadow/shadow_runner.py`,
`pathforge/services/ground_truth_builder.py`,
`pathforge/services/persistence.py`,
`pathforge/services/problem_resolver.py`) are **pre-existing uncommitted work from
earlier batches** and were not touched by B10.

---

## 9. Open questions

1. **Is a discriminator for `hash_lookup` extractable at all?** The missing signal
   is *key provenance* — is the tested key derived from the current element, or a
   raw symbol read out of a fixed table? `membership_test` exposes only
   `{variable, negated}` and `subscript_read` only `{structure, gated}`. Without a
   new fact, `C2` cannot pass and promoting T13 would keep the db-33 false
   confirmation.
2. **How should `sequential_accumulation` be narrowed?** C1 currently fails on the
   meaning. Either the producer is narrowed so it stops firing on bare counters
   and digit sums, or the concept is re-declared as a component/mechanism (which
   is what it already is, class-wise: `TECHNIQUE`, `SUPPORT`, `COMPONENT`) and no
   promotion is attempted.
3. **Are the `ONE_OF` memberships meaningful?** `one_of_8512ca5d5fda` is recorded
   for `hash_lookup` and `sequential_accumulation` but not for the other two. C5
   should eventually distinguish "required is genuinely required" from "required
   is one alternative among equals" — the current evidence records it without
   interpreting it.
4. **Who reviews the 253 rows, and against what oracle?** The review file assumes
   a human reads the shadow-vs-legacy disagreement. If legacy is not an oracle,
   the reviewer needs a per-record rationale; the `note` column is there but the
   batch does not prescribe a rubric.
5. **Should `legacy_evidence_only` be a bucket?** It is large for
   `forward_pointer_advance` (176/301) and `candidate_selection` (37/301), meaning
   the namesake detector nearly fires. It is currently reported outside the
   buckets; whether "near-miss" is evidence for or against shadow remains open.

---

## 10. Explicit statement

**No technique was promoted in B10.** `hash_lookup`,
`sequential_accumulation`, `candidate_selection` and
`forward_pointer_advance` all remain `TECHNIQUE`; no Ground Truth, detector, B3,
B4, B5, B6, authority or parity logic was modified; no production path behaviour
changed; and no product consequence was executed. The contract's strongest
possible verdict is `READY_FOR_REVIEW`, and every one of the four candidates is
currently `BLOCKED`.
