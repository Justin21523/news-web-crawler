"""
Scrapy Settings for News Web Crawler

Shared configuration for all spiders.
Override per-spider in their `custom_settings` dict.
"""

BOT_NAME = "news_crawler"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True

# ---------------------------------------------------------------------------
# Concurrency (conservative defaults — override per-spider)
# ---------------------------------------------------------------------------
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1

RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ---------------------------------------------------------------------------
# Playwright
# ---------------------------------------------------------------------------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handlers.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handlers.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ],
}
PLAYWRIGHT_STEALTH_ENABLED = True

# ---------------------------------------------------------------------------
# Middlewares
# ---------------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "middlewares.stealth.StealthMiddleware": 585,
    "middlewares.humanization.HumanizationMiddleware": 586,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ---------------------------------------------------------------------------
# Item Pipeline (pass-through — add dedup / validation as needed)
# ---------------------------------------------------------------------------
ITEM_PIPELINES = {}
