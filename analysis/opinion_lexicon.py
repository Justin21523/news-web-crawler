"""
Opinion Lexicon Sentiment Analyzer

Loads the NTUSD-based opinion word lexicon from Excel and computes
weighted sentiment scores for Chinese text using CKIP tokenization.

Features:
  - Weighted scoring from lexicon values
  - Multiple scoring strategies (mean, sum, max-weighted)
  - Category-level sentiment (5 feature columns)
  - Comparison with lexicon-free methods (TextBlob-like, VADER-like)

Usage:
    from analysis.opinion_lexicon import OpinionLexicon

    lex = OpinionLexicon("/mnt/c/data/features/opinion_word.xlsx")
    scores = lex.analyze_texts(texts)  # list of raw texts
    # Or use pre-tokenized:
    scores = lex.analyze_tokenized(token_lists)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OpinionScore:
    """Sentiment score for a single document."""
    text_preview: str
    # Primary score (weighted mean of matched opinion words)
    score: float
    # Number of opinion words matched
    matched_count: int
    # Total tokens in document
    total_tokens: int
    # Match rate
    match_rate: float
    # Positive / negative word lists found
    positive_words: list[tuple[str, float]] = field(default_factory=list)
    negative_words: list[tuple[str, float]] = field(default_factory=list)
    # Alternative scores for comparison
    score_sum: float = 0.0           # Sum of all matched scores
    score_max: float = 0.0           # Max absolute score
    category_scores: dict = field(default_factory=dict)  # Per-category scores
    label: str = ""                  # positive / negative / neutral


class OpinionLexicon:
    """
    Opinion word lexicon sentiment analyzer.

    Loads NTUSD-style lexicon from Excel:
      Column 0: word (Chinese opinion word)
      Column 1: sentiment score (-1 to +1)
      Columns 2-6: category features (0-9 integer)
    """

    def __init__(self, excel_path: str):
        logger.info(f"Loading opinion lexicon from {excel_path}...")
        df = pd.read_excel(excel_path, header=None,
                          names=["word", "score", "c1", "c2", "c3", "c4", "c5"])

        # Build lookup: word → (score, category_vector)
        self.lexicon: dict[str, tuple[float, list[int]]] = {}
        for _, row in df.iterrows():
            word = str(row["word"]).strip()
            score = float(row["score"])
            cats = [int(row["c1"]), int(row["c2"]), int(row["c3"]),
                    int(row["c4"]), int(row["c5"])]
            # If duplicate words, keep the one with highest absolute score
            if word not in self.lexicon or abs(score) > abs(self.lexicon[word][0]):
                self.lexicon[word] = (score, cats)

        # Index by length for longest-match tokenization
        self._max_word_len = max(len(w) for w in self.lexicon)
        self._words_by_len: dict[int, set[str]] = {}
        for w in self.lexicon:
            l = len(w)
            if l not in self._words_by_len:
                self._words_by_len[l] = set()
            self._words_by_len[l].add(w)

        logger.info(f"Lexicon loaded: {len(self.lexicon):,} words, "
                   f"score range [{df['score'].min():.3f}, {df['score'].max():.3f}]")

    # ------------------------------------------------------------------
    # Token-level matching (longest-match greedy)
    # ------------------------------------------------------------------
    def _match_opinion_words(self, text: str) -> list[tuple[str, float, list[int]]]:
        """
        Find all opinion words in text using longest-match strategy.

        Returns:
            List of (word, score, category_vector) tuples.
        """
        matches = []
        i = 0
        n = len(text)
        while i < n:
            matched = False
            # Try longest words first
            for length in range(min(self._max_word_len, n - i), 0, -1):
                candidate = text[i:i + length]
                if candidate in self.lexicon:
                    score, cats = self.lexicon[candidate]
                    matches.append((candidate, score, cats))
                    i += length
                    matched = True
                    break
            if not matched:
                i += 1
        return matches

    def _match_in_tokens(self, tokens: list[str]) -> list[tuple[str, float, list[int]]]:
        """Match opinion words in a pre-tokenized list."""
        # Also check n-grams of tokens
        matches = []
        n = len(tokens)

        # Single tokens
        for t in tokens:
            if t in self.lexicon:
                matches.append((t, *self.lexicon[t]))

        # Bigrams and trigrams (concatenated)
        for i in range(n):
            # Bigram
            if i + 1 < n:
                bigram = tokens[i] + tokens[i + 1]
                if bigram in self.lexicon:
                    matches.append((bigram, *self.lexicon[bigram]))
            # Trigram
            if i + 2 < n:
                trigram = tokens[i] + tokens[i + 1] + tokens[i + 2]
                if trigram in self.lexicon:
                    matches.append((trigram, *self.lexicon[trigram]))

        return matches

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _compute_score(self, matches: list[tuple[str, float, list[int]]],
                       total_tokens: int,
                       text_preview: str) -> OpinionScore:
        """Compute sentiment scores from matched opinion words."""
        if not matches:
            return OpinionScore(
                text_preview=text_preview[:80],
                score=0.0,
                matched_count=0,
                total_tokens=total_tokens,
                match_rate=0.0,
                label="neutral",
            )

        scores = [m[1] for m in matches]
        cats_vectors = [m[2] for m in matches]

        # Primary: weighted mean
        score_mean = float(np.mean(scores))
        score_sum = float(np.sum(scores))
        score_max = float(np.max(np.abs(scores)))

        # Category-level scores
        cat_names = ["intensity", "certainty", "valence", "subjectivity", "polarity"]
        category_scores = {}
        for j, name in enumerate(cat_names):
            vals = [c[j] for c in cats_vectors if c[j] > 0]
            if vals:
                category_scores[name] = round(float(np.mean(vals)), 3)

        # Positive / negative word lists
        pos_words = [(m[0], m[1]) for m in matches if m[1] > 0.05]
        neg_words = [(m[0], m[1]) for m in matches if m[1] < -0.05]

        # Label
        if score_mean > 0.03:
            label = "positive"
        elif score_mean < -0.03:
            label = "negative"
        else:
            label = "neutral"

        return OpinionScore(
            text_preview=text_preview[:80],
            score=round(score_mean, 4),
            matched_count=len(matches),
            total_tokens=total_tokens,
            match_rate=round(len(matches) / max(total_tokens, 1), 4),
            positive_words=pos_words[:10],
            negative_words=neg_words[:10],
            score_sum=round(score_sum, 4),
            score_max=round(score_max, 4),
            category_scores=category_scores,
            label=label,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_texts(self, texts: list[str]) -> list[OpinionScore]:
        """Analyze sentiment for raw texts."""
        return [self._compute_score(
            self._match_opinion_words(text),
            len(text),
            text
        ) for text in texts]

    def analyze_tokenized(self, token_lists: list[list[str]],
                          texts: list[str] | None = None) -> list[OpinionScore]:
        """Analyze sentiment for pre-tokenized documents."""
        results = []
        for i, tokens in enumerate(token_lists):
            text = texts[i] if texts and i < len(texts) else " ".join(tokens)
            matches = self._match_in_tokens(tokens)
            results.append(self._compute_score(matches, len(tokens), text))
        return results

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def summary(self, scores: list[OpinionScore]) -> dict:
        """Summary statistics of sentiment analysis results."""
        if not scores:
            return {}

        labels = {"positive": 0, "negative": 0, "neutral": 0}
        for s in scores:
            labels[s.label] += 1

        vals = [s.score for s in scores]
        return {
            "total_docs": len(scores),
            "labels": labels,
            "mean_score": round(float(np.mean(vals)), 4),
            "std_score": round(float(np.std(vals)), 4),
            "median_score": round(float(np.median(vals)), 4),
            "min_score": round(float(np.min(vals)), 4),
            "max_score": round(float(np.max(vals)), 4),
            "mean_match_rate": round(float(np.mean([s.match_rate for s in scores])), 4),
            "lexicon_size": len(self.lexicon),
        }

    def to_dataframe(self, scores: list[OpinionScore]) -> pd.DataFrame:
        """Export scores to DataFrame."""
        rows = []
        for s in scores:
            rows.append({
                "text_preview": s.text_preview,
                "score": s.score,
                "label": s.label,
                "matched_count": s.matched_count,
                "total_tokens": s.total_tokens,
                "match_rate": s.match_rate,
                "score_sum": s.score_sum,
                "score_max": s.score_max,
                "positive_words": ", ".join(f"{w}({sc:.2f})" for w, sc in s.positive_words[:5]),
                "negative_words": ", ".join(f"{w}({sc:.2f})" for w, sc in s.negative_words[:5]),
                **{f"cat_{k}": v for k, v in s.category_scores.items()},
            })
        return pd.DataFrame(rows)
