from __future__ import annotations

import csv
import json
import math
import re
import uuid
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from app.services.database import Database, decode_json
from app.services.entity_utils import entity_count_rows, fallback_entities_from_row, fallback_entity_note
from app.services.entity_extraction import EntityExtractionService
from app.schemas.text_mining import (
    AssignmentListResponse,
    AssignmentRunResponse,
    ClusterResponse,
    BurstTrendResponse,
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


class TextMiningService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def overview(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> TextMiningOverviewResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        token_docs = [row for row in rows if row["tokens"]]
        entities = self._entity_counts(rows, 20)
        notes = []
        if not rows:
            notes.append("Run demo, ingest, and NLP jobs before text mining.")
        note = fallback_entity_note(rows)
        if note:
            notes.append(note)
        elif not entities:
            notes.append("No named entities are available in current NLP outputs.")
        return TextMiningOverviewResponse(
            status="ready" if rows else "insufficient_data",
            total_documents=len(rows),
            top_keywords=self._keyword_counts(rows, 20),
            top_ngrams=self._ngram_counts(rows, 2, 20),
            top_entities=entities,
            coverage={
                "nlp_documents": len(token_docs),
                "entity_documents": sum(1 for row in rows if fallback_entities_from_row(row)),
                "sources": len({row["source"] for row in rows if row["source"]}),
                "categories": len({row["category_label"] for row in rows if row["category_label"]}),
            },
            notes=notes,
        )

    def tfidf(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> TfidfResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        docs, doc_ids = self._documents(rows)
        if len(docs) < 2:
            return TfidfResponse(status="insufficient_data", total_documents=len(docs), notes=["At least 2 NLP documents are required for TF-IDF."])
        try:
            from features.tfidf import TfidfBuilder
        except ImportError:
            return TfidfResponse(status="dependency_missing", total_documents=len(docs), notes=["scikit-learn is required for TF-IDF."])
        builder = TfidfBuilder(max_features=5000, min_df=1, max_df=1.0)
        builder.fit(docs, doc_ids)
        document_terms = []
        matrix = builder._dtm
        names = builder.feature_names
        for idx, doc_id in enumerate(doc_ids[:20]):
            weights = matrix[idx].toarray().ravel()
            top_idx = weights.argsort()[::-1][:8]
            terms = [{"term": names[i], "weight": round(float(weights[i]), 4)} for i in top_idx if weights[i] > 0]
            document_terms.append({"article_id": doc_id, "terms": terms})
        return TfidfResponse(
            status="ready",
            total_documents=len(docs),
            vocabulary_size=builder.vocabulary_size,
            top_terms=[{"term": term, "weight": weight} for term, weight in builder.get_top_terms(30)],
            document_terms=document_terms,
        )

    def ngrams(self, n: int = 2, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> NgramResponse:
        n = min(max(n, 1), 3)
        rows = self._rows(source, category, date_from, date_to, limit)
        return NgramResponse(
            status="ready" if rows else "insufficient_data",
            total_documents=len(rows),
            n=n,
            ngrams=self._ngram_counts(rows, n, 50),
            by_source=self._ngram_profile(rows, n, "source", 40),
            by_category=self._ngram_profile(rows, n, "category_label", 40),
        )

    def topics(self, method: str = "nmf", n_topics: int = 5, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> TopicModelResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        docs_tokens = [self._safe_json(row["tokens"], []) for row in rows if row["tokens"]]
        doc_ids = [row["article_id"] for row in rows if row["tokens"]]
        if len(docs_tokens) < 3:
            return TopicModelResponse(status="insufficient_data", total_documents=len(docs_tokens), method=method, notes=["At least 3 NLP documents are required for topic modeling."])
        try:
            from analysis.text_mining import TextMiningAnalyzer
        except ImportError:
            return TopicModelResponse(status="dependency_missing", total_documents=len(docs_tokens), method=method, notes=["scikit-learn is required for topic modeling."])
        n_topics = min(max(n_topics, 2), max(2, min(8, len(docs_tokens) - 1)))
        try:
            analyzer = TextMiningAnalyzer(min_df=1, max_df=1.0, max_features=5000)
            analyzer.fit(docs_tokens, doc_ids=doc_ids)
            topics = analyzer.topic_model(n_topics=n_topics, method=method, top_terms=10)
        except Exception as exc:
            return TopicModelResponse(status="error", total_documents=len(docs_tokens), method=method, notes=[str(exc)])
        return TopicModelResponse(
            status="ready",
            total_documents=len(docs_tokens),
            method=method,
            topics=[{"topic_id": t.topic_id, "top_terms": [{"term": w, "weight": s} for w, s in t.top_terms], "top_docs": [{"article_id": d, "weight": s} for d, s in t.top_docs[:5]]} for t in topics],
        )

    def clusters(self, method: str = "kmeans", n_clusters: int = 5, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> ClusterResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        docs_tokens = [self._safe_json(row["tokens"], []) for row in rows if row["tokens"]]
        doc_ids = [row["article_id"] for row in rows if row["tokens"]]
        if len(docs_tokens) < 3:
            return ClusterResponse(status="insufficient_data", total_documents=len(docs_tokens), method=method, notes=["At least 3 NLP documents are required for clustering."])
        try:
            from analysis.clustering import DocumentClusterer
        except ImportError:
            return ClusterResponse(status="dependency_missing", total_documents=len(docs_tokens), method=method, notes=["scikit-learn is required for clustering."])
        n_clusters = min(max(n_clusters, 2), max(2, min(8, len(docs_tokens) - 1)))
        try:
            clusterer = DocumentClusterer(max_features=5000)
            labels, metrics = clusterer.fit(docs_tokens, doc_ids=doc_ids, method=method, n_clusters=n_clusters)
            summaries = clusterer.summarize(top_terms=8)
        except Exception as exc:
            return ClusterResponse(status="error", total_documents=len(docs_tokens), method=method, notes=[str(exc)])
        meta = {row["article_id"]: row for row in rows}
        points = self._cluster_projection_points(clusterer, labels, meta)
        return ClusterResponse(
            status="ready",
            total_documents=len(docs_tokens),
            method=method,
            metrics={key: round(float(value), 4) if isinstance(value, float) else value for key, value in metrics.items()},
            clusters=[
                {
                    "cluster_id": c.cluster_id,
                    "size": c.size,
                    "top_terms": [{"term": w, "weight": s} for w, s in c.top_terms],
                    "examples": [{"article_id": aid, "title": meta.get(aid, {}).get("title", "")} for aid in c.doc_ids[:5]],
                    "points": [point for point in points if point["cluster_id"] == c.cluster_id],
                }
                for c in summaries
            ],
        )

    def similarity(self, query: str | None = None, article_id: str | None = None, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> SimilarityResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        docs, doc_ids = self._documents(rows)
        if len(docs) < 2:
            return SimilarityResponse(status="insufficient_data", total_documents=len(docs), query=query, article_id=article_id, notes=["At least 2 NLP documents are required for similarity search."])
        try:
            from features.tfidf import TfidfBuilder
        except ImportError:
            return SimilarityResponse(status="dependency_missing", total_documents=len(docs), query=query, article_id=article_id, notes=["scikit-learn is required for similarity search."])
        builder = TfidfBuilder(max_features=5000, min_df=1, max_df=1.0)
        builder.fit(docs, doc_ids)
        if article_id:
            from sklearn.metrics.pairwise import cosine_similarity
            if article_id not in doc_ids:
                return SimilarityResponse(status="insufficient_data", total_documents=len(docs), article_id=article_id, notes=["Article is not available in the filtered NLP corpus."])
            idx = doc_ids.index(article_id)
            scores = cosine_similarity(builder._dtm[idx:idx + 1], builder._dtm).ravel()
            ranked = [(doc_ids[i], float(scores[i])) for i in scores.argsort()[::-1] if doc_ids[i] != article_id and scores[i] > 0][:20]
        else:
            ranked = builder.search(query or "", topk=20)
        meta = {row["article_id"]: row for row in rows}
        return SimilarityResponse(
            status="ready",
            total_documents=len(docs),
            query=query,
            article_id=article_id,
            results=[{"article_id": aid, "title": meta.get(aid, {}).get("title", ""), "source": meta.get(aid, {}).get("source", ""), "category": meta.get(aid, {}).get("category_label", ""), "score": round(float(score), 6)} for aid, score in ranked],
            notes=[] if ranked else ["No similar articles matched the current query or filters."],
        )

    def network(self, kind: str = "keyword", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 500) -> NetworkResponse:
        kind = "entity" if kind == "entity" else "keyword"
        rows = self._rows(source, category, date_from, date_to, limit)
        docs = []
        for row in rows:
            if kind == "entity":
                values = [entity for entity, _ in fallback_entities_from_row(row)]
            else:
                values = [item["ngram"] for item in self._ngram_counts([row], 1, 12)]
            values = list(dict.fromkeys(values))[:12]
            if values:
                docs.append(values)
        nodes, edges = self._network_from_docs(docs, kind)
        notes = []
        note = fallback_entity_note(rows) if kind == "entity" else None
        if note:
            notes.append(note)
        if kind == "entity" and not nodes:
            notes.append("No entity network is available because current NLP outputs do not include entities.")
        return NetworkResponse(status="ready" if rows else "insufficient_data", total_documents=len(rows), type=kind, nodes=nodes, edges=edges, notes=notes)

    def collocations(
        self,
        metric: str = "npmi",
        level: str = "sentence",
        ngram_type: str = "bigram",
        window_size: int = 5,
        min_freq: int = 2,
        top_k: int = 50,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
    ) -> CollocationResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        metric = metric if metric in {"frequency", "pmi", "ppmi", "npmi", "log_likelihood", "dice", "t_score"} else "npmi"
        level = level if level in {"window", "sentence", "document"} else "sentence"
        ngram_type = ngram_type if ngram_type in {"bigram", "trigram"} else "bigram"
        window_size = min(max(window_size, 2), 10)
        min_freq = max(min_freq, 1)
        top_k = min(max(top_k, 10), 200)

        units_by_article: list[tuple[dict[str, Any], list[list[str]]]] = []
        unigram_counts: Counter[str] = Counter()
        pair_counts: Counter[tuple[str, str]] = Counter()
        trigram_counts: Counter[tuple[str, str, str]] = Counter()
        term_doc_counts: Counter[str] = Counter()
        total_units = 0
        total_tokens = 0

        for row in rows:
            units = self._cooccurrence_units(row, level, window_size)
            units_by_article.append((row, units))
            doc_terms: set[str] = set()
            for unit in units:
                tokens = [token for token in unit if len(token) > 1]
                if not tokens:
                    continue
                total_units += 1
                total_tokens += len(tokens)
                unigram_counts.update(tokens)
                doc_terms.update(tokens)
                if ngram_type == "trigram":
                    for idx in range(0, max(0, len(tokens) - 2)):
                        trigram_counts[tuple(tokens[idx:idx + 3])] += 1
                for a, b in self._pairs_for_unit(tokens, level, window_size):
                    pair_counts[(a, b)] += 1
            term_doc_counts.update(doc_terms)

        scored_pairs = self._score_collocation_pairs(pair_counts, unigram_counts, total_tokens, total_units)
        scored_trigrams = self._score_trigrams(trigram_counts, unigram_counts, total_tokens)
        rows_out = scored_trigrams if ngram_type == "trigram" else scored_pairs
        rows_out = [item for item in rows_out if int(item.get("count", 0)) >= min_freq]
        rows_out.sort(key=lambda item: (float(item.get(metric, item.get("score", 0)) or 0), int(item.get("count", 0))), reverse=True)
        selected = rows_out[:top_k]
        selected_terms = {self._collocation_key(item) for item in selected}

        source_counts: Counter[tuple[str, str]] = Counter()
        category_counts: Counter[tuple[str, str]] = Counter()
        trend_counts: Counter[tuple[str, str]] = Counter()
        examples: list[dict[str, Any]] = []
        example_seen: set[tuple[str, str]] = set()
        for row, units in units_by_article:
            article_terms = self._article_collocation_hits(row, units, ngram_type, selected_terms, level, window_size)
            for key in article_terms:
                source_counts[(str(row.get("source") or "unknown"), key)] += 1
                category_counts[(str(row.get("category_label") or "unknown"), key)] += 1
                if row.get("publish_date"):
                    trend_counts[(str(row["publish_date"])[:10], key)] += 1
                marker = (key, str(row.get("article_id")))
                if marker not in example_seen and len(examples) < 80:
                    example_seen.add(marker)
                    examples.append({
                        "collocation": key,
                        "article_id": row.get("article_id"),
                        "title": row.get("title"),
                        "source": row.get("source"),
                        "category": row.get("category_label"),
                        "publish_date": row.get("publish_date"),
                    })

        for item in selected:
            item["score"] = round(float(item.get(metric, 0) or 0), 6)
            item["metric"] = metric
        notes = []
        if not rows:
            notes.append("Run ingestion and NLP before collocation analysis.")
        if not selected:
            notes.append("No collocations met the current frequency and filter settings.")
        return CollocationResponse(
            status="ready" if selected else ("insufficient_data" if not rows else "ready"),
            total_documents=len(rows),
            metric=metric,
            level=level,
            ngram_type=ngram_type,
            window_size=window_size,
            collocations=selected,
            heatmap=[{"term_a": item.get("term_a"), "term_b": item.get("term_b"), "count": item.get("count"), "score": item.get("score")} for item in selected[:40] if item.get("term_b")],
            source_matrix=[{"source": group, "collocation": key, "count": count} for (group, key), count in source_counts.most_common(120)],
            category_matrix=[{"category": group, "collocation": key, "count": count} for (group, key), count in category_counts.most_common(120)],
            trend=[{"date": date, "collocation": key, "count": count} for (date, key), count in sorted(trend_counts.items())[-160:]],
            examples=examples,
            notes=notes,
        )

    def co_occurrence(
        self,
        kind: str = "keyword",
        level: str = "document",
        weight_metric: str = "npmi",
        min_weight: float = 0.0,
        max_nodes: int = 80,
        focus: str | None = None,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
    ) -> CooccurrenceResponse:
        kind = "entity" if kind == "entity" else "keyword"
        level = level if level in {"window", "sentence", "document"} else "document"
        weight_metric = weight_metric if weight_metric in {"count", "pmi", "npmi", "jaccard"} else "npmi"
        rows = self._rows(source, category, date_from, date_to, limit)
        docs: list[list[str]] = []
        article_values: list[tuple[dict[str, Any], list[str]]] = []
        for row in rows:
            values = self._entity_values(row) if kind == "entity" else self._keyword_values(row)
            values = list(dict.fromkeys(values))[:20]
            if values:
                docs.append(values)
                article_values.append((row, values))
        nodes, edges, degraded = self._network_metrics_from_docs(docs, kind, weight_metric, max_nodes, min_weight)
        if focus:
            focus_l = focus.lower()
            edges = [edge for edge in edges if focus_l in str(edge["source"]).lower() or focus_l in str(edge["target"]).lower()]
            keep = {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
            nodes = [node for node in nodes if node["id"] in keep or focus_l in str(node["id"]).lower()]
        communities = self._community_summary(nodes)
        article_matches = []
        if focus:
            for row, values in article_values:
                if any(focus.lower() in value.lower() for value in values):
                    article_matches.append({"article_id": row.get("article_id"), "title": row.get("title"), "source": row.get("source"), "category": row.get("category_label"), "matched_terms": ", ".join(values[:8])})
        notes = []
        note = fallback_entity_note(rows) if kind == "entity" else None
        if note:
            notes.append(note)
        if not nodes:
            notes.append("No co-occurrence graph is available for the current filters.")
        return CooccurrenceResponse(
            status="ready" if nodes else ("insufficient_data" if not rows else "ready"),
            total_documents=len(rows),
            kind=kind,
            level=level,
            weight_metric=weight_metric,
            metrics_degraded=degraded,
            nodes=nodes,
            edges=edges,
            communities=communities,
            ego_network=[edge for edge in edges if focus and (edge["source"] == focus or edge["target"] == focus)],
            article_matches=article_matches[:80],
            notes=notes,
        )

    def relationships(
        self,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        entity_type: str | None = None,
        limit: int = 500,
    ) -> RelationshipMiningResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        if entity_type:
            rows = [row for row in rows if any(typ == entity_type for _, typ in fallback_entities_from_row(row))]
        provider_info = EntityExtractionService(self.db).providers()
        entity_frequency = entity_count_rows(rows, 60)
        total_mentions = sum(int(item.get("count", 0)) for item in entity_frequency) or 1
        share = [{**item, "share": round(int(item.get("count", 0)) / total_mentions, 4)} for item in entity_frequency[:30]]
        entity_docs = [list(dict.fromkeys(self._entity_values(row)))[:16] for row in rows if self._entity_values(row)]
        nodes, edges, _ = self._network_metrics_from_docs(entity_docs, "entity", "count", 70, 0)
        source_counts: Counter[tuple[str, str]] = Counter()
        category_counts: Counter[tuple[str, str]] = Counter()
        entity_topic: Counter[tuple[str, str]] = Counter()
        entity_keyword: Counter[tuple[str, str]] = Counter()
        trend: Counter[str] = Counter()
        risk: Counter[str] = Counter()
        for row in rows:
            entities = self._entity_values(row)
            keywords = self._keyword_values(row)[:8]
            topic = self._dominant_assignment(row.get("article_id"), "topic")
            for entity in entities:
                source_counts[(str(row.get("source") or "unknown"), entity)] += 1
                category_counts[(str(row.get("category_label") or "unknown"), entity)] += 1
                if row.get("publish_date"):
                    trend[str(row["publish_date"])[:10]] += 1
                if topic:
                    entity_topic[(entity, topic)] += 1
                for keyword in keywords:
                    entity_keyword[(entity, keyword)] += 1
                if any(word in f"{row.get('title', '')} {row.get('content_clean', '')}".lower() for word in ["risk", "危機", "爭議", "下跌", "調查", "warning"]):
                    risk[entity] += 1
        notes = []
        note = fallback_entity_note(rows)
        if note:
            notes.append(note)
        return RelationshipMiningResponse(
            status="ready" if entity_frequency else ("insufficient_data" if not rows else "ready"),
            total_documents=len(rows),
            active_entity_source=provider_info.active_entity_source,
            entity_frequency=entity_frequency,
            share_of_voice=share,
            entity_network_nodes=nodes,
            entity_network_edges=edges,
            entity_source_matrix=[{"source": src, "entity": ent, "count": count} for (src, ent), count in source_counts.most_common(140)],
            entity_category_matrix=[{"category": cat, "entity": ent, "count": count} for (cat, ent), count in category_counts.most_common(140)],
            entity_topic_links=[{"entity": ent, "topic": topic, "count": count} for (ent, topic), count in entity_topic.most_common(100)],
            entity_keyword_links=[{"entity": ent, "keyword": keyword, "count": count} for (ent, keyword), count in entity_keyword.most_common(120)],
            entity_trend_calendar=[{"date": date, "count": count} for date, count in sorted(trend.items())],
            risk_summary=[{"entity": entity, "risk_mentions": count} for entity, count in risk.most_common(30)],
            notes=notes,
        )

    def bursts(
        self,
        recent_window_days: int = 7,
        baseline_window_days: int = 30,
        min_count: int = 3,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
    ) -> BurstTrendResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        recent_window_days = min(max(recent_window_days, 1), 30)
        baseline_window_days = min(max(baseline_window_days, recent_window_days + 1), 120)
        min_count = max(min_count, 1)
        dated_rows = [row for row in rows if row.get("publish_date")]
        dates = sorted({str(row["publish_date"])[:10] for row in dated_rows})
        if not dates:
            return BurstTrendResponse(status="insufficient_data", total_documents=len(rows), notes=["Publication dates are required for burst detection."])
        recent_dates = set(dates[-recent_window_days:])
        baseline_dates = set(dates[-baseline_window_days:-recent_window_days] or dates[:-recent_window_days])
        recent_counts: Counter[str] = Counter()
        baseline_counts: Counter[str] = Counter()
        daily_counts: Counter[tuple[str, str]] = Counter()
        source_counts: Counter[tuple[str, str]] = Counter()
        volume_by_date: Counter[str] = Counter()
        for row in dated_rows:
            date = str(row["publish_date"])[:10]
            terms = self._keyword_values(row)[:12]
            volume_by_date[date] += 1
            for term in terms:
                daily_counts[(date, term)] += 1
                if date in recent_dates:
                    recent_counts[term] += 1
                    source_counts[(str(row.get("source") or "unknown"), term)] += 1
                elif date in baseline_dates:
                    baseline_counts[term] += 1
        all_terms = set(recent_counts) | set(baseline_counts)
        scored = []
        for term in all_terms:
            recent = recent_counts[term]
            baseline = baseline_counts[term]
            if recent < min_count and baseline < min_count:
                continue
            recent_rate = recent / max(len(recent_dates), 1)
            baseline_rate = baseline / max(len(baseline_dates), 1)
            growth = (recent_rate + 0.1) / (baseline_rate + 0.1)
            z_score = (recent - baseline_rate * len(recent_dates)) / math.sqrt(max(baseline_rate * len(recent_dates), 1))
            scored.append({"term": term, "recent_count": recent, "baseline_count": baseline, "growth_rate": round(growth, 4), "z_score": round(z_score, 4), "lifecycle": self._lifecycle(growth, recent, baseline)})
        rising = sorted(scored, key=lambda item: (item["growth_rate"], item["recent_count"]), reverse=True)[:30]
        declining = sorted(scored, key=lambda item: (item["growth_rate"], -item["baseline_count"]))[:30]
        burst_terms = [item for item in rising if item["z_score"] >= 2.0 or item["growth_rate"] >= 2.0][:30]
        values = list(volume_by_date.values())
        avg = sum(values) / max(len(values), 1)
        stdev = math.sqrt(sum((value - avg) ** 2 for value in values) / max(len(values), 1)) or 1
        anomaly = [{"date": date, "count": count, "z_score": round((count - avg) / stdev, 4), "is_anomaly": abs((count - avg) / stdev) >= 2.0} for date, count in sorted(volume_by_date.items())]
        return BurstTrendResponse(
            status="ready" if scored else ("insufficient_data" if not rows else "ready"),
            total_documents=len(rows),
            recent_window_days=recent_window_days,
            baseline_window_days=baseline_window_days,
            rising_terms=rising,
            declining_terms=declining,
            burst_terms=burst_terms,
            anomaly_timeline=anomaly,
            calendar=[{"date": date, "count": count} for date, count in sorted(volume_by_date.items())],
            source_bursts=[{"source": src, "term": term, "count": count} for (src, term), count in source_counts.most_common(80)],
            lifecycle=sorted(scored, key=lambda item: item["recent_count"], reverse=True)[:60],
            notes=[] if scored else ["Not enough dated keyword observations for burst detection."],
        )

    def entities(
        self,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        entity_type: str | None = None,
        entity: str | None = None,
        limit: int = 500,
    ) -> EntityMiningResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        if entity_type:
            rows = [row for row in rows if any(typ == entity_type for _, typ in fallback_entities_from_row(row))]
        if entity:
            target = entity.lower()
            rows = [row for row in rows if any(target in value.lower() for value, _ in fallback_entities_from_row(row))]

        entity_frequency = entity_count_rows(rows, 50)
        type_counts: Counter[str] = Counter()
        trend_counts: Counter[tuple[str, str, str]] = Counter()
        source_counts: Counter[tuple[str, str, str]] = Counter()
        category_counts: Counter[tuple[str, str, str]] = Counter()
        docs: list[list[str]] = []
        representatives: list[dict[str, Any]] = []

        for row in rows:
            entities = fallback_entities_from_row(row)
            if not entities:
                continue
            values = list(dict.fromkeys(entity for entity, _ in entities))[:12]
            docs.append(values)
            for value, typ in entities:
                type_counts[typ] += 1
                if row.get("publish_date"):
                    trend_counts[(str(row["publish_date"])[:10], value, typ)] += 1
                source_counts[(str(row.get("source") or "unknown"), value, typ)] += 1
                category_counts[(str(row.get("category_label") or "unknown"), value, typ)] += 1
            representatives.append({
                "article_id": row.get("article_id"),
                "title": row.get("title"),
                "source": row.get("source"),
                "category": row.get("category_label"),
                "publish_date": row.get("publish_date"),
                "entities": ", ".join(values[:6]),
            })

        nodes, edges = self._network_from_docs(docs, "entity")
        notes: list[str] = []
        note = fallback_entity_note(rows)
        if note:
            notes.append(note)
        if not entity_frequency:
            notes.append("No entities matched the current corpus filters.")
        provider_info = EntityExtractionService(self.db).providers()

        return EntityMiningResponse(
            status="ready" if rows else "insufficient_data",
            total_documents=len(rows),
            active_entity_source=provider_info.active_entity_source,
            active_run_id=provider_info.active_run_id,
            provider_status=[item.model_dump() for item in provider_info.providers],
            entity_frequency=entity_frequency,
            entity_type_distribution=[{"type": typ, "count": count} for typ, count in type_counts.most_common()],
            entity_trend=[{"date": date, "entity": value, "type": typ, "count": count} for (date, value, typ), count in trend_counts.most_common(120)],
            entity_source_matrix=[{"source": source_name, "entity": value, "type": typ, "count": count} for (source_name, value, typ), count in source_counts.most_common(120)],
            entity_category_matrix=[{"category": category_name, "entity": value, "type": typ, "count": count} for (category_name, value, typ), count in category_counts.most_common(120)],
            cooccurrence_nodes=nodes,
            cooccurrence_edges=edges,
            representative_articles=representatives[:40],
            notes=notes,
        )

    def persist_assignments(
        self,
        assignment_type: str = "both",
        topic_method: str = "nmf",
        cluster_method: str = "kmeans",
        n_topics: int = 5,
        n_clusters: int = 5,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
    ) -> AssignmentRunResponse:
        assignment_type = assignment_type if assignment_type in {"topic", "cluster", "both"} else "both"
        run_id = f"text-assign-{uuid.uuid4().hex[:10]}"
        params = {
            "assignment_type": assignment_type,
            "topic_method": topic_method,
            "cluster_method": cluster_method,
            "n_topics": n_topics,
            "n_clusters": n_clusters,
            "source": source,
            "category": category,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
        }
        notes: list[str] = []
        labels: dict[str, list[dict[str, Any]]] = {"topic": [], "cluster": []}
        counts: Counter[str] = Counter()
        total_documents = 0
        self.db.execute(
            """
            INSERT OR REPLACE INTO text_mining_runs
            (run_id, assignment_type, method, params_json, status, summary_json)
            VALUES (?, ?, ?, ?, 'running', '{}')
            """,
            (run_id, assignment_type, f"topic:{topic_method}|cluster:{cluster_method}", json.dumps(params, ensure_ascii=False)),
        )

        if assignment_type in {"topic", "both"}:
            topic_result = self.topics(topic_method, n_topics, source, category, date_from, date_to, limit)
            total_documents = max(total_documents, topic_result.total_documents)
            notes.extend(topic_result.notes)
            if topic_result.status == "ready":
                for topic in topic_result.topics:
                    label = f"topic_{topic.get('topic_id')}"
                    terms = topic.get("top_terms", [])
                    labels["topic"].append({"label": label, "terms": terms, "documents": len(topic.get("top_docs", []))})
                    for doc in topic.get("top_docs", []):
                        self._insert_assignment(run_id, "topic", str(doc.get("article_id")), label, float(doc.get("weight") or 0), terms)
                        counts["topic"] += 1
            else:
                notes.append(f"Topic assignment skipped: {topic_result.status}.")

        if assignment_type in {"cluster", "both"}:
            cluster_result = self.clusters(cluster_method, n_clusters, source, category, date_from, date_to, limit)
            total_documents = max(total_documents, cluster_result.total_documents)
            notes.extend(cluster_result.notes)
            if cluster_result.status == "ready":
                for cluster in cluster_result.clusters:
                    label = f"cluster_{cluster.get('cluster_id')}"
                    terms = cluster.get("top_terms", [])
                    labels["cluster"].append({"label": label, "terms": terms, "documents": len(cluster.get("examples", [])), "size": cluster.get("size")})
                    for doc in cluster.get("examples", []):
                        self._insert_assignment(run_id, "cluster", str(doc.get("article_id")), label, 1.0, terms)
                        counts["cluster"] += 1
            else:
                notes.append(f"Cluster assignment skipped: {cluster_result.status}.")

        status = "ready" if counts else "insufficient_data"
        summary = {"assignment_counts": dict(counts), "labels": labels, "notes": notes}
        self.db.execute(
            """
            UPDATE text_mining_runs
            SET status = ?, summary_json = ?
            WHERE run_id = ?
            """,
            (status, json.dumps(summary, ensure_ascii=False), run_id),
        )
        row = self.db.fetch_one("SELECT created_at FROM text_mining_runs WHERE run_id = ?", (run_id,))
        return AssignmentRunResponse(
            status=status,
            total_documents=total_documents,
            notes=notes,
            run_id=run_id,
            assignment_type=assignment_type,
            method=f"topic:{topic_method}|cluster:{cluster_method}",
            assignment_counts=dict(counts),
            labels=labels,
            created_at=row["created_at"] if row else None,
        )

    def latest_assignments(self, limit: int = 200) -> AssignmentListResponse:
        runs = [dict(row) for row in self.db.fetch_all(
            """
            SELECT run_id, assignment_type, method, status, summary_json, created_at
            FROM text_mining_runs
            ORDER BY datetime(created_at) DESC
            LIMIT 10
            """
        )]
        latest = runs[0]["run_id"] if runs else ""
        assignments = []
        if latest:
            assignments = [dict(row) for row in self.db.fetch_all(
                """
                SELECT assignment_type, article_id, label, score, terms_json, created_at
                FROM text_mining_assignments
                WHERE run_id = ?
                ORDER BY assignment_type, label, score DESC
                LIMIT ?
                """,
                (latest, min(max(limit, 1), 1000)),
            )]
        for run in runs:
            run["summary"] = decode_json(run.pop("summary_json", None), {})
        for item in assignments:
            item["terms"] = decode_json(item.pop("terms_json", None), [])
        return AssignmentListResponse(
            status="ready" if runs else "insufficient_data",
            total_documents=len(assignments),
            runs=runs,
            assignments=assignments,
            notes=[] if runs else ["Persist topic/cluster assignments before using assignment facets."],
        )

    def article_assignments(self, article_id: str) -> AssignmentListResponse:
        latest = self.db.fetch_one(
            """
            SELECT run_id, assignment_type, method, status, summary_json, created_at
            FROM text_mining_runs
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """
        )
        if not latest:
            return AssignmentListResponse(status="insufficient_data", notes=["No persisted topic or cluster assignments are available."])
        rows = [dict(row) for row in self.db.fetch_all(
            """
            SELECT assignment_type, article_id, label, score, terms_json, created_at
            FROM text_mining_assignments
            WHERE run_id = ? AND article_id = ?
            ORDER BY assignment_type, score DESC
            """,
            (latest["run_id"], article_id),
        )]
        for row in rows:
            row["terms"] = decode_json(row.pop("terms_json", None), [])
        run = dict(latest)
        run["summary"] = decode_json(run.pop("summary_json", None), {})
        return AssignmentListResponse(status="ready" if rows else "insufficient_data", total_documents=len(rows), runs=[run], assignments=rows, notes=[] if rows else ["This article is not included in the latest assignment run."])

    def export(self, section: str, fmt: str, **filters: Any) -> tuple[str, str, str]:
        dispatch = {
            "overview": lambda: self.overview(**filters).model_dump(),
            "tfidf": lambda: self.tfidf(**filters).model_dump(),
            "ngrams": lambda: self.ngrams(**filters).model_dump(),
            "topics": lambda: self.topics(**filters).model_dump(),
            "clusters": lambda: self.clusters(**filters).model_dump(),
            "network": lambda: self.network(**filters).model_dump(),
            "entities": lambda: self.entities(**filters).model_dump(),
            "collocations": lambda: self.collocations(**filters).model_dump(),
            "co_occurrence": lambda: self.co_occurrence(**filters).model_dump(),
            "relationships": lambda: self.relationships(**filters).model_dump(),
            "bursts": lambda: self.bursts(**filters).model_dump(),
        }
        payload = dispatch.get(section, dispatch["overview"])()
        if fmt == "csv":
            from io import StringIO
            out = StringIO()
            rows = self._flatten(payload)
            if rows:
                writer = csv.DictWriter(out, fieldnames=sorted({k for row in rows for k in row}))
                writer.writeheader()
                writer.writerows(rows)
            return out.getvalue(), "text/csv; charset=utf-8", f"text-mining-{section}.csv"
        if fmt == "markdown":
            lines = [f"# Text Mining {section.title()}", ""]
            for key, value in payload.items():
                lines.append(f"## {key}")
                lines.append(json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value)
                lines.append("")
            return "\n".join(lines), "text/markdown; charset=utf-8", f"text-mining-{section}.md"
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json; charset=utf-8", f"text-mining-{section}.json"

    def _insert_assignment(self, run_id: str, assignment_type: str, article_id: str, label: str, score: float, terms: list[dict[str, Any]]) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO text_mining_assignments
            (run_id, assignment_type, article_id, label, score, terms_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, assignment_type, article_id, label, score, json.dumps(terms, ensure_ascii=False)),
        )

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
        rows = self.db.fetch_all(
            f"""
            SELECT a.article_id, a.title, a.source, a.category, a.category_name,
                   COALESCE(NULLIF(a.category_name, ''), NULLIF(a.category, ''), 'unknown') AS category_label,
                   a.publish_date, a.content_clean, n.tokens, n.keywords, n.entities
            FROM articles a
            LEFT JOIN nlp_outputs n ON n.article_id = a.article_id
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
            LIMIT ?
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

    def _documents(self, rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        docs, ids = [], []
        for row in rows:
            tokens = self._safe_json(row["tokens"], [])
            if tokens:
                docs.append(" ".join(str(t) for t in tokens))
                ids.append(row["article_id"])
        return docs, ids

    def _keyword_counts(self, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        for row in rows:
            keywords = self._safe_json(row["keywords"], [])
            if keywords:
                for item in keywords:
                    if isinstance(item, (list, tuple)) and item:
                        counts[str(item[0])] += float(item[1] or 1) if len(item) > 1 else 1
            else:
                tokens = self._safe_json(row["tokens"], [])
                counts.update(str(token) for token in tokens if len(str(token)) > 1)
        return [{"keyword": key, "score": round(value, 4)} for key, value in counts.most_common(limit)]

    def _entity_counts(self, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        return entity_count_rows(rows, limit)

    def _ngram_counts(self, rows: list[dict[str, Any]], n: int, limit: int) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        for row in rows:
            tokens = [str(token) for token in self._safe_json(row["tokens"], []) if len(str(token)) > 1]
            for idx in range(0, max(0, len(tokens) - n + 1)):
                counts[" ".join(tokens[idx:idx + n])] += 1
        return [{"ngram": key, "count": count} for key, count in counts.most_common(limit)]

    def _ngram_profile(self, rows: list[dict[str, Any]], n: int, group_key: str, limit: int) -> list[dict[str, Any]]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            group = str(row.get(group_key) or "unknown")
            tokens = [str(token) for token in self._safe_json(row["tokens"], []) if len(str(token)) > 1]
            for idx in range(0, max(0, len(tokens) - n + 1)):
                counts[(group, " ".join(tokens[idx:idx + n]))] += 1
        label = "category" if group_key == "category_label" else group_key
        return [{label: group, "ngram": ngram, "count": count} for (group, ngram), count in counts.most_common(limit)]

    def _keyword_values(self, row: dict[str, Any]) -> list[str]:
        keywords = self._safe_json(row.get("keywords"), [])
        values: list[str] = []
        if keywords:
            for item in keywords:
                if isinstance(item, (list, tuple)) and item:
                    values.append(str(item[0]))
                elif isinstance(item, str):
                    values.append(item)
        if not values:
            values = [str(token) for token in self._safe_json(row.get("tokens"), []) if len(str(token)) > 1]
        return [value for value in values if value and len(value) > 1]

    def _entity_values(self, row: dict[str, Any]) -> list[str]:
        return [entity for entity, _ in fallback_entities_from_row(row) if entity]

    def _cooccurrence_units(self, row: dict[str, Any], level: str, window_size: int) -> list[list[str]]:
        tokens = [str(token) for token in self._safe_json(row.get("tokens"), []) if len(str(token)) > 1]
        if not tokens:
            content = str(row.get("content_clean") or row.get("title") or "")
            tokens = [token for token in re.split(r"\s+", content) if len(token) > 1]
        if not tokens:
            return []
        if level == "document":
            return [tokens]
        if level == "window":
            return [tokens[index:index + window_size] for index in range(0, max(1, len(tokens) - window_size + 1))]
        content = str(row.get("content_clean") or "")
        raw_sentences = [part.strip() for part in re.split(r"[。！？.!?\n]+", content) if part.strip()]
        if len(raw_sentences) <= 1 or " " not in content:
            return [tokens]
        units = [[token for token in re.split(r"\s+", sentence) if len(token) > 1] for sentence in raw_sentences]
        return [unit for unit in units if unit] or [tokens]

    def _pairs_for_unit(self, tokens: list[str], level: str, window_size: int) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        if level == "window":
            for idx, a in enumerate(tokens):
                for b in tokens[idx + 1:idx + window_size]:
                    if a != b:
                        pairs.append(tuple(sorted((a, b))))
            return pairs
        for a, b in combinations(sorted(set(tokens)), 2):
            pairs.append((a, b))
        return pairs

    def _score_collocation_pairs(self, pair_counts: Counter[tuple[str, str]], unigram_counts: Counter[str], total_tokens: int, total_units: int) -> list[dict[str, Any]]:
        total_tokens = max(total_tokens, 1)
        total_units = max(total_units, 1)
        rows = []
        for (a, b), count in pair_counts.items():
            freq_a = unigram_counts[a]
            freq_b = unigram_counts[b]
            expected = (freq_a * freq_b) / total_tokens
            p_ab = count / total_units
            p_a = freq_a / total_tokens
            p_b = freq_b / total_tokens
            pmi = math.log2(p_ab / max(p_a * p_b, 1e-12)) if p_ab > 0 else 0
            ppmi = max(pmi, 0)
            npmi_denominator = -math.log2(max(min(p_ab, 1 - 1e-12), 1e-12))
            npmi = pmi / npmi_denominator if p_ab > 0 and npmi_denominator else 0
            dice = (2 * count) / max(freq_a + freq_b, 1)
            t_score = (count - expected) / math.sqrt(max(count, 1))
            rows.append({
                "term_a": a,
                "term_b": b,
                "collocation": f"{a} {b}",
                "count": int(count),
                "frequency": int(count),
                "pmi": round(pmi, 6),
                "ppmi": round(ppmi, 6),
                "npmi": round(npmi, 6),
                "log_likelihood": round(self._log_likelihood(count, freq_a, freq_b, total_tokens), 6),
                "dice": round(dice, 6),
                "t_score": round(t_score, 6),
                "freq_a": int(freq_a),
                "freq_b": int(freq_b),
            })
        return rows

    def _score_trigrams(self, trigram_counts: Counter[tuple[str, str, str]], unigram_counts: Counter[str], total_tokens: int) -> list[dict[str, Any]]:
        rows = []
        for (a, b, c), count in trigram_counts.items():
            avg_freq = (unigram_counts[a] + unigram_counts[b] + unigram_counts[c]) / 3
            score = count / max(avg_freq, 1)
            rows.append({
                "term_a": a,
                "term_b": b,
                "term_c": c,
                "collocation": f"{a} {b} {c}",
                "count": int(count),
                "frequency": int(count),
                "pmi": round(math.log2((count / max(total_tokens, 1)) / max((unigram_counts[a] / max(total_tokens, 1)) * (unigram_counts[b] / max(total_tokens, 1)) * (unigram_counts[c] / max(total_tokens, 1)), 1e-12)), 6),
                "ppmi": round(max(score, 0), 6),
                "npmi": round(score, 6),
                "log_likelihood": round(score * count, 6),
                "dice": round((3 * count) / max(unigram_counts[a] + unigram_counts[b] + unigram_counts[c], 1), 6),
                "t_score": round((count - avg_freq / 3) / math.sqrt(max(count, 1)), 6),
            })
        return rows

    def _log_likelihood(self, observed: int, freq_a: int, freq_b: int, total: int) -> float:
        expected = max((freq_a * freq_b) / max(total, 1), 1e-12)
        if observed <= 0:
            return 0.0
        return 2 * observed * math.log(observed / expected)

    def _collocation_key(self, item: dict[str, Any]) -> str:
        terms = [str(item.get("term_a") or ""), str(item.get("term_b") or ""), str(item.get("term_c") or "")]
        return " ".join(term for term in terms if term)

    def _article_collocation_hits(self, row: dict[str, Any], units: list[list[str]], ngram_type: str, selected_terms: set[str], level: str, window_size: int) -> set[str]:
        hits: set[str] = set()
        for unit in units:
            tokens = [token for token in unit if len(token) > 1]
            if ngram_type == "trigram":
                for idx in range(0, max(0, len(tokens) - 2)):
                    key = " ".join(tokens[idx:idx + 3])
                    if key in selected_terms:
                        hits.add(key)
            else:
                for a, b in self._pairs_for_unit(tokens, level, window_size):
                    key = f"{a} {b}"
                    if key in selected_terms:
                        hits.add(key)
        return hits

    def _network_metrics_from_docs(self, docs: list[list[str]], kind: str, weight_metric: str, max_nodes: int, min_weight: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        node_counts: Counter[str] = Counter()
        edge_counts: Counter[tuple[str, str]] = Counter()
        doc_counts: Counter[str] = Counter()
        for values in docs:
            uniq = sorted(set(values))
            node_counts.update(uniq)
            doc_counts.update(uniq)
            for a, b in combinations(uniq, 2):
                edge_counts[(a, b)] += 1
        total_docs = max(len(docs), 1)
        scored_edges = []
        for (a, b), count in edge_counts.items():
            if weight_metric == "jaccard":
                weight = count / max(doc_counts[a] + doc_counts[b] - count, 1)
            elif weight_metric in {"pmi", "npmi"}:
                p_ab = count / total_docs
                p_a = doc_counts[a] / total_docs
                p_b = doc_counts[b] / total_docs
                pmi = math.log2(p_ab / max(p_a * p_b, 1e-12)) if p_ab > 0 else 0
                npmi_denominator = -math.log2(max(min(p_ab, 1 - 1e-12), 1e-12))
                weight = pmi / npmi_denominator if weight_metric == "npmi" and p_ab > 0 and npmi_denominator else pmi
            else:
                weight = float(count)
            if weight >= min_weight:
                scored_edges.append((a, b, count, weight))
        allowed_nodes = {node for node, _ in node_counts.most_common(max_nodes)}
        scored_edges = [(a, b, count, weight) for a, b, count, weight in scored_edges if a in allowed_nodes and b in allowed_nodes]
        degraded = False
        graph_metrics: dict[str, dict[str, float | int]] = defaultdict(dict)
        try:
            import networkx as nx

            graph = nx.Graph()
            for node in allowed_nodes:
                graph.add_node(node)
            for a, b, count, weight in scored_edges:
                graph.add_edge(a, b, weight=weight, count=count)
            degree_c = nx.degree_centrality(graph)
            between = nx.betweenness_centrality(graph, weight="weight", normalized=True) if graph.number_of_edges() else {}
            eigen = nx.eigenvector_centrality_numpy(graph, weight="weight") if graph.number_of_nodes() > 1 and graph.number_of_edges() else {}
            core = nx.core_number(graph) if graph.number_of_edges() else {}
            communities = list(nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")) if graph.number_of_edges() else []
            community_map = {node: idx for idx, group in enumerate(communities) for node in group}
            for node in allowed_nodes:
                graph_metrics[node] = {
                    "centrality": round(float(degree_c.get(node, 0)), 6),
                    "betweenness": round(float(between.get(node, 0)), 6),
                    "eigenvector": round(float(eigen.get(node, 0)), 6),
                    "k_core": int(core.get(node, 0)),
                    "community": int(community_map.get(node, 0)),
                }
        except Exception:
            degraded = True
            weighted_degree: Counter[str] = Counter()
            for a, b, _, weight in scored_edges:
                weighted_degree[a] += weight
                weighted_degree[b] += weight
            max_degree = max(max(weighted_degree.values(), default=0), 1)
            for node in allowed_nodes:
                graph_metrics[node] = {
                    "centrality": round(float(weighted_degree[node] / max_degree), 6),
                    "betweenness": 0,
                    "eigenvector": 0,
                    "k_core": 0,
                    "community": 0,
                }
        weighted_degree_counts: Counter[str] = Counter()
        for a, b, count, _ in scored_edges:
            weighted_degree_counts[a] += count
            weighted_degree_counts[b] += count
        nodes = []
        for node in allowed_nodes:
            metrics = graph_metrics[node]
            nodes.append({
                "id": node,
                "label": node,
                "count": int(node_counts[node]),
                "degree": int(weighted_degree_counts[node]),
                "weighted_degree": int(weighted_degree_counts[node]),
                "centrality": metrics.get("centrality", 0),
                "betweenness": metrics.get("betweenness", 0),
                "eigenvector": metrics.get("eigenvector", 0),
                "k_core": metrics.get("k_core", 0),
                "community": metrics.get("community", 0),
                "category": "Entity" if kind == "entity" else "Keyword",
                "value": int(node_counts[node]),
                "symbolSize": max(14, min(60, 14 + int(weighted_degree_counts[node]) * 2)),
            })
        nodes.sort(key=lambda item: (item["degree"], item["count"]), reverse=True)
        edges = [
            {"source": a, "target": b, "count": int(count), "weight": round(float(weight), 6), "value": round(float(weight), 6), "metric": weight_metric}
            for a, b, count, weight in sorted(scored_edges, key=lambda item: (item[3], item[2]), reverse=True)[:160]
        ]
        return nodes, edges, degraded

    def _community_summary(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: Counter[int] = Counter(int(node.get("community", 0)) for node in nodes)
        return [{"community": community, "nodes": count} for community, count in counts.most_common()]

    def _dominant_assignment(self, article_id: Any, assignment_type: str) -> str:
        if not article_id:
            return ""
        row = self.db.fetch_one(
            """
            SELECT label
            FROM text_mining_assignments
            WHERE article_id = ? AND assignment_type = ?
            ORDER BY score DESC, created_at DESC
            LIMIT 1
            """,
            (str(article_id), assignment_type),
        )
        return str(row["label"]) if row else ""

    def _lifecycle(self, growth: float, recent: int, baseline: int) -> str:
        if recent > 0 and baseline == 0:
            return "emerging"
        if growth >= 1.5:
            return "growing"
        if growth <= 0.7:
            return "declining"
        return "mature"

    def _network_from_docs(self, docs: list[list[str]], kind: str = "keyword") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        node_counts: Counter[str] = Counter()
        edge_counts: Counter[tuple[str, str]] = Counter()
        for values in docs:
            node_counts.update(values)
            for a, b in combinations(sorted(values), 2):
                edge_counts[(a, b)] += 1
        degree: defaultdict[str, int] = defaultdict(int)
        for (a, b), weight in edge_counts.items():
            degree[a] += weight
            degree[b] += weight
        max_degree = max(degree.values(), default=1)
        nodes = [
            {
                "id": node,
                "label": node,
                "count": count,
                "degree": degree[node],
                "value": count,
                "centrality": round(degree[node] / max_degree, 4) if max_degree else 0,
                "category": "Entity" if kind == "entity" else "Keyword",
                "symbolSize": max(14, min(56, 14 + degree[node] * 2)),
            }
            for node, count in node_counts.most_common(50)
        ]
        allowed = {node["id"] for node in nodes}
        edges = [{"source": a, "target": b, "weight": weight, "value": weight} for (a, b), weight in edge_counts.most_common(100) if a in allowed and b in allowed]
        return nodes, edges

    def _cluster_projection_points(self, clusterer: Any, labels: Any, meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        if getattr(clusterer, "_dtm", None) is None:
            return []
        doc_ids = list(getattr(clusterer, "_doc_ids", []))
        if not doc_ids:
            return []
        try:
            from sklearn.decomposition import TruncatedSVD

            matrix = clusterer._dtm
            if matrix.shape[1] > 1:
                coords = TruncatedSVD(n_components=2, random_state=42).fit_transform(matrix)
            else:
                coords = [[float(index), 0.0] for index in range(len(doc_ids))]
        except Exception:
            coords = [[float(index % 12), float(index // 12)] for index in range(len(doc_ids))]

        points = []
        for index, article_id in enumerate(doc_ids):
            row = meta.get(article_id, {})
            x, y = coords[index]
            points.append({
                "article_id": article_id,
                "title": row.get("title", ""),
                "cluster_id": int(labels[index]) if index < len(labels) else 0,
                "x": round(float(x), 6),
                "y": round(float(y), 6),
                "source": row.get("source", ""),
                "category": row.get("category_label", ""),
            })
        return points

    def _flatten(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    rows.append({"section": key, **item} if isinstance(item, dict) else {"section": key, "value": str(item)})
            elif isinstance(value, dict):
                rows.append({"section": key, **value})
            else:
                rows.append({"section": key, "value": str(value)})
        return rows
