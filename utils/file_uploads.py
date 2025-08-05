import uuid
from typing import Optional
from urllib.parse import urljoin

from fastapi import HTTPException, UploadFile, status

from core.config import settings
from core.logging_config import get_logger
from utils.format_validators import is_valid_filename, sanitize_filename
from utils.secure_filename import secure_filename
from utils.upload_files import delete_file_from_s3, upload_file_to_s3

logger = get_logger(__name__)


async def save_uploaded_file(
    file: UploadFile,
    relative_sub_path: str,
) -> str | None:
    """
    Validates and uploads a file to DigitalOcean Spaces.
    Returns the relative path for DB/API usage.
    """
    if not file or not file.filename:
        return None

    if not is_valid_filename(file.filename):
        file.filename = sanitize_filename(file.filename)

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

    cleaned_filename = secure_filename(file.filename)
    short_suffix = uuid.uuid4().hex[:8]
    safe_filename = f"{short_suffix}_{cleaned_filename}"

    relative_sub_path = relative_sub_path.strip("/\\")
    relative_path = f"{relative_sub_path}/{safe_filename}".strip("/")

    try:
        await upload_file_to_s3(
            file_content=content,
            file_path=relative_path,
            file_type=file.content_type,
        )
    except Exception as e:
        logger.exception("Failed to upload file to Spaces")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload file: {str(e)}"
        )

    return relative_path


async def remove_file_if_exists(relative_path: str) -> None:
    """
    Deletes a file from DigitalOcean Spaces if it exists.
    """
    if not relative_path:
        return

    try:
        await delete_file_from_s3(relative_path)
        logger.info("Successfully deleted file: %s", relative_path)
    except Exception as e:
        logger.warning("Failed to delete file '%s': %s", relative_path, e)


def remove_file_if_exists_sync(relative_path: str) -> None:
    """
    Synchronous wrapper for remove_file_if_exists.
    Creates a new event loop if none exists.
    """
    if not relative_path:
        return

    try:
        import asyncio

        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            asyncio.create_task(remove_file_if_exists(relative_path))
        except RuntimeError:
            # No event loop running, create a new one
            asyncio.run(remove_file_if_exists(relative_path))
    except Exception as e:
        logger.warning("Failed to delete file '%s': %s", relative_path, e)


def get_media_url(relative_path: Optional[str]) -> Optional[str]:
    """
    Converts a relative path to full DigitalOcean Spaces URL.
    """
    if not relative_path or not isinstance(relative_path, str):
        return None

    if relative_path.startswith(("http://", "https://")):
        return relative_path

    relative_path = relative_path.strip().lstrip("/\\")
    if not relative_path:
        return None

    return urljoin(settings.SPACES_PUBLIC_URL.rstrip("/") + "/", relative_path)
