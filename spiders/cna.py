#!/usr/bin/env python
"""
CNA (Central News Agency / 中央社) Spider — Playwright version

Strategy:
    1. Start from category list pages: https://www.cna.com.tw/list/{cat}.aspx
    2. Follow pagination: ?page=N
    3. Extract article links → detail page → parse with 6-level fallback

Usage:
    scrapy crawl cna -a start_date=2024-01-01 -a end_date=2024-01-31
"""

import scrapy
import logging
from datetime import datetime
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod

from spiders.base import BasePlaywrightSpider

logger = logging.getLogger(__name__)


class CNASpider(BasePlaywrightSpider):
    name = "cna"
    allowed_domains = ["cna.com.tw"]

    CATEGORIES = {
        "aipl": "政治", "aie": "財經", "ahel": "生活", "ait": "科技",
        "asoc": "社會", "acul": "文化", "aspt": "運動", "amov": "娛樂",
        "aopl": "國際", "acn": "兩岸", "aloc": "地方",
    }

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 3,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3,
        "AUTOTHROTTLE_MAX_DELAY": 15,
    }

    def __init__(self, start_date: str = None, end_date: str = None,
                 categories: str = None, max_articles: int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_date = datetime.fromisoformat(start_date) if start_date else None
        self.end_date = datetime.fromisoformat(end_date) if end_date else None
        self.target_cats = [c.strip() for c in categories.split(",")] if categories else list(self.CATEGORIES.keys())
        self.max_articles = max_articles
        self.article_count = 0

    def start_requests(self):
        for cat in self.target_cats:
            if cat not in self.CATEGORIES:
                continue
            url = f"https://www.cna.com.tw/list/{cat}.aspx"
            yield scrapy.Request(
                url, callback=self.parse_list,
                meta={"category": cat, "category_name": self.CATEGORIES[cat], "page": 1,
                      **self.get_playwright_meta(wait_selector="div.newsList")},
            )

    def parse_list(self, response):
        if self.max_articles and self.article_count >= self.max_articles:
            return

        for link in response.css("div.newsList li a::attr(href)").getall():
            article_url = urljoin(response.url, link)
            yield scrapy.Request(
                article_url, callback=self.parse_article,
                meta={
                    "category": response.meta["category"],
                    "category_name": response.meta["category_name"],
                    **self.get_playwright_meta(wait_selector="div.article"),
                },
            )

        # pagination
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page, callback=self.parse_list,
                meta={"category": response.meta["category"],
                      "category_name": response.meta["category_name"],
                      "page": response.meta["page"] + 1,
                      **self.get_playwright_meta(wait_selector="div.newsList")},
            )

    def parse_article(self, response):
        if self.max_articles and self.article_count >= self.max_articles:
            return

        title = (response.css("h1.centralContent span::text").get()
                 or response.css("meta[property='og:title']::attr(content)").get()
                 or response.css("title::text").get() or "").strip()
        content = " ".join(response.css("div.paragraph p::text").getall()).strip()
        date_str = (response.css("div.date::text").get()
                    or response.css("meta[property='article:published_time']::attr(content)").get() or "")
        publish_date = self.parse_date_from_text(date_str) if date_str else None

        if self.start_date and publish_date:
            try:
                pub_dt = datetime.fromisoformat(publish_date)
                if pub_dt < self.start_date:
                    return
                if self.end_date and pub_dt > self.end_date:
                    return
            except ValueError:
                pass

        if not title or not content:
            return

        self.article_count += 1
        yield {
            "article_id": response.url.split("/")[-1].replace(".aspx", ""),
            "url": response.url,
            "source": "cna",
            "source_name": "中央社",
            "title": title,
            "content": content,
            "author": "",
            "publish_date": publish_date,
            "category": response.meta.get("category", ""),
            "category_name": response.meta.get("category_name", ""),
            "tags": [t.strip() for t in response.css("div.keywordTag a::text").getall()],
            "image_url": response.css("meta[property='og:image']::attr(content)").get(""),
            "crawled_at": datetime.now().isoformat(),
        }
