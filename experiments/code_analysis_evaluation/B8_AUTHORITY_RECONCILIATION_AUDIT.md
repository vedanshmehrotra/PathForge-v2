# B8 — Ground Truth Authority Reconciliation Audit

**Batch:** B8 (provenance-first GT authority reconciliation)
**Predecessor:** B7 — Legacy-vs-Shadow Verdict Parity / Migration Readiness
**Status:** COMPLETE — matcher replacement has NOT started; B6 remains OFF; no
production behavior changed.
**Date:** 2026-09-27

---

## 1. Objective

Turn the 32 ambiguous native GT authority conflicts isolated by B7 into
**explicitly sourced decisions or explicitly unresolved cases** — resolved only
through explicit provenance, never by picking the value that "looks more
trustworthy", never by automatically preferring `human_curated` over
`structurally_observed`, and never by preferring `authority_tier` over
`evidence` as a matter of policy.

## 2. Authority field semantics (`authority_tier`)

* **Semantics: Ground-Truth authority** — who/what established the expected
  solution family.
* **Stored-row writers:** `pathforge/scripts/seed_ground_truth.py`
  (`structurally_observed`, provenance `manual_verification`) and
  `ground_truth_builder._build_single_group` (`llm_proposed`, provenance
  `llm_ground_truth`).
* **Load-time writer:** `problem_resolver._load_ground_truth` CSV
  reconciliation overwrites the *emitted* `authority_tier` to
  `"human_curated"` when a curated CSV pattern exists — the stored row is not
  modified. **B8 change:** this overwrite is now skipped for groups whose
  provenance carries the `b8_authority_reconciliation` marker (explicit
  reconciled authority wins); the production **patterns** still come from the
  CSV (representation, not authority). Legacy fields (`evidence`, `patterns`)
  are untouched.
* **Readers:** shadow authority path (B5/B5.5/B6), B3 passthrough.

## 3. Evidence field semantics (`evidence`)

* **Semantics: legacy validation state, overloaded** — the validation state the
  GT row was written with; the legacy Elo reader
  (`EVIDENCE_K_CEILINGS`) additionally treats it as *implementation-evidence
  strength* ("how strongly the submitted implementation was observed"), and the
  legacy persistence gate (`evidence ∈ {structurally_observed,
  externally_listed}`) treats it as a verdict-authority signal.
* **Writers:** seed script and GT builder — always equal to the row's
  `authority_tier` at write time.
* **Readers:** `persistence.run_persistence` (legacy verdict gate), `elo_engine`
  (implementation-evidence strength), loader fallback when `authority_tier` is
  absent.

**B8 §4/§5 answer:** `evidence` is NOT a second GT-authority field. The 32 B7
conflicts are **field-semantic collisions created at load time**, not incorrect
GT and not two disagreeing human decisions: the stored rows were internally
consistent (`authority_tier == evidence` on every seeded row); the loader then
overwrote only the emitted tier. B8 therefore does **not** collapse the fields:
`authority_tier` remains the canonical GT-authority representation, `evidence`
remains the legacy compatibility field (per B6.5), and both semantics are
documented as machine-readable constants (`AUTHORITY_TIER_SEMANTICS`,
`EVIDENCE_SEMANTICS` in `pathforge/services/authority_reconciliation.py`,
embedded in the candidates artifact).

## 4. Conflict inventory (all 32 individually accounted)

Artifact: `experiments/code_analysis_evaluation/results/b8_authority_reconciliation_candidates_PREREC.json`
(pre-reconciliation inventory, preserved) — one record per conflicted group
with problem_id, group_id, concepts, both canonical interpretations,
provenance, version, family_relation, alternative_group_id, legacy/shadow/B6
behavior, and the source of each field.

* **32 group-level conflicts** across **20 problems**:
  2, 3, 11, 15, 21, 35, 46, 62, 70, 78, 102, 125, 141, 200, 209, 322, 424,
  438, 496, 704.

## 5. Conflict classifications (exactly one status each)

