"""Detector for BFS shortest path in graphs.

Detects BFS-based shortest path algorithms using queue traversal,
distance tracking, and visited sets. Characteristic of shortest path
in unweighted graphs, word ladder minimum steps, and rotten oranges
distance problems.

Does NOT detect:
- Tree BFS level-order traversal (no distance tracking, no visited set)
- Non-BFS queue usage
- Dijkstra or weighted shortest path (uses heapq, not deque)
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BFSShortestPathDetector(BaseDetector):
    pattern_id = "bfs_shortest_path"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_bfs_shortest_path(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_queue_traversal = any(e.type == "queue_traversal" for e in evidence)
        has_distance_tracking = any(e.type == "distance_tracking" for e in evidence)
        has_visited_set = any(e.type == "visited_set" for e in evidence)

        detected = has_queue_traversal and (
            has_distance_tracking or has_visited_set
        )

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_bfs_shortest_path(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            queue_var = self._find_queue_var_in_while(node)
            if queue_var is None:
                continue

            has_popleft = self._find_popleft_in_while(node, queue_var)
            if not has_popleft:
                continue

            has_distance_tracking = self._find_distance_tracking(node)
            has_visited_set = self._find_visited_in_while(node)
            has_neighbor_expansion = self._find_neighbor_expansion(node)
            has_level_for_loop = self._find_level_for_loop(node)

            evidence.append(
                EvidenceItem(
                    type="queue_traversal",
                    description=f"BFS queue traversal with '{queue_var}' and popleft",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.30,
                )
            )

            if has_distance_tracking:
                evidence.append(
                    EvidenceItem(
                        type="distance_tracking",
                        description="Distance/step tracking variable incremented per level",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_visited_set:
                evidence.append(
                    EvidenceItem(
                        type="visited_set",
                        description="Visited set used to avoid reprocessing nodes",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_neighbor_expansion:
                evidence.append(
                    EvidenceItem(
                        type="neighbor_expansion",
                        description="Iteration over neighbors/adjacent nodes for graph expansion",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_level_for_loop:
                evidence.append(
                    EvidenceItem(
                        type="level_for_loop",
                        description="For-loop over current level size for level-by-level processing",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
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
                        if stmt.func.attr in ("popleft",):
                            return True
                        if stmt.func.attr == "pop":
                            if stmt.args and len(stmt.args) == 1:
                                if isinstance(stmt.args[0], ast.Constant) and stmt.args[0].value == 0:
                                    return True
        return False

    def _find_distance_tracking(self, while_node: ast.While) -> bool:
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
                            if isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
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
        for child in ast.walk(while_node):
            if isinstance(child, ast.Name):
                name = child.id.lower()
                if "visited" in name or "seen" in name:
                    if isinstance(child.ctx, ast.Store):
                        return True
        return False

    def _find_neighbor_expansion(self, while_node: ast.While) -> bool:
        target_keywords = {"neighbor", "neighbors", "adjacent", "adj", "nbr", "next_node"}
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.For):
                if isinstance(stmt.target, ast.Name):
                    name = stmt.target.id.lower()
                    for kw in target_keywords:
                        if kw in name or name in kw:
                            return True
                if isinstance(stmt.iter, ast.Subscript):
                    if isinstance(stmt.iter.value, ast.Name):
                        name = stmt.iter.value.id.lower()
                        if any(gkw in name for gkw in ("graph", "adj", "tree", "node", "neighbor")):
                            return True
                if isinstance(stmt.iter, ast.Attribute):
                    attr_name = stmt.iter.attr.lower()
                    for kw in target_keywords:
                        if kw in attr_name or attr_name in kw:
                            return True
        return False

    def _find_level_for_loop(self, while_node: ast.While) -> bool:
        for stmt in while_node.body:
            if isinstance(stmt, ast.For):
                if isinstance(stmt.iter, ast.Call):
                    if isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "range":
                        for arg in stmt.iter.args:
                            if isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name) and arg.func.id == "len":
                                    return True
                            if isinstance(arg, ast.Attribute) and arg.attr == "len":
                                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
