# Vocabulary Layer 2 — Step 2: `hash_lookup`

**Scope honored:** `hash_lookup` + the map-kind vocabulary it needs only. No
`frequency_counting`, no sort-form, no `greedy` strategy, no set-based identity,
no set-based frequency semantics, no problem-ID logic, no variable-name
allowlists, no legacy-matcher changes, no ground-truth data edits.

## 1. Files changed

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | 3 new **name-free** facts: `mapping_construction`, `membership_test`, `subscript_read`; new `visit_If`, `visit_Compare`, gated-read hook in `visit_While`; construction hook in `visit_Assign`/`visit_AnnAssign` |
| `pathforge/ast_analysis/shadow/techniques.py` | new `_detect_hash_lookup` (T13), registered in `detect_techniques`; docstring T13 |
| `pathforge/services/ground_truth_builder.py` | `hash_lookup` added to `VALID_TECHNIQUES` (12); `hash_map_lookup` mapping → `required=["hash_lookup"], excluded=["recursive_branching"]` |
| `pathforge/ast_analysis/shadow/tests/test_vocab2_hash_lookup.py` | **new**, 31 generalized tests |
| `pathforge/ast_analysis/shadow/tests/test_phase4a_enrichment.py` | vocabulary tripwire 11→12 / 20→21; `hash_map_lookup` mapping test replaced; `hash_map_frequency` still-unmapped assertion added |
| `pathforge/ast_analysis/shadow/tests/test_batch2a_ground_truth_consistency.py` | unmapped-pattern fixtures re-pointed to patterns that are still unmapped |
| `pathforge/ast_analysis/shadow/tests/test_regression_vocabulary_mismatch.py` | `hash_map_lookup` mapping expectation updated; `hash_map_frequency` still-unmapped assertion added |
| `pathforge/ast_analysis/shadow/tests/test_sliding_window_fixes.py` | `test_same_strategy_patterns_merged` fixture reused `hash_map_lookup` as an *unmapped* filler; replaced with `sliding_window_fixed` (intent preserved: two same-strategy patterns merge) |

Two new fact types were **not** avoidable: the design's lookup evidence is
"membership test **or** gating subscript read", and the fact layer had neither
(`cache_lookup`/`visited_tracking` are name-gated; `subscript_index_access`
records only index variables, never the structure, and has no notion of gating).
Mutating an existing fact's attributes instead would have fed the generic
attribute scan in `loop_state_tracking` and risked unrelated evidence drift.

## 2. Exact semantics of `mapping_construction`

An `Assign`/`AnnAssign` of a `Name` target to one of, with a recorded `kind`:

| value form | kind |
|---|---|
| `{}` | `dict_empty` |
| `{k: v, ...}` | `dict_literal` |
| `dict(...)` | `dict` |
| `defaultdict(...)` | `defaultdict` |
| `Counter(...)` / `collections.Counter(...)` | `Counter` |

**No fact is emitted at all** for sets, set literals, lists, `[0] * n`,
comprehensions, or any other call — absence, not a weaker kind. A set therefore
can never satisfy a map-typed requirement.

## 3. Exact semantics of `hash_lookup`

All of:

1. `mapping_construction` for a variable with `kind ∈ {dict_empty, dict_literal,
   dict, defaultdict}` — **`Counter` excluded** (counting identity); and
2. lookup evidence **tied to that same variable**:
   - `membership_test` on it (`k in m` / `k not in m`), or
   - `subscript_read` on it — a keyed read whose result **gates control flow**
     (`if m[k] > x`; ungated reads used for arithmetic/aggregation do not count).

Excluded: `recursive_branching` — a dict used as a recursion memo has the same
construction + membership shape, so the recursion concept is an explicit fence
(same concept the GT mapping names as `excluded`). No variable names are used.

## 4. Tests added (31) and suite results

`test_vocab2_hash_lookup.py`: 9 positives (membership lookup, gated literal read,
non-obvious names, defaultdict, `dict()`, AnnAssign form, relations-parity,
evidence citations), 12 negatives (set / set-literal / list / input-array
membership, write-only + `.get` map, ungated read, Counter-alone,
Counter-membership, recursive memo, recursion without map, map-like names
without map structure, unrelated membership), 5 fact-semantics, 5 vocabulary.

