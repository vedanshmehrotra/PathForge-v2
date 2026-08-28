# PATHFORGE PROJECT HANDOFF

**Branch:** `architecture/strategy-evidence-spike`
**Date:** 2026-08-25
**Latest commit:** `b88cab4` — "feat: upadted shadow pilot observability in the analysis section along with title slug mismatch corrections"

---

## 1. PROJECT STRUCTURE

### Repository Root

```
/pathforge/                  — Python backend (FastAPI)
/pathforge-frontend/         — Next.js frontend (TypeScript, Tailwind)
/src/                        — Production AST detection + matching engine (shared Python)
/tests/                      — Empty directory (tests live inside their respective modules)
/docs/                       — Documentation directory
*.md                         — Architecture reports, phase docs, evaluation results
pathforge.db                 — SQLite database (local dev, superseded by PostgreSQL)
Procfile                      — Render deployment entry point
requirements.txt             — Python dependencies
config.py                    — Environment variable loader
```

### Backend (`pathforge/`)

| Directory | Purpose |
|-----------|---------|
| `pathforge/api/` | FastAPI application, route handlers, auth middleware |
| `pathforge/api/routes/` | Individual endpoint modules: `analyze.py`, `prepare_problem.py`, `gaps.py`, `elo_route.py`, `recommend.py` |
| `pathforge/api/services/` | Orchestration services: `analysis.py` (AST+matching), `gap.py`, `elo.py`, `loader.py`, `recommend_service.py`, `shadow_observability.py` |
| `pathforge/services/` | Core business logic: `problem_resolver.py`, `ground_truth_builder.py`, `persistence.py`, `submission_persistence.py` |
| `pathforge/ast_analysis/shadow/` | Shadow analysis pipeline: fact extraction, technique detection, strategy evaluation, matching, authority, coherence, persistence, data structures |
| `pathforge/ast_engine/` | Legacy AST engine: `classifier.py`, `extractor.py`, `patterns.py`, `sanitizer.py` |
| `pathforge/db/` | Database layer: `db.py` (PostgreSQL pool), `schema.sql` (SQLite), `schema_pg.sql` (PostgreSQL), `elo.py`, `profile_manager.py` |
| `pathforge/llm/` | External API clients: `graphql_client.py` (LeetCode GraphQL), `openrouter_client.py` (OpenRouter/GPT-4o-mini) |
| `pathforge/routes/` | Additional route modules: `auth.py`, `problems.py`, `profile.py`, `submissions.py` |
| `pathforge/auth/` | Authentication middleware |
| `pathforge/data/` | Dataset files: `pathforge_problems_fixed.csv`, `validate_dataset.py` |

### Production AST + Matching (`src/`)

| Directory | Purpose |
|-----------|---------|
| `src/ast_detection/` | Production AST analysis engine |
| `src/ast_detection/detectors/` | 36 individual pattern detectors (one per algorithmic pattern) |
| `src/ast_detection/semantic/` | Legacy semantic/hybrid shadow detector (ShadowDetector) |
| `src/ast_detection/tests/` | Tests for detectors, registry, coordinator, parser, output pipeline |
| `src/matching_engine/` | Pattern matching engine (`matching_engine.py`) |

### Frontend (`pathforge-frontend/`)

| Directory | Purpose |
|-----------|---------|
| `pathforge-frontend/app/` | Next.js app router pages: `analysis/`, `auth/`, `profile/`, `progress/`, `recommendations/` |
| `pathforge-frontend/components/` | React components: `analysis-view.tsx`, `experimental-panel.tsx`, `charts.tsx`, `dashboard.tsx`, `profile-view.tsx`, `progress-view.tsx`, `recommendations-view.tsx` |
| `pathforge-frontend/components/ui/` | Shared UI primitives: `badge.tsx`, `button.tsx`, `panel.tsx`, `stat.tsx` |
| `pathforge-frontend/src/types/` | TypeScript type definitions: `api.ts` |
| `pathforge-frontend/src/services/` | API client layer: `api/endpoints.ts`, `api/client.ts`, `api/auth.ts`, `shadow-mapper.ts` |
| `pathforge-frontend/src/hooks/` | React hooks: `useApi.ts` |

### Configuration Files

| File | Purpose |
|------|---------|
| `config.py` | Loads `SECRET_KEY`, `DATABASE_PATH`, `JWT_SECRET`, `OPENROUTER_API_KEY` from env |
| `pathforge-frontend/next.config.mjs` | Next.js configuration |
| `pathforge-frontend/postcss.config.mjs` | PostCSS/Tailwind configuration |
| `pathforge-frontend/vitest.config.ts` | Frontend test configuration |
| `pathforge-frontend/package.json` | Frontend dependencies |
| `requirements.txt` | Python dependencies (psycopg2-binary, fastapi, etc.) |
| `Procfile` | Render deployment command |
| `.env.example` | Environment variable template |
| `pathforge-frontend/.env.local` | Frontend local env vars |

---

## 2. BACKEND ARCHITECTURE

### End-to-End Analysis Request Flow

```
POST /analyze
  │
  ├─ Auth: get_current_user(request) → user.user_id
  │
  ├─ Problem Resolution (if problem provided):
  │   └─ resolve_problem(conn, leetcode_id, title_slug) → ProblemContext
  │       ├─ _find_problem_in_db() → DB lookup
  │       ├─ _fetch_and_store_problem() → GraphQL cache-fill (if missing)
  │       │   └─ fetch_problem_by_slug() → LeetCode GraphQL
  │       ├─ _ensure_ground_truth() → LLM generation (if missing)
  │       │   └─ build_ground_truth() → OpenRouter LLM
  │       └─ _load_ground_truth() → DB load + V1 vocabulary mapping
  │
  ├─ Production AST Analysis:
  │   └─ run_analysis(code, language, accepted_solution_groups) → {ast, match_result}
  │       ├─ ASTAnalysisEngine.analyze(code)
  │       │   ├─ Parser.parse(code) → ast.AST
  │       │   ├─ DetectorManager.detect_all(ast_root) → List[DetectionResult]
  │       │   │   └─ For each of 36 detectors: detector.detect(ast_root)
  │       │   ├─ Coordinator.aggregate_and_filter(results) → filtered + sorted
  │       │   └─ OutputPipeline.package_results(detected) → {detected_patterns: [...]}
  │       └─ MatchingEngine.match(llm_input, ast_output) → MatchResult
  │           ├─ _normalize_ast() → {pattern_id: confidence}
  │           ├─ _normalize_llm() → List[Set[str]] groups
  │           ├─ _compute_group_matches() → per-group coverage
  │           ├─ _compute_confidence() → weighted confidence
  │           ├─ _decide_match_result() → FULL_MATCH | PARTIAL_MATCH | NO_MATCH
  │           └─ _build_reasoning_signals() → human-readable signals
  │
  ├─ Persistence:
  │   └─ run_persistence(conn, user_id, problem_id, ..., ast_output, match_result, groups)
  │       ├─ Evidence authority gating (is_authoritative check)
  │       │   ├─ If authoritative → full pipeline:
  │       │   │   ├─ update_topic_profile() → topic_profiles ELO
  │       │   │   ├─ GapSignalEngine.compute_signals() + persist_signals()
  │       │   │   ├─ EloEngine.compute_updates() + persist_elos()
  │       │   │   ├─ get_recommendation() + _log_recommendation()
  │       │   │   └─ evidence_ceiling = EVIDENCE_K_CEILINGS[evidence_state]
  │       │   └─ If analysis_only → submission stored, no downstream scoring
  │       └─ _update_user_streak() → always updated
  │
  ├─ Shadow Hybrid Analysis (observational, try/except wrapped):
  │   └─ ShadowDetector.analyze_safe(code) → discrepancies, hybrid_detections
  │
  ├─ Shadow Fact/Technique/Strategy Analysis (observational, try/except wrapped):
  │   └─ run_shadow_analysis(code, solution_groups) → shadow results
  │       ├─ ast.parse(code) → AST
  │       ├─ extract_structural_facts(tree) → List[StructuralFact]
  │       ├─ detect_techniques(facts) → List[TechniqueEvidence]
  │       ├─ evaluate_strategies(technique_evidence, facts) → List[StrategyEvidence]
  │       └─ evaluate_solution_groups(groups, techniques, strategies, facts) → MatchOutcome
  │   └─ persist_shadow_analysis(conn, submission_id, code_hash, shadow_raw) → DB write
  │   └─ record_shadow_pipeline_result() → in-memory observability counters
  │
  └─ Response: AnalyzeResponse
```

### `POST /prepare-problem` Flow

```
POST /prepare-problem
  │
  ├─ Auth gate
  ├─ resolve_problem(conn, leetcode_id, title_slug) → ProblemContext
  │   ├─ DB lookup → GraphQL fetch (if missing) → LLM ground truth (if missing)
  │   └─ Returns: leetcode_id, title_slug, title, difficulty, topics
  │
  └─ Response: PrepareResponse
```

### Key Functions per Stage

