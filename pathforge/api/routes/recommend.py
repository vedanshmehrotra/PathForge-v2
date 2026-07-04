"""POST /recommend route — returns problem recommendations for a user."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.api.services.recommend_service import get_recommendations

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: int


@router.post("/recommend")
def recommend_endpoint(req: RecommendRequest):
    result = get_recommendations(req.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
