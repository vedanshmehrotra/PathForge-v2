# AST Analysis Engine Architecture

Version: 1.0
Status: Design — Frozen for Phase 3C
Last Updated: 2026-07-03

---

## 1. Purpose

The AST Analysis Engine determines which algorithmic patterns a learner's Python solution implements.

It is the evidence generator for PathForge V2.

Unlike the V1 AST engine (which uses a single monolithic classifier with heuristic weights), the V2 AST engine is a modular, detector-based architecture designed for independent development, easy extension, and deterministic evidence collection.

---

## 2. Architecture Overview

```
User Python Source Code
         │
         ▼
┌──────────────────────┐
│       Parser         │
│  (sanitize + parse)  │
└──────────┬───────────┘
           │ AST root
           ▼
┌──────────────────────┐
│   Detector Manager   │
│  (orchestrates all   │
│   detectors)         │
└──┬───┬───┬───┬───┬───┘
   │   │   │   │   │
   ▼   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐
│D1│ │D2│ │D3│ │D4│ │D5│  ...
└──┘ └──┘ └──┘ └──┘ └──┘
   │   │   │   │   │
   │   └───┼───┼───┘
   └───────┼───┘
           ▼
┌──────────────────────┐
│     Coordinator      │
│  (collects results,  │
│   resolves overlaps) │
└──────────┬───────────┘
           │ DetectionResult[]
           ▼
┌──────────────────────┐
│  Final Output        │
│  Pipeline            │
│  → DetectionResult   │
│  → Confidence        │
│  → Evidence          │
└──────────────────────┘
```

---

## 3. Component Descriptions

### 3.1 Parser

**Responsibility:** Accept raw Python source code, validate it is safe Python, produce a parsed AST.

**Input:** `code_string: str`

**Output:** `ast_root: ast.AST` or error

**Rules:**
- Must reject non-Python code (Java, C++, JavaScript)
- Must reject unsafe imports and dangerous builtins (eval, exec, etc.)
- Must reject syntactically invalid code
- Must return the same `ast.AST` root that all detectors consume

**Out of Scope:**
- Runtime execution
- Code formatting checks
- Style linting

### 3.2 Detector Manager

**Responsibility:** Orchestrate all registered detectors. Pass the same AST root to each detector independently. Collect individual DetectionResult objects. Guarantee zero communication between detectors.

**Input:** `ast_root: ast.AST`

**Output:** `list[DetectionResult]` (one per detector that triggered)

**Rules:**
- Every detector receives the identical AST root
- Detectors execute in any order (no ordering dependencies)
- If a detector fails (exception), the manager catches it, logs it, and marks that detector's result as inconclusive
- The manager does not interpret, merge, or modify results — it passes them through to the Coordinator

### 3.3 Independent Detectors

**Responsibility:** Analyze the AST for a single pattern (or a tightly related set of patterns) and return structured evidence.

**Input:** `ast_root: ast.AST`

**Output:** `DetectionResult`

**Rules:**
- Each detector targets exactly one pattern ID from `pattern_taxonomy_v1.json`
- Detectors never communicate with one another
- Detectors never access external state (no database, no LLM, no network)
- Detectors are deterministic: same AST always produces the same DetectionResult
- Detectors must not modify the AST or any shared state
- A detector may return an empty evidence list (pattern not detected)

**Design for extensibility:**
- Adding a new detector requires only: (1) create a new detector module, (2) register it with the Detector Manager
- No existing detector is modified when adding a new one
- Detectors can be enabled/disabled independently

### 3.4 Coordinator

**Responsibility:** Collect all DetectionResult objects and produce the final ordered list of detected patterns.

**Input:** `list[DetectionResult]`

**Output:** `list[DetectionResult]` (sorted, filtered to those with evidence)

**Rules:**
- Collects all detector outputs (including those with evidence and those without)
- Filters out DetectionResults with empty evidence (i.e., patterns not detected)
- Applies conflict resolution and merges overlapping detections (e.g., hierarchical pattern specificity)
- The coordinator may sort results by confidence descending
- The coordinator does NOT assign weights or trust scores — those are maintained by the Output Pipeline
- The coordinator does NOT make taxonomy-specific decisions (specificity, hierarchy, algorithm preference)
- Taxonomy-specific resolution is handled by the Matching Engine and taxonomy rules

