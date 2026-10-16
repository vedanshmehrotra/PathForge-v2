"""gt_poc_v2 — problem metadata, concept tiers, and provisional constants.

CURATED PATTERN PROVENANCE
--------------------------
``curated_patterns`` is a snapshot of the live ``problems.pattern`` column
(PostgreSQL) as observed when the corpus was assembled.  It is the POC's
INDEPENDENT label source (spec V2 §3.3 precedence channel 2).  Snapshotted —
never read live — so the pipeline is deterministic and makes no DB call.

Problems 1/21/125/209/242/560/704/3236 keep the exact same curated patterns as
POC v1 (so before/after is comparable).  Problem 3236's curated list is
genuinely empty in the live DB and is preserved verbatim.

Four problems are added (spec V2 §8.3) to cover strategy families the first POC
did not exercise: a level-order BFS problem (LC 102), a bottom-up DP problem
(LC 70), a backtracking problem (LC 46) and a union-find problem (LC 547).

Nothing here is tuned to make any grouping/validation result look better.
"""

POC_VERSION = "2.0.0"

# Frozen vocabulary identifier (informational; the vocabulary itself is untouched).
TAXONOMY_VERSION = "v1"

# ---------------------------------------------------------------------------
# PROVISIONAL constants (spec V2 §10 OPEN decisions).  Recorded in every
# artifact that depends on them; never tuned per problem.
# ---------------------------------------------------------------------------
# Representative-selection parameter only (V2 §2.2).  It is NOT a grouping
# threshold: skeleton distance can never create a family boundary in V2.
PROVISIONAL_REPRESENTATIVE_TAU = 0.35
PROVISIONAL_TAU_ROLE = (
    "representative-selection / diagnostic only; NOT a family split trigger "
    "(V2 §2). Value is OPEN — see §10 OPEN-1."
)

# §7.2 family-first split: n>=3 -> ceil(0.4*n) held out (keep >=1 derivation);
# n==2 -> 1/1; n==1 -> VALIDATION_LIMITED.
HELD_OUT_FRACTION = 0.4

# §7.4: acceptance criteria may only be judged met when held_out_population
# >= HELD_OUT_POPULATION_MULTIPLIER * problems.
HELD_OUT_POPULATION_MULTIPLIER = 3

# §6.3 rule 4 / per-group minimum.  PROVISIONAL (OPEN-5).
N_MIN_CONTROLS = 5

ALLOWED_SOURCE_TYPES = {
    "pathforge_db",     # existing stored PathForge submission (read-only snapshot)
    "authored",         # hand-written reference by the project author
    "user_export",      # user-owned exported submission (not used in this POC run)
    "licensed_repo",    # permissively-licensed public solution (not used here)
}
DISALLOWED_SOURCE_TYPES = {"scraped", "unknown", "editorial_copy"}

CURATED_PATTERN_SOURCE = "problems.pattern (live PostgreSQL snapshot, read-only)"

# ---------------------------------------------------------------------------
# The 12 POC problems (8 from POC v1 + 4 added)
# ---------------------------------------------------------------------------
PROBLEMS = {
    1: {"title": "Two Sum", "difficulty": "Easy",
        "curated_patterns": ["hash_map_lookup"]},
    21: {"title": "Merge Two Sorted Lists", "difficulty": "Easy",
         "curated_patterns": ["two_pointers_same"]},
    125: {"title": "Valid Palindrome", "difficulty": "Easy",
          "curated_patterns": ["two_pointers_opposite"]},
    209: {"title": "Minimum Size Subarray Sum", "difficulty": "Medium",
          "curated_patterns": ["prefix_sum", "sliding_window_variable"]},
    242: {"title": "Valid Anagram", "difficulty": "Easy",
          "curated_patterns": ["hash_map_frequency"]},
    560: {"title": "Subarray Sum Equals K", "difficulty": "Medium",
          "curated_patterns": ["hash_map_frequency", "prefix_sum"]},
    704: {"title": "Binary Search", "difficulty": "Easy",
          "curated_patterns": ["binary_search_standard"]},
    3236: {"title": "Smallest Missing Integer Greater Than Sequential Prefix Sum",
           "difficulty": "Easy",
           "curated_patterns": []},  # genuinely empty in the live DB — preserved
    102: {"title": "Binary Tree Level Order Traversal", "difficulty": "Medium",
          "curated_patterns": ["bfs_level_order"]},
    70: {"title": "Climbing Stairs", "difficulty": "Easy",
         "curated_patterns": ["dp_1d_forward"]},
    46: {"title": "Permutations", "difficulty": "Medium",
         "curated_patterns": ["backtracking_permutation"]},
    547: {"title": "Number of Provinces", "difficulty": "Medium",
          "curated_patterns": ["union_find"]},
}

