"""CRUD + filtering endpoints for product inventory."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_session
from app.api.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from app.db.models.product import Product

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    summary="List products with filters and pagination",
    response_model=ProductListResponse,
)
async def list_products(
    sku: str | None = Query(None, description="Filter by SKU (case-insensitive)"),
    name: str | None = Query(None, description="Filter by name (partial match)"),
    description: str | None = Query(
        None, description="Filter by description (partial match)"
    ),
    active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_session),
) -> ProductListResponse:
    """Return paginated product data for the dashboard grid.

    Only returns non-deleted products (is_deleted=False) by default.
    Filters are combined with AND logic.
    """
    try:
        query = select(Product).where(~Product.is_deleted)

        # Apply filters
        if sku:
            query = query.where(func.lower(Product.sku).contains(sku.lower()))
        if name:
            query = query.where(Product.name.ilike(f"%{name}%"))
        if description:
            query = query.where(Product.description.ilike(f"%{description}%"))
        if active is not None:
            query = query.where(Product.active == active)

        # Count total matching records (more efficient than subquery for simple cases)
        count_query = select(func.count(Product.id)).where(~Product.is_deleted)
        if sku:
            count_query = count_query.where(
                func.lower(Product.sku).contains(sku.lower())
            )
        if name:
            count_query = count_query.where(Product.name.ilike(f"%{name}%"))
        if description:
            count_query = count_query.where(
                Product.description.ilike(f"%{description}%")
            )
        if active is not None:
            count_query = count_query.where(Product.active == active)
        total = db.scalar(count_query) or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = (
            query.order_by(Product.created_at.desc()).offset(offset).limit(page_size)
        )

        products = db.scalars(query).all()

        return ProductListResponse(
            items=[ProductRead.model_validate(p) for p in products],
            total=total,
            page=page,
            page_size=page_size,
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error listing products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error listing products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.post(
    "/",
    summary="Create a product manually",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductRead,
)
async def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_session),
) -> ProductRead:
    """Persist a product record from UI form submissions.

    SKU must be unique (case-insensitive). If a product with the same SKU
    exists but is deleted, it will be restored and updated.
    """
    try:
        # Validate input
        if not payload.sku or not payload.sku.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU is required and cannot be empty",
            )
        if not payload.name or not payload.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product name is required",
            )

        # Check for existing product (including soft-deleted)
        existing = db.scalar(
            select(Product).where(
                func.lower(Product.sku) == payload.sku.lower().strip()
            )
        )

        if existing:
            if not existing.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product with SKU '{payload.sku}' already exists",
                )
            # Restore soft-deleted product
            existing.name = payload.name.strip()
            existing.description = (
                payload.description.strip() if payload.description else None
            )
            existing.active = payload.active
            existing.is_deleted = False
            db.commit()
            db.refresh(existing)
            logger.info(f"Restored soft-deleted product with SKU {payload.sku}")
            return ProductRead.model_validate(existing)

        # Create new product
        product = Product(
            sku=payload.sku.strip(),
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            active=payload.active,
            is_deleted=payload.is_deleted,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        logger.info(f"Created product {product.id} with SKU {payload.sku}")
        return ProductRead.model_validate(product)

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create product. SKU may already exist.",
        ) from e
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.put(
    "/{product_id}",
    summary="Update existing product",
    response_model=ProductRead,
)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_session),
) -> ProductRead:
    """Handle inline edits or modal saves for a single product.

    Only updates provided fields (partial update). Cannot update SKU.
    """
    try:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.is_deleted:
            raise HTTPException(status_code=404, detail="Product has been deleted")

        # Validate input if provided
        if payload.name is not None:
            if not payload.name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product name cannot be empty",
                )
            product.name = payload.name.strip()

        if payload.description is not None:
            product.description = (
                payload.description.strip() if payload.description else None
            )

        if payload.active is not None:
            product.active = payload.active

        if payload.is_deleted is not None:
            product.is_deleted = payload.is_deleted

        db.commit()
        db.refresh(product)

        logger.info(f"Updated product {product_id}")
        return ProductRead.model_validate(product)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error updating product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error updating product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.delete(
    "/{product_id}",
    summary="Delete product (soft delete)",
)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_session),
) -> Response:
    """Soft delete a single product by setting is_deleted=True.

    The product remains in the database but is excluded from list queries.
    """
    try:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.is_deleted:
            raise HTTPException(status_code=400, detail="Product is already deleted")

        product.is_deleted = True
        db.commit()

        logger.info(f"Soft deleted product {product_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error deleting product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error deleting product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.delete(
    "/",
    summary="Bulk delete all products (soft delete)",
)
async def delete_all_products(
    db: Session = Depends(get_session),
) -> Response:
    """Soft delete all products by setting is_deleted=True for all records.

    This operation is idempotent - already deleted products remain deleted.
    Used by the bulk delete UI action after user confirmation.
    """
    try:
        # Use update statement for bulk operation
        stmt = update(Product).where(~Product.is_deleted).values(is_deleted=True)
        result = db.execute(stmt)
        db.commit()

        deleted_count = result.rowcount
        logger.info(f"Bulk deleted {deleted_count} products")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during bulk delete: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete products",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during bulk delete: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
