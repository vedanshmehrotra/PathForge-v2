"""Shadow-mode hybrid detector for Experiment 2C.

Runs the existing AST engine and the proposed hybrid detector on the same
code, but NEVER changes the production result. Observational only.

Usage:
    from src.ast_detection.semantic.shadow_detector import ShadowDetector
    shadow = ShadowDetector()
    result = shadow.analyze(code_string)
    # result contains both ast_result and hybrid_result
    # production behavior is unchanged
"""
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from src.ast_detection.run_analysis import ASTAnalysisEngine
from src.ast_detection.semantic.analyzer import SemanticAnalyzer


# Fusion policies per pattern (from Experiment 2B)
FUSION_POLICIES = {
    "two_pointers_opposite": "semantic_primary",
    "prefix_sum": "ast_primary_semantic_gaps",
    "hash_map_lookup": "agreement",
    "array_traversal": "ast_only",
}

SEMANTIC_THRESHOLDS = {
    "array_traversal": 0.3,
    "hash_map_lookup": 0.5,
    "prefix_sum": 0.3,
    "two_pointers_opposite": 0.3,
}


@dataclass
class PatternDiscrepancy:
    """A discrepancy between AST and hybrid detection for one pattern."""
    pattern_id: str
    ast_detected: bool
    ast_confidence: float
    sem_score: float
    sem_detected: bool
    hybrid_detected: bool
    fusion_policy: str
    discrepancy_type: str  # "ast_only", "semantic_only", "both", "none", "conflict"


@dataclass
class ShadowResult:
    """Complete shadow-mode analysis result."""
    code_hash: str
    ast_result: Dict[str, Any]
    semantic_scores: Dict[str, float]
    hybrid_detections: Dict[str, bool]
    discrepancies: List[PatternDiscrepancy]
    ast_latency_ms: float
    sem_latency_ms: float
    total_latency_ms: float
    policy_summary: Dict[str, str]


class ShadowDetector:
    """Shadow-mode hybrid detector.

    Runs AST engine and semantic scorer, applies fusion policies,
    and reports discrepancies. Never modifies production behavior.
    """

    def __init__(self):
        self.ast_engine = ASTAnalysisEngine()
        self.semantic = SemanticAnalyzer()
        self.target_patterns = list(FUSION_POLICIES.keys())

    def _code_hash(self, code: str) -> str:
        """Deterministic hash of code for logging (no source code stored)."""
        return hashlib.sha256(code.encode()).hexdigest()[:12]

    def _get_ast_detection(self, ast_result: Dict, pattern: str) -> tuple:
        """Extract AST detection status and confidence for a pattern."""
        for dp in ast_result.get("detected_patterns", []):
            if dp["pattern_id"] == pattern:
                return True, dp["confidence"]
        return False, 0.0

    def _apply_fusion(self, pattern: str, ast_detected: bool,
                      ast_confidence: float, sem_detected: bool,
                      sem_score: float) -> bool:
        """Apply the fusion policy for a specific pattern."""
        policy = FUSION_POLICIES.get(pattern, "ast_only")

        if policy == "semantic_primary":
            return sem_detected or ast_detected

        elif policy == "ast_primary_semantic_gaps":
            return ast_detected or (sem_detected and ast_confidence == 0)

        elif policy == "agreement":
            return ast_detected and sem_detected

        elif policy == "ast_only":
            return ast_detected

        # Default: AST-only
        return ast_detected

    def _classify_discrepancy(self, ast_detected: bool, sem_detected: bool,
                              hybrid_detected: bool) -> str:
        """Classify the type of discrepancy."""
        if ast_detected and sem_detected:
            return "both"
        elif ast_detected and not sem_detected:
            if hybrid_detected:
                return "ast_only"
            return "ast_only"
        elif not ast_detected and sem_detected:
            if hybrid_detected:
                return "semantic_only"
            return "semantic_only"
        else:
            return "none"

    def analyze(self, code: str) -> ShadowResult:
        """Run shadow-mode analysis on code.

        Args:
            code: Python source code string

        Returns:
            ShadowResult with both AST and hybrid results
        """
        code_hash = self._code_hash(code)

        # Run AST engine (production path — unchanged)
        t0 = time.perf_counter()
        ast_result = self.ast_engine.analyze(code)
        ast_latency = (time.perf_counter() - t0) * 1000

        # Run semantic scorer (shadow only)
        t1 = time.perf_counter()
        sem_result = self.semantic.analyze(code)
        sem_latency = (time.perf_counter() - t1) * 1000

        # Extract semantic scores
        semantic_scores = {}
        if sem_result:
            for pat in self.target_patterns:
                semantic_scores[pat] = sem_result["scores"].get(pat, {}).get("score", 0.0)

        # Apply fusion policies
        hybrid_detections = {}
        discrepancies = []

        for pat in self.target_patterns:
            ast_det, ast_conf = self._get_ast_detection(ast_result, pat)
            sem_score = semantic_scores.get(pat, 0.0)
            sem_det = sem_score >= SEMANTIC_THRESHOLDS.get(pat, 0.3)
            hybrid_det = self._apply_fusion(pat, ast_det, ast_conf, sem_det, sem_score)

            hybrid_detections[pat] = hybrid_det

            disc_type = self._classify_discrepancy(ast_det, sem_det, hybrid_det)
            # Detect conflicts: AST and semantic disagree, hybrid picks one
            if ast_det != sem_det and hybrid_det != ast_det:
                disc_type = "conflict"

            discrepancies.append(PatternDiscrepancy(
                pattern_id=pat,
                ast_detected=ast_det,
                ast_confidence=ast_conf,
                sem_score=sem_score,
                sem_detected=sem_det,
                hybrid_detected=hybrid_det,
                fusion_policy=FUSION_POLICIES.get(pat, "ast_only"),
                discrepancy_type=disc_type,
            ))

        total_latency = ast_latency + sem_latency

        return ShadowResult(
            code_hash=code_hash,
            ast_result=ast_result,
            semantic_scores=semantic_scores,
            hybrid_detections=hybrid_detections,
            discrepancies=discrepancies,
            ast_latency_ms=round(ast_latency, 2),
            sem_latency_ms=round(sem_latency, 2),
            total_latency_ms=round(total_latency, 2),
            policy_summary=dict(FUSION_POLICIES),
        )

    def analyze_safe(self, code: str) -> Optional[ShadowResult]:
        """Safe version that never raises exceptions.

        If semantic analysis fails, returns a result with zero semantic
        scores and AST-only hybrid detections.
        """
        try:
            return self.analyze(code)
        except Exception:
            # Fallback: AST-only, no semantic contribution
            try:
                t0 = time.perf_counter()
                ast_result = self.ast_engine.analyze(code)
                ast_latency = (time.perf_counter() - t0) * 1000

                return ShadowResult(
                    code_hash=self._code_hash(code),
                    ast_result=ast_result,
                    semantic_scores={pat: 0.0 for pat in self.target_patterns},
                    hybrid_detections={pat: False for pat in self.target_patterns},
                    discrepancies=[],
                    ast_latency_ms=round(ast_latency, 2),
                    sem_latency_ms=0.0,
                    total_latency_ms=round(ast_latency, 2),
                    policy_summary={},
                )
            except Exception:
                return None
