from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImportUploadResponse(BaseModel):
    upload_id: str
    filename: str
    detected_format: str
    input_dir: str
    saved_path: str
    article_count_preview: int = 0
    job_id: int | None = None
    suggested_job: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
