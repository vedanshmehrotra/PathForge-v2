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
from src.ast_detection.python_structure import recursive_calls, scope_nodes
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

            calls = recursive_calls(ast_root, node)
            if not calls:
                continue

            has_recursive_call = True
            has_graph_traversal = self._find_graph_traversal(node, calls)
            has_child_recursion = self._find_child_recursion(calls)
            has_grid_expansion = self._find_grid_expansion(calls)
            has_visited_tracking = self._find_visited_tracking(node)
            has_base_case = self._find_base_case(node)

            method_calls = any(isinstance(c.func, ast.Attribute) for c in calls)
            if method_calls and has_grid_expansion:
                grids = {n.value.value.id for n in scope_nodes(node.body)
                         if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Subscript)
                         and isinstance(n.value.value, ast.Name)}
                has_grid_expansion = any(isinstance(a, ast.Name) and a.id in grids
                                         for c in calls for a in c.args)
            if not (has_graph_traversal or has_child_recursion or has_grid_expansion
                    ):
                continue

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

    def _find_graph_traversal(self, func_def, calls):
        parameters = {a.arg for a in func_def.args.args}
        for loop in scope_nodes(func_def.body):
            if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name):
                continue
            inside = set(scope_nodes(loop.body))
            linked = [c for c in calls if c in inside and any(
                isinstance(a, ast.Name) and a.id == loop.target.id for a in c.args)]
            if not linked:
                continue
            # Adjacency-list or child-collection iteration indexed by the
            # current recursive parameter; no keyword or unrelated loop.
            if (isinstance(loop.iter, ast.Subscript) and isinstance(loop.iter.slice, ast.Name)
                    and loop.iter.slice.id in parameters):
                return True
            if (isinstance(loop.iter, ast.Attribute) and loop.iter.attr in ('neighbors', 'children', 'adjacent')
                    and isinstance(loop.iter.value, ast.Name) and loop.iter.value.id in parameters):
                return True
            # Adjacency-matrix expansion: the guard must read the current
            # parameter's row at the recursively visited candidate column.
            for guard in scope_nodes(loop.body):
                if not isinstance(guard, ast.If) or not any(c in scope_nodes(guard.body) for c in linked):
                    continue
                if any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Subscript)
                       and isinstance(n.value.slice, ast.Name) and n.value.slice.id in parameters
                       and isinstance(n.slice, ast.Name) and n.slice.id == loop.target.id
                       for n in ast.walk(guard.test)):
                    return True
        return False

    def _find_child_recursion(self, calls) -> bool:
        for call in calls:
            for arg in call.args:
                if isinstance(arg, ast.Attribute) and arg.attr in ("left", "right"):
                    return True
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr in ("left", "right"):
                    return True
        return False

    def _find_grid_expansion(self, calls) -> bool:
        direction_count = 0
        for call in calls:
            for arg in call.args:
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Sub)):
                    if any(isinstance(v, ast.Constant) and v.value == 1 for v in (arg.left, arg.right)):
                        direction_count += 1
        return direction_count >= 3

    def _find_visited_tracking(self, func_def):
        parameters = {a.arg for a in func_def.args.args}
        for child in scope_nodes(func_def.body):
            if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                    and child.func.attr in ('add', 'append') and any(
                        isinstance(a, ast.Name) and a.id in parameters for a in child.args)):
                return True
            if isinstance(child, ast.Assign) and any(
                isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Name)
                and t.slice.id in parameters for t in child.targets):
                return True
        return False

    def _find_base_case(self, func_def: ast.FunctionDef) -> bool:
        for child in scope_nodes(func_def.body):
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
