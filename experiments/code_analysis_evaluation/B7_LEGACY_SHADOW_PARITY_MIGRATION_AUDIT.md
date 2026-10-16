# B7 — Legacy-vs-Shadow Verdict Parity / Migration Readiness: Audit

**Batch:** B7 — observational parity / migration-readiness evidence
**Implementation:** `pathforge/services/legacy_shadow_parity.py` (new, observational)
**Tests:** `pathforge/tests/test_b7_legacy_shadow_parity.py` (22)
**Measurement:** `experiments/.../runners/b7_parity_measure.py` → `results/b7_parity_measurement.json`
**Baseline:** `results/b7_baseline_tests.txt` (frozen pre-B7: 454 + 810 + 79 passed; `src` 605/606 pre-existing; flag OFF; legacy constants `{externally_listed, structurally_observed}` / `{editorial, externally_listed, structurally_observed}`)

> **B7 replaces nothing and decides nothing.** The legacy matcher is intact, the
> B6 flag remains OFF, no consequence was executed, and the 32 authority
> conflicts remain unresolved. B7 produces the evidence required to decide what
> must happen before any replacement.

---

## 1. Objective

Answer: *if the shadow architecture were eventually made authoritative, where
would its decisions differ from the legacy system, and why?* — at multiple
semantic levels, with every disagreement categorized (not reduced to
`legacy == shadow`).

## 2. Baseline (frozen before any B7 change)

| Suite | Result |
|---|---|
| `pathforge/tests` | 454 passed |
| shadow | 810 passed |
| experiments | 79 passed |
| `src` | 605 passed / 1 pre-existing failure (PrefixSumDetector, unrelated) |
| B6 flag | OFF (`<unset>`) |
| legacy `_AUTHORITATIVE_STATES` | `{structurally_observed, externally_listed}` |
| legacy `_AUTHORITATIVE_TIERS` | `{editorial, externally_listed, structurally_observed}` |

Post-B7 rerun (§17) matches the baseline: no production behavior changed.

## 3. Legacy pipeline (captured without reinterpretation)

`run_analysis` (AST engine → `MatchingEngine.match`) produces
`match_result ∈ {FULL_MATCH, PARTIAL_MATCH, NO_MATCH, NO_GROUND_TRUTH}`,
`matched_groups` (indices), `unmatched_patterns`. Product consequence
eligibility in production is **evidence-based**:
`evidence ∈ {structurally_observed, externally_listed}` → `verdict_type =
"authoritative"` → Elo/gaps/recommendations. B7 records exactly this rule
(`legacy_authoritative`), including the fact that `human_curated` is *not*
legacy-authoritative while `structurally_observed` *is*.

## 4. Shadow pipeline (captured independently)

`run_shadow_analysis` → B2 tri-state counts → B3 coverage (`aggregate_state`)
→ B4 primary strategy → B5/B5.5 canonical authority (+ per-group normalization
diagnostic) → B6 eligibility. Canonical fields only; no new taxonomy.

## 5. Comparison model

`LegacyShadowParityRecord` = `submission_id`, `problem_id`, `title`, **legacy**
(matched, verdict_type, matched_group_id, evidence, expected_pattern,
matched/unmatched patterns), **shadow** (coverage_state, primary_strategy,
authority_tier, authority_diagnostic, logical_requirements,
authoritative_requirements, b6_eligible, b6_reasons, B2 counts), **comparison**
(parity_category, divergence_reason, migration_status), **consequence
simulation** (six booleans, `simulated_only: true`), `technique_only_one_of`,
`one_of_group_ids`. Neither input is mutated (deep-copied; asserted by tests).

## 6. Parity categories

P1 exact parity · P2 legacy-authoritative/shadow-blocked (sub-reasoned) ·
P3 legacy-blocked/shadow-eligible · P4 legacy-match/shadow-unresolved ·
P5 legacy-no-match/shadow-confirmed · P6 legacy-match/shadow-contradicted ·
P7 authority-conflict · P8 representation-difference · P9 no-comparable-GT ·
P10 error. Classification order: errors → GT-insufficiency → **P7 before any
verdict comparison** → consequence-dimension comparison → verdict-layer
comparison.

