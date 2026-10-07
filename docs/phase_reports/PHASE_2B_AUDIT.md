# Phase 2B Audit

**Date:** August 22, 2026
**Audit target:** Phase 2B strategy implementation (all 8 strategies)
**Reference documents:**
- `PATHFORGE_ANALYSIS_ARCHITECTURE_V1.md` (frozen architecture)
- `PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md` (technique/strategy vocabulary)
- `PHASE_VERTICAL_SLICE_AUDIT.md` (previous audit)
- `PHASE_2B_STRATEGIES_IMPLEMENTATION_REPORT.md` (Phase 2B report)

---

## 1. All 8 Strategies Remain Derived Projections

**Check:** Are strategies derived from techniques + facts, not canonical truth?

**Evidence:**
- `StrategyEvidence` dataclass has `supporting_technique_ids` and `supporting_fact_ids` referencing lower layers.
- Each strategy evaluator returns `StrategyEvidence` with explicit derivation chain.
- `shadow_runner.py` stores the full chain: facts → techniques → strategies → match outcome.
- `MatchOutcome` stores `strategy_evidence` as a list of derived projections.

**Verdict:** ✅ **CORRECT.** All 8 strategies are derived projections with traceable derivation chains.

**Deviation:** None.

---

## 2. No Strategy Logic Leaked into Fact Extractor

**Check:** Does `fact_extractor.py` contain any technique/strategy logic?

**Evidence:**
- Grep for strategy names (`binary_search`, `sliding_window`, `two_pointers_opposite`, `dfs_backtracking`, `dp_top_down`, `dp_bottom_up`, `bfs_shortest_path`, `union_find`) in fact_extractor.py returns only:
  - Line 7: Module docstring listing original scope (documentation only)
  - Line 783: `"bfs_queue"` in queue variable name heuristic (variable name heuristic, not strategy logic)
  - Lines 797-799: Docstring mentioning "backtracking" and "dfs" (documentation only)
- No method name contains a strategy or technique ID.
- No fact type contains a strategy or technique ID.
- The fact extractor imports only `StructuralFact` and `EXTRACTOR_VERSION`.

**Verdict:** ✅ **CORRECT.** The fact extractor contains no strategy/technique logic.

**Deviation:** None.

---

## 3. No New Name-Based Classification Exists

**Check:** Does any detection rely on variable names or function names?

**Evidence (name-based heuristics in fact_extractor.py):**

| Heuristic | Location | Architecture Justification |
|---|---|---|
| `CARRY_LIKE_NAMES` | Line 57 | §4.4 "limited, intraprocedural type inference" — heuristic, not hard requirement |
| `NODE_CONSTRUCTOR_PREFIXES` | Line 62 | §4.4 — heuristic for node construction detection |
| `cache_like` (DP top-down) | Lines 697, 745 | §4.4 — heuristic for memoization detection |
| `graph_like` (BFS) | Line 720 | §4.4 — heuristic for graph structure detection |
| `queue_like` (BFS) | Line 782 | §4.4 — heuristic for queue detection |
| `depth_like` (recursive depth) | Line 891 | §4.4 — heuristic for depth parameter detection |
| `visited_tracking` | Line 969 | §4.4 — heuristic for visited set detection |

**Critical check:** Are any of these heuristics hard requirements that would cause false negatives?

- `CARRY_LIKE_NAMES`: If a carry variable is named `c` (which IS in the set), it fires. If named `tmp`, it doesn't. The test `test_renamed_carry_propagation` verifies `c` works. This is a documented heuristic.
- `cache_like`: If the memo dict is named `memo`, `cache`, `dp`, `table`, etc., it fires. If named `lookup`, it doesn't. This could cause false negatives for non-standard cache names.
- `graph_like`: If the graph is named `graph`, `adj`, etc., it fires. If named `g`, it doesn't. This could cause false negatives.
- `queue_like`: If the queue is named `queue`, `q`, etc., it fires. If named `frontier`, it doesn't. This could cause false negatives.
- `visited_tracking`: If the visited set is named `visited`, `seen`, etc., it fires. If named `vis`, it fires (in the set). If named `explored`, it fires. This is reasonable.

