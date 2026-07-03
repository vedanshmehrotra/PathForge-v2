# src/ast_detection/__init__.py

from .detector_interface import BaseDetector, DetectionResult, EvidenceItem
from .detector_manager import DetectorManager
from .coordinator import Coordinator
from .output_pipeline import OutputPipeline
from .run_analysis import run_analysis, ASTAnalysisEngine
from .registry import (
    register_detector,
    get_all_detectors,
    get_detector,
    DetectorRegistry,
    _detector_registry,
)

# Import detectors sub-package to trigger @register_detector decorators
from . import detectors  # noqa: F401


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "EvidenceItem",
    "DetectorManager",
    "Coordinator",
    "OutputPipeline",
    "run_analysis",
    "ASTAnalysisEngine",
    "register_detector",
    "get_all_detectors",
    "get_detector",
    "DetectorRegistry",
    "_detector_registry",
]
