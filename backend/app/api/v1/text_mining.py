from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.schemas.text_mining import (
    AssignmentListResponse,
    AssignmentRunResponse,
    BurstTrendResponse,
    ClusterResponse,
    CollocationResponse,
    CooccurrenceResponse,
    EntityMiningResponse,
    NetworkResponse,
    NgramResponse,
    RelationshipMiningResponse,
    SimilarityResponse,
    TextMiningOverviewResponse,
    TfidfResponse,
    TopicModelResponse,
)
from app.services.text_mining import TextMiningService

router = APIRouter(tags=["text-mining"])


def _service() -> TextMiningService:
    return TextMiningService()


@router.get("/text-mining/overview", response_model=TextMiningOverviewResponse)
def overview(source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().overview(source, category, date_from, date_to, limit)


@router.get("/text-mining/tfidf", response_model=TfidfResponse)
def tfidf(source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().tfidf(source, category, date_from, date_to, limit)


@router.get("/text-mining/ngrams", response_model=NgramResponse)
def ngrams(n: int = Query(2, ge=1, le=3), source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().ngrams(n, source, category, date_from, date_to, limit)


@router.get("/text-mining/topics", response_model=TopicModelResponse)
def topics(method: str = Query("nmf", pattern="^(nmf|lda)$"), n_topics: int = Query(5, ge=2, le=20), source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().topics(method, n_topics, source, category, date_from, date_to, limit)


@router.get("/text-mining/clusters", response_model=ClusterResponse)
def clusters(method: str = Query("kmeans", pattern="^(kmeans|hierarchical)$"), n_clusters: int = Query(5, ge=2, le=20), source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().clusters(method, n_clusters, source, category, date_from, date_to, limit)


@router.get("/text-mining/similarity", response_model=SimilarityResponse)
def similarity(query: str | None = None, article_id: str | None = None, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().similarity(query, article_id, source, category, date_from, date_to, limit)


@router.get("/text-mining/network", response_model=NetworkResponse)
def network(type: str = Query("keyword", pattern="^(keyword|entity)$"), source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().network(type, source, category, date_from, date_to, limit)


@router.get("/text-mining/collocations", response_model=CollocationResponse)
def collocations(
    metric: str = Query("npmi", pattern="^(frequency|pmi|ppmi|npmi|log_likelihood|dice|t_score)$"),
    level: str = Query("sentence", pattern="^(window|sentence|document)$"),
    ngram_type: str = Query("bigram", pattern="^(bigram|trigram)$"),
    window_size: int = Query(5, ge=2, le=10),
    min_freq: int = Query(2, ge=1, le=50),
    top_k: int = Query(50, ge=10, le=200),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
):
    return _service().collocations(metric, level, ngram_type, window_size, min_freq, top_k, source, category, date_from, date_to, limit)


@router.get("/text-mining/co-occurrence", response_model=CooccurrenceResponse)
def co_occurrence(
    kind: str = Query("keyword", pattern="^(keyword|entity)$"),
    level: str = Query("document", pattern="^(window|sentence|document)$"),
    weight_metric: str = Query("npmi", pattern="^(count|pmi|npmi|jaccard)$"),
    min_weight: float = Query(0.0, ge=-1.0, le=1000.0),
    max_nodes: int = Query(80, ge=10, le=160),
    focus: str | None = None,
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
):
    return _service().co_occurrence(kind, level, weight_metric, min_weight, max_nodes, focus, source, category, date_from, date_to, limit)


@router.get("/text-mining/relationships", response_model=RelationshipMiningResponse)
def relationships(source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, entity_type: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().relationships(source, category, date_from, date_to, entity_type, limit)


@router.get("/text-mining/bursts", response_model=BurstTrendResponse)
def bursts(
    recent_window_days: int = Query(7, ge=1, le=30),
    baseline_window_days: int = Query(30, ge=2, le=120),
    min_count: int = Query(3, ge=1, le=50),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
):
    return _service().bursts(recent_window_days, baseline_window_days, min_count, source, category, date_from, date_to, limit)


@router.get("/text-mining/entities", response_model=EntityMiningResponse)
def entities(source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, entity_type: str | None = None, entity: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return _service().entities(source, category, date_from, date_to, entity_type, entity, limit)


@router.post("/text-mining/assignments", response_model=AssignmentRunResponse)
def persist_assignments(
    assignment_type: str = Query("both", pattern="^(topic|cluster|both)$"),
    topic_method: str = Query("nmf", pattern="^(nmf|lda)$"),
    cluster_method: str = Query("kmeans", pattern="^(kmeans|hierarchical)$"),
    n_topics: int = Query(5, ge=2, le=20),
    n_clusters: int = Query(5, ge=2, le=20),
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
):
    return _service().persist_assignments(assignment_type, topic_method, cluster_method, n_topics, n_clusters, source, category, date_from, date_to, limit)


@router.get("/text-mining/assignments/latest", response_model=AssignmentListResponse)
def latest_assignments(limit: int = Query(200, ge=1, le=1000)):
    return _service().latest_assignments(limit)


@router.get("/text-mining/assignments/articles/{article_id}", response_model=AssignmentListResponse)
def article_assignments(article_id: str):
    return _service().article_assignments(article_id)


@router.get("/text-mining/export")
def export(section: str = Query("overview", pattern="^(overview|tfidf|ngrams|topics|clusters|network|entities|collocations|co_occurrence|relationships|bursts)$"), format: str = Query("json", pattern="^(json|csv|markdown)$"), source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = Query(500, ge=1, le=2000)) -> Response:
    content, media_type, filename = _service().export(section, format, source=source, category=category, date_from=date_from, date_to=date_to, limit=limit)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
