from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EntityProvider = Literal["fallback", "ckip", "spacy", "auto"]
EntityRunStatus = Literal["ready", "running", "insufficient_data", "dependency_missing", "error"]


class EntityProviderStatus(BaseModel):
    provider: str
    available: bool
    status: str = "available"
    detail: str = ""
    model: str | None = None


class EntityExtractionRun(BaseModel):
    run_id: str
    provider: str
    strategy: str
    status: EntityRunStatus | str
    params: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str | None = None


class EntityProviderListResponse(BaseModel):
    providers: list[EntityProviderStatus] = Field(default_factory=list)
    active_run_id: str | None = None
    active_entity_source: str = "fallback"


class EntityExtractionRunResponse(BaseModel):
    status: EntityRunStatus | str = "ready"
    run: EntityExtractionRun | None = None
    processed_documents: int = 0
    activated: bool = False
    outputs_preview: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EntityExtractionRunListResponse(BaseModel):
    runs: list[EntityExtractionRun] = Field(default_factory=list)


class EntityExtractionCompareResponse(BaseModel):
    status: EntityRunStatus | str = "ready"
    left_run: EntityExtractionRun | None = None
    right_run: EntityExtractionRun | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    type_distribution: list[dict[str, Any]] = Field(default_factory=list)
    sample_diffs: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
