from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class XPathCreate(BaseModel):
    """Schema for creating a new XPath entry."""

    provider_name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    field_name: str = Field(..., min_length=1, max_length=100, description="Standardized field key")
    xpath: Optional[str] = Field(None, description="XPath selector")
    css_selector: Optional[str] = Field(None, description="CSS selector")
    description: Optional[str] = Field(None, description="Field description")
    is_active: bool = Field(True, description="Whether this XPath config is active")


class XPathUpdate(BaseModel):
    """Schema for updating an existing XPath entry."""

    xpath: Optional[str] = Field(None, description="XPath selector")
    css_selector: Optional[str] = Field(None, description="CSS selector")
    description: Optional[str] = Field(None, description="Field description")
    is_active: Optional[bool] = Field(None, description="Whether this XPath config is active")


class XPathResponse(BaseModel):
    """Schema for XPath response."""

    id: str
    provider_name: str
    field_name: str
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class XPathBulkUpsert(BaseModel):
    """Schema for bulk upsert of XPath entries."""

    entries: list[XPathCreate] = Field(..., min_length=1)
