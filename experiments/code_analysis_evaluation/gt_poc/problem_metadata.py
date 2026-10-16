"""POC problem metadata: the 8 target problems and their CURATED pattern labels.

CURATED PATTERN PROVENANCE
--------------------------
``curated_patterns`` is a **snapshot** of the live ``problems.pattern`` column
(PostgreSQL) as observed at POC build time.  It is the POC's *independent label
source* (spec §9, precedence rule 1: ``editorial`` / ``externally_listed``).
It is snapshotted — not read live — so the pipeline is deterministic and makes
no database call on the default path.

Problem 3236's curated pattern list is genuinely **empty** in the live database.
That is preserved verbatim, not filled in: it is the POC's label-source gap.

Values are NOT adjusted to make any grouping or validation result look better.
"""

POC_VERSION = "1.0.0"

# Frozen vocabulary identifier (spec §13 axis 1). Informational for the POC.
TAXONOMY_VERSION = "v1"

# ---------------------------------------------------------------------------
# PROVISIONAL constants (spec §21 OPEN decisions O1/O2).  Deliberately not
# tuned per problem; recorded in every artifact that depends on them.
# ---------------------------------------------------------------------------
PROVISIONAL_SKELETON_TAU = 0.35        # family split / merge threshold (O1)
PROVISIONAL_TAU_RATIONALE = (
    "Chosen as a single documented constant, not calibrated. Reported as an "
    "OPEN decision; the POC treats it as evidence-gathering input, not a result."
)

DERIVATION_FRACTION = 0.6              # spec §11 60/40 derivation/held-out split

ALLOWED_SOURCE_TYPES = {
    "pathforge_db",     # existing stored PathForge submission (read-only snapshot)
    "authored",         # hand-written reference by the project author
    "user_export",      # user-owned exported submission (not used in this POC run)
    "licensed_repo",    # permissively-licensed public solution (not used here)
}

DISALLOWED_SOURCE_TYPES = {
    "scraped",
    "unknown",
    "editorial_copy",
}

CURATED_PATTERN_SOURCE = "problems.pattern (live PostgreSQL snapshot, read-only)"

PROBLEMS = {
    1: {
        "title": "Two Sum",
        "difficulty": "Easy",
        "curated_patterns": ["hash_map_lookup"],
    },
    21: {
        "title": "Merge Two Sorted Lists",
        "difficulty": "Easy",
        "curated_patterns": ["two_pointers_same"],
    },
    125: {
        "title": "Valid Palindrome",
        "difficulty": "Easy",
        "curated_patterns": ["two_pointers_opposite"],
    },
    209: {
        "title": "Minimum Size Subarray Sum",
        "difficulty": "Medium",
        "curated_patterns": ["prefix_sum", "sliding_window_variable"],
    },
    242: {
        "title": "Valid Anagram",
        "difficulty": "Easy",
        "curated_patterns": ["hash_map_frequency"],
    },
    560: {
        "title": "Subarray Sum Equals K",
        "difficulty": "Medium",
        "curated_patterns": ["hash_map_frequency", "prefix_sum"],
    },
    704: {
        "title": "Binary Search",
        "difficulty": "Easy",
        "curated_patterns": ["binary_search_standard"],
    },
    3236: {
        "title": "Smallest Missing Integer Greater Than Sequential Prefix Sum",
        "difficulty": "Easy",
        "curated_patterns": [],   # genuinely empty in the live DB — preserved
    },
}

# Problems included in the POC, in deterministic order.
POC_PROBLEM_IDS = sorted(PROBLEMS)

TARGET_SOLUTIONS_PER_PROBLEM = 5
TARGET_CORPUS_SIZE = len(POC_PROBLEM_IDS) * TARGET_SOLUTIONS_PER_PROBLEM
