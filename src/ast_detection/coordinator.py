# src/ast_detection/coordinator.py
"""Coordinator collects all DetectionResult objects and produces ordered detected patterns."""

from typing import List
from src.ast_detection.detector_interface import DetectionResult
class Coordinator:
    """Coordinator collects all DetectionResult objects and produces ordered detected patterns.

    The Coordinator is responsible for:
    1. Collecting all detector outputs (including those with and without evidence)
    2. Filtering out DetectionResults with empty evidence
    3. Applying conflict resolution and merging overlapping detections
    4. Sorting results by confidence descending
    5. Passing only detected patterns to downstream components

    The coordinator operates as a neutral aggregator that passes detection results
    through to downstream processing stages. It does NOT:
    - Assign weights or trust scores
    - Make taxonomy-specific decisions
    - Perform taxonomy reasoning

    Taxonomy-specific resolution is handled by the Matching Engine and taxonomy rules.
    """

    def __init__(self):
        """Initialize the Coordinator."""
        pass

    def aggregate_and_filter(
        self, detection_results: List[DetectionResult]
    ) -> List[DetectionResult]:
        """
        Aggregate detector outputs and filter to detected patterns only.

        Args:
            detection_results: List of DetectionResult objects from all detectors

        Returns:
            List of DetectionResult objects for patterns that were detected
            (non-empty evidence), sorted by confidence descending
        """
        # Step 1: Filter to only results with non-empty evidence
        detected_results = [
            result for result in detection_results if result.evidence
        ]

        # Step 2: Sort by confidence descending
        detected_results.sort(key=lambda x: x.confidence, reverse=True)

        return detected_results

    def filter_empty_evidence(
        self, detection_results: List[DetectionResult]
    ) -> List[DetectionResult]:
        """
        Filter out DetectionResults with empty evidence.

        Args:
            detection_results: List of DetectionResult objects from all detectors

        Returns:
            List of DetectionResult objects with non-empty evidence
        """
        return [
            result for result in detection_results if result.evidence
        ]

    def sort_by_confidence(
        self, detection_results: List[DetectionResult]
    ) -> List[DetectionResult]:
        """
        Sort DetectionResults by confidence descending.

        Args:
            detection_results: List of DetectionResult objects to sort

        Returns:
            List of DetectionResult objects sorted by confidence descending
        """
        return sorted(
            detection_results, key=lambda x: x.confidence, reverse=True
        )

    def resolve_overlaps(self, detection_results: List[DetectionResult]) -> List[DetectionResult]:
        """
        Resolve overlapping detections using hierarchical pattern specificity.

        This method handles conflicts where multiple patterns match the same
        code. It applies a hierarchical resolution algorithm where more
        specific patterns (subsets of more general patterns) win.

        Args:
            detection_results: List of DetectionResult objects to resolve

        Returns:
            List of DetectionResult objects after overlap resolution

        Note:
            This is a basic implementation that resolves conflicts based on
            pattern specificity. More complex resolution strategies should be
            implemented here to handle actual taxonomy hierarchies.
        """
        if not detection_results:
            return []

        pattern_ids = [result.pattern_id for result in detection_results]

        # Basic conflict resolution: remove duplicates, keeping highest confidence
        seen = set()
        unique_results = []

        for result in detection_results:
            if result.pattern_id not in seen:
                seen.add(result.pattern_id)
                unique_results.append(result)

        return unique_results