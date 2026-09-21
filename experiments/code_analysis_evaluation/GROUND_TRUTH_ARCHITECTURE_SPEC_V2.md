# Ground-Truth Generation, Validation, and Versioning Architecture — Specification V2

**Status:** DESIGN REVISION ONLY. No production code, shadow code, detector, technique,
strategy, matcher, database row, existing ground truth, or POC implementation was modified.
No Phase 6 work is specified as ready.

**Relationship to V1.** `GROUND_TRUTH_ARCHITECTURE_SPEC.md` (V1) is **unchanged and remains
the record of the original design**. V2 revisits it strictly on evidence produced by the
JSON-first POC (`gt_poc/POC_REPORT.md`). V2 **supersedes** these V1 sections:

| V1 section | V2 disposition |
|---|---|
| §8 Solution-family grouping | **Replaced** by V2 §1 + §2 |
| §9 Label-generation mechanism | **Replaced** by V2 §3 + §4 + §5 |
| §11 Validation methodology | **Amended** by V2 §6 + §7 (control rule + split rule defined) |
| §5 / §17 Corpus size & POC spec | **Amended** by V2 §8 |
| §12 Uncertainty model | **Extended** by V2 §9 (zero-evidence as first-class state) |
| §16 Minimal DB model | **Corrected** (count/field inconsistencies) — V2 §11 |
| §21 Open decisions | **Updated** — V2 §10 (some resolved, some still OPEN) |
| §1–§4, §6–§7, §10, §13–§15, §18–§20 | **Carried forward unchanged.** |

Readers should treat V1 + V2 together: V1 for the architecture and rationale, V2 for the
grouping/labeling/validation contract.

## 0. Preserved invariants (unchanged from V1, restated as hard constraints on everything below)

1. Runtime is fully deterministic. No runtime LLM, no runtime network call for GT judgment.
2. The analyzer never authors the label that validates itself. Labels come from a source
   external to the analyzer under test.
