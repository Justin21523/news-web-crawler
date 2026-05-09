"""
Classification analysis for news documents.

Provides:
  - News category classification (supervised, with TF-IDF + classifier)
  - Sentiment analysis (lexicon-based for Chinese)
  - Zero-shot classification via TF-IDF prototype matching

Usage:
    from analysis.classification import NewsClassifier

    classifier = NewsClassifier()
    # Supervised
    classifier.train(documents, labels)
    preds = classifier.predict(new_documents)

    # Sentiment
    from analysis.classification import SentimentAnalyzer
    sa = SentimentAnalyzer()
    scores = sa.analyze(texts)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sentiment lexicon (simplified Chinese/Traditional)
# ---------------------------------------------------------------------------
POSITIVE_WORDS = {
    "好", "棒", "優秀", "成功", "進步", "發展", "成長", "提升", "改善", "突破",
    "創新", "領先", "榮耀", "勝利", "喜悅", "滿意", "肯定", "讚賞", "鼓勵",
    "支持", "幫助", "貢獻", "效益", "優勢", "機會", "希望", "樂觀", "積極",
    "good", "great", "excellent", "best", "success", "progress", "growth",
    "improve", "innovate", "leading", "positive", "opportunity",
}

NEGATIVE_WORDS = {
    "壞", "差", "失敗", "衰退", "下降", "減少", "惡化", "危機", "風險", "問題",
    "困難", "挑戰", "衝突", "爭議", "批評", "指責", "反對", "拒絕", "損失",
    "損害", "負面", "悲觀", "擔憂", "恐懼", "憤怒", "不滿", "抗議", "打擊",
    "bad", "poor", "worst", "fail", "crisis", "risk", "problem", "conflict",
    "controversy", "criticism", "oppose", "loss", "negative", "worry", "fear",
}


@dataclass
class SentimentResult:
    text_preview: str
    positive_score: float
    negative_score: float
    compound: float           # positive - negative
    label: str                # positive / negative / neutral
    positive_words: list[str]
    negative_words: list[str]


class SentimentAnalyzer:
    """Lexicon-based sentiment analysis for Chinese news."""

    def __init__(self):
        self.positive = POSITIVE_WORDS
        self.negative = NEGATIVE_WORDS

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        """Analyze sentiment for a list of texts."""
        results = []
        for text in texts:
            results.append(self._analyze_one(text))
        return results

    def _analyze_one(self, text: str) -> SentimentResult:
        words = set(re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z]+", text.lower()))

        pos_found = words & self.positive
        neg_found = words & self.negative

        pos_score = len(pos_found) / max(len(words), 1)
        neg_score = len(neg_found) / max(len(words), 1)
        compound = pos_score - neg_score

        if compound > 0.02:
            label = "positive"
        elif compound < -0.02:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            text_preview=text[:80],
            positive_score=round(pos_score, 4),
            negative_score=round(neg_score, 4),
            compound=round(compound, 4),
            label=label,
            positive_words=sorted(pos_found),
            negative_words=sorted(neg_found),
        )


class NewsClassifier:
    """TF-IDF + classifier for news category prediction."""

    def __init__(self, classifier: str = "logistic"):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required")

        self.classifier_name = classifier
        self._vectorizer = TfidfVectorizer(
            max_features=30000, min_df=2, max_df=0.9, sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b",
        )
        self._classifier = None
        self._labels: list[str] = []
        self._fitted = False

    def train(self, documents: list[list[str]], labels: list[str]):
        """Train the classifier."""
        texts = [" ".join(doc) for doc in documents]
        self._labels = sorted(set(labels))
        label_idx = {l: i for i, l in enumerate(self._labels)}
        y = [label_idx[l] for l in labels]

        X = self._vectorizer.fit_transform(texts)

        if self.classifier_name == "logistic":
            self._classifier = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        elif self.classifier_name == "svm":
            self._classifier = LinearSVC(random_state=42)
        else:
            self._classifier = LogisticRegression(max_iter=1000, random_state=42)

        self._classifier.fit(X, y)
        self._fitted = True
        logger.info(f"Classifier trained: {self.classifier_name}, "
                   f"{len(self._labels)} classes, {X.shape[1]} features")

    def predict(self, documents: list[list[str]]) -> list[str]:
        """Predict categories for documents."""
        if not self._fitted:
            raise RuntimeError("Call train() first")

        texts = [" ".join(doc) for doc in documents]
        X = self._vectorizer.transform(texts)
        y_pred = self._classifier.predict(X)
        return [self._labels[i] for i in y_pred]

    def evaluate(self, documents: list[list[str]],
                 labels: list[str]) -> dict:
        """Evaluate classifier performance."""
        preds = self.predict(documents)
        return {
            "accuracy": accuracy_score(labels, preds),
            "report": classification_report(labels, preds, output_dict=True),
        }
