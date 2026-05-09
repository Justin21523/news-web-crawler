#!/usr/bin/env python
"""
Humanization Middleware

Simulates human browsing to evade behavioral bot detection:
- Random scrolling (1-4 actions, 20-80% positions)
- Occasional scroll-up (re-reading)
- Mouse movement dispatch
- Gaussian delays between actions

Usage in settings.py:
    DOWNLOADER_MIDDLEWARES = {
        "middlewares.humanization.HumanizationMiddleware": 586,
    }
"""

import logging
import random
from typing import List
from scrapy import signals
from scrapy.http import Request
from scrapy.exceptions import NotConfigured

try:
    from scrapy_playwright.page import PageMethod
except ImportError:
    PageMethod = None

logger = logging.getLogger(__name__)


class HumanizationMiddleware:
    """Add human-like behavior to Playwright requests."""

    def __init__(
        self,
        enabled: bool = True,
        min_delay: float = 0.5,
        max_delay: float = 2.0,
        scroll_enabled: bool = True,
    ):
        if PageMethod is None:
            raise NotConfigured("scrapy-playwright not installed")
        self.enabled = enabled
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.scroll_enabled = scroll_enabled

    @classmethod
    def from_crawler(cls, crawler):
        mw = cls(
            enabled=crawler.settings.getbool("HUMANIZATION_ENABLED", True),
            min_delay=crawler.settings.getfloat("HUMANIZATION_MIN_DELAY", 0.5),
            max_delay=crawler.settings.getfloat("HUMANIZATION_MAX_DELAY", 2.0),
            scroll_enabled=crawler.settings.getbool("HUMANIZATION_SCROLL_ENABLED", True),
        )
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        logger.info(f"HumanizationMiddleware active for {spider.name}")

    def process_request(self, request: Request, spider):
        if not self.enabled or not request.meta.get("playwright"):
            return None

        page_methods = request.meta.get("playwright_page_methods", [])
        if not isinstance(page_methods, list):
            page_methods = [page_methods]

        page_methods.extend(self._humanization_methods())
        request.meta["playwright_page_methods"] = page_methods
        return None

    # ------------------------------------------------------------------
    def _humanization_methods(self) -> List[PageMethod]:
        methods = []

        # initial load delay
        methods.append(PageMethod("wait_for_timeout", int(self._delay(0.5, 1.5) * 1000)))

        # scroll pattern
        if self.scroll_enabled:
            methods.extend(self._scroll_pattern())

        # mouse movement
        if random.random() > 0.5:
            x, y = random.randint(100, 1200), random.randint(100, 800)
            methods.append(PageMethod("evaluate", f"() => document.dispatchEvent(new MouseEvent('mousemove', {{clientX:{x},clientY:{y},bubbles:true}}))"))

        # reading delay
        methods.append(PageMethod("wait_for_timeout", int(self._delay(1.0, 3.0) * 1000)))
        return methods

    def _delay(self, lo: float, hi: float) -> float:
        mean, std = (lo + hi) / 2, (hi - lo) / 4
        return max(lo, min(hi, random.gauss(mean, std)))

    def _scroll_pattern(self) -> List[PageMethod]:
        methods = []
        for _ in range(random.randint(1, 4)):
            pct = random.randint(20, 80)
            methods.append(PageMethod("evaluate", f"() => window.scrollTo({{top: document.body.scrollHeight * {pct}/100, behavior:'smooth'}})"))
            methods.append(PageMethod("wait_for_timeout", int(self._delay(0.3, 1.0) * 1000)))
        return methods