| suite | result |
|---|---|
| New tests | **31 passed** |
| Shadow suite | **668 passed** |
| Full repository | **1542 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` failure (`src/ast_detection/tests/test_detectors_batch2.py`) |

## 5. 46-submission before/after (fingerprint-matched; BEFORE = `vocab2_step1`, AFTER = `vocab2_step2`; groups from live DB)

| | BEFORE | AFTER |
|---|---|---|
| CONFIRMED | 35 | 35 |
| UNRESOLVED | 11 | 11 |
| CONTRADICTED / ERROR | 0 / 0 | 0 / 0 |

**3 verdict flips — exactly the 3 records the v2 design predicted:**

| record | problem | evidence causing the change |
|---|---|---|
| db-11 | LC 1 Two Sum | `seen = {}` (dict_empty) + `complement in seen` → `hash_lookup` → group_0 satisfied 0.800 |
| db-33 | LC 13 Roman to Integer | `hashm = {...}` (dict_literal) + `hashm[s[i]] > hashm[s[i-1]]` gated read → satisfied 0.800 |
| db-39 | LC 1 Two Sum | `num_map = {}` + `oth_num in num_map` → satisfied 0.800 |

**Technique-evidence-only changes (same verdict): 0.** **Strategy changes: 0.**
**False confirmations: 0. False contradictions: 0.**
**Fact-type changes: only the 3 new fact types, in 27 records; no existing fact
type changed anywhere in the corpus.**

**Zero-evidence-change battery (v2 design's core acceptance test): PASSED.**
db-35, db-230, db-49, db-51, db-194, db-193, db-238, db-240 gain **no**
`hash_lookup` evidence (the fences hold: set/list/input membership → no map
identity; write-only map → no tie; ungated reads → not lookup; `Counter` →
excluded; recursion memo → fenced).

## 6. ⚠ Three verdict regressions — and why I stopped

db-49, db-51, db-194 (three submissions of **problem 3236**, LC 3236 Smallest
Missing Integer) went **CONFIRMED → UNRESOLVED**. They gained no new technique
evidence; the regressions are entirely a defect in the **stored ground-truth
group representation**, exposed — not created — by this change.

Exact mechanism (verified against the live DB):

- `problem_ground_truth` for 3236 stores `solution_groups` as **one** group
  with `patterns: ['hash_map_lookup', 'prefix_sum']`, **no `required`**, and
  **no `provenance` marker**.
- `_load_ground_truth`'s stored-group branch therefore computes
  `required = _map_legacy_patterns_to_v1(patterns)` = `['hash_lookup',
  'sequential_accumulation']` — i.e. it **conjoins two alternative legacy
  patterns into one AND-requirement**. Before this step, `hash_map_lookup`
  mapped to nothing, so the conjunction degenerated to
  `['sequential_accumulation']` and was satisfied.
- The production **fallback** splitter already does the right thing:
  `_split_csv_patterns_to_groups(['hash_map_lookup','prefix_sum'])` →
  `group_0 required=['hash_lookup']`, `group_1 required=['sequential_accumulation']`
  (alternatives, as the architecture specifies).
- All three submissions have `sequential_accumulation`, so with the correct
  representation they satisfy `group_1` and remain CONFIRMED. **Verified
  in-memory (no code change)**: evaluating db-49/db-51/db-194 against
  `_split_csv_patterns_to_groups(['hash_map_lookup','prefix_sum'])` yields
  `CONFIRMED` via `group_1` for all three.

Scope: **exactly one stored GT row** in the corpus has a merged-required group
(problem 3236); no other record's groups changed. The fix is a single,
generalized, problem-ID-free change (route vocabulary-derived stored groups
whose patterns map to more than one distinct concept through the existing
alternative splitter, or split a merged group at derivation time).

**Per the instruction to stop and report a blast-radius discrepancy rather than
expand the fix, I did not apply it.** This batch therefore has 3 gains and 3
losses (net 0) instead of the design's clean 3 flips.

## 7. Discrepancies vs the stated Step-2 expectation

1. **"6 evidence-only technique changes" — measured 0.** That figure is the
   *superseded v1* count: it counted db-35, db-230, db-49/51/194, db-193, which
   the v2 correction explicitly turned into **zero-change negatives**. v2's
   gates hold; the number is stale, not a shortfall.
2. **"no unrelated strategy changes" — confirmed (0).**
3. **The v2 negative battery listed db-49/51/194 as "must show zero change".**
   This holds at the *evidence* level (no `hash_lookup` gained) but **not** at
   the *verdict* level, because of the 3236 conjunctive-merge defect above.

## 8. Verdict

Step 2's detector is correct and its blast radius is exactly as designed: 3
gains, 0 spurious evidence, all fences (map identity, Counter, lookup tie,
gating, recursion) verified on real code and in 31 tests. The only blocker to a
clean result is the pre-existing 3236 group-representation defect.

**Recommendation:** do not proceed to Step 3 until the 3236 representation fix
is decided (a small, isolated, generalized fix, not a GT data edit). Once it
lands, Step 2 measures as 3 flips / 0 losses and Step 3
(`frequency_counting`) can proceed on that foundation.
