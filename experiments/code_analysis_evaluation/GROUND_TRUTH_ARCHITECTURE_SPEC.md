# Ground-Truth Generation, Validation, and Versioning Architecture — Implementation Specification

**Status:** design / specification only. No production code, shadow analysis,
detectors, techniques, strategies, matcher behaviour, DB rows, or existing ground
truth were modified. Nothing here is implemented yet.

**Preconditions (frozen, do not redesign here):**
- Structural Analysis / Vocabulary Layer 2 (VL2) is frozen and validated.
- The runtime pipeline is fixed: `source → structural facts → techniques →
  strategies → solution-group matching → CONFIRMED / UNRESOLVED / CONTRADICTED`.
- The V1 vocabulary registries are frozen: `VALID_TECHNIQUES` (13),
  `VALID_STRATEGIES`, `PATTERN_TO_V1_MAPPING`, `pattern_family()`.
- Known taxonomy boundaries are accepted, not to be reopened here (e.g.
  `prefix_sum → sequential_accumulation` breadth; see
  `PREFIX_SUM_TAXONOMY_AUDIT.md`, `PREFIX_SUM_PRODUCTION_FALSE_CONFIRMATION_AUDIT.md`).

---

## 1. Problem statement

PathForge's analysis quality is bounded by the quality of its ground truth (GT),
and GT is currently *authored by a single LLM prompt with no independent
evidence and no validation*. The conceptual workflow
(*reference solutions → normalize/deduplicate → identify families → derive groups
→ validate → version → deterministic consumption*) has no implementation, no data
model, and no measurement.

This specifies exactly how to build that pipeline so that:

1. GT is **derived from observed implementations** and **external
   metadata**, not from the analyzer's own output (§6 independence rule);
2. every GT decision is **reproducible, auditable, and versioned** (§10, §11, §14);
3. the **runtime stays deterministic** and LLM-free for judgment (§12);
4. the whole thing is **small enough for one student project** (§13, §18).

## 2. Current limitations (measured against the codebase)

| # | Limitation | Where |
|---|---|---|
| L1 | GT is authored solely by one LLM call. `build_ground_truth()` → `call_llm()` (`openrouter_client.py`, `openai/gpt-4o-mini`, one prompt, `{"patterns", "confidence"}`) → normalize → build groups → store. | `ground_truth_builder.py:583`, `llm/openrouter_client.py:16,48` |
| L2 | **No reference corpus exists.** No table, no files, no ingestion path. GT derives from the *problem description* only. | absent |
| L3 | **No validation.** Nothing checks that a problem's groups are actually satisfiable by real accepted solutions, or that they *discriminate* against other solutions. | absent |
| L4 | **No versioning.** `problem_ground_truth` is a single mutable row keyed by `problem_id`, updated in place via `ON CONFLICT DO UPDATE`; only `created_at`/`updated_at` remain. A regeneration destroys the prior GT. | `schema_pg.sql:135`, `ground_truth_builder.py:931` |
| L5 | **No provenance beyond an authority tier.** `VALID_AUTHORITY_TIERS` (bootstrap/llm_proposed/structurally_observed/externally_listed/editorial) exists, but stored groups carry only `evidence`/`authority_tier` and often an empty `provenance` list. | `ground_truth_builder.py:59,931` |
| L6 | **Semantic validation is shallow and self-referential.** `_validate_group()` checks vocabulary membership, required/excluded overlap, threshold bounds, and strategy mutual exclusion (`coherence.py`) — all *internal consistency*, never *external truth*. | `ground_truth_builder.py:827` |
| L7 | **Circularity risk is structural.** The same vocabulary/pipeline that a group is used to *validate* is the thing that derives the group's concepts (`_derive_concepts_from_patterns`, `refresh_group_vocabulary`). | `ground_truth_builder.py:335,431` |
| L8 | **No approval state.** `validation_status` is set only by the *generator* (`'llm_proposed'`); there is no human gate, no promotion step. | `ground_truth_builder.py:931` |
| L9 | **Refresh is ad hoc.** Vocabulary re-derivation happens at *load* time (`_load_ground_truth` → `refresh_group_vocabulary`), so an obsolete concept can be silently rewritten on read, with no audit trail. | `problem_resolver.py:268` |
| L10 | **Evaluation corpora are not GT corpora.** The 46-record production set and the 301-case disjoint set exist only as evaluation artifacts; using them to *derive* GT would leak. | `experiments/code_analysis_evaluation/` |

## 3. Proposed architecture