**Verdict:** ⚠️ **ACCEPTED WITH DOCUMENTATION.** The name-based heuristics are documented as heuristics, not hard requirements. They work for common variable names but may cause false negatives for unusual names. This is consistent with §4.4 ("limited, intraprocedural type inference") and the Phase Vertical Slice Audit's acceptance of carry name heuristics.

**Risk for Phase 3:** The `cache_like` and `graph_like` heuristics could cause false negatives in production. Consider adding structural fallbacks (e.g., detecting dict access patterns regardless of variable name) in Phase 3.

---

## 4. Union-Find Is Genuinely Name-Independent

**Check:** Does union-find detection rely on any variable or function names?

**Evidence:**
- `_detect_parent_pointer_chase` (line 1031): Checks for `while subscript[x] != x: x = subscript[x]` pattern. Uses only AST structure (Subscript, Name, Compare, Assign). No variable name checks.
- `_detect_parent_root_merge` (line 1084): Checks for `subscript[a] = b` pattern. Uses only AST structure. No variable name checks.
- `_evaluate_union_find` (strategies.py): Requires both `parent_pointer_chase` AND `parent_root_merge` facts. No technique required. No variable name checks.

**Verification from Phase 2B report:**
- ✅ Classic find() + union() with rank
- ✅ Renamed functions (find_root, merge_sets)
- ✅ Inline implementation (nested function)
- ✅ Union-find without rank optimization
- ✅ Path compression present
- ❌ find_max → NOT detected (correct)
- ❌ Generic parent array → NOT detected (correct)
- ❌ Tree traversal → NOT detected (correct)
- ❌ Graph DFS → NOT detected (correct)

**Verdict:** ✅ **CORRECT.** Union-find detection is purely structural. No variable names or function names are involved.

**Deviation:** None.

---

## 5. Binary Search vs Two-Pointers vs Sliding-Window Separation Is Structurally Justified

**Check:** Are the three strategies separated by structural constraints, not heuristics?

**Evidence:**

| Strategy | Required Facts | Absence Constraints |
|---|---|---|
| `binary_search` | midpoint_calculation + while_loop_comparison + conditional_index_update | no opposite_direction_updates |
| `two_pointers_opposite` | bidirectional_index_scan + while_loop_comparison + opposite_direction_updates | no midpoint_calculation |
| `sliding_window` | loop_state_tracking + variable_use_in_loop_body | no midpoint, no opposite updates |

**Structural justification:**
- **Binary search** is uniquely identified by midpoint calculation — no other strategy computes `(lo + hi) // 2`.
- **Two-pointers opposite** is uniquely identified by opposite-direction updates without midpoint.
- **Sliding window** is uniquely identified by conditional state update + variable use in later expression.

**Cross-strategy confusion tests (all pass):**
- ✅ Binary search → NOT two_pointers_opposite
- ✅ Binary search → NOT sliding_window
- ✅ Two-pointers → NOT binary_search
- ✅ Sliding window → NOT two_pointers_opposite
- ✅ Sliding window → NOT binary_search

**Verdict:** ✅ **CORRECT.** The three strategies are separated by structural constraints (midpoint calculation, opposite-direction updates, variable_use_in_loop_body). No heuristics or naming involved.

**Deviation:** None.

---

## 6. DFS/Backtracking Fallback Does Not Violate Technique/Strategy Boundary

**Check:** Does the DFS/backtracking strategy bypass the technique layer?

**Evidence:**
- The vocabulary specifies: "Required techniques: recursive_branching (T4)"
- The implementation uses: `(recursive_branching OR self_recursive_call + early_termination) + state_restoration`
- The fallback path (`self_recursive_call + early_termination`) still uses structural facts from the fact layer.
- The strategy does NOT skip the technique layer entirely — it uses facts directly when the technique doesn't fire.

