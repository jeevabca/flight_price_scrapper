import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flight_result import FlightResult
from app.models.search_log import SearchLog
from app.schemas.flight import FlightSearchRequest, FlightResult as FlightResultSchema, ProviderError
from app.config import get_settings

settings = get_settings()


class FlightService:
    """Service for flight search operations including caching."""

    @staticmethod
    async def check_cache(
        db: AsyncSession,
        request: FlightSearchRequest,
    ) -> list[FlightResult] | None:
        """Check if valid cached results exist for the given search parameters."""
        # Build cache key from request params
        cache_key = FlightService._build_cache_key(request)

        # Query for cached results that haven't expired
        query = select(FlightResult).where(
            and_(
                FlightResult.search_id == cache_key,
                FlightResult.expires_at > datetime.utcnow(),
            )
        )
        result = await db.execute(query)
        cached_results = result.scalars().all()

        if not cached_results:
            return None

        return [
            FlightResultSchema(
                provider=r.provider,
                airline=r.airline,
                flight_number=r.flight_number,
                origin=r.origin,
                destination=r.destination,
                departure_time=r.departure_time,
                arrival_time=r.arrival_time,
                duration=r.duration,
                stops=r.stops,
                price=r.price,
                currency=r.currency,
                cabin_class=r.cabin_class,
                scraped_at=r.scraped_at,
            )
            for r in cached_results
        ]

    @staticmethod
    def _build_cache_key(request: FlightSearchRequest) -> str:
        """Build a deterministic cache key from search parameters."""
        params = {
            "trip_type": request.trip_type.value,
            "origin": request.origin,
            "destination": request.destination,
            "outbound_date": request.outbound_date,
            "return_date": request.return_date,
            "passengers": request.passengers,
            "cabin_class": request.cabin_class.value,
            "providers": sorted(request.providers) if request.providers else [],
        }
        if request.multi_city_legs:
            params["multi_city_legs"] = [
                {"origin": leg.origin, "destination": leg.destination, "date": leg.date}
                for leg in request.multi_city_legs
            ]
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, json.dumps(params, sort_keys=True)))

    @staticmethod
    async def save_results(
        db: AsyncSession,
        search_id: str,
        results: list[FlightResultSchema],
    ) -> None:
        """Save scraped flight results to the database."""
        expires_at = datetime.utcnow() + timedelta(minutes=settings.cache_ttl_minutes)

        for result in results:
            flight_result = FlightResult(
                search_id=search_id,
                provider=result.provider,
                airline=result.airline,
                flight_number=result.flight_number,
                origin=result.origin,
                destination=result.destination,
                departure_time=result.departure_time,
                arrival_time=result.arrival_time,
                duration=result.duration,
                stops=result.stops,
                price=result.price,
                currency=result.currency,
                cabin_class=result.cabin_class,
                expires_at=expires_at,
            )
            db.add(flight_result)

        await db.flush()

    @staticmethod
    async def log_search(
        db: AsyncSession,
        search_id: str,
        request: FlightSearchRequest,
        total_results: int,
        total_errors: int,
        duration_ms: int,
    ) -> None:
        """Log a search request for audit purposes."""
        search_log = SearchLog(
            search_id=search_id,
            request_params=request.model_dump(mode="json"),
            providers_requested=request.providers,
            total_results=total_results,
            total_errors=total_errors,
            duration_ms=duration_ms,
        )
        db.add(search_log)
        await db.flush()

    @staticmethod
    async def get_all_providers(db: AsyncSession) -> list[str]:
        """Get all unique provider names from the database."""
        query = select(ProviderXPath.provider_name).distinct()
        result = await db.execute(query)
        return list(result.scalars().all())


# Import here to avoid circular dependency
from app.models.provider_xpath import ProviderXPath
