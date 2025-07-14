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


from api.v1.endpoints.vendor import vendor_signup, email_verification, business_profile
from api.v1.endpoints.admin import registration, admin_login, password_manager

api_router = APIRouter(prefix="/api/v1")


# KYC Endpoints
# api_router.include_router(abn_check.router, prefix="/abn_check", tags=["ABN"])


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


#Vendor Endpoints

api_router.include_router(
    vendor_signup.router, prefix="/vendor", tags=["Vendor"]
)

api_router.include_router(
    email_verification.router, prefix="/vendor", tags=["Vendor"]
)

api_router.include_router(
    business_profile.router, prefix="/vendor", tags=["Vendor"]
)

# Admin User Endpoints
api_router.include_router(
    registration.router, prefix="/admin-users", tags=["Admin Users Registration"]
)
api_router.include_router(
    admin_login.router, prefix="/admin-login", tags=["Admin Users Authentication"]
)
api_router.include_router(
    password_manager.router, prefix="/admin", tags= ["Admin Password Management"]
)