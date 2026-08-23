# PathForge Architecture Feasibility Audit

**Date:** August 22, 2026
**Audit target:** `PATHFORGE_ANALYSIS_ARCHITECTURE_V1.md` (frozen architecture)
**Scope:** Codebase feasibility check — no code changes, no migrations, no tests

---

## 1. Current Architecture Truth

### AST Entry Points

There are **two** AST analysis paths in the codebase. Only one is used in production.

**Production path (active):**
```
src/ast_detection/run_analysis.py::ASTAnalysisEngine.analyze(code)
  → Parser.parse(code)                          # ast.parse()
  → DetectorManager.detect_all(ast_root)         # runs 37 detectors
  → Coordinator.aggregate_and_filter(results)    # filter detected=True, sort by confidence
  → OutputPipeline.package_results(results)      # serialize to dict
```

Entry call chain: `POST /analyze` → `pathforge/api/services/analysis.py::run_analysis()` → `ASTAnalysisEngine.analyze()`

**Legacy path (dead code, still importable):**
```
pathforge/ast_engine/extractor.py::extract_features(ast_root)  # 50+ boolean features
pathforge/ast_engine/classifier.py::classify_pattern(features) # weighted scoring → 33 pattern scores
```
These are NOT called by the production pipeline but remain in the codebase as importable modules.

### Detector Coordinator

`src/ast_detection/coordinator.py::Coordinator.aggregate_and_filter()`:
- Filters to results where `result.detected == True AND result.evidence is non-empty`
- Sorts by confidence descending
- Returns filtered, sorted `DetectionResult` list
- Does NOT perform conflict resolution, taxonomy reasoning, or weighting

### Current Pattern Output Structure

```python
# Output from ASTAnalysisEngine.analyze()
{
    "detected_patterns": [
        {
            "pattern_id": "dfs_recursive",      # ← flat pattern ID string
            "confidence": 0.85,                  # ← single float 0.0-1.0
            "evidence": [                        # ← EvidenceItem list
                {"type": "recursive_call", "description": "...", "location": "5:10", "weight": 0.35},
                {"type": "graph_traversal", "description": "...", "location": "6:8", "weight": 0.30},
            ]
        },
        # ... more patterns
    ],
    "engine_version": "2.0.0",
    "analyzed_at": "...",
    "patterns_checked": 37,
    "patterns_detected": N
}
```

Each detector produces a `DetectionResult`:
```python
class DetectionResult:
    pattern_id: str        # e.g., "dfs_recursive" — ONE pattern per detector
    confidence: float      # 0.0-1.0
    evidence: List[EvidenceItem]  # structured evidence items
    detected: bool         # confidence > 0 AND evidence non-empty
```

### ProblemContext / Ground-Truth Structures

`pathforge/services/problem_resolver.py::ProblemContext`:
```python
@dataclass
class ProblemContext:
    leetcode_id: int
    title_slug: str
    title: str
    difficulty: str
    topics: list
    description: str
    accepted_solution_groups: list = field(default_factory=list)
    ground_truth_confidence: dict = field(default_factory=dict)
```

`accepted_solution_groups` is a list of dicts:
```python
[
    {
        "id": "group_0",
        "patterns": ["linked_list_reversal", "fast_slow_pointers"],  # ← flat pattern IDs
        "evidence": "llm_proposed",  # ← evidence state
        "confidence": {"linked_list_reversal": 0.8, "fast_slow_pointers": 0.6}
    }
]
```

Loaded from `problem_ground_truth.solution_groups` (JSONB) or fallback from `patterns`/`confidence` TEXT columns.

Ground truth builder (`pathforge/services/ground_truth_builder.py`) generates flat pattern lists via LLM, stores as `group_0` with evidence `"llm_proposed"`.

### MatchingEngine API

`src/matching_engine/matching_engine.py::MatchingEngine.match()`:

**Input:**
```python
llm_output = {
    "accepted_solution_groups": [
        ["linked_list_reversal", "fast_slow_pointers"],  # group 0
        ["two_pointers_opposite"]                          # group 1
    ]
}
ast_output = [
    {"pattern_id": "linked_list_reversal", "confidence": 0.85},
    {"pattern_id": "two_pointers_opposite", "confidence": 0.30},
]
```

**Output (`MatchResult.to_dict()`):**
```python
{
    "match_result": "FULL_MATCH",      # FULL_MATCH | PARTIAL_MATCH | NO_MATCH
    "matched_groups": [0],              # indices of fully-matched groups
    "unmatched_patterns": [],           # expected but not detected
    "confidence_score": 0.85,           # weighted average
    "reasoning_signals": [...]          # human-readable signals
}
```

**Matching mechanism (THE critical code):**
```python
def _compute_group_matches(self, ast_patterns, ast_map, llm_groups):
    for group in llm_groups:
        matched = group & ast_patterns        # ← SET INTERSECTION (exact string equality)
        missing = group - ast_patterns        # ← SET DIFFERENCE
        is_fully_matched = overlap_count == group_size  # ← ALL expected patterns detected
```

### Persistence Structures

`pathforge/services/persistence.py::run_persistence()`:

