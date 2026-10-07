# Primary Strategy Selection — Batch B4 Audit

**Document type:** implementation + measurement audit (B4 only)
**Status:** B4 implemented and measured; **B5 not started**
**Date:** 2026-09-26
**Scope:** specificity + primary-strategy selection — shadow / presentation layer only.

**Invariants honoured:**

- no detector, technique, strategy, threshold, Ground-Truth row, database, API,
  ELO, gap, recommendation or frontend file was modified;
- the official matcher and the legacy AST engine are untouched;
- the B2 falsifier ledger and the B3 coverage rules are unchanged;
- only one already-tracked production file changed (`shadow_runner.py`), and the
  change is purely additive;
- every number below was measured, never tuned to a target.

---

## 1. Exact selection algorithm

`select_primary_strategy(relevant_concepts, snapshot, *, scope, family_id,
family_contradicted)`:

1. **Filter** `relevant_concepts` (deduplicated, order-preserving) to those that
   are `conclusion_eligible == True` **and** `PRESENT` in the B2 snapshot. Only
   these are candidates. This is the whole eligibility rule.
2. If `family_contradicted` (B3's applicable family-level contradiction) → no
   selection (`reason = family_contradicted`).
3. If there are no candidates → no selection
   (`reason = no_conclusion_eligible_present`).
4. Otherwise order candidates by
   `(-specificity_rank, -confidence, concept_id)` and select the first:
   - one candidate → `single_candidate`;
   - the leader has strictly higher `specificity_rank` → `selected_by_specificity`;
   - else the leader has strictly higher `confidence` → `selected_by_confidence`;
   - else (a genuine tie) → `tie_broken_by_concept_id`, `tie_resolved = True`,
     `ambiguity = True`.

The result carries the full ranked `candidates`, the `selected` id,
`reason_codes`, `tie_resolved` and `ambiguity`, so every choice is explainable.

`select_submission_primary(groups, snapshot, coverage_report)` builds the
per-family selections and the submission-level selection (candidate scope = the
union of every family's `required`).

## 2. Why observations cannot become primary

`OBSERVATION` concepts have registry `conclusion_eligible = False` (derived from
`class == STRATEGY`). The candidate filter requires `conclusion_eligible`, so an
observation is excluded **by metadata, not by a hand-written rule**. The B4 source
names no observation: `array_traversal`, `brute_force`, `sorting` and every
structural fact are excluded through the registry alone. Measured: a PRESENT
`accumulator_update` (a real structural-fact observation) yields zero candidates.

## 3. Why techniques cannot become primary

A `TECHNIQUE` may be `IDENTIFYING` and `PRESENT` (e.g. `hash_lookup`,
`candidate_selection`), so it can establish a family's identity — but its
registry `conclusion_eligible` is `False`, so it cannot enter the candidate pool.
B4 therefore never promotes a technique to a strategy merely because it has high
confidence, and the registry is not modified to make one eligible.

## 4. How registry metadata is used

Only the B1 registry is consulted:

- `conclusion_eligible` — the sole membership gate for the candidate pool;
- `specificity_rank` — the primary ordering key (derived from class + tier);
- `tier` — carried on each candidate for explanation;
- the B2 snapshot supplies `confidence` and `evidence_source` (secondary signal).

No new precedence table exists. There is no `if sliding_window: ... elif
binary_search: ...`; there is no semantic ranking such as "binary search beats
sliding window" or "DFS is more specific than BFS". No ordering is invented.

## 5. Family scoping

A strategy is never selected because it appears somewhere in the submission.
The candidate scope is exactly the evaluated family's `required` concepts (or the
union of the families' `required` for the submission-level selection). An
unrelated PRESENT strategy is not a candidate: measured, a sliding-window
`PRESENT` strategy does not activate a family whose `required` is
`sequential_accumulation`. This is the same relevancy principle as B3's
conclusion-eligible gate, reused rather than re-implemented.

## 6. Contradiction handling

Only an **applicable family-level** contradiction influences selection
(`family_contradicted`, taken from the B3 coverage report). A concept-level
`CONTRADICTED` does not blindly remove an otherwise-eligible candidate and does
not affect an unrelated family: in `WINDOW_209`, `binary_search` is
`CONTRADICTED` yet `sliding_window` is still selected. Because candidates must be
`PRESENT`, a contradicted concept is simply not a candidate, so an applicable
identifying contradiction yields no candidates and the family is reported
`CONTRADICTED` by B3 (which B4 does not rewrite).

## 7. Tie-breaking

Ordering is `(-specificity_rank, -confidence, concept_id)` — deterministic and
independent of input order. Specificity is registry metadata; confidence is a
secondary signal; `concept_id` is the final deterministic tie-break. A tie that
the registry cannot distinguish on specificity or confidence is surfaced as an
**explicit ambiguity** (`tie_broken_by_concept_id`) rather than dressed up as a
ranking. Verified by unit test: the same two strategies with equal confidence
select the same `concept_id` regardless of input order.

## 8. LC3236 analysis

Recorded Ground Truth requires only `sequential_accumulation` (a COMPONENT
technique). B3 already keeps the family `UNRESOLVED`. B4 therefore produces **no
submission candidate** and **no family candidate** for `db-49`, `db-51`, `db-194`
(`reason = no_conclusion_eligible_present`). No strategy is manufactured from
`sequential_accumulation` or `forward_pointer_advance`.

## 9. LC209 / LC102 / LC704 analysis

- **LC209** (`db-190`, `required = ["sliding_window"]`): `sliding_window`
  PRESENT and conclusion-eligible → selected `sliding_window`.
- **LC102** (`db-244`, `required = ["bfs_shortest_path"]`): selected
  `bfs_shortest_path`.
- **LC704** (`db-235`, `required = ["binary_search"]`): selected
  `binary_search` (the existing strategy taxonomy, not an arbitrary confidence
  winner).

## 10. LC1 / LC560 analysis

- **LC1** (`db-11`): the stored group has an empty `required` set and
  `hash_lookup` is a technique → no candidate, no selection. `hash_lookup` is
  **not** promoted.
- **LC560**: a `frequency_counting` + `sequential_accumulation` family has no
  conclusion-eligible concept → no candidate. The real 301 case
  `hm_subarray_sum_k` (`required = ["hash_lookup"]`) likewise selects nothing. No
  strategy is fabricated.

## 11. 46-case results

Reconstructed pre-B4 arm (B2/B3 kept, only B4 lines removed) vs post-B4:

| metric | value |
|---|---|
| deterministic-field mismatches | **0** |
| coverage distribution identical | **yes** |
| old-matcher outcome distribution identical | **yes** |
| submissions — exactly one candidate | 23 |
| submissions — multiple candidates | 0 |
| submissions — zero candidates | 23 |
| deterministic primary selected | 23 |
| ties broken by `concept_id` (ambiguity) | 0 |
| per-family — one / multiple / zero candidates | 23 / 0 / 28 |

Selected-strategy distribution: `sliding_window 7`, `two_pointers_opposite 5`,
`dp_bottom_up 3`, `binary_search 2`, `dfs_backtracking 2`, `dp_top_down 2`,
`bfs_shortest_path 1`, `union_find 1`.

## 12. 301-case results

Same reconstruction; each case's `required_concepts` is the family requirement.

| metric | value |
|---|---|
| deterministic-field mismatches | **0** |
| coverage distribution identical | **yes** |
| old-matcher outcome distribution identical | **yes** |
| submissions — exactly one candidate | 29 |
| submissions — multiple candidates | 0 |
| submissions — zero candidates | 272 |
| deterministic primary selected | 29 |
| ties broken by `concept_id` (ambiguity) | 0 |

Selected-strategy distribution: `two_pointers_opposite 27`, `binary_search 2`.

## 13. Unchanged B3 coverage results

Retained verbatim from B3 in both arms:

- 46: `{CONFIRMED 23, CONTRADICTED 1, UNMATCHABLE 11, UNRESOLVED 11}`;
- 301: `{CONFIRMED 29, PROVISIONAL 23, UNMATCHABLE 59, UNRESOLVED 190}`.

B4 is a selection layer: an `UNRESOLVED` or `PROVISIONAL` family does not become
`CONFIRMED` because a strategy was selected. No B3 rule was rewritten.

## 14. Unchanged legacy matcher results

Old `match_outcome` distribution identical before/after in both arms:

- 46: `{CONFIRMED 32, UNRESOLVED 14}`;
- 301: `{CONFIRMED 112, UNRESOLVED 189}`.

`match_outcome` remains intact and the old matcher's own nested
`primary_strategy` field is not overwritten. `matching.py` does not consume the
B4 selector.

## 15. Ambiguities that require architecture decisions

Reported, not resolved:

1. **No principled specificity among strategies.** Every `STRATEGY` shares
   `specificity_rank == 3`, so when several strategies are PRESENT the registry
   provides no specificity distinction; selection falls back to confidence and
   then `concept_id`, which is flagged as an ambiguity. **No corpus case produced
   multiple candidates**, so this is currently only reachable by construction —
   but the architecture cannot resolve it without a ratified specificity
   ordering (or per-family disambiguation) that does not yet exist.
2. **`hash_lookup`-family conclusion.** Technique-only families stay
   `PROVISIONAL` and select no primary. Whether a strategy concept should exist
   for them (or they remain permanently non-concluding) is a vocabulary decision.
3. **Submission-level vs family-level primary.** B4 reports both; which one is
   the user-facing "primary approach" is a presentation decision for a later
   batch.
4. **Authority interaction.** B4 ignores `authority_tier`; how authority gates a
   selected primary is B5 work.
5. **The old matcher's nested `primary_strategy`.** It is kept for
   cross-checking; deciding when (if ever) the two projections reconcile is
   later work.

---

**No corpus case requires an out-of-band decision to select a primary strategy.**
Every case with candidates had exactly one candidate; every multiple-candidate
path is flagged as an explicit ambiguity rather than silently ranked.

**STOP — B4 complete. B5 not started.**
