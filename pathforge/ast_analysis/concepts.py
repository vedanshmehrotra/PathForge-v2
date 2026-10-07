"""Concept registry — the single declarative classification of PathForge analysis concepts.

BATCH B1 — DECLARATION ONLY
===========================

This module is a **metadata layer**. It declares, for every existing analysis
concept, what *kind* of concept it is and what it is *allowed to do*.

**Nothing reads this module.** B1 introduces no runtime consumer, no database
table, no service, no configuration system and no external dependency. Adding
this file changes no analysis, matching, persistence, API or UI behaviour. The
guarantee is enforced by ``pathforge/tests/test_concept_registry.py``
(``test_no_runtime_consumer_exists``), which fails if anything outside this
module and its own test starts importing it.

Why this exists
---------------

Before B1 the same concept could be:

* a legacy detector ``pattern_id`` (``src/ast_detection/detectors/``),
* an entry in the curated problem taxonomy
  (``pathforge/ast_engine/patterns.py::ALL_PATTERNS``),
* a shadow technique or strategy
  (``pathforge/ast_analysis/shadow/techniques.py`` / ``strategies.py``),
* a V2 Ground-Truth tier
  (``experiments/code_analysis_evaluation/gt_poc_v2/problem_metadata.py``),
* or a shadow structural fact (``pathforge/ast_analysis/shadow/fact_extractor.py``)

— with no single place saying which of those roles may conclude, may identify a
Ground-Truth family, or may never appear in a family requirement at all. The
consequence is documented in
``experiments/code_analysis_evaluation/ARCHITECTURE_REDESIGN_PROPOSAL.md`` §4.

The three classes
-----------------

``OBSERVATION``
    A deterministic, name-free structural property. Never an algorithmic
    conclusion. ``conclusion_eligible`` is always ``False``. Corresponds to the
    shadow structural facts and to the legacy ``array_traversal`` /
    ``brute_force`` / ``sorting`` detectors.

``TECHNIQUE``
    A reusable *method* composed of observations, recurring across several
    strategies and not implying one. May be *required* by a family (it can be
    **identifying**), but is never the reported algorithmic conclusion.

``STRATEGY``
    An approach-level conclusion. The only class that may be reported as the
    primary approach for a submission.

Tier, rank and eligibility
--------------------------

``tier`` is the existing V2 tier model (``PEC`` / ``SUPPORT``). ``PEC`` means
"may partition a Ground-Truth family"; ``SUPPORT`` means "recorded, usable as
required/optional support, but never creates a family boundary".

``specificity_rank`` is **derived** from class + tier, per the approved design —
it is never hand-assigned:

===========================  ===============
class / tier                 rank
===========================  ===============
``OBSERVATION`` (any tier)   0
``TECHNIQUE`` / ``SUPPORT``  1
``TECHNIQUE`` / ``PEC``      2
``STRATEGY`` (any tier)      3
===========================  ===============

``conclusion_eligible`` is likewise derived: ``class == "STRATEGY"``.

``family_role`` is **declared, not derived**. It states the maximum permitted
participation in a Ground-Truth family requirement:

``IDENTIFYING``
    May be the concept that identifies a family.
``COMPONENT``
    May appear in a family's ``required`` set, but must not identify a family
    alone.
``SUPPORTING``
    May appear only in ``optional``. **Currently unused** — see the audit report;
    no evidence-backed instance exists yet, so the role is declared and reserved
    rather than invented.
``ABSENT-NOT-ALLOWED``
    Must never appear in any family requirement.

Observations are declared ``SUPPORT`` tier because "never partitions a family"
is exactly their guarantee, and because V2's ``concept_tier()`` already defaults
an unregistered id to ``SUPPORT``.

Falsifier policy
----------------

``falsifier`` is optional and records a **known structural condition that
positively establishes the concept's absence**. It is declared for concepts
whose implementation already carries an explicit absence/exclusion condition
(the ``Absence constraint`` blocks in ``strategies.py`` and the memoization
fences in ``techniques.py``), and for legacy patterns whose
``PATTERN_TO_V1_MAPPING`` entry declares ``excluded`` concepts.

Two caveats, recorded deliberately and reviewed in the audit report:

1. Legacy ``excluded`` entries are **presence-triggered** exclusions, not yet
   structural falsifiers (see proposal §9 rules K1/K3). They are transcribed
   verbatim so the registry does not overstate them.
2. **Nothing reads ``falsifier`` in B1.** It is traceability metadata.

Source vocabularies
-------------------

Every concept records the vocabularies that reference it. Shared spellings are
registered **once**, with all their sources, and are never renamed in this
batch.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ============================================================================
# Vocabulary — classes, tiers, family roles
# ============================================================================

OBSERVATION = "OBSERVATION"
TECHNIQUE = "TECHNIQUE"
STRATEGY = "STRATEGY"

CONCEPT_CLASSES: Tuple[str, ...] = (OBSERVATION, TECHNIQUE, STRATEGY)

PEC = "PEC"
SUPPORT = "SUPPORT"

CONCEPT_TIERS: Tuple[str, ...] = (PEC, SUPPORT)

IDENTIFYING = "IDENTIFYING"
COMPONENT = "COMPONENT"
SUPPORTING = "SUPPORTING"
ABSENT_NOT_ALLOWED = "ABSENT-NOT-ALLOWED"

FAMILY_ROLES: Tuple[str, ...] = (
    IDENTIFYING,
    COMPONENT,
    SUPPORTING,
    ABSENT_NOT_ALLOWED,
)

#: Derived specificity rank. See the module docstring — this is the ONLY place
#: the approved rank scheme is encoded.
RANK_BY_CLASS_TIER: Dict[Tuple[str, str], int] = {
    (OBSERVATION, PEC): 0,
    (OBSERVATION, SUPPORT): 0,
    (TECHNIQUE, SUPPORT): 1,
    (TECHNIQUE, PEC): 2,
    (STRATEGY, PEC): 3,
    (STRATEGY, SUPPORT): 3,
}

#: The only class whose concepts may be reported as a submission's primary
#: approach.
CONCLUSION_ELIGIBLE_CLASS = STRATEGY


def derive_specificity_rank(concept_class: str, tier: str) -> int:
    """Return the declared specificity rank for a class + tier pair.

    Raises ``ValueError`` for an unknown pair so an invalid declaration fails
    loudly instead of silently defaulting.
    """
    try:
        return RANK_BY_CLASS_TIER[(concept_class, tier)]
    except KeyError:
        raise ValueError(
            f"no specificity rank for class={concept_class!r} tier={tier!r}"
        ) from None


def derive_conclusion_eligible(concept_class: str) -> bool:
    """Return whether a concept of this class may be a final conclusion."""
    if concept_class not in CONCEPT_CLASSES:
        raise ValueError(f"unknown concept class: {concept_class!r}")
    return concept_class == CONCLUSION_ELIGIBLE_CLASS


# ============================================================================
# Source-vocabulary markers
# ============================================================================

#: Registered in the runtime detector registry
#: (``src/ast_detection/detectors/``).
SRC_LEGACY_DETECTOR = "legacy_detector"

#: Present in the curated problem taxonomy
#: (``pathforge/ast_engine/patterns.py::ALL_PATTERNS``).
SRC_CURATED_TAXONOMY = "curated_taxonomy"

#: Emitted as a structural fact by
#: ``pathforge/ast_analysis/shadow/fact_extractor.py``.
SRC_STRUCTURAL_FACT = "structural_fact"

#: Implemented shadow technique (``shadow/techniques.py``).
SRC_V1_TECHNIQUE = "v1_technique"

#: Implemented shadow strategy (``shadow/strategies.py``).
SRC_V1_STRATEGY = "v1_strategy"

#: Declared PEC strategy by the V2 Ground-Truth POC
#: (``gt_poc_v2/problem_metadata.py``).
SRC_V2_PEC_STRATEGY = "v2_pec_strategy"

#: Declared PEC technique by the V2 POC.
SRC_V2_PEC_TECHNIQUE = "v2_pec_technique"

#: Declared SUPPORT technique by the V2 POC.
SRC_V2_SUPPORT_TECHNIQUE = "v2_support_technique"

#: Documented in ``PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md`` but with no
#: runtime implementation and no emitted artifact.
SRC_DOCUMENTED_ONLY = "documented_only"

#: Every recognised source marker.
CONCEPT_SOURCES: Tuple[str, ...] = (
    SRC_LEGACY_DETECTOR,
    SRC_CURATED_TAXONOMY,
    SRC_STRUCTURAL_FACT,
    SRC_V1_TECHNIQUE,
    SRC_V1_STRATEGY,
    SRC_V2_PEC_STRATEGY,
    SRC_V2_PEC_TECHNIQUE,
    SRC_V2_SUPPORT_TECHNIQUE,
    SRC_DOCUMENTED_ONLY,
)


# ============================================================================
# The concept record
# ============================================================================

@dataclass(frozen=True)
class Concept:
    """One declared analysis concept.

    ``specificity_rank`` and ``conclusion_eligible`` are always derived from
    ``concept_class`` / ``tier`` by :func:`_concept`; they are stored so the
    registry is directly inspectable, and re-derived by the test suite so a
    hand-edited value is caught.
    """

    concept_id: str
    concept_class: str
    tier: str
    specificity_rank: int
    conclusion_eligible: bool
    family_role: str
    sources: Tuple[str, ...] = ()
    v1_image: Optional[str] = None
    falsifier: Optional[str] = None
    rationale: str = ""


def _concept(
    concept_id: str,
    concept_class: str,
    tier: str,
    family_role: str,
    sources: Tuple[str, ...],
    v1_image: Optional[str] = None,
    falsifier: Optional[str] = None,
    rationale: str = "",
) -> Concept:
    """Build a validated :class:`Concept`, deriving rank and eligibility."""
    if not concept_id or not isinstance(concept_id, str):
        raise ValueError(f"concept_id must be a non-empty string: {concept_id!r}")
    if concept_class not in CONCEPT_CLASSES:
        raise ValueError(f"{concept_id}: invalid class {concept_class!r}")
    if tier not in CONCEPT_TIERS:
        raise ValueError(f"{concept_id}: invalid tier {tier!r}")
    if family_role not in FAMILY_ROLES:
        raise ValueError(f"{concept_id}: invalid family_role {family_role!r}")
    for source in sources:
        if source not in CONCEPT_SOURCES:
            raise ValueError(f"{concept_id}: invalid source {source!r}")
    return Concept(
        concept_id=concept_id,
        concept_class=concept_class,
        tier=tier,
        specificity_rank=derive_specificity_rank(concept_class, tier),
        conclusion_eligible=derive_conclusion_eligible(concept_class),
        family_role=family_role,
        sources=tuple(sources),
        v1_image=v1_image,
        falsifier=falsifier,
        rationale=rationale,
    )


def _observation(
    concept_id: str,
    sources: Tuple[str, ...],
    rationale: str = "",
) -> Concept:
    """Declare an observation: rank 0, never a conclusion, never a requirement."""
    return _concept(
        concept_id,
        OBSERVATION,
        SUPPORT,
        ABSENT_NOT_ALLOWED,
        sources,
        rationale=rationale,
    )


# ============================================================================
# Group 1 — legacy detector patterns in the curated taxonomy (30)
# ============================================================================
# Classified from each pattern's V1 image in ``PATTERN_TO_V1_MAPPING``: a
# strategy image makes the pattern strategy-class; a technique image makes it
# technique-class with that technique's V2 tier. ``falsifier`` transcribes the
# mapping's own ``excluded`` list (presence-triggered, see module docstring).

_LEGACY_STRATEGY = (
    # -- sliding window ------------------------------------------------------
    _concept(
        "sliding_window_fixed", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="sliding_window",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    _concept(
        "sliding_window_variable", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="sliding_window",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    # -- graphs & trees ------------------------------------------------------
    _concept(
        "bfs_level_order", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="bfs_shortest_path",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "binary_search_tree", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="binary_search",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    # -- dynamic programming (all seven map to dp_bottom_up) -----------------
    _concept(
        "dp_1d_forward", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_1d_sequence", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_2d_grid", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_2d_string", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_knapsack", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_interval", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    _concept(
        "dp_state_machine", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dp_bottom_up",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
    ),
    # -- binary search -------------------------------------------------------
    _concept(
        "binary_search_standard", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="binary_search",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    _concept(
        "binary_search_rotated", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="binary_search",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    _concept(
        "binary_search_answer", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="binary_search",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    # -- backtracking --------------------------------------------------------
    _concept(
        "backtracking_permutation", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dfs_backtracking",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): dp_top_down",
    ),
    _concept(
        "backtracking_subset", STRATEGY, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="dfs_backtracking",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): dp_top_down",
    ),
    # -- linked lists & stack ------------------------------------------------
    # (monotonic_stack / monotonic_deque are technique-class; see group 2)
    # -- two pointers (opposite) and union_find are shared ids; see group 3 ---
)

_LEGACY_TECHNIQUE_PEC = (
    _concept(
        "hash_map_lookup", TECHNIQUE, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="hash_lookup",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
        rationale=(
            "V1 image hash_lookup activated a V2 group as its complete required "
            "set (lc1_fam1), so it may identify a family."
        ),
    ),
    _concept(
        "hash_map_frequency", TECHNIQUE, PEC, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="frequency_counting",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): recursive_branching",
        rationale=(
            "V1 image frequency_counting activated V2 groups as its complete "
            "required set (lc242_fam1, lc242_fam3)."
        ),
    ),
    _concept(
        "linked_list_reversal", TECHNIQUE, PEC, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="linked_list_traversal",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    _concept(
        "monotonic_stack", TECHNIQUE, PEC, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="monotonic_stack_maintenance",
    ),
    _concept(
        "monotonic_deque", TECHNIQUE, PEC, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="monotonic_stack_maintenance",
    ),
)

_LEGACY_TECHNIQUE_SUPPORT = (
    _concept(
        "prefix_sum", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="sequential_accumulation",
        rationale=(
            "V1 image is a SUPPORT technique, which cannot identify a family "
            "(V2 refused all six SUPPORT-only labels). Flagged: prefix_sum is a "
            "first-class curated pattern yet cannot be a final conclusion under "
            "the declared class model."
        ),
    ),
    _concept(
        "two_pointers_same", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="forward_pointer_advance",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): two_pointers_opposite",
    ),
    _concept(
        "dfs_recursive", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="recursive_branching",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): bfs_shortest_path",
        rationale=(
            "Maps to the broad recursion evidence concept recursive_branching; "
            "the specific recursive strategies are not modelled yet (proposal "
            "§14)."
        ),
    ),
    _concept(
        "fast_slow_pointers", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="forward_pointer_advance",
    ),
    _concept(
        "greedy_local", TECHNIQUE, SUPPORT, IDENTIFYING,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        v1_image="candidate_selection",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): sliding_window",
        rationale=(
            "Identifying but NOT conclusion-eligible. It is the sole required "
            "concept of the greedy legacy family (candidate_selection), so it "
            "may identify that family, but a technique must never be reported as "
            "the final algorithmic conclusion. This is the architectural cause of "
            "the observed greedy_local / array_traversal mismatch (proposal §6.1)."
        ),
    ),
)

#: Legacy patterns whose ``PATTERN_TO_V1_MAPPING`` entry has an empty
#: ``required`` list — the four entries in ``MISSING_VOCABULARY_PATTERNS``.
#: Classified TECHNIQUE because the mapping note for each describes the missing
#: image as a *technique* ("no direct V1 technique equivalent"), and because the
#: V1 model deliberately has no greedy/DFS-iterative approach of its own.
_LEGACY_TECHNIQUE_UNMAPPED = (
    _concept(
        "dfs_iterative", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        rationale=(
            "MISSING_VOCABULARY_PATTERNS: mapping note is 'Iterative DFS has no "
            "direct V1 technique equivalent'. Ambiguous (approach-like name, "
            "technique-like V1 description) — flagged for review."
        ),
    ),
    _concept(
        "topological_sort", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        rationale=(
            "MISSING_VOCABULARY_PATTERNS: mapping note is 'No direct V1 "
            "technique; uses BFS-like traversal'. Ambiguous — flagged."
        ),
    ),
    _concept(
        "heap_top_k", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        rationale=(
            "MISSING_VOCABULARY_PATTERNS: mapping note is 'No direct V1 "
            "technique for heap operations'; the detector matches heapq "
            "container operations, not an algorithmic strategy. Flagged."
        ),
    ),
    _concept(
        "greedy_interval", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY),
        rationale=(
            "MISSING_VOCABULARY_PATTERNS: mapping note is 'No direct V1 "
            "technique for interval greedy'. Consistent with greedy_local, whose "
            "V1 image is also technique-class. Flagged."
        ),
    ),
)

# ============================================================================
# Group 2 — shared spellings: legacy pattern id AND V1 strategy id (3)
# ============================================================================
# These three strings exist in BOTH the legacy detector taxonomy and the V1
# strategy vocabulary with identical spelling. Registered ONCE as the strategy
# they denote, with both sources recorded. No rename.

_SHARED_LEGACY_AND_V1_STRATEGY = (
    _concept(
        "two_pointers_opposite", STRATEGY, PEC, IDENTIFYING,
        (
            SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY,
            SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY,
        ),
        v1_image="two_pointers_opposite",
        falsifier="declared exclusion (PATTERN_TO_V1_MAPPING): binary_search",
    ),
    _concept(
        "bfs_shortest_path", STRATEGY, PEC, IDENTIFYING,
        (
            SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY,
            SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY,
        ),
        v1_image="bfs_shortest_path",
        falsifier="recursive_branching evidence present (evaluator absence constraint)",
    ),
    _concept(
        "union_find", STRATEGY, PEC, IDENTIFYING,
        (
            SRC_LEGACY_DETECTOR, SRC_CURATED_TAXONOMY,
            SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY,
        ),
        v1_image="union_find",
    ),
)

# ============================================================================
# Group 3 — legacy detectors outside the curated taxonomy (3)
# ============================================================================
# The only three registered detectors whose ``pattern_id`` is absent from
# ``ALL_PATTERNS``: they can be detected and displayed but can never be an
# expected ground-truth pattern. Declared OBSERVATION per the approved audit.

_LEGACY_NON_TAXONOMY_OBSERVATIONS = (
    _observation(
        "array_traversal",
        (SRC_LEGACY_DETECTOR,),
        rationale=(
            "Structural observation, not an approach. Not in ALL_PATTERNS, so it "
            "can never be an expected pattern, yet it can currently become the "
            "primary detected pattern. Measured precision 0.24-0.30 with 106-183 "
            "false positives and a 62% fire rate in "
            "reports and docs/SEMANTIC_EXPERIMENT_2A/2B/3A/3B/3C. Proposal §6.2 "
            "recommends demotion; B1 only classifies."
        ),
    ),
    _observation(
        "brute_force",
        (SRC_LEGACY_DETECTOR,),
        rationale=(
            "Exists as a runtime detector (src/ast_detection/detectors/"
            "brute_force.py) but is not a taxonomy pattern and not V2 vocabulary. "
            "'nested loops' has a measured 66.7% false-positive exposure on the "
            "V2 corpus (8 of 12 nested-loop families are legitimate specific "
            "approaches). Not a conclusion; not a Ground-Truth activation concept. "
            "Detector is NOT modified."
        ),
    ),
    _observation(
        "sorting",
        (SRC_LEGACY_DETECTOR,),
        rationale=(
            "Structurally 'a sort happens', present inside many distinct "
            "approaches (proposal §8.1). Not in ALL_PATTERNS. Treated as "
            "structural evidence; no taxonomy evidence found to the contrary."
        ),
    ),
)

# ============================================================================
# Group 4 — V1 shadow techniques (13)
# ============================================================================
# Tier is the existing V2 tier model. ``carry_propagation`` is BOTH an emitted
# structural fact and a technique id — the same string in two roles; registered
# once, with both sources, and flagged in the audit report.

_TECHNIQUES = (
    _concept(
        "sequential_accumulation", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_SUPPORT_TECHNIQUE),
        rationale=(
            "V2 SUPPORT tier: refused a family on its own (all six SUPPORT-only "
            "labels were refused by the specificity floor)."
        ),
    ),
    _concept(
        "bidirectional_index_scan", TECHNIQUE, PEC, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        rationale="PEC technique; never appeared as a family's own required set.",
    ),
    _concept(
        "carry_propagation", TECHNIQUE, PEC, COMPONENT,
        (SRC_STRUCTURAL_FACT, SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        rationale=(
            "DUAL ROLE / IDENTIFIER COLLISION: the same string is (a) a "
            "structural fact emitted by fact_extractor and (b) the T5 technique "
            "id. Registered once as the technique because that is the stronger "
            "role; the fact role is recorded via SRC_STRUCTURAL_FACT. Flagged "
            "for review — see CONCEPT_REGISTRY_AUDIT.md."
        ),
    ),
    _concept(
        "recursive_branching", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_SUPPORT_TECHNIQUE),
        rationale=(
            "Broad recursion EVIDENCE, not a strategy. It currently absorbs five "
            "structurally distinguishable recursive strategies (merge, DFS by "
            "depth, recursive two-pointer, DFS traversal, recursive binary "
            "search) across five problems in the V2 corpus. Remains supporting "
            "evidence; no recursive-strategy refinement is implemented in B1 "
            "(proposal §14)."
        ),
    ),
    _concept(
        "loop_state_tracking", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_SUPPORT_TECHNIQUE),
    ),
    _concept(
        "iterative_table_filling", TECHNIQUE, PEC, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
    ),
    _concept(
        "linked_list_traversal", TECHNIQUE, PEC, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
    ),
    _concept(
        "fixed_window_maintenance", TECHNIQUE, PEC, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        rationale=(
            "Provisionally ratified PEC (V2 OPEN-2). Tier itself is not ratified "
            "by a human."
        ),
    ),
    _concept(
        "monotonic_stack_maintenance", TECHNIQUE, PEC, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        rationale="Provisionally ratified PEC (V2 OPEN-2).",
    ),
    _concept(
        "forward_pointer_advance", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_V1_TECHNIQUE, SRC_V2_SUPPORT_TECHNIQUE),
        falsifier=(
            "genuine opposite-direction scan (compared variables are a subset of "
            "modified variables), or parent_pointer_chase present"
        ),
    ),
    _concept(
        "candidate_selection", TECHNIQUE, SUPPORT, IDENTIFYING,
        (SRC_V1_TECHNIQUE, SRC_V2_SUPPORT_TECHNIQUE),
        rationale=(
            "IDENTIFYING but NOT conclusion-eligible. It is the V1 image of the "
            "greedy-local family, so it may identify that family, but it must not "
            "be promoted to a strategy merely because it identifies one."
        ),
    ),
    _concept(
        "hash_lookup", TECHNIQUE, PEC, IDENTIFYING,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        falsifier="recursive_branching evidence present (mapping is a recursion memo)",
        rationale=(
            "Activated a V2 group as its complete required set (lc1_fam1), so it "
            "may identify a family. Provisionally ratified PEC (V2 OPEN-2)."
        ),
    ),
    _concept(
        "frequency_counting", TECHNIQUE, PEC, IDENTIFYING,
        (SRC_V1_TECHNIQUE, SRC_V2_PEC_TECHNIQUE),
        falsifier="recursive_branching evidence present (mapping is a recursion memo)",
        rationale=(
            "Activated V2 groups as its complete required set (lc242_fam1, "
            "lc242_fam3). Provisionally ratified PEC (V2 OPEN-2)."
        ),
    ),
)

# ============================================================================
# Group 5 — V1 shadow strategies other than the three shared ids (6)
# ============================================================================

_STRATEGIES = (
    _concept(
        "binary_search", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
        falsifier="opposite_direction_updates present (evaluator absence constraint)",
    ),
    _concept(
        "sliding_window", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
        falsifier=(
            "midpoint_calculation present, or a genuine opposite-direction scan, "
            "or the monotonic-stack fact triad "
            "(stack_operation + monotonic_comparison + conditional_pop) present"
        ),
    ),
    _concept(
        "dfs_backtracking", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
        falsifier="cache_lookup or cache_write present (evaluator absence constraint)",
    ),
    _concept(
        "dp_top_down", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
        falsifier="state_restoration present (evaluator absence constraint)",
    ),
    _concept(
        "dp_bottom_up", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
        falsifier="recursive_branching evidence present (evaluator absence constraint)",
    ),
    _concept(
        "monotonic_stack_strategy", STRATEGY, PEC, IDENTIFYING,
        (SRC_V1_STRATEGY, SRC_V2_PEC_STRATEGY),
    ),
)

# ============================================================================
# Group 6 — documented-only concepts (2)
# ============================================================================
# Declared in PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md with no runtime
# implementation and no emitted artifact. Registered so the documented
# vocabulary and the implemented vocabulary cannot silently diverge.

_DOCUMENTED_ONLY = (
    _concept(
        "boundary_narrowing", TECHNIQUE, SUPPORT, COMPONENT,
        (SRC_DOCUMENTED_ONLY,),
        rationale=(
            "Documented as technique T2 in PATHFORGE_TECHNIQUE_STRATEGY_"
            "VOCABULARY_V1.md but NOT implemented: techniques.py has no detector "
            "for it, and _evaluate_binary_search substitutes raw structural facts "
            "('boundary_narrowing is not a technique yet (Phase 1 limitation)'). "
            "Registered so the documentation/implementation gap is explicit. It is "
            "absent from VALID_TECHNIQUES, so it is not a live concept."
        ),
    ),
    _concept(
        "loop_shape", OBSERVATION, SUPPORT, ABSENT_NOT_ALLOWED,
        (SRC_DOCUMENTED_ONLY,),
        rationale=(
            "Documented as a structural fact in the vocabulary (§2.1) but never "
            "emitted as a fact_type. The implemented equivalents are "
            "for_loop_iteration / while_loop_comparison / while_loop_truthiness. "
            "The same name is also one of the five V2 grouping-profile dimensions "
            "(gt_poc_v2/core.py), which is a different concept — do not conflate."
        ),
    ),
)

# ============================================================================
# Group 7 — shadow structural fact types (39)
# ============================================================================
# Every fact_type emitted by fact_extractor.py, minus carry_propagation (group
# 4, because it is also a technique id). These are the raw structural signals:
# class OBSERVATION, rank 0, never a family requirement.

_STRUCTURAL_FACT_IDS: Tuple[str, ...] = (
    "accumulator_update",
    "cache_lookup",
    "cache_write",
    "conditional_index_update",
    "conditional_pop",
    "early_termination",
    "extremum_access",
    "for_loop_iteration",
    "index_lookback",
    "indexed_write",
    "linked_attribute_access",
    "linked_structure_traversal",
    "list_construction",
    "mapping_construction",
    "membership_test",
    "midpoint_calculation",
    "monotonic_comparison",
    "multiple_pointer_traversal",
    "multiple_recursive_paths",
    "neighbor_traversal",
    "node_constructor",
    "opposite_direction_updates",
    "parent_pointer_chase",
    "parent_root_merge",
    "pointer_rewiring",
    "queue_dequeue",
    "recursive_call_in_conditional",
    "recursive_depth_tracking",
    "self_recursive_call",
    "sorting_operation",
    "stack_operation",
    "state_restoration",
    "subscript_index_access",
    "subscript_read",
    "variable_use_in_loop_body",
    "visited_tracking",
    "while_loop_comparison",
    "while_loop_truthiness",
    "window_size_constant",
)

_STRUCTURAL_FACTS: Tuple[Concept, ...] = tuple(
    _observation(fact_id, (SRC_STRUCTURAL_FACT,)) for fact_id in _STRUCTURAL_FACT_IDS
)

# ============================================================================
# The registry
# ============================================================================

_DECLARATIONS: Tuple[Concept, ...] = (
    _LEGACY_STRATEGY
    + _LEGACY_TECHNIQUE_PEC
    + _LEGACY_TECHNIQUE_SUPPORT
    + _LEGACY_TECHNIQUE_UNMAPPED
    + _SHARED_LEGACY_AND_V1_STRATEGY
    + _LEGACY_NON_TAXONOMY_OBSERVATIONS
    + _TECHNIQUES
    + _STRATEGIES
    + _DOCUMENTED_ONLY
    + _STRUCTURAL_FACTS
)


def _build_registry(declarations: Tuple[Concept, ...]) -> Dict[str, Concept]:
    """Index declarations by concept_id, refusing silent duplicates."""
    registry: Dict[str, Concept] = {}
    for concept in declarations:
        if concept.concept_id in registry:
            raise ValueError(
                f"duplicate concept registration: {concept.concept_id!r}"
            )
        registry[concept.concept_id] = concept
    return registry


#: ``concept_id -> Concept``. The single source of truth.
CONCEPTS: Dict[str, Concept] = _build_registry(_DECLARATIONS)


# -- accessors ---------------------------------------------------------------

def all_concepts() -> Tuple[Concept, ...]:
    """Every registered concept, in declaration order."""
    return _DECLARATIONS


def get_concept(concept_id: str) -> Concept:
    """Return one concept. Raises ``KeyError`` for an unregistered id."""
    return CONCEPTS[concept_id]


def registry_ids() -> frozenset:
    """The set of every registered concept id."""
    return frozenset(CONCEPTS)


def has_concept(concept_id: str) -> bool:
    """Whether a concept id is registered."""
    return concept_id in CONCEPTS


def concepts_by_class(concept_class: str) -> Tuple[Concept, ...]:
    """All concepts of one class (``OBSERVATION`` / ``TECHNIQUE`` / ``STRATEGY``)."""
    if concept_class not in CONCEPT_CLASSES:
        raise ValueError(f"unknown concept class: {concept_class!r}")
    return tuple(c for c in all_concepts() if c.concept_class == concept_class)


def concepts_by_tier(tier: str) -> Tuple[Concept, ...]:
    """All concepts of one tier (``PEC`` / ``SUPPORT``)."""
    if tier not in CONCEPT_TIERS:
        raise ValueError(f"unknown tier: {tier!r}")
    return tuple(c for c in all_concepts() if c.tier == tier)


def concepts_by_family_role(family_role: str) -> Tuple[Concept, ...]:
    """All concepts carrying one family role."""
    if family_role not in FAMILY_ROLES:
        raise ValueError(f"unknown family role: {family_role!r}")
    return tuple(c for c in all_concepts() if c.family_role == family_role)


def concepts_by_source(source: str) -> Tuple[Concept, ...]:
    """All concepts referenced by one source vocabulary."""
    if source not in CONCEPT_SOURCES:
        raise ValueError(f"unknown source: {source!r}")
    return tuple(c for c in all_concepts() if source in c.sources)


def conclusion_eligible_ids() -> frozenset:
    """Every concept that may be reported as a submission's primary approach."""
    return frozenset(c.concept_id for c in all_concepts() if c.conclusion_eligible)


