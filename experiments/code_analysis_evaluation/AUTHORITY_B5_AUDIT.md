# B5 — Authority Gating: Audit

**Batch:** B5 — authority gating (shadow path only)
**Implementation:** `pathforge/ast_analysis/shadow/authority_gating.py` (new)
**Wiring:** one additive step in `pathforge/ast_analysis/shadow/shadow_runner.py`
**Tests:** `pathforge/tests/test_authority_gating.py` (36 tests)
**Measurement:** `experiments/code_analysis_evaluation/runners/authority_b5_measure.py`
→ `experiments/code_analysis_evaluation/results/authority_b5_measurement.json`

B1–B4 remain the baseline. B5 is stacked on top of them, consumes them
read-only, and declares no production authority. **The shadow pipeline is not
production-authoritative after B5.**

---

## 1. Scope

B5 answers: *"How authoritative is the B4 result?"*

It is a **deterministic evaluation layer** downstream of B3 coverage and B4
selection:

```
B2 evidence  →  B3 family coverage  →  B4 primary strategy  →  B5 authority
```

B5 does **not** replace the official matcher, does not change family coverage,
does not reorder B4 candidates, does not touch detectors, Ground Truth rows,
the database, the API, the frontend, Elo, gap detection or recommendations.
The only production-adjacent code touched is the same single shadow file that
B2/B3/B4 already extended, with one additive `"authority"` key.

**Naming note.** The brief suggested `shadow/authority.py`, but that path is
already taken by an unrelated Phase-5B module that records authority *upgrade
history*. B5 therefore uses `authority_gating.py` and leaves the existing module
untouched (see §22).

---

## 2. Authority tier definitions

A small explicit model, strongest first:

| Tier | Meaning | Authorizes? |
|---|---|---|
| `HUMAN_APPROVED` | Human-reviewed/approved Ground Truth or equivalent explicit human adjudication (`human_curated`, `human_approved`, `reviewed`, `editorial`) | **yes** |
| `EXTERNAL_VERIFIED` | Trusted external/reference evidence explicitly marked as such (`externally_listed`) | **yes** |
| `STRUCTURALLY_OBSERVED` | Deterministic analyzer evidence **about the submitted implementation** — not Ground Truth about the expected solution | no |
| `INFERRED` | Not independently authoritative (`llm_proposed`, `bootstrap`, `unobserved`, `unknown`, missing, anything unrecognised) | no |

Only `HUMAN_APPROVED` and `EXTERNAL_VERIFIED` are in `AUTHORIZING_TIERS`. This
follows the brief literally: Case 1 (human-approved) and Case 2 (external
verified) authorize; Case 3 explicitly says structural-only is **not** an
authoritative match. `STRUCTURALLY_OBSERVED` exists as a tier precisely so the
analyzer's own evidence can be *named* without being promoted.

The declared tiers already present in the codebase are **mapped explicitly**
(`AUTHORITY_TIER_MAP`), never silently renamed; unmapped values fall to
`INFERRED` and are separately flagged (§22).

---

## 3. Exact authority decision rules

Evaluated **per family**, in this order (branch order is the contract):

1. No Ground Truth at all → `NO_GROUND_TRUTH`, non-authoritative.
2. Coverage ≠ `CONFIRMED` → non-authoritative, reason `coverage_not_confirmed`.
   This covers `PROVISIONAL`, `UNRESOLVED`, `CONTRADICTED`, `UNMATCHABLE` in one
   branch: **no authority tier can override a B3 state.**
3. Coverage `CONFIRMED` but B4 selected no primary strategy → non-authoritative,
   reason `no_primary_strategy`. **B5 cannot invent a strategy B4 declined.**
4. Coverage `CONFIRMED` + B4 primary + tier `HUMAN_APPROVED` → **authoritative**
   (`authoritative_human_approved`).
5. Coverage `CONFIRMED` + B4 primary + tier `EXTERNAL_VERIFIED` →
   **authoritative** (`authoritative_external_verified`).
6. Coverage `CONFIRMED` + B4 primary + tier `STRUCTURALLY_OBSERVED` →
   non-authoritative (`structural_observation_only`).
7. Coverage `CONFIRMED` + B4 primary + tier `INFERRED` → non-authoritative
   (`inferred_authority`), or `unrecognized_authority_tier` when the declared
   value is not in the map at all.

Each family emits `authority_tier`, `declared_authority_tier`,
`authority_known`, `authoritative`, `safe_for_product_scoring`,
`coverage_state`, `primary_strategy`, `supporting_concepts` (the B3
conclusion-eligible PRESENT concepts, i.e. the structural evidence responsible),
and `reason_codes`.

