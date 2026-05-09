"""
Feature engineering for news articles.

Provides:
  - TF-IDF vectorization (scikit-learn)
  - Document-term matrix utilities
  - Cosine similarity search
  - Vector persistence (numpy / scipy sparse)

Usage:
    from features.tfidf import TfidfBuilder

    builder = TfidfBuilder()
    builder.fit(texts)
    vectors = builder.transform(texts)
    sims = builder.search("人工智慧", topk=10)
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.sparse import csr_matrix, save_npz

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class TfidfBuilder:
    """TF-IDF vector builder with search capability."""

    def __init__(self, max_features: int = 50000,
                 min_df: int = 2, max_df: float = 0.8,
                 ngram_range: tuple[int, int] = (1, 1)):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for TfidfBuilder")

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=min_df,
            max_df=max_df,
            ngram_range=ngram_range,
            token_pattern=r"(?u)\b\w+\b|[\u4e00-\u9fff]",  # supports CJK chars
            sublinear_tf=True,
        )
        self._dtm: Optional[csr_matrix] = None
        self._doc_ids: list[str] = []
        self._fitted = False

    # ------------------------------------------------------------------
    def fit(self, documents: list[str], doc_ids: list[str] | None = None):
        """Fit the vectorizer on a list of pre-tokenized (space-joined) documents."""
        self._dtm = self.vectorizer.fit_transform(documents)
        self._doc_ids = doc_ids or [str(i) for i in range(len(documents))]
        self._fitted = True
        logger.info(f"TF-IDF fitted: {self._dtm.shape[0]} docs × "
                    f"{self._dtm.shape[1]} features")

    def transform(self, documents: list[str]) -> csr_matrix:
        """Transform new documents into TF-IDF space."""
        if not self._fitted:
            raise RuntimeError("Call fit() before transform()")
        return self.vectorizer.transform(documents)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, topk: int = 10) -> list[tuple[str, float]]:
        """
        Search for documents most similar to query.

        Returns:
            List of (doc_id, score) sorted by descending score.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before search()")

        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._dtm).flatten()
        top_indices = np.argsort(scores)[::-1][:topk]

        return [(self._doc_ids[i], round(float(scores[i]), 6))
                for i in top_indices if scores[i] > 0]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, directory: str | Path):
        """Save vectorizer + DTM + doc_ids to directory."""
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)

        with open(d / "vectorizer.pkl", "wb") as f:
            pickle.dump(self.vectorizer, f)
        save_npz(str(d / "dtm.npz"), self._dtm)
        with open(d / "doc_ids.pkl", "wb") as f:
            pickle.dump(self._doc_ids, f)
        logger.info(f"Saved TF-IDF model to {d}")

    @classmethod
    def load(cls, directory: str | Path) -> "TfidfBuilder":
        """Load a saved TF-IDF model."""
        d = Path(directory)
        obj = cls.__new__(cls)
        with open(d / "vectorizer.pkl", "rb") as f:
            obj.vectorizer = pickle.load(f)
        from scipy.sparse import load_npz
        obj._dtm = load_npz(str(d / "dtm.npz"))
        with open(d / "doc_ids.pkl", "rb") as f:
            obj._doc_ids = pickle.load(f)
        obj._fitted = True
        logger.info(f"Loaded TF-IDF model from {d}")
        return obj

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------
    @property
    def vocabulary_size(self) -> int:
        return len(self.vectorizer.vocabulary_) if self._fitted else 0

    @property
    def feature_names(self) -> list[str]:
        return self.vectorizer.get_feature_names_out().tolist() if self._fitted else []

    def get_top_terms(self, n: int = 20) -> list[tuple[str, float]]:
        """Get top terms by total TF-IDF weight across corpus."""
        if not self._fitted:
            return []
        total_weights = np.asarray(self._dtm.sum(axis=0)).flatten()
        top_idx = np.argsort(total_weights)[::-1][:n]
        names = self.feature_names
        return [(names[i], round(float(total_weights[i]), 4)) for i in top_idx]
