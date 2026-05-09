"""
SQLite database layer for the news pipeline.

Provides:
  - Schema creation (articles, nlp_outputs, processing_log)
  - Batch upsert from JSONL / CleanArticle / EnrichedArticle
  - Query helpers for analysis (date range, source stats, full-text search)
  - Export to DataFrame / Parquet

Usage:
    from pipeline.db import NewsDB

    db = NewsDB("/mnt/c/data/information-retrieval/news.db")
    db.init()
    db.insert_raw_articles(jsonl_path)
    results = db.search("人工智慧", limit=20)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Iterable
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from pipeline.schema import RawArticle, CleanArticle, EnrichedArticle
from pipeline.text_cleaner import normalize
from pipeline.validator import compute_dedup_hash, validate_raw

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "/mnt/c/data/information-retrieval/news.db"

# ---------------------------------------------------------------------------
# SQL DDL
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS articles (
    article_id    TEXT PRIMARY KEY,
    url           TEXT UNIQUE NOT NULL,
    source        TEXT NOT NULL,
    source_name   TEXT,
    title         TEXT NOT NULL,
    title_clean   TEXT,
    content_clean TEXT,
    author        TEXT,
    publish_date  TEXT,
    category      TEXT,
    category_name TEXT,
    tags          TEXT,          -- JSON array
    image_url     TEXT,
    crawled_at    TEXT,
    cleaned_at    TEXT,
    dedup_hash    TEXT,
    char_count    INTEGER DEFAULT 0,
    word_count    INTEGER DEFAULT 0,
    lang          TEXT DEFAULT 'zh-Hant',
    status        TEXT DEFAULT 'raw'   -- raw | cleaned | enriched
);

CREATE TABLE IF NOT EXISTS nlp_outputs (
    article_id        TEXT PRIMARY KEY REFERENCES articles(article_id),
    tokens            TEXT,      -- JSON array
    pos_tags          TEXT,      -- JSON array of [word, pos]
    entities          TEXT,      -- JSON array of [entity, type]
    keywords          TEXT,      -- JSON array of [term, score]
    keyword_summary   TEXT,
    tfidf_vector_path TEXT,
    embedding_path    TEXT,
    model_version     TEXT,
    enriched_at       TEXT
);

CREATE TABLE IF NOT EXISTS processing_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,
    source_file TEXT,
    records_in  INTEGER,
    records_out INTEGER,
    details     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_pubdate   ON articles(publish_date);
CREATE INDEX IF NOT EXISTS idx_articles_category  ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_status    ON articles(status);
CREATE INDEX IF NOT EXISTS idx_nlp_keywords       ON nlp_outputs(keywords);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title_clean, content_clean,
    content='articles',
    content_rowid='rowid',
    tokenize='unicode61'
);
"""


