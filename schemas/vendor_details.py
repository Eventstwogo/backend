from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class VendorCategoryInfo(BaseModel):
    category_id: str
    category_name: str
    industry_id: str


class VendorDetailsResponse(BaseModel):
    vendor_id: str
    store_name: Optional[str] = None
    store_slug: Optional[str] = None
    location: Optional[str] = None
    business_logo: Optional[str] = None
    store_logo: Optional[str] = None
    categories: List[VendorCategoryInfo] = []
    total_products: int = 0
    years_in_business: str = "0:00"  # Format: yyyy:mm


class AllVendorsResponse(BaseModel):
    vendors: List[VendorDetailsResponse]
    total_vendors: int


class VendorProductInfo(BaseModel):
    product_id: str
    vendor_id: str
    category_id: str
    category_name: str
    subcategory_id: Optional[str] = None
    slug: str
    identification: Dict[str, Any]
    descriptions: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None
    physical_attributes: Optional[Dict[str, Any]] = None
    images: Optional[Dict[str, Any]] = None
    tags_and_relationships: Optional[Dict[str, Any]] = None
    status_flags: Dict[str, bool]


class VendorSubcategoryInfo(BaseModel):
    subcategory_id: str
    subcategory_name: str


class VendorCategoryManagementInfo(BaseModel):
    category_id: str
    category_name: str
    subcategories: List[VendorSubcategoryInfo] = []


class VendorProductsAndCategoriesResponse(BaseModel):
    vendor_id: str
    store_name: Optional[str] = None
    store_slug: Optional[str] = None
    products: List[VendorProductInfo] = []
    total_products: int = 0
    category_management: List[VendorCategoryManagementInfo] = []

class VendorProfilePictureUploadResponse(BaseModel):
    """Response schema for vendor profile picture upload"""
    user_id: str
    profile_picture_url: str
    message: str


class VendorBannerUploadResponse(BaseModel):
    """Response schema for vendor banner image upload"""
    banner_image_url: str
    banner_title: Optional[str] = None
    banner_subtitle: Optional[str] = None


class VendorBannerResponse(BaseModel):
    """Response schema for vendor banner image retrieval"""
    banner_image_url: Optional[str] = None
    banner_title: Optional[str] = None
    banner_subtitle: Optional[str] = None


class VendorUserDetailResponse(BaseModel):
    """Response schema for vendor user profile details"""
    user_id: str
    username: str
    email: EmailStr
    store_name: Optional[str] = None
    store_url: Optional[str] = None
    role_id: Optional[str] = None
    role: Optional[str] = None
    profile_picture_url: Optional[str] = None
    join_date: Optional[str] = None  # Format: dd-mm-yyyy


class VendorLoginRequest(BaseModel):
    email: str = Field(..., description="Username or email (case-insensitive)")
    password: str = Field(..., description="User password")


class VendorUserInfo(BaseModel):
    is_approved: int
    ref_number: str
    industry: str
    onboarding_status: str 
    vendor_store_slug: str 
    reviewer_comment: str

class VendorLoginResponse(BaseModel):
    access_token: str
    message: str
    user: VendorUserInfo | None = None