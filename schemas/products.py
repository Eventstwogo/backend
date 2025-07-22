from pydantic import BaseModel, Field, root_validator
from typing import Optional, Dict, List, Any
from datetime import datetime


class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = ''
    slug: Optional[str] = ''
    parent:Optional[str] = ''
    description: Optional[str] = ''
    meta_title: Optional[str] = ''
    meta_description: Optional[str] = ''
    image: Optional[str] = ''
    featured_category: Optional[bool] = False
    show_in_menu: Optional[bool] = False


class StatusUpdate(BaseModel):
    status: bool

class ProductSubCategoryCreate(BaseModel):
    prodcat_id: str
    prod_sub_name: str

class ProductSubCategoryUpdate(BaseModel):
    prod_sub_name: Optional[str] = None




class Identification(BaseModel):
    product_name: str
    product_sku: Optional[str] = None

class Descriptions(BaseModel):
    short_description: Optional[str] = None
    full_description: Optional[str] = None

class Pricing(BaseModel):
    actual_price: Optional[str] = None  # Could use float if Decimal in DB
    selling_price: Optional[str] = None

class Inventory(BaseModel):
    stock_quantity: Optional[str] = None  # Could use int if Integer in DB
    stock_alert_status: Optional[str] = None

class PhysicalAttributes(BaseModel):
    weight: Optional[str] = None  # Could use float if Float in DB
    dimensions: Optional[Dict[str, float]] = None  # e.g., {"length": 10, "width": 5, "height": 2}
    shipping_class: Optional[str] = None

class Images(BaseModel):
    pimg1: Optional[str] = None
    pimg2: Optional[str] = None
    pimg3: Optional[str] = None
    pimg4: Optional[str] = None
    pimg5: Optional[str] = None

class TagsAndRelationships(BaseModel):
    product_tags: Optional[List[str]] = None  # e.g., ["fruit", "fresh"]
    linkedproductid: Optional[str] = None

class StatusFlags(BaseModel):
    featured_product: bool = False
    published_product: bool = False
    product_status: bool = False

class ProductCreate(BaseModel):
    cat_id: str
    subcat_id: str
    identification: Identification
    descriptions: Optional[Descriptions] = None
    pricing: Optional[Pricing] = None
    inventory: Optional[Inventory] = None
    physical_attributes: Optional[PhysicalAttributes] = None
    images: Optional[Images] = None
    tags_and_relationships: Optional[TagsAndRelationships] = None
    status_flags: Optional[StatusFlags] = None

class ProductResponse(BaseModel):
    product_id: str
    vendor_id: str
    slug: str
    identification: Dict[str, Any]
    descriptions: Optional[Dict[str, Any]]
    pricing: Optional[Dict[str, Any]]
    inventory: Optional[Dict[str, Any]]
    physical_attributes: Optional[Dict[str, Any]]
    images: Optional[Dict[str, Any]]
    tags_and_relationships: Optional[Dict[str, Any]]
    status_flags: Dict[str, bool]
    timestamp: Optional[datetime]
    
    category_name: Optional[str]
    subcategory_name: Optional[str]

    

class ProductSearchResult(BaseModel):
    product_id: str
    product_name: str
    image_url: str | None
    selling_price: str
    slug: str
    category_slug: str