Input: `ast_output` (dict with `detected_patterns`), `match_result` (dict), `groups` (solution groups)

Key transformations:
1. Extracts `primary_pattern` (highest-confidence pattern_id) and `primary_confidence`
2. Extracts `expected_pattern` from first matched group's patterns list
3. Maps `match_result` to `verdict`: `"pass"` if FULL_MATCH or PARTIAL_MATCH, else `"fail"`
4. Maps group evidence to `verdict_type`: `"authoritative"` if in `_AUTHORITATIVE_STATES`, else `"analysis_only"`
5. Stores: `detected_pattern` (single string), `expected_pattern` (single string), `detected_patterns_json` (full list), `verdict_type`, `code_hash`

### Evidence / Authority Propagation

```
group.evidence ("llm_proposed" / "structurally_observed" / "externally_listed")
  → matched_group_evidence
  → verdict_type ("authoritative" | "analysis_only")
  → if NOT authoritative: skip ELO, gaps, recommendations entirely
  → if authoritative: full downstream pipeline (profile, gaps, ELO, recommendations)
```

Evidence K ceilings in `elo_engine.py`:
```python
EVIDENCE_K_CEILINGS = {
    "structurally_observed": 24,  # 75% of DEFAULT_K
    "externally_listed": 16,      # 50% of DEFAULT_K
    "llm_proposed": 0,            # zero — no scoring
    "unobserved": 0,
    "conflicted": 0,
}
```

---

## 2. Frozen Architecture Mapping

| Architecture Layer | Current Code Equivalent | Gap |
|---|---|---|
| **Structural Facts** (§4) | `EvidenceItem` in detectors + `extract_features()` booleans | EvidenceItem IS a fact-like structure, but it's tied to pattern-ID detectors. No standalone fact layer. |
| **Technique Evidence** (§5) | Does not exist | Must be built. Detector evidence is consumed directly by pattern classification. |
| **Strategy Evidence** (§6) | Does not exist | Must be built. Strategies are conflated with pattern IDs. |
| **Solution Groups** (§8) | `accepted_solution_groups` in ProblemContext | Has basic structure (id, patterns, evidence, confidence) but uses flat pattern lists, not required/optional/excluded/threshold. |
| **Matching** (§9) | `MatchingEngine.match()` | Uses exact pattern-ID equality (`group & ast_patterns`). Must change to satisfaction-based evaluation. |
| **Tri-state Outcomes** (§9.1) | `match_result`: FULL_MATCH / PARTIAL_MATCH / NO_MATCH | Must become CONFIRMED / UNRESOLVED / CONTRADICTED. Current NO_MATCH is punitive; UNRESOLVED must not be. |
| **Authority Gate** (§10) | `verdict_type` gating in `run_persistence()` | Already functional. `llm_proposed` → analysis_only → skip ELO. |
| **Primary Strategy Projection** (§7) | `primary_pattern` in persistence | Currently the highest-confidence pattern_id. Must become a derived projection or null. |

---

## 3. Reusable Existing Components

### A. Reusable As-Is

| Component | File | Why |
|---|---|---|
| `Parser` | `src/ast_detection/parser.py` | AST parsing is language-level, not taxonomy-dependent |
| `DetectorManager` execution framework | `src/ast_detection/detector_manager.py` | Iterates detectors, catches exceptions, collects results |
| `BaseDetector` interface | `src/ast_detection/detector_interface.py` | Stateless, deterministic, isolated — matches architecture principles |
| `EvidenceItem` | `src/ast_detection/detector_interface.py` | Already has `type`, `description`, `location`, `weight` — maps well to structural facts |
| `Coordinator` filtering | `src/ast_detection/coordinator.py` | Filter non-empty evidence + sort by confidence is valid for facts too |
| `PgConnection` wrapper | `pathforge/db/db.py` | Database abstraction, not analysis-dependent |
| `GapSignalEngine` | `pathforge/gap_signal_engine.py` | Consumes pattern-level output; interface preserved by adapter |
| `EloEngine` | `pathforge/elo_engine.py` | Consumes pattern-level output; interface preserved by adapter |
| `profile_manager` | `pathforge/db/profile_manager.py` | Topic-level ELO; interface preserved |
| `recommender` | `pathforge/recommender.py` | Consumes gap_info; interface preserved |
| ProblemContext dataclass | `pathforge/services/problem_resolver.py` | Structure is extensible |
| `GraphQLUnavailableError` / `GroundTruthError` | various | Error handling is architecture-independent |
| Multi-group infrastructure in MatchingEngine | `src/matching_engine/matching_engine.py` | `llm_groups` is already `List[Set[str]]`, iteration is per-group |

### B. Reusable With Output-Contract Changes

| Component | File | Change Required |
|---|---|---|
| Individual detectors (37 files) | `src/ast_detection/detectors/*.py` | Must emit `StructuralFact` objects instead of `DetectionResult(pattern_id=...)`. Evidence items already map well. |
| `OutputPipeline` | `src/ast_detection/output_pipeline.py` | Must package structural facts instead of detected patterns. Framework is reusable. |
| `DetectionResult` | `src/ast_detection/detector_interface.py` | Must be split: evidence → `StructuralFact`, pattern_id → removed from canonical output |
| `_load_ground_truth()` | `pathforge/services/problem_resolver.py` | Must parse extended solution_groups with required/optional/excluded/threshold |
| `run_persistence()` | `pathforge/services/persistence.py` | Must bridge new match outcomes to existing downstream interfaces |