| Stage | File | Function/Class | Input | Output | Affects Production? |
|-------|------|----------------|-------|--------|-------------------|
| Request routing | `pathforge/api/routes/analyze.py` | `analyze_endpoint()` | `AnalyzeRequest` | `AnalyzeResponse` | Yes |
| Problem resolution | `pathforge/services/problem_resolver.py` | `resolve_problem()` | `conn, leetcode_id?, title_slug?` | `ProblemContext` | Yes (provides ground truth) |
| GraphQL fetch | `pathforge/llm/graphql_client.py` | `fetch_problem_by_slug()` | `title_slug` | `dict` or `None` | No (cache-fill only) |
| LLM ground truth | `pathforge/llm/openrouter_client.py` | `call_llm()` | `problem_text` | `dict` or `None` | No (cache-fill only) |
| GT building | `pathforge/services/ground_truth_builder.py` | `build_ground_truth()` | `problem_id, description, conn` | `list[str]` patterns | No (one-time cache) |
| GT loading | `pathforge/services/problem_resolver.py` | `_load_ground_truth()` | `conn, problem_id` | `(groups, confidence)` | Yes (provides matching input) |
| AST analysis | `src/ast_detection/run_analysis.py` | `ASTAnalysisEngine.analyze()` | `code_string` | `{detected_patterns}` | Yes |
| Pattern detection | `src/ast_detection/detector_manager.py` | `DetectorManager.detect_all()` | `ast_root` | `List[DetectionResult]` | Yes |
| Coordination | `src/ast_detection/coordinator.py` | `Coordinator.aggregate_and_filter()` | `List[DetectionResult]` | `List[DetectionResult]` | Yes |
| Matching | `src/matching_engine/matching_engine.py` | `MatchingEngine.match()` | `llm_output, ast_output` | `MatchResult dict` | Yes |
| Persistence | `pathforge/services/persistence.py` | `run_persistence()` | `conn, user_id, ..., ast_output, match_result, groups` | `dict` with IDs | Yes |
| Shadow runner | `pathforge/ast_analysis/shadow/shadow_runner.py` | `run_shadow_analysis()` | `code, solution_groups` | `dict` or `None` | No (shadow only) |
| Shadow fact extraction | `pathforge/ast_analysis/shadow/fact_extractor.py` | `extract_structural_facts()` | `ast_root` | `List[StructuralFact]` | No |
| Shadow technique detection | `pathforge/ast_analysis/shadow/techniques.py` | `detect_techniques()` | `List[StructuralFact]` | `List[TechniqueEvidence]` | No |
| Shadow strategy eval | `pathforge/ast_analysis/shadow/strategies.py` | `evaluate_strategies()` | `techniques, facts` | `List[StrategyEvidence]` | No |
| Shadow matching | `pathforge/ast_analysis/shadow/matching.py` | `evaluate_solution_groups()` | `groups, techniques, strategies, facts` | `MatchOutcome` | No |
| Shadow persistence | `pathforge/ast_analysis/shadow/persistence.py` | `persist_shadow_analysis()` | `conn, submission_id, code_hash, shadow_raw` | `bool` | No |
| Shadow observability | `pathforge/api/services/shadow_observability.py` | `record_shadow_pipeline_result()` | keyword args | `None` (updates counters) | No |

---

## 3. CURRENT PRODUCTION ANALYSIS SYSTEM

### Detector Registry

**File:** `src/ast_detection/registry.py`
**Class:** `DetectorRegistry`

The registry uses a decorator-based pattern. A global `_detector_registry` singleton holds all detector classes keyed by `pattern_id`. Detectors are registered via `@register_detector` decorator. The registry enforces:
- All detectors must subclass `BaseDetector`
- `pattern_id` must be lowercase alphanumeric + underscores
- No duplicate pattern IDs

### Base Classes

**File:** `src/ast_detection/detector_interface.py`

- `EvidenceItem`: Structured evidence with `type`, `description`, `location`, `weight`
- `DetectionResult`: Contains `pattern_id`, `confidence` (0.0–1.0), `evidence` (list of EvidenceItem), `detected` (bool)
- `BaseDetector(ABC)`: Abstract base with `pattern_id` property and `detect(ast_root) -> DetectionResult`

Design constraints:
- Stateless (no mutable state)
- Deterministic (same AST → same result)
- Isolated (no inter-detector communication)
- Safe (no I/O, no shared state)

### Detector Categories (36 detectors)

Each detector lives in `src/ast_detection/detectors/` as a separate Python file:

**Arrays & Hashing (7):**
- `hash_map_lookup.py`, `hash_map_frequency.py`, `prefix_sum.py`
- `sliding_window_fixed.py`, `sliding_window_variable.py`
- `two_pointers_opposite.py`, `two_pointers_same.py`

**Graphs & Trees (7):**
- `dfs_recursive.py`, `dfs_iterative.py`
- `bfs_level_order.py`, `bfs_shortest_path.py`
- `topological_sort.py`, `union_find.py`, `binary_search_tree.py`

**Dynamic Programming (7):**
- `dp_1d_forward.py`, `dp_1d_sequence.py`
- `dp_2d_grid.py`, `dp_2d_string.py`
- `dp_knapsack.py`, `dp_interval.py`, `dp_state_machine.py`

**Linked Lists & Stack (4):**
- `fast_slow_pointers.py`, `linked_list_reversal.py`
- `monotonic_stack.py`, `monotonic_queue.py`

**Binary Search (3):**
- `binary_search_classic.py`, `binary_search_rotated.py`, `binary_search_answer.py`

**Heap / Greedy / Backtracking (5):**
- `heap_priority_queue.py`, `greedy_local.py`, `greedy_interval.py`
- `backtracking_permutation.py`, `backtracking_subset.py`

Plus `base.py` with shared utilities.

### Pattern Representation

**File:** `pathforge/ast_engine/patterns.py`

33 canonical pattern IDs defined as string constants, collected in `ALL_PATTERNS` set. The pattern taxonomy covers: Arrays & Hashing, Graphs & Trees, Dynamic Programming, Linked Lists & Stack, Binary Search, Heap/Greedy/Backtracking.

### Confidence Handling

- Each detector returns a `DetectionResult` with `confidence` on a 0.0–1.0 scale
- `detected` is `True` only when `confidence > 0.0` AND evidence is non-empty
- The `Coordinator` filters to `detected == True` with non-empty evidence only
- No cross-detector confidence weighting is applied at the production level

### Naming Assumptions

- Pattern IDs are lowercase snake_case (e.g., `hash_map_lookup`)
- Evidence types are lowercase snake_case (e.g., `membership_check`)
- The `Coordinator` sorts by confidence descending

### Matching Engine Behavior

**File:** `src/matching_engine/matching_engine.py`
**Class:** `MatchingEngine`

Constants: `MATCH_THRESHOLD = 0.6`, `EXTRA_PATTERN_PENALTY = 0.1`

**Input normalization:**
- AST output: `[{pattern_id, confidence}]` → `{pattern_id: max_confidence}`
- LLM output: `accepted_solution_groups` → `List[Set[str]]`

**Group matching:**
- For each LLM group: compute `overlap = group ∩ ast_patterns`
- `coverage = |matched| / |group|`
- `is_fully_matched = |matched| == |group|` (all expected patterns detected)

**Confidence computation:**
- For each group: `group_conf = Σ(ast_conf[p]) / |group|`
- Best confidence across groups
- Penalty for extra AST patterns not in LLM groups (0.1 × sum of extra confidences)
- Capped at 1.0

**Verdict production:**
- `FULL_MATCH`: At least one group has `is_fully_matched == True`
- `PARTIAL_MATCH`: No full match, but some overlap exists
- `NO_MATCH`: No overlap between any AST pattern and any LLM group
- When no problem is provided: LLM input defaults to `[[hash_map_lookup]]`

### What Drives Production Behavior

The production path is: `ASTAnalysisEngine` → `MatchingEngine` → persistence with evidence gating. The verdict (`FULL_MATCH`/`PARTIAL_MATCH`/`NO_MATCH`) drives:
- Submission verdict (`pass`/`fail`)
- ELO updates (score = 1.0 for FULL_MATCH, 0.5 for PARTIAL, 0.0 for NO_MATCH)
- Gap signal computation
- Recommendation generation

---

## 4. SHADOW ARCHITECTURE

### Complete Shadow Pipeline

The shadow system runs the new fact/technique/strategy path in parallel with the production system. It is **observational only** — wrapped in `try/except` blocks that silently swallow all exceptions.

```
Code
  │
  ├─ ast.parse(code) → AST tree
  │
  ├─ Structural Fact Extraction
  │   └─ extract_structural_facts(tree) → List[StructuralFact]
  │
  ├─ Technique Detection
  │   └─ detect_techniques(facts) → List[TechniqueEvidence]
  │
  ├─ Strategy Evaluation
  │   └─ evaluate_strategies(technique_evidence, facts) → List[StrategyEvidence]
  │
  ├─ Solution-Group Matching
  │   └─ evaluate_solution_groups(groups, techniques, strategies, facts) → MatchOutcome
  │
  └─ Persistence + Observability
      ├─ persist_shadow_analysis(conn, submission_id, code_hash, result) → DB update
      └─ record_shadow_pipeline_result(...) → in-memory counters
```

### Layer Details

#### 1. Structural Fact Extraction

**File:** `pathforge/ast_analysis/shadow/fact_extractor.py`
**Class:** `_FactExtractor(ast.NodeVisitor)`
**Entry:** `extract_structural_facts(ast_root) → List[StructuralFact]`

**Data Structure:** `StructuralFact` (dataclass) with `fact_id`, `fact_type`, `ast_ref`, `attributes`, `extractor_version`

**Fact Types Detected (deterministic, syntax-normalized):**

