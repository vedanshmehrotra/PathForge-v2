# src/ast_detection/tests/test_coordinator.py
"""Unit tests for the Coordinator module."""

import pytest
from src.ast_detection.coordinator import Coordinator
from src.ast_detection.detector_interface import DetectionResult, EvidenceItem
class TestCoordinator:
    """Test suite for the Coordinator class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.coordinator = Coordinator()

    def test_aggregate_and_filter_with_results(self):
        """Test aggregate_and_filter with detection results."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.5,
                evidence=[EvidenceItem("type1", "desc1", weight=0.5)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.8,
                evidence=[EvidenceItem("type2", "desc2", weight=0.8)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern3",
                confidence=0.0,
                evidence=[],
                detected=False,
            ),
        ]
        
        filtered = self.coordinator.aggregate_and_filter(results)
        
        # Should only include results with evidence
        assert len(filtered) == 2
        assert all(r.evidence for r in filtered)
        
        # Should be sorted by confidence descending
        assert filtered[0].confidence == 0.8
        assert filtered[1].confidence == 0.5

    def test_aggregate_and_filter_with_no_results(self):
        """Test aggregate_and_filter with no detection results."""
        filtered = self.coordinator.aggregate_and_filter([])
        
        assert len(filtered) == 0

    def test_filter_empty_evidence(self):
        """Test filter_empty_evidence method."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.5,
                evidence=[EvidenceItem("type1", "desc1", weight=0.5)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.0,
                evidence=[],
                detected=False,
            ),
        ]
        
        filtered = self.coordinator.filter_empty_evidence(results)
        
        assert len(filtered) == 1
        assert filtered[0].pattern_id == "pattern1"
        assert filtered[0].evidence

    def test_sort_by_confidence(self):
        """Test sort_by_confidence method."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.3,
                evidence=[EvidenceItem("type1", "desc1", weight=0.3)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.9,
                evidence=[EvidenceItem("type2", "desc2", weight=0.9)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern3",
                confidence=0.6,
                evidence=[EvidenceItem("type3", "desc3", weight=0.6)],
                detected=True,
            ),
        ]
        
        sorted_results = self.coordinator.sort_by_confidence(results)
        
        assert sorted_results[0].confidence == 0.9
        assert sorted_results[1].confidence == 0.6
        assert sorted_results[2].confidence == 0.3

    def test_resolve_overlaps_no_duplicates(self):
        """Test resolve_overlaps with no duplicates."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.5,
                evidence=[EvidenceItem("type1", "desc1", weight=0.5)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.8,
                evidence=[EvidenceItem("type2", "desc2", weight=0.8)],
                detected=True,
            ),
        ]
        
        resolved = self.coordinator.resolve_overlaps(results)
        
        assert len(resolved) == 2
        assert resolved[0].pattern_id == "pattern1"
        assert resolved[1].pattern_id == "pattern2"

    def test_resolve_overlaps_with_duplicates(self):
        """Test resolve_overlaps with duplicate pattern IDs."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.5,
                evidence=[EvidenceItem("type1", "desc1", weight=0.5)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.9,
                evidence=[EvidenceItem("type1", "desc1", weight=0.9)],
                detected=True,
            ),
        ]
        
        resolved = self.coordinator.resolve_overlaps(results)
        
        # Should have only one result per pattern_id
        assert len(resolved) == 1
        assert resolved[0].pattern_id == "pattern1"
        # Should keep the first one (confidence 0.5)
        assert resolved[0].confidence == 0.5

    def test_sort_by_confidence_empty(self):
        """Test sort_by_confidence with empty list."""
        sorted_results = self.coordinator.sort_by_confidence([])
        
        assert len(sorted_results) == 0

    def test_filter_empty_evidence_empty(self):
        """Test filter_empty_evidence with empty list."""
        filtered = self.coordinator.filter_empty_evidence([])
        
        assert len(filtered) == 0