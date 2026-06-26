#!/usr/bin/env python
"""
Pipeline CLI — full data engineering + analysis workflow.

Usage:
    # ── Data Pipeline ──────────────────────────────────
    python pipeline_cli.py run-all --engine ckip

    # ── CKIP NLP ───────────────────────────────────────
    python pipeline_cli.py nlp --engine ckip --batch-size 64

    # ── Collocation Analysis ──────────────────────────
    python pipeline_cli.py collocation --method pmi --topk 100

    # ── Text Mining ────────────────────────────────────
    python pipeline_cli.py text-mining --topics 10 --method nmf

    # ── Clustering ─────────────────────────────────────
    python pipeline_cli.py cluster --method kmeans --n-clusters 8

    # ── Sentiment Analysis ─────────────────────────────
    python pipeline_cli.py sentiment --limit 1000

    # ── Time Series ────────────────────────────────────
    python pipeline_cli.py time-series --bin month

    # ── Summarization ──────────────────────────────────
    python pipeline_cli.py summarize --doc-id 123 --method mmr

    # ── Stats ──────────────────────────────────────────
    python pipeline_cli.py stats
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from pipeline.db import NewsDB
from pipeline.schema import RawArticle, CleanArticle, EnrichedArticle
from pipeline.text_cleaner import normalize
from pipeline.validator import merge_jsonl_files
from nlp.ckip_pipeline import CKIPPipeline, CKIPResult
from nlp.pipeline import NLPPipeline
from features.tfidf import TfidfBuilder
from exports.exporter import Exporter
from analysis.collocation import CollocationAnalyzer
from analysis.text_mining import TextMiningAnalyzer
from analysis.clustering import DocumentClusterer
from analysis.classification import NewsClassifier, SentimentAnalyzer
from analysis.summarization import Summarizer
from analysis.time_series import TimeSeriesAnalyzer
from utils.resource_manager import ResourceManager
from app.services.entity_extraction import EntityExtractionService
from app.services.database import Database

DATA_DIR = os.getenv("NEWS_DATA_DIR", "data")
DB_PATH = os.getenv("NEWS_DB_PATH", f"{DATA_DIR}/news.db")
RAW_DIR = os.getenv("NEWS_RAW_DIR", f"{DATA_DIR}/raw")
PROCESSED_DIR = os.getenv("NEWS_PROCESSED_DIR", f"{DATA_DIR}/processed")
MODELS_DIR = os.getenv("NEWS_MODELS_DIR", f"{DATA_DIR}/models")
FEATURES_DIR = os.getenv("NEWS_FEATURES_DIR", f"{DATA_DIR}/features")
REPORTS_DIR = os.getenv("NEWS_REPORTS_DIR", f"{DATA_DIR}/reports")
EXPORTS_DIR = os.getenv("NEWS_EXPORTS_DIR", f"{DATA_DIR}/exports")
SAMPLE_DATASET = Path(__file__).parent / "sample_data" / "news_sample.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline_cli")


# ===========================================================================
# Resource Manager (shared)
# ===========================================================================
def get_rm(args) -> ResourceManager:
    return ResourceManager(
        max_ram_gb=getattr(args, "max_ram", 4.0),
        max_threads=getattr(args, "max_threads", 32),
    )


# ===========================================================================
# Commands
# ===========================================================================

def cmd_ingest(args):
    db = NewsDB(args.db or DB_PATH)
    db.init()
    input_dir = Path(args.input_dir or RAW_DIR)
    output = Path(PROCESSED_DIR) / "merged_raw.jsonl"
    stats = merge_jsonl_files(input_dir, output, pattern="*.jsonl")
    result = db.insert_raw_articles(output, batch_size=args.batch_size)
    print(f"\nIngest: {result}")
    for k, v in db.stats().items():
        print(f"  {k}: {v}")


def ensure_data_dirs(data_dir: str | Path = DATA_DIR) -> dict[str, Path]:
    """建立 demo pipeline 需要的資料目錄。"""
    root = Path(data_dir)
    dirs = {
        "raw": Path(RAW_DIR),
        "processed": Path(PROCESSED_DIR),
        "features": Path(FEATURES_DIR),
        "models": Path(MODELS_DIR),
        "reports": Path(REPORTS_DIR),
        "exports": Path(EXPORTS_DIR),
    }
    for path in [root, *dirs.values()]:
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _reset_sqlite(db_path: str | Path) -> None:
    base = Path(db_path)
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{base}{suffix}")
        if path.exists():
            path.unlink()


def _write_demo_reports(db_path: str | Path, reports_dir: str | Path = REPORTS_DIR) -> None:
    """輸出前端可直接讀取的輕量 demo 分析報表。"""
    db = NewsDB(db_path)
    db.connect()
    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_rows = db._conn.execute(
        "SELECT COALESCE(source, 'unknown') AS source, COUNT(*) AS count FROM articles GROUP BY source ORDER BY count DESC"
    ).fetchall()
    category_rows = db._conn.execute(
        "SELECT COALESCE(NULLIF(category_name, ''), COALESCE(category, 'unknown')) AS category, COUNT(*) AS count "
        "FROM articles GROUP BY category ORDER BY count DESC"
    ).fetchall()
    date_rows = db._conn.execute(
        "SELECT substr(publish_date, 1, 10) AS date, COUNT(*) AS count FROM articles "
        "WHERE publish_date IS NOT NULL AND trim(publish_date) != '' GROUP BY date ORDER BY date"
    ).fetchall()
    length_row = db._conn.execute(
        "SELECT MIN(char_count), AVG(char_count), MAX(char_count) FROM articles"
    ).fetchone()
    nlp_rows = db._conn.execute("SELECT keywords, tokens FROM nlp_outputs").fetchall()

    keyword_counts: Counter[str] = Counter()
    for row in nlp_rows:
        try:
            keywords = json.loads(row["keywords"] or "[]")
            tokens = json.loads(row["tokens"] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue
        if keywords:
            for term, score in keywords:
                keyword_counts[str(term)] += float(score or 1)
        else:
            keyword_counts.update(str(token) for token in tokens if len(str(token)) > 1)

    by_month: dict[str, int] = defaultdict(int)
    for row in date_rows:
        if row["date"]:
            by_month[str(row["date"])[:7]] += int(row["count"])

    text_mining = {
        "summary": "Demo keyword and coverage report generated from sample news data.",
        "top_keywords": [{"keyword": k, "score": round(v, 4)} for k, v in keyword_counts.most_common(20)],
        "source_distribution": [dict(row) for row in source_rows],
        "category_distribution": [dict(row) for row in category_rows],
    }
    time_series = {
        "summary": "Demo article volume trend by publish date.",
        "daily_volume": [dict(row) for row in date_rows],
        "monthly_volume": [{"month": k, "count": v} for k, v in sorted(by_month.items())],
    }
    sentiment = {
        "summary": "Rule-based sentiment is not enabled in Phase 1 demo.",
        "distribution": [{"label": "neutral", "count": db.stats().get("total_articles", 0)}],
    }
    analysis_report = {
        "summary": "Sample dataset analysis report.",
        "sources": text_mining["source_distribution"],
        "categories": text_mining["category_distribution"],
        "top_keywords": text_mining["top_keywords"],
        "daily_volume": time_series["daily_volume"],
        "article_length": {
            "min": int(length_row[0] or 0),
            "avg": round(float(length_row[1] or 0), 1),
            "max": int(length_row[2] or 0),
        },
    }

    for filename, payload in {
        "text_mining.json": text_mining,
        "time_series.json": time_series,
        "sentiment_report.json": sentiment,
        "analysis_report.json": analysis_report,
    }.items():
        (out_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    db.close()


def cmd_demo(args):
    """建立可展示的 sample news pipeline 閉環。"""
    dirs = ensure_data_dirs()
    db_path = args.db or DB_PATH
    if args.reset:
        _reset_sqlite(db_path)

    sample = Path(args.sample or SAMPLE_DATASET)
    if not sample.exists():
        raise FileNotFoundError(f"Sample dataset not found: {sample}")

    target = dirs["raw"] / sample.name
    shutil.copyfile(sample, target)
    logger.info("Copied sample dataset to %s", target)

    cmd_ingest(argparse.Namespace(db=db_path, input_dir=str(dirs["raw"]), batch_size=200))
    cmd_nlp(argparse.Namespace(
        db=db_path, engine="jieba", top_k=10, stopwords=None,
        batch_size=32, max_ram=args.max_ram, max_threads=args.max_threads,
    ))
    _write_demo_reports(db_path, dirs["reports"])
    cmd_stats(argparse.Namespace(db=db_path))
    logger.info("Demo pipeline complete. Reports written to %s", dirs["reports"])


def cmd_nlp(args):
    """NLP enrichment with CKIP (GPU-accelerated, batched)."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()
    rm = get_rm(args)
    rm.log_ram_status("NLP start")

    device_id = rm.get_cuda_device_id()
    engine = args.engine or "ckip"

    if engine == "ckip":
        nlp = CKIPPipeline(device_id=device_id)
    else:
        nlp = NLPPipeline(engine="jieba", top_keywords=args.top_k or 10)

    if args.stopwords:
        if hasattr(nlp, 'load_stopwords'):
            nlp.load_stopwords(args.stopwords)

    rows = db._conn.execute(
        "SELECT article_id, content_clean, title_clean FROM articles "
        "WHERE status='cleaned' AND article_id NOT IN (SELECT article_id FROM nlp_outputs)"
    ).fetchall()

    if not rows:
        logger.info("No articles need NLP processing")
        return

    logger.info(f"Processing {len(rows):,} articles with {engine} on {rm.get_device()}...")

    def process_batch(batch_rows):
        texts = [f"{r['title_clean'] or ''} {r['content_clean'] or ''}" for r in batch_rows]
        if engine == "ckip":
            return nlp.process_batch(texts)
        else:
            return [nlp.process(t) for t in texts]

    results = rm.process_in_batches(rows, process_batch,
                                    batch_size=args.batch_size, desc="NLP")

    processed = 0
    for row, result in zip(rows, results):
        aid = row["article_id"]
        if engine == "ckip":
            enriched = EnrichedArticle(
                article_id=aid, url="", title="", content_clean="",
                source="", publish_date=None, category="", category_name="", tags=[],
                tokens=result.filtered_words,
                pos_tags=result.words_with_pos,
                entities=result.entities,
                keywords=[],
                keyword_summary=", ".join(w for w, _ in result.words_with_pos[:5]),
                model_version=f"ckip-v1-{rm.get_device()}",
            )
        else:
            entities = [] if getattr(args, "ner_strategy", "fallback") == "none" else result.entities
            enriched = EnrichedArticle(
                article_id=aid, url="", title="", content_clean="",
                source="", publish_date=None, category="", category_name="", tags=[],
                tokens=result.tokens,
                pos_tags=result.pos_tags,
                entities=entities,
                keywords=result.keywords,
                keyword_summary=", ".join(w for w, _ in result.keywords[:5]),
                model_version=f"jieba-v1|ner:{getattr(args, 'ner_strategy', 'fallback')}",
            )
        db.upsert_nlp(enriched)
        processed += 1

    rm.log_ram_status("NLP done")
    logger.info(f"NLP enrichment complete: {processed:,} articles")


