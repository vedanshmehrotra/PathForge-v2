"""Small, conservative Python syntax links. No pattern, confidence or authority policy.

These observations do not execute or rewrite the submitted AST. Dynamic dispatch,
decorators, rebinding and unresolved unpacking are deliberately not inferred.
"""
import ast


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def scope_nodes(body):
    """Walk executable syntax without borrowing nested function/class bodies."""
    for node in body:
        yield node
        if not isinstance(node, SCOPES):
            yield from scope_nodes(ast.iter_child_nodes(node))


def assignment_values(statement):
    """Return name -> RHS links for simple, chained or literal unpacked assignments.

    Each chained RHS is evaluated once by Python; we only reference its AST.
    Refuse repeated names, starred/dynamic unpacking and attribute/subscript
    targets, whose evaluation/write order could invalidate another target.
    """
    result = {}

    def link(target, value):
        if isinstance(target, ast.Name) and target.id not in result:
            result[target.id] = value
            return True
        if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)):
            return all(link(t, v) for t, v in zip(target.elts, value.elts))
        return False

    if isinstance(statement, ast.Assign):
        targets, value = statement.targets, statement.value
    elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
        targets, value = [statement.target], statement.value
    else:
        return {}
    return result if all(link(target, value) for target in targets) else {}


def bindings(body, identifier):
    """Conservative lexical bindings, including declarations not stored as Names."""
    found = []
    for node in scope_nodes(body):
        if isinstance(node, ast.Name) and node.id == identifier and isinstance(node.ctx, (ast.Store, ast.Del)):
            found.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == identifier:
            found.append(node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if any((a.asname or a.name.split('.')[0]) == identifier or a.name == '*' for a in node.names):
                found.append(node)
        elif isinstance(node, ast.ExceptHandler) and node.name == identifier:
            found.append(node)
        elif isinstance(node, (ast.Global, ast.Nonlocal)) and identifier in node.names:
            found.append(node)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == identifier:
            found.append(node)
        elif isinstance(node, ast.MatchMapping) and node.rest == identifier:
            found.append(node)
    return found


def parameter_names(function):
    args = function.args
    return {a.arg for a in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                            *([args.vararg] if args.vararg else []),
                            *([args.kwarg] if args.kwarg else [])]}


def recursive_calls(root, function):
    """Link direct recursion or a stable receiver's locally defined instance method.

    A matching attribute spelling on an arbitrary object is not recursion. We
    abstain on explicit monkey-patching, duplicate definitions or decorators.
    This is local static evidence, not proof about arbitrary runtime subclasses.
    """
    if function.decorator_list:
        return []
    owner = next((n for n in ast.walk(root) if isinstance(n, (ast.Module, *SCOPES[:-1]))
                  and function in getattr(n, 'body', [])), None)
    if owner is None:
        return []
    if bindings(owner.body, function.name) != [function]:
        return []
    if function.name in parameter_names(function) or bindings(function.body, function.name):
        return []
    calls = [n for n in scope_nodes(function.body) if isinstance(n, ast.Call)]
    if not isinstance(owner, ast.ClassDef):
        if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)) and function.name in parameter_names(owner):
            return []
        return [c for c in calls if isinstance(c.func, ast.Name) and c.func.id == function.name]

    args = [*function.args.posonlyargs, *function.args.args]
    if not args:
        return []
    receiver = args[0].arg
    if (owner.decorator_list or bindings(function.body, receiver)
            or any(isinstance(n, ast.FunctionDef) and n.name in ('__getattr__', '__getattribute__')
                   for n in owner.body)):
        return []
    for node in ast.walk(root):
        if (isinstance(node, ast.Attribute) and node.attr == function.name
                and isinstance(node.ctx, (ast.Store, ast.Del))):
            return []
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ('setattr', 'delattr') and len(node.args) >= 2):
            attribute = node.args[1]
            if not isinstance(attribute, ast.Constant) or attribute.value == function.name:
                return []
    return [c for c in calls if isinstance(c.func, ast.Attribute) and c.func.attr == function.name
            and isinstance(c.func.value, ast.Name) and c.func.value.id == receiver]
