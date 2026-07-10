"""POST /prepare-problem route — pre-fills the problem cache (GraphQL + LLM).

This is a slow endpoint (may take several seconds) that should be called
once per problem before the first /analyze for that problem.
Runtime /analyze always remains fast and deterministic.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.services.problem_resolver import resolve_problem
from pathforge.services.ground_truth_builder import GroundTruthError
from pathforge.llm.graphql_client import GraphQLUnavailableError
from pathforge.db.db import get_connection
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


@router.post("/prepare-problem", response_model=PrepareResponse)
def prepare_problem_endpoint(req: PrepareRequest):
    conn = get_connection(config.DATABASE_PATH)
    try:
        ctx = resolve_problem(
            conn,
            leetcode_id=req.problem.leetcode_id,
            title_slug=req.problem.title_slug,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"This problem could not be prepared. Very recent or contest problems may not yet be available through the LeetCode GraphQL API. ({e})",
        )
    except (GraphQLUnavailableError, GroundTruthError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"This problem could not be prepared. Very recent or contest problems may not yet be available through the LeetCode GraphQL API. ({e})",
        )

    return PrepareResponse(
        leetcode_id=ctx.leetcode_id,
        title_slug=ctx.title_slug,
        title=ctx.title,
        difficulty=ctx.difficulty,
        topics=ctx.topics,
    )
