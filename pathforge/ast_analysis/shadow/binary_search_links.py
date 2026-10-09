"""Scoped S1 observations, not a general control-flow or monotonicity prover.

The one supported feasibility helper is ceiling-sum <= budget. Its usual
domain is positive integer candidates and nonnegative integer items, with a
fixed collection and budget. Recognizing that structure does not establish
those input assumptions, functional correctness, or product authority.
"""
import ast

from pathforge.ast_analysis.shadow.data_structures import StructuralFact


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
_ORDERED = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)


def _name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _integer(node, value):
    return isinstance(node, ast.Constant) and type(node.value) is int and node.value == value


def _ref(node):
    return f"{node.lineno}:{node.col_offset}"


def _scope_nodes(body):
    for node in body:
        yield node
        if not isinstance(node, _SCOPES):
            yield from _scope_nodes(ast.iter_child_nodes(node))


def _bindings(scope, name):
    result = []
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
        result.extend(a for a in ast.walk(scope.args) if isinstance(a, ast.arg) and a.arg == name)
    for node in _scope_nodes(scope.body):
        if (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del))
                or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name
                or isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == name
                or isinstance(node, ast.ExceptHandler) and node.name == name
                or isinstance(node, (ast.Global, ast.Nonlocal)) and name in node.names):
            result.append(node)
    return result


def _midpoint(value, lower, upper):
    def half(node):
        return isinstance(node, ast.BinOp) and (
            isinstance(node.op, (ast.FloorDiv, ast.Div)) and _integer(node.right, 2)
            or isinstance(node.op, ast.RShift) and _integer(node.right, 1))
    if half(value) and isinstance(value.left, ast.BinOp) and isinstance(value.left.op, ast.Add):
        return ((_name(value.left.left, lower) and _name(value.left.right, upper))
                or (_name(value.left.left, upper) and _name(value.left.right, lower)))
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        for base, offset in ((value.left, value.right), (value.right, value.left)):
            if _name(base, lower) and half(offset):
                difference = offset.left
                if (isinstance(difference, ast.BinOp) and isinstance(difference.op, ast.Sub)
                        and _name(difference.left, upper) and _name(difference.right, lower)):
                    return True
    return False


def _sequence_comparison(test, mid, lower, upper):
    if not isinstance(test, ast.Compare):
        return None
    ordered = all(isinstance(op, _ORDERED) for op in test.ops)
    if not ordered and not (len(test.ops) == 1 and isinstance(test.ops[0], (ast.Eq, ast.NotEq))):
        return None
    operands = [test.left, *test.comparators]
    reads = [v for v in operands if isinstance(v, ast.Subscript)]
    if not any(_name(v.slice, mid) for v in reads):
        return None
    if not reads or not all(isinstance(v.value, ast.Name) for v in reads):
        return None
    sequences = {v.value.id for v in reads}
    if len(sequences) != 1:
        return None
    for value in operands:
        if isinstance(value, (ast.Name, ast.Constant)):
            continue
        if not isinstance(value, ast.Subscript):
            return None
        index = value.slice
        if isinstance(index, ast.Name) and index.id in (mid, lower, upper):
            continue
        if (isinstance(index, ast.BinOp) and isinstance(index.op, (ast.Add, ast.Sub))
                and _name(index.left, mid) and _integer(index.right, 1)):
            continue
        return None
    # Do not borrow an indexed comparison from an unrelated chained clause.
    if any(not any(isinstance(v, ast.Subscript) for v in operands[i:i + 2]) for i in range(len(test.ops))):
        return None
    return sequences.pop(), ordered


