from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.entity_extraction import (
    EntityExtractionCompareResponse,
    EntityExtractionRunListResponse,
    EntityExtractionRunResponse,
    EntityProviderListResponse,
)
from app.services.entity_extraction import EntityExtractionService

router = APIRouter(tags=["entity-extraction"])


def _service() -> EntityExtractionService:
    return EntityExtractionService()


@router.get("/entity-extraction/providers", response_model=EntityProviderListResponse)
def providers() -> EntityProviderListResponse:
    return _service().providers()


@router.get("/entity-extraction/runs", response_model=EntityExtractionRunListResponse)
def runs(limit: int = Query(20, ge=1, le=100)) -> EntityExtractionRunListResponse:
    return _service().runs(limit)


@router.post("/entity-extraction/run", response_model=EntityExtractionRunResponse)
def run(
    provider: str = Query("fallback", pattern="^(fallback|ckip|spacy|auto)$"),
    activate: bool = True,
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
    spacy_model: str | None = None,
) -> EntityExtractionRunResponse:
    return _service().run(provider, activate, source, category, date_from, date_to, limit, spacy_model)


@router.get("/entity-extraction/compare", response_model=EntityExtractionCompareResponse)
def compare(left_run_id: str | None = None, right_run_id: str | None = None, limit: int = Query(20, ge=1, le=100)) -> EntityExtractionCompareResponse:
    return _service().compare(left_run_id, right_run_id, limit)