def falsifier_ids() -> frozenset:
    """Every concept carrying a declared falsifier (traceability only in B1)."""
    return frozenset(c.concept_id for c in all_concepts() if c.falsifier)


def v1_image_ids() -> frozenset:
    """Every concept that declares a V1 image."""
    return frozenset(c.concept_id for c in all_concepts() if c.v1_image)


def registry_stats() -> Dict[str, object]:
    """Summary counts for the B1 audit report and reviewer inspection."""
    concepts = all_concepts()

    def _tally(values) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items()))

    multi_source = [c for c in concepts if len(c.sources) > 1]
    return {
        "total": len(concepts),
        "by_class": _tally(c.concept_class for c in concepts),
        "by_tier": _tally(c.tier for c in concepts),
        "by_specificity_rank": _tally(c.specificity_rank for c in concepts),
        "by_family_role": _tally(c.family_role for c in concepts),
        "by_source": {
            source: len(concepts_by_source(source))
            for source in CONCEPT_SOURCES
            if concepts_by_source(source)
        },
        "conclusion_eligible": len(conclusion_eligible_ids()),
        "with_falsifier": len(falsifier_ids()),
        "with_v1_image": len(v1_image_ids()),
        "multi_source_concepts": {
            c.concept_id: list(c.sources) for c in multi_source
        },
    }