No LLM. No probabilistic authority. No new scoring model.

---

## 4. Relationship to B2

B5 never reads B2 directly; it consumes B3, which consumes B2. The B2 tri-state
is unchanged and is still attached as `evidence_state`. Consequence: a
concept-level `CONTRADICTED` (e.g. the broad `dfs_backtracking` contradiction)
only reaches B5 through B3's *applicable identifying* escalation, and B5 then
just sees `CONTRADICTED` coverage → non-authoritative. B5 adds no new
contradiction source and changes no B2 state.

Measured: `evidence_state` is byte-identical before/after B5 on both corpora.

---

## 5. Relationship to B3

B5 consumes `CoverageReport` read-only. It never writes a coverage state and
cannot turn `PROVISIONAL` / `UNRESOLVED` / `CONTRADICTED` / `UNMATCHABLE` into
anything authoritative. Measured: the coverage distribution is identical on
both corpora (46: `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}`;
301: `{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}`).

Family alignment between B5/B4/B3 is **positional** — all three are built by
enumerating the same `solution_groups` list — so no id-matching can drift.

---

## 6. Relationship to B4

B5 consumes `SubmissionStrategySelection` read-only: for each family it takes
`selected` as the family's `primary_strategy`. It does **not** modify the
candidate ordering, adds no semantic strategy precedence, and invents no
strategy. When B4 returns no candidate, B5 reports `no_primary_strategy` and
stays non-authoritative (rule 3). Measured: the B4 selected-strategy
distribution is identical on both corpora.

---

## 7. Ground Truth authority handling

B5 reads each group's declared `authority_tier` (via B3's `FamilyCoverage`).
It mutates no Ground Truth row, refreshes no vocabulary, relabels no family,
promotes no technique-only family, and adds no Ground Truth. It also does
**not** silently repair a wrong or missing tier — it reports it (§22) and maps it
to the non-authorizing `INFERRED` tier.

Measured invariants: the `solution_groups` argument is unchanged after a full
run (deep-equality asserted in tests).

---

## 8. PROVISIONAL policy

`PROVISIONAL` stays an internal analytical state. B5 keeps it
non-authoritative (rule 2) and does not upgrade it even when B4 selected a
primary strategy. It is not a successful match, an Elo result, a gap result, a
recommendation trigger, or a frontend success state. Nothing user-facing was
modified in B5.

Demonstrated in tests: a `PROVISIONAL` family with `sliding_window` selected as
primary still reports `authoritative = False`,
`reason = coverage_not_confirmed`. Corpus B contributes 23 such families.

---

## 9. Family-level authority

Authority is decided **per family**; `AuthorityReport.families` preserves every
family's decision. The submission-level result is *derived from* the family
results and never erases them.

---

## 10. Submission-level aggregation

Deterministic, from the family results only:

| Aggregation | Meaning |
|---|---|
| `NO_GROUND_TRUTH` | no families were supplied |
| `NO_AUTHORITATIVE_FAMILY` | families exist, none authoritative |
| `MIXED_AUTHORITY` | some authoritative, some not |
| `ALL_FAMILIES_AUTHORITATIVE` | every family authoritative |

No single arbitrary "overall confidence" score is invented. The report exposes
`has_authoritative_family` separately from the aggregation so a mixed submission
is never collapsed to a bare boolean.

---

## 11. Scoring safety

`safe_for_product_scoring` (family and submission level) is **false** unless the
authority rules establish authoritative conclusions. At submission level it is
true only for `ALL_FAMILIES_AUTHORITATIVE` — i.e. it requires *every* evaluated
family to be authoritative.

This makes it impossible for "structural detection + B4 primary strategy" alone
to become an authoritative product result: a structural detection cannot satisfy
rules 4/5 without a human/external Ground-Truth claim, and a single
non-authoritative family keeps the submission unsafe.

---

## 12. Legacy isolation

- Legacy `MatchingEngine`, `src/ast_detection/`, ELO, gaps, recommendations, API,
  frontend and database schema: **untouched.**
- The old shadow matcher (`evaluate_solution_groups`) and its nested
  `match_outcome.primary_strategy` are untouched and still reported as
  `match_outcome`.
- `shadow_runner.py` received exactly one additive B5 step plus one additive
  `"authority"` key.
- A guard test asserts no production module imports `authority_gating`.

`git diff --stat` for the entire B2–B5 work: **1 tracked file changed, +82 lines,
0 deletions.**

