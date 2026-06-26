from __future__ import annotations

import json
from collections import Counter
from typing import Any

from analysis.summarization import Summarizer
from app.services.llm import LLMService

from app.schemas.articles import (
    ArticleDetail,
    FacetCount,
    ArticleListItem,
    ArticleListResponse,
    FacetsResponse,
    RelatedArticle,
    SummaryResponse,
)
from app.services.database import Database, decode_json
from app.services.analysis import AnalysisService
from app.services.entity_utils import entity_values, fallback_entities_from_row


class ArticleService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def list_articles(
        self,
        query: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        search_scope: str = "all",
        ranking: str = "recent",
        sort: str = "date_desc",
        entity: str | None = None,
        keyword: str | None = None,
        quality_issue: str | None = None,
        topic: str | None = None,
        cluster: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ArticleListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        where, params = self._build_filters(source, category, date_from, date_to, status, min_length, max_length, topic, cluster)
        order_by = self._order_by(sort, bool(query))

        if query:
            if search_scope in ("entity", "keyword"):
                like = f"%{query}%"
                field = "n.keywords"
                extra_filter = "" if search_scope == "entity" else f" AND {field} LIKE ?"
                count_sql = f"""
                    SELECT COUNT(*)
                    FROM articles a
                    LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
                    {where}{extra_filter}
                """
                rows_sql = f"""
                    SELECT a.article_id, a.title, a.source, a.source_name, a.publish_date,
                           a.category, a.category_name, a.status, a.content_clean, a.image_url,
                           a.char_count, n.keywords, n.entities, 0.0 AS relevance_score
                    FROM articles a
                    LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
                    {where}{extra_filter}
                    ORDER BY {order_by}
                    LIMIT ? OFFSET ?
                """
                count_params = params if search_scope == "entity" else (*params, like)
                rows_params = (*params, page_size, offset) if search_scope == "entity" else (*params, like, page_size, offset)
            else:
                match = self._fts_query(query, search_scope)
                count_sql = f"""
                    SELECT COUNT(*)
                    FROM articles_fts f
                    JOIN articles a ON a.rowid = f.rowid
                    LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
                    {where} AND articles_fts MATCH ?
                """
                rows_sql = f"""
                    SELECT a.article_id, a.title, a.source, a.source_name, a.publish_date,
                           a.category, a.category_name, a.status, a.content_clean, a.image_url,
                           a.char_count, n.keywords, n.entities, rank AS relevance_score
                    FROM articles_fts f
                    JOIN articles a ON a.rowid = f.rowid
                    LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
                    {where} AND articles_fts MATCH ?
                    ORDER BY {order_by}
                    LIMIT ? OFFSET ?
                """
                count_params = (*params, match)
                rows_params = (*params, match, page_size, offset)
        else:
            count_sql = f"SELECT COUNT(*) FROM articles a {where}"
            rows_sql = f"""
                SELECT a.article_id, a.title, a.source, a.source_name, a.publish_date,
                       a.category, a.category_name, a.status, a.content_clean, a.image_url,
                       a.char_count, n.keywords, n.entities, NULL AS relevance_score
                FROM articles a
                LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
                {where}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            count_params = params
            rows_params = (*params, page_size, offset)

        total_row = self.db.fetch_one(count_sql, count_params)
        rows = [dict(row) for row in self.db.fetch_all(rows_sql, rows_params)]
        if query and search_scope == "entity":
            rows = [row for row in rows if self._contains_entity(row, query)]
        if keyword:
            rows = [row for row in rows if self._contains_keyword(row.get("keywords"), keyword)]
        if entity:
            rows = [row for row in rows if self._contains_entity(row, entity)]
        if quality_issue:
            issue_ids = {issue.article_id for issue in AnalysisService(self.db).data_quality_issues(issue_type=quality_issue, page_size=100).items}
            rows = [row for row in rows if row.get("article_id") in issue_ids]
        total = int(total_row[0] if total_row else 0)
        if keyword or entity or quality_issue:
            total = len(rows)
        return ArticleListResponse(
            items=[self._to_list_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_article(self, article_id: str) -> ArticleDetail | None:
        row = self.db.fetch_one(
            """
            SELECT a.*, n.tokens, n.pos_tags, n.entities, n.keywords, n.keyword_summary,
                   n.tfidf_vector_path, n.embedding_path, n.model_version, n.enriched_at
            FROM articles a
            LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
            WHERE a.article_id = ?
            """,
            (article_id,),
        )
        if not row:
            return None
        data = dict(row)
        nlp = None
        if data.get("tokens") is not None:
            nlp = {
                "tokens": decode_json(data.get("tokens"), []),
                "pos_tags": decode_json(data.get("pos_tags"), []),
                "entities": [list(item) for item in fallback_entities_from_row(data)],
                "keywords": decode_json(data.get("keywords"), []),
                "keyword_summary": data.get("keyword_summary") or "",
                "model_version": data.get("model_version") or "",
                "entity_source": self._entity_source_from_version(data.get("model_version") or ""),
                "entity_run_id": self._entity_run_from_version(data.get("model_version") or ""),
                "enriched_at": data.get("enriched_at") or "",
            }
        item = self._to_list_item(data)
        return ArticleDetail(
            **item.model_dump(),
            url=data.get("url") or "",
            author=data.get("author") or "",
            content_clean=data.get("content_clean") or "",
            tags=decode_json(data.get("tags"), []),
            crawled_at=data.get("crawled_at"),
            cleaned_at=data.get("cleaned_at"),
            word_count=int(data.get("word_count") or 0),
            nlp=nlp,
            quality_issues=AnalysisService(self.db).article_quality_issues(article_id),
            assignments=self._article_assignments(article_id),
        )

    def summarize(self, article_id: str, method: str = "mmr", k: int = 3) -> SummaryResponse | None:
        article = self.get_article(article_id)
        if not article:
            return None
        text = f"{article.title}\n{article.content_clean}"
        notes: list[str] = []
        try:
            llm_summary = LLMService().summarize(
                text,
                instruction=f"請將這篇新聞整理成 {k} 個重點，並保留可供資料分析平台展示的具體資訊。",
                max_tokens=480,
            )
            if llm_summary:
                return SummaryResponse(
                    article_id=article_id,
                    method="llama_cpp",
                    sentences=llm_summary.bullets[:k],
                    compression_ratio=0.0,
                    provider=llm_summary.provider,
                )
        except Exception as exc:
            notes.append(f"llama.cpp fallback: {exc}")
        summarizer = Summarizer()
        if method == "lead_k":
            result = summarizer.lead_k(text, k=k)
        elif method == "extractive":
            result = summarizer.extractive(text, ratio=0.15)
        else:
            result = summarizer.mmr_summary(text, k=k, diversity=0.7)
        return SummaryResponse(
            article_id=article_id,
            method=result.method,
            sentences=result.sentences,
            compression_ratio=result.compression_ratio,
            provider="extractive",
            notes=notes,
        )

    def facets(self) -> FacetsResponse:
        source_counts = self._count_facet("source")
        category_rows = self.db.fetch_all(
            """
            SELECT COALESCE(NULLIF(category_name, ''), NULLIF(category, ''), 'unknown') AS value, COUNT(*) AS count
            FROM articles
            GROUP BY value
            ORDER BY count DESC, value
            """
        )
        status_counts = self._count_facet("status")
        issue_counts = Counter(issue.issue_type for issue in AnalysisService(self.db).data_quality().issues)
        keyword_counts, entity_counts = self._nlp_facets()
        topic_counts = self._assignment_counts("topic")
        cluster_counts = self._assignment_counts("cluster")
        date_row = self.db.fetch_one("SELECT MIN(publish_date), MAX(publish_date) FROM articles WHERE publish_date IS NOT NULL AND trim(publish_date) != ''")
        length_rows = self.db.fetch_all(
            """
            SELECT
              CASE
                WHEN COALESCE(char_count, length(COALESCE(content_clean, ''))) < 300 THEN 'short'
                WHEN COALESCE(char_count, length(COALESCE(content_clean, ''))) < 1000 THEN 'medium'
                ELSE 'long'
              END AS value,
              COUNT(*) AS count
            FROM articles
            GROUP BY value
            ORDER BY count DESC
            """
        )
        return FacetsResponse(
            sources=[item.value for item in source_counts],
            categories=[str(row["value"]) for row in category_rows],
            statuses=[item.value for item in status_counts],
            source_counts=source_counts,
            category_counts=[FacetCount(value=str(row["value"]), count=int(row["count"])) for row in category_rows],
            status_counts=status_counts,
            issue_type_counts=[FacetCount(value=value, count=count) for value, count in issue_counts.most_common()],
            keyword_counts=[FacetCount(value=value, count=count) for value, count in keyword_counts.most_common(40)],
            entity_counts=[FacetCount(value=value, count=count) for value, count in entity_counts.most_common(40)],
            topic_counts=topic_counts,
            cluster_counts=cluster_counts,
            length_buckets=[FacetCount(value=str(row["value"]), count=int(row["count"])) for row in length_rows],
            date_range=[date_row[0], date_row[1]] if date_row else [None, None],
        )

    def related(self, article_id: str, limit: int = 8) -> list[RelatedArticle]:
        try:
            from app.services.text_mining import TextMiningService

            result = TextMiningService(self.db).similarity(article_id=article_id, limit=500)
            rows = result.results[:limit]
        except Exception:
            rows = []
        if not rows:
            article = self.get_article(article_id)
            if not article:
                return []
            rows = [
                {
                    "article_id": row["article_id"],
                    "title": row["title"],
                    "source": row["source"],
                    "category": row["category_label"],
                    "score": 0.0,
                }
                for row in self.db.fetch_all(
                    """
                    SELECT article_id, title, source,
                           COALESCE(NULLIF(category_name, ''), NULLIF(category, ''), 'unknown') AS category_label
                    FROM articles
                    WHERE article_id != ? AND (source = ? OR category_name = ? OR category = ?)
                    ORDER BY COALESCE(publish_date, crawled_at) DESC
                    LIMIT ?
                    """,
                    (article_id, article.source, article.category_name or article.category or "", article.category or "", limit),
                )
            ]
        output = []
        for item in rows[:limit]:
            detail = self.get_article(str(item["article_id"]))
            output.append(
                RelatedArticle(
                    article_id=str(item["article_id"]),
                    title=str(item.get("title") or ""),
                    source=str(item.get("source") or ""),
                    category=str(item.get("category") or ""),
                    score=round(float(item.get("score") or 0), 6),
                    snippet=detail.snippet if detail else "",
                )
            )
        return output

    def _build_filters(
        self,
        source: str | None,
        category: str | None,
        date_from: str | None,
        date_to: str | None,
        status: str | None,
        min_length: int | None = None,
        max_length: int | None = None,
        topic: str | None = None,
        cluster: str | None = None,
    ) -> tuple[str, tuple[str, ...]]:
        clauses = ["1=1"]
        params: list[str] = []
        if source:
            clauses.append("a.source = ?")
            params.append(source)
        if category:
            clauses.append("(a.category = ? OR a.category_name = ?)")
            params.extend([category, category])
        if date_from:
            clauses.append("a.publish_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("a.publish_date <= ?")
            params.append(date_to)
        if status:
            clauses.append("a.status = ?")
            params.append(status)
        if min_length is not None:
            clauses.append("COALESCE(a.char_count, length(COALESCE(a.content_clean, ''))) >= ?")
            params.append(str(min_length))
        if max_length is not None:
            clauses.append("COALESCE(a.char_count, length(COALESCE(a.content_clean, ''))) <= ?")
            params.append(str(max_length))
        if topic:
            clauses.append(
                """
                EXISTS (
                  SELECT 1 FROM text_mining_assignments tma
                  WHERE tma.article_id = a.article_id
                    AND tma.assignment_type = 'topic'
                    AND tma.label = ?
                    AND tma.run_id = (
                      SELECT run_id FROM text_mining_runs
                      WHERE status = 'ready'
                      ORDER BY datetime(created_at) DESC
                      LIMIT 1
                    )
                )
                """
            )
            params.append(topic)
        if cluster:
            clauses.append(
                """
                EXISTS (
                  SELECT 1 FROM text_mining_assignments tma
                  WHERE tma.article_id = a.article_id
                    AND tma.assignment_type = 'cluster'
                    AND tma.label = ?
                    AND tma.run_id = (
                      SELECT run_id FROM text_mining_runs
                      WHERE status = 'ready'
                      ORDER BY datetime(created_at) DESC
                      LIMIT 1
                    )
                )
                """
            )
            params.append(cluster)
        return f"WHERE {' AND '.join(clauses)}", tuple(params)

    def _to_list_item(self, data: dict) -> ArticleListItem:
        content = data.get("content_clean") or ""
        snippet = content[:180] + ("..." if len(content) > 180 else "")
        return ArticleListItem(
            article_id=data.get("article_id") or "",
            title=data.get("title") or "",
            source=data.get("source") or "",
            source_name=data.get("source_name") or "",
            publish_date=data.get("publish_date"),
            category=data.get("category") or "",
            category_name=data.get("category_name") or "",
            status=data.get("status") or "",
            snippet=snippet,
            image_url=data.get("image_url") or "",
            relevance_score=float(data["relevance_score"]) if data.get("relevance_score") is not None else None,
            char_count=int(data.get("char_count") or len(content)),
            keywords=self._keyword_values(data.get("keywords"))[:8],
            entities=self._entity_values(data)[:8],
        )

    def _order_by(self, sort: str, has_query: bool) -> str:
        if sort == "length_desc":
            return "COALESCE(a.char_count, length(COALESCE(a.content_clean, ''))) DESC, a.article_id DESC"
        if sort == "length_asc":
            return "COALESCE(a.char_count, length(COALESCE(a.content_clean, ''))) ASC, a.article_id DESC"
        if sort == "date_asc":
            return "COALESCE(a.publish_date, a.crawled_at) ASC, a.article_id ASC"
        if sort == "relevance" and has_query:
            return "rank, COALESCE(a.publish_date, a.crawled_at) DESC"
        return "COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC"

    def _fts_query(self, query: str, scope: str) -> str:
        safe = query.replace('"', '""').strip()
        if not safe:
            return '""'
        phrase = f'"{safe}"'
        if scope == "title":
            return f"title_clean:{phrase}"
        if scope == "content":
            return f"content_clean:{phrase}"
        return phrase

    def _json(self, value: Any, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return fallback

    def _keyword_values(self, value: Any) -> list[str]:
        output = []
        for item in self._json(value, []):
            if isinstance(item, (list, tuple)) and item:
                output.append(str(item[0]))
            elif isinstance(item, dict) and item.get("term"):
                output.append(str(item["term"]))
            elif isinstance(item, str):
                output.append(item)
        return output

    def _entity_values(self, value: Any) -> list[str]:
        if isinstance(value, dict):
            return entity_values(value)
        return entity_values({"entities": value})

    def _contains_keyword(self, value: Any, keyword: str) -> bool:
        target = keyword.lower()
        return any(target in item.lower() for item in self._keyword_values(value))

    def _contains_entity(self, value: Any, entity: str) -> bool:
        target = entity.lower()
        return any(target in item.lower() for item in self._entity_values(value))

    def _entity_source_from_version(self, value: str) -> str:
        if "|ner:" not in value:
            return "fallback"
        return value.split("|ner:", 1)[1].split("|", 1)[0]

    def _entity_run_from_version(self, value: str) -> str:
        if "|entity-run:" not in value:
            return ""
        return value.split("|entity-run:", 1)[1].split("|", 1)[0]

    def _count_facet(self, column: str) -> list[FacetCount]:
        rows = self.db.fetch_all(
            f"""
            SELECT COALESCE(NULLIF({column}, ''), 'unknown') AS value, COUNT(*) AS count
            FROM articles
            GROUP BY value
            ORDER BY count DESC, value
            """
        )
        return [FacetCount(value=str(row["value"]), count=int(row["count"])) for row in rows]

    def _nlp_facets(self) -> tuple[Counter[str], Counter[str]]:
        keyword_counts: Counter[str] = Counter()
        entity_counts: Counter[str] = Counter()
        for row in self.db.fetch_all(
            """
            SELECT n.keywords, n.entities, n.tokens, a.title, a.content_clean
            FROM nlp_outputs n
            LEFT JOIN articles a ON a.article_id = n.article_id
            """
        ):
            keyword_counts.update(self._keyword_values(row["keywords"])[:10])
            entity_counts.update(self._entity_values(dict(row))[:10])
        return keyword_counts, entity_counts

    def _assignment_counts(self, assignment_type: str) -> list[FacetCount]:
        rows = self.db.fetch_all(
            """
            SELECT label AS value, COUNT(DISTINCT article_id) AS count
            FROM text_mining_assignments
            WHERE assignment_type = ?
              AND run_id = (
                SELECT run_id FROM text_mining_runs
                WHERE status = 'ready'
                ORDER BY datetime(created_at) DESC
                LIMIT 1
              )
            GROUP BY label
            ORDER BY count DESC, label
            """,
            (assignment_type,),
        )
        return [FacetCount(value=str(row["value"]), count=int(row["count"])) for row in rows]

    def _article_assignments(self, article_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetch_all(
            """
            SELECT assignment_type, label, score, terms_json, created_at
            FROM text_mining_assignments
            WHERE article_id = ?
              AND run_id = (
                SELECT run_id FROM text_mining_runs
                WHERE status = 'ready'
                ORDER BY datetime(created_at) DESC
                LIMIT 1
              )
            ORDER BY assignment_type, score DESC
            """,
            (article_id,),
        )
        output = []
        for row in rows:
            item = dict(row)
            item["terms"] = decode_json(item.pop("terms_json", None), [])
            output.append(item)
        return output