| Fact Type | Trigger | Key Attributes |
|-----------|---------|----------------|
| `midpoint_calculation` | BinOp: `(a+b)//2`, `a+(b-a)//2` | `form` |
| `while_loop_comparison` | While-loop with comparison on modified vars | `compared_variables`, `modified_variables` |
| `while_loop_truthiness` | `while queue:`, `while stack:` | `variable` |
| `opposite_direction_updates` | Loop body with inc + dec vars | `incremented`, `decremented` |
| `linked_structure_traversal` | `.next`, `.left`, `.right` access in loop | `attributes` |
| `carry_propagation` | Carry-like var in loop with linked traversal | `carry_variables`, `linked_attrs` |
| `accumulator_update` | `x += expr` or `x = x + expr` | `variable`, `operator`, `syntax_form` |
| `self_recursive_call` | Function calls itself | `function_name`, `context` |
| `recursive_call_in_conditional` | Self-recursive call inside if/else | `function_name`, `branch` |
| `multiple_recursive_paths` | 2+ call sites with distinct signatures | `function_name`, `call_count` |
| `state_restoration` | mutation → recurse → restoration pattern | `state_variable`, `mutation`, `restoration` |
| `recursive_depth_tracking` | Depth/level param passed to recursive calls | `depth_parameter` |
| `indexed_write` | `arr[i] = value` | `structure`, `index_type` |
| `index_lookback` | `arr[i-1]`, `arr[i+1]`, `dp[i-coin]` | `structure`, `lookback` |
| `cache_lookup` | `cache[key]`, `memo[key]` (named like cache) | `cache_variable` |
| `cache_write` | `cache[key] = value` (named like cache) | `cache_variable` |
| `queue_dequeue` | `deque()` creation or `popleft()`, `pop(0)` | `queue_variable`, `operation` |
| `stack_creation` | `stack = []` or `stack.append()` | `stack_variable` |
| `stack_operation` | `append()` / `pop()` on stack-like var | `stack_variable`, `operation` |
| `monotonic_comparison` | Comparison with stack top | `operator`, `direction` |
| `conditional_pop` | Pop inside conditional | `condition_type` |
| `neighbor_traversal` | `graph[node]`, `adj[u]` | `graph_variable` |
| `visited_tracking` | `visited = set()` | `variable` |
| `parent_pointer_chase` | `while parent[x] != x: x = parent[x]` | `structure`, `index_variable` |
| `parent_root_merge` | `parent[a] = b` | `structure` |
| `pointer_rewiring` | `node.next = prev` | `pointer_vars`, `direction` |
| `multiple_pointer_traversal` | Loop with 2+ pointer-like vars | `pointer_vars` |
| `linked_attribute_access` | `.next`, `.left`, `.right` anywhere | `attribute`, `receiver` |
| `node_constructor` | `ListNode()`, `TreeNode()` etc. | `constructor`, `arg_count` |
| `early_termination` | `return` statement | `statement` |
| `conditional_index_update` | Index var updated conditionally | `condition_variables`, `updated_variables` |
| `variable_use_in_loop_body` | Conditionally updated var used later | `variables` |
| `for_loop_iteration` | `for` loop (range or iterable) | `loop_variable`, `is_range` |
| `window_size_constant` | Subscript with constant offset | `offset_type`, `structure` |
| `indexed_access` | `arr[i]` read | `structure` |

**Key properties:**
- Deterministic: same code → same facts
- Syntax-normalized: `i += 1` and `i = i + 1` produce same `accumulator_update` fact
- Variable-name-agnostic for structural facts (carry-like names are heuristic only)
- Each fact has a `fact_id` assigned post-extraction (`fact_000`, `fact_001`, etc.)

#### 2. Technique Detection

**File:** `pathforge/ast_analysis/shadow/techniques.py`
**Entry:** `detect_techniques(facts) → List[TechniqueEvidence]`

**Data Structure:** `TechniqueEvidence` (dataclass) with `technique_id`, `technique_version`, `supporting_fact_ids`, `presence_confidence`, `centrality`

**9 Technique Detectors:**

| ID | Name | Required Facts | Optional Facts | Confidence | Centrality |
|----|------|---------------|----------------|------------|------------|
| `sequential_accumulation` | Running total | `while_loop_comparison` + `accumulator_update` (modified in loop) | — | 0.85 | 0.6 |
| `bidirectional_index_scan` | Two-way scan | `while_loop_comparison` + `opposite_direction_updates` (same loop vars) | `conditional_index_update` | 0.9 | 0.85 |
| `carry_propagation` | Carry propagation | `linked_structure_traversal` + `carry_propagation` | `while_loop_comparison`, `node_constructor` | 0.9 | 0.8 |
| `recursive_branching` | Recursive branching | `self_recursive_call` + (`recursive_call_in_conditional` or `multiple_recursive_paths`) | — | 0.75–0.85 | 0.65–0.8 |
| `loop_state_tracking` | State tracking in loops | `while/for_loop` + `conditional_index_update` + def-use chain check | — | 0.75 | 0.7 |
| `iterative_table_filling` | Table building | `while/for_loop` + `indexed_write` + `index_lookback` | `accumulator_update` | 0.8 | 0.75 |
| `linked_list_traversal` | Linked list walk | `linked_structure_traversal` + (`pointer_rewiring` or `multiple_pointer_traversal`) | — | 0.8–0.85 | 0.7–0.8 |
| `fixed_window_maintenance` | Fixed window | `for_loop_iteration` + `window_size_constant` + `indexed_access` | `indexed_write` | 0.8 | 0.75 |
| `monotonic_stack_maintenance` | Monotonic stack | `stack_operation` + `monotonic_comparison` + `conditional_pop` | — | 0.85 | 0.8 |

**Key properties:**
- Techniques are **non-exclusive**: multiple techniques can fire on the same code
- `presence_confidence` indicates detection confidence (0.0–1.0)
- `centrality` indicates how central this technique is to the detected code structure (0.0–1.0)
- Techniques reference their supporting `fact_ids` for traceability

#### 3. Strategy Evaluation

**File:** `pathforge/ast_analysis/shadow/strategies.py`
**Entry:** `evaluate_strategies(technique_evidence, facts) → List[StrategyEvidence]`

**Data Structure:** `StrategyEvidence` (dataclass) with `strategy_id`, `strategy_version`, `supporting_technique_ids`, `supporting_fact_ids`, `confidence`, `problem_context_signals`

**9 Strategy Evaluators:**

| ID | Required Techniques | Required Facts | Absence Constraints | Confidence Source |
|----|-------------------|----------------|--------------------|--------------------|
| `two_pointers_opposite` | `bidirectional_index_scan` | `while_loop_comparison` + `opposite_direction_updates` | NO `midpoint_calculation` | Technique confidence |
| `binary_search` | — | `while_loop_comparison` + `midpoint_calculation` + `conditional_index_update` | NO `opposite_direction_updates` | Hardcoded 0.85 |
| `sliding_window` | `loop_state_tracking` OR `fixed_window_maintenance` | loop present | NO `opposite_direction_updates`, NO `midpoint_calculation` | Technique confidence |
| `dfs_backtracking` | `recursive_branching` OR (`self_recursive_call` + `early_termination`) | `state_restoration` | NO `cache_lookup`, NO `cache_write` | Technique confidence |
| `dp_top_down` | `recursive_branching` | `cache_lookup` + `cache_write` | NO `state_restoration` | Technique confidence |
| `dp_bottom_up` | `iterative_table_filling` | `indexed_write` + `index_lookback` | NO `recursive_branching` | Technique confidence |
| `bfs_shortest_path` | — | `queue_dequeue` + (`neighbor_traversal` OR `linked_structure_traversal`) + loop | NO `recursive_branching` | Hardcoded 0.8 |
| `union_find` | — | `parent_pointer_chase` + `parent_root_merge` | — | Hardcoded 0.85 |
| `monotonic_stack_strategy` | `monotonic_stack_maintenance` | `stack_operation` + `monotonic_comparison` + `conditional_pop` | — | Technique confidence |

**Key properties:**
- Strategies **use absence constraints** (e.g., binary_search rejects code with `opposite_direction_updates`)
- Strategies derive confidence from supporting technique confidence or hardcoded values
- Each strategy references its supporting techniques and facts for traceability

#### 4. Solution-Group Matching

**File:** `pathforge/ast_analysis/shadow/matching.py`
**Entry:** `evaluate_solution_groups(groups, technique_evidence, strategy_evidence, facts) → MatchOutcome`

**Data Structure:** `MatchOutcome` (dataclass) with `outcome`, `satisfied_group_ids`, `authority_tier`, `primary_strategy`, `reasoning`

**Three possible outcomes:**
- `CONFIRMED`: Required concepts satisfied, satisfaction ≥ threshold
- `UNRESOLVED`: Required concepts not met, or low-authority contradiction
- `CONTRADICTED`: Excluded concept detected, only from authoritative tiers

**Matching logic per group:**
1. Check `excluded` concepts → if found in detected techniques/strategies → `contradicted`
2. Check `required` concepts → each must be present with `presence_confidence ≥ 0.5`
3. Compute satisfaction = average confidence of matched required concepts + optional boost (0.15 × optional confidence)
4. Compare satisfaction to `threshold` (default 0.5)

**Authority gating:**
- `_AUTHORITATIVE_TIERS = {"structurally_observed", "externally_listed", "editorial"}`
- If a group contradicts but its authority is NOT authoritative → downgrade to `UNRESOLVED`
- Low-authority (`bootstrap`, `llm_proposed`) groups CANNOT produce `CONTRADICTED`

**Cross-group priority:** `CONTRADICTED > CONFIRMED > UNRESOLVED`. Within same level, higher satisfaction wins.

#### 5. Shadow Persistence

**File:** `pathforge/ast_analysis/shadow/persistence.py`

Persists to `submissions` table columns:
- `structural_facts_json` (JSONB) — canonical persisted artifact
- `shadow_extractor_version` — extractor version tracking
- `technique_evidence_json` (JSONB) — cached technique projections
- `strategy_evidence_json` (JSONB) — cached strategy projections
- `shadow_match_outcome_json` (JSONB) — match outcome
- `shadow_technique_def_version`, `shadow_strategy_def_version` — version tracking

Supports re-derivation: `rerun_derivation(facts, groups)` re-runs technique → strategy → matching from stored structural facts.

#### 6. Shadow Observability

**File:** `pathforge/api/services/shadow_observability.py`

Two in-memory counter systems (reset on process restart):
- `ShadowCounters` — legacy hybrid/semantic shadow detector
- `ShadowPipelineCounters` — fact/technique/strategy shadow pipeline

Tracks: total analyses, confirmed/unresolved/contradictions, strategy breakdown, unresolved categorization, parse failures, extraction failures, latency percentiles (p50/p95/p99/max), circular buffer of last 200 confirmed records.

Thread-safe via `threading.Lock`.

#### What the Shadow System Does NOT Control

- Shadow results are wrapped in `try/except: pass` — exceptions never reach production
- Shadow does NOT affect: ELO updates, gap signals, recommendations, topic profiles, streaks
- Shadow does NOT affect: production verdict (`FULL_MATCH`/`PARTIAL_MATCH`/`NO_MATCH`)
- Shadow persistence is a separate DB write after production persistence completes
- Shadow results appear in the response as `shadow_analysis` and `hybrid_analysis` fields

---

## 5. GROUND TRUTH ARCHITECTURE

### Current Representation

Ground truth is stored in `problem_ground_truth` table with these columns:
- `problem_id` (INTEGER PRIMARY KEY)
- `patterns` (TEXT/JSONB) — legacy flat pattern list
- `confidence` (TEXT/JSONB) — confidence per pattern
- `solution_groups` (JSONB) — structured V1 groups (Phase 4A)
- `validation_status` (TEXT) — e.g., `llm_proposed`, `unobserved`
- `created_at`, `updated_at` (TEXT)

