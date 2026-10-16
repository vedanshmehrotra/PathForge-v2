# B5.5 — Ground-Truth / Authority Normalization: Audit

**Batch:** B5.5 — Ground-Truth authority normalization + explicit alternative families
**Implementation:**
`pathforge/ast_analysis/authority_vocabulary.py` (new, canonical),
`pathforge/ast_analysis/shadow/authority_gating.py` (canonicalized + `ONE_OF`),
`pathforge/ast_analysis/shadow/family_coverage.py` (additive relation metadata),
`pathforge/ast_analysis/shadow/authority.py` (canonical vocabulary),
`pathforge/services/ground_truth_builder.py` (vocabulary + group serialization + relations),
`pathforge/services/problem_resolver.py` (loader relation marking),
`experiments/.../runners/real_submission_harness.py` (full group serialization)
**Tests:** `pathforge/tests/test_gt_authority_normalization.py` (58)
**Measurement:** `experiments/.../runners/authority_normalization_b5_5_measure.py`
→ `results/authority_normalization_b5_5_measurement.json`

> **The shadow pipeline is NOT production-authoritative.** B5.5 is a
> normalization and representation batch only. Production policy is recorded and
> pinned, never migrated. **B6 has NOT started.**

---

## 1. Scope

B5.5 normalizes the Ground-Truth / authority **representation** problems B5
exposed, and introduces an explicit representation for alternative (`ONE_OF`)
families. It does not migrate anything into production, changes no Elo/gap/
recommendation/frontend/API/database behavior, replaces no matcher, and changes
no detector, technique, strategy, threshold or B2/B3/B4 rule.

Two things are intentionally allowed to change:

1. **Representation** — one canonical authority vocabulary; alternative-family
   relation metadata; complete (non-lossy) group serialization.
2. **The shadow authority *aggregation unit*** — an explicitly declared `ONE_OF`
   set counts as one logical requirement.

Everything else must be byte-identical. The measurement confirms that.

---

## 2. Files changed

| File | Change |
|---|---|
| `pathforge/ast_analysis/authority_vocabulary.py` | **new** — the single canonical vocabulary (tiers, stored-value map, authorizing set, missing-metadata semantics, legacy production policy, alternative-family markers, evidence/authority agreement helpers) |
| `pathforge/ast_analysis/shadow/authority_gating.py` | imports the canonical vocabulary (no local mapping); adds `AlternativeGroupAuthority`, `ONE_OF` aggregation, relation fields |
| `pathforge/ast_analysis/shadow/family_coverage.py` | `FamilyCoverage` gains additive `family_relation` / `alternative_group_id` (default `None`); ordinary-family semantics unchanged |
| `pathforge/ast_analysis/shadow/authority.py` | `VALID_AUTHORITY_TIERS` now derives from the canonical vocabulary (was a divergent literal) |
| `pathforge/services/ground_truth_builder.py` | `VALID_AUTHORITY_TIERS` derives from canonical; new `serialize_solution_group(s)` / `deserialize_solution_groups`; new `mark_family_relations` / `alternative_group_id_for` |
| `pathforge/services/problem_resolver.py` | loader preserves + derives `family_relation` / `alternative_group_id`; preserves `authority_tier` |
| `experiments/.../runners/real_submission_harness.py` | records the **complete** solution group (previously a field whitelist that dropped `authority_tier`) |
| `pathforge/tests/test_gt_authority_normalization.py` | **new** — 58 tests |
| `pathforge/tests/test_family_coverage.py`, `test_primary_strategy.py` | isolation allowlists extended for the new test file |

`git diff --stat`: **5 tracked files, +251 / −26 lines** (the removals are the
replaced literals/mapping). Shadow runner untouched by B5.5.

---

## 3. Canonical authority vocabulary

There is now exactly **one** definition of "what does a stored authority value
mean": `pathforge/ast_analysis/authority_vocabulary.py`.

