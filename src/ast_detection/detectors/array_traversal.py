"""Detector for array_traversal pattern.

Detects sequential element-by-element processing of array-like structures.
Requires a collection loop and linked use of its elements or indexed accesses.
Annotations, unused targets and evidence from separate scopes do not qualify.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem
from src.ast_detection.python_structure import bindings, parameter_names, scope_nodes


@register_detector
class ArrayTraversalDetector(BaseDetector):
    pattern_id = "array_traversal"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        parents = {child: parent for parent in ast.walk(ast_root) for child in ast.iter_child_nodes(parent)}
        for loop in ast.walk(ast_root):
            if not isinstance(loop, ast.For):
                continue
            iterator = loop.iter
            if isinstance(iterator, ast.Call):
                if (not isinstance(iterator.func, ast.Name) or not iterator.args
                        or iterator.func.id not in ("range", "enumerate")
                        or self._shadowed_iterator(loop, iterator.func.id, parents)):
                    continue
            elif not isinstance(iterator, ast.Name):
                continue
            local = []
            self._detect_traversal_loop(loop, local)
            accessed = self._detect_subscript_access(loop, local)
            updated = self._detect_element_update(loop, local)
            used = self._detect_element_usage(loop, local)
            if accessed or updated or used:
                evidence.extend(local)
        confidence = self._calculate_confidence(evidence, bool(evidence))
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_traversal_loop(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in [ast_root]:
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Name):
                    evidence.append(
                        EvidenceItem(
                            type="for_loop_over_collection",
                            description=f"Iteration over collection '{node.iter.id}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.35,
                        )
                    )
                    found = True
                elif isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                    if node.iter.func.id in ("range", "enumerate"):
                        evidence.append(
                            EvidenceItem(
                                type="iterator_based_loop",
                                description=f"Iterator-based loop: {ast.unparse(node.iter)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.35,
                            )
                        )
                        found = True
        return found

    def _detect_element_usage(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in [ast_root]:
            if isinstance(node, ast.For):
                loop_var_names = self._get_loop_var_names(node)
                if loop_var_names:
                    body_names = {
                        n.id for n in self._body_nodes(node)
                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in loop_var_names
                    }
                    if body_names:
                        evidence.append(
                            EvidenceItem(
                                type="element_usage",
                                description=f"Loop variable '{', '.join(sorted(body_names))}' used in body",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.30,
                            )
                        )
                        found = True
                        break
        return found

    def _get_loop_var_names(self, for_node: ast.For) -> set:
        names = set()
        target = for_node.target
        if isinstance(for_node.iter, ast.Call):
            if for_node.iter.func.id != "enumerate" or not isinstance(target, (ast.Tuple, ast.List)) or len(target.elts) != 2:
                return names
            # The index is not the sequence element. Do not count its use alone.
            target = target.elts[1]
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    names.add(elt.id)
        return names

    def _detect_subscript_access(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in self._body_nodes(ast_root):
            if self._linked_access(ast_root, node):
                evidence.append(
                    EvidenceItem(
                        type="subscript_access",
                        description=f"Element access via subscript: {ast.unparse(node)}",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                        weight=0.35,
                    )
                )
                found = True
                break
        return found

    def _detect_element_update(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in self._body_nodes(ast_root):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if self._linked_access(ast_root, target):
                        evidence.append(
                            EvidenceItem(
                                type="element_update",
                                description=f"Sequential element update: {ast.unparse(node)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.30,
                            )
                        )
                        found = True
                        break
        return found

    @staticmethod
    def _body_nodes(loop):
        nodes = list(scope_nodes(loop.body))
        annotations = {id(child) for node in nodes if isinstance(node, ast.AnnAssign)
                       for child in ast.walk(node.annotation)}
        return [node for node in nodes if id(node) not in annotations]

    def _linked_access(self, loop, node):
        if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
            return False
        elements = self._get_loop_var_names(loop)
        if node.value.id in elements:
            return True
        target = loop.target
        if isinstance(loop.iter, ast.Call) and loop.iter.func.id == "enumerate":
            if not isinstance(target, (ast.Tuple, ast.List)) or len(target.elts) != 2:
                return False
            target = target.elts[0]
        indices = {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}
        return any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in indices
                   for n in ast.walk(node.slice))

    @staticmethod
    def _shadowed_iterator(loop, name, parents):
        ancestor = parents.get(loop)
        while ancestor is not None:
            if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if name in parameter_names(ancestor) or bindings(ancestor.body, name):
                    return True
            elif isinstance(ancestor, ast.Module) and bindings(ancestor.body, name):
                return True
            ancestor = parents.get(ancestor)
        return False

    def _calculate_confidence(self, evidence: list, has_required: bool) -> float:
        if not evidence or not has_required:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
