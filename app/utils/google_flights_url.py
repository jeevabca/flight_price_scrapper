from app.schemas.flight import FlightSearchRequest, TripType

def build_google_flights_url(params: FlightSearchRequest) -> str:
    """
    Build a Google Flights search URL using the powerful 'q' parameter.
    This approach is more robust than manual form-filling as Google
    interprets the query and populates the search results automatically.
    """
    query_parts = ["flights"]
    
    if params.origin:
        query_parts.append(f"from {params.origin}")
    if params.destination:
        query_parts.append(f"to {params.destination}")
    if params.outbound_date:
        query_parts.append(f"on {params.outbound_date}")
    
    if params.trip_type == TripType.RETURN and params.return_date:
        query_parts.append(f"return on {params.return_date}")
    elif params.trip_type == TripType.ONEWAY:
        query_parts.append("one way")
    elif params.trip_type == TripType.MULTICITY and params.multi_city_legs:
        # For multi-city, we construct a sequential query
        query_parts = ["multi city flights"]
        for leg in params.multi_city_legs:
            query_parts.append(f"from {leg.origin} to {leg.destination} on {leg.date}")

    query = "+".join([p.replace(" ", "+") for p in query_parts])
    
    # Adding hl=en and curr=INR/USD to ensure consistent UI language and currency
    # The 'q' parameter is handled by Google's search-to-flights redirector
    return f"https://www.google.com/travel/flights?q={query}&hl=en&curr=INR"
