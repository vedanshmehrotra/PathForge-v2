# Phase Vertical Slice Audit

**Date:** August 22, 2026
**Audit target:** Vertical-slice implementation (shadow analysis path)
**Reference documents:**
- `PATHFORGE_ANALYSIS_ARCHITECTURE_V1.md` (frozen architecture)
- `PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md` (technique/strategy vocabulary)
- `PATHFORGE_ARCHITECTURE_FEASIBILITY_AUDIT.md` (feasibility baseline)

---

## 1. Structural Facts Are Canonical

**Check:** Are structural facts the canonical output of the new analysis layer?

**Evidence:**
- `fact_extractor.py` produces `StructuralFact` objects as the first step in the pipeline.
- `techniques.py` consumes facts and produces `TechniqueEvidence` (derived).
- `strategies.py` consumes techniques and facts and produces `StrategyEvidence` (derived).
- `matching.py` consumes all three and produces `MatchOutcome` (derived).
- `shadow_runner.py` orchestrates: facts → techniques → strategies → match.
- `data_structures.py` docstrings explicitly state: "Canonical persisted artifact. Higher-level labels are derived from these."

**Verdict:** ✅ **CORRECT.** Facts are canonical; everything else is a derived projection.

**Deviation:** None.

---

## 2. Techniques and Strategies Are Derived Projections

**Check:** Are techniques and strategies derived projections, not canonical truth?

**Evidence:**
- `TechniqueEvidence` has `supporting_fact_ids` referencing facts.
- `StrategyEvidence` has `supporting_technique_ids` and `supporting_fact_ids`.
- `MatchOutcome` stores the full chain: facts → techniques → strategies.
- The data structures docstrings explicitly state "Derived evidence for a reusable computational technique" and "Derived evidence for a higher-level algorithmic strategy."

**Verdict:** ✅ **CORRECT.** The derivation chain is explicit and traceable.

**Deviation:** None.

---

## 3. Presence Confidence and Centrality Remain Separate

**Check:** Are presence_confidence and centrality deliberately separate values?

**Evidence:**
- `TechniqueEvidence` has both `presence_confidence` and `centrality` as separate float fields.
- Each technique detector sets them independently:
  - `sequential_accumulation`: presence=0.85, centrality=0.6
  - `bidirectional_index_scan`: presence=0.9, centrality=0.85
  - `carry_propagation`: presence=0.9, centrality=0.8
- `shadow_runner.py` serializes them as separate fields in `_tech_to_dict`.
- The architecture spec (§5.3) requires: "These are deliberately separate. They must not be prematurely collapsed into one scalar."

**Verdict:** ✅ **CORRECT.** The two values are never collapsed.

**Deviation:** None.

---

## 4. No Technique/Strategy Logic Leaked into Fact Extractor

**Check:** Does the structural fact extractor contain any technique or strategy logic?

**Evidence:**
- `fact_extractor.py` imports only `StructuralFact` and `EXTRACTOR_VERSION` from data structures.
- It does NOT import `TechniqueEvidence`, `StrategyEvidence`, or any technique/strategy IDs.
- Detection methods are named `_detect_*` and describe structural patterns:
  - `_detect_while_comparison` — while-loop with comparison
  - `_detect_opposite_updates_in_loop` — two variables with opposite augmented assignments
  - `_detect_linked_traversal_in_loop` — `.next`/`.left`/`.right` access
  - `_detect_carry_in_loop` — carry-like variable updated in loop with linked traversal
- No method references `two_pointers_opposite`, `binary_search`, `linked_list_reversal`, or any technique/strategy name.

**Verdict:** ✅ **CORRECT.** The fact extractor is purely structural.

**Deviation:** None.

---

## 5. No Variable-Name Dependence Introduced

**Check:** Does the implementation depend on specific variable names?

