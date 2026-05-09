"""
Time Series analysis for news topics and trends.

Provides:
  - Topic热度追踪 (topic popularity over time)
  - Burst detection (sudden spikes in mention frequency)
  - Trend analysis (linear regression on time series)
  - Cross-topic correlation

Usage:
    from analysis.time_series import TimeSeriesAnalyzer

    analyzer = TimeSeriesAnalyzer()
    analyzer.fit(documents, dates=dates, keywords=keywords)
    trends = analyzer.topic_trends()
    bursts = analyzer.detect_bursts(keyword="人工智慧")
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrendData:
    """Time series trend for a keyword."""
    keyword: str
    dates: list[str]
    counts: list[int]
    trend_direction: str       # 'up', 'down', 'stable'
    slope: float               # Linear regression slope
    peak_date: str
    peak_count: int
    avg_count: float
    std_count: float


@dataclass
class BurstEvent:
    """Detected burst event."""
    keyword: str
    burst_date: str
    burst_count: int
    baseline_avg: float
    burst_ratio: float         # count / baseline
    significance: float        # z-score


class TimeSeriesAnalyzer:
    """Time series analysis for news topics."""

    def __init__(self, time_bin: str = "day"):
        """
        Args:
            time_bin: 'day', 'week', or 'month'.
        """
        self.time_bin = time_bin
        self._keyword_counts: dict[str, Counter] = defaultdict(Counter)
        self._all_dates: list[str] = []
        self._fitted = False

    # ------------------------------------------------------------------
    def fit(self, documents: list[list[str]],
            dates: list[str],
            keywords: list[str] | None = None,
            top_keywords: int = 50):
        """
        Fit on tokenized documents with dates.

        Args:
            documents: List of token lists.
            dates: List of publish dates (YYYY-MM-DD).
            keywords: Specific keywords to track (None = auto-extract top N).
            top_keywords: Number of top keywords to auto-track.
        """
        logger.info(f"Fitting time series on {len(documents):,} documents...")

        if keywords is None:
            # Auto-extract top keywords
            all_words = Counter()
            for doc in documents:
                all_words.update(doc)
            keywords = [w for w, _ in all_words.most_common(top_keywords)]

        # Count keyword occurrences per time bin
        for i, doc in enumerate(documents):
            if i >= len(dates):
                continue
            date_bin = self._bin_date(dates[i])
            self._all_dates.append(date_bin)

            doc_set = set(doc)
            for kw in keywords:
                if kw in doc_set:
                    self._keyword_counts[kw][date_bin] += doc.count(kw)

        self._fitted = True
        self._keywords = keywords
        logger.info(f"Time series fitted: {len(keywords)} keywords tracked")

    def _bin_date(self, date_str: str) -> str:
        """Bin a date string into the configured time bin."""
        if not date_str:
            return "unknown"
        try:
            dt = datetime.fromisoformat(date_str[:10])
            if self.time_bin == "month":
                return dt.strftime("%Y-%m")
            elif self.time_bin == "week":
                return dt.strftime("%Y-W%W")
            else:
                return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return "unknown"

    # ------------------------------------------------------------------
    # Topic Trends
    # ------------------------------------------------------------------
    def topic_trends(self) -> list[TrendData]:
        """Get trends for all tracked keywords."""
        if not self._fitted:
            raise RuntimeError("Call fit() first")

        trends = []
        for kw in self._keywords:
            counts = self._keyword_counts[kw]
            if not counts:
                continue

            sorted_dates = sorted(counts.keys())
            count_vals = [counts[d] for d in sorted_dates]

            # Linear regression
            x = np.arange(len(count_vals))
            y = np.array(count_vals, dtype=float)
            if len(x) > 1:
                slope = float(np.polyfit(x, y, 1)[0])
            else:
                slope = 0.0

            if slope > 0.1:
                direction = "up"
            elif slope < -0.1:
                direction = "down"
            else:
                direction = "stable"

            peak_idx = int(np.argmax(y))
            trends.append(TrendData(
                keyword=kw,
                dates=sorted_dates,
                counts=count_vals,
                trend_direction=direction,
                slope=round(slope, 4),
                peak_date=sorted_dates[peak_idx],
                peak_count=int(y[peak_idx]),
                avg_count=round(float(np.mean(y)), 2),
                std_count=round(float(np.std(y)), 2),
            ))

        return trends

    # ------------------------------------------------------------------
    # Burst Detection
    # ------------------------------------------------------------------
    def detect_bursts(self, keyword: str,
                      z_threshold: float = 2.0) -> list[BurstEvent]:
        """
        Detect burst events for a keyword.

        A burst is a time bin where the count exceeds
        baseline_avg + z_threshold * baseline_std.

        Args:
            keyword: Keyword to analyze.
            z_threshold: Z-score threshold for burst detection.
        """
        if not self._fitted or keyword not in self._keyword_counts:
            return []

        counts = self._keyword_counts[keyword]
        sorted_dates = sorted(counts.keys())
        count_vals = np.array([counts[d] for d in sorted_dates], dtype=float)

        if len(count_vals) < 3:
            return []

        mean = np.mean(count_vals)
        std = np.std(count_vals)
        if std == 0:
            return []

        threshold = mean + z_threshold * std
        bursts = []

        for i, (date, count) in enumerate(zip(sorted_dates, count_vals)):
            if count > threshold:
                bursts.append(BurstEvent(
                    keyword=keyword,
                    burst_date=date,
                    burst_count=int(count),
                    baseline_avg=round(float(mean), 2),
                    burst_ratio=round(count / max(mean, 1), 2),
                    significance=round((count - mean) / std, 2),
                ))

        return bursts

    # ------------------------------------------------------------------
    # Cross-topic Correlation
    # ------------------------------------------------------------------
    def keyword_correlation(self, keyword1: str,
                            keyword2: str) -> float:
        """Compute Pearson correlation between two keyword time series."""
        if not self._fitted:
            raise RuntimeError("Call fit() first")

        c1 = self._keyword_counts[keyword1]
        c2 = self._keyword_counts[keyword2]

        # Union of all dates
        all_dates = sorted(set(c1.keys()) | set(c2.keys()))
        v1 = np.array([c1.get(d, 0) for d in all_dates], dtype=float)
        v2 = np.array([c2.get(d, 0) for d in all_dates], dtype=float)

        if len(v1) < 3:
            return 0.0

        corr = np.corrcoef(v1, v2)[0, 1]
        return round(float(corr), 4) if not np.isnan(corr) else 0.0
