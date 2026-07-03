"""Detector for sorting pattern.

Detects explicit sorting operations: .sort() method calls, sorted() function,
or custom sort with key functions.

Does NOT detect implicit ordering or natural sortedness of data structures.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class SortingDetector(BaseDetector):
    pattern_id = "sorting"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_sort_method(ast_root, evidence)
        self._detect_sorted_function(ast_root, evidence)
        self._detect_custom_sort_key(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_sort_method(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: list.sort() or similar .sort() call.

        Matches: arr.sort() or arr.sort(key=...)
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
                    evidence.append(
                        EvidenceItem(
                            type="sort_method_call",
                            description=f"In-place sort method call: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.40,
                        )
                    )

    def _detect_sorted_function(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: sorted() built-in function call.

        Matches: result = sorted(arr)
        Does NOT match: str.sort() or other attribute accesses named sorted.
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "sorted":
                    evidence.append(
                        EvidenceItem(
                            type="sorted_function_call",
                            description=f"Sorted function call: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.40,
                        )
                    )

    def _detect_custom_sort_key(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: sort or sorted with a key argument.

        Matches: sorted(arr, key=lambda x: ...) or arr.sort(key=...)
        This is a supporting signal that adds confidence when sorting is detected.
        """
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call):
                has_keyword_key = any(
                    kw.arg == "key" for kw in node.keywords if kw.arg is not None
                )
                if has_keyword_key:
                    evidence.append(
                        EvidenceItem(
                            type="custom_sort_key",
                            description=f"Sort with custom key function: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.20,
                        )
                    )

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
