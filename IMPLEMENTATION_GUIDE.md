# Google Flights Scraper - Implementation Guide

A step-by-step guide to building your own Google Flights scraper using Python and Playwright.

---

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Basic understanding of async Python

---

## Step 1: Project Setup

### Create Project Directory

```bash
mkdir google-flights-scraper
cd google-flights-scraper
```

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

### Install Dependencies

```bash
pip install playwright tenacity
playwright install chromium
```

### Project Structure

```
google-flights-scraper/
├── scraper.py              # Main scraper code
├── requirements.txt        # Dependencies
├── output/                 # JSON output directory
└── README.md              # Project documentation
```

---

## Step 2: Create Requirements File

Create `requirements.txt`:

```txt
playwright>=1.40.0
tenacity>=8.2.0
```

---

## Step 3: Build the Scraper

Create `scraper.py` with the following implementation:

### 3.1 Imports and Data Class

```python
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_fixed
from dataclasses import dataclass
from typing import List
import asyncio
import json
import re


@dataclass
class FlightData:
    """Data class to store individual flight information"""
    
    airline: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: str
    price: str
    co2_emissions: str
    emissions_variation: str
```

### 3.2 Scraper Class with Selectors

```python
class FlightScraper:
    """Class to handle Google Flights scraping operations"""
    
    # CSS Selectors for Google Flights elements
    SELECTORS = {
        "airline": "div.sSHqwe.tPgKwe.ogfYpf",
        "departure_time": 'span[aria-label^="Departure time"]',
        "arrival_time": 'span[aria-label^="Arrival time"]',
        "duration": 'div[aria-label^="Total duration"]',
        "stops": "div.hF6lYb span.rGRiKd",
        "price": "div.FpEdX span",
        "co2_emissions": "div.O7CXue",
        "emissions_variation": "div.N6PNV",
    }
```

### 3.3 Helper Methods

```python
    async def _extract_text(self, element) -> str:
        """Extract text content from a page element safely"""
        return (await element.text_content()).strip() if element else "N/A"

    async def _load_all_flights(self, page) -> None:
        """Click 'Show more flights' button until all flights are loaded"""
        while True:
            try:
                more_button = await page.wait_for_selector(
                    'button[aria-label*="more flights"]', timeout=5000
                )
                if more_button:
                    await more_button.click()
                    await page.wait_for_timeout(2000)  # Wait for new content
                else:
                    break
            except:
                break  # No more button or timeout
```

### 3.4 Flight Data Extraction

```python
    async def _extract_flight_data(self, page) -> List[FlightData]:
        """Extract flight information from search results"""
        try:
            # Wait for flight results to load
            await page.wait_for_selector("li.pIav2d", timeout=30000)
            
            # Load all available flights
            await self._load_all_flights(page)
            
            # Get all flight elements
            flights = await page.query_selector_all("li.pIav2d")
            
            # Extract data from each flight
            flights_data = []
            for flight in flights:
                flight_info = {}
                for key, selector in self.SELECTORS.items():
                    element = await flight.query_selector(selector)
                    flight_info[key] = await self._extract_text(element)
                flights_data.append(FlightData(**flight_info))
            
            return flights_data
            
        except Exception as e:
            raise Exception(f"Failed to extract flight data: {str(e)}")
```

### 3.5 URL Parsing

```python
    def _extract_trip_info_from_url(self, url: str) -> dict:
        """Extract trip information from Google Flights URL"""
        trip_info = {}
        
        # Extract airport codes (e.g., DEL, SFO)
        airport_match = re.search(r"[?&]tfs=.*?([A-Z]{3}).*?([A-Z]{3})", url)
        if airport_match:
            trip_info["origin"] = airport_match.group(1)
            trip_info["destination"] = airport_match.group(2)
        
        # Extract date (YYYY-MM-DD format)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", url)
        if date_match:
            trip_info["date"] = date_match.group(1)
        
        return trip_info
```

### 3.6 Save Results

```python
    def save_results(self, flights: List[FlightData], url: str) -> str:
        """Save flight search results to a JSON file"""
        output_data = {
            "search_url": url,
            "flights": [vars(flight) for flight in flights],
        }
        
        filepath = "output/flight_results.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return filepath
```

### 3.7 Main Search Function with Retry

```python
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def search_flights(self, url: str) -> List[FlightData]:
        """Execute the flight search with retry capability"""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Navigate to Google Flights
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("networkidle")
                
                # Extract flight data
                flights = await self._extract_flight_data(page)
                
                # Save results
                filepath = self.save_results(flights, url)
                print(f"Results saved to: {filepath}")
                
                return flights
                
            finally:
                await browser.close()
```

### 3.8 Main Entry Point

```python
async def main():
    """Main function to demonstrate usage"""
    scraper = FlightScraper()
    
    # Example URL: Delhi to San Francisco on April 1, 2025
    url = "https://www.google.com/travel/flights/search?tfs=CBwQAhoeEgoyMDI1LTA0LTAxagcIARIDREVMcgcIARIDU0ZPQAFIAXABggELCP___________wGYAQI&curr=USD"
    
    try:
        flights = await scraper.search_flights(url)
        print(f"Successfully found {len(flights)} flights")
        
        # Print first 3 flights
        for flight in flights[:3]:
            print(f"\n{flight.airline}: {flight.price}")
            print(f"  {flight.departure_time} - {flight.arrival_time}")
            print(f"  {flight.stops}")
            
    except Exception as e:
        print(f"Error during flight search: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 4: How to Get Google Flights URLs

### Method 1: Manual Search

1. Go to [Google Flights](https://www.google.com/travel/flights)
2. Enter your search criteria (origin, destination, date)
3. Copy the URL from the address bar

### Method 2: URL Structure

Google Flights URLs follow this pattern:

```
https://www.google.com/travel/flights/search?tfs=<ENCODED_PARAMS>&curr=<CURRENCY>
```

The `tfs` parameter contains:
- Origin airport code
- Destination airport code  
- Travel date
- Trip type (one-way, round-trip)

### Common Airport Codes

| Code | Airport |
|------|---------|
| DEL | Delhi, India |
| SFO | San Francisco, USA |
| JFK | New York, USA |
| LHR | London, UK |
| DXB | Dubai, UAE |
| ICN | Seoul, South Korea |

---

## Step 5: Running the Scraper

### Basic Execution

```bash
python scraper.py
```

### Expected Output

```
Results saved to: output/flight_results.json
Successfully found 15 flights

