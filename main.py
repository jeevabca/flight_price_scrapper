import asyncio
import subprocess
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import init_db, async_session_maker
from app.models.provider_xpath import ProviderXPath
from app.services.xpath_service import XPathService
from app.schemas.xpath import XPathCreate

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Required XPath fields for each provider
REQUIRED_XPATH_FIELDS = [
    ("search_origin_input", "Origin input field", None),
    ("search_destination_input", "Destination input field", None),
    ("search_date_outbound", "Outbound date picker", None),
    ("search_date_return", "Return date picker", None),
    ("search_passengers_input", "Passengers selector", None),
    ("search_submit_button", "Search submit button", None),
    ("results_flight_card", "Flight result card container", None),
    ("result_price", "Flight price element", None),
    ("result_airline", "Airline name element", None),
    ("result_flight_number", "Flight number element", None),
    ("result_departure_time", "Departure time element", None),
    ("result_arrival_time", "Arrival time element", None),
    ("result_duration", "Flight duration element", None),
    ("result_stops", "Number of stops element", None),
    ("result_booking_link", "Booking link/button", None),
]

# Default XPath placeholders for initial seed
DEFAULT_XPATHS = {
    "skyscanner": {
        "search_origin_input": ("//input[@id='origin-input']", "//input[id='origin-input']", "Origin airport input"),
        "search_destination_input": ("//input[@id='destination-input']", "//input[id='destination-input']", "Destination airport input"),
        "search_date_outbound": ("//input[@id='outbound-date']", "//input[id='outbound-date']", "Outbound date picker"),
        "search_date_return": ("//input[@id='return-date']", "//input[id='return-date']", "Return date picker"),
        "search_passengers_input": ("//button[@id='travellers-select']", "//button[id='travellers-select']", "Passengers dropdown"),
        "search_submit_button": ("//button[@id='search-button']", "//button[id='search-button']", "Search flights button"),
        "results_flight_card": ("//div[@data-testid='flight-card']", "//div[data-testid='flight-card']", "Flight result card"),
        "result_price": ("//span[@data-testid='price']", "//span[data-testid='price']", "Flight price"),
        "result_airline": ("//span[@data-testid='airline-name']", "//span[data-testid='airline-name']", "Airline name"),
        "result_flight_number": ("//span[@data-testid='flight-number']", "//span[data-testid='flight-number']", "Flight number"),
        "result_departure_time": ("//span[@data-testid='departure-time']", "//span[data-testid='departure-time']", "Departure time"),
        "result_arrival_time": ("//span[@data-testid='arrival-time']", "//span[data-testid='arrival-time']", "Arrival time"),
        "result_duration": ("//span[@data-testid='duration']", "//span[data-testid='duration']", "Flight duration"),
        "result_stops": ("//span[@data-testid='stops']", "//span[data-testid='stops']", "Number of stops"),
        "result_booking_link": ("//a[@data-testid='select-flight']", "//a[data-testid='select-flight']", "Select flight button"),
    },
    "makemytrip": {
        "search_origin_input": ("//input[@id='fromCity']", "//input[id='fromCity']", "Origin city input"),
        "search_destination_input": ("//input[@id='toCity']", "//input[id='toCity']", "Destination city input"),
        "search_date_outbound": ("//input[@id='departureCalendar']", "//input[id='departureCalendar']", "Departure date picker"),
        "search_date_return": ("//input[@id='returnCalendar']", "//input[id='returnCalendar']", "Return date picker"),
        "search_passengers_input": ("//div[@id='traveller-modal']", "//div[id='traveller-modal']", "Traveller selection"),
        "search_submit_button": ("//button[@id='searchButton']", "//button[id='searchButton']", "Search flights button"),
        "results_flight_card": ("//li[@data-cy='flightCard']", "//li[data-cy='flightCard']", "Flight card"),
        "result_price": ("//span[@data-cy='flightPrice']", "//span[data-cy='flightPrice']", "Flight price"),
        "result_airline": ("//div[@data-cy='airline-name']", "//div[data-cy='airline-name']", "Airline name"),
        "result_flight_number": ("//div[@data-cy='flight-number']", "//div[data-cy='flight-number']", "Flight number"),
        "result_departure_time": ("//div[@data-cy='departure-time']", "//div[data-cy='departure-time']", "Departure time"),
        "result_arrival_time": ("//div[@data-cy='arrival-time']", "//div[data-cy='arrival-time']", "Arrival time"),
        "result_duration": ("//div[@data-cy='duration']", "//div[data-cy='duration']", "Flight duration"),
        "result_stops": ("//div[@data-cy='stops']", "//div[data-cy='stops']", "Number of stops"),
        "result_booking_link": ("//button[@data-cy='view-flights']", "//button[data-cy='view-flights']", "View flights button"),
    },
    "kayak": {
        "search_origin_input": ("//input[@id='origin-input']", "//input[id='origin-input']", "Origin airport input"),
        "search_destination_input": ("//input[@id='destination-input']", "//input[id='destination-input']", "Destination airport input"),
        "search_date_outbound": ("//input[@id='date-picker-start']", "//input[id='date-picker-start']", "Start date picker"),
        "search_date_return": ("//input[@id='date-picker-end']", "//input[id='date-picker-end']", "End date picker"),
        "search_passengers_input": ("//button[@id='passengers']", "//button[id='passengers']", "Passengers dropdown"),
        "search_submit_button": ("//button[@id='submit']", "//button[id='submit']", "Search flights button"),
        "results_flight_card": ("//div[@data-testid='flight-result']", "//div[data-testid='flight-result']", "Flight result"),
        "result_price": ("//span[@data-testid='price']", "//span[data-testid='price']", "Flight price"),
        "result_airline": ("//span[@data-testid='airline']", "//span[data-testid='airline']", "Airline name"),
        "result_flight_number": ("//span[@data-testid='flight-num']", "//span[data-testid='flight-num']", "Flight number"),
        "result_departure_time": ("//span[@data-testid='depart-time']", "//span[data-testid='depart-time']", "Departure time"),
        "result_arrival_time": ("//span[@data-testid='arrive-time']", "//span[data-testid='arrive-time']", "Arrival time"),
        "result_duration": ("//span[@data-testid='duration']", "//span[data-testid='duration']", "Flight duration"),
        "result_stops": ("//span[@data-testid='stops']", "//span[data-testid='stops']", "Number of stops"),
        "result_booking_link": ("//a[@data-testid='deal-button']", "//a[data-testid='deal-button']", "Deal button"),
    },
    "google": {
        "search_origin_input": (
            "//input[@aria-label='Where from?' or @aria-label='From' or @placeholder='Where from?']",
            "input[aria-label='Where from?'], input[aria-label='From'], input[placeholder='Where from?']",
            "Origin airport input",
        ),
        "search_destination_input": (
            "//input[@aria-label='Where to?' or @aria-label='To' or @placeholder='Where to?']",
            "input[aria-label='Where to?'], input[aria-label='To'], input[placeholder='Where to?']",
            "Destination airport input",
        ),
        "search_date_outbound": (
            "//input[@aria-label='Departure' or @placeholder='Departure']",
            "input[aria-label='Departure'], input[placeholder='Departure']",
            "Start date picker",
        ),
        "search_date_return": (
            "//input[@aria-label='Return' or @placeholder='Return']",
            "input[aria-label='Return'], input[placeholder='Return']",
            "End date picker",
        ),
        "search_passengers_input": ("//div[contains(@class, 'passengers')]", "div.passengers", "Passengers dropdown"),
        "search_submit_button": (
            "//button[@aria-label='Search' or contains(@aria-label,'Search')]",
            "button[aria-label='Search'], button[aria-label*='Search']",
            "Search flights button",
        ),
        "results_flight_card": ("//div[@role='listitem']", "div[role='listitem']", "Flight result"),
        "result_price": ("//span[contains(@class, 'Price')]", "span.Price", "Flight price"),
        "result_airline": ("//span[contains(@class, 'Airline')]", "span.Airline", "Airline name"),
        "result_flight_number": ("//span[contains(@class, 'Flight')]", "span.Flight", "Flight number"),
        "result_departure_time": ("//span[contains(@class, 'Departure')]", "span.Departure", "Departure time"),
        "result_arrival_time": ("//span[contains(@class, 'Arrival')]", "span.Arrival", "Arrival time"),
        "result_duration": ("//div[contains(@class, 'Duration')]", "div.Duration", "Flight duration"),
        "result_stops": ("//span[contains(@class, 'Stops')]", "span.Stops", "Number of stops"),
        "result_booking_link": ("//a[contains(@href, '/flights')]", "a[href*='/flights']", "Deal button"),
    },
}


