from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from collections import Counter

from analysis.summarization import Summarizer
from app.services.llm import LLMService
from app.core.config import Settings, get_settings
from app.schemas.analysis import (
    AnalysisCategoryResponse,
    AnalysisDashboardResponse,
    AnalysisKeywordEntityResponse,
    AnalysisOverviewResponse,
    AnalysisReport,
    AnalysisSourceResponse,
    AnalysisTrendResponse,
    BusinessInsightResponse,
    DataQualityIssue,
    DataQualityIssueListResponse,
    DataQualityMetric,
    DataQualityResponse,
    IRHealthResponse,
    LiveSummaryResponse,
    PipelineStatusResponse,
    PipelineStep,
)
from app.services.database import Database
from app.services.entity_utils import entity_count_rows, entity_profile_rows, fallback_entity_note


class AnalysisService:
    report_files = {
        "text_mining": "text_mining.json",
        "clustering": "clustering.json",
        "sentiment": "sentiment_report.json",
        "time_series": "time_series.json",
        "summaries": "summaries.json",
    }

    def __init__(self, db: Database | None = None, settings: Settings | None = None):
        self.db = db or Database()
        self.settings = settings or get_settings()

    def data_quality(self) -> DataQualityResponse:
        total = self._count("SELECT COUNT(*) FROM articles")
        enriched = self._count("SELECT COUNT(*) FROM nlp_outputs")
        cleaned = self._count("SELECT COUNT(*) FROM articles WHERE status='cleaned'")
        duplicate_hashes = self._count(
            "SELECT COUNT(*) FROM (SELECT dedup_hash FROM articles WHERE dedup_hash != '' GROUP BY dedup_hash HAVING COUNT(*) > 1)"
        )
        duplicate_titles = self._count(
            "SELECT COUNT(*) FROM (SELECT lower(trim(title_clean)) AS key FROM articles WHERE title_clean IS NOT NULL AND trim(title_clean) != '' GROUP BY key HAVING COUNT(*) > 1)"
        )
        invalid_urls = self._count(
            "SELECT COUNT(*) FROM articles WHERE url IS NULL OR trim(url) = '' OR lower(url) NOT LIKE 'http%'"
        )
        short_content = self._count(
            "SELECT COUNT(*) FROM articles WHERE COALESCE(char_count, length(COALESCE(content_clean, ''))) < 60"
        )
        missing_fields = {
            "title": self._count("SELECT COUNT(*) FROM articles WHERE title IS NULL OR trim(title) = ''"),
            "content": self._count("SELECT COUNT(*) FROM articles WHERE content_clean IS NULL OR trim(content_clean) = ''"),
            "publish_date": self._count("SELECT COUNT(*) FROM articles WHERE publish_date IS NULL OR trim(publish_date) = ''"),
            "source": self._count("SELECT COUNT(*) FROM articles WHERE source IS NULL OR trim(source) = ''"),
            "url": self._count("SELECT COUNT(*) FROM articles WHERE url IS NULL OR trim(url) = ''"),
        }
        present_required = sum(total - value for value in missing_fields.values())
        required_total = max(total * len(missing_fields), 1)
        field_score = present_required / required_total * 100
        nlp_score = (enriched / total * 100) if total else 0
        completeness = round(field_score * 0.7 + nlp_score * 0.3, 1) if total else 0.0
        issue_penalty = (
            sum(missing_fields.values()) * 8
            + invalid_urls * 6
            + short_content * 4
            + (duplicate_hashes + duplicate_titles) * 5
        )
        quality_score = round(max(0, 100 - (issue_penalty / max(total, 1))), 1) if total else 0.0

        source_rows = self.db.fetch_all("SELECT COALESCE(NULLIF(source, ''), 'unknown') AS source, COUNT(*) AS cnt FROM articles GROUP BY source ORDER BY cnt DESC")
        category_rows = self.db.fetch_all(
            """
            SELECT COALESCE(NULLIF(category_name, ''), NULLIF(category, ''), 'unknown') AS category, COUNT(*) AS cnt
            FROM articles
            GROUP BY category
            ORDER BY cnt DESC, category
            """
        )
        date_rows = self.db.fetch_all(
            """
            SELECT substr(publish_date, 1, 10) AS date, COUNT(*) AS count
            FROM articles
            WHERE publish_date IS NOT NULL AND trim(publish_date) != ''
            GROUP BY date
            ORDER BY date
            """
        )
        date_row = self.db.fetch_one(
            "SELECT MIN(publish_date), MAX(publish_date) FROM articles WHERE publish_date IS NOT NULL AND trim(publish_date) != ''"
        )
        metrics = [
            self._metric("cleaned", "Cleaned articles", cleaned, total),
            self._metric("enriched", "NLP enriched articles", enriched, total),
            self._metric("missing_dates", "Missing publish dates", missing_fields["publish_date"], total, inverse=True),
            self._metric("invalid_urls", "Invalid URLs", invalid_urls, total, inverse=True),
            self._metric("short_content", "Short content", short_content, total, inverse=True),
            self._metric("duplicates", "Duplicate title/hash groups", duplicate_hashes + duplicate_titles, max(total, 1), inverse=True),
        ]
        all_issues = self._quality_issues(limit=None)
        issues = all_issues[:100]
        issue_counts = Counter(issue.issue_type for issue in all_issues)
        severity_counts = Counter(issue.severity for issue in all_issues)
        recommendations = []
        if total == 0:
            recommendations.append("Run a crawl or ingest job before analysis.")
        if total and enriched < total:
            recommendations.append("Run the NLP job to complete token, entity, and keyword coverage.")
        if missing_fields["publish_date"]:
            recommendations.append("Review parser output for publish_date because time-series analysis depends on it.")
        if duplicate_hashes:
            recommendations.append("Inspect duplicate hash groups before exporting analysis datasets.")
        if invalid_urls:
            recommendations.append("Fix invalid URLs so article drill-down and source verification stay reliable.")
        if short_content:
            recommendations.append("Review short-content articles because parser extraction may be incomplete.")

        return DataQualityResponse(
            total_articles=total,
            completeness_score=completeness,
            quality_score=quality_score,
            metrics=metrics,
            issues=issues,
            issue_counts=dict(issue_counts),
            severity_counts=dict(severity_counts),
            missing_fields=missing_fields,
            source_coverage={row["source"] or "unknown": int(row["cnt"]) for row in source_rows},
            category_coverage={row["category"] or "unknown": int(row["cnt"]) for row in category_rows},
            date_coverage=[{"date": row["date"], "count": int(row["count"])} for row in date_rows],
            length_distribution=self._length_distribution(),
            date_range=[date_row[0], date_row[1]] if date_row else [None, None],
            recommendations=recommendations,
        )

    def data_quality_issues(
        self,
        issue_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        article_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> DataQualityIssueListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        items = self._filtered_quality_issues(
            issue_type=issue_type,
            severity=severity,
            source=source,
            category=category,
            date_from=date_from,
            date_to=date_to,
            article_id=article_id,
        )
        offset = (page - 1) * page_size
        return DataQualityIssueListResponse(
            items=items[offset:offset + page_size],
            total=len(items),
            page=page,
            page_size=page_size,
        )

    def article_quality_issues(self, article_id: str) -> list[DataQualityIssue]:
        return self._filtered_quality_issues(article_id=article_id)

    def export_quality_report(
        self,
        fmt: str = "json",
        issue_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[str, str, str]:
        issues = self._filtered_quality_issues(issue_type, severity, source, category, date_from, date_to)
        quality = self.data_quality()
        fmt = fmt.lower()
        if fmt == "csv":
            from io import StringIO

            out = StringIO()
            writer = csv.DictWriter(
                out,
                fieldnames=[
                    "article_id", "title", "source", "category", "publish_date",
                    "category_name", "char_count", "issue_type", "severity", "message", "suggested_fix",
                ],
            )
            writer.writeheader()
            for issue in issues:
                writer.writerow(issue.model_dump())
            return out.getvalue(), "text/csv; charset=utf-8", "data-quality-report.csv"
        if fmt == "markdown":
            lines = [
                "# Data Quality Report",
                "",
                f"- Total articles: {quality.total_articles}",
                f"- Quality score: {quality.quality_score}",
                f"- Completeness score: {quality.completeness_score}",
                f"- Issues: {len(issues)}",
                "",
                "| Article ID | Issue | Severity | Source | Category | Message | Suggested fix |",
                "|---|---|---|---|---|---|---|",
            ]
            for issue in issues:
                lines.append(
                    f"| {issue.article_id} | {issue.issue_type} | {issue.severity} | "
                    f"{issue.source} | {issue.category_name or issue.category} | "
                    f"{issue.message} | {issue.suggested_fix} |"
                )
            return "\n".join(lines) + "\n", "text/markdown; charset=utf-8", "data-quality-report.md"

        payload = {
            "summary": quality.model_dump(exclude={"issues"}),
            "issues": [issue.model_dump() for issue in issues],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json; charset=utf-8", "data-quality-report.json"

    def pipeline_status(self) -> PipelineStatusResponse:
        total = self._count("SELECT COUNT(*) FROM articles")
        cleaned = self._count("SELECT COUNT(*) FROM articles WHERE status='cleaned'")
        enriched = self._count("SELECT COUNT(*) FROM nlp_outputs")
        reports = sum(1 for name in self.report_files.values() if (self.settings.resolved_reports_dir / name).exists())
        latest_running = self._count("SELECT COUNT(*) FROM jobs WHERE status='running'")

        steps = [
            PipelineStep(key="collect", label="上傳/爬取", status=self._step_status(total, total, latest_running), count=total, total=max(total, 1), detail="Raw article records"),
            PipelineStep(key="profile", label="檢查與概要分析", status="complete" if total else "not_started", count=total, total=max(total, 1), detail="Coverage, missing values, source/date profile"),
            PipelineStep(key="clean", label="資料清洗", status=self._step_status(cleaned, total, latest_running), count=cleaned, total=max(total, 1), detail="Normalized text and dedup hash"),
            PipelineStep(key="enrich", label="進階分析", status=self._step_status(enriched, total, latest_running), count=enriched, total=max(total, 1), detail="NLP, tokens, entities, keywords"),
            PipelineStep(key="visualize", label="視覺化與報表", status="complete" if reports else ("ready" if enriched else "not_started"), count=reports, total=len(self.report_files), detail="ML/data-mining/IR reports"),
        ]
        current = next((step.key for step in steps if step.status not in ("complete",)), steps[-1].key)
        completion = round(sum(min(step.count / max(step.total, 1), 1) for step in steps) / len(steps) * 100, 1)
        return PipelineStatusResponse(steps=steps, current_step=current, completion_percent=completion)

    def overview(self) -> AnalysisOverviewResponse:
        reports = [
            self.collocations(limit=10),
            self._json_report("text_mining", "Topic modeling and keyword trends"),
            self._json_report("clustering", "Document cluster summaries"),
            self._json_report("sentiment", "Sentiment distribution and comparison"),
            self._json_report("time_series", "Keyword trend and burst detection"),
        ]
        nlp_docs = self._count("SELECT COUNT(*) FROM nlp_outputs")
        recommendations = []
        if nlp_docs < 10:
            recommendations.append("At least 10 NLP-enriched documents are recommended for stable text mining.")
        if not any(report.status == "ready" for report in reports):
            recommendations.append("Run an analysis job to generate visualization-ready reports.")
        return AnalysisOverviewResponse(
            reports=reports,
            nlp_documents=nlp_docs,
            analyzed_documents=nlp_docs if any(report.status == "ready" for report in reports) else 0,
            recommendations=recommendations,
        )

    def collocations(self, limit: int = 50) -> AnalysisReport:
        path = self.settings.resolved_reports_dir / "collocation_pmi.csv"
        if not path.exists():
            return AnalysisReport(name="collocations", status="missing", summary="No collocation report found.", data=[])
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
                if len(rows) >= limit:
                    break
        return AnalysisReport(
            name="collocations",
            status="ready",
            summary=f"{len(rows)} collocation pairs loaded.",
            updated_at=self._mtime(path),
            data=rows,
        )

    def report(self, name: str) -> AnalysisReport:
        if name == "collocations":
            return self.collocations()
        return self._json_report(name, f"{name.replace('_', ' ').title()} report")

    def ir_health(self) -> IRHealthResponse:
        total = self._count("SELECT COUNT(*) FROM articles")
        indexed = self._count("SELECT COUNT(*) FROM articles_fts")
        samples = []
        for query in ("人工智慧", "台灣", "經濟"):
            try:
                row = self.db.fetch_one(
                    "SELECT COUNT(*) FROM articles_fts WHERE articles_fts MATCH ?",
                    (f'"{query}"',),
                )
                samples.append({"query": query, "matches": int(row[0] if row else 0)})
            except Exception:
                samples.append({"query": query, "matches": 0})
        return IRHealthResponse(
            indexed_articles=indexed,
            total_articles=total,
            index_coverage_percent=round(indexed / total * 100, 1) if total else 0,
            sample_queries=samples,
        )

    def dashboard(
        self,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
    ) -> AnalysisDashboardResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        total = len(rows)
        enriched = sum(1 for row in rows if row.get("tokens"))
        with_dates = sum(1 for row in rows if row.get("publish_date"))
        sources = self._count_rows(rows, "source", limit=limit)
        categories = self._count_rows(rows, "category_label", limit=limit)
        keywords = self._keyword_counts(rows, limit=limit)
        entities = self._entity_counts(rows, limit=limit)
        sentiment = self._sentiment_summary(total)
        daily = self._daily_volume(rows)
        insights = self._business_cards(rows, keywords, entities)
        notes = []
        if total and with_dates < total:
            notes.append(f"{total - with_dates} articles are excluded from time-series charts because publish_date is missing.")
        note = fallback_entity_note(rows)
        if note:
            notes.append(note)
        elif not entities:
            notes.append("Named entity preview is empty because current NLP outputs do not include entities.")
        return AnalysisDashboardResponse(
            kpis={
                "total_articles": total,
                "nlp_enriched": enriched,
                "source_count": len({row.get("source") for row in rows if row.get("source")}),
                "category_count": len({row.get("category_label") for row in rows if row.get("category_label")}),
                "date_coverage_percent": round(with_dates / total * 100, 1) if total else 0,
            },
            source_distribution=sources,
            category_distribution=categories,
            daily_volume=daily,
            top_keywords=keywords,
            top_entities=entities,
            sentiment_summary=sentiment,
            insights=insights,
            notes=notes,
        )

    def trends(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 20) -> AnalysisTrendResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        notes = []
        daily = self._daily_volume(rows)
        if len(daily) < 2:
            notes.append("Insufficient multi-period data for growth or rising-topic analysis.")
        return AnalysisTrendResponse(
            daily_volume=daily,
            category_trend=self._trend_rows(rows, "category_label", limit=limit),
            source_trend=self._trend_rows(rows, "source", limit=limit),
            keyword_trend=self._keyword_trend(rows, limit=limit),
            notes=notes,
        )

    def sources(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 20) -> AnalysisSourceResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        return AnalysisSourceResponse(
            source_volume=self._count_rows(rows, "source", limit=limit),
            source_category_matrix=self._matrix(rows, "source", "category_label", "source", "category", limit=limit),
            source_keyword_profile=self._keyword_profile(rows, "source", limit=limit),
            insights=self._source_insights(rows),
        )

    def categories(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 20) -> AnalysisCategoryResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        return AnalysisCategoryResponse(
            category_distribution=self._count_rows(rows, "category_label", limit=limit),
            category_source_mix=self._matrix(rows, "category_label", "source", "category", "source", limit=limit),
            category_keywords=self._keyword_profile(rows, "category_label", limit=limit),
            insights=self._category_insights(rows),
        )

    def keywords_entities(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 30) -> AnalysisKeywordEntityResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        entities = self._entity_counts(rows, limit=limit)
        notes = []
        if not entities:
            notes.append("No named entities are available. Run CKIP NER or an entity extraction job to populate this section.")
        note = fallback_entity_note(rows)
        if note:
            notes.append(note)
        return AnalysisKeywordEntityResponse(
            top_keywords=self._keyword_counts(rows, limit=limit),
            keyword_by_source=self._keyword_profile(rows, "source", limit=limit),
            keyword_by_category=self._keyword_profile(rows, "category_label", limit=limit),
            top_entities=entities,
            entity_by_source=self._entity_profile(rows, "source", limit=limit),
            entity_by_category=self._entity_profile(rows, "category_label", limit=limit),
            notes=notes,
        )

    def business_insights(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 20) -> BusinessInsightResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        keywords = self._keyword_counts(rows, limit=limit)
        entities = self._entity_counts(rows, limit=limit)
        quality = self.data_quality()
        cards = self._business_cards(rows, keywords, entities)
        risks = []
        if quality.quality_score < 90:
            risks.append({"title": "Quality score below target", "severity": "warning", "detail": f"Current quality score is {quality.quality_score}."})
        if not entities:
            risks.append({"title": "Entity coverage unavailable", "severity": "info", "detail": "NER output is empty, limiting entity trend and monitoring views."})
        elif fallback_entity_note(rows):
            risks.append({"title": "Fallback entity extraction active", "severity": "info", "detail": "Entity insights are generated from lightweight rules until a full NER job is available."})
        if len(self._daily_volume(rows)) < 2:
            risks.append({"title": "Trend window too short", "severity": "info", "detail": "More dated articles are needed for lifecycle and growth analysis."})
        recommendations = [
            {"title": "Expand under-covered categories", "detail": "Use category coverage to decide crawler targets."},
            {"title": "Run entity extraction", "detail": "Entity coverage unlocks share-of-voice and co-occurrence analysis."},
            {"title": "Export current analysis", "detail": "Download JSON, CSV, or Markdown snapshots before model experiments."},
        ]
        return BusinessInsightResponse(
            cards=cards,
            recommendations=recommendations,
            risks=risks,
            tables={
                "under_covered_categories": self._under_covered_categories(rows),
                "source_concentration": self._count_rows(rows, "source", limit=limit),
                "hot_topics": keywords[:10],
            },
        )

    def live_summary(
        self,
        query: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
    ) -> LiveSummaryResponse:
        rows = self._analysis_rows(source, category, date_from, date_to)
        if query:
            needle = query.lower()
            rows = [
                row for row in rows
                if needle in str(row.get("title") or "").lower()
                or needle in str(row.get("content_clean") or "").lower()
                or any(needle in term.lower() for term in self._keyword_terms(row))
            ]
        rows = rows[: max(1, min(limit, 100))]
        if not rows:
            return LiveSummaryResponse(status="insufficient_data", notes=["No articles match the current live-analysis filters."])

        snippets = []
        for row in rows:
            text = f"{row.get('title') or ''}. {row.get('content_clean') or ''}".strip()
            if text:
                snippets.append(text[:1200])
        corpus = "\n".join(snippets)[:30000]
        provider = "extractive"
        notes: list[str] = []
        try:
            llm_summary = LLMService().summarize(
                corpus,
                instruction="請將以下新聞語料整理成 4 到 6 個重點，說明主要趨勢、風險與值得追蹤的議題。",
                max_tokens=650,
            )
            if llm_summary:
                bullets = llm_summary.bullets[:6]
                provider = llm_summary.provider
            else:
                result = Summarizer().mmr_summary(corpus, k=min(5, max(2, len(rows))), diversity=0.7)
                bullets = result.sentences
                notes.append("llama.cpp is disabled; used extractive fallback.")
        except Exception as exc:
            try:
                result = Summarizer().mmr_summary(corpus, k=min(5, max(2, len(rows))), diversity=0.7)
                bullets = result.sentences
                notes.append(f"llama.cpp fallback: {exc}")
            except Exception as fallback_exc:
                return LiveSummaryResponse(status="error", notes=[str(fallback_exc)])

        top_terms = self._keyword_counts(rows, limit=12)
        representatives = [
            {
                "article_id": row["article_id"],
                "title": row["title"],
                "source": row["source"],
                "category": row["category_label"],
                "publish_date": row["publish_date"],
            }
            for row in rows[:8]
        ]
        return LiveSummaryResponse(
            status="ready",
            summary=" ".join(bullets[:3]),
            bullets=bullets,
            top_terms=top_terms,
            representative_articles=representatives,
            notes=notes if len(rows) >= 5 else [*notes, "Summary is based on a small filtered article set."],
            provider=provider,
        )

    def export_analysis(
        self,
        section: str = "overview",
        fmt: str = "json",
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[str, str, str]:
        payload = self._analysis_section_payload(section, source, category, date_from, date_to)
        fmt = fmt.lower()
        if fmt == "csv":
            from io import StringIO

            out = StringIO()
            rows = self._flatten_export_rows(payload)
            if rows:
                writer = csv.DictWriter(out, fieldnames=sorted({key for row in rows for key in row.keys()}))
                writer.writeheader()
                writer.writerows(rows)
            return out.getvalue(), "text/csv; charset=utf-8", f"analysis-{section}.csv"
        if fmt == "markdown":
            lines = [f"# Analysis {section.replace('_', ' ').title()}", ""]
            for key, value in payload.items():
                lines.append(f"## {key.replace('_', ' ').title()}")
                if isinstance(value, list):
                    for item in value[:20]:
                        lines.append(f"- {item}")
                else:
                    lines.append(str(value))
                lines.append("")
            return "\n".join(lines), "text/markdown; charset=utf-8", f"analysis-{section}.md"
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json; charset=utf-8", f"analysis-{section}.json"

    def _json_report(self, name: str, summary: str) -> AnalysisReport:
        filename = self.report_files.get(name, f"{name}.json")
        path = self.settings.resolved_reports_dir / filename
        if not path.exists():
            return AnalysisReport(name=name, status="missing", summary=f"{summary} is not generated yet.")
        try:
            return AnalysisReport(
                name=name,
                status="ready",
                summary=summary,
                updated_at=self._mtime(path),
                data=json.loads(path.read_text(encoding="utf-8")),
            )
        except Exception as exc:
            return AnalysisReport(name=name, status="error", summary=str(exc))

    def _count(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        row = self.db.fetch_one(sql, params)
        return int(row[0] if row else 0)

    def _analysis_rows(
        self,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
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
        rows = self.db.fetch_all(
            f"""
            SELECT a.article_id, a.title, a.source, a.category, a.category_name,
                   COALESCE(NULLIF(a.category_name, ''), NULLIF(a.category, ''), 'unknown') AS category_label,
                   a.publish_date, a.char_count, a.content_clean, n.tokens, n.keywords, n.entities
            FROM articles a
            LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
            """,
            tuple(params),
        )
        return [dict(row) for row in rows]

    def _safe_json(self, value: Any, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return fallback

    def _count_rows(self, rows: list[dict[str, Any]], key: str, limit: int = 20) -> list[dict[str, Any]]:
        counts = Counter(str(row.get(key) or "unknown") for row in rows)
        return [{"name": name, "count": count} for name, count in counts.most_common(limit)]

    def _daily_volume(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        for row in rows:
            date = str(row.get("publish_date") or "").strip()[:10]
            if date:
                counts[date] += 1
        return [{"date": date, "count": counts[date]} for date in sorted(counts)]

    def _trend_rows(self, rows: list[dict[str, Any]], key: str, limit: int = 20) -> list[dict[str, Any]]:
        counts: dict[tuple[str, str], int] = {}
        for row in rows:
            date = str(row.get("publish_date") or "").strip()[:10]
            value = str(row.get(key) or "unknown")
            if date:
                counts[(date, value)] = counts.get((date, value), 0) + 1
        output = [{"date": date, key: value, "count": count} for (date, value), count in counts.items()]
        return sorted(output, key=lambda item: (item["date"], -int(item["count"])))[:limit]

    def _keyword_counts(self, rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        for row in rows:
            keywords = self._safe_json(row.get("keywords"), [])
            tokens = self._safe_json(row.get("tokens"), [])
            if keywords:
                for item in keywords:
                    if isinstance(item, (list, tuple)) and item:
                        counts[str(item[0])] += float(item[1] or 1) if len(item) > 1 else 1
            else:
                counts.update(str(token) for token in tokens if len(str(token)) > 1)
        if not counts:
            report = self._json_report("text_mining", "Text mining report")
            data = report.data if isinstance(report.data, dict) else {}
            for item in data.get("top_keywords", []):
                counts[str(item.get("keyword"))] += float(item.get("score") or item.get("count") or 1)
        return [{"keyword": keyword, "score": round(score, 4)} for keyword, score in counts.most_common(limit)]

    def _entity_counts(self, rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
        return entity_count_rows(rows, limit)

    def _keyword_trend(self, rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            date = str(row.get("publish_date") or "").strip()[:10]
            if not date:
                continue
            for keyword in self._keyword_terms(row)[:8]:
                counts[(date, keyword)] += 1
        return [{"date": date, "keyword": keyword, "count": count} for (date, keyword), count in counts.most_common(limit)]

    def _keyword_terms(self, row: dict[str, Any]) -> list[str]:
        keywords = self._safe_json(row.get("keywords"), [])
        if keywords:
            return [str(item[0]) for item in keywords if isinstance(item, (list, tuple)) and item]
        tokens = self._safe_json(row.get("tokens"), [])
        return [str(token) for token in tokens if len(str(token)) > 1]

    def _keyword_profile(self, rows: list[dict[str, Any]], group_key: str, limit: int = 20) -> list[dict[str, Any]]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            group = str(row.get(group_key) or "unknown")
            for keyword in self._keyword_terms(row)[:8]:
                counts[(group, keyword)] += 1
        label = "group" if group_key == "category_label" else group_key
        return [{label: group, "keyword": keyword, "count": count} for (group, keyword), count in counts.most_common(limit)]

    def _entity_profile(self, rows: list[dict[str, Any]], group_key: str, limit: int = 20) -> list[dict[str, Any]]:
        label = "group" if group_key == "category_label" else group_key
        return entity_profile_rows(rows, group_key, label, limit)

    def _matrix(self, rows: list[dict[str, Any]], row_key: str, col_key: str, row_label: str, col_label: str, limit: int = 50) -> list[dict[str, Any]]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            counts[(str(row.get(row_key) or "unknown"), str(row.get(col_key) or "unknown"))] += 1
        return [{row_label: r, col_label: c, "count": count} for (r, c), count in counts.most_common(limit)]

    def _sentiment_summary(self, total: int) -> list[dict[str, Any]]:
        report = self._json_report("sentiment", "Sentiment report")
        data = report.data if isinstance(report.data, dict) else {}
        distribution = data.get("distribution")
        if isinstance(distribution, list) and distribution:
            return distribution
        return [{"label": "neutral", "count": total}]

    def _business_cards(self, rows: list[dict[str, Any]], keywords: list[dict[str, Any]], entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total = len(rows)
        source_counts = self._count_rows(rows, "source", limit=1)
        max_source = source_counts[0] if source_counts else {"name": "none", "count": 0}
        source_share = round(max_source["count"] / total * 100, 1) if total else 0
        top_keyword = keywords[0]["keyword"] if keywords else "none"
        return [
            {"title": "Top source share", "metric": f"{source_share}%", "detail": f"{max_source['name']} has the largest article share."},
            {"title": "Hot topic", "metric": top_keyword, "detail": "Highest weighted keyword in the current filter."},
            {"title": "Entity coverage", "metric": str(len(entities)), "detail": "Unique entity rows available from NLP output."},
            {"title": "Article base", "metric": str(total), "detail": "Filtered articles available for analysis."},
        ]

    def _source_insights(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        source_counts = self._count_rows(rows, "source", limit=5)
        return [{"title": f"{item['name']} volume", "detail": f"{item['count']} articles in current filters."} for item in source_counts]

    def _category_insights(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        under = self._under_covered_categories(rows)
        return [{"title": f"{item['category']} under-covered", "detail": f"{item['count']} articles, below average coverage."} for item in under[:5]]

    def _under_covered_categories(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts = self._count_rows(rows, "category_label", limit=100)
        if not counts:
            return []
        avg = sum(int(item["count"]) for item in counts) / len(counts)
        return [{"category": item["name"], "count": item["count"], "average": round(avg, 1)} for item in counts if int(item["count"]) < avg]

    def _analysis_section_payload(self, section: str, source: str | None, category: str | None, date_from: str | None, date_to: str | None) -> dict[str, Any]:
        if section == "trends":
            return self.trends(source, category, date_from, date_to).model_dump()
        if section == "sources":
            return self.sources(source, category, date_from, date_to).model_dump()
        if section == "categories":
            return self.categories(source, category, date_from, date_to).model_dump()
        if section == "keywords_entities":
            return self.keywords_entities(source, category, date_from, date_to).model_dump()
        if section == "business":
            return self.business_insights(source, category, date_from, date_to).model_dump()
        return self.dashboard(source, category, date_from, date_to).model_dump()

    def _flatten_export_rows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        rows.append({"section": key, **item})
                    else:
                        rows.append({"section": key, "value": str(item)})
            elif isinstance(value, dict):
                rows.append({"section": key, **value})
            else:
                rows.append({"section": key, "value": str(value)})
        return rows

    def _metric(self, key: str, label: str, value: int, total: int, inverse: bool = False) -> DataQualityMetric:
        percent = round(value / total * 100, 1) if total else 0.0
        quality = 100 - percent if inverse else percent
        severity = "good" if quality >= 90 else ("warning" if quality >= 70 else "danger")
        return DataQualityMetric(key=key, label=label, value=value, total=total, percent=percent, severity=severity)

    def _quality_issues(self, limit: int | None = 100) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []

        checks = [
            (
                "missing_title",
                "danger",
                "Missing title",
                "Re-run parser or fill the title from metadata.",
                "title IS NULL OR trim(title) = ''",
            ),
            (
                "missing_content",
                "danger",
                "Missing content",
                "Inspect crawler selectors and retry extraction.",
                "content_clean IS NULL OR trim(content_clean) = ''",
            ),
            (
                "missing_publish_date",
                "warning",
                "Missing publish date",
                "Normalize source date fields before trend analysis.",
                "publish_date IS NULL OR trim(publish_date) = ''",
            ),
            (
                "invalid_url",
                "danger",
                "Invalid URL",
                "Keep absolute HTTP(S) article URLs during ingestion.",
                "url IS NULL OR trim(url) = '' OR lower(url) NOT LIKE 'http%'",
            ),
            (
                "short_content",
                "warning",
                "Content is shorter than 60 characters",
                "Check whether the crawler captured only teaser text.",
                "COALESCE(char_count, length(COALESCE(content_clean, ''))) < 60",
            ),
        ]

        for issue_type, severity, message, suggested_fix, where in checks:
            if limit is not None and len(issues) >= limit:
                break
            sql = f"""
                SELECT article_id, title, source, category, category_name, publish_date, char_count
                FROM articles
                WHERE {where}
                ORDER BY COALESCE(publish_date, crawled_at) DESC, article_id DESC
            """
            rows = self.db.fetch_all(sql)
            for row in rows:
                if limit is not None and len(issues) >= limit:
                    break
                issues.append(self._issue_from_row(row, issue_type, severity, message, suggested_fix))

        if limit is None or len(issues) < limit:
            rows = self.db.fetch_all(
                """
                SELECT a.article_id, a.title, a.source, a.category, a.category_name, a.publish_date, a.char_count
                FROM articles a
                JOIN (
                    SELECT lower(trim(title_clean)) AS key
                    FROM articles
                    WHERE title_clean IS NOT NULL AND trim(title_clean) != ''
                    GROUP BY key HAVING COUNT(*) > 1
                ) d ON lower(trim(a.title_clean)) = d.key
                ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
                """,
            )
            for row in rows:
                if limit is not None and len(issues) >= limit:
                    break
                issues.append(self._issue_from_row(
                    row,
                    "duplicate_title",
                    "warning",
                    "Potential duplicate title",
                    "Review duplicate groups before model training or export.",
                ))
        if limit is None or len(issues) < limit:
            rows = self.db.fetch_all(
                """
                SELECT a.article_id, a.title, a.source, a.category, a.category_name, a.publish_date, a.char_count
                FROM articles a
                JOIN (
                    SELECT dedup_hash
                    FROM articles
                    WHERE dedup_hash IS NOT NULL AND trim(dedup_hash) != ''
                    GROUP BY dedup_hash HAVING COUNT(*) > 1
                ) d ON a.dedup_hash = d.dedup_hash
                ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
                """
            )
            for row in rows:
                if limit is not None and len(issues) >= limit:
                    break
                issues.append(self._issue_from_row(
                    row,
                    "duplicate_hash",
                    "warning",
                    "Potential duplicate content hash",
                    "Review duplicate content groups before analysis or export.",
                ))
        return issues

    def _issue_from_row(self, row: Any, issue_type: str, severity: str, message: str, suggested_fix: str) -> DataQualityIssue:
        return DataQualityIssue(
            article_id=row["article_id"],
            title=row["title"] or "",
            source=row["source"] or "",
            category=row["category"] or "",
            category_name=row["category_name"] or "",
            publish_date=row["publish_date"],
            char_count=int(row["char_count"] or 0),
            issue_type=issue_type,
            severity=severity,
            message=message,
            suggested_fix=suggested_fix,
        )

    def _filtered_quality_issues(
        self,
        issue_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        article_id: str | None = None,
    ) -> list[DataQualityIssue]:
        items = self._quality_issues(limit=None)
        if issue_type:
            items = [item for item in items if item.issue_type == issue_type]
        if severity:
            items = [item for item in items if item.severity == severity]
        if source:
            items = [item for item in items if item.source == source]
        if category:
            items = [item for item in items if item.category == category or item.category_name == category]
        if date_from:
            items = [item for item in items if item.publish_date and item.publish_date >= date_from]
        if date_to:
            items = [item for item in items if item.publish_date and item.publish_date <= date_to]
        if article_id:
            items = [item for item in items if item.article_id == article_id]
        return items

    def _length_distribution(self) -> list[dict[str, Any]]:
        buckets = [
            ("0-59", 0, 59),
            ("60-119", 60, 119),
            ("120-239", 120, 239),
            ("240-499", 240, 499),
            ("500+", 500, None),
        ]
        rows = []
        for label, lower, upper in buckets:
            if upper is None:
                count = self._count("SELECT COUNT(*) FROM articles WHERE COALESCE(char_count, length(COALESCE(content_clean, ''))) >= ?", (lower,))
            else:
                count = self._count(
                    "SELECT COUNT(*) FROM articles WHERE COALESCE(char_count, length(COALESCE(content_clean, ''))) BETWEEN ? AND ?",
                    (lower, upper),
                )
            rows.append({"bucket": label, "count": count})
        return rows

    def _step_status(self, count: int, total: int, running: int) -> str:
        if running:
            return "running"
        if total == 0:
            return "not_started"
        if count >= total:
            return "complete"
        return "warning" if count else "ready"

    def _mtime(self, path: Path) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
