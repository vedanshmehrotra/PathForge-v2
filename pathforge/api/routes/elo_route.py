"""POST /elo route — returns stored Elo ratings for a user."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.api.services.elo import get_elo_ratings

router = APIRouter()


class EloRequest(BaseModel):
    user_id: int


@router.post("/elo")
def elo_endpoint(req: EloRequest):
    result = get_elo_ratings(req.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