**Evidence:**
- `CARRY_LIKE_NAMES` is a heuristic set, not a hard requirement. The carry detection checks: "is there a variable with a carry-like name updated in a loop with linked traversal?" If the variable is named `c` instead of `carry`, it still fires (verified by `test_renamed_carry_propagation`).
- `LINKED_ATTRS = {"next", "left", "right"}` — these are structural attributes, not variable names. The detection looks for `.next` access on ANY receiver variable.
- `NODE_CONSTRUCTOR_PREFIXES = ("node", "listnode", "treenode", "btnode")` — these are function name patterns, not variable names.
- `test_renamed_two_pointers` verifies that `a`/`b` instead of `left`/`right` still triggers `bidirectional_index_scan`.
- `test_renamed_carry_propagation` verifies that `la`/`lb`/`c`/`v`/`d` instead of `l1`/`l2`/`carry`/`val`/`digit` still triggers `carry_propagation`.

**Verdict:** ⚠️ **MOSTLY CORRECT.** The carry detection uses a name heuristic, but:
- It is documented as a heuristic, not a hard requirement.
- It works with alternative names (verified by tests).
- The architecture spec (§4.4) allows "limited, intraprocedural type inference" — the name heuristic is a lighter-weight version of this.

**Deviation:** The carry detection heuristic could miss a variable named `x` that carries state. This is a known limitation, not a violation. The architecture allows it.

**Technical debt:** The `CARRY_LIKE_NAMES` set is opinionated. A future improvement could use data-flow analysis to detect self-referential updates without name heuristics.

---

## 6. Add Two Numbers Cannot Be Classified as linked_list_reversal

**Check:** Can the old `linked_list_reversal` label force a false contradiction?

**Evidence:**
- The fact extractor detects `linked_structure_traversal` for `.next` access — this is the same fact that the old `linked_list_reversal` detector would partially match on.
- However, the technique layer does NOT have a `linked_list_reversal` technique. The only technique that fires is `carry_propagation`.
- The strategy layer does NOT have a `linked_list_reversal` strategy.
- `test_add_two_numbers_shadow` explicitly verifies:
  - `carry_propagation` is detected ✅
  - `two_pointers_opposite` is NOT detected ✅
  - Outcome is `UNRESOLVED` ✅
- The old flat-pattern detector (`linked_list_reversal.py`) requires `pointer_rewiring` (e.g., `node.next = prev`) which is NOT present in Add Two Numbers (the code has `curr.next = ListNode(digit)` — construction, not rewiring). So the old system ALSO doesn't fire `linked_list_reversal` on this code. But the new system is architecturally immune to this class of error regardless.

**Verdict:** ✅ **CORRECT.** The new system cannot produce `linked_list_reversal` because:
1. The fact extractor emits structural observations, not pattern labels.
2. The technique vocabulary does not include `linked_list_reversal`.
3. The matching engine uses solution-group satisfaction, not pattern-ID equality.

**Deviation:** None.

---

## 7. 2996 Cannot Classify List Membership as Hash-Map Behavior

**Check:** Does `summ in nums` produce hash-map classification?

**Evidence:**
- The fact extractor does NOT have a `membership_check` fact type in its vocabulary. The `in` operator is not detected as a structural fact by the current implementation.
- Even if it were, the technique vocabulary does NOT include `hash_map_lookup` or `frequency_counting`.
- `test_membership_in_loop` explicitly verifies:
  - `hash_map_lookup` is NOT in detected techniques ✅
  - `frequency_counting` is NOT in detected techniques ✅
  - `sequential_accumulation` IS detected ✅
- The architecture spec (§4.2) explicitly prohibits `hash_map_lookup` as a fact-layer label.

**Verdict:** ✅ **CORRECT.** List membership remains a structural observation (or is not observed at all) — it never becomes a hash-map technique or strategy.

**Deviation:** None.

---

## 8. UNRESOLVED Is Genuinely Non-Punitive

**Check:** Does UNRESOLVED trigger ELO, gaps, or recommendations?

**Evidence:**
- The shadow analysis is observational only. It returns results in the `shadow_analysis` field of the API response.
- The main production pipeline (`run_analysis` → `run_persistence`) is completely independent of the shadow analysis.
- The shadow analysis does NOT call `run_persistence`, `EloEngine`, `GapSignalEngine`, or `get_recommendation`.
- The `MatchOutcome.outcome` value is never used to set `verdict`, `verdict_type`, or any downstream signal.
- `test_problem_2996_shadow` verifies UNRESOLVED outcome.

