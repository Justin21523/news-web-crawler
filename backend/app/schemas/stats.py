from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.jobs import JobRecord


class HealthResponse(BaseModel):
    status: str
    db_path: str
    data_dir: str


class StatsResponse(BaseModel):
    total_articles: int = 0
    cleaned: int = 0
    enriched: int = 0
    sources: dict[str, int] = Field(default_factory=dict)
    date_range: list[str | None] = Field(default_factory=lambda: [None, None])
    latest_jobs: list[JobRecord] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
