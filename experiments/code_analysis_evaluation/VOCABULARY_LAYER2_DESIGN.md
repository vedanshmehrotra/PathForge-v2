# Design Survey — Vocabulary Layer 2: `greedy_local`, `hash_map_lookup`, `hash_map_frequency`

**Read-only survey. No code modified. All claims below are verified against the current tree and the 46-record corpus fact inventories.**

---

## 0. Ground rules established by the evidence

Post-M1/M2, the residual 14 UNRESOLVED records are dominated by three expected-pattern labels with **no V1 concept** (mapping `required: []` in `ground_truth_builder.PATTERN_TO_V1_MAPPING`, so their groups derive unmatchable):

| expected pattern | records where expected | records actually blocked by it |
|---|---|---|
| `hash_map_lookup` | 9 (db-11, 33, 35, 39, 49, 51, 193, 194, 230) | 3 (db-11, db-33, db-39) |
| `hash_map_frequency` | 5 (db-41, 64, 138, 191, 192) | 3 (db-41, db-64, db-192) |
| `greedy_local` | 5 (db-18, 36, 37, 255, 256) | 5 (all blocked) |

Important nuance: 6 of the 9 `hash_map_lookup` records and 2 of the 5 `hash_map_frequency` records already CONFIRM via a *co-listed* primary strategy (sliding_window / monotonic_stack / prefix-sum groups). Only the blocked records need the new concepts; the others gain technique evidence without changing verdicts.

**Verified fact-layer ground truth (all probed on the real corpus code):**

- `_detect_cache_lookup` (fact_extractor.py:951) is **name-gated** (`cache/memo/dp/table/visited/seen/...`). db-11's `seen` fires only by luck; db-39's `num_map` gets **no lookup fact**. Not a usable foundation.
- `_detect_parent_root_merge` (:1380) is name-free but shape-overbroad: it fires on **any** `m[k] = v` (db-11/db-39 hash writes trigger it; verified `parent_root_merge: structure='seen'` on two-sum). Existing noise, no verdict damage (union_find strategy requires more), but it must not be reused as lookup evidence.
- **No membership-test fact exists**: `complement in seen`, `oth_num in num_map`, `k*i not in sett` produce **nothing** today.
- **No mapping-construction fact exists**: `seen = {}`, `num_map = {}`, `hashm = {...}`, `freq = Counter(s)`, `sett = set(nums)` produce nothing (visited_tracking fires only for visited-like names on `set()/dict()/defaultdict()` calls or `{...}` **Set** literals — `seen = {}` is an ast.Dict, so not even that).
- `_detect_indexed_write` (+`_aug`, :878/:901) records `{structure, index_type}` on **both** Assign (`dp[0] = 1`) and AugAssign (`cnt2[...] += 1`) forms, but does **not record which form** — the frequency primitive needs that distinction.
- `.sort()` / `sorted()` / `min()` / `max()` produce **nothing**.
- M2 relations already provide `used_as_subscript_index` per variable — the exact primitive needed to separate "conditionally updated scalar that is NOT an index" (greedy) from "conditionally updated index variable" (sliding window / pointers).

---

## 1. `hash_map_lookup`

### Corpus forms that must belong (verified code)

| record | form | distinguishing structure |
|---|---|---|
| db-11 (LC 1) | `seen = {}` → `if complement in seen: return [seen[complement], i]` → `seen[num] = i` | dict literal + membership-gated read + deferred write |
| db-39 (LC 1) | `num_map = {}` → `if oth_num in num_map: return [num_map[oth_num], i]` | same, range-loop form |
| db-33 (LC 13) | `hashm = {…literal…}` → `val += hashm[s[i]]`, comparisons `hashm[s[i]] > hashm[s[i-1]]` | dict-literal table, read-driven branch decisions |

### Structurally similar code that must NOT belong (negative controls, probed)

