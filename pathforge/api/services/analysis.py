"""Analysis orchestration — AST + Matching Engine pipeline."""

from typing import Dict, Any, Optional
from src.ast_detection.run_analysis import ASTAnalysisEngine
from src.matching_engine.matching_engine import MatchingEngine


_ast_engine = ASTAnalysisEngine()
_matching_engine = MatchingEngine()


def run_analysis(
    code: str,
    language: str = "python",
    accepted_solution_groups: Optional[list] = None,
) -> Dict[str, Any]:
    if language != "python":
        return {
            "error": f"Unsupported language: {language}",
            "stage": "VALIDATION",
        }
    try:
        ast_output = _ast_engine.analyze(code)
    except SyntaxError as e:
        return {
            "error": f"Syntax error in code: {e}",
            "stage": "AST",
        }
    except Exception as e:
        return {
            "error": f"AST analysis failed: {e}",
            "stage": "AST",
        }

    detected = ast_output.get("detected_patterns", [])
    ast_for_matching = []
    for entry in detected:
        ast_for_matching.append({
            "pattern_id": entry.get("pattern_id", ""),
            "confidence": entry.get("confidence", 0.0),
        })

    if accepted_solution_groups:
        llm_input = {
            "accepted_solution_groups": [
                g["patterns"] for g in accepted_solution_groups
            ],
        }
    else:
        # No ground truth available — do NOT fall back to a hardcoded pattern.
        # Return an explicit unresolved result so the user is never told
        # their code is wrong based on fabricated expected patterns.
        return {
            "ast": ast_output,
            "match_result": {
                "match_result": "NO_GROUND_TRUTH",
                "matched_groups": [],
                "unmatched_patterns": [],
                "confidence_score": 0.0,
                "reasoning_signals": [
                    "No verified ground truth available for this problem.",
                    "Matching was skipped.",
                ],
            },
        }

    try:
        match_result = _matching_engine.match(llm_input, ast_for_matching)
    except Exception as e:
        return {
            "error": f"Matching Engine failed: {e}",
            "stage": "MATCHING",
        }

    return {
        "ast": ast_output,
        "match_result": match_result,
    }
