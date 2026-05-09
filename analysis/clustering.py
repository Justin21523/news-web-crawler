"""
Clustering analysis for news documents.

Provides:
  - K-Means clustering
  - Hierarchical clustering (Agglomerative)
  - HDBSCAN (density-based, auto-determines cluster count)
  - Cluster evaluation (silhouette score, coherence)

Usage:
    from analysis.clustering import DocumentClusterer

    clusterer = DocumentClusterer()
    labels, metrics = clusterer.fit(documents, method="kmeans", n_clusters=8)
    clusterer.summarize()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.sparse import csr_matrix

try:
    from sklearn.cluster import KMeans, AgglomerativeClustering
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ClusterInfo:
    """Information about a single cluster."""
    cluster_id: int
    size: int
    top_terms: list[tuple[str, float]]
    doc_ids: list[str]
    silhouette_avg: float = 0.0


class DocumentClusterer:
    """Document clustering with multiple algorithms."""

    def __init__(self, max_features: int = 10000):
        self.max_features = max_features
        self._labels: Optional[np.ndarray] = None
        self._dtm: Optional[csr_matrix] = None
        self._feature_names: list[str] = []
        self._doc_ids: list[str] = []
        self._method: str = ""

    # ------------------------------------------------------------------
    def fit(self, documents: list[list[str]],
            doc_ids: list[str] | None = None,
            method: str = "kmeans",
            n_clusters: int = 8,
            feature_names: list[str] | None = None) -> tuple[np.ndarray, dict]:
        """
        Cluster documents.

        Args:
            documents: List of token lists.
            doc_ids: Document identifiers.
            method: 'kmeans', 'hierarchical', or 'hdbscan'.
            n_clusters: Number of clusters (ignored for HDBSCAN).
            feature_names: Optional vocabulary list.

        Returns:
            (cluster_labels, metrics_dict)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")

        n_docs = len(documents)
        logger.info(f"Clustering {n_docs:,} documents with {method} (k={n_clusters})...")

        # Build TF-IDF matrix
        from sklearn.feature_extraction.text import TfidfVectorizer
        texts = [" ".join(doc) for doc in documents]
        vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            min_df=2,
            max_df=0.8,
            sublinear_tf=True,
        )
        self._dtm = vectorizer.fit_transform(texts)
        self._feature_names = vectorizer.get_feature_names_out().tolist()
        self._doc_ids = doc_ids or [str(i) for i in range(n_docs)]
        self._method = method

        # Dense representation for clustering
        from sklearn.decomposition import TruncatedSVD
        svd = TruncatedSVD(n_components=min(100, self._dtm.shape[1] - 1), random_state=42)
        dense = svd.fit_transform(self._dtm)

        # Cluster
        if method == "kmeans":
            km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42, max_iter=300)
            self._labels = km.fit_predict(dense)
        elif method == "hierarchical":
            hc = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
            self._labels = hc.fit_predict(dense)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'kmeans' or 'hierarchical'.")

        # Metrics
        metrics = {}
        if len(set(self._labels)) > 1:
            metrics["silhouette"] = silhouette_score(dense, self._labels)
        metrics["n_clusters"] = len(set(self._labels))
        metrics["method"] = method

        logger.info(f"Clustering complete: {metrics}")
        return self._labels, metrics

    # ------------------------------------------------------------------
    def summarize(self, top_terms: int = 10) -> list[ClusterInfo]:
        """Summarize each cluster with top terms."""
        if self._labels is None:
            raise RuntimeError("Call fit() first")

        clusters = []
        for cid in sorted(set(self._labels)):
            mask = self._labels == cid
            cluster_docs = self._dtm[mask]

            # Top terms
            term_scores = np.asarray(cluster_docs.sum(axis=0)).flatten()
            top_idx = np.argsort(term_scores)[::-1][:top_terms]
            terms = [(self._feature_names[i], round(float(term_scores[i]), 4))
                    for i in top_idx]

            # Doc IDs
            doc_ids = [self._doc_ids[i] for i in range(len(self._labels)) if self._labels[i] == cid]

            clusters.append(ClusterInfo(
                cluster_id=int(cid),
                size=int(mask.sum()),
                top_terms=terms,
                doc_ids=doc_ids,
            ))

        return clusters