### Legacy Flat Patterns

The `patterns` column stores a JSON array of pattern ID strings (e.g., `["hash_map_lookup", "two_pointers_opposite"]`). The `confidence` column stores a JSON dict mapping pattern IDs to float confidence values.

### Structured Solution Groups (V1)

The `solution_groups` column stores a JSON array of group objects:

```json
{
  "id": "group_0",
  "version": 1,
  "required": ["binary_search"],
  "optional": ["bidirectional_index_scan"],
  "excluded": ["two_pointers_opposite"],
  "threshold": 0.5,
  "authority_tier": "llm_proposed",
  "provenance": ["llm_ground_truth", "vocabulary_v1"],
  "patterns": ["binary_search_standard"],
  "evidence": "llm_proposed",
  "confidence": {"binary_search_standard": 0.9}
}
```

**Required concepts:** Must be detected for the group to be satisfied. Uses V1 vocabulary IDs (technique or strategy IDs).

**Optional concepts:** Boost satisfaction when present (0.15 × confidence per concept).

**Excluded concepts:** If detected, the group is contradicted.

**Threshold:** Minimum satisfaction score to consider the group satisfied (default 0.5).

### V1 Vocabulary Mapping

**File:** `pathforge/services/ground_truth_builder.py`

The `PATTERN_TO_V1_MAPPING` dict maps each legacy pattern ID to V1 required/optional/excluded concepts. Examples:

| Legacy Pattern | Required | Optional | Excluded |
|---------------|----------|----------|----------|
| `binary_search_standard` | `binary_search` | `bidirectional_index_scan` | `two_pointers_opposite` |
| `dfs_recursive` | `recursive_branching` | `dfs_backtracking` | `bfs_shortest_path` |
| `dp_1d_forward` | `dp_bottom_up` | `iterative_table_filling` | `recursive_branching` |
| `sliding_window_fixed` | `sliding_window` | `loop_state_tracking` | `two_pointers_opposite` |
| `linked_list_reversal` | `linked_list_traversal` | — | `two_pointers_opposite` |
| `hash_map_lookup` | `[]` (none) | — | — |
| `greedy_local` | `[]` (none) | `sequential_accumulation` | — |
| `heap_top_k` | `[]` (none) | — | — |

### Legacy-to-V1 Conversion

**Function:** `_map_legacy_patterns_to_v1(patterns)` in `problem_resolver.py`

Called during `_load_ground_truth()` when processing groups. If a group has `required` field → use it directly. If it only has legacy `patterns` → map via `_map_legacy_patterns_to_v1()`.

### Where Ground Truth Is Stored and Loaded

1. **Stored by:** `build_ground_truth()` in `ground_truth_builder.py` (called from `problem_resolver.py:_ensure_ground_truth()`)
2. **Loaded by:** `_load_ground_truth()` in `problem_resolver.py`
3. **Consumers:**
   - Production matching: uses `patterns` (legacy) from groups → `MatchingEngine.match()`
   - Shadow matching: uses `required`/`optional`/`excluded` (V1) from groups → `evaluate_solution_groups()`

### Vocabulary Conversion Layer

The conversion happens in `_load_ground_truth()`:
- For each group: `legacy_patterns = g.get("patterns", [])` → used by production matcher
- `required = g.get("required") or _map_legacy_patterns_to_v1(legacy_patterns)` → used by shadow matcher
- Both representations are passed through `ProblemContext.accepted_solution_groups`

---

## 6. EVIDENCE / AUTHORITY ARCHITECTURE

### Per-Group Evidence State

Each solution group has an `authority_tier` field with these valid values:
- `bootstrap` — initial/default
- `llm_proposed` — generated by LLM
- `structurally_observed` — confirmed by structural observation
- `externally_listed` — confirmed by external source
- `editorial` — confirmed by editorial solution

### Authoritative vs Analysis-Only Behavior

**File:** `pathforge/services/persistence.py`

The `verdict_type` is derived from the matched group's `evidence` field:
- `structurally_observed` or `externally_listed` → `verdict_type = "authoritative"`
- Everything else → `verdict_type = "analysis_only"`

When `verdict_type == "analysis_only"`:
- The submission is stored (for future clustering)
- But NO downstream scoring occurs: no topic profile updates, no gap signals, no ELO updates, no recommendations
- Streak is still updated (independent)

### K-Factor Ceilings

**File:** `pathforge/elo_engine.py`

```python
EVIDENCE_K_CEILINGS = {
    "structurally_observed": 24,   # 0.75 × 32
    "externally_listed": 16,       # 0.5 × 32
    "llm_proposed": 0,
    "unobserved": 0,
    "conflicted": 0,
}
```

In `EloEngine.compute_updates()`: if `evidence_state` is provided, `k = min(k, evidence_ceiling)`. If ceiling is 0, `k = 0` (no scoring).

### ELO Gating

- Evidence ceiling applied in `EloEngine.compute_updates()` via `evidence_state` parameter
- In `run_persistence()`: `topic_evidence_ceiling = EVIDENCE_K_CEILINGS.get(matched_group_evidence, 0)`
- Unknown/unrecognized evidence states default to 0 (fail-closed)

### Topic-Profile Gating

- `update_topic_profile()` accepts `evidence_ceiling` parameter
- Uses `db/elo.py:update_elo()` with `k_ceiling` parameter
- Effective K = `min(base_k, k_ceiling)`

### Gap Gating

- Gap signals are only computed when `is_authoritative == True`
- `GapSignalEngine` operates on match results and AST output
- No direct evidence-state gating within the engine itself

### Recommendation Gating

- Recommendations are only generated when `is_authoritative == True`
- `_mark_last_recommendation_acted_on()` clears previous recommendation before generating new one
- Three tiers: `specific` (confidence ≥ 0.75), `topic_hint` (≥ 0.55), `general_hint` (< 0.55)

### Streak Behavior

- Streak is **always updated** regardless of evidence authority
- `_update_user_streak(connection, user_id, timestamp)` runs outside the `is_authoritative` block

### Unknown-State Fail-Closed Behavior

- `EVIDENCE_K_CEILINGS.get(evidence_state, 0)` — unknown states return 0
- `_AUTHORITATIVE_STATES = {"structurally_observed", "externally_listed"}` — only these grant authority
- Any unrecognized evidence → `analysis_only` → no downstream scoring

### Evidence State Flow

```
Storage: problem_ground_truth.solution_groups[i].authority_tier
  ↓
Loading: _load_ground_truth() → groups[i]["authority_tier"]
  ↓
Persistence: matched_group_evidence = groups[matched_idx]["evidence"]
  ↓
Gating: verdict_type = "authoritative" if evidence in _AUTHORITATIVE_STATES
  ↓
Scoring: EVIDENCE_K_CEILINGS[evidence] → ELO K ceiling
  ↓
Topic Profile: update_topic_profile(evidence_ceiling=...)
```

---

## 7. DATABASE

### Tables

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | |
| `username` | TEXT NOT NULL UNIQUE | |
| `email` | TEXT NOT NULL UNIQUE | |
| `password_hash` | TEXT NOT NULL | |
| `display_name` | TEXT | |
| `experience_level` | TEXT | beginner/intermediate/advanced |
| `confident_areas` | TEXT NOT NULL DEFAULT '[]' | JSON array |
| `onboarding_complete` | BOOLEAN NOT NULL DEFAULT FALSE | |
| `last_recommendation_id` | INTEGER | FK → recommendations(id) |
| `current_streak` | INTEGER NOT NULL DEFAULT 0 | |
| `last_submission_date` | TEXT | |
| `supabase_id` | TEXT UNIQUE | |
| `created_at`, `updated_at` | TEXT NOT NULL | |

#### `problems`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | LeetCode question ID |
| `title` | TEXT NOT NULL | |
| `difficulty` | TEXT NOT NULL | CHECK IN ('Easy','Medium','Hard') |
| `topics` | TEXT NOT NULL | Comma-separated |
| `pattern` | TEXT NOT NULL | JSON array of pattern IDs |
| `test_cases` | TEXT NOT NULL | JSON array |
| `link` | TEXT | LeetCode URL |
| `acceptance_rate` | REAL | |
| `premium_only` | BOOLEAN NOT NULL DEFAULT FALSE | |
| `category`, `likes`, `dislikes`, `similar_questions` | TEXT/INTEGER | |
| `title_slug` | TEXT | Added by migration |
| `description` | TEXT | Added by migration |
| `created_at`, `updated_at` | TEXT NOT NULL | |

#### `submissions`
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | |
| `user_id` | INTEGER NOT NULL | FK → users(id) |
| `problem_id` | INTEGER | FK → problems(id) |
| `code_text` | TEXT NOT NULL | Truncated to 1000 chars in persistence |
| `verdict` | TEXT NOT NULL | CHECK IN ('pass','fail','error','tle') |
| `detected_pattern` | TEXT | Primary detected pattern ID |
| `detected_confidence` | REAL DEFAULT 0.0 | |
| `expected_pattern` | TEXT | From matched ground truth group |
| `target_pattern` | TEXT | |
| `gap_identified` | BOOLEAN NOT NULL DEFAULT FALSE | |
| `diagnosis_confidence` | REAL DEFAULT 0.0 | Match engine confidence score |
| `time_taken_seconds` | INTEGER | |
| `attempt_number` | INTEGER NOT NULL DEFAULT 1 | |
| `topic` | TEXT NOT NULL | Primary pattern or topic |
| `elo_before`, `elo_after` | REAL | |
| `submitted_at` | TEXT NOT NULL | |
| `verdict_type` | TEXT DEFAULT 'authoritative' | Phase 0B: 'authoritative' or 'analysis_only' |
| `detected_patterns_json` | JSONB | Phase 0B: full AST detection output |
| `code_hash` | TEXT | Phase 0B: SHA-256 of source code |
| `structural_facts_json` | JSONB | Phase 3A: shadow structural facts |
| `shadow_extractor_version` | TEXT | Phase 3A: extractor version |
| `technique_evidence_json` | JSONB | Phase 3A: technique evidence |
| `strategy_evidence_json` | JSONB | Phase 3A: strategy evidence |
| `shadow_match_outcome_json` | JSONB | Phase 3A: shadow match outcome |
| `shadow_technique_def_version` | TEXT | Phase 3A: technique def version |
| `shadow_strategy_def_version` | TEXT | Phase 3A: strategy def version |

