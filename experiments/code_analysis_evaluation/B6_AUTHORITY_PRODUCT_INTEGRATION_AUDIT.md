# B6 — Controlled Authority → Product Verdict Integration: Audit

**Batch:** B6 — controlled integration of the canonical shadow authority model into product verdict/scoring eligibility
**Implementation:** `pathforge/services/product_eligibility.py` (new), `pathforge/services/persistence.py` (+56 additive lines), `config.py` (+8)
**Tests:** `pathforge/tests/test_b6_product_eligibility.py` (39)
**Measurement:** `experiments/.../runners/b6_product_integration_measure.py` → `results/b6_product_integration_measurement.json`

> **Legacy behavior remains the default.** The feature flag
> `SHADOW_AUTHORITY_PRODUCT_GATING` defaults to **OFF**; with it OFF, nothing in
> the product flow changed. B6 does **not** replace the legacy matcher. The
> shadow pipeline is **not** production-authoritative by default.

---

## 1. Files inspected

* `pathforge/services/persistence.py` — the product-consequence boundary
  (`_AUTHORITATIVE_STATES`, `verdict_type`, Elo/gap/recommendation branch).
* `pathforge/ast_analysis/shadow/matching.py` — the old shadow matcher
  (`_AUTHORITATIVE_TIERS`, `evaluate_solution_groups`).
* `pathforge/api/routes/analyze.py` — the `/analyze` orchestration: legacy
  `run_analysis` → `run_persistence` (product consequences) → shadow analysis
  (observational) → `persist_shadow_analysis`.
* `pathforge/api/services/analysis.py` — the legacy analysis entry point.
* `pathforge/gap_signal_engine.py`, `pathforge/elo_engine.py`,
  `pathforge/recommender.py` — the consequence engines (unchanged).
* `config.py` — the existing environment configuration pattern.
* B1–B5.5 implementations and audits.

## 2. Current legacy product flow (traced)

```
/analyze (analyze.py)
  ├─ resolve_problem() → groups (GT solution groups)
  ├─ run_analysis() → ast_output + match_result          [LEGACY matcher]
  ├─ run_persistence()                                   [PRODUCT CONSEQUENCES]
  │    ├─ expected_pattern / matched_group_evidence from matched group
  │    ├─ verdict_type = "authoritative" iff evidence ∈ _AUTHORITATIVE_STATES
  │    │                = {structurally_observed, externally_listed}
  │    ├─ if verdict_type == "authoritative":
  │    │     update_topic_profile → gap_engine.compute_signals+persist
  │    │     → elo_engine.compute_updates+persist → get_recommendation+log
  │    └─ (else: submission stored, NO consequences)   [cold-start suppression]
  └─ shadow analysis (observational, persisted to the submission row, never
       affects the response beyond its own additive fields)
```

Key legacy facts:

* the legacy gate is **evidence-based**, not tier-based: `evidence ∈
  {structurally_observed, externally_listed}` → authoritative;
* `human_curated` (the most human-trusted label) is **not** in that set, while
  `structurally_observed` (analyzer evidence about the submission) **is** — the
  exact conflict B5.5 recorded;
* gaps: `gap_identified = len(unmatched) > 0` is stored for every submission,
  but the **gap engine** (signals, persistence) only runs on the authoritative
  branch;
* streak updates run unconditionally (unchanged by B6);
* the shadow result is computed and persisted observationally, never consulted
  for consequences.

**The legacy policy is not assumed correct.** B6 preserves it verbatim when the
flag is OFF, and exposes the canonical alternative behind the flag.

## 3. B6 architecture

```
shadow evidence → B2 → B3 → B4 → B5/B5.5 canonical authority
                                      ↓
                     B6 product_eligibility (single explicit decision)
                                      ↓  [only when flag ON]
                     ELO / gaps / recommendations
```

New module `pathforge/services/product_eligibility.py`:

* `flag_enabled()` — the migration switch (default **OFF**);
* `product_eligibility(authority_report)` — the one eligibility decision;
* `evaluate_submission(code, groups)` — runs the shadow path end-to-end and
  produces `shadow_result` / `authority` / `eligibility` as **separate**
  structures;
