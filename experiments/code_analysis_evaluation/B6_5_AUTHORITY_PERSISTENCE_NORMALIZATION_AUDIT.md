# B6.5 — Canonical Authority Persistence Normalization + Native Corpus: Audit

**Batch:** B6.5 — authority representation normalization + native corpus provenance
**Implementation:** `pathforge/ast_analysis/authority_vocabulary.py` (normalization), `pathforge/ast_analysis/shadow/authority_gating.py` (conflict fail-closed), `pathforge/services/problem_resolver.py` (loader annotation), `pathforge/services/product_eligibility.py` (conflict reporting)
**Tests:** `pathforge/tests/test_b6_5_authority_persistence.py` (39)
**Measurement:** `experiments/.../runners/b6_5_authority_normalization_measure.py` → `results/b6_5_authority_normalization_measurement.json` + **native corpus** `results/db_batch3/submission_eval_results_NATIVE.json`

> **The legacy matcher was not replaced.** The feature flag still defaults to
> OFF; legacy semantics (including the deliberate `human_curated` /
> `structurally_observed` conflict) are unchanged. B6 eligibility semantics are
> unchanged. **B7 (legacy-vs-shadow parity/migration readiness) has NOT
> started.**

---

## 1. Scope

B6.5 resolves the two representation problems B6 left open:

1. legacy persistence reads `evidence` while the canonical shadow path reads
   `authority_tier` — two independently interpreted authority values;
2. the historical 46-corpus lacks native `authority_tier` (the old harness
   serialization dropped it), forcing measurement-time enrichment.

Allowed and done: authority representation, serialization, persistence
normalization, GT corpus regeneration/loading, B6 authority input, tests, audit.
Not done: legacy matcher replacement, detector changes, B2–B6 semantics changes,
new tiers, ONE_OF inference, Elo/gap/recommendation/frontend changes, LLM
inference, destructive DB migrations.

## 2. Files inspected

`pathforge/services/persistence.py` (legacy `evidence` gate),
`pathforge/ast_analysis/shadow/matching.py` (legacy tier gate),
`pathforge/services/product_eligibility.py` (B6 gate),
`pathforge/ast_analysis/authority_vocabulary.py` (canonical vocabulary),
`pathforge/services/problem_resolver.py` (loader/reconciliation),
`pathforge/services/ground_truth_builder.py` (builder/serialization),
`pathforge/ast_analysis/shadow/authority_gating.py` (B5),
`experiments/.../runners/real_submission_harness.py` (corpus serialization),
plus the B5/B5.5/B6 audits.

## 3. Canonical authority field

`authority_tier` is the canonical semantic authority field
(`CANONICAL_AUTHORITY_FIELD`); `evidence` is the legacy compatibility
representation (`LEGACY_AUTHORITY_FIELD`). The canonical vocabulary remains
exactly `{HUMAN_APPROVED, EXTERNAL_VERIFIED, STRUCTURALLY_OBSERVED, INFERRED}`,
authorizing = `{HUMAN_APPROVED, EXTERNAL_VERIFIED}`. No new vocabulary or tiers.

## 4. Legacy evidence mapping

`normalize_authority_tier` (B5.5, unchanged) maps every stored value:
`human_curated`/`human_approved`/`reviewed`/`editorial` → `HUMAN_APPROVED`;
`externally_listed`/`external_verified` → `EXTERNAL_VERIFIED`;
`structurally_observed` → `STRUCTURALLY_OBSERVED`;
`llm_proposed`/`bootstrap`/`unobserved`/`unknown`/`inferred`/`hypothesis`/missing/unrecognised → `INFERRED`.

The explicit, tested inverse `to_legacy_evidence` writes the representative
value production code actually uses (`human_curated`, `externally_listed`,
`structurally_observed`, `llm_proposed`) and round-trips canonically for every
tier.

## 5. Conflict handling

`normalize_group_authority(group)` returns a diagnostic record
(`diagnostic`, both stored values, both canonical interpretations, `conflict`,
`authorizing`) without mutating the group:

| Situation | Diagnostic | Authorizing? |
|---|---|---|
| both present, canonically equal | `None` | per canonical tier |
| both present, canonically different | `AUTHORITY_CONFLICT` | **no (fail closed)** |
| `authority_tier` absent | `AUTHORITY_MISSING` | no |
| `authority_tier` unrecognised | `AUTHORITY_UNKNOWN` | no |

