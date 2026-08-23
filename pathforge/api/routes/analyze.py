"""POST /analyze route — runs AST + Matching Engine on submitted code.

After a successful analysis, the result is persisted to the database:
submissions, gap_signals, user_pattern_elo, topic_profiles,
recommendations, and user streak.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pathforge.api.services.analysis import run_analysis
from pathforge.auth.auth_middleware import get_current_user
from pathforge.services.problem_resolver import resolve_problem
from pathforge.services.ground_truth_builder import GroundTruthError
from pathforge.services.persistence import run_persistence
from pathforge.llm.graphql_client import GraphQLUnavailableError
from pathforge.db.db import get_connection
from pathforge.api.services.shadow_observability import record_shadow_result, get_shadow_log_dict
import config

router = APIRouter()


class ProblemIdentifier(BaseModel):
    leetcode_id: Optional[int] = None
    title_slug: Optional[str] = None


class AnalyzeRequest(BaseModel):
    user_id: int
    code: str
    language: str = "python"
    problem: Optional[ProblemIdentifier] = None


class PersistenceInfo(BaseModel):
    submission_id: int
    gap_signals_count: int
    elo_updates_count: int
    recommendation_id: Optional[int] = None


class CanonicalPattern(BaseModel):
    name: str
    confidence: float


class ProblemInfo(BaseModel):
    leetcode_id: Optional[int] = None
    title: Optional[str] = None
    difficulty: Optional[str] = None
    canonical_patterns: list[CanonicalPattern] = []


class EloUpdate(BaseModel):
    pattern_id: str
    elo_before: float
    elo_after: float
    delta: float


class SubmissionGap(BaseModel):
    detected_pattern_ids: list[str]
    missing_pattern_ids: list[str]
    gap_identified: bool


class HybridPatternInfo(BaseModel):
    """Per-pattern shadow detection info."""
    pattern_id: str
    ast_detected: bool
    ast_confidence: float = 0.0
    semantic_score: float = 0.0
    hybrid_detected: bool = False
    fusion_policy: str = ""
    discrepancy_type: str = ""


class HybridAnalysis(BaseModel):
    """Optional shadow-mode hybrid analysis metadata."""
    code_hash: str
    hybrid_detections: dict[str, bool]
    patterns: list[HybridPatternInfo]
    ast_latency_ms: float = 0.0
    semantic_latency_ms: float = 0.0


class ShadowAnalysisResult(BaseModel):
    """Shadow-mode analysis result from the new fact/technique/strategy path."""
    structural_facts: list[dict] = []
    technique_evidence: list[dict] = []
    strategy_evidence: list[dict] = []
    match_outcome: Optional[dict] = None
    extractor_version: str = ""
    elapsed_ms: float = 0.0


class AnalyzeResponse(BaseModel):
    ast: dict
    match_result: dict
    problem_info: Optional[ProblemInfo] = None
    elo_updates: list[EloUpdate] = []
    submission_gap: Optional[SubmissionGap] = None
    persisted: PersistenceInfo
    hybrid_analysis: Optional[HybridAnalysis] = None
    shadow_analysis: Optional[ShadowAnalysisResult] = None


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest, request: Request):
    user = get_current_user(request)
    conn = get_connection(config.DATABASE_PATH)
    try:
        groups = None
        ctx = None

        if req.problem:
            try:
                ctx = resolve_problem(
                    conn,
                    leetcode_id=req.problem.leetcode_id,
                    title_slug=req.problem.title_slug,
                )
                groups = ctx.accepted_solution_groups
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except (GraphQLUnavailableError, GroundTruthError) as e:
                raise HTTPException(status_code=502, detail=str(e))

        result = run_analysis(req.code, req.language, accepted_solution_groups=groups)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result)

        problem_info = None
        if ctx:
            canonical_patterns = [
                CanonicalPattern(name=p, confidence=ctx.ground_truth_confidence.get(p, 0.0))
                for g in (ctx.accepted_solution_groups or [])
                for p in (g.get("patterns", []) if isinstance(g, dict) else g)
            ]
            problem_info = ProblemInfo(
                leetcode_id=ctx.leetcode_id,
                title=ctx.title,
                difficulty=ctx.difficulty,
                canonical_patterns=canonical_patterns,
            )

        try:
            persisted = run_persistence(
                connection=conn,
                user_id=user.user_id,
                problem_id=ctx.leetcode_id if ctx else None,
                problem_difficulty=ctx.difficulty if ctx else None,
                code=req.code,
                ast_output=result["ast"],
                match_result=result["match_result"],
                groups=groups,
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Analysis completed but persistence failed: {e}",
            )

        elo_updates = [
            EloUpdate(
                pattern_id=u["pattern_id"],
                elo_before=u["old_elo"],
                elo_after=u["new_elo"],
                delta=u["delta"],
            )
            for u in persisted.get("elo_output", {}).get("pattern_elo_updates", [])
        ]

        submission_gap = None
        if ctx:
            detected_patterns = result.get("ast", {}).get("detected_patterns", [])
            detected_ids = [
                d.get("pattern_id", d.get("name", ""))
                for d in detected_patterns
                if d.get("detected", True)
            ]
            unmatched = result.get("match_result", {}).get("unmatched_patterns", [])
            missing_ids = [
                u if isinstance(u, str) else u.get("pattern_id", u.get("name", ""))
                for u in (unmatched or [])
            ]
            submission_gap = SubmissionGap(
                detected_pattern_ids=detected_ids,
                missing_pattern_ids=missing_ids,
                gap_identified=len(missing_ids) > 0,
            )

        # --- Shadow-mode hybrid analysis (observational only) ---
        hybrid_analysis = None
        try:
            from src.ast_detection.semantic.shadow_detector import ShadowDetector
            _shadow = ShadowDetector()
            _shadow_result = _shadow.analyze_safe(req.code)
            record_shadow_result(_shadow_result)

            if _shadow_result:
                patterns_info = []
                for disc in _shadow_result.discrepancies:
                    patterns_info.append(HybridPatternInfo(
                        pattern_id=disc.pattern_id,
                        ast_detected=disc.ast_detected,
                        ast_confidence=disc.ast_confidence,
                        semantic_score=disc.sem_score,
                        hybrid_detected=disc.hybrid_detected,
                        fusion_policy=disc.fusion_policy,
                        discrepancy_type=disc.discrepancy_type,
                    ))
                hybrid_analysis = HybridAnalysis(
                    code_hash=_shadow_result.code_hash,
                    hybrid_detections=_shadow_result.hybrid_detections,
                    patterns=patterns_info,
                    ast_latency_ms=_shadow_result.ast_latency_ms,
                    semantic_latency_ms=_shadow_result.sem_latency_ms,
                )
        except Exception:
            # Shadow analysis must never affect production
            pass

        # --- Shadow analysis: new fact/technique/strategy path (observational only) ---
        shadow_result = None
        submission_id = persisted["submission_id"]
        try:
            from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
            from pathforge.ast_analysis.shadow.persistence import (
                persist_shadow_analysis, compute_code_hash,
            )
            shadow_raw = run_shadow_analysis(req.code, solution_groups=groups)
            if shadow_raw:
                shadow_result = ShadowAnalysisResult(**shadow_raw)
                # Persist shadow results to the submission row
                code_hash = compute_code_hash(req.code)
                persist_shadow_analysis(conn, submission_id, code_hash, shadow_raw)
        except Exception:
            # Shadow analysis must never affect production
            pass

        return AnalyzeResponse(
            ast=result["ast"],
            match_result=result["match_result"],
            problem_info=problem_info,
            elo_updates=elo_updates,
            submission_gap=submission_gap,
            persisted=PersistenceInfo(
                submission_id=persisted["submission_id"],
                gap_signals_count=persisted["gap_signals_count"],
                elo_updates_count=persisted["elo_updates_count"],
                recommendation_id=persisted.get("recommendation_id"),
            ),
            hybrid_analysis=hybrid_analysis,
            shadow_analysis=shadow_result,
        )
    finally:
        conn.close()
