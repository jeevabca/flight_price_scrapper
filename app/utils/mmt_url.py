from app.schemas.flight import FlightSearchRequest, TripType

def build_makemytrip_url(params: FlightSearchRequest) -> str:
    """
    Build a MakeMyTrip search URL for direct navigation.
    Example: https://www.makemytrip.com/flight/search?itinerary=MAA-DEL-20/04/2026&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E&lang=eng
    """
    base = "https://www.makemytrip.com/flight/search"
    
    origin = (params.origin or "").upper()
    destination = (params.destination or "").upper()
    
    # MMT Date: DD/MM/YYYY
    if params.outbound_date:
        date_parts = params.outbound_date.split("-")
        ddmmyyyy = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
    else:
        ddmmyyyy = ""
        
    itinerary = f"{origin}-{destination}-{ddmmyyyy}"
    
    trip_type = "O" if params.trip_type == TripType.ONEWAY else "R"
    
    cabin = "E"
    if params.cabin_class.value == "business":
        cabin = "B"
    elif params.cabin_class.value == "first":
        cabin = "F"
        
    pax = f"A-{params.passengers or 1}_C-0_I-0"
    
    url = f"{base}?itinerary={itinerary}&tripType={trip_type}&paxType={pax}&intl=false&cabinClass={cabin}&lang=eng"
    return url
