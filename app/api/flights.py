import time
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.flight_service import FlightService
from app.services.xpath_service import XPathService
from app.schemas.flight import (
    FlightSearchRequest,
    FlightSearchResponse,
    FlightResult as FlightResultSchema,
    ProviderError,
    ProviderInfo,
)
from app.scrapers.engine import ScraperEngine

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for flights across multiple providers.

    This endpoint:
    1. Checks cache for recent results
    2. If cache miss, scrapes providers concurrently
    3. Returns unified results with any errors
    """
    start_time = time.time()
    search_id = FlightService._build_cache_key(request)

    # Step 1: Check cache
    cached_results = await FlightService.check_cache(db, request)

    if cached_results:
        # Cache hit - return cached results
        duration_ms = int((time.time() - start_time) * 1000)

        return FlightSearchResponse(
            search_id=search_id,
            searched_at=datetime.utcnow(),
            cached=True,
            params=request.model_dump(mode="json"),
            results=cached_results,
            errors=[],
            total_results=len(cached_results),
            total_errors=0,
            duration_ms=duration_ms,
        )

    # Step 2: Cache miss - scrape providers
    try:
        engine = ScraperEngine(request.providers)
        results, errors = await engine.scrape_all(request)
    except Exception as e:
        # Handle unexpected errors
        results = []
        errors = [ProviderError(
            provider="system",
            reason="internal_error",
            message=str(e),
        )]

    # Step 3: Save results to cache
    if results:
        await FlightService.save_results(db, search_id, results)

    # Step 4: Log the search
    await FlightService.log_search(
        db,
        search_id,
        request,
        total_results=len(results),
        total_errors=len(errors),
        duration_ms=int((time.time() - start_time) * 1000),
    )

    duration_ms = int((time.time() - start_time) * 1000)

    return FlightSearchResponse(
        search_id=search_id,
        searched_at=datetime.utcnow(),
        cached=False,
        params=request.model_dump(mode="json"),
        results=results,
        errors=errors,
        total_results=len(results),
        total_errors=len(errors),
        duration_ms=duration_ms,
    )


@router.get("/providers", response_model=list[ProviderInfo])
async def get_providers(db: AsyncSession = Depends(get_db)):
    """
    Get list of all available providers with their readiness status.

    A provider is 'ready' if it has all 15 required XPath fields configured and active.
    """
    # Get all providers
    all_xpaths = await XPathService.get_all_xpaths(db)
    provider_names = set(xp.provider_name for xp in all_xpaths)

    # Required fields for readiness check
    required_fields = {
        "search_origin_input",
        "search_destination_input",
        "search_date_outbound",
        "search_date_return",
        "search_passengers_input",
        "search_submit_button",
        "results_flight_card",
        "result_price",
        "result_airline",
        "result_flight_number",
        "result_departure_time",
        "result_arrival_time",
        "result_duration",
        "result_stops",
        "result_booking_link",
    }

    providers = []
    for provider_name in sorted(provider_names):
        provider_xpaths = [xp for xp in all_xpaths if xp.provider_name == provider_name]
        active_fields = {xp.field_name for xp in provider_xpaths if xp.is_active}
        active_count = len(active_fields.intersection(required_fields))
        is_ready = active_count == len(required_fields)

        # Check if provider has any active config
        has_active = any(xp.is_active for xp in provider_xpaths)

        providers.append(ProviderInfo(
            name=provider_name,
            is_active=has_active,
            active_field_count=active_count,
            required_field_count=len(required_fields),
            is_ready=is_ready,
        ))

    return providers