POC_PROBLEM_IDS = sorted(PROBLEMS)

TARGET_SOLUTIONS_PER_PROBLEM = 8
TARGET_CORPUS_SIZE = len(POC_PROBLEM_IDS) * TARGET_SOLUTIONS_PER_PROBLEM  # 96

# ---------------------------------------------------------------------------
# S1 — concept tiers (V2 §1.3).  Every frozen technique/strategy id is in
# exactly one tier.  A concept absent from both sets defaults to SUPPORT so
# newly-added vocabulary can never silently fragment families.
# ---------------------------------------------------------------------------

#: All strategies are PEC (a strategy denotes an algorithmic structure).
PEC_STRATEGIES = frozenset({
    "sliding_window",
    "two_pointers_opposite",
    "binary_search",
    "dp_bottom_up",
    "dp_top_down",
    "dfs_backtracking",
    "bfs_shortest_path",
    "union_find",
    "monotonic_stack_strategy",
})

#: Techniques that may partition: V1-documented specificity >= Medium-high plus
#: provisionally ratified PECs (V2 §1.3; ratification itself is OPEN-2).
PEC_TECHNIQUES = frozenset({
    # documented High / Medium-high
    "carry_propagation",
    "iterative_table_filling",
    "bidirectional_index_scan",
    # provisionally ratified (no documented specificity)
    "hash_lookup",
    "frequency_counting",
    "linked_list_traversal",
    "monotonic_stack_maintenance",
    "fixed_window_maintenance",
})

#: SUPPORT-tier: recorded, available to required/optional derivation, but they
#: NEVER create a family boundary.
SUPPORT_TECHNIQUES = frozenset({
    "sequential_accumulation",     # Low
    "loop_state_tracking",         # Medium
    "recursive_branching",         # Medium
    "forward_pointer_advance",
    "candidate_selection",
})

PEC_CONCEPTS = PEC_STRATEGIES | PEC_TECHNIQUES
SUPPORT_CONCEPTS = SUPPORT_TECHNIQUES

#: Provisional PEC ratification list, surfaced for OPEN-2 human ratification.
PROVISIONALLY_RATIFIED_PECS = (
    "hash_lookup", "frequency_counting", "linked_list_traversal",
    "monotonic_stack_maintenance", "fixed_window_maintenance",
)

# ---------------------------------------------------------------------------
# Label modes.
# ---------------------------------------------------------------------------
#: STRICT      — only an APPROVED family label may activate a group (spec §4.5).
#: PROVISIONAL — the environment cannot supply human review, so a §3.4-screened
#:               curated_problem label (or an authored family proposal) is
#:               accepted as provisionally activatable.  This is a recorded
#:               PROVISIONAL assumption (PA1), NOT an approval.
LABEL_MODE_STRICT = "strict_human"
LABEL_MODE_PROVISIONAL = "provisional_unreviewed"
ACTIVATABLE_APPROVAL_STATES = {
    LABEL_MODE_STRICT: {"APPROVED"},
    LABEL_MODE_PROVISIONAL: {"APPROVED", "PENDING_REVIEW"},
}

PROVISIONAL_ASSUMPTION_PA1 = (
    "PA1: the POC runs with label_mode='provisional_unreviewed' because this "
    "environment cannot supply a human reviewer. A family label that passes the "
    "spec V2 §3.4 consistency screen is treated as provisionally activatable. "
    "No label is marked APPROVED; the '>=6 APPROVED labels' acceptance "
    "criterion is reported NOT MET. See §10 OPEN-3 / OPEN-4."
)
