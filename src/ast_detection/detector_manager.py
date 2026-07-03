# src/ast_detection/detector_manager.py
"""Detecter Manager orchestrates all registered detectors."""

import logging
from typing import List
from src.ast_detection.detector_interface import DetectionResult
from src.ast_detection.registry import get_all_detectors
class DetectorManager:
    """Detecter Manager orchestrates all registered detectors.

    The Detector Manager is responsible for executing all detectors
    on the parsed AST. Each detector receives the identical AST root,
    executes independently, and produces a DetectionResult.

    The manager ensures:
    - Every detector receives the identical AST root
    - Detectors execute in any order (no ordering dependencies)
    - If a detector fails (exception), the manager catches it, logs it,
      and marks that detector's result as inconclusive
    - The manager does not interpret, merge, or modify results
    """

    def __init__(self):
        """Initialize the Detector Manager."""
        self.logger = logging.getLogger(__name__)
        self.detectors = get_all_detectors()

    def detect_all(self, ast_root) -> List[DetectionResult]:
        """
        Execute all detectors on the given AST.

        This is the main entry point for the Detector Manager. It:
        1. Passes the same AST root to each detector
        2. Collects individual DetectionResult objects
        3. Handles exceptions by catching them and logging
        4. Returns all detector outputs (including empty evidence results)

        Args:
            ast_root: The parsed AST to analyze

        Returns:
            List of DetectionResult objects, one per detector (including
            those that returned empty evidence)
        """
        all_results = []

        for detector in self.detectors:
            try:
                result = detector.detect(ast_root)
                all_results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Detector {detector.pattern_id} failed: {e}"
                )
                result = DetectionResult(
                    pattern_id=detector.pattern_id,
                    confidence=0.0,
                    evidence=[],
                    detected=False,
                )
                all_results.append(result)

        return all_results

    def get_detector_count(self) -> int:
        """
        Get the number of registered detectors.

        Returns:
            Number of detectors
        """
        return len(self.detectors)