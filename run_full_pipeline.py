#!/usr/bin/env python
"""
CKIP GPU 大量處理管線（688K 篇文章優化版）

功能：
  1. 文字清理（raw → cleaned）
  2. CKIP GPU NLP 處理（斷詞/詞性/實體辨識）
  3. TF-IDF 建模
  4. 匯出 Parquet

特色：
  - 批次大小 512（最大化 GPU 使用）
  - 自動進度追蹤和 ETA 預估
  - 記憶體監控
  - 斷點續傳（可中斷後繼續）

使用方式：
  conda run -n data_env python run_full_pipeline.py [--batch-size 512]
"""

import sys
import json
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.db import NewsDB
from pipeline.text_cleaner import normalize
from nlp.ckip_pipeline import CKIPPipeline
from utils.resource_manager import ResourceManager

DB_PATH = "/mnt/c/data/information-retrieval/news.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("full_pipeline")


def format_time(seconds):
    """格式化時間顯示"""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f}分鐘"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小時"


def step1_clean_articles(db: NewsDB, batch_size: int = 2000):
    """步驟 1: 文字清理（最佳化批次處理）"""
    logger.info("=" * 70)
    logger.info("步驟 1: 文字清理 (raw → cleaned)")
    logger.info("=" * 70)
    
    conn = db.connect()
    
    # 查詢需要清理的文章
    rows = conn.execute(
        "SELECT article_id, title, content_clean FROM articles WHERE status='raw'"
    ).fetchall()
    
    total = len(rows)
    if total == 0:
        # 檢查是否已經清理過
        cleaned = conn.execute("SELECT COUNT(*) FROM articles WHERE status='cleaned'").fetchone()[0]
        logger.info(f"✅ 沒有需要清理的文章（已有 {cleaned:,} 篇 cleaned）")
        return cleaned
    
    logger.info(f"📝 找到 {total:,} 篇 raw 狀態文章需要清理")
    
    cleaned_count = 0
    start_time = time.time()
    errors = 0
    
    for i, row in enumerate(rows, 1):
        try:
            title_clean = normalize(row["title"])
            content_clean = normalize(row["content_clean"] or "")
            char_count = len(content_clean)
            
            if not content_clean or char_count < 50:
                continue
            
            conn.execute("""
                UPDATE articles 
                SET title_clean = ?, content_clean = ?, char_count = ?,
                    word_count = ?, cleaned_at = ?, status = 'cleaned'
                WHERE article_id = ?
            """, (
                title_clean, content_clean, char_count,
                len(content_clean.split()), datetime.now().isoformat(),
                row["article_id"]
            ))
            
            cleaned_count += 1
            
            if cleaned_count % batch_size == 0:
                conn.commit()
            
            # 進度顯示
            if i % 10000 == 0 or i == total:
                elapsed = time.time() - start_time
                speed = i / elapsed
                eta = (total - i) / speed
                logger.info(
                    f"  📊 進度: {i:,}/{total:,} ({i/total*100:.1f}%) | "
                    f"速度: {speed:.0f} 篇/秒 | "
                    f"預計剩餘: {format_time(eta)}"
                )
                
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.debug(f"清理失敗: {e}")
            continue
    
    conn.commit()
    elapsed = time.time() - start_time
    logger.info(f"✅ 清理完成: {cleaned_count:,} 篇，耗時 {format_time(elapsed)}")
    return cleaned_count


