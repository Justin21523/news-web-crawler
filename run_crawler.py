#!/usr/bin/env python
"""
Run crawler — single entry point

Usage:
    python run_crawler.py cna --days 7
    python run_crawler.py pts --start-date 2024-01-01 --end-date 2024-01-31
    python run_crawler.py ltn --max-articles 1000
    python run_crawler.py --all --days 3
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

SPIDER_MAP = {
    "cna": "spiders/cna.py",
    "pts": "spiders/pts.py",
    "ltn": "spiders/ltn.py",
}

DATA_DIR = os.getenv("NEWS_DATA_DIR", "data")
SETTINGS = "configs.settings"


def run_spider(name: str, extra_args: list[str] | None = None):
    raw_dir = Path(DATA_DIR) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / f"{name}_news_%(time)s.jsonl"
    cmd = [
        "scrapy", "runspider",
        SPIDER_MAP[name],
        "-s", SETTINGS,
        "-O", str(output_path),
    ]
    if extra_args:
        cmd.extend(extra_args)
    print(f"[run] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="News Crawler Runner")
    parser.add_argument("spider", nargs="?", choices=list(SPIDER_MAP.keys()) + ["all"],
                        help="Spider name or 'all'")
    parser.add_argument("--days", type=int, default=7, help="Crawl last N days")
    parser.add_argument("--start-date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--max-articles", type=int, help="Max articles per spider")
    parser.add_argument("--categories", type=str, help="Comma-separated categories (CNA only)")
    args = parser.parse_args()

    # Compute dates
    end = args.end_date or datetime.now().strftime("%Y-%m-%d")
    start = args.start_date or (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    common = [
        "-a", f"start_date={start}",
        "-a", f"end_date={end}",
    ]
    if args.max_articles:
        common.extend(["-a", f"max_articles={args.max_articles}"])
    if args.categories:
        common.extend(["-a", f"categories={args.categories}"])

    targets = list(SPIDER_MAP.keys()) if args.spider == "all" else [args.spider]
    if not args.spider:
        parser.print_help()
        sys.exit(1)

    for sp in targets:
        rc = run_spider(sp, common)
        if rc != 0:
            print(f"[warn] Spider {sp} exited with code {rc}")


if __name__ == "__main__":
    main()