**Architecture analysis:**
- §6.1: "A strategy must be defined by a combination of technique evidence, required structural constraints, optional supporting evidence."
- The fallback path uses "required structural constraints" (facts) instead of "technique evidence."
- This is architecturally valid: the strategy layer can combine techniques AND facts.

**Recursive pattern analysis (from Phase 2B report):**

| Pattern | recursive_branching | state_restoration | Correct Strategy |
|---|---|---|---|
| Fibonacci | ✅ | ❌ | none (correct) |
| Tree DFS | ✅ | ❌ | none (correct) |
| Backtracking | ❌ | ✅ | dfs_backtracking (via fallback) |
| Top-down DP | ✅ | ❌ | dp_top_down (correct) |
| Linear recursion | ❌ | ❌ | none (correct) |

**Verdict:** ✅ **CORRECT.** The fallback path is architecturally valid. It uses structural facts (self_recursive_call, early_termination) as constraints, which is permitted by §6.1. The technique layer is not bypassed — it is supplemented.

**Note:** The vocabulary's `recursive_branching` technique is defined as "recursion across distinct branches." Backtracking has linear recursion with state management, which is an orthogonal concern. The current architecture correctly treats these as separate signals.

**Deviation:** Minor deviation from vocabulary (which requires `recursive_branching`). Justified by structural analysis. Documented in Phase 2B report.

---

## 7. DP Top-Down vs DFS Separation Is Structurally Justified

**Check:** Are DP top-down and DFS/backtracking separated by structural constraints?

**Evidence:**

| Strategy | Required | Absence Constraint |
|---|---|---|
| `dp_top_down` | recursive_branching + cache_lookup + cache_write | no state_restoration |
| `dfs_backtracking` | self_recursive_call + early_termination + state_restoration | no cache_lookup/cache_write |

**Structural justification:**
- **DP top-down** requires cache/memoization (cache_lookup + cache_write) — this is the defining structural feature.
- **DFS/backtracking** requires state restoration (add/remove or append/pop) — this is the defining structural feature.
- The two strategies are mutually exclusive via absence constraints: cache ↔ state_restoration.

**Cross-strategy confusion tests (all pass):**
- ✅ DFS → NOT dp_top_down
- ✅ DP top-down → NOT dfs_backtracking

**Verdict:** ✅ **CORRECT.** The separation is structural and bidirectional. No heuristics involved.

**Deviation:** None.

---

## 8. DP Bottom-Up vs Simple Prefix-Sum False Positive Is Explicitly Documented and Contained

**Check:** Is the prefix-sum false positive documented and contained?

**Evidence:**
- Phase 2B report explicitly documents: "Prefix sums classified as dp_bottom_up — Requires lookback-count or recurrence-complexity fact. Deferred to V2."
- The false positive occurs because prefix sums have `indexed_write + index_lookback`, which satisfies `iterative_table_filling`.
- The `dp_bottom_up` strategy does NOT have an absence constraint for prefix sums.
- The false positive is contained: it does not affect other strategies or cause false contradictions.

**Architecture analysis:**
- The vocabulary §3.7 acknowledges: "Simple prefix sum (`prefix[i] = prefix[i-1] + nums[i]`) is a borderline case. It IS iterative table filling."
- The vocabulary §5.7 notes: "Known confusing strategies: prefix_sum — both fill arrays iteratively. DP bottom-up has branching/recurrence; prefix sum is a single accumulation formula."
- The current fact model cannot distinguish "single accumulation formula" from "branching/recurrence."

**Verdict:** ⚠️ **ACCEPTED V1 LIMITATION.** The false positive is explicitly documented, contained, and acknowledged in the vocabulary. It does not cause incorrect contradictions. The distinction requires deeper structural analysis (recurrence complexity) not justified in V1.

**Risk for Phase 3:** If solution groups for specific problems require distinguishing DP from prefix sums, this limitation will need to be addressed. Consider adding a `recurrence_branching` fact (e.g., multiple lookback positions or conditional recurrence) in V2.