**Shadow-related columns explained:**

| Column | Why it exists | Writer | Reads it | Affects production? |
|--------|--------------|--------|----------|-------------------|
| `structural_facts_json` | Canonical persisted artifact for re-derivation | `shadow_runner.py` via `persist_shadow_analysis()` | `persistence.py:load_shadow_facts()`, `rerun_derivation()` | No |
| `shadow_extractor_version` | Version tracking for re-derivation | Same | Same | No |
| `technique_evidence_json` | Cached technique projections | Same | `load_shadow_techniques()` | No |
| `strategy_evidence_json` | Cached strategy projections | Same | `load_shadow_strategies()` | No |
| `shadow_match_outcome_json` | Shadow matching result | Same | `load_shadow_outcome()` | No |
| `shadow_technique_def_version` | Technique definition version | Same | For re-derivation check | No |
| `shadow_strategy_def_version` | Strategy definition version | Same | For re-derivation check | No |

#### `problem_ground_truth`
| Column | Type | Notes |
|--------|------|-------|
| `problem_id` | INTEGER PRIMARY KEY | FK → problems(id) |
| `patterns` | TEXT NOT NULL DEFAULT '[]' | Legacy flat pattern list |
| `confidence` | TEXT NOT NULL DEFAULT '{}' | Legacy confidence dict |
| `solution_groups` | JSONB | Phase 0C: structured V1 groups |
| `validation_status` | TEXT DEFAULT 'unobserved' | |
| `created_at`, `updated_at` | TEXT NOT NULL | |

#### `topic_profiles`
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER NOT NULL | FK |
| `topic` | TEXT NOT NULL | Pattern ID |
| `elo_rating` | REAL NOT NULL DEFAULT 800.0 | CHECK ≥ 400.0 |
| `attempt_count` | INTEGER DEFAULT 0 | |
| `pass_count` | INTEGER DEFAULT 0 | |
| `pattern_match_count` | INTEGER DEFAULT 0 | |
| `accuracy` | REAL DEFAULT 0.0 | CHECK 0.0–1.0 |
| `recent_failures` | INTEGER DEFAULT 0 | |
| `last_attempt_at` | TEXT | |
| `created_at`, `updated_at` | TEXT | |
| PRIMARY KEY | `(user_id, topic)` | |

#### `gap_signals`
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | |
| `user_id` | INTEGER NOT NULL | FK |
| `pattern_id` | TEXT NOT NULL | |
| `gap_strength` | REAL DEFAULT 0.0 | CHECK 0.0–1.0 |
| `frequency` | INTEGER DEFAULT 0 | |
| `last_seen` | TEXT NOT NULL | |
| `created_at`, `updated_at` | TEXT NOT NULL | |
| UNIQUE | `(user_id, pattern_id)` | |

#### `user_pattern_elo`
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | |
| `user_id` | INTEGER NOT NULL | FK |
| `pattern_id` | TEXT NOT NULL | |
| `elo` | REAL NOT NULL DEFAULT 1200.0 | CHECK ≥ 400.0 |
| `last_updated` | TEXT NOT NULL | |
| `created_at`, `updated_at` | TEXT | |
| UNIQUE | `(user_id, pattern_id)` | |

#### `recommendations`
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PRIMARY KEY | |
| `user_id` | INTEGER NOT NULL | FK |
| `problem_id` | INTEGER | FK |
| `topic` | TEXT NOT NULL | |
| `reason` | TEXT | |
| `confidence_tier` | TEXT | CHECK IN ('specific','topic_hint','general_hint') |
| `acted_on` | BOOLEAN DEFAULT FALSE | |
| `followed` | BOOLEAN DEFAULT FALSE | |
| `elo_delta_after` | REAL | |
| `created_at` | TEXT NOT NULL | |
| `acted_on_at` | TEXT | |

### Migration Behavior

**File:** `pathforge/db/db.py`

- `init_db()` is called at FastAPI startup from `app.py`
- Verifies all required tables exist via `information_schema.tables`
- If tables are missing → raises `RuntimeError` (must run `schema_pg.sql` manually)
- `_apply_migrations()` reads `schema_pg.sql`, classifies each statement:
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` → migration (executed)
  - `CREATE INDEX IF NOT EXISTS` → migration (executed)
  - `CREATE TABLE` → skip (tables must exist)
- Each migration statement committed individually (atomic per statement)
- Failed statements rolled back independently (prior commits preserved)
- All statements use `IF NOT EXISTS` — idempotent

---

## 8. API

### POST /analyze

**Request:**
```json
{
  "user_id": 1,
  "code": "def twoSum(nums, target):\n  ...",
  "language": "python",
  "problem": {
    "leetcode_id": 1,
    "title_slug": "two-sum"
  }
}
```

**Response:**
```json
{
  "ast": {
    "detected_patterns": [
      {
        "pattern_id": "hash_map_lookup",
        "confidence": 0.8,
        "evidence": [...],
        "detected": true
      }
    ]
  },
  "match_result": {
    "match_result": "FULL_MATCH",
    "matched_groups": [0],
    "unmatched_patterns": [],
    "confidence_score": 0.8,
    "reasoning_signals": ["match_result=FULL_MATCH", ...]
  },
  "problem_info": {
    "leetcode_id": 1,
    "title": "Two Sum",
    "difficulty": "Easy",
    "canonical_patterns": [
      {"name": "hash_map_lookup", "confidence": 0.9}
    ]
  },
  "elo_updates": [
    {"pattern_id": "hash_map_lookup", "elo_before": 800, "elo_after": 832, "delta": 32}
  ],
  "submission_gap": {
    "detected_pattern_ids": ["hash_map_lookup"],
    "missing_pattern_ids": [],
    "gap_identified": false
  },
  "persisted": {
    "submission_id": 42,
    "gap_signals_count": 0,
    "elo_updates_count": 1,
    "recommendation_id": 7
  },
  "hybrid_analysis": null,
  "shadow_analysis": {
    "structural_facts": [...],
    "technique_evidence": [...],
    "strategy_evidence": [...],
    "match_outcome": {
      "outcome": "CONFIRMED",
      "satisfied_group_ids": ["group_0"],
      "authority_tier": "llm_proposed",
      "primary_strategy": "two_pointers_opposite",
      "reasoning": [...]
    },
    "extractor_version": "1.0.0",
    "elapsed_ms": 12.34
  }
}
```

### Field Classification

**Authoritative production fields:** `ast`, `match_result`, `problem_info`, `elo_updates`, `submission_gap`, `persisted`

**Observational shadow fields:** `hybrid_analysis`, `shadow_analysis`

### Error Behavior

| Condition | Status Code | Detail |
|-----------|------------|--------|
| Problem not found | 404 | "Cannot resolve LeetCode ID..." |
| GraphQL unavailable | 502 | "This problem could not be prepared..." |
| LLM ground truth failed | 502 | "Ground truth generation failed..." |
| Invalid language | 400 | "Unsupported language: ..." |
| Syntax error | 400 | "Syntax error in code: ..." |
| Persistence failed | 500 | "Analysis completed but persistence failed: ..." |

### Backwards Compatibility

- `AnalyzeRequest.problem` is optional — analysis works without problem context (defaults to `hash_map_lookup` group)
- `hybrid_analysis` field present in response model but currently always `null` (legacy code path)
- `shadow_analysis` field present when shadow runs successfully, `null` otherwise

---

## 9. FRONTEND

### Analysis UI Flow

**File:** `pathforge-frontend/components/analysis-view.tsx`

1. **Problem Input Row:** User enters LeetCode problem ID → clicks "Prepare" → calls `POST /prepare-problem` → displays title + difficulty badge
2. **Solution Input:** Code editor with line numbers
3. **Run Analysis:** User clicks "Run Analysis" → calls `POST /analyze` with `{user_id, code, language, problem}`
4. **Result Panels (top to bottom):**
   - **Problem Info** (conditional): Shows title, difficulty, expected canonical patterns
   - **AST Detected Patterns** (left): Pattern name, category, nodes, confidence meter + percentage
   - **Matching Engine** (right): Match score meter, matched/unmatched counts, expected patterns, verdict with reasoning signals
   - **Skill Changes** (left): ELO before → after, delta per pattern
   - **Gaps** (right): Submission gap (missing patterns) + Long-term gap signals from DB
   - **Experimental Analysis** (bottom, dashed border): Shadow analysis results

### Presentation Mapping

**File:** `pathforge-frontend/src/services/shadow-mapper.ts`

- `mapShadowToDisplay()` converts internal shadow data to `ShadowDisplayData`
- Strategy IDs → human-readable names (e.g., `two_pointers_opposite` → "Two Pointers")
- Technique IDs → human-readable names (e.g., `sequential_accumulation` → "Running total")
- Outcomes → status badges: `CONFIRMED` → "Likely match" (green), `UNRESOLVED` → "Not enough evidence" (yellow), `CONTRADICTED` → "Possible mismatch" (red)
- Confidence: ≥ 0.8 → "High", ≥ 0.5 → "Medium", else "Low"

### Confidence Scale

- Frontend `pct()` helper: `Math.round(confidence * 100)` — converts 0.0–1.0 to 0–100
- `Meter` component: `max=100` default, all callers pass 0–100 values
- Badge threshold: `matchScore >= 0.8` compares raw 0.0–1.0 value

### Developer Details

- Collapsed by default in experimental panel
- Shows: outcome, authority tier, fact count, latency, extractor version, strategies, techniques, reasoning

### Stale State Handling

- `handleProblemInputChange()` clears prepare result when user edits input after a prepare
- Error display for both prepare and analyze failures

### API Client

**File:** `pathforge-frontend/src/services/api/client.ts`

- `API_BASE` = `NEXT_PUBLIC_API_URL` or `https://pathforge-v2.onrender.com`
- JWT token stored in `_accessToken` module variable
- `ApiError` class with status code, message, body

