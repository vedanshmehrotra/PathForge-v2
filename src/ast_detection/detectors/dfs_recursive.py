"""Detector for recursive depth-first search (DFS) traversal pattern.

Detects both graph DFS (visited set + neighbor iteration) and tree DFS
(recursive calls with left/right children) as well as grid-based DFS
(Number of Islands style). Requires a recursive self-call combined with
some traversal context to fire.

Does NOT detect:
- Simple recursion without graph/tree traversal context (Fibonacci, etc.)
- Iterative DFS (explicit stack-based)
- BFS traversal patterns
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DFSRecursiveDetector(BaseDetector):
    pattern_id = "dfs_recursive"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_recursive_dfs(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_recursive_call = any(e.type == "recursive_call" for e in evidence)
        has_graph_traversal = any(e.type == "graph_traversal" for e in evidence)
        has_child_recursion = any(e.type == "child_recursion" for e in evidence)
        has_grid_expansion = any(e.type == "grid_expansion" for e in evidence)
        has_visited_tracking = any(e.type == "visited_tracking" for e in evidence)

        detected = has_recursive_call and (
            has_graph_traversal or has_child_recursion or has_grid_expansion or has_visited_tracking
        )

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_recursive_dfs(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            func_name = node.name

            if not self._find_recursive_call(node, func_name):
                continue

            has_recursive_call = True
            has_graph_traversal = self._find_graph_traversal(node)
            has_child_recursion = self._find_child_recursion(node, func_name)
            has_grid_expansion = self._find_grid_expansion(node, func_name)
            has_visited_tracking = self._find_visited_tracking(node)
            has_base_case = self._find_base_case(node)

            if has_recursive_call:
                evidence.append(
                    EvidenceItem(
                        type="recursive_call",
                        description=f"Recursive self-call to '{func_name}' found",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_graph_traversal:
                evidence.append(
                    EvidenceItem(
                        type="graph_traversal",
                        description="For-loop iteration over neighbors/children/adjacent nodes",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_child_recursion:
                evidence.append(
                    EvidenceItem(
                        type="child_recursion",
                        description="Recursive call with child attribute (.left or .right)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_grid_expansion:
                evidence.append(
                    EvidenceItem(
                        type="grid_expansion",
                        description="Multiple recursive calls with direction offsets (grid DFS)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_visited_tracking:
                evidence.append(
                    EvidenceItem(
                        type="visited_tracking",
                        description="Visited-tracking operations (visited.add, node in visited, etc.)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_base_case:
                evidence.append(
                    EvidenceItem(
                        type="base_case",
                        description="Base-case check for None/null in recursive function",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _find_recursive_call(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    return True
        return False

    def _find_graph_traversal(self, func_def: ast.FunctionDef) -> bool:
        neighbor_keywords = {"neighbor", "neighbors", "adjacent", "adj", "children", "child", "nbr"}
        for child in ast.walk(func_def):
            if isinstance(child, ast.For):
                if isinstance(child.target, ast.Name):
                    target_name = child.target.id.lower()
                    for kw in neighbor_keywords:
                        if kw in target_name or target_name in kw:
                            return True
                if isinstance(child.iter, ast.Attribute):
                    attr_name = child.iter.attr.lower()
                    for kw in neighbor_keywords:
                        if kw in attr_name or attr_name in kw:
                            return True
                if isinstance(child.iter, ast.Subscript):
                    if isinstance(child.iter.value, ast.Name):
                        name = child.iter.value.id.lower()
                        if any(gkw in name for gkw in ("graph", "adj", "tree", "node")):
                            return True
                    if isinstance(child.iter.slice, ast.Name):
                        name = child.iter.slice.id.lower()
                        if any(gkw in name for gkw in ("graph", "adj", "tree", "node")):
                            return True
        return False

    def _find_child_recursion(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    for arg in child.args:
                        if isinstance(arg, ast.Attribute) and arg.attr in ("left", "right"):
                            return True
                        if isinstance(arg, ast.Call):
                            if isinstance(arg.func, ast.Attribute) and arg.func.attr in ("left", "right"):
                                return True
        return False

    def _find_grid_expansion(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        direction_count = 0
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    for arg in child.args:
                        if isinstance(arg, ast.BinOp):
                            if isinstance(arg.op, (ast.Add, ast.Sub)):
                                right_one = (
                                    isinstance(arg.right, ast.Constant) and arg.right.value == 1
                                )
                                left_one = (
                                    isinstance(arg.left, ast.Constant) and arg.left.value == 1
                                )
                                if right_one or left_one:
                                    direction_count += 1
        return direction_count >= 3

    def _find_visited_tracking(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        name = child.func.value.id.lower()
                        if "visited" in name or "seen" in name:
                            if child.func.attr in ("add", "append", "discard"):
                                return True
            if isinstance(child, ast.Compare):
                for comp in child.comparators:
                    if isinstance(comp, ast.Name):
                        name = comp.id.lower()
                        if "visited" in name or "seen" in name:
                            return True
                if isinstance(child.left, ast.Name):
                    name = child.left.id.lower()
                    if "visited" in name or "seen" in name:
                        return True
            if isinstance(child, ast.BinOp):
                if isinstance(child.op, (ast.In, ast.NotIn)):
                    if isinstance(child.right, ast.Name):
                        name = child.right.id.lower()
                        if "visited" in name or "seen" in name:
                            return True
            if isinstance(child, ast.Subscript):
                if isinstance(child.value, ast.Name):
                    name = child.value.id.lower()
                    if "visited" in name or "seen" in name:
                        return True
        return False

    def _find_base_case(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.If):
                test = child.test
                if isinstance(test, ast.Compare):
                    if len(test.ops) == 1 and isinstance(test.ops[0], (ast.Is, ast.IsNot, ast.Eq, ast.NotEq)):
                        if isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
                            return True
                        if isinstance(test.left, ast.Constant) and test.left.value is None:
                            return True
                if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                    if isinstance(test.operand, ast.Name):
                        return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