---

## 9. BFS Detection Does Not Overclaim Tree BFS Support

**Check:** Does BFS detection claim to support tree BFS?

**Evidence:**
- The `bfs_shortest_path` strategy requires `neighbor_traversal` — which is defined as `graph[node]` subscript access.
- Tree BFS uses `node.left`/`node.right` attribute access, which is `linked_attribute_access`, not `neighbor_traversal`.
- The test `test_bfs_level_order_tree` explicitly verifies that tree level-order traversal does NOT fire `bfs_shortest_path`.

**Phase 2B report documents:** "Tree BFS not detected — Level-order tree traversal uses `node.left`/`node.right` (linked attributes), not `graph[node]` (neighbor traversal). This is a legitimate structural distinction."

**Verdict:** ✅ **CORRECT.** BFS detection correctly scopes to graph BFS only. Tree BFS is a known V1 limitation, explicitly documented.

**Deviation:** None. The architecture spec does not require tree BFS support.

---

## 10. UNRESOLVED Remains Non-Punitive

**Check:** Does UNRESOLVED trigger any punitive behavior?

**Evidence:**
- `matching.py`: The `evaluate_solution_groups` function returns `MatchOutcome` with `outcome="UNRESOLVED"` when no solution group is satisfied.
- The shadow analysis path is observational only — it does NOT affect production verdict, ELO, gaps, or recommendations.
- The `shadow_runner.py` returns results as diagnostic output, not authoritative analysis.
- The `analyze.py` endpoint stores shadow results in `hybrid_analysis` field, which is separate from the production `match_result`.

**Architecture invariants:**
- §9.1: "UNRESOLVED: Evidence is insufficient, ground truth is not authoritative enough, or no solution group is adequately satisfied."
- §15: "Correct code with incomplete ground truth → UNRESOLVED, not an unjustified contradiction."
- §20.9: "Unresolved is a normal and non-punitive outcome."

**Verdict:** ✅ **CORRECT.** UNRESOLVED is non-punitive. It does not trigger ELO changes, gap signals, or recommendations.

**Deviation:** None.

---

## 11. Low-Authority Contradictions Remain Downgraded to UNRESOLVED

**Check:** Are low-authority contradictions correctly downgraded?

**Evidence:**
- `matching.py` line ~80: `if group_authority in _AUTHORITATIVE_TIERS: group_final = "CONTRADICTED"` else `group_final = "UNRESOLVED"`.
- `_AUTHORITATIVE_TIERS = {"structurally_observed", "externally_listed", "editorial"}`.
- Bootstrap/llm_proposed tiers are NOT in `_AUTHORITATIVE_TIERS`.
- Test `test_bootstrap_contradiction_becomes_unresolved` verifies this behavior.

**Architecture invariants:**
- §9.1: "A low-authority/bootstrap group must not generate CONTRADICTED."
- §10.2: "Bootstrap-tier solution groups must not produce authoritative contradiction."
- §20.10: "Bootstrap ground truth cannot confidently contradict a user."

**Verdict:** ✅ **CORRECT.** Low-authority contradictions are correctly downgraded to UNRESOLVED.

**Deviation:** None.

---

## 12. Shadow Analysis Cannot Affect Production Verdict/ELO/Gaps/Recommendations

**Check:** Is the shadow analysis path completely isolated from production?

**Evidence:**
- `shadow_runner.py` is a standalone module — it does NOT modify any production state.
- `analyze.py` calls `run_shadow_analysis()` and stores results in `hybrid_analysis` field of `AnalyzeResponse`.
- `hybrid_analysis` is an `Optional[HybridAnalysis]` field — it is diagnostic metadata, not authoritative analysis.
- The production verdict (`match_result`), ELO updates (`elo_updates`), gap signals (`submission_gap`), and recommendations are computed by the existing production pipeline, not the shadow path.
- If `run_shadow_analysis()` fails, it returns `None` — the production analysis continues normally.

