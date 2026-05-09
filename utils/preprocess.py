#!/usr/bin/env python
"""
Preprocess merged news data — tokenize, filter, and build index-ready format.

Reads from /mnt/c/data/information-retrieval/processed/merged.jsonl
Outputs cleaned JSONL with tokenized content.

Usage:
    python utils/preprocess.py
    python utils/preprocess.py --input /mnt/c/data/information-retrieval/processed/custom.jsonl
    python utils/preprocess.py --tokenizer jieba
"""

import json
import re
from pathlib import Path
from datetime import datetime

try:
    import jieba
except ImportError:
    jieba = None

INPUT_DEFAULT = Path("/mnt/c/data/information-retrieval/processed/merged.jsonl")
OUTPUT_DEFAULT = Path("/mnt/c/data/information-retrieval/processed/clean_tokenized.jsonl")

# Common Chinese + English stopwords (minimal set)
STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一個",
    "上", "也", "很", "到", "說", "會", "為", "這", "那", "但", "而", "與", "及",
    "其", "此", "等", "被", "把", "讓", "給", "對", "關於", "the", "a", "an", "is",
    "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "but",
}


def tokenize(text: str, engine: str = "jieba") -> list[str]:
    if engine == "jieba" and jieba:
        return [w for w in jieba.lcut(text) if w.strip() and w not in STOPWORDS]
    # fallback: simple character split for CJK, word split for English
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text)
    return [t for t in tokens if t not in STOPWORDS]


def preprocess(input_path: Path = INPUT_DEFAULT, output_path: Path = OUTPUT_DEFAULT,
               tokenizer: str = "jieba"):
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Clean content
            content = obj.get("content", "")
            content = re.sub(r"\s+", " ", content).strip()
            tokens = tokenize(content, tokenizer)

            obj["content_clean"] = content
            obj["tokens"] = tokens
            obj["token_count"] = len(tokens)
            obj["processed_at"] = datetime.now().isoformat()

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1

    print(f"Processed {count:,} articles → {output_path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=INPUT_DEFAULT)
    p.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    p.add_argument("--tokenizer", choices=["jieba", "char"], default="jieba")
    args = p.parse_args()
    preprocess(args.input, args.output, args.tokenizer)
