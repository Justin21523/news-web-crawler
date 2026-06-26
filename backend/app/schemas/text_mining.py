from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TextMiningStatus = Literal["ready", "insufficient_data", "dependency_missing", "error"]


class TextMiningBaseResponse(BaseModel):
    status: TextMiningStatus = "ready"
    total_documents: int = 0
    notes: list[str] = Field(default_factory=list)


class TextMiningOverviewResponse(TextMiningBaseResponse):
    top_keywords: list[dict[str, Any]] = Field(default_factory=list)
    top_ngrams: list[dict[str, Any]] = Field(default_factory=list)
    top_entities: list[dict[str, Any]] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)


class TfidfResponse(TextMiningBaseResponse):
    vocabulary_size: int = 0
    top_terms: list[dict[str, Any]] = Field(default_factory=list)
    document_terms: list[dict[str, Any]] = Field(default_factory=list)


class NgramResponse(TextMiningBaseResponse):
    n: int = 1
    ngrams: list[dict[str, Any]] = Field(default_factory=list)
    by_source: list[dict[str, Any]] = Field(default_factory=list)
    by_category: list[dict[str, Any]] = Field(default_factory=list)


class TopicModelResponse(TextMiningBaseResponse):
    method: str = "nmf"
    topics: list[dict[str, Any]] = Field(default_factory=list)


class ClusterResponse(TextMiningBaseResponse):
    method: str = "kmeans"
    metrics: dict[str, Any] = Field(default_factory=dict)
    clusters: list[dict[str, Any]] = Field(default_factory=list)


class SimilarityResponse(TextMiningBaseResponse):
    query: str | None = None
    article_id: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)


class NetworkResponse(TextMiningBaseResponse):
    type: Literal["keyword", "entity"] = "keyword"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class CollocationResponse(TextMiningBaseResponse):
    metric: str = "npmi"
    level: str = "sentence"
    ngram_type: str = "bigram"
    window_size: int = 5
    collocations: list[dict[str, Any]] = Field(default_factory=list)
    heatmap: list[dict[str, Any]] = Field(default_factory=list)
    source_matrix: list[dict[str, Any]] = Field(default_factory=list)
    category_matrix: list[dict[str, Any]] = Field(default_factory=list)
    trend: list[dict[str, Any]] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)


class CooccurrenceResponse(TextMiningBaseResponse):
    kind: Literal["keyword", "entity"] = "keyword"
    level: str = "document"
    weight_metric: str = "npmi"
    metrics_degraded: bool = False
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    communities: list[dict[str, Any]] = Field(default_factory=list)
    ego_network: list[dict[str, Any]] = Field(default_factory=list)
    article_matches: list[dict[str, Any]] = Field(default_factory=list)


class RelationshipMiningResponse(TextMiningBaseResponse):
    active_entity_source: str = "fallback"
    entity_frequency: list[dict[str, Any]] = Field(default_factory=list)
    share_of_voice: list[dict[str, Any]] = Field(default_factory=list)
    entity_network_nodes: list[dict[str, Any]] = Field(default_factory=list)
    entity_network_edges: list[dict[str, Any]] = Field(default_factory=list)
    entity_source_matrix: list[dict[str, Any]] = Field(default_factory=list)
    entity_category_matrix: list[dict[str, Any]] = Field(default_factory=list)
    entity_topic_links: list[dict[str, Any]] = Field(default_factory=list)
    entity_keyword_links: list[dict[str, Any]] = Field(default_factory=list)
    entity_trend_calendar: list[dict[str, Any]] = Field(default_factory=list)
    risk_summary: list[dict[str, Any]] = Field(default_factory=list)


class BurstTrendResponse(TextMiningBaseResponse):
    recent_window_days: int = 7
    baseline_window_days: int = 30
    rising_terms: list[dict[str, Any]] = Field(default_factory=list)
    declining_terms: list[dict[str, Any]] = Field(default_factory=list)
    burst_terms: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_timeline: list[dict[str, Any]] = Field(default_factory=list)
    calendar: list[dict[str, Any]] = Field(default_factory=list)
    source_bursts: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle: list[dict[str, Any]] = Field(default_factory=list)


class EntityMiningResponse(TextMiningBaseResponse):
    active_entity_source: str = "fallback"
    active_run_id: str | None = None
    provider_status: list[dict[str, Any]] = Field(default_factory=list)
    entity_frequency: list[dict[str, Any]] = Field(default_factory=list)
    entity_type_distribution: list[dict[str, Any]] = Field(default_factory=list)
    entity_trend: list[dict[str, Any]] = Field(default_factory=list)
    entity_source_matrix: list[dict[str, Any]] = Field(default_factory=list)
    entity_category_matrix: list[dict[str, Any]] = Field(default_factory=list)
    cooccurrence_nodes: list[dict[str, Any]] = Field(default_factory=list)
    cooccurrence_edges: list[dict[str, Any]] = Field(default_factory=list)
    representative_articles: list[dict[str, Any]] = Field(default_factory=list)


class AssignmentRunResponse(TextMiningBaseResponse):
    run_id: str = ""
    assignment_type: str = "both"
    method: str = ""
    assignment_counts: dict[str, int] = Field(default_factory=dict)
    labels: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    created_at: str | None = None


class AssignmentListResponse(TextMiningBaseResponse):
    runs: list[dict[str, Any]] = Field(default_factory=list)
    assignments: list[dict[str, Any]] = Field(default_factory=list)
