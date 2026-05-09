"""
News data pipeline — import shortcuts.
"""

from pipeline.schema import RawArticle, CleanArticle, EnrichedArticle
from pipeline.text_cleaner import normalize
from pipeline.validator import (
    compute_dedup_hash,
    validate_raw,
    deduplicate_jsonl,
    merge_jsonl_files,
)

__all__ = [
    "RawArticle",
    "CleanArticle",
    "EnrichedArticle",
    "normalize",
    "compute_dedup_hash",
    "validate_raw",
    "deduplicate_jsonl",
    "merge_jsonl_files",
]
