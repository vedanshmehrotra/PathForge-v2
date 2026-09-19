# Vocabulary Layer 2 — Step 3: `frequency_counting`

**Scope honored:** `frequency_counting` only. No sort-form candidate selection,
no `candidate_selection`/`hash_lookup` semantics change, no frequency strategy, no
problem-ID or variable-name logic, no set folding, no DB row edits, no test
weakening.

## 1. Files changed

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | backward-compatible `syntax_form` + `operator` attributes on the existing **`indexed_write`** fact (both the Assign and AugAssign detectors); **one new fact type** `list_construction` (`kind: "list_mult"`) emitted from `visit_Assign`/`visit_AnnAssign` for `x = [..] * n` |
| `pathforge/ast_analysis/shadow/techniques.py` | new `_detect_frequency_counting` (T14), registered in `detect_techniques`; docstring T14 |
| `pathforge/services/ground_truth_builder.py` | `frequency_counting` added to `VALID_TECHNIQUES` (13); `hash_map_frequency` mapping → `required=["frequency_counting"], optional=["hash_lookup"], excluded=["recursive_branching"]` |
| `pathforge/ast_analysis/shadow/tests/test_vocab2_frequency_counting.py` | **new**, 41 generalized tests |
| `test_phase4a_enrichment.py`, `test_regression_vocabulary_mismatch.py`, `test_vocab2_hash_lookup.py` | three expectations that pinned `hash_map_frequency` as unmapped updated to the new mapping / tripwire count 12→13, 21→22 (stronger assertions, not weakened) |

## 2. Was a new fact type necessary?

**Partly.** Exactly **one** new fact type (`list_construction`) was genuinely
necessary: no existing fact represented `[0] * n` (Step 2 deliberately emits
nothing for lists, and `mapping_construction` excludes them), so Branch B had no
construction evidence to consume. The operator/form information the design hoped
could ride on an existing fact **did** — `syntax_form`/`operator` were added as
backward-compatible attributes to `indexed_write`, exactly as the design
preferred, rather than introducing a second new fact type.

## 3. Exact semantics of `frequency_counting`

Structural evidence of a tally of occurrences by key/value. Two branches, both
name-free:

**Branch A — counting map.** A `mapping_construction` with
`kind ∈ {Counter, defaultdict, dict_empty, dict_literal, dict}` **plus** a
**counted write**: an `indexed_write` on that same variable with
`syntax_form == "augmented"` and `operator ∈ {Add, Sub}` (`cnt[x] += 1`,
`cnt[x] -= 1`). `Counter(data)` establishes counting identity by construction, so
it needs one counted write **or** one counted read (a `subscript_read` — a keyed
read that gates control flow, e.g. `if freq[i] % 2 != 0`).

**Branch B — pre-sized count array.** A `list_construction` of kind `list_mult`
(`cnt = [0] * 26`) **plus** a counted write on that variable whose `index_type`
is **not** positional (`Name`/`Constant`) — i.e. a keyed index
(`cnt[ord(ch) - ord('a')] += 1`). The positional exclusion is what keeps
`dp[i] += dp[i-2]`-style tables out.

Excluded: `recursive_branching` (memoization fence). No variable names are used.

## 4. Branch A implementation

Counted writes are indexed by `structure` from `indexed_write` facts filtered to
`augmented` + Add/Sub; counted reads are indexed by `structure` from
`subscript_read`. For each map-kind `mapping_construction`, a counted write
satisfies it; for `Counter` specifically, a counted read also satisfies it.
Confidence 0.8 / centrality 0.7.

## 5. Branch B implementation

`list_construction` facts of kind `list_mult` are joined with a counted write on
the same variable; the write's `index_type` must not be `Name`/`Constant`. No
separate pre-sizing check is needed beyond the fact itself.

## 6. Tests added (41) and results

`test_vocab2_frequency_counting.py`: **10 positives** (`Counter(data)` + counted
read; `Counter()` + counted write; `defaultdict(int)`; plain `{}`; dict literal;
`[0]*n` + keyed count; Add and Sub; non-obvious names; BinOp and Call keyed
indices; AnnAssign list construction) with evidence-citation checks;
**11 negatives** (set construction/membership, ordinary dict assignment, scalar
accumulation, DP bottom-up array, recursive memo, plain `[0]*n` without count
update, indexed assignment without AugAssign, unrelated membership, unused
Counter, list accumulation, positional-index pre-sized array); **4 fact-semantics**
tests (`syntax_form`/`operator`, `list_construction` only for `list_mult`, lists
still produce no `mapping_construction`); **3 relation-contract** tests (relations
neither create nor change the detection; a synthetic relations bundle cannot
fabricate it); **4 vocabulary** tests.

