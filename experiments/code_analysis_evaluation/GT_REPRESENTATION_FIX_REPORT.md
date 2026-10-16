# Ground-Truth Representation Repair — alternatives must not collapse into a conjunction

**Scope:** the ground-truth representation/loading/refresh logic only. No
`frequency_counting`, no sort-form, no detector semantics change, no
`hash_lookup` change, no single-row DB patch, no problem-ID or name logic.

## 1. Exact root cause

A stored `problem_ground_truth.solution_groups` row may hold **one** group whose
flat `patterns` list contains several *alternative* approaches and no explicit
`required` concepts (problem 3236:

```json
{"id": "group_0", "evidence": "llm_proposed",
 "patterns": ["hash_map_lookup", "prefix_sum"],
 "confidence": {"prefix_sum": 0.85, "hash_map_lookup": 0.75}}
```

The loader re-derived that group's concepts by **merging every pattern's mapped
concepts into one `required` list**:

```
required = _map_legacy_patterns_to_v1(["hash_map_lookup", "prefix_sum"])
         = ["hash_lookup", "sequential_accumulation"]      # == AND, not OR
```

While `hash_map_lookup` mapped to nothing, the merge was invisible (it
degenerated to `["sequential_accumulation"]`). Vocabulary Layer 2 Step 2 gave
that pattern a concept, so the merge became a genuine **conjunction**: the group
could then only be satisfied by an implementation that both performs a mapping
lookup *and* accumulates — which none of the three submissions does. All three
had `sequential_accumulation`, so the `prefix_sum` alternative should still have
matched.

## 2. Exact file / function where the semantic loss occurred

| site | defect |
|---|---|
| `pathforge/services/problem_resolver.py` → `_load_ground_truth()` (stored-`solution_groups` branch, `required = _map_legacy_patterns_to_v1(legacy_patterns)`) | **The semantic loss.** Merges multi-family patterns into one conjunctive `required`, discarding "these are alternatives". The flat-pattern fallback path two lines below it (`_split_csv_patterns_to_groups`) already got this right, so the two representations disagreed. |
| `pathforge/services/ground_truth_builder.py` → `refresh_group_vocabulary()` (via `_derive_concepts_from_patterns`) | Re-derives a group's concepts by unioning all its patterns' concepts — could **re-create** the same conjunction for a multi-family group during the Batch 2A refresh. |
| three separate copies of the "primary concept" rule (`_split_csv_patterns_to_groups`, `_split_patterns_into_groups`, and the implicit merge) | Duplicated definitions of "same approach vs different approach" — the drift vector behind the disagreement. |

## 3. Files changed

| file | change |
|---|---|
| `pathforge/services/ground_truth_builder.py` | **New** `pattern_family()` — the single definition of a pattern's solution family — and `patterns_span_multiple_families()`. `refresh_group_vocabulary()` now returns early for multi-family groups so the refresh can never re-create a conjunction. `_split_patterns_into_groups()` now uses `pattern_family()`. |
| `pathforge/services/problem_resolver.py` | `_load_ground_truth()` stored-group branch now keeps explicit `required` authoritative and, for vocabulary-derived groups, expands multi-family patterns into the same alternative groups the flat-pattern fallback derives (per-family `required`/`excluded`/`patterns`). `_split_csv_patterns_to_groups()` now uses `pattern_family()`. |
| `pathforge/ast_analysis/shadow/tests/test_gt_representation_alternatives.py` | **new**, 22 generalized regression tests |

No DB row was edited. (Measurement artifacts landed in
`results/vocab2_step2_gtfix/`.)

## 4. Why the fix is generic, not problem-specific

- **No problem IDs, no pattern-name hard-codes, no submission identities.** The
  decision is driven entirely by `pattern_family()` / `_derive_concepts_from_patterns`
  over whatever patterns a group carries.
- It reuses the repository's **existing** convention for alternatives
  (`_split_csv_patterns_to_groups`, the flat-pattern fallback) instead of
  inventing a heuristic, and makes the stored path call it — the two
  representations now converge by construction.
- It does **not** assume every multi-item list is alternative: patterns that map
  to the *same* family still merge into one group (existing behavior), and a
  group with explicit `required` is preserved exactly — so a genuine conjunction
  still requires all its concepts.
- It is **DB-wide blast-radius zero** outside the defect: a sweep of all **103**
  live `problem_ground_truth` rows found exactly **one** (3236) that is
  vocabulary-derived **and** multi-family — the only row whose loaded semantics
  change. The other 102 are untouched (single-family, explicit `required`, or no
  `solution_groups`).

## 5. Tests added (22)

`test_gt_representation_alternatives.py` — a fake-connection harness drives the
real `_load_ground_truth`:

- **Alternatives not conjunction:** two-family patterns load as two groups; no
  group requires both; per-family `patterns`/`excluded` retained; a
  provenance-marked group is still expanded.
- **Fallback convergence:** loaded groups' `(required, optional, excluded)`
  signature equals `_split_csv_patterns_to_groups`; `pattern_family()` is the
  shared definition; single-family patterns still merge.
- **Real submissions:** three LC-3236-shaped implementations all CONFIRMED
  against the repaired groups; a control asserts the *conjunctive* representation
  is what produced UNRESOLVED.
- **Authoritative structured groups:** genuine conjunction preserved; explicit
  `required`/`optional`/`excluded` preserved exactly.
- **Batch 2A invariants:** an unmapped single-pattern group stays
  `matchable=False` with a reason; `refresh_group_vocabulary` refuses to collapse
  a multi-family group but still refreshes a single-family one.
- **`hash_lookup` unchanged:** still detected for a mapping lookup, still absent
  for set membership.
- **Genericity/consistency:** derivation is problem-ID independent; flat patterns
  and structured groups produce no `pattern_not_in_groups` /
  `group_pattern_not_declared` / `concept_not_derived_from_patterns` /
  `unmatchable_group` disagreement.

## 6. New / shadow / full-repo results

| suite | result |
|---|---|
| New tests | **22 passed** |
| Shadow suite | **690 passed** (668 → +22) |
| Full repository | **1564 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` failure (`src/ast_detection/tests/test_detectors_batch2.py`) |

## 7. 46-record before/after (fingerprint-matched; BEFORE = `vocab2_step2`, AFTER = `vocab2_step2_gtfix`)

| | BEFORE | AFTER |
|---|---|---|
| CONFIRMED | 35 | **38** |
| UNRESOLVED | 11 | **8** |
| CONTRADICTED / ERROR | 0 / 0 | 0 / 0 |

**Verdict changes: exactly 3, all recoveries.** **Technique changes: 0.**
**Strategy changes: 0.** **False confirmations: 0. False contradictions: 0.**

## 8. db-49 / db-51 / db-194

All three: `UNRESOLVED → CONFIRMED`, recovered through the new alternative
`prefix_sum` group (`group_0_alt1`, `required=["sequential_accumulation"]`) — not
through new evidence (their technique sets are byte-identical before/after). The
group required changed from `["hash_lookup","sequential_accumulation"]` (one
conjunctive group) to `["hash_lookup"]`, `["sequential_accumulation"]` (two
alternative groups).

## 9. Any other records changed

**None.** db-11 / db-33 / db-39 remain CONFIRMED; all Step 2 negative records
(db-35, db-230, db-49/51/194, db-193, db-238/240) keep their prior evidence;
no record's technique or strategy evidence changed.

## 10. Do flat `patterns` and structured `solution_groups` now converge?

**Yes.** For the affected row the stored-group path now produces the same
signature as the flat-pattern fallback (`_signature(loaded) ==
_signature(_split_csv_patterns_to_groups(...))`, asserted in the tests), and
`find_ground_truth_disagreements` reports no drift between the two
representations. All three derivation sites now share one `pattern_family()`
definition, so they cannot diverge again by copy-drift.

## 11. Safe for Step 3?

**Yes.** The repair is a representation fix (not an algorithmic recovery — the
recovered records are a consequence of correct alternative grouping, not of new
detection). Blast radius is DB-wide provable-zero outside the one defective row,
all suites are green except the known legacy failure, and the stored and flat
representations are now guaranteed to agree. Step 3 (`frequency_counting`) can
proceed on this foundation.
