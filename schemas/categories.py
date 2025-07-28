from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SubCategoryOut(BaseModel):
    id: str
    subcategory_id: str
    subcategory_name: str
    subcategory_description: Optional[str]
    subcategory_slug: str
    subcategory_meta_title: Optional[str]
    subcategory_meta_description: Optional[str]
    subcategory_img_thumbnail: Optional[str]
    featured_subcategory: Optional[bool]
    show_in_menu: Optional[bool]
    subcategory_status: bool
    subcategory_tstamp: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CategoryOut(BaseModel):
    category_id: str
    industry_id: str
    category_name: str
    category_description: Optional[str]
    category_slug: str
    category_meta_title: Optional[str]
    category_meta_description: Optional[str]
    category_img_thumbnail: Optional[str]
    featured_category: Optional[bool]
    show_in_menu: Optional[bool]
    category_status: bool
    category_tstamp: Optional[datetime]
    subcategories: List[SubCategoryOut] = []

    model_config = ConfigDict(from_attributes=True)