Five offline stages, one promotion gate, one runtime edge:

```
OFFLINE (batch, human-gated)
  ┌──────────────┐   ┌───────────────┐   ┌────────────────┐   ┌──────────────┐   ┌────────────────┐
  │ 1 INGEST     │→  │ 2 NORMALIZE   │→  │ 3 GROUP        │→  │ 4 LABEL      │→  │ 5 VALIDATE     │
  │ reference    │   │ signatures +  │   │ deterministic  │   │ independent  │   │ held-out +     │
  │ solutions    │   │ dedup ladder  │   │ family cluster │   │ label source │   │ discrimination │
  └──────────────┘   └───────────────┘   └────────────────┘   └──────────────┘   └───────┬────────┘
                                                                                         ↓
                                                                        ┌────────────────────────────┐
                                                                        │ 6 VERSION + APPROVAL GATE  │
                                                                        │ immutable gt_version rows  │
                                                                        └───────────────┬────────────┘
                                                                                        ↓ (explicit promote)
RUNTIME (per request, deterministic, no LLM)
  load active gt_version → AST facts→techniques→strategies → match → CONFIRMED / UNRESOLVED / CONTRADICTED
```

**Design principle — the independence rule:** the *authority* for a label or a
required-concept set must come from a source **outside the analyzer under test**
(external/editorial metadata, or human review). The analyzer may *describe* and
*measure* a family; it may not *create* the label that validates it. §6 and §8
make this operational with a **discrimination test**.

**Everything offline is a file→script→table pipeline**, matching the existing
`experiments/code_analysis_evaluation/runners/*` style. No services, no queues.

## 4. Data-source strategy

| source | verdict | notes |
|---|---|---|
| **Existing stored PathForge submissions** (`submissions` table, 92 rows today) | **ACCEPTABLE** (primary) | already user-owned, already in DB, includes `code_hash`, `verdict`, `verdict_type`. Small but real. |
| **User-owned exported submissions** via the existing browser-export harness | **ACCEPTABLE** (primary) | the user's own LeetCode history; the harness already exists (`real_submission_harness.py`, fingerprint registry). Consent-by-authorship. |
| **Hand-written reference implementations** by the project author | **ACCEPTABLE** (primary) | highest quality control; the only source for problems the user has not attempted. |
| **Editorial/pattern metadata** (which patterns a problem requires) | **ACCEPTABLE**, manual/curated | used only as a *label seed* (§6); never scraped wholesale. Prefer the problem's own curated `problems.pattern` CSV plus author-entered notes. |
| Public solution repositories (GitHub etc.) | **CONDITIONAL** | only with a permissive license (MIT/Apache/CC) and license file retained; project must record `source_ref` + license. |
| Permitted datasets | **CONDITIONAL** | must be license-checked per dataset; default is *no*. |
| Bulk competitor-submission dumps / scraped LeetCode corpora | **NOT AVAILABLE** | legality and ToS; do not assume access. |
| LeetCode editorials (paywalled or otherwise) | **DO NOT SCRAPE** | reimplement the *idea* in the author's own code; do not copy editorial source. |
| Automated LeetCode submission scraping / crawler | **DO NOT BUILD** | explicitly out of bounds (already a standing constraint). |

**Required manual input:** editorial pattern metadata, and final label/family
approval. Everything else can be automated.

**Rule:** every ingested solution row must carry `source_type`
(`pathforge_db` | `user_export` | `authored` | `licensed_repo`) and `source_ref`
(DB id, file path, or repo URL + license). Solutions with unknown provenance are
rejected at ingestion.

## 5. Corpus-size recommendation

Reasoning from what grouping needs, not from what would be nice to have:

- A problem typically has **1–3 genuinely distinct solution families**.
- Each family needs **≥2 implementations** to be distinguishable from a lucky
  one-off, and **≥2 syntax/implementation variants** to prove the family key is
  name/syntax invariant.
- Therefore **5–8 reference implementations per problem** covers 2–3 families
  with variants. **Minimum useful: 4** (2 families × 2 variants) — enough to
  detect a family split, not enough to be confident it is exhaustive.

**Saturation:** stop adding implementations per problem when a batch of 5 new
implementations adds **no new family** and **no new structural-fact/technique
signature**. Practically this happens by ~6–10 for typical problems; for
problems with many solutions (e.g. two-pointers, sliding window) expect more.

**POC target:** **8 problems × 5 implementations = 40 reference solutions**
(§18). **First production target:** 25–40 problems, ≥5 each, queued only for
problems that appear in the live `submissions` table or the recommendation flow.

