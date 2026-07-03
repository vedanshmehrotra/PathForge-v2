"""Detector registry for automatic discovery and registration.

This module implements the decorator-based registry system described in
DETECTOR_INTERFACE.md. It provides a centralized way to discover and
instantiate all pattern detectors in the system.

The registry ensures that:
1. All detectors implement the required BaseDetector interface
2. No detector is registered twice (unique pattern_ids)
3. New detectors are automatically discovered when added to the registry
"""

from typing import Dict, Type, List

from src.ast_detection.detector_interface import BaseDetector


class DetectorRegistry:
    def __init__(self):
        self._detector_classes: Dict[str, Type[BaseDetector]] = {}

    def register(self, detector_cls: Type[BaseDetector]) -> Type[BaseDetector]:
        if not issubclass(detector_cls, BaseDetector):
            raise ValueError(f"{detector_cls.__name__} is not a subclass of BaseDetector")
        pattern_id = getattr(detector_cls, "pattern_id", None)
        if not pattern_id:
            raise ValueError(f"{detector_cls.__name__} must have a pattern_id attribute")
        if not self._validate_pattern_id(pattern_id):
            raise ValueError(f"Invalid pattern_id '{pattern_id}' in {detector_cls.__name__}")
        if pattern_id in self._detector_classes:
            raise ValueError(f"Pattern ID '{pattern_id}' is already registered by {self._detector_classes[pattern_id].__name__}")
        self._detector_classes[pattern_id] = detector_cls
        return detector_cls

    def _validate_pattern_id(self, pattern_id: str) -> bool:
        if not pattern_id or not isinstance(pattern_id, str):
            return False
        return pattern_id.islower() and all(c.isalnum() or c == "_" for c in pattern_id)

    def get_all_detectors(self) -> List[BaseDetector]:
        detectors = []
        for detector_cls in self._detector_classes.values():
            detector_instance = detector_cls()
            detectors.append(detector_instance)
        return detectors

    def get_detector(self, pattern_id: str) -> Type[BaseDetector]:
        if pattern_id not in self._detector_classes:
            raise KeyError(f"Pattern ID '{pattern_id}' is not registered. Available IDs: {list(self._detector_classes.keys())}")
        return self._detector_classes[pattern_id]

    def list_pattern_ids(self) -> List[str]:
        return list(self._detector_classes.keys())

    def is_registered(self, pattern_id: str) -> bool:
        return pattern_id in self._detector_classes

    def count_detectors(self) -> int:
        return len(self._detector_classes)

    def __len__(self) -> int:
        return self.count_detectors()

    def __contains__(self, pattern_id: str) -> bool:
        return self.is_registered(pattern_id)

    def __iter__(self):
        return iter(self._detector_classes.values())


_detector_registry = DetectorRegistry()


def register_detector(detector_cls: Type[BaseDetector]) -> Type[BaseDetector]:
    return _detector_registry.register(detector_cls)


def get_all_detectors() -> List[BaseDetector]:
    return _detector_registry.get_all_detectors()


def get_detector(pattern_id: str) -> Type[BaseDetector]:
    return _detector_registry.get_detector(pattern_id)
