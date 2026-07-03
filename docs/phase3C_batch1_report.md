# Phase 3C Batch 1 — Detector Implementation Report

## Overview

Batch 1 implements 5 detectors for common algorithmic patterns, each registered in the global `_detector_registry` via the `@register_detector` decorator. All detectors extend `BaseDetector` and follow the frozen Phase 3B contract.

## Detectors

| Pattern ID | Class | Module | Core Signal |
|---|---|---|---|
| `hash_map_lookup` | `HashMapLookupDetector` | `hash_map_lookup.py` | dict creation + membership check + loop |
| `array_traversal` | `ArrayTraversalDetector` | `array_traversal.py` | loop (collection or index-based) + subscript access or element update |
| `sorting` | `SortingDetector` | `sorting.py` | `.sort()` or `sorted()` call |
| `brute_force` | `BruteForceDetector` | `brute_force.py` | nested loops or recursive branching |
| `hash_map_frequency` | `FrequencyCountingDetector` | `frequency_counting.py` | increment pattern (`.get(x,0)+1`) or Counter import + loop/constructor |

## Evidence Strategy

Each detector collects structural AST evidence (typed `EvidenceItem` objects) and computes a combined confidence score:

- **Evidence types** describe actual AST constructs (e.g., `dict_creation`, `membership_check`, `sort_method_call`, `nested_loops`, `frequency_increment`).
- **Weights** range from 0.20 to 0.50 based on how strongly a signal indicates the target pattern.
- **Confidence** = `min(sum(weights), 1.0)` when core signals present; `0.0` otherwise.
- **Empty evidence** is returned when core signals are absent (no partial detections).

### Core Signal Requirement

Each detector uses a "core signal" gating pattern: `detect()` returns empty evidence and `0.0` confidence if the required structural evidence is missing. This prevents false positives from partial evidence.

## False Positive Prevention

The following scenarios are explicitly rejected by each detector (tested):

| Detector | Rejected Scenario | Reason |
|---|---|---|
| `hash_map_lookup` | Static config dict (`{'key':'val'}`) | No membership check or loop |
| `hash_map_lookup` | Membership check without loop | No iteration context |
| `hash_map_lookup` | Dict + loop without membership check | No lookup signal |
| `hash_map_lookup` | Literal dict in loop with membership | Dict is static, not built for lookup |
| `hash_map_lookup` | Set without loop | No iteration context |
| `array_traversal` | Range-only loop (`for i in range(10)`) | No subscript access |
| `array_traversal` | Collection loop without subscript | No indexed element access |
| `array_traversal` | While loop with subscript | Not a for-loop traversal pattern |
| `array_traversal` | Enumerate without subscript | No direct element access |
| `array_traversal` | Subscript without loop | No iteration context |
| `brute_force` | Single loop | Not O(n²) or exponential |
| `brute_force` | Sequential (non-nested) loops | Linear complexity |
| `brute_force` | Single recursion without branching | Linear recursion |
| `sorting` | Non-sort operations | Only `.sort()`/`sorted()` trigger |
| `sorting` | `reversed()` call | Not a sort operation |
| `hash_map_frequency` | Static dict | No increment or loop |
| `hash_map_frequency` | Empty dict without loop | No counting context |
| `hash_map_frequency` | `.get()` lookup without increment | No frequency accumulation |
| `hash_map_frequency` | Counter import without counting | Lookup-only usage |
| `hash_map_frequency` | `x += 1` without dict context | Not frequency counting |

## Limitations

### Undetected Cases

The detectors are intentionally conservative and **will not detect** these valid patterns:

1. **hash_map_lookup**: Dynamic dict creation via `.setdefault()` or `collections.defaultdict` without explicit `in` check.
2. **array_traversal**: `while` loops with index increment (currently requires `for` loop). Numpy-style vectorized operations.
3. **brute_force**: Nested comprehensions (e.g., `[f(x,y) for x in X for y in Y]`) — AST shows generators, not `ast.For`. Permutations via `itertools`.
4. **sorting**: Custom comparison via `functools.cmp_to_key`. Sorting with `heapq` or `numpy.sort`.
5. **frequency_counting**: Manual `counts[x] += 1` without involving `.get()` — uses `ast.AugAssign` which is not matched by the increment pattern detector. `itertools.groupby` patterns.

### Deliberate Design Choices

- **Precision over recall**: Returning no detection is preferred over a false positive.
- **AST-only analysis**: No type inference, no dataflow analysis, no semantic understanding.
- **Closed-book**: Detectors cannot inspect each other's output or perform I/O.

## Test Coverage

- **136 total tests** across all modules (detectors, interface, manager, coordinator, output pipeline, parser, registry, run_analysis).
- **55 detector-specific tests** (11 per detector on average, covering positive detection, false-positive rejection, and determinism).
- All tests pass cleanly (0 failures, 0 errors).

## Files Changed

- `src/ast_detection/detectors/hash_map_lookup.py` — New
- `src/ast_detection/detectors/array_traversal.py` — New
- `src/ast_detection/detectors/sorting.py` — New
- `src/ast_detection/detectors/brute_force.py` — New
- `src/ast_detection/detectors/frequency_counting.py` — New
- `src/ast_detection/detectors/__init__.py` — Updated imports
- `src/ast_detection/tests/test_detectors.py` — Updated
- `src/ast_detection/tests/test_registry.py` — Updated expectations
