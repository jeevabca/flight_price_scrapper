from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.xpath_service import XPathService
from app.schemas.xpath import XPathCreate, XPathUpdate, XPathResponse, XPathBulkUpsert

router = APIRouter(prefix="/api/xpaths", tags=["xpaths"])


@router.get("", response_model=list[XPathResponse])
async def list_xpaths(
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    db: AsyncSession = Depends(get_db),
):
    """List all XPath configurations, optionally filtered by provider."""
    xpaths = await XPathService.get_all_xpaths(db, provider)
    return xpaths


@router.get("/{provider}", response_model=list[XPathResponse])
async def get_provider_xpaths(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all active XPath configurations for a specific provider."""
    xpaths = await XPathService.get_all_xpaths(db, provider)
    return xpaths


@router.post("", response_model=XPathResponse, status_code=201)
async def create_xpath(
    xpath_data: XPathCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new XPath configuration entry."""
    xpath_entry = await XPathService.create_xpath(db, xpath_data)
    return xpath_entry


@router.put("/{xpath_id}", response_model=XPathResponse)
async def update_xpath(
    xpath_id: str,
    xpath_data: XPathUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing XPath configuration entry."""
    xpath_entry = await XPathService.update_xpath(db, xpath_id, xpath_data)
    if not xpath_entry:
        raise HTTPException(status_code=404, detail="XPath entry not found")
    return xpath_entry


@router.delete("/{xpath_id}", status_code=204)
async def delete_xpath(
    xpath_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an XPath configuration entry (sets is_active=False)."""
    success = await XPathService.delete_xpath(db, xpath_id)
    if not success:
        raise HTTPException(status_code=404, detail="XPath entry not found")
    return None


@router.post("/bulk", response_model=list[XPathResponse])
async def bulk_upsert_xpaths(
    bulk_data: XPathBulkUpsert,
    db: AsyncSession = Depends(get_db),
):
    """Bulk upsert multiple XPath entries for a provider."""
    if not bulk_data.entries:
        raise HTTPException(status_code=400, detail="No entries provided")

    # All entries should be for the same provider
    provider_name = bulk_data.entries[0].provider_name

    result_xpaths = await XPathService.bulk_upsert_xpaths(
        db,
        provider_name,
        bulk_data.entries,
    )
    return result_xpaths