No precedence is invented: even a `human_curated` tier backed by
`structurally_observed` evidence is **not** authorizing while the conflict
stands. The B5 layer additionally fails the family closed
(`REASON_AUTHORITY_CONFLICT`), and B6 surfaces `AUTHORITY_CONFLICT` as the
headline submission reason. Diagnostics: `AUTHORITY_CONFLICT`,
`AUTHORITY_MISSING`, `AUTHORITY_UNKNOWN`.

## 6. B6 integration

`product_eligibility` semantics are unchanged (CONFIRMED + primary +
HUMAN_APPROVED/EXTERNAL_VERIFIED). B6.5 only (a) consumes the canonical field
via B5 (which now normalizes groups built directly, not just loader output),
and (b) reports conflicts first so they are never buried under
`coverage_not_confirmed`. The flag-gated flow, fail-closed missing-evaluation
behavior, and the OFF path are untouched.

## 7. Legacy compatibility

With the flag OFF the legacy gate still reads `evidence ∈
{structurally_observed, externally_listed}`. `human_curated` is still **not**
legacy-authoritative and `structurally_observed` still **is** — pinned by tests.
The loader's new `authority_normalization` annotation is additive and read by
nothing in the legacy path.

## 8. Native corpus regeneration

The live database **was reachable**, so the 46 corpus was regenerated from the
actual source data: submissions from the historical artifact, ground truth from
live `problem_ground_truth` rows via the production loader
(`_load_ground_truth`), preserving `authority_tier`, `evidence`, `provenance`,
`version`, `family_relation`, `alternative_group_id` and the new
`authority_normalization` record where actually present. Written to
`results/db_batch3/submission_eval_results_NATIVE.json` with
`"provenance": "NATIVE"`. The runner reuses a cached native artifact only if it
is verifiably native; otherwise it regenerates.

**Provenance rules enforced:** no authority is attached at measurement time and
called native; a row with no authority metadata stays `INFERRED`/missing
(7 native groups carry no tier, 5 problems have no stored groups and fall back
to the CSV split with their real `evidence` value); the enriched corpus is kept
**only** as a labelled comparison (`"native": false`,
"measurement-time" in the note).

## 9. ONE_OF handling

B5.5/B6 rules unchanged and explicit-only. Native loader marking now also
produces the LC3236 alternative split (`group_0_alt0`/`group_0_alt1`), giving
**7 native ONE_OF groups** (db-49/51/194 + db-237/238/239/240). Inference from
identical/similar patterns, same problem or overlapping concepts remains
prohibited; **db-254 remains two independent requirements** (regression tests).

## 10. db-254 handling

Unchanged: different patterns, no explicit provenance → not marked, not merged,
2 independent logical requirements, not eligible (tests + measurement).

## 11. 46 native results

| Metric | Value |
|---|---|
| native authority tiers | `human_curated 32, llm_proposed 15, <missing> 7` |
| B3 coverage | `{CONFIRMED 23, CONTRADICTED 1, PROVISIONAL 10, UNRESOLVED 12}` |
| B4 selected | `{sliding_window 7, two_pointers_opposite 5, dp_bottom_up 3, binary_search 2, dfs_backtracking 2, dp_top_down 2, bfs 1, union_find 1, none 23}` |
| B5 aggregation | `NO_AUTHORITATIVE_FAMILY 46` |
| canonical authority | `HUMAN_APPROVED 28, INFERRED 18` |
| normalization conflicts | **32** (`AUTHORITY_CONFLICT`) |
| B6 eligible / blocked | **0 / 46** |
| ONE_OF groups / submissions | 7 / 7 |

The 32 conflicts are a **real pre-existing production inconsistency surfaced by
normalization**: CSV reconciliation writes `authority_tier = human_curated`
while the stored `evidence` remains `structurally_observed` (or `llm_proposed`).
Under the B6.5 fail-closed rule these families cannot authorize until the
Ground Truth is reconciled — exactly the "do not silently choose one" behavior
the batch required.

## 12. 46 enriched results (comparison only — NOT native)

| Metric | Value |
|---|---|
| authority (re-attached) | `human_curated 30, llm_proposed 5, unknown 16` |
| B5 aggregation | `ALL_FAMILIES_AUTHORITATIVE 20, NO_AUTHORITATIVE_FAMILY 26` |
| B6 eligible / blocked | 20 / 26 |
| conflicts | 0 (enrichment overwrites the conflicting field wholesale) |

## 13. 301 results

`INFERRED 301` → **0 eligible, 301 blocked**, coverage
`{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}`, 0 conflicts,
0 ONE_OF. Expected behavior holds: non-authoritative GT cannot create product
consequences.

