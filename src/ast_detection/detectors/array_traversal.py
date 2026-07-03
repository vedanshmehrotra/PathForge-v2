"""Detector for array_traversal pattern.

Detects sequential element-by-element processing of array-like structures.
Requires BOTH a loop over a collection AND subscript access or element update.

A for loop over a collection alone does NOT trigger this detector (that is
just iteration, not array traversal with indexed access).
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class ArrayTraversalDetector(BaseDetector):
    pattern_id = "array_traversal"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        has_loop = self._detect_traversal_loop(ast_root, evidence)
        has_subscript = self._detect_subscript_access(ast_root, evidence)
        has_update = self._detect_element_update(ast_root, evidence)
        has_elem_use = self._detect_element_usage(ast_root, evidence)

        has_element_access = has_subscript or has_update or has_elem_use
        has_required_signals = has_loop and has_element_access
        confidence = self._calculate_confidence(evidence, has_required_signals)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence if has_required_signals else [],
            detected=confidence > 0.0,
        )

    def _detect_traversal_loop(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Name):
                    evidence.append(
                        EvidenceItem(
                            type="for_loop_over_collection",
                            description=f"Iteration over collection '{node.iter.id}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.35,
                        )
                    )
                    found = True
                elif isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                    if node.iter.func.id in ("range", "enumerate"):
                        evidence.append(
                            EvidenceItem(
                                type="iterator_based_loop",
                                description=f"Iterator-based loop: {ast.unparse(node.iter)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.35,
                            )
                        )
                        found = True
        return found

    def _detect_element_usage(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                loop_var_names = self._get_loop_var_names(node)
                if loop_var_names:
                    body_names = {
                        n.id for stmt in node.body for n in ast.walk(stmt)
                        if isinstance(n, ast.Name) and n.id in loop_var_names
                    }
                    if body_names:
                        evidence.append(
                            EvidenceItem(
                                type="element_usage",
                                description=f"Loop variable '{', '.join(sorted(body_names))}' used in body",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.30,
                            )
                        )
                        found = True
                        break
        return found

    def _get_loop_var_names(self, for_node: ast.For) -> set:
        names = set()
        target = for_node.target
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    names.add(elt.id)
        return names

    def _detect_subscript_access(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                evidence.append(
                    EvidenceItem(
                        type="subscript_access",
                        description=f"Element access via subscript: {ast.unparse(node)}",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                        weight=0.35,
                    )
                )
                found = True
                break
        return found

    def _detect_element_update(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                        evidence.append(
                            EvidenceItem(
                                type="element_update",
                                description=f"Sequential element update: {ast.unparse(node)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.30,
                            )
                        )
                        found = True
                        break
        return found

    def _calculate_confidence(self, evidence: list, has_required: bool) -> float:
        if not evidence or not has_required:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
