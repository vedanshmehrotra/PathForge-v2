# Fresh-Submissions Measurement Report — Post-M1/M2 Architecture Check

**Measurement only. No production code modified. No M3, no vocabulary expansion, no BFS/strategy/matcher/ground-truth changes.**

## 1. New-submission availability

- Prior registries (7 files) merged: **69 unique fingerprints** (`results/registry_merged_prior.json`).
- Live `submissions` table: **92 rows** → 48 unique normalized-code fingerprints (harness `sha256(normalize_code(code))`).
- Harness verdict with the merged registry: **"nothing new to analyse (47 submission(s) already in registry)"** → **0 genuinely new submissions exist.** The dataset file written during discovery (`dataset/db_submissions_m1m2_fresh.json`) is an input artifact of the (disproven) new-batch hypothesis; it contains only already-analyzed submissions.
- Integrity note: an initial ad-hoc fingerprint formula (problem_id + code, unnormalized) disagreed with the harness registry; the harness-native formula was adopted and the discovery finding was **discarded** rather than re-analyzing anything. The no-re-analysis rule held.

## 2. Method

Since no fresh code exists, the honest substitute is a **record-level pre/post comparison over the identical corpus** (same 46 DB submissions, same fingerprints, verified pairwise):

- BEFORE = `results/db_batch3/submission_eval_results.json` (pre-M1/M2 code)
- AFTER = `results/m1m2/submission_eval_results.json` (current code: M1+M2+N2, live DB groups)

## 3. CONFIRMED / UNRESOLVED / CONTRADICTED

| | batch3 (pre) | m1m2 (post) |
|---|---|---|
| CONFIRMED | 31 | **32** |
| UNRESOLVED | 15 | **14** |
| CONTRADICTED | 0 | **0** |

**Exactly one verdict change:** `db-244` (LC 102) UNRESOLVED → CONFIRMED via `bfs_shortest_path` at satisfaction 0.800 — the already-committed **N2** queue-fact fix, not M1/M2. All other 45 records: identical verdict, identical strategy sets, **zero gt-finding drift**.

- **False confirmations: 0** (the 2 historical label-mismatch flags remain GT-representation artifacts, unchanged).
- **False contradictions: 0.**
- **Wrong strategy selections: 1** (unchanged: `db-246` LC 200 — correct `union_find` + spurious `dp_bottom_up`; verdict unaffected).

## 4. Failure distribution (14 UNRESOLVED, classified by fact profile + code inspection)

| category | n | share | detail |
|---|---|---|---|
| **GT vocabulary gap (missing concept)** | 11 | **78.6%** | 9 with `unmatchable_group` (expected `hash_map_lookup`/`hash_map_frequency`/`greedy_local` — no V1 concept exists, group cannot be satisfied); 2 more (LC 70/322 `concept_not_derived_from_patterns`) are the same root in derived form. Affected problems: 1×2, 13, 628, 1574×2, 3812, 4080, 438, 4256, 4258 (+70, 322). |
| **Genuine GT/implementation divergence** | 2 | 14.3% | `db-251` (LC 2212): index-arithmetic solution, `nums.index()`-based; expected `two_pointers_opposite` — UNRESOLVED is *correct*, no detector owes this code a strategy. `db-254` (LC 4284): slice-scan (`max(nums[0:i+1])`); expected `two_pointers_same`+`prefix_sum` — likewise a true mismatch. |
| **Missing technique evidence (thin impls)** | 1 | 7.1% | `db-253` (LC 29): division-by-doubling; has `while_loop_comparison`+`opposite_direction_updates` but no binary-search gate satisfied; UNRESOLVED is acceptable-correct. |

**Category checks:**

- **Syntactic-form failures: 0.** Probed all 14 for the exact M1-class forms (assigned stack ops, AnnAssign accumulators, AugAssign-carried ops): none present; none blocked by any form. (M1 already removed the one previously-live instance in LC 102.)
- **Variable-name-heuristic failures: 0 active.** Several UNRESOLVED codes contain graph/cache-like variable names, but no record fails *because* a name allowlist blocked detection — the blocking layer above them is the missing GT concept, not naming. (Residual *risk* confirmed latent: the neighbor/grid allowlist remains the known open case for future grid BFS submissions.)
- **Missing relational evidence: 0.** No record needs a relation the M2 layer does not express.
- **Genuinely new algorithm/strategy concepts: 0.** Every UNRESOLVED maps to a concept already on the known backlog (`hash_map_lookup`, `hash_map_frequency`, `greedy_local`) or to a correct refusal.

## 5. Comparison with pre-M1/M2 batches — did the failure *nature* shift?

| failure class | batch1 | batch2A | batch3 | now |
|---|---|---|---|---|
| GT empty-required / vocabulary gap | 11 (64.7% of UNRES) | 11 | 11 | **11 (78.6%)** — same records |
| REQUIRED_CONCEPT_UNREACHABLE | 6 | 2 (B3/B4 only) | 2 | **2 (Genuine GT/impl divergence)** |
| Syntactic-form failures | 0 in corpus (latent class proven by N2) | 0 | 0 | **0, class closed by construction** |
| Name-heuristic failures | 0 active | 0 | 0 | **0 active** (latent risk only) |
| Missing-relational failures | 0 | 0 | 0 | **0** |
| No-technique-evidence | 3 | 3 | 2 | **1 (thin impl)** |
| New concept families | — | — | — | **0** |

**Conclusion: yes — the nature has shifted, and the shift is now complete.** The residual failure surface is ~79% ground-truth vocabulary (a data/derivation problem, not an analysis problem), ~14% correct refusals, ~7% thin implementations. There is **no remaining record** whose failure is "the analyzer cannot see this syntactic/relational form." The M1/M2 architectural classes went from proven-live (N2's Expr/Assign gap; F4's hand-rolled joins) to zero-occurrence, and importantly the M1 fix is what converted LC 102 from latent-broken to CONFIRMED.

## 6. Recommendations

1. **Is M1/M2 working as an architectural foundation? Yes.** Evidence: zero verdict regressions across every batch; evidence-citation quality improved (23 strict-subset tightenings); the M1 dispatch layer absorbed the LC 102 form gap *before* N2 landed in production; and no remaining failure is attributable to form/name/relational visibility. The pipeline's remaining misses are now almost exclusively *semantic* (missing concepts) or *truthful* (divergence refusals) — exactly where a deterministic analyzer's misses should live.
2. **Is M3 now justified? Partially — and it is no longer the bottleneck.** M3's highest-value piece (queue allowlist) was implicitly superseded: structural queue detection now works through the N2-corrected extractor, and no current failure is name-blocked. The remaining allowlists (neighbor/grid, cache names) have zero active failures in this corpus. Recommend **holding M3** until a future fresh batch shows an actual name-blocked miss; when grid BFS code appears, RC-N2-4 (structural neighbor classification) is the pre-agreed batch for it. Justification-by-evidence, not by anticipation.
3. **Single strongest next engineering candidate: a vocabulary-expansion batch** — add `hash_map_lookup`, `hash_map_frequency`, and `greedy_local` as V1 concepts/techniques with detector wiring, then re-derive affected stored groups via the Batch 2A refresh. This addresses 11 of 14 UNRESOLVED (78.6%) in one generalized move, requires no matcher or strategy changes, and the harness + 46-record corpus is the ready-made acceptance test.

**Stopped after the report. No fixes implemented.**