---

## 13. LC209 / db-190

`Minimum Size Subarray Sum`, GT tier `human_curated`, family
`required = ["sliding_window"]`.

* B3 coverage: `CONFIRMED` (identifying + conclusion-eligible PRESENT).
* B4 primary: `sliding_window`.
* B5: `HUMAN_APPROVED` + `CONFIRMED` + primary → **authoritative**
  (`authoritative_human_approved`); submission `ALL_FAMILIES_AUTHORITATIVE`,
  `safe_for_product_scoring = True`.

Authority follows the **actual GT tier**, not the B4 selection.

---

## 14. LC102 / db-244

`Binary Tree Level Order Traversal`, GT tier `unknown` (INFERRED), family
`required = ["bfs_shortest_path"]`.

* B3 coverage: `CONFIRMED`.
* B4 primary: `bfs_shortest_path`.
* B5: `CONFIRMED` + primary but tier `INFERRED` → **non-authoritative**
  (`inferred_authority`).

This is Case 3: the analyzer observed the strategy, but no authoritative Ground
Truth establishes the expected approach, so it is reported as non-authoritative
structural evidence rather than a match.

---

## 15. LC704 / db-235

`Binary Search`, GT tier `human_curated`, `required = ["binary_search"]`.

* B3: `CONFIRMED`; B4 primary `binary_search`;
* B5: `HUMAN_APPROVED` + `CONFIRMED` + primary → **authoritative**.

Variants resolve through the existing strategy taxonomy (B4), and authority then
follows the declared GT tier.

---

## 16. LC3236 / db-49 / db-51 / db-194

`Smallest Missing Integer Greater Than Sequential Prefix Sum`. The recorded
family requires only `sequential_accumulation` — a **COMPONENT**, no identifying
requirement — and the GT tier is `llm_proposed`.

* B3 coverage: `UNRESOLVED` (no identity anchor).
* B4: no candidate (no conclusion-eligible concept required).
* B5: rule 2 fires first → **non-authoritative** (`coverage_not_confirmed`),
  `safe_for_product_scoring = False`.

Even if the tier were `human_curated`, B5 would still be non-authoritative,
because coverage is not `CONFIRMED`. The critical false-confirmation case stays
unconfirmed and un-authorized end-to-end.

---

## 17. LC1 / db-11

`Two Sum`. The recorded group has `required = []` → B3 `UNMATCHABLE`; GT tier
`unknown`.

* B4: `hash_lookup` is a technique (not conclusion-eligible) → no candidate.
* B5: rule 2 (`UNMATCHABLE`) → **non-authoritative**.

`hash_lookup` is neither promoted to a strategy nor to an authoritative
conclusion; a technique family would in any case be `PROVISIONAL` (no
conclusion-eligible PRESENT), never `CONFIRMED`.

---

## 18. LC560

A hash-map/frequency family (`frequency_counting` + `sequential_accumulation`,
both non-conclusion-eligible):

* B4: no candidate → primary `None`.
* B5: even if a GT tier were authoritative, rule 3 (`no_primary_strategy`) keeps
  it non-authoritative. No strategy is fabricated and no authority is claimed.

---

## 19. 46-case measurement (corpus A)

46 real submissions, 51 families. Pre-B5 runner reconstructed by deleting exactly
the 19 B5 lines; both arms run on identical inputs.

| Metric | Value |
|---|---|
| deterministic-field mismatches | **0** |
| coverage distribution | `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}` — identical |
| old `match_outcome` distribution | `{CONFIRMED 32, UNRESOLVED 14}` — identical |
| B4 selected-strategy distribution | identical |
| declared tiers | `human_curated 30, unknown 16, llm_proposed 5` |
| mapped tiers | `HUMAN_APPROVED 30, INFERRED 21` |
| family coverage states | `CONFIRMED 23, UNRESOLVED 16, UNMATCHABLE 11, CONTRADICTED 1` |
| family reasons | `authoritative_human_approved 20, coverage_not_confirmed 28, inferred_authority 3` |
| authoritative families | **20** |
| non-authoritative families | **31** |
| aggregation | `ALL_FAMILIES_AUTHORITATIVE 16, MIXED_AUTHORITY 4, NO_AUTHORITATIVE_FAMILY 26` |
| safe_for_product_scoring submissions | **16** |
| mixed-authority submissions | 4 |
| no-authoritative-family submissions | 26 |
| no-ground-truth submissions | 0 |
| structural-observation-only strategies | 0 (corpus A declares no `structurally_observed` family — see §22) |