def registry_as_dicts() -> List[Dict[str, object]]:
    """Plain-dict projection of the registry, for machine-readable dumps."""
    return [
        {
            "concept_id": c.concept_id,
            "class": c.concept_class,
            "tier": c.tier,
            "specificity_rank": c.specificity_rank,
            "conclusion_eligible": c.conclusion_eligible,
            "family_role": c.family_role,
            "falsifier": c.falsifier,
            "sources": list(c.sources),
            "v1_image": c.v1_image,
            "rationale": c.rationale,
        }
        for c in all_concepts()
    ]


__all__ = [
    # vocabulary
    "OBSERVATION", "TECHNIQUE", "STRATEGY",
    "CONCEPT_CLASSES",
    "PEC", "SUPPORT", "CONCEPT_TIERS",
    "IDENTIFYING", "COMPONENT", "SUPPORTING", "ABSENT_NOT_ALLOWED",
    "FAMILY_ROLES",
    "RANK_BY_CLASS_TIER", "CONCLUSION_ELIGIBLE_CLASS",
    # sources
    "SRC_LEGACY_DETECTOR", "SRC_CURATED_TAXONOMY", "SRC_STRUCTURAL_FACT",
    "SRC_V1_TECHNIQUE", "SRC_V1_STRATEGY", "SRC_V2_PEC_STRATEGY",
    "SRC_V2_PEC_TECHNIQUE", "SRC_V2_SUPPORT_TECHNIQUE", "SRC_DOCUMENTED_ONLY",
    "CONCEPT_SOURCES",
    # record + derivation
    "Concept",
    "derive_specificity_rank", "derive_conclusion_eligible",
    # registry
    "CONCEPTS",
    "all_concepts", "get_concept", "has_concept", "registry_ids",
    "concepts_by_class", "concepts_by_tier", "concepts_by_family_role",
    "concepts_by_source",
    "conclusion_eligible_ids", "falsifier_ids", "v1_image_ids",
    "registry_stats", "registry_as_dicts",
]