**Explicitly rejected:** "collect thousands per problem." With ≤3 real families,
the marginal information beyond ~10 is duplicate-detection, not GT quality.

## 6. Sampling strategy

Ingestion is a **stratified ladder**, applied in order, with every stage recorded
so a solution is never silently dropped:

**Stage A — quality gate** (§7): keep only solutions with positive acceptance
evidence; keep `brute_force`/inefficient solutions but *quarantined into their own
family*, never deleted (they are valid, just not representative — §15 "rare valid
approaches discarded").

**Stage B — dedup ladder** (four distinct levels, all reported):

| level | identity | action |
|---|---|---|
| **D1 exact duplicate** | raw-text hash | collapse; keep first + `duplicate_of` |
| **D2 syntax variant** | whitespace/comment-stripped + identifier-canonicalized hash | **keep** (this is the variant evidence) but mark `variant_of` a canonical member |
| **D3 same algorithm, different implementation** | structural signature (facts+technique multiset) **equal**, AST skeleton distance < τ | keep, same family, mark `same_family_as` |
| **D4 genuinely different solution family** | structural signature **differs**, or skeleton distance ≥ τ | **new family** |

The distinction that matters: **D2 exists to prove the family key ignores names
and formatting; D3 exists to prove it ignores implementation restatement; D4 is
the only thing that creates a new family.** Conflating D2/D3 is the main way a
corpus becomes biased toward the style of its collectors.

**Stage C — coverage audit:** after grouping, report per problem: number of
families, members per family, and which sources contributed. Flag problems with
1 family + 1 source (fragile) and problems with an unrepresentedly large family
(possible under-splitting).

## 7. Normalization model

**Do not replace the source.** Normalization produces *derived comparison keys*;
the runtime always analyzes the original `code_text`.

Never normalize away algorithmically meaningful structure. Explicitly **not**
normalized: operators, control flow, loop nesting, subscript/index structure,
call targets (builtin vs method), numeric literals' *values*, and any identifier
that carries structural role (container vs index vs scalar) — those are exactly
what the pipeline detects.

| key | definition | used for | must NOT be used for |
|---|---|---|---|
| `raw_hash` | sha256 of exact text | D1 | anything else |
| `norm_hash` | whitespace collapsed, comments/docstrings stripped, identifiers renamed `v0..vN` by first occurrence | D2 near-dup | family identity (names are gone) |
| `fact_signature` | sorted multiset of structural-fact types (+ selected attributes: operators, container kinds) | D3 | labels |
| `technique_signature` | sorted set of `(technique_id)` from the frozen pipeline | D3/D4, family key input | label *authoring* (§6 independence rule) |
| `strategy_signature` | sorted set of `(strategy_id)` from the frozen pipeline | family key input | label authoring |
| `skeleton` | coarse AST control-flow shape: statement-kind sequence with expressions abstracted to `{Name, Literal, Subscript, Call, BinOp(op), Compare(op)}` | D3/D4 distance, cross-check | final family decision alone |
| `complexity_est` | optional; derived estimate (loop nesting × input scaling) with confidence | advisory tie-break | hard family boundary |

Identifier renaming is a **comparison-only transform** and must never be written
into `reference_solutions.code_text`.

## 8. Solution-family grouping mechanism

Comparison of the options in the brief:

| option | deterministic | name-free | explains *why* | cost | verdict |
|---|---|---|---|---|---|
| A. AST/structural similarity | yes | yes | partially (structure) | low | **used as a cross-check**, not primary |
| B. technique/strategy signature | yes | yes | yes (names the concept) | low | **primary key** |
| C. complexity + structural | yes | yes | partially | low | **advisory only** (complexity estimates are noisy) |
| D. clustering | yes (if fixed) | yes | no | medium | used only for *tie-breaks* within a signature bucket |
| E. LLM-assisted grouping | **no** | — | yes | medium | **offline proposals only**, human-approved |
| F. hybrid | yes | yes | yes | low–medium | **chosen** |

**Chosen mechanism (deterministic, hybrid):**

1. **Primary partition** — group by `technique_signature` ∪ `strategy_signature`
   under the frozen pipeline, restricted to concepts the problem's label seed
   (§9) admits. This is deterministic and name-free.
2. **Skeleton refinement** — within a signature bucket, split when skeleton
   distance ≥ τ (prevents one bucket hiding two families that happen to share a
   coarse signature, e.g. a bucket containing both a 1-D and a 2-D recurrence).
3. **Cluster tie-break** — only where the refined groups are still ambiguous, run
   a fixed deterministic agglomerative pass (single key, fixed τ, no randomness).
4. **Anti-split guard** — merge two refined groups when their *differences* are
   purely D2/D3 (names, formatting, restatement). This is the guard against
   **over-specific clustering**.
5. **LLM (offline, only)** — after step 4, for each problem, produce a *proposal
   sheet*: "these two families look mergeable / this family looks split". The LLM
   sees the problem statement + anonymized per-family structural summaries.
   **A human accepts or rejects every proposal.** No proposal is ever applied
   automatically. This is the guard against **under-specific clustering**.
6. **Record the decision** — `family_key`, the signatures that produced it, the
   skeleton τ used, and whether a human changed anything.

τ is a single documented constant, fixed per `gt_taxonomy_version`, and changed
only by an explicit spec revision (never tuned per problem).

## 9. Label-generation mechanism

**Definition of "label":** the V1 concept set a family's solution group *requires*
(plus optional/excluded), and the legacy pattern name(s) the family corresponds
to.

**Independence rule (breaks circularity — §15 F1):**

- **Concept IDs** come from the frozen `VALID_TECHNIQUES`/`VALID_STRATEGIES`
  registries. Fixed input, not derived.
- **The label assignment** (which concepts this family requires) must be
  supported by a source **outside the analyzer under test**, in this order of
  precedence:
  1. **`editorial` / `externally_listed`** — the problem's own curated
     `problems.pattern` CSV and author-entered pattern notes → mapped through the
     frozen `PATTERN_TO_V1_MAPPING`.
  2. **Human review** — a reviewer confirms the required set for the family while
     *blinded to the analyzer's detection of the members* (the review sheet shows
     the code and problem, not the detected techniques). Only afterwards is the
     analyzer's detection shown, as a comparison.
  3. **LLM proposal (offline)** — may draft candidate concepts from the problem
     statement + family summaries, with `authority_tier="llm_proposed"`, always
     human-approved before promotion.

