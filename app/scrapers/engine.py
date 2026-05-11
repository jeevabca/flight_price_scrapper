import asyncio
import re
import random
import time
from typing import Optional
from datetime import datetime
from playwright.async_api import Locator, Page
from app.utils.google_flights_url import build_google_flights_url
from app.utils.kayak_url import build_kayak_url
from app.utils.skyscanner_url import build_skyscanner_url
from app.utils.mmt_url import build_makemytrip_url
from app.config import get_settings
from app.schemas.flight import (
    FlightSearchRequest,
    FlightResult as FlightResultSchema,
    ProviderError,
    ProviderException,
)
from app.scrapers.base_scraper import BaseScraper

settings = get_settings()


class SkyscannerScraper(BaseScraper):
    """Scraper for Skyscanner (https://www.skyscanner.co.in)."""

    provider_name = "skyscanner"
    base_url = "https://www.skyscanner.co.in"

    SELECTORS = {
        "result_price": "span[class*='Price_mainPriceContainer']",
        "result_airline": "div[class*='LegLogo_label']",
        "result_departure_time": "span[class*='LegInfo_routePartialTime']:first-of-type",
        "result_arrival_time": "span[class*='LegInfo_routePartialTime']:last-of-type",
        "result_duration": "span[class*='Duration_duration']",
        "result_stops": "span[class*='LegInfo_stopStation']",
    }

    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        """Scrape flight results from Skyscanner using Direct URL."""
        results, error = await self.scrape_with_retry(params)
        if error:
            raise ProviderException(error)
        return results

    async def scrape_with_retry(
        self,
        params: FlightSearchRequest,
        max_retries: int = None,
    ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
        """Overridden to use Direct URL technique for Skyscanner."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries or 2

        last_error = None
        for attempt in range(max_retries + 1):
            browser = None
            context = None
            page = None
            try:
                browser, context, page = await self._launch_browser()
                
                # Step 1: Build Direct URL
                search_url = build_skyscanner_url(params)
                print(f"[{self.provider_name.upper()}] Navigating to: {search_url}")
                
                # Step 2: Navigate directly
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(8) # Wait for page results

                # Step 3: Check for CAPTCHA/Blocks
                if await self._is_captcha(page):
                    if attempt < max_retries: continue
                    return [], ProviderError(provider=self.provider_name, reason="captcha_blocked", message="Skyscanner blocked our search")

                # Step 4: Extract
                try:
                    await page.wait_for_selector("div[class*='ResultCard_container']", timeout=15000)
                except Exception:
                    return [], None

                flights = await page.query_selector_all("div[class*='ResultCard_container']")
                print(f"[{self.provider_name.upper()}] Found {len(flights)} flight cards")
                
                raw_results = []
                for flight in flights:
                    try:
                        flight_info = {}
                        for key, selector in self.SELECTORS.items():
                            element = await flight.query_selector(selector)
                            flight_info[key] = await element.text_content() if element else "N/A"
                        
                        # Link
                        link_elem = await flight.query_selector("a[class*='ResultCard_link']")
                        if link_elem:
                            flight_info["result_booking_link"] = await link_elem.get_attribute("href")
                        
                        raw_results.append(flight_info)
                    except Exception:
                        continue

                return await self._parse_results(raw_results, params), None

            except Exception as e:
                last_error = e
                if attempt < max_retries: continue
            finally:
                if browser: await browser.close()

        return [], ProviderError(provider=self.provider_name, reason="scrape_error", message=str(last_error))

    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        """Convert raw Skyscanner data into FlightResultSchema."""
        parsed = []
        for raw in raw_results:
            try:
                price_str = raw.get("result_price", "0")
                price = float(re.sub(r"[^\d]", "", price_str) or "0")
                
                if price <= 0:
                    continue
                
                stops_text = raw.get("result_stops", "0").lower()
                stops = 1 if "1 stop" in stops_text else (2 if "2 stop" in stops_text else 0)

                parsed.append(FlightResultSchema(
                    provider=self.provider_name,
                    airline=raw.get("result_airline", "Unknown"),
                    origin=params.origin or "N/A",
                    destination=params.destination or "N/A",
                    departure_time=raw.get("result_departure_time", "N/A"),
                    arrival_time=raw.get("result_arrival_time", "N/A"),
                    duration=raw.get("result_duration", "N/A"),
                    stops=stops,
                    price=price,
                    currency="INR",
                    cabin_class=params.cabin_class.value,
                    scraped_at=datetime.utcnow()
                ))
            except Exception:
                continue
        return parsed


class MakeMyTripScraper(BaseScraper):
    """Scraper for MakeMyTrip (https://www.makemytrip.com)."""

    provider_name = "makemytrip"
    base_url = "https://www.makemytrip.com"

    SELECTORS = {
        "result_price": "div[class*='priceSection'] span[class*='blackText']",
        "result_airline": "p[class*='font14']",
        "result_departure_time": "div[class*='flexOne'] p[class*='appendBottom2']",
        "result_arrival_time": "div[class*='flexOne'] p[class*='appendBottom2']", # Usually in the same group
        "result_duration": "div[class*='stop-info'] p",
        "result_stops": "div[class*='stop-info'] p:last-child",
    }

    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        """Scrape flight results from MakeMyTrip using Direct URL."""
        results, error = await self.scrape_with_retry(params)
        if error:
            raise ProviderException(error)
        return results

    async def scrape_with_retry(
        self,
        params: FlightSearchRequest,
        max_retries: int = None,
    ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
        """Overridden to use Direct URL technique for MakeMyTrip."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries or 2

        last_error = None
        for attempt in range(max_retries + 1):
            browser = None
            context = None
            page = None
            try:
                browser, context, page = await self._launch_browser()
                
                search_url = build_makemytrip_url(params)
                print(f"[{self.provider_name.upper()}] Navigating to: {search_url}")
                
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(10) # MMT is slow

                # Step 4: Extract
                try:
                    await page.wait_for_selector("div[class*='listingCard']", timeout=20000)
                except Exception:
                    return [], None

                flights = await page.query_selector_all("div[class*='listingCard']")
                print(f"[{self.provider_name.upper()}] Found {len(flights)} flight cards")
                
                raw_results = []
                for flight in flights:
                    try:
                        flight_info = {}
                        # MMT has complex structure, let's just grab text from columns
                        cols = await flight.query_selector_all("div[class*='makeFlex']")
                        if len(cols) >= 3:
                            flight_info["result_airline"] = await cols[0].inner_text()
                            flight_info["result_departure_time"] = await cols[1].inner_text()
                            flight_info["result_duration"] = await cols[2].inner_text()
                            
                            price_elem = await flight.query_selector("div[class*='priceSection']")
                            flight_info["result_price"] = await price_elem.inner_text() if price_elem else "0"
                        
                        raw_results.append(flight_info)
                    except Exception:
                        continue

                return await self._parse_results(raw_results, params), None

            except Exception as e:
                last_error = e
                if attempt < max_retries: continue
            finally:
                if browser: await browser.close()

        return [], ProviderError(provider=self.provider_name, reason="scrape_error", message=str(last_error))

    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        parsed = []
        for raw in raw_results:
            try:
                price_str = raw.get("result_price", "0")
                price = float(re.sub(r"[^\d]", "", price_str) or "0")
                
                if price <= 0:
                    continue
                
                parsed.append(FlightResultSchema(
                    provider=self.provider_name,
                    airline=raw.get("result_airline", "Unknown").split("\n")[0],
                    origin=params.origin or "N/A",
                    destination=params.destination or "N/A",
                    departure_time=raw.get("result_departure_time", "N/A"),
                    arrival_time="N/A",
                    duration=raw.get("result_duration", "N/A"),
                    stops=0,
                    price=price,
                    currency="INR",
                    cabin_class=params.cabin_class.value,
                    scraped_at=datetime.utcnow()
                ))
            except Exception:
                continue
        return parsed


class KayakScraper(BaseScraper):
    """Scraper for Kayak (https://www.kayak.co.in)."""

    provider_name = "kayak"
    base_url = "https://www.kayak.co.in"

    # Selectors for Kayak elements
    SELECTORS = {
        "result_price": "div.f8F1-price-text, div.f8F1-price-text-small, .oVHK-fclink",
        "result_airline": "div.J_W7-airline-name, .J_W7, div.codeshares-text",
        "result_departure_time": "span.vmXl:nth-child(1), .vmXl-mod-variant-large:nth-child(1)",
        "result_arrival_time": "span.vmXl:nth-child(3), .vmXl-mod-variant-large:nth-child(3)",
        "result_duration": "div.yuAt-duration, div.xdXm div.vmXw",
        "result_stops": "span.yuAt-stops-text, div.JW_f div.vmXw",
    }

    async def _load_all_flights(self, page: Page) -> None:
        """Scroll down to load more flights on Kayak."""
        for _ in range(3):
            try:
                # Kayak loads results as you scroll or click 'Show more'
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                show_more = await page.query_selector("div.show-more-button")
                if show_more and await show_more.is_visible():
                    await show_more.click()
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                else:
                    break
            except Exception:
                break

    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        """Scrape flight results from Kayak."""
        results, error = await self.scrape_with_retry(params)
        if error:
            raise ProviderException(error)
        return results

    async def scrape_with_retry(
        self,
        params: FlightSearchRequest,
        max_retries: int = None,
    ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
        """Overridden to use Direct URL technique for Kayak."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries or 2

        last_error = None
        for attempt in range(max_retries + 1):
            browser = None
            context = None
            page = None
            try:
                browser, context, page = await self._launch_browser()
                
                # Step 1: Build Direct URL
                search_url = build_kayak_url(params)
                print(f"[{self.provider_name.upper()}] Navigating to: {search_url}")
                
                # Step 2: Navigate directly
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(5.0, 8.0)) # Wait for results to load

                # Step 3: Check for CAPTCHA
                if await self._is_captcha(page):
                    await self._save_screenshot(page, "captcha")
                    if attempt < max_retries:
                        await asyncio.sleep(5)
                        continue
                    return [], ProviderError(
                        provider=self.provider_name,
                        reason="captcha_blocked",
                        message="CAPTCHA detected on Kayak",
                    )

                # Step 4: Load more flights
                await self._load_all_flights(page)

                # Step 5: Extract raw data
                try:
                    await page.wait_for_selector("div.yuAt, div[aria-label^='Result item']", timeout=20000)
                except Exception:
                    await self._save_screenshot(page, "no_results")
                    return [], None

                flights = await page.query_selector_all("div.yuAt, div[aria-label^='Result item']")
                print(f"[{self.provider_name.upper()}] Found {len(flights)} flight cards")
                
                raw_results = []
                for flight in flights:
                    try:
                        flight_info = {}
                        for key, selector in self.SELECTORS.items():
                            content = "N/A"
                            # Try each selector part if it's a comma-separated list
                            for sub_selector in selector.split(", "):
                                element = await flight.query_selector(sub_selector)
                                if element:
                                    text = await element.text_content()
                                    if text:
                                        content = text.strip()
                                        break
                            flight_info[key] = content
                        
                        # Special handling for times if nth-child failed
                        if flight_info.get("result_departure_time") == "N/A":
                            times = await flight.query_selector_all("span.vmXl")
                            if len(times) >= 2:
                                flight_info["result_departure_time"] = (await times[0].text_content()).strip()
                                flight_info["result_arrival_time"] = (await times[1].text_content()).strip()
                        
                        raw_results.append(flight_info)
                    except Exception:
                        continue

                # Step 6: Parse results
                parsed_results = await self._parse_results(raw_results, params)
                return parsed_results, None

            except Exception as e:
                last_error = e
                print(f"[{self.provider_name.upper()}] Attempt {attempt + 1} failed: {str(e)}")
                if page:
                    await self._save_screenshot(page, f"error_attempt_{attempt}")
                
                if attempt < max_retries:
                    await asyncio.sleep(5)
                    continue
            finally:
                if page: await page.close()
                if context: await context.close()
                if browser: await browser.close()

        error_msg = str(last_error) if last_error else "Unknown error"
        return [], ProviderError(
            provider=self.provider_name,
            reason="scrape_error",
            message=f"Kayak scraping failed: {error_msg}",
        )

    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        """Convert raw Kayak data into FlightResultSchema."""
        parsed = []
        for raw in raw_results:
            try:
                # Price extraction
                price_str = raw.get("result_price", "0")
                price_digits = re.sub(r"[^\d]", "", price_str)
                price = float(price_digits or "0")

                if price <= 0:
                    continue

                # Stops extraction
                stops_text = raw.get("result_stops", "0").lower()
                stops = 0
                if any(t in stops_text for t in ("direct", "nonstop", "non-stop")):
                    stops = 0
                else:
                    match = re.search(r"(\d+)\s*stop", stops_text)
                    if match:
                        stops = int(match.group(1))
                    elif "stop" in stops_text:
                        stops = 1

                parsed.append(FlightResultSchema(
                    provider=self.provider_name,
                    airline=raw.get("result_airline", "Unknown"),
                    origin=params.origin or "N/A",
                    destination=params.destination or "N/A",
                    departure_time=raw.get("result_departure_time", "N/A"),
                    arrival_time=raw.get("result_arrival_time", "N/A"),
                    duration=raw.get("result_duration", "N/A"),
                    stops=stops,
                    price=price,
                    currency="INR",
                    cabin_class=params.cabin_class.value,
                    scraped_at=datetime.utcnow()
                ))
            except Exception:
                continue
        return parsed


class GoogleFlightsScraper(BaseScraper):
    """Scraper for Google Flights (https://www.google.com/travel/flights)."""

    provider_name = "google"
    base_url = "https://www.google.com/travel/flights"

    # CSS Selectors for Google Flights elements (Updated 2026)
    SELECTORS = {
        "result_airline": ".sSHq0c, .X9iS9b, div.sSHqwe",
        "result_departure_time": '[aria-label*="Departure time"]',
        "result_arrival_time": '[aria-label*="Arrival time"]',
        "result_duration": '.gv0Sre, .gvO9ec, [aria-label*="Total duration"], [aria-label*="Duration"]',
        "result_stops": ".Ef97Ae, .EfJuyc",
        "result_price": ".YMlS1d, .FpEdX span",
    }

    async def _load_all_flights(self, page: Page) -> None:
        """Click 'Show more flights' button until all flights are loaded (from Guide)"""
        while True:
            try:
                more_button = await page.wait_for_selector(
                    'button[aria-label*="more flights"]', timeout=3000
                )
                if more_button and await more_button.is_visible():
                    await more_button.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                else:
                    break
            except Exception:
                break

    async def scrape_with_retry(
        self,
        params: FlightSearchRequest,
        max_retries: int = None,
    ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
        """Overridden scrape_with_retry to use Direct URL technique."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries or 2

        last_error = None
        for attempt in range(max_retries + 1):
            browser = None
            context = None
            page = None
            try:
                browser, context, page = await self._launch_browser()
                
                # Step 1: Build the Direct URL
                search_url = build_google_flights_url(params)
                print(f"[{self.provider_name.upper()}] Navigating to: {search_url}")
                
                # Step 2: Navigate directly
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(random.uniform(2.0, 4.0))

                # Step 3: Check for CAPTCHA
                if await self._is_captcha(page):
                    await self._save_screenshot(page, "captcha")
                    if attempt < max_retries:
                        await asyncio.sleep(5)
                        continue
                    return [], ProviderError(
                        provider=self.provider_name,
                        reason="captcha_blocked",
                        message="CAPTCHA detected on Google Flights",
                    )

                # Step 4: Load more flights
                await self._load_all_flights(page)

                # Step 5: Extract raw data
                # Identify flight search results (from Guide)
                try:
                    await page.wait_for_selector("li.pIav2d", timeout=20000)
                except Exception:
                    # Fallback or empty results
                    await self._save_screenshot(page, "no_results")
                    return [], None

                flights = await page.query_selector_all("li.pIav2d")
                print(f"[{self.provider_name.upper()}] Found {len(flights)} flight cards")
                
                raw_results = []
                for flight in flights:
                    try:
                        flight_info = {}
                        for key, selector in self.SELECTORS.items():
                            content = "N/A"
                            # Try each sub-selector in comma-separated list
                            for sub_selector in selector.split(", "):
                                element = await flight.query_selector(sub_selector)
                                if element:
                                    # Try text content first
                                    text = await element.text_content()
                                    if text and text.strip():
                                        content = text.strip()
                                        break
                                    # Fallback to aria-label for items like time/duration
                                    aria = await element.get_attribute("aria-label")
                                    if aria:
                                        # Clean up common aria prefixes
                                        content = aria.replace("Total duration ", "").replace("Departure time ", "").replace("Arrival time ", "").strip()
                                        break
                            flight_info[key] = content
                        
                        raw_results.append(flight_info)
                    except Exception:
                        continue

                # Step 6: Parse results
                parsed_results = await self._parse_results(raw_results, params)
                return parsed_results, None

            except Exception as e:
                last_error = e
                print(f"[{self.provider_name.upper()}] Attempt {attempt + 1} failed: {str(e)}")
                if page:
                    await self._save_screenshot(page, f"error_attempt_{attempt}")
                
                if attempt < max_retries:
                    await asyncio.sleep(3)
                    continue
            finally:
                if page: await page.close()
                if context: await context.close()
                if browser: await browser.close()

        error_msg = str(last_error) if last_error else "Unknown error"
        return [], ProviderError(
            provider=self.provider_name,
            reason="scrape_error",
            message=f"Google Flights scraping failed after retries: {error_msg}",
        )

    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        """Convert raw Google Flights extraction to schema objects."""
        parsed = []
        for raw in raw_results:
            try:
                # Price cleaning
                price_str = raw.get("result_price", "0")
                # Remove symbols like ₹, $, commas
                price_digits = re.sub(r"[^\d.]", "", price_str)
                price = float(price_digits or "0")

                if price <= 0:
                    continue

                # Stops extraction (from Guide: '1 stop in DXB')
                stops_text = raw.get("result_stops", "0").lower()
                stops = 0
                if any(t in stops_text for t in ("nonstop", "direct", "0 stop")):
                    stops = 0
                else:
                    match = re.search(r"(\d+)\s*stop", stops_text)
                    if match:
                        stops = int(match.group(1))
                    elif "stop" in stops_text:
                        stops = 1

                parsed.append(FlightResultSchema(
                    provider=self.provider_name,
                    airline=raw.get("result_airline", "Unknown"),
                    origin=params.origin or "N/A",
                    destination=params.destination or "N/A",
                    departure_time=raw.get("result_departure_time", "N/A"),
                    arrival_time=raw.get("result_arrival_time", "N/A"),
                    duration=raw.get("result_duration", "N/A"),
                    stops=stops,
                    price=price,
                    currency="INR",
                    cabin_class=params.cabin_class.value,
                    scraped_at=datetime.utcnow()
                ))
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        return parsed
    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        """Main entry point for the scraper."""
        results, error = await self.scrape_with_retry(params)
        if error:
            raise ProviderException(error)
        return results


class ScraperEngine:
    """Engine that orchestrates multi-provider scraping concurrently."""

    # Registry of available scrapers
    SCRAPER_REGISTRY = {
        "skyscanner": SkyscannerScraper,
        "makemytrip": MakeMyTripScraper,
        "kayak": KayakScraper,
        "google": GoogleFlightsScraper,
    }

    def __init__(self, provider_names: list[str]):
        """Initialize engine with list of provider names to scrape."""
        self.provider_names = provider_names
        self.scrapers = self._instantiate_scrapers()

    def _instantiate_scrapers(self) -> list[BaseScraper]:
        """Instantiate scraper instances for each requested provider."""
        scrapers = []
        for provider_name in self.provider_names:
            scraper_class = self.SCRAPER_REGISTRY.get(provider_name.lower())
            if scraper_class:
                scrapers.append(scraper_class())
        return scrapers

    async def scrape_all(
        self,
        params: FlightSearchRequest,
        timeout_seconds: int = 90,
    ) -> tuple[list[FlightResultSchema], list[ProviderError]]:
        """
        Scrape all providers concurrently.

        Returns:
            tuple: (list of FlightResultSchema, list of ProviderError)
        """
        all_results: list[FlightResultSchema] = []
        all_errors: list[ProviderError] = []

        async def scrape_with_timeout(
            scraper: BaseScraper,
        ) -> tuple[list[FlightResultSchema], Optional[ProviderError]]:
            """Scrape a single provider with timeout."""
            try:
                results = await asyncio.wait_for(
                    scraper.scrape(params),
                    timeout=timeout_seconds,
                )
                return results, None
            except asyncio.TimeoutError:
                return [], ProviderError(
                    provider=scraper.provider_name,
                    reason="timeout",
                    message=f"Scraping timed out after {timeout_seconds} seconds",
                )
            except ProviderException as e:
                return [], e.error
            except Exception as e:
                return [], ProviderError(
                    provider=scraper.provider_name,
                    reason="scrape_error",
                    message=str(e),
                )

        # Run all scrapers concurrently
        tasks = [scrape_with_timeout(scraper) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Collect results and errors
        for result in results:
            flight_results, error = result
            all_results.extend(flight_results)
            if error:
                all_errors.append(error)

        return all_results, all_errors

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls.SCRAPER_REGISTRY.keys())
