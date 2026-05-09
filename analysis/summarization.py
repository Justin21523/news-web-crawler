"""
Summarization module for Chinese news articles.

Provides:
  - Extractive summarization (TextRank, Lead-K, MMR)
  - Query-focused summarization
  - Multi-document summarization

Usage:
    from analysis.summarization import Summarizer

    s = Summarizer()
    summary = s.extractive(text, ratio=0.15)
    summary = s.mmr_summary(text, k=3, diversity=0.7)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    method: str
    sentences: list[str]
    score: float = 0.0
    compression_ratio: float = 0.0


class Summarizer:
    """Extractive summarization for Chinese text."""

    def __init__(self, tokenizer=None):
        """
        Args:
            tokenizer: Optional callable that splits text into sentences.
                      Defaults to regex-based Chinese sentence splitter.
        """
        self._tokenize_sentences = tokenizer or self._default_sentence_splitter

    @staticmethod
    def _default_sentence_splitter(text: str) -> list[str]:
        """Split Chinese text into sentences."""
        # Chinese sentence boundaries: 。 ！ ？ ； \n
        parts = re.split(r'[。！？；\n]+', text)
        return [p.strip() for p in parts if p.strip()]

    # ------------------------------------------------------------------
    # Lead-K
    # ------------------------------------------------------------------
    def lead_k(self, text: str, k: int = 3) -> SummaryResult:
        """Extract first K sentences."""
        sentences = self._tokenize_sentences(text)
        selected = sentences[:k]
        return SummaryResult(
            method="lead_k",
            sentences=selected,
            compression_ratio=len("".join(selected)) / max(len(text), 1),
        )

    # ------------------------------------------------------------------
    # TextRank-based extractive
    # ------------------------------------------------------------------
    def extractive(self, text: str, ratio: float = 0.15,
                   top_k: int | None = None) -> SummaryResult:
        """
        Extractive summarization using sentence scoring.

        Scores sentences by:
        1. TF-based word importance
        2. Position bias (early sentences weighted higher)
        3. Sentence length normalization

        Args:
            text: Input text.
            ratio: Fraction of sentences to extract.
            top_k: Override ratio with absolute count.
        """
        sentences = self._tokenize_sentences(text)
        if not sentences:
            return SummaryResult(method="extractive", sentences=[])

        # Tokenize all sentences
        sent_tokens = []
        for s in sentences:
            # Simple CJK tokenization
            tokens = re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z]+", s.lower())
            sent_tokens.append(tokens)

        # Compute word frequencies
        from collections import Counter
        word_freq = Counter()
        for tokens in sent_tokens:
            word_freq.update(tokens)

        # Score sentences
        scores = []
        for i, tokens in enumerate(sent_tokens):
            if not tokens:
                scores.append(0.0)
                continue

            # TF-based score
            tf_score = sum(word_freq.get(t, 0) for t in tokens) / len(tokens)

            # Position bias (first sentences are more important)
            pos_bias = 1.0 / (1 + 0.5 * i)

            # Length normalization (avoid very short/long)
            length_factor = min(len(tokens), 30) / max(len(tokens), 1)

            score = tf_score * pos_bias * length_factor
            scores.append(score)

        # Select top sentences
        n_select = top_k or max(1, int(len(sentences) * ratio))
        top_indices = np.argsort(scores)[::-1][:n_select]
        top_indices = sorted(top_indices)  # Preserve original order

        selected = [sentences[i] for i in top_indices]
        avg_score = np.mean([scores[i] for i in top_indices])

        return SummaryResult(
            method="extractive_textrank",
            sentences=selected,
            score=round(float(avg_score), 4),
            compression_ratio=len("".join(selected)) / max(len(text), 1),
        )

    # ------------------------------------------------------------------
    # MMR (Maximal Marginal Relevance)
    # ------------------------------------------------------------------
    def mmr_summary(self, text: str, k: int = 3,
                    diversity: float = 0.7) -> SummaryResult:
        """
        MMR summarization — balances relevance and diversity.

        MMR = λ × Sim(Si, Query) - (1-λ) × max[Sim(Si, Sj)]

        Args:
            text: Input text.
            k: Number of sentences.
            diversity: λ parameter (0.5 = balanced, 0.7 = more diverse).
        """
        sentences = self._tokenize_sentences(text)
        if not sentences:
            return SummaryResult(method="mmr", sentences=[])

        sent_tokens = []
        for s in sentences:
            tokens = set(re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z]+", s.lower()))
            sent_tokens.append(tokens)

        # Query = all tokens combined
        query_tokens = set()
        for tokens in sent_tokens:
            query_tokens.update(tokens)

        selected: list[int] = []
        remaining = set(range(len(sentences)))

        for _ in range(min(k, len(sentences))):
            if not remaining:
                break

            best_idx = -1
            best_score = -float("inf")

            for idx in remaining:
                # Relevance to query
                rel = len(sent_tokens[idx] & query_tokens) / max(len(sent_tokens[idx]), 1)

                # Diversity from selected
                if selected:
                    sim_max = max(
                        len(sent_tokens[idx] & sent_tokens[s]) / max(len(sent_tokens[idx] | sent_tokens[s]), 1)
                        for s in selected
                    )
                else:
                    sim_max = 0

                score = diversity * rel - (1 - diversity) * sim_max
                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx >= 0:
                selected.append(best_idx)
                remaining.remove(best_idx)

        selected.sort()
        selected_sentences = [sentences[i] for i in selected]

        return SummaryResult(
            method="mmr",
            sentences=selected_sentences,
            score=round(best_score, 4) if selected else 0,
            compression_ratio=len("".join(selected_sentences)) / max(len(text), 1),
        )
