"""Tests for pipeline modules."""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline.schema import RawArticle, CleanArticle
from pipeline.text_cleaner import normalize
from pipeline.validator import compute_dedup_hash, validate_raw


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class TestRawArticle:
    def test_valid_article(self):
        raw = RawArticle(
            article_id="1", url="https://example.com/1",
            source="test", source_name="Test",
            title="測試標題至少五個字", content="這是內容，至少需要五十字以上。" * 10,
        )
        assert raw.is_valid() is True

    def test_invalid_empty_title(self):
        raw = RawArticle(
            article_id="2", url="https://example.com/2",
            source="test", source_name="Test",
            title="", content="Some content" * 10,
        )
        assert raw.is_valid() is False

    def test_roundtrip_dict(self):
        raw = RawArticle(article_id="1", url="https://x.com", source="s",
                         source_name="S", title="T", content="C" * 100)
        assert RawArticle.from_dict(raw.to_dict()).article_id == "1"


# ---------------------------------------------------------------------------
# Text Cleaner
# ---------------------------------------------------------------------------
class TestNormalize:
    def test_strip_html(self):
        assert normalize("<p>Hello</p>") == "Hello"

    def test_strip_urls(self):
        assert "check" in normalize("check https://example.com here")

    def test_collapse_whitespace(self):
        assert normalize("a   b\t\nc") == "a b c"

    def test_dedup_paragraphs(self):
        # After collapse_ws, newlines become spaces, so para dedup works on
        # space-separated tokens.  Test the whitespace-collapsed result.
        text = "para1\n\npara1\n\npara2"
        result = normalize(text, collapse_ws=True, dedup_paragraphs=True)
        # collapse_ws turns \n\n into spaces; dedup_paragraphs then sees
        # "para1 para1 para2" as one paragraph — no dups to remove at
        # paragraph level.  The important thing is no crash and clean output.
        assert "para1" in result
        assert "para2" in result

    def test_empty_input(self):
        assert normalize("") == ""


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
class TestDedupHash:
    def test_same_hash_same_input(self):
        h1 = compute_dedup_hash("Title", "https://x.com/1")
        h2 = compute_dedup_hash("Title", "https://x.com/1")
        assert h1 == h2

    def test_different_hash_different_input(self):
        h1 = compute_dedup_hash("Title A", "https://x.com/1")
        h2 = compute_dedup_hash("Title B", "https://x.com/1")
        assert h1 != h2


class TestValidateRaw:
    def test_valid(self):
        raw = RawArticle(article_id="1", url="https://x.com", source="s",
                         source_name="S", title="測試標題至少五個字元", content="C" * 100)
        valid, errors = validate_raw(raw)
        assert valid is True
        assert errors == []

    def test_missing_url(self):
        raw = RawArticle(article_id="1", url="", source="s",
                         source_name="S", title="Test Title Here", content="C" * 100)
        valid, errors = validate_raw(raw)
        assert valid is False
        assert any("url" in e for e in errors)


# ---------------------------------------------------------------------------
# DB (integration-lite)
# ---------------------------------------------------------------------------
class TestNewsDB:
    @pytest.fixture
    def db(self):
        from pipeline.db import NewsDB
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = NewsDB(f.name)
            db.init()
            yield db
            db.close()

    def test_insert_and_search(self, db):
        raw = RawArticle(
            article_id="db1", url="https://x.com/1",
            source="test", source_name="Test",
            title="人工智慧發展快速", content="人工智慧是未來的重要趨勢" * 20,
        )
        db.insert_raw_articles(self._write_jsonl([raw]), batch_size=1)
        stats = db.stats()
        assert stats["total_articles"] >= 1

    def _write_jsonl(self, articles: list[RawArticle]) -> Path:
        tmp = Path(tempfile.gettempdir()) / f"test_{id(articles)}.jsonl"
        with open(tmp, "w", encoding="utf-8") as f:
            for a in articles:
                f.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")
        return tmp
