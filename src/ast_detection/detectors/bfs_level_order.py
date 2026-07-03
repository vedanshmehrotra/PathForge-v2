"""Detector for breadth-first search level-order traversal pattern.

Detects BFS implemented with a deque/queue where nodes are processed
level by level. Characteristic of binary tree level-order traversal,
N-ary tree level-order, and zigzag level-order problems.

Does NOT detect:
- BFS shortest path in graphs (distance tracking, visited set)
- Monotonic deque patterns (comparison-driven pop)
- Generic queue usage without level-based processing
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BFSLevelOrderDetector(BaseDetector):
    pattern_id = "bfs_level_order"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_bfs_level_order(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_queue_popleft = any(e.type == "queue_popleft" for e in evidence)
        has_child_enqueue = any(e.type == "child_enqueue" for e in evidence)
        has_distance_tracking = any(e.type == "distance_tracking" for e in evidence)
        has_visited_tracking = any(e.type == "visited_tracking" for e in evidence)

        detected = has_queue_popleft and has_child_enqueue and not has_distance_tracking and not has_visited_tracking

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_bfs_level_order(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            queue_var = self._find_queue_var_in_while(node)
            if queue_var is None:
                continue

            has_popleft = self._find_popleft_in_while(node, queue_var)
            if not has_popleft:
                continue

            has_child_enqueue = self._find_child_enqueue(node, queue_var)
            has_level_tracking = self._find_level_tracking(node)
            has_deque_import = self._find_deque_import(ast_root)
            has_distance = self._find_distance_tracking_any(node)
            has_visited = self._find_visited_in_while(node)

            evidence.append(
                EvidenceItem(
                    type="queue_popleft",
                    description=f"Popleft from '{queue_var}' in while loop",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.35,
                )
            )

            if has_child_enqueue:
                evidence.append(
                    EvidenceItem(
                        type="child_enqueue",
                        description=f"Children appended to '{queue_var}' in loop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_level_tracking:
                evidence.append(
                    EvidenceItem(
                        type="level_tracking",
                        description="Level-by-level processing with level-size measurement",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_deque_import:
                evidence.append(
                    EvidenceItem(
                        type="deque_import",
                        description="Deque imported from collections",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_distance:
                evidence.append(
                    EvidenceItem(
                        type="distance_tracking",
                        description="Distance/step tracking found (shortest path BFS)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.10,
                    )
                )

            if has_visited:
                evidence.append(
                    EvidenceItem(
                        type="visited_tracking",
                        description="Visited set found (graph BFS)",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.10,
                    )
                )

    def _find_queue_var_in_while(self, while_node: ast.While) -> str | None:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if stmt.func.attr in ("popleft", "pop"):
                        if isinstance(stmt.func.value, ast.Name):
                            return stmt.func.value.id
        return None

    def _find_popleft_in_while(self, while_node: ast.While, queue_var: str) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == queue_var:
                        if stmt.func.attr in ("popleft", "pop"):
                            if stmt.func.attr == "pop":
                                if stmt.args and len(stmt.args) == 1:
                                    if isinstance(stmt.args[0], ast.Constant) and stmt.args[0].value == 0:
                                        return True
                            else:
                                return True
        return False

    def _find_child_enqueue(self, while_node: ast.While, queue_var: str) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == queue_var:
                        if stmt.func.attr in ("append", "extend"):
                            for arg in stmt.args:
                                if isinstance(arg, ast.Attribute) and arg.attr in ("left", "right", "children", "child"):
                                    return True
                                if isinstance(arg, ast.IfExp):
                                    return True
                            return True
        return False

    def _find_level_tracking(self, while_node: ast.While) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name) and stmt.func.id == "len":
                    return True
                if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "len":
                    return True
            if isinstance(stmt, ast.For):
                if isinstance(stmt.iter, ast.Call):
                    if isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "range":
                        for arg in stmt.iter.args:
                            if isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name) and arg.func.id == "len":
                                    return True
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if "level" in name or "size" in name or "depth" in name:
                            return True
        return False

    def _find_distance_tracking_any(self, while_node: ast.While) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    name = stmt.target.id.lower()
                    if any(kw in name for kw in ("distance", "step", "level", "depth", "dist", "minute")):
                        if isinstance(stmt.op, (ast.Add, ast.Sub)):
                            return True
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(kw in name for kw in ("distance", "step", "level", "depth", "dist", "minute")):
                            if isinstance(stmt.value, ast.BinOp):
                                if isinstance(stmt.value.op, (ast.Add, ast.Sub)):
                                    return True
        return False

    def _find_visited_in_while(self, while_node: ast.While) -> bool:
        for child in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        name = child.func.value.id.lower()
                        if "visited" in name or "seen" in name:
                            if child.func.attr in ("add", "append", "discard"):
                                return True
            if isinstance(child, ast.BinOp):
                if isinstance(child.op, (ast.In, ast.NotIn)):
                    if isinstance(child.right, ast.Name):
                        name = child.right.id.lower()
                        if "visited" in name or "seen" in name:
                            return True
        return False

    def _find_deque_import(self, ast_root: ast.AST) -> bool:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "collections":
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "collections":
                    for alias in node.names:
                        if alias.name == "deque":
                            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
