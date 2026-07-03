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


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "EvidenceItem",
    "register_detector",
    "ast",
]