| control | why excluded | available discriminator |
|---|---|---|
| dp-memo (LC 322-style: `memo = {}`, `if rem in memo: return memo[rem]`, `memo[rem] = …`) | IS a hash table, but memoization, not complement-lookup | `recursive_branching` / self-recursive call present (all three positives are iterative). This is the same recursive/iterative separation the taxonomy already uses for dp_top_down. |
| dp-array (LC 70-style: `dp = [0]*(n+1)`, `dp[i] = dp[i-1]+dp[i-2]`) | positional list, not a key→value lookup | no mapping construction (list-mult creation), no membership test |
| hash-group-builder (`groups = {}`, `groups[key] = groups.get(key, []) + [s]`) | write-dominant aggregation; reads never gate control flow | no membership test; read of same key feeding its own write |
| BFS/DFS `visited`-set membership (`if x in visited:`) | hash-set membership exists but the label means lookup-table reasoning | acceptable residual: technique fires as *evidence noise* on graph submissions, but no graph GT group requires `hash_map_lookup`, so no verdict impact |

### Concept level: **technique only** (not a strategy)

`hash_map_lookup` in LeetCode taxonomy is data-structure usage, not an algorithmic strategy — it co-exists with real strategies (db-35/230 sliding_window, db-193 monotonic_stack, db-49/51/194 prefix-sum groups). A `hash_lookup` strategy would be both semantically wrong and redundant. As a technique it joins the technique layer and becomes satisfiable evidence for groups.

### Minimum structural evidence (all name-free)

1. **Mapping identity**: a variable is constructed as a mapping — `ast.Dict` literal, `dict()`, `defaultdict(...)`, `Counter(...)`, or `set(...)`/`ast.Set` (one new name-free fact: `mapping_construction {variable, constructor}`).
2. **Gated read**: membership test (`ast.Compare` with `In`/`NotIn` on that variable — new name-free fact `membership_test {variable, negated}`) **or** subscript read of that variable appearing in an `if`/`while` condition or comparison.
3. **Deferred/different-key write** (supporting, not required): indexed write to the same variable (already `indexed_write`).

Recommended requirement for the technique: mapping identity ∧ gated read. Item 3 stays optional evidence.

### Likely false positives & their fences

- dp-memo → fenced by requiring **no** `recursive_branching` in the same evidence set (consistent with existing dp_top_down exclusions).
- write-dominant builders (group-by) → fenced by the gated-read requirement (verified absent in the negative).
- visited-set membership in graph code → unfenced but verdict-neutral (no GT group requires this concept on graph problems). Documented residual.

### solution_groups mapping

```
"hash_map_lookup": {
    "required": ["hash_lookup"],          # new technique id
    "optional": [],
    "excluded": ["recursive_branching"],  # memoization is not complement lookup
}
```
`MISSING_VOCABULARY_PATTERNS` shrinks automatically (it is derived from mappings with empty `required`), and the Batch 2A refresh re-derives the stored `group_0` rows for db-11/33/39/49/51/193/194/230/35 with no manual GT edits — the exact machinery built for this.

### Validation against larger corpus / automated GT builder

- The 9 expected-records are the immediate acceptance set (3 verdict flips expected: db-11, db-33, db-39 — each currently unsatisfiable-empty-required).
- Negative acceptance: db-238/db-240 (dp-memo submissions) must **not** newly satisfy anything; their GT is dp groups, and the recursive_branching exclusion keeps them out.
- Future: `mapping_construction` + `membership_test` counts are exactly the features an automated GT builder would correlate against problem tags ("Hash Table") — well-formed for that loop.

---

## 2. `hash_map_frequency`

### Corpus forms that must belong (verified)

| record | form | distinguishing structure |
|---|---|---|
| db-41 (LC 3812) | `freq = Counter(s)`; reads `freq[i]`, `freq[i]//2`, `freq[i]%2` | Counter construction + counted reads |
| db-64 (LC 4080) | `sett = set(nums)`; `k*i not in sett` | set construction + membership (counting family via set) |
| db-192 (LC 438) | `cnt1[ord(p[i])-ord('a')] += 1` ×4 (two fixed arrays of counts) | **augmented** indexed writes building counts |

