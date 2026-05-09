"""
Text Mining analysis module.

Provides:
  - Keyword trend analysis over time
  - Topic evolution tracking
  - Word co-occurrence networks
  - Document similarity matrix
  - Topic modeling (LDA, NMF via scikit-learn)

Usage:
    from analysis.text_mining import TextMiningAnalyzer

    analyzer = TextMiningAnalyzer()
    analyzer.fit(documents, doc_ids=ids, dates=dates)
    trends = analyzer.keyword_trends(topk=20, time_bin="month")
    topics = analyzer.topic_model(n_topics=10, method="nmf")
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.sparse import csr_matrix

try:
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    from sklearn.feature_extraction.text import CountVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class KeywordTrend:
    """Keyword trend over time bins."""
    keyword: str
    time_series: list[tuple[str, int]]  # [(time_bin, count), ...]
    total_count: int
    peak_bin: str
    direction: str = "stable"  # up / down / stable


@dataclass
class TopicResult:
    """Topic modeling result."""
    topic_id: int
    top_terms: list[tuple[str, float]]  # [(term, weight), ...]
    top_docs: list[tuple[str, float]]    # [(doc_id, weight), ...]
    coherence: float = 0.0


class TextMiningAnalyzer:
    """Text mining analysis for news articles."""

    def __init__(self, min_df: int = 2, max_df: float = 0.8,
                 max_features: int = 20000):
        self.min_df = min_df
        self.max_df = max_df
        self.max_features = max_features

        self._dtm: Optional[csr_matrix] = None
        self._doc_ids: list[str] = []
        self._dates: list[str] = []
        self._feature_names: list[str] = []
        self._fitted = False

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------
    def fit(self, documents: list[list[str]],
            doc_ids: list[str] | None = None,
            dates: list[str] | None = None):
        """
        Fit on tokenized documents.

        Args:
            documents: List of documents (each is list of tokens).
            doc_ids: Document identifiers.
            dates: Publish dates (YYYY-MM-DD).
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")

        logger.info(f"Fitting text mining on {len(documents):,} documents...")

        # Build document-term matrix
        # Join tokens with spaces for CountVectorizer
        text_docs = [" ".join(doc) for doc in documents]

        self._vectorizer = CountVectorizer(
            max_features=self.max_features,
            min_df=self.min_df,
            max_df=self.max_df,
            token_pattern=r"(?u)\b\w+\b",
        )
        self._dtm = self._vectorizer.fit_transform(text_docs)
        self._feature_names = self._vectorizer.get_feature_names_out().tolist()
        self._doc_ids = doc_ids or [str(i) for i in range(len(documents))]
        self._dates = dates or [""] * len(documents)
        self._fitted = True

        logger.info(f"DTM: {self._dtm.shape[0]} docs × {self._dtm.shape[1]} features")

    # ------------------------------------------------------------------
    # Keyword Trends
    # ------------------------------------------------------------------
    def keyword_trends(self, topk: int = 20,
                       time_bin: str = "month") -> list[KeywordTrend]:
        """
        Analyze keyword frequency trends over time.

        Args:
            topk: Number of top keywords to track.
            time_bin: 'day', 'week', 'month', or 'year'.

        Returns:
            List of KeywordTrend objects.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() first")

        # Get top terms by total frequency
        term_freqs = np.asarray(self._dtm.sum(axis=0)).flatten()
        top_indices = np.argsort(term_freqs)[::-1][:topk]

        # Bin documents by time
        time_bins = self._bin_dates(self._dates, time_bin)

        trends = []
        for idx in top_indices:
            term = self._feature_names[idx]
            # Count occurrences per time bin
            bin_counts: Counter = Counter()
            col = self._dtm[:, idx].toarray().flatten()

            for doc_i, count in enumerate(col):
                if count > 0:
                    bin_counts[time_bins[doc_i]] += int(count)

            # Build time series (fill missing bins with 0)
            all_bins = sorted(bin_counts.keys())
            time_series = [(b, bin_counts.get(b, 0)) for b in all_bins]
            total = sum(bin_counts.values())
            peak = max(bin_counts, key=bin_counts.get) if bin_counts else ""

            # Compute trend direction via linear regression
            count_vals = np.array([bin_counts.get(b, 0) for b in all_bins], dtype=float)
            if len(count_vals) > 1:
                x = np.arange(len(count_vals))
                sl = float(np.polyfit(x, count_vals, 1)[0])
            else:
                sl = 0.0
            direction = "up" if sl > 0.1 else ("down" if sl < -0.1 else "stable")

            trends.append(KeywordTrend(
                keyword=term,
                time_series=time_series,
                total_count=total,
                peak_bin=peak,
                direction=direction,
            ))

        return trends

    @staticmethod
    def _bin_dates(dates: list[str], bin_type: str) -> list[str]:
        """Bin dates into time periods."""
        bins = []
        for d in dates:
            if not d:
                bins.append("unknown")
                continue
            try:
                dt = datetime.fromisoformat(d[:10])
                if bin_type == "year":
                    bins.append(dt.strftime("%Y"))
                elif bin_type == "month":
                    bins.append(dt.strftime("%Y-%m"))
                elif bin_type == "week":
                    bins.append(dt.strftime("%Y-W%W"))
                else:  # day
                    bins.append(dt.strftime("%Y-%m-%d"))
            except (ValueError, TypeError):
                bins.append("unknown")
        return bins

    # ------------------------------------------------------------------
    # Topic Modeling
    # ------------------------------------------------------------------
    def topic_model(self, n_topics: int = 10,
                    method: str = "nmf",
                    top_terms: int = 15) -> list[TopicResult]:
        """
        Extract topics from documents.

        Args:
            n_topics: Number of topics.
            method: 'nmf' or 'lda'.
            top_terms: Number of top terms per topic.

        Returns:
            List of TopicResult objects.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() first")
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")

        logger.info(f"Topic modeling: {method.upper()}, {n_topics} topics...")

        if method == "nmf":
            model = NMF(n_components=n_topics, random_state=42,
                       max_iter=200, init='nndsvda')
            topic_matrix = model.fit_transform(self._dtm)
        else:  # LDA
            model = LatentDirichletAllocation(n_components=n_topics,
                                              random_state=42,
                                              max_iter=10,
                                              learning_method='online')
            topic_matrix = model.fit_transform(self._dtm)

        # Get component matrix
        if hasattr(model, 'components_'):
            components = model.components_
        else:
            components = topic_matrix.T

        results = []
        for t in range(n_topics):
            # Top terms for this topic
            term_weights = components[t]
            top_idx = np.argsort(term_weights)[::-1][:top_terms]
            terms = [(self._feature_names[i], round(float(term_weights[i]), 4))
                    for i in top_idx]

            # Top documents for this topic
            doc_weights = topic_matrix[:, t]
            top_doc_idx = np.argsort(doc_weights)[::-1][:10]
            docs = [(self._doc_ids[i], round(float(doc_weights[i]), 4))
                   for i in top_doc_idx]

            results.append(TopicResult(
                topic_id=t,
                top_terms=terms,
                top_docs=docs,
            ))

        logger.info(f"Topic modeling complete: {len(results)} topics")
        return results

    # ------------------------------------------------------------------
    # Document Similarity
    # ------------------------------------------------------------------
    def document_similarity(self, doc_id: str, topk: int = 10) -> list[tuple[str, float]]:
        """Find most similar documents."""
        if not self._fitted:
            raise RuntimeError("Call fit() first")

        from sklearn.metrics.pairwise import cosine_similarity

        idx = self._doc_ids.index(doc_id) if doc_id in self._doc_ids else None
        if idx is None:
            return []

        doc_vec = self._dtm[idx:idx + 1]
        sims = cosine_similarity(doc_vec, self._dtm).flatten()
        top_idx = np.argsort(sims)[::-1][1:topk + 1]  # exclude self

        return [(self._doc_ids[i], round(float(sims[i]), 6)) for i in top_idx]
