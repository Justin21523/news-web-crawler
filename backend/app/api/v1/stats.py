from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_stats
from app.schemas.stats import StatsResponse
from app.services.stats import StatsService

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def stats(service: StatsService = Depends(get_stats)) -> StatsResponse:
    return service.stats()
