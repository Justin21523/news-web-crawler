# News Web Crawler & Analysis Pipeline

Scrapy-based Taiwanese news crawler with full CKIP NLP pipeline and ML analysis suite.

## Web App Quick Start

This repository now includes a Next.js frontend and FastAPI backend for running
the crawler/analysis pipeline from a browser.

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8011/api/v1/health
- API docs: http://localhost:8011/docs

## Portfolio Demo Evidence

This project includes a guided, interview-ready walkthrough for the News Data
Intelligence Platform. The floating assistant opens by default on every page and
walks through upload, pipeline jobs, data quality, EDA, text mining, article
search, ML diagnostics, and report export.

Links:

- GitHub: https://github.com/Justin21523/news-web-crawler
- Demo: deployed URL is recorded in `docs/demo-artifacts/latest/qa-manifest.json`
- README: https://github.com/Justin21523/news-web-crawler#readme
- Guided tour video: [docs/demo-artifacts/latest/videos/guided-tour.webm](docs/demo-artifacts/latest/videos/guided-tour.webm)

Representative screenshots:

| View | Screenshot |
| --- | --- |
| Dashboard desktop | [dashboard-desktop-01.png](docs/demo-artifacts/latest/screenshots/dashboard-desktop-01.png) |
| Journey desktop | [journey-desktop-01.png](docs/demo-artifacts/latest/screenshots/journey-desktop-01.png) |
| Data Quality mobile | [data-quality-mobile-01.png](docs/demo-artifacts/latest/screenshots/data-quality-mobile-01.png) |
| Text Mining desktop | [text-mining-desktop-01.png](docs/demo-artifacts/latest/screenshots/text-mining-desktop-01.png) |
| ML desktop | [ml-desktop-01.png](docs/demo-artifacts/latest/screenshots/ml-desktop-01.png) |

Generate fresh evidence:

```bash
cd frontend
E2E_BASE_URL=http://127.0.0.1:3009 npm run test:e2e:guided
E2E_BASE_URL=http://127.0.0.1:3009 npm run demo:capture
```

The generated QA manifest is stored at
`docs/demo-artifacts/latest/qa-manifest.json`.

Local development without Docker:

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend:. uvicorn app.main:app --reload --port 8011

# Frontend
cd frontend
npm install
npm run dev
```

Default data paths are under `data/` for the web app. Override them with:

```bash
NEWS_DATA_DIR=data
NEWS_DB_PATH=data/news.db
NEWS_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8011/api/v1
```

## Web Architecture

```text
frontend/                 Next.js App Router UI
  src/app/                Dashboard, articles, jobs, settings
  src/components/         Shared shell and UI primitives
  src/lib/api.ts          FastAPI client

backend/                  FastAPI service
  app/main.py             API entrypoint
  app/api/v1/             Versioned routes
  app/services/           Article, stats, job, and DB services
  app/schemas/            Pydantic response/request models

data/                     Web app runtime volume
  raw/                    Raw crawler JSONL files
  processed/              Export outputs
  reports/                Analysis reports
  jobs/                   Background job logs
  news.db                 SQLite database
```

## Dashboard Design System

The web app uses a light, data-first dashboard style inspired by Geckoboard,
Tableau, Urban Institute, and Berkeley data visualization guidance.

- Primary palette: Urban blue `#1696D2`, dark blue `#0A4B69`, neutral background
  `#F5F5F5`, and high-emphasis text `#17202A`.
- Accent palette is intentionally limited: yellow `#FDBF11`, magenta
  `#EC008B`, green `#55B748`, and gray `#7B8A8B`. Categorical charts should
  stay at six colors or fewer.
- Typography uses a sans-serif stack (`Lato`, `Arial`, system fallback).
  KPI values and counts use tabular numeric styling for easier scanning.
- Layouts follow an executive-summary pattern: high-level KPIs first, processing
  flow next, then supporting charts and diagnostic details.
- Empty states are explicit. The UI reports missing data or insufficient
  analysis coverage rather than filling dashboards with placeholder values.

Screenshots are saved under:

```text
docs/screenshots/before/
docs/screenshots/phase-1-theme/
docs/screenshots/phase-2-layout/
docs/screenshots/phase-4-analysis/
```

Generate screenshots with Playwright:

```bash
npx playwright screenshot --viewport-size=1440,900 http://127.0.0.1:3000 docs/screenshots/phase-4-analysis/dashboard-desktop.png
```

## Web Analysis Features

The FastAPI backend exposes structured endpoints for analysis-ready UI:

```text
GET /api/v1/data-quality
GET /api/v1/pipeline/status
GET /api/v1/analysis/overview
GET /api/v1/analysis/collocations
GET /api/v1/analysis/topics
GET /api/v1/analysis/clusters
GET /api/v1/analysis/sentiment
GET /api/v1/analysis/time-series
GET /api/v1/analysis/ir
```

Phase 5 adds a dedicated Machine Learning dashboard at `/ml` with on-demand
baseline training and interpretable Decision Tree views:

```text
GET /api/v1/ml/overview
GET /api/v1/ml/dataset
GET /api/v1/ml/train
GET /api/v1/ml/compare
GET /api/v1/ml/decision-tree
GET /api/v1/ml/decision-tree/image
GET /api/v1/ml/decision-tree/path
GET /api/v1/ml/export
GET /api/v1/ml/artifacts
GET /api/v1/ml/artifacts/{artifact_id}
GET /api/v1/ml/artifacts/compare
GET /api/v1/ml/artifacts/{artifact_id}/download
```

Supported baseline targets are `category`, `source`, and weak-label
`sentiment`. Supported models are Logistic Regression, Linear SVM, Naive Bayes,
Decision Tree, and Random Forest. Sentiment classification is explicitly marked
as weak supervision until manually labeled sentiment data is available.

ML training can also run as persistent background jobs:

```json
{"type":"train_ml","params":{"target":"source","model":"logistic_regression","feature_limit":1000}}
{"type":"train_decision_tree","params":{"target":"category","max_depth":4,"feature_limit":1000}}
```

Saved artifacts are written to `data/models/ml/{artifact_id}/` and include
`model.joblib`, `vectorizer.joblib`, `manifest.json`, metrics, reports,
feature importance, and Decision Tree PNG/SVG files when applicable.

Run analysis reports from the Jobs page with job type `analysis`, or from CLI:

```bash
NEWS_DATA_DIR=data NEWS_DB_PATH=data/news.db \
python run_analysis.py --steps collocation text_mining clustering sentiment time_series summarization
```

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
PYTHONPATH=backend:. pytest -q
cd frontend && npm run lint && npm run build
```
