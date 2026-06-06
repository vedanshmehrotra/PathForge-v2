from pathforge.ast_engine.patterns import (
    ALL_PATTERNS,
    BACKTRACKING_PERMUTATION,
    BACKTRACKING_SUBSET,
    BINARY_SEARCH_TREE,
    BFS_LEVEL_ORDER,
    BFS_SHORTEST_PATH,
    BINARY_SEARCH_ANSWER,
    BINARY_SEARCH_ROTATED,
    BINARY_SEARCH_STANDARD,
    DFS_ITERATIVE,
    DFS_RECURSIVE,
    DP_1D_FORWARD,
    DP_1D_SEQUENCE,
    DP_2D_GRID,
    DP_2D_STRING,
    DP_INTERVAL,
    DP_KNAPSACK,
    DP_STATE_MACHINE,
    FAST_SLOW_POINTERS,
    GREEDY_INTERVAL,
    GREEDY_LOCAL,
    HASH_MAP_FREQUENCY,
    HASH_MAP_LOOKUP,
    HEAP_TOP_K,
    LINKED_LIST_REVERSAL,
    MONOTONIC_DEQUE,
    MONOTONIC_STACK,
    PREFIX_SUM,
    SLIDING_WINDOW_FIXED,
    SLIDING_WINDOW_VARIABLE,
    TOPOLOGICAL_SORT,
    TWO_POINTERS_OPPOSITE,
    TWO_POINTERS_SAME,
    UNION_FIND,
)


