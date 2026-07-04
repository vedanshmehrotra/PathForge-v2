"""Detector sub-package.

All pattern detectors live in this package. Each detector targets exactly
one pattern ID from pattern_taxonomy_v1.json.

Detectors are registered automatically via the @register_detector decorator
which targets the global registry in src.ast_detection.registry.

All detector modules are imported here to trigger their @register_detector
decorators on package import.
"""

from src.ast_detection.detectors.base import (
    BaseDetector,
    DetectionResult,
    EvidenceItem,
    register_detector,
)

# Detector Batch 1
from src.ast_detection.detectors import brute_force  # noqa: F401
from src.ast_detection.detectors import array_traversal  # noqa: F401
from src.ast_detection.detectors import sorting  # noqa: F401
from src.ast_detection.detectors import hash_map_lookup  # noqa: F401
from src.ast_detection.detectors import frequency_counting  # noqa: F401

# Detector Batch 2
from src.ast_detection.detectors import two_pointers_same  # noqa: F401
from src.ast_detection.detectors import two_pointers_opposite  # noqa: F401
from src.ast_detection.detectors import sliding_window_fixed  # noqa: F401
from src.ast_detection.detectors import sliding_window_variable  # noqa: F401
from src.ast_detection.detectors import prefix_sum  # noqa: F401

# Detector Batch 3
from src.ast_detection.detectors import binary_search_classic  # noqa: F401
from src.ast_detection.detectors import binary_search_answer  # noqa: F401
from src.ast_detection.detectors import heap_priority_queue  # noqa: F401
from src.ast_detection.detectors import monotonic_stack  # noqa: F401
from src.ast_detection.detectors import monotonic_queue  # noqa: F401

# Detector Batch 4
from src.ast_detection.detectors import fast_slow_pointers  # noqa: F401
from src.ast_detection.detectors import linked_list_reversal  # noqa: F401

# Detector Batch 5
from src.ast_detection.detectors import dfs_recursive  # noqa: F401
from src.ast_detection.detectors import dfs_iterative  # noqa: F401
from src.ast_detection.detectors import bfs_level_order  # noqa: F401
from src.ast_detection.detectors import bfs_shortest_path  # noqa: F401
from src.ast_detection.detectors import binary_search_tree  # noqa: F401

# Detector Batch 6
from src.ast_detection.detectors import topological_sort  # noqa: F401
from src.ast_detection.detectors import union_find  # noqa: F401
from src.ast_detection.detectors import binary_search_rotated  # noqa: F401

# Detector Batch 7
from src.ast_detection.detectors import greedy_local  # noqa: F401
from src.ast_detection.detectors import greedy_interval  # noqa: F401
from src.ast_detection.detectors import backtracking_subset  # noqa: F401
from src.ast_detection.detectors import backtracking_permutation  # noqa: F401

# Detector Batch 8 — DP
from src.ast_detection.detectors import dp_1d_forward  # noqa: F401
from src.ast_detection.detectors import dp_state_machine  # noqa: F401
from src.ast_detection.detectors import dp_1d_sequence  # noqa: F401
from src.ast_detection.detectors import dp_2d_grid  # noqa: F401
from src.ast_detection.detectors import dp_2d_string  # noqa: F401
from src.ast_detection.detectors import dp_knapsack  # noqa: F401
from src.ast_detection.detectors import dp_interval  # noqa: F401


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "EvidenceItem",
    "register_detector",
]
