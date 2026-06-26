from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings

import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.db import DDL, NewsDB  # noqa: E402


JOBS_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    params_json TEXT NOT NULL DEFAULT '{}',
    progress_done INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    log_path TEXT,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    ended_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);

CREATE TABLE IF NOT EXISTS model_artifacts (
    artifact_id TEXT PRIMARY KEY,
    job_id INTEGER,
    target TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    artifact_dir TEXT NOT NULL,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_model_artifacts_created_at ON model_artifacts(created_at);
CREATE INDEX IF NOT EXISTS idx_model_artifacts_target_model ON model_artifacts(target, model);
"""

TEXT_MINING_ASSIGNMENTS_DDL = """
CREATE TABLE IF NOT EXISTS text_mining_runs (
    run_id TEXT PRIMARY KEY,
    assignment_type TEXT NOT NULL,
    method TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS text_mining_assignments (
    run_id TEXT NOT NULL,
    assignment_type TEXT NOT NULL,
    article_id TEXT NOT NULL,
    label TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    terms_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(run_id, assignment_type, article_id, label),
    FOREIGN KEY(run_id) REFERENCES text_mining_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_text_mining_assignments_type_label
ON text_mining_assignments(assignment_type, label);

CREATE INDEX IF NOT EXISTS idx_text_mining_assignments_article
ON text_mining_assignments(article_id);
"""

REPORT_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS report_metadata (
    report_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',
    tags_json TEXT NOT NULL DEFAULT '[]',
    archived_at TEXT,
    trashed_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_report_metadata_status ON report_metadata(status);
CREATE INDEX IF NOT EXISTS idx_report_metadata_updated_at ON report_metadata(updated_at);
"""

ENTITY_EXTRACTION_DDL = """
CREATE TABLE IF NOT EXISTS entity_extraction_runs (
    run_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    strategy TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS entity_extraction_outputs (
    run_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    entities_json TEXT NOT NULL DEFAULT '[]',
    provider TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(run_id, article_id),
    FOREIGN KEY(run_id) REFERENCES entity_extraction_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_extraction_outputs_article
ON entity_extraction_outputs(article_id);

CREATE INDEX IF NOT EXISTS idx_entity_extraction_runs_created
ON entity_extraction_runs(created_at);
"""


FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
  INSERT INTO articles_fts(rowid, title_clean, content_clean)
  VALUES (new.rowid, new.title_clean, new.content_clean);
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title_clean, content_clean)
  VALUES('delete', old.rowid, old.title_clean, old.content_clean);
END;

CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title_clean, content_clean)
  VALUES('delete', old.rowid, old.title_clean, old.content_clean);
  INSERT INTO articles_fts(rowid, title_clean, content_clean)
  VALUES (new.rowid, new.title_clean, new.content_clean);
END;
"""


class Database:
    def __init__(self, db_path: str | Path | None = None):
        settings = get_settings()
        self.db_path = Path(db_path or settings.resolved_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        db = NewsDB(self.db_path)
        db.init()
        db.close()
        with self.connect() as conn:
            conn.executescript(JOBS_DDL)
            conn.executescript(TEXT_MINING_ASSIGNMENTS_DDL)
            conn.executescript(REPORT_METADATA_DDL)
            conn.executescript(ENTITY_EXTRACTION_DDL)
            conn.executescript(FTS_TRIGGERS)
            conn.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")
            conn.execute(
                """
                UPDATE jobs
                SET status='abandoned', ended_at=datetime('now'), error='API restarted before job completed'
                WHERE status IN ('queued', 'running')
                """
            )
            conn.commit()

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.execute(query, params)
            conn.commit()
            return int(cur.lastrowid or 0)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
