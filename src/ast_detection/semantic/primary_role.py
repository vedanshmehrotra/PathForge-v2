"""Primary-role feature extractor.

Determines whether a structurally detected pattern is the PRIMARY
algorithmic strategy of the code, or merely incidental implementation
behavior (e.g., a visited set in DFS, an index counter in sorting).

Architecture: This module sits above the structural semantic features
(structural_features) and produces role-evidence that can gate whether
a pattern receives authoritative classification.
"""
import ast
from typing import Optional, Set, Dict, List, Tuple
from dataclasses import dataclass, field

from .features import SemanticFeatures, PrimaryRoleFeatures


@dataclass
class CandidateInfo:
    """Information about a candidate pattern's presence in the code."""
    pattern_id: str
    candidate_vars: list = field(default_factory=list)
    variables_terminate_result: bool = False
    drives_decision: bool = False
    result_depends_on_candidate: bool = False
    has_competing_pattern: bool = False


def extract_primary_role(tree: ast.AST, features: SemanticFeatures) -> PrimaryRoleFeatures:
    """Extract primary-role features for all candidate patterns.

    Analyzes data-flow centrality, return-value dependency, and
    competing-pattern presence to determine which patterns are
    primary strategies vs incidental behavior.
    """
    pr = features.primary_role

    # 1. Find what the return value depends on
    return_info = _analyze_return_value(tree)

    # 2. Find what variables are used in the main loop condition and branches
    loop_condition_vars, branch_vars = _analyze_control_flow(tree)

    # 3. For each candidate pattern, check centrality
    _check_two_pointers_centrality(tree, features, pr, return_info, loop_condition_vars, branch_vars)
    _check_prefix_sum_centrality(tree, features, pr, return_info, loop_condition_vars, branch_vars)
    _check_hash_map_centrality(tree, features, pr, return_info, loop_condition_vars, branch_vars)
    _check_competing_patterns(tree, features, pr)

    return pr


def _analyze_return_value(tree: ast.AST) -> dict:
    """Find what variables/expressions the return value depends on."""
    info = {"return_vars": set(), "return_expressions": []}

    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value:
            info["return_expressions"].append(node.value)
            for child in ast.walk(node.value):
                if isinstance(child, ast.Name):
                    info["return_vars"].add(child.id)

    return info


def _analyze_control_flow(tree: ast.AST) -> Tuple[Set[str], Set[str]]:
    """Find variables used in loop conditions and branch decisions."""
    condition_vars = set()
    branch_vars = set()

    for node in ast.walk(tree):
        # Loop conditions
        if isinstance(node, (ast.While, ast.For)):
            if isinstance(node, ast.While):
                for child in ast.walk(node.test):
                    if isinstance(child, ast.Name):
                        condition_vars.add(child.id)
            elif isinstance(node, ast.For):
                # For-loop variables (the target) are in condition_vars
                for child in ast.walk(node.target):
                    if isinstance(child, ast.Name):
                        condition_vars.add(child.id)

        # Branch decisions (if/elif/else)
        if isinstance(node, ast.If):
            for child in ast.walk(node.test):
                if isinstance(child, ast.Name):
                    branch_vars.add(child.id)

    return condition_vars, branch_vars


def _check_two_pointers_centrality(tree: ast.AST, features: SemanticFeatures,
                                    pr: PrimaryRoleFeatures,
                                    return_info: dict,
                                    condition_vars: set, branch_vars: set) -> None:
    """Check if bidirectional movement is central to the algorithm.

    Two pointers is central when:
    - Both pointer variables influence comparisons
    - The result depends on which pointer is at what position
    - There is no competing binary-search or sorting pattern
    """
    if not features.pointers.has_bidirectional:
        return

    # Find all variables that move
    incr_vars = set()
    decr_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            if isinstance(node.op, ast.Add) and isinstance(node.value, ast.Constant) and node.value.value == 1:
                incr_vars.add(node.target.id)
            elif isinstance(node.op, ast.Sub) and isinstance(node.value, ast.Constant) and node.value.value == 1:
                decr_vars.add(node.target.id)

    all_pointer_vars = incr_vars | decr_vars

    # Check: do both pointer variables appear in return, conditions, or branches?
    in_return = all_pointer_vars & return_info["return_vars"]
    in_conditions = all_pointer_vars & condition_vars
    in_branches = all_pointer_vars & branch_vars

    if len(in_return) + len(in_conditions) + len(in_branches) >= 2:
        pr.result_depends_on_candidate = True
        pr.candidate_vars_terminate_result = bool(in_return)
        pr.candidate_drives_decision = bool(in_conditions | in_branches)
        pr.candidate_vars = list(all_pointer_vars)


