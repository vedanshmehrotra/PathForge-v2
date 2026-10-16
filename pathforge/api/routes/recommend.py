"""POST /recommend route — returns problem recommendations for a user."""

from fastapi import APIRouter, HTTPException, Request
from typing import Literal, Optional
from pydantic import BaseModel, Field

from pathforge.api.services.recommend_service import get_recommendations
from pathforge.auth.auth_middleware import get_current_user

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: int
    mode: Literal["legacy", "practice"] = "legacy"
    difficulty: Optional[Literal["Easy", "Medium", "Hard"]] = None
    excluded_ids: list[str] = Field(default_factory=list, max_length=50)


@router.post("/recommend")
def recommend_endpoint(req: RecommendRequest, request: Request):
    user = get_current_user(request)
    if req.mode == "practice":
        result = get_recommendations(user.user_id, mode="practice",
                                     difficulty=req.difficulty, excluded_ids=req.excluded_ids)
    else:
        result = get_recommendations(user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
