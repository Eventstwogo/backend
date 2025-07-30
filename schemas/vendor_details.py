from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


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


class VendorCategoryManagementInfo(BaseModel):
    category_id: str
    category_name: str
    subcategory_id: Optional[str] = None
    subcategory_name: Optional[str] = None


class VendorProductsAndCategoriesResponse(BaseModel):
    vendor_id: str
    store_name: Optional[str] = None
    store_slug: Optional[str] = None
    products: List[VendorProductInfo] = []
    total_products: int = 0
    category_management: List[VendorCategoryManagementInfo] = []