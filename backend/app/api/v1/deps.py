from __future__ import annotations

from fastapi import Request

from app.services.articles import ArticleService
from app.services.analysis import AnalysisService
from app.services.database import Database
from app.services.jobs import JobService
from app.services.stats import StatsService


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_jobs(request: Request) -> JobService:
    return request.app.state.jobs


def get_articles(request: Request) -> ArticleService:
    return ArticleService(request.app.state.db)


def get_stats(request: Request) -> StatsService:
    return StatsService(request.app.state.db, request.app.state.jobs)


def get_analysis(request: Request) -> AnalysisService:
    return AnalysisService(request.app.state.db)
