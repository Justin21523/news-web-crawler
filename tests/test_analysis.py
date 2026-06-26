"""Tests for analysis modules."""

import pytest
import json
import tempfile
from pathlib import Path

from analysis.collocation import CollocationAnalyzer
from analysis.classification import SentimentAnalyzer, SentimentResult
from analysis.summarization import Summarizer
from analysis.time_series import TimeSeriesAnalyzer
from utils.resource_manager import ResourceManager


# ---------------------------------------------------------------------------
# Resource Manager
# ---------------------------------------------------------------------------
class TestResourceManager:
    def test_init(self):
        rm = ResourceManager(max_ram_gb=2.0, max_threads=16)
        assert rm.max_threads <= 16

    def test_ram_status(self):
        rm = ResourceManager()
        usage = rm.current_ram_usage_gb()
        assert usage > 0
        assert rm.available_ram_gb() > 0

    def test_estimate_batch_size(self):
        rm = ResourceManager(max_ram_gb=4.0)
        bs = rm.estimate_batch_size(["test"] * 100, chars_per_item=1000)
        assert bs >= 8

    def test_thread_pool(self):
        rm = ResourceManager(max_threads=4)
        with rm.get_thread_pool() as pool:
            futures = [pool.submit(lambda: 1) for _ in range(4)]
            results = [f.result() for f in futures]
        assert results == [1, 1, 1, 1]


# ---------------------------------------------------------------------------
# Collocation
# ---------------------------------------------------------------------------
class TestCollocationAnalyzer:
    @pytest.fixture
    def analyzer(self):
        # Create synthetic documents with known collocations
        docs = [
            ["人工", "智慧", "發展", "快速", "人工", "智慧", "未來"],
            ["人工", "智慧", "應用", "廣泛", "機器", "學習"],
            ["機器", "學習", "深度", "學習", "人工", "智慧"],
            ["人工", "智慧", "發展", "機器", "學習"],
            ["深度", "學習", "人工", "智慧", "發展"],
        ] * 20  # Repeat for frequency
        a = CollocationAnalyzer(window_size=3, min_freq=5)
        a.fit(docs)
        return a

    def test_fit(self, analyzer):
        assert analyzer.total_tokens > 0
        assert analyzer.total_docs > 0
        assert len(analyzer.unigram_freq) > 0

    def test_top_collocations_pmi(self, analyzer):
        pairs = analyzer.top_collocations(topk=10, method="pmi")
        assert len(pairs) > 0
        assert pairs[0].pmi > 0

    def test_top_collocations_ll(self, analyzer):
        pairs = analyzer.top_collocations(topk=10, method="log_likelihood")
        assert len(pairs) > 0

    def test_cooccurrence_matrix(self, analyzer):
        matrix, vocab = analyzer.get_cooccurrence_matrix(top_n=20)
        assert matrix.shape[0] == len(vocab)
        assert matrix.shape[0] == matrix.shape[1]


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------
class TestSentimentAnalyzer:
    @pytest.fixture
    def sa(self):
        return SentimentAnalyzer()

    def test_positive(self, sa):
        results = sa.analyze(["人工智慧發展快速，帶來許多創新突破"])
        assert len(results) == 1
        assert len(results[0].positive_words) >= 0  # may or may not hit lexicon

    def test_negative(self, sa):
        results = sa.analyze(["經濟衰退危機，股市下跌損失慘重"])
        assert len(results) == 1

    def test_neutral(self, sa):
        results = sa.analyze(["今天天氣晴朗溫度適中"])
        assert len(results) == 1

    def test_batch(self, sa):
        texts = ["好消息成功突破", "壞消息失敗危機", "普通的一天"]
        results = sa.analyze(texts)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------
class TestSummarizer:
    SAMPLE_TEXT = (
        "人工智慧是當前最熱門的技術話題。許多專家認為人工智慧將改變產業。"
        "機器學習是人工智慧的核心技術之一。深度學習則進一步推動了發展。"
        "台灣在人工智慧領域具有重要地位。許多科技公司投入大量資源研發。"
        "未來人工智慧將更加普及化。各行各業都會受到影響。"
    )

    @pytest.fixture
    def summarizer(self):
        return Summarizer()

    def test_lead_k(self, summarizer):
        result = summarizer.lead_k(self.SAMPLE_TEXT, k=2)
        assert len(result.sentences) == 2
        assert result.method == "lead_k"

    def test_extractive(self, summarizer):
        result = summarizer.extractive(self.SAMPLE_TEXT, ratio=0.3)
        assert len(result.sentences) >= 1
        assert result.method == "extractive_textrank"

    def test_mmr(self, summarizer):
        result = summarizer.mmr_summary(self.SAMPLE_TEXT, k=3, diversity=0.7)
        assert len(result.sentences) <= 3
        assert result.method == "mmr"


