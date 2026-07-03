"""Detector for iterative depth-first search (DFS) using an explicit stack.

Detects graph and tree DFS implemented with an explicit stack variable,
where nodes are popped and their children/neighbors pushed. The key
distinction from monotonic stack patterns is the absence of comparison-
driven pops and the presence of child/neighbor iteration after popping.

Does NOT detect:
- Recursive DFS (detected by dfs_recursive)
- Monotonic stack patterns (comparison-driven pop)
- BFS queue patterns (popleft-based)
- Simple stack usage without traversal context
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DFSIterativeDetector(BaseDetector):
    pattern_id = "dfs_iterative"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_iterative_dfs(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_explicit_stack = any(e.type == "explicit_stack" for e in evidence)
        has_stack_traversal = any(e.type == "stack_traversal" for e in evidence)
        has_visited_tracking = any(e.type == "visited_tracking" for e in evidence)
        has_child_push = any(e.type == "child_push" for e in evidence)

        detected = has_explicit_stack and (
            has_stack_traversal or has_child_push or has_visited_tracking
        )

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_iterative_dfs(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            stack_var = self._find_stack_initialized_before(ast_root, node)
            if stack_var is None:
                continue

            has_stack_pop = self._find_stack_pop_in_while(node, stack_var)
            if not has_stack_pop:
                continue

            has_child_push = self._find_child_push_in_while(node, stack_var)
            visited_tracking = self._find_visited_in_while(node)
            stack_traversal = self._find_stack_traversal(node, stack_var)
            has_comparison_pop = self._find_comparison_driven_pop(node, stack_var)

            if has_comparison_pop:
                continue

            evidence.append(
                EvidenceItem(
                    type="explicit_stack",
                    description=f"Explicit stack variable '{stack_var}' used with while loop",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.35,
                )
            )

            if stack_traversal:
                evidence.append(
                    EvidenceItem(
                        type="stack_traversal",
                        description=f"Pop from '{stack_var}' followed by child/neighbor iteration",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_child_push:
                evidence.append(
                    EvidenceItem(
                        type="child_push",
                        description=f"Children/neighbors pushed onto '{stack_var}' after pop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if visited_tracking:
                evidence.append(
                    EvidenceItem(
                        type="visited_tracking",
                        description="Visited set used to avoid revisiting nodes",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _find_stack_initialized_before(self, root: ast.AST, target_while: ast.While) -> str | None:
        for stmt in getattr(root, "body", []):
            if stmt is target_while:
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id != "self":
                        val = stmt.value
                        if isinstance(val, ast.List):
                            return target.id
                        if isinstance(val, ast.Call):
                            if isinstance(val.func, ast.Name) and val.func.id in ("list", "deque"):
                                return target.id
            elif isinstance(stmt, ast.FunctionDef):
                result = self._find_stack_initialized_before(stmt, target_while)
                if result:
                    return result
        return None

    def _find_stack_pop_in_while(self, while_node: ast.While, stack_var: str) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == stack_var:
                        if stmt.func.attr == "pop":
                            return True
        return False

    def _find_child_push_in_while(self, while_node: ast.While, stack_var: str) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == stack_var:
                        if stmt.func.attr in ("append", "extend"):
                            return True
        return False

    def _find_stack_traversal(self, while_node: ast.While, stack_var: str) -> bool:
        for stmt in ast.walk(ast.Module(body=while_node.body)):
            if isinstance(stmt, (ast.For, ast.While)):
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            if isinstance(child.func.value, ast.Name) and child.func.value.id == stack_var:
                                if child.func.attr in ("append", "extend"):
                                    return True
                target_keywords = {"neighbor", "neighbors", "child", "children", "adjacent", "adj", "nbr"}
                if isinstance(stmt, ast.For):
                    if isinstance(stmt.target, ast.Name):
                        name = stmt.target.id.lower()
                        for kw in target_keywords:
                            if kw in name:
                                return True
                    if isinstance(stmt.iter, ast.Attribute):
                        attr_name = stmt.iter.attr.lower()
                        for kw in target_keywords:
                            if kw in attr_name:
                                return True
                    if isinstance(stmt.iter, ast.Subscript):
                        if isinstance(stmt.iter.value, ast.Name):
                            name = stmt.iter.value.id.lower()
                            if any(gkw in name for gkw in ("graph", "adj", "tree", "node")):
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

    def _find_comparison_driven_pop(self, while_node: ast.While, stack_var: str) -> bool:
        body_module = ast.Module(body=while_node.body)

        for sub in ast.walk(body_module):
            if isinstance(sub, ast.While):
                for sub2 in ast.walk(sub):
                    if isinstance(sub2, ast.Name) and sub2.id == stack_var:
                        for sub3 in ast.walk(sub):
                            if isinstance(sub3, ast.Call):
                                if isinstance(sub3.func, ast.Attribute):
                                    if isinstance(sub3.func.value, ast.Name) and sub3.func.value.id == stack_var:
                                        if sub3.func.attr == "pop":
                                            for sub4 in ast.walk(sub):
                                                if isinstance(sub4, ast.Compare):
                                                    for op in sub4.ops:
                                                        if isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                                                            return True
                        break

        for sub in ast.walk(while_node.test):
            if isinstance(sub, ast.Compare):
                for op in sub.ops:
                    if isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                        for sub2 in ast.walk(while_node.test):
                            if isinstance(sub2, ast.Name) and sub2.id == stack_var:
                                for sub3 in ast.walk(body_module):
                                    if isinstance(sub3, ast.Call):
                                        if isinstance(sub3.func, ast.Attribute):
                                            if isinstance(sub3.func.value, ast.Name) and sub3.func.value.id == stack_var:
                                                if sub3.func.attr == "pop":
                                                    return True

        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