### C. Tightly Coupled to Pattern Classification — Must Be Rewritten

| Component | File | Why |
|---|---|---|
| `ASTPatternClassifier` | `pathforge/ast_engine/classifier.py` | Weighted scoring directly maps features → 33 pattern IDs. Entirely the old flat model. |
| `MatchingEngine._compute_group_matches()` | `src/matching_engine/matching_engine.py` | `group & ast_patterns` is exact set-intersection matching. Must become satisfaction evaluation. |
| `MatchingEngine._decide_match_result()` | `src/matching_engine/matching_engine.py` | FULL_MATCH/PARTIAL_MATCH/NO_MATCH tri-state doesn't match CONFIRMED/UNRESOLVED/CONTRADICTED. |
| `MatchingEngine._compute_confidence()` | `src/matching_engine/matching_engine.py` | Pattern-ID-based weighted confidence must become technique-evidence-based. |
| `_normalize_ast()` in MatchingEngine | `src/matching_engine/matching_engine.py` | Normalizes to `{pattern_id: confidence}` — must normalize to `{fact_id: fact}` or `{technique_id: evidence}` |

### D. Likely Obsolete

| Component | File | Why |
|---|---|---|
| `pathforge/ast_engine/extractor.py` | `pathforge/ast_engine/extractor.py` | Old feature extraction. The `src/` engine superseded it. 50+ boolean flags are the old model. |
| `pathforge/ast_engine/classifier.py` | `pathforge/ast_engine/classifier.py` | Weighted scoring → 33 pattern IDs. Dead code in production. |
| `ALL_PATTERNS` set for classification | `pathforge/ast_engine/patterns.py` | Still needed as display labels / backward-compat IDs but NOT as classification targets. |

---

## 4. Required New Data Structures

### StructuralFact

```python
@dataclass
class StructuralFact:
    fact_id: str            # unique within submission (e.g., "fact_001")
    fact_type: str          # e.g., "recursive_call", "membership_check", "loop_shape_for"
    ast_ref: str            # source location (e.g., "5:10")
    attributes: dict        # type-specific attributes (e.g., {"depth": 2, "bounded": True})
    extractor_version: str  # e.g., "1.0.0" for versioning
```

**Should live in:** `src/ast_detection/facts.py` (new file, canonical layer)

### TechniqueEvidence

```python
@dataclass
class TechniqueEvidence:
    technique_id: str             # e.g., "binary_search_narrowing"
    technique_version: str        # e.g., "1.0.0"
    supporting_fact_ids: list[str] # refs to StructuralFact
    presence_confidence: float     # 0.0-1.0: is the technique present?
    centrality: float              # 0.0-1.0: how central is it?
```

**Should live in:** `src/ast_detection/techniques.py` (new file, derived layer)

### StrategyEvidence

```python
@dataclass
class StrategyEvidence:
    strategy_id: str                  # e.g., "binary_search"
    strategy_version: str             # e.g., "1.0.0"
    supporting_technique_ids: list[str]
    supporting_fact_ids: list[str]
    confidence: float
    problem_context_signals: dict     # tag → "confirmed" | "absent" | "unknown"
```

**Should live in:** `src/ast_detection/strategies.py` (new file, derived layer)

### SolutionGroupDefinition

```python
@dataclass
class SolutionGroupDefinition:
    group_id: str
    version: int
    problem_id: int
    required: list[str]        # technique IDs that MUST be present
    optional: list[str]        # technique IDs that boost confidence
    excluded: list[str]        # technique IDs that argue AGAINST this approach
    threshold: float           # minimum satisfaction score
    authority_tier: str        # "bootstrap" | "reviewed" | "editorial"
    provenance: list[str]      # source of this definition
```

**Should live in:** `pathforge/services/solution_groups.py` (new file) or extend `pathforge/services/problem_resolver.py`

### MatchOutcome

```python
@dataclass
class MatchOutcome:
    outcome: str                        # "CONFIRMED" | "UNRESOLVED" | "CONTRADICTED"
    satisfied_group_ids: list[str]
    authority_tier: str
    structural_facts: list[StructuralFact]
    technique_evidence: list[TechniqueEvidence]
    strategy_evidence: list[StrategyEvidence]
    primary_strategy: Optional[str]     # derived projection, may be None
    reasoning: list[str]
```

**Should live in:** `src/matching_engine/matching_engine.py` (replaces `MatchResult`)

---

## 5. Persistence Impact

### Current `submissions` Table Columns — What Can Be Reused

