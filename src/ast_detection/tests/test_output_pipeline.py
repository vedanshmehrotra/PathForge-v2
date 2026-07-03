# src/ast_detection/tests/test_output_pipeline.py
"""Unit tests for the OutputPipeline module."""

import pytest
from src.ast_detection.output_pipeline import OutputPipeline
from src.ast_detection.detector_interface import DetectionResult, EvidenceItem
class TestOutputPipeline:
    """Test suite for the OutputPipeline class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.pipeline = OutputPipeline()

    def test_package_results_with_patterns(self):
        """Test package_results with detected patterns."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.8,
                evidence=[
                    EvidenceItem("type1", "desc1", weight=0.8),
                    EvidenceItem("type2", "desc2", weight=0.5),
                ],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.4,
                evidence=[EvidenceItem("type3", "desc3", weight=0.4)],
                detected=True,
            ),
        ]
        
        output = self.pipeline.package_results(results)
        
        assert "detected_patterns" in output
        assert "engine_version" in output
        assert "analyzed_at" in output
        assert "patterns_checked" in output
        assert "patterns_detected" in output
        
        assert output["engine_version"] == "2.0.0"
        assert output["patterns_detected"] == 2
        assert len(output["detected_patterns"]) == 2
        
        # Check pattern structure
        assert output["detected_patterns"][0]["pattern_id"] == "pattern1"
        assert output["detected_patterns"][0]["confidence"] == 0.8
        assert len(output["detected_patterns"][0]["evidence"]) == 2
        
        assert output["detected_patterns"][1]["pattern_id"] == "pattern2"
        assert output["detected_patterns"][1]["confidence"] == 0.4

    def test_package_results_empty(self):
        """Test package_results with no patterns."""
        output = self.pipeline.package_results([])
        
        assert "detected_patterns" in output
        assert output["patterns_detected"] == 0
        assert len(output["detected_patterns"]) == 0

    def test_package_single_result(self):
        """Test package_single_result with a single pattern."""
        result = DetectionResult(
            pattern_id="pattern1",
            confidence=0.7,
            evidence=[EvidenceItem("type1", "desc1", weight=0.7)],
            detected=True,
        )
        
        output = self.pipeline.package_single_result(result)
        
        assert output["pattern_id"] == "pattern1"
        assert output["confidence"] == 0.7
        assert output["detected"] == True
        assert len(output["evidence"]) == 1

    def test_format_for_matching_engine(self):
        """Test format_for_matching_engine method."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.8,
                evidence=[EvidenceItem("type1", "desc1", weight=0.8)],
                detected=True,
            ),
        ]
        
        output = self.pipeline.format_for_matching_engine(results)
        
        assert "patterns" in output
        assert "patterns_checked" in output
        assert "patterns_detected" in output
        
        assert len(output["patterns"]) == 1
        assert output["patterns"][0]["pattern_id"] == "pattern1"
        assert output["patterns"][0]["confidence"] == 0.8

    def test_format_for_confidence_layer(self):
        """Test format_for_confidence_layer method."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.9,
                evidence=[EvidenceItem("type1", "desc1", weight=0.9)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.3,
                evidence=[EvidenceItem("type2", "desc2", weight=0.3)],
                detected=True,
            ),
        ]
        
        output = self.pipeline.format_for_confidence_layer(results)
        
        assert "detected" in output
        assert "confidence_distribution" in output
        
        assert output["detected"] == True
        assert output["confidence_distribution"]["high"] == 1
        assert output["confidence_distribution"]["low"] == 1
        assert output["confidence_distribution"]["medium"] == 0

    def test_get_statistics_with_patterns(self):
        """Test get_statistics with patterns."""
        results = [
            DetectionResult(
                pattern_id="pattern1",
                confidence=0.9,
                evidence=[EvidenceItem("type1", "desc1", weight=0.9)],
                detected=True,
            ),
            DetectionResult(
                pattern_id="pattern2",
                confidence=0.5,
                evidence=[EvidenceItem("type2", "desc2", weight=0.5)],
                detected=True,
            ),
        ]
        
        stats = self.pipeline.get_statistics(results)
        
        assert "patterns_detected" in stats
        assert "patterns_checked" in stats
        assert "detection_ratio" in stats
        assert "average_confidence" in stats
        assert "confidence_distribution" in stats
        
        assert stats["patterns_detected"] == 2
        assert stats["average_confidence"] == 0.7
        assert stats["confidence_distribution"]["high"] == 1
        assert stats["confidence_distribution"]["medium"] == 1

    def test_get_statistics_empty(self):
        """Test get_statistics with no patterns."""
        stats = self.pipeline.get_statistics([])
        
        assert "patterns_detected" in stats
        assert "patterns_checked" in stats
        assert "detection_ratio" in stats
        assert "average_confidence" in stats
        assert "confidence_distribution" in stats
        
        assert stats["patterns_detected"] == 0
        assert stats["patterns_checked"] == 22
        assert stats["detection_ratio"] == 0.0
        assert stats["average_confidence"] == 0.0

    def test_format_output_structure(self):
        """Test that output structure matches expected V2 format."""
        result = DetectionResult(
            pattern_id="hash_map_lookup",
            confidence=0.87,
            evidence=[
                EvidenceItem("membership_check", "if x in seen", weight=0.6),
                EvidenceItem("dict_creation", "seen = {}", weight=0.27),
                EvidenceItem("loop", "for num in nums", weight=0.20),
            ],
            detected=True,
        )
        
        output = self.pipeline.package_single_result(result)
        
        # Verify structure matches V2 output format
        required_keys = {"pattern_id", "confidence", "evidence", "detected"}
        assert set(output.keys()) == required_keys
        
        assert output["pattern_id"] == "hash_map_lookup"
        assert output["confidence"] == 0.87
        assert output["detected"] == True
        assert len(output["evidence"]) == 3