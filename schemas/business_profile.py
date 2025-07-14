


from pydantic import BaseModel, Field


class VendorBusinessProfileRequest(BaseModel):
    business_profile_id: str = Field(..., min_length=6, max_length=6)
    abn_id: str