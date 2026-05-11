# Flight Scraper API

A complete flight price scraping API built with Python, FastAPI, and Playwright. Scrapes multiple flight providers concurrently and returns unified results with caching support.

## Features

- **Multi-provider scraping**: Scrape Skyscanner, MakeMyTrip, Kayak simultaneously
- **Concurrent execution**: Uses asyncio for parallel provider scraping
- **TTL caching**: 30-minute cache to reduce redundant scraping
- **XPath management**: Configure and update XPaths via API without redeploying
- **Anti-detection**: Stealth browser, rotating user agents, randomized viewports
- **Audit logging**: All searches logged for debugging and analytics
- **Single-file UI**: Complete web interface served from one HTML file

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| Scraping | Playwright (Python) + Chromium |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite (dev) / PostgreSQL (prod-ready) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Anti-detection | playwright-stealth |

## Setup & Installation

### Prerequisites

- Python 3.10+
- pip

### Installation Steps

```bash
# Navigate to project directory
cd flight_scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Copy environment file
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./flight_scraper.db` | Database connection string |
| `HEADLESS` | `true` | Run browser in headless mode |
| `CACHE_TTL_MINUTES` | `30` | Cache expiration time |
| `SCRAPER_TIMEOUT_SECONDS` | `60` | Timeout per provider |
| `SCRAPER_MAX_RETRIES` | `2` | Max retry attempts |
| `DEBUG_SCREENSHOTS_DIR` | `./debug_screenshots` | Screenshot save location |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access the UI at: http://localhost:8000

## API Reference

### Health Check

```bash
GET /health
```

```json
{"status": "ok", "db": "connected"}
```

### Search Flights

```bash
POST /api/flights/search
Content-Type: application/json
```

**Request Body (One-way):**
```json
{
  "providers": ["skyscanner", "makemytrip"],
  "trip_type": "oneway",
  "origin": "MAA",
  "destination": "DEL",
  "outbound_date": "2025-08-10",
  "passengers": 1,
  "cabin_class": "economy"
}
```

**Request Body (Return):**
```json
{
  "providers": ["skyscanner"],
  "trip_type": "return",
  "origin": "DEL",
  "destination": "BOM",
  "outbound_date": "2025-08-10",
  "return_date": "2025-08-17",
  "passengers": 2,
  "cabin_class": "business"
}
```

**Request Body (Multi-city):**
```json
{
  "providers": ["skyscanner", "kayak"],
  "trip_type": "multicity",
  "multi_city_legs": [
    {"origin": "MAA", "destination": "DEL", "date": "2025-08-10"},
    {"origin": "DEL", "destination": "BOM", "date": "2025-08-15"}
  ],
  "passengers": 1,
  "cabin_class": "economy"
}
```

**Response:**
```json
{
  "search_id": "uuid-v4",
  "searched_at": "2025-06-01T10:00:00Z",
  "cached": false,
  "params": {...},
  "results": [
    {
      "provider": "skyscanner",
      "airline": "IndiGo",
      "flight_number": "6E-201",
      "origin": "MAA",
      "destination": "DEL",
      "departure_time": "06:00",
      "arrival_time": "08:30",
      "duration": "2h 30m",
      "stops": 0,
      "price": 4599.0,
      "currency": "INR",
      "cabin_class": "economy",
      "booking_link": "https://...",
      "scraped_at": "2025-06-01T10:00:05Z"
    }
  ],
  "errors": [],
  "total_results": 1,
  "total_errors": 0,
  "duration_ms": 12500
}
```

### Get Providers

```bash
GET /api/flights/providers
```

```json
[
  {
    "name": "skyscanner",
    "is_active": true,
    "active_field_count": 15,
    "required_field_count": 15,
    "is_ready": true
  }
]
```

### XPath CRUD Endpoints

**List all XPaths:**
```bash
GET /api/xpaths
GET /api/xpaths?provider=skyscanner
```

**Get provider XPaths:**
```bash
GET /api/xpaths/{provider}
```

**Create XPath:**
```bash
POST /api/xpaths
Content-Type: application/json

{
  "provider_name": "skyscanner",
  "field_name": "result_price",
  "xpath": "//span[@data-testid='price']",
  "css_selector": null,
  "description": "Flight price element",
  "is_active": true
}
```

**Update XPath:**
```bash
PUT /api/xpaths/{id}
Content-Type: application/json

{
  "xpath": "//span[@data-testid='new-price']",
  "is_active": true
}
```

**Delete XPath (soft):**
```bash
DELETE /api/xpaths/{id}
```

**Bulk Upsert:**
```bash
POST /api/xpaths/bulk
Content-Type: application/json

{
  "entries": [
    {
      "provider_name": "skyscanner",
      "field_name": "result_price",
      "xpath": "//span[@price]",
      "is_active": true
    }
  ]
}
```

## How to Add a New Provider

### Step 1: Create Scraper Class

Add a new scraper in `app/scrapers/engine.py`:

