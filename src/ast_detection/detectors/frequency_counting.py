"""Detector for frequency_counting pattern.

Detects frequency counting using dictionaries or Counter/defaultdict.
Requires the increment pattern (counter[x] = counter.get(x, 0) + 1) or
Counter import combined with dict creation and a loop.

An empty dict alone or dict + loop without counting does NOT trigger.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class FrequencyCountingDetector(BaseDetector):
    pattern_id = "hash_map_frequency"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        has_dict = self._detect_dict_for_counting(ast_root, evidence)
        has_increment = self._detect_increment_pattern(ast_root, evidence)
        has_loop = self._detect_counting_loop(ast_root, evidence)
        has_counter = self._detect_counter_import(ast_root, evidence)
        has_counter_call = self._detect_counter_constructor_call(ast_root, evidence)

        has_counting_core = has_increment or (has_counter and (has_loop or has_counter_call))
        has_required_signals = has_counting_core and (has_dict or has_counter or has_increment)
        confidence = self._calculate_confidence(evidence, has_required_signals)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence if has_required_signals else [],
            detected=confidence > 0.0,
        )

    def _detect_dict_for_counting(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Dict):
                            if len(node.value.keys) == 0:
                                evidence.append(
                                    EvidenceItem(
                                        type="empty_dict_creation",
                                        description=f"Empty dictionary for counting: {target.id} = {{}}",
                                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                        weight=0.25,
                                    )
                                )
                                found = True
                        elif isinstance(node.value, ast.Call):
                            if isinstance(node.value.func, ast.Name):
                                if node.value.func.id == "dict":
                                    evidence.append(
                                        EvidenceItem(
                                            type="dict_constructor",
                                            description=f"Dictionary constructor for counting: {target.id} = dict()",
                                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                            weight=0.25,
                                        )
                                    )
                                    found = True
        return found

    def _detect_increment_pattern(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        try:
                            lhs_name = target.value.id if isinstance(target.value, ast.Name) else None
                            rhs = node.value
                            if (isinstance(rhs, ast.BinOp) and isinstance(rhs.op, ast.Add)):
                                if isinstance(rhs.left, ast.Call) and isinstance(rhs.left.func, ast.Attribute):
                                    get_call = rhs.left
                                    if get_call.func.attr == "get" and isinstance(get_call.func.value, ast.Name):
                                        call_obj = get_call.func.value.id
                                        if lhs_name and call_obj == lhs_name:
                                            evidence.append(
                                                EvidenceItem(
                                                    type="frequency_increment",
                                                    description=f"Frequency increment pattern: {ast.unparse(node)}",
                                                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                                    weight=0.35,
                                                )
                                            )
                                            found = True
                        except Exception:
                            pass
        return found

    def _detect_counting_loop(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.For):
                evidence.append(
                    EvidenceItem(
                        type="counting_loop",
                        description=f"Loop over elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                        weight=0.20,
                    )
                )
                found = True
                break
        return found

    def _detect_counter_import(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.ImportFrom):
                if node.module == "collections":
                    for alias in node.names:
                        if alias.name in ("Counter", "defaultdict"):
                            evidence.append(
                                EvidenceItem(
                                    type="counter_import",
                                    description=f"Import of {alias.name} from collections",
                                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                    weight=0.20,
                                )
                            )
                            found = True
        return found

    def _detect_counter_constructor_call(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("Counter", "defaultdict") and len(node.args) > 0:
                    evidence.append(
                        EvidenceItem(
                            type="counter_constructor",
                            description=f"Counter/defaultdict constructor call",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.30,
                        )
                    )
                    found = True
        return found

    def _calculate_confidence(self, evidence: list, has_required: bool) -> float:
        if not evidence or not has_required:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
