"""Detector for hash_map_lookup pattern.

Detects dictionary/set creation combined with membership checking in a loop
context to identify hash map lookup patterns.

Requires ALL THREE core signals before detection:
1. Dict/set creation
2. Membership check (in / not in)
3. Loop structure providing lookup context

A dict used for configuration or membership check without a loop does NOT fire.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class HashMapLookupDetector(BaseDetector):
    pattern_id = "hash_map_lookup"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        has_dict = self._detect_dict_creation(ast_root, evidence)
        has_membership = self._detect_membership_check(ast_root, evidence)
        has_loop = self._detect_loop_structure(ast_root, evidence)

        has_required_signals = has_dict and has_membership and has_loop
        confidence = self._calculate_confidence(evidence, has_required_signals)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence if has_required_signals else [],
            detected=confidence > 0.0,
        )

    def _detect_dict_creation(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        value = node.value
                        if isinstance(value, ast.Dict) and len(value.keys) == 0:
                            evidence.append(
                                EvidenceItem(
                                    type="dict_creation",
                                    description=f"Empty dictionary creation: {target.id} = {{}}",
                                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                    weight=0.25,
                                )
                            )
                            found = True
                        elif isinstance(value, ast.Call):
                            if isinstance(value.func, ast.Name) and value.func.id in ("dict", "set"):
                                evidence.append(
                                    EvidenceItem(
                                        type=f"{value.func.id}_creation",
                                        description=f"{value.func.id.capitalize()} creation: {ast.unparse(node)}",
                                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                        weight=0.25,
                                    )
                                )
                                found = True
                        elif isinstance(value, ast.DictComp):
                            evidence.append(
                                EvidenceItem(
                                    type="dict_comp_creation",
                                    description=f"Dict comprehension creation: {ast.unparse(node)}",
                                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                    weight=0.20,
                                )
                            )
                            found = True
        return found

    def _detect_membership_check(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Compare):
                has_in = any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)
                if has_in:
                    evidence.append(
                        EvidenceItem(
                            type="membership_check",
                            description=f"Membership check: {ast.unparse(node)}",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.35,
                        )
                    )
                    found = True
        return found

    def _detect_loop_structure(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, (ast.For, ast.While)):
                evidence.append(
                    EvidenceItem(
                        type="loop_structure",
                        description=f"Loop providing lookup context",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                        weight=0.20,
                    )
                )
                found = True
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                evidence.append(
                    EvidenceItem(
                        type="comprehension_iteration",
                        description=f"Comprehension providing lookup context",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                        weight=0.15,
                    )
                )
                found = True
        return found

    def _calculate_confidence(self, evidence: list, has_required: bool) -> float:
        if not evidence or not has_required:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
