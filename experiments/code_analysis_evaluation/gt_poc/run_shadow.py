"""Single documented boundary to the frozen shadow matcher (READ-ONLY).

The POC never re-implements matching and never changes it; it calls the frozen
``run_shadow_analysis`` and reduces the result to the fields the POC reports.
"""
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


def evaluate_with_groups(code_text: str, groups: list) -> dict:
    """Evaluate one solution against a group list using the frozen matcher."""
    result = run_shadow_analysis(code_text, solution_groups=groups or None)
    if result is None:
        return {
            "outcome": "ERROR",
            "satisfied_group_ids": [],
            "reasoning": ["frozen shadow pipeline returned None"],
        }
    mo = result.get("match_outcome") or {}
    return {
        "outcome": mo.get("outcome"),
        "satisfied_group_ids": list(mo.get("satisfied_group_ids") or []),
        "reasoning": list(mo.get("reasoning") or []),
    }
