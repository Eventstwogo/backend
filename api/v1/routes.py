from fastapi import APIRouter

from api.v1.endpoints import (
    abn_check,
    categories,
    categories_by_id,
    categories_by_slug,
    categories_or_subcategories_by_id,
    config,
    roles,
    sub_categories_by_id,
    sub_categories_by_slug,
    subcategories,
)


api_router = APIRouter(prefix="/api/v1")


# KYC Endpoints
api_router.include_router(abn_check.router, prefix="/abn_check", tags=["ABN"])


# Role Endpoints
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])


# Category Endpoints
api_router.include_router(
    categories.router, prefix="/categories", tags=["Categories"]
)
api_router.include_router(
    categories_by_id.router, prefix="/categories", tags=["Categories by ID"]
)
api_router.include_router(
    categories_by_slug.router, prefix="/categories", tags=["Categories by Slug"]
)

# Subcategory Endpoints
api_router.include_router(
    subcategories.router, prefix="/subcategories", tags=["Subcategories"]
)
api_router.include_router(
    sub_categories_by_id.router,
    prefix="/subcategories",
    tags=["Subcategories by ID"],
)
api_router.include_router(
    sub_categories_by_slug.router,
    prefix="/subcategories",
    tags=["Subcategories by Slug"],
)

api_router.include_router(
    categories_or_subcategories_by_id.router,
    prefix="/categories_or_subcategories_by_id",
    tags=["categories or subcategories by id"],
)


# Configuration Endpoints
api_router.include_router(
    config.router, prefix="/config", tags=["Configuration"]
)
