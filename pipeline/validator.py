"""
Validation and deduplication utilities for the news pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Iterable

from pipeline.schema import RawArticle, CleanArticle

logger = logging.getLogger(__name__)

# Minimum content length to consider an article valid
MIN_CONTENT_CHARS = 50
MIN_TITLE_CHARS = 3

# Required fields for a raw article
REQUIRED_RAW_FIELDS = {"article_id", "url", "title", "content", "source"}


def compute_dedup_hash(title: str, url: str) -> str:
    """Deterministic hash for deduplication (title + URL)."""
    key = f"{title.strip().lower()}||{url.strip().lower()}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def validate_raw(article: RawArticle) -> tuple[bool, list[str]]:
    """
    Validate a raw article record.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    for fld in REQUIRED_RAW_FIELDS:
        if not getattr(article, fld, ""):
            errors.append(f"Missing required field: {fld}")

    if len(article.title.strip()) < MIN_TITLE_CHARS:
        errors.append(f"Title too short ({len(article.title.strip())} chars < {MIN_TITLE_CHARS})")

    if len(article.content.strip()) < MIN_CONTENT_CHARS:
        errors.append(f"Content too short ({len(article.content.strip())} chars < {MIN_CONTENT_CHARS})")

    return len(errors) == 0, errors


def deduplicate_jsonl(input_path: Path, output_path: Path) -> dict:
    """
    Deduplicate a JSONL file by (title, url) hash.

    Args:
        input_path: Path to input JSONL.
        output_path: Path to deduplicated output JSONL.

    Returns:
        Stats dict with total, kept, dupes, invalid counts.
    """
    seen: set[str] = set()
    stats = {"total": 0, "kept": 0, "dupes": 0, "invalid": 0}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            stats["total"] += 1

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                stats["invalid"] += 1
                continue

            h = compute_dedup_hash(obj.get("title", ""), obj.get("url", ""))
            if h in seen:
                stats["dupes"] += 1
                continue
            seen.add(h)
            stats["kept"] += 1
            fout.write(line + "\n")

    logger.info(f"Dedup complete: {stats['total']:,} → {stats['kept']:,} "
                f"({stats['dupes']:,} dupes, {stats['invalid']:,} invalid)")
    return stats


def merge_jsonl_files(input_dir: Path, output_path: Path,
                      pattern: str = "*.jsonl", limit: int | None = None) -> dict:
    """
    Merge multiple JSONL files, deduplicating globally.

    Args:
        input_dir: Directory containing JSONL files.
        output_path: Output merged + deduped JSONL.
        pattern: Glob pattern for files to include.
        limit: Max articles to keep (None = all).

    Returns:
        Stats dict.
    """
    files = sorted(Path(input_dir).glob(pattern))
    if not files:
        logger.warning(f"No files matching {pattern} in {input_dir}")
        return {"total": 0, "kept": 0, "dupes": 0, "invalid": 0}

    logger.info(f"Merging {len(files)} file(s) from {input_dir}")

    seen: set[str] = set()
    stats = {"total": 0, "kept": 0, "dupes": 0, "invalid": 0}
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fout:
        for fp in files:
            for line in fp.open("r", encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                stats["total"] += 1

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    stats["invalid"] += 1
                    continue

                h = compute_dedup_hash(obj.get("title", ""), obj.get("url", ""))
                if h in seen:
                    stats["dupes"] += 1
                    continue
                seen.add(h)
                stats["kept"] += 1
                fout.write(line + "\n")

                if limit and stats["kept"] >= limit:
                    logger.info(f"Reached limit {limit}, stopping.")
                    return stats

    logger.info(f"Merge complete: {stats['total']:,} → {stats['kept']:,} "
                f"({stats['dupes']:,} dupes, {stats['invalid']:,} invalid)")
    return stats