- **The analyzer's detection is measurement, not authorship.** It is used to
  *design the required set's satisfiability* and to *report agreement*, never to
  become the label. Concretely: a label is accepted only if it passes §10's
  **discrimination test**, which by construction cannot be passed by a group that
  merely mirrors the analyzer.
- **`structurally_observed`** is an authority tier permitted only when the label
  is corroborated by rule 1 or 2 — never a standalone justification.

**Required/optional/excluded derivation** per family: `required` = concepts present
in *all* members of the family and admitted by the label seed; `optional` =
concepts present in *some* members; `excluded` = concepts that appear in the
problem's other families' `required` sets or that the problem's negative controls
exhibit (i.e. what would make the group over-accept).

## 10. Quality filtering

**What "accepted" means:** the solution passed the judge's hidden tests on the
problem. It proves **correct output on those tests**. It does **NOT** prove:

- optimality or intended complexity (an accepted O(n²) solution is still valid);
- idiomaticity or representativeness;
- general correctness beyond the test set (no proof of absence of edge-case bugs);
- that it is not test-fitted (hardcoded outputs).

Handling:

| class | action |
|---|---|
| incorrect / fails | **exclude** from the corpus (record why) |
| accepted but inefficient / brute force | **keep, quarantined into its own family** (do not discard — §15 F5) |
| accepted, unusual approach | **keep as a family**; mark `REVIEW_REQUIRED` if it is a singleton with no editorial pattern support |
| partially correct / fails edge cases | exclude, but record — these are useful as *negative controls* (§11) |
| duplicates | collapsed per §6 D1 |
| syntactically valid but semantically broken (e.g. returns a constant) | **exclude from positives, retain as negative control** |

## 11. Validation methodology

**Split:** for each problem, partition the reference corpus into
**derivation split (≈60%)** and **held-out split (≈40%)**, stratified by family
(every family contributes to both) and by source. Solutions are never in both.

**Derive** the family partition and groups on the derivation split only.
**Evaluate** on the held-out split. Never derive from the held-out set.

**Required metrics (per problem and aggregate):**

