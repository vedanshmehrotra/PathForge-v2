# Design Survey v2 — Vocabulary Layer 2 (revised): `candidate_selection`, `hash_lookup`, `frequency_counting`

**Read-only revision. No code modified. Supersedes `VOCABULARY_LAYER2_DESIGN.md` (v1, preserved for history).**

## 0. What changed and why

v1 allowed `set` construction/membership to satisfy both `hash_map_lookup` and `frequency_counting`. That was semantically wrong and is corrected here:

- **A set is not a frequency structure.** `sett = set(nums)` + `k*i not in sett` (db-64) is membership *search*, not counting. v1 would have forced it into `frequency_counting`.
- **A set is not a key→value map.** `if n in seen` over `seen = set()` (db-230) is visited-tracking, not map lookup. v1 would have forced it into `hash_map_lookup`.

All definitions below were re-verified by in-memory AST probes over the corpus records and synthetic edge cases (S1–S7). Container-kind probe results (exact, from the probes):

| record | construction | membership | indexed writes | reads |
|---|---|---|---|---|
| db-11 | `seen = {}` → **dict_empty** | `complement in seen` | assign-form | `seen[complement]` |
| db-39 | `num_map = {}` → **dict_empty** | `oth_num in num_map` | assign-form | `num_map[oth_num]` |
| db-33 | `hashm = {…}` → **dict_literal** | — | — | `hashm[s[i]]` in **elif-comparisons** |
| db-41 | `freq = Counter(s)` → **Counter(data)** | — | — | `freq[i]` incl. in `if` condition |
| db-64 | `sett = set(nums)` → **set(data)** | `k*i not in sett` | — | — |
| db-192 | `cnt1/cnt2 = [0]*26` → **list_mult** | — | **aug-form ×4** (BinOp index) | — |
| db-230 | `seen = set()` → **set()** | `n in seen` | — | — |
| db-35 | `lst` list-literal | `x not in lst` | — | — |
| db-49/51/194 | none (membership over input `nums`) | `nums` | — | — |
| db-138 | `n = Counter()` → **Counter()** | — | aug-form (Subscript index) | `n[...]` |
| db-191 | `freq = {}` → **dict_empty** | — | assign + aug-form | `freq[...]` |
| db-193 | `mp = {}` → **dict_empty** | — | assign-form (Call value) | — |
| S1 | `d = defaultdict(int)` → **defaultdict(data)** | — | aug-form | — |
| S2 | `seen = {}` dict as visited | `n in seen` | assign-form | — |
| S3 | `dp = {}` iterative dp-dict | — | assign-form ×3 (cross-key reads) | `dp[i-1]` |
| S5 | `sett = set(nums)` | `k*i not in sett` | — | — |
| S6 | none (membership over list `nums`) | `t - x in nums` | — | — |

---

## 1. Shared primitive: `mapping_construction` (new name-free fact)

**What counts as mapping construction** — an `ast.Assign` of a `Name` target to one of, with a recorded `kind`:

| kind | forms | is a key→value map |
|---|---|---|
| `dict_empty` | `x = {}` (ast.Dict, no keys) | yes |
| `dict_literal` | `x = {'I': 1, …}` | yes |
| `dict` | `x = dict()`, `dict(pairs)` | yes |
| `defaultdict` | `x = defaultdict(...)` | yes |
| `Counter` | `x = Counter(s)`, `x = Counter()`, `collections.Counter(...)` | yes (counting map) |
| **`set` / set-literal / list / list_mult** | `set()`, `set(xs)`, `{a, b}`, `[]`, `[0]*n` | **NO — excluded from the fact entirely** |

Sets, set literals, lists and `[0]*n` multiplications produce **no `mapping_construction` fact at all** (not a fact with `kind="set"` — absence, not a weaker kind). This is the structural guarantee behind both corrections: a set can never satisfy a map-typed requirement because it never produces map-typed evidence.

## 2. `hash_lookup` (technique) — revised definition

**Semantics:** key→value map lookup — a read of `m[key]` (or `m.get(key)`), whose result is *gated* by a membership test or a condition.