**Design for extensiblity:** The coordinator operates as a neutral aggregator that passes detection results through to downstream processing stages.

---

**Responsibility:** Package the coordinated results into the standardized V2 output structure consumed by downstream consumers (Matching Engine, Confidence Layer).

**Output structure:**

```python
{
    "detected_patterns": [
        {
            "pattern_id": "hash_map_lookup",
            "confidence": 0.87,
            "evidence": [
                {"type": "membership_check", "details": "if x in seen"},
                {"type": "dict_creation", "details": "seen = {}"},
                {"type": "loop", "details": "for num in nums"},
            ],
        },
        {
            "pattern_id": "prefix_sum",
            "confidence": 0.0,
            "evidence": [],
        },
    ],
    "engine_version": "2.0.0",
    "analyzed_at": "2026-07-03T12:00:00Z",
    "patterns_checked": 44,
    "patterns_detected": 1,
}
```

**Rule 1:** Every pattern in the taxonomy is **not** represented in the output. Only patterns that were actually detected (with evidence) are included. This ensures downstream consumers only process patterns that were found in the code.

**Rule 2:** The output never includes confidence values for patterns not in the taxonomy. If a pattern is not detected, it is simply omitted from the result set.

**Rule 3:** The output includes only the patterns that were detected, in order of confidence descending.

**Result:** This lazy detection approach significantly reduces unnecessary data processing and storage.

---

## 4. Relationship with V1 AST Engine

The V2 AST Analysis Engine is an independent module.

| Aspect | V1 Engine | V2 Engine |
|--------|-----------|-----------|
| Location | `pathforge/ast_engine/` | `src/ast_detection/` |
| Architecture | Monolithic classifier | Modular independent detectors |
| Output | Single dict of scores | DetectionResult with evidence |
| Pattern source | Hardcoded constants in `patterns.py` | Reads `pattern_taxonomy_v1.json` |
| Taxonomy | 33 patterns (V1 subset) | All 44 taxonomy patterns |
| Integration | Internal to V1 pipeline | Feeds V2 Matching Engine |
| Detector count | 1 (combined) | 44 (one per pattern) |

V1 is not modified. V2 runs alongside V1 and is used for V2 learning mode only.

---

## 5. Data Flow (Complete V2 Submission Path)

```
User submission (question_id + code)
         │
         ▼
Question Resolver (Phase 1)
         │
         ▼
Metadata Cache / LLM Classifier (Phase 2 / 3A)
  → Accepted Solution Groups
         │
         ▼
AST Analysis Engine (Phase 3B/3C — this design)
  → Detected patterns + evidence + confidence
         │
         ▼
Matching Engine (Phase 3B — this design)
  → Full / Partial / No match
         │
         ▼
Confidence Layer (Phase 5)
         │
         ▼
Gap Signal Engine (Phase 6)
         │
         ▼
Recommendation Engine (Phase 7)
```

---

## 6. Module Boundaries

```
src/ast_detection/
├── __init__.py                  # Exports run_analysis()
├── parser.py                    # Parse and sanitize source code
├── detector_manager.py          # Orchestrate all detectors
├── coordinator.py               # Merge and resolve conflicts
├── output_pipeline.py           # Package final result
├── detectors/
│   ├── __init__.py              # Detector registry
│   ├── base.py                  # Abstract base detector class
│   ├── hash_map_lookup.py       # One detector per pattern
│   ├── frequency_counting.py
│   ├── sorting.py
│   ├── ...                      # 44 detectors total
└── tests/
    ├── test_parser.py
    ├── test_detector_manager.py
    ├── test_coordinator.py
    ├── test_output_pipeline.py
    └── detectors/
        ├── test_hash_map_lookup.py
        ├── test_frequency_counting.py
        └── ...
```

---

## 7. Design Constraints

1. **Zero coupling between detectors** — No detector calls or references another detector
2. **Deterministic output** — Same code always produces the same result
3. **Taxonomy-driven** — Pattern IDs come from `pattern_taxonomy_v1.json`, never hardcoded
4. **Safe by default** — Parser rejects unsafe code before any detector runs
5. **Resilient** — A single detector failure does not block other detectors
6. **Extensible** — New detectors plug in via registry, no existing code changes
7. **Evidence-first** — Every confidence value is backed by explicit evidence items