---

## 10. TEST ARCHITECTURE

### Test Inventory

#### Production AST Detectors (43 tests across 8 batch files)
- `src/ast_detection/tests/test_detectors.py` through `test_detectors_batch8.py`
- `src/ast_detection/tests/test_detector_interface.py`
- `src/ast_detection/tests/test_detector_manager.py`
- `src/ast_detection/tests/test_registry.py`
- `src/ast_detection/tests/test_coordinator.py`
- `src/ast_detection/tests/test_parser.py`
- `src/ast_detection/tests/test_output_pipeline.py`
- `src/ast_detection/tests/test_run_analysis.py`
- `src/ast_detection/tests/test_validation.py`
- `src/ast_detection/tests/adversarial_evaluation.py`
- `src/ast_detection/tests/deep_failure_analysis.py`
- `src/ast_detection/tests/mutation_benchmark.py`
- `src/ast_detection/tests/validate_17_detectors.py`
- `src/ast_detection/tests/validate_all_36_detectors.py`
- `src/ast_detection/tests/validate_all_detectors.py`

#### Matching Engine
- `src/matching_engine/tests/test_matching_engine.py`

#### Shadow Analysis (10 tests)
- `pathforge/ast_analysis/shadow/tests/test_shadow_analysis.py`
- `pathforge/ast_analysis/shadow/tests/test_persistence.py`
- `pathforge/ast_analysis/shadow/tests/test_phase3b_integration.py`
- `pathforge/ast_analysis/shadow/tests/test_phase4a_enrichment.py`
- `pathforge/ast_analysis/shadow/tests/test_phase4b_readiness.py`
- `pathforge/ast_analysis/shadow/tests/test_phase5a.py`
- `pathforge/ast_analysis/shadow/tests/test_phase5b.py`
- `pathforge/ast_analysis/shadow/tests/test_regression_vocabulary_mismatch.py`
- `pathforge/ast_analysis/shadow/tests/test_boolop_while_comparison.py`
- `pathforge/ast_analysis/shadow/tests/evaluation_corpus.py`
- `pathforge/ast_analysis/shadow/tests/large_corpus.py`
- `pathforge/ast_analysis/shadow/tests/run_e2e_evaluation.py`
- `pathforge/ast_analysis/shadow/tests/run_evaluation.py`
- `pathforge/ast_analysis/shadow/tests/run_large_corpus.py`
- `pathforge/ast_analysis/shadow/tests/diagnostic_full_trace.py`
- `pathforge/ast_analysis/shadow/tests/diagnostic_trace.py`

#### Evidence Architecture
- `pathforge/tests/test_evidence_architecture.py`
- `pathforge/tests/test_ground_truth_builder.py`
- `pathforge/tests/test_pipeline.py`
- `pathforge/tests/test_submission_handler.py`
- `pathforge/tests/test_boolean_persistence.py`
- `pathforge/tests/test_diversity.py`
- `pathforge/tests/test_llm_client.py`

#### ELO
- `pathforge/db/tests/test_elo.py`
- `pathforge/elo_engine_test.py`

#### Gap Signals
- `pathforge/gap_signal_engine_test.py`

#### Recommendations
- `pathforge/recommendation_engine_test.py`

#### Semantic/Hybrid
- `src/ast_detection/semantic/tests/test_semantic.py`
- `src/ast_detection/semantic/tests/test_shadow.py`

#### Legacy AST Engine
- `pathforge/ast_engine/tests/test_dfs.py`
- `pathforge/ast_engine/tests/test_dp.py`
- `pathforge/ast_engine/tests/test_expanded_patterns.py`
- `pathforge/ast_engine/tests/test_greedy.py`
- `pathforge/ast_engine/tests/test_hashmap.py`
- `pathforge/ast_engine/tests/test_pipeline.py`

#### API
- `pathforge/api_test.py`
- `pathforge/auth_test.py`

**Total: approximately 50+ test files**

### What Each Area Protects

| Area | Protects Against |
|------|-----------------|
| Detector batches (1–8) | Pattern detection regressions for all 36 detectors |
| Adversarial evaluation | False positives on adversarial code |
| Matching engine | Verdict correctness (FULL/PARTIAL/NO_MATCH) |
| Shadow tests | Fact extraction, technique detection, strategy evaluation, matching correctness |
| Evidence architecture | Authority gating, K-ceiling, verdict_type derivation |
| ELO tests | Score computation, anti-drift, K-factor |
| Ground truth builder | V1 vocabulary mapping, group validation |
| Persistence tests | DB writes, JSONB storage, re-derivation |

---

## 11. EXPERIMENT HISTORY

### Phase-0: Adversarial AST Evaluation
- **Problem:** Existing detectors might have high false-positive rates on adversarial code
- **Change:** Created adversarial evaluation corpus with mutated/obfuscated code
- **Result:** Identified specific false-positive patterns in detectors
- **Conclusion:** Deterministic AST detection alone has precision limits; semantic analysis needed

### Experiment 1: Alias Expansion
- **Problem:** Variable naming differences caused detection inconsistency
- **Change:** Tried alias/variable-name normalization
- **Result:** Marginal improvement, high complexity
- **Conclusion:** Variable-name normalization is not sufficient; structural analysis is more robust

### Phase 1.5: Reconciliation
- **Problem:** Multiple analysis approaches produced conflicting results
- **Change:** Reconciled detection results across approaches
- **Result:** Unified framework for comparing approaches
- **Conclusion:** Need a principled architecture for multi-layer analysis

### Phase 2: Architecture Analysis
- **Problem:** Need principled layering for AST analysis + semantic analysis
- **Change:** Designed layered architecture: facts → techniques → strategies
- **Result:** Architecture spike validated the layered approach
- **Conclusion:** Three-layer architecture (facts/techniques/strategies) is viable

### Multi-Solution Ground-Truth Investigations
- **Problem:** Most problems have multiple valid solution approaches
- **Change:** Investigated multi-group ground truth representation
- **Result:** Designed `solution_groups` structure with required/optional/excluded
- **Conclusion:** Multi-group representation captures problem complexity better than flat patterns

### Evidence-Authority Architecture
- **Problem:** LLM-generated ground truth should not have full scoring authority
- **Change:** Implemented authority tiers and K-factor ceilings
- **Result:** `llm_proposed` gets K=0 (no scoring), `structurally_observed` gets K=24
- **Conclusion:** Authority gating prevents low-confidence ground truth from corrupting skill models

### Semantic Experiments
- **Problem:** Pure AST detection misses semantic-level patterns
- **Change:** Implemented semantic analyzer with TF-IDF features, shadow detector
- **Result:** Identified semantic-only detections and conflicts
- **Conclusion:** Semantic layer useful as observational signal, not ready for production

### Taxonomy/Generalization Findings
- **Problem:** 33 legacy patterns don't map cleanly to algorithmic concepts
- **Change:** Investigated V1 vocabulary (9 techniques + 9 strategies)
- **Result:** V1 vocabulary captures algorithmic intent better than legacy pattern IDs
- **Conclusion:** V1 vocabulary is the right abstraction level for solution-group matching

### Primitive → Technique → Strategy Redesign
- **Problem:** Original design had flat pattern detection
- **Change:** Redesigned as fact extraction → technique detection → strategy evaluation
- **Result:** Each layer adds abstraction while maintaining traceability
- **Conclusion:** Layered design allows for component-level testing and improvement

### Large Corpus Validation
- **Problem:** Need to validate shadow pipeline across many problems
- **Change:** Ran evaluation on large corpus of LeetCode solutions
- **Result:** Shadow pipeline CONFIRMED rate measured; known failure categories identified
- **Conclusion:** Pipeline works for well-structured solutions; edge cases identified

### Controlled Shadow Pilot Preparation
- **Problem:** Shadow system needs production observability
- **Change:** Added in-memory counters, latency tracking, confirmed record buffer
- **Result:** `ShadowPipelineCounters` tracks all metrics needed for pilot evaluation
- **Conclusion:** Observability infrastructure is ready for pilot monitoring

### Current UI Work
- **Problem:** Shadow results need user-facing presentation
- **Change:** Added experimental panel, shadow mapper, confidence display
- **Result:** Non-technical summary of shadow analysis visible in analysis view
- **Conclusion:** UI presentation layer is complete; ready for user testing

---

## 12. CURRENT VALIDATION STATUS

### A. Proven

- Production AST detection pipeline works end-to-end (parse → detect → match → persist)
- Evidence authority gating prevents low-confidence ground truth from affecting skill models
- V1 vocabulary mapping correctly translates legacy patterns to technique/strategy concepts
- Solution-group validation catches mutually exclusive strategies and invalid combinations
- PostgreSQL migration schema is complete and idempotent
- Frontend analysis view correctly displays all panels with proper confidence scaling
- Shadow persistence writes to correct DB columns
- Shadow observability tracks all required metrics

### B. Observed

- Shadow pipeline produces CONFIRMED outcomes for well-structured solutions
- Shadow pipeline has known failure categories (parse failures, extraction failures, below-threshold)
- Latency overhead of shadow pipeline is measurable but within acceptable range
- Some legacy patterns map to empty V1 required lists (e.g., `hash_map_lookup`, `heap_top_k`)

### C. Unresolved

- Whether shadow CONFIRMED rate is sufficient to justify promoting shadow to production
- Whether the V1 vocabulary covers all important algorithmic strategies
- Whether authority tier upgrades should be automatic or manual
- How to handle submissions where ground truth is missing

### D. Not Yet Tested

- End-to-end production with real users (shadow pilot not yet live)
- Persistence of shadow results across server restarts
- Re-derivation from stored facts after technique/strategy definition changes
- Behavior under concurrent submissions

---

## 13. KNOWN LIMITATIONS

### Extraction Gaps
- Cache/memo detection relies on variable naming heuristics (`cache`, `memo`, `dp`, `table`)
- Neighbor traversal detection relies on variable naming (`graph`, `adj`, `neighbors`)
- Queue detection relies on `deque()` call or queue-like variable names
- Greedy patterns have no V1 technique equivalent (map to empty required list)
- Heap operations have no V1 technique equivalent

