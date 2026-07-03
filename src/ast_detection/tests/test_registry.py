"""Unit tests for the Detector Registry module."""

import pytest
from src.ast_detection.registry import (
    DetectorRegistry,
    register_detector,
    get_all_detectors,
    get_detector,
    _detector_registry,
)
from src.ast_detection.detector_interface import BaseDetector, DetectionResult


class TestDetectorRegistry:
    def setup_method(self):
        self.registry = DetectorRegistry()

    def test_registry_initialization(self):
        assert self.registry is not None
        assert self.registry.count_detectors() == 0

    def test_register_detector_success(self):
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])

        self.registry.register(TestDetector)
        assert self.registry.count_detectors() == 1
        assert self.registry.is_registered("test_pattern")

    def test_register_duplicate_pattern_id(self):
        class DetectorA(BaseDetector):
            pattern_id = "same_pattern"
            def detect(self, ast_root):
                return DetectionResult("same_pattern", 0.0, [])

        class DetectorB(BaseDetector):
            pattern_id = "same_pattern"
            def detect(self, ast_root):
                return DetectionResult("same_pattern", 0.0, [])

        self.registry.register(DetectorA)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(DetectorB)

    def test_register_invalid_pattern_id(self):
        class InvalidDetector(BaseDetector):
            pattern_id = ""
            def detect(self, ast_root):
                return DetectionResult("", 0.0, [])

        with pytest.raises(ValueError, match="must have a pattern_id"):
            self.registry.register(InvalidDetector)

    def test_get_all_detectors_returns_instances(self):
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])

        self.registry.register(TestDetector)
        detectors = self.registry.get_all_detectors()
        assert len(detectors) == 1
        assert isinstance(detectors[0], TestDetector)

    def test_get_detector_found(self):
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])

        self.registry.register(TestDetector)
        cls = self.registry.get_detector("test_pattern")
        assert cls == TestDetector

    def test_get_detector_not_found(self):
        with pytest.raises(KeyError):
            self.registry.get_detector("nonexistent")

    def test_list_pattern_ids(self):
        class DetectorA(BaseDetector):
            pattern_id = "pattern_a"
            def detect(self, ast_root):
                return DetectionResult("pattern_a", 0.0, [])
        class DetectorB(BaseDetector):
            pattern_id = "pattern_b"
            def detect(self, ast_root):
                return DetectionResult("pattern_b", 0.0, [])

        self.registry.register(DetectorA)
        self.registry.register(DetectorB)
        ids = self.registry.list_pattern_ids()
        assert sorted(ids) == ["pattern_a", "pattern_b"]

    def test_contains_operator(self):
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])

        self.registry.register(TestDetector)
        assert "test_pattern" in self.registry
        assert "nonexistent" not in self.registry

    def test_len(self):
        class TestDetector(BaseDetector):
            pattern_id = "test_pattern"
            def detect(self, ast_root):
                return DetectionResult("test_pattern", 0.0, [])
        self.registry.register(TestDetector)
        assert len(self.registry) == 1

    def test_iteration(self):
        class DetectorA(BaseDetector):
            pattern_id = "pattern_a"
            def detect(self, ast_root):
                return DetectionResult("pattern_a", 0.0, [])
        class DetectorB(BaseDetector):
            pattern_id = "pattern_b"
            def detect(self, ast_root):
                return DetectionResult("pattern_b", 0.0, [])
        self.registry.register(DetectorA)
        self.registry.register(DetectorB)
        classes = list(self.registry)
        assert len(classes) == 2


class TestGlobalRegistry:
    def test_global_registry_exists(self):
        assert _detector_registry is not None
        assert isinstance(_detector_registry, DetectorRegistry)

    def test_get_all_detectors_from_global_registry(self):
        detectors = get_all_detectors()
        assert len(detectors) >= 3
        pattern_ids = [d.pattern_id for d in detectors]
        assert "hash_map_lookup" in pattern_ids
        assert "brute_force" in pattern_ids
        assert "sorting" in pattern_ids