```python
class NewProviderScraper(BaseScraper):
    provider_name = "newprovider"
    base_url = "https://www.newprovider.com"

    async def scrape(self, params: FlightSearchRequest) -> list[FlightResultSchema]:
        results, error = await self.scrape_with_retry(params)
        if error:
            raise error
        return results

    async def _parse_results(
        self,
        raw_results: list[dict],
        params: FlightSearchRequest,
    ) -> list[FlightResultSchema]:
        parsed = []
        for raw in raw_results:
            # Parse provider-specific HTML structure
            result = FlightResultSchema(
                provider=self.provider_name,
                airline=raw.get("result_airline", "Unknown"),
                # ... map other fields
            )
            parsed.append(result)
        return parsed
```

### Step 2: Register Scraper

Add to `SCRAPER_REGISTRY` in `ScraperEngine`:

```python
SCRAPER_REGISTRY = {
    "skyscanner": SkyscannerScraper,
    "makemytrip": MakeMyTripScraper,
    "kayak": KayakScraper,
    "newprovider": NewProviderScraper,  # Add here
}
```

### Step 3: Add XPath Configuration

Add default XPaths in `main.py`:

```python
DEFAULT_XPATHS = {
    ...
    "newprovider": {
        "search_origin_input": ("//input[@id='from']", None, "Origin input"),
        # ... add all 15 fields
    },
}
```

### Step 4: Restart and Configure

1. Restart the server
2. Go to XPath Manager tab
3. Select "newprovider" from dropdown
4. Update XPaths to match actual site structure

## How to Update XPaths Without Redeploying

XPaths are stored in the database and can be updated at runtime:

### Via UI (Recommended)

1. Go to **XPath Manager** tab
2. Select provider from dropdown
3. Click on any cell to edit XPath/CSS/Description
4. Click **Save** for individual updates or **Bulk Save** for all changes

### Via API

```bash
# Update single XPath
curl -X PUT http://localhost:8000/api/xpaths/{id} \
  -H "Content-Type: application/json" \
  -d '{"xpath": "//new/xpath/here"}'

# Bulk update
curl -X POST http://localhost:8000/api/xpaths/bulk \
  -H "Content-Type: application/json" \
  -d '{"entries": [...]}'
```

### Via Database

```bash
# Direct SQLite update
sqlite3 flight_scraper.db "UPDATE provider_xpaths SET xpath='//new/xpath' WHERE id='...';"
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  GET /           → Serve UI (index.html)                    │
│  GET /health     → Health check                             │
│  POST /api/flights/search → Flight search endpoint          │
│  GET  /api/flights/providers → List providers               │
│  CRUD /api/xpaths          → XPath management               │
├─────────────────────────────────────────────────────────────┤
│  ScraperEngine                                                │
│  ├─ asyncio.gather() for concurrent scraping                │
│  ├─ SkyscannerScraper (BaseScraper)                         │
│  ├─ MakeMyTripScraper (BaseScraper)                         │
│  └─ KayakScraper (BaseScraper)                              │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                                │
│  ├─ FlightService: Cache check, save results, log searches  │
│  └─ XPathService: DB CRUD for XPath configs                 │
├─────────────────────────────────────────────────────────────┤
│  Database (SQLite/PostgreSQL)                                 │
│  ├─ provider_xpaths: XPath configurations                   │
│  ├─ flight_results: Cached scrape results (TTL 30min)       │
│  └─ search_logs: Audit trail                                │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Cache Check**: Before scraping, check `flight_results` for valid cached data
2. **Dispatch**: If cache miss, `ScraperEngine` launches concurrent scrapers
3. **Scrape**: Each provider:
   - Launches headless Chromium with stealth
   - Fills search form using DB-loaded XPaths
   - Waits for results
   - Extracts and parses data
4. **Aggregate**: Results from all providers merged into unified response
5. **Cache**: Fresh results saved with 30-minute TTL
6. **Log**: Search logged to `search_logs` table

## Troubleshooting

### CAPTCHA Detected

**Symptoms:** Response contains `{"reason": "captcha_blocked"}`

**Solutions:**
1. Check debug screenshots in `./debug_screenshots/`
2. Increase delay between interactions in `base_scraper.py`
3. Rotate user agents (already implemented)
4. Consider adding cookie persistence
5. Use residential proxies for production

### Timeout Errors

**Symptoms:** `{"reason": "timeout"}`

**Solutions:**
1. Increase `SCRAPER_TIMEOUT_SECONDS` in `.env`
2. Check if website structure changed (update XPaths)
3. Verify `results_flight_card` XPath is correct
4. Enable debug logging: `LOG_LEVEL=DEBUG`

### No Results Returned

**Symptoms:** Empty `results` array, no errors

**Solutions:**
1. Verify XPaths match current site structure
2. Check browser console in UI for network errors
3. Run with `HEADLESS=false` to visually debug
4. Inspect debug screenshots for page state

### Database Migration Errors

**Symptoms:** App fails to start, migration errors

**Solutions:**
```bash
# Reset migrations (dev only!)
rm flight_scraper.db
rm alembic/versions/*.py
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

### Playwright Installation Issues

**Symptoms:** "Browser not found" errors

**Solutions:**
```bash
# Reinstall Playwright browsers
playwright install chromium
playwright install-deps chromium  # Linux only
```

### Debug Screenshots

When scrapers fail, screenshots are saved to `./debug_screenshots/` with naming pattern:
- `{provider}_{timestamp}_error.png` - General errors
- `{provider}_{timestamp}_captcha.png` - CAPTCHA detection

Review these to understand page state at failure time.

## License

MIT License
