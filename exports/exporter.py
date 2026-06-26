"""
Data export utilities for the news pipeline.

Supports:
  - CSV
  - Parquet
  - JSONL
  - HuggingFace Dataset

Usage:
    from exports.exporter import Exporter

    exp = Exporter(db_path="data/news.db")
    exp.to_csv("data/processed/export.csv")
    exp.to_parquet("data/processed/export.parquet")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pipeline.db import NewsDB

logger = logging.getLogger(__name__)


class Exporter:
    """Export cleaned/enriched articles to various formats."""

    def __init__(self, db_path: str | Path):
        self.db = NewsDB(db_path)
        self.db.connect()

    def _status_values(self, status: str) -> tuple[str, ...]:
        # 明確定義 pipeline 狀態集合，避免用字串大小比較狀態。
        if status == "raw":
            return ("raw", "cleaned", "enriched")
        if status == "enriched":
            return ("enriched",)
        return ("cleaned", "enriched")

    def _get_query(self, status: str = "cleaned", include_nlp: bool = False) -> tuple[str, tuple[str, ...]]:
        statuses = self._status_values(status)
        placeholders = ",".join("?" for _ in statuses)
        if include_nlp:
            return f"""
                SELECT a.*, n.tokens, n.pos_tags, n.entities, n.keywords,
                       n.keyword_summary, n.model_version
                FROM articles a
                LEFT JOIN nlp_outputs n ON a.article_id = n.article_id
                WHERE a.status IN ({placeholders})
            """, statuses
        return f"SELECT * FROM articles WHERE status IN ({placeholders})", statuses

    def _ensure_parent(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    # ------------------------------------------------------------------
    def to_csv(self, path: str | Path, status: str = "cleaned",
               include_nlp: bool = False):
        """Export to CSV."""
        import pandas as pd
        path = self._ensure_parent(path)
        query, params = self._get_query(status, include_nlp)
        df = pd.read_sql_query(query, self.db._conn, params=params)
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to {path}")

    def to_parquet(self, path: str | Path, status: str = "cleaned",
                   include_nlp: bool = False):
        """Export to Parquet."""
        import pandas as pd
        path = self._ensure_parent(path)
        query, params = self._get_query(status, include_nlp)
        df = pd.read_sql_query(query, self.db._conn, params=params)
        df.to_parquet(path, index=False, engine="pyarrow")
        logger.info(f"Exported {len(df)} rows to {path}")

    def to_jsonl(self, path: str | Path, status: str = "cleaned",
                 include_nlp: bool = False):
        """Export to JSONL."""
        path = self._ensure_parent(path)
        query, params = self._get_query(status, include_nlp)
        conn = self.db._conn
        rows = conn.execute(query, params).fetchall()

        count = 0
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                obj = dict(row)
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                count += 1
        logger.info(f"Exported {count} rows to {path}")

    def to_huggingface(self, dataset_name: str, status: str = "cleaned",
                       include_nlp: bool = False, private: bool = True):
        """Push to HuggingFace Hub (requires `datasets` package)."""
        try:
            from datasets import Dataset
        except ImportError:
            raise ImportError("pip install datasets to use to_huggingface()")

        query, params = self._get_query(status, include_nlp)
        conn = self.db._conn
        rows = conn.execute(query, params).fetchall()
        data = [dict(r) for r in rows]

        ds = Dataset.from_list(data)
        ds.push_to_hub(dataset_name, private=private)
        logger.info(f"Pushed {len(data)} rows to {dataset_name}")

    def summary(self) -> dict:
        """Print a summary of exportable data."""
        return self.db.stats()
