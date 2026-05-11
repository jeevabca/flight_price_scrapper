import uuid
from datetime import datetime, timedelta
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.config import get_settings

settings = get_settings()


class FlightResult(Base):
    """Scraped flight results with TTL cache."""

    __tablename__ = "flight_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    search_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    airline: Mapped[str] = mapped_column(String(255), nullable=False)
    flight_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin: Mapped[str] = mapped_column(String(10), nullable=False)
    destination: Mapped[str] = mapped_column(String(10), nullable=False)
    departure_time: Mapped[str] = mapped_column(String(50), nullable=False)
    arrival_time: Mapped[str] = mapped_column(String(50), nullable=False)
    duration: Mapped[str] = mapped_column(String(50), nullable=False)
    stops: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    cabin_class: Mapped[str] = mapped_column(String(50), default="economy")
    booking_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(minutes=settings.cache_ttl_minutes),
    )

    def __repr__(self) -> str:
        return f"<FlightResult(id={self.id}, provider={self.provider}, price={self.price})>"
