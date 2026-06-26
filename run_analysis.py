#!/usr/bin/env python
"""
Full Analysis Pipeline — CKIP GPU-accelerated

Usage (in data_env conda environment):
    conda activate data_env
    cd ~/web-projects/news-web-crawler
    export HF_HOME=/mnt/c/data/information-retrieval/.hf_cache

    # Full pipeline
    python run_analysis.py --all --engine ckip --batch-size 128 --max-ram 8.0

    # Sentiment only (fast)
    python run_analysis.py --sentiment-only

    # Specific steps
    python run_analysis.py --steps nlp collocation sentiment
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Set HF cache before any imports
os.environ.setdefault("HF_HOME", "/mnt/c/data/information-retrieval/.hf_cache")

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.db import NewsDB
from pipeline.schema import EnrichedArticle
from nlp.ckip_pipeline import CKIPPipeline
from nlp.pipeline import NLPPipeline
from analysis.collocation import CollocationAnalyzer
from analysis.text_mining import TextMiningAnalyzer
from analysis.clustering import DocumentClusterer
from analysis.classification import SentimentAnalyzer
from analysis.summarization import Summarizer
from analysis.time_series import TimeSeriesAnalyzer
from analysis.opinion_lexicon import OpinionLexicon
from utils.resource_manager import ResourceManager

# Paths
DATA_DIR = os.getenv("NEWS_DATA_DIR", "/mnt/c/data/information-retrieval")
DB_PATH = os.getenv("NEWS_DB_PATH", f"{DATA_DIR}/news.db")
LEXICON_PATH = os.getenv("NEWS_LEXICON_PATH", "/mnt/c/data/features/opinion_word.xlsx")
PROCESSED_DIR = os.getenv("NEWS_PROCESSED_DIR", f"{DATA_DIR}/processed")
REPORTS_DIR = os.getenv("NEWS_REPORTS_DIR", f"{DATA_DIR}/reports")
MODELS_DIR = os.getenv("NEWS_MODELS_DIR", f"{DATA_DIR}/models")
REPORTS_DIR = Path(REPORTS_DIR)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_analysis")


def get_rm(max_ram: float = 8.0) -> ResourceManager:
    return ResourceManager(max_ram_gb=max_ram, max_threads=32)


# ===========================================================================
# Step 1: CKIP NLP (GPU-accelerated batch processing)
# ===========================================================================
def run_nlp(db: NewsDB, rm: ResourceManager, engine: str = "ckip",
            batch_size: int = 128) -> int:
    """Run NLP pipeline on all cleaned articles."""
    rows = db._conn.execute(
        "SELECT article_id, content_clean, title_clean FROM articles "
        "WHERE status='cleaned' AND article_id NOT IN (SELECT article_id FROM nlp_outputs)"
    ).fetchall()

    if not rows:
        logger.info("No articles need NLP processing — skipping")
        return 0

    logger.info(f"NLP: {len(rows):,} articles, engine={engine}, device={rm.get_device()}")
    rm.log_ram_status("NLP start")

    device_id = rm.get_cuda_device_id()
    if engine == "ckip":
        nlp = CKIPPipeline(device_id=device_id, use_ner=True)
    else:
        nlp = NLPPipeline(engine="jieba", top_keywords=10)

    def process_batch(batch_rows):
        texts = [f"{r['title_clean'] or ''} {r['content_clean'] or ''}" for r in batch_rows]
        if engine == "ckip":
            return nlp.process_batch(texts)
        return [nlp.process(t) for t in texts]

    results = rm.process_in_batches(rows, process_batch,
                                    batch_size=batch_size, desc="CKIP NLP")

    count = 0
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
                model_version=f"ckip-bert-{rm.get_device()}",
            )
        else:
            enriched = EnrichedArticle(
                article_id=aid, url="", title="", content_clean="",
                source="", publish_date=None, category="", category_name="", tags=[],
                tokens=result.tokens, pos_tags=result.pos_tags,
                entities=result.entities, keywords=result.keywords,
                keyword_summary=", ".join(w for w, _ in result.keywords[:5]),
                model_version="jieba-v1",
            )
        db.upsert_nlp(enriched)
        count += 1

    rm.log_ram_status("NLP done")
    return count


# ===========================================================================
# Step 2: Collocation Analysis
# ===========================================================================
def run_collocation(db: NewsDB, rm: ResourceManager,
                    topk: int = 100, window: int = 3) -> dict:
    logger.info("Collocation analysis...")
    rows = db._conn.execute(
        "SELECT n.tokens FROM nlp_outputs n "
        "JOIN articles a ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    documents = []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens:
                documents.append(tokens)
        except (json.JSONDecodeError, TypeError):
            continue

    if len(documents) < 10:
        logger.info("Too few documents — skipping")
        return {}

    analyzer = CollocationAnalyzer(window_size=window, min_freq=5)
    analyzer.fit(documents)
    pairs = analyzer.top_collocations(topk=topk, method="pmi")

    logger.info(f"Top 10 collocations (PMI):")
    for i, p in enumerate(pairs[:10], 1):
        logger.info(f"  {i}. {p.word1} + {p.word2}  (co={p.co_occurrence}, pmi={p.pmi:.4f})")

    out_path = REPORTS_DIR / "collocation_pmi.csv"
    analyzer.to_dataframe(topk).to_csv(out_path, index=False, encoding="utf-8")
    logger.info(f"Exported → {out_path}")
    return {"collocations": len(pairs), "export": str(out_path)}


# ===========================================================================
# Step 3: Text Mining
# ===========================================================================
def run_text_mining(db: NewsDB, rm: ResourceManager, n_topics: int = 10) -> dict:
    logger.info("Text mining...")
    rows = db._conn.execute(
        "SELECT a.article_id, a.publish_date, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

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

    if len(documents) < 10:
        return {}

    analyzer = TextMiningAnalyzer()
    analyzer.fit(documents, doc_ids=doc_ids, dates=dates)

    trends = analyzer.keyword_trends(topk=20, time_bin="month")
    topics = analyzer.topic_model(n_topics=n_topics, method="nmf")

    report = {
        "keyword_trends": [{"keyword": t.keyword, "total": t.total_count,
                           "direction": t.direction, "peak": t.peak_bin} for t in trends[:15]],
        "topics": [{"topic_id": t.topic_id, "terms": [w for w, _ in t.top_terms[:8]]} for t in topics],
    }

    out_path = REPORTS_DIR / "text_mining.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Exported → {out_path}")
    return {"trends": len(trends), "topics": len(topics)}


# ===========================================================================
# Step 4: Clustering
# ===========================================================================
def run_clustering(db: NewsDB, rm: ResourceManager, n_clusters: int = 8) -> dict:
    logger.info("Clustering...")
    rows = db._conn.execute(
        "SELECT a.article_id, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id WHERE a.status='cleaned'"
    ).fetchall()

    documents, doc_ids = [], []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens:
                documents.append(tokens)
                doc_ids.append(r["article_id"])
        except (json.JSONDecodeError, TypeError):
            continue

    if len(documents) < 20:
        return {}

    clusterer = DocumentClusterer()
    labels, metrics = clusterer.fit(documents, doc_ids=doc_ids,
                                    method="kmeans", n_clusters=n_clusters)
    summaries = clusterer.summarize(top_terms=10)

    report = {"metrics": {k: str(v) for k, v in metrics.items()},
              "clusters": [{"id": c.cluster_id, "size": c.size,
                           "terms": [w for w, _ in c.top_terms[:8]]} for c in summaries]}

    out_path = REPORTS_DIR / "clustering.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return metrics


# ===========================================================================
# Step 5: Sentiment (Opinion Lexicon + comparison)
# ===========================================================================
def run_sentiment(db: NewsDB, rm: ResourceManager, limit: int = 10000) -> dict:
    logger.info("Sentiment analysis...")
    rows = db._conn.execute(
        "SELECT a.article_id, a.title_clean, a.content_clean, n.tokens "
        "FROM articles a LEFT JOIN nlp_outputs n ON a.article_id = n.article_id "
        "WHERE a.status='cleaned' LIMIT ?", (limit,)
    ).fetchall()

    if not rows:
        return {}

    texts = []
    token_lists = []
    for r in rows:
        text = f"{r['title_clean'] or ''} {r['content_clean'] or ''}"
        texts.append(text)
        try:
            tokens = json.loads(r["tokens"]) if r["tokens"] else []
        except (json.JSONDecodeError, TypeError):
            tokens = []
        token_lists.append(tokens if tokens else [])

    # Method 1: Simple lexicon, always available.
    sa = SentimentAnalyzer()
    simple_scores = sa.analyze(texts[:min(limit, 5000)])
    simple_summary = {
        "positive": sum(1 for s in simple_scores if s.label == "positive"),
        "negative": sum(1 for s in simple_scores if s.label == "negative"),
        "neutral": sum(1 for s in simple_scores if s.label == "neutral"),
    }

    # Method 2: Opinion Lexicon, optional external resource.
    lex_scores = []
    lex_summary = {"total_docs": len(texts), "mean_score": 0, "labels": simple_summary}
    lex_available = Path(LEXICON_PATH).exists()
    if lex_available:
        lex = OpinionLexicon(LEXICON_PATH)
        logger.info(f"Analyzing {len(texts):,} articles with opinion lexicon (longest-match)...")
        lex_scores = lex.analyze_texts(texts)
        lex_summary = lex.summary(lex_scores)

        has_tokens = any(len(t) > 0 for t in token_lists)
        if has_tokens:
            logger.info("CKIP tokens available — running tokenized analysis too...")
            lex_scores_tok = lex.analyze_tokenized(token_lists, texts=texts)
            lex_summary_tok = lex.summary(lex_scores_tok)
            logger.info(f"Tokenized summary: {lex_summary_tok}")
    else:
        logger.warning(f"Opinion lexicon not found: {LEXICON_PATH}; using simple lexicon only.")

    report = {
        "opinion_lexicon_weighted": lex_summary,
        "simple_lexicon": {
            **simple_summary,
            "method": "simple_lexicon",
        },
        "comparison": {
            "weighted_mean": lex_summary.get("mean_score", 0),
            "weighted_positive_pct": lex_summary.get("labels", {}).get("positive", 0) /
                                     max(lex_summary.get("total_docs", 1), 1) * 100,
            "simple_positive_pct": sum(1 for s in simple_scores if s.label == "positive") /
                                   max(len(simple_scores), 1) * 100,
            "agreement_rate": sum(1 for ls, ss in zip(lex_scores[:len(simple_scores)], simple_scores)
                                 if ls.label == ss.label) / max(len(simple_scores), 1) * 100 if lex_scores else 0,
        },
        "method": "opinion_lexicon" if lex_available else "simple_lexicon_fallback",
    }

    # Export
    if lex_scores and lex_available:
        lex_df = lex.to_dataframe(lex_scores)
        lex_df.to_csv(REPORTS_DIR / "sentiment_scores.csv", index=False, encoding="utf-8")
    with open(REPORTS_DIR / "sentiment_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Sentiment: {lex_summary.get('labels', simple_summary)}")
    logger.info(f"Agreement: {report['comparison']['agreement_rate']:.1f}%")
    return report


# ===========================================================================
# Step 6: Time Series
# ===========================================================================
def run_time_series(db: NewsDB, rm: ResourceManager) -> dict:
    logger.info("Time series analysis...")
    rows = db._conn.execute(
        "SELECT a.publish_date, n.tokens FROM articles a "
        "JOIN nlp_outputs n ON a.article_id = n.article_id "
        "WHERE a.status='cleaned' AND a.publish_date IS NOT NULL"
    ).fetchall()

    documents, dates = [], []
    for r in rows:
        try:
            tokens = json.loads(r["tokens"])
            if tokens and r["publish_date"]:
                documents.append(tokens)
                dates.append(r["publish_date"])
        except (json.JSONDecodeError, TypeError):
            continue

    if len(documents) < 20:
        return {}

    analyzer = TimeSeriesAnalyzer(time_bin="month")
    analyzer.fit(documents, dates=dates, top_keywords=30)
    trends = analyzer.topic_trends()

    burst_report = []
    for t in trends[:5]:
        bursts = analyzer.detect_bursts(t.keyword, z_threshold=1.5)
        burst_report.append({
            "keyword": t.keyword, "trend": t.trend_direction, "slope": getattr(t, 'slope', 0),
            "bursts": [{"date": b.burst_date, "count": b.burst_count} for b in bursts[:3]],
        })

    with open(REPORTS_DIR / "time_series.json", "w") as f:
        json.dump({"trends": burst_report}, f, ensure_ascii=False, indent=2)
    return {"trends": len(trends)}


# ===========================================================================
# Step 7: Summarization
# ===========================================================================
def run_summarization(db: NewsDB, sample_count: int = 10):
    logger.info(f"Summarization ({sample_count} samples)...")
    rows = db._conn.execute(
        "SELECT article_id, title_clean, content_clean FROM articles "
        "WHERE status='cleaned' AND length(content_clean) > 200 LIMIT ?",
        (sample_count,)
    ).fetchall()

    summarizer = Summarizer()
    samples = []
    for r in rows:
        text = f"{r['title_clean'] or ''}\n{r['content_clean']}"
        mmr = summarizer.mmr_summary(text, k=3, diversity=0.7)
        samples.append({
            "article_id": r["article_id"], "title": r["title_clean"],
            "mmr_summary": mmr.sentences, "compression": round(mmr.compression_ratio, 3),
        })

    with open(REPORTS_DIR / "summaries.json", "w") as f:
        json.dump({"samples": samples}, f, ensure_ascii=False, indent=2)
    return {"samples": len(samples)}


# ===========================================================================
# Main
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="Full Analysis Pipeline (CKIP + GPU)")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--max-ram", type=float, default=8.0, help="RAM budget (GB)")
    parser.add_argument("--engine", choices=["ckip", "jieba"], default="ckip")
    parser.add_argument("--batch-size", type=int, default=128, help="CKIP batch size")
    parser.add_argument("--limit", type=int, default=10000, help="Max articles for sentiment")
    parser.add_argument("--n-topics", type=int, default=10)
    parser.add_argument("--n-clusters", type=int, default=8)
    parser.add_argument("--collocation-topk", type=int, default=100)

    steps = parser.add_mutually_exclusive_group()
    steps.add_argument("--all", action="store_true")
    steps.add_argument("--nlp-only", action="store_true")
    steps.add_argument("--sentiment-only", action="store_true")
    steps.add_argument("--steps", nargs="+")

    args = parser.parse_args()
    rm = get_rm(args.max_ram)
    logger.info(f"Device: {rm.get_device()} | Threads: {rm.max_threads} | RAM: {rm.max_ram_bytes/1024**3:.1f} GB")

    db = NewsDB(args.db)
    db.connect()
    db.init()

    t0 = time.time()
    results = {}

    def should_run(step: str) -> bool:
        if args.all:
            return True
        if args.nlp_only:
            return step == "nlp"
        if args.sentiment_only:
            return step == "sentiment"
        if args.steps:
            return step in args.steps
        return True

    if should_run("nlp"):
        results["nlp"] = {"articles": run_nlp(db, rm, engine=args.engine, batch_size=args.batch_size)}
    if should_run("collocation"):
        results["collocation"] = run_collocation(db, rm, topk=args.collocation_topk)
    if should_run("text_mining"):
        results["text_mining"] = run_text_mining(db, rm, n_topics=args.n_topics)
    if should_run("clustering"):
        results["clustering"] = run_clustering(db, rm, n_clusters=args.n_clusters)
    if should_run("sentiment"):
        results["sentiment"] = run_sentiment(db, rm, limit=args.limit)
    if should_run("time_series"):
        results["time_series"] = run_time_series(db, rm)
    if should_run("summarization"):
        results["summarization"] = run_summarization(db)

    elapsed = time.time() - t0
    results["elapsed_seconds"] = round(elapsed, 1)
    results["ram_used_gb"] = round(rm.current_ram_usage_gb(), 2)

    with open(REPORTS_DIR / "analysis_report.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    db.close()
    logger.info(f"\n{'='*60}")
    logger.info(f"Analysis complete in {elapsed:.1f}s | RAM: {rm.current_ram_usage_gb():.2f} GB")
    logger.info(f"Reports → {REPORTS_DIR}")
    for k, v in results.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    main()