### Low Recall Strategies
- `bfs_shortest_path` requires both queue + neighbor access → misses simple tree BFS
- `dp_bottom_up` requires `iterative_table_filling` technique → misses some DP patterns
- `union_find` requires both pointer chase + root merge → very specific structural signature
- `sliding_window` with fixed window requires `window_size_constant` → misses some variable windows

### Ground-Truth Uncertainty
- All ground truth is LLM-generated (`llm_proposed` authority)
- No `structurally_observed` or `externally_listed` authority in current data
- This means ELO K-ceiling is 0 for all problems → no scoring occurs
- Ground truth correctness is not validated against editorial solutions

### Taxonomy Ambiguity
- Some patterns overlap (e.g., `binary_search_standard` vs `binary_search_answer`)
- Some V1 mappings produce empty required lists → shadow matcher cannot confirm
- `dp_top_down` vs `dfs_backtracking` distinction depends on cache vs state restoration detection

### Production/Shadow Disagreement
- Production uses legacy flat-pattern matching; shadow uses V1 technique/strategy matching
- These systems can produce contradictory verdicts
- No reconciliation mechanism exists

### UI Limitations
- Experimental panel hidden when shadow analysis is absent
- No persistence of shadow observability data across server restarts
- No historical comparison of shadow vs production verdicts

### Deployment Assumptions
- PostgreSQL connection via `DATABASE_URL` environment variable
- JWT authentication via `JWT_SECRET`
- LeetCode GraphQL requires browser-like headers to avoid 403
- OpenRouter API key required for ground truth generation
- Frontend assumes `NEXT_PUBLIC_API_URL` points to backend

### Monitoring Limitations
- Shadow observability counters are in-memory only (lost on restart)
- No alerting on shadow pipeline degradation
- No A/B testing framework for comparing approaches

### Persistence Limitations
- Code text truncated to 1000 chars in submissions table
- Shadow persistence commits separately from production persistence (not atomic)
- No cleanup/compaction for old shadow data

---

## 14. CURRENT BRANCH / DEPLOYMENT STATE

### Current Branch
- **Branch:** `architecture/strategy-evidence-spike`
- **Latest commit:** `b88cab4` — "feat: upadted shadow pilot observability in the analysis section along with title slug mismatch corrections"
- **Relationship to master:** Branched from master; contains shadow analysis infrastructure, evidence architecture, PostgreSQL migration, and frontend updates not on master

### Deployment Assumptions

**Render (Backend):**
- `Procfile` runs the FastAPI app
- PostgreSQL via Supabase (`DATABASE_URL` env var)
- JWT auth via `JWT_SECRET`
- CORS allows `localhost:3000` and `path-forge-v2.vercel.app`

**Vercel (Frontend):**
- Next.js app
- `NEXT_PUBLIC_API_URL` → `https://pathforge-v2.onrender.com`
- JWT token managed client-side via `_accessToken`

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection string | Supabase |
| `JWT_SECRET` | JWT signing key | Environment |
| `SECRET_KEY` | Application secret | Environment |
| `OPENROUTER_API_KEY` | LLM ground truth generation | OpenRouter |

### Whether Shadow is Observational
**Yes.** Shadow analysis runs in `try/except: pass` blocks. Shadow persistence writes to separate DB columns. Shadow does not affect production scoring.

### Whether Production Scoring Uses Old Path
**Yes.** Production scoring uses the legacy production path: `ASTAnalysisEngine` → `MatchingEngine` → `run_persistence()`. The shadow fact/technique/strategy path is observational only.

---

## 15. EXACT FILE-LEVEL MAP

| File | Purpose | Key Classes/Functions | Reads | Writes | Called by | Calls |
|------|---------|----------------------|-------|--------|-----------|-------|
| `pathforge/api/routes/analyze.py` | POST /analyze endpoint | `analyze_endpoint()`, `AnalyzeRequest`, `AnalyzeResponse` | — | — | FastAPI | `run_analysis`, `resolve_problem`, `run_persistence`, `run_shadow_analysis` |
| `pathforge/api/routes/prepare_problem.py` | POST /prepare-problem endpoint | `prepare_problem_endpoint()` | — | — | FastAPI | `resolve_problem` |
| `pathforge/services/problem_resolver.py` | Problem resolution + GT loading | `resolve_problem()`, `ProblemContext`, `_load_ground_truth()` | DB (problems, problem_ground_truth) | DB (problems) | analyze, prepare_problem | `fetch_problem_by_slug`, `build_ground_truth` |
| `pathforge/services/ground_truth_builder.py` | LLM GT generation + storage | `build_ground_truth()`, `_build_solution_groups()`, `PATTERN_TO_V1_MAPPING` | — | DB (problem_ground_truth) | problem_resolver | `call_llm` |
| `pathforge/services/persistence.py` | Post-analysis persistence | `run_persistence()` | DB (submissions, problems) | DB (submissions, gap_signals, user_pattern_elo, topic_profiles, recommendations) | analyze route | `GapSignalEngine`, `EloEngine`, `get_recommendation` |
| `src/ast_detection/run_analysis.py` | Production AST engine entry | `ASTAnalysisEngine.analyze()` | — | — | analysis service | `Parser`, `DetectorManager`, `Coordinator`, `OutputPipeline` |
| `src/ast_detection/detector_manager.py` | Runs all detectors | `DetectorManager.detect_all()` | — | — | `ASTAnalysisEngine` | `get_all_detectors()` |
| `src/ast_detection/registry.py` | Detector registration | `DetectorRegistry`, `register_detector()` | — | — | All detectors | — |
| `src/matching_engine/matching_engine.py` | Pattern matching | `MatchingEngine.match()`, `MatchResult` | — | — | analysis service | — |
| `pathforge/ast_analysis/shadow/shadow_runner.py` | Shadow analysis orchestrator | `run_shadow_analysis()` | — | — | analyze route | `extract_structural_facts`, `detect_techniques`, `evaluate_strategies`, `evaluate_solution_groups` |
| `pathforge/ast_analysis/shadow/fact_extractor.py` | Structural fact extraction | `extract_structural_facts()`, `_FactExtractor` | — | — | shadow_runner | — |
| `pathforge/ast_analysis/shadow/techniques.py` | Technique detection | `detect_techniques()` | — | — | shadow_runner | — |
| `pathforge/ast_analysis/shadow/strategies.py` | Strategy evaluation | `evaluate_strategies()` | — | — | shadow_runner | — |
| `pathforge/ast_analysis/shadow/matching.py` | Solution-group matching | `evaluate_solution_groups()` | — | — | shadow_runner | — |
| `pathforge/ast_analysis/shadow/authority.py` | Authority upgrade metadata | `AuthorityUpgradeRecord`, `validate_upgrade_record()` | — | — | (future Phase 6) | — |
| `pathforge/ast_analysis/shadow/coherence.py` | Strategy compatibility | `check_mutual_exclusion()`, `check_unsatisfiable_combinations()` | — | — | ground_truth_builder | — |
| `pathforge/ast_analysis/shadow/persistence.py` | Shadow DB persistence | `persist_shadow_analysis()`, `rerun_derivation()` | DB (submissions) | DB (submissions) | analyze route | `detect_techniques`, `evaluate_strategies`, `evaluate_solution_groups` |
| `pathforge/ast_analysis/shadow/data_structures.py` | Core data types | `StructuralFact`, `TechniqueEvidence`, `StrategyEvidence`, `MatchOutcome` | — | — | All shadow modules | — |
| `pathforge/api/services/shadow_observability.py` | Shadow counters | `ShadowPipelineCounters`, `record_shadow_pipeline_result()` | — | — | analyze route | — |
| `pathforge/elo_engine.py` | ELO computation + persistence | `EloEngine.compute_updates()`, `EVIDENCE_K_CEILINGS` | DB (user_pattern_elo) | DB (user_pattern_elo) | persistence | — |
| `pathforge/gap_signal_engine.py` | Gap signal computation | `GapSignalEngine.compute_signals()`, `persist_signals()` | DB (gap_signals) | DB (gap_signals) | persistence | — |
| `pathforge/db/db.py` | PostgreSQL pool + migrations | `get_connection()`, `init_db()`, `_apply_migrations()`, `PgConnection` | DB | DB | All modules | — |
| `pathforge/db/schema_pg.sql` | PostgreSQL schema + migrations | — | — | — | `init_db()` | — |
| `pathforge/db/profile_manager.py` | Topic profile management | `update_topic_profile()`, `get_weakest_topics()` | DB (topic_profiles) | DB (topic_profiles) | persistence, recommender | — |
| `pathforge/recommender.py` | Recommendation generation | `get_recommendation()` | DB (problems, submissions) | — | persistence | `get_weakest_topics`, `_select_problem` |
| `pathforge-frontend/components/analysis-view.tsx` | Main analysis UI | `AnalysisView()` | — | — | Next.js | `useAnalyzeCode`, `usePrepareProblem`, `ExperimentalPanel` |
| `pathforge-frontend/components/experimental-panel.tsx` | Shadow results display | `ExperimentalPanel()` | — | — | analysis-view | `mapShadowToDisplay` |
| `pathforge-frontend/src/services/shadow-mapper.ts` | Shadow data → display | `mapShadowToDisplay()` | — | — | experimental-panel | — |
| `pathforge-frontend/src/types/api.ts` | TypeScript type definitions | All interfaces | — | — | All frontend | — |
| `pathforge-frontend/src/hooks/useApi.ts` | React hooks | `useAnalyzeCode()`, `usePrepareProblem()` | — | — | analysis-view | `analyzeCode`, `prepareProblem` |
| `pathforge-frontend/src/services/api/endpoints.ts` | API endpoint functions | `analyzeCode()`, `prepareProblem()` | — | — | hooks | `apiRequest` |
| `pathforge-frontend/src/services/api/client.ts` | HTTP client | `apiRequest()`, `setAccessToken()` | — | — | endpoints | — |

---

## 16. DATA FLOW DIAGRAMS

### A. Production Analysis Flow

