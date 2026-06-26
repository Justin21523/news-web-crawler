from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DataQualityMetric(BaseModel):
    key: str
    label: str
    value: int | float
    total: int | float | None = None
    percent: float | None = None
    severity: Literal["good", "warning", "danger", "neutral"] = "neutral"


class DataQualityIssue(BaseModel):
    article_id: str
    title: str = ""
    source: str = ""
    category: str = ""
    category_name: str = ""
    publish_date: str | None = None
    char_count: int = 0
    issue_type: str
    severity: Literal["info", "warning", "danger"]
    message: str
    suggested_fix: str


class DataQualityIssueListResponse(BaseModel):
    items: list[DataQualityIssue]
    total: int
    page: int
    page_size: int


class DataQualityResponse(BaseModel):
    total_articles: int
    completeness_score: float
    quality_score: float = 0.0
    metrics: list[DataQualityMetric]
    issues: list[DataQualityIssue] = Field(default_factory=list)
    issue_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    missing_fields: dict[str, int] = Field(default_factory=dict)
    source_coverage: dict[str, int] = Field(default_factory=dict)
    category_coverage: dict[str, int] = Field(default_factory=dict)
    date_coverage: list[dict[str, Any]] = Field(default_factory=list)
    length_distribution: list[dict[str, Any]] = Field(default_factory=list)
    date_range: list[str | None] = Field(default_factory=lambda: [None, None])
    recommendations: list[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    key: str
    label: str
    status: Literal["not_started", "ready", "running", "complete", "warning", "failed"]
    count: int = 0
    total: int = 0
    detail: str = ""


class PipelineStatusResponse(BaseModel):
    steps: list[PipelineStep]
    current_step: str
    completion_percent: float


class AnalysisReport(BaseModel):
    name: str
    status: Literal["ready", "missing", "insufficient_data", "error"]
    summary: str
    updated_at: str | None = None
    data: Any = None


class AnalysisOverviewResponse(BaseModel):
    reports: list[AnalysisReport]
    nlp_documents: int
    analyzed_documents: int
    recommendations: list[str] = Field(default_factory=list)


class AnalysisDashboardResponse(BaseModel):
    kpis: dict[str, Any] = Field(default_factory=dict)
    source_distribution: list[dict[str, Any]] = Field(default_factory=list)
    category_distribution: list[dict[str, Any]] = Field(default_factory=list)
    daily_volume: list[dict[str, Any]] = Field(default_factory=list)
    top_keywords: list[dict[str, Any]] = Field(default_factory=list)
    top_entities: list[dict[str, Any]] = Field(default_factory=list)
    sentiment_summary: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AnalysisTrendResponse(BaseModel):
    daily_volume: list[dict[str, Any]] = Field(default_factory=list)
    category_trend: list[dict[str, Any]] = Field(default_factory=list)
    source_trend: list[dict[str, Any]] = Field(default_factory=list)
    keyword_trend: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AnalysisSourceResponse(BaseModel):
    source_volume: list[dict[str, Any]] = Field(default_factory=list)
    source_category_matrix: list[dict[str, Any]] = Field(default_factory=list)
    source_keyword_profile: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisCategoryResponse(BaseModel):
    category_distribution: list[dict[str, Any]] = Field(default_factory=list)
    category_source_mix: list[dict[str, Any]] = Field(default_factory=list)
    category_keywords: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisKeywordEntityResponse(BaseModel):
    top_keywords: list[dict[str, Any]] = Field(default_factory=list)
    keyword_by_source: list[dict[str, Any]] = Field(default_factory=list)
    keyword_by_category: list[dict[str, Any]] = Field(default_factory=list)
    top_entities: list[dict[str, Any]] = Field(default_factory=list)
    entity_by_source: list[dict[str, Any]] = Field(default_factory=list)
    entity_by_category: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BusinessInsightResponse(BaseModel):
    cards: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class LiveSummaryResponse(BaseModel):
    status: Literal["ready", "insufficient_data", "error"] = "ready"
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)
    top_terms: list[dict[str, Any]] = Field(default_factory=list)
    representative_articles: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    provider: str = "extractive"


class IRHealthResponse(BaseModel):
    indexed_articles: int
    total_articles: int
    index_coverage_percent: float
    sample_queries: list[dict[str, Any]] = Field(default_factory=list)
