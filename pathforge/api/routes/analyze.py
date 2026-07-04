"""POST /analyze route — runs AST + Matching Engine on submitted code."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pathforge.api.services.analysis import run_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    user_id: str
    code: str
    language: str = "python"


class AnalyzeResponse(BaseModel):
    ast: dict
    match_result: dict


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    result = run_analysis(req.code, req.language)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return AnalyzeResponse(
        ast=result["ast"],
        match_result=result["match_result"],
    )