def step2_ckip_nlp(db: NewsDB, batch_size: int = 512):
    """步驟 2: CKIP GPU NLP 處理（大量優化版）"""
    logger.info("=" * 70)
    logger.info("步驟 2: CKIP GPU NLP 處理（批次大小: {}）".format(batch_size))
    logger.info("=" * 70)
    
    conn = db.connect()
    rm = ResourceManager(max_ram_gb=12.0)
    rm.log_ram_status("CKIP NLP 開始")
    
    # 初始化 CKIP
    device_id = rm.get_cuda_device_id()
    logger.info(f"🎮 使用裝置: {rm.get_device()} (CUDA:{device_id})")
    logger.info(f"⚡ 批次大小: {batch_size}")
    
    nlp = CKIPPipeline(device_id=device_id)
    
    # 查詢需要 NLP 的文章
    rows = conn.execute("""
        SELECT article_id, title_clean, content_clean 
        FROM articles 
        WHERE status='cleaned' 
        AND article_id NOT IN (SELECT article_id FROM nlp_outputs)
    """).fetchall()
    
    total = len(rows)
    if total == 0:
        enriched = conn.execute("SELECT COUNT(*) FROM nlp_outputs").fetchone()[0]
        logger.info(f"✅ 沒有需要 NLP 的文章（已有 {enriched:,} 篇 enriched）")
        return enriched
    
    logger.info(f"📝 找到 {total:,} 篇需要 NLP 處理的文章")
    
    # 預估時間
    estimated_speed = 6.7  # 篇/秒（從測試得出）
    estimated_time = total / estimated_speed
    logger.info(f"⏱️  預估時間: {format_time(estimated_time)}")
    
    start_time = time.time()
    processed = 0
    errors = 0
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_rows = rows[batch_start:batch_end]
        
        try:
            # 準備文字
            texts = [f"{r['title_clean'] or ''} {r['content_clean'] or ''}" for r in batch_rows]
            
            # CKIP 批次處理
            results = nlp.process_batch(texts)
            
            # 批次寫入
            for row, result in zip(batch_rows, results):
                try:
                    conn.execute("""
                        INSERT INTO nlp_outputs (
                            article_id, tokens, pos_tags, entities, keywords,
                            keyword_summary, model_version, enriched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(article_id) DO UPDATE SET
                            tokens=excluded.tokens,
                            pos_tags=excluded.pos_tags,
                            entities=excluded.entities,
                            enriched_at=excluded.enriched_at
                    """, (
                        row["article_id"],
                        json.dumps(result.filtered_words, ensure_ascii=False),
                        json.dumps([list(t) for t in result.words_with_pos], ensure_ascii=False),
                        json.dumps([list(t) for t in result.entities], ensure_ascii=False),
                        json.dumps([], ensure_ascii=False),
                        ", ".join(w for w, _ in result.words_with_pos[:5]),
                        f"ckip-v1-cuda{device_id}",
                        datetime.now().isoformat()
                    ))
                    processed += 1
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        logger.debug(f"寫入失敗: {e}")
                    continue
            
            # 每 10 個批次提交一次
            if (batch_start // batch_size) % 10 == 0:
                conn.commit()
            
        except Exception as e:
            logger.error(f"批次處理失敗 (batch {batch_start}-{batch_end}): {e}")
            errors += 1
            continue
        
        # 進度顯示
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / speed if speed > 0 else 0
        
        # 記憶體監控
        if (batch_start // batch_size) % 20 == 0:
            rm.log_ram_status(f"CKIP 處理中 ({processed:,}/{total:,})")
        
        logger.info(
            f"  📊 進度: {processed:,}/{total:,} ({processed/total*100:.1f}%) | "
            f"速度: {speed:.1f} 篇/秒 | "
            f"預計剩餘: {format_time(eta)} | "
            f"已耗時: {format_time(elapsed)}"
        )
    
    conn.commit()
    elapsed = time.time() - start_time
    speed = processed / elapsed if elapsed > 0 else 0
    logger.info(f"✅ CKIP NLP 完成: {processed:,} 篇，耗時 {format_time(elapsed)} ({speed:.1f} 篇/秒)")
    logger.info(f"   錯誤數: {errors}")
    return processed


def step3_tfidf(db: NewsDB):
    """步驟 3: TF-IDF 建模"""
    logger.info("=" * 70)
    logger.info("步驟 3: 建立 TF-IDF 模型")
    logger.info("=" * 70)
    
    from features.tfidf import TfidfBuilder
    
    conn = db.connect()
    rows = conn.execute(
        "SELECT article_id, content_clean FROM articles WHERE status='cleaned'"
    ).fetchall()
    
    if not rows:
        logger.info("⚠️  沒有 cleaned 文章，跳過 TF-IDF")
        return
    
    logger.info(f"📝 使用 {len(rows):,} 篇文章建立 TF-IDF 模型")
    
    documents, doc_ids = [], []
    for r in rows:
        text = r["content_clean"] or ""
        tokens = text.split() if " " in text else list(text)
        documents.append(" ".join(tokens))
        doc_ids.append(r["article_id"])
    
    start_time = time.time()
    builder = TfidfBuilder(max_features=50000, min_df=2)
    builder.fit(documents, doc_ids)
    
    out_dir = Path("/mnt/c/data/information-retrieval/models/tfidf")
    builder.save(out_dir)
    
    elapsed = time.time() - start_time
    logger.info(f"✅ TF-IDF 完成: 詞彙量={builder.vocabulary_size:,}，耗時 {format_time(elapsed)}")
    logger.info(f"   Top 10 詞彙: {builder.get_top_terms(10)}")


def step4_export(db: NewsDB):
    """步驟 4: 匯出結果"""
    logger.info("=" * 70)
    logger.info("步驟 4: 匯出處理結果")
    logger.info("=" * 70)
    
    from exports.exporter import Exporter
    
    db.connect()
    exp = Exporter(db.db_path)
    
    output_path = "/mnt/c/data/information-retrieval/processed/articles_full.parquet"
    start_time = time.time()
    
    exp.to_parquet(output_path, include_nlp=True)
    
    elapsed = time.time() - start_time
    logger.info(f"✅ 匯出完成: {output_path}，耗時 {format_time(elapsed)}")


def main():
    parser = argparse.ArgumentParser(description="CKIP GPU 大量處理管線")
    parser.add_argument("--batch-size", type=int, default=512, help="CKIP 批次大小")
    parser.add_argument("--skip-clean", action="store_true", help="跳過清理")
    parser.add_argument("--skip-nlp", action="store_true", help="跳過 NLP")
    parser.add_argument("--skip-tfidf", action="store_true", help="跳過 TF-IDF")
    parser.add_argument("--skip-export", action="store_true", help="跳過匯出")
    args = parser.parse_args()
    
    logger.info("🚀 CKIP GPU 大量處理管線啟動")
    logger.info(f"   📦 批次大小: {args.batch_size}")
    logger.info(f"   💾 資料庫: {DB_PATH}")
    logger.info(f"   🕐 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = NewsDB(DB_PATH)
    db.init()
    
    total_start = time.time()
    
    try:
        # 步驟 1: 文字清理
        if not args.skip_clean:
            step1_clean_articles(db, batch_size=2000)
        
        # 步驟 2: CKIP NLP
        if not args.skip_nlp:
            step2_ckip_nlp(db, batch_size=args.batch_size)
        
        # 步驟 3: TF-IDF
        if not args.skip_tfidf:
            step3_tfidf(db)
        
        # 步驟 4: 匯出
        if not args.skip_export:
            step4_export(db)
        
        # 最終統計
        stats = db.stats()
        logger.info("\n" + "=" * 70)
        logger.info("📊 最終統計")
        logger.info("=" * 70)
        for k, v in stats.items():
            if hasattr(v, '__iter__') and not isinstance(v, str):
                logger.info(f"   {k}: {dict(v)}")
            else:
                logger.info(f"   {k}: {v}")
        
        total_elapsed = time.time() - total_start
        logger.info(f"\n🎉 管線全部完成！總耗時 {format_time(total_elapsed)}")
        logger.info(f"   🕐 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  使用者中斷！進度已儲存，可重新執行繼續處理")
        stats = db.stats()
        logger.info(f"   目前 cleaned: {stats.get('cleaned', 0):,}")
        logger.info(f"   目前 enriched: {stats.get('enriched', 0):,}")
    except Exception as e:
        logger.exception(f"\n❌ 管線執行失敗: {e}")
        raise


if __name__ == "__main__":
    main()
