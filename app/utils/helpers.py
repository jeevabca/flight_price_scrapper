import re
from datetime import datetime
from typing import Optional


# Valid IATA airport codes (subset of major airports)
VALID_IATA_CODES = {
    # India
    "DEL", "BOM", "MAA", "BLR", "HYD", "CCU", "AMD", "COK", "GOI", "PNQ",
    "IXC", "JAipur", "IXL", "IXB", "IXR", "IXZ", "IXM", "IXE", "IXU", "IXY",
    # International hubs
    "LHR", "CDG", "FRA", "AMS", "DXB", "DOH", "SIN", "HKG", "BKK", "KUL",
    "JFK", "LAX", "ORD", "DFW", "IAH", "MIA", "SFO", "SEA", "BOS", "ATL",
    "SYD", "MEL", "BNE", "PER", "AKL", "WLG", "NRT", "HND", "ICN", "PEK",
    "SHA", "PVG", "TPE", "MNL", "CGK", "DMK", "BKK", "RGN", "DAC", "KTM",
    "CMB", "MLE", "AUH", "SHJ", "RUH", "JED", "CAI", "IST", "SAW", "ESB",
    # More Indian cities
    "LKO", "NAG", "PAT", "RPR", "IDR", "BHO", "JDH", "UDR", "IXR", "GAU",
    "IMF", "IXA", "AGT", "NDC", "HPT", "IXH", "SHL", "AJL", "DMU", "TEZ",
}


def validate_iata(code: str) -> bool:
    """Validate if a string is a valid IATA airport code."""
    if not code or len(code) != 3:
        return False
    return code.upper() in VALID_IATA_CODES


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in various formats."""
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    mins = minutes % 60

    if mins == 0:
        return f"{hours}h"

    return f"{hours}h {mins}m"


def extract_time(time_str: str) -> Optional[str]:
    """Extract time from various time formats."""
    # Match HH:MM or HH:MM AM/PM patterns
    patterns = [
        r"(\d{1,2}:\d{2})\s*(AM|PM)?",
        r"(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)?",
    ]

    for pattern in patterns:
        match = re.search(pattern, time_str, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def normalize_price(price_str: str) -> Optional[float]:
    """Extract numeric price from string."""
    if not price_str:
        return None

    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,]", "", price_str)

    # Handle comma as thousand separator or decimal
    if "," in cleaned and "." in cleaned:
        # Both present - comma is thousand separator
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Only comma - could be decimal separator
        # Assume it's a decimal if there are exactly 2 digits after comma
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_flight_number(text: str) -> Optional[str]:
    """Extract flight number from text."""
    # Match patterns like AI101, 6E201, SG8157, etc.
    pattern = r"([A-Z]{2,3}\d{3,5})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def parse_stops(stops_text: str) -> int:
    """Parse stops text to integer."""
    if not stops_text:
        return 0

    text_lower = stops_text.lower()

    if "non" in text_lower or "direct" in text_lower or "non-stop" in text_lower:
        return 0
    if "1 stop" in text_lower or "one stop" in text_lower:
        return 1
    if "2 stop" in text_lower or "two stop" in text_lower:
        return 2
    if "3 stop" in text_lower or "three stop" in text_lower:
        return 3

    # Try to extract number
    match = re.search(r"(\d+)\s*stop", text_lower)
    if match:
        return int(match.group(1))

    return 0