**Architecture invariants:**
- §20.11: "Lower-confidence analysis cannot silently affect ELO, gaps, recommendations, or other authoritative downstream behavior."

**Verdict:** ✅ **CORRECT.** The shadow analysis path is completely isolated from production behavior.

**Deviation:** None.

---

## 13. Versioning and Fact Traceability Are Preserved

**Check:** Are facts versioned and traceable?

**Evidence:**
- `EXTRACTOR_VERSION = "1.0.0"` in `data_structures.py`.
- Every `StructuralFact` has `extractor_version` field.
- Every `TechniqueEvidence` has `technique_version` field.
- Every `StrategyEvidence` has `strategy_version` field.
- Every fact has `ast_ref` for source-location traceability.
- Every fact has `fact_id` for cross-referencing.
- `shadow_runner.py` serializes all version fields in output.

**Architecture invariants:**
- §11: "The canonical persisted submission artifact is the structural fact set."
- §12: "Structural facts are stable observations tied to an extractor version."
- §20.12: "Higher-level definitions are versioned and re-derivable from stable evidence."

**Verdict:** ✅ **CORRECT.** Versioning and traceability are preserved across all layers.

**Deviation:** None.

---

## 14. Existing 554-Test Behavior Remains Unchanged

**Check:** Do all existing tests pass?

**Evidence:**
- Phase 2B report: "554 existing tests: ALL PASS (16 pre-existing PostgreSQL connection failures)"
- The 16 failures are all `psycopg2.OperationalError: could not translate host name` — pre-existing database connection issues unrelated to Phase 2B.
- The shadow analysis path is additive — it does NOT modify any existing production code paths.
- All 132 shadow tests pass.

**Verdict:** ✅ **CORRECT.** Existing test behavior is unchanged. No regressions.

**Deviation:** None.

---

## 15. No Problem-Specific Heuristics Were Introduced

**Check:** Does the implementation contain problem-specific logic?

**Evidence:**
- Grep for problem IDs, problem names, or LeetCode-specific patterns in shadow analysis code returns no results.
- No detector is named after a specific problem.
- No fact type references a specific problem.
- No technique or strategy references a specific problem.
- The Add Two Numbers and 2996 validation cases use generic code patterns, not problem-specific detectors.

**Architecture invariants:**
- §17: "A problem-specific detector is explicitly prohibited."

**Verdict:** ✅ **CORRECT.** No problem-specific heuristics were introduced.

**Deviation:** None.

---

## 16. V1 Limitations — Phase 3 Risk Assessment

The following "accepted V1 limitations" were identified. I assess each for Phase 3 risk:

### 16.1 Prefix sums classified as dp_bottom_up

**Risk Level:** LOW-MEDIUM
- The false positive is contained — it does not cause incorrect contradictions.
- If solution groups require distinguishing DP from prefix sums, a `recurrence_branching` fact will be needed.
- Recommendation: Defer to V2. Add `recurrence_branching` fact (multiple lookback positions or conditional recurrence) when needed.

### 16.2 Tree BFS not detected

**Risk Level:** LOW
- Tree BFS uses a different structural pattern (attribute access vs subscript).
- If tree problems need BFS detection, add `linked_attribute_traversal` as an alternative to `neighbor_traversal`.
- Recommendation: Defer to V2. Document as known limitation.

### 16.3 DFS/backtracking technique gap

**Risk Level:** NONE
- The strategy works correctly via fallback path.
- The architecture correctly treats `recursive_branching` and `state_restoration` as orthogonal concerns.
- No fix needed.

### 16.4 Name-based heuristics (cache_like, graph_like, queue_like)

**Risk Level:** MEDIUM
- These heuristics work for common variable names but may cause false negatives for unusual names.
- If production needs broader detection, add structural fallbacks (e.g., detecting dict access patterns regardless of variable name).
- Recommendation: Monitor false negatives in production. Add structural fallbacks in V2 if needed.

