from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from exports.exporter import Exporter
from pipeline.db import NewsDB
from pipeline.schema import RawArticle


ROOT = Path(__file__).resolve().parents[1]


def test_demo_pipeline_creates_articles_nlp_and_reports(tmp_path):
    env = os.environ.copy()
    env["NEWS_DATA_DIR"] = str(tmp_path)
    env["NEWS_DB_PATH"] = str(tmp_path / "news.db")
    result = subprocess.run(
        [sys.executable, "pipeline_cli.py", "--db", str(tmp_path / "news.db"), "demo", "--reset"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode == 0, result.stdout
    with sqlite3.connect(tmp_path / "news.db") as conn:
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        nlp_outputs = conn.execute("SELECT COUNT(*) FROM nlp_outputs").fetchone()[0]
    assert articles == 20
    assert nlp_outputs == 20
    assert (tmp_path / "reports" / "text_mining.json").exists()
    assert (tmp_path / "reports" / "analysis_report.json").exists()


def test_exporter_status_filter_uses_explicit_status_sets(tmp_path):
    db_path = tmp_path / "news.db"
    db = NewsDB(db_path)
    db.init()
    raw = RawArticle(
        article_id="export-1",
        url="https://example.com/export-1",
        source="test",
        source_name="Test",
        title="測試匯出文章",
        content="這是一篇用來測試匯出狀態篩選的文章，內容長度足夠進入資料庫。" * 3,
    )
    jsonl = tmp_path / "raw.jsonl"
    jsonl.write_text(json.dumps(raw.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")
    db.insert_raw_articles(jsonl)
    db.close()

    output = tmp_path / "exports" / "articles.jsonl"
    Exporter(db_path).to_jsonl(output, status="cleaned")

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["article_id"] == "export-1"