async def seed_xpaths():
    """Seed default XPath configurations if table is empty."""
    from sqlalchemy import select

    async with async_session_maker() as db:
        # Check if table is empty
        result = await db.execute(select(ProviderXPath))
        existing = result.scalars().all()

        if existing:
            logger.info("XPath table already has entries, skipping seed")
            return

        logger.info("Seeding default XPath configurations...")

        for provider_name, fields in DEFAULT_XPATHS.items():
            for field_name, (xpath, css_selector, description) in fields.items():
                xpath_entry = ProviderXPath(
                    provider_name=provider_name,
                    field_name=field_name,
                    xpath=xpath,
                    css_selector=css_selector,
                    description=description,
                    is_active=True,
                )
                db.add(xpath_entry)

        await db.commit()
        logger.info(f"Seeded XPaths for {len(DEFAULT_XPATHS)} providers")


async def ensure_playwright_installed():
    """Ensure Playwright Chromium is installed."""
    try:
        # Check if chromium is installed
        result = subprocess.run(
            ["playwright", "is-installed", "chromium"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.info("Installing Playwright Chromium...")
            subprocess.run(
                ["playwright", "install", "chromium"],
                check=True,
            )
            logger.info("Playwright Chromium installed successfully")
        else:
            logger.info("Playwright Chromium already installed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Playwright Chromium: {e}")
    except FileNotFoundError:
        logger.warning("Playwright not found. Run: playwright install chromium")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting up Flight Scraper API...")

    # Run migrations
    logger.info("Running database migrations...")
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Database migrations completed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        raise

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    # Seed XPaths
    await seed_xpaths()

    # Ensure Playwright is installed
    await ensure_playwright_installed()

    logger.info("Flight Scraper API ready!")

    yield

    # Shutdown
    logger.info("Shutting down Flight Scraper API...")


# Create FastAPI app
app = FastAPI(
    title="Flight Scraper API",
    description="Multi-provider flight price scraping API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration_ms}ms")
    return response


# Mount static files
ui_dir = Path(__file__).parent / "ui"
app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")


# Serve UI at root
@app.get("/")
async def serve_ui():
    """Serve the main UI page."""
    return FileResponse(ui_dir / "index.html")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "db": "connected"}


# Include routers
from app.api import flights, xpaths

app.include_router(flights.router)
app.include_router(xpaths.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
