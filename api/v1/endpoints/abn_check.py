from fastapi import APIRouter, HTTPException, Query, status, Depends
from starlette.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup
import re

router = APIRouter()


def sanitize_inputs(text: str) -> str:

    text = re.sub(r"<.*?>", "", text)  # remove HTML tags
    text = re.sub(r"[\"';`]|--", "", text)  # remove dangerous SQL chars
    return text.strip()


def validate_abn_id(id: str) -> str:
    # Check if input has leading/trailing whitespace
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



@router.get(
    "/",
    summary="Get ABN details by ID"
)
async def get_abn_details(
    id: str = Depends(validate_abn_id)
) -> JSONResponse:
    try:
        url = f"https://abr.business.gov.au/ABN/View?id={id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch data from ABN Lookup site"
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract data
        entity_name = soup.find("span", {"itemprop": "legalName"})
        entity_status_row = soup.find("th", text="ABN status:")
        entity_type_row = soup.find("th", text="Entity type:")
        entity_location_row = soup.find("th", text="Main business location:")

        entity_status = entity_status_row.find_next_sibling("td") if entity_status_row else None
        entity_type = entity_type_row.find_next_sibling("td") if entity_type_row else None
        entity_location = entity_location_row.find_next_sibling("td") if entity_location_row else None

        if not (entity_name and entity_status and entity_type and entity_location):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Unable to extract ABN details from the page."}
            )

        data = {
            "entity_name": entity_name.get_text(strip=True),
            "status": entity_status.get_text(strip=True),
            "type": entity_type.get_text(strip=True),
            "location": entity_location.get_text(strip=True)
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "ABN details retrieved successfully.",
                "data": data
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )
