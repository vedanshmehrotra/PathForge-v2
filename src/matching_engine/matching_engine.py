"""Matching Engine: converts LLM + AST signals into final structured decisions.

This is the FIRST system layer that interprets AST outputs.
It is deterministic, pattern-level matching only.
No problem-specific logic is hardcoded.
"""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field


MATCH_THRESHOLD = 0.6
EXTRA_PATTERN_PENALTY = 0.1


@dataclass
class MatchResult:
    match_result: str
    matched_groups: List[int]
    unmatched_patterns: List[str]
    confidence_score: float
    reasoning_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_result": self.match_result,
            "matched_groups": self.matched_groups,
            "unmatched_patterns": self.unmatched_patterns,
            "confidence_score": self.confidence_score,
            "reasoning_signals": self.reasoning_signals,
        }


class MatchingEngine:

    def match(self, llm_output: Dict[str, Any], ast_output: List[Dict[str, Any]]) -> Dict[str, Any]:
        ast_map = self._normalize_ast(ast_output)
        ast_pattern_set = set(ast_map.keys())

        llm_groups = self._normalize_llm(llm_output)
        all_llm_patterns = set()
        for group in llm_groups:
            all_llm_patterns.update(group)

        group_matches = self._compute_group_matches(ast_pattern_set, ast_map, llm_groups)

        confidence = self._compute_confidence(
            ast_map, ast_pattern_set, all_llm_patterns, llm_groups, group_matches
        )

        match_result = self._decide_match_result(group_matches, ast_pattern_set, confidence)

        matched_group_indices = [
            i for i, m in enumerate(group_matches) if m["is_fully_matched"]
        ]

        unmatched = self._compute_unmatched(ast_pattern_set, all_llm_patterns, llm_groups)

        reasoning = self._build_reasoning_signals(
            match_result, group_matches, ast_pattern_set, all_llm_patterns, confidence
        )

        result = MatchResult(
            match_result=match_result,
            matched_groups=matched_group_indices,
            unmatched_patterns=sorted(unmatched),
            confidence_score=round(confidence, 4),
            reasoning_signals=reasoning,
        )

        return result.to_dict()

    def _normalize_ast(self, ast_output: List[Dict[str, Any]]) -> Dict[str, float]:
        result = {}
        for entry in ast_output:
            pid = entry.get("pattern_id", "")
            conf = entry.get("confidence", 0.0)
            if pid and conf > 0.0:
                existing = result.get(pid, 0.0)
                result[pid] = max(existing, conf)
        return result

    def _normalize_llm(self, llm_output: Dict[str, Any]) -> List[Set[str]]:
        raw_groups = llm_output.get("accepted_solution_groups", [])
        groups = []
        for g in raw_groups:
            normalized = set()
            for p in g:
                if isinstance(p, str) and p.strip():
                    normalized.add(p.strip())
            if normalized:
                groups.append(normalized)
        return groups

    def _compute_group_matches(
        self,
        ast_patterns: Set[str],
        ast_map: Dict[str, float],
        llm_groups: List[Set[str]],
    ) -> List[Dict[str, Any]]:
        results = []
        for group in llm_groups:
            matched = group & ast_patterns
            missing = group - ast_patterns
            overlap_count = len(matched)
            group_size = len(group)
            coverage = overlap_count / group_size if group_size > 0 else 0.0
            is_fully_matched = overlap_count == group_size and group_size > 0
            avg_confidence = 0.0
            if matched:
                avg_confidence = sum(ast_map.get(p, 0.0) for p in matched) / len(matched)
            results.append({
                "matched": matched,
                "missing": missing,
                "overlap_count": overlap_count,
                "group_size": group_size,
                "coverage": coverage,
                "is_fully_matched": is_fully_matched,
                "avg_confidence": avg_confidence,
            })
        return results

    def _compute_confidence(
        self,
        ast_map: Dict[str, float],
        ast_pattern_set: Set[str],
        all_llm_patterns: Set[str],
        llm_groups: List[Set[str]],
        group_matches: List[Dict[str, Any]],
    ) -> float:
        if not all_llm_patterns or not ast_pattern_set:
            return 0.0

        best_confidence = 0.0
        for gm in group_matches:
            if gm["group_size"] == 0:
                continue
            matched = gm["matched"]
            if not matched:
                continue
            group_weighted = sum(ast_map.get(p, 0.0) for p in matched)
            group_conf = group_weighted / gm["group_size"]
            best_confidence = max(best_confidence, group_conf)

        extra_ast = ast_pattern_set - all_llm_patterns
        if extra_ast and best_confidence > 0.0:
            extra_penalty = sum(ast_map.get(p, 0.0) for p in extra_ast) * EXTRA_PATTERN_PENALTY
            best_confidence = max(0.0, best_confidence - extra_penalty)

        return min(best_confidence, 1.0)

    def _decide_match_result(
        self,
        group_matches: List[Dict[str, Any]],
        ast_pattern_set: Set[str],
        confidence: float,
    ) -> str:
        if not group_matches or not ast_pattern_set:
            return "NO_MATCH"

        has_full = any(m["is_fully_matched"] for m in group_matches)

        if has_full and confidence >= MATCH_THRESHOLD:
            return "FULL_MATCH"

        has_any_overlap = any(m["overlap_count"] > 0 for m in group_matches)

        if has_any_overlap:
            return "PARTIAL_MATCH"

        return "NO_MATCH"

    def _compute_unmatched(
        self,
        ast_pattern_set: Set[str],
        all_llm_patterns: Set[str],
        llm_groups: List[Set[str]],
    ) -> List[str]:
        unmatched = set()
        for group in llm_groups:
            for p in group:
                if p not in ast_pattern_set:
                    unmatched.add(p)
        return list(unmatched)

    def _build_reasoning_signals(
        self,
        match_result: str,
        group_matches: List[Dict[str, Any]],
        ast_pattern_set: Set[str],
        all_llm_patterns: Set[str],
        confidence: float,
    ) -> List[str]:
        signals = []
        signals.append(f"match_result={match_result}")
        signals.append(f"confidence={confidence:.4f}")

        total_ast = len(ast_pattern_set)
        total_llm = len(all_llm_patterns)
        signals.append(f"ast_patterns_detected={total_ast}")
        signals.append(f"llm_patterns_expected={total_llm}")

        for i, gm in enumerate(group_matches):
            if gm["is_fully_matched"]:
                signals.append(f"group_{i}_full_match")
            elif gm["overlap_count"] > 0:
                signals.append(
                    f"group_{i}_partial({gm['overlap_count']}/{gm['group_size']})"
                )
            else:
                signals.append(f"group_{i}_no_match")

        if total_llm > 0:
            coverage = sum(m["overlap_count"] for m in group_matches) / total_llm
            signals.append(f"llm_coverage={coverage:.4f}")

        return signals
