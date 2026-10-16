"""Detector for classic binary search over an ordered search space (array indices).

Detects the textbook binary search pattern: while left <= right loop with
midpoint calculation and boundary updates based on element comparison.

Does NOT detect answer-space binary search (feasibility-check based).
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BinarySearchClassicDetector(BaseDetector):
    pattern_id = "binary_search_standard"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_binary_search_while(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_binary_search_while(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with binary search structure.

        Core pattern:
            left, right = 0, len(arr) - 1
            while left <= right:
                mid = (left + right) // 2
                if arr[mid] == target:
                    return mid
                elif arr[mid] < target:
                    left = mid + 1
                else:
                    right = mid - 1
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            # Names and co-occurring statements are not sufficient: every
            # accepted form must link the interval, midpoint, ordered indexed
            # comparison, and midpoint-based updates in the same loop.
            if not self._has_linked_binary_search(node):
                continue

            has_midpoint = has_boundary_update = has_mid_comparison = False
            has_answer_space_check = False
            midpoint_description = "Midpoint calculation: (left + right) // 2"
            boundary_description = "Boundary update: left = mid + 1 or right = mid - 1"
            if self._is_binary_search_condition(node.test):
                has_midpoint = self._find_midpoint_calculation(node.body)
                has_boundary_update = self._find_boundary_update(node.body)
                has_mid_comparison = self._find_mid_comparison(node.body)
                has_answer_space_check = self._find_answer_space_check(node.body)

            # Retain the existing evidence descriptions for validated legacy
            # forms; additional names/syntax use the same structural gate.
            if not (has_midpoint and has_boundary_update and has_mid_comparison and not has_answer_space_check):
                has_midpoint = has_boundary_update = has_mid_comparison = True
                has_answer_space_check = False
                midpoint_description = "Midpoint derived by halving the current interval"
                boundary_description = "Both interval boundaries narrow from that midpoint under indexed comparison"

            if has_midpoint and has_boundary_update and has_mid_comparison and not has_answer_space_check:
                if has_midpoint:
                    evidence.append(
                        EvidenceItem(
                            type="binary_midpoint",
                            description=midpoint_description,
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )
                if has_boundary_update:
                    evidence.append(
                        EvidenceItem(
                            type="boundary_update",
                            description=boundary_description,
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                if has_mid_comparison:
                    evidence.append(
                        EvidenceItem(
                            type="mid_comparison",
                            description="Element comparison at mid index",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="left_right_boundary",
                        description="Binary search while loop with left/right boundaries",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _has_linked_binary_search(self, loop: ast.While) -> bool:
        test = loop.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)):
            return False
        if isinstance(test.ops[0], (ast.Lt, ast.LtE)):
            lower, upper = test.left.id, test.comparators[0].id
        elif isinstance(test.ops[0], (ast.Gt, ast.GtE)):
            lower, upper = test.comparators[0].id, test.left.id
        else:
            return False
        if lower == upper:
            return False

        for position, statement in enumerate(loop.body):
            if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id not in (lower, upper)
                    and self._midpoint_uses_bounds(statement.value, lower, upper)):
                continue
            midpoint = statement.targets[0].id
            following = loop.body[position + 1:]
            if any(isinstance(n, ast.Name) and n.id == midpoint and isinstance(n.ctx, (ast.Store, ast.Del))
                   for s in following for n in ast.walk(s)):
                continue
            if self._linked_comparison_updates(following, midpoint, lower, upper):
                return True
        return False

    @staticmethod
    def _midpoint_uses_bounds(value: ast.AST, lower: str, upper: str) -> bool:
        def is_half(node):
            return (isinstance(node, ast.BinOp) and isinstance(node.right, ast.Constant)
                    and type(node.right.value) is int and (
                        (isinstance(node.op, ast.FloorDiv) and node.right.value == 2)
                        or (isinstance(node.op, ast.RShift) and node.right.value == 1)
                    ))

        if is_half(value):
            operands = value.left
            return (isinstance(operands, ast.BinOp) and isinstance(operands.op, ast.Add)
                    and isinstance(operands.left, ast.Name) and isinstance(operands.right, ast.Name)
                    and {operands.left.id, operands.right.id} == {lower, upper})
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            for base, half in ((value.left, value.right), (value.right, value.left)):
                if isinstance(base, ast.Name) and base.id == lower and is_half(half):
                    difference = half.left
                    if (isinstance(difference, ast.BinOp) and isinstance(difference.op, ast.Sub)
                            and isinstance(difference.left, ast.Name) and difference.left.id == upper
                            and isinstance(difference.right, ast.Name) and difference.right.id == lower):
                        return True
        return False

    def _linked_comparison_updates(self, body: list, midpoint: str, lower: str, upper: str) -> bool:
        """Collect narrowing writes controlled by an ordered sequence[mid] comparison.

        Do not borrow evidence from separate conditions, nested loops/functions,
        or feasibility calls. Unknown writes to the bounds fail this new path.
        """
        updated = set()
        updated_sequences = set()

        def indexed_comparison(test):
            """Return the linked sequence and whether an ordered midpoint clause exists."""
            if isinstance(test, ast.Compare):
                operands = [test.left, *test.comparators]
                sequences, ordered_midpoint = set(), False
                for index, op in enumerate(test.ops):
                    if not isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)):
                        return None
                    reads = []
                    for value in operands[index:index + 2]:
                        if isinstance(value, (ast.Name, ast.Constant)):
                            continue
                        if not isinstance(value, ast.Subscript) or not isinstance(value.value, ast.Name):
                            return None
                        position = value.slice
                        direct = isinstance(position, ast.Name) and position.id in (midpoint, lower, upper)
                        adjacent = (isinstance(position, ast.BinOp) and isinstance(position.op, (ast.Add, ast.Sub))
                                    and isinstance(position.left, ast.Name) and position.left.id == midpoint
                                    and isinstance(position.right, ast.Constant) and type(position.right.value) is int
                                    and position.right.value == 1)
                        if not (direct or adjacent):
                            return None
                        reads.append(value)
                        sequences.add(value.value.id)
                    # Every chained clause must concern the same interval's sequence.
                    if not reads:
                        return None
                    if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                        ordered_midpoint |= any(isinstance(value.slice, ast.Name) and value.slice.id == midpoint
                                                for value in reads)
                return (next(iter(sequences)), ordered_midpoint) if len(sequences) == 1 else None
            if isinstance(test, ast.BoolOp):
                links = [indexed_comparison(value) for value in test.values]
                if not all(links) or len({link[0] for link in links}) != 1:
                    return None
                return links[0][0], any(link[1] for link in links)
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                return indexed_comparison(test.operand)
            return None

        def visit(statements, controlled=None):
            for statement in statements:
                if isinstance(statement, ast.If):
                    for node in ast.walk(statement.test):
                        if isinstance(node, ast.Call) and any(
                            isinstance(n, ast.Name) and n.id == midpoint
                            for arg in [*node.args, *(kw.value for kw in node.keywords)]
                            for n in ast.walk(arg)
                        ):
                            return False
                    indexed = indexed_comparison(statement.test)
                    if indexed and controlled:
                        # Only a linked guard on the same sequence may retain
                        # its parent's ordered evidence. Unknown guards reset it.
                        indexed = ((indexed[0], indexed[1] or controlled[1])
                                   if indexed[0] == controlled[0] else None)
                    if not (visit(statement.body, indexed)
                            and visit(statement.orelse, indexed)):
                        return False
                elif (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                      and isinstance(statement.targets[0], ast.Name)
                      and statement.targets[0].id in (lower, upper)):
                    target = statement.targets[0].id
                    value = statement.value
                    direct_upper = target == upper and isinstance(value, ast.Name) and value.id == midpoint
                    offset_update = (
                        isinstance(value, ast.BinOp)
                        and isinstance(value.left, ast.Name) and value.left.id == midpoint
                        and isinstance(value.right, ast.Constant) and type(value.right.value) is int
                        and value.right.value == 1
                        and ((target == lower and isinstance(value.op, ast.Add))
                             or (target == upper and isinstance(value.op, ast.Sub)))
                    )
                    if not controlled or not controlled[1] or not (direct_upper or offset_update):
                        return False
                    updated.add(target)
                    updated_sequences.add(controlled[0])
                elif any(isinstance(n, ast.Name) and n.id in (lower, upper)
                         and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(statement)):
                    return False
            return True

        return visit(body) and updated == {lower, upper} and len(updated_sequences) == 1

    def _is_binary_search_condition(self, test: ast.AST) -> bool:
        """Check if the while condition is a binary search pattern (left <= right or left < right)."""
        if not isinstance(test, ast.Compare):
            return False
        if len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], (ast.LtE, ast.Lt, ast.LtE, ast.GtE, ast.Gt)):
            return False
        if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name):
            left_id = test.left.id
            right_id = test.comparators[0].id
            if left_id in ("left", "low", "l", "lo", "start", "i") and right_id in ("right", "high", "r", "hi", "end", "j"):
                return True
            if left_id in ("right", "high", "r", "hi", "end", "j") and right_id in ("left", "low", "l", "lo", "start", "i"):
                return True
        return False

    def _find_midpoint_calculation(self, body: list) -> bool:
        """Check if the loop body contains a midpoint calculation.

        Matches: mid = (left + right) // 2  or  mid = left + (right - left) // 2
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in ("mid", "m", "middle", "pivot"):
                        val = stmt.value
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.FloorDiv):
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.Add):
                                return True
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.Sub):
                                return True
                            if isinstance(val.left, ast.Name):
                                return True
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.FloorDiv):
                                return True
                            if isinstance(val.left, ast.Name):
                                if isinstance(val.right, ast.BinOp) and isinstance(val.right.op, ast.FloorDiv):
                                    return True
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                            if isinstance(val.left, ast.Name) and isinstance(val.right, ast.Name):
                                return True
        return False

    def _find_boundary_update(self, body: list) -> bool:
        """Check if the loop body contains boundary updates.

        Matches: left = mid + 1  or  right = mid - 1
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in ("left", "low", "l", "lo", "right", "high", "r", "hi"):
                        val = stmt.value
                        if isinstance(val, ast.BinOp):
                            if isinstance(val.op, (ast.Add, ast.Sub)):
                                if isinstance(val.left, ast.Name) and val.left.id in ("mid", "m", "middle", "pivot"):
                                    return True
                                if isinstance(val.right, ast.Name) and val.right.id in ("mid", "m", "middle", "pivot"):
                                    return True
                                if isinstance(val.left, ast.Name) and val.left.id == target.id:
                                    if isinstance(val.right, ast.Constant) and isinstance(val.right.value, int):
                                        return True
        return False

    def _find_mid_comparison(self, body: list) -> bool:
        """Check that the loop body contains at least one If statement.

        Binary search always makes a decision based on mid via conditional
        branching. Without an If, the loop is just blindly shrinking boundaries
        (e.g., `mid = (left+right)//2; left = mid + 1`), which is not a real
        binary search and would be a false positive.
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                return True
        return False

    def _find_answer_space_check(self, body: list) -> bool:
        """Check if there's a feasibility function call (answer-space BS pattern).

        A function call with mid as argument in an if condition indicates
        answer-space binary search, not classic index-based binary search.
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                test = stmt.test
                if isinstance(test, ast.Call):
                    for arg in test.args:
                        if isinstance(arg, ast.Name) and arg.id in ("mid", "m", "middle", "pivot"):
                            return True
                if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                    if isinstance(test.operand, ast.Call):
                        for arg in test.operand.args:
                            if isinstance(arg, ast.Name) and arg.id in ("mid", "m", "middle", "pivot"):
                                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
