import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ProviderXPath(Base):
    """XPath configuration for scraping providers."""

    __tablename__ = "provider_xpaths"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    xpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    css_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ProviderXPath(id={self.id}, provider={self.provider_name}, field={self.field_name})>"
