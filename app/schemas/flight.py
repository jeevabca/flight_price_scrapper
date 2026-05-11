from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import datetime
from typing import Optional
from enum import Enum


class TripType(str, Enum):
    ONEWAY = "oneway"
    RETURN = "return"
    MULTICITY = "multicity"


class CabinClass(str, Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class MultiCityLeg(BaseModel):
    """Schema for a multi-city flight leg."""

    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Travel date YYYY-MM-DD")


class FlightSearchRequest(BaseModel):
    """Schema for flight search request."""

    providers: list[str] = Field(..., min_length=1, description="List of providers to scrape")
    trip_type: TripType = Field(default=TripType.ONEWAY, description="Trip type")
    origin: Optional[str] = Field(None, min_length=3, max_length=3, description="Origin IATA code")
    destination: Optional[str] = Field(None, min_length=3, max_length=3, description="Destination IATA code")
    outbound_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Outbound date YYYY-MM-DD")
    return_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Return date YYYY-MM-DD")
    multi_city_legs: Optional[list[MultiCityLeg]] = Field(None, description="Multi-city legs")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY, description="Cabin class")

    @field_validator("origin")
    @classmethod
    def validate_origin(cls, v: str | None, info: ValidationInfo) -> str:
        if v is None and info.data.get("trip_type") != TripType.MULTICITY:
            raise ValueError("origin is required for oneway/return trips")
        return v.upper() if v else v

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str | None, info: ValidationInfo) -> str:
        if v is None and info.data.get("trip_type") != TripType.MULTICITY:
            raise ValueError("destination is required for oneway/return trips")
        return v.upper() if v else v

    @field_validator("outbound_date")
    @classmethod
    def validate_outbound_date(cls, v: str | None, info: ValidationInfo) -> str:
        if v is None and info.data.get("trip_type") != TripType.MULTICITY:
            raise ValueError("outbound_date is required for oneway/return trips")
        return v

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None and info.data.get("trip_type") == TripType.RETURN:
            raise ValueError("return_date is required for return trips")
        return v

    @field_validator("multi_city_legs")
    @classmethod
    def validate_multi_city_legs(cls, v: list | None, info: ValidationInfo) -> list | None:
        if v is None and info.data.get("trip_type") == TripType.MULTICITY:
            raise ValueError("multi_city_legs is required for multicity trips")
        if len(v) < 1 if v else False:
            raise ValueError("multi_city_legs must have at least one leg")
        return v


class FlightResult(BaseModel):
    """Schema for a single flight result."""

    provider: str
    airline: str
    flight_number: Optional[str] = None
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: int
    price: float
    currency: str = "INR"
    cabin_class: str
    scraped_at: Optional[datetime] = None


class ProviderError(BaseModel):
    """Schema for provider scraping errors."""

    provider: str
    reason: str
    message: str


class ProviderException(Exception):
    """Exception wrapping a ProviderError."""
    
    def __init__(self, error: ProviderError):
        super().__init__(error.message)
        self.error = error


class FlightSearchResponse(BaseModel):
    """Schema for flight search response."""

    search_id: str
    searched_at: datetime
    cached: bool
    params: dict
    results: list[FlightResult]
    errors: list[ProviderError]
    total_results: int
    total_errors: int
    duration_ms: int


class ProviderInfo(BaseModel):
    """Schema for provider information."""

    name: str
    is_active: bool
    active_field_count: int
    required_field_count: int = 15
    is_ready: bool
