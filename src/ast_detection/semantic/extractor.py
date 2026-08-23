"""Minimal semantic feature extractor for Python AST.

Extracts features that are invariant to superficial code differences:
- Counter-loop behavior (while/for with incrementing index)
- Membership usage (x in collection, with collection-type awareness)
- Accumulation patterns (numeric accumulation from collection)
- Pointer/index movement (i += 1)
- Sequential collection access (arr[i], arr[i-1])
- Dict/set construction and membership tracking
"""
import ast
from typing import Optional, Set

from .features import (
    SemanticFeatures,
    LoopFeatures,
    AccessFeatures,
    AccumulationFeatures,
    PointerFeatures,
)


def extract_features(tree: ast.AST) -> SemanticFeatures:
    """Extract semantic features from a Python AST.

    Args:
        tree: Parsed Python AST (from ast.parse)

    Returns:
        SemanticFeatures with all extracted features populated
    """
    features = SemanticFeatures()
    _extract_loop_features(tree, features)
    _extract_collection_construction(tree, features)
    _extract_access_features(tree, features)
    _extract_accumulation_features(tree, features)
    _extract_pointer_features(tree, features)
    _check_membership_collection_type(features)
    return features


# ---------------------------------------------------------------------------
# Fix 1: For-loop counter detection + enumerate recognition
# ---------------------------------------------------------------------------

def _extract_loop_features(tree: ast.AST, features: SemanticFeatures) -> None:
    """Extract loop-related features."""
    loops = features.loops

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loops.total_loops += 1

            if isinstance(node, ast.For):
                loops.for_loops += 1

                # --- enumerate() iteration ---
                if (isinstance(node.iter, ast.Call)
                        and isinstance(node.iter.func, ast.Name)
                        and node.iter.func.id == "enumerate"):
                    loops.has_enumerate_iteration = True
                    loops.has_collection_iteration = True
                    # The second target of enumerate is the value, first is index
                    if isinstance(node.target, ast.Tuple) and len(node.target.elts) >= 2:
                        idx_name = _safe_name(node.target.elts[0])
                        if idx_name:
                            loops.counter_var = idx_name
                            loops.has_counter_loop = True
                            loops.has_for_counter_loop = True
                            loops.counter_increments = True
                            # enumerate inherently iterates the full collection
                            loops.counter_compares_to_len = True
                    continue

                # --- range() iteration → counter loop ---
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                    if node.iter.func.id == "range":
                        for_counter = _analyze_for_range_counter(node)
                        if for_counter:
                            loops.has_counter_loop = True
                            loops.has_for_counter_loop = True
                            loops.counter_var = for_counter["var"]
                            loops.counter_increments = True
                            loops.counter_compares_to_len = for_counter.get("compares_to_len", False)
                        continue

                # --- direct collection iteration (for x in collection) ---
                if isinstance(node.iter, ast.Name):
                    loops.has_collection_iteration = True
                    loops.collection_var = node.iter.id

            elif isinstance(node, ast.While):
                loops.while_loops += 1
                # Check if this is a counter loop
                counter_info = _analyze_counter_loop(node)
                if counter_info:
                    loops.has_counter_loop = True
                    # Prefer counter variable that compares to len()
                    if counter_info.get("compares_to_len", False) or not loops.counter_compares_to_len:
                        loops.counter_var = counter_info["var"]
                    loops.counter_increments = True
                    if counter_info.get("compares_to_len", False):
                        loops.counter_compares_to_len = True

            # Check for early exit
            for child in ast.walk(node):
                if isinstance(child, (ast.Break, ast.Continue)):
                    loops.has_early_exit = True
                    break
                if isinstance(child, ast.Return):
                    # Return inside loop body (not at function level)
                    if child is not node.body[-1] if isinstance(node.body, list) else False:
                        loops.has_early_exit = True
                        break


def _analyze_for_range_counter(for_node: ast.For) -> Optional[dict]:
    """Analyze if a for-loop over range() acts as a counter loop.

    Detects:
    - for i in range(N)           → counter var = i
    - for i in range(len(arr))    → counter var = i, compares_to_len = True
    - for i in range(start, end)  → counter var = i
    """
    # The target must be a single Name
    target_name = _safe_name(for_node.target)
    if not target_name:
        return None

    iter_call = for_node.iter  # already known to be ast.Call with ast.Name func
    args = iter_call.args
    if not args:
        return None

    compares_to_len = False

    # Check if any argument to range() calls len()
    for arg in args:
        if _calls_len(arg):
            compares_to_len = True
            break

    return {"var": target_name, "compares_to_len": compares_to_len}


def _safe_name(node: ast.expr) -> Optional[str]:
    """Safely extract a Name node's id."""
    if isinstance(node, ast.Name):
        return node.id
    return None


