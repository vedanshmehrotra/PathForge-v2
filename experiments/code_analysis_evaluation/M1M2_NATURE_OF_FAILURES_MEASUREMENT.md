# Measurement Report — Post-M1/M2 Failure-Nature Check

**Measurement only. No production code modified. No M3, no vocabulary expansion, no BFS/strategy/matcher/ground-truth changes.**

## 0. Data-integrity disclosure (read first)

- Prior registries (7 files) merged: **69 fingerprints**. Live `submissions` table: **92 rows → 48 unique normalized-code fingerprints** (harness `sha256(normalize_code(code))`).
- **Zero genuinely new submissions exist.** The previous pass's harness verdict stands: every fingerprint in the live table is already in the registry. The table has not changed (still 92 rows; no new export files anywhere in the repo newer than `registry_merged_prior.json`).
- Therefore **no analysis was re-run this session**. All numbers below come from saved, per-record result artifacts compared pairwise by fingerprint:
  - PRE  = `results/db_batch3/submission_eval_results.json` (pre-M1/M2 code, 46 records)
  - POST = `results/m1m2/submission_eval_results.json` (current code: M1+M2+N2, 46 records)
  - Pairwise match: **46/46 fingerprints identical** (0 only-old, 0 only-new).

## 1. Verdicts

| | PRE | POST |
|---|---|---|
| CONFIRMED | 31 | **32** |
| UNRESOLVED | 15 | **14** |
| CONTRADICTED | 0 | 0 |
| NO_GROUPS (no GT row) | (excluded both runs) | (excluded both runs) |

**Exactly one verdict change** across all 46 pairwise-matched records: `db-244` LC 102 Level Order Traversal `UNRESOLVED → CONFIRMED` via `bfs_shortest_path` @ 0.8 — the committed **N2** queue-fact fix, not M1/M2. Technique presence: **0 changes**. Strategy selection: **1 change** (same record).

## 2. Requested per-category results (POST)

| category | count | detail |
|---|---|---|
| False confirmations | **0 real** | 2 label-mismatch flags (db-238 LC 70, db-240 LC 322) are GT-representation issues, not matcher errors: code is recursive-with-memo; structured groups legitimately offer the top-down group; consistency checker reports `concept_not_derived_from_patterns` |
| False contradictions | **0** | no CONTRADICTED in either run |
| Wrong strategy selections | **1 real** | db-246 LC 200: `union_find` ✅ + spurious `dp_bottom_up` ❌; verdict CONFIRMED on the correct group — extra strategy is noise. (db-193 is a naming artifact, not real) |
| Missing vocabulary | **11 records (78.6% of UNRESOLVED)** | `greedy_local` ×5 (db-18, db-36, db-37, db-255, db-256), `hash_map_frequency` ×3 (db-41, db-64, db-192), `hash_map_lookup` ×3 (db-11, db-33, db-39), `sliding_window_fixed` ×1 (db-192, overlapping) |
| Missing technique evidence | **2 records** | db-251 LC 2212 (only `early_termination` + `subscript_index_access` facts — genuinely thin), db-254 LC 4284 (the original Case-3 family: `ind = i` is not self-referential → no accumulator fact; candidate-selection concept does not exist in the technique layer) |
| Syntactic-form failures | **0** | the M1 class (Expr-vs-Assign/AnnAssign/AugAssign) causes zero unresolved records; the one production instance (LC 102 assignment-form dequeue) was absorbed by the M1 dispatch layer via N2 |
| Variable-name-heuristic failures | **0 active** | latent grid-BFS/neighbor-allowlist risk only; no grid-BFS submission exists in the corpus to trigger it |
| Missing relational evidence | **0** | M2 relations are consumed (proven by 23 strict-subset citation tightenings with identical verdicts, from the HEAD-vs-tree diagnostic); no UNRESOLVED record lacks a relation it would need |
| Genuinely new algorithm concepts | **0** | every miss maps to an already-known family (vocabulary, candidate-selection/greedy-local technique, binary-search-on-answer family) |

## 3. Root-cause family distribution, PRE → POST (delta)

```
gt_missing_vocabulary_exposed          11 → 11   (unchanged)
group_unsatisfiable_empty_required     11 → 11   (unchanged)
group_unmatchable_empty_required       11 → 11   (unchanged)
legacy_ast_vocabulary_mismatch         32 → 32   (unchanged, informational)
required_concept_not_detected           4 →  3   (-1, db-244 fixed by N2)
no_technique_evidence                   3 →  2   (-1, db-244 fixed by N2)
ok_confirmed                           12 → 12
concept_not_derived_from_patterns       4 →  4
false_confirmation_label_mismatch       2 →  2
confirmed_on_unexpected_strategy        2 →  2
extra_strategy_inferred                 2 →  2
patterns_vs_groups_drift                1 →  1
required_accumulation_needs_acc_update  1 →  1
```

## 4. Has the NATURE of failures changed? — Yes.

Composition of the 14 UNRESOLVED records (POST):

| nature | n | share |
|---|---|---|
| Missing vocabulary/concept (semantic) | 11 | 78.6% |
| Truthful UNRESOLVED — genuine GT/implementation divergence (LC 2212, LC 4284) | 2 | 14.3% |
| Thin implementation, too little structure to classify (LC 29 variant) | 1 | 7.1% |
| **Syntactic-form (M1 class)** | **0** | 0% |
| **Variable-name heuristic** | **0** | 0% |
| **Missing relational evidence (M2 class)** | **0** | 0% |

Pre-M1/M2 batches contained the two largest detector bugs ever found in exactly those mechanical classes (N2: Expr-only dequeue; N3: while-only accumulation gate). Post-M1/M2, **zero** unresolved records are attributable to mechanical form/relations, and every remaining miss is either a missing *concept* (where a deterministic analyzer's misses should live) or a *correct refusal*. The direction the architecture work targeted is confirmed on real submissions.

## 5. Recommendations

**1. Is M1/M2 working as an architectural foundation? — Yes.**
Zero verdict regressions across every batch since landing; evidence citations strictly tightened without verdict drift; the production form-gap (LC 102) was absorbed by the dispatch layer; the residual failure set is 100% semantic or truthful. Caveat: the corpus is exhausted and the strongest supporting datapoint (M1 preventing the next Expr-vs-Assign bug) is preventive rather than observable; the 32 generalized M1/M2 tests are the standing guard.

**2. Is M3 now justified? — No.**
No current failure is name-blocked. The queue-name allowlist was superseded by N2's structural detection. The only latent name-heuristic failure mode (grid BFS / neighbor allowlist) has no triggering submission. Keep M3 deferred until a real name-blocked miss appears.

**3. Strongest next engineering candidate — vocabulary expansion.**
Add `hash_map_lookup`, `hash_map_frequency`, `greedy_local` as V1 concepts with detector wiring, then re-derive stored groups via the Batch 2A refresh. One generalized move addresses 11/14 UNRESOLVED (78.6%), with the existing 46-record corpus as the ready acceptance test. Second candidate (separate batch): a candidate-selection / greedy-local *technique* for the db-251/db-254 family (original Cases 3/4/5) — that is technique-layer coverage, not a form problem. Tertiary: binary-search-on-answer family (db-253 LC 29) — note its false Sliding-Window inference from the original diagnosis is already gone; it now shows UNRESOLVED with correct techniques.

---

*No code was modified for this report. No submissions were re-analyzed; every number is reproducible from the saved artifacts in `results/db_batch3/` and `results/m1m2/`.*
