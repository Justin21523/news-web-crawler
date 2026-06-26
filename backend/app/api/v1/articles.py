from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import get_articles
from app.schemas.articles import ArticleDetail, ArticleListResponse, FacetsResponse, RelatedArticle, SummaryResponse
from app.services.articles import ArticleService

router = APIRouter(tags=["articles"])


@router.get("/articles", response_model=ArticleListResponse)
def list_articles(
    query: str | None = None,
    source: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    search_scope: str = Query("all", pattern="^(all|title|content|entity|keyword)$"),
    ranking: str = Query("recent", pattern="^(recent|fts|tfidf|hybrid)$"),
    sort: str = Query("date_desc", pattern="^(relevance|date_desc|date_asc|length_desc|length_asc)$"),
    entity: str | None = None,
    keyword: str | None = None,
    quality_issue: str | None = None,
    topic: str | None = None,
    cluster: str | None = None,
    min_length: int | None = Query(None, ge=0),
    max_length: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ArticleService = Depends(get_articles),
) -> ArticleListResponse:
    return service.list_articles(
        query=query,
        source=source,
        category=category,
        date_from=date_from,
        date_to=date_to,
        status=status,
        search_scope=search_scope,
        ranking=ranking,
        sort=sort,
        entity=entity,
        keyword=keyword,
        quality_issue=quality_issue,
        topic=topic,
        cluster=cluster,
        min_length=min_length,
        max_length=max_length,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/{article_id}", response_model=ArticleDetail)
def get_article(article_id: str, service: ArticleService = Depends(get_articles)) -> ArticleDetail:
    article = service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/articles/{article_id}/summary", response_model=SummaryResponse)
def summarize_article(
    article_id: str,
    method: str = Query("mmr", pattern="^(mmr|lead_k|extractive)$"),
    k: int = Query(3, ge=1, le=10),
    service: ArticleService = Depends(get_articles),
) -> SummaryResponse:
    summary = service.summarize(article_id, method=method, k=k)
    if not summary:
        raise HTTPException(status_code=404, detail="Article not found")
    return summary


@router.get("/articles/{article_id}/related", response_model=list[RelatedArticle])
def related_articles(
    article_id: str,
    limit: int = Query(8, ge=1, le=20),
    service: ArticleService = Depends(get_articles),
) -> list[RelatedArticle]:
    return service.related(article_id, limit=limit)


@router.get("/facets", response_model=FacetsResponse)
def facets(service: ArticleService = Depends(get_articles)) -> FacetsResponse:
    return service.facets()