| Column | Current Use | Reuse in New Architecture |
|---|---|---|
| `detected_pattern` (TEXT, single) | Primary pattern string | **KEEP for backward compat.** Derive as projection from highest-evidence technique. |
| `expected_pattern` (TEXT, single) | Ground truth pattern string | **KEEP for backward compat.** Derive from matched solution group. |
| `detected_patterns_json` (JSONB) | Full detection output | **REPURPOSE.** Store `structural_facts_json` in a new parallel column. Keep old column for historical data. |
| `verdict_type` (TEXT) | "authoritative" / "analysis_only" | **EXTEND.** Map to CONFIRMED/UNRESOLVED/CONTRADICTED with authority gating. |
| `code_hash` (TEXT) | Dedup | **KEEP as-is.** |
| `verdict` (TEXT) | pass/fail/error/tle | **KEEP as-is.** Maps from CONFIRMED→pass, UNRESOLVED→fail, CONTRADICTED→fail. |
| `detected_confidence` (REAL) | Single confidence float | **KEEP.** Derive as projection. |
| `diagnosis_confidence` (REAL) | Match confidence score | **KEEP.** Derive from technique-evidence-based confidence. |
| `gap_identified` (BOOLEAN) | Boolean gap flag | **KEEP as-is.** |

### New Columns Actually Required

```sql
-- New columns for submissions (ADD COLUMN IF NOT EXISTS for safety)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS structural_facts_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS technique_evidence_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS strategy_evidence_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS match_outcome TEXT;  -- CONFIRMED/UNRESOLVED/CONTRADICTED
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS extractor_version TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS technique_def_version TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS strategy_def_version TEXT;
```

### New Tables Required

```sql
CREATE TABLE IF NOT EXISTS technique_definitions (
    id SERIAL PRIMARY KEY,
    technique_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_json JSONB NOT NULL,  -- supporting facts, admission criteria
    created_at TEXT NOT NULL,
    UNIQUE(technique_id, version)
);

CREATE TABLE IF NOT EXISTS strategy_definitions (
    id SERIAL PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_json JSONB NOT NULL,  -- required techniques, constraints
    created_at TEXT NOT NULL,
    UNIQUE(strategy_id, version)
);
```

### `problem_ground_truth` — Extend, Don't Replace

The `solution_groups` JSONB column already supports the Phase 0C structure. Extend it:
```json
{
    "id": "group_0",
    "version": 1,
    "required": ["linked_list_traversal", "accumulator_propagation"],
    "optional": ["carry_management"],
    "excluded": ["pointer_rewiring"],
    "threshold": 0.6,
    "authority_tier": "llm_proposed",
    "provenance": ["openrouter_llm_v1"],
    "patterns": ["linked_list_traversal"],  // backward compat
    "confidence": {"linked_list_traversal": 0.8}  // backward compat
}
```

**Legacy `patterns` and `confidence` TEXT columns remain untouched.** Historical data is valid and must not be migrated.

### Extractor/Definition Versioning

Represented in new tables (`technique_definitions`, `strategy_definitions`) with `(technique_id, version)` UNIQUE constraint. Submissions reference versions via `extractor_version`, `technique_def_version`, `strategy_def_version`.

---

## 6. MatchingEngine Impact

### What Can Remain Unchanged

- **Multi-group iteration infrastructure**: `llm_groups` as `List[Set[str]]`, per-group evaluation in `_compute_group_matches()`, `matched_group_indices` output. The loop structure is reusable.
- **`MatchResult` dataclass structure**: Output shape with outcome, matched groups, unmatched items, confidence, reasoning is structurally sound.
- **Error handling in `run_analysis()`**: Exception wrapping around matching is fine.
- **`_build_reasoning_signals()`**: Human-readable reasoning is valuable; needs updating for new outcomes.

### What Must Change

| Current Code | Required Change |
|---|---|
| `_normalize_ast()`: `{pattern_id: confidence}` | Must normalize to structural facts or technique evidence |
| `_normalize_llm()`: `List[Set[str]]` of pattern IDs | Must parse `SolutionGroupDefinition` with required/optional/excluded |
| `_compute_group_matches()`: `group & ast_patterns` | Must evaluate satisfaction: check required evidence present, excluded evidence absent, optional evidence counted |
| `_decide_match_result()`: FULL_MATCH/PARTIAL_MATCH/NO_MATCH | Must output CONFIRMED/UNRESOLVED/CONTRADICTED |
| `_compute_confidence()`: pattern-ID-weighted | Must compute from technique-evidence confidence + centrality |
| `_compute_unmatched()`: pattern set difference | Must compute: required techniques not sufficiently supported |

### Multi-Group Support — Already Useful

The MatchingEngine already supports multiple solution groups:
```python
llm_groups = [
    {"linked_list_reversal", "fast_slow_pointers"},  # group 0
    {"two_pointers_opposite"}                          # group 1
]
```

In the new architecture, this becomes:
```python
solution_groups = [
    SolutionGroupDefinition(group_id="g0", required=["ll_traversal", "carry_propagation"], ...),
    SolutionGroupDefinition(group_id="g1", required=["opposite_direction_scan"], ...),
]
```

Each group is evaluated independently. A single group match is sufficient for CONFIRMED if authority allows it. **This is directly compatible with the architecture's §8.3 semantics.**

### Where Equality-Based Matching Currently Occurs

```python
# src/matching_engine/matching_engine.py, line ~70
matched = group & ast_patterns        # SET INTERSECTION of pattern ID strings
missing = group - ast_patterns        # SET DIFFERENCE
is_fully_matched = overlap_count == group_size and group_size > 0
```

