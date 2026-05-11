from app.schemas.flight import FlightSearchRequest, TripType

def build_skyscanner_url(params: FlightSearchRequest) -> str:
    """
    Build a Skyscanner search URL for direct navigation.
    Example: https://www.skyscanner.co.in/transport/flights/MAA/DEL/260601/
    """
    base = "https://www.skyscanner.co.in/transport/flights"
    
    origin = (params.origin or "").upper()
    destination = (params.destination or "").upper()
    
    # Format date as YYMMDD
    if params.outbound_date:
        date_parts = params.outbound_date.split("-")
        yymmdd = f"{date_parts[0][2:]}{date_parts[1]}{date_parts[2]}"
    else:
        yymmdd = ""
        
    url = f"{base}/{origin}/{destination}/{yymmdd}/"
    
    # Adding params for adults/class
    cabin = "economy"
    if params.cabin_class.value == "business":
        cabin = "business"
    elif params.cabin_class.value == "first":
        cabin = "first"
        
    url += f"?adults={params.passengers or 1}&cabinclass={cabin}&children=0&infants=0"
    
    return url
