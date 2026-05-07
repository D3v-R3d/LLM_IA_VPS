"""
Scraping Service

Handles URL fetching and content extraction with anti-block measures:
- Retry with exponential backoff
- Realistic browser headers
- Playwright for JavaScript rendering
- BeautifulSoup for HTML parsing
- Scrapy-inspired concurrency for large crawls
"""

from typing import Dict, Any, Optional
import asyncio
import logging
import random

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


class ScrapingService:
    """
    Service for scraping web content with anti-block measures.

    Features:
    - Retry with exponential backoff (3 attempts)
    - Realistic browser headers to avoid detection
    - Random User-Agent rotation
    - Playwright for JavaScript rendering
    - BeautifulSoup for HTML parsing
    - Concurrency control for multiple URLs
    """

    def __init__(self):
        from app.services.agent_tools.tools import URLFetchService
        self.url_fetch = URLFetchService()
        from app.services.document import TextCleaningService
        self.text_cleaning = TextCleaningService()
        self._playwright_browser = None
        self._playwright_context = None

    async def _get_playwright(self):
        """Lazy-initialize Playwright browser with stealth settings."""
        if self._playwright_browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright_browser = await async_playwright().start()
                logger.info("Playwright initialized")
            except ImportError:
                logger.warning("playwright not installed")
                self._playwright_browser = None

    async def _close_playwright(self):
        """Close Playwright gracefully."""
        if self._playwright_browser is not None:
            try:
                await self._playwright_browser.__aexit__(None, None, None)
            except Exception:
                pass
            self._playwright_browser = None
            self._playwright_context = None

    async def _playwright_fetch_with_retry(
        self,
        url: str,
        max_retries: int = 2,
        base_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Fetch URL using Playwright (headless browser) with retry.

        Args:
            url: URL to fetch
            max_retries: Number of retry attempts
            base_delay: Initial delay between retries

        Returns:
            Dict with success, content, error
        """
        await self._get_playwright()
        if self._playwright_browser is None:
            return {"success": False, "error": "playwright not available"}

        from playwright.async_api import Browser, Page

        for attempt in range(max_retries + 1):
            browser: Browser = None
            context = None
            page: Page = None
            try:
                browser = await self._playwright_browser.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ]
                )
                context = await browser.new_context(
                    user_agent=random.choice(DEFAULT_USER_AGENTS),
                    viewport={"width": 1280, "height": 720},
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                page.set_default_timeout(30000)

                response = await page.goto(url, wait_until="load")
                status = response.status if response else 0

                if status == 200:
                    content = await page.content()
                    return {"success": True, "content": content, "url": url}

                blocked_signals = [403, 429]
                if status in blocked_signals:
                    logger.warning(f"Attempt {attempt + 1}: Blocked ({status}) for {url}")
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(delay)
                        continue
                    return {"success": False, "error": f"HTTP {status}", "url": url}

                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue

                return {"success": False, "error": f"HTTP {status}", "url": url}

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": str(e), "url": url}
            finally:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()

        return {"success": False, "error": "Max retries exceeded", "url": url}

    async def _basic_fetch_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Fetch URL using basic HTTP client with retry and exponential backoff.

        Args:
            url: URL to fetch
            max_retries: Number of retry attempts
            base_delay: Initial delay between retries

        Returns:
            Dict with success, content, headers, error
        """
        import aiohttp

        headers = {
            "User-Agent": random.choice(DEFAULT_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

        timeout = aiohttp.ClientTimeout(total=30)

        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers, ssl=True) as response:
                        if response.status == 200:
                            content = await response.text()
                            return {
                                "success": True,
                                "content": content,
                                "url": url,
                                "headers": dict(response.headers),
                            }
                        elif response.status in (403, 429):
                            logger.warning(f"Attempt {attempt + 1}: Blocked ({response.status}) for {url}")
                            if attempt < max_retries:
                                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                                await asyncio.sleep(delay)
                                continue
                            return {"success": False, "error": f"HTTP {response.status}", "url": url}
                        else:
                            if attempt < max_retries:
                                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                                await asyncio.sleep(delay)
                                continue
                            return {"success": False, "error": f"HTTP {response.status}", "url": url}

            except asyncio.TimeoutError:
                logger.warning(f"Attempt {attempt + 1}: Timeout for {url}")
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": "Timeout", "url": url}
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": str(e), "url": url}

        return {"success": False, "error": "Max retries exceeded", "url": url}

    async def fetch_and_clean(
        self,
        url: str,
        max_length: int = 10000,
        clean: bool = True,
        use_playwright: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch URL content with retry, then clean it.

        Strategy:
        1. Try Playwright (headless browser, JS rendering) for JS-heavy sites
        2. Fall back to basic HTTP fetch on failure

        Args:
            url: URL to fetch
            max_length: Maximum characters to fetch
            clean: Whether to clean the text
            use_playwright: Whether to try Playwright first (default True)

        Returns:
            Dict with success, content, title, url, error
        """
        raw_html = None

        if use_playwright:
            playwright_result = await self._playwright_fetch_with_retry(url)
            if playwright_result.get("success"):
                raw_html = playwright_result.get("content")

        if not raw_html:
            basic_result = await self._basic_fetch_with_retry(url)
            if basic_result.get("success"):
                raw_html = basic_result.get("content")
            else:
                return {
                    "success": False,
                    "error": basic_result.get("error", "Fetch failed"),
                    "url": url,
                }

        if not raw_html:
            return {
                "success": False,
                "error": "No content received",
                "url": url,
            }

        if clean:
            content = self._extract_text_from_html(raw_html)
            content = self.text_cleaning.clean(content)
            content = self.text_cleaning.truncate(content, max_length)
        else:
            content = raw_html

        return {
            "success": True,
            "content": content,
            "url": url,
            "title": self._extract_title_from_html(raw_html) or "",
            "snippet": content[:200] if content else "",
        }

    def _extract_text_from_html(self, html_text: str) -> str:
        """Extract clean text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_text, 'lxml')

        for tag in soup(['script', 'style', 'noscript', 'svg', 'meta', 'link']):
            tag.decompose()

        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())

        return text

    def _extract_title_from_html(self, html_text: str) -> str:
        """Extract title from HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_text, 'lxml')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.get_text(strip=True)

        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.string:
            return h1_tag.get_text(strip=True)

        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        return ""

    async def fetch_multiple(
        self,
        urls: list[str],
        max_length: int = 10000,
        clean: bool = True,
        concurrency: int = 3,
    ) -> list[Dict[str, Any]]:
        """
        Fetch multiple URLs with controlled concurrency.

        Args:
            urls: List of URLs to fetch
            max_length: Maximum characters per URL
            clean: Whether to clean each text
            concurrency: Maximum concurrent requests (default 3)

        Returns:
            List of result dicts
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_fetch(url: str) -> Dict[str, Any]:
            async with semaphore:
                await asyncio.sleep(random.uniform(0.5, 2.0))
                return await self.fetch_and_clean(url, max_length, clean)

        tasks = [bounded_fetch(url) for url in urls]
        return await asyncio.gather(*tasks)