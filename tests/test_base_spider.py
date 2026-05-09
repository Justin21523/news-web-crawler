"""Tests for base spider components."""

import pytest
from spiders.base import BasePlaywrightSpider


class DummySpider(BasePlaywrightSpider):
    name = "test_dummy"
    allowed_domains = ["test.com"]


@pytest.fixture
def spider():
    return DummySpider()


class TestFingerprint:
    def test_init_fingerprint(self, spider):
        assert spider.current_user_agent is not None
        assert spider.current_viewport in spider.VIEWPORTS
        assert spider.timezone == "Asia/Taipei"
        assert spider.locale == "zh-TW"

    def test_playwright_meta(self, spider):
        meta = spider.get_playwright_meta()
        assert meta["playwright"] is True
        assert "playwright_context_kwargs" in meta
        assert "playwright_page_goto_kwargs" in meta

    def test_playwright_meta_with_selector(self, spider):
        meta = spider.get_playwright_meta(wait_selector="div.content")
        assert "playwright_page_methods" in meta


class TestDateParsing:
    @pytest.mark.parametrize("input_date,expected", [
        ("2024年1月15日", "2024-01-15"),
        ("2024/01/15", "2024-01-15"),
        ("113年1月15日", "2024-01-15"),  # ROC year
        ("2024-03-20", "2024-03-20"),
        ("invalid", None),
    ])
    def test_parse_date(self, spider, input_date, expected):
        assert spider.parse_date_from_text(input_date) == expected


class TestExtractText:
    def test_extract_basic(self, spider):
        class FakeSel:
            def css(self, sel):
                class Inner:
                    def get(self):
                        return "  Hello  World  "
                return Inner()
        result = spider.extract_text(FakeSel(), css="h1")
        assert result == "Hello World"

    def test_extract_default(self, spider):
        class FakeSel:
            def css(self, sel):
                class Inner:
                    def get(self):
                        return None
                return Inner()
        assert spider.extract_text(FakeSel(), css="h1", default="N/A") == "N/A"


class TestHumanDelay:
    def test_delay_range(self, spider):
        for _ in range(20):
            d = spider.human_delay(1.0, 3.0)
            assert 1.0 <= d <= 3.0