* `gating_decision(...)` — the boundary decision consumed by persistence;
* `LegacyShadowComparison` + `classify_comparison` — migration evidence.

`persistence.run_persistence` gained one additive block: when (and only when)
the flag is ON, it evaluates the B6 gate; if the gate says `allow_shadow=False`,
`is_authoritative` becomes False **for that decision** so no Elo/gap/
recommendation consequence runs. The legacy `verdict_type` and all legacy fields
are computed and stored exactly as before.

## 4. Canonical authority flow

B6 uses **only** the B5.5 canonical vocabulary
(`pathforge.ast_analysis.authority_vocabulary`):

* authorizing tiers: `{HUMAN_APPROVED, EXTERNAL_VERIFIED}`;
* `STRUCTURALLY_OBSERVED` / `INFERRED` / missing / unrecognised → never
  authorize;
* no second authority vocabulary exists in B6 code (guarded by a test that
  asserts no stored-value literal is restated in the module);
* the legacy production constants are recorded in the canonical module and
  pinned by tests — B6 does not silently change them.

## 5. Product eligibility rule

A logical requirement (independent family, or an explicit `ONE_OF` group) is
**eligible** iff:

1. B3 coverage is `CONFIRMED`, **and**
2. B4 selected a primary strategy, **and**
3. canonical authority ∈ `{HUMAN_APPROVED, EXTERNAL_VERIFIED}`.

The submission is eligible iff **every** logical requirement is eligible.
Ineligible states, each with an explicit reason code: `coverage_not_confirmed`
(PROVISIONAL / UNRESOLVED / CONTRADICTED / NO_GROUND_TRUTH / UNMATCHABLE),
`no_primary_strategy`, `structural_observation_only`, `inferred_authority`,
`missing_authority`, `no_authoritative_alternative`, `no_authority_report`.
`PROVISIONAL` is never treated as confirmed. A structurally observed
implementation can never become an authoritative expected strategy.

## 6. ONE_OF implementation

B5.5 semantics, explicit metadata only (`family_relation="ONE_OF"` +
`alternative_group_id`):

* one authoritative alternative → the logical requirement is satisfied;
* an unresolved sibling does **not** downgrade it to mixed;
* all alternatives non-authoritative → `no_authoritative_alternative`, blocked;
* multiple authoritative alternatives → all preserved and visible.

Unmarked groups remain independent. **`db-254` is NOT classified as `ONE_OF`**
(different patterns, no explicit provenance) — verified by test and by
measurement (`corpus_a` shows exactly 4 `ONE_OF` groups: db-237/238/239/240;
db-254 contributes 2 independent requirements).

## 7. Feature flag

* `SHADOW_AUTHORITY_PRODUCT_GATING` in `config.py` (parsed from the environment,
  default `""` → **False/OFF**), plus a runtime check
  `product_eligibility.flag_enabled()`.
* **OFF (default):** `run_persistence` computes `b6_decision = {source:
  "legacy", ...}` and the legacy evidence gate is the only decision. No shadow
  analysis runs inside persistence. Every legacy behavior — matcher, scoring,
  gaps, recommendations, streaks, API contract — is unchanged.
* **ON:** the shadow path is evaluated; the canonical gate decides product
  consequences, fail-closed (a failed/missing shadow evaluation can never
  enable scoring).
* Legacy and shadow conclusions are never silently mixed: the response carries
  both, and the B6 decision is attached additively as `b6_gate`.

## 8. ELO protection

The gate sits at the exact boundary before the consequence branch: when the
flag is ON and the canonical authority does not authorize, `is_authoritative`
is False for that decision → `_elo_engine.compute_updates` / `persist_elos`
never run for the submission. The Elo algorithm itself is untouched. With the
flag OFF, Elo behavior is byte-identical to pre-B6.

## 9. Gap protection