def _ceiling_sum_roles(helper):
    parameters = [a.arg for a in [*helper.args.posonlyargs, *helper.args.args, *helper.args.kwonlyargs]]
    if (len(parameters) != 3 or len(set(parameters)) != 3 or helper.decorator_list
            or helper.args.vararg or helper.args.kwarg or helper.args.defaults
            or any(d is not None for d in helper.args.kw_defaults)):
        return None
    body = helper.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None
    test = body[0].value
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.LtE)
            and isinstance(test.comparators[0], ast.Name)):
        return None
    budget = test.comparators[0].id
    call = test.left
    if not (isinstance(call, ast.Call) and _name(call.func, "sum") and len(call.args) == 1 and not call.keywords
            and isinstance(call.args[0], ast.GeneratorExp)):
        return None
    generator = call.args[0]
    if len(generator.generators) != 1:
        return None
    iteration = generator.generators[0]
    if not (isinstance(iteration.target, ast.Name) and isinstance(iteration.iter, ast.Name)
            and not iteration.ifs and not iteration.is_async):
        return None
    collection, item = iteration.iter.id, iteration.target.id
    quotient = generator.elt
    if not (isinstance(quotient, ast.BinOp) and isinstance(quotient.op, ast.FloorDiv)
            and isinstance(quotient.right, ast.Name)):
        return None
    candidate = quotient.right.id
    numerator = quotient.left
    if not (isinstance(numerator, ast.BinOp) and isinstance(numerator.op, ast.Sub)
            and _integer(numerator.right, 1) and isinstance(numerator.left, ast.BinOp)
            and isinstance(numerator.left.op, ast.Add)):
        return None
    addition = numerator.left
    if not ((_name(addition.left, item) and _name(addition.right, candidate))
            or (_name(addition.left, candidate) and _name(addition.right, item))):
        return None
    if {collection, candidate, budget} != set(parameters) or item in parameters:
        return None
    return parameters, collection, candidate, budget


