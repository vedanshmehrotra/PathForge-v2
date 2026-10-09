"""Detector for Union-Find (Disjoint Set Union) data structure.

Detects Union-Find implementations with parent array, find operations with
path compression, and union operations with optional rank/size optimization.

Does NOT detect:
- Ordinary tree traversals or graph traversals
- Non-DSU parent/child relationships in unrelated data structures
- Simple array operations without path compression or union logic
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class UnionFindDetector(BaseDetector):
    pattern_id = "union_find"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_union_find(ast_root, evidence)
        self._detect_functional_union_find(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_parent_array = any(e.type == "parent_array" for e in evidence)
        has_find_operation = any(e.type in ("find_recursive", "find_iterative") for e in evidence)
        has_union_operation = any(e.type == "union_operation" for e in evidence)

        detected = has_parent_array and (has_find_operation or has_union_operation)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_union_find(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.ClassDef):
                continue

            has_parent_array = self._find_parent_array_in_class(node)
            if not has_parent_array:
                continue

            has_find_recursive = self._find_find_recursive_in_class(node)
            has_find_iterative = self._find_find_iterative_in_class(node)
            has_union = self._find_union_in_class(node)
            has_connected = self._find_connected_in_class(node)
            has_rank = self._find_rank_in_class(node)

            if not has_find_recursive and not has_find_iterative and not has_union:
                continue

            evidence.append(
                EvidenceItem(
                    type="parent_array",
                    description="Parent array initialized for disjoint set",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.25,
                )
            )

            if has_find_recursive:
                evidence.append(
                    EvidenceItem(
                        type="find_recursive",
                        description="Recursive find with path compression",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_find_iterative:
                evidence.append(
                    EvidenceItem(
                        type="find_iterative",
                        description="Iterative find with path compression",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_union:
                evidence.append(
                    EvidenceItem(
                        type="union_operation",
                        description="Union operation merging two disjoint sets",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_connected:
                evidence.append(
                    EvidenceItem(
                        type="connected_check",
                        description="Connected check using find on both elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_rank:
                evidence.append(
                    EvidenceItem(
                        type="rank_optimization",
                        description="Union by rank/size for balanced tree",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _detect_functional_union_find(self, ast_root: ast.AST, evidence: list) -> None:
        """Recognize explicit-parent functions in one module, without borrowing scopes."""
        if not isinstance(ast_root, ast.Module):
            return
        functions = [node for node in ast_root.body if isinstance(node, ast.FunctionDef)]
        for lookup in functions:
            if lookup.decorator_list or sum(fn.name == lookup.name for fn in functions) != 1:
                continue
            # Rebindings/imports outside the function invalidate the callee link.
            if any(self._binds_name(statement, lookup.name) for statement in ast_root.body
                   if not isinstance(statement, ast.FunctionDef)):
                continue
            roles = self._functional_lookup_roles(lookup)
            if roles is None:
                continue
            for caller in functions:
                if caller is lookup or caller.decorator_list or self._binds_name(caller, lookup.name):
                    continue
                if not self._has_functional_root_merge(caller, lookup, roles):
                    continue
                kind = roles[2]
                evidence.extend([
                    EvidenceItem(
                        type="parent_array", description="Shared parent parameter connects root lookup and merging",
                        location=f"{caller.lineno}:{caller.col_offset}" if hasattr(caller, "lineno") else None,
                        weight=0.25,
                    ),
                    EvidenceItem(
                        type=kind, description="Representative lookup follows self-root parent links",
                        location=f"{lookup.lineno}:{lookup.col_offset}" if hasattr(lookup, "lineno") else None,
                        weight=0.30 if kind == "find_recursive" else 0.25,
                    ),
                    EvidenceItem(
                        type="union_operation", description="Parent write links two representatives returned by the same lookup",
                        location=f"{caller.lineno}:{caller.col_offset}" if hasattr(caller, "lineno") else None,
                        weight=0.30,
                    ),
                ])

    @staticmethod
    def _parent_item(node: ast.AST, parent: str, item: str) -> bool:
        return (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id == parent and isinstance(node.slice, ast.Name) and node.slice.id == item)

    @staticmethod
    def _call_arguments(call: ast.AST, function: ast.FunctionDef):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == function.name):
            return None
        names = [arg.arg for arg in [*function.args.posonlyargs, *function.args.args]]
        if len(call.args) > len(names) or any(isinstance(arg, ast.Starred) for arg in call.args):
            return None
        arguments = dict(zip(names, call.args))
        for keyword in call.keywords:
            if keyword.arg not in names or keyword.arg in arguments:
                return None
            arguments[keyword.arg] = keyword.value
        return arguments if set(arguments) == set(names) else None

    def _functional_lookup_roles(self, function: ast.FunctionDef):
        parameters = {arg.arg for arg in [*function.args.posonlyargs, *function.args.args]}
        if len(parameters) != 2 or function.args.vararg or function.args.kwarg or function.args.kwonlyargs:
            return None
        body = function.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        if len(body) != 2 or not isinstance(body[0], (ast.While, ast.If)) or not isinstance(body[1], ast.Return):
            return None
        traversal, returned = body
        guard = traversal.test
        if not (isinstance(guard, ast.Compare) and len(guard.ops) == 1 and isinstance(guard.ops[0], ast.NotEq)):
            return None
        for link, vertex in ((guard.left, guard.comparators[0]), (guard.comparators[0], guard.left)):
            if not (isinstance(vertex, ast.Name) and isinstance(link, ast.Subscript)
                    and isinstance(link.value, ast.Name) and link.value.id != vertex.id
                    and {link.value.id, vertex.id} == parameters
                    and self._parent_item(link, link.value.id, vertex.id)):
                continue
            parent, item = link.value.id, vertex.id
            if traversal.orelse:
                continue
            if isinstance(traversal, ast.While):
                if not (isinstance(returned.value, ast.Name) and returned.value.id == item):
                    continue
                advanced = False
                for statement in traversal.body:
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                        break
                    target, value = statement.targets[0], statement.value
                    if isinstance(target, ast.Name) and target.id == item and self._parent_item(value, parent, item):
                        if advanced:
                            break
                        advanced = True
                    elif (not advanced and self._parent_item(target, parent, item)
                          and isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name)
                          and value.value.id == parent and self._parent_item(value.slice, parent, item)):
                        continue
                    else:
                        break
                else:
                    if advanced:
                        return parent, item, "find_iterative"
            elif (function.name not in parameters and self._parent_item(returned.value, parent, item)
                  and len(traversal.body) == 1):
                compression = traversal.body[0]
                if isinstance(compression, ast.Assign) and len(compression.targets) == 1:
                    arguments = self._call_arguments(compression.value, function)
                    if (self._parent_item(compression.targets[0], parent, item) and arguments
                            and isinstance(arguments[parent], ast.Name) and arguments[parent].id == parent
                            and self._parent_item(arguments[item], parent, item)):
                        return parent, item, "find_recursive"
        return None

    def _has_functional_root_merge(self, caller: ast.FunctionDef, lookup: ast.FunctionDef, roles: tuple) -> bool:
        parameters = {arg.arg for arg in [*caller.args.posonlyargs, *caller.args.args, *caller.args.kwonlyargs]}
        parent_role, item_role, _ = roles
        roots, assigned = {}, set()

        def invalidate(name):
            roots.pop(name, None)
            for root in list(roots):
                if roots[root][0] == name:
                    del roots[root]
            assigned.add(name)

        def visit(statements, direct=False):
            for statement in statements:
                if isinstance(statement, ast.If):
                    for node in self._scope_nodes(statement.test):
                        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                            invalidate(node.id)
                    if visit(statement.body) or visit(statement.orelse):
                        return True
                elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target, value = statement.targets[0], statement.value
                    if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                            and isinstance(target.slice, ast.Name) and isinstance(value, ast.Name)):
                        first, second = roots.get(target.slice.id), roots.get(value.id)
                        if first and second and first[0] == second[0] == target.value.id and first[1] != second[1]:
                            return True
                    if isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple):
                        names = [n.id for n in target.elts if isinstance(n, ast.Name)]
                        values = [n.id for n in value.elts if isinstance(n, ast.Name)]
                        if (len(names) == len(values) == 2 and names[0] != names[1]
                                and values == names[::-1] and all(name in roots for name in names)
                                and roots[names[0]][0] == roots[names[1]][0]):
                            # A rank-driven exchange preserves the two root roles.
                            continue
                        if len(target.elts) != len(value.elts):
                            for node in self._scope_nodes(target):
                                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                                    invalidate(node.id)
                            continue
                        pairs = zip(target.elts, value.elts)
                    else:
                        pairs = [(target, value)]
                    for name, expression in pairs:
                        if not isinstance(name, ast.Name):
                            for node in self._scope_nodes(name):
                                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                                    invalidate(node.id)
                            continue
                        arguments = self._call_arguments(expression, lookup) if direct else None
                        if (name.id not in assigned and arguments
                                and all(isinstance(arguments[role], ast.Name) and arguments[role].id in parameters
                                        for role in (parent_role, item_role))):
                            invalidate(name.id)
                            roots[name.id] = (arguments[parent_role].id, arguments[item_role].id)
                        else:
                            invalidate(name.id)
                else:
                    for node in self._scope_nodes(statement):
                        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                            invalidate(node.id)
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            invalidate(node.name)
                        elif isinstance(node, ast.alias):
                            invalidate(node.asname or node.name.split('.')[0])
            return False

        return visit(caller.body, direct=True)

    @staticmethod
    def _scope_nodes(statement: ast.AST):
        pending = [statement]
        while pending:
            node = pending.pop()
            yield node
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                pending.extend(ast.iter_child_nodes(node))

    def _binds_name(self, statement: ast.AST, name: str) -> bool:
        if isinstance(statement, ast.FunctionDef):
            if statement.name == name:
                return True
            if any(arg.arg == name for arg in ast.walk(statement.args) if isinstance(arg, ast.arg)):
                return True
            nodes = (node for child in statement.body for node in self._scope_nodes(child))
        else:
            nodes = self._scope_nodes(statement)
        return any(
            (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)))
            or (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name)
            or (isinstance(node, ast.alias) and (node.asname or node.name.split('.')[0]) == name)
            for node in nodes
        )

    def _find_parent_array_in_class(self, class_def: ast.ClassDef) -> bool:
        for child in ast.walk(class_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        if target.attr == "parent":
                            val = child.value
                            if isinstance(val, ast.Call):
                                if isinstance(val.func, ast.Name) and val.func.id in ("list", "range"):
                                    return True
                            if isinstance(val, ast.ListComp):
                                return True
                            if isinstance(val, ast.List):
                                return True
        return False

    def _find_find_recursive_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_find_function(item):
                    if self._has_recursive_self_call(item):
                        if self._has_parent_assignment_in_find(item):
                            return True
        return False

    def _find_find_iterative_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_find_function(item):
                    if self._has_while_loop_in_find(item):
                        if self._has_parent_assignment_in_find(item):
                            return True
        return False

    def _find_union_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_union_function(item):
                    return True
        return False

    def _find_connected_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                name = item.name.lower()
                if "connect" in name or name == "same" or "isconnected" in name:
                    for sub in ast.walk(item):
                        if isinstance(sub, ast.Call):
                            if isinstance(sub.func, ast.Attribute) and sub.func.attr in ("find", "f"):
                                return True
        return False

    def _is_find_function(self, func_def: ast.FunctionDef) -> bool:
        return "find" in func_def.name.lower() or func_def.name == "f"

    def _is_union_function(self, func_def: ast.FunctionDef) -> bool:
        name = func_def.name.lower()
        return "union" in name or name in ("unite", "merge", "join")

    def _has_recursive_self_call(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == "self":
                        if child.func.attr == func_def.name:
                            return True
                if isinstance(child.func, ast.Name) and child.func.id == func_def.name:
                    return True
        return False

    def _has_parent_assignment_in_find(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Attribute):
                            if target.value.attr == "parent":
                                if isinstance(target.value.value, ast.Name) and target.value.value.id == "self":
                                    return True
                        if isinstance(target.value, ast.Name) and target.value.id == "parent":
                            return True
        return False

    def _has_while_loop_in_find(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.While):
                return True
        return False

    def _find_rank_in_class(self, class_def: ast.ClassDef) -> bool:
        rank_vars = set()
        for child in ast.walk(class_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        name = target.attr.lower()
                        if "rank" in name or "size" in name:
                            rank_vars.add(target.attr)
        for child in ast.walk(class_def):
            if isinstance(child, ast.If):
                if isinstance(child.test, ast.Compare):
                    for side in (child.test.left, child.test.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.value, ast.Attribute):
                                if side.value.attr in rank_vars:
                                    return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
