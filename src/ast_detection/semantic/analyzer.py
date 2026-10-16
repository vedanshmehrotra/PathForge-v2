"""Main semantic analyzer combining feature extraction and scoring.

Provides a single entry point for analyzing code and producing
pattern scores with evidence.
"""
import ast
from typing import Dict, Optional

from .features import SemanticFeatures
from .extractor import extract_features
from .scorer import PatternScore, score_patterns
from .primary_role import extract_primary_role
from .primary_scorer import compute_primary_role_scores, PrimaryRoleResult


class SemanticAnalyzer:
    """Deterministic semantic analyzer for Python code.

    Extracts semantic features and computes pattern scores without
    depending on variable names, specific AST shapes, or loop forms.
    """

    def analyze(self, code: str) -> Optional[dict]:
        """Analyze code and return semantic features + pattern scores.

        Args:
            code: Python source code string

        Returns:
            Dict with 'features', 'scores', and 'primary_role_scores',
            or None if parsing fails
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        features = extract_features(tree)
        extract_primary_role(tree, features)
        scores = score_patterns(features)
        primary_scores = compute_primary_role_scores(features)

        return {
            "features": features.to_dict(),
            "scores": {name: ps.to_dict() for name, ps in scores.items()},
            "primary_role_scores": {
                name: {
                    "structural_score": round(pr.structural_score, 4),
                    "gate": round(pr.gate, 4),
                    "final_score": round(pr.final_score, 4),
                    "is_primary": pr.is_primary,
                    "classification": pr.classification,
                    "evidence": [
                        {"signal": e.signal, "impact": e.impact, "description": e.description}
                        for e in pr.gate_evidence
                    ],
                }
                for name, pr in primary_scores.items()
            },
        }

    def analyze_from_ast(self, tree: ast.AST) -> dict:
        """Analyze from a pre-parsed AST.

        Args:
            tree: Parsed Python AST

        Returns:
            Dict with 'features' and 'scores'
        """
        features = extract_features(tree)
        extract_primary_role(tree, features)
        scores = score_patterns(features)
        primary_scores = compute_primary_role_scores(features)

        return {
            "features": features.to_dict(),
            "scores": {name: ps.to_dict() for name, ps in scores.items()},
            "primary_role_scores": {
                name: {
                    "structural_score": round(pr.structural_score, 4),
                    "gate": round(pr.gate, 4),
                    "final_score": round(pr.final_score, 4),
                    "is_primary": pr.is_primary,
                    "classification": pr.classification,
                }
                for name, pr in primary_scores.items()
            },
        }