def cmd_entities(args):
    """Run switchable entity extraction strategy."""
    database = Database(args.db or DB_PATH)
    database.init()
    service = EntityExtractionService(database)
    result = service.run(
        provider=args.provider,
        activate=args.activate,
        source=args.source,
        category=args.category,
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit,
        spacy_model=args.spacy_model,
    )
    logger.info(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


def cmd_collocation(args):
    """Collocation analysis."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()
    rm = get_rm(args)

    rows = db._conn.execute(
        "SELECT n.tokens FROM nlp_outputs n "
        "JOIN articles a ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    if not rows:
        logger.info("No NLP data. Run `nlp` first.")
        return

    documents = []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens:
                documents.append(tokens)
        except (json.JSONDecodeError, TypeError):
            continue

    logger.info(f"Running collocation analysis on {len(documents):,} documents...")
    analyzer = CollocationAnalyzer(
        window_size=args.window or 3,
        min_freq=args.min_freq or 3,
    )
    analyzer.fit(documents)

    method = args.method or "pmi"
    pairs = analyzer.top_collocations(topk=args.topk or 50, method=method)

    print(f"\nTop Collocations ({method}, top {len(pairs)}):")
    print(f"{'Rank':<5} {'Word1':<12} {'Word2':<12} {'Co-occur':<10} {'PMI':<10} {'LL':<10}")
    print("-" * 60)
    for i, p in enumerate(pairs, 1):
        print(f"{i:<5} {p.word1:<12} {p.word2:<12} {p.co_occurrence:<10} "
              f"{p.pmi:<10.4f} {p.log_likelihood:<10.4f}")

    # Export
    if args.output:
        df = analyzer.to_dataframe(args.topk or 200)
        df.to_csv(args.output, index=False, encoding="utf-8")
        logger.info(f"Exported to {args.output}")


def cmd_text_mining(args):
    """Text mining: keyword trends + topic modeling."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()

    rows = db._conn.execute(
        "SELECT a.article_id, a.publish_date, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    if not rows:
        logger.info("No NLP data. Run `nlp` first.")
        return

    documents, doc_ids, dates = [], [], []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens:
                documents.append(tokens)
                doc_ids.append(r["article_id"])
                dates.append(r["publish_date"] or "")
        except (json.JSONDecodeError, TypeError):
            continue

    logger.info(f"Text mining on {len(documents):,} documents...")
    analyzer = TextMiningAnalyzer()
    analyzer.fit(documents, doc_ids=doc_ids, dates=dates)

    # Keyword trends
    trends = analyzer.keyword_trends(topk=args.topk or 20, time_bin=args.bin or "month")
    print(f"\nKeyword Trends ({args.bin or 'month'}):")
    for t in trends[:10]:
        print(f"  {t.keyword:<10} total={t.total_count:<6} peak={t.peak_bin} dir={t.trend_direction}")

    # Topic modeling
    n_topics = args.topics or 10
    method = args.method or "nmf"
    topics = analyzer.topic_model(n_topics=n_topics, method=method)
    print(f"\nTopic Modeling ({method}, {n_topics} topics):")
    for t in topics:
        terms_str = ", ".join(f"{w}({s:.3f})" for w, s in t.top_terms[:8])
        print(f"  Topic {t.topic_id}: {terms_str}")


def cmd_cluster(args):
    """Document clustering."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()

    rows = db._conn.execute(
        "SELECT a.article_id, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    if not rows:
        logger.info("No NLP data. Run `nlp` first.")
        return

    documents, doc_ids = [], []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens:
                documents.append(tokens)
                doc_ids.append(r["article_id"])
        except (json.JSONDecodeError, TypeError):
            continue

    logger.info(f"Clustering {len(documents):,} documents...")
    clusterer = DocumentClusterer()
    method = args.method or "kmeans"
    n_clusters = args.n_clusters or 8
    labels, metrics = clusterer.fit(documents, doc_ids=doc_ids,
                                    method=method, n_clusters=n_clusters)

    print(f"\nClustering Results ({method}):")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Summarize clusters
    summaries = clusterer.summarize(top_terms=8)
    for c in summaries:
        terms_str = ", ".join(f"{w}" for w, _ in c.top_terms[:5])
        print(f"  Cluster {c.cluster_id} (n={c.size}): {terms_str}")


def cmd_sentiment(args):
    """Sentiment analysis."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()

    limit = args.limit or 1000
    rows = db._conn.execute(
        "SELECT article_id, title_clean, content_clean FROM articles "
        "WHERE status='cleaned' LIMIT ?", (limit,)
    ).fetchall()

    if not rows:
        logger.info("No cleaned articles found")
        return

    texts = [f"{r['title_clean'] or ''} {r['content_clean'] or ''}" for r in rows]
    analyzer = SentimentAnalyzer()
    results = analyzer.analyze(texts)

    # Summary
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for r in results:
        counts[r.label] += 1

    print(f"\nSentiment Analysis ({len(results)} articles):")
    for label, count in counts.items():
        pct = count / len(results) * 100
        print(f"  {label:<12}: {count:>5} ({pct:.1f}%)")

    # Show examples
    if args.examples:
        print(f"\nTop {args.examples} examples per category:")
        for label in ["positive", "negative"]:
            examples = [r for r in results if r.label == label][:args.examples]
            print(f"\n  {label.upper()}:")
            for ex in examples:
                print(f"    [{ex.compound:+.3f}] {ex.text_preview[:80]}")


def cmd_time_series(args):
    """Time series analysis."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()

    rows = db._conn.execute(
        "SELECT a.article_id, a.publish_date, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    if not rows:
        logger.info("No NLP data. Run `nlp` first.")
        return

    documents, dates = [], []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens and r["publish_date"]:
                documents.append(tokens)
                dates.append(r["publish_date"])
        except (json.JSONDecodeError, TypeError):
            continue

    logger.info(f"Time series on {len(documents):,} documents...")
    analyzer = TimeSeriesAnalyzer(time_bin=args.bin or "month")
    analyzer.fit(documents, dates=dates, top_keywords=args.topk or 30)

    trends = analyzer.topic_trends()
    print(f"\nTopic Trends ({args.bin or 'month'}):")
    print(f"{'Keyword':<12} {'Direction':<10} {'Slope':<10} {'Peak':<12} {'Avg':<8} {'Std':<8}")
    print("-" * 65)
    for t in trends[:20]:
        print(f"{t.keyword:<12} {t.trend_direction:<10} {t.slope:<10.4f} "
              f"{t.peak_date:<12} {t.avg_count:<8.1f} {t.std_count:<8.1f}")

    # Burst detection for top keywords
    if args.bursts:
        print(f"\nBurst Events:")
        for t in trends[:5]:
            bursts = analyzer.detect_bursts(t.keyword)
            if bursts:
                print(f"  {t.keyword}:")
                for b in bursts[:3]:
                    print(f"    {b.burst_date}: count={b.burst_count} "
                          f"({b.burst_ratio:.1f}x baseline, z={b.significance:.1f})")


def cmd_summarize(args):
    """Summarize a document."""
    db = NewsDB(args.db or DB_PATH)
    db.connect()

    doc_id = args.doc_id
    row = db._conn.execute(
        "SELECT title_clean, content_clean FROM articles WHERE article_id = ?",
        (doc_id,)
    ).fetchone()

    if not row or not row["content_clean"]:
        logger.info(f"Document {doc_id} not found or empty")
        return

    text = f"{row['title_clean'] or ''}\n{row['content_clean']}"
    method = args.method or "mmr"
    summarizer = Summarizer()

    if method == "lead_k":
        result = summarizer.lead_k(text, k=args.k or 3)
    elif method == "mmr":
        result = summarizer.mmr_summary(text, k=args.k or 3, diversity=0.7)
    else:
        result = summarizer.extractive(text, ratio=args.ratio or 0.15)

    print(f"\nSummary ({result.method}, compression: {result.compression_ratio:.1%}):")
    print("-" * 60)
    for i, s in enumerate(result.sentences, 1):
        print(f"{i}. {s}")


def cmd_export(args):
    db_path = args.db or DB_PATH
    exp = Exporter(db_path)
    fmt = args.format or "parquet"
    output = Path(args.output or f"{PROCESSED_DIR}/articles.{fmt}")

    if fmt == "csv":
        exp.to_csv(output, include_nlp=args.with_nlp)
    elif fmt == "parquet":
        exp.to_parquet(output, include_nlp=args.with_nlp)
    elif fmt == "jsonl":
        exp.to_jsonl(output, include_nlp=args.with_nlp)
    elif fmt == "huggingface":
        if not args.dataset_name:
            logger.error("--dataset-name required for huggingface format")
            sys.exit(1)
        exp.to_huggingface(args.dataset_name, include_nlp=args.with_nlp,
                          private=not getattr(args, "public", False))
    logger.info(f"Exported to {output}")


def cmd_search(args):
    db = NewsDB(args.db or DB_PATH)
    db.connect()
    results = db.search(args.query, limit=args.limit or 10)
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"\n{i}. [{r['source']}] {r['title']}")
        print(f"   {r.get('publish_date', 'N/A')} | {r.get('category_name', '')}")
        print(f"   {r['content_clean'][:150]}...")


def cmd_stats(args):
    db = NewsDB(args.db or DB_PATH)
    db.connect()
    stats = db.stats()
    print("\n" + "=" * 50)
    print("Database Statistics")
    print("=" * 50)
    for k, v in stats.items():
        print(f"  {k}: {v}")


def cmd_run_all(args):
    """Full pipeline: ingest → CKIP NLP → collocation → export."""
    logger.info("=" * 60)
    logger.info("RUNNING FULL PIPELINE (CKIP + GPU)")
    logger.info("=" * 60)

    rm = get_rm(args)
    logger.info(f"Device: {rm.get_device()} | Threads: {rm.max_threads} | RAM budget: {rm.max_ram_bytes/1024**3:.1f} GB")

    # Ingest
    logger.info("[1/4] Ingesting raw data...")
    cmd_ingest(argparse.Namespace(db=args.db, input_dir=args.input_dir, batch_size=500))

    # CKIP NLP
    logger.info("[2/4] Running CKIP NLP pipeline...")
    cmd_nlp(argparse.Namespace(
        db=args.db, engine="ckip", top_k=10, stopwords=None,
        batch_size=args.batch_size or 64, max_ram=4.0, max_threads=32,
    ))

    # TF-IDF
    logger.info("[3/4] Building TF-IDF model...")
    cmd_tfidf(argparse.Namespace(db=args.db, max_features=50000, min_df=2, output=MODELS_DIR))

    # Export
    logger.info("[4/4] Exporting to Parquet...")
    cmd_export(argparse.Namespace(
        db=args.db, format="parquet",
        output=f"{PROCESSED_DIR}/articles_full.parquet",
        with_nlp=True, dataset_name=None
    ))

    cmd_stats(argparse.Namespace(db=args.db))
    logger.info("Full pipeline complete!")


def cmd_tfidf(args):
    db = NewsDB(args.db or DB_PATH)
    db.connect()
    rows = db._conn.execute(
        "SELECT article_id, content_clean FROM articles WHERE status='cleaned'"
    ).fetchall()
    if not rows:
        logger.info("No cleaned articles found")
        return
    documents, doc_ids = [], []
    for r in rows:
        text = r["content_clean"] or ""
        tokens = text.split() if " " in text else list(text)
        documents.append(" ".join(tokens))
        doc_ids.append(r["article_id"])

    builder = TfidfBuilder(max_features=args.max_features or 50000, min_df=args.min_df or 2)
    builder.fit(documents, doc_ids)
    out_dir = Path(args.output or MODELS_DIR) / "tfidf"
    builder.save(out_dir)
    print(f"\nTF-IDF: vocab={builder.vocabulary_size:,}, "
          f"top={builder.get_top_terms(10)}")


# ===========================================================================
# CLI Parser
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="News Data Pipeline CLI (CKIP + GPU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--max-ram", type=float, default=4.0, help="Max RAM in GB")
    parser.add_argument("--max-threads", type=int, default=32, help="Max threads")

    sub = parser.add_subparsers(dest="command")

    # ingest
    p = sub.add_parser("ingest")
    p.add_argument("--input-dir")
    p.add_argument("--batch-size", type=int, default=500)
    p.set_defaults(func=cmd_ingest)

    # demo
    p = sub.add_parser("demo")
    p.add_argument("--sample", help="Path to sample JSONL dataset")
    p.add_argument("--reset", action="store_true", help="Reset demo SQLite database before import")
    p.set_defaults(func=cmd_demo)

    # nlp
    p = sub.add_parser("nlp")
    p.add_argument("--engine", choices=["ckip", "jieba"], default="ckip")
    p.add_argument("--batch-size", type=int, default=64, help="CKIP batch size")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--stopwords")
    p.add_argument("--ner-strategy", choices=["fallback", "ckip", "spacy", "auto", "none"], default="fallback")
    p.set_defaults(func=cmd_nlp)

    # entity extraction
    p = sub.add_parser("entities")
    p.add_argument("--provider", choices=["fallback", "ckip", "spacy", "auto"], default="fallback")
    p.add_argument("--activate", action="store_true")
    p.add_argument("--source")
    p.add_argument("--category")
    p.add_argument("--date-from")
    p.add_argument("--date-to")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--spacy-model")
    p.set_defaults(func=cmd_entities)

    # collocation
    p = sub.add_parser("collocation")
    p.add_argument("--method", choices=["pmi", "log_likelihood", "combined"], default="pmi")
    p.add_argument("--topk", type=int, default=50)
    p.add_argument("--window", type=int, default=3)
    p.add_argument("--min-freq", type=int, default=3)
    p.add_argument("--output", help="Export CSV path")
    p.set_defaults(func=cmd_collocation)

    # text-mining
    p = sub.add_parser("text-mining")
    p.add_argument("--topics", type=int, default=10)
    p.add_argument("--method", choices=["nmf", "lda"], default="nmf")
    p.add_argument("--topk", type=int, default=20)
    p.add_argument("--bin", default="month")
    p.set_defaults(func=cmd_text_mining)

    # cluster
    p = sub.add_parser("cluster")
    p.add_argument("--method", choices=["kmeans", "hierarchical"], default="kmeans")
    p.add_argument("--n-clusters", type=int, default=8)
    p.set_defaults(func=cmd_cluster)

    # sentiment
    p = sub.add_parser("sentiment")
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--examples", type=int, default=3)
    p.set_defaults(func=cmd_sentiment)

    # time-series
    p = sub.add_parser("time-series")
    p.add_argument("--bin", default="month")
    p.add_argument("--topk", type=int, default=30)
    p.add_argument("--bursts", action="store_true")
    p.set_defaults(func=cmd_time_series)

    # summarize
    p = sub.add_parser("summarize")
    p.add_argument("--doc-id", required=True)
    p.add_argument("--method", choices=["lead_k", "mmr", "extractive"], default="mmr")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--ratio", type=float, default=0.15)
    p.set_defaults(func=cmd_summarize)

    # export
    p = sub.add_parser("export")
    p.add_argument("--format", choices=["csv", "parquet", "jsonl", "huggingface"])
    p.add_argument("--output")
    p.add_argument("--with-nlp", action="store_true")
    p.add_argument("--dataset-name")
    p.add_argument("--public", action="store_true")
    p.set_defaults(func=cmd_export)

    # search
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_search)

    # stats
    p = sub.add_parser("stats")
    p.set_defaults(func=cmd_stats)

    # tfidf
    p = sub.add_parser("tfidf")
    p.add_argument("--max-features", type=int, default=50000)
    p.add_argument("--min-df", type=int, default=2)
    p.add_argument("--output")
    p.set_defaults(func=cmd_tfidf)

    # run-all
    p = sub.add_parser("run-all")
    p.add_argument("--input-dir")
    p.add_argument("--batch-size", type=int, default=64)
    p.set_defaults(func=cmd_run_all)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
