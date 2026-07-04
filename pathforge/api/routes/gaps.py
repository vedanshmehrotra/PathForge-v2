"""POST /gaps route — returns stored gap signals for a user."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.api.services.gap import get_gap_signals

router = APIRouter()


class GapRequest(BaseModel):
    user_id: int


@router.post("/gaps")
def gaps_endpoint(req: GapRequest):
    result = get_gap_signals(req.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
