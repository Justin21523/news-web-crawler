from __future__ import annotations

import importlib.util
import json
import os
import uuid
from collections import Counter
from typing import Any

from app.schemas.entity_extraction import (
    EntityExtractionCompareResponse,
    EntityExtractionRun,
    EntityExtractionRunListResponse,
    EntityExtractionRunResponse,
    EntityProviderListResponse,
    EntityProviderStatus,
)
from app.services.database import Database, decode_json
from app.services.entity_utils import fallback_entities_from_row, parse_entities


class EntityExtractionService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def providers(self) -> EntityProviderListResponse:
        spacy_model = os.getenv("NEWS_SPACY_MODEL", "zh_core_web_sm")
        providers = [
            EntityProviderStatus(provider="fallback", available=True, detail="Rule-based extractor available without optional dependencies."),
            self._module_status("ckip", "ckip_transformers", "CKIP Transformers NER provider."),
            self._module_status("spacy", "spacy", "spaCy NER provider.", model=spacy_model),
        ]
        active = self.active_run()
        return EntityProviderListResponse(
            providers=providers,
            active_run_id=active.run_id if active else None,
            active_entity_source=active.provider if active else self._active_entity_source(),
        )

    def runs(self, limit: int = 20) -> EntityExtractionRunListResponse:
        rows = self.db.fetch_all(
            """
            SELECT run_id, provider, strategy, params_json, status, metrics_json, error, created_at
            FROM entity_extraction_runs
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (min(max(limit, 1), 100),),
        )
        return EntityExtractionRunListResponse(runs=[self._run_from_row(dict(row)) for row in rows])

    def active_run(self) -> EntityExtractionRun | None:
        row = self.db.fetch_one(
            """
            SELECT run_id, provider, strategy, params_json, status, metrics_json, error, created_at
            FROM entity_extraction_runs
            WHERE json_extract(metrics_json, '$.activated') = 1
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """
        )
        return self._run_from_row(dict(row)) if row else None

    def run(
        self,
        provider: str = "fallback",
        activate: bool = True,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
        spacy_model: str | None = None,
    ) -> EntityExtractionRunResponse:
        provider = provider if provider in {"fallback", "ckip", "spacy", "auto"} else "fallback"
        selected, notes = self._resolve_provider(provider)
        run_id = f"entity-{uuid.uuid4().hex[:10]}"
        params = {
            "provider": provider,
            "selected_provider": selected,
            "activate": activate,
            "source": source,
            "category": category,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
            "spacy_model": spacy_model or os.getenv("NEWS_SPACY_MODEL", "zh_core_web_sm"),
        }
        self._insert_run(run_id, selected, provider, params, "running", {"activated": False})
        rows = self._rows(source, category, date_from, date_to, limit)
        if not rows:
            metrics = {"documents": 0, "entities": 0, "activated": False}
            self._finish_run(run_id, "insufficient_data", metrics)
            return EntityExtractionRunResponse(status="insufficient_data", run=self._get_run(run_id), notes=["No articles matched the entity extraction filters."])

        if selected in {"ckip", "spacy"} and not self._provider_available(selected):
            detail = f"{selected} optional dependency is not available."
            self._finish_run(run_id, "dependency_missing", {"documents": len(rows), "entities": 0, "activated": False}, error=detail)
            return EntityExtractionRunResponse(status="dependency_missing", run=self._get_run(run_id), notes=[detail, *notes])

        extractor = self._extract_fallback if selected == "fallback" else self._extract_model_provider
        output_preview: list[dict[str, Any]] = []
        total_entities = 0
        docs_with_entities = 0
        type_counts: Counter[str] = Counter()
        for row in rows:
            entities = extractor(row, selected, params)
            if entities:
                docs_with_entities += 1
            total_entities += len(entities)
            type_counts.update(entity_type for _, entity_type in entities)
            self.db.execute(
                """
                INSERT OR REPLACE INTO entity_extraction_outputs
                (run_id, article_id, entities_json, provider, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["article_id"],
                    json.dumps([list(item) for item in entities], ensure_ascii=False),
                    selected,
                    json.dumps({"source": selected, "requested_provider": provider}, ensure_ascii=False),
                ),
            )
            if len(output_preview) < 12:
                output_preview.append({"article_id": row["article_id"], "title": row.get("title"), "entities": [list(item) for item in entities[:8]]})

        metrics = {
            "documents": len(rows),
            "documents_with_entities": docs_with_entities,
            "entities": total_entities,
            "unique_entities": len({entity for item in output_preview for entity, *_ in item.get("entities", [])}),
            "type_distribution": dict(type_counts),
            "activated": bool(activate),
        }
        if activate:
            self._activate_run(run_id, selected)
        self._finish_run(run_id, "ready", metrics)
        return EntityExtractionRunResponse(
            status="ready",
            run=self._get_run(run_id),
            processed_documents=len(rows),
            activated=activate,
            outputs_preview=output_preview,
            notes=notes,
        )

    def compare(self, left_run_id: str | None = None, right_run_id: str | None = None, limit: int = 20) -> EntityExtractionCompareResponse:
        runs = self.runs(limit=10).runs
        if not left_run_id and len(runs) >= 1:
            left_run_id = runs[0].run_id
        if not right_run_id and len(runs) >= 2:
            right_run_id = runs[1].run_id
        if not left_run_id or not right_run_id:
            return EntityExtractionCompareResponse(status="insufficient_data", notes=["At least two entity extraction runs are required for comparison."])

        left = self._get_run(left_run_id)
        right = self._get_run(right_run_id)
        left_rows = self._outputs(left_run_id)
        right_rows = self._outputs(right_run_id)
        common_ids = sorted(set(left_rows) & set(right_rows))
        if not common_ids:
            return EntityExtractionCompareResponse(status="insufficient_data", left_run=left, right_run=right, notes=["Selected runs have no overlapping articles."])

        overlaps: list[float] = []
        left_only_total = 0
        right_only_total = 0
        sample_diffs = []
        type_counts: Counter[tuple[str, str]] = Counter()
        for article_id in common_ids:
            left_entities = set(entity for entity, _ in left_rows[article_id])
            right_entities = set(entity for entity, _ in right_rows[article_id])
            union = left_entities | right_entities
            overlap = len(left_entities & right_entities) / len(union) if union else 1.0
            overlaps.append(overlap)
            left_only = sorted(left_entities - right_entities)
            right_only = sorted(right_entities - left_entities)
            left_only_total += len(left_only)
            right_only_total += len(right_only)
            for _, typ in left_rows[article_id]:
                type_counts[("left", typ)] += 1
            for _, typ in right_rows[article_id]:
                type_counts[("right", typ)] += 1
            if len(sample_diffs) < limit:
                sample_diffs.append({"article_id": article_id, "jaccard": round(overlap, 4), "left_only": ", ".join(left_only[:8]), "right_only": ", ".join(right_only[:8])})

        metrics = {
            "overlap_articles": len(common_ids),
            "avg_jaccard": round(sum(overlaps) / len(overlaps), 4) if overlaps else 0,
            "left_only_entities": left_only_total,
            "right_only_entities": right_only_total,
        }
        return EntityExtractionCompareResponse(
            status="ready",
            left_run=left,
            right_run=right,
            metrics=metrics,
            type_distribution=[{"side": side, "type": typ, "count": count} for (side, typ), count in type_counts.most_common()],
            sample_diffs=sample_diffs,
        )

    def _extract_fallback(self, row: dict[str, Any], provider: str, params: dict[str, Any]) -> list[tuple[str, str]]:
        return fallback_entities_from_row(row)

    def _extract_model_provider(self, row: dict[str, Any], provider: str, params: dict[str, Any]) -> list[tuple[str, str]]:
        text = f"{row.get('title') or ''} {row.get('content_clean') or ''}".strip()
        if provider == "spacy":
            try:
                import spacy

                nlp = spacy.load(str(params.get("spacy_model") or "zh_core_web_sm"))
                return [(ent.text, ent.label_) for ent in nlp(text).ents]
            except Exception:
                return []
        try:
            from nlp.pipeline import NLPPipeline

            result = NLPPipeline(engine="ckip", top_keywords=10).process(text)
            return result.entities
        except Exception:
            return []

    def _activate_run(self, run_id: str, provider: str) -> None:
        outputs = self.db.fetch_all("SELECT article_id, entities_json FROM entity_extraction_outputs WHERE run_id = ?", (run_id,))
        for row in outputs:
            existing = self.db.fetch_one("SELECT model_version FROM nlp_outputs WHERE article_id = ?", (row["article_id"],))
            model_version = f"{existing['model_version'] if existing and existing['model_version'] else 'nlp'}|ner:{provider}|entity-run:{run_id}"
            self.db.execute(
                """
                INSERT INTO nlp_outputs (article_id, tokens, pos_tags, entities, keywords, keyword_summary, model_version, enriched_at)
                VALUES (?, '[]', '[]', ?, '[]', '', ?, datetime('now'))
                ON CONFLICT(article_id) DO UPDATE SET
                    entities=excluded.entities,
                    model_version=excluded.model_version,
                    enriched_at=excluded.enriched_at
                """,
                (row["article_id"], row["entities_json"], model_version),
            )

    def _resolve_provider(self, provider: str) -> tuple[str, list[str]]:
        if provider != "auto":
            return provider, []
        if self._provider_available("ckip"):
            return "ckip", ["Auto selected CKIP NER provider."]
        if self._provider_available("spacy"):
            return "spacy", ["Auto selected spaCy NER provider."]
        return "fallback", ["Auto selected fallback because model providers are unavailable."]

    def _provider_available(self, provider: str) -> bool:
        if provider == "fallback":
            return True
        if provider == "ckip":
            return importlib.util.find_spec("ckip_transformers") is not None
        if provider == "spacy":
            return importlib.util.find_spec("spacy") is not None
        return False

    def _module_status(self, provider: str, module: str, detail: str, model: str | None = None) -> EntityProviderStatus:
        available = importlib.util.find_spec(module) is not None
        return EntityProviderStatus(provider=provider, available=available, status="available" if available else "dependency_missing", detail=detail if available else f"Install optional dependency for {provider}.", model=model)

    def _rows(self, source: str | None, category: str | None, date_from: str | None, date_to: str | None, limit: int) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[Any] = []
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
        params.append(min(max(limit, 1), 2000))
        return [dict(row) for row in self.db.fetch_all(
            f"""
            SELECT a.article_id, a.title, a.content_clean, a.source, a.category, a.category_name,
                   a.publish_date, n.tokens, n.keywords, n.entities
            FROM articles a
            LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
            LIMIT ?
            """,
            tuple(params),
        )]

    def _insert_run(self, run_id: str, provider: str, strategy: str, params: dict[str, Any], status: str, metrics: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO entity_extraction_runs
            (run_id, provider, strategy, params_json, status, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, provider, strategy, json.dumps(params, ensure_ascii=False), status, json.dumps(metrics, ensure_ascii=False)),
        )

    def _finish_run(self, run_id: str, status: str, metrics: dict[str, Any], error: str | None = None) -> None:
        self.db.execute(
            "UPDATE entity_extraction_runs SET status = ?, metrics_json = ?, error = ? WHERE run_id = ?",
            (status, json.dumps(metrics, ensure_ascii=False), error, run_id),
        )

    def _get_run(self, run_id: str) -> EntityExtractionRun | None:
        row = self.db.fetch_one(
            "SELECT run_id, provider, strategy, params_json, status, metrics_json, error, created_at FROM entity_extraction_runs WHERE run_id = ?",
            (run_id,),
        )
        return self._run_from_row(dict(row)) if row else None

    def _outputs(self, run_id: str) -> dict[str, list[tuple[str, str]]]:
        rows = self.db.fetch_all("SELECT article_id, entities_json FROM entity_extraction_outputs WHERE run_id = ?", (run_id,))
        return {row["article_id"]: parse_entities(row["entities_json"]) for row in rows}

    def _run_from_row(self, row: dict[str, Any]) -> EntityExtractionRun:
        return EntityExtractionRun(
            run_id=row["run_id"],
            provider=row["provider"],
            strategy=row["strategy"],
            status=row["status"],
            params=decode_json(row.get("params_json"), {}),
            metrics=decode_json(row.get("metrics_json"), {}),
            error=row.get("error"),
            created_at=row.get("created_at"),
        )

    def _active_entity_source(self) -> str:
        row = self.db.fetch_one(
            """
            SELECT model_version FROM nlp_outputs
            WHERE model_version LIKE '%|ner:%'
            ORDER BY datetime(enriched_at) DESC
            LIMIT 1
            """
        )
        value = str(row["model_version"] if row else "")
        if "|ner:" not in value:
            return "fallback"
        return value.split("|ner:", 1)[1].split("|", 1)[0]