3. Human review stays external to analyzer detection (reviewer-facing artifacts must not
   display the analyzer's technique/strategy detections).
4. GT versions are immutable; a new version is created, never an in-place rewrite.
5. No silent GT replacement. Promotion is an explicit, recorded, human-approved step.
6. No unnecessary infrastructure: JSON-first, no vector DB, no Kubernetes, no distributed
   pipelines, no ML/embedding stack.
7. Prefer refusal (`REVIEW_REQUIRED` / `UNRESOLVED`) over an invented or over-broad group.

## 0.1 Evidence base (the only findings this revision is allowed to act on)

All numbers below are measured in `gt_poc/POC_REPORT.md` (8 problems × 5 authored/DB-derived
solutions = 40; 17 derived groups; 171 eligible cross-problem control pairs).

| ID | POC finding | Measured value |
|---|---|---|
| F1 | Families produced | 31 families / 40 solutions |
| F2 | Singleton families | 23 / 31 (74%) |
| F3 | Whole-problem splits | LC 21 split 5/5; LC 560 split 5/5 |
| F4 | Identical-signature solutions split by skeleton distance alone | LC 1: three `hash_lookup` solutions → 2 families; LC 560: three `{sequential_accumulation}` solutions → 3 families |
| F5 | Families with no usable label/group | 12 / 29 labelable problems' families |
| F6 | Problem-level curated label cannot label individual families | all families of a problem receive the same `label_required` set |
| F7 | `derived_required = detected ∩ label_required` collapses to one generic technique | 5 groups activated on a single low-specificity concept |
| F8 | `discrimination_FP_disjoint` | 0.1228 (21/171), gate ≤ 0.05 |
| F9 | `label_agreement` | 0.8529, gate ≥ 0.90 |
| F10 | Held-out population | 8 / 40 (degenerate) |
| F11 | D1 / D2 dedup levels exercised | 0 / 0 |
| F12 | Solutions with zero techniques **and** zero strategies | 6 / 40 |
| F13 | Label↔vocabulary divergence | LC 21, LC 704, LC 242 |
| F14 | Control-set definition materially changes the metric | raw FP 0.1702 vs disjoint FP 0.1228 |

Supporting evidence reused from earlier frozen work (not new measurements):

- **Control-hit attribution by required concept (POC, 171 eligible pairs):**
  `sequential_accumulation` **8** + **6**; `forward_pointer_advance` **4**;
  `hash_lookup` **2**; `two_pointers_opposite` **1**.
  → 20 of 21 false-positive pairs came from groups whose `required` set consisted of a
  **single concept**; 18 of those 20 came from the two lowest-specificity concepts.
- **Independent 301-case corpus (frozen, from `VOCAB2_FINAL_EVALUATION_REPORT.md`):**
  `two_pointers_opposite` P = 1.000, `binary_search_standard` P = 1.000,
  `hash_map_lookup` P = 0.957, `prefix_sum` P = 0.783.
- **Production audit (`PREFIX_SUM_PRODUCTION_FALSE_CONFIRMATION_AUDIT.md`):** 0 confirmed
  production false confirmations from the broad `prefix_sum → sequential_accumulation`
  mapping, but 13 synthetic false positives in the 301 corpus — i.e. the *structural
  pattern* is broad while the *production* label set does not yet exercise the broad cases.
- **V1 vocabulary doc specificity ratings:** `sequential_accumulation` **Low**,
  `loop_state_tracking` **Medium**, `recursive_branching` **Medium**,
  `bidirectional_index_scan` **Medium-high**, `carry_propagation` **High**,
  `iterative_table_filling` **High**. `forward_pointer_advance`, `hash_lookup`,
  `frequency_counting`, `linked_list_traversal`, `fixed_window_maintenance`,
  `monotonic_stack_maintenance` have **no documented rating** (Phase 5A / Vocabulary
  Layer 2 additions).

**Interpretation rule used throughout:** every change below cites the finding(s) it is
caused by. Where the POC does not supply enough evidence, the decision is marked
**OPEN** rather than chosen.

---

## 1. Revised family grouping (supersedes V1 §8)

### 1.1 Why the V1 design was wrong (not merely mis-tuned)

V1 §8 made the **full detected concept set** the primary partition key and then applied
skeleton edit-distance as a refinement. Two independent defects follow:

- **Defect A — low-specificity concepts are allowed to partition.** The concept set is a
  *flat set*, so a solution that shows an extra Low/Medium concept lands in a different
  bucket even when the algorithm is unchanged. Measured: LC 21's four iterative merges
  differ only in which of `forward_pointer_advance`, `linked_list_traversal`,
  `loop_state_tracking`, `sequential_accumulation`, `candidate_selection` fired — four
  families for one algorithm (F3). LC 1's three `hash_lookup` solutions differ in *no*
  concept at all and were split purely by skeleton distance (F4).
- **Defect B — skeleton distance acts as a *split trigger*, not a cross-check.** Because
  partition happened first, the very coarse signature left skeleton distance as the only
  discriminator, and ordinary style variation became a family boundary (F4).

**This is why "use a different τ" cannot be the fix** (the task's explicit constraint).
The partition key itself is wrong; F4 shows two *byte-different but conceptually identical*
implementations splitting with τ unaltered.

### 1.2 Revised mechanism — four stages, in this order

```
solutions
  → S1  concept tiers            (what MAY partition vs what MAY NOT)
  → S2  primary partition        by PEC set  (partition-eligible concepts)
  → S3  structural-profile refinement  (coarse, role-based discriminants; NOT edit distance)
  → S4  deterministic agglomeration + anti-split guard
```

Every stage is deterministic and order-independent (stable sort on family keys).

### 1.3 S1 — Concept tiers

The central new concept. Every frozen technique/strategy ID is assigned to exactly one tier.

**PEC — Partition-Eligible Concept.** A PEC may create a family boundary. Designated PEC:

- **All strategies** (`sliding_window`, `two_pointers_opposite`, `binary_search`,
  `dp_bottom_up`, `dfs_backtracking`, …). Justification: a strategy denotes an algorithmic
  structure; two solutions under different strategies are genuinely different families.
- **Techniques with V1-documented specificity ≥ Medium-high**: `carry_propagation` (High),
  `iterative_table_filling` (High), `bidirectional_index_scan` (Medium-high).
- **Provisionally ratified PECs** (no documented specificity; ratified by POC + 301
  evidence, and flagged for human confirmation — V2 §10 OPEN-2):
  `hash_lookup`, `frequency_counting`, `linked_list_traversal`,
  `monotonic_stack_maintenance`, `fixed_window_maintenance`.
  - `hash_lookup`: 301 precision 0.957; and F4 shows it does **not** split identical
    `hash_lookup` implementations (the LC 1 split was the skeleton, not this concept).
  - `linked_list_traversal`: F3 — LC 21's four iterative merges all share it,
    so it is a *correct* co-partitioner for that problem.
  - `frequency_counting` / `monotonic_stack_maintenance` / `fixed_window_maintenance`:
    each denotes a distinct data structure or maintenance discipline.

**SUPPORT — supporting evidence only; NEVER partitions.** A SUPPORT concept is recorded,
is available to `required`/`optional` derivation (§4), and is displayed, but two solutions
differing only in a SUPPORT concept remain **one family**:

- `sequential_accumulation` (**Low** — V1 doc: "claims a computational pattern, not an
  algorithm"). 18 of 20 measured control-hit pairs came from groups built on this alone.
- `loop_state_tracking` (**Medium**) and `recursive_branching` (**Medium**).
- `forward_pointer_advance` — the direct cause of the LC 21 5/5 split (F3) and of 4 of the
  21 control hits.
- `candidate_selection`.
- Any technique added later **defaults to SUPPORT** until it is explicitly ratified as PEC.
  (Safe default: new vocabulary cannot silently fragment families.)

**This tiering is the single change that answers "when do two different technique sets
remain the same family?"**: they remain the same family when their **PEC sets are equal**
and their structural profile (§1.5) matches — even if their SUPPORT sets differ; they are a
different family when their **PEC sets differ** in a way not covered by the §1.6 merge rule.

### 1.4 S2 — Primary partition

```
PEC_set(solution) = { c ∈ concepts(solution) : tier(c) == PEC }
family_key_stage2 = PEC_set
```

Worked outcomes against the POC corpus:

| problem | before (V1) | after (S2) | why |
|---|---|---|---|
| LC 21 | 5 families | 2 | four iterative merges all `PEC = {linked_list_traversal}`; the recursive one is `PEC = {}` + different profile |
| LC 1 | 4 families | 3 | three `hash_lookup` solutions share `PEC = {hash_lookup}` and the same profile; brute force is `PEC = {}` + nesting 2; two-pointer is `PEC = {two_pointers_opposite}` |
| LC 560 | 5 families | ≤3 | three `{sequential_accumulation}`-only solutions collapse to `PEC = {}`; the DP solution is `PEC = {dp_bottom_up, iterative_table_filling, fixed_window_maintenance}`; the hash/frequency solution is `PEC = {hash_lookup, frequency_counting}` |

### 1.5 S3 — Structural-profile refinement (replaces skeleton edit-distance as splitter)

Only applied **inside** a stage-2 bucket. Purpose: separate structurally different
implementations that happen to share a PEC set (e.g. iterative vs nested-loop brute force,
both `PEC = {}`). The profile is a **coarse, role-based, low-cardinality tuple** derived
from facts the analyzer already emits — **no edit distance, no embeddings, no new facts**:

| profile dimension | source facts (existing) | values |
|---|---|---|
| `recursion` | `recursive_call_in_conditional`, `self_recursive_call`, `multiple_recursive_paths` | `none` / `single` / `multi` |
| `loop_shape` | `for_loop_iteration`, `while_loop_comparison`, `while_loop_truthiness` | `none` / `flat` / `nested` |
| `container` | `indexed_write`, `subscript_index_access`, `collection_ops` kind | `none` / `index_read` / `index_write` / `append` |
| `map_kind` | `mapping_construction`, `subscript_read` | `none` / `dict` / `set` / `array_presized` |
| `iterates_collection` | `for_loop_iteration` over a collection vs `range` | `range` / `container` / `both` |

`loop_shape = nested` is derived from the **skeleton tree depth of loop nodes** (a bounded
structural feature the POC already computes), not from edit distance.

Two solutions join the same family iff **all five dimensions are equal**. This is
deliberately coarse: it separates brute force from single-pass (LC 1, LC 560) while
never separating style variants of the same shape.

### 1.6 S4 — Deterministic agglomeration + anti-split guard

1. **`PEC_SUBSET_MERGE` (anti-split guard).** If, within one problem, family A and family B
   have (a) **identical structural profiles** and (b) one PEC set is a **non-empty subset**
   of the other, merge them. Rationale: a superset of specific concepts is an *additional
   observation of the same implementation family*, not a different algorithm. Evidence: the
   LC 560 dict-based prefix solutions where only one member emits `hash_lookup` (the `.get()`
   form) — they are the same implementation family.
2. **Deterministic tie-break.** When two candidate families are indistinguishable under (1),
   the family with the lexicographically smallest sorted PEC tuple is the canonical family
   key; the other is recorded as an alias. No randomness, no seeding, no ordering sensitivity.
3. **Anti-split report.** Every merge and every split records `grouping_reason` +
   `merged_because` (`pec_subset` | `profile_equal` | `distinct_pec` | `profile_differs`).
   F4's LC 1 case must record `profile_equal` + `pec_subset` with the merged members listed.

### 1.7 Kill criterion (must be measured in the next POC)

If the revised mechanism still yields > 25% singleton families or > 4 families per problem,
**do not tune parameters** — the profile discriminants are wrong and V3 must revise §1.5.
The POC baseline to beat: 74% singleton, up to 5 families/problem.

---

## 2. Revised skeleton usage (supersedes the V1 §8 refinement role)

The POC falsified skeleton edit-distance as an automatic splitter: LC 1's three identical
`hash_lookup` solutions split by skeleton distance alone (F4), and LC 560's three identical
`{sequential_accumulation}` solutions split likewise. Skeleton distance is therefore
**demoted**, not tuned.

**V2 role — three permitted uses, none of which is automatic splitting:**

1. **Bounded feature extraction (primary use).** The skeleton tree supplies
   `loop_shape` (loop-node nesting depth) and call/statement shape for the §1.5 profile.
   This is a *derived coarse feature*, not a distance.
2. **Tie-break on a merged bucket only.** Within a bucket that has already been merged by
   `PEC_SUBSET_MERGE`, if a downstream stage must choose a representative implementation
   for display/review, pick the smallest skeleton distance to the bucket's medoid. It never
   creates a boundary.
3. **Diagnostic / advisory signal.** Recorded per family as `skeleton_spread` and surfaced
   in the review sheet as *"these members differ stylistically"* — informational only.

**Removed:** skeleton Levenshtein as a **split trigger**; τ as a **per-family grouping
threshold**. τ survives only as the §2.2 representative-selection parameter and as a
*specimen-distance report*, and its value is **OPEN** (V2 §10 OPEN-1).

**Explicit answer to the required question:** the three LC 1 `hash_lookup` implementations
remain **one family** because they have equal `PEC_set = {hash_lookup}` and equal structural
profiles (`recursion=none`, `loop_shape=flat`, `container=index_read`,
`map_kind=dict`, `iterates_collection=container`), and because skeleton distance is no
longer consulted when deciding boundaries.

**Rejected alternatives (with reason):** weighted structural distance and semantic-role-aware
distance would reintroduce a tuned metric as a boundary rule and require a corpus to
calibrate — the POC has 40 solutions and cannot calibrate such a metric. ML embeddings are
excluded by the hard constraints. Hence: **coarse profile equality**, the simplest defensible
mechanism that survives the POC data.

---

## 3. Revised family labeling (supersedes V1 §9)

### 3.1 Why V1 was wrong

V1 attached the curated `problems.pattern` set to the *problem*, then intersected it with each
family. The POC proved this cannot work: **all families of a problem receive the same label**
(F6), which is why LC 21's iterative and recursive families both got
`forward_pointer_advance`, and why LC 560's brute-force, prefix-array, DP, dict `.get()`, and
frequency-map families all got `{frequency_counting, sequential_accumulation}`. That is the
root of F5 (12 families with no usable label) and F7 (collapse to one generic concept).

### 3.2 Core rule

```
problem label      ≠  automatic family label
```

The problem-level curated label is a **prior / candidate pool**, never an assigned family
label. A family receives a label only through an explicit **family-level** decision, and that
decision is external to the analyzer (invariant 2).

### 3.3 Label channels and precedence (unchanged precedence, new granularity)

For **each family**, a label is sought in this order:

1. **`curated_family`** — a human/editorial annotation attached to *that family* (new
   artifact; see §3.5).
2. **`curated_problem`** — the existing `problems.pattern` set, applicable to a family only
   if the family is **label-consistent** with it (a §3.4 screening test), otherwise it stays a
   *family-candidate* pool.
3. **`human_review`** — the reviewer's decision on the review sheet.
4. **`llm_proposed_offline`** — an offline proposal, recorded as `proposed`, never active
   without a human decision.

If no channel yields a label, the family is **unlabeled** and can never activate a group
(§4). It is not an error; it is the expected state for odd families.

### 3.4 Label–family consistency screening (deterministic)

Before a `curated_problem` label may be applied to a family, the family must pass a
**structural screening test** — this is where the analyzer is *used as a filter*, not as an
author:

```
family is label-consistent with label L  iff
    observed_union(family) ∩ L.required ≠ ∅
AND at least one of:
    (a) every concept in L.required is observed by every family member, or
    (b) the family is the *only* family for the problem
```

If the screen fails, the family does **not** inherit L. It becomes `REVIEW_REQUIRED` with
`reason = partial_label` (V2 §4). The analyzer's evidence is never written into the label.

### 3.5 New artifact: `family_labels.json` (POC-side, JSON-first)

One record per family, produced blind to the analyzer:

```
{ problem_id, family_key, member_solution_ids, source_type, anonymized_code,
  proposed_label_source, proposed_label_required/optional/excluded,
  approval_state, reviewer, reviewed_at, notes }
```

`approval_state ∈ { PENDING_REVIEW, APPROVED, REJECTED, REVIEW_REQUIRED }`. The POC default
is `PENDING_REVIEW` — nothing auto-approves.

### 3.6 Reviewer blinding (preserved, now verifiable per family)

`review_sheet.md` / `review_sheet.json` must render, for each family: problem, family key,
member code (anonymized/verbatim), source, and the *proposed* label — and must **not** render
detected techniques or strategies. The analyzer's detections appear only in the separate,
post-hoc `label_comparison.json`. The POC verified artifact-level blindness; human blinding
remains **OPEN** (V2 §10 OPEN-3).

---

## 4. Revised required / optional / excluded derivation (supersedes V1 §9's rule)

### 4.1 Why V1 was wrong

V1 derived `required = detection_derived_required ∩ label_required`. When the label names a
concept the analyzer cannot see for that family, the intersection silently **narrows** to
whatever generic concept happens to remain, producing `required = ["sequential_accumulation"]`
or `required = ["forward_pointer_advance"]`. Measured consequence: those single-generic-concept
groups owned 20 of the 21 false-positive control pairs (F7 + attribution table), i.e.
`discrimination_FP = 0.1228` (F8).

### 4.2 Revised rule — never narrow, refuse instead

Let `L = label_required` (from an approved family label) and `O = observed(family)
= ⋂ members' detected concepts`.

```
if  L == ∅:                     → NO_GROUP                (no independent label)
if  L ⊆ O:                      → derive required = L      (label-faithful)
if  L ∩ O == ∅:                 → NO_GROUP, state = UNEXPRESSIBLE
else (partial):                 → NO_GROUP, state = REVIEW_REQUIRED(partial_label)
```

**The `else` branch is the whole fix.** A partial observation is **never** resolved by
narrowing to the observed subset. It is surfaced for review. This directly implements the
task's key requirement: a family must not silently become
`required=["generic_technique"]` when the label intends something more specific.

### 4.3 Specificity floor (second, independent guard)

Even when `L ⊆ O`, a group is **not auto-activated** if `required = L` consists **only of
SUPPORT-tier concepts** (no PEC). Such a group is `REVIEW_REQUIRED(reason = generic_label)`.

Justification is measured, not assumed:

| required set of the POC groups | control-hit pairs |
|---|---|
| `[sequential_accumulation]` (SUPPORT only) | 8 + 6 = **14** |
| `[forward_pointer_advance]` (SUPPORT only) | **4** |
| `[hash_lookup]` (PEC) | 2 |
| `[two_pointers_opposite]` (strategy/PEC) | 1 |
| any group containing a PEC **and** a second concept | **0** |

Predicted effect of §4.2 + §4.3 on the POC control metric: `14 + 4 = 18` of the 21 hitting
pairs are removed → `discrimination_FP` ≈ **3/171 = 0.018 ≤ 0.05**. This is a *prediction to
verify in the next POC*, not a claim about the current system.

### 4.4 `optional` / `excluded`

- `optional` = observed concepts not in `required`, restricted to those the label marks
  optional **or** that are SUPPORT-tier. Never includes unobserved concepts.
- `excluded` = the label's `excluded` set, carried through verbatim (unchanged from V1).
- **`required_expected` (new, informational only).** Where `L` names a concept the analyzer
  cannot express, the *intended* set is recorded as `required_expected` on the **review
  artifact** so the gap is auditable. It is **never** written into `solution_groups.required`
  and never affects matching.

### 4.5 Minimum evidence before a family becomes active

A family may produce an active group only if **all** hold:

1. an approved family label exists (`APPROVED`), and
2. `required = L` is non-empty, and
3. §4.3's specificity floor passes (≥ 1 PEC in `required`), and
4. every required concept is observed by **every** member (so `group_satisfiability` stays 1.0), and
5. the family is not `ZERO_EVIDENCE` (§9).

Everything else is `REVIEW_REQUIRED` / `UNEXPRESSIBLE` / `INSUFFICIENT_VALIDATION` (§7) — all
recorded, none silent.

---

## 5. Label ↔ frozen-vocabulary divergence (formalised)

### 5.1 The state

V1 had no explicit representation for "the label is real, and the vocabulary cannot describe
it". The POC exposed three shapes (F13):

| case | independent label | vocabulary can express? | observed for the family |
|---|---|---|---|
| LC 21 | `two_pointers_same` → `forward_pointer_advance` | **yes**, but SUPPORT-tier only | yes (iterative family) |
| LC 704 | `binary_search` | yes | **no** — recursive family shows `recursive_branching` |
| LC 242 | `hash_map_frequency` | partially | **no** — `Counter(a)==Counter(b)` yields zero concepts |

### 5.2 Formal divergence states (one per family; mutually exclusive)

```
LABEL_OK              L ⊆ O and specificity floor passes        → may activate
LABEL_GENERIC         L ⊆ O but L is SUPPORT-only               → REVIEW_REQUIRED(generic_label)
LABEL_PARTIAL         L ∩ O ≠ ∅ but L ⊄ O                      → REVIEW_REQUIRED(partial_label)
LABEL_UNEXPRESSIBLE   L ∩ O == ∅                                → UNEXPRESSIBLE (no group)
LABEL_MULTI_OVERLAP   |L| > 1 and O contains several concepts
                      that each cover only part of L           → REVIEW_REQUIRED(ambiguous_label)
NO_INDEPENDENT_LABEL  L == ∅                                    → no group
ZERO_EVIDENCE         O == ∅ and no facts of interest          → §9
```

`LABEL_MULTI_OVERLAP` is included because a label like
`{frequency_counting, sequential_accumulation}` can be partially covered by two different
observed concepts; attributing it to whichever one happens to be observed would be the same
silent-narrowing error in a different disguise.

### 5.3 What GT generation does — and does not do

The correct behaviour, per the task's constraint, is **refusal plus a recorded reason**:

- **Does:** record the divergence state, the intended `required_expected`, the observed set,
  and route the family to human review. Reports the divergence in the metrics as a
  distribution (see §7.4) rather than a single agreement score.
- **Does not:** modify the frozen vocabulary, invent a concept, force an intersection,
  auto-approve a substitute label, or lower any threshold. Vocabulary changes are an
  explicitly separate track with its own gates.

### 5.4 Why the metric must change (replaces V1 `label_agreement ≥ 0.90`)

Under the revised rule, every activated group has `required == L` **by construction**, so a
"derived vs independent agreement" score is 1.0 whenever it is defined and undefined
otherwise — it can no longer measure anything. V2 replaces it with the following, all
reported as a **distribution** (counts + fraction), never as a single pass/fail number:

| metric | definition | gate |
|---|---|---|
| `activation_rate` | activated groups ÷ labelable families | report only (**OPEN-4**) |
| `divergence_distribution` | counts by the §5.2 states | report only |
| `family_coverage` | held-out members confirmed ÷ held-out members **with a held-out sample** (§7) | ≥ 0.85 |
| `discrimination_FP` | per V2 §6 canonical rule | ≤ 0.05 |
| `group_satisfiability` | active groups satisfied by all their derivation members | = 1.00 |
| `narrowing_violations` | activated groups where `required ≠ L` | **= 0 (hard)** |

`narrowing_violations = 0` is the new hard gate that encodes the task's key requirement.

---

## 6. Canonical negative-control rule (amends V1 §11)

### 6.1 Why this must be defined precisely

The POC produced two different numbers from the same run: raw FP **0.1702** and disjoint FP
**0.1228** (F14). V1 defined the metric without defining the control set, so the gate could
be met or missed by changing the definition. A canonical rule is therefore mandatory.

### 6.2 Problem with a naive rule

A naive rule ("every solution from another problem is a control") trivially penalises a group
whenever another problem legitimately uses the same algorithmic family — e.g. a
`sliding_window` group on one problem would be "falsely confirmed" by a `sliding_window`
solution on another. That is not over-broadness; it is vocabulary reuse. It must be excluded,
not counted as a failure.

### 6.3 Canonical rule (deterministic)

For an active group `G` on problem `P` with required set `L`, a candidate control solution
`S` on problem `Q` is **eligible** iff **all** hold:

1. `Q ≠ P`;
2. `curated_patterns(Q) ∩ curated_patterns(P) = ∅` — the two problems' **curated** pattern
   sets are disjoint (uses the independent, editorially sourced pattern metadata, not
   analyzer output);
3. `PEC_set(S) ∩ PEC_set_of(G) = ∅` — **structurally disjoint**: the control does not share
   a partition-eligible concept with the group, so same-family reuse is excluded rather than
   scored;
4. `S` is not `ZERO_EVIDENCE` (§9) — a zero-evidence solution cannot discriminate and would
   always trivially "pass".

**Excluded from the denominator:** same-problem solutions (they are the derivation/held-out
population, not controls); same-curated-pattern problems; PEC-overlapping solutions;
zero-evidence solutions.

**Count:** **all** eligible controls, exhaustively — no sampling, no random draw.

**Cross-problem same-family handling:** excluded by rule 3, and separately **reported** as
`same_family_reuse_count` so the exclusion is visible and auditable rather than invisible.

**Denominator:** the number of `(G, eligible control)` pairs that were actually tested.

**Per-group minimum:** a group with fewer than `N_min` eligible controls is reported as
`INSUFFICIENT_CONTROLS` and **excluded from the aggregate denominator** (neither pass nor
fail). `N_min = 5` is **PROVISIONAL** (V2 §10 OPEN-5).

### 6.4 Reported forms

```
discrimination_FP        = failing pairs / eligible pairs            (gate ≤ 0.05)
discrimination_FP_by_group  per-group counts (attribution)
same_family_reuse_count     controls excluded by rule 3
excluded_by_rule            counts per exclusion rule
insufficient_controls       groups excluded by the N_min rule
zero_evidence_controls      controls excluded by rule 4
```

`bootstrap ci` framing is deliberately **not** used given the corpus size; the raw counts and
denominator are reported so the reader can judge stability.

### 6.5 What the rule does *not* do

The rule does not relax the gate. It removes controls that cannot discriminate, and it
reports every exclusion. §4.2/§4.3 (not §6) are what are expected to bring the measured
value under the gate; §6 only ensures the value is measured the same way twice.

---

## 7. Validation split (amends V1 §11)

### 7.1 Why the 60/40 solution-level split degenerated

With 23 of 31 families singletons (F2), a solution-level split leaves families with a single
member either in derivation *or* held-out, never both. The POC result was a held-out
population of **8/40** (F10) — technically computed, practically meaningless, and it lets a
`family_coverage = 1.0` on 3 solutions look like strong evidence.

### 7.2 Revised split: family-first, problem-scoped, stratified

```
for each problem:
    for each family:
        n = |members|
        if n >= 3:  held_out = ceil(0.4*n) capped so derivation >= 1 ; rest = derivation
        if n == 2:  1 derivation, 1 held_out
        if n == 1:  derivation only, family flagged VALIDATION_LIMITED
```

Invariants: no solution appears in both sets (by construction); the split is per family, so a
multi-family problem keeps every family represented in derivation; deterministic (stable
ordering by `raw_hash`, take the first `k`).

### 7.3 Explicit insufficient-validation states

| state | condition | effect |
|---|---|---|
| `VALIDATION_LIMITED` | family has 1 member | contributes to `group_satisfiability`; **excluded** from `family_coverage` numerator and denominator |
| `INSUFFICIENT_VALIDATION` | problem where **no** family has ≥ 2 members | contributes **0** held-out solutions; reported as its own state |
| `NO_HELD_OUT` | a problem whose derived groups exist but whose held-out population is 0 | coverage for that problem is **undefined**, not `1.0` |

Nothing is silently omitted: every family and problem appears in `validation.json` with its
state.

### 7.4 Coverage is reported with its population, and gated

```
family_coverage          confirmed held-out / held-out with a sample
held_out_population      absolute count
limited_families         count of VALIDATION_LIMITED families
insufficient_problems    count of INSUFFICIENT_VALIDATION problems
divergence_distribution  per V2 §5.2
```

**New hard gate:** acceptance criteria may only be judged **met** when
`held_out_population ≥ 3 × (number of problems in the POC)` — i.e. ≥ 24 for an 8-problem
POC. Below that threshold the run is reported as `INSUFFICIENT_VALIDATION` overall and no
criterion is claimed met. This is the direct correction of F10.

### 7.5 What is *not* changed

The split remains solution-level *within* a family (V1's intent), the analyzer/matcher is
used read-only, and no rule is adjusted when validation fails — failures are reported (V1
invariant, retained).

---

## 8. Revised corpus requirements (amends V1 §5 and §17)

### 8.1 Which POC findings force this

F2/F3 (74% singletons, whole-problem splits) and F10 (8/40 held-out) show 5 solutions/problem
is too thin to validate anything. F11 (D1/D2 = 0/0) shows the dedup ladder was never
exercised. F12 (6/40 zero-evidence) shows the zero-evidence path is common, not an edge case.

### 8.2 Revised numbers (still JSON-first, still small)

| item | V1 | V2 | reason |
|---|---|---|---|
| solutions per problem | 5 | **8** | ≥ 3 per family needed for a non-degenerate split (§7.2) |
| minimum per **family** | not stated | **3** (validation-grade); 2 = `VALIDATION_LIMITED` | §7.2 |
| problems | 8 | **12** | add strategy families the first 8 did not cover |
| total reference solutions | 40 | **96** | 12 × 8 |
| deliberate D1 duplicates | 0 | **≥ 3 problems** | F11 |
| deliberate D2 syntax variants | 0 | **≥ 3 families** | F11 |
| deliberate zero-evidence cases | 0 | **≥ 3** | F12 / §9 |

This is **not** "thousands of solutions". It is the smallest corpus that can exercise every
stage the POC left untested.

### 8.3 Problem selection

- **Keep the same 8 problems** (LC 1, 21, 125, 209, 242, 560, 704 and the 8th already in the
  POC corpus) — they carry prior measured evidence, so before/after is comparable.
- **Add 4** problems chosen to cover strategy families the 301-corpus evaluation could not
  measure (`binary_search_standard` n=2; graph/DP families "not measurable") and which the
  first POC's concepts did not include:
  1. a **grid/graph traversal** problem (e.g. LC 200 or 102) — `bfs_shortest_path` / `neighbor_traversal`;
  2. a **bottom-up DP** problem (e.g. LC 70 or 322) — `dp_bottom_up`;
  3. a **backtracking** problem (e.g. LC 46 or 78) — `dfs_backtracking`;
  4. a **union-find** problem (e.g. LC 547 or 684) — the only major strategy family with no
     representation anywhere in the POC or the 301 labels.

### 8.4 Saturation

The V1 saturation rule is retained and now testable: add implementations until **5 further
solutions add no new family and no new PEC signature**. With 8/problem and ≥ 3/family the
revised corpus is the first in which the rule can actually be evaluated.

---

## 9. Zero-evidence solutions (new first-class state)

### 9.1 Definition

A reference solution is `ZERO_EVIDENCE` iff it yields **no techniques and no strategies**,
regardless of how many raw facts it produces. POC: 6/40 (F12) — `bisect`-based search,
`Counter(a) == Counter(b)`, `sorted(a) == sorted(b)`, and a brute-force shape.

### 9.2 Rules (all explicit, none invented)

| question | answer |
|---|---|
| How do they enter the corpus? | Normally, with `quality_state = accepted` **and** `evidence_state = zero_evidence`. They are recorded, never silently dropped. |
| Can they create a family? | Yes — an `UNCLASSIFIED` family with `PEC = ∅` and `support = ∅`. They **cannot** be merged with a non-zero-evidence family (profiles differ by construction in the `map_kind`/`container` dimensions in most cases; where profiles coincide, the `ZERO_EVIDENCE` flag is part of the family key). |
| Can they be held out? | Yes, and they **should** be: they are coverage misses by definition, so holding them out measures whether the derived groups wrongly confirm them. A `ZERO_EVIDENCE` held-out member that confirms is a **false confirmation** and is reported as such. |
| Are they counted as covered? | **No.** A zero-evidence held-out member counts as UNRESOLVED and is excluded from the `family_coverage` numerator with its own reported count. |
| Can they receive a label? | **No.** A `ZERO_EVIDENCE` family can never activate a group (`required` would have to come from nothing). It is `NO_INDEPENDENT_LABEL` at best. |
| When do they force `REVIEW_REQUIRED`? | When a problem's **only** or **primary** family is `ZERO_EVIDENCE` — the vocabulary cannot describe that problem's accepted approach at all, which is a vocabulary/coverage signal for the reviewer, not a grouping bug. |
| Do they become controls? | **No** (V2 §6.3 rule 4). They cannot discriminate. |

The rule from the task is honoured: **no analyzer evidence is invented for them.** They are
described by their absence of evidence and nothing more.

---

## 10. Open decisions (updated from V1 §21)

### 10.1 Resolved by the POC (no longer OPEN)

| V1 open item | resolution | evidence |
|---|---|---|
| Skeleton/τ as a grouping threshold | **Resolved: τ is not a grouping mechanism.** Skeleton distance is demoted to representative-selection + diagnostic (V2 §2). | F4 (identical-signature splits by distance alone) |
| "DB now vs JSON-first" | **Resolved: JSON-first.** The POC ran end-to-end with no DB and no schema change, and produced auditable artifacts. | POC execution (no DB touched) |
| Is over-splitting fixable by threshold tuning? | **Resolved: no.** The partition key itself was wrong (flat concept set). | F3/F4 |
| Does `label_agreement` measure anything? | **Resolved: no, as defined.** Replaced by the §5.4 distribution + `narrowing_violations`. | F9 (0.8529 while 12 families had no group) |
| Is zero-evidence an edge case? | **Resolved: no.** First-class state. | F12 (6/40) |
| Are D1/D2 exercised by the POC corpus? | **Resolved: no.** Corpus requirement added. | F11 (0/0) |
| Is reviewer blinding verifiable at the artifact level? | **Resolved: yes** (artifact-level). Human blinding still OPEN below. | POC test: reviewer artifact hides detections |

### 10.2 Still OPEN — must not be silently chosen

| ID | open decision | what evidence would settle it |
|---|---|---|
| **OPEN-1** | Skeleton distance as representative-selection parameter (V2 §2.2): exact metric and value | next POC: does representative choice change any reported metric? If not, the value is cosmetic and should be fixed at the smallest defensible value. |
| **OPEN-2** | The provisional PEC list (V2 §1.3): should `hash_lookup`, `frequency_counting`, `linked_list_traversal`, `monotonic_stack_maintenance`, `fixed_window_maintenance` be ratified as partition-eligible? | Human/taxonomy ratification. This is taxonomy-adjacent and cannot be machine-decided. Evidence supplied: 301 precision (0.957 for `hash_lookup`) + F3/F4 behaviour. |
| **OPEN-3** | Human blinding: are reviewers actually blind in practice? | An actual review run with a human. Artifact-level blindness alone does not prove it. |
| **OPEN-4** | `activation_rate` floor: what minimum activation rate is acceptable before the vocabulary is deemed inadequate? | A real review round producing approved family labels; the POC had 0 approved labels. |
| **OPEN-5** | Negative-control strength: is `N_min = 5` per group correct, and is rule 3 (PEC-disjointness) the right exclusion? | next POC: report `discrimination_FP` with and without rule 3, and report `INSUFFICIENT_CONTROLS` counts. |
| **OPEN-6** | LLM usage: does an offline LLM label-proposal stage ship at all? | next POC with human labels first; only then measure whether LLM proposals agree, blind. Deferred, **not** decided. |
| **OPEN-7** | Label-source conflict rule when `curated_family`, `human_review` and `llm_proposed_offline` disagree | A conflict instance. Precedence is specified (§3.3); the *tie-breaking on disagreement* is not. |
| **OPEN-8** | Profile discriminant set (V2 §1.5): are these five dimensions sufficient, or does the next POC show new split/merge errors requiring a dimension change? | next POC singleton rate and per-problem family count versus §1.7 kill criterion. |
| **OPEN-9** | Corpus saturation point for the revised design (V2 §8.4) | next POC: the "5 further solutions add nothing" test on 12 problems. |
| **OPEN-10** | Cross-problem **same-family** controls: is excluding them (rule 3) correct, or should they count as weak positives/negatives? | next POC: report both; decide with data. |
| **OPEN-11** | `LABEL_MULTI_OVERLAP` handling: refuse (as specified) or split the label into per-family sub-labels? | next POC divergence distribution. |
| **OPEN-12** | Minimum corpus size before GT for a problem may be promoted (not merely derived) | next POC + a human review round. |

No value in §10.2 may be filled in by the implementation without a recorded decision.

---

## 11. Corrected spec/POC internal inconsistencies

These are corrections to V1 text; **nothing is implemented**.

| # | V1 location | Inconsistency | Correction |
|---|---|---|---|
| I1 | §16 opening line (V1 line 414): *"Four new tables + two columns"* | §16 then **defines five** tables (`reference_solutions`, `solution_families`, `solution_family_members`, `gt_versions`, `gt_validation_runs`) and **three** column additions (`problem_ground_truth` +2, `submissions` +1) | Correct to **five new tables + three new columns** |
| I2 | §16 `problem_ground_truth + approval_state TEXT DEFAULT 'llm_proposed'` | Existing `problem_ground_truth.validation_status` already carries `'llm_proposed'` (V1 §2 L8 notes this). Adding `approval_state` creates two fields with overlapping meaning | Define **one** field. Recommended: reuse `validation_status` with a single documented value domain (`llm_proposed \| draft \| validated \| approved \| rejected`), and do **not** add `approval_state` to `problem_ground_truth`. `gt_versions.status` keeps its own domain (it is per-version, not per-problem) |
| I3 | Document outline | V1 was required to include a standalone **LLM boundary** section in the outline; the written document folds it into §9/§15 and has no such heading, which shifts every section from the outline's §10 onward by one | V2 restores an explicit **LLM boundary** statement (below) and notes the numbering offset so cross-references from V1 are read correctly |
| I4 | §16 ordering | `solution_families.gt_version_id → gt_versions(id)` is declared before `gt_versions` is defined in the same section | Reorder so `gt_versions` precedes `solution_families` (documentation-only nit) |
| I5 | §11 vs §17 | §11 lists `discrimination_FP ≤ 0.05` and `label_agreement ≥ 0.90` as gates, but §11 never defines the control set while §17's acceptance criteria assume one | Resolved by V2 §6 (canonical rule) and V2 §5.4 (metric replacement) |
| I6 | §5 vs §17 | §5 says minimum useful corpus = **4** per problem ("2 families × 2 variants"); §17 sets the POC at **5** per problem. Neither supports a held-out split once a family has 1 member | Resolved by V2 §8.2: **3 per family** is the validation-grade minimum; < 3 produces `VALIDATION_LIMITED` (§7.3) |
| I7 | §11 metric list | `family_coverage ≥ 0.85` was stated without a denominator rule, which is what allowed a 1.0 over 3 held-out solutions to look adequate | Resolved by V2 §7.4 (`held_out_population` gate) |

### 11.1 LLM boundary (explicit, restored)

- **Offline only.** Permitted uses: (1) optional *proposal* of family labels/merge-split
  suggestions for a human to accept or reject; (2) nothing else in the GT pipeline.
- **Never runtime.** The runtime loads a validated, versioned GT artifact and runs the frozen
  deterministic analyzer. No network call participates in a verdict.
- **Never authoritative.** An LLM proposal enters the corpus in `proposed` state and cannot be
  promoted without a human decision (§3.3, §3.5).
- **Never the same source as the analyzer's own output.** A proposal derived from analyzer
  detections would be circular; proposals must be derived from code and problem text, and are
  compared against analyzer output only *after* the human decision is recorded.
- **Not shipped in the POC.** The JSON-first POC omits it entirely (OPEN-6).

---

## 12. Next POC plan (to validate V2; not to be run now)

### 12.1 Name and scope

`experiments/code_analysis_evaluation/gt_poc_v2/` — same JSON-first, no-DB, no-network, no-LLM
shape as the first POC. Phases 1–5 only. No Phase 6, no schema, no promotion.

### 12.2 Corpus (per §8)

- 12 problems × 8 solutions = **96** reference solutions.
- Same 8 problems as POC v1 where useful + 4 added (grid/BFS, DP bottom-up, backtracking,
  union-find).
- **Duplicate-containing by construction:** ≥ 3 problems contain a byte-identical D1 pair
  (e.g. one DB-derived solution and one authored restatement); ≥ 3 families contain a D2
  syntax variant (renamed variables / reformatted, same algorithm); ≥ 3 solutions are
  deliberately `ZERO_EVIDENCE` (e.g. `Counter == Counter`, `sorted == sorted`, `bisect`).
- **Family-level human labels required**: the review sheet must be filled in (at least 6
  families fully `APPROVED`) so `activation_rate` and `label_expressibility` are measurable.
  A run with 0 approved labels cannot evaluate §4 and must report that as a limitation.
- Canonical negative controls enabled (§6) with the N_min and rule-3 reporting.

### 12.3 Mechanism to implement (exactly V2 §1–§9)

`ingest → normalize → S1 tiers → S2 PEC partition → S3 profile refinement → S4 agglomeration
→ family labels (blind sheet) → §4 derivation → family-first split → §7 metrics → §6 controls`

### 12.4 Outputs

`reference_solutions.json`, `normalized_solutions.json`, `families.json` (with `grouping_reason`,
`merged_because`, `skeleton_spread`), `family_labels.json`, `review_sheet.{json,md}` (blind),
`label_comparison.json` (post-hoc), `derivation_outcomes.json` (per-family §5.2 state +
`required_expected`), `negative_controls.json` (per §6.4), `validation.json` (per §7.4),
`run_manifest.json`, `POC_V2_REPORT.md`.

### 12.5 Acceptance criteria (all must be reported; none may be forced)

| criterion | gate | POC v1 baseline |
|---|---|---|
| singleton families | ≤ **25%** | 74% |
| families per problem | ≤ **4** | up to 5 |
| `held_out_population` | ≥ **3 × problems** (≥ 24) | 8 |
| `discrimination_FP` (canonical rule) | ≤ **0.05** | 0.1228 |
| `group_satisfiability` | = **1.00** | 1.00 |
| `narrowing_violations` | = **0** | n/a (new) |
| `family_coverage` | ≥ **0.85** on families with a held-out sample | n/a |
| D1 / D2 exercised | ≥ 3 each, classified correctly | 0 / 0 |
| `ZERO_EVIDENCE` handling | 3 cases, none confirmed, none labeled, none used as controls | untested |
| divergence distribution | reported by state; `activation_rate` reported | not measurable |

### 12.6 Explicit non-actions

- If grouping still over-splits, **do not tune**; revise §1.5 discriminants (V3).
- If `discrimination_FP` still exceeds the gate, **do not weaken §6**; the failing groups are
  by construction label-faithful, so the finding is a **label/vocabulary** finding and is
  routed to OPEN-2/OPEN-6.
- If a criterion fails, report it; do not adjust rules, thresholds, or corpus to pass.

---

## Final section

### 1. What changed from V1 → V2

1. **§8 grouping replaced.** Flat concept-set partitioning → four stages: concept **tiers**
   (PEC vs SUPPORT), PEC partition, coarse structural-profile refinement, deterministic
   agglomeration with a `PEC_SUBSET_MERGE` anti-split guard.
2. **Skeleton demoted.** Edit-distance is no longer a split trigger and τ is no longer a
   grouping parameter; skeleton supplies bounded features and a diagnostic only.
3. **§9 labeling replaced.** Problem label is a candidate pool; families receive labels
   through an explicit family-level, external channel; a deterministic consistency screen
   gates inheritance.
4. **Derivation rule replaced.** `required = L` when `L ⊆ observed`; **never narrow** on
   partial observation (`REVIEW_REQUIRED`) instead of silently intersecting.
5. **Specificity floor added.** A group made only of SUPPORT concepts cannot auto-activate.
6. **Divergence formalised** into seven mutually exclusive family states; the metric becomes
   a distribution + `narrowing_violations = 0`.
7. **Negative-control rule defined canonically** (eligibility, exclusions, denominator,
   N_min, same-family reporting).
8. **Validation made family-first** with `VALIDATION_LIMITED` / `INSUFFICIENT_VALIDATION`
   states and a `held_out_population` gate.
9. **Corpus requirement raised** to 12 × 8 = 96 with deliberate D1/D2/zero-evidence content.
10. **Zero-evidence made first-class** with explicit enter/group/hold-out/label/control rules.
11. **DB-model inconsistencies corrected** (five tables / three columns; `approval_state`
    duplication; ordering) and the missing **LLM boundary** section restored.

### 2. Which POC finding caused each change

| change | finding |
|---|---|
| Concept tiers (PEC/SUPPORT) and PEC partition | **F3, F4** (LC 21 5/5, LC 1 hash split identically) |
| Skeleton demoted from splitter to cross-check/feature | **F4** (identical signatures split by distance) |
| Profile refinement replacing edit distance | **F1, F2** (31 families, 74% singletons) |
| `PEC_SUBSET_MERGE` anti-split guard | **F4** (LC 560 dict `.get()` variant) |
| Family-level labeling | **F5, F6** (12 families unlabelable; problem label applied to all families) |
| Never-narrow derivation + specificity floor | **F7, F8** (single-generic-concept groups; 0.1228 FP, 20/21 hits attributable) |
| Divergence states + metric replacement | **F9, F13** (0.8529 agreement; LC 21/704/242 divergence) |
| Canonical negative-control rule | **F14** (raw 0.1702 vs disjoint 0.1228 from the same run) |
| Family-first split + population gate | **F2, F10** (singletons; 8/40 held-out) |
| Corpus requirement raise (12 × 8, D1/D2/zero-evidence) | **F11, F12, F2** (0 D1/D2; 6/40 zero-evidence; singletons) |
| Zero-evidence first-class state | **F12** |
| DB/LLM-boundary corrections | **I1–I7** (spec self-consistency; not a POC failure) |

### 3. What remains OPEN

All twelve items in §10.2, with OPEN-2 (PEC ratification) and OPEN-6 (LLM usage) the most
consequential. §10.1 lists what the POC has now resolved. **No OPEN value is chosen in this
document.**

### 4. Exact next POC experiment

`gt_poc_v2` per §12: 12 problems × 8 reference solutions (96), duplicate-containing corpus
with ≥ 3 D1 pairs, ≥ 3 D2 variants and ≥ 3 zero-evidence cases; family-level human labels with
≥ 6 approved families; canonical negative controls; the S1–S4 grouping of V2 §1; the §4
derivation; the §7 family-first split; outputs and acceptance criteria exactly as listed in
§12.4 and §12.5. Not run in this task.

### 5. Conditions required before Phase 6 (DB / versioning / promotion)

Immutable **and all satisfied**:

1. Next POC executes end-to-end and meets §12.5's structural criteria (singletons, families
   per problem, D1/D2 exercise, `held_out_population`, `group_satisfiability`,
   `narrowing_violations`).
2. `discrimination_FP ≤ 0.05` under the **canonical** §6 rule.
3. `family_coverage ≥ 0.85` measured on a population meeting the §7.4 gate.
4. A real human review round has produced `APPROVED` family labels (OPEN-3, OPEN-4, OPEN-12).
5. OPEN-2 (PEC list) and OPEN-8 (profile discriminants) ratified by a human.
6. §11 corrections accepted so the schema is designed from consistent text.

Until **all six** hold, Phase 6 would freeze a grouping/labeling contract that the POC has not
validated — which is exactly the failure this revision exists to prevent.

### 6. Is the revised architecture ready for implementation?

**Design-ready, not implementation-ready.** The V2 contract is now
specific enough to build (`gt_poc_v2`), deterministic, and non-circular: every derivation rule
is stated in terms of PEC/SUPPORT tiers, observed-vs-declared concepts, and explicit refusal
states. But three things are still unproven: the grouping still has to demonstrate it stops
over-splitting (OPEN-8), the derivation still has to demonstrate it removes the false-positive
pairs without losing coverage (§4.3's prediction is untested), and a human must ratify the PEC
list (OPEN-2). Therefore:

**B. The POC exposed specific design flaws; the specification has now been revised, and the
revised design must be validated by the `gt_poc_v2` experiment (§12) before any Phase 6 work.**
