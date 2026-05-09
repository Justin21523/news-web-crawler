"""
Data schemas for the news pipeline.

Defines validated schemas for raw, cleaned, and enriched article records.
Uses Python dataclasses for type safety and self-documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Raw article (direct from crawler)
# ---------------------------------------------------------------------------
@dataclass
class RawArticle:
    """Schema for raw crawled article — matches crawler JSONL output."""
    article_id: str
    url: str
    source: str
    source_name: str
    title: str
    content: str
    author: str = ""
    publish_date: Optional[str] = None
    category: str = ""
    category_name: str = ""
    tags: list[str] = field(default_factory=list)
    image_url: str = ""
    crawled_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> RawArticle:
        return cls(
            article_id=d.get("article_id", ""),
            url=d.get("url", ""),
            source=d.get("source", ""),
            source_name=d.get("source_name", ""),
            title=d.get("title", ""),
            content=d.get("content", ""),
            author=d.get("author", ""),
            publish_date=d.get("publish_date"),
            category=d.get("category", ""),
            category_name=d.get("category_name", ""),
            tags=d.get("tags", []),
            image_url=d.get("image_url", ""),
            crawled_at=d.get("crawled_at", ""),
        )

    def is_valid(self) -> bool:
        return bool(self.title.strip() and self.content.strip() and self.url.strip())


# ---------------------------------------------------------------------------
# Cleaned article (after text normalization + validation)
# ---------------------------------------------------------------------------
@dataclass
class CleanArticle:
    """Schema after cleaning / normalization / dedup."""
    article_id: str
    url: str
    source: str
    source_name: str
    title: str
    title_clean: str                    # normalized title
    content_clean: str                  # normalized content
    author: str
    publish_date: Optional[str]
    category: str
    category_name: str
    tags: list[str]
    image_url: str
    crawled_at: str
    cleaned_at: str = ""
    dedup_hash: str = ""                # MD5 of title+url
    char_count: int = 0
    word_count: int = 0                 # after tokenization
    lang: str = "zh-Hant"               # detected language

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: RawArticle, title_clean: str, content_clean: str,
                 dedup_hash: str) -> CleanArticle:
        return cls(
            article_id=raw.article_id,
            url=raw.url,
            source=raw.source,
            source_name=raw.source_name,
            title=raw.title,
            title_clean=title_clean,
            content_clean=content_clean,
            author=raw.author,
            publish_date=raw.publish_date,
            category=raw.category,
            category_name=raw.category_name,
            tags=raw.tags,
            image_url=raw.image_url,
            crawled_at=raw.crawled_at,
            cleaned_at=datetime.now().isoformat(),
            dedup_hash=dedup_hash,
            char_count=len(content_clean),
        )


# ---------------------------------------------------------------------------
# Enriched article (after NLP pipeline + feature extraction)
# ---------------------------------------------------------------------------
@dataclass
class EnrichedArticle:
    """Schema after NLP enrichment — ready for ML / analysis."""
    article_id: str
    url: str
    source: str
    title: str
    content_clean: str
    publish_date: Optional[str]
    category: str
    category_name: str
    tags: list[str]

    # NLP outputs
    tokens: list[str] = field(default_factory=list)
    pos_tags: list[tuple[str, str]] = field(default_factory=list)   # [(word, pos), ...]
    entities: list[tuple[str, str]] = field(default_factory=list)   # [(entity, type), ...]
    keywords: list[tuple[str, float]] = field(default_factory=list)  # [(term, score), ...]

    # Feature vectors (stored as JSON-serializable lists or file paths)
    tfidf_vector_path: str = ""
    embedding_path: str = ""
    keyword_summary: str = ""             # top-5 keywords joined

    # Metadata
    enriched_at: str = ""
    model_version: str = ""               # which tokenizer / model version

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert tuples to lists for JSON serialization
        d["pos_tags"] = [list(t) for t in self.pos_tags]
        d["entities"] = [list(t) for t in self.entities]
        d["keywords"] = [list(t) for t in self.keywords]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> EnrichedArticle:
        return cls(
            article_id=d["article_id"],
            url=d["url"],
            source=d["source"],
            title=d["title"],
            content_clean=d["content_clean"],
            publish_date=d.get("publish_date"),
            category=d.get("category", ""),
            category_name=d.get("category_name", ""),
            tags=d.get("tags", []),
            tokens=d.get("tokens", []),
            pos_tags=[tuple(t) for t in d.get("pos_tags", [])],
            entities=[tuple(t) for t in d.get("entities", [])],
            keywords=[tuple(t) for t in d.get("keywords", [])],
            tfidf_vector_path=d.get("tfidf_vector_path", ""),
            embedding_path=d.get("embedding_path", ""),
            keyword_summary=d.get("keyword_summary", ""),
            enriched_at=d.get("enriched_at", ""),
            model_version=d.get("model_version", ""),
        )
