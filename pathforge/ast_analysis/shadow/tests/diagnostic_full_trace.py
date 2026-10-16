"""Full execution trace diagnostic.

Traces the EXACT path from _load_ground_truth → shadow runner → matcher
for Add Two Numbers and Problem 3236.

Tests with BOTH the existing DB data AND synthetic groups to isolate the issue.
"""
import ast
import json
import sys
sys.path.insert(0, '.')

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups, _evaluate_single_group
from pathforge.ast_analysis.shadow.data_structures import MatchOutcome


def trace_case(label, code, solution_groups):
    """Full trace for a single case."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")

    # Step 1: Facts
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    fact_types = {f.fact_type for f in facts}
    print(f"\n  [1] Structural facts: {len(facts)} total")
    for ft in sorted(fact_types):
        count = sum(1 for f in facts if f.fact_type == ft)
        print(f"       {ft}: {count}")

    # Step 2: Techniques
    techs = detect_techniques(facts)
    tech_ids = {t.technique_id for t in techs}
    print(f"\n  [2] Techniques detected: {len(techs)}")
    for t in techs:
        print(f"       {t.technique_id} (conf={t.presence_confidence}, cen={t.centrality})")

    # Step 3: Strategies
    strats = evaluate_strategies(techs, facts)
    strat_ids = {s.strategy_id for s in strats}
    print(f"\n  [3] Strategies detected: {len(strats)}")
    for s in strats:
        print(f"       {s.strategy_id} (conf={s.confidence})")

    # Step 4: Solution groups
    print(f"\n  [4] Solution groups: {len(solution_groups) if solution_groups else 0}")
    if not solution_groups:
        print(f"       (NO GROUPS — shadow matcher will produce UNRESOLVED)")

    # Step 5: Matching
    det_techs = {t.technique_id: t for t in techs}
    det_strats = {s.strategy_id: s for s in strats}

    if solution_groups:
        for g in solution_groups:
            group_id = g.get("id", "?")
            required = g.get("required", [])
            optional = g.get("optional", [])
            excluded = g.get("excluded", [])
            authority = g.get("authority_tier", "?")
            print(f"\n  [5] Group '{group_id}':")
            print(f"       required  = {required}")
            print(f"       optional  = {optional}")
            print(f"       excluded  = {excluded}")
            print(f"       authority = {authority}")

            result = _evaluate_single_group(g, det_techs, det_strats)
            print(f"       OUTCOME   = {result['outcome']}")
            print(f"       SATISFAC. = {result['satisfaction']:.3f}")

            for req in required:
                in_t = req in det_techs
                in_s = req in det_strats
                conf = None
                if in_t:
                    conf = det_techs[req].presence_confidence
                elif in_s:
                    conf = det_strats[req].confidence
                print(f"       req '{req}': in_tech={in_t}, in_strat={in_s}, conf={conf}")

        # Full evaluation
        outcome = evaluate_solution_groups(solution_groups, techs, strats, facts)
        print(f"\n  [6] FINAL OUTCOME: {outcome.outcome}")
        print(f"       authority: {outcome.authority_tier}")
        print(f"       primary_strategy: {outcome.primary_strategy}")
        print(f"       satisfied_group_ids: {outcome.satisfied_group_ids}")
        for r in outcome.reasoning:
            print(f"       reasoning: {r}")
    else:
        outcome = MatchOutcome(
            outcome="UNRESOLVED",
            authority_tier="unknown",
            technique_evidence=techs,
            strategy_evidence=strats,
            structural_facts=facts,
            reasoning=["No solution groups provided"],
        )
        print(f"  [6] FINAL OUTCOME: {outcome.outcome}")
        print(f"       (No groups to match against)")

    return outcome


# ============================================================
# Case 1: Add Two Numbers
# ============================================================
ADD_TWO_NUMBERS = """
class Solution:
    def addTwoNumbers(self, l1, l2):
        dummy = ListNode()
        curr = dummy
        carry = 0

        while l1 or l2 or carry:
            val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
            carry, digit = divmod(val, 10)
            curr.next = ListNode(digit)
            curr = curr.next
            l1 = l1.next if l1 else None
            l2 = l2.next if l2 else None

        return dummy.next
