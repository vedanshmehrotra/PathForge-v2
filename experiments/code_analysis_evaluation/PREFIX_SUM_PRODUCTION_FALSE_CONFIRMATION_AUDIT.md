# Production False-Confirmation Audit — `prefix_sum` → `sequential_accumulation`

**Type:** evaluation-only audit. No production code, shadow code, detectors,
techniques, strategies, ground truth, matcher, tests, or DB rows were modified.

**Question:** does the broad mapping
`prefix_sum → required = ["sequential_accumulation"]`
produce **real false confirmations in the available production submission data**?

**Answer: A — no production false-confirmation evidence was found; freeze the taxonomy.**

---

## 1. Dataset / submission scope

Source: the live application database (`submissions`, `problem_ground_truth`) —
the same data the running product uses.

| | count |
|---|---|
| stored submissions | **92** |
| with a ground-truth row for their problem | 87 |
| without GT (`NO_GT`) | 5 |
| `verdict_type = analysis_only` | 51 |
| `verdict_type = authoritative` | 41 |
| distinct users | 5 (85 of 92 are user 14) |

Ground-truth rows mentioning `prefix_sum` / `sequential_accumulation`: **4 of 103**
(`problems`: 3236, 4284, 4256, 4258). Only **two** carry a group that *requires*
`sequential_accumulation`:

| problem | stored `patterns` | live loaded groups (via `_load_ground_truth`) |
|---|---|---|
| **3236** | `['hash_map_lookup','prefix_sum']` | `group_0_alt0` req `["hash_lookup"]`; `group_0_alt1` req `["sequential_accumulation"]` (alternatives derived from one stored group with no `required`/`provenance`) |
| **4284** | `['two_pointers_same','prefix_sum']` | `group_0` req `["forward_pointer_advance"]`; `group_1` req `["sequential_accumulation"]` opt `["iterative_table_filling"]` (two stored groups, provenance `llm_ground_truth`+`vocabulary_v1`) |
| 4256 / 4258 | `['greedy_local']` | `group_0` req `["candidate_selection"]` opt `["sequential_accumulation"]` — **not prefix_sum** (out of scope; confirmed via `candidate_selection`) |

## 2. Method

For every submission, in-process and read-only:

1. loaded the **live** groups with `problem_resolver._load_ground_truth(conn, problem_id)`
   (identical to production runtime);
2. ran the frozen shadow pipeline via `run_shadow_analysis(code, solution_groups=groups)`;
3. recorded `match_outcome` (`outcome`, `satisfied_group_ids`, `reasoning`),
   `technique_evidence`, `strategy_evidence`;
4. for each `CONFIRMED`, computed the **union of `required` concepts of the
   satisfied groups** and flagged whether `sequential_accumulation` was load-bearing;
5. inspected the source of every `sequential_accumulation`-dependent confirmation
   against the problem's stated intent.

HELD OUT: synthetic benchmark negatives were **not** used to judge production
correctness.

## 3. Production results

Whole-corpus outcome distribution (87 submissions with GT):

```
CONFIRMED    79
UNRESOLVED    8
(NO_GT)       5
```

Of the **79** confirmations, exactly **14 depend on `sequential_accumulation`**;
the other 65 depend on unrelated required concepts:

```
CONFIRMED dependent on sequential_accumulation: {False: 65, True: 14}
```

All 14 are **problem 3236**; **problem 4284's single submission is `UNRESOLVED`**
(satisfied = `[]`, no confirmation). So:

| metric | value |
|---|---|
| total `prefix_sum`-family confirmations | **14** |
| distinct problems | **1** (3236) |
| distinct normalized implementations | **3** |
| clearly correct (A) | **14** |
| likely false (B) | **0** |
| ambiguous (C) | **0** |
| GT-representation (D) | 0 blocking (see §6) |
| **% of confirmations possibly false** | **0 / 14 = 0 %** |

The 14 rows are 3 implementations repeated across attempts:

```
02673b46abba  subs 49, 66, 70, 72, 136      (j-index variant)
fbc45e500c35  subs 51, 53, 54, 58, 59, 60   (i-index, <= bound)
d19a7a96b35b  subs 194, 218, 219             (i-index, < bound)
```

## 4. Candidate false confirmations

**None.** No production confirmation depends on `sequential_accumulation` for a
submission that does not implement the intended prefix/sequential accumulation.

Specifically, of the problematic categories the taxonomy audit named, the
production corpus contains **zero** confirmed instances of:

| category | confirmed in production via `prefix_sum`? |
|---|---|
| terminal scalar aggregate (`count += 1`, returned only) | no |
| greedy scalar state (`five -= 1`, `child += 1`) | no |
| DP state (Kadane-style reset) | no |
| generic counter | no |
| greedy propagation (`candies[i] = candies[i-1] + 1`) | no |
| hash-map accumulation (as the *only* evidence) | no |
| genuine prefix / range reasoning | **yes — 14 (all of them)** |

## 5. Evidence for each candidate

There are no candidates to evidence. What *was* confirmed is structurally and
semantically consistent with the intended algorithm. All 14 submissions are
variants of:

```python
summ = nums[0]
while j <= len(nums) - 1 and nums[j] == nums[j - 1] + 1:
    summ += nums[j]
    j += 1
while summ in nums:
    summ += 1
return summ
```