Same boundary: a non-authoritative or `PROVISIONAL` shadow conclusion prevents
the gap-engine branch (`compute_signals` / `persist_signals`) from running. The
legacy `gap_identified` boolean on the submission row is unchanged (it is
descriptive, not a consequence). Legacy gap semantics are untouched when OFF.

## 10. Recommendation protection

Same boundary: the `get_recommendation` / `_log_recommendation` branch runs only
when the gate allows. `_mark_last_recommendation_acted_on` also stays inside the
gated branch, exactly as before.

## 11. Legacy/shadow comparison

`LegacyShadowComparison` + `classify_comparison` produce the six required
categories (plus `LEGACY_OTHER`), as **migration evidence only** — they never
change behavior and never mutate either result (guarded by a test that
deep-compares the shadow result before/after a gating decision).

## 12. 46-submission results

| | native authority | authority-enriched view |
|---|---|---|
| B3 coverage | `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}` | same |
| B4 selected | `{sliding_window 7, two_pointers_opposite 5, dp_bottom_up 3, binary_search 2, dfs_backtracking 2, dp_top_down 2, bfs 1, union_find 1, none 23}` | same |
| B5 aggregation | `NO_AUTHORITATIVE_FAMILY 46` | `ALL_FAMILIES_AUTHORITATIVE 20, NO_AUTHORITATIVE_FAMILY 26` |
| B6 eligible / blocked | **0 / 46** | **20 / 26** |
| ONE_OF groups | 4 (4 submissions) | 4 |
| comparison | `CONFIRMED_NOT_AUTHORIZED 32, UNRESOLVED_NOT_AUTHORIZED 14` | `CONFIRMED_AUTHORIZED 20, CONFIRMED_NOT_AUTHORIZED 12, UNRESOLVED_NOT_AUTHORIZED 14` |

**Provenance is explicit:** the *native* mode is the recorded historical corpus,
whose groups lost `authority_tier` in the pre-B5.5 serialization — so native
authority is genuinely absent and everything is correctly blocked. The
*enriched* view re-attaches the record-level `shadow_authority_tier` at
measurement time; it is **not** native corpus provenance and is labelled as
such in the measurement JSON. The 4 `ONE_OF` submissions are now single
logical requirements and eligible under enriched authority.

## 13. 301-benchmark results

| Metric | Value |
|---|---|
| B3 coverage | `{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}` |
| B6 eligible / blocked | **0 / 301** |
| canonical authority | `INFERRED 301` (GT is `llm_proposed` — native) |
| comparison | `CONFIRMED_NOT_AUTHORIZED 112, UNRESOLVED_NOT_AUTHORIZED 189` |

The important result holds: **non-authoritative GT cannot create product
consequences.** The benchmark was not expected to become authoritative and is
not.

## 14. Test counts

| Suite | Result |
|---|---|
| B6 (`test_b6_product_eligibility.py`) | **39 passed** |
| B1 (48) + B2 (65) + B3 (32) + B4 (28) + B5 (36) + B5.5 (58) | **267 passed** |
| `pathforge/tests` (full) | **415 passed** |
| shadow suite | **810 passed** |
| experiments | **79 passed** |
| `ast_engine` + `db` | **76 passed** |
| `src` | 605 passed, **1 pre-existing failure** (`TestPrefixSumDetector::test_detected_product_except_self` — isolated from B6, unmodified) |
| `test_pipeline.py` | **8 passed** (previously environment-blocked; now green) |

## 15. Regression results

* B2 tri-state: unchanged (test).
* B3 coverage: unchanged (test).
* B4 primary strategy: unchanged (test).
* B5 authority: unchanged (test).
* Legacy matcher + legacy constants: unchanged (tests).
* Flag OFF: legacy path unchanged (tests + full-suite run).
* Flag ON: PROVISIONAL / UNRESOLVED / CONTRADICTED / INFERRED /
  STRUCTURALLY_OBSERVED / missing authority / missing primary / empty-required
  → all blocked (tests); eligible path allows consequences (test).
* ONE_OF: one-authoritative eligible, all-non-authoritative blocked, multiple
  preserved, db-254 independent (tests).