def _calls_len(node: ast.expr) -> bool:
    """Check if an expression calls len()."""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "len":
            return True
    return False


def _analyze_counter_loop(while_node: ast.While) -> Optional[dict]:
    """Analyze if a while loop is a counter loop.

    A counter loop has:
    1. A variable that is incremented by 1 in the body
    2. The variable is used in a comparison (<=, <, >=, >) in the condition
    """
    # Collect variables that are incremented by exactly 1
    incremented_vars = set()
    for stmt in while_node.body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    if isinstance(node.op, ast.Add):
                        if isinstance(node.value, ast.Constant) and node.value.value == 1:
                            incremented_vars.add(node.target.id)
                    elif isinstance(node.op, ast.Sub):
                        if isinstance(node.value, ast.Constant) and node.value.value == 1:
                            incremented_vars.add(node.target.id)

    if not incremented_vars:
        return None

    # Find variables that appear in comparisons in the condition
    comparison_vars = _find_comparison_vars(while_node.test)

    # A counter variable should appear in both incremented_vars and comparison_vars
    for var in incremented_vars:
        if var in comparison_vars:
            compares_to_len = _condition_compares_to_len(while_node.test, var)
            return {"var": var, "compares_to_len": compares_to_len}

    return None


def _find_comparison_vars(node: ast.expr) -> set:
    """Find variables that appear in comparison operations."""
    vars_in_comparisons = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Compare):
            # Get names from left side of comparison
            for name_node in ast.walk(child.left):
                if isinstance(name_node, ast.Name):
                    vars_in_comparisons.add(name_node.id)
            # Get names from comparators
            for comp in child.comparators:
                for name_node in ast.walk(comp):
                    if isinstance(name_node, ast.Name):
                        vars_in_comparisons.add(name_node.id)
    return vars_in_comparisons


def _condition_compares_to_len(condition: ast.expr, var: str) -> bool:
    """Check if a condition compares a variable against len()."""
    for node in ast.walk(condition):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "len":
                return True
    return False


# ---------------------------------------------------------------------------
# Fix 2: Collection construction tracking (dict/set)
# ---------------------------------------------------------------------------

def _extract_collection_construction(tree: ast.AST, features: SemanticFeatures) -> None:
    """Track dict() / {} / set() construction and dict usage patterns."""
    access = features.access

    for node in ast.walk(tree):
        # --- Explicit construction ---

        # Assignment: x = dict() or x = {} or x = set() or x = {...}
        if isinstance(node, ast.Assign):
            for target in node.targets:
                var_name = _safe_name(target)
                if not var_name:
                    continue
                value = node.value

                # dict() or {} → dict variable
                if _is_dict_creation(value):
                    if var_name not in access.dict_vars:
                        access.dict_vars.append(var_name)

                # set() or set literal (non-empty) → set variable
                elif _is_set_creation(value):
                    if var_name not in access.set_vars:
                        access.set_vars.append(var_name)

        # AugAssign: x = {} (only at initialization, not x[key] = val)
        if isinstance(node, ast.AugAssign):
            var_name = _safe_name(node.target)
            if var_name and isinstance(node.op, ast.Add):
                if _is_dict_creation(node.value):
                    if var_name not in access.dict_vars:
                        access.dict_vars.append(var_name)

        # --- Usage-based inference ---

        # Pattern: x[key] = value → x is likely a dict
        if isinstance(node, ast.Subscript):
            if isinstance(node.ctx, ast.Store):
                coll_var = _safe_name(node.value)
                if coll_var and coll_var not in access.dict_vars:
                    access.dict_vars.append(coll_var)

        # Pattern: x.get(key, default) → x is likely a dict
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ('get', 'items', 'keys', 'values', 'pop'):
                    obj_name = _safe_name(node.func.value)
                    if obj_name and obj_name not in access.dict_vars:
                        access.dict_vars.append(obj_name)
                # Track .get() specifically as a lookup signal
                if node.func.attr == 'get':
                    obj_name = _safe_name(node.func.value)
                    if obj_name and obj_name in access.dict_vars:
                        access.has_dict_get_lookup = True



def _is_dict_creation(node: ast.expr) -> bool:
    """Check if an expression creates a dict."""
    # dict()
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            return True
    # {} literal
    if isinstance(node, ast.Dict):
        return True
    return False


def _is_set_creation(node: ast.expr) -> bool:
    """Check if an expression creates a set."""
    # set()
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "set":
            return True
    # set literal {a, b} — Python set literals have >= 2 elements
    # Empty set must use set(), not {}
    if isinstance(node, ast.Set):
        return True
    return False


