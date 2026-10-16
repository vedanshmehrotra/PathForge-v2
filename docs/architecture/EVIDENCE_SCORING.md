# Evidence Scoring

Version: 1.0
Status: Design — Frozen for Phase 3C
Last Updated: 2026-07-03

---

## 1. Purpose

Define the philosophy and architecture for evidence collection and confidence calculation in the V2 AST Analysis Engine.

This document describes **why** evidence-based scoring is the correct approach. It does not assign numeric weights — those are determined during Phase 3C implementation.

---

## 2. Evidence Philosophy

### Evidence is structural, not heuristic

A pattern detector identifies an algorithmic pattern by finding **structural evidence** in the AST. Structural evidence means the detector observes concrete code constructs that are characteristic of the pattern.

Examples of structural evidence:
- `hash_map_lookup`: a dictionary/set creation + a membership check (`in`) inside a loop
- `prefix_sum`: a subscript write that references the same array with an index offset of -1
- `tree_dfs`: a recursive function that visits `node.left` and `node.right`

Structural evidence is objective. Given the same AST, every invocation of the same detector produces the same evidence.

### Evidence is not guesswork

A detector does not guess. It does not use probabilistic models, neural networks, or fuzzy matching.

A detector walks the AST, applies deterministic rules, and if a rule matches, it records evidence. The presence of evidence is binary for each rule (either the construct exists or it does not).

### Evidence prevents overfiring

Overfiring occurs when a detector incorrectly identifies a pattern that the code does not implement.

Evidence prevents overfiring through three mechanisms:

1. **Multiple evidence requirements** — A detector should require multiple independent signals before a pattern is considered detected. One coincidental construct (e.g., a single `dict()` call in code that otherwise uses a completely different approach) should not fire the detector.

2. **Negative evidence** — Some detectors should include negative signals that reduce confidence when a conflicting pattern is detected. For example, if code has both `dict` operations and complex recursion/backtracking structure, the presence of the conflicting pattern lowers confidence for the hash map detector.

3. **Evidence weight ceiling** — No single evidence item can contribute more than a configurable maximum (e.g., 0.6 of the total confidence). This prevents one strong signal from dominating and ensures that confident detection requires multiple corroborating signals.

---

## 4. Confidence Calculation Philosophy

### Confidence is evidence ratio

Confidence answers: "How much of the expected structural evidence for this pattern is present in the code?"

Confidence is calculated as:

```
confidence = sum(evidence_weights) / max_possible_confidence
```

Where:
- `sum(evidence_weights)` = total weight of all evidence items that matched
- `max_possible_confidence` = maximum achievable confidence if every signal in the detector fired

### Example

For `hash_map_lookup`, the detector might look for:

| Evidence Signal | Weight | Present? |
|----------------|--------|---------|
| Dictionary/set creation (`= {}`, `= set()`, `= dict()`) | 0.25 | Yes |
| Membership check (`in` / `not in` on dict/set) | 0.35 | Yes |
| Loop construct (`for` / `while`) | 0.20 | Yes |
| No conflicting increment pattern | 0.20 | Yes (no increments) |

```
confidence = (0.25 + 0.35 + 0.20 + 0.20) / 1.0 = 1.0
```

If the membership check were absent:

```
confidence = (0.25 + 0.0 + 0.20 + 0.20) / 1.0 = 0.65
```

### No evidence, no confidence

A detector must never return confidence > 0.0 with an empty evidence list. Every non-zero confidence must be attributable to specific, collectible evidence items.

If a detector cannot find any evidence, it returns 0.0 confidence and an empty evidence list. The downstream system treats this as "pattern not detected."

---

## 5. Confidence Ranges

Confidence is divided into three ranges. These ranges are used by downstream consumers (Matching Engine, Confidence Layer, Gap Signal Engine) to determine how to treat the detection.

| Range | Label | Meaning |
|-------|-------|---------|
| 0.80 – 1.00 | **High** | Multiple strong evidence signals present. Pattern is confidently identified. |
| 0.40 – 0.79 | **Medium** | Some evidence signals present, but not enough for confident identification. Requires verification. |
| 0.00 – 0.39 | **Low** | Weak or no evidence. Pattern is not considered detected. |