American: $732
  11:30 PM - 11:43 AM+1
  1 stop in JFK

Korean Air: $810
  6:50 PM - 10:40 AM+1
  1 stop in ICN

Emirates: $1,139
  4:15 AM - 2:00 PM
  1 stop in DXB
```

---

## Step 6: Understanding the Output

### JSON Structure

```json
{
  "search_url": "https://www.google.com/...",
  "flights": [
    {
      "airline": "Emirates",
      "departure_time": "4:15 AM",
      "arrival_time": "2:00 PM",
      "duration": "22 hr 15 min",
      "stops": "1 stop in DXB",
      "price": "$1,139",
      "co2_emissions": "1,092 kg CO2e",
      "emissions_variation": "+6% emissions"
    }
  ]
}
```

### Field Descriptions

| Field | Description |
|-------|-------------|
| `airline` | Airline name(s) for the flight |
| `departure_time` | Local departure time |
| `arrival_time` | Local arrival time (+1/+2 for next days) |
| `duration` | Total flight duration |
| `stops` | Number and location of layovers |
| `price` | Ticket price in specified currency |
| `co2_emissions` | Estimated carbon emissions |
| `emissions_variation` | Comparison to average emissions |

---

## Step 7: Customization Options

### 7.1 Headless Mode

Change browser visibility in `search_flights()`:

```python
# Visible browser (less likely to be detected)
browser = await p.chromium.launch(headless=False)

# Hidden browser (faster, more detectable)
browser = await p.chromium.launch(headless=True)
```

### 7.2 User Agent

Update the User-Agent string to mimic different browsers:

```python
# Chrome on Windows
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

# Firefox on macOS
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0"
```

### 7.3 Retry Configuration

Adjust retry behavior:

```python
@retry(
    stop=stop_after_attempt(5),      # 5 attempts instead of 3
    wait=wait_fixed(10)              # 10 seconds between attempts
)
async def search_flights(self, url: str):
    ...
```

### 7.4 Add Delay Between Requests

To reduce detection risk:

```python
import random

async def search_flights(self, url: str):
    # Random delay before request
    await asyncio.sleep(random.uniform(2, 5))
    ...
```

---

## Step 8: Error Handling

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `TimeoutError` | Page took too long to load | Increase timeout in `page.goto()` |
| `ElementNotFound` | Selectors changed | Update CSS selectors |
| Empty results | No flights match criteria | Verify URL parameters |
| CAPTCHA | Detection by Google | Use `headless=False`, add delays |
| IP Block | Too many requests | Wait longer between requests |

### Adding Custom Error Handling

```python
try:
    flights = await scraper.search_flights(url)
except Exception as e:
    print(f"Scraping failed: {e}")
    # Log error, send notification, etc.
```

---

## Step 9: Best Practices

### Do's

- Use `headless=False` for production to reduce detection
- Add random delays between requests
- Respect Google's terms of service
- Handle errors gracefully
- Log scraping attempts for debugging

### Don'ts

- Don't scrape at high frequency
- Don't use for commercial purposes without authorization
- Don't ignore CAPTCHAs or blocks
- Don't hardcode selectors without fallback handling

---

## Step 10: Testing Your Implementation

### Test with Known URL

```python
async def test_scraper():
    scraper = FlightScraper()
    
    # Test URL with expected results
    test_url = "https://www.google.com/travel/flights/search?tfs=..."
    
    flights = await scraper.search_flights(test_url)
    
    assert len(flights) > 0, "No flights found"
    assert flights[0].airline != "N/A", "Airline extraction failed"
    assert "$" in flights[0].price, "Price extraction failed"
    
    print("All tests passed!")
```

---

## Complete Code

The complete implementation is available in `scraper.py`. Copy the code from all sections above into a single file, or reference the original `google-flights-scraper/google-flights-scraper.py` in this repository.

---

## Troubleshooting

### "playwright not found"

```bash
pip install playwright
playwright install chromium
```

### "No module named 'tenacity'"

```bash
pip install tenacity
```

### Selectors Not Working

Google frequently updates their HTML structure. If selectors fail:

1. Open the URL in Chrome
2. Right-click an element → Inspect
3. Find the new selector
4. Update the `SELECTORS` dictionary

### Browser Opens But No Results

- Check if the URL is valid
- Ensure you're not blocked by Google
- Try increasing the timeout value
- Check if manual search works in the same browser

---

## Next Steps

1. **Add More Data Points**: Extract additional flight details
2. **Multiple URLs**: Scrape multiple search queries in sequence
3. **Database Storage**: Save results to SQLite/PostgreSQL
4. **API Endpoint**: Wrap in FastAPI for HTTP access
5. **Scheduled Runs**: Use cron or GitHub Actions for periodic scraping

---

## License & Disclaimer

This implementation is for educational purposes. Always:
- Review Google's Terms of Service
- Respect rate limits
- Use responsibly and ethically
- Consider using official APIs for production use
