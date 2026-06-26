from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.v1.deps import get_jobs
from app.core.config import get_settings
from app.schemas.imports import ImportUploadResponse
from app.schemas.jobs import JobCreateRequest
from app.services.jobs import JobService

router = APIRouter(tags=["imports"])

ALLOWED_EXTENSIONS = {".csv", ".json", ".jsonl"}


@router.post("/import/upload", response_model=ImportUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    run: bool = Query(False, description="Create an ingest job immediately after saving the upload."),
    jobs: JobService = Depends(get_jobs),
) -> ImportUploadResponse:
    filename = Path(file.filename or "uploaded.jsonl").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension or 'unknown'}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    settings = get_settings()
    upload_id = uuid4().hex[:12]
    upload_dir = settings.resolved_raw_dir / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / "uploaded.jsonl"

    notes: list[str] = []
    try:
        if extension == ".csv":
            rows = _csv_rows(content)
            count = _write_jsonl(saved_path, rows, upload_id)
            notes.append("CSV columns were mapped into raw article fields.")
        elif extension == ".json":
            rows = _json_rows(content)
            count = _write_jsonl(saved_path, rows, upload_id)
            notes.append("JSON was normalized into JSONL for the ingestion pipeline.")
        else:
            count = _copy_jsonl(saved_path, content)
            notes.append("JSONL was stored directly for ingestion.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id: int | None = None
    suggested_job = {"type": "ingest", "params": {"input_dir": str(upload_dir)}}
    if run:
        created = jobs.create(JobCreateRequest(type="ingest", params=suggested_job["params"]))
        job_id = created.id
        notes.append("An ingest job was queued for this upload.")

    return ImportUploadResponse(
        upload_id=upload_id,
        filename=filename,
        detected_format=extension.lstrip("."),
        input_dir=str(upload_dir),
        saved_path=str(saved_path),
        article_count_preview=count,
        job_id=job_id,
        suggested_job=suggested_job,
        notes=notes,
    )


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Uploaded file must be UTF-8 encoded") from exc


def _csv_rows(content: bytes) -> list[dict[str, Any]]:
    text = _decode(content)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file must include a header row")
    return [dict(row) for row in reader if any((value or "").strip() for value in row.values())]


def _json_rows(content: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(_decode(content))
    except json.JSONDecodeError as exc:
        raise ValueError("JSON file is not valid") from exc
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("articles"), list):
        rows = payload["articles"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ValueError("JSON must be an object, an array, or an object with an articles array")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Every JSON article item must be an object")
    return [dict(row) for row in rows]


def _copy_jsonl(path: Path, content: bytes) -> int:
    text = _decode(content)
    rows = [line for line in text.splitlines() if line.strip()]
    for index, line in enumerate(rows, start=1):
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSONL line {index} is not valid JSON") from exc
    path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return len(rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]], upload_id: str) -> int:
    normalized = [_normalize_article(row, upload_id, index) for index, row in enumerate(rows, start=1)]
    with path.open("w", encoding="utf-8") as output:
        for row in normalized:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(normalized)


def _normalize_article(row: dict[str, Any], upload_id: str, index: int) -> dict[str, Any]:
    content = _first(row, "content", "content_clean", "body", "text", "description", "summary")
    if not content:
        content = " ".join(str(value) for value in row.values() if value not in (None, ""))
    title = _first(row, "title", "headline", "name") or str(content)[:80] or f"Uploaded article {index}"
    source = _first(row, "source", "publisher", "site", "media") or "uploaded"
    article_id = _first(row, "article_id", "id", "uuid") or f"upload-{upload_id}-{index}"
    url = _first(row, "url", "link", "canonical_url") or f"https://uploaded.local/{upload_id}/{index}"
    tags = row.get("tags") or row.get("keywords") or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.replace(";", ",").split(",") if item.strip()]

    # 保留 pipeline 需要的核心欄位，其他原始欄位放入 metadata 方便追蹤。
    return {
        "article_id": str(article_id),
        "url": str(url),
        "source": str(source),
        "source_name": str(_first(row, "source_name", "publisher_name") or source),
        "title": str(title),
        "content": str(content),
        "publish_date": str(_first(row, "publish_date", "published_at", "date", "published") or ""),
        "category": str(_first(row, "category", "section", "topic") or "uploaded"),
        "category_name": str(_first(row, "category_name", "section_name") or _first(row, "category", "section", "topic") or "Uploaded"),
        "author": str(_first(row, "author", "byline") or ""),
        "tags": tags,
        "image_url": str(_first(row, "image_url", "image", "thumbnail") or ""),
        "metadata": row,
    }


def _first(row: dict[str, Any], *keys: str) -> Any:
    lowered = {key.lower(): value for key, value in row.items()}
    for key in keys:
        value = row.get(key, lowered.get(key.lower()))
        if value not in (None, ""):
            return value
    return None