**Verdict:** ✅ **CORRECT.** UNRESOLVED is non-punitive because:
1. The shadow path has no write path to the database.
2. The shadow path has no influence on the production analysis pipeline.
3. The `MatchOutcome` is serialized and returned but not consumed by any downstream system.

**Deviation:** None.

---

## 9. Low-Authority CONTRADICTED Is Downgraded to UNRESOLVED

**Check:** Does the authority gate correctly downgrade bootstrap/llm_proposed contradictions?

**Evidence:**
- `matching.py` defines `_AUTHORITATIVE_TIERS = {"structurally_observed", "externally_listed", "editorial"}`.
- In `evaluate_solution_groups`, when `group_outcome == "contradicted"`:
  - If `group_authority in _AUTHORITATIVE_TIERS` → `group_final = "CONTRADICTED"`
  - Else → `group_final = "UNRESOLVED"` with reasoning logged.
- `test_bootstrap_contradiction_becomes_unresolved` verifies:
  - Group requires `carry_propagation` (not detected for palindrome) + excludes `bidirectional_index_scan` (detected)
  - Authority is `llm_proposed`
  - Outcome is `UNRESOLVED` ✅
- `test_authoritative_contradiction_stays_contradicted` verifies:
  - Same group structure but authority is `structurally_observed`
  - Outcome is `CONTRADICTED` ✅

**Verdict:** ✅ **CORRECT.** The authority gate works as specified.

**Deviation:** None.

---

## 10. Shadow Path Cannot Modify Production Systems

**Check:** Does the shadow path modify verdict, verdict_type, ELO, topic profiles, gaps, or recommendations?

**Evidence:**
- The shadow analysis call in `analyze.py` is:
  ```python
  shadow_result = None
  try:
      from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
      shadow_raw = run_shadow_analysis(req.code, solution_groups=groups)
      if shadow_raw:
          shadow_result = ShadowAnalysisResult(**shadow_raw)
  except Exception:
      pass
  ```
- This runs AFTER `run_persistence()` has already committed the production analysis.
- The shadow result is only assigned to `shadow_result`, which is passed as `shadow_analysis=shadow_result` in the response.
- The shadow runner (`shadow_runner.py`) does NOT:
  - Call `run_persistence()`
  - Call `EloEngine`
  - Call `GapSignalEngine`
  - Call `get_recommendation()`
  - Modify any database tables
  - Set `verdict` or `verdict_type`
- The shadow runner is wrapped in `try/except` — if it fails, `shadow_result` stays `None` and production continues normally.

**Verdict:** ✅ **CORRECT.** The shadow path is strictly observational.

**Deviation:** None.

---

## 11. Stored Evidence Is Versioned for Future Re-Derivation

**Check:** Is version information preserved for technique and strategy definitions?

**Evidence:**
- `StructuralFact.extractor_version = "1.0.0"` — tracks which extractor version produced the facts.
- `TechniqueEvidence.technique_version = "1.0.0"` — tracks which technique definition version was used.
- `StrategyEvidence.strategy_version = "1.0.0"` — tracks which strategy definition version was used.
- `shadow_runner.py` includes `"extractor_version": EXTRACTOR_VERSION` in the output dict.
- The architecture spec (§12) requires: "Introduce a new version when semantics change" and "Re-derive higher-level evidence from persisted facts when needed."

**Verdict:** ✅ **CORRECT.** Version information is preserved at all three layers.

**Deviation:** The version numbers are currently hardcoded to `"1.0.0"`. A future improvement should make them configurable or increment them when definitions change.

**Technical debt:** Version numbers are static. No migration or re-derivation mechanism exists yet — this is deferred per architecture §12.5.

---

## 12. Legacy Flat-Pattern Behavior Remains Intact

**Check:** Does the existing AST detector system continue to work unchanged?