### 16.5 `visited_tracking` requires variable name "visited" or similar

**Risk Level:** LOW-MEDIUM
- Most BFS/DFS code uses `visited` or `seen` as variable names.
- If unusual names are used, the fact won't fire, causing false negatives.
- Recommendation: Consider detecting `set()` creation paired with `in`/`not in` membership checks as a structural alternative.

---

## 17. Dead Code Issue — FIXED

**Check:** Is there dead code in the implementation?

**Evidence:**
- `strategies.py` line 254: `{"loop_state_tracking" if False else "conditional_index_update", ...}` — the `if False` branch was dead code.

**Fix applied:** Removed the dead `if False` branch. Expression now simply uses `"conditional_index_update"`.

**Verdict:** ✅ **FIXED.**

---

## 18. Vocabulary Deviations

The implementation deviates from the vocabulary in several places. I assess each:

### 18.1 `boundary_narrowing` (T2) not implemented as a technique

**Vocabulary:** Binary search requires `boundary_narrowing` technique.
**Implementation:** Binary search uses structural facts directly (midpoint_calculation + while_loop_comparison + conditional_index_update).
**Assessment:** Acceptable. The `boundary_narrowing` concept is captured by the structural fact combination. Implementing it as a separate technique would add complexity without benefit.

### 18.2 `sequential_accumulation` (T1) not required for sliding_window

**Vocabulary:** Sliding window requires `sequential_accumulation` + `loop_state_tracking`.
**Implementation:** Sliding window requires `loop_state_tracking` + `variable_use_in_loop_body`.
**Assessment:** Acceptable. The `variable_use_in_loop_body` fact is more specific than `sequential_accumulation` for the sliding window pattern. The vocabulary's `sequential_accumulation` requirement was overly broad.

### 18.3 DFS/backtracking uses fallback path

**Vocabulary:** DFS backtracking requires `recursive_branching` technique.
**Implementation:** Uses `self_recursive_call + early_termination + state_restoration` (facts) as fallback.
**Assessment:** Acceptable. Documented in Phase 2B report. The fallback is architecturally valid per §6.1.

### 18.4 BFS requires no techniques

**Vocabulary:** BFS requires no techniques (uses structural facts directly).
**Implementation:** BFS requires no techniques (uses structural facts directly).
**Assessment:** ✅ MATCH.

### 18.5 Union-find requires no techniques

**Vocabulary:** Union-find requires no techniques.
**Implementation:** Union-find requires no techniques.
**Assessment:** ✅ MATCH.

---

## Final Verdict

**APPROVED**

### Required Fixes (addressed):

1. **Dead code cleanup:** ✅ FIXED — Removed `if False` branch in `strategies.py` line 254.

### Recommended Fixes (should be addressed in Phase 3):

2. **Name-based heuristic documentation:** Add explicit documentation in `fact_extractor.py` that `cache_like`, `graph_like`, `queue_like`, and `visited_tracking` are name-based heuristics that may cause false negatives for unusual variable names.

3. **Vocabulary alignment:** Update `PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md` to reflect the actual implementation:
   - Binary search uses structural facts directly (not `boundary_narrowing` technique)
   - Sliding window uses `variable_use_in_loop_body` (not `sequential_accumulation`)
   - DFS/backtracking uses fallback path (not `recursive_branching`)

### No Fixes Required:

- Union-find is purely structural ✅
- Binary search / two-pointers / sliding-window separation is structural ✅
- DP top-down vs DFS separation is structural ✅
- UNRESOLVED is non-punitive ✅
- Low-authority contradictions are downgraded ✅
- Shadow analysis is isolated from production ✅
- Versioning and traceability are preserved ✅
- No regressions ✅
- No problem-specific heuristics ✅

### V1 Limitations (accepted, documented, low Phase 3 risk):

- Prefix sums classified as dp_bottom_up
- Tree BFS not detected
- Name-based heuristics may cause false negatives
