"""POST /analyze route — runs AST + Matching Engine on submitted code.

After a successful analysis, the result is persisted to the database:
submissions, gap_signals, user_pattern_elo, topic_profiles,
recommendations, and user streak.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.api.services.analysis import run_analysis
from pathforge.services.problem_resolver import resolve_problem
from pathforge.services.ground_truth_builder import GroundTruthError
from pathforge.services.persistence import run_persistence
from pathforge.llm.graphql_client import GraphQLUnavailableError
from pathforge.db.db import get_connection
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


class AnalyzeResponse(BaseModel):
    ast: dict
    match_result: dict
    persisted: PersistenceInfo


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    conn = get_connection(config.DATABASE_PATH)
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

    try:
        persisted = run_persistence(
            connection=conn,
            user_id=req.user_id,
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

    return AnalyzeResponse(
        ast=result["ast"],
        match_result=result["match_result"],
        persisted=PersistenceInfo(
            submission_id=persisted["submission_id"],
            gap_signals_count=persisted["gap_signals_count"],
            elo_updates_count=persisted["elo_updates_count"],
            recommendation_id=persisted.get("recommendation_id"),
        ),
    )
