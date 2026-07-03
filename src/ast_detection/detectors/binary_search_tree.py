"""Detector for binary search tree (BST) operation patterns.

Detects BST-specific algorithms that rely on the BST ordering property:
left subtree values < node.val < right subtree values. Characteristic of
BST search, insertion, deletion, and validation problems.

Does NOT detect:
- Ordinary binary-tree traversal without BST comparisons
- Array-based binary search (no tree structure)
- Heap operations (no left/right BST ordering)
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BinarySearchTreeDetector(BaseDetector):
    pattern_id = "binary_search_tree"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_bst_patterns(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_bst_comparison = any(e.type == "bst_comparison" for e in evidence)
        has_bst_recursion = any(e.type == "bst_recursion" for e in evidence)

        detected = has_bst_comparison and has_bst_recursion

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_bst_patterns(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            has_bst_comparison = self._find_bst_comparison(node)
            has_bst_recursion = self._find_bst_recursion(node)
            has_min_max_constraint = self._find_min_max_constraint(node)
            has_bst_operation = self._find_bst_operation(node)

            if not has_bst_comparison and not has_bst_recursion:
                continue

            if has_bst_comparison:
                evidence.append(
                    EvidenceItem(
                        type="bst_comparison",
                        description="BST ordering comparison (val < node.val or val > node.val)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_bst_recursion:
                evidence.append(
                    EvidenceItem(
                        type="bst_recursion",
                        description="Recursive call with .left or .right child in BST context",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_min_max_constraint:
                evidence.append(
                    EvidenceItem(
                        type="min_max_constraint",
                        description="Min/max bound parameters for BST validation",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_bst_operation:
                evidence.append(
                    EvidenceItem(
                        type="bst_operation",
                        description="BST operation (search/insert/delete with BST ordering)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

    def _find_bst_comparison(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.If):
                test = child.test
                comparisons = []

                if isinstance(test, ast.Compare) and len(test.ops) == 1:
                    comparisons.append(test)
                elif isinstance(test, ast.BoolOp):
                    for value in test.values:
                        if isinstance(value, ast.Compare) and len(value.ops) == 1:
                            comparisons.append(value)

                for comp in comparisons:
                    if not isinstance(comp.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                        continue
                    left = comp.left
                    right = comp.comparators[0]
                    if self._is_val_attribute(left) or self._is_val_attribute(right):
                        return True
                    if self._is_val_name(left) or self._is_val_name(right):
                        return True
                    if isinstance(left, ast.Attribute) and isinstance(right, ast.Attribute):
                        if left.attr in ("val", "value", "key", "data") or right.attr in ("val", "value", "key", "data"):
                            return True
        return False

    def _is_val_attribute(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute) and node.attr in ("val", "value", "key", "data"):
            return True
        if isinstance(node, ast.Attribute):
            return self._is_val_attribute(node.value)
        return False

    def _is_val_name(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in ("val", "value", "key", "data"):
            return True
        return False

    def _find_bst_recursion(self, func_def: ast.FunctionDef) -> bool:
        func_name = func_def.name
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    for arg in child.args:
                        if isinstance(arg, ast.Attribute) and arg.attr in ("left", "right"):
                            for sub in ast.walk(func_def):
                                if isinstance(sub, ast.Compare) and len(sub.ops) == 1:
                                    if isinstance(sub.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                                        return True
                            return True
        return False

    def _find_min_max_constraint(self, func_def: ast.FunctionDef) -> bool:
        param_names = {arg.arg.lower() for arg in func_def.args.args}
        min_max_keywords = {"min", "max", "minimum", "maximum", "lower", "upper", "low", "high", "lo", "hi"}
        has_bounds_param = any(
            any(kw in pn for kw in min_max_keywords)
            for pn in param_names
        )
        if not has_bounds_param:
            return False
        for child in ast.walk(func_def):
            if isinstance(child, ast.Compare) and len(child.ops) == 1:
                if isinstance(child.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                    for side in (child.left, child.comparators[0]):
                        if isinstance(side, ast.Attribute) and side.attr in ("val", "value", "key", "data"):
                            return True
        return False

    def _find_bst_operation(self, func_def: ast.FunctionDef) -> bool:
        func_name = func_def.name.lower()
        operation_keywords = {"search", "insert", "delete", "remove", "find", "contains", "put", "add", "bst"}
        return any(kw in func_name for kw in operation_keywords)

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