# ---------------------------------------------------------------------------
# Access features (membership + indexed access)
# ---------------------------------------------------------------------------

def _extract_access_features(tree: ast.AST, features: SemanticFeatures) -> None:
    """Extract collection access features."""
    access = features.access

    for node in ast.walk(tree):
        # Indexed access: collection[i]
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                access.has_indexed_access = True
                access.indexed_collection = node.value.id
                # Track index variables
                idx_names = _get_names(node.slice)
                for name in idx_names:
                    if name not in access.index_vars:
                        access.index_vars.append(name)

        # Membership test: x in collection  OR  x not in collection
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    access.has_membership_test = True
                    # Get the collection being tested
                    if isinstance(node.comparators[0], ast.Name):
                        coll_name = node.comparators[0].id
                        access.membership_collection = coll_name
                        if coll_name not in access.membership_collections:
                            access.membership_collections.append(coll_name)
                    # Get the variable being tested
                    left_names = _get_names(node.left)
                    for name in left_names:
                        if name not in access.membership_vars:
                            access.membership_vars.append(name)

    # Pass 2: membership collection subscript reads → likely dict
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.ctx, ast.Load):
                coll_var = _safe_name(node.value)
                if coll_var and coll_var not in access.dict_vars:
                    if coll_var in access.membership_collections:
                        access.dict_vars.append(coll_var)

    # Check for sequential index access (arr[i], arr[i-1], etc.)
    if access.has_indexed_access:
        _check_sequential_access(tree, access)