**Evidence:**
- All 551 existing tests pass (verified by running `pytest src/ast_detection/tests/ pathforge/ast_engine/tests/`).
- The shadow analysis is a separate code path in `pathforge/ast_analysis/shadow/`.
- The existing detector system (`src/ast_detection/`) is not imported by or modified by the shadow code.
- The `run_analysis()` function in `pathforge/api/services/analysis.py` is unchanged.
- The `MatchingEngine` in `src/matching_engine/matching_engine.py` is unchanged.
- The `AnalyzeResponse` now has an additional optional field `shadow_analysis` — this is backward-compatible (the field is `Optional`).

**Verdict:** ✅ **CORRECT.** Legacy behavior is fully intact.

**Deviation:** None.

---

## 13. No Problem-Specific Logic Introduced

**Check:** Does the implementation contain hard-coded logic for specific problems?

**Evidence:**
- The fact extractor uses generic AST patterns:
  - While loops with comparisons
  - Augmented assignments
  - Linked structure attributes (`.next`, `.left`, `.right`)
  - Node constructors (`ListNode`, `Node`, etc.)
- The technique detectors use generic fact combinations:
  - `sequential_accumulation`: loop + accumulator + modified variable
  - `bidirectional_index_scan`: loop comparison + opposite updates
  - `carry_propagation`: linked traversal + carry variable
- The strategy evaluator uses generic technique requirements:
  - `two_pointers_opposite`: bidirectional_index_scan + while comparison + opposite updates + no midpoint
- No hard-coded problem names, LeetCode IDs, or specific algorithm implementations.
- `test_complex_code_no_crash` verifies that complex code with graph traversal, recursion, and defaultdict doesn't crash the system.

**Verdict:** ✅ **CORRECT.** No problem-specific logic.

**Deviation:** None.

---

## 14. Architectural Deviations, Hidden Coupling, and Technical Debt

### 14.1 Architectural Deviations

| Deviation | Severity | Description |
|---|---|---|
| **Midpoint detection gap** | Medium | The `two_pointers_opposite` strategy uses an absence constraint (`has_midpoint = any(f.fact_type == "midpoint_calculation" for f in facts)`), but `midpoint_calculation` is not a fact type the extractor produces. This means the absence check always passes, and binary search would be misclassified as two-pointers-opposite if it happened to have opposite-direction updates. |
| **Carry name heuristic** | Low | The carry detection uses `CARRY_LIKE_NAMES` which is a heuristic. A variable named `x` that carries state would not be detected. The architecture allows this (§4.4), but it's a known limitation. |
| **`while_loop_comparison` for truthiness** | Low | Add Two Numbers uses `while l1 or l2 or carry` (truthiness), not a comparison. The `while_loop_comparison` fact doesn't fire. This is correct behavior but means `sequential_accumulation` doesn't fire for this case. The `carry_propagation` technique correctly captures the relevant pattern. |

### 14.2 Hidden Coupling

| Coupling | Severity | Description |
|---|---|---|
| **`shadow_runner.py` imports `ast.parse`** | Low | The shadow runner duplicates the AST parsing step (the existing `run_analysis` also calls `ast.parse` via `Parser`). This is intentional for isolation but means the code is parsed twice per request. |
| **`matching.py` `_evaluate_single_group` returns inconsistent keys** | Low | The function returns `{"outcome": "contradicted", "satisfaction": 0.0}` when excluded fires, but `{"outcome": "satisfied", "satisfaction": ...}` or `{"outcome": "unsatisfied", "satisfaction": ...}` otherwise. The key name is consistent (`satisfaction`), but the semantics differ (0.0 for contradicted vs computed value for satisfied). |

### 14.3 Technical Debt

| Debt | Severity | Description |
|---|---|---|
| **No persistence** | Medium | Shadow analysis results are returned in the API response but not persisted to the database. Future re-derivation from structural facts is not possible without persistence. |
| **Static version numbers** | Low | All version numbers are hardcoded to `"1.0.0"`. No mechanism exists to increment them when definitions change. |
| **No re-derivation engine** | Medium | The architecture (§12) requires: "Re-derive higher-level evidence from persisted facts when needed." No such engine exists yet. |
| **`CARRY_LIKE_NAMES` is opinionated** | Low | The set includes `"val"` which is very generic. A variable named `val` in a non-carry context would produce a false `carry_propagation` fact. |
| **`NODE_CONSTRUCTOR_PREFIXES` is fragile** | Low | A constructor named `TreeNode` (capital T) would not match `"treenode"` (lowercase) because the check uses `name.lower().startswith(p)`. This works because of `.lower()`, but a constructor named `MyNode` would not match. |

