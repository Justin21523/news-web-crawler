# News Web Crawler & Analysis Pipeline

Scrapy-based Taiwanese news crawler with full CKIP NLP pipeline and ML analysis suite.

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium

# ── Crawl ──────────────────────────────────────────────
python run_crawler.py cna --days 7 --max-articles 500

# ── Full Pipeline (CKIP + GPU auto-detect) ─────────────
python pipeline_cli.py run-all

# ── CKIP NLP (GPU-accelerated, batched) ────────────────
python pipeline_cli.py nlp --engine ckip --batch-size 64

# ── Analysis ───────────────────────────────────────────
python pipeline_cli.py collocation --method pmi --topk 100
python pipeline_cli.py text-mining --topics 10 --method nmf
python pipeline_cli.py cluster --method kmeans --n-clusters 8
python pipeline_cli.py sentiment --limit 5000
python pipeline_cli.py time-series --bin month --bursts
python pipeline_cli.py summarize --doc-id abc123 --method mmr

# ── Export & Search ────────────────────────────────────
python pipeline_cli.py export --format parquet --with-nlp
python pipeline_cli.py search "人工智慧" --limit 20
python pipeline_cli.py stats
```

## Architecture

```
spiders/              — Crawler definitions (CNA, PTS, LTN)
middlewares/          — Stealth + humanization (anti-detection)
pipeline/             — Data engineering core
  schema.py             — RawArticle → CleanArticle → EnrichedArticle
  text_cleaner.py       — Normalization (width, trad/simp, HTML, URLs)
  validator.py          — Validation, dedup, JSONL merge
  db.py                 — SQLite + FTS5, batch upsert, export
nlp/                  — NLP engines
  ckip_pipeline.py      — CKIP: joint seg+POS+NER, GPU, batched
  pipeline.py           — Jieba fallback
analysis/             — ML analysis suite
  collocation.py        — PMI, log-likelihood, co-occurrence matrix
  text_mining.py        — Keyword trends, LDA/NMF topic modeling
  clustering.py         — K-Means, hierarchical, silhouette score
  classification.py     — TF-IDF classifier, sentiment lexicon
  summarization.py      — Lead-K, TextRank, MMR
  time_series.py        — Trend analysis, burst detection, correlation
features/             — Feature engineering
  tfidf.py              — TF-IDF builder + cosine similarity
exports/              — CSV, Parquet, JSONL, HuggingFace Dataset
utils/
  resource_manager.py   — RAM monitoring, GPU detection, thread pool
pipeline_cli.py       — Unified CLI (13 commands)
```

## CKIP Pipeline

The CKIP pipeline uses **joint word segmentation + POS tagging** for higher accuracy:

```python
from nlp.ckip_pipeline import CKIPPipeline
from utils.resource_manager import ResourceManager

rm = ResourceManager(max_ram_gb=4.0)
nlp = CKIPPipeline(device_id=rm.get_cuda_device_id())  # GPU if available

# Batch processing with RAM safety
results = rm.process_in_batches(texts, nlp.process_batch, batch_size=64)
# Each result: words_with_pos, filtered_words, fused_tokens, entities
```

**Output per document:**
- `words_with_pos`: `[("人工智慧", "Na"), ("發展", "VA"), ...]`
- `filtered_words`: `["人工智慧", "發展", ...]` (stopwords + non-content POS removed)
- `fused_tokens`: `["人工智慧/Na", "發展/VA", ...]` (word+POS combined)
- `entities`: `[("台灣", "ORG"), ...]` (NER)

## Analysis Modules

| Module | Methods | Output |
|--------|---------|--------|
| **Collocation** | PMI, log-likelihood, sliding window | Top word pairs, co-occurrence matrix |
| **Text Mining** | Keyword trends, LDA/NMF topics | Time series, topic-term distributions |
| **Clustering** | K-Means, hierarchical | Cluster labels, silhouette score |
| **Classification** | Logistic/SVM, lexicon sentiment | Predicted categories, sentiment scores |
| **Summarization** | Lead-K, TextRank, MMR | Extracted sentences, compression ratio |
| **Time Series** | Linear trend, burst detection | Direction, slope, burst events |

## Resource Management

Automatic GPU detection and RAM-safe batch processing:

| Setting | Default | Description |
|---------|---------|-------------|
| `--max-ram` | 4.0 GB | RAM budget for processing |
| `--max-threads` | 32 | Thread pool size |
| `--batch-size` | 64 | CKIP batch size (auto-adjusted by RAM) |
| GPU | Auto-detect | Uses CUDA if available, falls back to CPU |

## Data Paths

All data at `/mnt/c/data/information-retrieval/`:

| Path | Purpose |
|------|---------|
| `raw/` | Per-crawl JSONL from spiders |
| `processed/` | Merged, cleaned, exported data |
| `news.db` | SQLite database (FTS5 full-text search) |
| `models/tfidf/` | Saved TF-IDF vectorizer + DTM |
| `models/` | Saved model artifacts |

## Adding Analysis

Each analysis module is independent and reads from the SQLite database:

```python
from pipeline.db import NewsDB
from analysis.collocation import CollocationAnalyzer

db = NewsDB()
rows = db.db._conn.execute(
    "SELECT n.tokens FROM nlp_outputs n JOIN articles a ON a.article_id = n.article_id"
).fetchall()

documents = [json.loads(r["tokens"]) for r in rows]
analyzer = CollocationAnalyzer()
analyzer.fit(documents)
pairs = analyzer.top_collocations(topk=50)
```

## Tests

```bash
pytest tests/ -v    # 42 tests
```
