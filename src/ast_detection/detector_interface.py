# src/ast_detection/detector_interface.py

"""Detector interface definitions for the AST Analysis Engine.

This module defines the abstract detector interface, result structures,
and the registration mechanism for all pattern detectors.

The implementation follows the DETECTOR_INTERFACE.md architecture,
ensuring stateless, deterministic detection with proper error handling.
"""

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Dict, Optional
class EvidenceItem:
    """Structured evidence item produced by detectors.

    Each evidence item represents a specific code pattern or structural
    feature that supports detection of a pattern.

    Attributes:
        type: Machine-readable evidence type (e.g., "membership_check")
        description: Human-readable explanation of the evidence
        location: Optional source location (e.g., "5:10" for line 5, col 10)
        weight: Contribution to confidence calculation (0.0-1.0)
    """

    def __init__(
        self,
        type: str,
        description: str,
        location: Optional[str] = None,
        weight: float = 0.0,
    ):
        self.type = type
        self.description = description
        self.location = location
        self.weight = weight

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence item to dictionary for serialization."""
        return {
            "type": self.type,
            "description": self.description,
            "location": self.location,
            "weight": self.weight,
        }

    def __repr__(self) -> str:
        return f"EvidenceItem(type={self.type}, weight={self.weight})"
class DetectionResult:
    """Result object returned by detectors.

    This structure contains all information about a pattern detection,
    including confidence level and supporting evidence.

    Attributes:
        pattern_id: The ID of the pattern detected (from taxonomy)
        confidence: Confidence score (0.0 = not detected, 1.0 = confident)
        evidence: List of evidence items supporting the detection
        detected: Whether the pattern was detected (confidence > 0.0)
    """

    def __init__(
        self,
        pattern_id: str,
        confidence: float,
        evidence: List[EvidenceItem],
        detected: bool = False,
    ):
        self.pattern_id = pattern_id
        self.confidence = confidence
        self.evidence = evidence
        self.detected = detected

    def to_dict(self) -> Dict[str, Any]:
        """Convert detection result to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "detected": self.detected,
        }

    def __repr__(self) -> str:
        return (
            f"DetectionResult(pattern_id={self.pattern_id}, "
            f"confidence={self.confidence}, evidence={len(self.evidence)})"
        )
class BaseDetector(ABC):
    """Abstract base class for all pattern detectors.

    All AST pattern detectors must inherit from this class and implement
    the required interface. This ensures consistent behavior across all
    detector types.

    Design principles:
    - Stateless: detectors should not maintain mutable state
    - Deterministic: same AST always produces same result
    - Isolated: detectors cannot communicate with each other
    - Safe: no external I/O or shared state access

    Subclasses should implement:
    1. `pattern_id` property returning their taxonomy ID
    2. `detect()` method analyzing the AST
    """

    @property
    @abstractmethod
    def pattern_id(self) -> str:
        """Return the taxonomy pattern ID this detector targets.

        Must be an ID from pattern_taxonomy_v1.json.
        This property is used by the registry and coordinator.

        Returns:
            String pattern ID (e.g., "hash_map_lookup")
        """
        ...

    @abstractmethod
    def detect(self, ast_root: ast.AST) -> DetectionResult:
        """Analyze the AST and return detection results.

        Args:
            ast_root: The parsed Python AST (output of the Parser)

        Returns:
            DetectionResult with pattern_id, confidence, evidence, and detected flag

        Rules:
            - Must be deterministic (same AST → same result)
            - Must not modify ast_root or any shared state
            - Must not call other detectors
            - Must not access network, database, or filesystem
            - Must complete synchronously (no I/O)
            - May return empty evidence and 0.0 confidence
        """
        ...

    def _validate_pattern_id(self, pattern_id: str) -> bool:
        """Validate that pattern_id matches required format.

        This helper ensures that pattern IDs follow the expected
        naming convention. Subclasses may override this method for
        custom validation.

        Args:
            pattern_id: The pattern ID to validate

        Returns:
            True if pattern_id is valid, False otherwise
        """
        # Basic validation: non-empty string with alphanumeric chars
        if not pattern_id or not isinstance(pattern_id, str):
            return False
        # Allow letters, numbers, and underscores (consistent with taxonomy)
        return pattern_id.replace("_", "").isalnum()

    def _create_detection_result(
        self,
        pattern_id: str,
        confidence: float,
        evidence: List[EvidenceItem],
        detected: bool = False,
    ) -> DetectionResult:
        """Helper method for creating detection results.

        This method ensures consistent result creation across all
        detector implementations. Subclasses may override if needed.

        Args:
            pattern_id: The pattern ID this detector targets
            confidence: Confidence score (0.0-1.0)
            evidence: List of evidence items
            detected: Whether pattern was detected

        Returns:
            DetectionResult object
        """
        return DetectionResult(pattern_id, confidence, evidence, detected)
