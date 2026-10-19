"""Lookup in a locally linked mapping/set, not pooled creation/membership flags."""

import ast
from src.ast_detection.collection_links import collection_events
from src.ast_detection.python_structure import assignment_values, bindings, parameter_names, scope_nodes
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class HashMapLookupDetector(BaseDetector):
    pattern_id = "hash_map_lookup"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        lookups = [e for e in collection_events(ast_root) if e['kind'] == 'lookup']
        if lookups:
            event = lookups[0]
            creation, operation, loop = event['collection'].creation, event['node'], event['loop']
            for kind, node, weight, description in [
                ('dict_creation', creation, 0.25, 'Local dictionary/set binding'),
                ('membership_check', operation, 0.35, 'Membership or populated-map read on that same collection'),
                ('loop_structure', loop, 0.20, 'Loop containing the linked lookup'),
            ]:
                evidence.append(EvidenceItem(type=kind, description=description,
                    location=f'{node.lineno}:{node.col_offset}', weight=weight))
        else:
            evidence = self._exception_lookup(ast_root)
        has_required_signals = bool(evidence)
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

    def _calculate_confidence(self, evidence: list, has_required: bool) -> float:
        if not evidence or not has_required:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
