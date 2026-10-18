"""Detector for backtracking permutation generation pattern.

Detects recursive permutation generation algorithms using either:
1. Swap/recurse/swap pattern (in-place permutation)
2. Visited-array pattern (used-element tracking)

Does NOT detect:
- Subset generation (append/pop based)
- Ordinary recursion without permutation-specific patterns
- Iterative permutation generation
"""

import ast
from src.ast_detection.python_structure import recursive_calls, scope_nodes
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BacktrackingPermutationDetector(BaseDetector):
    pattern_id = "backtracking_permutation"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_backtracking_permutation(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_swap_recurse_swap = any(e.type == "swap_recurse_swap" for e in evidence)
        has_visited_array = any(e.type == "visited_array" for e in evidence)
        has_permutation = any(e.type == "permutation_generation" for e in evidence)
        has_exploration = any(e.type == "recursive_exploration" for e in evidence)

        detected = has_swap_recurse_swap or (has_visited_array and has_permutation)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_backtracking_permutation(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            func_name = node.name

            calls = recursive_calls(ast_root, node)
            if not calls:
                continue

            has_swap = self._find_swap_recurse_swap(node, calls)
            has_visited = self._find_visited_array(node)
            has_perm = self._find_permutation_generation(node)
            has_explore = self._find_recursive_exploration(calls)

            if not (has_swap or has_visited):
                continue

            if has_swap:
                evidence.append(
                    EvidenceItem(
                        type="swap_recurse_swap",
                        description="Swap/recurse/swap pattern for in-place permutation",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_visited:
                evidence.append(
                    EvidenceItem(
                        type="visited_array",
                        description="Visited/used boolean array for tracking selected elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_perm:
                evidence.append(
                    EvidenceItem(
                        type="permutation_generation",
                        description="Building permutation result by appending elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_explore:
                evidence.append(
                    EvidenceItem(
                        type="recursive_exploration",
                        description="Recursive call with incremented index",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _find_swap_recurse_swap(self, func_def, calls) -> bool:
        # Reversible swaps and the bound recursive call must occur in order in
        # one range-driven branch, not in disconnected functions or loops.
        def swap(statement):
            if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], (ast.Tuple, ast.List))
                    and isinstance(statement.value, (ast.Tuple, ast.List))):
                return None
            targets, values = statement.targets[0].elts, statement.value.elts
            if not (len(targets) == len(values) == 2
                    and all(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) for t in targets)
                    and targets[0].value.id == targets[1].value.id):
                return None
            shape = lambda n: ast.dump(n, include_attributes=False).replace("ctx=Store()", "ctx=Load()")
            if shape(targets[0]) == shape(targets[1]):
                return None
            if [shape(t) for t in targets] == [shape(v) for v in reversed(values)]:
                return ast.dump(statement, include_attributes=False)
            return None

        for loop in scope_nodes(func_def.body):
            if not (isinstance(loop, ast.For) and isinstance(loop.iter, ast.Call)
                    and isinstance(loop.iter.func, ast.Name) and loop.iter.func.id == "range"
                    and isinstance(loop.target, ast.Name) and len(loop.iter.args) == 2
                    and isinstance(loop.iter.args[0], ast.Name)):
                continue
            first = loop.iter.args[0].id
            def advances(call):
                parameters = [*func_def.args.posonlyargs, *func_def.args.args]
                if isinstance(call.func, ast.Attribute):
                    parameters = parameters[1:]
                names = [p.arg for p in parameters]
                if any(isinstance(a, ast.Starred) for a in call.args) or len(call.args) > len(names):
                    return False
                arguments = dict(zip(names, call.args))
                for keyword in call.keywords:
                    if keyword.arg not in names or keyword.arg in arguments:
                        return False
                    arguments[keyword.arg] = keyword.value
                value = arguments.get(first)
                return (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)
                        and any(isinstance(a, ast.Name) and a.id == first
                                and isinstance(b, ast.Constant) and type(b.value) is int and b.value == 1
                                for a, b in ((value.left, value.right), (value.right, value.left))))
            for i, statement in enumerate(loop.body):
                before = swap(statement)
                if before is None:
                    continue
                indices = statement.targets[0].elts
                if not all(isinstance(t.slice, ast.Name) for t in indices) or {
                    t.slice.id for t in indices
                } != {first, loop.target.id}:
                    continue
                for j in range(i + 2, len(loop.body)):
                    if swap(loop.body[j]) == before and any(
                        advances(call) and call in scope_nodes(loop.body[i+1:j]) for call in calls
                    ):
                        return True
        return False

    def _find_visited_array(self, func_def: ast.FunctionDef) -> bool:
        for child in scope_nodes(func_def.body):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(kw in name for kw in ("used", "visited", "seen", "taken", "chosen", "cols")):
                            val = child.value
                            if isinstance(val, ast.List):
                                for elt in val.elts:
                                    if isinstance(elt, ast.Constant) and elt.value is False:
                                        return True
                            if isinstance(val, ast.ListComp):
                                return True
                            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mult):
                                if isinstance(val.left, ast.List):
                                    for elt in val.left.elts:
                                        if isinstance(elt, ast.Constant) and elt.value is False:
                                            return True
            if isinstance(child, ast.Subscript):
                if isinstance(child.value, ast.Name):
                    name = child.value.id.lower()
                    if any(kw in name for kw in ("used", "visited", "seen", "taken", "cols")):
                        return True
        return False

    def _find_permutation_generation(self, func_def: ast.FunctionDef) -> bool:
        for child in scope_nodes(func_def.body):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == "append":
                    if isinstance(child.func.value, ast.Name):
                        name = child.func.value.id.lower()
                        if any(kw in name for kw in ("perm", "res", "result", "path", "sol", "curr")):
                            return True
        return False

    def _find_recursive_exploration(self, calls) -> bool:
        return any(isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)
                   and any(isinstance(v, ast.Constant) and v.value == 1 for v in (arg.left, arg.right))
                   for call in calls for arg in call.args)

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
