from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.provider_xpath import ProviderXPath
from app.schemas.xpath import XPathCreate, XPathUpdate


class XPathService:
    """Service for managing XPath configurations in the database."""

    @staticmethod
    async def get_all_xpaths(db: AsyncSession, provider: Optional[str] = None) -> list[ProviderXPath]:
        """Get all XPath entries, optionally filtered by provider."""
        query = select(ProviderXPath)
        if provider:
            query = query.where(ProviderXPath.provider_name == provider)
        query = query.order_by(ProviderXPath.provider_name, ProviderXPath.field_name)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_xpaths_for_provider(db: AsyncSession, provider_name: str) -> dict[str, ProviderXPath]:
        """Get all active XPaths for a specific provider as a dict keyed by field_name."""
        query = select(ProviderXPath).where(
            and_(
                ProviderXPath.provider_name == provider_name,
                ProviderXPath.is_active == True,
            )
        )
        result = await db.execute(query)
        xpaths = result.scalars().all()
        return {xp.field_name: xp for xp in xpaths}

    @staticmethod
    async def get_xpath(db: AsyncSession, xpath_id: str) -> Optional[ProviderXPath]:
        """Get a single XPath entry by ID."""
        query = select(ProviderXPath).where(ProviderXPath.id == xpath_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_xpath(db: AsyncSession, xpath_data: XPathCreate) -> ProviderXPath:
        """Create a new XPath entry."""
        xpath_entry = ProviderXPath(**xpath_data.model_dump())
        db.add(xpath_entry)
        await db.flush()
        await db.refresh(xpath_entry)
        return xpath_entry

    @staticmethod
    async def update_xpath(
        db: AsyncSession,
        xpath_id: str,
        xpath_data: XPathUpdate,
    ) -> Optional[ProviderXPath]:
        """Update an existing XPath entry."""
        xpath_entry = await XPathService.get_xpath(db, xpath_id)
        if not xpath_entry:
            return None

        update_data = xpath_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(xpath_entry, field, value)

        await db.flush()
        await db.refresh(xpath_entry)
        return xpath_entry

    @staticmethod
    async def delete_xpath(db: AsyncSession, xpath_id: str) -> bool:
        """Soft delete an XPath entry by setting is_active=False."""
        xpath_entry = await XPathService.get_xpath(db, xpath_id)
        if not xpath_entry:
            return False

        xpath_entry.is_active = False
        await db.flush()
        return True

    @staticmethod
    async def bulk_upsert_xpaths(
        db: AsyncSession,
        provider_name: str,
        entries: list[XPathCreate],
    ) -> list[ProviderXPath]:
        """Bulk upsert XPath entries for a provider."""
        result_xpaths = []

        for entry in entries:
            # Check if entry exists
            query = select(ProviderXPath).where(
                and_(
                    ProviderXPath.provider_name == provider_name,
                    ProviderXPath.field_name == entry.field_name,
                )
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.xpath = entry.xpath
                existing.css_selector = entry.css_selector
                existing.description = entry.description
                existing.is_active = entry.is_active
                result_xpaths.append(existing)
            else:
                # Create new
                new_xpath = ProviderXPath(
                    provider_name=provider_name,
                    field_name=entry.field_name,
                    xpath=entry.xpath,
                    css_selector=entry.css_selector,
                    description=entry.description,
                    is_active=entry.is_active,
                )
                db.add(new_xpath)
                result_xpaths.append(new_xpath)

        await db.flush()
        return result_xpaths

    @staticmethod
    async def get_provider_readiness(db: AsyncSession, provider_name: str) -> tuple[int, bool]:
        """Get active field count and readiness status for a provider."""
        required_fields = [
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
        ]

        query = select(ProviderXPath).where(
            and_(
                ProviderXPath.provider_name == provider_name,
                ProviderXPath.is_active == True,
                ProviderXPath.field_name.in_(required_fields),
            )
        )
        result = await db.execute(query)
        active_xpaths = result.scalars().all()
        active_field_names = {xp.field_name for xp in active_xpaths}

        active_count = len(active_field_names)
        is_ready = active_count == len(required_fields)

        return active_count, is_ready