| Status | Count | Mechanism |
|---|---|---|
| `RECONCILE_STRUCTURALLY_OBSERVED` | 25 | CSV-reconciliation collision: stored row records `authority_tier == evidence == structurally_observed` with documented writer provenance (`manual_verification`) / `validation_status`; the emitted tier was overwritten to `human_curated` at load time. Resolution **restores the stored authority explicitly**. |
| `RECONCILE_INFERRED` | 4 | Same collision mechanism; the stored row records `llm_proposed` (provenance `llm_ground_truth`). Restored to INFERRED — **not upgraded** because the implementation looks convincing (§11 respected). |
| `NEEDS_HUMAN_REVIEW` | 3 | Problem 2 (`db-48/50/135`): CSV-fallback groups with **no stored `authority_tier` at all** (`evidence=llm_proposed`, no tier, provenance only `csv_curated_override`). Nothing to restore → fail-closed, review records emitted. |

Human-review records are in the candidates artifact under
`human_review_records` in exactly the §7 shape (`required_reviewer: "human"`,
`status: "NEEDS_HUMAN_REVIEW"`); they were **not** auto-activated.

No bulk rule beyond the documented collision mechanism was applied; each
record was classified individually from its own provenance (classification
runs per record in `classify_conflict()`).

## 6. Provenance sources used

Only records that actually exist:

* stored `problem_ground_truth.solution_groups` rows (tier, evidence,
  provenance list, version);
