"""Detector for heap / priority queue pattern.

Detects heapq module usage including heappush, heappop, heapify, nlargest,
and nsmallest. Only fires on explicit heapq operations.

Does NOT classify ordinary lists or sort operations as heaps.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class HeapPriorityQueueDetector(BaseDetector):
    pattern_id = "heap_top_k"

    def __init__(self):
        super().__init__()
        self._heapq_imported = False
        self._heapq_imported_as = "heapq"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_heapq_import(ast_root)
        self._detect_heappush(ast_root, evidence)
        self._detect_heappop(ast_root, evidence)
        self._detect_heapify(ast_root, evidence)
        self._detect_nlargest_nsmallest(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_heapq_import(self, ast_root: ast.AST) -> None:
        """Check if heapq is imported and how."""
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "heapq":
                        self._heapq_imported = True
                        if alias.asname:
                            self._heapq_imported_as = alias.asname
            elif isinstance(node, ast.ImportFrom):
                if node.module == "heapq":
                    self._heapq_imported = True
                    for alias in node.names:
                        if alias.name in ("heappush", "heappop", "heapify", "nlargest", "nsmallest"):
                            pass

    def _detect_heappush(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: heapq.heappush() call.

        Matches: heapq.heappush(heap, item) or heappush(heap, item)
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                func_name = self._resolve_func_name(node)
                if func_name in ("heappush", "heapq.heappush"):
                    evidence.append(
                        EvidenceItem(
                            type="heap_push",
                            description=f"Heap push: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )

    def _detect_heappop(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: heapq.heappop() call.

        Matches: heapq.heappop(heap) or heappop(heap)
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                func_name = self._resolve_func_name(node)
                if func_name in ("heappop", "heapq.heappop"):
                    evidence.append(
                        EvidenceItem(
                            type="heap_pop",
                            description=f"Heap pop: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )

    def _detect_heapify(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: heapq.heapify() call.

        Matches: heapq.heapify(arr) or heapify(arr)
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                func_name = self._resolve_func_name(node)
                if func_name in ("heapify", "heapq.heapify"):
                    evidence.append(
                        EvidenceItem(
                            type="heapify_call",
                            description=f"Heapify: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

    def _detect_nlargest_nsmallest(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: heapq.nlargest() or heapq.nsmallest() call."""
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                func_name = self._resolve_func_name(node)
                if func_name in ("nlargest", "heapq.nlargest", "nsmallest", "heapq.nsmallest"):
                    evidence.append(
                        EvidenceItem(
                            type="nlargest_nsmallest",
                            description=f"Heap nlargest/nsmallest: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

    def _resolve_func_name(self, node: ast.Call) -> str:
        """Resolve the full function name of a call node."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return node.func.attr
        elif isinstance(node.func, ast.Name):
            return node.func.id
        return ""

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