## 14. Native vs enriched comparison

| Metric | Old native | Enriched | New native |
|---|---|---|---|
| authoritative families | 0 | 20 | **0** |
| eligible submissions | 0 | 20 | **0** |
| blocked submissions | 46 | 26 | **46** |
| ONE_OF requirements | 0 | 4 | **7** |
| authority conflicts | 0 | 0 | **32** |

**The previous 20/26 eligible result does NOT survive native provenance** —
exactly why the batch demanded the distinction. The enriched 20 depended on
wholesale re-attachment of a record-level tier that silently overwrote the
conflicting legacy `evidence`; native data exposes 32 conflicts and fails them
closed. Native provenance also reveals the true ONE_OF structure (7 groups, not
4) and the LC3236 alternative split.

## 15. Tests

39 new B6.5 tests: every B5.5 mapping (16 stored values), canonical round-trip,
evidence→authority normalization, authority→compatibility inverse, matching
pair, conflicting pair (both directions), missing, unknown, conflict finder,
loader annotation (stored + fallback paths), B6 canonical consumption + conflict
rejection + non-leakage, ONE_OF unchanged, db-254 unchanged, flag OFF + legacy
constants unchanged, native corpus retains authority, enriched clearly marked
non-native, 301 remains non-authoritative.

## 16. Regressions

| Suite | Result |
|---|---|
| B6.5 | **39 passed** |
| B1–B6 focused (B1 48, B2 65, B3 32, B4 28, B5 36, B5.5 58, B6 39) | **306 passed** (combined run: 345 with allowlist updates) |
| `pathforge/tests` (full) | **454 passed** |
| shadow | **810 passed** |
| experiments | **79 passed** |
| `src` | 605 passed, **1 pre-existing failure** (PrefixSumDetector, isolated) |

## 17. Changed files

* `pathforge/ast_analysis/authority_vocabulary.py` — `normalize_group_authority`,
  `find_normalization_conflicts`, `to_legacy_evidence`, diagnostics
  (`AUTHORITY_CONFLICT`/`MISSING`/`UNKNOWN`), field-name constants.
* `pathforge/ast_analysis/shadow/authority_gating.py` — per-group conflict
  normalization (loader-attached or computed), fail-closed family decision,
  `REASON_AUTHORITY_CONFLICT`.
* `pathforge/services/problem_resolver.py` — additive
  `authority_normalization` annotation on both loader paths.
* `pathforge/services/product_eligibility.py` — conflict reason surfaced first
  (no semantics change).
* `pathforge/tests/test_b6_5_authority_persistence.py` (new), two isolation
  allowlists extended.
* `experiments/.../runners/b6_5_authority_normalization_measure.py` (new),
  `results/b6_5_authority_normalization_measurement.json`,
  `results/db_batch3/submission_eval_results_NATIVE.json`.
* Tracked diff now: 8 files, +332/−26 (cumulative B2–B6.5).

## 18. Remaining ambiguities

1. **32 native conflicts need GT reconciliation** (CSV reconciliation writes
   `human_curated` over non-matching stored `evidence`). This is a data decision,
   deliberately *not* taken here.
2. **`<missing>` authority on 7 native groups** (problems 2 and 3236 stored
   groups predate the field) — stay `INFERRED` until relabelled.
3. **5 problems have no stored groups** and use the CSV-split fallback; their
   authority is the row's `validation_status`/`evidence`, not a group tier.
4. **Flag-scoped governance** (legacy AND B6, or B6 alone) remains a B7+ policy
   decision, untouched per instruction 14.
5. **Streak updates remain outside B6 gating** — recorded for a future policy
   decision; unchanged in B6.5.
6. **Native ONE_OF for LC3236** (`hash_lookup` OR `sequential_accumulation`)
   comes from the loader's alternative split; both alternatives are
   technique-only, so neither can be authoritative — no action needed, but the
   relation's interaction with technique-only families is worth reviewing in B7.

## 19. Explicit statement

**The legacy matcher was not replaced.** Legacy verdict/evidence/Elo/gap/
recommendation/streak semantics are unchanged with the flag OFF; the default
flag value is unchanged (OFF); no legacy authority fields were removed; no Elo,
gap or recommendation algorithm was modified; no new Ground Truth or ONE_OF
relationship was inferred; no destructive migration was performed.

---

**HARD STOP — B6.5 complete. B7 (legacy-vs-shadow verdict parity /
migration-readiness) has NOT started.**
