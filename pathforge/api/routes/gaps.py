"""POST /gaps route — returns stored gap signals for a user."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pathforge.api.services.gap import get_gap_signals
from pathforge.auth.auth_middleware import get_current_user

router = APIRouter()


class GapRequest(BaseModel):
    user_id: int


@router.post("/gaps")
def gaps_endpoint(req: GapRequest, request: Request):
    user = get_current_user(request)
    result = get_gap_signals(user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
