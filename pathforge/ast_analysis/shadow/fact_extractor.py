"""Structural fact extractor — deterministic, syntax-normalized AST observation.

Walks the AST and extracts structural facts for the vertical slice:
- sequential_accumulation
- bidirectional_index_scan
- carry_propagation
- two_pointers_opposite

Facts are:
- deterministic (same code → same facts)
- syntax-normalized (i += 1 and i = i + 1 produce same fact)
- independent of variable naming
- stored with extractor version
- traceable to source locations
"""
import ast
from typing import Optional

from pathforge.ast_analysis.shadow.data_structures import StructuralFact, EXTRACTOR_VERSION


# --- Carry-like variable name heuristic (not naming-dependent, just heuristic) ---
CARRY_LIKE_NAMES = frozenset({
    "carry", "c", "sum", "total", "acc", "accumulator", "running",
    "result", "res", "val",
})

# Linked structure attribute patterns
LINKED_ATTRS = frozenset({"next", "left", "right"})

# Node constructor name patterns
NODE_CONSTRUCTOR_PREFIXES = ("node", "listnode", "treenode", "btnode")


def extract_structural_facts(ast_root: ast.AST) -> list[StructuralFact]:
    """Extract all structural facts from a parsed AST.

    Returns a list of StructuralFact objects, deduplicated by (fact_type, ast_ref).
    """
    extractor = _FactExtractor()
    extractor.visit(ast_root)
    facts = extractor._deduplicate()
    for i, fact in enumerate(facts):
        fact.fact_id = f"fact_{i:03d}"
    return facts


def _ref(node: ast.AST) -> str:
    """Create a source-location reference string."""
    if hasattr(node, "lineno") and hasattr(node, "col_offset"):
        return f"{node.lineno}:{node.col_offset}"
    return ""


def _is_carry_name(name: str) -> bool:
    """Check if a variable name is carry-like (heuristic, not naming-dependent)."""
    return name.lower() in CARRY_LIKE_NAMES


def _is_node_constructor_name(name: str) -> bool:
    """Check if a function name looks like a node constructor."""
    return any(name.lower().startswith(p) for p in NODE_CONSTRUCTOR_PREFIXES)


def _is_name_node(node: ast.AST) -> bool:
    """Check if a node is a Name (variable) node."""
    return isinstance(node, ast.Name)


def _get_name_id(node: ast.AST) -> str:
    """Get the name string from a Name node, or empty string."""
    return node.id if isinstance(node, ast.Name) else ""


def _is_two_distinct_names(node: ast.AST) -> bool:
    """Check if a BinOp has two distinct Name children (a + b, a - b, etc.)."""
    if not isinstance(node, ast.BinOp):
        return False
    if not (_is_name_node(node.left) and _is_name_node(node.right)):
        return False
    return node.left.id != node.right.id


def _is_divide_by_two(node: ast.BinOp) -> bool:
    """Check if a BinOp divides by 2: floor-div, true-div, or right-shift by 1."""
    if isinstance(node.op, (ast.FloorDiv, ast.Div)):
        return isinstance(node.right, ast.Constant) and node.right.value == 2
    if isinstance(node.op, ast.RShift):
        return isinstance(node.right, ast.Constant) and node.right.value == 1
    return False


def _is_midpoint_calculation(node: ast.BinOp) -> bool:
    """Check if a BinOp node is a midpoint calculation.

    Standard form: (a + b) // 2, (a + b) / 2, (a + b) >> 1
    Overflow-safe form: a + (b - a) // 2, a + (b - a) / 2, a + (b - a) >> 1

    The two variables in the inner operation must be distinct Name nodes.
    This prevents false positives on `len(arr) // 2` or `total // 2`.
    """
    # Standard form: (a + b) // 2  — the BinOp is the division itself
    if _is_divide_by_two(node):
        left = node.left
        if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
            if _is_two_distinct_names(left):
                return True

    # Overflow-safe form: a + (b - a) // 2  — the BinOp is the outer addition
    if isinstance(node.op, ast.Add):
        left = node.left
        right = node.right
        # The right side must be a division-by-2 with a subtraction inside
        if isinstance(right, ast.BinOp) and _is_divide_by_two(right):
            inner = right.left
            if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Sub):
                if _is_name_node(left) and _is_two_distinct_names(inner):
                    return True

    return False


def _midpoint_form_label(node: ast.BinOp) -> str:
    """Return a human-readable label for the midpoint form detected."""
    # Standard form: (a + b) // 2 — node is the division
    if _is_divide_by_two(node):
        left = node.left
        if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
            op_sym = "//" if isinstance(node.op, ast.FloorDiv) else "/" if isinstance(node.op, ast.Div) else ">>"
            a = _get_name_id(left.left)
            b = _get_name_id(left.right)
            return f"({a} + {b}) {op_sym} 2"

    # Overflow-safe form: a + (b - a) // 2 — node is the outer Add
    if isinstance(node.op, ast.Add) and isinstance(node.right, ast.BinOp):
        inner_div = node.right
        op_sym = "//" if isinstance(inner_div.op, ast.FloorDiv) else "/" if isinstance(inner_div.op, ast.Div) else ">>"
        a = _get_name_id(node.left)
        return f"{a} + (overflow-safe {op_sym} 2)"

    return "midpoint calculation"