- Detected evidence (all 14): `sequential_accumulation` (presence 0.85);
  8 of them additionally `forward_pointer_advance` (0.80, the `j += 1` advance).
  No competing or spurious strategy.
- Satisfied group: `group_0_alt1` (`required=["sequential_accumulation"]`) — i.e.
  confirmation is load-bearing on the required concept, exactly as designed.
- Problem 3236 is literally *"Smallest Missing Integer Greater Than **Sequential
  Prefix Sum**"*: `summ` **is** the sequential prefix sum of the longest
  consecutive prefix, and the second loop scans for the smallest integer ≥ it
  absent from `nums`. The mapping's required concept names the submission's
  actual computation.
- Note the stored `verdict = 'fail'` on all 14 (repeated failed attempts, same
  user). A pattern confirmation on a failing attempt is the intended use of the
  analysis layer (approach matches; implementation has a bug) — it is not a
  false confirmation of the *pattern*.

## 6. Ground-truth issues (separate from false confirmation)

- **Problem 3236**: the stored `solution_groups` is a single group carrying only
  `patterns: ['hash_map_lookup','prefix_sum']`, with **no `required` and no
  `provenance`** (`authority_tier: llm_proposed`). This is precisely the
  "collapsed alternative" representation the existing generic GT repair handles:
  the loader expands it into two **alternative** groups (`hash_lookup` OR
  `sequential_accumulation`), and all 14 submissions satisfy the
  `sequential_accumulation` alternative. No blocking defect; no confirmation
  was produced by a malformed conjunction.
- **Problem 4284**: two proper alternative groups with provenance; its single
  submission is `UNRESOLVED` — no false confirmation, and consistent with the
  known dev-corpus case (`db-254`).
- **Problems 4256 / 4258**: stored `greedy_local` groups derive
  `required=["candidate_selection"]`, confirmed via that concept; their
  `optional=["sequential_accumulation"]` is never load-bearing. Out of scope for
  this audit.
- No GT row produced an empty-required matchable group that was confirmed.

## 7. Comparison with the 46-record and 301-case benchmark findings

*(Production evidence kept separate from synthetic evidence.)*

| finding | 46-record | 301-case | production |
|---|---|---|---|
| `prefix_sum` confirmations | 3 (db-49/51/194, all LC 3236) | n/a (labelled corpus) | **14, all LC 3236** |
| confirmations load-bearing on `sequential_accumulation` | 3 | n/a | 14 |
| false confirmations | 0 | n/a | **0** |
| false positives | n/a | 13 (12 generic scalar aggregates + `greedy_candy`) | **0** |
| `greedy_candy`-shaped greedy propagation confirmed | false | false | **absent from corpus** |

The 3 dev-corpus confirmations (db-49/51/194) are a subset of the 14. The
**301-case synthetic FPs did not translate into any production false
confirmation**: the categories the benchmark penalises (generic scalar
aggregates, greedy/DP state, greedy array propagation) simply do not appear as
confirmed `prefix_sum` submissions in the production data — the only
`prefix_sum`-labelled problem in production receives a genuine sequential
prefix-sum implementation. This is direct confirmation of the taxonomy audit's
claim that the synthetic FPs were an artifact of comparing a *structural* pattern
against a *semantic* algorithm label.

## 8. Does real-world evidence justify a value-role / taxonomy experiment?

**No.** There is no production evidence of false confirmation — repeated or
otherwise — for `prefix_sum → sequential_accumulation`. The decision rule is
explicit: without actual production evidence of repeated false confirmation, the
mapping should remain frozen.

**Scope caveat (stated for honesty):** production `prefix_sum` coverage is
currently one problem and three distinct implementations, all from a single user
and all `analysis_only`. This is therefore *not proof that no false confirmation
is possible* — only that none exists in the available data. It removes the sole
production justification for a taxonomy experiment while leaving the synthetic
risk characterised in `PREFIX_SUM_TAXONOMY_AUDIT.md`.

**Re-run trigger:** re-run this audit when additional `prefix_sum`-labelled
problems (~≥3 problems, ≥~10 distinct implementations, ideally from
`authoritative` submissions) enter production, or immediately if any confirmed
`prefix_sum` submission is found to be a terminal aggregate / greedy / DP state.

---

## Recommendation

### A. No production false-confirmation evidence → freeze taxonomy.

Backing evidence:

- 79 production confirmations; **14** load-bearing on `sequential_accumulation`;
  **0** false (0 %), across **3** distinct implementations.
- Every one of the 14 is a genuine sequential prefix-sum computation on a problem
  whose accepted patterns include `prefix_sum`.
- The 301-case synthetic FPs have **no production analogue**; no confirmed
  generic counter, greedy state, DP state, or greedy propagation exists under
  `prefix_sum` in production.
- All three 46-record confirmations are a subset of these 14 and remain correct.

**Not B** — no repeated (or any) production false confirmation exists.
**Not C** — the decision rule resolves an absence of evidence to "freeze"; a
collection drive is only warranted once a `prefix_sum`-labelled population
exists, as captured by the re-run trigger above.

**Frozen:** the mapping `prefix_sum → required=["sequential_accumulation"]` stays
as-is. Explicitly not recommended: narrowing the mapping, adding
`prefix_accumulation`/`prefix_state_build`, restricting the assign form, or any
value-role/taxonomy change.