### 14.4 Responsibility Boundary Assessment

| Boundary | Architecture Says | Implementation Does | Match? |
|---|---|---|---|
| Facts are canonical | §3.1: "The canonical persisted analysis artifact is the set of deterministic structural facts" | Facts are the first output; everything else derives from them | ✅ |
| Techniques are derived | §5: "Techniques are reusable computational idioms constructed from multiple structural facts" | `detect_techniques(facts)` produces derived `TechniqueEvidence` | ✅ |
| Strategies are derived | §6: "Strategies are higher-level, derived concepts" | `evaluate_strategies(techniques, facts)` produces derived `StrategyEvidence` | ✅ |
| Primary strategy is a projection | §7: "`primary_strategy` is a derived projection only" | `_get_primary_strategy()` returns highest-confidence strategy or None | ✅ |
| Multiple solution groups are first-class | §8: "A problem may have multiple accepted solution approaches" | `evaluate_solution_groups` iterates over all groups independently | ✅ |
| Exact pattern-ID equality is NOT valid matching | §20.8: "Exact pattern-ID equality is not the definition of a valid solution" | Matching uses technique/strategy satisfaction, not pattern-ID equality | ✅ |
| UNRESOLVED is non-punitive | §9.1: "UNRESOLVED is normal and non-punitive" | Shadow path has no write path; UNRESOLVED doesn't trigger downstream | ✅ |
| Bootstrap cannot contradict | §10.2: "Bootstrap-tier solution groups must not produce authoritative contradiction" | `llm_proposed` CONTRADICTED → UNRESOLVED | ✅ |
| Facts don't compete | §3.2: "A submission may contain many simultaneously true facts" | Multiple facts are extracted simultaneously (no competition) | ✅ |
| Techniques are non-exclusive | §3.3: "A technique can appear in many strategies" | `carry_propagation` and `bidirectional_index_scan` can both fire | ✅ |

---

## Summary of Findings

### Critical Issues: 0

### Important Issues: 1

1. **Midpoint detection gap (§14.1):** The `two_pointers_opposite` strategy checks for absence of `midpoint_calculation`, but no fact type produces this. This means binary search with opposite-direction updates would be misclassified as `two_pointers_opposite`. **Fix required before activating the matcher in production.** For the current vertical slice (observational only), this is acceptable.

### Minor Issues: 3

1. **Carry name heuristic (§14.1):** Works but is opinionated. Acceptable per architecture §4.4.
2. **Double AST parsing (§14.2):** Intentional for isolation. Acceptable for V1.
3. **Static version numbers (§14.3):** Deferred per architecture §12.

### Technical Debt: 2 items

1. **No persistence** — Must be added before production activation.
2. **No re-derivation engine** — Deferred per architecture §12.5.

---

## Final Verdict

**APPROVED WITH REQUIRED FIXES**

The vertical-slice implementation is architecturally sound. It correctly implements:
- Canonical structural facts as the first layer
- Derived technique and strategy evidence
- Separate presence_confidence and centrality
- Solution-group satisfaction matching
- Authority-gated CONFIRMED/UNRESOLVED/CONTRADICTED outcomes
- Shadow-only execution with no production impact

**Required fix before next phase:**
1. Implement `midpoint_calculation` as a structural fact type in the fact extractor, so the `two_pointers_opposite` strategy's absence constraint actually works. Without this, binary search would be misclassified.

**Recommended fixes (not blocking):**
1. Add persistence for shadow analysis results (JSONB column on submissions).
2. Make `CARRY_LIKE_NAMES` less opinionated or use data-flow analysis.
3. Document the double-parse performance trade-off.

**The implementation is ready for Phase 2** (remaining techniques and strategies) once the midpoint detection gap is addressed.
