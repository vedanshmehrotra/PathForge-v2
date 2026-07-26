"""POST /elo route — returns stored Elo ratings for a user."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pathforge.api.services.elo import get_elo_ratings
from pathforge.auth.auth_middleware import get_current_user

router = APIRouter()


class EloRequest(BaseModel):
    user_id: int


@router.post("/elo")
def elo_endpoint(req: EloRequest, request: Request):
    user = get_current_user(request)
    result = get_elo_ratings(user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
