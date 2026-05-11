from app.schemas.flight import FlightSearchRequest, TripType

def build_kayak_url(params: FlightSearchRequest) -> str:
    """
    Build a Kayak search URL for direct navigation.
    Example: https://www.kayak.co.in/flights/MAA-DEL/2026-06-01?sort=bestflight_a
    """
    base = "https://www.kayak.co.in/flights"
    
    origin = (params.origin or "").upper()
    destination = (params.destination or "").upper()
    outbound_date = params.outbound_date
    
    if params.trip_type == TripType.RETURN and params.return_date:
        url = f"{base}/{origin}-{destination}/{outbound_date}/{params.return_date}"
    else:
        url = f"{base}/{origin}-{destination}/{outbound_date}"
        
    return f"{url}?sort=bestflight_a"