* stored `problem_ground_truth.validation_status`;
* GT writer provenance: `manual_verification` (seed script — "manually
  verified"), `llm_ground_truth` (GT builder);
* CSV reconciliation provenance (`csv_curated`, `csv_curated_override`) —
  treated as a **pattern label**, never as human GT approval.

Nothing invented: no human approval, no external verification, no
implementation-evidence promotion.

## 7. Automatically resolvable vs human-review vs unresolved

| Outcome | Count | Meaning |
|---|---|---|
| **Resolved authority** | 0 | No conflict resolved to HUMAN_APPROVED / EXTERNAL_VERIFIED (the GT genuinely lacks such provenance). |
| **Resolved non-authority** | 29 | 25 → STRUCTURALLY_OBSERVED, 4 → INFERRED (explicit stored provenance). |
| **Unresolved** | 3 | Problem 2's tier-less CSV-fallback groups — remain **fail-closed**. |

## 8. Changes to GT (versioned, never silent)

29 stored groups updated via **versioned GT updates** on the live DB:

* `authority_tier` → restored stored value (`structurally_observed` × 17,
  `llm_proposed` × 4, plus 8 sibling `_alt` variants of the same rows across
  19 problems — 21 distinct stored group records);
* `version` bumped to `2` (`RECONCILIATION_VERSION`);
* `provenance += ["b8_authority_reconciliation", "csv_reconciliation_field_collision"]`;
* `reconciled_from` record preserves the previous tier/evidence/version;
* `evidence` **never modified**; no rows deleted; no labels relabeled beyond
  the explicit restoration;
* `authority_normalization` annotation refreshed (clean pair afterwards).

Sequence followed exactly: live DB → B8 extraction → reconciliation artifact →
explicit decision → versioned GT update. The candidates artifact was written
**before** any modification and preserved on re-run.

## 9. Native corpus regeneration

`results/db_batch3/submission_eval_results_NATIVE.json` regenerated from the
live DB via the B6.5 native builder — `provenance: "NATIVE"`, no
measurement-time enrichment, preserving `authority_tier`, `evidence`,
`provenance`, `version`, `family_relation`, `alternative_group_id`,
`authority_normalization`. 0 serialization round-trip failures.

Post-reconciliation native state: **3 residual conflicts** (problem 2), 37
conflict-free families: STRUCTURALLY_OBSERVED 17, INFERRED 20.

## 10. Before/after B7 parity (native 46)

| Category | Before | After |
|---|---|---|
| P1 EXACT_PARITY | 15 | **17** |
| P2 LEGACY_AUTHORITATIVE_SHADOW_BLOCKED | 0 | **21** |
| P3 LEGACY_BLOCKED_SHADOW_ELIGIBLE | 0 | 0 |
| P4 LEGACY_MATCH_SHADOW_UNRESOLVED | 3 | **5** (db-11, db-18, db-39, db-139, db-252) |
| P5/P6/P8/P9/P10 | 0 | 0 |
| **P7 AUTHORITY_CONFLICT** | **28** | **3** |

P7 did not disappear (§13 respected): the 3 remaining are the genuinely
tier-less problem-2 rows. The 21 formerly-conflicted legacy-authoritative
submissions moved to **P2** — the documented legacy-vs-canonical policy
difference (legacy trusts `structurally_observed` evidence; the canonical gate
authorizes only HUMAN_APPROVED/EXTERNAL_VERIFIED). These are **not** shadow
failures, false positives, or unresolved conflicts — they are the expected
policy divergence that B6's flag-gated design exists to manage. 301 corpus:
unchanged (0 eligible, 0 conflicts, 189 P1 + 53 P4 + 59 P9). Enriched arm:
recomputed as a labelled NON-NATIVE comparison only.

## 11. Before/after B6 eligibility (measurement only)

| Metric | Before | After |
|---|---|---|
| B6 eligible (native 46) | 0 | **0** |
| B6 blocked | 46 | 46 |
| Flag state | OFF (`<unset>`) | OFF (`<unset>`) |

0 → 0 is the correct outcome: the reconciled authorities are
STRUCTURALLY_OBSERVED/INFERRED, which must never authorize scoring (§11 of the
brief). No production consequence changed; the flag was never enabled.

## 12. Human-approved coverage (§18 answered)

Post-reconciliation conflict-free family tiers: **HUMAN_APPROVED 0,
EXTERNAL_VERIFIED 0, STRUCTURALLY_OBSERVED 17, INFERRED 20.**

**Diagnosis: the GT genuinely lacks human-approved provenance.** The seed
script wrote `structurally_observed` (its "manually verified" claim concerned
the *pattern labels*, and was recorded as implementation evidence, not GT
authority); `manual_verification` provenance never denoted human approval of
the expected solution. This is not a metadata inconsistency — human approval
would have to be **newly recorded** (with a reviewer and a decision), which B8
must not fabricate. B7's "0 conflict-free HUMAN_APPROVED families" is therefore
a true statement about the corpus, not an artifact of stored inconsistency.

## 13. LC3236 status (§16 — recorded, not solved)

The LC3236 alternative split remains
`hash_lookup OR sequential_accumulation`, both technique-level
(`conclusion_eligible=False` in the B1 registry). Neither was promoted to a
strategy; the ONE_OF group remains explicit-only and technique-only. This
remains a separate architecture decision (as flagged in B5.5/B7).

## 14. P4 status (§17 — investigated, not patched)

All 5 P4 cases require **only technique-level concepts**:

| Case | Required concept | Class | conclusion_eligible |
|---|---|---|---|
| db-11, db-39 (problem 1) | `hash_lookup` | TECHNIQUE rank 2, IDENTIFYING | False |
| db-18 (problem 628) | `candidate_selection` | TECHNIQUE rank 1, IDENTIFYING | False |
| db-139, db-252 (141/21) | `forward_pointer_advance` | TECHNIQUE rank 1, COMPONENT | False |

Classification: **legitimate unresolved implementation + missing strategy
vocabulary** for these techniques. Legacy recognizes the pattern (the stored
pattern maps 1:1 to the technique); the shadow correctly declines to confirm a
family whose only required concept is not conclusion-eligible (B3 gate working
as designed — db-18/db-139/db-252 additionally have zero stored tier). B3/B4
were NOT modified. Options (future decision): add conclusion-eligible
strategies for these technique families, or relabel the GT — both out of B8
scope. db-11/db-39 moved P4 3→5 relative to B7 only because their P7 conflict
was resolved (they were previously counted as conflicts, not P4).

## 15. Tests

`pathforge/tests/test_b8_authority_reconciliation.py` — **45 tests**, covering:
all 32 conflicts surfaced with every required field; one status each; no
silent resolution (every resolution carries a provenance-backed reason);
`human_curated` mapping unchanged; no new tiers; `llm_proposed` stays INFERRED;
missing/unknown/garbage stay non-authoritative; explicit human approval and
external verification can authorize; conflicting pairs still fail closed;
`evidence`/`authority_tier` semantics documented; versioned update writes
provenance+version+`reconciled_from`; NEEDS_HUMAN_REVIEW never writes; native
provenance survives serialization round-trip; NATIVE/ENRICHED labels cannot
collide; db-254 independent; ONE_OF explicit-only; LC3236 techniques not
promoted; B6 flag OFF; flag-OFF gating = legacy; reconciliation module/runner
never invoke Elo/gap/recommendation engines (code-level scan); B7 before/after
recorded; legacy verdict rule untouched.

## 16. Regressions

| Suite | Result |
|---|---|
| B1–B8 focused (registry/tri-state/coverage/strategy/authority/normalization/B6/B6.5/B7/B8) | 412 ✅ |
| `pathforge/tests` (full) | 521 ✅ |
| shadow suite (`pathforge/ast_analysis`) | 810 ✅ |
| experiments (gt_poc + gt_poc_v2) | 79 ✅ |
| `src` | 605/606 (1 pre-existing `TestPrefixSumDetector::test_detected_product_except_self`, isolated per brief) |

Two pre-existing isolation guards were updated for the new authorized consumer:
the registry-referer allowlist (B8 test file) and the
family-coverage production-isolation allowlist (`authority_reconciliation.py` —
a metadata service that never runs analysis).

## 17. Remaining policy decisions (not taken here)

1. The 3 problem-2 rows still need a human decision (review records ready).
2. Whether `manual_verification` should henceforth be recorded as a
   HUMAN_APPROVED provenance marker for *newly reviewed* GT (a recording-workflow
   decision, not a retroactive relabel).
3. P2 policy: whether the legacy evidence gate or the canonical gate governs
   production (B6's flag question — unchanged, OFF).
4. Technique-only families (LC3236, P4's db-11/db-18/db-39 class): promote,
   relabel, or leave unresolved.
5. `evidence` eventually converging into `authority_tier` + a separate
   implementation-evidence field (B6.5 left both; B8 documented the overloading).

## 18. Files changed

* **New:** `pathforge/services/authority_reconciliation.py`,
  `pathforge/tests/test_b8_authority_reconciliation.py`,
  `experiments/code_analysis_evaluation/runners/b8_authority_reconciliation.py`,
  `results/b8_authority_reconciliation_candidates_PREREC.json`,
  `results/b8_authority_reconciliation_candidates.json`,
  `results/b8_reconciliation_result.json` (+ `_PREREC.json`),
  this audit.
* **Modified:** `pathforge/services/problem_resolver.py` (B8 guard: reconciled
  authority survives load-time CSV reconciliation; patterns still CSV-driven),
  two isolation-test allowlists, regenerated
  `results/db_batch3/submission_eval_results_NATIVE.json` and the B7/B6.5
  measurement artifacts.
* **DB:** 29 versioned GT group updates (19 problems) as described in §8.

## 19. Explicit statements

* The legacy matcher was **not replaced, modified, or disabled**.
* `SHADOW_AUTHORITY_PRODUCT_GATING` remains **OFF**; the flag-OFF path is
  byte-identical to pre-B8 behavior.
* ELO / gap / recommendation engines were **never invoked** by reconciliation
  (enforced by tests).
* No authority was invented; no human approval inferred; no new tiers; no new
  ONE_OF; db-254 untouched.

## 20. HARD STOP

B8 is complete. Matcher replacement has NOT started. The legacy-vs-shadow
governance decision has NOT been made. B6 has NOT been enabled. Production
behavior has NOT changed. The shadow pipeline remains **not
production-authoritative**.