It owns:

* the four canonical tiers and their rank;
* `AUTHORIZING_TIERS` = `{HUMAN_APPROVED, EXTERNAL_VERIFIED}`;
* `SOURCE_TIER_MAP` — the one stored-value → tier mapping;
* `VALID_GT_TIERS` — the stored values the Ground-Truth builder accepts;
* `MISSING_AUTHORITY_VALUES` — values meaning "metadata absent";
* the recorded legacy production policy;
* the alternative-family relation markers;
* `authority_evidence_agreement` / `find_authority_evidence_disagreements`.

Consumers import it:

* `shadow/authority_gating.py` re-exports `AUTHORITY_TIER_MAP is vocab.SOURCE_TIER_MAP`.
* `ground_truth_builder.VALID_AUTHORITY_TIERS = set(vocab.VALID_GT_TIERS)`.
* `shadow/authority.py.VALID_AUTHORITY_TIERS = set(vocab.KNOWN_SOURCE_TIERS)`.
* the measurement runners read it instead of restating anything.

`matching.py` and `pathforge/services/persistence.py` are **not** modified
(§17); their policy is recorded in the canonical module and pinned by a test.

---

## 4. Complete mapping table

| Stored value | Canonical tier | Authorizes? | Established from |
|---|---|---|---|
| `human_curated` | `HUMAN_APPROVED` | yes | CSV reconciliation in `_load_ground_truth` (explicit human adjudication) |
| `human_approved` | `HUMAN_APPROVED` | yes | canonical human-approved name |
| `reviewed` | `HUMAN_APPROVED` | yes | `shadow/authority.py` `editorial → reviewed` transition target |
| `editorial` | `HUMAN_APPROVED` | yes | V2 review pipeline derived groups (see §5) |
| `externally_listed` | `EXTERNAL_VERIFIED` | yes | trusted external/reference evidence, explicitly marked |
| `external_verified` | `EXTERNAL_VERIFIED` | yes | canonical external name |
| `structurally_observed` | `STRUCTURALLY_OBSERVED` | **no** | analyzer evidence about the submitted code; also `scripts/seed_ground_truth.py` |
| `llm_proposed` | `INFERRED` | no | LLM-proposed Ground Truth |
| `bootstrap` | `INFERRED` | no | cold-start placeholder |
| `unobserved` | `INFERRED` | no | absent observation (missing metadata) |
| `unknown` | `INFERRED` | no | unspecified (missing metadata) |
| `inferred` / `hypothesis` | `INFERRED` | no | canonical non-authoritative names |

Unrecognised / missing values map to `INFERRED` and are additionally reported by
`authority_data_quality`. **Absence never becomes authority.**

---

## 5. Human-approval semantics

The four human-related values were resolved from the code that writes them:

* **`human_curated`** — `problem_resolver._load_ground_truth` sets this when a
  curated CSV pattern label overrides or agrees with the stored one. The
  reconciliation fix report documents it as the human-curated authority for the
  production matcher. → `HUMAN_APPROVED`.
* **`human_approved`** — the canonical name for the same concept. → `HUMAN_APPROVED`.
* **`reviewed`** — the target of the `editorial → reviewed` transition declared
  in `shadow/authority.py::VALID_TIER_TRANSITIONS`; a human review step. →
  `HUMAN_APPROVED`.
* **`editorial`** — written by the V2 Ground-Truth review pipeline
  (`gt_poc_v2/derive.py`) on groups whose activation requires
  `approval_state == "APPROVED"`, recorded with
  `granularity: "family_level_human_approved"` (see `gt_poc_v2/human_review.py`).
  It is *not* "every value containing editorial": it is the specific tier the
  reviewed-and-approved derivation writes. → `HUMAN_APPROVED`.

