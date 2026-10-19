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
from src.ast_detection.queue_links import queue_features
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
        has_expansion = any(e.type == "neighbor_expansion" for e in evidence)

        detected = has_queue_traversal and has_expansion and (
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

            facts = queue_features(node)
            queue_var = facts['queue']
            if queue_var is None:
                continue

            has_popleft = self._find_popleft_in_while(node, queue_var)
            if not has_popleft:
                continue

            has_distance_tracking = facts['distance']
            has_visited_set = facts['visited']
            has_neighbor_expansion = facts['expansion']
            has_level_for_loop = facts['level']

            if not has_neighbor_expansion or not (has_distance_tracking or has_visited_set):
                continue

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


    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