This is the **single point** where the flat pattern-ID equality contract is enforced. The architecture says (§20.8): "Exact pattern-ID equality is NOT the definition of a valid solution."

### Minimum Abstraction for Satisfaction Matching

Replace the set-intersection with:

```python
def evaluate_group_satisfaction(
    group: SolutionGroupDefinition,
    technique_evidence: list[TechniqueEvidence],
    strategy_evidence: list[StrategyEvidence],
) -> float:
    """Return satisfaction score [0.0, 1.0] for one solution group."""
    # 1. Check required techniques — all must be present
    # 2. Check excluded techniques — presence reduces score
    # 3. Check optional techniques — boost score
    # 4. Apply threshold → satisfied or not
```

The function takes technique evidence (not pattern IDs) and returns a satisfaction score. The threshold comparison replaces the binary `is_fully_matched`.

---

## 7. Evidence/Authority Impact

### Current Authority Flow (Traced Through Code)

```
1. ProblemResolver.resolve_problem()
   → loads ground truth from DB
   → returns ProblemContext with accepted_solution_groups

2. analyze_endpoint()
   → passes groups to run_analysis()

3. run_analysis()
   → passes groups to MatchingEngine.match()
   → MatchingEngine returns match_result

4. run_persistence()
   → extracts matched_group_evidence from first matched group
   → verdict_type = "authoritative" if evidence in _AUTHORITATIVE_STATES
   → if NOT authoritative: skip ALL downstream (ELO, gaps, recommendations)

5. ELO engine
   → uses EVIDENCE_K_CEILINGS based on evidence_state
   → llm_proposed → K=0 (no scoring)
```

### Mapping CONFIRMED / UNRESOLVED / CONTRADICTED

| New Outcome | Current Analog | Authority Behavior |
|---|---|---|
| `CONTRADICTED` | Does not exist explicitly. CLOSEST: NO_MATCH with high confidence → verdict="fail" → ELO decreases | **Must be gated**: low-authority CONTRADICTED must be downgraded to UNRESOLVED |
| `UNRESOLVED` | Does not exist. PARTIAL_MATCH and low-confidence NO_MATCH flow through as "fail" | **Must be non-punitive**: no ELO change, no gap signal, no recommendation change |
| `CONFIRMED` | FULL_MATCH with authoritative evidence → verdict="pass" → ELO increases | Direct mapping to current authoritative path |

### Bootstrap Authority Rule Compliance

