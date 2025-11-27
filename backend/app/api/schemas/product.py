"""Pydantic models describing Product payloads."""

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    sku: str = Field(..., description="Case-insensitive unique SKU")
    name: str
    description: str | None = None
    active: bool = True
    is_deleted: bool = False


class ProductCreate(ProductBase):
    """Schema for UI-created product rows."""


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None
    is_deleted: bool | None = None


class ProductRead(ProductBase):
    id: int

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