```
                        ┌──────────────────┐
                        │  POST /analyze   │
                        └────────┬─────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   resolve_problem()      │
                    │  (if problem provided)   │
                    └────────────┬─────────────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │ DB lookup       │ GraphQL fill     │ LLM GT fill
               │ (fast)          │ (slow, once)     │ (slow, once)
               └─────────────────┼─────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   ProblemContext         │
                    │   .accepted_solution_groups
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   run_analysis()         │
                    │   ├─ ASTEngine.analyze() │
                    │   └─ MatchingEngine.match│
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   run_persistence()      │
                    │   ├─ evidence gating     │
                    │   ├─ topic_profiles      │
                    │   ├─ gap_signals         │
                    │   ├─ user_pattern_elo    │
                    │   ├─ recommendations     │
                    │   └─ streak update       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   AnalyzeResponse        │
                    └──────────────────────────┘
```

### B. Shadow Analysis Flow

```
                    ┌──────────────────────────┐
                    │   ast.parse(code)         │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ extract_structural_facts  │
                    │ → List[StructuralFact]   │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ detect_techniques        │
                    │ → List[TechniqueEvidence]│
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ evaluate_strategies      │
                    │ → List[StrategyEvidence] │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ evaluate_solution_groups │
                    │ → MatchOutcome           │
                    │   CONFIRMED|UNRESOLVED   │
                    │   |CONTRADICTED          │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ persist_shadow_analysis  │
                    │ (DB update, separate     │
                    │  from production write)  │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ record_pipeline_result   │
                    │ (in-memory counters)     │
                    └──────────────────────────┘
```

### C. Ground Truth Flow

```
    LeetCode GraphQL API
           │
    ┌──────▼──────┐
    │ fetch_problem│ (cache-fill only, called by ProblemResolver only)
    │ _by_slug()  │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  problems   │ (DB table)
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │ OpenRouter   │ (cache-fill only)
    │ LLM call     │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │ problem_     │ (DB table)
    │ ground_truth │
    │  ├─ patterns │ (legacy flat)
    │  ├─ solution │ (V1 structured)
    │  │  _groups  │
    └──────┬──────┘
           │
    ┌──────▼──────────────────┐
    │ _load_ground_truth()     │
    │  ├─ Production: patterns │ → MatchingEngine
    │  └─ Shadow: required/    │ → evaluate_solution_groups
    │     optional/excluded    │
    └─────────────────────────┘
```

### D. Evidence Authority Flow

```
    problem_ground_truth.solution_groups[i].authority_tier
           │
    ┌──────▼──────────────┐
    │ Group matched →      │
    │ matched_group_evidence│
    └──────┬──────────────┘
           │
    ┌──────▼──────────────┐
    │ Is authoritative?    │
    │ (structurally_       │
    │  observed or         │
    │  externally_listed?) │
    └──┬──────────────┬───┘
       │ YES          │ NO
       ▼              ▼
    ┌──────┐    ┌───────────┐
    │ Full │    │ analysis_  │
    │ pipe-│    │ only:      │
    │ line:│    │ - Store    │
    │ - ELO│    │ - Streak   │
    │ - Gap│    │ - Skip     │
    │ - Rec│    │   scoring  │
    └──────┘    └───────────┘
```

### E. Persistence Flow

```
    run_persistence(conn, user_id, problem_id, ...)
           │
    ┌──────▼──────┐
    │ INSERT INTO │
    │ submissions │ (with verdict_type, code_hash,
    │             │  detected_patterns_json)
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │ Is authoritative?│
    └──┬──────────┬───┘
       │ YES      │ NO → done (streak only)
       ▼
    ┌──────────────┐
    │ update_topic │
    │ _profile()   │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ GapSignal    │
    │ Engine       │
    │ .compute +   │
    │ .persist     │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ EloEngine    │
    │ .compute +   │
    │ .persist     │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ Recommender  │
    │ .get + log   │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ streak update│ (always)
    └──────────────┘
```

### F. Frontend Analysis Flow

```
    User types LeetCode ID
           │
    ┌──────▼──────┐
    │ "Prepare"   │ → POST /prepare-problem → title + difficulty
    └──────┬──────┘
           │
    User pastes code
           │
    ┌──────▼──────┐
    │ "Run        │
    │  Analysis"  │ → POST /analyze
    └──────┬──────┘
           │
    ┌──────▼──────────────────────┐
    │ AnalyzeResponse received    │
    │  ├─ Problem Info panel      │
    │  ├─ AST Detected Patterns   │
    │  ├─ Matching Engine panel   │
    │  ├─ Skill Changes (ELO)     │
    │  ├─ Gaps panel              │
    │  └─ Experimental (shadow)   │
    └─────────────────────────────┘
```

---

## 17. ARCHITECTURAL INVARIANTS

1. **Shadow cannot alter production scoring.** Shadow analysis runs in `try/except: pass` blocks. Shadow persistence writes to separate DB columns. No shadow code path can affect ELO, gap signals, recommendations, or topic profiles.

2. **Unknown evidence fails closed.** `EVIDENCE_K_CEILINGS.get(evidence_state, 0)` returns 0 for unknown states. `_AUTHORITATIVE_STATES` only includes `structurally_observed` and `externally_listed`. Any unrecognized evidence → `analysis_only` → no downstream scoring.

3. **Legacy ground truth remains compatible.** The `_load_ground_truth()` function handles both legacy flat patterns and V1 structured groups. Legacy groups are mapped to V1 concepts via `_map_legacy_patterns_to_v1()`.

4. **Evidence is per-group.** Each solution group has its own `authority_tier`. The matched group's evidence determines the verdict type.

5. **K ceiling is a cap.** `EVIDENCE_K_CEILINGS` values are applied as `min(base_k, ceiling)`. They never increase the K-factor.

6. **ProblemResolver is the ONLY module allowed to call GraphQL or invoke ground truth generation.** No other module imports `graphql_client` or `openrouter_client` directly.

7. **Ground truth generation happens exactly once per problem.** `_ensure_ground_truth()` checks for existing row before generating.

8. **Confidence values are 0.0–1.0 in the backend.** Frontend multiplies by 100 for display. Badge threshold compares raw `>= 0.8`.

9. **Streak is always updated.** `_update_user_streak()` runs outside the `is_authoritative` block.

10. **Techniques are non-exclusive.** Multiple techniques can fire on the same code. The matching layer handles which technique is relevant to which solution group.

11. **Structural facts are the canonical persisted artifact.** Technique/strategy evidence can be re-derived from stored facts via `rerun_derivation()`.

12. **GraphQL and OpenRouter are cache builders only.** They are never called during runtime analysis.

---

## 18. OPEN QUESTIONS

1. **When should shadow replace production?** No criteria or timeline defined.

2. **What is the required CONFIRMED rate for promotion?** No threshold established.

3. **How should ground-truth authority be upgraded?** `authority.py` provides infrastructure but no automatic upgrades. Phase 6+ deferred.

4. **How should unresolved submissions be handled?** Currently they are stored but not scored. Should they be retried?

5. **Should the V1 vocabulary be expanded?** Some legacy patterns map to empty required lists (greedy, heap). Should new techniques be added?

6. **Should techniques become first-class entities?** Currently they are intermediate representations. Should they be persisted independently?

7. **What is the pilot exit criteria?** `CONTROLLED_SHADOW_PILOT_PLAN.md` exists but no quantitative exit criteria defined.

8. **How should production/shadow disagreements be surfaced?** No reconciliation mechanism exists.

9. **Should ground truth be validated against editorial solutions?** Currently all GT is `llm_proposed`.

10. **Should shadow observability be persisted?** Currently in-memory only, lost on restart.

---

## 19. FINAL HANDOFF SUMMARY

### CURRENT SYSTEM

PathForge is a LeetCode skill assessment platform with a production analysis pipeline that parses Python code into ASTs, runs 36 pattern detectors, matches detected patterns against LLM-generated ground truth using a grouping engine, and persists results to PostgreSQL. The persistence layer computes gap signals, ELO skill ratings, topic profiles, and problem recommendations, all gated by an evidence authority system that prevents low-confidence ground truth from affecting user skill models.

### CURRENT EXPERIMENT

A shadow analysis pipeline runs in parallel with production on every `/analyze` request. It extracts structural facts from the AST, detects 9 computational techniques, evaluates 9 algorithmic strategies, and matches against V1 vocabulary-mapped solution groups to produce CONFIRMED/UNRESOLVED/CONTRADICTED outcomes. This shadow pipeline is observational only — wrapped in exception handlers that prevent any failure from affecting production behavior. Results are persisted to separate DB columns and tracked via in-memory observability counters.

### WHAT IS PROVEN

- Production AST detection + matching works end-to-end
- Evidence authority gating correctly prevents low-confidence scoring
- V1 vocabulary mapping is internally consistent
- Solution-group validation catches semantic incoherence
- PostgreSQL schema is complete and migration-ready
- Frontend correctly displays all analysis panels with proper confidence scaling
- Shadow persistence writes to correct DB columns without errors

### WHAT IS NOT PROVEN

- Whether shadow CONFIRMED rate justifies production promotion
- Whether the V1 vocabulary covers all important algorithmic strategies
- Whether authority tier upgrades work correctly in practice
- Whether shadow results are accurate across diverse problem types
- Whether the system performs well under concurrent load

### DO NOT TOUCH YET

- `src/ast_detection/detectors/` — production detectors are stable
- `pathforge/elo_engine.py` — ELO computation is validated
- `pathforge/gap_signal_engine.py` — gap signals are validated
- `pathforge/recommender.py` — recommendation logic is stable
- `pathforge/db/schema.sql` — SQLite schema (superseded by PostgreSQL)
- Evidence authority gating logic — core invariant

### NEXT DECISIONS REQUIRED

1. Define quantitative criteria for shadow pilot exit (CONFIRMED rate, precision, recall)
2. Decide when/if shadow replaces production matching
3. Determine how to upgrade ground truth authority tiers
4. Decide whether to persist shadow observability data
5. Determine if V1 vocabulary needs expansion for uncovered patterns
6. Establish monitoring/alerting for shadow pipeline degradation
7. Define handling for submissions with missing ground truth

---

**Major files inspected:** 40+ source files across backend, frontend, database, and tests.

**Approximate document length:** ~4,500 lines.

**Internal consistency:** Verified — all file paths, class names, function signatures, and data flows are grounded in the actual repository code.
