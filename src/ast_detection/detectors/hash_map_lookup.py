"""Detector for hash_map_lookup pattern.

Detects dictionary/set creation combined with membership checking in a loop
context to identify hash map lookup patterns.

Requires ALL THREE core signals before detection:
1. Dict/set creation
2. Membership check (in / not in), or a linked dictionary read guarded by KeyError
3. Loop structure providing lookup context

A dict used for configuration or membership check without a loop does NOT fire.
"""

import ast
from src.ast_detection.python_structure import assignment_values, bindings, parameter_names, scope_nodes
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
        if not has_required_signals:
            exception_evidence = self._exception_lookup(ast_root)
            if exception_evidence:
                evidence = exception_evidence
                has_required_signals = True
        confidence = self._calculate_confidence(evidence, has_required_signals)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence if has_required_signals else [],
            detected=confidence > 0.0,
        )

    def _exception_lookup(self, root):
        """Only extend lookup syntax when dictionary, read and handler are linked."""
        parents = {child: parent for parent in ast.walk(root) for child in ast.iter_child_nodes(parent)}
        def shadowed(scope, identifier):
            while scope is not None:
                if isinstance(scope, (ast.Module, ast.FunctionDef)) and (
                    bindings(scope.body, identifier)
                    or isinstance(scope, ast.FunctionDef) and identifier in parameter_names(scope)
                ):
                    return True
                scope = parents.get(scope)
            return False

        for scope in ast.walk(root):
            if not isinstance(scope, (ast.Module, ast.FunctionDef)):
                continue
            if shadowed(scope, 'KeyError'):
                continue
            dictionaries = {}
            for statement in scope.body:
                if isinstance(statement, (ast.For, ast.While)):
                    for handler_owner in scope_nodes(statement.body):
                        if not isinstance(handler_owner, ast.Try) or not any(
                            isinstance(h.type, ast.Name) and h.type.id == 'KeyError'
                            for h in handler_owner.handlers
                        ):
                            continue
                        for read in scope_nodes(handler_owner.body):
                            if not (isinstance(read, ast.Subscript) and isinstance(read.ctx, ast.Load)
                                    and isinstance(read.value, ast.Name) and read.value.id in dictionaries
                                    and not bindings([statement], read.value.id)):
                                continue
                            creation = dictionaries[read.value.id]
                            return [
                                EvidenceItem(type='dict_creation', description='Dictionary bound before lookup loop',
                                             location=f'{creation.lineno}:{creation.col_offset}', weight=0.25),
                                EvidenceItem(type='exception_lookup', description='Same dictionary read guarded by KeyError',
                                             location=f'{read.lineno}:{read.col_offset}', weight=0.35),
                                EvidenceItem(type='loop_structure', description='Loop providing lookup context',
                                             location=f'{statement.lineno}:{statement.col_offset}', weight=0.20),
                            ]
                # Unknown rebindings invalidate the local dictionary type link.
                for identifier in list(dictionaries):
                    if bindings([statement], identifier):
                        dictionaries.pop(identifier)
                for identifier, value in assignment_values(statement).items():
                    if (isinstance(value, (ast.Dict, ast.DictComp))
                            or isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                            and value.func.id == 'dict' and not shadowed(scope, 'dict')):
                        dictionaries[identifier] = statement
        return []

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