class _SearchLinks(ast.NodeVisitor):
    def __init__(self):
        self.scopes = []
        self.facts = []

    def visit_Module(self, node):
        self.scopes.append(node)
        self.generic_visit(node)
        self.scopes.pop()

    visit_FunctionDef = visit_Module
    visit_AsyncFunctionDef = visit_Module
    visit_ClassDef = visit_Module

    def _helper_predicate(self, test, mid, loop):
        negated = isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
        call = test.operand if negated else test
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            return None
        helper = None
        for i in range(len(self.scopes) - 1, -1, -1):
            scope = self.scopes[i]
            if isinstance(scope, ast.ClassDef):
                continue  # Bare calls in methods do not resolve in the class namespace.
            bindings = _bindings(scope, call.func.id)
            if not bindings:
                continue
            if len(bindings) != 1 or not isinstance(bindings[0], ast.FunctionDef) or bindings[0] not in scope.body:
                return None
            helper = bindings[0]
            # A local helper must have executed its definition before the loop.
            if i == len(self.scopes) - 1 and helper.lineno >= loop.lineno:
                return None
            helper_scopes = [*self.scopes[:i + 1], helper]
            break
        if helper is None or any(_bindings(s, "sum") for s in helper_scopes if not isinstance(s, ast.ClassDef)):
            return None
        roles = _ceiling_sum_roles(helper)
        if roles is None:
            return None
        parameters, collection, candidate, budget = roles
        positional = [a.arg for a in [*helper.args.posonlyargs, *helper.args.args]]
        if len(call.args) > len(positional) or any(isinstance(a, ast.Starred) for a in call.args):
            return None
        arguments = dict(zip(positional, call.args))
        for keyword in call.keywords:
            if keyword.arg not in parameters or keyword.arg in arguments or keyword.arg in {a.arg for a in helper.args.posonlyargs}:
                return None
            arguments[keyword.arg] = keyword.value
        if set(arguments) != set(parameters) or not all(isinstance(v, ast.Name) for v in arguments.values()):
            return None
        if not _name(arguments[candidate], mid):
            return None
        fixed = {arguments[collection].id, arguments[budget].id}
        if len(fixed) != 2 or mid in fixed:
            return None
        for node in _scope_nodes(loop.body):
            if (isinstance(node, ast.Name) and node.id in fixed and isinstance(node.ctx, (ast.Store, ast.Del))
                    or isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.value, ast.Name) and node.value.id in fixed):
                return None
        return {"kind": "ceiling_sum_budget", "helper": helper.name, "helper_ref": _ref(helper),
                "candidate_parameter": candidate, "collection_argument": arguments[collection].id,
                "budget_argument": arguments[budget].id, "negated": negated}

    def visit_While(self, loop):
        test = loop.test
        if (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], _ORDERED)
                and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)):
            lower, upper = test.left.id, test.comparators[0].id
            if isinstance(test.ops[0], (ast.Gt, ast.GtE)):
                lower, upper = upper, lower
            if lower != upper:
                for position, statement in enumerate(loop.body):
                    if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                            and isinstance(statement.targets[0], ast.Name)
                            and statement.targets[0].id not in (lower, upper)
                            and _midpoint(statement.value, lower, upper)):
                        mid = statement.targets[0].id
                        attrs = self._partition(loop, loop.body[position + 1:], lower, upper, mid)
                        if attrs:
                            attrs.update(lower=lower, upper=upper, midpoint=mid, midpoint_ref=_ref(statement))
                            # Keep the relation opaque to legacy generic scans
                            # of top-level attribute strings (e.g. loop-state
                            # tracking); only S1 reads this scoped partition.
                            self.facts.append(StructuralFact(fact_type="binary_search_partition", ast_ref=_ref(loop),
                                                             attributes={"partition": attrs}))
                            break
        self.generic_visit(loop)

    def _partition(self, loop, body, lower, upper, mid):
        sensitive = {lower, upper, mid}
        updates, predicates, ordered_updates = {}, [], set()
        modes = set()

        def identity(context):
            if context["kind"] == "sequence":
                return context["sequence"]
            return (context["helper_ref"], context["collection_argument"], context["budget_argument"])

        def visit(statements, control=None, branch=None):
            for statement in statements:
                if isinstance(statement, ast.If):
                    if any(isinstance(n, ast.Name) and n.id in sensitive and isinstance(n.ctx, (ast.Store, ast.Del))
                           for n in _scope_nodes([statement.test])):
                        return False
                    sequence = _sequence_comparison(statement.test, mid, lower, upper)
                    helper = self._helper_predicate(statement.test, mid, loop) if not sequence else None
                    if sequence:
                        name, ordered = sequence
                        context = {"kind": "sequence", "sequence": name, "ordered": ordered}
                    elif helper:
                        context = helper
                    else:
                        context = None
                    # An unrelated nested condition cannot borrow its parent's predicate.
                    predicates.append((statement, context))
                    if not (visit(statement.body, context, True) and visit(statement.orelse, context, False)):
                        return False
                elif (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                      and isinstance(statement.targets[0], ast.Name) and statement.targets[0].id in (lower, upper)):
                    if control is None:
                        return False
                    target, value = statement.targets[0].id, statement.value
                    direct_upper = target == upper and _name(value, mid)
                    offset = (isinstance(value, ast.BinOp) and _name(value.left, mid) and _integer(value.right, 1)
                              and (target == lower and isinstance(value.op, ast.Add)
                                   or target == upper and isinstance(value.op, ast.Sub)))
                    if not (direct_upper or offset):
                        return False
                    if control["kind"] == "ceiling_sum_budget":
                        feasible = branch != control["negated"]
                        if target != (upper if feasible else lower) or target == upper and not direct_upper:
                            return False
                    elif control["ordered"]:
                        ordered_updates.add(control["sequence"])
                    modes.add((control["kind"], identity(control)))
                    updates[target] = _ref(statement)
                elif any(
                    isinstance(n, ast.Name) and n.id in sensitive and isinstance(n.ctx, (ast.Store, ast.Del))
                    or isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in sensitive
                    for n in _scope_nodes([statement])
                ):
                    return False
            return True

        if not visit(body) or set(updates) != {lower, upper} or len(modes) != 1:
            return None
        kind, selected_identity = next(iter(modes))
        if kind == "sequence" and selected_identity not in ordered_updates:
            return None
        sources = [(node, context) for node, context in predicates
                   if context and (context["kind"], identity(context)) == (kind, selected_identity)]
        attrs = dict(sources[0][1])
        attrs.update(predicate_refs=[_ref(node) for node, _ in sources], update_refs=updates)
        if kind == "ceiling_sum_budget":
            attrs["domain_assumptions"] = ["positive integer candidate", "nonnegative integer items", "fixed collection and budget"]
        return attrs


def extract_binary_search_links(tree):
    extractor = _SearchLinks()
    extractor.visit(tree)
    return extractor.facts
