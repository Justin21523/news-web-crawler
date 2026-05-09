#!/usr/bin/env python
"""
CKIP GPU 批次處理管線

功能：
  1. 將 raw 狀態文章清理為 cleaned
  2. 使用 CKIP + GPU 進行 NLP 處理（分詞/詞性標記/實體辨識）
  3. 建立 TF-IDF 模型
  4. 匯出結果

使用方式：
  conda run -n data_env python run_ckip_gpu_pipeline.py [--batch-size 128] [--limit 1000]
"""

import sys
import json
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime

# 加入專案路徑
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.db import NewsDB
from pipeline.schema import CleanArticle, EnrichedArticle
from pipeline.text_cleaner import normalize
from pipeline.validator import compute_dedup_hash
from nlp.ckip_pipeline import CKIPPipeline
from utils.resource_manager import ResourceManager

DB_PATH = "/mnt/c/data/information-retrieval/news.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ckip_gpu_pipeline")


def step1_clean_articles(db: NewsDB, batch_size: int = 1000, limit: int = None):
    """步驟 1: 將 raw 狀態文章轉換為 cleaned（直接使用 SQL 更新）"""
    logger.info("=" * 60)
    logger.info("步驟 1: 文字清理 (raw → cleaned)")
    logger.info("=" * 60)
    
    conn = db.connect()
    
    # 直接更新所有 raw 狀態的文章
    query = "SELECT article_id, title, content_clean FROM articles WHERE status='raw'"
    if limit:
        query += f" LIMIT {limit}"
    
    rows = conn.execute(query).fetchall()
    total = len(rows)
    logger.info(f"找到 {total:,} 篇 raw 狀態文章需要清理")
    
    if total == 0:
        logger.info("沒有需要清理的文章，跳過此步驟")
        return 0
    
    cleaned_count = 0
    start_time = time.time()
    
    for i, row in enumerate(rows, 1):
        try:
            # 清理標題和內容
            title_clean = normalize(row["title"])
            content_clean = normalize(row["content_clean"] or "")
            
            # 計算統計
            char_count = len(content_clean)
            word_count = len(content_clean.split()) if content_clean else 0
            
            # 如果內容為空則跳過
            if not content_clean or char_count < 50:
                continue
            
            # 直接 SQL 更新
            conn.execute("""
                UPDATE articles 
                SET title_clean = ?, 
                    content_clean = ?,
                    char_count = ?,
                    word_count = ?,
                    cleaned_at = ?,
                    status = 'cleaned'
                WHERE article_id = ?
            """, (title_clean, content_clean, char_count, word_count, 
                  datetime.now().isoformat(), row["article_id"]))
            
            cleaned_count += 1
            
            # 批次提交
            if cleaned_count % batch_size == 0:
                conn.commit()
            
            # 顯示進度
            if i % 5000 == 0 or i == total:
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                logger.info(f"  進度: {i:,}/{total:,} ({i/total*100:.1f}%) - {speed:.0f} 篇/秒")
                
        except Exception as e:
            logger.debug(f"清理文章 {row['article_id']} 失敗: {e}")
            continue
    
    conn.commit()
    elapsed = time.time() - start_time
    logger.info(f"✅ 清理完成: {cleaned_count:,} 篇，耗時 {elapsed:.1f} 秒")
    return cleaned_count


