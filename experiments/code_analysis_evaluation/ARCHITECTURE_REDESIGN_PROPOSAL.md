# PathForge Analysis & Matching — Architecture Redesign Proposal

**Document type:** architecture audit + redesign proposal (DESIGN ONLY)
**Status:** no implementation authorised by this document
**Date:** 2026-09-21
**Author:** engineering (PathForge)

**Invariants honoured while producing this document:**

- no detector, technique, strategy, vocabulary, threshold, matcher, Ground-Truth,
  database or production-runtime file was modified;
- the V2 POC (`experiments/code_analysis_evaluation/gt_poc_v2/`) was read, not changed;
- every claim below is traceable to a file in this repository (paths + symbols given
  inline); where the evidence does **not** justify a single answer, the alternatives
  are stated instead of a decision being invented (§24, §26).

**Change footprint of this task:** one new file (`ARCHITECTURE_REDESIGN_PROPOSAL.md`).
`git status` shows no modification to any tracked production file.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [What was inspected (evidence base)](#2-what-was-inspected-evidence-base)
3. [Current architecture map (traced from code, not from docs)](#3-current-architecture-map)
4. [Current architecture problems](#4-current-architecture-problems)
5. [Evidence from the V1/V2 Ground-Truth experiments](#5-evidence-from-the-v1v2-ground-truth-experiments)
6. [Evidence from real production mismatches](#6-evidence-from-real-production-mismatches)
7. [Technique vs strategy distinction](#7-technique-vs-strategy-distinction)
8. [Generic vs specific evidence model](#8-generic-vs-specific-evidence-model)
9. [UNKNOWN vs ABSENT vs CONTRADICTED model](#9-unknown-vs-absent-vs-contradicted-model)
10. [Compound strategy matching design](#10-compound-strategy-matching-design)
11. [Specific-vs-generic precedence design](#11-specific-vs-generic-precedence-design)
12. [Zero-evidence handling design](#12-zero-evidence-handling-design)
13. [Brute-force policy](#13-brute-force-policy)
14. [Recursive-branching policy](#14-recursive-branching-policy)
15. [Experimental / LLM role](#15-experimental--llm-role)
16. [Proposed target architecture](#16-proposed-target-architecture)
17. [Data flow](#17-data-flow)
18. [Authority boundaries](#18-authority-boundaries)
19. [Migration strategy from the current architecture](#19-migration-strategy-from-the-current-architecture)
20. [What should remain unchanged](#20-what-should-remain-unchanged)
21. [What should eventually change](#21-what-should-eventually-change)
22. [Risks and tradeoffs](#22-risks-and-tradeoffs)
23. [Minimal implementation phases](#23-minimal-implementation-phases)
24. [Questions that genuinely remain unresolved](#24-questions-that-genuinely-remain-unresolved)
25. [Why this is better than detector-by-detector patching](#25-why-this-is-better-than-detector-by-detector-patching)
26. [Final answers (A–E)](#26-final-answers-ae)

---

## 1. Executive summary

PathForge does not have one analysis system with an experimental extension. It has
**three partially-overlapping taxonomies and two independent matchers**, wired together
by a hand-maintained one-way mapping, where the *less* trustworthy of the two matchers
is the one that produces the official user-facing result.

1. **Legacy detector taxonomy** — 36 `pattern_id`s registered under
   `src/ast_detection/detectors/` (e.g. `hash_map_lookup`, `two_pointers_opposite`,
   `array_traversal`, `brute_force`, `sorting`). These are the strings the official
   matcher compares.
2. **Declared problem taxonomy** — `pathforge/ast_engine/patterns.py::ALL_PATTERNS`,
   33 patterns, matching the curated problem CSV. Ground truth is normalised against
   this set (`ground_truth_builder._normalize_patterns`). **It does not contain
   `array_traversal`, `brute_force` or `sorting`** — three of the 36 detectors.
3. **Shadow vocabulary** — techniques `T1–T14` and strategies `S1–S9`
   (`pathforge/ast_analysis/shadow/techniques.py`, `strategies.py`), plus the V2 POC's
   PEC/SUPPORT tiers (`gt_poc_v2/problem_metadata.py`).

The bridge between (1)/(2) and (3) is `ground_truth_builder.PATTERN_TO_V1_MAPPING`, a
one-way, hand-written dictionary. It is lossy by construction
(`MISSING_VOCABULARY_PATTERNS`), and it is the only relation that exists.

The two matchers:

| | official (`src/matching_engine/matching_engine.py`) | shadow (`pathforge/ast_analysis/shadow/matching.py`) |
|---|---|---|
| input | legacy `pattern_id` strings vs `group["patterns"]` | V1 technique/strategy ids vs `group["required"]` |
| decision | set intersection; `FULL_MATCH` / `PARTIAL_MATCH` / `NO_MATCH` | `CONFIRMED` / `UNRESOLVED` / `CONTRADICTED` |
| unknown state | **absent** — a detector's silence is a negative | **absent** — `unsatisfied` is a negative |
| authority | `evidence` field → `verdict_type` | `authority_tier`, but **only gates contradictions** |
| user-facing | primary result | "Experimental Analysis → Likely match" badge |

The observable consequence is the mismatch the teacher reported: for a solution whose
intended approach is `greedy_local`, the official path reports `array_traversal` as the
dominant detection and finds no expected-pattern match, while the experimental path
reports `candidate_selection` as a high-confidence match. **This is not a `greedy_local`
bug and not an `array_traversal` bug. It is the absence of a decision layer.**

Three further findings make the case stronger:

- The project has **already measured** the `array_traversal` problem and reached the
  correct conclusion, five separate times, in `reports and docs/`:
  precision **0.24–0.30**, **106–183 AST false positives**, it fires on **188/301 (62%)**
  of cases, and the explicit recommendation
  *"Demote `array_traversal` to structural primitive (not a scored pattern)"*
  (`SEMANTIC_EXPERIMENT_3C_TAXONOMY_GENERALIZATION_REPORT.md`), with
  *"`array_traversal` demotion ✅ Correct"* (`SEMANTIC_EXPERIMENT_3B_COMPETITION_REPORT.md`)
  and *"`array_traversal`: DISABLE/REWORK"* (`SEMANTIC_EXPERIMENT_2D_REAL_WORLD_REPORT.md`).
  **That conclusion was never enforceable, because nothing in the runtime architecture
  can express "evidence that is not a conclusion". So it was never applied.**
- `brute_force` **already exists in production** as a runtime detector
  (`src/ast_detection/detectors/brute_force.py`, firing on nested loops with a
  structural core = `has_nested or has_branch`). The teacher's concern is therefore about
  live behaviour, not a hypothetical. The post-review report's statement that it is
  "absent from the analyzer entirely" is true only of the *shadow* analyzer.
- The experimental path **already leaks authority**: `shadow-mapper.ts` maps
  `CONFIRMED → "Likely match"` with a success badge, and `matching.py` only downgrades
  `contradicted` for low-authority tiers — `satisfied` becomes `CONFIRMED`
  unconditionally, including for `llm_proposed` and `bootstrap` groups.

The proposal is a **single authoritative reasoning path** with an explicit evidence →
technique → strategy → coverage → family-match layering, a three-valued observation model
(`PRESENT` / `NOT_ESTABLISHED` / `CONTRADICTED`), a declarative concept registry carrying
`tier`, `specificity_rank` and `conclusion_eligible`, a new `PROVISIONAL` match state for
compound families with unestablished components, and a strict hypothesis-only role for
the experimental/LLM path. It is deliberately **additive**: no engine is rewritten, no
threshold changed, no detector patched, and the migration is staged so that each batch is
independently measurable and reversible.

---

## 2. What was inspected (evidence base)

**Production analysis (legacy path)**

- `pathforge/api/services/analysis.py` — `run_analysis()`
- `src/ast_detection/run_analysis.py`, `detector_manager.py`, `coordinator.py`,
  `output_pipeline.py`, `detector_interface.py`, `registry.py`
- `src/ast_detection/detectors/` — all 36 registered detectors (read: `array_traversal.py`,
  `brute_force.py`, `greedy_local.py`, plus the registry listing)
- `src/matching_engine/matching_engine.py`
- `pathforge/ast_engine/patterns.py::ALL_PATTERNS`

**Production orchestration / persistence**

- `pathforge/api/routes/analyze.py`
- `pathforge/services/problem_resolver.py` — `_load_ground_truth`,
  `_split_csv_patterns_to_groups`, `_map_legacy_patterns_to_v1`
- `pathforge/services/ground_truth_builder.py` — `PATTERN_TO_V1_MAPPING`,
  `MISSING_VOCABULARY_PATTERNS`, `pattern_family`, `group_matchability`,
  `refresh_group_vocabulary`, `_store_ground_truth`
- `pathforge/services/persistence.py` — `run_persistence`, `_AUTHORITATIVE_STATES`
- `pathforge/scripts/seed_ground_truth.py`
- `pathforge/elo_engine.py` — `EVIDENCE_K_CEILINGS`

**Shadow path**

- `pathforge/ast_analysis/shadow/shadow_runner.py`, `fact_extractor.py`, `relations.py`,
  `techniques.py`, `strategies.py`, `matching.py`, `coherence.py`, `authority.py`,
  `persistence.py`

**Frontend surfaces**

- `pathforge-frontend/src/services/shadow-mapper.ts`
- `pathforge-frontend/components/experimental-panel.tsx`, `analysis-view.tsx`

**Ground-Truth POC / specs**

- `experiments/code_analysis_evaluation/GROUND_TRUTH_ARCHITECTURE_SPEC.md`
- `experiments/code_analysis_evaluation/GROUND_TRUTH_ARCHITECTURE_SPEC_V2.md`
- `experiments/code_analysis_evaluation/gt_poc_v2/POC_V2_REPORT.md`
- `experiments/code_analysis_evaluation/gt_poc_v2/POC_V2_POST_HUMAN_REVIEW_REPORT.md`
- `experiments/code_analysis_evaluation/gt_poc_v2/GT_ARCHITECTURE_RATIFICATION_SHEET.md`
- `experiments/code_analysis_evaluation/gt_poc_v2/human_review.json` / `.md`
- `experiments/code_analysis_evaluation/gt_poc_v2/problem_metadata.py`, `core.py`
  (`PEC_STRATEGIES`, `PEC_TECHNIQUES`, `SUPPORT_TECHNIQUES`, `concept_tier`)
- `PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md` (technique admission rule §1.1,
  "what a technique is NOT" §1.2, strategy rule §1.3)

**Prior empirical work (this proposal leans on it heavily)**

- `reports and docs/SEMANTIC_EXPERIMENT_1D/1E/2A/2B/2C/2D/3A/3B/3C*_REPORT.md`
- `reports and docs/SEMANTIC_ANALYSIS_ARCHITECTURE.md`
- root-level architecture reconciliation set: `ARCHITECTURE_FINAL_RECONCILIATION.md`,
  `ARCHITECTURE_PREIMPLEMENTATION_AUDIT.md`, `ARCHITECTURE_AUTHORITY_STRESS_TEST.md`,
  `GROUND_TRUTH_AUTHORITY_RECONCILIATION.md`, `FINAL_ARCHITECTURE_VERDICT.md`,
  `FINAL_PREIMPLEMENTATION_SPEC.md`
- evaluation artifacts: `e2e_architecture_evaluation.json`, `fusion_eval_data.json`,
  `shadow_realworld_data.json`, `deep_failure_analysis.json`

---

## 3. Current architecture map

### 3.1 The official path (drives the user-facing result)

```
POST /analyze                             pathforge/api/routes/analyze.py
  └─ resolve_problem(...)                 pathforge/services/problem_resolver.py
       └─ _load_ground_truth()            → groups: [{patterns, required,
                                                  optional, excluded, evidence, ...}]
  └─ run_analysis(code, language, groups) pathforge/api/services/analysis.py
       ├─ ASTAnalysisEngine.analyze()     src/ast_detection/run_analysis.py
       │    ├─ Parser.parse()             → ast.Module            (SyntaxError → 400)
       │    ├─ DetectorManager.detect_all() → [DetectionResult]*36
       │    ├─ Coordinator.aggregate_and_filter()
       │    │     └─ filter(detected and evidence) → sort by confidence DESC
       │    └─ OutputPipeline.package_results()
       │          → {"detected_patterns": [{pattern_id, confidence, evidence}],
       │             "engine_version", "analyzed_at", "patterns_checked",
       │             "patterns_detected"}
       └─ MatchingEngine.match({accepted_solution_groups: [g["patterns"]…]},
                               [{pattern_id, confidence}…])
            → {"match_result", "matched_groups", "unmatched_patterns",
               "confidence_score", "reasoning_signals"}
  └─ run_persistence(...)                 pathforge/services/persistence.py
       ├─ submissions row (primary_pattern = argmax confidence)
       ├─ verdict = "pass" iff match_result ∈ {FULL_MATCH, PARTIAL_MATCH}
       ├─ verdict_type = "authoritative" iff matched group's `evidence` ∈
       │                 {structurally_observed, externally_listed}
       └─ IF authoritative: topic profile, gap signals, Elo, recommendation
          ALWAYS: user streak
```

Key structural facts, read from the code:

- **The coordinator does no reconciliation.** `aggregate_and_filter()` filters and sorts;
  `Coordinator.resolve_overlaps()` — the one method that talks about "hierarchical
  pattern specificity" — is **never called** from `run_analysis.ASTAnalysisEngine.analyze()`
  or `analyze_with_results()`. Its docstring even says
  *"This is a basic implementation … More complex resolution strategies should be
  implemented here"*. Specificity resolution exists as an unused stub.
- **The official decision is set membership, not a score.**
  `MatchingEngine._compute_group_matches()` computes `is_fully_matched = (group ⊆ detected)`;
  `_decide_match_result()` returns `FULL_MATCH` if any group is fully matched, else
  `PARTIAL_MATCH` if any group overlaps by ≥1, else `NO_MATCH`. `confidence_score` is
  computed by `_compute_confidence()` but **does not participate in the decision**.
  `MATCH_THRESHOLD = 0.6` is declared and **never used**.
- **`array_traversal` cannot match anything.** `ALL_PATTERNS` (33) has no
  `array_traversal`; `_normalize_patterns()` filters LLM GT to `ALL_PATTERNS`; the curated
  CSV uses the 33-pattern taxonomy. So `array_traversal` — plus `brute_force` and
  `sorting` — can be *detected* and *displayed* and *become `primary_pattern`*, but can
  never be an expected pattern. They are, in the current architecture, structurally
  inert as far as matching goes, while remaining fully authoritative as far as
  presentation and persistence go.

### 3.2 The dual representation in one group object

`_load_ground_truth()` returns groups that carry **both** representations at once:

```python
{
  "id": ..., "version": ..., "threshold": ...,
  # V1 vocabulary — consumed ONLY by the shadow matcher
  "required":  [...], "optional": [...], "excluded": [...],
  "authority_tier": ..., "provenance": [...],
  # legacy flat patterns — consumed ONLY by the official matcher
  "patterns":            [...],   # may be CSV-curated (overridden)
  "derivation_patterns": [...],   # what the V1 concepts were derived from
  "evidence": ...,                # decides verdict_type in persistence
}
```

Reconciliation is explicitly one-directional (documented in the function docstring):
*"The shadow matcher's V1 fields (required/optional/excluded) are NEVER modified by
reconciliation."* So for any problem whose curated CSV patterns differ from the stored
LLM patterns, **the two matchers are evaluating two different descriptions of the same
problem**, and neither is reconciled against the other.

### 3.3 The shadow path (observational, but user-visible)

```
ast.parse(code)
  → build_relations(tree)                       relations.py
  → extract_structural_facts(tree)              fact_extractor.py
  → detect_techniques(facts, relations)         techniques.py   (T1–T14)
  → evaluate_strategies(technique_evidence, facts)  strategies.py (S1–S9)
  → evaluate_solution_groups(groups, tech, strat, facts)  matching.py
       → CONFIRMED | UNRESOLVED | CONTRADICTED  (+ authority downgrade of CONTRADICTED only)
```

`evaluate_solution_groups()` outcome logic, verbatim in structure:

- `excluded ∩ detected` → `contradicted` (hard negative)
- `required` non-empty and any required concept missing or `presence_confidence < 0.5`
  → `unsatisfied` **(no third state)**
- `required` empty → `unmatchable` (explicit; good) → reported as `UNRESOLVED`
- else → `satisfied` → **`CONFIRMED`, regardless of `authority_tier`**
- group priority: `CONTRADICTED (3) > CONFIRMED (2) > UNRESOLVED (1)`

And on the frontend, `CONFIRMED` is rendered as a success-badged
**"Likely match"** (`shadow-mapper.ts::STATUS_CONFIG` / `STATUS_LABELS`), inside a panel
titled "Experimental Analysis" in `analysis-view.tsx` — i.e. a low-authority,
LLM-derived, unverified group can produce a user-visible confirmation.

### 3.4 Where Ground Truth comes from, and where authority actually is set

| GT origin | `evidence` written | `verdict_type` | Downstream |
|---|---|---|---|
| `ground_truth_builder._build_single_group()` (LLM, normal cache-build path) | `"llm_proposed"` | `analysis_only` | **no Elo, no gaps, no recommendation** |
| `_split_csv_patterns_to_groups()` (fallback path) | `validation_status or "unobserved"` | usually `analysis_only` | same |
| CSV-curated override | appends provenance `csv_curated_override`, sets `authority_tier="human_curated"` — **but `evidence` stays as stored** | `analysis_only` unless stored evidence was authoritative | same |
| `pathforge/scripts/seed_ground_truth.py` | hardcodes `"structurally_observed"` | `authoritative` | Elo / gaps / recommendations **active** |

Two consequences worth stating plainly, because they change what "the system learns" means:

1. **The most human-trusted label (curated CSV) is not authoritative.** CSV override sets
   `authority = "human_curated"`, which is absent from
   `persistence._AUTHORITATIVE_STATES = {"structurally_observed", "externally_listed"}`.
   So a curated problem can be `analysis_only` while a *seeded* problem is authoritative.
   Whether that is the intended policy is a product decision, not a code bug — but it is
   currently an undocumented side effect of which channel wrote the row.
2. **Learning authority depends on a manual seed script, not on analysis.** With
   LLM-built GT, every submission is `analysis_only`: `elo_updates` are always empty,
   gap signals are always empty, recommendations are never logged. This is consistent
   with the reconciliation documents (cold-start suppression is intentional) but it means
   the *observable* learning behaviour of PathForge is effectively gated by
   `seed_ground_truth.py`, and nothing in the analysis architecture can promote a
   problem out of that state except that script.

---

## 4. Current architecture problems

Each problem is stated with its evidence and its architectural (not local) cause.

### P1 — Three vocabularies, no registry, no authority order

There is no single place that says what a concept *is*, what tier it has, whether it may
be a conclusion, or how it relates to other concepts. Instead:

- `src/ast_detection/detectors/*` (36 ids, peer-level, each with a `confidence` float)
- `pathforge/ast_engine/patterns.py::ALL_PATTERNS` (33 ids, the GT/taxonomy vocabulary)
- shadow `T1–T14` + `S1–S9` + `PEC_STRATEGIES`/`PEC_TECHNIQUES`/`SUPPORT_TECHNIQUES`
- `PATTERN_TO_V1_MAPPING` (the only bridge, one-way, lossy)

Effects: the same word means different things in different files
(`prefix_sum` is a production detector `pattern_id`, a legacy GT pattern, and *not* a V1
concept; `hash_map_frequency` is a detector id but `frequency_counting` is the V1 concept);
`array_traversal`/`brute_force`/`sorting` exist in one taxonomy and nowhere else.

### P2 — The official matcher cannot represent "unknown"

`_compute_group_matches()` produces `missing = group - ast_patterns` and
`_compute_unmatched()` returns every expected pattern the detector didn't emit.
There is no state between "expected and present" and "expected and absent". A detector at
`0.01` confidence and a detector that never ran are the same input. `unmatched_patterns`
then flows into the persisted `gap_identified` flag, `GapSignalEngine`, and the
"missing patterns" UI. **`NOT DETECTED` is therefore rendered as `ABSENT` — the exact
collapse the teacher objected to.**

### P3 — The shadow matcher has the same collapse, plus a hard negative

`_evaluate_single_group()` returns `{"outcome": "unsatisfied", "satisfaction": 0.0}` when
`required_met < len(required)`, where `required_met` counts only concepts whose
`presence_confidence >= 0.5`. So `UNKNOWN` and `ABSENT` are merged at a threshold, and the
UI explanation for that state ("Not enough evidence") is produced from the *same* state
that also means "you used a different approach".

Separately, `excluded` produces `contradicted`, a hard negative, from mere presence — a
detector crossing a threshold creates a contradiction.

### P4 — Two matchers can disagree with no arbitration

For the same submission and the same problem, the official matcher returns
`NO_MATCH`/`PARTIAL_MATCH`/`FULL_MATCH` and the shadow matcher returns
`CONFIRMED`/`UNRESOLVED`/`CONTRADICTED`. Nothing compares them, nothing decides which is
right, and nothing tells the user why. Both are shown. This is exactly observed
mismatch #1 and #2 (§6).

### P5 — Confidence is used as if it were specificity

`Coordinator.aggregate_and_filter()` sorts by `confidence` descending;
`persistence.run_persistence()` picks `primary_pattern = argmax(confidence)`;
`strategies._get_primary_strategy()` picks `max(strategy_evidence, key=confidence)`;
`shadow-mapper.ts` shows the first strategy by confidence with a High/Medium/Low label.
A generic observation whose detector accumulates more evidence items outranks a specific
conclusion whose detector is deliberately conservative. `array_traversal` can reach
`1.0` (weights `0.35 + 0.30 + 0.35 + 0.30`, clamped) purely for being a loop with a
subscript somewhere in the file.

### P6 — Generic detectors are unbounded and module-scoped

`ArrayTraversalDetector._detect_subscript_access()` walks the **whole module** and
returns true on the **first** `Subscript` node with a `Name` value — no loop containment,
no relation to the traversal loop, no receiver identity. With
`has_required_signals = has_loop and has_element_access`, almost any array solution
fires. `BruteForceDetector` fires on any nested loop with no notion of whether a specific
strategy is present. This is not over-tuned thresholds; it is a decision layer that treats
observations as conclusions (P5).

### P7 — Zero-evidence is a negative judgment in production

When GT exists but no detector fires: official → `NO_MATCH`,
`unmatched_patterns = all expected`, `gap_identified = true`, `primary_pattern = ""`,
`topic = expected_pattern`, `verdict = "fail"`. The user is told they are missing
patterns, when the truth is the analyzer recognised nothing. (`NO_GROUND_TRUTH` when GT is
absent is correct and should be preserved.)

### P8 — The experimental path already has user-visible authority

See §3.3. `CONFIRMED` is not authority-gated; the frontend maps it to a success badge.
"Experimental" is a *visual* label, not an *architectural* boundary. If an LLM-authored
group is satisfied, a user sees "Likely match — The solution follows a X approach".

### P9 — Family membership and activation authority are conflated with label approval

The V2 POC already separates these (§5), and its post-review report identifies the
tension explicitly (`NEW-3`): six human-approved labels (`forward_pointer_advance` ×2,
`sequential_accumulation` ×4) are refused a GT group **only** because those concepts are
SUPPORT-tier. In the production path there is no notion of tier at all, so this
distinction cannot be expressed.

### P10 — Prior empirical conclusions are not enforceable

The strongest evidence for a redesign: the project already reached the correct
conclusion about `array_traversal` and could not act on it, because no layer in the
runtime can represent "evidence that is not a conclusion". Detailed in §6.2. Any future
detector-level fix faces the same fate: it will be measurable in an offline report and
unenforceable at the decision layer.

---

## 5. Evidence from the V1/V2 Ground-Truth experiments

The V2 corpus (12 problems × 8 solutions = 96, grouped into 37 families) with a real,
verified human review round is the best-controlled data the project has. Reading it as
architecture evidence (not as a POC scorecard):

**5.1 The vocabulary, not the grouping, is the bottleneck.** Post-review:
**14 of 37 families (38%) produce an activatable GT group; 23 do not.** Breakdown of the
23: **10** `LABEL_UNEXPRESSIBLE` (label term outside the frozen vocabulary),
**6** refused by the specificity floor (SUPPORT-only labels), **5** `ZERO_EVIDENCE`,
**1** `LABEL_PARTIAL`, **1** rejected. `activation_rate = 0.3889`. Only 2 of 12 problems
(LC 21, LC 3236) produce no group at all.

**5.2 Human label approval ≠ group activation.** The 6 floor-refused families are
*approved as correct* by the reviewer and describe the intended algorithm faithfully
(LC 21 forward-pointer merge; LC 3236 running prefix sum) — yet cannot activate a group,
because a group whose `required` is made only of low-specificity concepts cannot
distinguish its own family from anything else. This is `NEW-3`, and it is a **tier**
question that only the *matcher architecture* can answer.

**5.3 `UNKNOWN` vs `ABSENT` is not hypothetical.** `lc560_fam3` was labelled
`frequency_counting + sequential_accumulation` and explicitly noted by the reviewer as
"the same core algorithm as fam2". The analyzer observes **only**
`sequential_accumulation` in every member. V2 refuses a group rather than narrowing
(`narrowing_violations = 0`) — the correct behaviour — but the *only* available outcomes
are "group" or "no group". There is no `PROVISIONAL` outcome meaning "this family is
correct and half of it is visible". §10 supplies one.

**5.4 Registered-but-unobserved is a distinct failure mode.** `lc125_fam3`
(`two_pointers_opposite`, recursive) and `lc704_fam3` (`binary_search`, recursive): the
concept exists and is registered; the *observation form* (recursive rather than iterative)
is missing. V2 correctly refuses rather than forcing or narrowing. Two more
(`lc547_fam1` `bfs_shortest_path`, `lc125_fam3`) resolve to `LABEL_UNEXPRESSIBLE` despite
the term being registered — i.e. again an observation gap. **Both of these are
"NOT_ESTABLISHED because of observation form", not "ABSENT".**

**5.5 `ZERO_EVIDENCE` partitions by absence, not similarity.** `lc242_fam2` merged
`Counter(a) == Counter(b)` with `sorted(a) == sorted(b)` and was rejected by the reviewer
because coherence could not be established (`NEW-2`). V2's containment rule (never
labelled, never activated, never a control) is correct and should be preserved
unchanged. It also means the *family count understates distinct approaches*, which is a
measurement caveat, not a safety problem.

**5.6 `brute_force` has a measured 66.7% FP exposure under the obvious definition.**
12 families have `loop_shape = nested`; only **4** were human-labelled `brute_force`;
**8** were legitimate specific approaches (`bfs_shortest_path` ×2, `sequential_accumulation` ×2,
`iterative_insertion`, `two_pointers_opposite`, `sequential_accumulation + sliding_window`,
`union_find`). And the analyzer *already* over-fires generic concepts on this code:
`sliding_window` on a brute-force pairwise scan (`lc1_fam3`) and on a BFS (`lc547_fam1`) —
two human-adjudicated false positives. Adding a broad `brute_force` would compound one
generic over-claim with another on the same code.

**5.7 The grouping/derivation/control mechanics are sound and should not be touched.**
`discrimination_FP = 0.0` (0/1034 with `N_min = 5` satisfied for all 14 groups),
`group_satisfiability = 1.0` (14/14), `family_coverage = 1.0` (25/25 within scope),
`narrowing_violations = 0`, singleton rate `10.8%`, `families/problem ≤ 4`, D1 `7/7`,
D2 `32/32`. The POC's own PEC/SUPPORT tier concept is the right primitive; it simply lives
in an offline experiment instead of in the runtime.

**5.8 Authority semantics for `excluded` are unresolved and were accidentally changed.**
`NEW-1`: all 4 held-out `CONTRADICTED` cases came from problem-level exclusions firing on
*sibling* families. Removing them (because human labels carry no `excluded` set) took
`CONTRADICTED 4 → 0`. The post-review report is careful that this is *a consequence of the
label channel*, not evidence that exclusions are unnecessary. §9 addresses this directly.

---

## 6. Evidence from real production mismatches

### 6.1 Mismatch #1 — expected `greedy_local`, official `array_traversal`, experimental `candidate_selection`

Traced to four independent architecture facts, none of which is a `greedy_local` bug:

1. **The expected label cannot be produced by naming rules.**
   `GreedyLocalDetector._find_local_optimum_selection()` requires either a `max()`/`min()`
   call, or an assignment target whose *name* contains
   `best|max|min|optimum|optimal|profit|gain|max_val|min_val`, or an `AugAssign` to a
   name containing `max|min|best|profit`. `_find_immediate_decision()` also depends on
   names (`profit|price|val|curr|best|max|min`), and `_find_forward_progress()` on names
   (`i|j|k|idx|pos|index|left|right|l|r`). A correct greedy solution written with
   different identifiers emits no `greedy_local` evidence at all. (Notably this
   *contradicts* the vocabulary's own rule §1.1: *"A technique must NOT depend on
   variable naming."*)
2. **The generic detector fires unconditionally.** `array_traversal` needs only a `for`
   over a Name/`range`/`enumerate` plus *any* `Subscript` in the module.
3. **The coordinator ranks by confidence.** `array_traversal` sums four evidence weights
   and clamps to `1.0`, so it is frequently the max-confidence pattern → `primary_pattern`
   in `submissions`, and the top item in the UI.
4. **Neither matcher has an arbitration.** The official matcher compares
   `greedy_local` (from GT) against `{array_traversal, ...}` → no overlap → `NO_MATCH`
   (or `PARTIAL_MATCH` if some other expected pattern happened to overlap), and that
   becomes `unmatched_patterns` → a gap. Meanwhile the shadow matcher sees
   `candidate_selection` (T12, the V1 concept that `greedy_local` maps to via
   `PATTERN_TO_V1_MAPPING`) → group satisfied → `CONFIRMED` → "Likely match".

So the *same* submission receives a negative verdict on the authoritative surface and a
positive verdict on the experimental surface, for the *same* intended approach. The
architecture has no place to say "the specific technique `candidate_selection` is present,
so the generic `array_traversal` must not be reported as the primary approach".

### 6.2 Prior measurement already established the `array_traversal` conclusion

This is the decisive evidence for §25. From `reports and docs/`:

| Report | Finding |
|---|---|
| `SEMANTIC_EXPERIMENT_2B_HYBRID_REPORT.md` | *"The AST detector itself has 106 false positives on the full corpus for `array_traversal` … the AST detector is also too broad when applied outside its own test cases."* |
| `SEMANTIC_EXPERIMENT_2A_FULL_CORPUS_REPORT.md` | P = 0.243; *"`array_traversal` as a semantic concept is indistinguishable from 'any code that iterates a collection.'"* |
| `SEMANTIC_EXPERIMENT_2D_REAL_WORLD_REPORT.md` | *"`array_traversal`: **DISABLE/REWORK** — both AST and semantic are too noisy on cross-pattern code"*; 106 AST FPs vs 109 total. |
| `SEMANTIC_EXPERIMENT_3A_PRIMARY_ROLE_REPORT.md` | *"`array_traversal` ❌ FUNDAMENTALLY TOO BROAD … Classification: **KEEP AST-ONLY** — `array_traversal` should remain a structural-only concept"*; 183 FPs. |
| `SEMANTIC_EXPERIMENT_3B_COMPETITION_REPORT.md` | *"**Conclusion**: `array_traversal` should remain AST-only and be treated as a structural observation, not an algorithmic classification."*; `array_traversal_demotion` → *"✅ Correct"*. |
| `SEMANTIC_EXPERIMENT_3C_TAXONOMY_GENERALIZATION_REPORT.md` | *"188/301 cases trigger `array_traversal` detection (62%)"*; *"**`array_traversal` should NOT be a pattern label**"*; *"Demote `array_traversal` to structural primitive (not a scored pattern)"*. |

The conclusion has been reached six times with measurements and was **never applied**,
because there is no architectural mechanism by which "structural observation" differs
from "conclusion". A seventh detector patch will have the same fate.

### 6.3 Mismatch #2 — prefix-array / prefix-processing

Same shape, different vocabulary. `PATTERN_TO_V1_MAPPING["prefix_sum"] = {required:
["sequential_accumulation"], optional: ["iterative_table_filling"], excluded: []}`.
`sequential_accumulation` is **SUPPORT-tier** in V2 (`PEC_TECHNIQUES` excludes it), so a
prefix-sum family can never activate a V2 group on its own — this is exactly the LC 3236
outcome (`LABEL_GENERIC`, 7 members, `sequential_accumulation`, no group). Already
documented in-repo as a false-confirmation history
(`PREFIX_SUM_PRODUCTION_FALSE_CONFIRMATION_AUDIT.md`, `PREFIX_SUM_TAXONOMY_AUDIT.md`).
Architecturally: the *production* path has no tier concept at all, so it treats
`prefix_sum` as a first-class matchable label; the V2 path treats its V1 image as
insufficient. Two opposite policies for one concept, in one system.

---

## 7. Technique vs strategy distinction

### 7.1 What the code actually has today (answer to audit question A)

| Layer | What it contains | What it is *in practice* |
|---|---|---|
| `src/ast_detection/detectors/` | 36 detectors → `pattern_id` + `confidence` | a **mixture** of (a) approach-level patterns (`two_pointers_opposite`, `bfs_shortest_path`, `union_find`), (b) implementation variants (`sliding_window_fixed`/`_variable`, `dp_1d_forward`/`dp_1d_sequence`, `binary_search_standard`/`_rotated`/`_answer`), (c) generic structural observations (`array_traversal`, `sorting`, `prefix_sum`), (d) a policy concept (`brute_force`) |
| `pathforge/ast_engine/patterns.py` | 33 ids | the **problem/taxonomy** vocabulary (matches the curated CSV) |
| shadow `techniques.py` | T1–T14 | mostly **reusable methods** (`sequential_accumulation`, `hash_lookup`, `frequency_counting`, `candidate_selection`, `carry_propagation`) — but includes `recursive_branching`, which is recursion *evidence*, not a method |
| shadow `strategies.py` | S1–S9 | **approach-level** conclusions, of two internal kinds: those requiring a technique (`sliding_window` ← `loop_state_tracking`/`fixed_window_maintenance`; `dp_bottom_up` ← `iterative_table_filling`) and those built purely from facts (`binary_search` ← `midpoint_calculation`; `bfs_shortest_path` ← `queue_dequeue` + neighbour access; `union_find` ← `parent_pointer_chase` + `parent_root_merge`) |
| `gt_poc_v2/problem_metadata.py` | `PEC_STRATEGIES`, `PEC_TECHNIQUES`, `SUPPORT_TECHNIQUES` | the only **tier** model in the project (offline only) |

So: currently **"technique" = "detector" = "pattern_id"**, and the tier distinction exists
only in an experiment. That is the root of P1.

### 7.2 Proposed distinction

Adopt three explicit, *declared* classes (no renaming of runtime output required for
classes 1–3 to be useful; the classification is additive metadata):

**(1) Observation** — a deterministic, name-free, module-scoped structural property.
Never a conclusion. Examples: *has a loop over a collection*; *has indexed access within
a loop body*; *has a nested loop*; *has ≥2 recursive call sites*; *has a midpoint
assignment*; *has a queue dequeue*. These correspond to today's shadow **structural
facts** and to today's `array_traversal` / `brute_force` / `sorting`.

**(2) Technique** — a reusable *method*, composed of ≥2 observations, recurring across
multiple strategies, non-implying. This is exactly the vocabulary's own admission rule
(`PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md` §1.1) and it is what `T1–T14` already are.
Techniques are `conclusion_eligible = False` **as an approach**, but they are legitimate
run of family requirements (see §10 — a technique can be *identifying*).

**(3) Strategy** — an *approach-level* conclusion: at most one per submission may be
reported as the primary approach, and it requires (a) ≥1 technique or a defined set of
observations, plus (b) declared structural constraints, plus (c) an explicit exclusion set.
This is `S1–S9` plus the proposal's remedy for `greedy_local`-class labels, which
currently have no strategy representation at all (`greedy_local` maps to a *technique*,
`candidate_selection`, and never to a strategy).

**Recommendation (evidence-supported):** make the tier/class explicit and declared, and
make `array_traversal` / `brute_force` / `sorting` class (1) — `conclusion_eligible = False`.
This is exactly what `SEMANTIC_EXPERIMENT_3C` recommends; §11 gives it an enforceable form.

**Deliberately NOT proposed:** creating ~20 new strategy definitions to cover every label
in `PATTERN_TO_V1_MAPPING`. The V2 evidence (P5.1: 10 of 23 non-activating families are
vocabulary gaps; P5.4: 2 are *observation* gaps) does not justify bulk vocabulary growth
before the tier/precedence layer exists. Growth without a layer simply produces more
peers in the `ALL_PATTERNS`-style namespace.

---

## 8. Generic vs specific evidence model

### 8.1 The problem, stated precisely

"Generic" and "specific" are currently indistinguishable in the data model: both are a
`pattern_id` with a `float confidence`. So generic concepts compete with specific ones
under one numeric ordering (P5) and can occupy the *primary* slot (P6). The teacher's
examples of over-broad concepts map exactly onto concepts the code treats as peers:

| Concept | Where produced | Class today |
|---|---|---|
| `array_traversal` | `detectors/array_traversal.py` | detector pattern_id (peer) |
| `sequential_accumulation` | shadow T1 | technique (SUPPORT in V2) |
| `loop_state_tracking` | shadow T6 | technique (SUPPORT in V2) |
| `recursive_branching` | shadow T4 | technique (SUPPORT in V2) |
| `forward_pointer_advance` | shadow T11 | technique (SUPPORT in V2) |
| `candidate_selection` | shadow T12 | technique (SUPPORT in V2) |
| `brute_force` | `detectors/brute_force.py` | detector pattern_id (peer) |
| `loop_shape` / `nested` | shadow fact | structural fact |

### 8.2 Proposed model

Three declared attributes per concept, in one registry:

```
concept_id
class                  ∈ {OBSERVATION, TECHNIQUE, STRATEGY}
tier                   ∈ {PEC, SUPPORT}          # V2 vocabulary, adopted as-is
specificity_rank       ∈ {0,1,2,3}               # 0=observation, 1=SUPPORT, 2=PEC technique, 3=strategy
conclusion_eligible    bool                      # may it be the reported primary approach?
family_role            ∈ {IDENTIFYING, COMPONENT, SUPPORTING, ABSENT-NOT-ALLOWED}
falsifier              optional: a structural condition that positively proves absence
```

`specificity_rank` is **derived**, not hand-assigned, so it cannot drift:
`OBSERVATION→0`, `SUPPORT technique→1`, `PEC technique→2`, `STRATEGY→3`.
`conclusion_eligible = (class == STRATEGY)`.

The registry is the single place that answers "what is a technique?", "what may conclude?"
and "which concepts may partition GT families?" — replacing the implicit peer ordering.

**What it costs:** one new module and one new test asserting that *every* detector
`pattern_id`, every `ALL_PATTERNS` entry, and every shadow T/S id is classified (a
completeness gate, not a behaviour change). This is a metadata layer; it changes no
detector.

**Why tier alone is insufficient (and rank alone is insufficient):** tier answers *may this
partition a family?* (V2's question); rank answers *may this be the reported approach?*
(the teacher's question). `candidate_selection` is SUPPORT (rank 1, may not partition) yet
it is the *correct identifying technique* for a greedy family (it can be a required
component). Conversely `array_traversal` is rank 0: it may not partition **and** may not
conclude. Two axes are needed; V2 supplied one.

---

## 9. UNKNOWN vs ABSENT vs CONTRADICTED model

### 9.1 Semantics (three distinct states, never collapsed)

| State | Meaning | How it is established |
|---|---|---|
| `PRESENT` | the concept is established from current evidence | the concept's own detector produced admissible evidence above its declared floor |
| `NOT_ESTABLISHED` | the concept is **not established** from current evidence — this says nothing about absence | the detector produced nothing, or produced evidence below the floor, or the observation *form* is unsupported (e.g. recursive rather than iterative `binary_search`) |
| `CONTRADICTED` | the concept is **positively excluded** for this submission | a declared structural `falsifier` fires, OR a declared mutual-exclusion with a `PRESENT` concept holds |

**Rule K1 (the core correction).** *A detector's silence is never `CONTRADICTED`.* Silence
is `NOT_ESTABLISHED`. `CONTRADICTED` requires positive evidence of absence.

**Rule K2.** A sub-threshold detection is `NOT_ESTABLISHED`, **not** `ABSENT`. The
threshold must not be load-bearing for a hard negative. (Today
`matching._evaluate_single_group` uses `presence_confidence >= 0.5` for exactly that.)

**Rule K3.** `CONTRADICTED` is scoped: it is asserted *for the specific claim*, never
globally. "This submission is not a `dp_top_down`" is assertable; "there is no memoization
anywhere" is not.

**Rule K4 (authority).** No state may be `CONTRADICTED` from a `bootstrap` /
`llm_proposed` group's own exclusions unless the `falsifier` is structural. This preserves
V2's `NEW-1` lesson (problem-level exclusions firing across sibling families) and the
existing shadow rule that low-authority contradiction becomes `UNRESOLVED`.

### 9.2 Effect on family matching

Given a family with `required` components C₁…Cₙ (each mapped to a concept) and an explicit
`identifying` subset:

| Situation | Outcome | Rationale |
|---|---|---|
| all Cᵢ `PRESENT` | `CONFIRMED` | full coverage |
| any Cᵢ `CONTRADICTED` (rule K3/K4 satisfied) | `CONTRADICTED` | a specific, positive exclusion |
| all `PRESENT` except ≥1 `NOT_ESTABLISHED`; none `CONTRADICTED`; every `identifying` component `PRESENT` | **`PROVISIONAL`** (new) | the family's identity is established; a supporting component is merely unobserved — must not be reported as a failure |
| an `identifying` component `NOT_ESTABLISHED`; none `CONTRADICTED` | `UNRESOLVED` | we cannot tell whether this is the family |
| no family evaluable / no GT | `NO_GROUND_TRUTH` | unchanged from today |
| a group's `required` is empty | `UNMATCHABLE` | already correct in both matchers (`unmatchable`) |

`PROVISIONAL` is the direct answer to §10 and to `lc560_fam3`: *"the family is right and
half of it is visible"* becomes representable, instead of forcing a choice between a
false `CONFIRMED` and a false `CONTRADICTED`.

**Downstream policy for `PROVISIONAL` (recommended):** informative, non-scoring.
It may be shown (as "approach identified; not fully verified"), it must **not** update Elo,
gap signals or recommendations, and it must not be the load-bearing basis for a "your code
is wrong/correct" claim. This keeps "refusal is better than a confident wrong strategy"
while removing the *false negative*.

**Why not simply more thresholds?** Because the distinction is qualitative
(silence vs exclusion), not a tuning problem. §5.4's recursive-vs-iterative cases
(`lc125_fam3`, `lc704_fam3`) are `NOT_ESTABLISHED` for an *observation-form* reason; no
threshold separates them from `ABSENT`.

---

## 10. Compound strategy matching design

Worked example from the brief: expected family `hash_lookup + sliding_window`; strong
sliding-window evidence, weak/partial hash-map evidence.

**Today** (`matching._evaluate_single_group`): `required = [hash_lookup, sliding_window]`;
`hash_lookup` is either detected (`presence_confidence >= 0.5` → OK) or not
(`unsatisfied`, satisfaction 0.0) → the compound family is rejected outright. With
`excluded` present it is `contradicted`, i.e. a hard negative.

**Proposed semantics.** A family's requirement is a *set of components*, each with:

```
component: { concept, necessity ∈ {REQUIRED, SUPPORTING}, identifying: bool }
```

Matching (per §9.2):

1. Evaluate each component to `PRESENT` / `NOT_ESTABLISHED` / `CONTRADICTED`.
2. All `PRESENT` → `CONFIRMED`.
3. Any `CONTRADICTED` (rule K3/K4) → `CONTRADICTED`.
4. Otherwise, if every `identifying` component is `PRESENT` and the only gaps are
   `NOT_ESTABLISHED` `REQUIRED` components → **`PROVISIONAL`**, and **report the
   unestablished components by name** (`unestablished_components: ["hash_lookup"]`).
5. Otherwise (`identifying` component unestablished) → `UNRESOLVED`.

For the example: `hash_lookup` `NOT_ESTABLISHED` + `sliding_window` `PRESENT` (and
`sliding_window` declared `identifying`) → `PROVISIONAL`, not rejected. The user is told
*"sliding window identified; the hash-map component was not established from this code"* —
which is true, and is not a failure claim.

**Design requirements this imposes on Ground Truth** (all additive, no schema change yet):

- `identifying` must be declared per component. Derivation already has the information:
  the *first strategy* in a family's label is the family's identity in
  `ground_truth_builder.pattern_family()`. So `identifying` can default to "the strategy
  component(s)", with a human override.
- `optional` keeps its current meaning (boost only) and remains incapable of activating.
- `excluded` becomes a *falsifier set* subject to rules K1/K3/K4, not a presence-trigger.

**Never-narrow is preserved.** `PROVISIONAL` is not a narrowed `required`; `required` is
reported exactly as labelled (`narrowing_violations` must stay 0). The distinction is in
the *outcome*, not the requirement.

---

## 11. Specific-vs-generic precedence design

### 11.1 Why not "higher confidence always wins"

Confidence is evidence strength *for that detector*, computed by each detector's own
private weighting (`array_traversal`: 0.35+0.30+0.35+0.30, clamped to 1.0;
`bidirectional_index_scan`: flat 0.9; `binary_search` strategy: flat 0.85). Comparing
them numerically compares incomparable scales, and it is exactly how a loop observation
outranked `greedy_local` in §6.1. The V2 POC reached the same conclusion from the other
direction: it introduced tiers precisely because confidence could not express specificity.

### 11.2 Proposed rule

Let `C` be the set of concepts with an admissible observation, and define

```
precedence(c)   = (class(c) == STRATEGY, specificity_rank(c), confidence(c))
```

**Rule S1 (primary approach).** The reported primary approach is the maximum of
`C ∩ {c : conclusion_eligible(c)}` under `precedence`. If that set is empty, the verdict
is `UNRECOGNIZED` — an *explicit* state — and **no generic concept is promoted into the
primary slot**.

**Rule S2 (generic concepts never conclude).** `conclusion_eligible = (class == STRATEGY)`.
An `OBSERVATION` (rank 0) can never be the reported approach and can never satisfy
`identifying` for a family. This single rule makes `SEMANTIC_EXPERIMENT_3C`'s
recommendation ("demote `array_traversal` to structural primitive") *enforceable* rather
than advisory.

**Rule S3 (specific wins the slot, generic is retained as support).** A generic concept's
evidence is never discarded: it may appear in `supporting`, it may satisfy a `SUPPORTING`
component, and it remains visible in technical detail. Only the *primary slot* is
protected. This is what the brief asks for: *"array_traversal remains a low-level
structural observation but is not allowed to serve as the primary algorithmic conclusion
when more specific strategy evidence exists."*

**Rule S4 (contradiction outranks specificity).** Specificity never crosses an evidence
state. A `CONTRADICTED` specific strategy claim outranks a `PRESENT` generic observation;
a `PRESENT` generic observation can never override a `CONTRADICTED` specific claim.

**Rule S5 (tie-break determinism).** Within equal `precedence`, order by
`(PEC before SUPPORT, then concept_id lexicographic)`. No randomness, no insertion order,
no dict iteration order. This makes the whole pipeline byte-reproducible (a property the
V2 POC already establishes for its artifacts and that the brief requires:
*"deterministic runtime"*).

**Rule S6 (compound specificity).** A family whose `required` contains a rank-3 strategy
outranks a family whose `required` contains only rank ≤2 concepts when both are
candidates. This is a *family* ordering rule, structurally parallel to the existing
`STRATEGY_COMPATIBILITY` ordering already in `coherence.py`.

**Consequence for §6.1.** With `candidate_selection` (rank 1, `NOT_ESTABLISHED`-vs-`PRESENT`
aside) as the identifying technique of the greedy family and `array_traversal` demoted to
rank 0, the reported approach becomes the specific one, and `array_traversal` appears as
support rather than as the headline. Fixed without touching either detector.

**Consequence for §6.3.** `prefix_sum` becomes a rank-1/2 concept with an explicit
declared tier, so the *same* policy applies in both matchers — removing the current
situation where production treats it as matchable and V2 treats it as insufficient.

---

## 12. Zero-evidence handling design

### 12.1 Requirement

Separate roughly three situations without building a code-quality or verification system:

1. valid/meaningful code but an unfamiliar or unsupported approach;
2. obviously invalid / gibberish / broken submission;
3. recognizable approach.

Never treat "zero detected patterns" as proof of no approach.

### 12.2 Lightweight model (mechanical checks only)

A single deterministic pre-stage produces `code_state`, using only properties already
computable from the AST:

| `code_state` | Mechanical test (sufficient, not exhaustive) | Runtime meaning |
|---|---|---|
| `NOT_CODE` | `ast.parse` raises; or module has no statements | `SyntaxError` → existing 400 path; nothing else changes |
| `TRIVIAL` | parses, but contains no function/class body with ≥1 statement beyond `pass` / docstring / bare literal / `print`-only | cannot be an algorithmic approach; **must not** produce a gap or an Elo event |
| `VALID_UNRECOGNIZED` | parses, has a function with statements, contains at least one control-flow or return construct, and **no** `conclusion_eligible` concept is `PRESENT` | explicit state: *valid code, approach outside the current vocabulary* |
| `RECOGNIZED` | ≥1 `conclusion_eligible` concept `PRESENT` | normal path |

Everything else derives from the existing observation layer; no new analysis machinery.

**Policy mapping:**

- `TRIVIAL` → verdict `NO_APPROACH` (not `fail`); no gap; no Elo; UI says the submission
  does not contain an algorithm to analyse.
- `VALID_UNRECOGNIZED` → verdict `UNRECOGNIZED`; **no** `missing_patterns`; no gap; no Elo;
  optional (non-scoring) note that the approach is outside the recognised set. This is the
  state V2 §9 protects with its ZERO_EVIDENCE rules (never label, never activate, never
  control) — adopted unchanged, now expressible at runtime.
- `RECOGNIZED` → normal matching.

**Preserved from V2 (must not change):** a zero-evidence grouping is never labelled,
never activates a family, never acts as a negative control, and never counts as
confirmation. `lc242_fam2` proved this containment is doing real work.

**Explicitly out of scope:** any liveness/termination/numeric correctness proving, any
LLM judging of the submission, any attempt to decide whether an unfamiliar approach is
*correct*. The brief's constraint (`no giant code-quality subsystem`) and the project's
authority rules both forbid it.

---

## 13. Brute-force policy

### 13.1 Current state (must be stated accurately)

`brute_force` is **not** absent from the runtime. It exists as
`src/ast_detection/detectors/brute_force.py`:

- fires when `has_exhaustive_core = has_nested or has_branch`, where `has_nested` = any
  loop whose direct body contains a loop, and `has_branch` = ≥2 recursive call sites, or
  1 call site plus a loop;
- `_detect_range_enumeration` (+0.20) and `_detect_pair_checking` (+0.25) accumulate
  additional weight;
- `confidence = min(sum(weights), 1.0)`.

It is *not* in `ALL_PATTERNS`, and `POC_V2_POST_HUMAN_REVIEW_REPORT.md` correctly states it
is absent from `PEC_CONCEPTS`/`SUPPORT_CONCEPTS` and from
`pathforge/ast_analysis/shadow/`. Both statements are true and they describe different
layers. The teacher's concern applies to the live detector.

### 13.2 Measured danger

From §5.6 and §6.2, on this project's own data:

- "contains a nested loop" → **66.7% FP exposure** (8 of 12 nested-loop families are
  legitimate specific approaches);
- the analyzer already produces human-adjudicated generic false positives on this exact
  code (`sliding_window` on `lc1_fam3` and `lc547_fam1`);
- the same error family was already documented in `SEMANTIC_EXPERIMENT_1E/2A/2B`.

### 13.3 Recommendation

**Keep `brute_force` out of the conclusion class, and out of the GT activation class.**
Concretely:

- **GT:** remains a family-level *descriptive* label. Never registered in
  `PEC_CONCEPTS`; if ever registered, `SUPPORT` only — V2's `concept_tier()` default
  (unknown → SUPPORT) already makes this the safe default.
- **Runtime:** classify the existing `brute_force` as an `OBSERVATION`
  (`conclusion_eligible = False`, `specificity_rank = 0`), making it structurally
  subordinate to every specific strategy **by construction** rather than by convention.
  Do **not** delete the detector and do **not** retune it — both are detector-level
  changes and both would be re-litigated next quarter.
- **Precedence:** every specific strategy in §11.2 outranks it automatically (rank 3 > 0).
  A `brute_force` claim is therefore only ever visible when no specific conclusion exists.

### 13.4 Open policy question (needs a decision, §26)

Should the demoted `brute_force` observation remain *visible* in the user-facing
"detected patterns" list? Arguments: it is genuinely informative about the shape of the
code; it is also the most likely source of an unfair-sounding diagnosis. **Recommendation:**
visible only inside technical detail, never as a headline and never in gap text — but this
is a product-tone decision, not an architectural one, and the architecture supports either.
`POC_V2_POST_HUMAN_REVIEW_REPORT.md` §9.5 reached the same position
("keep it label-only for now") independently.

---

## 14. Recursive-branching policy

### 14.1 Current state

`recursive_branching` is a single SUPPORT-tier technique (T4) that fires on
`self_recursive_call` plus conditional branching / multiple call sites / nested
self-recursion. It excludes: linear recursion, mutual recursion. In the production
detector set, `dfs_recursive` + `brute_force._detect_recursive_branching` cover similar
ground with different logic.

### 14.2 Evidence that it is overloaded (from §5.4)

Five families across five different problems carry a *specific* recursive strategy label
while the analyzer observes only `recursive_branching`:

| family | problem | human label | analyzer |
|---|---|---|---|
| `lc21_fam4` | 21 | `recursive_merge` | `recursive_branching` |
| `lc102_fam2` | 102 | `recursive_dfs_by_depth` | `recursive_branching` |
| `lc125_fam3` | 125 | `two_pointers_opposite` (recursive) | `recursive_branching` |
| `lc547_fam2` | 547 | `recursive_dfs_traversal` | `recursive_branching` |
| `lc704_fam3` | 704 | `binary_search` (recursive) | `recursive_branching` |

Two of the five are **not vocabulary gaps at all** — the label term is registered; the
*observation form* is missing. This is `NOT_ESTABLISHED` for an observation-form reason
(§9.2), which is precisely the state the tri-state model makes representable.

### 14.3 Recommendation

**Do not add recursive vocabulary in this batch.** Adopt `recursive_branching` as an
`OBSERVATION` (`conclusion_eligible = False`, rank ≤1). Then design — but do not yet build —
a *recursion-shape* refinement as a **derived observation bundle**, not as new labels:

```
recursion_shape evidence (all name-free, from the existing fact extractor):
  call_sites                 : count / distinct argument shapes
  state_mutation             : add/append + remove/pop around the call  → backtracking family
  memo_table_access          : cache read + cache write                  → top-down DP family
  depth_or_level_parameter   : an argument that is incremented/decremented per call
  visited_marking            : a structure mutated before and visited-tested on entry
  bounded_range_halving      : a midpoint/range argument split per call
  single_call_site           : linear recursion (not branching)
```

This is justified by the brief's own bar (`≥2 independent occurrences across ≥2 problems`
plus a plausible general structural definition): the strong candidate is the recursion
refinement with **5 families / 5 problems**, which the post-review report already names as
the strongest expansion candidate. It remains **out of scope for this task** and is
recorded as a candidate in §21.

---

## 15. Experimental / LLM role

### 15.1 What the brief requires

One authoritative production decision; experimental analysis = hypothesis / suggestion
only; **no runtime LLM authority**; deterministic production.

### 15.2 Current reality (three distinct LLM touchpoints, one of which has authority)

1. **Ground-Truth authoring (offline, cached).** `ground_truth_builder.build_ground_truth()`
   calls `call_llm()` during `/prepare-problem`. The result is cached in
   `problem_ground_truth` and never regenerated (`AGENTS.md`: "Ground truth generation
   happens exactly once per problem"). Correct pattern; the *output* is `llm_proposed`.
2. **Shadow analysis (runtime, deterministic).** `run_shadow_analysis()` — no LLM. But its
   outcome is rendered to the user, and `CONFIRMED` is not authority-gated (§3.3, P8),
   so an `llm_proposed` group can display as "Likely match".
3. **Semantic shadow detector (runtime, observational).** `ShadowDetector.analyze_safe()`
   runs inside `/analyze` and is used only for the hybrid metadata block
   (`hybrid_analysis`). This one is architecturally correct: it cannot influence the
   verdict, and its failures are swallowed.

### 15.3 Proposed separation

| Channel | Authority | Visibility | Determinism |
|---|---|---|---|
| **Ground Truth** (offline, human-approved, versioned) | the *only* source of family expectations and exclusions | not user-facing | frozen per version |
| **Authoritative analysis** (deterministic; observations → techniques → strategies → coverage → match) | the only source of `verdict`, `verdict_type`, Elo, gaps, recommendations | primary result surface | byte-reproducible |
| **Hypothesis channel** (shadow + semantic + any future LLM signal) | none, ever | explicitly non-authoritative surface; no success styling; labelled as a hypothesis | may be non-deterministic, must not persist a "fact" |

Three enforceable rules:

- **A1.** A hypothesis can never write `verdict`, `verdict_type`, `elo`, `gap_signals`,
  or a recommendation. (Today this holds for the shadow *pipeline* because it is only
  persisted to the submission row — but the UI implication does not.)
- **A2.** `authority_tier` gates **all** outcome classes, including positive ones.
  `satisfied` on a non-authoritative group becomes `PROVISIONAL`
  (`analysis_only`), never `CONFIRMED`.
- **A3.** The user-facing label set derives from the authoritative decision only. The
  hypothesis surface gets hypothesis vocabulary ("unverified signal", "not used for your
  score") and must not use success styling. This removes the specific behaviour the
  teacher observed: an experimental "Likely match" contradicting an official "no match".

---

## 16. Proposed target architecture

The brief's suggested pipeline is close to correct. Two changes are made and justified
below: (i) an explicit **concept registry** between facts and conclusions, and (ii) an
explicit **coverage** layer between strategy inference and family matching, because
"how much of the expected family is established?" is a different question from "what does
this code look like?" and today no layer owns it.

```
SOURCE CODE
   ↓
L0  PARSE + SANITY                 deterministic; SyntaxError stays a 400
   ↓                               → code_state ∈ {NOT_CODE, TRIVIAL,
                                   VALID_UNRECOGNIZED, RECOGNIZED}
L1  STRUCTURAL FACTS               shadow fact_extractor + relations  (EXISTING, unchanged)
   ↓                               name-free, module-scoped, deterministic
L2  CONCEPT REGISTRY               NEW: class / tier / specificity_rank /
   (declarative)                   conclusion_eligible / family_role / falsifier
   ↓
L3  OBSERVATION + EVIDENCE         observations (rank 0) + techniques (rank 1–2)
   ↓                               each with a tri-state per concept
L4  STRATEGY INFERENCE             strategies (rank 3) = the only
   ↓                               conclusion-eligible layer
L5  COVERAGE PER EXPECTED FAMILY   NEW: PRESENT / NOT_ESTABLISHED / CONTRADICTED
   ↓                               per required component
L6  FAMILY MATCH                   CONFIRMED / PROVISIONAL / UNRESOLVED /
   ↓                               CONTRADICTED / UNMATCHABLE / NO_GROUND_TRUTH
L7  DECISION + AUTHORITY GATE      one authoritative verdict; authority_tier gates
   ↓                               every class
L8  USER-FACING RESULT             primary surface (authoritative)  ‖
                                   hypothesis surface (non-authoritative, separate)
```

**Why the registry (L2) is a layer and not a table of constants.** It is the only place
that can answer audit questions A/B/C/D/E consistently, and it is what makes Rules
S1–S6 *enforceable* rather than advisory. Constants spread across
`PATTERN_TO_V1_MAPPING`, `ALL_PATTERNS`, `coherence.STRATEGY_COMPATIBILITY`,
`problem_metadata` and 36 detector files cannot be ordered consistently.

**Why the coverage layer (L5) is a layer.** `lc560_fam3` (§5.3) is a coverage fact
("1 of 2 required components established; none contradicted"), not a strategy fact and not
a matching fact. Today it is computed inside the matching loop and thrown away
(satisfaction float), which is why `PROVISIONAL` is not expressible.

**What is deliberately NOT added:** no vector DB, no distributed components, no
service split, no schema rewrite, no new engine. `L1` already exists; `L3`'s technique
detectors already exist; `L4`'s strategies already exist; `L6` partially exists. The new
work is `L0` (mechanical), `L2` (metadata), `L5` (coverage record) and the three-valued
propagation through `L6`/`L7`.

### 16.1 Layer ownership (audit questions 1–12 answered concretely)

| # | Question | Answer |
|---|---|---|
| 1 | Who owns each decision? | L0 owns validity/triviality; L1 owns structural truth; L2 owns *permission* (may this concept conclude / partition / falsify); L3 owns per-concept state; L4 owns the primary approach; L5 owns the per-family component state; L6 owns the outcome class; L7 owns authority and the single verdict; L8 owns presentation only |
| 2 | What flows between layers? | L0→`code_state`; L1→facts+relations; L3→`{concept_id, state, evidence_refs, confidence}`; L4→`{strategy_id, supporting_concepts, confidence}`; L5→`{family_id, components:[{concept,state}], identifying_state}`; L6→`{outcome_class, unestablished[], contradicted[]}`; L7→`{verdict, verdict_type, authority_tier}` |
| 3 | Which concepts are merely evidence? | class `OBSERVATION` (rank 0): `array_traversal`, `sorting`, `brute_force`, all `structural_fact`s, `loop_shape`, `nested`, etc. |
| 4 | Which are strategies? | class `STRATEGY` (rank 3): `two_pointers_opposite`, `binary_search`, `sliding_window`, `dfs_backtracking`, `dp_top_down`, `dp_bottom_up`, `bfs_shortest_path`, `union_find`, `monotonic_stack_strategy` — the existing `PEC_STRATEGIES` set, adopted verbatim |
| 5 | Which may partition GT families? | `tier == PEC` (V2's existing rule, unchanged) |
| 6 | Which may activate a GT group? | `required` must contain ≥1 `concept ∈ PEC` **or** an explicitly reviewed low-specificity group (`NEW-3` decision) — the rule, not the exception, is unchanged from V2 |
| 7 | How do compound strategies work? | §10: components with `necessity` + `identifying`; outcome via §9.2, with `PROVISIONAL` |
| 8 | How is uncertainty represented? | the tri-state (§9) + `confidence` (evidence strength, only a tie-break in `precedence`) + `PROVISIONAL` (family-level uncertainty) |
| 9 | How does a specific strategy override generic evidence? | Rules S1–S6 (§11): the primary slot is restricted to `conclusion_eligible`; generic evidence is retained as support |
| 10 | How is one weak detector prevented from failing a correct strategy? | Rule K1/K2 (silence ≠ absence) + §9.2 (`PROVISIONAL` when only `NOT_ESTABLISHED` components remain and the identifying component is `PRESENT`) |
| 11 | How does experimental analysis stay non-authoritative? | §15.3 A1–A3: separate channel, separate vocabulary, authority gates all classes |
| 12 | How is the system deterministic? | L0–L7 use no LLM, no network, no clock-dependent ordering; Rule S5 fixes tie-break order; V2 already proves byte-identical artifacts on re-run |

---

## 17. Data flow

### 17.1 Authoritative submission flow (proposed)

```
POST /analyze
 ├─ resolve_problem()            → GT: families with required/optional/excluded/
 │                                   identifying/authority_tier (versioned, frozen)
 ├─ L0 parse + sanity            → code_state
 ├─ L1 facts + relations         → [StructuralFact], Relations
 ├─ L3 observations/techniques   → [(concept, state, evidence_refs, confidence)]
 ├─ L4 strategies                → [StrategyEvidence]
 ├─ L5 coverage                  → per family: components[] states
 ├─ L6 family match              → outcome_class per family
 ├─ L7 authority gate            → ONE verdict {outcome_class, verdict_type,
 │                                   authority_tier, unestablished[], contradicted[]}
 └─ persistence
      verdict_type = authoritative  →  Elo / gaps / recommendation ACTIVE
      verdict_type = analysis_only  →  submission row only (unchanged rule)
      ALWAYS                        →  streak (unchanged) + hypothesis-channel
                                       results persisted for diagnosis only
```

**Nothing in this flow is new infrastructure.** It replaces the two parallel matchers with
one pipeline that already exists in pieces.

### 17.2 What is *removed* from the decision path

- `matching_engine.MatchingEngine` as an independent authority (it survives, per §19, as a
  projection check during migration, then as the compatibility shim for problems whose GT
  is unexpressible).
- `shadow → "Likely match"` (the hypothesis surface loses success vocabulary).
- `argmax(confidence)` as the primary-approach rule, in both `persistence` and
  `shadow-mapper`.

### 17.3 Information that must be added to GT (additive, no schema rewrite)

| Field | Purpose | Default for existing rows |
|---|---|---|
| `identifying` per component | §10 compound semantics | "the strategy component(s)" — derivable from `pattern_family()` |
| `falsifier` per excluded concept | §9 Rule K3 | *absent* → exclusions cannot produce `CONTRADICTED` from mere presence (this is deliberately the conservative default and matches `NEW-1`'s observed behaviour) |
| `authority_tier` on the group | §18 gating of all classes | existing value |

---

## 18. Authority boundaries

| Layer / channel | May decide | May NOT decide |
|---|---|---|
| **Ground Truth** (§7 of the brief's framing) | which approaches are valid for a family; required/optional/excluded/identifying; authority tier; versions | anything about a *submission*; it may not read analyzer output to rewrite itself; may not be authored by the analyzer |
| **Observation layer (L1/L3)** | what structural evidence exists | any approach claim; any exclusion of a specific strategy |
| **Concept registry (L2)** | which concepts may conclude / partition / falsify | any per-submission judgement |
| **Strategy inference (L4)** | the primary approach, from existing evidence | absence claims; Elo; gaps |
| **Coverage/matching (L5/L6)** | the per-family outcome class, including `PROVISIONAL` | scoring; recommendations |
| **Decision (L7)** | the single authoritative verdict + `verdict_type` | re-deriving evidence; reading the hypothesis channel |
| **Hypothesis channel** | nothing authoritative: a recorded, non-scoring signal | `verdict`, `verdict_type`, `elo`, `gap_signals`, recommendations, and any user-facing success claim |
| **Elo / Gap / Recommendation engines** | unchanged — they consume the authoritative verdict exactly as today | being driven by `analysis_only` or `PROVISIONAL` outcomes |
| **Ground Truth authoring (offline LLM, cached)** | a *proposal* stored as `llm_proposed` | activating a group without the existing approval path |

**The two boundaries the brief calls out explicitly, and how they hold:**

- *Ground Truth must not silently rewrite analyzer facts.* Today the CSV reconciliation
  replaces `group["patterns"]` (the official matcher's expectation) while the docstring
  guarantees it will not touch `required/optional/excluded`. Under the proposal, the GT
  describes *families*, and the analyzer describes *submissions*; reconciliation (if kept)
  stays on the GT side and is recorded in `provenance`/`derivation_patterns` exactly as now.
- *Analyzer output must not author Ground Truth.* It does not today and must not: promotion
  (`llm_proposed → structurally_observed`) is documented but has **no implementing code**
  except the manual seed script. §21 records this as a policy item, not a defect.

---

## 19. Migration strategy from the current architecture

Additive, staged, flag-gated, each step independently measurable and reversible.

**Step 0 — Freeze and classify (no behaviour change).**
Create the concept registry (§16/L2) as *declarations only*, mapping every existing
`pattern_id`, `ALL_PATTERNS` entry and shadow T/S id to
`{class, tier, specificity_rank, conclusion_eligible, family_role}`. Add a completeness
test so an unclassified concept is a test failure, not a silent peer. **Nothing reads the
registry yet.** Deliverable: one module + one test + a report listing every concept's
class. This is where the audit questions get a permanent, checked answer.

**Step 1 — Tri-state observations on the shadow path only (no production change).**
Introduce `PRESENT`/`NOT_ESTABLISHED`/`CONTRADICTED` inside
`pathforge/ast_analysis/shadow/`, replacing the `presence_confidence >= 0.5` gate with an
explicit admissible-evidence floor and making `excluded` require a falsifier. Re-run the
V2 corpus read-only and compare: the acceptance criteria that must not move are
`discrimination_FP ≤ 0.05`, `narrowing_violations = 0`, `group_satisfiability = 1.0`.
Expected movement: held-out `UNRESOLVED`/`CONTRADICTED` redistribute.

**Step 2 — Coverage + `PROVISIONAL` (shadow only).**
Add the L5 coverage record and the `PROVISIONAL` outcome. Measure how many of the 27
held-out `UNRESOLVED` become `PROVISIONAL` (they should be exactly the compound
`NOT_ESTABLISHED` cases), and confirm `CONFIRMED` does not grow by a single case.

**Step 3 — Precedence + demotion (shadow + presentation).**
Activate Rules S1–S6 for the primary-approach selection; classify `array_traversal`,
`brute_force`, `sorting` as `OBSERVATION`. Measure the primary-pattern distribution before
and after. **No detector is edited.**

**Step 4 — Authority gating (shadow + hypothesis surface).**
Apply Rule A2 (positive outcomes on non-authoritative groups become `PROVISIONAL`) and A3
(hypothesis vocabulary, no success styling). This is where the observed
"Likely match vs official no-match" contradiction disappears.

**Step 5 — One authoritative path, flag-gated, per problem set.**
For problems with an activatable GT family, make the authoritative verdict the *projection*
of L7 instead of `MatchingEngine`. Keep `MatchingEngine` as: (a) an offline cross-check
that emits a disagreement report, then (b) the fallback for problems whose GT is
unexpressible (§5.1 — 23 of 37 families). Roll out problem-set by problem-set, never
big-bang. `verdict_type` semantics and the Elo/gap/recommendation engines are untouched.

**Step 6 — Retire only what is proven redundant.**
Delete `MatchingEngine`'s authority only when the disagreement report is clean on the
covered problem set *and* the fallback path is explicit. Anything not proven redundant stays.

**Rollback:** every step is behind a flag; each step's measurement is a report artifact;
steps 1–4 do not touch production behaviour at all, so the only risky step is 5.

---

## 20. What should remain unchanged

Explicitly and intentionally frozen by this proposal:

- **The AST detection engine's internals.** 36 detectors, `Parser`, `DetectorManager`,
  `Coordinator` aggregation, `OutputPipeline`. Their outputs stay available; only their
  *rank* changes (L2 metadata), never their code or thresholds.
- **The Elo engine**, `EVIDENCE_K_CEILINGS`, the `verdict_type` → `is_authoritative`
  gate, and `_AUTHORITATIVE_STATES`.
- **The Gap signal engine and the Recommendation engine** — inputs and ranking untouched.
- **The API contract** (`AnalyzeRequest`/`AnalyzeResponse`, `ProblemIdentifier`,
  `/prepare-problem`, `GroundTruthError` → 502, `ValueError` → 404,
  GraphQL-unavailable → 502, no-LLM-caching-on-failure, "GT exactly once per problem").
- **The database schema** for now (§17.3's fields are additive and can be JSON-embedded
  in the existing `solution_groups` column before any schema decision).
- **The V2 POC and its artifacts**, including its PEC/SUPPORT tier lists, its grouping,
  its derivation and its ZERO_EVIDENCE containment rules. The proposal *adopts* them.
- **Confidence semantics** (0.0–1.0 in the backend; frontend multiplies by 100) and the
  existing frontend display helpers.
- **The hybrid semantic observation block** (`hybrid_analysis`), which is already
  correctly non-authoritative.
- **`NO_GROUND_TRUTH`**, `unmatchable`-group reporting, and never-narrow.
- **All 33 `ALL_PATTERNS`** as the curated problem taxonomy.
- **Whatever `array_traversal` detection does**, for now: it must be *demoted*, not
  deleted or retuned (deleting it would lose the 183/301 cases where it is the only
  signal that the code iterates anything).
- **Whatever `brute_force` detection does** — same reasoning (§13.3).

---

## 21. What should eventually change

Ordered by evidence strength. None of these is authorised by this document.

1. **Primary-approach selection** stops being `argmax(confidence)` and becomes Rule S1
   (this is a *behaviour* change and belongs to Step 3/5).
2. **`array_traversal` / `sorting` / `brute_force` become observations** in the runtime
   decision path, per the project's own six prior conclusions (§6.2).
3. **`PROVISIONAL` becomes a first-class persisted outcome** (needs a decision on whether
   it is stored on the submission row, and how it appears in history).
4. **`excluded` semantics get decided** (`NEW-1`): per-family exclusions with structural
   falsifiers, not problem-level sets applied across siblings.
5. **`NEW-3` gets decided**: may a reviewed, low-specificity family ever activate a group,
   or is the specificity floor absolute? This changes what `solution_families` must store,
   so it precedes any GT schema work.
6. **`NEW-2` gets decided**: how a `ZERO_EVIDENCE` bucket with ≥2 members is represented.
7. **Recursion-shape refinement** (§14.3) as a later, separately-scoped vocabulary step —
   the strongest expansion candidate (5 families / 5 problems / 5 problems of evidence),
   but it is the *result* of the layer existing, not a prerequisite for it.
8. **Promotion policy** (`llm_proposed → structurally_observed`) is currently a manual
   seed script. If clustering is ever implemented, it must be gated by the recorded
   `AuthorityUpgradeRecord` transitions already in `shadow/authority.py`, with the
   self-reinforcement concern from `ARCHITECTURE_PREIMPLEMENTATION_AUDIT.md` addressed.
9. **Curated-vs-authoritative inversion** (§3.4): whether `human_curated` CSV GT should be
   authoritative. Evidence is currently insufficient to call this a defect — it may be
   deliberate. Flagged, not fixed.
10. **Retire the legacy flat-pattern matcher** for covered problem sets only (§19 Step 6).

---

## 22. Risks and tradeoffs

| Risk | Tradeoff / mitigation |
|---|---|
| **`PROVISIONAL` becomes a soft "yes"** and users read it as confirmation | Keep it non-scoring (no Elo, no gaps) and give it hypothesis-toned copy; measure `CONFIRMED` count before/after (must not grow) |
| **Demoting generic concepts hides real information** (e.g. a genuinely lazy solution) | Generic evidence stays visible in support/technical detail and stays usable as a `SUPPORTING` component; only the *primary slot* and *identifying* role are restricted |
| **A concept registry becomes a maintenance burden** and drifts from the 36 detector files | The completeness test (§19 Step 0) makes drift a test failure instead of a silent peer; the registry declares, it does not implement |
| **Two axes (tier, rank) invite confusion** | Rank is *derived* from class + tier, not hand-assigned — one input, one output |
| **The migration leaves two paths longer than comfortable** | Intentional: Step 5 is per-problem-set with a mandatory disagreement report; the fallback is required by §5.1 (23 of 37 families have no group) |
| **Reclassifying `brute_force` changes live user output** | It changes *rank*, not detection. Visible-behaviour change is confined to which pattern occupies the primary slot; that is measured, and it is reversible via the flag |
| **Tri-state without a falsifier makes `CONTRADICTED` rare** | Deliberate. `NEW-1` showed false contradictions are worse than missing ones; falsifiers can be added incrementally per concept |
| **Evidence base is one corpus (12 problems, 96 solutions) plus one teacher review** | This is the honest limit. The proposal therefore maps each claim to a measurable metric (§23) rather than asserting a general improvement; §24 lists what the corpus cannot decide |
| **`VALID_UNRECOGNIZED` becomes a place where real approaches hide** | Its purpose: stop calling it a *failure*. It is measured (count + examples), and it is the correct input for future vocabulary work rather than a false negative |
| **Touching the user-facing verdict at all** | Highest-risk item. Steps 1–4 touch nothing user-authoritative; Step 5 is flagged, per-problem-set, and backed by a disagreement report |

---

## 23. Minimal implementation phases

| Phase | Scope | Must not change | Measurable outcome |
|---|---|---|---|
| **B1 — Registry + classification audit** | concept registry module (declarations), completeness test, generated concept-classification report | any runtime behaviour, any detector, any threshold, GT, DB | 100% of `pattern_id`s, `ALL_PATTERNS` entries and T/S ids classified; 0 unclassified; report lists class/tier/rank per concept |
| **B2 — Tri-state in the shadow matcher** | replace the `< 0.5` gate with an admissible-evidence floor; `excluded` requires a falsifier | production path; V2 POC logic | V2 corpus re-run: `discrimination_FP ≤ 0.05`, `narrowing_violations = 0`, `group_satisfiability = 1.0`; held-out outcome distribution reported |
| **B3 — Coverage + `PROVISIONAL`** | coverage record; `PROVISIONAL` outcome class | `CONFIRMED` semantics; never-narrow; production | count of `PROVISIONAL` (expect the compound cases, e.g. `lc560_fam3`-shaped); `CONFIRMED` count unchanged (+0) |
| **B4 — Precedence + observation demotion** | Rules S1–S6; `array_traversal`/`sorting`/`brute_force` → `OBSERVATION` | detectors' code and thresholds | primary-approach distribution before/after; share of submissions whose primary pattern is rank 0 must go to 0 |
| **B5 — Authority gating + hypothesis surface** | Rule A2 (positive outcomes on low-authority groups → `PROVISIONAL`), Rule A3 (hypothesis vocabulary/styling) | Elo/gap/recommendation engines; `_AUTHORITATIVE_STATES` | count of user-visible experimental "Likely match" claims that contradict the official verdict → 0 |
| **B6 — One authoritative path (flagged, per problem set)** | verdict becomes the L7 projection for covered problems | API contract; GT semantics; schema | official-vs-new disagreement report on real submissions (`shadow_realworld_data.json` + live traffic); per-problem-set sign-off |

**Explicitly not in any phase:** implementing `brute_force`, implementing recursion
refinement, changing any threshold, patching any detector, GT schema changes, runtime LLM.

---

## 24. Questions that genuinely remain unresolved

Stated with the evidence that is missing, per the "no premature certainty" constraint.

1. **Must the two matchers converge, or only the two *decisions*?**
   - *Alternative A:* one pipeline (this proposal). *Alternative B:* keep two evidence
     producers but reconcile their verdicts in a thin arbitration layer.
   - *Evidence:* the two matchers produce structurally compatible, not incompatible,
     evidence — the shadow path already has facts that subsume the legacy detector
     signals, but the legacy path has 36 detectors tuned against a real corpus
     (`pathforge.db` submissions snapshot, `adversarial_evaluation_results.json`,
     `large_corpus_results.json`) while the shadow path's corpus evidence is thinner.
   - *Tradeoff:* A is cleaner; B preserves the tuned detector corpus as an independent
     second opinion.
   - **Recommendation (moderate confidence):** A, because B leaves "which matcher is
     authoritative" as a permanent open question, which is the current failure. But the
     disagreement-report step (B6) should decide it *empirically* rather than by
     preference.

2. **Is `PROVISIONAL` a real outcome for the user, or an internal state?**
   *Missing evidence:* no user study, and no data on how often it would occur in practice
   (the V2 corpus is 96 solutions). Recommendation: internal + non-scoring in B3, then
   decide visibility from measured frequency.

3. **Should generic concepts ever be the reported approach when nothing specific exists?**
   This is the `array_traversal` question in its purest form. *Evidence:* the project's six
   reports say no (keep it structural); the fused corpus (`fusion_eval_data.json`) also
   treats it as a scorable pattern with expected=true cases — i.e. two of the project's own
   artifacts disagree about whether it is a *target* at all. Recommendation: no for the
   *conclusion*, yes as retained evidence; the tension itself is the open question.

4. **Does `human_curated` CSV GT deserve authority?** (§3.4) Currently it is treated as
   *less* authoritative than a seeded row. *Evidence:* `ARCHITECTURE_FINAL_RECONCILIATION.md`
   says the opposite of `persistence._AUTHORITATIVE_STATES`. Unresolved, and it is a policy
   question.

5. **What is the minimum corpus/coverage before the authoritative path may be trusted for
   scrolling user traffic?** V2's `OPEN-12` (minimum corpus before *promotion*) and
   `OPEN-4` (`activation_rate` floor) are both open, and `OPEN-3` (blinding in practice)
   is only partially provable from artifacts.
6. **`NEW-1`, `NEW-2`, `NEW-3`** — all three require a human decision (§24.7) and all three
   change what GT must store. They must be settled before any GT schema work.
7. **Which of the 6 floor-refused families may activate, and under what separation
   requirement?** (`NEW-3`) This is a taxonomy/human question, not derivable from the code.

---

## 25. Why this is better than detector-by-detector patching

**Because this project has already run that experiment, taken the measurements, and
reached the correct conclusion six times — and the conclusion was never applied.**

The `array_traversal` history is the proof:

1. `docs/phase3C_batch1..4_report.md` and `phase3C_validation_report.md` — the detector was
   *added, then extended* (element-usage detection, `enumerate` support, "+11 TP").
2. `SEMANTIC_EXPERIMENT_1B/1C/1D/1E_REPORT.md` — for-loop recognition, direct-iteration
   credit, weight tuning; F1 moved `0.60 → 0.65`; precision `0.79`; 25 FNs remain.
3. `SEMANTIC_EXPERIMENT_2A_FULL_CORPUS_REPORT.md` — **P = 0.243, 112 false positives**,
   *"indistinguishable from any code that iterates a collection"*,
   **"Verdict: REJECT"**.
4. `SEMANTIC_EXPERIMENT_2B_HYBRID_REPORT.md` — *"the AST detector itself has 106 false
   positives … the AST detector is also too broad when applied outside its own test cases"*.
5. `SEMANTIC_EXPERIMENT_2D_REAL_WORLD_REPORT.md` — *"DISABLE/REWORK"*.
6. `SEMANTIC_EXPERIMENT_3A/3B/3C_REPORT.md` — *"FUNDAMENTALLY TOO BROAD"*, **62% of cases**,
   precision **11–13%**, *"should NOT be a pattern label"*, *"Demote `array_traversal` to
   structural primitive (not a scored pattern)"*, and — importantly —
   **`array_traversal demotion ✅ Correct / ✅ Helps / Robust`**.

Six rounds of detector work produced a *correct recommendation* that is **not executable**.
The reason is architectural, and it is the same reason the teacher's concerns cannot be
satisfied by detector work:

- **There is nowhere to put "this evidence is not a conclusion."** Every concept is a peer
  with a float. So a detector that is correct-but-generic is indistinguishable from one
  that is specific, and specificity becomes a numeric comparison that the generic detector
  wins by accumulating weights.
- **There is nowhere to put "not established".** The official matcher's universe is
  `detected ⊆ expected`. So any detector fix must make every expected pattern certain,
  which is why the fixes above oscillate between false positives and false negatives rather
  than converging. Adding a 37th detector *adds a peer*, increasing the number of ways a
  correct specific strategy can be outranked or falsely contradicted.
- **There is nowhere to arbitrate between two matchers**, so a detector-level improvement
  in one path is invisible or contradictory in the other. Patching `greedy_local` would
  improve the official path and leave the shadow path's `candidate_selection` disagreement
  untouched — and vice versa.
- **The teacher's four requirements are layer requirements, not detector requirements:**
  "not detected ≠ absent" is a state model; "zero evidence needs interpretation" is a
  pre-stage; "broad labels must not overpower specific strategies" is a precedence lattice;
  "final precedence is our architecture decision" is a registry. None of them can be
  expressed by editing a detector, and each detector edit made without them will need to be
  revisited when the layer arrives.
- **Patching produces local fixes with global regressions.** `array_traversal`'s own
  history is a false-positive/false-negative oscillation under a fixed decision rule. The
  proposals in §10–§12 change the *rule*, which is why they can be evaluated once and
  measured against stable gates (`discrimination_FP`, `narrowing_violations`,
  `CONFIRMED`-must-not-grow) instead of against per-detector precision that moves every
  time a different detector's threshold shifts.

In one sentence: **detector patching cannot express the difference between "we did not see
it" and "it is not there", and that distinction is the whole problem.** Every patch that
skips the layer will be another iteration of the same loop, and this repository already
contains six iterations of it.

---

## 26. Final answers (A–E)

### A. Recommended target architecture

A **single authoritative, deterministic pipeline** (§16), layered as

`L0 sanity/sanity-state → L1 structural facts → L2 declarative concept registry →
L3 tri-state observations/techniques → L4 strategy inference (the only conclusion-eligible
layer) → L5 per-family coverage → L6 family match (with a new `PROVISIONAL` class) →
L7 authority-gated single verdict → L8 authoritative vs hypothesis presentation`,

with the existing `Elo`/`Gap`/`Recommendation` engines and the API contract unchanged, and
the Ground-Truth family expectations (V2 PEC/SUPPORT tiers, never-narrow, ZERO_EVIDENCE
containment) adopted verbatim.

Four enforcements carry the architectural weight:

- **K1/K2** — silence is `NOT_ESTABLISHED`, never `CONTRADICTED`; sub-threshold is not absent.
- **S1–S6** — the primary approach is chosen by (class → specificity_rank → confidence),
  never by confidence alone; `conclusion_eligible = (class == STRATEGY)`.
- **`PROVISIONAL`** — a family with an established identifying component and only
  `NOT_ESTABLISHED` supporting components is neither confirmed nor rejected.
- **A1–A3** — the hypothesis channel (shadow, semantic, any LLM signal) can never write a
  verdict, and non-authoritative groups can never produce a user-visible success claim.

### B. What should NOT be changed

Everything in §20, and summarised: the AST engine and its 36 detectors; all thresholds; the
Elo, Gap and Recommendation engines; `verdict_type`/`is_authoritative` and
`_AUTHORITATIVE_STATES`; the Elo/gap/recommendation suppression for `analysis_only`; the API
contracts and error-code mapping; the database schema (for now); the V2 POC, its PEC/SUPPORT
lists, its grouping/derivation/control rules and its ZERO_EVIDENCE containment; the
`NO_GROUND_TRUTH` and `unmatchable` behaviours; never-narrow; the 33-pattern
`ALL_PATTERNS` taxonomy; and — explicitly — the *existence* of `array_traversal` and
`brute_force` detection, which must be demoted, not deleted or re-tuned.

### C. First implementation batch after architecture approval

**B1 — Concept registry + classification audit** (declarations only, zero behaviour
change): one module declaring `{class, tier, specificity_rank, conclusion_eligible,
family_role, falsifier?}` for every `pattern_id`, `ALL_PATTERNS` entry and shadow T/S id;
one completeness test; one generated report. No detector, matcher, threshold, GT, DB or
production file is modified.

Followed immediately by **B2 — tri-state in the shadow matcher only** (still no production
behaviour change).

### D. What must be measured after that batch

1. **Completeness:** 0 unclassified concepts (hard gate).
2. **V2 regression gates (must not move):** `discrimination_FP ≤ 0.05`,
   `narrowing_violations = 0`, `group_satisfiability = 1.0`, singleton rate ≤ 0.25,
   D1/D2 correct.
3. **Outcome redistribution (expected to move):** held-out `CONFIRMED` / `PROVISIONAL` /
   `UNRESOLVED` / `CONTRADICTED` counts. `CONFIRMED` must **not increase** in B2/B3.
4. **Compound cases:** `lc560_fam3`-shaped families become `PROVISIONAL`
   (from "no group"); the 6 SUPPORT-floor families are enumerated with their
   `PROVISIONAL`-eligibility.
5. **Primary-approach distribution (after B4):** share of primary patterns that are
   rank 0 (`array_traversal`, `sorting`, `brute_force`) must reach **0**.
6. **Official-vs-new disagreement rate (after B6 groundwork):** on
   `shadow_realworld_data.json` plus live traffic, the fraction of submissions where the
   two paths disagree, and the direction of disagreement, per problem.
7. **Hypothesis-leak count (after B5):** number of user-visible non-authoritative success
   claims → **0**.
8. **Zero-evidence split:** submissions classified `TRIVIAL` / `VALID_UNRECOGNIZED` /
   `RECOGNIZED`, with the `VALID_UNRECOGNIZED` examples retained as the vocabulary-work
   backlog.

### E. Which decisions still require human input

1. **`NEW-3` / `OPEN-2` (highest priority)** — may a human-approved, low-specificity family
   (`forward_pointer_advance` ×2, `sequential_accumulation` ×4) ever activate, and under
   what separation requirement? This determines what GT must store.
2. **`NEW-1`** — per-family `excluded` semantics, and whether exclusions require structural
   falsifiers (recommended) or may fire on mere presence.
3. **`OPEN-8`** — ratification of the five profile dimensions used for grouping.
4. **`NEW-2`** — how a `ZERO_EVIDENCE` bucket with ≥2 members is represented.
5. **Authority policy inversion** (§3.4) — should `human_curated` CSV GT be authoritative?
6. **`brute_force` visibility** (§13.4) — user-visible observation, technical-detail only, or
   not shown at all.
7. **`PROVISIONAL` visibility** (§24.2) — internal state only, or a user-facing outcome.
8. **`OPEN-4`/`OPEN-12`** — the `activation_rate` floor and the minimum corpus before the
   authoritative path may carry real traffic without a per-problem-set review.

---

*Prepared as an architecture audit and redesign proposal. No production behaviour,
detector, technique, strategy, vocabulary, threshold, matcher, Ground-Truth row, database
schema or V2 POC behaviour was changed in preparing this document.*