**Minimum structural evidence (all required):**
1. **Mapping identity:** variable has `mapping_construction` with `kind ∈ {dict_empty, dict_literal, dict, defaultdict}`. **`Counter` does NOT qualify** for lookup (it is the counting identity; its reads may serve as *optional* support for frequency, not lookup).
2. **Gated read:** membership test over that variable (`ast.Compare` with `In`/`NotIn` — new name-free fact `membership_test {variable, negated}`) **or** a subscript read of that variable appearing inside an `If`/`While` test subtree or comparison. Verified present: db-11/db-39 (membership + `seen[complement]` read), db-33 (`hashm[s[i]] > hashm[s[i-1]]` in elif comparison).

**Excluded:** `recursive_branching` (memoization fence — dp-memo negative has identical shape otherwise).

**Set membership treatment:** a membership test over a **set** (or a list, or an input array) does **not** count — requirement 1 fails because no `mapping_construction` fact exists for it. `membership_test` as a *fact* is form-agnostic, but the technique joins it to mapping-typed variables only.

**Counter/dict/defaultdict handling:** dict family + defaultdict = lookup identity; Counter = frequency identity (explicitly removed from lookup's kinds in this revision); sets = neither.

**Covers:** db-11, db-33, db-39 (the 3 blocked records). **No longer claims:** db-230 (set), db-35 (list), db-49/51/194 (input-array membership) — v1 would have added noise evidence here; all are already CONFIRMED via their real strategies, so nothing is lost.

## 3. `frequency_counting` (technique) — revised definition

**Semantics:** tallying occurrences — counting how many times each distinct value/key appears.

**Minimum structural evidence** — one of two branches, per variable:

- **Branch A (counting map):** `mapping_construction` with `kind ∈ {Counter, defaultdict, dict_empty, dict_literal}` **plus** an indexed write in **augmented form with Add/Sub operator** on that variable (`d[x] += 1`, S1; db-138 `n[...] += 1`; db-191). For `Counter(data)` construction, construction alone suffices as identity but at least one counted read (`m[key]` in an expression/condition) or counted write is still required (db-41: reads `freq[i]//2`, `freq[i]%2` in a condition ✓).
- **Branch B (pre-sized count array):** variable constructed as `list_mult` (`[0] * 26`) **plus** an augmented-form Add/Sub indexed write with a **keyed index** (`cnt2[ord(s[i]) - ord('a')] += 1`, index_type BinOp — db-192 ✓).

**Why Branch B does not leak into DP:** the dp-array negative (`dp = [0]*(n+1)`, `dp[i] = dp[i-1]+dp[i-2]`) writes in **assign form with cross-key reads** — no augmented writes at all (verified). The form distinction (assign vs augmented) plus Add/Sub operator is the fence. Documented residual: an exotic `dp[i] += dp[i-2]` dp would need a cross-key-read fence (write RHS reads the same structure at a different key) — detectable, deferred unless real cases appear.

**How `cnt[x] += 1` is handled:** augmented indexed write, operator Add/Sub, any index shape — the canonical counting primitive. Requires the variable to be map- or pre-sized-array-constructed, so a stray `total += arr[i]` (accumulator, not subscripted target) never qualifies.

**Set membership treatment:** **sets are not frequency structures and never satisfy any branch.** `sett = set(nums)` produces no `mapping_construction` fact; membership is not counted evidence.

**Covers:** db-41 (A), db-192 (B), S1; evidence gains without verdict change on db-138 (already CONFIRMED via sliding_window), db-191 (same).
**Intentionally NOT covered:** db-64 (set) — see §5.

## 4. `candidate_selection` (technique) — unchanged by this correction

The set-membership issue does not touch greedy (its positives have no sets, membership tests, or maps: verified — db-18/36/37/255/256 produce no container/membership facts at all). v1 definition stands:

- **Loop form (no new facts):** `for_loop_iteration` ∨ `while_loop_comparison`, plus `conditional_index_update` whose `updated_variables` are all **non-index** (M2 `used_as_subscript_index` join — the F4-tested fence separating greedy from sliding-window/pointer state). Covers db-255, db-256, db-37.
- **Sort form (needs the `sorting_operation` fact, phase 4):** `.sort()`/`sorted()` + bounded extremum reads. Covers db-18, db-36 (both produce only `subscript_index_access` + `early_termination` today — nothing else is honestly available).

`excluded: [sliding_window]` stands; no corpus greedy-positive fires sliding_window and no window positive loses index participation.

## 5. Set membership — no new concept (decision)

Evidence does not require one:

- db-64 is the **only blocked record** whose implementation is set-based. Its true semantics ("scan multiples until one is absent from the set") has no GT label in the taxonomy; v1's plan to push it into `frequency_counting` would have been a misconfirmation waiting to happen — exactly the class of false-confirmation the project's quality bar forbids.
- db-230 (set-as-visited) already CONFIRMS via sliding_window; db-35/db-49 confirm via their own strategies.
- **Decision: no `set_membership` concept now.** db-64 intentionally remains UNRESOLVED — a truthful refusal, same category as LC 2212/4284 (GT/implementation divergence). Revisit only if a future fresh batch shows a recurring blocked set-based family; it would then get its **own** concept and GT label, never be folded into map lookup or counting.

## 6. GT mapping (revised, changed cells bold)

```
"hash_map_lookup":    required=["hash_lookup"],        excluded=["recursive_branching"]
"hash_map_frequency": required=["frequency_counting"], optional=["hash_lookup"], excluded=["recursive_branching"]
"greedy_local":       required=["candidate_selection"], optional=["sorting_operation"], excluded=["sliding_window"]
```
`mapping_construction` `kind` is an attribute on one fact (no per-kind vocabulary); `VALID_TECHNIQUES` gains `hash_lookup`, `frequency_counting`, `candidate_selection` (+ later `sorting_operation`). Batch 2A refresh re-derives stored groups automatically.

## 7. Expected affected records (prediction, post-correction)

After steps 1–3 (candidate_selection, hash_lookup, frequency_counting):

| outcome | records | why |
|---|---|---|
| **Verdict flips (UNRESOLVED → CONFIRMED)** | db-11, db-33, db-39 (lookup); db-41, db-192 (frequency) | 5 flips; corpus 32/14 → **37/9** |
| Stays UNRESOLVED **by design** | db-64 (set semantics, no honest label); db-18, db-36 (until sort-form step 4); db-37, db-255, db-256 (until step 1 lands); db-251, db-253, db-254 (known non-vocabulary causes) | truthful refusals |
| Evidence-only gains (verdicts unchanged) | db-138, db-191 (+frequency technique), db-41 (+optional hash_lookup support via gated Counter read) | alternative-group semantics |
| **Must show zero change (negatives)** | db-35, db-230, db-49/51/194, db-193 (no new technique evidence — v1 would have fired here; v2 must not); db-238/240 (recursion fence); all sliding-window/dp/two-pointer/binary-search regressions (index fence) | the correction's acceptance test |

## 8. Implementation order (revised numbering, same sequence)

1. `candidate_selection` loop form — 0 new facts, 3 records, F4-tested fence.
2. `mapping_construction` + `membership_test` facts and `hash_lookup` — 3 flips; **negative battery now explicitly includes db-35/db-230/db-49/db-193 zero-evidence-change assertions** (the v2 correction's core test).
3. `frequency_counting` (Branch A + B) — 2 flips + 2 evidence-only; db-64 must remain UNRESOLVED (assert this).
4. `sorting_operation` fact + sort-form greedy — 2 flips (db-18, db-36).

Same validation loop per step: new generalized tests → shadow suite → full repo suite → 46-record before/after with per-record expected-change table above.

## 9. Safety verdict

**Enough evidence to implement safely — and safer than v1.** The correction removes v1's two semantic over-reaches (set→frequency, set→lookup); every remaining positive is map/Counter/count-array-typed with verified kind attribution, every negative has a kind- or form-level structural fence, and one record (db-64) is now honestly expected to stay UNRESOLVED rather than be force-matched. Machinery unchanged: two new name-free facts + one technique-layer batch; small extension, no architectural change.
