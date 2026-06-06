import ast


class ASTFeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        self.function_stack = []
        self.current_loop_depth = 0
        self.loop_stack = []
        self.recursive_function_depth = 0

        self.has_recursion = False
        self.has_loop = False
        self.max_loop_depth = 0
        self.has_dict_creation = False
        self.has_set_creation = False
        self.dict_updates = False
        self.dict_increments = False
        self.has_membership_check = False
        self.has_conditional = False
        self.has_helper_function = False
        self.has_dp_array = False
        self.has_index_lookback = False
        self.has_math_max_min = False
        self.has_sorting = False
        self.has_return = 0

        self.has_queue_creation = False
        self.has_deque_popleft = False
        self.has_heap_operations = False
        self.has_node_attributes = False
        self.has_node_value = False
        self.has_node_value_compare = False
        self.has_node_next = False
        self.has_node_left_right = False
        self.has_mid_calculation = False
        self.has_key_based_sorting = False
        self.has_stack_negative_index = False
        self.has_union_find_keywords = False
        self.has_list_copy_slice = False
        self.has_list_stack_ops = False
        self.has_monotonic_comparison = False
        self.has_deque_window_ops = False
        self.has_augmented_addition = False
        self.has_subtraction = False
        self.has_subscript_write = False
        self.has_prefix_sum_array = False
        self.has_2d_array = False
        self.has_grid_lookback = False
        self.has_string_compare = False
        self.has_capacity_compare = False
        self.has_distance_tracking = False
        self.has_indegree_tracking = False
        self.has_adjacency_iteration = False
        self.has_path_accumulator = False
        self.has_reverse_pointer_update = False
        self.has_fast_slow_pointers = False
        self.has_binary_search_loop = False
        self.has_rotated_array_condition = False
        self.has_answer_search = False
        self.has_backtracking_branch = False
        self.has_recursive_loop = False
        self.has_interval_access = False
        self.has_pointer_updates = False
        self.has_opposite_pointer_updates = False

        self._list_appends = set()
        self._list_pops = set()
        self._deque_appends = set()
        self._deque_poplefts = set()
        self._name_hits = set()
        self._loop_aug_add = set()
        self._loop_aug_sub = set()

    def visit_FunctionDef(self, node):
        if self.function_stack:
            self.has_helper_function = True
        if node.name.lower() in ("find", "union", "find_parent", "union_find"):
            self.has_union_find_keywords = True

        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_For(self, node):
        self._enter_loop()
        self.visit(node.target)
        self.visit(node.iter)
        if self._contains_name(node.iter, ("adj", "graph", "neighbors", "edges")):
            self.has_adjacency_iteration = True
        for child in node.body:
            self.visit(child)
        for child in node.orelse:
            self.visit(child)
        self._exit_loop()

    def visit_While(self, node):
        self._enter_loop()
        if self._is_binary_search_test(node.test):
            self.has_binary_search_loop = True
        self.visit(node.test)
        for child in node.body:
            self.visit(child)
        for child in node.orelse:
            self.visit(child)
        self._exit_loop()

    def visit_If(self, node):
        self.has_conditional = True
        if self.current_loop_depth and self._contains_compare_op(node.test, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)):
            self.has_monotonic_comparison = True
        if (
            self.has_mid_calculation
            and self._contains_name(node.test, ("nums", "arr"))
            and self._contains_name(node.test, ("left", "right", "lo", "hi"))
        ):
            self.has_rotated_array_condition = True
        self.generic_visit(node)

    def visit_Return(self, node):
        self.has_return += 1
        if self._contains_name(node.value, ("left", "right", "lo", "hi", "answer", "ans")):
            self.has_answer_search = True
        self.generic_visit(node)

    def visit_Dict(self, node):
        self.has_dict_creation = True
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.has_dict_creation = True
        self.generic_visit(node)

    def visit_Set(self, node):
        self.has_set_creation = True
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.has_set_creation = True
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.has_dp_array = True
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op in node.ops:
            if isinstance(op, (ast.In, ast.NotIn)):
                self.has_membership_check = True
        if self._has_node_value_compare(node):
            self.has_node_value_compare = True
        if self._contains_name(node, ("capacity", "cap", "weight", "wt")):
            self.has_capacity_compare = True
        if self._string_compare(node):
            self.has_string_compare = True
        self.generic_visit(node)

    def visit_Call(self, node):
        call_name = self._call_name(node)
        receiver = self._receiver_name(node)

        if call_name in self.function_stack:
            self.has_recursion = True
            if self.current_loop_depth:
                self.has_recursive_loop = True

        if call_name in ("dict", "defaultdict"):
            self.has_dict_creation = True
        elif call_name == "set":
            self.has_set_creation = True
        elif call_name == "Counter":
            self.has_dict_creation = True
            self.dict_increments = True
        elif call_name in ("deque", "Queue", "SimpleQueue"):
            self.has_queue_creation = True
        elif call_name in ("max", "min"):
            self.has_math_max_min = True
        elif call_name == "sorted":
            self.has_sorting = True
            if node.keywords:
                self.has_key_based_sorting = any(k.arg == "key" for k in node.keywords)
        elif call_name in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace"):
            self.has_heap_operations = True

        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("update", "setdefault"):
                self.dict_updates = True
            elif attr == "sort":
                self.has_sorting = True
                self.has_key_based_sorting = any(k.arg == "key" for k in node.keywords)
            elif attr == "append" and receiver:
                self._list_appends.add(receiver)
                if receiver in self._deque_poplefts:
                    self.has_deque_window_ops = True
            elif attr == "pop" and receiver:
                self._list_pops.add(receiver)
            elif attr == "popleft" and receiver:
                self.has_deque_popleft = True
                self._deque_poplefts.add(receiver)
                if receiver in self._list_appends:
                    self.has_deque_window_ops = True
            elif attr == "copy":
                self.has_list_copy_slice = True

        if self._list_appends & self._list_pops:
            self.has_list_stack_ops = True
        if self._list_appends & self._deque_poplefts:
            self.has_deque_window_ops = True

        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr == "next":
            self.has_node_attributes = True
            self.has_node_next = True
        elif node.attr in ("left", "right"):
            self.has_node_attributes = True
            self.has_node_left_right = True
        elif node.attr in ("val", "value", "key"):
            self.has_node_attributes = True
            self.has_node_value = True
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mult) and (isinstance(node.left, ast.List) or isinstance(node.right, ast.List)):
            self.has_dp_array = True
            if self._contains_nested_list(node.left) or self._contains_nested_list(node.right):
                self.has_2d_array = True
        if isinstance(node.op, (ast.FloorDiv, ast.Div)) and self._has_constant(node, 2):
            self.has_mid_calculation = True
        if isinstance(node.op, ast.RShift) and self._has_constant(node, 1):
            self.has_mid_calculation = True
        if isinstance(node.op, ast.Sub):
            self.has_subtraction = True
        self.generic_visit(node)

    def visit_Subscript(self, node):
        slice_node = self._slice_value(node.slice)
        if isinstance(slice_node, ast.BinOp) and isinstance(slice_node.op, ast.Sub):
            self.has_index_lookback = True
        if isinstance(slice_node, ast.UnaryOp) and isinstance(slice_node.op, ast.USub):
            self.has_stack_negative_index = True
        if isinstance(slice_node, ast.Slice):
            self.has_list_copy_slice = True
        if self._nested_subscript(node):
            self.has_grid_lookback = True
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if isinstance(node.op, ast.Add):
            self.has_augmented_addition = True
        if isinstance(node.target, ast.Subscript):
            self.dict_updates = True
            self.has_subscript_write = True
            if isinstance(node.op, ast.Add):
                self.dict_increments = True
        elif isinstance(node.target, ast.Name):
            self._record_pointer_update(node.target.id, node.op)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self._record_assignment_target(target, node.value)
            if isinstance(target, ast.Subscript):
                self.dict_updates = True
                self.has_subscript_write = True
                if self._is_get_increment(node.value):
                    self.dict_increments = True
                if self._is_prefix_sum_assignment(target, node.value):
                    self.has_prefix_sum_array = True
            elif isinstance(target, ast.Name):
                if self._keyword_hit(target.id, ("parent", "rank")):
                    self.has_union_find_keywords = True
                if self._keyword_hit(target.id, ("indegree", "in_degree", "degree")):
                    self.has_indegree_tracking = True
                if self._keyword_hit(target.id, ("dist", "distance", "steps", "level")):
                    self.has_distance_tracking = True
                if self._keyword_hit(target.id, ("path", "depth")):
                    self.has_path_accumulator = True
                if self._keyword_hit(target.id, ("slow", "fast")):
                    self._name_hits.add(target.id)
                    self.has_fast_slow_pointers = {"slow", "fast"}.issubset(self._name_hits)
                if self._keyword_hit(target.id, ("ans", "answer", "best", "res")) and self.has_mid_calculation:
                    self.has_answer_search = True
                if self._is_reverse_pointer_update(target, node.value):
                    self.has_reverse_pointer_update = True
        self.generic_visit(node)

    def visit_Name(self, node):
        if self._keyword_hit(node.id, ("parent", "rank")) or node.id.lower() in ("find", "union"):
            self.has_union_find_keywords = True
        if self._keyword_hit(node.id, ("indegree", "in_degree")):
            self.has_indegree_tracking = True
        if self._keyword_hit(node.id, ("dist", "distance", "steps", "level")):
            self.has_distance_tracking = True
        if self._keyword_hit(node.id, ("interval", "start", "end")):
            self.has_interval_access = True
        if node.id in ("slow", "fast"):
            self._name_hits.add(node.id)
            self.has_fast_slow_pointers = {"slow", "fast"}.issubset(self._name_hits)

    def _enter_loop(self):
        self.has_loop = True
        self.current_loop_depth += 1
        self.loop_stack.append({"add": set(), "sub": set()})
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)

    def _exit_loop(self):
        frame = self.loop_stack.pop()
        if frame["add"] and frame["sub"]:
            self.has_opposite_pointer_updates = True
        if len(frame["add"]) >= 2:
            self.has_pointer_updates = True
        self.current_loop_depth -= 1

    def _record_pointer_update(self, name, op):
        if not self.loop_stack:
            return
        if isinstance(op, ast.Add):
            self.loop_stack[-1]["add"].add(name)
        elif isinstance(op, ast.Sub):
            self.loop_stack[-1]["sub"].add(name)
        self.has_pointer_updates = True

    def _record_assignment_target(self, target, value):
        if isinstance(target, ast.Tuple):
            names = [elt.id for elt in target.elts if isinstance(elt, ast.Name)]
            if {"slow", "fast"}.issubset(set(names)):
                self.has_fast_slow_pointers = True
        if isinstance(value, ast.List):
            self.has_dp_array = True
            if any(isinstance(elt, ast.List) for elt in value.elts):
                self.has_2d_array = True
        if self._contains_nested_list(value):
            self.has_2d_array = True
            self.has_dp_array = True

    @staticmethod
    def _slice_value(node):
        if hasattr(ast, "Index") and isinstance(node, ast.Index):
            return node.value
        return node

    @staticmethod
    def _call_name(node):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    @staticmethod
    def _receiver_name(node):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            return node.func.value.id
        return ""

    @staticmethod
    def _keyword_hit(name, keywords):
        lowered = name.lower()
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _has_constant(node, value):
        return any(isinstance(child, ast.Constant) and child.value == value for child in ast.walk(node))

    @staticmethod
    def _contains_name(node, names):
        if node is None:
            return False
        lowered = tuple(name.lower() for name in names)
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and any(part in child.id.lower() for part in lowered):
                return True
            if isinstance(child, ast.Attribute) and any(part in child.attr.lower() for part in lowered):
                return True
        return False

    @staticmethod
    def _contains_compare_op(node, op_types):
        return any(isinstance(op, op_types) for child in ast.walk(node) if isinstance(child, ast.Compare) for op in child.ops)

    @staticmethod
    def _contains_nested_list(node):
        return node is not None and any(isinstance(child, ast.ListComp) for child in ast.walk(node))

    @staticmethod
    def _nested_subscript(node):
        return isinstance(node.value, ast.Subscript) or any(isinstance(child, ast.Subscript) for child in ast.iter_child_nodes(node.value))

    @staticmethod
    def _is_get_increment(node):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            return False
        return any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "get" for child in ast.walk(node))

    def _is_prefix_sum_assignment(self, target, value):
        if not isinstance(target.value, ast.Name):
            return False
        target_name = target.value.id
        lookbacks = 0
        for child in ast.walk(value):
            if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name) and child.value.id == target_name:
                slice_node = self._slice_value(child.slice)
                if isinstance(slice_node, ast.BinOp) and isinstance(slice_node.op, ast.Sub):
                    lookbacks += 1
        return lookbacks == 1 and isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)

    @staticmethod
    def _string_compare(node):
        return any(isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name) and child.value.id.lower() in ("s", "t", "word", "text") for child in ast.walk(node))

    @staticmethod
    def _is_binary_search_test(node):
        if not isinstance(node, ast.Compare):
            return False
        names = {child.id.lower() for child in ast.walk(node) if isinstance(child, ast.Name)}
        return bool(names & {"left", "right", "lo", "hi", "l", "r"})

    @staticmethod
    def _is_reverse_pointer_update(target, value):
        if not isinstance(target, ast.Attribute) or target.attr != "next":
            return False
        return isinstance(value, (ast.Name, ast.Attribute, ast.Constant))

    @staticmethod
    def _has_node_value_compare(node):
        return any(
            isinstance(child, ast.Attribute) and child.attr in ("val", "value", "key")
            for child in ast.walk(node)
        )


def extract_features(ast_root: ast.AST) -> dict:
    extractor = ASTFeatureExtractor()
    extractor.visit(ast_root)

    return {
        key: value
        for key, value in extractor.__dict__.items()
        if key.startswith("has_") or key in ("max_loop_depth", "dict_updates", "dict_increments")
    }
