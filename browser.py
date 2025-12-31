"""
KZBIT Automation - Browser Management Module

Handles Playwright browser lifecycle with performance optimizations:
- Single browser instance
- Lightweight context per account
- Resource blocking for speed
"""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
)

from config import (
    BLOCKED_RESOURCE_TYPES,
    BLOCKED_URL_PATTERNS,
    NAVIGATION_TIMEOUT,
    HEADLESS,
)


class BrowserManager:
    """
    Manages a single Playwright browser instance.
    
    Design:
    - Browser launched once, reused for all accounts
    - Each account gets a fresh, isolated context
    - Contexts destroyed immediately after use
    - Resource blocking enabled for performance
    """
    
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Launch the browser instance."""
        async with self._lock:
            if self._browser is not None:
                return
            
            self._playwright = await async_playwright().start()
            
            # Use configured headless mode (True for server, False for debug)
            self._browser = await self._playwright.chromium.launch(
                headless=HEADLESS,
                slow_mo=0 if HEADLESS else 100,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-sandbox",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-translate",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-first-run",
                    "--safebrowsing-disable-auto-update",
                ]
            )
    
    async def stop(self) -> None:
        """Close browser and cleanup."""
        async with self._lock:
            try:
                if self._browser:
                    await self._browser.close()
            except Exception as e:
                # Silently catch to avoid crashing during shutdown
                # This often happens if the browser process is already gone
                error_msg = str(e)
                if "Connection closed" not in error_msg and "Target page, context or browser has been closed" not in error_msg:
                    print(f"Warning: Error closing browser: {e}")
            finally:
                self._browser = None

            try:
                if self._playwright:
                    await self._playwright.stop()
            except Exception as e:
                error_msg = str(e)
                if "invalid state" not in error_msg.lower():
                    print(f"Warning: Error stopping playwright: {e}")
            finally:
                self._playwright = None
    
    @asynccontextmanager
    async def new_context(self):
        """
        Create a new isolated browser context.
        
        Context is automatically destroyed on exit.
        Resource blocking is enabled for performance.
        
        Usage:
            async with browser_manager.new_context() as context:
                page = await context.new_page()
                await page.goto(url)
        """
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")
        
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
            # Minimal user agent
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        
        # Set default timeout
        context.set_default_timeout(NAVIGATION_TIMEOUT)
        
        try:
            yield context
        finally:
            await context.close()
    
    @asynccontextmanager
    async def new_page(self):
        """
        Create a new page with resource blocking.
        
        Convenience method that creates context + page.
        
        Usage:
            async with browser_manager.new_page() as page:
                await page.goto(url)
        """
        async with self.new_context() as context:
            page = await context.new_page()
            
            # Block unnecessary resources for speed
            await self._setup_resource_blocking(page)
            
            yield page
    
    async def _setup_resource_blocking(self, page: Page) -> None:
        """
        Configure resource blocking for maximum performance.
        
        Blocks: images, fonts, media, analytics
        """
        async def handle_route(route: Route) -> None:
            # Block by resource type
            if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            
            # Block by URL pattern
            url = route.request.url.lower()
            for pattern in BLOCKED_URL_PATTERNS:
                # Simple wildcard matching
                pattern_clean = pattern.replace("*", "").lower()
                if pattern_clean in url:
                    await route.abort()
                    return
            
            await route.continue_()
        
        await page.route("**/*", handle_route)


# Global singleton
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the browser manager singleton."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


async def cleanup_browser() -> None:
    """Cleanup browser resources."""
    global _browser_manager
    if _browser_manager:
        await _browser_manager.stop()
        _browser_manager = None