class _FactExtractor(ast.NodeVisitor):
    """AST visitor that collects structural facts."""

    def __init__(self):
        self._facts: list[StructuralFact] = []
        self._function_defs: dict[str, ast.FunctionDef] = {}
        self._current_func_params: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function_defs[node.name] = node
        # Track function parameters for window detection
        self._current_func_params = {a.arg for a in node.args.args}
        self._detect_self_recursive_call_in_function(node)
        self._detect_recursive_call_in_conditional(node)
        self._detect_multiple_recursive_paths(node)
        self._detect_state_mutation_and_restoration(node)
        self._detect_recursive_depth_tracking(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._function_defs[node.name] = node
        self._detect_self_recursive_call_in_function(node)
        self._detect_recursive_call_in_conditional(node)
        self._detect_multiple_recursive_paths(node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self._detect_while_comparison(node)
        self._detect_opposite_updates_in_loop(node)
        self._detect_linked_traversal_in_loop(node)
        self._detect_carry_in_loop(node)
        self._detect_self_recursive_call_in_loop(node)
        self._detect_loop_body_conditional_updates(node)
        self._detect_variable_use_in_loop_body(node)
        self._detect_parent_pointer_chase(node)
        self._detect_monotonic_comparison(node)
        self._detect_conditional_pop(node)
        self._detect_multiple_pointer_traversal(node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self._detect_linked_traversal_in_for(node)
        self._detect_self_recursive_call_in_loop(node)
        self._detect_for_loop_iteration(node)
        self._detect_conditional_index_update_in_for(node)
        self._detect_variable_use_in_loop_body_for(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        self._detect_equal_assignment(node)
        self._detect_indexed_write(node)
        self._detect_cache_write(node)
        self._detect_queue_creation(node)
        self._detect_visited_tracking(node)
        self._detect_parent_root_merge(node)
        self._detect_stack_creation(node)
        self._detect_pointer_rewiring_in_assign(node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        self._detect_augmented_assignment(node)
        if isinstance(node.target, ast.Subscript):
            self._detect_indexed_write_aug(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self._detect_linked_node_constructor(node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self._detect_linked_attribute_access(node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        self._detect_index_lookback(node)
        self._detect_cache_lookup(node)
        self._detect_neighbor_traversal(node)
        self._detect_window_size_constant(node)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        self._detect_midpoint_calculation(node)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        self._detect_queue_dequeue(node)
        self._detect_stack_operation(node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self._detect_early_termination(node)
        self.generic_visit(node)

    # ----------------------------------------------------------------
    # Detection methods
    # ----------------------------------------------------------------

    def _detect_midpoint_calculation(self, node: ast.BinOp):
        """Detect midpoint-style calculations: (a + b) // 2, a + (b - a) // 2,
        (a + b) >> 1, (a + b) / 2.

        A midpoint calculation divides the sum of two distinct variables by 2
        (or equivalently right-shifts by 1). The two variables must be
        different Name nodes — this prevents false positives on `len(arr) // 2`
        or `total // 2`.

        Forms detected:
        - (a + b) // 2  →  BinOp(FloorDiv, BinOp(Add, Name, Name), Const(2))
        - (a + b) / 2   →  BinOp(Div, BinOp(Add, Name, Name), Const(2))
        - (a + b) >> 1  →  BinOp(RShift, BinOp(Add, Name, Name), Const(1))
        - a + (b - a) // 2  →  BinOp(Add, Name, BinOp(FloorDiv, BinOp(Sub, Name, Name), Const(2)))
        - a + (b - a) / 2   →  BinOp(Add, Name, BinOp(Div, BinOp(Sub, Name, Name), Const(2)))
        - a + (b - a) >> 1  →  BinOp(Add, Name, BinOp(RShift, BinOp(Sub, Name, Name), Const(1)))
        """
        if _is_midpoint_calculation(node):
            self._facts.append(StructuralFact(
                fact_type="midpoint_calculation",
                ast_ref=_ref(node),
                attributes={"form": _midpoint_form_label(node)},
            ))

    def _detect_while_comparison(self, node: ast.While):
        """While-loop with comparison on index variables that are modified.

        Handles:
        - Bare Compare:          while i < n:
        - BoolOp(And, [Compare]): while i < n and total > 0:
        - BoolOp(Or, [Compare]):  while i < n or force:
        - Nested BoolOp:         while (i < n and running > 0) or force:

        Also emits while_loop_truthiness for truthiness-based loops
        (e.g., while queue: while stack:).
        """
        test = node.test
        if isinstance(test, ast.Compare):
            self._emit_while_comparison_from_compares(node, [test])
        elif isinstance(test, ast.BoolOp):
            # Decompose BoolOp into its Compare components.
            # A BoolOp(And/Or, [Compare, Compare, ...]) or nested BoolOps
            # all contribute comparison conditions to the same while loop.
            compares = self._collect_compare_from_boolop(test)
            if compares:
                self._emit_while_comparison_from_compares(node, compares)
        elif isinstance(test, ast.Name):
            # Truthiness-based while loop: while queue:, while stack:
            self._facts.append(StructuralFact(
                fact_type="while_loop_truthiness",
                ast_ref=_ref(node),
                attributes={"variable": test.id},
            ))

    def _emit_while_comparison_from_compares(self, node: ast.While, compares: list):
        """Emit while_loop_comparison from a list of Compare nodes.

        Collects all Name nodes across all comparisons and checks whether
        any compared variable is modified in the loop body.
        """
        comp_names = set()
        for cmp in compares:
            for child in ast.walk(cmp):
                if isinstance(child, ast.Name):
                    comp_names.add(child.id)
        if not comp_names:
            return
        modified = self._collect_body_modified_names(node.body)
        modified.update(self._collect_body_augmented_names(node.body))
        modified_names = comp_names & modified
        if not modified_names:
            return
        self._facts.append(StructuralFact(
            fact_type="while_loop_comparison",
            ast_ref=_ref(node),
            attributes={
                "compared_variables": sorted(comp_names),
                "modified_variables": sorted(modified_names),
            },
        ))

    def _collect_compare_from_boolop(self, node: ast.BoolOp) -> list:
        """Recursively collect all Compare nodes from a BoolOp tree.

        Handles:
        - BoolOp(And, [Compare, Compare])  →  [Compare, Compare]
        - BoolOp(And, [BoolOp(Or, [...])])  →  flattened
        - Nested: BoolOp(Or, [BoolOp(And, [Compare, Compare]), Compare])
        """
        compares = []
        for value in node.values:
            if isinstance(value, ast.Compare):
                compares.append(value)
            elif isinstance(value, ast.BoolOp):
                compares.extend(self._collect_compare_from_boolop(value))
        return compares

    def _detect_opposite_updates_in_loop(self, node: ast.While):
        """Two variables updated in opposite directions within the same loop body."""
        aug_map = self._collect_body_augmented_directions(node.body)
        inc_vars = {v for v, d in aug_map.items() if d == "inc"}
        dec_vars = {v for v, d in aug_map.items() if d == "dec"}
        if inc_vars and dec_vars:
            self._facts.append(StructuralFact(
                fact_type="opposite_direction_updates",
                ast_ref=_ref(node),
                attributes={
                    "incremented": sorted(inc_vars),
                    "decremented": sorted(dec_vars),
                },
            ))

    def _detect_linked_traversal_in_loop(self, node: ast.While):
        """Linked structure attribute access (.next, .left, .right) inside a while loop."""
        attrs = self._collect_linked_attrs(node.body)
        if attrs:
            self._facts.append(StructuralFact(
                fact_type="linked_structure_traversal",
                ast_ref=_ref(node),
                attributes={"attributes": sorted(attrs)},
            ))

    def _detect_linked_traversal_in_for(self, node: ast.For):
        """Linked structure attribute access inside a for loop."""
        attrs = self._collect_linked_attrs(node.body)
        if attrs:
            self._facts.append(StructuralFact(
                fact_type="linked_structure_traversal",
                ast_ref=_ref(node),
                attributes={"attributes": sorted(attrs)},
            ))

    def _detect_carry_in_loop(self, node: ast.While):
        """Carry/accumulator update inside a loop with linked structure traversal."""
        attrs = self._collect_linked_attrs(node.body)
        if not attrs:
            return

        carry_vars = set()
        # Check augmented assignments for carry-like names
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                if _is_carry_name(child.target.id):
                    carry_vars.add(child.target.id)
            # Check tuple unpacking: carry, digit = divmod(val, 10)
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name) and _is_carry_name(elt.id):
                                carry_vars.add(elt.id)

        if carry_vars:
            self._facts.append(StructuralFact(
                fact_type="carry_propagation",
                ast_ref=_ref(node),
                attributes={
                    "carry_variables": sorted(carry_vars),
                    "linked_attrs": sorted(attrs),
                },
            ))

    def _detect_self_recursive_call_in_loop(self, node: ast.While):
        """Self-recursive call inside a while loop body."""
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in self._function_defs:
                    self._facts.append(StructuralFact(
                        fact_type="self_recursive_call",
                        ast_ref=_ref(child),
                        attributes={"function_name": child.func.id, "context": "loop"},
                    ))
                    return

    def _detect_loop_body_conditional_updates(self, node: ast.While):
        """Conditional index/pointer updates inside a loop body."""
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                cond_vars = self._collect_name_ids(stmt.test)
                updated_in_if = self._collect_augmented_names_in(stmt.body)
                updated_in_else = self._collect_augmented_names_in(stmt.orelse) if stmt.orelse else set()
                all_updated = updated_in_if | updated_in_else
                # The condition variables and updated variables should overlap
                # or the updated variables should be index-like
                if all_updated:
                    self._facts.append(StructuralFact(
                        fact_type="conditional_index_update",
                        ast_ref=_ref(stmt),
                        attributes={
                            "condition_variables": sorted(cond_vars),
                            "updated_variables": sorted(all_updated),
                            "branch": "if",
                        },
                    ))

    def _detect_augmented_assignment(self, node: ast.AugAssign):
        """Augmented assignment (+=, -=, etc.) as a structural fact."""
        if isinstance(node.target, ast.Name):
            op_name = type(node.op).__name__
            self._facts.append(StructuralFact(
                fact_type="accumulator_update",
                ast_ref=_ref(node),
                attributes={
                    "variable": node.target.id,
                    "operator": op_name,
                    "syntax_form": "augmented",
                },
            ))

    def _detect_equal_assignment(self, node: ast.Assign):
        """Equal-sign assignment (x = x + expr) as accumulator_update."""
        if len(node.targets) != 1:
            return
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return
        target_name = target.id
        # Check if target appears on the right side (x = x + ...)
        right_names = set()
        for child in ast.walk(node.value):
            if isinstance(child, ast.Name):
                right_names.add(child.id)
        if target_name in right_names:
            op = "unknown"
            if isinstance(node.value, ast.BinOp):
                op = type(node.value.op).__name__
            self._facts.append(StructuralFact(
                fact_type="accumulator_update",
                ast_ref=_ref(node),
                attributes={
                    "variable": target_name,
                    "operator": op,
                    "syntax_form": "equal_sign",
                },
            ))

    def _detect_linked_attribute_access(self, node: ast.Attribute):
        """Linked structure attribute access (.next, .left, .right)."""
        if node.attr in LINKED_ATTRS:
            # Get the receiver variable name
            receiver = ""
            if isinstance(node.value, ast.Name):
                receiver = node.value.id
            self._facts.append(StructuralFact(
                fact_type="linked_attribute_access",
                ast_ref=_ref(node),
                attributes={"attribute": node.attr, "receiver": receiver},
            ))

    def _detect_linked_node_constructor(self, node: ast.Call):
        """Node constructor call (ListNode(...), Node(...), etc.)."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name and _is_node_constructor_name(func_name):
            self._facts.append(StructuralFact(
                fact_type="node_constructor",
                ast_ref=_ref(node),
                attributes={"constructor": func_name, "arg_count": len(node.args)},
            ))

    def _detect_early_termination(self, node: ast.Return):
        """Return statement as potential early termination."""
        self._facts.append(StructuralFact(
            fact_type="early_termination",
            ast_ref=_ref(node),
            attributes={"statement": "return"},
        ))

    def _detect_self_recursive_call_in_function(self, node: ast.FunctionDef):
        """Self-recursive call anywhere in the function body (not just in loops).

        This is a structural observation: the function calls itself.
        """
        func_name = node.name
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == func_name:
                    self._facts.append(StructuralFact(
                        fact_type="self_recursive_call",
                        ast_ref=_ref(child),
                        attributes={"function_name": func_name, "context": "function"},
                    ))
                    return

    def _detect_for_loop_iteration(self, node: ast.For):
        """For-loop with range() or iterable iteration.

        This is a structural observation: the code iterates over a range
        or collection.
        """
        # Check if iterating over range()
        is_range = False
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == "range":
                is_range = True

        # Get the loop variable
        loop_var = ""
        if isinstance(node.target, ast.Name):
            loop_var = node.target.id
        elif isinstance(node.target, ast.Tuple) and node.target.elts:
            if isinstance(node.target.elts[0], ast.Name):
                loop_var = node.target.elts[0].id

        self._facts.append(StructuralFact(
            fact_type="for_loop_iteration",
            ast_ref=_ref(node),
            attributes={
                "loop_variable": loop_var,
                "is_range": is_range,
            },
        ))

    def _detect_conditional_index_update_in_for(self, node: ast.For):
        """Conditional index/pointer updates inside a for-loop body."""
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                cond_vars = self._collect_name_ids(stmt.test)
                updated_in_if = self._collect_augmented_names_in(stmt.body)
                updated_in_else = self._collect_augmented_names_in(stmt.orelse) if stmt.orelse else set()
                all_updated = updated_in_if | updated_in_else
                if all_updated:
                    self._facts.append(StructuralFact(
                        fact_type="conditional_index_update",
                        ast_ref=_ref(stmt),
                        attributes={
                            "condition_variables": sorted(cond_vars),
                            "updated_variables": sorted(all_updated),
                            "branch": "if",
                        },
                    ))

    def _detect_variable_use_in_loop_body_for(self, node: ast.For):
        """Detect conditionally-updated variables used in later for-loop expressions.

        Same logic as _detect_variable_use_in_loop_body but for for-loops.
        """
        cond_vars = set()
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                updated = self._collect_augmented_names_in(stmt.body)
                updated.update(self._collect_augmented_names_in(stmt.orelse) if stmt.orelse else set())
                cond_vars.update(updated)
        if not cond_vars:
            return
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                continue
            used_in_stmt = set()
            for child in ast.walk(stmt):
                if isinstance(child, ast.Name):
                    used_in_stmt.add(child.id)
            intersection = cond_vars & used_in_stmt
            if intersection:
                self._facts.append(StructuralFact(
                    fact_type="variable_use_in_loop_body",
                    ast_ref=_ref(node),
                    attributes={"variables": sorted(intersection)},
                ))
                return

    def _detect_recursive_call_in_conditional(self, node: ast.FunctionDef):
        """Self-recursive call inside an if/else branch within the function.

        This is a structural observation: the recursion is guarded by a
        condition, which means the function has branching recursive paths.
        """
        func_name = node.name
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                # Check if body or orelse contains a self-recursive call
                if self._has_self_recursive_call(stmt.body, func_name):
                    self._facts.append(StructuralFact(
                        fact_type="recursive_call_in_conditional",
                        ast_ref=_ref(stmt),
                        attributes={"function_name": func_name, "branch": "if"},
                    ))
                if stmt.orelse and self._has_self_recursive_call(stmt.orelse, func_name):
                    self._facts.append(StructuralFact(
                        fact_type="recursive_call_in_conditional",
                        ast_ref=_ref(stmt),
                        attributes={"function_name": func_name, "branch": "else"},
                    ))

    def _detect_multiple_recursive_paths(self, node: ast.FunctionDef):
        """Function has 2+ self-recursive call sites with different arguments.

        This is a structural observation: the function explores multiple
        recursive paths (e.g., fib(n-1) + fib(n-2)).
        """
        func_name = node.name
        call_sites = []
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == func_name:
                    # Create a signature from the call arguments
                    arg_sig = ast.dump(child)
                    call_sites.append((child, arg_sig))

        if len(call_sites) >= 2:
            # Check if there are distinct argument patterns
            sigs = set(sig for _, sig in call_sites)
            if len(sigs) >= 2:
                self._facts.append(StructuralFact(
                    fact_type="multiple_recursive_paths",
                    ast_ref=_ref(node),
                    attributes={
                        "function_name": func_name,
                        "call_count": len(call_sites),
                        "distinct_signatures": len(sigs),
                    },
                ))

    def _detect_indexed_write(self, node: ast.Assign):
        """Subscript assignment: arr[i] = value.

        This is a structural observation: a value is written into an
        indexed data structure.
        """
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                # Get the structure name
                struct_name = ""
                if isinstance(target.value, ast.Name):
                    struct_name = target.value.id
                # Get the index expression
                index_desc = type(target.slice).__name__
                self._facts.append(StructuralFact(
                    fact_type="indexed_write",
                    ast_ref=_ref(node),
                    attributes={
                        "structure": struct_name,
                        "index_type": index_desc,
                    },
                ))

    def _detect_indexed_write_aug(self, node: ast.AugAssign):
        """Subscript augmented assignment: arr[i] += value."""
        if isinstance(node.target, ast.Subscript):
            struct_name = ""
            if isinstance(node.target.value, ast.Name):
                struct_name = node.target.value.id
            index_desc = type(node.target.slice).__name__
            self._facts.append(StructuralFact(
                fact_type="indexed_write",
                ast_ref=_ref(node),
                attributes={
                    "structure": struct_name,
                    "index_type": index_desc,
                },
            ))

    def _detect_index_lookback(self, node: ast.Subscript):
        """Subscript access with lookback: arr[i-1], arr[i+1], arr[i-coin], etc.

        This is a structural observation: the code reads from an earlier
        or later position in the same indexed structure.

        Forms detected:
        - arr[i-1]     → Name - Constant
        - arr[i+1]     → Name + Constant
        - arr[i-j]     → Name - Name (e.g., dp[i - coin])
        - arr[i+j]     → Name + Name
        """
        slice_node = node.slice
        # Check for BinOp in the slice: i-1, i+1, i-j, etc.
        if isinstance(slice_node, ast.BinOp) and isinstance(slice_node.op, (ast.Sub, ast.Add)):
            left_name = isinstance(slice_node.left, ast.Name)
            right_const = isinstance(slice_node.right, ast.Constant)
            right_name = isinstance(slice_node.right, ast.Name)
            left_const = isinstance(slice_node.left, ast.Constant)
            # Name op Constant (e.g., i-1, i+1)
            # Name op Name (e.g., i-coin)
            if (left_name and right_const) or (right_name and left_const) or (left_name and right_name):
                struct_name = ""
                if isinstance(node.value, ast.Name):
                    struct_name = node.value.id
                self._facts.append(StructuralFact(
                    fact_type="index_lookback",
                    ast_ref=_ref(node),
                    attributes={
                        "structure": struct_name,
                        "lookback": "sub" if isinstance(slice_node.op, ast.Sub) else "add",
                    },
                ))

    def _detect_cache_lookup(self, node: ast.Subscript):
        """Cache/memo lookup: checking if a value exists in a dict/list cache.

        Detects: var_name[key], cache[key] where var_name looks cache-like.
        This is a structural observation, not a strategy label.
        """
        # Get the variable being subscripted
        var_name = ""
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
        if not var_name:
            return
        cache_like = var_name.lower() in {
            "cache", "memo", "dp", "table", "visited", "seen",
            "memoize", "lookup", "cache_map",
        }
        if not cache_like:
            return
        self._facts.append(StructuralFact(
            fact_type="cache_lookup",
            ast_ref=_ref(node),
            attributes={"cache_variable": var_name},
        ))

    def _detect_neighbor_traversal(self, node: ast.Subscript):
        """Neighbor traversal: graph[node] or adj[u] inside a loop.

        This is a structural observation: indexed access on a graph-like
        structure to get neighbors.
        """
        var_name = ""
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
        if not var_name:
            return
        graph_like = var_name.lower() in {
            "graph", "adj", "adjacency", "adj_list", "adjlist",
            "neighbors", "neighbours", "edges", "g",
        }
        if not graph_like:
            return
        self._facts.append(StructuralFact(
            fact_type="neighbor_traversal",
            ast_ref=_ref(node),
            attributes={"graph_variable": var_name},
        ))

    def _detect_cache_write(self, node: ast.Assign):
        """Cache/memo write: assigning into a dict/list cache structure.

        Detects: cache[key] = value, memo[key] = value, dp[key] = value.
        This is a structural observation, not a strategy label.
        """
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                var_name = ""
                if isinstance(target.value, ast.Name):
                    var_name = target.value.id
                if not var_name:
                    continue
                cache_like = var_name.lower() in {
                    "cache", "memo", "dp", "table", "memoize",
                    "lookup", "cache_map",
                }
                if not cache_like:
                    continue
                self._facts.append(StructuralFact(
                    fact_type="cache_write",
                    ast_ref=_ref(node),
                    attributes={"cache_variable": var_name},
                ))

    def _detect_queue_creation(self, node: ast.Assign):
        """Queue creation: deque() or [] used as queue.

        This is a structural observation: a queue-like data structure is created.
        """
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            # Check if the value is a deque() call
            if isinstance(node.value, ast.Call):
                func_name = ""
                if isinstance(node.value.func, ast.Name):
                    func_name = node.value.func.id
                elif isinstance(node.value.func, ast.Attribute):
                    func_name = node.value.func.attr
                if func_name == "deque":
                    self._facts.append(StructuralFact(
                        fact_type="queue_dequeue",
                        ast_ref=_ref(node),
                        attributes={"queue_variable": var_name, "operation": "creation"},
                    ))
                    return
            # Check if the value is an empty list []
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                queue_like = var_name.lower() in {
                    "queue", "q", "bfs_queue", "frontier",
                    "level_queue", "next_level",
                }
                if queue_like:
                    self._facts.append(StructuralFact(
                        fact_type="queue_dequeue",
                        ast_ref=_ref(node),
                        attributes={"queue_variable": var_name, "operation": "creation"},
                    ))
                    return

    def _detect_state_mutation_and_restoration(self, node: ast.FunctionDef):
        """Detect state mutation before recursive call and restoration after.

        This captures the backtracking pattern:
        1. state.add(x) or path.append(x) before dfs(...)
        2. state.remove(x) or path.pop() after dfs(...)

        The detection is structural: look for mutation/restoration pairs on
        the same variable, with a recursive call between them.

        Handles nested functions and recursive calls inside for/if blocks.
        """
        func_name = node.name
        body = node.body
        # Mutation patterns: add, append
        mutation_methods = {"add", "append"}
        # Restoration patterns: remove, pop
        restoration_methods = {"remove", "pop"}

        # Flatten the body into an ordered list of statements for sequence detection.
        # This handles for-loop bodies, if-blocks, etc.
        flat_stmts = self._flatten_body(body)

        for i, stmt in enumerate(flat_stmts):
            # Find a mutation call: state.add(x) or path.append(x)
            mutation_method, state_var = self._find_method_call(
                stmt, mutation_methods
            )
            if not mutation_method or not state_var:
                continue
            # Look ahead for a recursive call
            for j in range(i + 1, len(flat_stmts)):
                next_stmt = flat_stmts[j]
                has_recursive = self._has_self_recursive_call(
                    [next_stmt], func_name,
                )
                if has_recursive:
                    # Look after the recursive call for restoration
                    for k in range(j + 1, len(flat_stmts)):
                        restore_stmt = flat_stmts[k]
                        restore_method, restore_var = self._find_method_call(
                            restore_stmt, restoration_methods
                        )
                        if restore_method and restore_var == state_var:
                            self._facts.append(StructuralFact(
                                fact_type="state_restoration",
                                ast_ref=_ref(stmt),
                                attributes={
                                    "state_variable": state_var,
                                    "mutation": mutation_method,
                                    "restoration": restore_method,
                                },
                            ))
                            return

    def _flatten_body(self, body: list) -> list:
        """Flatten a function body into an ordered list of statements.

        This handles for-loops, while-loops, and if-blocks by recursively
        extracting their inner statements in order. This allows sequence-based
        detection of mutation → recursive call → restoration patterns.
        """
        result = []
        for stmt in body:
            result.append(stmt)
            if isinstance(stmt, (ast.For, ast.While)):
                result.extend(self._flatten_body(stmt.body))
            elif isinstance(stmt, ast.If):
                result.extend(self._flatten_body(stmt.body))
                result.extend(self._flatten_body(stmt.orelse))
        return result

    def _find_method_call(self, stmt, methods):
        """Find a method call like x.add(y) or x.append(y) in a statement.

        Returns (method_name, variable_name) or (None, None).
        """
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute):
                if call.func.attr in methods:
                    if isinstance(call.func.value, ast.Name):
                        return (call.func.attr, call.func.value.id)
        # Also check for assignment: x = x.method(...)
        if isinstance(stmt, ast.Assign):
            # Not a method call pattern
            pass
        return (None, None)

    def _detect_recursive_depth_tracking(self, node: ast.FunctionDef):
        """Detect depth parameter tracking in recursive functions.

        A depth/level parameter that is passed to recursive calls with
        increment/decrement is a structural observation of depth tracking.
        """
        func_name = node.name
        params = [a.arg for a in node.args.args]
        depth_like = [p for p in params if p.lower() in {
            "depth", "level", "dist", "distance", "step", "steps",
        }]
        if not depth_like:
            return
        depth_param = depth_like[0]
        # Check if the depth parameter is modified in the body
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == func_name:
                    # Check if depth_param appears as an argument with modification
                    for arg in child.args:
                        if isinstance(arg, ast.BinOp):
                            names = set()
                            for n in ast.walk(arg):
                                if isinstance(n, ast.Name):
                                    names.add(n.id)
                            if depth_param in names:
                                self._facts.append(StructuralFact(
                                    fact_type="recursive_depth_tracking",
                                    ast_ref=_ref(node),
                                    attributes={"depth_parameter": depth_param},
                                ))
                                return

    def _detect_variable_use_in_loop_body(self, node: ast.While):
        """Detect conditionally-updated variables used in later loop expressions.

        This captures the sliding-window pattern: a variable (e.g., left) is
        conditionally updated, then used in a later expression like
        max(max_len, right - left + 1). This is a def-use observation.
        """
        # Get conditionally updated variables
        cond_vars = set()
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                updated = self._collect_augmented_names_in(stmt.body)
                updated.update(self._collect_augmented_names_in(stmt.orelse) if stmt.orelse else set())
                cond_vars.update(updated)
        if not cond_vars:
            return
        # Check if these variables appear in statements AFTER the conditional
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                # Check statements after this if-block
                continue
            # This is a statement outside the if-block
            used_in_stmt = set()
            for child in ast.walk(stmt):
                if isinstance(child, ast.Name):
                    used_in_stmt.add(child.id)
            intersection = cond_vars & used_in_stmt
            if intersection:
                self._facts.append(StructuralFact(
                    fact_type="variable_use_in_loop_body",
                    ast_ref=_ref(node),
                    attributes={"variables": sorted(intersection)},
                ))
                return

    def _has_self_recursive_call(self, body: list, func_name: str) -> bool:
        """Check if a body contains a self-recursive call."""
        for child in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == func_name:
                    return True
        return False

    def _detect_visited_tracking(self, node: ast.Assign):
        """Detect visited/seen set creation: visited = set(), seen = set(), etc.

        This is a structural observation: a visited-tracking data structure
        is initialized.
        """
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            if var_name.lower() not in {
                "visited", "seen", "vis", "explored", "seen_set",
            }:
                continue
            # Check if the value is set() or similar
            if isinstance(node.value, ast.Call):
                func_name = ""
                if isinstance(node.value.func, ast.Name):
                    func_name = node.value.func.id
                elif isinstance(node.value.func, ast.Attribute):
                    func_name = node.value.func.attr
                if func_name in {"set", "dict", "defaultdict"}:
                    self._facts.append(StructuralFact(
                        fact_type="visited_tracking",
                        ast_ref=_ref(node),
                        attributes={"variable": var_name},
                    ))
                    return
            # Check for set literal: set() or {start}
            if isinstance(node.value, ast.Set):
                self._facts.append(StructuralFact(
                    fact_type="visited_tracking",
                    ast_ref=_ref(node),
                    attributes={"variable": var_name},
                ))
                return

    def _detect_queue_dequeue(self, node: ast.Expr):
        """Detect queue dequeue operation: queue.popleft(), q.pop(0).

        This is a structural observation: a dequeue operation is performed.
        """
        if not isinstance(node.value, ast.Call):
            return
        call = node.value
        if not isinstance(call.func, ast.Attribute):
            return
        method = call.func.attr
        if method not in {"popleft", "pop"}:
            return
        # For pop(), check if the argument is 0 (pop(0))
        # pop() with no args or pop(non-zero) is NOT a queue dequeue
        if method == "pop":
            if not call.args:
                return  # pop() with no args — stack pop, not queue
            arg = call.args[0]
            if isinstance(arg, ast.Constant) and arg.value == 0:
                pass  # This is pop(0) — queue-like
            else:
                return
        # Get the variable name
        var_name = ""
        if isinstance(call.func.value, ast.Name):
            var_name = call.func.value.id
        if not var_name:
            return
        self._facts.append(StructuralFact(
            fact_type="queue_dequeue",
            ast_ref=_ref(node),
            attributes={"queue_variable": var_name, "operation": "dequeue"},
        ))

    def _detect_parent_pointer_chase(self, node: ast.While):
        """Detect parent-pointer chasing: while parent[x] != x: x = parent[x].

        This is a purely structural observation — no variable names required.
        Detects the while-loop pattern characteristic of union-find root finding:
        - The test compares a subscript with a Name: parent[x] != x
        - The body assigns: x = parent[x] (same structure, same index)
        """
        test = node.test
        if not isinstance(test, ast.Compare):
            return
        if len(test.ops) != 1:
            return
        op = test.ops[0]
        if not isinstance(op, (ast.NotEq, ast.Eq)):
            return
        # Check that one side is a subscript and the other is a Name
        left, right = test.left, test.comparators[0]
        sub_node = None
        name_node = None
        if isinstance(left, ast.Subscript) and isinstance(right, ast.Name):
            sub_node, name_node = left, right
        elif isinstance(right, ast.Subscript) and isinstance(left, ast.Name):
            sub_node, name_node = right, left
        if sub_node is None or name_node is None:
            return
        # The subscript index must be the same Name as the comparison Name
        if not isinstance(sub_node.slice, ast.Name):
            return
        if sub_node.slice.id != name_node.id:
            return
        # Check that the loop body assigns: x = parent[x]
        target_name = name_node.id
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                t = stmt.targets[0]
                if isinstance(t, ast.Name) and t.id == target_name:
                    if isinstance(stmt.value, ast.Subscript):
                        val_sub = stmt.value
                        if (isinstance(val_sub.value, ast.Name) and
                                isinstance(val_sub.slice, ast.Name) and
                                val_sub.slice.id == target_name):
                            # parent[x] = parent[x] pattern found
                            self._facts.append(StructuralFact(
                                fact_type="parent_pointer_chase",
                                ast_ref=_ref(node),
                                attributes={
                                    "structure": val_sub.value.id,
                                    "index_variable": target_name,
                                },
                            ))
                            return

    def _detect_parent_root_merge(self, node: ast.Assign):
        """Detect parent root merge: parent[a] = b.

        This is a purely structural observation — no variable names required.
        Detects the assignment pattern characteristic of union-find merging:
        - Target is a subscript: parent[px] = ...
        - Value is a Name: py
        or
        - Value is a subscript: parent[py]
        """
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not isinstance(target.value, ast.Name):
                continue
            struct_name = target.value.id
            # Check if this is a subscript assignment on a structure
            # The value should be a Name (another root variable) or Subscript (parent[...])
            # The value can be a Name, Subscript, or Call (e.g., find(parent, x))
            if isinstance(node.value, (ast.Name, ast.Subscript, ast.Call)):
                val_type = type(node.value).__name__.lower()
                self._facts.append(StructuralFact(
                    fact_type="parent_root_merge",
                    ast_ref=_ref(node),
                    attributes={
                        "structure": struct_name,
                        "value_type": val_type,
                    },
                ))
                return

    # ----------------------------------------------------------------
    # Phase 5A: Linked-list manipulation
    # ----------------------------------------------------------------

    def _detect_pointer_rewiring_in_assign(self, node: ast.Assign):
        """Detect pointer rewiring: node.next = prev, node.prev = next, etc.

        This is a structural observation: a linked structure pointer is
        being reassigned, which is characteristic of linked-list manipulation.
        """
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr in {"next", "prev"}:
                if isinstance(target.value, ast.Name):
                    self._facts.append(StructuralFact(
                        fact_type="pointer_rewiring",
                        ast_ref=_ref(node),
                        attributes={
                            "receiver": target.value.id,
                            "attribute": target.attr,
                        },
                    ))
                    return

    def _detect_multiple_pointer_traversal(self, node: ast.While):
        """Detect multiple pointers traversing a linked structure.

        This is a structural observation: two or more variables access
        .next/.left/.right attributes in the same loop body.
        """
        # Collect all linked attribute receivers
        receivers = set()
        for stmt in node.body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Attribute) and child.attr in {"next", "left", "right"}:
                    if isinstance(child.value, ast.Name):
                        receivers.add(child.value.id)
        if len(receivers) >= 2:
            self._facts.append(StructuralFact(
                fact_type="multiple_pointer_traversal",
                ast_ref=_ref(node),
                attributes={"receivers": sorted(receivers)},
            ))

    # ----------------------------------------------------------------
    # Phase 5A: Fixed sliding window
    # ----------------------------------------------------------------

    def _detect_window_size_constant(self, node: ast.Subscript):
        """Detect fixed sliding window offset in index expressions.

        This is a structural observation: the code accesses arr[i-k] or arr[i+k]
        where k is a FUNCTION PARAMETER (not a literal constant or loop variable),
        indicating a fixed window size.

        IMPORTANT: Only detects parameter-based offsets (e.g., nums[i - k]).
        Does NOT detect:
        - dp[i - 1]    (literal constant = DP lookback)
        - dp[i - coin]  (loop variable = DP lookback)

        Detects:
        - nums[i - k]  (parameter offset)
        - nums[i + k]  (parameter offset)
        """
        slice_node = node.slice
        # Check for BinOp: i+k, i-k
        if isinstance(slice_node, ast.BinOp) and isinstance(slice_node.op, (ast.Add, ast.Sub)):
            left_name = isinstance(slice_node.left, ast.Name)
            right_name = isinstance(slice_node.right, ast.Name)

            # ONLY detect Name + Name (parameter-based offset)
            if left_name and right_name:
                # Determine which Name is the offset (not the loop variable)
                # The offset should be a function parameter
                left_id = slice_node.left.id if isinstance(slice_node.left, ast.Name) else None
                right_id = slice_node.right.id if isinstance(slice_node.right, ast.Name) else None

                # Check if either is a function parameter
                offset_name = None
                if left_id and left_id in self._current_func_params:
                    offset_name = left_id
                elif right_id and right_id in self._current_func_params:
                    offset_name = right_id

                # Only emit if offset is a function parameter
                if offset_name:
                    struct_name = ""
                    if isinstance(node.value, ast.Name):
                        struct_name = node.value.id
                    self._facts.append(StructuralFact(
                        fact_type="window_size_constant",
                        ast_ref=_ref(node),
                        attributes={
                            "structure": struct_name,
                            "offset": 0,  # Unknown at parse time
                            "offset_type": "parameter",
                            "offset_name": offset_name,
                        },
                    ))

    # ----------------------------------------------------------------
    # Phase 5A: Monotonic stack
    # ----------------------------------------------------------------

    def _detect_stack_creation(self, node: ast.Assign):
        """Detect stack creation: stack = [], st = [], etc.

        This is a structural observation: a list used as a stack is created.
        """
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            # Check if the value is an empty list
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                # Heuristic: variable name looks stack-like
                stack_like = var_name.lower() in {
                    "stack", "st", "monotonic", "mono_stack", "mono",
                    "inc_stack", "dec_stack",
                }
                if stack_like:
                    self._facts.append(StructuralFact(
                        fact_type="stack_operation",
                        ast_ref=_ref(node),
                        attributes={"stack_variable": var_name, "operation": "creation"},
                    ))
                    return

    def _detect_stack_operation(self, node: ast.Expr):
        """Detect stack operations: stack.append(x), stack.pop(), etc.

        This is a structural observation: a stack-like data structure is
        being modified.
        """
        if not isinstance(node.value, ast.Call):
            return
        call = node.value
        if not isinstance(call.func, ast.Attribute):
            return
        method = call.func.attr
        if method not in {"append", "pop"}:
            return
        if not isinstance(call.func.value, ast.Name):
            return
        var_name = call.func.value.id
        # Heuristic: variable name looks stack-like
        stack_like = var_name.lower() in {
            "stack", "st", "monotonic", "mono_stack", "mono",
            "inc_stack", "dec_stack",
        }
        if stack_like:
            self._facts.append(StructuralFact(
                fact_type="stack_operation",
                ast_ref=_ref(node),
                attributes={"stack_variable": var_name, "operation": method},
            ))

    def _detect_monotonic_comparison(self, node: ast.While):
        """Detect monotonic comparison in while-loop with stack access.

        This is a structural observation: the while-loop condition compares
        a value with the top of a stack (stack[-1]).
        
        Patterns detected:
        - while stack and nums[stack[-1]] < nums[i]
        - while stack and arr[stack[-1]] > target
        - while len(stack) > 0 and nums[stack[-1]] < nums[i]
        """
        test = node.test
        # Check for comparisons involving stack[-1] or st[-1]
        # Pattern: while stack and nums[stack[-1]] < nums[i]
        # or: while stack and arr[stack[-1]] > target
        if isinstance(test, ast.BoolOp):
            # Check each operand for stack[-1] access
            for value in test.values:
                if self._has_stack_top_access(value):
                    self._facts.append(StructuralFact(
                        fact_type="monotonic_comparison",
                        ast_ref=_ref(node),
                        attributes={"has_stack_access": True},
                    ))
                    return
        elif isinstance(test, ast.Compare):
            if self._has_stack_top_access(test):
                self._facts.append(StructuralFact(
                    fact_type="monotonic_comparison",
                    ast_ref=_ref(node),
                    attributes={"has_stack_access": True},
                ))
                return
        # Also check for while loop with stack truthiness and comparison in body
        # This handles cases where the comparison is not in the while condition
        # but the while loop checks stack truthiness
        if isinstance(test, ast.Name) and test.id.lower() in {"stack", "st", "monotonic", "mono_stack", "mono"}:
            # Check if the loop body has a comparison with stack[-1]
            for stmt in node.body:
                if isinstance(stmt, ast.If):
                    if self._has_stack_top_access(stmt.test):
                        self._facts.append(StructuralFact(
                            fact_type="monotonic_comparison",
                            ast_ref=_ref(node),
                            attributes={"has_stack_access": True},
                        ))
                        return

    def _has_stack_top_access(self, node: ast.AST) -> bool:
        """Check if an AST node contains stack[-1] or st[-1] access.
        
        Handles both:
        - stack[-1] (Constant with value -1)
        - stack[-1] as UnaryOp(USub, Constant(1)) (Python AST representation)
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript):
                # Check for stack[-1] pattern
                slice_node = child.slice
                is_negative_one = False
                
                # Case 1: Constant(-1)
                if isinstance(slice_node, ast.Constant) and slice_node.value == -1:
                    is_negative_one = True
                # Case 2: UnaryOp(USub, Constant(1))
                elif isinstance(slice_node, ast.UnaryOp) and isinstance(slice_node.op, ast.USub):
                    if isinstance(slice_node.operand, ast.Constant) and slice_node.operand.value == 1:
                        is_negative_one = True
                
                if is_negative_one and isinstance(child.value, ast.Name):
                    var_name = child.value.id.lower()
                    if var_name in {"stack", "st", "monotonic", "mono_stack", "mono"}:
                        return True
        return False

    def _detect_conditional_pop(self, node: ast.While):
        """Detect conditional pop from stack inside a while-loop.

        This is a structural observation: stack.pop() is called inside
        a conditional branch within a while-loop, OR the while loop itself
        has a stack truthiness check followed by a pop.
        
        Patterns detected:
        - while stack: ... stack.pop() ... (pop after truthiness check)
        - while stack and ...: ... stack.pop() ... (pop after comparison)
        """
        # Check if the while condition involves stack truthiness
        test = node.test
        has_stack_check = False
        if isinstance(test, ast.Name) and test.id.lower() in {"stack", "st", "monotonic", "mono_stack", "mono"}:
            has_stack_check = True
        elif isinstance(test, ast.BoolOp):
            for value in test.values:
                if isinstance(value, ast.Name) and value.id.lower() in {"stack", "st", "monotonic", "mono_stack", "mono"}:
                    has_stack_check = True
                    break
        
        if has_stack_check:
            # The while loop checks stack truthiness, so any pop inside is conditional
            if self._has_stack_pop(node.body):
                self._facts.append(StructuralFact(
                    fact_type="conditional_pop",
                    ast_ref=_ref(node),
                    attributes={"has_pop_in_branch": True},
                ))
                return
        
        # Also check for if-blocks with pop
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                # Check if body or orelse contains a pop operation
                if self._has_stack_pop(stmt.body) or self._has_stack_pop(stmt.orelse):
                    self._facts.append(StructuralFact(
                        fact_type="conditional_pop",
                        ast_ref=_ref(stmt),
                        attributes={"has_pop_in_branch": True},
                    ))
                    return

    def _has_stack_pop(self, body: list) -> bool:
        """Check if a body contains a stack.pop() call."""
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if child.func.attr == "pop":
                        if isinstance(child.func.value, ast.Name):
                            var_name = child.func.value.id.lower()
                            if var_name in {"stack", "st", "monotonic", "mono_stack", "mono"}:
                                return True
        return False

    # ----------------------------------------------------------------
    # Helper methods
    # ----------------------------------------------------------------

    def _collect_body_modified_names(self, body: list) -> set:
        """Collect variable names that are modified (assigned) in a loop body."""
        names = set()
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
        return names

    def _collect_body_augmented_names(self, body: list) -> set:
        """Collect variable names that have augmented assignments in a loop body."""
        names = set()
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                    names.add(child.target.id)
        return names

    def _collect_body_augmented_directions(self, body: list) -> dict:
        """Collect variable names and their update directions from augmented assignments."""
        result = {}
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                    name = child.target.id
                    if isinstance(child.op, ast.Add):
                        result[name] = "inc"
                    elif isinstance(child.op, ast.Sub):
                        result[name] = "dec"
        return result

    def _collect_linked_attrs(self, body: list) -> set:
        """Collect linked structure attributes (.next, .left, .right) from a body."""
        attrs = set()
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Attribute) and child.attr in LINKED_ATTRS:
                    attrs.add(child.attr)
        return attrs

    def _collect_augmented_names_in(self, body: list) -> set:
        """Collect names augmented in a list of statements."""
        names = set()
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                    names.add(child.target.id)
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
        return names

    def _collect_name_ids(self, node: ast.AST) -> set:
        """Collect all Name node IDs from an AST subtree."""
        names = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)
        return names

    def _deduplicate(self) -> list[StructuralFact]:
        """Deduplicate facts by (fact_type, ast_ref), keeping first occurrence."""
        seen = set()
        unique = []
        for fact in self._facts:
            key = (fact.fact_type, fact.ast_ref)
            if key not in seen:
                seen.add(key)
                unique.append(fact)
        return unique
