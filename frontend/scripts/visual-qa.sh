#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3001}"
OUT_DIR="${OUT_DIR:-/tmp/news-visual-qa}"
mkdir -p "$OUT_DIR"

pages=(
  "data-quality"
  "analysis"
  "text-mining"
  "ml"
  "jobs"
  "articles"
)

for page in "${pages[@]}"; do
  npx playwright screenshot --full-page --wait-for-timeout=4000 --viewport-size=1440,1000 "$BASE_URL/$page" "$OUT_DIR/$page-desktop.png"
  npx playwright screenshot --full-page --wait-for-timeout=4000 --viewport-size=390,844 "$BASE_URL/$page" "$OUT_DIR/$page-mobile.png"
done

ls -lh "$OUT_DIR"