## 7. Authority-conflict treatment

Conflicts are classified **P7** and never counted as shadow algorithm failures,
false negatives, or disagreement. Sub-reason `authority_conflict` inside P2 is
defensive only. The B6.5 rule stands: conflict → fail closed until explicit GT
reconciliation. No precedence was invented; `human_curated` was not chosen
merely because it looks more trustworthy.

## 8. ONE_OF treatment

ONE_OF sets are compared as **logical requirements**
(`alternative_group:<id>`), never as naive family counts: an unresolved sibling
does not create a disagreement when the requirement is satisfied (test_11).
`db-254` remains two independent requirements (test_12). Technique-only
ONE_OF (LC3236: `hash_lookup` OR `sequential_accumulation`) is recorded
(`technique_only_one_of=True`) and **neither technique is promoted** —
`primary_strategy` stays `None` (test_13). Native corpus: 7 ONE_OF groups
across db-49/51/194/237/238/239/240.

## 9. Native 46 methodology

Primary dataset: `submission_eval_results_NATIVE.json` (B6.5; GT from live
`problem_ground_truth` rows via the production loader). Legacy results were
computed observationally per submission with the production `run_analysis` on
the native groups. The enriched corpus was run **only** as a clearly-labelled
secondary comparison. 301 is the safety corpus. No result is called "accuracy".

## 10. 46 results (native — primary)

| Metric | Value |
|---|---|
| total submissions | 46 |
| legacy authoritative / blocked | **21 / 25** (evidence-based) |
| legacy matched | 26 (22 FULL, 4 PARTIAL) |
| shadow coverage | `CONFIRMED 23, CONTRADICTED 1, PROVISIONAL 10, UNRESOLVED 12` |
| B6 eligible / blocked | **0 / 46 (0.0%)** |
| P1 exact parity | **15 (32.6%)** |
| P4 legacy-match/shadow-unresolved | 3 (6.5%) — `db-11, db-18, db-39` |
| **P7 authority conflict** | **28 (60.9%)** |
| P2 / P3 / P5 / P6 / P8 / P9 / P10 | 0 |
| migration statuses | `READY_FOR_SHADOW 15, BLOCKED_BY_AUTHORITY 28, BLOCKED_BY_SHADOW_COVERAGE 3` |
| consequence simulation (legacy/shadow) | ELO 21/0 · GAP 21/0 · REC 21/0 |

## 11. 301 results (safety corpus)

| Metric | Value |
|---|---|
| B6 eligible / blocked | **0 / 301** (GT llm_proposed → INFERRED) |
| P1 exact parity | 189 (62.8%) |
| P4 legacy-match/shadow-unresolved | 53 (17.6%) |
| P9 no-comparable-GT | 59 (19.6%) — the `UNMAPPED_LABEL` population |
| P7 conflicts | 0 |
| consequence simulation | ELO 0/0 · GAP 0/0 · REC 0/0 |

Not used to estimate authoritative migration readiness. Useful for shadow
classification and authority-safety regression: zero confirmations escaped the
canonical gate.

## 12. Enriched 46 (secondary, NON-NATIVE / MEASUREMENT-TIME ENRICHED)

| Metric | Value |
|---|---|
| B6 eligible / blocked | 20 / 26 (43.5%) |
| P1 | 10 (21.7%) |
| P3 legacy-blocked/shadow-eligible | 20 (43.5%) — `db-20, db-35, db-137, db-190, …` |
| P4 | 5 (10.9%) — `db-48, db-50, db-135, db-139, db-252` |
| P9 | 11 (23.9%) — `db-11, db-18, db-33, db-36, db-37, db-39, …` |
| consequence simulation | ELO 0/20 · GAP 0/20 · REC 0/20 |

