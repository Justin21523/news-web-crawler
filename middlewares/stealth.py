#!/usr/bin/env python
"""
Stealth Middleware

Injects JavaScript before page load to hide automation markers:
- navigator.webdriver → undefined
- window.chrome.runtime → mock
- Permissions API spoof
- navigator.plugins → fake Chrome plugins
- WebGL vendor → Intel Inc.
- Function.toString → native-looking strings

Usage in settings.py:
    DOWNLOADER_MIDDLEWARES = {
        "middlewares.stealth.StealthMiddleware": 585,
    }
"""

import logging
from scrapy import signals
from scrapy.http import Request
from scrapy.exceptions import NotConfigured

try:
    from scrapy_playwright.page import PageMethod
except ImportError:
    PageMethod = None

logger = logging.getLogger(__name__)

STEALTH_SCRIPT = r"""
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

window.chrome = { runtime: {} };

const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { 0: {type:"application/x-google-chrome-pdf",suffixes:"pdf",description:"Portable Document Format"}, description:"Portable Document Format", filename:"internal-pdf-viewer", length:1, name:"Chrome PDF Plugin" },
        { 0: {type:"application/pdf",suffixes:"pdf",description:""}, description:"", filename:"mhjfbmdgcfjbbpaeojofohoefgiehjai", length:1, name:"Chrome PDF Viewer" },
        { 0: {type:"application/x-nacl",suffixes:"",description:"Native Client Executable"}, 1: {type:"application/x-pnacl",suffixes:"",description:"Portable Native Client Executable"}, description:"", filename:"internal-nacl-plugin", length:2, name:"Native Client" }
    ],
});

Object.defineProperty(navigator, 'languages', { get: () => ['zh-TW','zh','en-US','en'] });

const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};

if (!window.chrome) {
    Object.defineProperty(window, 'chrome', {
        get: () => ({
            app: { isInstalled: false },
            webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
            runtime: {
                PlatformOs: { MAC:'mac', WIN:'win', ANDROID:'android', CROS:'cros', LINUX:'linux' },
                PlatformArch: { ARM:'arm', X86_32:'x86-32', X86_64:'x86-64' },
            },
        }),
    });
}

delete navigator.__proto__.webdriver;

const _toString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === navigator.permissions.query) return 'function query() { [native code] }';
    if (this === WebGLRenderingContext.prototype.getParameter) return 'function getParameter() { [native code] }';
    return _toString.apply(this, arguments);
};
"""


class StealthMiddleware:
    """Apply stealth JS injection to every Playwright request."""

    def __init__(self, enabled: bool = True):
        if PageMethod is None:
            raise NotConfigured("scrapy-playwright not installed")
        self.enabled = enabled

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool("PLAYWRIGHT_STEALTH_ENABLED", True)
        mw = cls(enabled=enabled)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        logger.info(f"StealthMiddleware active for {spider.name}")

    def process_request(self, request: Request, spider):
        if not self.enabled or not request.meta.get("playwright"):
            return None

        page_methods = request.meta.get("playwright_page_methods", [])
        if not isinstance(page_methods, list):
            page_methods = [page_methods]

        page_methods.insert(0, PageMethod("add_init_script", script=STEALTH_SCRIPT))
        request.meta["playwright_page_methods"] = page_methods
        return None