The 20 authoritative families are the human-curated GT families whose coverage
is `CONFIRMED` and whose B4 primary is a conclusion-eligible strategy
(`two_pointers_opposite`, `sliding_window`, `binary_search`, `dp_bottom_up`,
`dp_top_down`, `dfs_backtracking`, `union_find`).

The 4 `MIXED_AUTHORITY` submissions are `db-237/238` (Climbing Stairs) and
`db-239/240` (Coin Change) — problems whose Ground Truth is stored as **two
alternative families** (`dp_bottom_up` OR `dp_top_down`). Exactly one
alternative can be confirmed, so the conservative all-families rule marks the
submission mixed. See §23.

The 3 `inferred_authority` families are `db-138`, `db-189` (`llm_proposed`,
`sliding_window`) and `db-244` (`unknown`, `bfs_shortest_path`) — observed and
confirmed, but not authorized.

---

## 20. 301-case measurement (corpus B)

301 disjoint cases, synthetic single-family groups. Corpus B carries **no**
authority metadata, so its groups are labelled `llm_proposed` (documented, not a
repair).

| Metric | Value |
|---|---|
| deterministic-field mismatches | **0** |
| coverage distribution | `{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}` — identical |
| old `match_outcome` distribution | `{CONFIRMED 112, UNRESOLVED 189}` — identical |
| B4 selected-strategy distribution | identical |
| family reasons | `coverage_not_confirmed 272, inferred_authority 29` |
| authoritative families | **0** |
| safe_for_product_scoring submissions | **0** |
| aggregation | `NO_AUTHORITATIVE_FAMILY 301` |

Every corpus-B case is non-authoritative — exactly what a corpus with no
human/external GT authority should report. The 29 `CONFIRMED` cases are
`inferred_authority`: observed and confirmed but not authorized.

---

## 21. Before/after invariants

Verified identical between the pre-B5 runner and the current runner, on both
corpora:

1. B2 evidence states — identical
2. B3 coverage states — identical
3. B4 strategy candidates — identical
4. B4 selected primary strategy — identical
5. legacy `match_outcome` — identical
6. legacy nested `match_outcome.primary_strategy` — identical
7. detectors / techniques / strategies / structural facts — identical

Only the new `authority` key differs. The measurement runner fails (non-zero
exit) if any invariant breaks; it returned clean.

---

## 22. Data-quality issues (reported, not repaired)

1. **Corpus A lost `authority_tier` at serialization.** The stored `groups` have
   no `authority_tier`, even though the original run recorded one (the
   record-level `shadow_authority_tier`). For measurement the record-level value
   was   re-attached to each group — exact for single-family records, an
   *upper bound* for the 5 multi-family records (`db-237/238/239/240/254`). This
   is a corpus-serialization defect, not a module defect.

2. **`human_curated` is not a builder-accepted tier.**
   `ground_truth_builder.VALID_AUTHORITY_TIERS = {bootstrap, llm_proposed,
   structurally_observed, externally_listed, editorial}`, yet CSV reconciliation
   writes `authority_tier = "human_curated"` (30 of 51 corpus-A families). The
   most human-trusted label is outside the declared vocabulary.

3. **`unknown` / `unobserved` are used as tier values** (16 corpus-A families)
   but are not in the builder's set and not documented as a tier anywhere.

4. **Two diverging tier vocabularies.**
   `shadow/authority.py::VALID_AUTHORITY_TIERS` additionally allows `reviewed`,
   which the builder does not. Neither includes `human_curated`.

5. **The existing production authority policy disagrees with B5.**
   `matching._AUTHORITATIVE_TIERS = {structurally_observed, externally_listed,
   editorial}` and `persistence._AUTHORITATIVE_STATES = {structurally_observed,
   externally_listed}` treat `structurally_observed` GT as authoritative and
   `human_curated` as *not* authoritative — the opposite of B5's mapping. B5
   reports this; it does not "fix" either policy (that is a product decision).

6. **`structurally_observed` GT families do not appear in either corpus**, so the
   `structural_observation_only` branch is demonstrated only by unit tests, not
   by corpus data.

7. **Name collision:** `shadow/authority.py` already exists (Phase-5B upgrade
   records). B5 could not reuse the suggested filename and created
   `authority_gating.py`; the pre-existing module is untouched.

---

## 23. Unresolved architecture questions (for review before B6)