Kept for comparison only. Its 20 eligible depend on measurement-time authority
attachment that overwrites the conflicting `evidence`; the native dataset is the
honest one.

## 13. Disagreement taxonomy

| Category | Count (native) | % | Examples |
|---|---|---|---|
| P1 exact parity | 15 | 32.6% | `db-21…` (consequence-identical blocks) |
| P2 legacy-auth/shadow-blocked | 0 | 0% | — (subsumed by P7 natively) |
| P3 legacy-blocked/shadow-eligible | 0 | 0% | — (enriched: 20) |
| P4 legacy-match/shadow-unresolved | 3 | 6.5% | `db-11, db-18, db-39` |
| P5 legacy-no-match/shadow-confirmed | 0 | 0% | — |
| P6 legacy-match/shadow-contradicted | 0 | 0% | — |
| **P7 authority conflict** | **28** | **60.9%** | `db-20, db-35, db-48, db-50, db-135, db-137, db-139, db-190, …` |
| P8 representation difference | 0 | 0% | — |
| P9 no comparable GT | 0 | 0% | — (enriched: 11; 301: 59) |
| P10 error | 0 | 0% | — |

## 14. Concrete disagreement examples

* **P7 (28):** `human_curated` tier over `structurally_observed`/`llm_proposed`
  evidence — the CSV-reconciliation inconsistency B6.5 surfaced. Legacy
  authorizes (evidence-based); shadow confirms but B6 fails closed. **Provenance
  disagreement, not an algorithmic failure.**
* **P4 (3):** `db-11/18/39` — problems with no stored solution groups; the CSV
  fallback produced an unmatchable legacy expectation while the shadow
  `PROVISIONAL` shows the real evidence state (LC1: `hash_lookup` PRESENT, no
  conclusion-eligible strategy).

## 15. Product-consequence simulation

`migration_consequence_comparison` (native 46): legacy would allow ELO for 21
submissions; shadow/B6 would allow **0**. GAP and recommendation identical. All
values are simulated booleans derived from the gate rules — **no Elo, gap, or
recommendation engine was invoked, no persistence occurred** (guarded by a
source-scan test over the parity module).

## 16. Migration-status distribution (native 46)

`READY_FOR_SHADOW 15 · BLOCKED_BY_AUTHORITY 28 · BLOCKED_BY_SHADOW_COVERAGE 3 ·
BLOCKED_BY_GT 0 · BLOCKED_BY_PARITY 0 · REPRESENTATION_ONLY 0 · ERROR 0`.
Deliberately **no single overall readiness score** — the distribution is the
diagnosis.

## 17. GT reconciliation required (32 conflicts across 28+ submissions)

Rows (problem_id / group / authority_tier / evidence / canonical readings /
legacy / shadow / B6) are itemized in
`results/b7_parity_measurement.json → native_46.authority_conflict_cases`
(e.g. `db-20: HUMAN_APPROVED over structurally_observed`). Every one is a
**data problem, not a shadow failure**. They must not contaminate algorithmic
parity analysis and were isolated as P7. Not resolved here by design.

## 18. Tests

22 B7 tests covering: all implemented categories (P1, P2+sub-reasons, P3, P4,
P5, P6, P7, P9, P10), authority-conflict isolation, missing authority, ONE_OF
logical comparison, db-254 independence, technique-only ONE_OF, purity (neither
result mutated), consequence-execution prohibition (source scan: no
`compute_updates`/`persist_elos`/`compute_signals`/`persist_signals`/
`get_recommendation`/`_log_recommendation`/`_update_user_streak`), flag OFF,
legacy constants unchanged, native-corpus integration.

## 19. Regressions (post-B7)

| Suite | Result | Baseline |
|---|---|---|
| `pathforge/tests` | **476 passed** | 454 (+22 B7) |
| shadow | **810 passed** | 810 |
| experiments | **79 passed** | 79 |
| `src` | 605/606 (1 pre-existing, isolated) | same |
| B6 flag | **OFF** | OFF |