"""

# What the ground truth builder would produce for "carry_propagation" pattern:
# mapping: carry_propagation → required=["carry_propagation"], optional=["linked_list_traversal"]
GROUP_CARRY = {
    "id": "group_0",
    "required": ["carry_propagation"],
    "optional": ["linked_list_traversal"],
    "excluded": ["binary_search"],
    "threshold": 0.5,
    "authority_tier": "llm_proposed",
    "patterns": ["carry_propagation"],
}

# What if the LLM proposes linked_list_reversal?
# mapping: linked_list_reversal → required=["linked_list_traversal"]
GROUP_LINKED_REVERSAL = {
    "id": "group_0",
    "required": ["linked_list_traversal"],
    "optional": ["pointer_rewiring", "multiple_pointer_traversal"],
    "excluded": ["two_pointers_opposite"],
    "threshold": 0.5,
    "authority_tier": "llm_proposed",
    "patterns": ["linked_list_reversal"],
}

# The split_groups result if both patterns proposed
# carry_propagation → group with required=["carry_propagation"]
# linked_list_reversal → group with required=["linked_list_traversal"]

# ============================================================
# Case 2: Problem 3236 (prefix_sum style)
# ============================================================
PROBLEM_3236 = """
class Solution:
    def minZeroArray(self, nums, queries):
        n = len(nums)
        diff = [0] * (n + 1)
        for l, r, val in queries:
            diff[l] += val
            if r + 1 <= n:
                diff[r + 1] -= val
        running = 0
        k = 0
        for i in range(n):
            running += diff[i]
            while k < len(queries) and running > 0:
                l, r, val = queries[k]
                if i < l or i > r:
                    diff[i] -= val
                    running -= val
                k += 1
            if running > 0:
                return -1
        return k
"""

GROUP_PREFIX_SUM = {
    "id": "group_0",
    "required": ["sequential_accumulation"],
    "optional": ["iterative_table_filling"],
    "excluded": [],
    "threshold": 0.5,
    "authority_tier": "llm_proposed",
    "patterns": ["prefix_sum"],
}

# ============================================================
# Run traces
# ============================================================
print("=" * 70)
print("DIAGNOSTIC TRACE: What happens at each pipeline step")
print("=" * 70)

# Add Two Numbers — with carry_propagation group
trace_case(
    "CASE 1A: Add Two Numbers + carry_propagation group",
    ADD_TWO_NUMBERS,
    [GROUP_CARRY],
)

# Add Two Numbers — with linked_list_reversal group (wrong group)
trace_case(
    "CASE 1B: Add Two Numbers + linked_list_reversal group (wrong match)",
    ADD_TWO_NUMBERS,
    [GROUP_LINKED_REVERSAL],
)

# Add Two Numbers — NO groups at all
trace_case(
    "CASE 1C: Add Two Numbers + NO solution groups",
    ADD_TWO_NUMBERS,
    [],
)

# Problem 3236 — with prefix_sum group
trace_case(
    "CASE 2A: Problem 3236 + prefix_sum group",
    PROBLEM_3236,
    [GROUP_PREFIX_SUM],
)

# Problem 3236 — NO groups
trace_case(
    "CASE 2B: Problem 3236 + NO solution groups",
    PROBLEM_3236,
    [],
)

# ============================================================
# Key diagnostic questions
# ============================================================
print("\n" + "=" * 70)
print("KEY DIAGNOSTIC FINDINGS")
print("=" * 70)

print("""
If Case 1A shows satisfaction > 0 and outcome = CONFIRMED:
  → The matching logic WORKS when the right group is provided.

If Case 1C shows UNRESOLVED (no groups):
  → The problem is that _load_ground_truth() returns empty groups
    or the solution_groups column is empty in the database.

If Case 1A works but the user still sees UNRESOLVED:
  → The deployed _load_ground_truth() is returning DIFFERENT groups
    than what we expect (possibly still returning V1 concepts in
    the 'patterns' field, or the solution_groups column is empty).
""")
