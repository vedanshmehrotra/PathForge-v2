"""Detector for two pointers opposite direction pattern.

Detects left/right converging pointer patterns where one pointer
starts at the beginning and the other at the end, moving toward
each other based on comparisons.

Does NOT detect same-direction (slow/fast) two-pointer patterns.
"""

import ast
from src.ast_detection.python_structure import assignment_values, bindings, scope_nodes
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class TwoPointersOppositeDetector(BaseDetector):
    pattern_id = "two_pointers_opposite"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_convergence_loop(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_convergence_loop(self, ast_root, evidence):
        for loop in ast.walk(ast_root):
            test = getattr(loop, 'test', None)
            if not (isinstance(loop, ast.While) and isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], (ast.Lt, ast.LtE)) and isinstance(test.left, ast.Name)
                    and isinstance(test.comparators[0], ast.Name) and test.left.id != test.comparators[0].id):
                continue
            lower, upper = test.left.id, test.comparators[0].id
            updates = {lower: [], upper: []}
            allowed = {lower: set(), upper: set()}
            def scan(body):
                for statement in body:
                    if isinstance(statement, ast.If):
                        scan(statement.body)
                        scan(statement.orelse)
                    elif isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name):
                        if statement.target.id in updates:
                            updates[statement.target.id].append((statement.op, statement.value))
                            allowed[statement.target.id].add(statement.target)
                    else:
                        for key, value in assignment_values(statement).items():
                            if key in updates:
                                allowed[key].update(n for n in scope_nodes([statement]) if isinstance(n, ast.Name)
                                                    and isinstance(n.ctx, ast.Store) and n.id == key)
                                if (isinstance(value, ast.BinOp) and isinstance(value.left, ast.Name)
                                        and value.left.id == key):
                                    updates[key].append((value.op, value.right))
                                else:
                                    updates[key].append((None, None))
            scan(loop.body)
            def direction(key, operator):
                return bool(updates[key]) and all(isinstance(op, operator) and isinstance(v, ast.Constant)
                    and type(v.value) is int and v.value > 0 for op, v in updates[key])
            if not (direction(lower, ast.Add) and direction(upper, ast.Sub)):
                continue
            if any(set(bindings(loop.body, key)) != allowed[key] for key in updates):
                continue
            for kind, description, weight in [
                ('left_pointer_increment', f"Lower pointer '{lower}' advances", 0.25),
                ('right_pointer_decrement', f"Upper pointer '{upper}' retreats", 0.25),
                ('convergence_loop', f"Compared pointers '{lower}' and '{upper}' converge in this loop", 0.40),
            ]:
                evidence.append(EvidenceItem(type=kind, description=description,
                    location=f'{loop.lineno}:{loop.col_offset}', weight=weight))


    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
