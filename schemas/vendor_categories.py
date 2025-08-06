from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class SubcategoryOut(BaseModel):
    subcategory_id: str
    subcategory_name: str
    subcategory_status: bool

class CategoryOut(BaseModel):
    category_id: str
    category_name: str
    category_description: str
    category_tstamp: Optional[datetime]
    subcategories: List[SubcategoryOut]

    class Config:
        from_attributes = True
