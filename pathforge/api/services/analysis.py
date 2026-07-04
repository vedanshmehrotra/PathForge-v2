"""Analysis orchestration — AST + Matching Engine pipeline."""

from typing import Dict, Any
from src.ast_detection.run_analysis import ASTAnalysisEngine
from src.matching_engine.matching_engine import MatchingEngine


_ast_engine = ASTAnalysisEngine()
_matching_engine = MatchingEngine()


def run_analysis(code: str, language: str = "python") -> Dict[str, Any]:
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

    llm_groups = []
    for entry in ast_for_matching:
        llm_groups.append([entry["pattern_id"]])

    if not llm_groups:
        llm_groups = [["hash_map_lookup"]]

    llm_input = {"accepted_solution_groups": llm_groups}

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