### Structurally similar code that must NOT belong (probed)

| control | why excluded | discriminator |
|---|---|---|
| dp-array (`dp[i] = dp[i-1]+dp[i-2]`) | positional table writes, not counting | writes are **Assign**-form with recomputed-from-table values; no mapping construction, no augmented count writes |
| dp-memo (`memo[rem] = …`) | cache write, not counting | Assign-form write; recursive exclusion as above |
| fixed-window count *arrays* in sliding-window code (db-138/191 style `cnt[...] += 1` at window edges) | genuinely IS counting — multi-label, not a false positive | none needed: frequency and window co-listed in GT (db-192 expects both); separate groups resolve independently |

### Concept level: **technique only**

Same reasoning as lookup: data-structure behavior, always co-listed with a real strategy (window, sort, reconstruction). Strategy-level "frequency" would double-label sliding-window solutions.

### Minimum structural evidence

1. **Mapping identity** via `mapping_construction` with `constructor ∈ {Counter, defaultdict(int), set, dict}` (db-41 ✓, db-64 ✓; db-192 has no constructor — covered by 2).
2. **Counting write**: indexed write in **AugAssign form** on the structure (`cnt[x] += 1`) — implementable either as an added `syntax_form` attribute on the existing `indexed_write` fact (backward-compatible attribute addition, mirrors the accumulator fact's existing `syntax_form` field) or via M2 `collection_ops` extension. Plus `mapping_construction` OR `Counter`-style constructor as identity.
3. **Counted read** (supporting): subscript read of the structure in a condition/expression (already observable as subscript_index_access/joins).

Recommended requirement: (constructor-call identity) ∨ (augmented indexed write) — plus a loop or iteration context to distinguish one-off bookkeeping.

### Likely false positives & fences

- dp tables → fenced by Assign-vs-AugAssign form + constant-index initialization pattern (verified: dp-array writes are Assign-form with `Constant`/`Name` indices).
- Ordinary `total += arr[i]` accumulation → not an indexed write (accumulator variable is not subscripted) — verified absent.
- Memoization → recursion fence as in §1.
- db-192 note: its fixed-window group may remain unsatisfied (window needs F4-style index participation the count-array form lacks) — it should CONFIRM via the frequency group instead. That is the GT offering alternative groups, working as designed.

### solution_groups mapping

```
"hash_map_frequency": {
    "required": ["frequency_counting"],   # new technique id
    "optional": ["hash_lookup"],
    "excluded": ["recursive_branching"],
}
```

### Validation path

3 blocked records flip candidates (db-41, db-64, db-192); db-138/db-191 gain technique evidence with verdicts unchanged (already CONFIRMED via sliding_window). Negative set identical to §1 plus dp-array.

---

## 3. `greedy_local`

### Corpus forms that must belong (verified)

| record | form | distinguishing structure |
|---|---|---|
| db-255 (LC 4256) | pass 1: `for x: if odd: odd = x; break` (select first odd); pass 2: transform relative to candidate | conditional **scalar** candidate update + break |
| db-256 (LC 4258) | `for x: if odd is None or x < odd: odd = x`; later validation pass | conditional **min-candidate** replacement |
| db-37 (LC 1574) | `if i<=nums[k]: j=i; i=nums[k] elif j<=nums[k]: j=nums[k]` | **cascading top-2** candidate replacement |
| db-18 (LC 628) | `nums.sort()`; `max(nums[0]*nums[1]*nums[-1], nums[-1]*nums[-2]*nums[-3])` | sort + extremum of a constant number of positions — **no loop at all** |
| db-36 (LC 1574) | `nums.sort()`; `(nums[-1]-1)*(nums[-2]-1)` | same sort+extremum form |

### Structurally similar code that must NOT belong (probed + existing tests)

| control | why excluded | discriminator |
|---|---|---|
| sliding window (db-35/138/191/230, LC 29 original case) | conditionally updated variables, but they are **subscript indices** | M2 `used_as_subscript_index` — the exact F4 discriminator, already built and tested |
| dp tables (dp[i] conditionally max'd) | conditionally updated **table positions** | same non-index-participation fence |
| forward_pointer_advance / two-pointer | conditionally updated **index** variables advancing in the same direction | same fence (verified: technique does not fire on db-255/256/37 today) |
| loop_state_tracking (any loop-carried state, e.g. running max displayed alone) | weakest neighbor; fence = candidate update must be **conditional replacement** (`if`-guarded rebinding), not unconditional accumulation | `conditional_index_update` fact requires the if-branch; `sequential_accumulation` covers unconditional adds |
| prefix/sum accumulation (db-33 `val += …`) | accumulation is not selection | accumulator facts are Add/Sub forms; selection is rebinding to another element |

### Concept level: **technique only — a `greedy` strategy is explicitly NOT recommended**

`greedy_local` sits alongside `greedy_interval` etc. as a problem-tag; greedy as a strategy needs problem semantics (exchange argument) that structural evidence cannot honestly carry, and one structural greedy technique could otherwise confirm both a greedy group and a dp group on ambiguous problems. Technique-only keeps verdicts with the strategies that already work (window, pointers, dp) while making greedy-only GT satisfiable.

### Minimum structural evidence

**Loop form (db-255, db-256, db-37) — zero new facts required:**
- `for_loop_iteration` ∨ `while_loop_comparison` (iteration context)
- `conditional_index_update` whose `updated_variables` are scalars — enforced via M2: **none of the updated variables appears in `used_as_subscript_index`** (this is the load-bearing fence; relations were built for exactly this join)
- supporting: `early_termination` (break) or a second pass over the same iterable (db-255/256 shape)

**Sort form (db-18, db-36) — one new name-free fact required:**
- `sorting_operation {target, form: method|builtin}` for `.sort()` / `sorted(...)`, optionally paired with extremum-call evidence (`max(...)`/`min(...)` of a bounded number of subscript reads). Without this fact the sort form stays UNRESOLVED — acceptable to phase (see order below), but the fact is cheap, name-free, and reusable for heap-vs-sort comparisons later.

### Likely false positives & fences

- Windows/pointers/dp → index-participation fence (strongest, already regression-tested by F4's battery).
- Any `if`-guarded rebinding in ordinary code (e.g., clamping `if x > hi: hi = x` inside an unrelated loop) → this genuinely is a running-extremum (greedy-local *evidence*); risk is bounded because the technique only matters where GT requires it, same as loop_state_tracking's exposure today.
- BoolOp conditions (`while a and b:`) → out of scope for the join; conditional_index_update already fires per verified branch facts.

### solution_groups mapping

```
"greedy_local": {
    "required": ["candidate_selection"],   # new technique id (loop form)
    "optional": ["sorting_operation"],     # sort-form support
    "excluded": ["sliding_window"],        # index-participating updates are windows, not greedy
}
```
Exclusion direction verified: no corpus greedy-positive fires `sliding_window` (their conditionally-updated vars are non-index scalars), and all window positives keep index participation, so the exclusion never bites a window submission.

### Validation path

All 5 greedy records are blocked and flip-candidates: db-255/256/37 via loop form, db-18/36 via sort form. Negative acceptance: the full sliding-window regression battery (db-35/138/191/230, LC 29, LC 6 Fixes) must show zero technique or verdict change — the fence is precisely F4's tested predicate.

---

## 4. Interaction with existing strategies (summary)

| existing strategy | interaction | verified safe because |
|---|---|---|
| sliding_window | greedy exclusion target; frequency/lookup co-exist | F4 index-participation separates greedy from window; window solutions with counting maps gain frequency technique without verdict change (db-138/191) |
| dp_top_down / dp_bottom_up | recursion exclusion keeps memo out of lookup/frequency groups | db-238/240 must remain CONFIRMED-only via dp groups; recursive fence blocks the new techniques |
| monotonic_stack (db-193) | gains hash_lookup technique evidence only | verdict already CONFIRMED; no GT group change |
| prefix_sum groups (db-49/51/194) | gains hash_lookup technique evidence only | same |
| bfs/dfs/union_find (db-244 etc.) | visited-set membership may fire lookup technique as noise | no graph GT group requires hash_map_lookup → verdict-neutral |
| two_pointers / binary_search | no shared evidence joins with the new techniques | disjoint fact requirements |

## 5. Ground-truth implications

- Three `PATTERN_TO_V1_MAPPING` entries gain real `required` concepts → `MISSING_VOCABULARY_PATTERNS` auto-shrinks (frozenset comprehension, no code edit needed there).
- Batch 2A `refresh_group_vocabulary` re-derives all stored `vocabulary_v1`-marked groups on the next derivation run — no manual GT edits, consistent with the "never persist unsatisfiable groups" invariant.
- The consistency checker (patterns-vs-groups) validates the new mappings everywhere at once; disagreement surfaces as `concept_not_derived_from_patterns`-style findings, not silent drift.
- New technique IDs must be added to `VALID_TECHNIQUES` (ground_truth_builder.py:25) — the single vocabulary registry — and to the V1 vocabulary doc, keeping derivation, validation and persistence versioned coherently.

## 6. Recommended implementation order

1. **`greedy_local` loop-form technique** (`candidate_selection`) — zero new facts, zero extractor changes; pure technique-layer join over existing facts + M2 relations. Smallest blast radius, 3 records, and its fence is the already-tested F4 predicate.
2. **`hash_map_lookup`** — two new name-free facts (`mapping_construction`, `membership_test`) + technique + mapping + recursion exclusion. 3 verdict flips + 6 evidence-only records.
3. **`hash_map_frequency`** — reuses `mapping_construction`; one backward-compatible attribute addition (`syntax_form` on `indexed_write` AugAssign) + technique. 3 records.
4. **`sorting_operation` fact + sort-form greedy support** — extends greedy to db-18/db-36 (2 records); also future-usable for sort-vs-heap comparisons. Independently shippable.
5. After each step: Batch 2A refresh + 46-record corpus before/after + full suites (the established loop).

Rationale for order: each step is independently falsifiable, later steps reuse earlier facts, and the riskiest negative surface (dp-memo confusion) is concentrated in step 2 where the recursion fence is testable against real dp submissions (db-238/240).

## 7. Is there enough evidence to implement safely?

**Yes — as techniques, in the order above.** Every positive form was probed against the current extractor and every negative control has a structural (not name-based) discriminator, two of which (index-participation, recursion) are already regression-tested predicates in the codebase. New machinery is limited to two/three name-free fact types and one attribute — a **small extension**, not an architectural change; M1's dispatch layer is where the new statement-form detectors plug in, and M2 supplies the non-index-participation fence.

**Not established:** strategy-level versions of any of the three (rejected in §1–3 with reasons); behavior on unseen implementations beyond the 46-record corpus — the sort-form greedy and set-membership families have ≤5 corpus exemplars, so the first post-implementation fresh-submission batch should oversample greedy/hash-tagged problems before declaring the layer stable.

## 8. Residual risks (disclosed)

- `parent_root_merge`'s overbroad shape match on hash writes (verified on db-11/db-39) is pre-existing noise; the new techniques do not depend on it, but a cleanup opportunity now exists (restrict to union-find context or rename), out of scope here.
- `membership_test` will fire on any `in`-test over any collection (lists included); requiring the operand to be a `mapping_construction` variable (or used-in-condition with one) keeps it honest.
- db-192's fixed-window group is expected to remain unsatisfied even after step 3 (count-array form lacks window index participation) — the CONFIRM comes from the frequency group; this is alternative-group semantics working, not a miss.