class ASTPatternClassifier:
    def classify(self, features: dict) -> dict:
        scores = {pattern: 0.0 for pattern in ALL_PATTERNS}
        f = features.get

        self._score(scores, DFS_RECURSIVE, [
            (f("has_recursion"), 0.5),
            (f("has_helper_function"), 0.2),
            (f("has_conditional"), 0.1),
            (f("has_return", 0) > 0, 0.1),
            (not f("has_dp_array"), 0.1),
        ])
        self._score(scores, DFS_ITERATIVE, [
            (f("has_loop"), 0.3),
            (f("has_list_stack_ops"), 0.45),
            (f("has_stack_negative_index"), 0.2),
            (f("has_adjacency_iteration"), 0.1),
            (not f("has_recursion"), 0.1),
        ])
        self._score(scores, BFS_LEVEL_ORDER, [
            (f("has_queue_creation"), 0.4),
            (f("has_loop"), 0.2),
            (f("has_deque_popleft"), 0.3),
            (f("has_distance_tracking"), 0.1),
        ])
        self._score(scores, BFS_SHORTEST_PATH, [
            (f("has_queue_creation"), 0.3),
            (f("has_deque_popleft"), 0.2),
            (f("has_loop"), 0.2),
            (f("has_distance_tracking"), 0.3),
        ])
        self._score(scores, TOPOLOGICAL_SORT, [
            (f("has_indegree_tracking"), 0.35),
            (f("has_queue_creation") or f("has_deque_popleft"), 0.25),
            (f("has_adjacency_iteration"), 0.25),
            (f("has_loop"), 0.15),
        ])
        self._score(scores, UNION_FIND, [
            (f("has_union_find_keywords"), 0.75),
            (f("has_loop") or f("has_recursion"), 0.25),
        ])
        self._score(scores, BINARY_SEARCH_TREE, [
            (f("has_node_left_right"), 0.3),
            (f("has_node_value_compare"), 0.3),
            (f("has_recursion"), 0.25),
            (f("has_conditional"), 0.15),
        ])

        self._score(scores, HASH_MAP_LOOKUP, [
            (f("has_membership_check"), 0.4),
            (f("has_dict_creation") or f("has_set_creation"), 0.3),
            (not f("dict_increments") and not f("has_list_stack_ops"), 0.2),
            (f("has_loop"), 0.1),
        ])
        self._score(scores, HASH_MAP_FREQUENCY, [
            (f("dict_increments"), 0.5),
            (f("has_loop"), 0.2),
            (f("has_dict_creation"), 0.2),
            (f("has_membership_check"), 0.1),
        ])
        self._score(scores, PREFIX_SUM, [
            (f("has_prefix_sum_array"), 0.55),
            (f("has_loop"), 0.2),
            (f("has_augmented_addition") or f("has_subscript_write"), 0.15),
            (not f("has_conditional"), 0.1),
        ])
        self._score(scores, SLIDING_WINDOW_FIXED, [
            (f("has_loop"), 0.35),
            (f("has_subtraction"), 0.25),
            (f("has_augmented_addition"), 0.2),
            (not f("has_conditional"), 0.2),
        ])
        self._score(scores, SLIDING_WINDOW_VARIABLE, [
            (f("has_loop"), 0.35),
            (f("has_subtraction"), 0.2),
            (f("has_augmented_addition"), 0.15),
            (f("has_conditional"), 0.3),
        ])
        self._score(scores, TWO_POINTERS_OPPOSITE, [
            (f("has_loop"), 0.35),
            (f("has_opposite_pointer_updates"), 0.35),
            (f("has_subtraction"), 0.15),
            (f("has_conditional"), 0.15),
        ])
        self._score(scores, TWO_POINTERS_SAME, [
            (f("has_loop"), 0.35),
            (f("has_pointer_updates"), 0.35),
            (not f("has_opposite_pointer_updates"), 0.15),
            (f("has_conditional"), 0.15),
        ])

        self._score(scores, DP_1D_FORWARD, [
            (f("has_dp_array"), 0.4),
            (f("has_index_lookback"), 0.3),
            (f("has_loop"), 0.2),
            (not f("has_recursion") and not f("has_prefix_sum_array"), 0.1),
        ])
        self._score(scores, DP_1D_SEQUENCE, [
            (f("has_dp_array"), 0.35),
            (f("has_index_lookback"), 0.2),
            (f("has_loop"), 0.2),
            (f("max_loop_depth", 0) >= 2 or f("has_math_max_min"), 0.25),
        ])
        self._score(scores, DP_2D_GRID, [
            (f("has_2d_array"), 0.35),
            (f("max_loop_depth", 0) >= 2, 0.3),
            (f("has_grid_lookback") or f("has_index_lookback"), 0.25),
            (not f("has_string_compare"), 0.1),
        ])
        self._score(scores, DP_2D_STRING, [
            (f("has_2d_array"), 0.35),
            (f("max_loop_depth", 0) >= 2, 0.25),
            (f("has_string_compare"), 0.3),
            (f("has_index_lookback") or f("has_grid_lookback"), 0.1),
        ])
        self._score(scores, DP_KNAPSACK, [
            (f("has_dp_array"), 0.3),
            (f("max_loop_depth", 0) >= 2, 0.25),
            (f("has_capacity_compare"), 0.3),
            (f("has_math_max_min"), 0.15),
        ])
        self._score(scores, DP_INTERVAL, [
            (f("has_dp_array"), 0.4),
            (f("max_loop_depth", 0) >= 2, 0.3),
            (f("has_math_max_min"), 0.3),
        ])
        self._score(scores, DP_STATE_MACHINE, [
            (f("has_dp_array"), 0.4),
            (f("has_conditional"), 0.3),
            (f("has_math_max_min"), 0.2),
            (f("has_loop"), 0.1),
        ])

        self._score(scores, FAST_SLOW_POINTERS, [
            (f("has_fast_slow_pointers"), 0.5),
            (f("has_node_next"), 0.3),
            (f("has_loop"), 0.2),
        ])
        self._score(scores, LINKED_LIST_REVERSAL, [
            (f("has_node_next"), 0.35),
            (f("has_reverse_pointer_update"), 0.45),
            (f("has_loop"), 0.2),
        ])
        self._score(scores, MONOTONIC_STACK, [
            (f("has_list_stack_ops"), 0.35),
            (f("has_stack_negative_index"), 0.25),
            (f("has_monotonic_comparison"), 0.25),
            (f("has_loop"), 0.15),
        ])
        self._score(scores, MONOTONIC_DEQUE, [
            (f("has_queue_creation"), 0.25),
            (f("has_deque_popleft") or f("has_deque_window_ops"), 0.35),
            (f("has_stack_negative_index"), 0.15),
            (f("has_loop"), 0.25),
        ])

        self._score(scores, BINARY_SEARCH_STANDARD, [
            (f("has_mid_calculation"), 0.45),
            (f("has_binary_search_loop"), 0.35),
            (f("has_return", 0) > 0, 0.2),
        ])
        self._score(scores, BINARY_SEARCH_ROTATED, [
            (f("has_mid_calculation"), 0.35),
            (f("has_binary_search_loop"), 0.25),
            (f("has_rotated_array_condition"), 0.3),
            (f("has_conditional"), 0.1),
        ])
        self._score(scores, BINARY_SEARCH_ANSWER, [
            (f("has_mid_calculation"), 0.35),
            (f("has_binary_search_loop"), 0.25),
            (f("has_answer_search"), 0.3),
            (f("has_math_max_min") or f("has_conditional"), 0.1),
        ])

        self._score(scores, HEAP_TOP_K, [
            (f("has_heap_operations"), 0.8),
            (f("has_loop"), 0.2),
        ])
        self._score(scores, GREEDY_LOCAL, [
            (f("has_loop"), 0.4),
            (f("has_math_max_min"), 0.3),
            (not f("has_dp_array") and not f("has_index_lookback"), 0.2),
            (not f("has_recursion"), 0.1),
        ])
        self._score(scores, GREEDY_INTERVAL, [
            (f("has_sorting"), 0.35),
            (f("has_key_based_sorting"), 0.25),
            (f("has_loop"), 0.25),
            (f("has_interval_access"), 0.15),
        ])
        self._score(scores, BACKTRACKING_PERMUTATION, [
            (f("has_recursion"), 0.35),
            (f("has_list_copy_slice"), 0.25),
            (f("has_recursive_loop"), 0.25),
            (f("has_membership_check"), 0.15),
        ])
        self._score(scores, BACKTRACKING_SUBSET, [
            (f("has_recursion"), 0.35),
            (f("has_list_copy_slice"), 0.25),
            (f("has_backtracking_branch") or f("has_conditional"), 0.2),
            (f("has_recursive_loop"), 0.2),
        ])

        return {pattern: round(min(max(score, 0.0), 1.0), 2) for pattern, score in scores.items()}

    @staticmethod
    def _score(scores, pattern, rules):
        scores[pattern] = sum(weight for passed, weight in rules if passed)


def classify_pattern(features: dict) -> dict:
    classifier = ASTPatternClassifier()
    return classifier.classify(features)