| metric | definition | target |
|---|---|---|
| `family_coverage` (recall) | fraction of held-out solutions that satisfy ≥1 derived group | ≥ 0.85 |
| `positive_confirm_rate` | fraction of held-out solutions that CONFIRM | = `family_coverage` |
| `discrimination_FP` | fraction of **cross-problem negative controls** (see below) that wrongly CONFIRM | ≤ 0.05 |
| `label_agreement` | agreement between derived required set and the independent (editorial/human) label | ≥ 0.90 |
| `unresolved_rate` | fraction of held-out solutions left UNRESOLVED | recorded, not targeted |
| `group_satisfiability` | every derived group is satisfied by ≥1 derivation-split member | = 1.00 (hard) |

**Discrimination test (the anti-circularity device):**
For each derived group, evaluate it against:
1. all held-out solutions of the **same** problem → must confirm its own family;
2. a **negative control set** of solutions for *other* problems (sampled across
   different families) → must **not** confirm.

A group that confirms everything is rejected regardless of coverage. This is the
cheapest test that cannot be satisfied by an analyzer merely agreeing with itself,
and it directly targets the failure family the audits found (over-broad required
sets).

**Minimum acceptance criteria for promotion:** all of
`group_satisfiability = 1.00`, `discrimination_FP ≤ 0.05`, `family_coverage ≥ 0.85`,
`label_agreement ≥ 0.90`, zero empty-`required` matchable groups, and every group
traceable to a non-analyzer label source.

## 12. Uncertainty model

Explicit states, stored (not inferred):

| state | meaning | runtime effect |
|---|---|---|
| `CONFIDENT` | passed all §11 criteria with human approval | groups are active; submission matching runs normally |
| `REVIEW_REQUIRED` | derived but a criterion is unmet, or an LLM/reviewer proposal is unresolved, or a family is a weakly-supported singleton | groups active **but flagged**; submissions matched against it return `UNRESOLVED` rather than CONFIRMED when only a flagged group is involved |
| `UNRESOLVED` | no group could be derived (missing vocabulary, insufficient corpus, no independent label) | problem ships with **no active groups**; runtime returns `UNRESOLVED` (never invents a group) |
| `REJECTED` | failed validation or was superseded | not loaded |

**Refusal rule:** GT must refuse to assign a group when (a) no independent label
source exists, (b) the derivation split has <2 members in a family, (c) the
discrimination test cannot be run (no negative controls available), or (d)
required concepts cannot be expressed in the frozen vocabulary. Refusal is
`UNRESOLVED`, never a guessed group. This is the existing Batch 2A safety
invariant generalised to the corpus layer.

## 13. Versioning / provenance

Three independent version axes — never conflate them:

| axis | example | changes when |
|---|---|---|
| `taxonomy_version` | `v1` | `VALID_TECHNIQUES`/`VALID_STRATEGIES`/`PATTERN_TO_V1_MAPPING` change |
| `pipeline_version` | `extractor=1.0.0, relations=1.1.0, strategy=1.0.0` | any shadow analyzer constant changes (`data_structures.py`, `relations.py`, `strategies.py`) |
| `gt_version` | `3236:v1`, `3236:v2` | any GT content changes for a problem |

Rules:

