# Vocabulary Layer 2 — Step 1: `candidate_selection` (loop form)

**Scope honored:** loop-form `candidate_selection` technique only. No hash_lookup, no frequency_counting, no sort-form, no greedy strategy, no problem-ID logic, no name allowlists, **0 new fact types** (as designed), no legacy matcher changes.

## 1. Files changed

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/techniques.py` | New `_candidate_vars` helper + `_detect_candidate_selection` (T12), registered in `detect_techniques` (receives `relations` like the other migrated detector) |
| `pathforge/services/ground_truth_builder.py` | `candidate_selection` added to `VALID_TECHNIQUES` (11 total); `greedy_local` mapping → `required=["candidate_selection"], optional=["sequential_accumulation"], excluded=["sliding_window"]` (v2 design). **Pre-existing data bug fixed** (see §5) |
| `pathforge/ast_analysis/shadow/tests/test_vocab2_candidate_selection.py` | **new**, 20 generalized tests |
| `pathforge/ast_analysis/shadow/tests/test_phase4a_enrichment.py` | vocabulary-registration tripwire count 10 → 11 (same update Phase 5A / Batch 1 performed) |

## 2. Implementation summary

Evidence, entirely from existing facts + the M2 relation layer:

1. **Loop:** `for_loop_iteration` ∨ `while_loop_comparison` ∨ `while_loop_truthiness`.
2. **Conditional update:** a `conditional_index_update` fact whose `updated_variables` include the candidate — the fact only exists for variables assigned inside a conditional branch inside a loop body.
3. **Scalar-selection fences (both structural, name-free):**
   - **Index-participation fence:** candidate must NOT appear as a subscript index — M2 `used_as_subscript_index` when relations are provided, `_collect_subscript_index_vars` fallback otherwise. Same predicate F4 introduced; separates candidate selection from sliding-window/pointer state.
   - **Accumulator fence:** candidate must have NO `accumulator_update` fact (emitted for every augmented assignment `c += 1` and every self-referential equal-sign assignment `result = result + [...]`). Separates selection from arithmetic accumulation and list building regardless of branch shape.
   - `Assign`/`AnnAssign`/`AugAssign`/tuple-unpack forms are covered automatically because the fact layer (M1 normalized dispatch + existing detectors) already records them — no new AST walking.

Confidence 0.8 / centrality 0.7; supporting = the conditional-update fact + one loop fact + `early_termination` when present (first-match corroboration).

GT integration used the existing machinery only: `MISSING_VOCABULARY_PATTERNS` auto-shrinks (derived from mappings with empty `required`), and the Batch 2A vocabulary refresh re-derives stored `greedy_local` groups — no manual GT rows touched.

## 3. Tests added (20, `test_vocab2_candidate_selection.py`)

- **Positives:** running max; non-obvious names (`q`/`z` — proves not name-based); cascading top-2 (db-37 shape); first-match select-with-break (db-255/256 shape); while-loop form; with-relations vs fact-fallback parity; supporting facts are the designed structural kinds.
- **Negatives:** sum accumulation; conditional count accumulation (`c += 1` inside `if` — caught by accumulator fence); unconditional loop assignment; `if` without candidate update; list accumulation (`result = result + [...]`); window-state index participation; dp-table update; loopless conditional.
- **Relation-layer contract:** a stub relation bundle that disagrees with facts must win (relations can only tighten, never create detections — the fact gates decide admissibility); fact fallback fences windows without relations.
- **Vocabulary:** registration in `VALID_TECHNIQUES`; `greedy_local` mapping shape; `greedy_local` no longer reported as missing vocabulary; every mapping concept is in `VALID_V1_CONCEPTS` (this test exposed the pre-existing bug below).

## 4. Test results

| suite | result |
|---|---|
| New tests | **20 passed** |
| Shadow suite | **635 passed** (615 + 20; all originals green) |
| Full repository | **1509 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` detector failure (`src/ast_detection/tests/test_detectors_batch2.py`); baseline 1489/1 → +20, zero movement |

## 5. Pre-existing mapping bug fixed (disclosed, behavior-neutral)

The new mapping-consistency test exposed that 4 existing entries listed **fact-type IDs** as optional techniques: `linked_list_reversal` (`pointer_rewiring`, `multiple_pointer_traversal`), `monotonic_stack`/`monotonic_deque` (`stack_operation`, `monotonic_comparison`). Fresh derivation of those groups validated as `rejected` today ("optional concept 'pointer_rewiring' not in V1 vocabulary"), and `refresh_group_vocabulary` re-derived the same invalid IDs. Verified behavior-neutral: those IDs could never match a technique as optional evidence (db-193 confirms via the required `monotonic_stack_maintenance`), so removal changes no matching outcome — it only lets fresh derivation validate cleanly. No test was weakened; the tripwire was corrected and the invalid data removed.

## 6. 46-submission before/after (pairwise by fingerprint, 46/46 matched, groups from live DB)

| | BEFORE (`m1m2`) | AFTER (`vocab2_step1`) |
|---|---|---|
| CONFIRMED | 32 | **35** |
| UNRESOLVED | 14 | **11** |
| CONTRADICTED | 0 | 0 |
| ERROR | 0 | 0 |

**Verdict changes — exactly the 3 loop-form greedy records the v2 design predicted:**

| record | problem | evidence causing the change |
|---|---|---|
| db-37 | LC 1574 Max Product of Two Elements | cascading top-2: `conditional_index_update(updated=['i','j'])`, neither participates as index, no accumulator facts → `candidate_selection` → group_0 satisfied 0.800 (bootstrap) |
| db-255 | LC 4256 Uniform Parity Array I | first-odd selection: `conditional_index_update(updated=['odd'])` + `early_termination` → satisfied 0.800 (llm_proposed) |
| db-256 | LC 4258 Uniform Parity Array II | min-odd selection: same shape → satisfied 0.800 (llm_proposed) |

**Technique-evidence changes (10 records):** the 3 flips plus db-254 (LC 4284 — gains `candidate_selection` evidence but its group needs accumulation it cannot produce; verdict correctly unchanged, consistent with the v2 design) and db-35, db-137, db-20, db-234, db-236, db-235 — all already CONFIRMED via their own strategies (window/binary-search families), now carrying additional technique evidence. **Strategy changes: 0. No false confirmations, no false contradictions, no unrelated changes.**

## 7. Safe to proceed with Step 2?

**Yes.** Blast radius matched the v2 prediction exactly (3 predicted flips, nothing else), both fences held on all 46 real submissions plus 20 generalized tests, the relation layer is provably operative, and the residual UNRESOLVED set is now: db-64 (set semantics — intentionally unresolved per v2), db-18/db-36 (sort-form, step 4), db-251/db-253/db-254 (non-vocabulary causes). Step 2 (`mapping_construction` + `membership_test` facts → `hash_lookup`, with the db-35/db-230/db-49/db-193 zero-evidence-change battery) can proceed on this foundation.
