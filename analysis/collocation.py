"""
Collocation Analysis — find significant word pairs and multi-word expressions.

Methods:
  - PMI (Pointwise Mutual Information)
  - Likelihood Ratio
  - TF-IDF filtered collocations
  - Sliding window co-occurrence

Usage:
    from analysis.collocation import CollocationAnalyzer

    analyzer = CollocationAnalyzer(window_size=3, min_freq=5)
    analyzer.fit(documents)  # list of token lists
    pairs = analyzer.top_collocations(topk=50, method="pmi")
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CollocationPair:
    """A collocation pair with statistics."""
    word1: str
    word2: str
    co_occurrence: int          # Raw co-occurrence count
    pmi: float                  # Pointwise Mutual Information
    log_likelihood: float       # Log-likelihood ratio score
    freq1: int                  # Frequency of word1
    freq2: int                  # Frequency of word2
    total_tokens: int           # Total tokens in corpus

    @property
    def pair(self) -> tuple[str, str]:
        return (self.word1, self.word2)

    def __repr__(self):
        return (f"Collocation('{self.word1}'+'{self.word2}', "
                f"co_occur={self.co_occurrence}, pmi={self.pmi:.4f})")


class CollocationAnalyzer:
    """
    Collocation detection using co-occurrence statistics.

    Finds word pairs that appear together more often than expected by chance.
    Supports bigram and trigram collocations.
    """

    def __init__(self, window_size: int = 3, min_freq: int = 3,
                 min_pmi: float = 3.0):
        """
        Args:
            window_size: Sliding window size for co-occurrence.
            min_freq: Minimum co-occurrence frequency to consider.
            min_pmi: Minimum PMI score threshold.
        """
        self.window_size = window_size
        self.min_freq = min_freq
        self.min_pmi = min_pmi

        # Counters
        self.unigram_freq: Counter = Counter()
        self.bigram_freq: Counter = Counter()
        self.co_occurrence: Counter = Counter()
        self.total_tokens = 0
        self.total_docs = 0
        self._fitted = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def fit(self, documents: list[list[str]]):
        """
        Fit on a list of tokenized documents.

        Args:
            documents: List of documents, each is a list of tokens.
        """
        logger.info(f"Fitting collocation analyzer on {len(documents):,} documents...")

        for doc in documents:
            self.total_docs += 1
            self.total_tokens += len(doc)

            # Unigram counts
            self.unigram_freq.update(doc)

            # Bigram counts (adjacent)
            for i in range(len(doc) - 1):
                bigram = (doc[i], doc[i + 1])
                self.bigram_freq[bigram] += 1

            # Window-based co-occurrence
            self._count_co_occurrences(doc)

        self._fitted = True
        logger.info(f"Fit complete: {len(self.unigram_freq):,} unigrams, "
                   f"{len(self.bigram_freq):,} bigrams, "
                   f"{self.total_tokens:,} total tokens")

    def _count_co_occurrences(self, tokens: list[str]):
        """Count word co-occurrences within sliding window."""
        unique_in_window: set[tuple[str, str]] = set()
        for i in range(len(tokens)):
            unique_in_window.clear()
            for j in range(i + 1, min(i + self.window_size, len(tokens))):
                if tokens[i] != tokens[j]:
                    pair = tuple(sorted([tokens[i], tokens[j]]))
                    if pair not in unique_in_window:
                        unique_in_window.add(pair)
                        self.co_occurrence[pair] += 1

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def top_collocations(self, topk: int = 50,
                         method: str = "pmi") -> list[CollocationPair]:
        """
        Get top collocation pairs ranked by the chosen method.

        Args:
            topk: Number of pairs to return.
            method: 'pmi', 'log_likelihood', or 'combined'.

        Returns:
            Sorted list of CollocationPair.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before scoring")

        pairs = []
        n = self.total_tokens

        for (w1, w2), co_count in self.co_occurrence.items():
            if co_count < self.min_freq:
                continue

            f1 = self.unigram_freq.get(w1, 0)
            f2 = self.unigram_freq.get(w2, 0)
            if f1 == 0 or f2 == 0:
                continue

            # PMI = log(P(w1,w2) / (P(w1) * P(w2)))
            p_joint = co_count / n
            p1 = f1 / n
            p2 = f2 / n
            pmi = math.log2(p_joint / (p1 * p2)) if p1 * p2 > 0 else 0

            # Log-likelihood ratio
            ll = self._log_likelihood(co_count, f1, f2, n)

            if pmi < self.min_pmi:
                continue

            pair = CollocationPair(
                word1=w1, word2=w2,
                co_occurrence=co_count,
                pmi=pmi,
                log_likelihood=ll,
                freq1=f1, freq2=f2,
                total_tokens=n,
            )
            pairs.append(pair)

        # Sort
        if method == "pmi":
            pairs.sort(key=lambda x: x.pmi, reverse=True)
        elif method == "log_likelihood":
            pairs.sort(key=lambda x: x.log_likelihood, reverse=True)
        elif method == "combined":
            # Weighted combination
            pairs.sort(key=lambda x: x.pmi * 0.6 + x.log_likelihood * 0.4,
                      reverse=True)
        else:
            pairs.sort(key=lambda x: x.co_occurrence, reverse=True)

        return pairs[:topk]

    @staticmethod
    def _log_likelihood(co_occur: int, f1: int, f2: int, n: int) -> float:
        """
        Calculate log-likelihood ratio for collocation significance.

        Based on Dunning (1993) method.
        """
        if n == 0:
            return 0.0

        # Expected co-occurrence under independence
        expected = (f1 * f2) / n
        if expected <= 0:
            return 0.0

        # Simplified LL
        ll = 2 * co_occur * math.log(co_occur / expected) if co_occur > 0 else 0
        return max(0, ll)

    # ------------------------------------------------------------------
    # Co-occurrence matrix (for downstream analysis)
    # ------------------------------------------------------------------
    def get_cooccurrence_matrix(self, vocab: list[str] | None = None,
                                top_n: int = 500) -> tuple[np.ndarray, list[str]]:
        """
        Build co-occurrence matrix for top vocabulary.

        Returns:
            (matrix, vocab_list) where matrix[i,j] = co-occurrence count
        """
        if vocab is None:
            # Use top N most frequent words
            vocab = [w for w, _ in self.unigram_freq.most_common(top_n)]

        word_idx = {w: i for i, w in enumerate(vocab)}
        n = len(vocab)
        matrix = np.zeros((n, n), dtype=np.int32)

        for (w1, w2), count in self.co_occurrence.items():
            if w1 in word_idx and w2 in word_idx:
                i, j = word_idx[w1], word_idx[w2]
                matrix[i, j] = count
                matrix[j, i] = count

        return matrix, vocab

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def to_dataframe(self, topk: int = 200) -> "pd.DataFrame":
        """Export collocation statistics to DataFrame."""
        import pandas as pd
        pairs = self.top_collocations(topk=topk)
        return pd.DataFrame([{
            "word1": p.word1,
            "word2": p.word2,
            "co_occurrence": p.co_occurrence,
            "pmi": round(p.pmi, 4),
            "log_likelihood": round(p.log_likelihood, 4),
            "freq1": p.freq1,
            "freq2": p.freq2,
        } for p in pairs])