def step2_ckip_nlp(db: NewsDB, batch_size: int = 128, limit: int = None):
    """步驟 2: CKIP GPU NLP 處理"""
    logger.info("=" * 60)
    logger.info("步驟 2: CKIP GPU NLP 處理")
    logger.info("=" * 60)
    
    db.connect()
    rm = ResourceManager(max_ram_gb=8.0)
    rm.log_ram_status("CKIP NLP 開始")
    
    # 初始化 CKIP Pipeline（使用 GPU）
    device_id = rm.get_cuda_device_id()
    logger.info(f"使用裝置: {rm.get_device()} (CUDA:{device_id})")
    
    nlp = CKIPPipeline(device_id=device_id)
    
    # 查詢需要 NLP 處理的文章（status='cleaned' 且不在 nlp_outputs 中）
    query = """
        SELECT article_id, title_clean, content_clean 
        FROM articles 
        WHERE status='cleaned' 
        AND article_id NOT IN (SELECT article_id FROM nlp_outputs)
    """
    if limit:
        query += f" LIMIT {limit}"
    
    conn = db.connect()
    rows = conn.execute(query).fetchall()
    total = len(rows)
    logger.info(f"找到 {total:,} 篇需要 NLP 處理的文章")
    
    if total == 0:
        logger.info("沒有需要處理的文章，跳過此步驟")
        return 0
    
    start_time = time.time()
    processed = 0
    
    # 批次處理
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_rows = rows[batch_start:batch_end]
        
        # 準備文字
        texts = [f"{r['title_clean'] or ''} {r['content_clean'] or ''}" for r in batch_rows]
        
        # CKIP 批次處理
        try:
            results = nlp.process_batch(texts)
            
            # 寫入資料庫
            for row, result in zip(batch_rows, results):
                enriched = EnrichedArticle(
                    article_id=row["article_id"],
                    url="",
                    title="",
                    content_clean="",
                    source="",
                    publish_date=None,
                    category="",
                    category_name="",
                    tags=[],
                    tokens=result.filtered_words,
                    pos_tags=result.words_with_pos,
                    entities=result.entities,
                    keywords=[],
                    keyword_summary=", ".join(w for w, _ in result.words_with_pos[:5]),
                    model_version=f"ckip-v1-cuda{device_id}",
                )
                db.upsert_nlp(enriched)
                processed += 1
                
        except Exception as e:
            logger.error(f"批次處理失敗 (batch {batch_start}-{batch_end}): {e}")
            continue
        
        # 顯示進度
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / speed if speed > 0 else 0
        logger.info(
            f"  進度: {processed:,}/{total:,} ({processed/total*100:.1f}%) - "
            f"{speed:.1f} 篇/秒 - 預計剩餘 {eta/60:.1f} 分鐘"
        )
        
        # 記憶體監控
        if (batch_start // batch_size) % 10 == 0:
            rm.log_ram_status(f"CKIP 處理中 ({processed:,}/{total:,})")
    
    elapsed = time.time() - start_time
    speed = processed / elapsed if elapsed > 0 else 0
    logger.info(f"✅ CKIP NLP 完成: {processed:,} 篇，耗時 {elapsed:.1f} 秒 ({speed:.1f} 篇/秒)")
    return processed


def step3_tfidf(db: NewsDB):
    """步驟 3: 建立 TF-IDF 模型"""
    logger.info("=" * 60)
    logger.info("步驟 3: 建立 TF-IDF 模型")
    logger.info("=" * 60)
    
    from features.tfidf import TfidfBuilder
    
    conn = db.connect()
    rows = conn.execute(
        "SELECT article_id, content_clean FROM articles WHERE status='cleaned'"
    ).fetchall()
    
    if not rows:
        logger.info("沒有 cleaned 文章，跳過 TF-IDF")
        return
    
    documents, doc_ids = [], []
    for r in rows:
        text = r["content_clean"] or ""
        # 如果有 tokens 就用 tokens，否則用字元分割
        tokens = text.split() if " " in text else list(text)
        documents.append(" ".join(tokens))
        doc_ids.append(r["article_id"])
    
    logger.info(f"使用 {len(documents):,} 篇文章建立 TF-IDF 模型")
    
    builder = TfidfBuilder(max_features=50000, min_df=2)
    builder.fit(documents, doc_ids)
    
    out_dir = Path("/mnt/c/data/information-retrieval/models/tfidf")
    builder.save(out_dir)
    
    logger.info(f"✅ TF-IDF 完成: 詞彙量={builder.vocabulary_size:,}")
    logger.info(f"   Top 10 詞彙: {builder.get_top_terms(10)}")


def step4_export(db: NewsDB):
    """步驟 4: 匯出結果"""
    logger.info("=" * 60)
    logger.info("步驟 4: 匯出處理結果")
    logger.info("=" * 60)
    
    from exports.exporter import Exporter
    
    db.connect()
    exp = Exporter(db.db_path)
    
    output_path = "/mnt/c/data/information-retrieval/processed/articles_full.parquet"
    exp.to_parquet(output_path, include_nlp=True)
    
    logger.info(f"✅ 匯出完成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="CKIP GPU 批次處理管線")
    parser.add_argument("--batch-size", type=int, default=128, help="CKIP 批次大小 (預設: 128)")
    parser.add_argument("--limit", type=int, default=None, help="限制處理文章數 (測試用)")
    parser.add_argument("--skip-clean", action="store_true", help="跳過清理步驟")
    parser.add_argument("--skip-nlp", action="store_true", help="跳過 NLP 步驟")
    parser.add_argument("--skip-tfidf", action="store_true", help="跳過 TF-IDF 步驟")
    parser.add_argument("--skip-export", action="store_true", help="跳過匯出步驟")
    args = parser.parse_args()
    
    logger.info("🚀 CKIP GPU 管線啟動")
    logger.info(f"   批次大小: {args.batch_size}")
    logger.info(f"   限制文章數: {args.limit if args.limit else '無限制'}")
    logger.info(f"   資料庫: {DB_PATH}")
    
    db = NewsDB(DB_PATH)
    db.init()
    
    total_start = time.time()
    
    # 步驟 1: 文字清理
    if not args.skip_clean:
        step1_clean_articles(db, batch_size=1000, limit=args.limit)
    
    # 步驟 2: CKIP NLP
    if not args.skip_nlp:
        step2_ckip_nlp(db, batch_size=args.batch_size, limit=args.limit)
    
    # 步驟 3: TF-IDF
    if not args.skip_tfidf:
        step3_tfidf(db)
    
    # 步驟 4: 匯出
    if not args.skip_export:
        step4_export(db)
    
    # 顯示統計
    stats = db.stats()
    logger.info("\n" + "=" * 60)
    logger.info("📊 最終統計")
    logger.info("=" * 60)
    for k, v in stats.items():
        logger.info(f"   {k}: {v}")
    
    total_elapsed = time.time() - total_start
    logger.info(f"\n✅ 管線全部完成！總耗時 {total_elapsed/60:.1f} 分鐘")


if __name__ == "__main__":
    main()
