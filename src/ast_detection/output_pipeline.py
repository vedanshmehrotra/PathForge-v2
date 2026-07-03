"""Output pipeline packages coordinated results into the final V2 output structure."""

from datetime import datetime, timezone
from typing import List, Dict, Any
from src.ast_detection.detector_interface import DetectionResult
from src.ast_detection.registry import get_all_detectors


class OutputPipeline:
    def __init__(self):
        pass

    def package_results(
        self, detected_results: List[DetectionResult]
    ) -> Dict[str, Any]:
        detected_patterns = []
        for result in detected_results:
            detected_patterns.append(
                {
                    "pattern_id": result.pattern_id,
                    "confidence": result.confidence,
                    "evidence": [e.to_dict() for e in result.evidence],
                }
            )

        output = {
            "detected_patterns": detected_patterns,
            "engine_version": "2.0.0",
            "analyzed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "patterns_checked": len(get_all_detectors()),
            "patterns_detected": len(detected_results),
        }
        return output

    def package_single_result(self, detection_result: DetectionResult) -> Dict[str, Any]:
        return {
            "pattern_id": detection_result.pattern_id,
            "confidence": detection_result.confidence,
            "evidence": [e.to_dict() for e in detection_result.evidence],
            "detected": detection_result.detected,
        }

    def format_for_matching_engine(self, detected_results: List[DetectionResult]) -> Dict[str, Any]:
        return {
            "patterns": [
                {
                    "pattern_id": result.pattern_id,
                    "confidence": result.confidence,
                    "evidence": [e.to_dict() for e in result.evidence],
                }
                for result in detected_results
            ],
            "patterns_checked": len(get_all_detectors()),
            "patterns_detected": len(detected_results),
        }

    def format_for_confidence_layer(self, detected_results: List[DetectionResult]) -> Dict[str, Any]:
        return {
            "detected": len(detected_results) > 0,
            "confidence_distribution": {
                "high": sum(1 for r in detected_results if r.confidence >= 0.80),
                "medium": sum(1 for r in detected_results if 0.40 <= r.confidence < 0.80),
                "low": sum(1 for r in detected_results if 0.00 <= r.confidence < 0.40),
            },
        }

    def get_statistics(self, detected_results: List[DetectionResult]) -> Dict[str, Any]:
        all_detectors = len(get_all_detectors())
        if not detected_results:
            return {
                "patterns_detected": 0,
                "patterns_checked": all_detectors,
                "detection_ratio": 0.0,
                "average_confidence": 0.0,
                "confidence_distribution": {
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                },
            }
        return {
            "patterns_detected": len(detected_results),
            "patterns_checked": all_detectors,
            "detection_ratio": len(detected_results) / all_detectors if all_detectors else 0.0,
            "average_confidence": sum(r.confidence for r in detected_results) / len(detected_results),
            "confidence_distribution": {
                "high": sum(1 for r in detected_results if r.confidence >= 0.80),
                "medium": sum(1 for r in detected_results if 0.40 <= r.confidence < 0.80),
                "low": sum(1 for r in detected_results if 0.00 <= r.confidence < 0.40),
            },
        }