### Range boundaries

These boundaries are frozen for V2. They may only be changed via ADR.

| Boundary | Rationale |
|----------|-----------|
| High ≥ 0.80 | Requires most evidence signals to fire. Guarantees multiple corroborating signals. |
| Medium 0.40–0.79 | Some signals present but incomplete. The pattern may be present but cannot be confirmed. |
| Low < 0.40 | Insufficient evidence. Treated as "not detected" by the Matching Engine. |

### How ranges are used

| Range | Matching Engine Action | Confidence Layer Action |
|-------|----------------------|----------------------|
| High (≥ 0.80) | Accept detection | Accept AST result directly |
| Medium (0.40–0.79) | Include in matching | Flag for LLM verification |
| Low (< 0.40) | Treat as not detected | Ignore (do not use) |

---

## 6. Weight Assignment Principles

Numeric weights will be assigned during Phase 3C implementation. The following principles govern weight assignment:

---

## 7. Per-Detector max_possible_confidence

Every detector declares its `max_possible_confidence`:

```python
class HashMapLookupDetector(BaseDetector):
    @property
    def max_possible_confidence(self) -> float:
        return 1.0  # Sum of all evidence weights in this detector
```

This value is used during confidence normalization. It is the denominator in the confidence calculation.

For most detectors, `max_possible_confidence` is 1.0. This ensures all detectors produce a normalized 0.0–1.0 confidence.

Some detectors may have a lower max if they have fewer evidence signals, but because all signals are normalized to 1.0, the practical range remains 0.0–1.0.

---

## 8. Evidence Format Summary

Every evidence item is:

```python
{
    "type": "machine_readable_type",
    "description": "Human-readable description",
    "location": "line:col or null",
    "weight": 0.0..1.0,
}
```

Example evidence for `fast_slow_pointers`:

```python
[
    {
        "type": "slow_fast_assignment",
        "description": "Variables 'slow' and 'fast' assigned in tuple unpacking: slow, fast = head, head",
        "location": "3:4",
        "weight": 0.25,
    },
    {
        "type": "dual_next_traversal",
        "description": "Both slow and fast advance via .next in loop: slow = slow.next / fast = fast.next.next",
        "location": "6:8",
        "weight": 0.40,
    },
    {
        "type": "cycle_check",
        "description": "Equality comparison between slow and fast: if slow == fast",
        "location": "8:11",
        "weight": 0.35,
    },
]
```

---

## 7. Per-Detector max_possible_confidence

Every detector declares its `max_possible_confidence`:

```python
class HashMapLookupDetector(BaseDetector):
    @property
    def max_possible_confidence(self) -> float:
        return 1.0  # Sum of all evidence weights in this detector
```

This value is used during confidence normalization. It is the denominator in the confidence calculation.

For most detectors, `max_possible_confidence` is 1.0. This ensures all detectors produce a normalized 0.0–1.0 confidence.

Some detectors may have a lower max if they have fewer evidence signals, but because all signals are normalized to 1.0, the practical range remains 0.0–1.0.

---

## 8. Evidence Format Summary

Every evidence item is:

```python
{
    "type": "machine_readable_type",
    "description": "Human-readable description",
    "location": "line:col or null",
    "weight": 0.0..1.0,
}
```

Example evidence for `fast_slow_pointers`:

```python
[
    {
        "type": "slow_fast_assignment",
        "description": "Variables 'slow' and 'fast' assigned in tuple unpacking: slow, fast = head, head",
        "location": "3:4",
        "weight": 0.25,
    },
    {
        "type": "dual_next_traversal",
        "description": "Both slow and fast advance via .next in loop: slow = slow.next / fast = fast.next.next",
        "location": "6:8",
        "weight": 0.40,
    },
    {
        "type": "cycle_check",
        "description": "Equality comparison between slow and fast: if slow == fast",
        "location": "8:11",
        "weight": 0.35,
    },
]
```
