"""Convenience re-exports for detector implementations.

This module re-exports the core types from detector_interface.py
and registry.py so that detector implementations can import everything
from a single location.
"""

import ast

from src.ast_detection.detector_interface import (
    BaseDetector,
    DetectionResult,
    EvidenceItem,
)
from src.ast_detection.registry import register_detector


# Common DP table name aliases.
# Used by dp_* detectors to recognize renamed variables.
# This is NOT a semantic classifier — it is a static alias set.
DP_TABLE_NAMES = frozenset({
    "dp", "table", "memo", "cache", "f", "state", "res", "arr",
    "dp_table", "dp_arr", "dp_memo", "dp_cache",
})


def is_dp_name(name: str) -> bool:
    """Check if a variable name is a common DP table name."""
    return name.lower() in DP_TABLE_NAMES


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "EvidenceItem",
    "register_detector",
    "is_dp_name",
    "ast",
]
