# Detector Interface

Version: 1.0
Status: Design — Frozen for Phase 3C
Last Updated: 2026-07-03

---

## 1. Purpose

Define the standard interface that every AST pattern detector must implement.

This interface ensures all detectors are interchangeable, independently testable, and produce structurally identical output that the Coordinator and downstream consumers can process uniformly.

---

## 2. DetectionResult Structure

Every detector returns a `DetectionResult` object.

```python
@dataclass
class DetectionResult:
    pattern_id: str
    confidence: float        # 0.0 to 1.0
    evidence: list[EvidenceItem]
    detected: bool           # True if confidence > 0


@dataclass
class EvidenceItem:
    type: str                # Machine-readable evidence type
    description: str         # Human-readable explanation
    location: str | None     # Source location (e.g., "line 5, col 10")
    weight: float            # Contribution to confidence (0.0 to 1.0)
```

### Field Rules

| Field | Constraint |
|-------|-----------|
| `pattern_id` | Must match exactly one `id` in `pattern_taxonomy_v1.json`. Never invented. |
| `confidence` | Calculated from evidence. 0.0 = no evidence. 1.0 = all evidence signals present. |
| `evidence` | Empty list when pattern is not detected. Non-empty when detected. |
| `detected` | `True` when confidence > 0.0. `False` when confidence == 0.0. |
| `evidence[].type` | Machine-readable label e.g. `"membership_check"`, `"dict_creation"` |
| `evidence[].description` | Human-readable e.g. `"if x in seen: membership check on dictionary 'seen'"` |
| `evidence[].location` | Optional. e.g. `"5:10"` means line 5, column 10. May be None. |
| `evidence[].weight` | Between 0.0 and 1.0. Represents this item's contribution to confidence. |

---

## 3. Detector Interface

```python
class BaseDetector(ABC):
    """Abstract base class for all pattern detectors."""

    @property
    @abstractmethod
    def pattern_id(self) -> str:
        """Return the taxonomy pattern ID this detector targets.
        
        Must be an ID from pattern_taxonomy_v1.json.
        """
        ...

    @abstractmethod
    def detect(self, ast_root: ast.AST) -> DetectionResult:
        """Analyze the AST and return detection results.
        
        Args:
            ast_root: The parsed Python AST (output of the Parser).
            
        Returns:
            DetectionResult with pattern_id, confidence, evidence, and detected flag.
            
        Rules:
            - Must be deterministic (same AST → same result).
            - Must not modify ast_root or any shared state.
            - Must not call other detectors.
            - Must not access network, database, or filesystem.
            - Must complete synchronously (no I/O).
            - May return empty evidence and 0.0 confidence.
        """
        ...
```

---

## 4. Detector Responsibilities

Every detector MUST:

1. **Target exactly one pattern ID** from `pattern_taxonomy_v1.json`
2. **Walk the AST** to find structural evidence for that pattern
3. **Return structured evidence** explaining why the pattern was detected (or not)
4. **Calculate confidence** from the evidence it collected
5. **Be deterministic** — same AST, same result, same confidence, same evidence
6. **Be stateless** — no shared mutable state between invocations
7. **Handle any valid AST** — including code that does not match the pattern (return empty evidence)

---

## 5. What Detectors Are NOT Allowed To Do

A detector MUST NOT:

1. **Communicate with other detectors** — no calling, importing, or referencing other detector modules
2. **Access external state** — no database queries, no network calls, no filesystem reads beyond the module's own imports
3. **Modify the AST** — the AST is read-only
4. **Modify global or module-level state** — detectors are stateless
5. **Access the classification cache, LLM, or any Phase 3A components**
6. **Hardcode pattern IDs** — the `pattern_id` property must return a string matching the taxonomy, but the detector itself should reference the taxonomy constant from `pattern_taxonomy_v1.json`
7. **Return confidence without evidence** — every non-zero confidence must correspond to at least one evidence item
8. **Return evidence without weight** — every evidence item must declare its weight contribution
9. **Raise exceptions for normal non-matches** — return `DetectionResult(detected=False, confidence=0.0, evidence=[])` instead
10. **Perform I/O of any kind** — detectors are pure AST walkers

---

## 6. Evidence Rules

### Evidence types must be semantic

Evidence types should describe what was found in the code, not the detector's identity.

Good: `"membership_check"`, `"dict_creation"`, `"loop_structure"`  
Bad: `"hash_map_lookup_heuristic_3"`, `"detector_rule_7"`

### Evidence must be independently meaningful

Each evidence item should stand alone as a signal for the pattern.

- If a single code construct provides multiple signals, emit multiple evidence items
- Do not bundle unrelated signals into one evidence item

### Evidence location is optional but encouraged

When available, include the line and column of the construct that generated the evidence. This supports future UI features (e.g., highlighting detected patterns in the code viewer).

---

## 7. Registration

Detectors register with the Detector Manager via a module-level registry.

```python
# src/ast_detection/detectors/__init__.py

_DETECTOR_REGISTRY: dict[str, type[BaseDetector]] = {}

def register_detector(detector_cls: type[BaseDetector]) -> type[BaseDetector]:
    """Register a detector class. Called as a decorator."""
    _DETECTOR_REGISTRY[detector_cls.pattern_id] = detector_cls
    return detector_cls


def get_all_detectors() -> list[BaseDetector]:
    """Instantiate all registered detectors."""
    return [cls() for cls in _DETECTOR_REGISTRY.values()]
```

### Detector module pattern

```python
# src/ast_detection/detectors/hash_map_lookup.py

import ast
from ..detectors.base import BaseDetector, register_detector
from ..detectors.base import DetectionResult, EvidenceItem


@register_detector
class HashMapLookupDetector(BaseDetector):
    pattern_id = "hash_map_lookup"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        # ... walk the AST, collect evidence ...
        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        return min(sum(item.weight for item in evidence), 1.0)
```

---

## 8. Error Handling

If a detector encounters an unexpected error during AST analysis:

```python
try:
    result = detector.detect(ast_root)
except Exception as e:
    result = DetectionResult(
        pattern_id=detector.pattern_id,
        confidence=0.0,
        evidence=[],
        detected=False,
    )
    log.error(f"Detector {detector.pattern_id} failed: {e}")
```

The Detector Manager wraps every detector call in a try/except. A single detector failure never blocks other detectors or crashes the pipeline.

---

## 9. Zero-Confidence Convention

When a detector finds no structural evidence for its target pattern in the AST, it returns a result indicating it did not detect the pattern:

```python
DetectionResult(
    pattern_id="hash_map_lookup",
    confidence=0.0,
    evidence=[],
    detected=False,
)
```

**Rule:** This result is a filtered-out placeholder:

1. Detectors return this result **only** when they have completed their analysis and found no relevant evidence. These results are passed to the Detector Manager.

2. The Coordinator filters out all results with empty evidence and no confidence.

3. The filtered results do **not** appear in the final output pipeline.

This design ensures that only patterns with actual detected evidence are processed by downstream components, maintaining a clean and efficient data flow.
