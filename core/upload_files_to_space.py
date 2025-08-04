from typing import Tuple

from botocore.exceptions import ClientError
from aiobotocore.session import get_session
from fastapi import HTTPException, UploadFile
import filetype
import mimetypes

from core.lifespan import app_settings  # Ensure this has correct configurations
from utils.logger_file import Logging


# Function to detect content type using filetype
def get_file_mime_type(file: UploadFile) -> Tuple[str, bytes]:
    """
    Determines the MIME type of an uploaded file.

    Args:
        file (UploadFile): The uploaded file object.

    Returns:
        Tuple[str, bytes]: Detected MIME type and file content.
    """
    file_content = file.file.read()  # Read file content
    kind = filetype.guess(file_content)  # Detect type using `filetype`

    if kind:
        mime_type = kind.mime  # Exact MIME type from file content
    else:
        mime_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    file.file.seek(0)  # Reset file pointer after reading

    return mime_type, file_content


# Async function to upload a file to Digital Ocean Spaces (S3-compatible storage)
async def upload_file_to_s3(
    file_content: bytes, file_path: str, file_type: str = None
) -> str:
    """
    Asynchronously uploads a file to Digital Ocean Spaces and returns its public URL.

    Args:
        file_content (bytes): The binary content of the file.
        file_path (str): The path within the Spaces bucket (e.g., "folder/filename.jpg").
        file_type (str, optional): The MIME type of the file. If not provided, auto-detect it.

    Returns:
        str: The public URL of the uploaded file.
    """
    if file_type == None:
        content_type, file_content = get_file_mime_type(file_content)
    else:
        content_type = file_type

    session = get_session()  # Correct session creation
    async with session.create_client(
        "s3",
        region_name=app_settings.spaces_region_name,
        endpoint_url=app_settings.spaces_endpoint_url,
        aws_access_key_id=app_settings.spaces_access_key,
        aws_secret_access_key=app_settings.spaces_secret_key,
    ) as s3_client:
        try:
            # Upload the file to Digital Ocean Spaces
            await s3_client.put_object(
                Bucket=app_settings.spaces_bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type,
                ACL="public-read",  # Ensures file is publicly accessible
            )

            # Construct the public URL
            file_url = f"{app_settings.spaces_endpoint_url}/{app_settings.spaces_bucket_name}/{file_path}"
            Logging.info(f"File uploaded successfully: {file_url}")
            return file_url

        except ClientError as e:
            Logging.error(f"S3 Client Error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to Digital Ocean Spaces: {str(e)}",
            )

        except Exception as e:
            Logging.error(f"Unexpected Error: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while uploading the file.",
            )