* Comparison purity: neither result mutated (test).

## 16. Changed behaviors — before / after / why / flag

| Behavior | Before | After | Why | Flag |
|---|---|---|---|---|
| Product-consequence decision | legacy `evidence ∈ {structurally_observed, externally_listed}` | unchanged | legacy contract preserved | OFF (default) |
| Product-consequence decision | (same) | canonical B5/B5.5 authority gates Elo/gaps/recs, fail-closed | canonical policy; protection of Elo/gaps/recs | ON |
| `run_persistence` return | no gating record | additive `b6_gate` key | comparison/audit visibility | both |
| `config.py` | no flag | additive `SHADOW_AUTHORITY_PRODUCT_GATING` (default False) | controlled migration | n/a |
| Frontend / API contracts | — | unchanged | out of scope | both |
| DB schema | — | unchanged (no migration needed) | eligibility is computed, not stored | both |

No destructive migration; no column added or removed; no existing field
reinterpreted.

## 17. Remaining ambiguities

1. **`db-254`-class groups** (multi-family, different patterns, no explicit
   provenance) remain independent. Making them `ONE_OF` requires a curated GT
   decision, not inference.
2. **Corpus authority provenance.** The recorded historical 46-corpus still
   lacks native `authority_tier`; a re-run with DB access is needed for native
   authority (B5.5 fixed the serialization for future runs only).
3. **Flag-scoped persistence source.** With the flag ON, the B6 gate supersedes
   the legacy evidence gate for consequences. Whether both gates must agree
   (intersection) or B6 alone governs is a policy choice; B6 currently governs
   alone but reports the legacy view alongside.
4. **`evidence` vs `authority_tier`.** The legacy gate still reads `evidence`;
   the canonical gate reads `authority_tier`. Converging on one persisted field
   remains the follow-up normalization.
5. **Streak updates** remain ungated (unchanged legacy behavior; arguably also a
   consequence — flagged for review).

## 18. Files changed

* **New:** `pathforge/services/product_eligibility.py`,
  `pathforge/tests/test_b6_product_eligibility.py`,
  `experiments/.../runners/b6_product_integration_measure.py`,
  `results/b6_product_integration_measurement.json`, this audit.
* **Modified:** `pathforge/services/persistence.py` (+56 additive lines, flag-gated),
  `config.py` (+8), `pathforge/tests/test_authority_gating.py` (guarded-prefix
  adjustment), `pathforge/tests/test_family_coverage.py` /
  `test_primary_strategy.py` (isolation allowlists).
* Untracked artifacts from B1–B5.5 unchanged.

## 19. Explicit statements

* **Legacy behavior remains the default** (flag OFF).
* The legacy matcher remains intact and available; nothing was deleted or
  replaced.
* Canonical authority (`HUMAN_APPROVED` / `EXTERNAL_VERIFIED`) is the only
  authorizing policy in B6; `PROVISIONAL` cannot score; non-authoritative
  results cannot create Elo, gaps, or recommendations.
* `ONE_OF` works only when explicitly declared; `db-254` remains independent.
* The known legacy test failure stays isolated from B6.

---

## Acceptance criteria

[x] Canonical authority is used · [x] No second authority vocabulary ·
[x] Product eligibility is explicit · [x] Only HUMAN_APPROVED / EXTERNAL_VERIFIED
authorize · [x] PROVISIONAL cannot score · [x] Non-authoritative cannot score ·
[x] ONE_OF only when explicitly declared · [x] db-254 independent ·
[x] ELO protected · [x] gaps protected · [x] recommendations protected ·
[x] legacy matcher intact · [x] flag defaults OFF · [x] OFF-path unchanged ·
[x] shadow/legacy comparison exists · [x] 46 corpus rerun · [x] 301 corpus rerun ·
[x] B1–B5.5 regressions pass · [x] B6 tests pass · [x] audit created.

**STOP — B6 complete. The legacy matcher has not been replaced; legacy behavior
remains the default.**