# ---------------------------------------------------------------------------
# NewsDB class
# ---------------------------------------------------------------------------
class NewsDB:
    """SQLite database wrapper for news articles."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            logger.info(f"Connected to {self.db_path}")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def init(self):
        """Create tables and indexes if they don't exist."""
        conn = self.connect()
        conn.executescript(DDL)
        conn.commit()
        logger.info("Database schema initialized")

    # ------------------------------------------------------------------
    # Insert helpers
    # ------------------------------------------------------------------
    def insert_raw_articles(self, jsonl_path: str | Path,
                            batch_size: int = 500) -> dict:
        """Load raw JSONL into the articles table."""
        path = Path(jsonl_path)
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return {"inserted": 0, "skipped": 0, "errors": 0}

        conn = self.connect()
        inserted = skipped = errors = 0
        batch: list[RawArticle] = []

        for line in path.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                raw = RawArticle.from_dict(obj)
                if not raw.is_valid():
                    skipped += 1
                    continue
                batch.append(raw)
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Parse error: {e}")
                errors += 1
                continue

            if len(batch) >= batch_size:
                inserted += self._upsert_batch(batch)
                batch.clear()

        if batch:
            inserted += self._upsert_batch(batch)

        self._log_action("insert_raw", str(path), 0, inserted)
        logger.info(f"Inserted {inserted:,} from {path.name} "
                    f"({skipped} skipped, {errors} errors)")
        return {"inserted": inserted, "skipped": skipped, "errors": errors}

    def _upsert_batch(self, articles: list[RawArticle]) -> int:
        conn = self.connect()
        conn.executemany("""
            INSERT INTO articles (
                article_id, url, source, source_name, title, title_clean,
                content_clean, author, publish_date, category, category_name,
                tags, image_url, crawled_at, status, dedup_hash, char_count
            ) VALUES (
                :article_id, :url, :source, :source_name, :title, :title_clean,
                :content_clean, :author, :publish_date, :category, :category_name,
                :tags, :image_url, :crawled_at, 'raw', :dedup_hash, :char_count
            )
            ON CONFLICT(article_id) DO UPDATE SET
                title=excluded.title,
                content_clean=excluded.content_clean,
                title_clean=excluded.title_clean,
                status='raw'
        """, [
            {
                **a.to_dict(),
                "title_clean": normalize(a.title),
                "content_clean": normalize(a.content),
                "dedup_hash": compute_dedup_hash(a.title, a.url),
                "char_count": len(a.content),
                "tags": json.dumps(a.tags, ensure_ascii=False),
            }
            for a in articles
        ])
        conn.commit()
        return len(articles)

    def upsert_clean(self, article: CleanArticle):
        """Upsert a single cleaned article."""
        conn = self.connect()
        conn.execute("""
            INSERT INTO articles (
                article_id, url, source, source_name, title, title_clean,
                content_clean, author, publish_date, category, category_name,
                tags, image_url, crawled_at, cleaned_at, dedup_hash,
                char_count, word_count, lang, status
            ) VALUES (
                :article_id, :url, :source, :source_name, :title, :title_clean,
                :content_clean, :author, :publish_date, :category, :category_name,
                :tags, :image_url, :crawled_at, :cleaned_at, :dedup_hash,
                :char_count, :word_count, :lang, 'cleaned'
            )
            ON CONFLICT(article_id) DO UPDATE SET
                title_clean=excluded.title_clean,
                content_clean=excluded.content_clean,
                char_count=excluded.char_count,
                word_count=excluded.word_count,
                status='cleaned'
        """, {
            **article.to_dict(),
            "tags": json.dumps(article.tags, ensure_ascii=False),
        })
        conn.commit()

    def upsert_nlp(self, enriched: EnrichedArticle):
        """Upsert NLP outputs."""
        conn = self.connect()
        conn.execute("""
            INSERT INTO nlp_outputs (
                article_id, tokens, pos_tags, entities, keywords,
                keyword_summary, tfidf_vector_path, embedding_path,
                model_version, enriched_at
            ) VALUES (
                :article_id, :tokens, :pos_tags, :entities, :keywords,
                :keyword_summary, :tfidf_vector_path, :embedding_path,
                :model_version, :enriched_at
            )
            ON CONFLICT(article_id) DO UPDATE SET
                tokens=excluded.tokens,
                pos_tags=excluded.pos_tags,
                entities=excluded.entities,
                keywords=excluded.keywords,
                enriched_at=excluded.enriched_at
        """, {
            "article_id": enriched.article_id,
            "tokens": json.dumps(enriched.tokens, ensure_ascii=False),
            "pos_tags": json.dumps([list(t) for t in enriched.pos_tags], ensure_ascii=False),
            "entities": json.dumps([list(t) for t in enriched.entities], ensure_ascii=False),
            "keywords": json.dumps([list(t) for t in enriched.keywords], ensure_ascii=False),
            "keyword_summary": enriched.keyword_summary,
            "tfidf_vector_path": enriched.tfidf_vector_path,
            "embedding_path": enriched.embedding_path,
            "model_version": enriched.model_version,
            "enriched_at": enriched.enriched_at or datetime.now().isoformat(),
        })
        conn.commit()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search using FTS5."""
        conn = self.connect()
        # Escape FTS5 special chars
        safe_q = query.replace('"', '""')
        rows = conn.execute("""
            SELECT a.article_id, a.url, a.source, a.title, a.content_clean,
                   a.publish_date, a.category_name,
                   rank
            FROM articles_fts f
            JOIN articles a ON a.rowid = f.rowid
            WHERE articles_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (f'"{safe_q}"', limit)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        """Return summary statistics."""
        conn = self.connect()
        return {
            "total_articles": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
            "cleaned": conn.execute("SELECT COUNT(*) FROM articles WHERE status='cleaned'").fetchone()[0],
            "enriched": conn.execute("SELECT COUNT(*) FROM nlp_outputs").fetchone()[0],
            "sources": {r["source"]: r["cnt"] for r in conn.execute(
                "SELECT source, COUNT(*) as cnt FROM articles GROUP BY source"
            ).fetchall()},
            "date_range": conn.execute(
                "SELECT MIN(publish_date), MAX(publish_date) FROM articles WHERE publish_date IS NOT NULL"
            ).fetchone(),
        }

    def to_dataframe(self, query: str = "SELECT * FROM articles WHERE status='cleaned'") -> "pd.DataFrame":
        """Export query result to pandas DataFrame."""
        if not HAS_PANDAS:
            raise ImportError("pandas is required for to_dataframe()")
        conn = self.connect()
        return pd.read_sql_query(query, conn)

    def export_parquet(self, output_path: str | Path,
                       query: str = "SELECT * FROM articles WHERE status='cleaned'"):
        """Export to Parquet format."""
        if not HAS_PANDAS:
            raise ImportError("pandas is required for export_parquet()")
        df = self.to_dataframe(query)
        df.to_parquet(output_path, index=False, engine="pyarrow")
        logger.info(f"Exported {len(df)} rows to {output_path}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log_action(self, action: str, source_file: str,
                    records_in: int, records_out: int, details: str = ""):
        conn = self.connect()
        conn.execute("""
            INSERT INTO processing_log (action, source_file, records_in, records_out, details)
            VALUES (?, ?, ?, ?, ?)
        """, (action, source_file, records_in, records_out, details))
        conn.commit()