**Current compliance (invariant #11):**
- `_AUTHORITATIVE_STATES = {"structurally_observed", "externally_listed"}` — `llm_proposed` is NOT included
- When evidence is `llm_proposed`: `verdict_type = "analysis_only"` → skips ELO, gaps, recommendations
- **Bootstrap ground truth CANNOT punish users via ELO** ← ALREADY SATISFIED

**Gap:** The system currently has no explicit `CONTRADICTED` outcome. The closest is `match_result="NO_MATCH"` which produces `verdict="fail"` and flows through as a penalty. Under the new architecture, if evidence is `llm_proposed` and the system disagrees, it must produce `UNRESOLVED` (not `CONTRADICTED`).

### Can the Existing Authority Gate Support This Without Redesigning Downstream?

**YES.** The changes needed are:
1. In the new MatchingEngine: emit CONFIRMED/UNRESOLVED/CONTRADICTED
2. In `run_persistence()`: map outcomes through authority gate:
   - `CONFIRMED` + authoritative evidence → full downstream (existing path)
   - `CONFIRMED` + low-authority evidence → store but skip ELO (existing path)
   - `UNRESOLVED` → store submission, NO downstream scoring (new path)
   - `CONTRADICTED` + authoritative evidence → store as fail, full downstream (existing path)
   - `CONTRADICTED` + low-authority evidence → **downgrade to UNRESOLVED** (new gate)
3. ELO/gaps/recommendations remain unchanged — they consume the same interface

The downstream systems (ELO, gaps, recommendations) do NOT need redesign. They consume `verdict`, `detected_pattern`, `expected_pattern`, `match_result`, evidence state. The persistence adapter bridges.

---

## 8. Ground-Truth Migration Strategy

### Current Schema

```sql
problem_ground_truth:
    problem_id INTEGER PRIMARY KEY
    patterns TEXT NOT NULL DEFAULT '[]'              -- flat JSON array of pattern strings
    confidence TEXT NOT NULL DEFAULT '{}'             -- flat JSON dict of pattern→float
    solution_groups JSONB                            -- Phase 0C structured groups
    validation_status TEXT DEFAULT 'unobserved'      -- evidence state
```

### Current Loading (`_load_ground_truth`)

Already handles two formats:
1. **New format**: `solution_groups` JSONB with `{"id", "patterns", "evidence", "confidence"}` per group
2. **Legacy format**: Falls back to `patterns`/`confidence` TEXT columns, wraps into `group_0`

### How Current Data Coexists with SolutionGroupDefinition

**Extended solution_groups JSONB:**
```json
{
    "id": "group_0",
    "version": 1,
    "patterns": ["hash_map_lookup"],           // backward compat
    "evidence": "llm_proposed",                // backward compat
    "confidence": {"hash_map_lookup": 0.8},    // backward compat
    "required": ["frequency_counting", "membership_check"],  // NEW
    "optional": ["loop_iteration"],            // NEW
    "excluded": [],                            // NEW
    "threshold": 0.6,                          // NEW
    "authority_tier": "llm_proposed",          // NEW
    "provenance": ["openrouter_llm_v1"]        // NEW
}
```

**Migration path:**
1. V1 ground truth builder generates BOTH `patterns` (backward compat) AND `required/optional/excluded` (new architecture)
2. `_load_ground_truth()` continues to parse both formats
3. Legacy `group_0` wrapping remains as fallback
4. Historical data with flat patterns can be enhanced with a future migration script that maps pattern IDs → techniques
5. `patterns` and `confidence` TEXT columns remain **completely untouched**

### Problem Resolver Changes

`ProblemContext.accepted_solution_groups` already returns a list of dicts. The dicts simply need additional keys (`required`, `optional`, `excluded`, `threshold`, `authority_tier`, `provenance`). No schema change needed — JSONB is schemaless.

---

## 9. Downstream Compatibility

### Interface Preserved By Adapter in `run_persistence()`

| Downstream System | Current Interface | Adapter Strategy |
|---|---|---|
| `GapSignalEngine.compute_signals()` | `ast_output`: list of `{pattern_id, confidence}`, `match_result`: dict with `unmatched_patterns` | Bridge: map technique evidence → pattern_id list for gap detection |
| `EloEngine.compute_updates()` | `match_result`: dict with `match_result` string, `matched_groups`, `unmatched_patterns` | Bridge: CONFIRMED→FULL_MATCH, UNRESOLVED→NO_MATCH (but authority-gated), CONTRADICTED→NO_MATCH |
| `update_topic_profile()` | Single `topic`, single `detected_pattern`, single `expected_pattern` | Bridge: derive `primary_pattern` as highest-evidence technique |
| `outcome_from_submission()` | `detected_pattern == expected_pattern` → 1.0 or 0.5 | Bridge: CONFIRMED→1.0 (or 0.5 for partial), UNRESOLVED→0.0 (but K=0), CONTRADICTED→0.0 |
| `get_recommendation()` | `gap_info` dict with `matched_pattern`, `gap_pattern`, `diagnosis_confidence` | Bridge: derive from technique-level data |
| `pattern_links.py` | Pattern ID → human-readable label, LeetCode URL | No change needed — still uses pattern IDs as display labels |

### Places Assuming One Pattern / Pass-Fail

| Location | Assumption | Impact |
|---|---|---|
| `submission_handler._get_pattern()` → `patterns[0]` | Single pattern per problem | Low impact — this is the legacy handler, not the new API path |
| `submission_handler._save_submission()` stores `detected_pattern` as single string | One primary pattern | Bridge: derive from highest-evidence technique |
| `profile_manager.update_topic_profile(topic=pattern)` | Single topic per submission | Bridge: derive from primary strategy/technique |
| `db/elo.outcome_from_submission(detected_pattern == expected_pattern)` | Binary match comparison | Bridge: map CONFIRMED/UNRESOLVED/CONTRADICTED to outcome scores |
| `recommender.gap_info["matched_pattern"]` | Single matched pattern | Bridge: derive from primary technique |

**Conclusion:** All existing downstream code assumes single-pattern pass/fail. The persistence adapter can bridge this in V1. A full downstream redesign is NOT required.

---

## 10. Add Two Numbers Walkthrough

### Current Code Being Analyzed

A typical iterative solution for Add Two Numbers:
```python
def addTwoNumbers(l1, l2):
    dummy = ListNode()
    curr = dummy
    carry = 0
    while l1 or l2 or carry:
        val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
        carry, digit = divmod(val, 10)
        curr.next = ListNode(digit)
        curr = curr.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    return dummy.next
```

### Current System Analysis

| Detector | Fires? | Evidence |
|---|---|---|
| DFS Recursive | NO | No recursive call |
| DFS Iterative | WEAK | Has loop + node.next, but no `list_stack_ops`, no `stack_negative_index` |
| BFS Level Order | NO | No deque creation, no popleft |
| Linked List Reversal | NO | Has `node.next` BUT no `pointer_rewiring` (.next = variable) and no recursive rewiring |
| Fast/Slow Pointers | NO | No `slow`/`fast` variable names |
| Binary Search | NO | No mid_calculation, no left/right variables |
| Hash Map Lookup | NO | No dict/set creation, no membership check |
| All DP detectors | NO | No DP array, no index lookback |
| All other detectors | NO | No relevant signals |

**Result:** Essentially zero patterns detected with meaningful confidence. If ground truth says `["linked_list_reversal"]` → FULL_MATCH fails → user gets verdict="fail" → ELO decreases. This is a **false negative caused by the category error** the architecture identifies (§2.1).

### New Architecture Walkthrough

1. **Structural facts extracted:**
   - `linked_structure_traversal` — `.next` attribute access in while loop
   - `loop_shape_while` — while loop structure
   - `accumulator_update(carry)` — variable updated from prior value via addition
   - `early_termination` — conditional None checks
   - `container_operation(ListNode())` — node construction
   - `control_dependency(carry)` — carry influences branch condition

2. **Technique evidence derived:**
   - `linked_list_traversal` (from `linked_structure_traversal` + `loop_shape_while`)
   - `carry_propagation` (from `accumulator_update` + `control_dependency`)
   - `conditional_null_handling` (from `early_termination`)

3. **SolutionGroupDefinition for Add Two Numbers (required: linked_list_traversal + carry_propagation)**
   - Required evidence: `linked_list_traversal` ✓, `carry_propagation` ✓
   - Optional: `node_construction` ✓ (boosts confidence)
   - Excluded: `pointer_rewiring` ✗ (not present — good)
   - Satisfaction: 1.0 → **CONFIRMED** ✓

4. **If no matching SolutionGroupDefinition exists:**
   - Facts are stored for future use
   - Result: **UNRESOLVED** (safe, non-punitive)
   - Old erroneous `linked_list_reversal` ground truth **cannot force a false contradiction**

---

## 11. Problem 2996 Walkthrough

### Current System Analysis

Problem 2996 (Squared Digits Sum / Perfect Square check) typically uses binary search or math.isqrt.

| Detector | Fires? | Notes |
|---|---|---|
| Binary Search Standard | YES (if binary search solution) | `mid_calculation` + `binary_search_loop` |
| Binary Search Rotated | MAYBE | Depends on if rotated condition is detected |
| Binary Search Answer | MAYBE | Depends on `answer_search` signal |

**If ground truth is correct** → system works reasonably well (this is a case where the existing system isn't terrible for standard solutions).

**If ground truth is wrong** → system follows wrong ground truth → false contradiction.

### New Architecture Walkthrough

**Structural facts:**
- `loop_shape_while` — while loop structure
- `binary_search_test` — comparison with left/right/lo/hi
- `midpoint_calculation` — division by 2 or right shift by 1
- `early_termination` — conditional break/return
- `accumulator_update` — if answer is tracked

**Technique evidence:**
- `binary_search_narrowing` (from `binary_search_test` + `midpoint_calculation` + `loop_shape_while`)

**If SolutionGroupDefinition requires `binary_search_narrowing`:**
- Required evidence present → **CONFIRMED**

**If no technique vocabulary matches (unusual solution style):**
- Facts stored → **UNRESOLVED** (safe)
- Stored structural facts remain available for future definition updates

**Key:** A problem-specific detector is explicitly prohibited per architecture §17. The fact extraction must be general enough to capture this case through standard structural observation.

---

## 12. Implementation Dependency Order

Derived from actual codebase analysis, not assumed:

```
Phase 1: Foundation (no breaking changes)
├── 1.1 StructuralFact dataclass + fact extraction layer
│     Files: src/ast_detection/facts.py (new)
│     Depends on: Nothing (new code)
│     Modifies: src/ast_detection/detectors/*.py (emit facts alongside DetectionResult)
│
├── 1.2 Fact normalization / syntax normalization
│     Files: src/ast_detection/fact_normalizer.py (new)
│     Depends on: 1.1
│
├── 1.3 Versioned technique definitions
│     Files: src/ast_detection/technique_definitions.py (new), schema_pg.sql
│     Depends on: 1.1
│
Phase 2: Derivation Engine
├── 2.1 Technique derivation engine
│     Files: src/ast_detection/technique_engine.py (new)
│     Depends on: 1.1, 1.3
│
├── 2.2 Versioned strategy definitions
│     Files: src/ast_detection/strategy_definitions.py (new), schema_pg.sql
│     Depends on: 1.3
│
├── 2.3 Strategy derivation engine
│     Files: src/ast_detection/strategy_engine.py (new)
│     Depends on: 2.1, 2.2
│
Phase 3: Solution Groups + Matching
├── 3.1 Solution group definitions (extend ProblemContext)
│     Files: pathforge/services/solution_groups.py (new), pathforge/services/problem_resolver.py
│     Depends on: 1.3, 2.2
│
├── 3.2 Ground truth builder update
│     Files: pathforge/services/ground_truth_builder.py
│     Depends on: 3.1
│
├── 3.3 Matching engine refactor
│     Files: src/matching_engine/matching_engine.py
│     Depends on: 2.1, 2.3, 3.1
│     CRITICAL: This is where set-intersection becomes satisfaction evaluation
│
Phase 4: Integration
├── 4.1 Tri-state outcome propagation
│     Files: pathforge/api/routes/analyze.py, pathforge/services/persistence.py
│     Depends on: 3.3
│
├── 4.2 Persistence schema extension
│     Files: pathforge/db/schema_pg.sql (ALTER TABLE ADD COLUMN IF NOT EXISTS)
│     Depends on: 4.1
│
├── 4.3 Downstream compatibility adapter
│     Files: pathforge/services/persistence.py
│     Depends on: 4.1
│     Modifies: persistence.py to bridge new outcomes to existing ELO/gaps/recommendations
│
Phase 5: Verification
├── 5.1 Add Two Numbers end-to-end test
├── 5.2 Problem 2996 end-to-end test
├── 5.3 Legacy data compatibility test
├── 5.4 Frontend type updates (minimal)
```

---

## 13. Risks / Blockers

### BLOCKER: Technique Vocabulary Design

The architecture defines the admission rule (§5.1) but does NOT provide the initial technique vocabulary. This is the **hardest open design problem** and blocks Phase 2.

Without a concrete technique vocabulary, you cannot:
- Define what facts compose what techniques
- Define what techniques compose what strategies
- Define solution groups
- Implement satisfaction matching

**Recommendation:** Design the technique vocabulary for 10-15 core techniques before implementation begins. Validate against Add Two Numbers and 2996.

### RISK: Strategy Definition Complexity

Defining when a combination of techniques constitutes a strategy (e.g., "binary search requires midpoint_calculation + binary_test + narrowing") requires deep algorithmic knowledge. The architecture defers OR/disjunction (§8.3) but basic strategy definitions are needed.

**Mitigation:** Start with simple AND-based strategy definitions. Extend when real problems demand it.

### RISK: Backward Compatibility of Historical Submissions

Existing submissions have `detected_pattern` and `expected_pattern` strings referencing the old flat taxonomy. These cannot be retroactively enriched with structural facts.

**Mitigation (V1):** Leave historical data as-is. Only new submissions get structural facts. Future submissions can be re-derived if needed.

### RISK: No CONTRADICTED State Exists Today

The system has no mechanism to explicitly contradict a user. Adding it requires careful gating to ensure bootstrap ground truth never triggers it.

**Mitigation:** The authority gate already prevents this for `llm_proposed` evidence. The new MatchingEngine must check authority_tier before emitting CONTRADICTED.

### RISK: Dead Code Confusion

`pathforge/ast_engine/` (extractor + classifier) is dead code but still importable. It could cause confusion during implementation.

**Mitigation:** Not a blocker. Clearly mark as deprecated or remove in a cleanup pass.

### RISK: Frontend Expectations

The frontend expects `match_result` field with FULL_MATCH/PARTIAL_MATCH/NO_MATCH semantics. Changing to CONFIRMED/UNRESOLVED/CONTRADICTED requires coordinated frontend updates.

**Mitigation:** The frontend display is minimal — a badge and percentage. Map new outcomes to the same display with different labels.

### RISK: Test Coverage

All existing tests use the old flat pattern contract. Pattern-ID-based assertions will break.

**Mitigation:** Write new tests alongside implementation. Don't try to migrate old tests.

---

## 14. Recommended V1 Implementation Scope

### IN SCOPE

1. **Structural fact extraction** from existing detector infrastructure (reusing EvidenceItem)
2. **Syntax normalization** (minimal: `i += 1` / `i = i + 1` equivalence)
3. **Technique definitions** as versioned data (initial vocabulary: 10-15 techniques)
4. **Strategy definitions** as versioned data (initial vocabulary: 5-8 strategies)
5. **Solution group definitions** (required/optional/excluded/threshold)
6. **Satisfaction-based matching engine** (replacing set-intersection)
7. **Tri-state outcomes** (CONFIRMED/UNRESOLVED/CONTRADICTED)
8. **Persistent structural facts** in submissions (new JSONB columns)
9. **Authority-gated downstream propagation** (UNRESOLVED = no-op, low-authority CONTRADICTED → UNRESOLVED)
10. **Backward-compatible outer pipeline** (ELO, gaps, recommendations unchanged in interface)

### OUT OF SCOPE (per architecture §18-19)

- Runtime LLM verification
- Full CFG framework
- Interprocedural analysis
- Generic constraint language
- OR/disjunction in solution groups
- Group inheritance
- Generic taxonomy migration engine
- Automatic taxonomy discovery
- ELO redesign
- Recommendation redesign
- Frontend redesign (minimal display updates only)

---

## 15. Final Verdict

**READY WITH REQUIRED DESIGN CLARIFICATION**

The codebase is structurally compatible with the frozen architecture. The existing detector infrastructure (BaseDetector, EvidenceItem, DetectorManager, Coordinator) provides a solid foundation for structural fact extraction. The multi-group matching infrastructure in MatchingEngine is directly reusable. The authority gate in persistence already prevents bootstrap ground truth from punishing users.

The minimum change boundary is clear:
- **Single point of change for matching semantics:** `MatchingEngine._compute_group_matches()` — replace `group & ast_patterns` with satisfaction evaluation
- **Single point of change for outcome semantics:** `run_persistence()` — map CONFIRMED/UNRESOLVED/CONTRADICTED through authority gate
- **Adapter pattern for downstream compatibility:** Bridge new multi-fact output to existing single-pattern downstream interfaces

**However**, implementation cannot begin until the **technique vocabulary** is concretely defined. The architecture provides the admission rule but not the vocabulary. This is a design task that must be completed before Phase 2.

**Recommended next steps:**
1. Design and validate the initial technique vocabulary (10-15 techniques) against Add Two Numbers and 2996
2. Design and validate the initial strategy vocabulary (5-8 strategies) against the same test cases
3. Define 2-3 concrete SolutionGroupDefinitions for validation problems
4. Then proceed with implementation in the dependency order specified in §12
