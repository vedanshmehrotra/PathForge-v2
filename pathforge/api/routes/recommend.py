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
    policy: Literal["recorded_practice_v1", "calendar_practice_v2"] = "recorded_practice_v1"
    difficulty: Optional[Literal["Easy", "Medium", "Hard"]] = None
    excluded_ids: list[str] = Field(default_factory=list, max_length=50)


@router.post("/recommend")
def recommend_endpoint(req: RecommendRequest, request: Request):
    user = get_current_user(request)
    if req.mode == "practice":
        options = {"mode": "practice", "difficulty": req.difficulty, "excluded_ids": req.excluded_ids}
        if req.policy != "recorded_practice_v1":
            options["policy"] = req.policy
        result = get_recommendations(user.user_id, **options)
    else:
        result = get_recommendations(user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
