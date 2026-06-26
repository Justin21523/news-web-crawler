from __future__ import annotations

from fastapi import APIRouter

from app.schemas.llm import LLMHealthResponse
from app.services.llm import LLMService

router = APIRouter(tags=["llm"])


@router.get("/llm/health", response_model=LLMHealthResponse)
def llm_health() -> LLMHealthResponse:
    return LLMService().health()