One isolation allowlist gained two authorized entries
(`product_eligibility.py`, `legacy_shadow_parity.py`) — both B6/B7 consumers
that read coverage *results* without executing analysis.

## 20. Remaining architecture gaps

1. **Authority provenance** — the dominant blocker (60.9% of the native corpus).
   Until the 32 conflicts are reconciled, canonical-authoritative migration is
   impossible for those problems.
2. **Technique-only families** (LC3236) can never conclude under the current
   registry; a migration decision needs either GT relabeling or vocabulary work.
3. **No-comparable-GT population** (59 in the 301 corpus) — unmapped legacy
   labels with no shadow equivalent.
4. **Legacy-only patterns** — `prefix_sum` (db-190's unmatched pattern) has no
   conclusion-eligible shadow strategy; the shadow verdict layer is stricter.
5. **B6-vs-legacy gate governance** (AND vs B6-alone) remains undecided by
   design.

## 21. Migration prerequisites (evidence, not a score)

Before any replacement could be considered: (a) explicit GT authority
reconciliation for the 32 conflicts; (b) a policy decision on the legacy/
canonical gate relationship; (c) technique-only family strategy or relabeling;
(d) native-corpus legacy results regenerated alongside authority (the historical
artifact predates native GT storage); (e) a larger human-approved corpus than
the current 0 `HUMAN_APPROVED`-without-conflict families.

## 22. Answers to the migration-readiness questions

* Legacy decisions reproduced by shadow (consequence dimension): **15/21
  legacy-authoritative cases agree with B6's block on non-eligible evidence**;
  28 more agree *in effect* but are blocked as P7 conflicts, not algorithmic
  mismatches.
* Legacy decisions not currently reproducible: **0 algorithmic** — every
  non-parity case is authority (28) or GT-coverage (3).
* Purely authority-related disagreements: **28 (60.9%)**.
* GT/representation-related: 0 P8 + 3 P4 (GT-fallback shape).
* Genuine algorithmic differences: **0** in the consequence dimension (P2–P6
  all zero natively; P4's 3 are GT-representation, not detection).
* Shadow confirmations with authoritative GT: 0 eligible / 23 CONFIRMED (all
  blocked by conflict or inference).
* Shadow confirmations remaining non-authoritative: 23.
* Largest unresolved population: `two_pointers_opposite`/`sliding_window`
  families under P7.
* Legacy patterns with no shadow equivalent: `prefix_sum` (technique-tier, not
  conclusion-eligible).
* Shadow strategies with no legacy equivalent: none observed in the native 46.
* ONE_OF-caused disagreements: **0** (logical comparison works; 7 groups).
* B4-caused disagreements: 0 (P2 `no_primary_strategy` = 0 natively).
* B3-caused disagreements: 0 beyond the 3 P4 coverage gaps.
* B2-contradiction-caused: 0 (1 CONTRADICTED family, legacy agrees).
* Missing-vocabulary-caused: the 3 P4 cases (GT fallback, not detector gaps).

## 23. Files changed

* **New:** `pathforge/services/legacy_shadow_parity.py`,
  `pathforge/tests/test_b7_legacy_shadow_parity.py`,
  `experiments/.../runners/b7_parity_measure.py`,
  `results/b7_parity_measurement.json`,
  `results/b7_baseline_tests.txt`, this audit.
* **Modified (allowlist only):** `pathforge/tests/test_family_coverage.py`.
* Legacy matcher, B2–B6 code, Elo/gap/recommendation engines, flag default:
  **unchanged**.

## 24. Explicit non-migration statement

**The legacy matcher was not replaced, modified, or disabled. No production
migration decision was made. `SHADOW_AUTHORITY_PRODUCT_GATING` remains OFF. No
Elo, gap, recommendation, or streak consequence was executed by B7. The 32
authority conflicts remain unresolved and fail closed. The shadow architecture
is not production-authoritative.**

---

**HARD STOP — B7 complete. Legacy-matcher replacement has NOT started.**
