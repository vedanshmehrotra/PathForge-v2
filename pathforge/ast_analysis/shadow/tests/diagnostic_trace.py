"""Diagnostic trace for vocabulary mismatch debugging.

Traces the complete path from ground truth loading → technique detection → strategy evaluation → matching.
"""
import json
import ast
import sys
sys.path.insert(0, '.')


def trace_add_two_numbers():
    """Trace Add Two Numbers (LeetCode 2)."""
    code = """
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

    print("=" * 70)
    print("CASE 1: ADD TWO NUMBERS")
    print("=" * 70)

    # Step 1: Extract facts
    from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    print("\n--- STRUCTURAL FACTS ---")
    for f in facts:
        print(f"  {f.fact_type}: {f.fact_id} (attributes={f.attributes})")

    # Step 2: Detect techniques
    from pathforge.ast_analysis.shadow.techniques import detect_techniques
    techs = detect_techniques(facts)
    print("\n--- TECHNIQUE EVIDENCE ---")
    for t in techs:
        print(f"  {t.technique_id}: confidence={t.presence_confidence}, centrality={t.centrality}")

    detected_technique_ids = {t.technique_id for t in techs}
    print(f"\n  Detected technique IDs: {detected_technique_ids}")

    # Step 3: Evaluate strategies
    from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
    strats = evaluate_strategies(techs, facts)
    print("\n--- STRATEGY EVIDENCE ---")
    for s in strats:
        print(f"  {s.strategy_id}: confidence={s.confidence}")
    if not strats:
        print("  (none)")

    detected_strategy_ids = {s.strategy_id for s in strats}
    print(f"\n  Detected strategy IDs: {detected_strategy_ids}")

    # Step 4: Simulate what _load_ground_truth returns
    # For Add Two Numbers, the ground truth builder maps:
    # LLM proposes: ["carry_propagation"] or similar
    # V1 mapping: carry_propagation → required=["carry_propagation"], optional=["linked_list_traversal"]
    print("\n--- SIMULATED SOLUTION GROUPS ---")

    # Case A: carry_propagation group
    group_carry = {
        "id": "group_0",
        "required": ["carry_propagation"],
        "optional": ["linked_list_traversal"],
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": ["carry_propagation"],
    }

    # Case B: linked_list_traversal group
    group_linked = {
        "id": "group_1",
        "required": ["linked_list_traversal"],
        "optional": ["carry_propagation"],
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": ["linked_list_traversal"],
    }

    # Case C: what ground truth builder actually produces for linked_list_reversal
    # The V1 mapping now says: linked_list_reversal → required=["linked_list_traversal"]
    group_from_reversal = {
        "id": "group_2",
        "required": ["linked_list_traversal"],
        "optional": [],
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": ["linked_list_reversal"],
    }

    groups = [group_carry, group_linked, group_from_reversal]

    for g in groups:
        print(f"\n  Group {g['id']}:")
        print(f"    required = {g['required']}")
        print(f"    optional = {g['optional']}")
        print(f"    excluded = {g['excluded']}")

        # Step 5: Evaluate
        from pathforge.ast_analysis.shadow.matching import _evaluate_single_group
        det_techs = {t.technique_id: t for t in techs}
        det_strats = {s.strategy_id: s for s in strats}
        result = _evaluate_single_group(g, det_techs, det_strats)

        print(f"    --- EVALUATION ---")
        print(f"    outcome = {result['outcome']}")
        print(f"    satisfaction = {result['satisfaction']:.3f}")

        # Trace each required item
        for req in g["required"]:
            in_tech = req in det_techs
            in_strat = req in det_strats
            tech_conf = det_techs[req].presence_confidence if in_tech else None
            strat_conf = det_strats[req].confidence if in_strat else None
            print(f"    req='{req}': in_techniques={in_tech}, in_strategies={in_strat}, "
                  f"tech_conf={tech_conf}, strat_conf={strat_conf}")

        for opt in g["optional"]:
            in_tech = opt in det_techs
            in_strat = opt in det_strats
            print(f"    opt='{opt}': in_techniques={in_tech}, in_strategies={in_strat}")

        for exc in g["excluded"]:
            in_tech = exc in det_techs
            in_strat = exc in det_strats
            print(f"    exc='{exc}': in_techniques={in_tech}, in_strategies={in_strat}")


def trace_3236():
    """Trace Problem 3236 (prefix_sum style)."""
    code = """
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

    print("\n" + "=" * 70)
    print("CASE 2: PROBLEM 3236 (prefix_sum style)")
    print("=" * 70)

    tree = ast.parse(code)
    from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
    from pathforge.ast_analysis.shadow.techniques import detect_techniques
    from pathforge.ast_analysis.shadow.strategies import evaluate_strategies

    facts = extract_structural_facts(tree)
    print("\n--- STRUCTURAL FACTS ---")
    for f in facts:
        print(f"  {f.fact_type}: {f.fact_id} (attributes={f.attributes})")

    techs = detect_techniques(facts)
    print("\n--- TECHNIQUE EVIDENCE ---")
    for t in techs:
        print(f"  {t.technique_id}: confidence={t.presence_confidence}, centrality={t.centrality}")

    detected_technique_ids = {t.technique_id for t in techs}
    print(f"\n  Detected technique IDs: {detected_technique_ids}")

    strats = evaluate_strategies(techs, facts)
    print("\n--- STRATEGY EVIDENCE ---")
    for s in strats:
        print(f"  {s.strategy_id}: confidence={s.confidence}")
    if not strats:
        print("  (none)")

    detected_strategy_ids = {s.strategy_id for s in strats}
    print(f"\n  Detected strategy IDs: {detected_strategy_ids}")

    # Simulated solution groups
    group_prefix = {
        "id": "group_0",
        "required": ["sequential_accumulation"],
        "optional": ["iterative_table_filling"],
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": ["prefix_sum"],
    }

    group_dp = {
        "id": "group_1",
        "required": ["iterative_table_filling"],
        "optional": ["sequential_accumulation"],
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": ["dp_bottom_up"],
    }

    groups = [group_prefix, group_dp]

    for g in groups:
        print(f"\n  Group {g['id']}:")
        print(f"    required = {g['required']}")
        print(f"    optional = {g['optional']}")

        from pathforge.ast_analysis.shadow.matching import _evaluate_single_group
        det_techs = {t.technique_id: t for t in techs}
        det_strats = {s.strategy_id: s for s in strats}
        result = _evaluate_single_group(g, det_techs, det_strats)

        print(f"    --- EVALUATION ---")
        print(f"    outcome = {result['outcome']}")
        print(f"    satisfaction = {result['satisfaction']:.3f}")

        for req in g["required"]:
            in_tech = req in det_techs
            in_strat = req in det_strats
            tech_conf = det_techs[req].presence_confidence if in_tech else None
            strat_conf = det_strats[req].confidence if in_strat else None
            print(f"    req='{req}': in_techniques={in_tech}, in_strategies={in_strat}, "
                  f"tech_conf={tech_conf}, strat_conf={strat_conf}")


if __name__ == "__main__":
    trace_add_two_numbers()
    trace_3236()
