from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import get_jobs
from app.schemas.jobs import JobCreateRequest, JobLogResponse, JobRecord
from app.services.jobs import JobService

router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobRecord, status_code=201)
def create_job(request: JobCreateRequest, service: JobService = Depends(get_jobs)) -> JobRecord:
    return service.create(request)


@router.get("/jobs", response_model=list[JobRecord])
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    service: JobService = Depends(get_jobs),
) -> list[JobRecord]:
    return service.list(limit=limit)


@router.get("/jobs/{job_id}", response_model=JobRecord)
def get_job(job_id: int, service: JobService = Depends(get_jobs)) -> JobRecord:
    job = service.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/logs", response_model=JobLogResponse)
def get_job_logs(job_id: int, service: JobService = Depends(get_jobs)) -> JobLogResponse:
    if not service.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return JobLogResponse(id=job_id, content=service.logs(job_id))
