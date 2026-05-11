from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import Browser, Page, BrowserContext, async_playwright
from playwright_stealth import Stealth
import asyncio
import random
from datetime import datetime
import os

from app.config import get_settings
from app.schemas.flight import FlightSearchRequest, FlightResult as FlightResultSchema, ProviderError
from app.services.xpath_service import XPathService
from app.database import async_session_maker
from app.utils.user_agents import get_random_user_agent

settings = get_settings()


class BaseScraper(ABC):
    """Abstract base class for all flight scrapers."""

    provider_name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.debug_screenshots_dir = settings.debug_screenshots_dir
        os.makedirs(self.debug_screenshots_dir, exist_ok=True)

    @abstractmethod
    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        """Main scraping method to be implemented by subclasses."""
        pass

    async def _launch_browser(self) -> tuple[Browser, BrowserContext, Page]:
        """Launch browser with stealth configuration."""
        playwright = await async_playwright().start()

        # Random viewport size
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(800, 1080)

        browser = await playwright.chromium.launch(
            headless=settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=get_random_user_agent(),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            color_scheme="light",
        )

        page = await context.new_page()

        # Apply stealth using the Stealth class
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        return browser, context, page

    async def _load_xpaths(self) -> dict[str, str]:
        """Load XPath configurations from database."""
        async with async_session_maker() as db:
            xpaths = await XPathService.get_xpaths_for_provider(db, self.provider_name)
            return {
                field_name: xp.xpath or xp.css_selector
                for field_name, xp in xpaths.items()
                if xp.xpath or xp.css_selector
            }

    async def _human_type(self, page: Page, selector: str, text: str) -> None:
        """Type text with human-like delays."""
        await page.type(
            selector,
            text,
            delay=random.randint(80, 180),
        )
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def _fill_search_form(
        self,
        page: Page,
        xpaths: dict[str, str],
        params: FlightSearchRequest,
    ) -> None:
        """Fill the search form with given parameters."""
        # Fill origin
        if "search_origin_input" in xpaths:
            selector = xpaths["search_origin_input"]
            if selector.startswith("//"):
                origin_elem = page.locator(f"xpath={selector}")
            else:
                origin_elem = page.locator(selector)
            if await origin_elem.count() > 0:
                await origin_elem.first.click()
                await asyncio.sleep(random.uniform(0.5, 0.8))
                # Clear any prefilled text
                for _ in range(15):
                    await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.2, 0.4))
                await page.keyboard.type(params.origin or "", delay=random.randint(80, 150))
                await asyncio.sleep(random.uniform(1.2, 1.8))
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(0.4, 0.8))

        # Fill destination
        if "search_destination_input" in xpaths:
            selector = xpaths["search_destination_input"]
            if selector.startswith("//"):
                dest_elem = page.locator(f"xpath={selector}")
            else:
                dest_elem = page.locator(selector)
            if await dest_elem.count() > 0:
                await dest_elem.first.click()
                await asyncio.sleep(random.uniform(0.5, 0.8))
                # Clear any prefilled text
                for _ in range(15):
                    await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.2, 0.4))
                await page.keyboard.type(params.destination or "", delay=random.randint(80, 150))
                await asyncio.sleep(random.uniform(1.2, 1.8))
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(0.4, 0.8))

        # Fill outbound date
        if "search_date_outbound" in xpaths and params.outbound_date:
            selector = xpaths["search_date_outbound"]
            if selector.startswith("//"):
                date_elem = page.locator(f"xpath={selector}")
            else:
                date_elem = page.locator(selector)
            await date_elem.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            # Date selection is provider-specific and handled in subclasses

        # Fill return date if needed
        if params.return_date and "search_date_return" in xpaths:
            selector = xpaths["search_date_return"]
            if selector.startswith("//"):
                return_date_elem = page.locator(f"xpath={selector}")
            else:
                return_date_elem = page.locator(selector)
            await return_date_elem.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))

        # Fill passengers
        if "search_passengers_input" in xpaths:
            selector = xpaths["search_passengers_input"]
            if selector.startswith("//"):
                pax_elem = page.locator(f"xpath={selector}")
            else:
                pax_elem = page.locator(selector)
            await pax_elem.click()
            await asyncio.sleep(random.uniform(0.3, 0.8))

        # Click search button
        if "search_submit_button" in xpaths:
            selector = xpaths["search_submit_button"]
            if selector.startswith("//"):
                submit_elem = page.locator(f"xpath={selector}")
            else:
                submit_elem = page.locator(selector)
            await submit_elem.click()

    async def _wait_for_results(self, page: Page, timeout_ms: int = 30000) -> bool:
        """Wait for results to load. Returns True if successful."""
        try:
            # Wait for flight cards to appear
            xpaths = await self._load_xpaths()
            if "results_flight_card" in xpaths:
                selector = xpaths["results_flight_card"]
                if selector.startswith("//"):
                    await page.wait_for_selector(f"xpath={selector}", timeout=timeout_ms)
                else:
                    await page.wait_for_selector(selector, timeout=timeout_ms)
            else:
                # Generic wait
                await page.wait_for_timeout(5000)
            return True
        except Exception:
            return False

    async def _extract_results(self, page: Page, xpaths: dict[str, str]) -> list[dict]:
        """Extract raw results from the page."""
        results = []

        if "results_flight_card" not in xpaths:
            return results

        card_selector = xpaths["results_flight_card"]
        if card_selector.startswith("//"):
            cards = await page.query_selector_all(f"xpath={card_selector}")
        else:
            cards = await page.query_selector_all(card_selector)

        for card in cards:
            try:
                raw_data = {}

                # Extract each field
                for field_name, selector in xpaths.items():
                    if not field_name.startswith("result_"):
                        continue

                    if selector.startswith("//"):
                        elem = await card.query_selector(f"xpath={selector}")
                    else:
                        elem = await card.query_selector(selector)

                    if elem:
                        text = await elem.text_content()
                        raw_data[field_name] = text.strip() if text else ""

                    # Also try to get href for booking link
                    if field_name == "result_booking_link":
                        if elem:
                            href = await elem.get_attribute("href")
                            if href:
                                raw_data["result_booking_link"] = href

                if raw_data:
                    results.append(raw_data)

            except Exception:
                continue

        return results

    @abstractmethod
    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        """Parse raw extracted data into FlightResultSchema objects."""
        pass

    async def _is_captcha(self, page: Page) -> bool:
        """Check if the page shows a CAPTCHA."""
        title = await page.title()
        captcha_indicators = [
            "captcha",
            "verify",
            "security check",
            "please complete the security check",
        ]

        for indicator in captcha_indicators:
            if indicator.lower() in title.lower():
                return True

        # Check for common CAPTCHA elements
        captcha_selectors = [
            '[id*="captcha"]',
            '[class*="captcha"]',
            '[name*="captcha"]',
            'iframe[src*="captcha"]',
            'iframe[src*="recaptcha"]',
        ]

        for selector in captcha_selectors:
            if await page.query_selector(selector):
                return True

        return False

    async def _save_screenshot(self, page: Page, reason: str = "error") -> str:
        """Save a debug screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.provider_name}_{timestamp}_{reason}.png"
        filepath = os.path.join(self.debug_screenshots_dir, filename)
        await page.screenshot(path=filepath, full_page=True)
        return filepath

    async def scrape_with_retry(
        self,
        params: FlightSearchRequest,
        max_retries: int = None,
    ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
        """Scrape with retry logic."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                browser = None
                context = None
                page = None

                try:
                    browser, context, page = await self._launch_browser()

                    # Navigate to the site
                    await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                    # Check for CAPTCHA
                    if await self._is_captcha(page):
                        await self._save_screenshot(page, "captcha")
                        return [], ProviderError(
                            provider=self.provider_name,
                            reason="captcha_blocked",
                            message="CAPTCHA detected on provider page",
                        )

                    # Load XPaths
                    xpaths = await self._load_xpaths()

                    # Fill and submit search form
                    await self._fill_search_form(page, xpaths, params)
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                    # Wait for results
                    results_loaded = await self._wait_for_results(page)

                    if not results_loaded:
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                            continue
                        return [], ProviderError(
                            provider=self.provider_name,
                            reason="timeout",
                            message="Results did not load within timeout period",
                        )

                    # Check for CAPTCHA again after search
                    if await self._is_captcha(page):
                        await self._save_screenshot(page, "captcha")
                        return [], ProviderError(
                            provider=self.provider_name,
                            reason="captcha_blocked",
                            message="CAPTCHA detected after search submission",
                        )

                    # Extract and parse results
                    raw_results = await self._extract_results(page, xpaths)
                    parsed_results = await self._parse_results(raw_results, params)

                    return parsed_results, None

                finally:
                    # Cleanup browser
                    if page:
                        await page.close()
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()

            except Exception as e:
                last_error = e
                try:
                    if page:
                        await self._save_screenshot(page, "error")
                except Exception:
                    pass

                if attempt < max_retries:
                    await asyncio.sleep(3)
                    continue

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        return [], ProviderError(
            provider=self.provider_name,
            reason="scrape_error",
            message=f"Scraping failed: {error_msg}",
        )
