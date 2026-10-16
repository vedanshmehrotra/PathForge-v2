"""Single documented boundary to the frozen shadow matcher (READ-ONLY).

The V2 POC never re-implements matching and never changes it.  Parsing +
fact/technique/strategy extraction are performed once per distinct code text
(cached) and the frozen ``evaluate_solution_groups`` is called with whatever
group list is being tested.  This preserves the frozen matcher's behaviour
exactly while avoiding redundant re-analysis across the ~thousands of
(solutions x groups) evaluations the canonical negative-control rule requires.
"""
import ast
from functools import lru_cache

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques

from .core import strategy_ids, technique_ids


@lru_cache(maxsize=None)
def _analyze(code_text: str):
    """Parse + fact/technique/strategy extraction once per distinct code text."""
    tree = ast.parse(code_text)
    relations = build_relations(tree)
    facts = extract_structural_facts(tree)
    tech = detect_techniques(facts, relations=relations)
    strat = evaluate_strategies(tech, facts)
    return tech, strat, facts


def observed_concepts(code_text: str) -> list:
    """Concept ids (techniques | strategies) observed by the frozen pipeline."""
    try:
        tech, strat, _ = _analyze(code_text)
    except Exception:
        return []
    return sorted(set(technique_ids_from(tech)) | set(strategy_ids_from(strat)))


def technique_ids_from(tech) -> list:
    return sorted({t.technique_id for t in tech})


def strategy_ids_from(strat) -> list:
    return sorted({s.strategy_id for s in strat})


def evaluate_with_groups(code_text: str, groups: list) -> dict:
    """Evaluate one solution against a group list using the frozen matcher."""
    try:
        tech, strat, facts = _analyze(code_text)
    except Exception:
        return {"outcome": "ERROR", "satisfied_group_ids": [],
                "reasoning": ["frozen shadow pipeline could not parse input"]}
    if not groups:
        return {"outcome": "UNRESOLVED", "satisfied_group_ids": [],
                "reasoning": ["no solution groups supplied"]}
    mo = evaluate_solution_groups(groups, tech, strat, facts)
    return {
        "outcome": mo.outcome,
        "satisfied_group_ids": list(mo.satisfied_group_ids or []),
        "reasoning": list(mo.reasoning or []),
    }