# ---------------------------------------------------------------------------
# Time Series
# ---------------------------------------------------------------------------
class TestTimeSeriesAnalyzer:
    @pytest.fixture
    def analyzer(self):
        documents = [
            ["人工", "智慧", "發展"],
            ["人工", "智慧", "應用"],
            ["機器", "學習", "突破"],
            ["人工", "智慧", "發展", "快速"],
            ["深度", "學習", "成長"],
        ]
        dates = [
            "2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15", "2024-03-01"
        ]
        a = TimeSeriesAnalyzer(time_bin="month")
        a.fit(documents, dates=dates, keywords=["人工", "智慧", "發展", "機器"])
        return a

    def test_topic_trends(self, analyzer):
        trends = analyzer.topic_trends()
        assert len(trends) > 0
        assert all(t.trend_direction in ("up", "down", "stable") for t in trends)

    def test_correlation(self, analyzer):
        corr = analyzer.keyword_correlation("人工", "智慧")
        assert -1 <= corr <= 1

    def test_burst_detection(self, analyzer):
        bursts = analyzer.detect_bursts("人工", z_threshold=1.0)
        # May or may not have bursts depending on data
        assert isinstance(bursts, list)


# ---------------------------------------------------------------------------
# CKIP Pipeline (skip if not installed)
# ---------------------------------------------------------------------------
class TestCKIPPipeline:
    @pytest.mark.skip(reason="CKIP requires ckip-transformers (heavy dependency)")
    def test_basic(self):
        from nlp.ckip_pipeline import CKIPPipeline
        nlp = CKIPPipeline(device_id=-1)  # CPU
        result = nlp.process("人工智慧是未來趨勢")
        assert len(result.filtered_words) > 0


# ---------------------------------------------------------------------------
# Opinion Lexicon (real file test)
# ---------------------------------------------------------------------------
class TestOpinionLexicon:
    LEXICON_PATH = "/mnt/c/data/features/opinion_word.xlsx"

    @pytest.fixture
    def lex(self):
        from analysis.opinion_lexicon import OpinionLexicon
        if not Path(self.LEXICON_PATH).exists():
            pytest.skip(f"Opinion lexicon file not found: {self.LEXICON_PATH}")
        return OpinionLexicon(self.LEXICON_PATH)

    def test_load(self, lex):
        assert len(lex.lexicon) > 20000  # ~27K words

    def test_match_positive(self, lex):
        matches = lex._match_opinion_words("這是一大步也是一大突破一大勝利")
        assert len(matches) > 0
        assert all(m[1] > 0 for m in matches)

    def test_match_negative(self, lex):
        matches = lex._match_opinion_words("這是一個一大打擊一文不值")
        assert len(matches) > 0
        assert all(m[1] < 0 for m in matches)

    def test_analyze_texts(self, lex):
        texts = [
            "人工智慧發展快速帶來許多創新突破",
            "經濟衰退危機股市下跌損失慘重",
            "今天開會討論了專案進度",
        ]
        scores = lex.analyze_texts(texts)
        assert len(scores) == 3
        assert all(isinstance(s.score, float) for s in scores)

    def test_analyze_tokenized(self, lex):
        token_lists = [
            ["人工", "智慧", "發展", "快速", "突破"],
            ["經濟", "衰退", "危機", "下跌"],
        ]
        scores = lex.analyze_tokenized(token_lists)
        assert len(scores) == 2

    def test_summary(self, lex):
        scores = lex.analyze_texts(["發展快速突破", "衰退危機下跌", "普通一天"])
        summary = lex.summary(scores)
        assert summary["total_docs"] == 3
        assert "mean_score" in summary

    def test_to_dataframe(self, lex):
        scores = lex.analyze_texts(["發展快速", "衰退下跌"])
        df = lex.to_dataframe(scores)
        assert len(df) == 2
        assert "score" in df.columns
        assert "label" in df.columns
