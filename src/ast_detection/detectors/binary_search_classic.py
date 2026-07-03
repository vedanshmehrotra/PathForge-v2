"""Detector skeleton for binary_search_standard pattern.

Returns DetectionResult(detected=False, confidence=0.0, evidence=[]).
Pattern-specific logic will be added in a future phase.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult


@register_detector
class BinarySearchClassicDetector(BaseDetector):
    pattern_id = "binary_search_standard"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=0.0,
            evidence=[],
            detected=False,
        )
