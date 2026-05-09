#!/usr/bin/env python
"""
Merge & clean crawled JSONL files.

- Merge all files in /mnt/c/data/information-retrieval/raw/ into one deduplicated file.
- Remove articles with empty title/content.
- Output to /mnt/c/data/information-retrieval/processed/merged.jsonl

Usage:
    python utils/merge_clean.py
    python utils/merge_clean.py --output /mnt/c/data/information-retrieval/processed/clean_2024.jsonl
    python utils/merge_clean.py --dry-run  # stats only
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

RAW_DIR = Path("/mnt/c/data/information-retrieval/raw")
DEFAULT_OUTPUT = Path("/mnt/c/data/information-retrieval/processed/merged.jsonl")


def file_hash(line: str) -> str:
    """Hash a JSONL line by title+url for dedup."""
    try:
        obj = json.loads(line)
        key = f"{obj.get('title','')}||{obj.get('url','')}"
        return hashlib.md5(key.encode()).hexdigest()
    except json.JSONDecodeError:
        return ""


def merge_clean(output: Path = DEFAULT_OUTPUT, dry_run: bool = False):
    raw_files = sorted(RAW_DIR.glob("*.jsonl"))
    if not raw_files:
        print(f"No JSONL files found in {RAW_DIR}")
        return

    print(f"Found {len(raw_files)} raw file(s). Merging...")

    seen = set()
    total, dupes, invalid, kept = 0, 0, 0, 0

    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        out_f = open(output, "w", encoding="utf-8")

    for fp in raw_files:
        for line in fp.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            total += 1

            # validation
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if not obj.get("title") or not obj.get("content"):
                invalid += 1
                continue

            # dedup
            h = file_hash(line)
            if h in seen:
                dupes += 1
                continue
            seen.add(h)
            kept += 1

            if not dry_run:
                out_f.write(line + "\n")

    if not dry_run:
        out_f.close()

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Results:")
    print(f"  Total lines : {total:>8,}")
    print(f"  Kept        : {kept:>8,}")
    print(f"  Duplicates  : {dupes:>8,}")
    print(f"  Invalid     : {invalid:>8,}")
    if not dry_run:
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"  Output      : {output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    merge_clean(args.output, args.dry_run)