1. **Immutable GT rows.** A new GT is a **new `gt_version` row**. Existing rows
   are never updated in place (this replaces today's `ON CONFLICT DO UPDATE`).
2. **Pinned compatibility.** Each `gt_version` records the `taxonomy_version`
   and `pipeline_version` it was validated against. It is valid for that
   combination; a pipeline bump marks it `STALE` (still loadable, flagged).
3. **Explicit promotion.** Only a `CONFIDENT` + approved version may be active.
   Promotion is a separate, recorded action (`approved_by`, `approved_at`).
4. **Reproducibility.** Given a `gt_version` id, the exact groups and the exact
   provenance are recoverable without re-running the pipeline.
5. **Provenance fields** (stored JSON): each family's member solution ids, the
   signatures used, the skeleton τ, the label source (`editorial` / `human` /
   `llm_proposed`+approved), the negative-control set ids, and the validation run
   id.
6. **Approval state:** `draft` → `validated` → `approved` → `active` (or
   `rejected` / `superseded`). Only `active` is loaded at runtime.

## 14. Refresh process

**Triggers to reprocess a problem** (any of):
- a new solution family is discovered in a new reference batch;
- `submissions` for the problem show a confirmation distribution inconsistent
  with the active GT (e.g. ≥2 CONFIRMED submissions with divergent satisfied
  groups, or any submission confirmed where a human says the approach is wrong);
- `taxonomy_version` changes;
- `pipeline_version` changes (marks STALE, forces re-validation);
- an accepted solution arrives that satisfies no active group (coverage miss);
- a scheduled review (e.g. per release) for problems with `REVIEW_REQUIRED`.

**What regeneration does:** re-runs §6–§11 for that problem, produces a **new
`gt_version`** in `draft`, and stops. It never activates automatically.

**New solution families appearing:** they become a new family; if the family
requires concepts outside the frozen vocabulary, the problem becomes
`UNRESOLVED` with the missing vocabulary named (never a guessed group).

**Old versions remain reproducible:** because GT rows are immutable and
`problem_ground_truth.active_gt_version_id` is a pointer, rolling back is a
pointer change.

**Regression testing of GT changes:** before promotion, the candidate version is
run through:
1. the problem's own held-out split (§11);
2. the **GT regression set** — a small fixed set of (problem, submission,
   expected-outcome) triples curated from production, including the known
   correct confirmations and any known false confirmations;
3. a cross-problem discrimination sample.
Promotion is blocked if (2) regresses.

## 15. Runtime / offline boundary

**OFFLINE (never on the request path):** corpus collection, normalization keys,
family grouping, label proposal/review, validation, versioning, promotion.
Implemented as `experiments/code_analysis_evaluation/runners/gt_*.py` scripts +
a review spreadsheet/JSON, not as services.

**RUNTIME (unchanged shape, GT-fed):**

```
load active gt_version for problem            (DB read, deterministic)
→ run frozen AST analysis (facts→techniques→strategies)
→ match submission against the active groups  (existing matcher, unchanged)
→ CONFIRMED / UNRESOLVED / CONTRADICTED       (existing verdicts)
```

**Hard rule:** no LLM on the runtime path. No network call for GT judgment.
Runtime behavior is a pure function of `(code, active gt_version,
pipeline_version)`. If `pipeline_version` ≠ the version the GT was validated
against, the runtime may still match but must mark the result as
`validation_basis: stale` rather than silently trusting it.

## 16. Minimal DB model

Four new tables + two columns. No separate `solution_group` table (groups stay in
`gt_versions.groups_json`). No vector DB; similarity is exact-key + a documented
distance over skeleton signatures.

```
reference_solutions
  id                SERIAL PK
  problem_id        INT  → problems(id)
  source_type       TEXT   -- pathforge_db | user_export | authored | licensed_repo
  source_ref        TEXT   -- db id / file path / repo URL (+license text)
  language          TEXT
  code_text         TEXT
  raw_hash          TEXT   -- UNIQUE per (problem_id, raw_hash)  → D1
  norm_hash         TEXT   -- D2
  quality_state     TEXT   -- accepted | brute_force | negative_control | excluded
  acceptance_evidence JSONB -- judge verdict, test count if known
  created_at        TEXT
  INDEX (problem_id), (norm_hash)

solution_families
  id                SERIAL PK
  problem_id        INT → problems(id)
  gt_version_id     INT → gt_versions(id)   -- families are versioned artifacts
  family_key        TEXT                    -- stable label within the version
  signature_json    JSONB                   -- technique/strategy signatures + τ
  member_count      INT
  label_source      TEXT                    -- editorial | human | llm_proposed
  approval_state    TEXT                    -- draft | validated | approved | rejected

solution_family_members
  family_id         INT → solution_families(id)
  solution_id       INT → reference_solutions(id)
  dedup_level       TEXT   -- canonical | variant_of (D2) | same_family_as (D3)
  PK (family_id, solution_id)

gt_versions
  id                SERIAL PK
  problem_id        INT → problems(id)
  version           TEXT   -- 'v1','v2',…
  status            TEXT   -- draft | validated | approved | active | rejected | superseded | stale
  taxonomy_version  TEXT
  pipeline_version  JSONB  -- {extractor, relations, strategy}
  groups_json       JSONB  -- the actual solution_groups (required/optional/excluded/patterns)
  provenance_json   JSONB  -- families, members, sources, τ, label sources, negative controls
  validation_json   JSONB  -- metrics from gt_validation_runs
  created_by        TEXT
  created_at        TEXT
  approved_by       TEXT
  approved_at       TEXT
  UNIQUE (problem_id, version)

gt_validation_runs
  id                SERIAL PK
  gt_version_id     INT → gt_versions(id)
  split_json        JSONB  -- derivation/held-out member ids
  metrics_json      JSONB  -- family_coverage, discrimination_FP, label_agreement, …
  passed            BOOLEAN
  created_at        TEXT
```

Changes to existing tables:

```
problem_ground_truth            -- becomes a POINTER + back-compat cache
  + active_gt_version_id  INT → gt_versions(id)
  + approval_state        TEXT DEFAULT 'llm_proposed'
  (patterns / confidence / solution_groups remain, written from the active version
   for backward compatibility; NO in-place regeneration any more)

submissions
  + gt_version_id_at_analysis  INT   -- which GT judged this submission (audit)
```

The existing `VALID_AUTHORITY_TIERS` becomes the `label_source`/authority enum and
gains a validation requirement: `structurally_observed` and `llm_proposed` are
only promotable with a corroborating editorial/human source (§9).

## 17. POC specification (smallest useful)

| dimension | choice |
|---|---|
| problems | **8**, chosen to span distinct families and to include ≥2 already in the live `submissions` table (e.g. LC 1, 21, 209, 704, 3236 + 3 authored) |
| implementations/problem | **5** → **40 reference solutions** |
| families covered | `two_pointers_opposite`, `sliding_window_variable`, `prefix_sum`(+`hash_map_lookup`), `binary_search_standard`, `hash_map_frequency` |
| sources | 1–3 from `submissions`/`user_export`, the rest hand-written references |
| negative controls | 1 solution per problem from a *different* family (cross-problem controls reused) |
| normalization | implement keys `raw_hash`, `norm_hash`, `technique_signature`, `skeleton` only |
| grouping | technique/strategy signature + skeleton refinement + anti-split guard (steps 1–4); **LLM proposals deferred** |
| label source | `problems.pattern` CSV (editorial) + author review; analyzer blinded during review |
| validation | 60/40 split, all §11 metrics, discrimination test on the cross-problem controls |
| human review | **required** for every family label and every promotion |
| output artifact | `gt_poc/` → `reference_solutions.json`, `families.json`, `review_sheet.(json|md)`, `validation.json`, and one draft `gt_versions` row per problem |

**POC success criteria:** `group_satisfiability = 1.00` for all 8,
`discrimination_FP ≤ 0.05`, `family_coverage ≥ 0.85` on held-out,
zero empty-required groups, and every family traceable to an editorial/human label.

**Can be mocked:** the LLM proposal stage; the `complexity_est` key; the
skeleton distance (replace with exact-signature equality) if time-boxed.

**Must be manual:** editorial pattern entry; family label approval; final
promotion.

**Deferred until after POC:** all DB tables except reading `submissions`/GT;
versioning promotion UX; scheduled refresh.

## 18. Failure modes + mitigations

| id | failure mode | mitigation |
|---|---|---|
| F1 | **Circular GT generation** (analyzer validates itself) | §9 independence rule + §11 discrimination test: a group must confirm its own family *and* reject cross-problem controls; labels need an editorial/human source |
| F2 | **LLM hallucinated strategy labels** | LLM output is `llm_proposed` only, offline, always human-approved, never runtime; hallucinated concepts are rejected by `_validate_group` vocabulary checks |
| F3 | **Biased reference corpus** (one style/source) | §6 stratification by source + coverage audit; flag single-source problems |
| F4 | **Duplicate solutions inflate a family** | D1/D2/D3 ladder; family membership pending dedup; `dedup_level` recorded |
| F5 | **Rare valid approaches discarded** | brute-force/unusual solutions retained as separate families with `REVIEW_REQUIRED`, never deleted |
| F6 | **Over-specific clustering** (one family split into many) | anti-split guard (§8 step 4) + merge proposals |
| F7 | **Under-specific clustering** (families merged) | skeleton refinement (§8 step 2) + LLM *proposals* for splits (§8 step 5), human-approved |
| F8 | **GT drift** (load-time silent rewrite) | remove load-time vocabulary rewriting as an authority: re-derivation becomes a *new version*, not an in-place read mutation; §13 immutability |
| F9 | **Taxonomy change invalidating old GT** | `taxonomy_version` pinning + `STALE` marking + §14 regression set; rollback is a pointer change |
| F10 | **Over-broad required set** (the prefix_sum/`sequential_accumulation` class of problem) | `discrimination_FP` is a first-class acceptance gate, not a report metric |
| F11 | **Under-broad required set** (rejects valid variants) | held-out `family_coverage` gate; D2 variants must confirm |
| F12 | **Test-fitted solutions accepted as references** | negative-control quarantine; prefer authored/user-owned sources; flag suspicious constant-return solutions |
| F13 | **Non-reproducible GT** | immutable `gt_versions` + recorded `pipeline_version`/`taxonomy_version`/τ + validation run id |

## 19. Phased implementation roadmap

**Phase 0 — specification (this document).**
Inputs: codebase survey, the VL2 audit set. Outputs: this spec + OPEN decisions
(§21). Dependencies: none. Mockable: n/a. Human review: approve this spec.

**Phase 1 — corpus ingestion.**
Inputs: `submissions` rows, user exports, authored references, `problems.pattern`.
Outputs: `gt_poc/reference_solutions.json` with `source_type`/`source_ref`/hashes.
Dependencies: `real_submission_harness` fingerprint registry (reuse as-is).
Mockable: licensed-repo source. Human review: provenance/license check.

**Phase 2 — normalization.**
Inputs: Phase 1. Outputs: `raw_hash`, `norm_hash`, `fact_signature`,
`technique_signature`, `strategy_signature`, `skeleton` per solution.
Dependencies: frozen shadow pipeline (read-only import). Mockable: `skeleton`
(skip → exact-signature equality). Human review: none.

**Phase 3 — family grouping.**
Inputs: Phase 2. Outputs: `families.json` (family_key, members, signatures, τ).
Dependencies: Phase 2. Mockable: LLM merge/split proposals (defer). Human review:
**required** — confirm family splits/merges.

**Phase 4 — label generation.**
Inputs: Phase 3 + editorial metadata. Outputs: per-family
required/optional/excluded + `label_source`. Dependencies: `PATTERN_TO_V1_MAPPING`.
Mockable: none — labels are the thing being made trustworthy. Human review:
**required**, analyzer-blinded.

**Phase 5 — validation.**
Inputs: Phases 3–4 + negative controls. Outputs: `validation.json` (§11 metrics).
Dependencies: frozen matcher (read-only). Mockable: negative-control set (start
with cross-problem references). Human review: adjudicate failures.

**Phase 6 — versioning.**
Inputs: Phases 4–5. Outputs: `gt_versions` draft rows + promotion records.
Dependencies: Phase 16 DB changes. Mockable: DB (use JSON files until then).
Human review: **required** for promotion.

**Phase 7 — production integration.**
Inputs: active `gt_versions`. Outputs: `_load_ground_truth` reads the active
version pointer; runs record `gt_version_id_at_analysis`. Dependencies: Phases
1–6 + regression set. Mockable: none. Human review: release approval + regression
sign-off.

## 20. Hard constraints (self-check)

- Runtime deterministic: yes — §15, LLM offline only.
- Reproducible: yes — §13 immutability + pinned versions.
- Auditable: yes — provenance JSON + `gt_validation_runs` + per-request GT id.
- Versioned: yes — §13 three axes.
- Small enough: 4 tables, JSON files, scripts; no new services.
- Extensible later: family/label/validation stages are separable.
- **Not introduced:** Kubernetes, distributed pipelines, vector databases,
  complex ML infrastructure, autonomous runtime LLM judging, silent GT
  replacement. Similarity is exact-key + a documented skeleton distance.

## 21. Open decisions requiring human approval

| # | decision | why OPEN |
|---|---|---|
| O1 | **Skeleton distance τ and its metric** | no evidence yet on how separable families are under a skeleton metric; must be calibrated on the POC and then frozen |
| O2 | **Minimum corpus size per problem** | §5 recommends 5–8; the saturation point is unmeasured for specific families |
| O3 | **Negative-control sourcing** | cross-problem controls are a proxy; whether they are strong enough to catch over-broad groups needs POC measurement |
| O4 | **Whether the LLM proposal stage ships at all** | it is optional; if human review alone is sufficient, drop it (simpler, no hallucination surface) |
| O5 | **`complexity_est` inclusion** | estimates are noisy; keep as advisory or omit |
| O6 | **Label-source precedence** when editorial metadata and human review disagree | needs a policy decision (precedence vs escalation) |
| O7 | **DB now vs JSON-first** | tables can be introduced after the POC proves the flow; decide timing |
| O8 | **Whether `REVIEW_REQUIRED` groups should match at runtime at all** | current proposal: match but never CONFIRM alone — needs product sign-off |
| O9 | **Licensed-repo ingestion** | whether to allow third-party permissively-licensed solutions, or authored-only |
| O10 | **Reviewer blinding workflow** | how strictly to hide analyzer output during label review, and how to record that it happened |

---

**Explicitly not decided here:** any change to detectors, techniques,
strategies, the matcher, the frozen vocabulary, or existing GT rows. Those are
out of scope for this architecture; this spec only governs how future GT is
created, validated, versioned, and consumed.