**Equivalence is encoded only where evidence supports it.** `reviewed` and
`editorial` are mapped to the same tier as `human_curated` because all three are
human adjudication of the accepted approach from *different channels*, not
because their strings look similar. The provenance for `editorial` lives in the
V2 review artifacts; **no corpus row currently exercises it**, which is recorded
as an unresolved provenance question (§18).

---

## 6. STRUCTURALLY_OBSERVED policy

There is now exactly one documented semantic definition:

> `STRUCTURALLY_OBSERVED` is deterministic evidence the analyzer produces about
> the **submitted implementation**. It is **not** Ground Truth about the
> **expected** solution, and it is **NON-AUTHORIZING**.

This is the B5 policy, preserved. Production currently implements the opposite
(`persistence._AUTHORITATIVE_STATES` trusts `structurally_observed`). B5.5 makes
the intended policy explicit, records the conflict (§17) and **does not change
production behavior** — that migration belongs to B6.

---

## 7. unknown / unobserved semantics

`unknown` and `unobserved` are **missing / unspecified authority metadata**, not
weaker authority tiers. They:

* map conservatively to `INFERRED` (non-authorizing);
* are listed in `MISSING_AUTHORITY_VALUES`;
* are reported by `authority_data_quality` under `missing_metadata`;
* are **not** accepted by the Ground-Truth builder (`VALID_GT_TIERS`) — they are
  loader fallbacks, not declared tiers.

Eleven tests cover the conservative mapping and the "cannot accidentally
authorize" property.

---

## 8. Serialization fix

**Defect.** `real_submission_harness.py` serialized groups with a field
whitelist (`id/required/optional/excluded/patterns/derivation_patterns/matchable`),
dropping `authority_tier` (and `evidence`, `provenance`, `version`, …). That is
why the B5 corpus had no authority metadata and the B5 measurement had to
re-attach it.

**Fix.**
* `ground_truth_builder.serialize_solution_group(s)` preserves *every* field;
  `deserialize_solution_groups` parses TEXT/JSONB and preserves every field.
* the harness now records the complete group via the canonical helper.

**Round-trip.** `original group == semantically reconstructed group` is asserted
for a fully-populated group and for the loader path. The measurement reports
**0 round-trip failures** on both corpora.

The builder→store path already used `json.dumps(full_group)`, so production
storage never lost the field; the loss was in the measurement artifact. The
canonical helpers now make that guarantee explicit and testable.

---

## 9. authority_tier vs evidence analysis

`authority_tier` and `evidence` are two stored representations of **the same
authority concept**:

* `_load_ground_truth` writes `authority_tier` (`human_curated` on reconciliation,
  else the stored tier or `unobserved`), and keeps `evidence` from the group.
* `pathforge/services/persistence.py` derives `verdict_type` from `evidence`.

So they **overlap**, and they can disagree. B5.5:

* provides `authority_evidence_agreement(group)` returning both canonical
  interpretations plus an `agree` flag;
* provides `find_authority_evidence_disagreements(groups)`;
* **does not** overwrite either field (no Ground Truth mutation).

No canonical *authority source* is removed; `authority_tier` is designated the
canonical field for the shadow authority path, and `evidence` remains a legacy
field for persistence compatibility. Measured disagreements on the corpora: **0**
(the recorded corpus groups carry no `evidence` key, so no disagreement is
representable there — an explicit corpus limitation, reported rather than hidden).

---

## 10. Alternative-family model

A Ground-Truth problem may express its accepted approaches as **alternatives**:

```
problem
  ├── independent family A          (its own requirement)
  └── ONE_OF group G                (one logical requirement)
        ├── alternative A
        └── alternative B
```

Minimal additive representation on a group dict:

* `family_relation` — `"ONE_OF"` (or absent/`"INDEPENDENT"`);
* `alternative_group_id` — ties sibling alternatives together.

**Only explicitly marked alternatives behave as `ONE_OF`.** Independent families
are never merged.

### Where the marking comes from (explicit provenance, not guessing)