| suite | result |
|---|---|
| New tests | **41 passed** |
| Shadow suite | **731 passed** (690 → +41) |
| Full repository | **1605 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` failure |

## 7. 46-record before/after (fingerprint-matched; BEFORE = `vocab2_step2_gtfix`, AFTER = `vocab2_step3`; groups from live DB)

| | BEFORE | AFTER |
|---|---|---|
| CONFIRMED | 38 | **40** |
| UNRESOLVED | 8 | **6** |
| CONTRADICTED / ERROR | 0 / 0 | **0 / 0** |

## 8. Exact changed records

**Verdict flips — exactly the 2 the design predicted:**

| record | problem | evidence causing the change |
|---|---|---|
| db-41 | LC 3812 Smallest Palindromic Rearrangement I | `freq = Counter(s)` (Counter identity) + gated counted read `freq[i] % 2 != 0` → `frequency_counting` → group_0 satisfied (`required=['frequency_counting']`) |
| db-192 | LC 438 Find All Anagrams | `cnt1/cnt2 = [0] * 26` (`list_mult`) + keyed `cnt[…ord…] += 1` / `-= 1` → Branch B `frequency_counting` → group_0 satisfied |

**Evidence-only changes (verdict unchanged):** db-138, db-191 (both predicted)
**and db-189** — all sliding-window submissions that genuinely tally occurrences
(`Counter` with an augmented indexed count write), so they now also carry
`frequency_counting` as non-exclusive evidence. db-189 was not listed in the
design's evidence-only set; its GT label is `sliding_window_variable` only, and
its verdict is unchanged.

**No record lost a technique. No record acquired any technique other than
`frequency_counting`. Strategy changes: 0. False confirmations: 0. False
contradictions: 0. Unrelated changes: 0.**

The only fact-type change in the corpus is the new `list_construction` fact on
db-192, db-237, db-239, db-246 — of those, only db-192 has a keyed counted write,
so the other three are inert fact additions with no downstream effect.

## 9. Requested status checks

- **db-64** (set-based, the design's intentional hold-out): **still UNRESOLVED.**
  Its group now correctly requires `frequency_counting`, and the set
  implementation produces none — a truthful refusal, not a false confirmation.
- **db-238 / db-240** (recursive memo): **unchanged** (`recursive_branching`
  fence; their memo writes are plain assignment, not counted writes).
- **db-138 / db-191**: gained `frequency_counting`; both remain **CONFIRMED** via
  their existing `sliding_window` strategy.
- Zero-change battery **db-35 / db-230 / db-49 / db-51 / db-194 / db-193**: all
  **unchanged** (no frequency evidence, no verdict movement). Sliding-window, DP,
  two-pointer, binary-search and BFS submissions acquired no unrelated frequency
  evidence — the only strategy-family submissions carrying it are db-138/189/191,
  which legitimately use frequency maps.

## 10. Two disclosed deviations from the Step 3 brief

1. **db-41 does not gain optional `hash_lookup` evidence.** Step 2's explicit
   rule (which the Step 3 brief also says not to revisit) excludes `Counter` from
   lookup identity, so a Counter read is not lookup evidence. db-41 flips on
   `frequency_counting` alone. Granting it would have required reopening
   `hash_lookup`.
2. **The `Counter` "counted read" is the existing gated `subscript_read`.** To
   honour "reuse existing facts" and "do not modify `hash_lookup`", Step 2's
   `subscript_read` fact (a keyed read that gates control flow) was reused
   unchanged. A `Counter` used *exclusively* with ungated reads and no counted
   write is therefore not detected; db-41 qualifies through its condition read
   (`freq[i] % 2 != 0`), which is exactly the evidence the v2 design cited for
   it. Widening `subscript_read` to all reads would require adding a `gated`
   guard to `hash_lookup` — a Step 2 change this batch was told not to make.

## 11. Verdict

Step 3's blast radius matched the design exactly: 2 predicted flips, 3
evidence-only gains, 0 losses, 0 strategy changes, 0 false confirmations, 0 false
contradictions, and the set-based hold-out remains truthfully UNRESOLVED. The
corpus is now **40 CONFIRMED / 6 UNRESOLVED**. Stopped here — sort-form
candidate selection (Step 4) was not implemented.
