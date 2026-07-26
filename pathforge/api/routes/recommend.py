"""POST /recommend route — returns problem recommendations for a user."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pathforge.api.services.recommend_service import get_recommendations
from pathforge.auth.auth_middleware import get_current_user

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: int


@router.post("/recommend")
def recommend_endpoint(req: RecommendRequest, request: Request):
    user = get_current_user(request)
    result = get_recommendations(user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
