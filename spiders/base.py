#!/usr/bin/env python
"""
Base Playwright Spider with Anti-Detection

Abstract base class providing Playwright integration with anti-detection:
- Browser fingerprint randomization (UA, viewport, timezone)
- Stealth JS injection hooks
- Human-like delay generation
- Chinese date parsing (ROC year conversion)

Usage:
    from spiders.base import BasePlaywrightSpider

    class MySpider(BasePlaywrightSpider):
        name = "my_spider"
        ...
"""

import scrapy
import random
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

logger = logging.getLogger(__name__)


class BasePlaywrightSpider(scrapy.Spider):
    """Base spider with Playwright support and anti-detection features."""

    use_playwright = True

    # Fallback UA pool
    FALLBACK_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    ]

    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1680, "height": 1050},
        {"width": 2560, "height": 1440},
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_fingerprint()
        logger.info(f"Initialized {self.name} — UA: {self.current_user_agent[:50]}..., Viewport: {self.current_viewport}")

    # ------------------------------------------------------------------
    # Fingerprint
    # ------------------------------------------------------------------
    def _init_fingerprint(self):
        if UserAgent:
            self.current_user_agent = UserAgent().random
        else:
            self.current_user_agent = random.choice(self.FALLBACK_USER_AGENTS)

        self.current_viewport = random.choice(self.VIEWPORTS)
        self.timezone = "Asia/Taipei"
        self.locale = "zh-TW"
        self.device_scale_factor = random.choice([1, 1.5, 2])

        self.playwright_context_kwargs = {
            "viewport": self.current_viewport,
            "user_agent": self.current_user_agent,
            "locale": self.locale,
            "timezone_id": self.timezone,
            "device_scale_factor": self.device_scale_factor,
            "has_touch": random.choice([True, False]),
            "is_mobile": False,
            "java_script_enabled": True,
            "ignore_https_errors": True,
            "bypass_csp": True,
            "extra_http_headers": {
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            },
        }

        self.playwright_page_goto_kwargs = {"wait_until": "domcontentloaded"}

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def get_playwright_meta(self, **kwargs) -> Dict[str, Any]:
        """Build Playwright request meta dict with fingerprint settings."""
        wait_selector = kwargs.pop("wait_selector", None)
        wait_selector_timeout = int(kwargs.pop("wait_selector_timeout", 30000))
        wait_until = kwargs.pop("wait_until", None)
        include_page = kwargs.pop("include_page", None)

        goto_kwargs = self.playwright_page_goto_kwargs.copy()
        if wait_until:
            goto_kwargs["wait_until"] = wait_until

        meta: Dict[str, Any] = {
            "playwright": True,
            "playwright_context_kwargs": self.playwright_context_kwargs.copy(),
            "playwright_page_goto_kwargs": goto_kwargs,
        }

        if include_page is not None:
            meta["playwright_include_page"] = bool(include_page)

        if kwargs:
            for key, value in kwargs.items():
                if key == "playwright_page_kwargs":
                    key = "playwright_page_goto_kwargs"
                if key in meta and isinstance(meta[key], dict) and isinstance(value, dict):
                    meta[key].update(value)
                else:
                    meta[key] = value

        if wait_selector:
            try:
                from scrapy_playwright.page import PageMethod
                page_methods = meta.get("playwright_page_methods", [])
                if not isinstance(page_methods, list):
                    page_methods = [page_methods]
                page_methods.insert(0, PageMethod("wait_for_selector", wait_selector, timeout=wait_selector_timeout))
                meta["playwright_page_methods"] = page_methods
            except Exception:
                pass

        return meta

    def human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
        mean = (min_seconds + max_seconds) / 2
        std = (max_seconds - min_seconds) / 4
        return max(min_seconds, min(max_seconds, random.gauss(mean, std)))

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def parse_date_from_text(self, date_text: str) -> Optional[str]:
        """Parse Chinese date strings (incl. ROC year) → ISO YYYY-MM-DD."""
        patterns = [
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
            r"(\d{2,3})年(\d{1,2})月(\d{1,2})日",
        ]
        for pattern in patterns:
            m = re.search(pattern, date_text)
            if m:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if year < 200:
                    year += 1911
                try:
                    return datetime(year, month, day).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def extract_text(self, selector, css: str = None, xpath: str = None, default: str = "") -> str:
        try:
            if css:
                text = selector.css(css).get()
            elif xpath:
                text = selector.xpath(xpath).get()
            else:
                text = selector.get()
            return " ".join(text.split()).strip() if text else default
        except Exception as e:
            logger.warning(f"Extract failed: {e}")
            return default

    def closed(self, reason):
        logger.info(f"Spider {self.name} closed: {reason}")


class PlaywrightPageMethods:
    """Common Playwright page method factories."""

    @staticmethod
    def wait_for_selector(selector: str, timeout: int = 30000):
        from scrapy_playwright.page import PageMethod
        return PageMethod("wait_for_selector", selector, timeout=timeout)

    @staticmethod
    def scroll_to_bottom():
        from scrapy_playwright.page import PageMethod
        return PageMethod("evaluate", "() => window.scrollTo(0, document.body.scrollHeight)")

    @staticmethod
    def random_scroll():
        from scrapy_playwright.page import PageMethod
        pct = random.randint(30, 70)
        return PageMethod("evaluate", f"() => window.scrollTo(0, document.body.scrollHeight * {pct / 100})")
