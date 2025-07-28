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
    industries,
 
)


from api.v1.endpoints.vendor import vendor_signup, email_verification, business_profile, vendor_login, vendor_onboarding, fetch_vendors, employee
from api.v1.endpoints.admin import registration, admin_login, password_manager, product, vendor_approval, admin_users
from api.v1.endpoints.vendor import vendor_category_mapping


api_router = APIRouter(prefix="/api/v1")


# KYC Endpoints
api_router.include_router(abn_check.router, prefix="/abn_check", tags=["ABN"])


# Role Endpoints
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])

api_router.include_router(
    industries.router, prefix="/industries", tags=["Industries"]
)


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

api_router.include_router(product.router, prefix="/products", tags=["Products"])


# Configuration Endpoints
api_router.include_router(
    config.router, prefix="/config", tags=["Configuration"]
)

api_router.include_router(
    vendor_category_mapping.router, prefix="/mapping", tags=["Vendor Category Management"]
)


#Vendor Endpoints

api_router.include_router(
    vendor_signup.router, prefix="/vendor", tags=["Vendor"]
)

api_router.include_router(
    email_verification.router, prefix="/vendor", tags=["Vendor"]
)
api_router.include_router(
    vendor_login.router, prefix="/vendor", tags=["Vendor"]
)


api_router.include_router(
    business_profile.router, prefix="/vendor", tags=["Vendor"]
)

api_router.include_router(
    vendor_onboarding.router, prefix="/vendor", tags=["Vendor"]
)


api_router.include_router(
    employee.router, prefix="/vendor/employee", tags=["Vendor Employee"]
)


api_router.include_router(fetch_vendors.router, prefix="/vendor",tags=["Vendor"] )


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

api_router.include_router(
    vendor_approval.router, prefix="/admin", tags= ["Admin Vendor Management"]
)

api_router.include_router(
    admin_users.router, prefix="/admin-users", tags=["Admin Users Management"]
)