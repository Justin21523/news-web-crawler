from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analysis, articles, entity_extraction, imports, jobs, llm, ml, stats, text_mining

api_router = APIRouter()
api_router.include_router(stats.router)
api_router.include_router(articles.router)
api_router.include_router(jobs.router)
api_router.include_router(imports.router)
api_router.include_router(llm.router)
api_router.include_router(analysis.router)
api_router.include_router(text_mining.router)
api_router.include_router(entity_extraction.router)
api_router.include_router(ml.router)
