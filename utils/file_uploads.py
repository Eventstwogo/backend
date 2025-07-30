import os
import uuid
from typing import Optional
from urllib.parse import urljoin

import aiofiles
from fastapi import HTTPException, UploadFile, status

from core.config import settings
from core.logging_config import get_logger
from utils.secure_filename import secure_filename
from utils.format_validators import is_valid_filename

logger = get_logger(__name__)

# async def save_uploaded_file(file: UploadFile, sub_path: str) -> Optional[str]:
#     try:
#         # Ensure the file has content
#         if not file.filename or not file.size:
#             logger.warning(f"Empty or invalid file: {file.filename}")
#             return None

#         # Validate file type (optional)
#         if not file.content_type.startswith("image/"):
#             logger.warning(f"Invalid file type for {file.filename}: {file.content_type}")
#             return None

#         # Define storage path (e.g., local storage or cloud storage like S3)
#         file_extension = file.filename.split(".")[-1]
#         file_name = f"{uuid.uuid4()}.{file_extension}"
#         file_path = os.path.join("uploads", sub_path, file_name)

#         # Create directory if it doesn't exist
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)

#         # Save the file
#         with open(file_path, "wb") as f:
#             content = await file.read()
#             f.write(content)

#         # Return the URL or path (adjust based on your storage setup)
#         file_url = f"/{file_path}"  # Example for local storage; modify for S3 or other storage
#         logger.info(f"File saved: {file_url}")
#         return file_url

#     except Exception as e:
#         logger.error(f"Error saving file {file.filename}: {str(e)}")
#         return None


async def save_uploaded_file(
    file: UploadFile,
    relative_sub_path: str,
) -> str | None:
    """
    Validates and saves an uploaded file to the media directory.
    Returns the relative path to the file for DB/API usage.
    """
    if not file or not file.filename:
        return None
 
    if not is_valid_filename(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file name.",
        )
 
    if file.content_type not in settings.ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type.",
        )
 
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the limit of {settings.MAX_UPLOAD_SIZE} bytes.",
        )
 
    media_root = str(settings.MEDIA_ROOT)
    relative_sub_path = relative_sub_path.strip("/\\")
    directory_path = os.path.join(media_root, relative_sub_path)
    os.makedirs(directory_path, exist_ok=True)
 
    # Secure and clean filename
    original_filename = os.path.basename(file.filename)
    cleaned_filename = secure_filename(original_filename)
 
    # Optional: Add a short hash if name uniqueness is important
    short_suffix = uuid.uuid4().hex[:8]
    safe_filename = f"{short_suffix}_{cleaned_filename}"
 
    file_path = os.path.join(directory_path, safe_filename)
 
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(content)
    except Exception as e:
        logger.exception("File save failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file. Reason: {str(e)}",
        ) from e
 
    relative_url = os.path.relpath(file_path, media_root).replace("\\", "/")
    return relative_url

def remove_file_if_exists(relative_path: str) -> None:
    """
    Deletes a file relative to MEDIA_ROOT if it exists.
    """
    media_root = str(settings.MEDIA_ROOT)
    full_path = os.path.join(media_root, relative_path.lstrip("/\\"))

    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
    except Exception as e:
        logger.warning(f"Failed to delete file '{relative_path}': {e}")


def get_media_url(relative_path: Optional[str]) -> str:
    """
    Converts a relative media path to a full URL for frontend usage.
    Returns a default image URL if path is None or invalid.
    """
    if not relative_path or not isinstance(relative_path, str):
        return settings.DEFAULT_MEDIA_URL

    relative_path = relative_path.strip().lstrip("/\\")
    if not relative_path:
        return settings.DEFAULT_MEDIA_URL

    return urljoin(settings.MEDIA_BASE_URL.rstrip("/") + "/", relative_path)


def get_media_file_path(relative_path: Optional[str]) -> Optional[str]:
    """
    Converts a relative path to a full filesystem path for backend usage.
    Returns None if the input is empty or invalid.
    """
    if not relative_path or not isinstance(relative_path, str):
        return None

    relative_path = relative_path.strip().lstrip("/\\")
    if not relative_path:
        return None

    return os.path.join(settings.MEDIA_ROOT, relative_path)