def _check_prefix_sum_centrality(tree: ast.AST, features: SemanticFeatures,
                                  pr: PrimaryRoleFeatures,
                                  return_info: dict,
                                  condition_vars: set, branch_vars: set) -> None:
    """Check if accumulation is central to the algorithm.

    Prefix sum is central when:
    - The accumulated value is used later to make decisions or compose the result
    - It's not just a counter (i += 1)
    - The accumulated value feeds into array lookups or comparisons
    """
    if not features.accumulation.has_accumulation:
        return
    if not features.accumulation.has_numeric_accumulation:
        return

    acc_var = features.accumulation.accumulator_var
    if not acc_var:
        return

    # Simple counter (i += 1) is NOT prefix sum centrality
    if features.accumulation.accumulator_op == "+=" and features.accumulation.accumulator_source == "1":
        pr.has_simple_counter = True
        return

    # Check if the accumulator variable is used in return, conditions, or branches
    # Also check if it's used as a subscript index (prefix_sum determines position)
    acc_in_return = acc_var in return_info["return_vars"]
    acc_in_conditions = acc_var in condition_vars
    acc_in_branches = acc_var in branch_vars

    # Check subscript usage of accumulator
    acc_in_subscript = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Name) and node.slice.id == acc_var:
                acc_in_subscript = True
                break
            # Check if acc_var is in subscript (e.g., nums[acc_var])
            for child in ast.walk(node.slice):
                if isinstance(child, ast.Name) and child.id == acc_var:
                    acc_in_subscript = True
                    break

    centrality_signals = sum([acc_in_return, acc_in_conditions, acc_in_branches, acc_in_subscript])

    if centrality_signals >= 2:
        pr.result_depends_on_candidate = True
        pr.candidate_vars_terminate_result = acc_in_return
        pr.candidate_drives_decision = acc_in_conditions or acc_in_branches
        pr.candidate_vars = [acc_var]

    # Also check: is the accumulator used as input to a later calculation?
    # e.g., prefix[-1] in a condition or expression
    if features.accumulation.has_append_accumulation or features.accumulation.has_assignment_accumulation:
        pr.result_depends_on_candidate = True
        pr.candidate_vars = [acc_var] if not pr.candidate_vars else pr.candidate_vars


def _check_hash_map_centrality(tree: ast.AST, features: SemanticFeatures,
                                pr: PrimaryRoleFeatures,
                                return_info: dict,
                                condition_vars: set, branch_vars: set) -> None:
    """Check if hash map lookup is central vs incidental bookkeeping.

    hash_map_lookup is central when:
    - The lookup result (in/True/False) determines control flow
    - The lookup is not just visited-set or frequency-counting

    hash_map_lookup is INCIDENTAL when:
    - dict/set is used only for visited tracking
    - dict is used for frequency counting but result doesn't depend on it
    - the dict construction is inside a loop but the main loop logic doesn't use it
    """
    if not features.access.has_membership_test:
        return

    membership_var = features.access.membership_collection

    # Determine if this is bookkeeping (visited/frequency) vs primary lookup
    is_bookkeeping = False

    # Check: is the dict/set used only in an 'if x in seen' guard before a 'continue' or 'pass'?
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check if condition contains membership test on membership_var
            condition_has_membership = False
            for child in ast.walk(node.test):
                if isinstance(child, ast.Compare):
                    for op in child.ops:
                        if isinstance(op, (ast.In, ast.NotIn)):
                            if isinstance(child.comparators[0], ast.Name):
                                if child.comparators[0].id == membership_var:
                                    condition_has_membership = True

            if condition_has_membership:
                # Check if the body is just continue/pass/break (bookkeeping guard)
                body_is_guard = False
                for stmt in node.body:
                    if isinstance(stmt, (ast.Continue, ast.Pass, ast.Break)):
                        body_is_guard = True
                    elif isinstance(stmt, ast.If):
                        # Nested: if x in seen: if already in result: return → could be primary
                        # But simple if x in seen: continue is bookkeeping
                        pass
                if body_is_guard:
                    is_bookkeeping = True

    # Check: is the dict/set populated in a loop and the result doesn't depend on it?
    has_populate_in_loop = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for child in ast.walk(node):
                if isinstance(child, ast.Subscript):
                    if isinstance(child.ctx, ast.Store):
                        if isinstance(child.value, ast.Name) and child.value.id == membership_var:
                            has_populate_in_loop = True
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if child.func.attr == 'get':
                            if isinstance(child.func.value, ast.Name) and child.func.value.id == membership_var:
                                has_populate_in_loop = True

    # Check: does the return value depend on the lookup variable or lookup results?
    in_return = False
    for var in return_info["return_vars"]:
        if var in features.access.membership_vars:
            in_return = True
            break

    # Bookkeeping detection
    pr.has_hash_bookkeeping = is_bookkeeping

    # If the lookup drives control flow, it's more likely primary
    if not is_bookkeeping and (in_return or has_populate_in_loop):
        pr.result_depends_on_candidate = True
        pr.candidate_vars_terminate_result = in_return
        pr.candidate_drives_decision = has_populate_in_loop


def _check_competing_patterns(tree: ast.AST, features: SemanticFeatures,
                               pr: PrimaryRoleFeatures) -> None:
    """Check for competing patterns that explain the same code.

    If a stronger/more-specific pattern explains the code, the candidate
    pattern is likely incidental.
    """
    # Check for binary search signals (stronger than two pointers in many cases)
    has_mid_computation = False
    has_left_right = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "mid":
                    has_mid_computation = True
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id in ("left", "right", "lo", "hi"):
                has_left_right = True

    if has_mid_computation and has_left_right:
        pr.has_competing_loop_pattern = True

    # Check for sorting-like patterns (inner loop swapping)
    has_nested_comparison_swap = False
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for inner in ast.walk(node):
                if isinstance(inner, ast.If):
                    for child in ast.walk(inner):
                        if isinstance(child, ast.Subscript) and isinstance(child.ctx, ast.Store):
                            has_nested_comparison_swap = True
    if has_nested_comparison_swap and features.loops.for_loops >= 2:
        pr.has_competing_loop_pattern = True
