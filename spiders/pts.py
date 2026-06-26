#!/usr/bin/env python
"""
PTS (Public Television Service / 公視) Spider — lightweight Scrapy only

Strategy: Sequential ID enumeration from /dailynews page
URL pattern: https://news.pts.org.tw/article/{ID}
"""

import scrapy
import json
import logging
from datetime import datetime
from spiders.base import BasePlaywrightSpider

logger = logging.getLogger(__name__)


class PTSSpider(BasePlaywrightSpider):
    name = "pts"
    allowed_domains = ["news.pts.org.tw"]
    use_playwright = False

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "DOWNLOAD_DELAY": 0.5,
    }

    def __init__(self, start_date: str = None, end_date: str = None,
                 max_articles: int = 50000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_date = datetime.fromisoformat(start_date) if start_date else None
        self.end_date = datetime.fromisoformat(end_date) if end_date else None
        self.max_articles = max_articles
        self.count = 0
        self.max_id = None

    def start_requests(self):
        # Discover max ID from dailynews page
        yield scrapy.Request("https://news.pts.org.tw/dailynews", callback=self.discover_ids)

    def discover_ids(self, response):
        # Extract highest article ID from the dailynews page
        ids = response.css("a[href*='/article/']::attr(href)").re(r"/article/(\d+)")
        if ids:
            self.max_id = max(int(i) for i in ids)
        else:
            self.max_id = 780000  # fallback

        start = max(0, self.max_id - self.max_articles)
        for aid in range(self.max_id, start, -1):
            yield scrapy.Request(
                f"https://news.pts.org.tw/article/{aid}",
                callback=self.parse_article,
                errback=self.handle_error,
                dont_filter=True,
            )

    def parse_article(self, response):
        # Try JSON-LD first
        json_ld = self._extract_json_ld(response)

        title = (json_ld.get("headline")
                 or response.css("meta[property='og:title']::attr(content)").get()
                 or response.css("h1::text").get() or "").strip()
        content = (json_ld.get("articleBody")
                   or " ".join(response.css("div.article-content p::text").getall())
                   or " ".join(response.css("article p::text").getall()) or "").strip()

        date_str = (json_ld.get("datePublished")
                    or response.css("meta[property='article:published_time']::attr(content)").get() or "")
        publish_date = date_str[:10] if date_str else None

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
        yield {
            "article_id": str(self.count),
            "url": response.url,
            "source": "pts",
            "source_name": "公視",
            "title": title,
            "content": content,
            "author": json_ld.get("author", "") or response.css('meta[name="author"]::attr(content)').get(""),
            "publish_date": publish_date,
            "category": response.css('meta[property="article:section"]::attr(content)').get(""),
            "category_name": "",
            "tags": [t for t in (response.css('meta[name="keywords"]::attr(content)').get("") or "").split(",") if t],
            "image_url": response.css("meta[property='og:image']::attr(content)").get(""),
            "crawled_at": datetime.now().isoformat(),
        }

    def handle_error(self, failure):
        """Silently skip 404s (sparse ID space)."""
        pass

    @staticmethod
    def _extract_json_ld(response) -> dict:
        for script in response.css("script[type='application/ld+json']::text").getall():
            try:
                data = json.loads(script)
                if isinstance(data, dict) and data.get("@type") == "NewsArticle":
                    return data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                            return item
            except json.JSONDecodeError:
                continue
        return {}
