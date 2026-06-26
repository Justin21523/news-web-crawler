from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.api.v1.deps import get_analysis
from app.schemas.analysis import (
    AnalysisCategoryResponse,
    AnalysisDashboardResponse,
    AnalysisKeywordEntityResponse,
    AnalysisOverviewResponse,
    AnalysisReport,
    AnalysisSourceResponse,
    AnalysisTrendResponse,
    BusinessInsightResponse,
    DataQualityIssueListResponse,
    DataQualityResponse,
    IRHealthResponse,
    LiveSummaryResponse,
    PipelineStatusResponse,
)
from app.services.analysis import AnalysisService

router = APIRouter(tags=["analysis"])


@router.get("/data-quality", response_model=DataQualityResponse)
def data_quality(service: AnalysisService = Depends(get_analysis)) -> DataQualityResponse:
    return service.data_quality()


@router.get("/data-quality/issues", response_model=DataQualityIssueListResponse)
def data_quality_issues(
    issue_type: str | None = None,
    severity: str | None = Query(None, pattern="^(info|warning|danger)$"),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> DataQualityIssueListResponse:
    return service.data_quality_issues(
        issue_type=issue_type,
        severity=severity,
        source=source,
        category=category,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/data-quality/export")
def data_quality_export(
    format: str = Query("json", pattern="^(json|csv|markdown)$"),
    issue_type: str | None = None,
    severity: str | None = Query(None, pattern="^(info|warning|danger)$"),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    service: AnalysisService = Depends(get_analysis),
) -> Response:
    content, media_type, filename = service.export_quality_report(
        fmt=format,
        issue_type=issue_type,
        severity=severity,
        source=source,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
def pipeline_status(service: AnalysisService = Depends(get_analysis)) -> PipelineStatusResponse:
    return service.pipeline_status()


@router.get("/analysis/overview", response_model=AnalysisOverviewResponse)
def analysis_overview(service: AnalysisService = Depends(get_analysis)) -> AnalysisOverviewResponse:
    return service.overview()


@router.get("/analysis/dashboard", response_model=AnalysisDashboardResponse)
def analysis_dashboard(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisDashboardResponse:
    return service.dashboard(source, category, date_from, date_to, limit)


@router.get("/analysis/trends", response_model=AnalysisTrendResponse)
def analysis_trends(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisTrendResponse:
    return service.trends(source, category, date_from, date_to, limit)


@router.get("/analysis/sources", response_model=AnalysisSourceResponse)
def analysis_sources(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisSourceResponse:
    return service.sources(source, category, date_from, date_to, limit)


@router.get("/analysis/categories", response_model=AnalysisCategoryResponse)
def analysis_categories(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisCategoryResponse:
    return service.categories(source, category, date_from, date_to, limit)


@router.get("/analysis/keywords-entities", response_model=AnalysisKeywordEntityResponse)
def analysis_keywords_entities(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisKeywordEntityResponse:
    return service.keywords_entities(source, category, date_from, date_to, limit)


@router.get("/analysis/business-insights", response_model=BusinessInsightResponse)
def analysis_business_insights(
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> BusinessInsightResponse:
    return service.business_insights(source, category, date_from, date_to, limit)


@router.get("/analysis/live-summary", response_model=LiveSummaryResponse)
def analysis_live_summary(
    query: str | None = None,
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis),
) -> LiveSummaryResponse:
    return service.live_summary(query, source, category, date_from, date_to, limit)


@router.get("/analysis/export")
def analysis_export(
    section: str = Query("overview", pattern="^(overview|trends|sources|categories|keywords_entities|business)$"),
    format: str = Query("json", pattern="^(json|csv|markdown)$"),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    service: AnalysisService = Depends(get_analysis),
) -> Response:
    content, media_type, filename = service.export_analysis(section, format, source, category, date_from, date_to)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/analysis/collocations", response_model=AnalysisReport)
def collocations(
    limit: int = Query(50, ge=1, le=200),
    service: AnalysisService = Depends(get_analysis),
) -> AnalysisReport:
    return service.collocations(limit=limit)


@router.get("/analysis/ir", response_model=IRHealthResponse)
def ir_health(service: AnalysisService = Depends(get_analysis)) -> IRHealthResponse:
    return service.ir_health()


@router.get("/analysis/topics", response_model=AnalysisReport)
def topics(service: AnalysisService = Depends(get_analysis)) -> AnalysisReport:
    return service.report("text_mining")


@router.get("/analysis/clusters", response_model=AnalysisReport)
def clusters(service: AnalysisService = Depends(get_analysis)) -> AnalysisReport:
    return service.report("clustering")


@router.get("/analysis/sentiment", response_model=AnalysisReport)
def sentiment(service: AnalysisService = Depends(get_analysis)) -> AnalysisReport:
    return service.report("sentiment")


@router.get("/analysis/time-series", response_model=AnalysisReport)
def time_series(service: AnalysisService = Depends(get_analysis)) -> AnalysisReport:
    return service.report("time_series")


@router.get("/analysis/{name}", response_model=AnalysisReport)
def analysis_report(name: str, service: AnalysisService = Depends(get_analysis)) -> AnalysisReport:
    return service.report(name)
