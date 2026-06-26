from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.analysis import DataQualityIssue


class ArticleListItem(BaseModel):
    article_id: str
    title: str
    source: str
    source_name: str | None = None
    publish_date: str | None = None
    category: str | None = None
    category_name: str | None = None
    status: str | None = None
    snippet: str = ""
    image_url: str | None = None
    relevance_score: float | None = None
    char_count: int = 0
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)


class ArticleDetail(ArticleListItem):
    url: str
    author: str | None = None
    content_clean: str = ""
    tags: list[str] = Field(default_factory=list)
    crawled_at: str | None = None
    cleaned_at: str | None = None
    char_count: int = 0
    word_count: int = 0
    nlp: dict[str, Any] | None = None
    quality_issues: list[DataQualityIssue] = Field(default_factory=list)
    assignments: list[dict[str, Any]] = Field(default_factory=list)


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    page_size: int


class SummaryResponse(BaseModel):
    article_id: str
    method: str
    sentences: list[str]
    compression_ratio: float
    provider: str = "extractive"
    notes: list[str] = Field(default_factory=list)


class FacetCount(BaseModel):
    value: str
    count: int


class FacetsResponse(BaseModel):
    sources: list[str]
    categories: list[str]
    statuses: list[str]
    source_counts: list[FacetCount] = Field(default_factory=list)
    category_counts: list[FacetCount] = Field(default_factory=list)
    status_counts: list[FacetCount] = Field(default_factory=list)
    issue_type_counts: list[FacetCount] = Field(default_factory=list)
    keyword_counts: list[FacetCount] = Field(default_factory=list)
    entity_counts: list[FacetCount] = Field(default_factory=list)
    topic_counts: list[FacetCount] = Field(default_factory=list)
    cluster_counts: list[FacetCount] = Field(default_factory=list)
    length_buckets: list[FacetCount] = Field(default_factory=list)
    date_range: list[str | None] = Field(default_factory=lambda: [None, None])


class RelatedArticle(BaseModel):
    article_id: str
    title: str
    source: str = ""
    category: str = ""
    score: float = 0.0
    snippet: str = ""