def _check_sequential_access(tree: ast.AST, access: AccessFeatures) -> None:
    """Check if collection is accessed with sequential indices."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == access.indexed_collection:
                slice_str = ast.unparse(node.slice)
                for var in access.index_vars:
                    if var in slice_str and ("+" in slice_str or "-" in slice_str):
                        access.has_sequential_index = True
                        return


# ---------------------------------------------------------------------------
# Fix 2 continued: Determine membership collection type
# ---------------------------------------------------------------------------

def _check_membership_collection_type(features: SemanticFeatures) -> None:
    """Determine if membership test is on a hash collection (dict/set) or a list."""
    access = features.access
    if not access.has_membership_test:
        return

    coll = access.membership_collection
    if not coll:
        return

    if coll in access.dict_vars:
        access.membership_collection_type = "dict"
        access.membership_on_hash_collection = True
    elif coll in access.set_vars:
        access.membership_collection_type = "set"
        access.membership_on_hash_collection = True
    else:
        access.membership_collection_type = "unknown"


# ---------------------------------------------------------------------------
# Fix 3: Accumulation — numeric vs non-numeric
# ---------------------------------------------------------------------------

def _extract_accumulation_features(tree: ast.AST, features: SemanticFeatures) -> None:
    """Extract accumulation patterns with numeric-accumulation awareness.

    Detects:
    - x += expr (AugAssign)
    - x *= expr (product accumulation)
    - x.append(expr) where expr depends on prior state
    - x[i] = x[i-1] + expr (prefix recurrence)
    """
    acc = features.accumulation

    for node in ast.walk(tree):
        # Pattern: x += expr
        if isinstance(node, ast.AugAssign):
            if isinstance(node.op, ast.Add):
                if isinstance(node.target, ast.Name):
                    acc.has_accumulation = True
                    acc.accumulator_var = node.target.id
                    acc.accumulator_op = "+="
                    acc.accumulator_source = ast.unparse(node.value)

                    if isinstance(node.value, ast.Subscript):
                        if isinstance(node.value.value, ast.Name):
                            acc.has_running_sum = True
                            acc.accumulator_is_from_collection = True

                    acc.has_numeric_accumulation = _is_numeric_accumulation(node.value)

            elif isinstance(node.op, ast.Mult):
                if isinstance(node.target, ast.Name):
                    acc.has_accumulation = True
                    acc.accumulator_var = node.target.id
                    acc.accumulator_op = "*="
                    acc.accumulator_source = ast.unparse(node.value)

                    if isinstance(node.value, ast.Subscript):
                        if isinstance(node.value.value, ast.Name):
                            acc.has_running_sum = True
                            acc.accumulator_is_from_collection = True

                    if isinstance(node.value, ast.Subscript):
                        acc.has_numeric_accumulation = True

        # Fix 3: Pattern: x.append(expr) — append accumulation
        # Only credit when the appended value depends on prior state of x
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                call = node.value
                if (isinstance(call.func, ast.Attribute)
                        and call.func.attr == "append"
                        and call.args):
                    # Check if the argument references the same variable
                    arg_str = ast.unparse(call.args[0])
                    coll_var = _safe_name(call.func.value)
                    if coll_var and coll_var in arg_str:
                        acc.has_append_accumulation = True
                        acc.has_accumulation = True
                        if not acc.accumulator_var:
                            acc.accumulator_var = coll_var
                        acc.accumulator_op = ".append()"
                        acc.accumulator_source = arg_str
                        acc.has_numeric_accumulation = True
                        # Check if argument is a subscript (collection element)
                        if isinstance(call.args[0], ast.Subscript):
                            acc.has_running_sum = True
                            acc.accumulator_is_from_collection = True

    # Fix 4: Pattern: x[i] = x[i-1] + expr (assignment-based accumulation)
    # Separate pass to handle Subscript store assignments
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if (len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Add)):
                target = node.targets[0]
                target_var = _safe_name(target.value)
                if not target_var:
                    continue
                # Left operand of + might be a Subscript (prefix[i-1]) or a Name
                left_expr = node.value.left
                left_var = None
                if isinstance(left_expr, ast.Subscript):
                    left_var = _safe_name(left_expr.value)
                elif isinstance(left_expr, ast.Name):
                    left_var = left_expr.id
                if target_var and left_var and target_var == left_var:
                    acc.has_assignment_accumulation = True
                    acc.has_accumulation = True
                    if not acc.accumulator_var:
                        acc.accumulator_var = target_var
                    acc.accumulator_op = "assignment"
                    acc.accumulator_source = ast.unparse(node.value)
                    acc.has_numeric_accumulation = True


def _is_numeric_accumulation(value_node: ast.expr) -> bool:
    """Determine if an accumulation value is numeric.

    Returns True if the value looks like numeric accumulation from a collection.
    Returns False for:
    - String concatenation (+= string_literal or += str_var + str_literal)
    - Simple counters (+= 1)
    """
    # String literal → not numeric
    if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
        return False

    # Constant integer 1 (or -1) → simple counter, not numeric accumulation
    if isinstance(value_node, ast.Constant) and isinstance(value_node.value, int):
        if abs(value_node.value) == 1:
            return False

    # Collection element → numeric
    if isinstance(value_node, ast.Subscript):
        return True

    # Binary op (arithmetic) → check if it's string concatenation
    if isinstance(value_node, ast.BinOp):
        if isinstance(value_node.op, ast.Add):
            # Check if either side involves a string constant → string concat
            if _contains_string_literal(value_node):
                return False
        if isinstance(value_node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)):
            # Check if either operand is a collection element
            if isinstance(value_node.left, ast.Subscript) or isinstance(value_node.right, ast.Subscript):
                return True
            # Arithmetic between variables could be numeric
            return True

    # Variable referencing a collection element (e.g., 'num' from 'for num in nums')
    if isinstance(value_node, ast.Name):
        return True

    # Constant number (other than 1/-1) → numeric
    if isinstance(value_node, ast.Constant) and isinstance(value_node.value, (int, float)):
        return True

    # Call — could be anything; be conservative
    if isinstance(value_node, ast.Call):
        return False

    # Default: assume numeric for unclassified expressions
    return True


def _contains_string_literal(node: ast.expr) -> bool:
    """Check if an expression tree contains a string literal."""
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            return True
    return False


# ---------------------------------------------------------------------------
# Pointer features
# ---------------------------------------------------------------------------

def _extract_pointer_features(tree: ast.AST, features: SemanticFeatures) -> None:
    """Extract pointer/index movement features."""
    ptr = features.pointers

    # Track all variables that move by 1
    movement_vars = {}  # var_name -> step direction

    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
                if isinstance(node.op, ast.Add):
                    if isinstance(node.value, ast.Constant) and node.value.value == 1:
                        movement_vars[var_name] = 1
                elif isinstance(node.op, ast.Sub):
                    if isinstance(node.value, ast.Constant) and node.value.value == 1:
                        movement_vars[var_name] = -1

    # Check for bidirectional movement (two variables moving in opposite directions)
    increments = [v for v, s in movement_vars.items() if s == 1]
    decrements = [v for v, s in movement_vars.items() if s == -1]

    if increments and decrements:
        ptr.has_bidirectional = True
        ptr.has_index_movement = True
        ptr.movement_var = increments[0]
        ptr.movement_step = 1
    elif movement_vars:
        # Prefer index variable over accumulator
        for var in features.access.index_vars:
            if var in movement_vars:
                ptr.has_index_movement = True
                ptr.movement_var = var
                ptr.movement_step = movement_vars[var]
                return
        # Fall back to first movement variable
        var = list(movement_vars.keys())[0]
        ptr.has_index_movement = True
        ptr.movement_var = var
        ptr.movement_step = movement_vars[var]


def _get_names(node: ast.expr) -> set:
    """Get all Name nodes in an expression."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names