Two code-established situations are marked, by
`ground_truth_builder.mark_family_relations` / `_split_csv_patterns_to_groups`:

1. **Curated alternatives** — sibling groups sharing an identical non-empty
   pattern set but requiring *different* concepts. This is the structure
   `refresh_group_vocabulary` already refuses to collapse ("that difference is
   curated information the mapping cannot reproduce"), and the case its test
   calls *"curated alternatives sharing patterns are preserved"*. This marks
   **db-237/238/239/240**.
2. **CSV multi-family split** — a pattern list spanning more than one solution
   family is split by `_split_csv_patterns_to_groups` into per-family groups,
   whose docstring states they are alternative approaches. The loader preserves
   the marker into the returned groups.

`db-254` (two groups with *different* patterns: `two_pointers_same` and
`prefix_sum`) is **not** marked — the source does not explicitly declare it an
alternative, so it stays independent and is reported (§18).

---

## 11. ONE_OF semantics

For an explicitly declared `ONE_OF` group:

| Situation | Result |
|---|---|
| one alternative authoritative | the group is **satisfied / authoritative** (`alternative_satisfied`) |
| multiple alternatives authoritative | **all preserved and visible** (`alternative_multiple_satisfied`); the group is authoritative |
| no alternative authoritative | the group is **unsatisfied** (`alternative_unsatisfied`) |
| one confirmed, another unresolved | the unresolved sibling is expected; the submission is **not** forced to `MIXED_AUTHORITY` |
| a `ONE_OF` set with a single member | not treated as a group; the family stays independent |

B5.5 keeps **every** individual family decision and adds:

* `alternative_groups` — one record per declared set (members, which are
  authoritative, reason codes);
* `logical_requirement_count` / `authoritative_logical_requirement_count`.

Aggregation now works over **logical requirements** (independent families +
`ONE_OF` groups), not raw families. `safe_for_product_scoring` requires **every**
logical requirement to be authoritative.

---

## 12. B2 / B3 / B4 compatibility

* **B2** — untouched. `evidence_state` identical.
* **B3** — the only change is the additive `family_relation` /
  `alternative_group_id` on `FamilyCoverage` (and its `to_dict`). Every ordinary
  family's `coverage_state`, `reason_codes`, present/absent/contradicted lists
  and `conclusion_eligible_present` are unchanged, and the new fields are `None`.
  A regression test asserts the semantic fields are identical and the relation
  fields are `None` for an ordinary family.
* **B4** — untouched. `select_submission_primary` and the per-family selections
  are unchanged; alternatives are still evaluated independently per family.

Measured: the coverage distribution and the B4 selected-strategy distribution
match the frozen B5 baseline on **both** corpora.

---

## 13. B5 compatibility

The seven authority rules are unchanged. Only two things changed:

1. the mapping now comes from the canonical vocabulary (values are identical for
   every stored value that already existed);
2. aggregation treats an explicit `ONE_OF` set as one logical requirement.

All existing B5 tests pass (36), with the two key-set assertions updated for the
additive fields.

---

## 14. 46-case results

| Metric | Value |
|---|---|
| coverage distribution | `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}` — **matches B5 baseline** |
| legacy `match_outcome` distribution | `{CONFIRMED 32, UNRESOLVED 14}` — **matches B5 baseline** |
| B4 selected distribution | **matches B5 baseline** |
| explicitly declared `ONE_OF` groups | **4** |
| submissions affected by `ONE_OF` | **4** (`db-237/238/239/240`) |
| serialization round-trip failures | **0** |
| authority/evidence disagreements | 0 (corpus groups carry no `evidence`) |
| families with missing authority metadata | 51 (the corpus artifact dropped `authority_tier`) |

**Raw arm** (corpus as stored — authority metadata absent): all 51 families
`INFERRED`, all 46 submissions `NO_AUTHORITATIVE_FAMILY`. This is the honest
result for a corpus that lost its authority field; B5.5 does not re-attach it.

**Authority-enriched view** (record-level `shadow_authority_tier` re-attached —
documented approximation, exact for single-family records):

| Metric | B5 | B5.5 |
|---|---|---|
| `ALL_FAMILIES_AUTHORITATIVE` | 16 | **20** |
| `MIXED_AUTHORITY` | **4** | **0** |
| `NO_AUTHORITATIVE_FAMILY` | 26 | 26 |
| safe-for-scoring submissions | 16 | **20** |
| canonical tiers | `HUMAN_APPROVED 30, INFERRED 21` | same |

The 4 previously-mixed submissions (`db-237/238/239/240`) are now correctly
single-requirement (`ALL_FAMILIES_AUTHORITATIVE`): **4 newly authoritative
submissions, 4 newly authoritative families**, exactly the families whose
alternative structure the source establishes.

---

## 15. 301-case results

| Metric | Value |
|---|---|
| coverage distribution | `{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}` — **matches B5 baseline** |
| legacy `match_outcome` distribution | `{CONFIRMED 112, UNRESOLVED 189}` — **matches B5 baseline** |
| B4 selected distribution | **matches B5 baseline** |
| `ONE_OF` groups | 0 (single synthetic family per case) |
| authoritative families / safe submissions | 0 / 0 (all `llm_proposed`) |
| round-trip failures | 0 |

No regression; the corpus carries no authority or alternative metadata.

---

## 16. Regression results

| Suite | Result |
|---|---|
| B5.5 normalization tests | **58 passed** |
| B1 registry (48), B2 tri-state (65), B3 coverage (32), B4 primary (28), B5 authority (36) | **all passed** |
| shadow suite | **810 passed** |
| `pathforge/tests` | **376 passed** |
| experiments | **79 passed** |
| `ast_engine` + `db` | **76 passed** |
| `src` | 605 passed, **1 pre-existing failure** (`TestPrefixSumDetector::test_detected_product_except_self`, unchanged and unrelated) |

Named regressions verified: LC209 unchanged, LC102 unchanged, LC704 unchanged,
LC3236 unresolved + non-authoritative, LC1 unmatchable + non-authoritative,
LC560 no fabricated strategy. Legacy matcher unchanged. B2 evidence unchanged.
Ordinary B3 coverage unchanged. B4 selection unchanged. No production scoring
change.

---

## 17. Production authority conflict (recorded, not fixed)

The canonical policy and the current production policy disagree:

| | Trusts | Ignores |
|---|---|---|
| Canonical (B5/B5.5) | `HUMAN_APPROVED`, `EXTERNAL_VERIFIED` | `STRUCTURALLY_OBSERVED`, `INFERRED` |
| `persistence._AUTHORITATIVE_STATES` | `structurally_observed`, `externally_listed` | `human_curated`, `editorial`, `reviewed` |
| `matching._AUTHORITATIVE_TIERS` | `structurally_observed`, `externally_listed`, `editorial` | `human_curated`, `reviewed` |

B5.5 records both legacy sets in the canonical module
(`LEGACY_PRODUCTION_AUTHORITATIVE_STATES`, `LEGACY_PRODUCTION_AUTHORITATIVE_TIERS`)
and pins them with a test, so B6 cannot change them silently. Per the batch's
safety rule, `matching.py` and `persistence.py` were **not modified**.

---

## 18. Unresolved provenance questions

1. **`db-254`** (`Smallest Stable Index I`) has two groups with *different*
   patterns (`two_pointers_same`, `prefix_sum`) covering different families. It is
   semantically an alternative set, but the source does not explicitly declare
   it one (no shared pattern, no relation field), so B5.5 **does not** mark it.
   Confirming whether multi-family stored groups with different patterns are
   always alternatives requires a product decision (and possibly a curated
   `family_relation` on the row).
2. **`editorial` ↔ `HUMAN_APPROVED`** is inferred from the V2 review pipeline
   (`approval_state == APPROVED`, `family_level_human_approved`) but is not
   exercised by any corpus row. Should the canonical map keep this equivalence?
3. **`reviewed`** has no writer in the current Ground-Truth code — it exists only
   in the legacy `shadow/authority.py` transition table. Its mapping to
   `HUMAN_APPROVED` rests on that declaration alone.
4. **Corpus serialization is historically lossy.** The recorded corpora still
   lack `authority_tier`; the fix applies to future harness runs. Existing
   corpora need a re-run (with DB access) to carry authority natively.
5. **`evidence` vs `authority_tier`** overlap is real; which one becomes the
   single canonical persisted field is a B6/next decision.
6. **`human_curated` was absent from the builder's accepted set.** B5.5 adds it,
   but adding a value to `VALID_AUTHORITY_TIERS` widens `_validate_group`; whether
   that is the desired end-state or a transition should be confirmed.

---

## 19. Migration implications for B6

1. **One canonical field.** Persist the canonical authority (or derive it from
   `authority_tier`) and let `evidence` become a documented legacy field, or
   explicitly map `evidence → authority_tier` on write.
2. **Adopt the canonical authorizing policy** in `persistence`/`matching`, which
   *inverts* the current behavior for `structurally_observed` and `human_curated`.
   This must be a reviewed, deliberate migration.
3. **Wire `ONE_OF` into the verdict path** so an alternative set counts once.
4. **Re-run the corpora** with the fixed harness so authority metadata is real
   rather than re-attached.
5. **Decide the `db-254`-class question** (multi-family, different-pattern
   groups) before relying on `ONE_OF` for scoring.
6. **`PROVISIONAL` stays internal** — do not expose it as a success state.

---

## 20. B6 has NOT started

No verdict/persistence migration, no Elo/gap/recommendation change, no frontend
or API change, no matcher replacement. The shadow pipeline is **not**
production-authoritative. B5.5 is complete and stops here.

---

## Final report

1. **Files changed** — §2 (1 new canonical module, 1 new test module, 5 modified
   source files, 1 modified measurement harness, 2 test allowlists).
2. **Canonical authority vocabulary** — `pathforge/ast_analysis/authority_vocabulary.py`,
   imported by the shadow authority path, the builder and the legacy shadow
   authority module; the only stored-value → tier mapping (§3).
3. **Authority mappings** — §4 (13 stored values; 2 authorizing tiers).
4. **Serialization result** — complete-field group serialization +
   `serialize/deserialize_solution_groups`; **0 round-trip failures**; loader and
   builder preserve `authority_tier` (§8).
5. **authority/evidence inconsistencies** — agreement helpers added; 0
   representable disagreements in the recorded corpora; the two fields are
   documented as overlapping (§9).
6. **Alternative-family implementation** — `family_relation` +
   `alternative_group_id`, marked only from explicit provenance, consumed by B3
   (exposed) and B5 (`ONE_OF` logical requirement) (§10–11).
7. **46-case results** — invariants match the B5 baseline; 4 `ONE_OF` groups;
   enriched view: `MIXED` 4 → **0**, `ALL` 16 → **20**, safe 16 → **20** (§14).
8. **301-case results** — invariants match; no `ONE_OF`; no regressions (§15).
9. **Regression results** — 58 new tests + all B1–B5 suites, shadow (810),
   `pathforge/tests` (376), experiments (79), `ast_engine`+`db` (76), `src`
   (605/606, 1 pre-existing) (§16).
10. **Remaining architecture decisions** — §18 (db-254 class, `editorial`/`reviewed`
    equivalence, corpus re-run, canonical persisted field, builder tier set).
11. **Recommended B6 scope** — §19 (adopt canonical policy in the verdict/
    persistence path, one canonical field, `ONE_OF` in the verdict path, re-run
    corpora).

**STOP — B5.5 complete. B6 not started.**
