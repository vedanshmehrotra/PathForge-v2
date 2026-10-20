"""POST /prepare-problem route — pre-fills the problem cache (GraphQL + LLM).

This is a slow endpoint (may take several seconds) that should be called
once per problem before the first /analyze for that problem.
Runtime /analyze always remains fast and deterministic.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pathforge.services.problem_resolver import resolve_problem, ProblemReadinessError
from pathforge.auth.auth_middleware import get_current_user
from pathforge.services.ground_truth_builder import GroundTruthError
from pathforge.llm.graphql_client import GraphQLUnavailableError
from pathforge.db.db import get_connection
from pathforge.api.services.approaches import SolutionApproach, UnscoredApproach, describe_approaches
import config

router = APIRouter()


class ProblemIdentifier(BaseModel):
    leetcode_id: Optional[int] = None
    title_slug: Optional[str] = None


class PrepareRequest(BaseModel):
    problem: ProblemIdentifier


class PrepareResponse(BaseModel):
    leetcode_id: int
    title_slug: str
    title: str
    difficulty: str
    topics: list
    solution_groups: list[SolutionApproach] = []
    unscored_approaches: list[UnscoredApproach] = []


@router.post("/prepare-problem", response_model=PrepareResponse)
def prepare_problem_endpoint(req: PrepareRequest, request: Request):
    get_current_user(request)  # auth gate — user object not needed by this endpoint
    conn = get_connection(config.DATABASE_PATH)
    try:
        try:
            ctx = resolve_problem(
                conn,
                leetcode_id=req.problem.leetcode_id,
                title_slug=req.problem.title_slug,
                allow_preparation=True,
            )
        except ProblemReadinessError as e:
            raise HTTPException(status_code=409, detail=e.detail)
        except ValueError as e:
            raise HTTPException(
                status_code=404,
                detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found. Check its LeetCode ID or link."},
            )
        except GraphQLUnavailableError:
            raise HTTPException(
                status_code=502,
                detail={"code": "PROBLEM_SOURCE_UNAVAILABLE", "message": "LeetCode could not be reached. Try preparing the problem later, or inspect your code on its own."},
            )
        except GroundTruthError as e:
            message = ("The generated approach information could not be validated. Nothing was saved for comparison. You can retry preparation or inspect your code on its own."
                       if e.code == "PREPARATION_INVALID_OUTPUT" else str(e))
            detail = {"code": e.code, "message": message}
            headers = None
            if e.retry_after is not None:
                detail["retry_after"] = e.retry_after
                headers = {"Retry-After": str(e.retry_after)}
            raise HTTPException(status_code=502, detail=detail, headers=headers)

        return PrepareResponse(
            leetcode_id=ctx.leetcode_id,
            title_slug=ctx.title_slug,
            title=ctx.title,
            difficulty=ctx.difficulty,
            topics=ctx.topics,
            solution_groups=describe_approaches(ctx.accepted_solution_groups),
            unscored_approaches=getattr(ctx, "unscored_approaches", []),
        )
    finally:
        conn.close()
