import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SearchLog(Base):
    """Audit log for flight searches."""

    __tablename__ = "search_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    search_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    providers_requested: Mapped[list] = mapped_column(JSON, nullable=False)
    total_results: Mapped[int] = mapped_column(Integer, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<SearchLog(id={self.id}, search_id={self.search_id}, results={self.total_results})>"
