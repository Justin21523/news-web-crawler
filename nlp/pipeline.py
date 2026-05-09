"""
NLP pipeline for Chinese news articles.

Provides:
  - Tokenization (jieba or CKIP)
  - POS tagging
  - Named Entity Recognition (CKIP)
  - Keyword extraction (TextRank / TF-IDF)
  - Stopword filtering

Usage:
    from nlp.pipeline import NLPPipeline

    nlp = NLPPipeline(engine="jieba")
    result = nlp.process("人工智慧是未來趨勢...")
    print(result.tokens, result.keywords)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

# Jieba
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

# CKIP
try:
    from ckip_transformers.nlp import CkipWordWrap, CkipPosTagger, CkipNerChunk
    CKIP_AVAILABLE = True
except ImportError:
    CKIP_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords (minimal set — can be extended from file)
# ---------------------------------------------------------------------------
DEFAULT_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一個", "上", "也", "很", "到", "說", "會", "為", "這", "那", "但", "而",
    "與", "及", "其", "此", "等", "被", "把", "讓", "給", "對", "關於",
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
    "for", "of", "and", "or", "but", "it", "that", "this", "which",
}


@dataclass
class NLPResult:
    tokens: list[str] = field(default_factory=list)
    pos_tags: list[tuple[str, str]] = field(default_factory=list)
    entities: list[tuple[str, str]] = field(default_factory=list)
    keywords: list[tuple[str, float]] = field(default_factory=list)


class NLPPipeline:
    """Unified NLP pipeline for Chinese text."""

    def __init__(self, engine: str = "jieba",
                 stopwords: set[str] | None = None,
                 use_pos: bool = True,
                 top_keywords: int = 10):
        self.engine = engine
        self.use_pos = use_pos
        self.top_keywords = top_keywords
        self.stopwords = stopwords or DEFAULT_STOPWORDS.copy()

        if engine == "ckip" and CKIP_AVAILABLE:
            self._ckip_ww = CkipWordWrap(device=-1)
            self._ckip_pos = CkipPosTagger(device=-1)
            self._ckip_ner = CkipNerChunk(device=-1)
            logger.info("CKIP NLP pipeline initialized")
        elif engine == "jieba" and JIEBA_AVAILABLE:
            logger.info("Jieba NLP pipeline initialized")
        else:
            logger.warning(f"NLP engine '{engine}' not available, using char-level fallback")
            self.engine = "char"

    # ------------------------------------------------------------------
    def process(self, text: str) -> NLPResult:
        """Run full NLP pipeline on a single text."""
        if not text or not text.strip():
            return NLPResult()

        result = NLPResult()
        result.tokens = self._tokenize(text)
        if self.use_pos:
            result.pos_tags = self._pos_tag(text)
        result.entities = self._extract_entities(text)
        result.keywords = self._extract_keywords(text, result.tokens)
        return result

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> list[str]:
        if self.engine == "ckip" and CKIP_AVAILABLE:
            seg = self._ckip_ww([text])
            return [w for s in seg[0] for w in s
                    if w.strip() and w not in self.stopwords]
        elif self.engine == "jieba" and JIEBA_AVAILABLE:
            return [w for w in jieba.lcut(text)
                    if w.strip() and w not in self.stopwords]
        # char-level fallback
        return [c for c in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text)
                if c not in self.stopwords]

    # ------------------------------------------------------------------
    # POS tagging
    # ------------------------------------------------------------------
    def _pos_tag(self, text: str) -> list[tuple[str, str]]:
        if self.engine == "ckip" and CKIP_AVAILABLE:
            ws = self._ckip_ww([text])
            ps = self._ckip_pos(ws)
            results = []
            for seg, pos_seq in zip(ws[0], ps[0]):
                for w, p in zip(seg, pos_seq):
                    if w.strip() and w not in self.stopwords:
                        results.append((w, p))
            return results
        elif self.engine == "jieba" and JIEBA_AVAILABLE:
            import jieba.posseg as pseg
            return [(w.flag, w.word) for w in pseg.lcut(text)
                    if w.word.strip() and w.word not in self.stopwords and w.flag != "x"]
        return []

    # ------------------------------------------------------------------
    # NER
    # ------------------------------------------------------------------
    def _extract_entities(self, text: str) -> list[tuple[str, str]]:
        if self.engine == "ckip" and CKIP_AVAILABLE:
            ner = self._ckip_ner([text])
            if ner and ner[0]:
                return [(e["word"], e["type"]) for e in ner[0]]
        return []

    # ------------------------------------------------------------------
    # Keyword extraction
    # ------------------------------------------------------------------
    def _extract_keywords(self, text: str, tokens: list[str]) -> list[tuple[str, float]]:
        if self.engine == "jieba" and JIEBA_AVAILABLE:
            # TextRank
            kw_textrank = jieba.analyse.textrank(
                text, topK=self.top_keywords, withWeight=True,
                allowPOS=("n", "nr", "ns", "nt", "nz", "v", "vd", "vn")
            )
            return [(w, round(s, 4)) for w, s in kw_textrank]
        elif self.engine == "ckip" and CKIP_AVAILABLE:
            # Simple TF-based for CKIP (no built-in TextRank)
            from collections import Counter
            tf = Counter(tokens)
            total = len(tokens) or 1
            return [(w, round(c / total, 4)) for w, c in tf.most_common(self.top_keywords)]
        return []

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------
    def process_batch(self, texts: list[str]) -> list[NLPResult]:
        return [self.process(t) for t in texts]

    def load_stopwords(self, filepath: str):
        """Load stopwords from a file (one per line)."""
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    self.stopwords.add(w)
        logger.info(f"Loaded {len(self.stopwords)} stopwords from {filepath}")
