"""Bound local collection operations to their receiver, scope and execution order.

LeetCode-style snippets may omit the standard Counter/defaultdict imports. An
otherwise unbound standard name is recognized structurally; a local/outer
binding, opaque constructor, escape or rebinding defeats that assumption. This
is not a runtime type proof or a general alias/effect analysis.
"""
import ast
from dataclasses import dataclass, replace

from src.ast_detection.python_structure import assignment_values, bindings, parameter_names, scope_nodes


@dataclass(frozen=True)
class Collection:
    kind: str
    creation: ast.AST
    populated: bool = False
    imported: ast.AST | None = None


def _same(a, b):
    return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)


def _constructor(root, scope, expression):
    parents = {child: node for node in ast.walk(root) for child in ast.iter_child_nodes(node)}
    if not isinstance(expression, ast.Name):
        return None
    identifier = expression.id
    current = scope
    while current is not None:
        if isinstance(current, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not isinstance(current, ast.Module) and identifier in parameter_names(current):
                return None
            writes = bindings(current.body, identifier)
            if writes:
                if len(writes) == 1 and isinstance(writes[0], ast.ImportFrom) and writes[0].module == 'collections':
                    alias = next((a for a in writes[0].names if (a.asname or a.name) == identifier), None)
                    if alias and alias.name in ('Counter', 'defaultdict'):
                        return alias.name, writes[0]
                return None
        current = parents.get(current)
    return (identifier, None) if identifier in ('dict', 'set', 'Counter', 'defaultdict', 'int') else None


def collection_events(root):
    """Return linked lookup/count observations; unrelated syntax cannot pool."""
    events = []

    def emit(kind, node, collection, loop=None):
        events.append({'kind': kind, 'node': node, 'collection': collection, 'loop': loop})

    for scope in ast.walk(root):
        if not isinstance(scope, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        def created(value, node):
            # Keep the historical literal-dictionary coverage boundary; a
            # populated literal alone was never part of this detector's core.
            if isinstance(value, ast.Dict) and not value.keys:
                return Collection('dict', node)
            if isinstance(value, ast.DictComp):
                return Collection('dict', node, True)
            if not isinstance(value, ast.Call):
                return None
            binding = _constructor(root, scope, value.func)
            if not binding or value.keywords:
                return None
            kind, imported = binding
            if kind in ('dict', 'set') and len(value.args) <= 1:
                return Collection(kind, node, bool(value.args))
            if kind == 'Counter' and len(value.args) <= 1:
                state = Collection(kind, node, bool(value.args), imported)
                if value.args:
                    emit('constructor_count', value, state)
                return state
            if (kind == 'defaultdict' and len(value.args) == 1
                    and _constructor(root, scope, value.args[0]) == ('int', None)):
                return Collection(kind, node, False, imported)
            return None

        def reads(expression, known, loop):
            if expression is None:
                return
            if isinstance(expression, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(expression, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                local = dict(known)
                for generator in expression.generators:
                    reads(generator.iter, local, loop)
                    for n in ast.walk(generator.target):
                        if isinstance(n, ast.Name):
                            local.pop(n.id, None)
                    for condition in generator.ifs:
                        reads(condition, local, expression)
                for attr in ('elt', 'key', 'value'):
                    reads(getattr(expression, attr, None), local, expression)
                return
            if loop is not None:
                if isinstance(expression, ast.Compare):
                    for operator, receiver in zip(expression.ops, expression.comparators):
                        if isinstance(operator, (ast.In, ast.NotIn)) and isinstance(receiver, ast.Name) and receiver.id in known:
                            emit('lookup', expression, known[receiver.id], loop)
                if (isinstance(expression, ast.Subscript) and isinstance(expression.ctx, ast.Load)
                        and isinstance(expression.value, ast.Name) and expression.value.id in known
                        and known[expression.value.id].populated and known[expression.value.id].kind != 'set'):
                    emit('lookup', expression, known[expression.value.id], loop)
            for child in ast.iter_child_nodes(expression):
                reads(child, known, loop)

        def block(body, known, loop=None):
            for statement in body:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    known.pop(statement.name, None)
                    continue
                if isinstance(statement, (ast.For, ast.While)):
                    reads(statement.iter if isinstance(statement, ast.For) else statement.test, known, loop)
                    local = dict(known)
                    if isinstance(statement, ast.For):
                        for n in ast.walk(statement.target):
                            if isinstance(n, ast.Name):
                                local.pop(n.id, None)
                    # A receiver rebound anywhere in the repeated body cannot
                    # borrow its pre-loop type on later iterations.
                    for key in list(local):
                        if bindings(statement.body, key):
                            local.pop(key)
                    block(statement.body, local, statement)
                    for key in list(known):
                        if key not in local:
                            known.pop(key)
                        else:
                            known[key] = local[key]
                    block(statement.orelse, known, loop)
                    continue
                if isinstance(statement, ast.If):
                    reads(statement.test, known, loop)
                    branches = [dict(known), dict(known)]
                    block(statement.body, branches[0], loop)
                    block(statement.orelse, branches[1], loop)
                    for key in list(known):
                        a, b = branches[0].get(key), branches[1].get(key)
                        if a is None or b is None or a.kind != b.kind or a.creation is not b.creation:
                            known.pop(key)
                        else:
                            known[key] = replace(a, populated=a.populated and b.populated)
                    continue
                if isinstance(statement, (ast.Try, ast.With, ast.Match)):
                    # The existing linked KeyError path remains separate.
                    for key in list(known):
                        if any(isinstance(n, ast.Name) and n.id == key for n in scope_nodes([statement])):
                            known.pop(key)
                    continue
                value = getattr(statement, 'value', None)
                targets = statement.targets if isinstance(statement, (ast.Assign, ast.Delete)) else [statement.target] if isinstance(statement, (ast.AnnAssign, ast.AugAssign)) else []
                for target in targets:
                    if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id in known):
                        continue
                    state = known[target.value.id]
                    counted = False
                    if isinstance(statement, ast.AugAssign):
                        counted = isinstance(statement.op, (ast.Add, ast.Sub)) and isinstance(value, ast.Constant) and type(value.value) is int and value.value == 1
                    elif isinstance(value, ast.BinOp) and isinstance(value.op, (ast.Add, ast.Sub)):
                        previous = value.left
                        linked = _same(previous, target) or (
                            isinstance(previous, ast.Call) and isinstance(previous.func, ast.Attribute)
                            and isinstance(previous.func.value, ast.Name) and previous.func.value.id == target.value.id
                            and previous.func.attr == 'get' and len(previous.args) == 2 and not previous.keywords
                            and _same(previous.args[0], target.slice) and isinstance(previous.args[1], ast.Constant)
                            and previous.args[1].value == 0)
                        counted = linked and isinstance(value.right, ast.Constant) and type(value.right.value) is int and value.right.value == 1
                    if counted and loop is not None and state.kind != 'set':
                        emit('frequency_increment', statement, state, loop)
                    known[target.value.id] = replace(state, populated=not isinstance(statement, ast.Delete))
                reads(value, known, loop)
                # Model only ordinary local population operations. Passing the
                # collection itself to opaque code invalidates its later use.
                for call in [n for n in scope_nodes([statement]) if isinstance(n, ast.Call)]:
                    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id in known:
                        receiver = call.func.value.id
                        if call.func.attr == 'update' and len(call.args) == 1 and isinstance(call.args[0], (ast.Dict, ast.DictComp)) and not call.keywords:
                            known[receiver] = replace(known[receiver], populated=True)
                        elif call.func.attr == 'add' and known[receiver].kind == 'set' and len(call.args) == 1:
                            known[receiver] = replace(known[receiver], populated=True)
                        elif call.func.attr not in ('get', 'keys', 'values', 'items'):
                            known.pop(receiver)
                    if not (isinstance(call.func, ast.Name) and call.func.id in ('len', 'print')):
                        for arg in call.args:
                            if isinstance(arg, ast.Name):
                                known.pop(arg.id, None)
                assigned = assignment_values(statement)
                for key in list(known):
                    if bindings([statement], key):
                        known.pop(key)
                for key, expression in assigned.items():
                    if isinstance(expression, ast.Name):
                        known.pop(expression.id, None)  # unmodeled mutable alias
                    state = created(expression, statement)
                    if state:
                        known[key] = state
            return known

        block(scope.body, {})
    return events
