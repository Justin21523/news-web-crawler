#!/usr/bin/env python
"""
LTN (Liberty Times Net / 自由時報) Spider — Sequential ID enumeration

Strategy: Direct ID enumeration from 1 to 5,250,000+
URL pattern: https://news.ltn.com.tw/news/{category}/paper/{ID}
No Playwright needed — serves static HTML.
"""

import scrapy
import logging
from datetime import datetime
from spiders.base import BasePlaywrightSpider

logger = logging.getLogger(__name__)


class LTNSpider(BasePlaywrightSpider):
    name = "ltn"
    allowed_domains = ["news.ltn.com.tw"]
    use_playwright = False

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "DOWNLOAD_DELAY": 0.5,
        "RETRY_TIMES": 2,
    }

    def __init__(self, start_date: str = None, end_date: str = None,
                 max_articles: int = 50000, start_id: int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_date = datetime.fromisoformat(start_date) if start_date else None
        self.end_date = datetime.fromisoformat(end_date) if end_date else None
        self.max_articles = max_articles
        self.start_id = start_id or 5200000
        self.count = 0

    def start_requests(self):
        end_id = self.start_id - self.max_articles
        for aid in range(self.start_id, end_id, -1):
            # Use breaking-news category as catch-all
            url = f"https://news.ltn.com.tw/news/breakingnews/paper/{aid}"
            yield scrapy.Request(url, callback=self.parse_article, errback=self._skip, dont_filter=True)

    def parse_article(self, response):
        title = (response.css("h1::text").get()
                 or response.css("meta[property='og:title']::attr(content)").get() or "").strip()
        content = " ".join(response.css("div.text p::text").getall()).strip()
        date_str = response.css("span.time::text").get("")
        publish_date = self.parse_date_from_text(date_str) if date_str else None

        if self.start_date and publish_date:
            try:
                if datetime.fromisoformat(publish_date) < self.start_date:
                    return
                if self.end_date and datetime.fromisoformat(publish_date) > self.end_date:
                    return
            except ValueError:
                pass

        if not title or not content:
            return

        self.count += 1
        # Extract category from URL: /news/{category}/breakingnews/...
        cat = response.url.split("/")[4] if len(response.url.split("/")) > 4 else ""

        yield {
            "article_id": str(self.count),
            "url": response.url,
            "source": "ltn",
            "source_name": "自由時報",
            "title": title,
            "content": content,
            "author": response.css("span.reporter::text").get(""),
            "publish_date": publish_date,
            "category": cat,
            "category_name": "",
            "tags": [t.strip() for t in response.css("div.keyword a::text").getall()],
            "image_url": response.css("meta[property='og:image']::attr(content)").get(""),
            "crawled_at": datetime.now().isoformat(),
        }

    def _skip(self, failure):
        pass  # silent 404