1. **Does `STRUCTURALLY_OBSERVED` Ground Truth authorize?** B5 follows the brief
   literally (no: structural observation is analyzer evidence about the
   submission, not GT about the expected solution). Production currently says
   yes. This single decision flips the corpus-A authoritative count for any
   future `structurally_observed` GT. Needs ratification.

2. **Alternative (OR) families.** `db-237/238/239/240` store mutually exclusive
   approaches as separate families. Because only one alternative can ever be
   `CONFIRMED`, the conservative all-families rule marks such submissions
   `MIXED_AUTHORITY` and thus not safe for scoring — even though the submitted
   approach was correctly identified and authoritative. The architecture needs
   an explicit "family alternatives / one-of" concept (B3/B4 currently cannot
   express it).

3. **Meaning of submission-level `safe_for_product_scoring`.** B5 chose the
   conservative "all evaluated families authoritative". The alternative —
   "at least one authoritative family, per approach" — is equally defensible and
   would change the corpus-A count from 16 to 20.

4. **Which layer owns the tier mapping?** `human_curated`, `reviewed`,
   `unobserved`, `unknown` need one canonical vocabulary, ideally in
   `ground_truth_builder`, with the shadow mapping derived from it rather than
   restated.

5. **`editorial` = `HUMAN_APPROVED`?** The V2 review pipeline records
   `granularity: family_level_human_approved` and derives groups as `editorial`.
   B5 maps `editorial` → `HUMAN_APPROVED`; this should be confirmed, since no
   current corpus row exercises it.

6. **Interaction with `evidence`.** Persistence derives `verdict_type` from the
   group's `evidence` field; B5 reads `authority_tier`. The two fields can
   disagree (issue 1). Authority gating should eventually read one field.

7. **Corpus B has no authority metadata**, so it cannot validate the authority
   layer end-to-end; it only proves additivity. A corpus with real human-approved
   tiers is needed before B6 relies on authority for scoring.

**Recommended B6 direction:** migrate the authority decision into the
verdict/persistence path so non-authoritative and `PROVISIONAL` results cannot
produce Elo, gap, or recommendation effects, and reconcile the Ground-Truth
authority vocabulary in one place. Do **not** wire shadow authority into the
official matcher yet.

---

## Final report

1. **Files changed** — new: `pathforge/ast_analysis/shadow/authority_gating.py`,
   `pathforge/tests/test_authority_gating.py`,
   `experiments/code_analysis_evaluation/runners/authority_b5_measure.py`,
   `experiments/code_analysis_evaluation/results/authority_b5_measurement.json`,
   this audit. Modified: `pathforge/ast_analysis/shadow/shadow_runner.py`
   (one additive B5 step + `"authority"` key), and the B2/B4 test
   reconstructions plus two isolation allowlists (additive). **1 tracked file
   changed, +82 lines, 0 deletions** (B2–B5 total).
2. **Tests added** — 36 (`test_authority_gating.py`), covering all 20 requested
   cases (human-approved, external-verified, structural-only, provisional,
   unresolved, contradicted, no-GT, unmatchable, B4-cannot-bypass-B3, technique
   never authoritative, family-level preservation, mixed authority,
   deterministic aggregation, scoring safety, legacy matcher unchanged,
   B2/B3/B4 unchanged, detectors unchanged, GT unmutated).
3. **Authority rules implemented** — the seven rules of §3, with authorizing
   tiers `{HUMAN_APPROVED, EXTERNAL_VERIFIED}`.
4. **46-case results** — 0 mismatches; 20 authoritative families; 16
   `ALL_FAMILIES_AUTHORITATIVE`, 4 `MIXED_AUTHORITY`, 26
   `NO_AUTHORITATIVE_FAMILY`; 16 safe-for-scoring submissions (§19).
5. **301-case results** — 0 mismatches; 0 authoritative families; all 301
   `NO_AUTHORITATIVE_FAMILY` (§20).
6. **Invariant verification** — B2, B3, B4 (candidates + selection) and the
   legacy matcher are identical before/after B5 on both corpora; only the new
   `authority` key changes (§21).
7. **Ground-Truth authority inconsistencies** — see §22 (issues 1–6).
8. **Cases where authority cannot be determined cleanly** — 16 `unknown` and 21
   `INFERRED` families map to non-authoritative by rule; none required an
   out-of-band decision. No case produced an ambiguous authority outcome.
9. **Recommended next architectural decision for B6** — reconcile the GT
   authority vocabulary and migrate authority into the verdict/persistence path
   (§23).

**STOP — B5 complete. B6 not started. The shadow pipeline is not
production-authoritative.**
