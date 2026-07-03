# src/ast_detection/tests/test_detector_manager.py
"""Unit tests for the DetectorManager module."""

import pytest
from src.ast_detection.detector_manager import DetectorManager
from src.ast_detection.detector_interface import DetectionResult, EvidenceItem
class TestDetectorManager:
    """Test suite for the DetectorManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = DetectorManager()

    def test_manager_initialization(self):
        """Test DetectorManager initializes with detectors."""
        assert self.manager is not None
        assert self.manager.get_detector_count() > 0

    def test_detect_all_calls_detectors(self):
        """Test that detect_all calls all detectors."""
        # Create a simple AST
        code = "x = 1"
        import ast
        ast_root = ast.parse(code)
        
        results = self.manager.detect_all(ast_root)
        
        # Should have one result per detector (possibly with empty evidence)
        assert len(results) > 0
        assert all(isinstance(r, DetectionResult) for r in results)

    def test_detector_manager_exception_handling(self):
        """Test that DetectorManager handles detector exceptions gracefully."""
        code = "x = 1"
        import ast
        ast_root = ast.parse(code)
        
        # Temporarily add a detector that raises an exception
        original_detectors = self.manager.detectors
        
        class FaultyDetector:
            pattern_id = "faulty"
            def detect(self, ast_root):
                raise RuntimeError("Intentional error")
        
        faulty_detector = FaultyDetector()
        self.manager.detectors = [faulty_detector] + original_detectors
        
        try:
            results = self.manager.detect_all(ast_root)
            
            # Should have a result for the faulty detector with empty evidence
            faulty_result = next(r for r in results if r.pattern_id == "faulty")
            assert faulty_result.confidence == 0.0
            assert faulty_result.evidence == []
            
            # Original detectors should still have results
            original_results = [r for r in results if r.pattern_id != "faulty"]
            assert len(original_results) > 0
        finally:
            self.manager.detectors = original_detectors

    def test_detector_manager_returns_detection_results(self):
        """Test that DetectorManager returns valid DetectionResult objects."""
        code = "x = 1"
        import ast
        ast_root = ast.parse(code)
        
        results = self.manager.detect_all(ast_root)
        
        for result in results:
            assert isinstance(result, DetectionResult)
            assert isinstance(result.pattern_id, str)
            assert isinstance(result.confidence, (int, float))
            assert isinstance(result.evidence, list)
            assert isinstance(result.detected, bool)
            assert result.confidence >= 0.0
            assert result.confidence <= 1.0

    def test_detector_manager_with_empty_ast(self):
        """Test DetectorManager with empty AST."""
        import ast
        ast_root = ast.Module(body=[], type_ignores=[])
        
        results = self.manager.detect_all(ast_root)
        
        assert len(results) > 0
        assert all(isinstance(r, DetectionResult) for r in results)