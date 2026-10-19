"""Local FIFO/expansion links shared by the two legacy BFS presentations.

Names such as 'minutes', 'level' and 'visited' confer no evidence. This observes
queue structure and layer/hop propagation; it does not prove shortest paths.
"""
import ast

from src.ast_detection.python_structure import assignment_values, scope_nodes


def queue_features(loop):
    nodes = list(scope_nodes(loop.body))
    popped = set()
    queue = None
    for statement in nodes:
        if not isinstance(statement, ast.Assign):
            continue
        call = statement.value
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and not call.keywords
                and (call.func.attr == 'popleft' and not call.args or call.func.attr == 'pop'
                     and len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and call.args[0].value == 0)):
            queue = call.func.value.id
            popped = {n.id for t in statement.targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            break
    result = dict(queue=queue, level=False, distance=False, visited=False, expansion=False)
    if queue is None:
        return result
    pushed = [n for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and isinstance(n.func.value, ast.Name) and n.func.value.id == queue and n.func.attr == 'append']
    length_aliases = {key for s in loop.body for key, v in assignment_values(s).items()
                      if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == 'len'
                      and len(v.args) == 1 and isinstance(v.args[0], ast.Name) and v.args[0].id == queue}
    for n in loop.body:
        if (isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name)
                and n.iter.func.id == 'range' and any(
                    isinstance(a, ast.Name) and a.id in length_aliases or isinstance(a, ast.Call)
                    and isinstance(a.func, ast.Name) and a.func.id == 'len' and len(a.args) == 1
                    and isinstance(a.args[0], ast.Name) and a.args[0].id == queue for a in n.iter.args)):
            result['level'] = True
    # A layer counter advances at the outer FIFO boundary, not inside a
    # neighbor loop. Alternatively the dequeued hop travels with successors.
    result['distance'] = result['level'] and any(
        isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and isinstance(n.op, ast.Add)
        and isinstance(n.value, ast.Constant) and n.value.value == 1 for n in loop.body)
    result['distance'] |= any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)
        and isinstance(n.left, ast.Name) and n.left.id in popped
        and isinstance(n.right, ast.Constant) and n.right.value == 1 for p in pushed for n in ast.walk(p))
    # The FIFO item's children or the iteration candidates are what is queued.
    for push in pushed:
        if any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in popped
               and n.attr in ('left', 'right', 'children') for a in push.args for n in ast.walk(a)):
            result['expansion'] = True
        for driver in nodes:
            if not isinstance(driver, ast.For) or push not in scope_nodes(driver.body):
                continue
            candidates = {n.id for n in ast.walk(driver.target) if isinstance(n, ast.Name)}
            iterator_reads_current = any(isinstance(n, ast.Name) and n.id in popped for n in ast.walk(driver.iter))
            derived = set(candidates) if iterator_reads_current else set()
            for statement in scope_nodes(driver.body):
                for key, value in assignment_values(statement).items():
                    if any(isinstance(n, ast.Name) and n.id in popped | derived for n in ast.walk(value)):
                        derived.add(key)
            if any(isinstance(n, ast.Name) and n.id in derived for a in push.args for n in ast.walk(a)):
                result['expansion'] = True
    for guard in nodes:
        if not isinstance(guard, ast.If) or not any(p in scope_nodes(guard.body) for p in pushed):
            continue
        for test in ast.walk(guard.test):
            if isinstance(test, ast.Compare) and any(isinstance(op, ast.NotIn) for op in test.ops):
                if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'add'
                       and ast.dump(n.func.value) == ast.dump(test.comparators[-1]) for n in scope_nodes(guard.body)):
                    result['visited'] = True
            if isinstance(test, ast.Subscript) and any(isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store)
                    and ast.dump(n, include_attributes=False).replace('Store()', 'Load()') == ast.dump(test)
                    for n in scope_nodes(guard.body)):
                result['visited'] = True
    return result
