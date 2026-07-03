# src/ast_detection/tests/test_detector_interface.py
"""Unit tests for the Detector Interface module."""

import pytest
from src.ast_detection.detector_interface import BaseDetector, DetectionResult, EvidenceItem
class TestEvidenceItem:
    """Test suite for the EvidenceItem class."""

    def test_evidence_item_creation(self):
        """Test creating an EvidenceItem with all fields."""
        evidence = EvidenceItem(
            type="test_type",
            description="Test description",
            location="1:2",
            weight=0.5,
        )
        
        assert evidence.type == "test_type"
        assert evidence.description == "Test description"
        assert evidence.location == "1:2"
        assert evidence.weight == 0.5

    def test_evidence_item_defaults(self):
        """Test creating an EvidenceItem with default values."""
        evidence = EvidenceItem(
            type="test_type",
            description="Test description",
        )
        
        assert evidence.type == "test_type"
        assert evidence.description == "Test description"
        assert evidence.location is None
        assert evidence.weight == 0.0

    def test_evidence_item_to_dict(self):
        """Test EvidenceItem.to_dict method."""
        evidence = EvidenceItem(
            type="test_type",
            description="Test description",
            location="1:2",
            weight=0.5,
        )
        
        result_dict = evidence.to_dict()
        
        expected = {
            "type": "test_type",
            "description": "Test description",
            "location": "1:2",
            "weight": 0.5,
        }
        assert result_dict == expected

    def test_evidence_item_repr(self):
        """Test EvidenceItem.__repr__ method."""
        evidence = EvidenceItem("test_type", "Test description", weight=0.5)
        repr_str = repr(evidence)
        
        assert "EvidenceItem" in repr_str
        assert "test_type" in repr_str
        assert "0.5" in repr_str
class TestDetectionResult:
    """Test suite for the DetectionResult class."""

    def test_detection_result_creation(self):
        """Test creating a DetectionResult with all fields."""
        evidence = [EvidenceItem("type1", "desc1")]
        result = DetectionResult(
            pattern_id="test_pattern",
            confidence=0.8,
            evidence=evidence,
            detected=True,
        )
        
        assert result.pattern_id == "test_pattern"
        assert result.confidence == 0.8
        assert result.evidence == evidence
        assert result.detected == True

    def test_detection_result_defaults(self):
        """Test creating a DetectionResult with default values."""
        result = DetectionResult(
            pattern_id="test_pattern",
            confidence=0.5,
            evidence=[],
        )
        
        assert result.pattern_id == "test_pattern"
        assert result.confidence == 0.5
        assert result.evidence == []
        assert result.detected == False

    def test_detection_result_to_dict(self):
        """Test DetectionResult.to_dict method."""
        evidence = [EvidenceItem("type1", "desc1", weight=0.5)]
        result = DetectionResult(
            pattern_id="test_pattern",
            confidence=0.8,
            evidence=evidence,
            detected=True,
        )
        
        result_dict = result.to_dict()
        
        expected = {
            "pattern_id": "test_pattern",
            "confidence": 0.8,
            "evidence": [
                {"type": "type1", "description": "desc1", "location": None, "weight": 0.5}
            ],
            "detected": True,
        }
        assert result_dict == expected

    def test_detection_result_repr(self):
        """Test DetectionResult.__repr__ method."""
        evidence = [EvidenceItem("type1", "desc1")]
        result = DetectionResult(
            pattern_id="test_pattern",
            confidence=0.8,
            evidence=evidence,
            detected=True,
        )
        repr_str = repr(result)
        
        assert "DetectionResult" in repr_str
        assert "test_pattern" in repr_str
        assert "0.8" in repr_str
        assert "1" in repr_str

    def test_detection_result_confidence_validation(self):
        """Test that DetectionResult accepts various confidence values."""
        for confidence in [0.0, 0.5, 1.0]:
            result = DetectionResult(
                pattern_id="test_pattern",
                confidence=confidence,
                evidence=[],
                detected=confidence > 0.0,
            )
            assert result.confidence == confidence
            assert result.detected == (confidence > 0.0)
class TestBaseDetector:
    """Test suite for the BaseDetector class."""


    def test_base_detector_abstract_methods(self):
        """Test that BaseDetector has abstract methods."""
        import inspect
        from abc import abstractmethod
        
        abstract_methods = BaseDetector.__abstractmethods__
        assert "pattern_id" in abstract_methods
        assert "detect" in abstract_methods

    def test_base_detector_validate_pattern_id_valid(self):
        """Test _validate_pattern_id with valid pattern IDs."""
        # Create a concrete implementation to test the helper
        class TestDetector(BaseDetector):
            pattern_id = "valid_pattern"
            
            def detect(self, ast_root):
                return DetectionResult("valid_pattern", 0.0, [])
        
        detector = TestDetector()
        
        assert detector._validate_pattern_id("valid_pattern") == True
        assert detector._validate_pattern_id("another_valid_pattern_123") == True

    def test_base_detector_validate_pattern_id_invalid(self):
        """Test _validate_pattern_id with invalid pattern IDs."""
        # Create a concrete implementation to test the helper
        class TestDetector(BaseDetector):
            pattern_id = "valid_pattern"
            
            def detect(self, ast_root):
                return DetectionResult("valid_pattern", 0.0, [])
        
        detector = TestDetector()
        
        assert detector._validate_pattern_id("") == False
        assert detector._validate_pattern_id("invalid pattern") == False
        assert detector._validate_pattern_id(123) == False

    def test_base_detector_create_detection_result(self):
        """Test _create_detection_result helper method."""
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])
        
        detector = TestDetector()
        evidence = [EvidenceItem("type1", "desc1")]
        result = detector._create_detection_result(
            "test_pattern",
            0.7,
            evidence,
            True,
        )
        
        assert result.pattern_id == "test_pattern"
        assert result.confidence == 0.7
        assert result.evidence == evidence
        assert result.detected == True

    def test_base_detector_concrete_implementation(self):
        """Test creating a concrete BaseDetector implementation."""
        
        class ConcreteDetector(BaseDetector):
            pattern_id = "concrete_pattern"
            
            def detect(self, ast_root):
                return DetectionResult("concrete_pattern", 0.0, [])
        
        detector = ConcreteDetector()
        assert detector.pattern_id == "concrete_pattern"
        
        # Test with mock AST
        import ast
        ast_root = ast.Module(body=[], type_ignores=[])
        result = detector.detect(ast_root)
        
        assert isinstance(result, DetectionResult)
        assert result.pattern_id == "concrete_pattern"
        assert result.confidence == 0.0