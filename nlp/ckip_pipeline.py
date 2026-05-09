"""
CKIP-enhanced NLP Pipeline with GPU support and batch processing.

Uses CKIP BERT-based models for:
  - Word segmentation (CkipWordSegmenter)
  - POS tagging (CkipPosTagger) — jointly with segmentation for higher accuracy
  - NER (CkipNerChunker) — named entity recognition

Features:
  - GPU-accelerated batched inference
  - RAM-safe batch sizing
  - Word+POS fused output tokens

Usage:
    from nlp.ckip_pipeline import CKIPPipeline
    from utils.resource_manager import ResourceManager

    rm = ResourceManager(max_ram_gb=4.0)
    nlp = CKIPPipeline(device_id=rm.get_cuda_device_id())
    results = rm.process_in_batches(texts, nlp.process_batch, desc="NLP")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

# CKIP imports — API varies by version
try:
    # ckip-transformers >= 0.3.4
    from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger, CkipNerChunker
    from ckip_transformers.nlp.driver import NerToken
    CKIP_AVAILABLE = True
    CKIP_NEW_API = True
except ImportError:
    try:
        # ckip-transformers < 0.3.4
        from ckip_transformers.nlp import CkipWordWrap, CkipPosTagger, CkipNerChunk
        CkipWordSegmenter = CkipWordWrap
        CkipNerChunker = CkipNerChunk
        NerToken = None
        CKIP_AVAILABLE = True
        CKIP_NEW_API = False
    except ImportError:
        CKIP_AVAILABLE = False

logger = logging.getLogger(__name__)

# POS tag groups to keep (content words)
KEEP_POS_GROUPS = {
    "Na", "Nb", "Nc", "Ncd",  # Nouns
    "VA", "VB", "VC", "VD",    # Verbs
    "A",                        # Adjectives
    "D",                        # Adverbs
    "Neu",                      # Numbers
    "Nr",                       # Pronouns
}

DEFAULT_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一個", "上", "也", "很", "到", "說", "會", "為", "這", "那", "但", "而",
    "與", "及", "其", "此", "等", "被", "把", "讓", "給", "對", "關於",
}


@dataclass
class CKIPResult:
    """Output from CKIP processing of a single document."""
    words_with_pos: list[tuple[str, str]] = field(default_factory=list)
    filtered_words: list[str] = field(default_factory=list)
    fused_tokens: list[str] = field(default_factory=list)
    entities: list[tuple[str, str]] = field(default_factory=list)


class CKIPPipeline:
    """
    CKIP NLP pipeline with GPU support.

    Uses joint word segmentation + POS tagging for higher accuracy
    than running them independently.
    """

    def __init__(self, device_id: int = -1,
                 use_ner: bool = True,
                 filter_pos: bool = True,
                 stopwords: set[str] | None = None):
        if not CKIP_AVAILABLE:
            raise ImportError(
                "ckip-transformers not installed. "
                "Run: pip install ckip-transformers"
            )

        self.device_id = device_id
        self.use_ner = use_ner
        self.filter_pos = filter_pos
        self.stopwords = stopwords or DEFAULT_STOPWORDS.copy()

        device_name = f"CUDA:{device_id}" if device_id >= 0 else "CPU"
        logger.info(f"Initializing CKIP pipeline on {device_name}")

        self.ws = CkipWordSegmenter(device=device_id)
        self.pos = CkipPosTagger(device=device_id)
        self.ner = CkipNerChunker(device=device_id) if use_ner else None

        logger.info(f"CKIP pipeline ready (device={device_name})")

    # ------------------------------------------------------------------
    def process(self, text: str) -> CKIPResult:
        """Process a single document."""
        results = self.process_batch([text])
        return results[0]

    def process_batch(self, texts: list[str]) -> list[CKIPResult]:
        """
        Process a batch of texts. Optimized for GPU when available.
        CKIP internally batches transformer inference efficiently.
        """
        if not texts:
            return []

        valid_texts = [t if t.strip() else " " for t in texts]

        # Step 1: Word segmentation
        raw_words = self.ws(valid_texts)

        # Step 2: POS tagging (uses segmentation internally)
        raw_pos = self.pos(raw_words)

        # Step 3: NER
        raw_ner = []
        if self.use_ner and self.ner:
            raw_ner = self.ner(valid_texts)
        else:
            raw_ner = [[] for _ in valid_texts]

        # Step 4: Combine
        results = []
        for i in range(len(texts)):
            words = raw_words[i] if i < len(raw_words) else []
            pos_list = raw_pos[i] if i < len(raw_pos) else []
            ner_list = raw_ner[i] if i < len(raw_ner) else []
            results.append(self._combine(words, pos_list, ner_list))

        return results

    def _combine(self, words, pos_list, ner_list) -> CKIPResult:
        """Combine word segmentation, POS, and NER into result."""
        result = CKIPResult()

        # Handle nested list format from CKIP
        if words and isinstance(words[0], list):
            words = words[0] if words else []
        if pos_list and isinstance(pos_list[0], list):
            pos_list = pos_list[0] if pos_list else []

        # Fuse words with POS
        for w, p in zip(words, pos_list):
            result.words_with_pos.append((w, p))

            if w in self.stopwords:
                continue
            if self.filter_pos and p not in KEEP_POS_GROUPS:
                continue

            result.filtered_words.append(w)
            result.fused_tokens.append(f"{w}/{p}")

        # Parse NER
        for ent in ner_list:
            if isinstance(ent, dict):
                result.entities.append((ent.get("word", ""), ent.get("type", "")))
            elif hasattr(ent, "word"):
                # NerToken object
                result.entities.append((ent.word, ent.ner))
            elif isinstance(ent, (list, tuple)) and len(ent) >= 2:
                result.entities.append((str(ent[0]), str(ent[1])))

        return result

    def load_stopwords(self, filepath: str):
        """Load stopwords from file (one per line)."""
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    self.stopwords.add(w)
        logger.info(f"Loaded {len(self.stopwords)} stopwords from {filepath}")
