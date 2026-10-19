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
from src.ast_detection.queue_links import queue_features
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

            facts = queue_features(node)
            queue_var = facts['queue']
            if queue_var is None:
                continue

            has_popleft = self._find_popleft_in_while(node, queue_var)
            if not has_popleft:
                continue

            has_child_enqueue = facts['expansion']
            has_level_tracking = facts['level']
            has_deque_import = self._find_deque_import(ast_root)
            has_distance = facts['distance']
            has_visited = facts['visited']

            if not has_child_enqueue or has_distance or has_visited:
                continue

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
