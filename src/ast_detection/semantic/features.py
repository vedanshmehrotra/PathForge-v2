"""Data classes for semantic feature extraction results."""
from dataclasses import dataclass, field


@dataclass
class LoopFeatures:
    """Features describing loop behavior."""
    total_loops: int = 0
    for_loops: int = 0
    while_loops: int = 0
    has_counter_loop: bool = False
    has_for_counter_loop: bool = False
    counter_var: str = ""
    counter_increments: bool = False
    counter_compares_to_len: bool = False
    has_collection_iteration: bool = False
    collection_var: str = ""
    has_enumerate_iteration: bool = False
    has_early_exit: bool = False


@dataclass
class AccessFeatures:
    """Features describing how collections are accessed."""
    has_indexed_access: bool = False
    indexed_collection: str = ""
    index_vars: list = field(default_factory=list)
    has_membership_test: bool = False
    membership_collection: str = ""
    membership_vars: list = field(default_factory=list)
    membership_collection_type: str = ""  # "list", "set", "dict", or "unknown"
    membership_collections: list = field(default_factory=list)  # all collections used in `in` tests
    has_sequential_index: bool = False
    # Dict/set construction tracking
    dict_vars: list = field(default_factory=list)
    set_vars: list = field(default_factory=list)
    # Membership on a dict/set variable
    membership_on_hash_collection: bool = False
    # Dict .get() lookup detected
    has_dict_get_lookup: bool = False


@dataclass
class AccumulationFeatures:
    """Features describing accumulation patterns."""
    has_accumulation: bool = False
    accumulator_var: str = ""
    accumulator_op: str = ""
    accumulator_source: str = ""
    has_running_sum: bool = False
    has_numeric_accumulation: bool = False
    accumulator_is_from_collection: bool = False
    has_append_accumulation: bool = False
    has_assignment_accumulation: bool = False


@dataclass
class PointerFeatures:
    """Features describing pointer/index movement."""
    has_index_movement: bool = False
    movement_var: str = ""
    movement_step: int = 0
    has_bidirectional: bool = False


@dataclass
class PrimaryRoleFeatures:
    """Features that determine whether a pattern is the PRIMARY algorithm
    strategy vs incidental implementation behavior.

    These features answer: "Is this pattern central to the algorithm?"
    rather than just "Is this pattern structurally present?"
    """
    # --- Return value dependency ---
    return_var_names: list = field(default_factory=list)  # variables in return statement
    return_involves_candidate: bool = False  # does return reference candidate state?

    # --- Influence on control flow ---
    candidate_in_main_condition: bool = False  # candidate state used in loop/if condition
    candidate_in_branches: bool = False  # candidate state used in if/elif/else
    candidate_in_comparisons: int = 0  # how many comparisons use candidate state

    # --- Data-flow reach ---
    candidate_vars: list = field(default_factory=list)  # vars that represent the candidate pattern
    candidate_vars_used_outside: bool = False  # are those vars used outside their creation context?
    candidate_vars_terminate_result: bool = False  # do candidate vars flow to the result?

    # --- Competing pattern presence ---
    has_competing_loop_pattern: bool = False  # binary search, sorting, etc.
    has_hash_bookkeeping: bool = False  # visited set, frequency map (incidental)
    has_simple_counter: bool = False  # just counting, not accumulating for a purpose

    # --- Centrality signals ---
    main_loop_candidate_vars: bool = False  # candidate vars used inside the main loop body
    candidate_drives_decision: bool = False  # lookup value or accumulated value determines branching
    result_depends_on_candidate: bool = False  # the final result depends on candidate state

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class SemanticFeatures:
    """Complete semantic feature set for a code snippet."""
    loops: LoopFeatures = field(default_factory=LoopFeatures)
    access: AccessFeatures = field(default_factory=AccessFeatures)
    accumulation: AccumulationFeatures = field(default_factory=AccumulationFeatures)
    pointers: PointerFeatures = field(default_factory=PointerFeatures)
    primary_role: PrimaryRoleFeatures = field(default_factory=PrimaryRoleFeatures)

    def to_dict(self) -> dict:
        """Convert to a flat dictionary for logging/debugging."""
        return {
            "loops": self.loops.__dict__,
            "access": self.access.__dict__,
            "accumulation": self.accumulation.__dict__,
            "pointers": self.pointers.__dict__,
            "primary_role": self.primary_role.__dict__,
        }
