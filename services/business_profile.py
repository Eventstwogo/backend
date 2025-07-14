
import re
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from utils.id_generators import hash_data
from core.api_response import api_response
from db.models.superadmin import BusinessProfile

def sanitize_inputs(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[\"';`]|--", "", text)
    return text.strip()

def validate_abn_id(id: str) -> str:
    if id != id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ABN must not contain leading or trailing whitespace."
        )
    id = sanitize_inputs(id)
    if not re.fullmatch(r"\d{11}", id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ABN must be exactly 11 digits with no spaces or other characters."
        )
    return id

async def fetch_abn_details(abn_id: str) -> dict:
    abn_id = validate_abn_id(abn_id)
    url = f"https://abr.business.gov.au/ABN/View?id={abn_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch ABN data."
        )

    soup = BeautifulSoup(response.text, "html.parser")
    entity_name = soup.find("span", {"itemprop": "legalName"})
    entity_status_row = soup.find("th", text="ABN status:")
    entity_type_row = soup.find("th", text="Entity type:")
    entity_location_row = soup.find("th", text="Main business location:")

    entity_status = entity_status_row.find_next_sibling("td") if entity_status_row else None
    entity_type = entity_type_row.find_next_sibling("td") if entity_type_row else None
    entity_location = entity_location_row.find_next_sibling("td") if entity_location_row else None

    if not (entity_name and entity_status and entity_type and entity_location):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not extract all ABN fields"
        )

    return {
        "entity_name": entity_name.get_text(strip=True),
        "status": entity_status.get_text(strip=True),
        "type": entity_type.get_text(strip=True),
        "location": entity_location.get_text(strip=True)
    }


async def business_profile_exists(db: AsyncSession, abn_id: str):
    abn_hash = hash_data(abn_id)
    result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.abn_hash == abn_hash)
    )
    return result.scalar_one_or_none()