from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

JobType = Literal["demo", "crawl", "ingest", "nlp", "tfidf", "export", "run_all", "analysis", "entity_extraction", "train_ml", "train_decision_tree", "export_ml_diagnostics_report"]
JobStatus = Literal["queued", "running", "succeeded", "failed", "abandoned"]


class JobCreateRequest(BaseModel):
    type: JobType
    params: dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    id: int
    type: str
    status: str
    params: dict[str, Any]
    progress_done: int
    progress_total: int
    log_path: str | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class JobLogResponse(BaseModel):
    id: int
    content: str
