import mimetypes
from typing import Optional, Tuple

import aioboto3
import filetype
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


def get_file_mime_type(file: UploadFile) -> Tuple[str, bytes]:
    """
    Determine the MIME type of an uploaded file using file content,
    with a fallback to mimetypes based on the filename.

    Args:
        file (UploadFile): The uploaded file object.

    Returns:
        Tuple[str, bytes]: MIME type string and the file's raw binary content.
    """
    file_content = file.file.read()
    kind = filetype.guess(file_content)

    if file.filename is not None:
        mime_type = (
            kind.mime if kind else mimetypes.guess_type(file.filename)[0]
        ) or "application/octet-stream"
    else:
        mime_type = kind.mime if kind else "application/octet-stream"

    file.file.seek(0)
    return mime_type, file_content


def get_mime_type_from_bytes(file_content: bytes) -> str:
    """
    Guess the MIME type of a file from its raw bytes.

    Args:
        file_content (bytes): Raw file data.

    Returns:
        str: The detected MIME type.
    """
    kind = filetype.guess(file_content)
    return kind.mime if kind else "application/octet-stream"


async def upload_file_to_s3(
    file_content: bytes,
    file_path: str,
    file_type: Optional[str] = None,
) -> str:
    """
    Upload a file asynchronously to DigitalOcean Spaces (S3-compatible).

    Args:
        file_content (bytes): The raw binary data of the file.
        file_path (str): The path where the file will be stored in the bucket.
        file_type (Optional[str]): MIME type of the file. If not provided,
        it's auto-detected.

    Returns:
        str: Public URL to access the uploaded file.

    Raises:
        HTTPException: Raised if the upload fails.
    """
    content_type = file_type or get_mime_type_from_bytes(file_content)

    session = aioboto3.Session()
    async with session.client(
        "s3",
        region_name=settings.SPACES_REGION_NAME,
        endpoint_url=settings.SPACES_ENDPOINT_URL,
        aws_access_key_id=settings.SPACES_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SPACES_SECRET_ACCESS_KEY,
    ) as s3_client:
        try:
            await s3_client.put_object(
                Bucket=settings.SPACES_BUCKET_NAME,
                Key=file_path,
                Body=file_content,
                ContentType=content_type,
                ACL="public-read",
            )

            file_url = (
                f"{settings.SPACES_ENDPOINT_URL}/"
                f"{settings.SPACES_BUCKET_NAME}/{file_path}"
            )
            logger.info(
                "File uploaded successfully",
                extra={
                    "file_url": file_url,
                    "file_path": file_path,
                    "content_type": content_type,
                },
            )
            return file_url

        except ClientError as e:
            logger.error(
                "S3 upload error",
                exc_info=True,
                extra={"error": str(e), "file_path": file_path},
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )
        except Exception as e:
            logger.error(
                "Unexpected error during upload",
                exc_info=True,
                extra={"error": str(e), "file_path": file_path},
            )
            raise HTTPException(
                status_code=500, detail="Unexpected error during file upload."
            )


async def delete_file_from_s3(
    file_path: str, delete_folder: bool = False
) -> bool:
    """
    Delete a file or all files under a folder prefix in DigitalOcean Spaces.

    Args:
        file_path (str): The S3 key or prefix to delete.
        delete_folder (bool): If True, deletes all files under the
        folder prefix.

    Returns:
        bool: True if deletion was successful, False if no files matched.

    Raises:
        HTTPException: Raised if deletion fails.
    """
    session = aioboto3.Session()
    async with session.client(
        "s3",
        region_name=settings.SPACES_REGION_NAME,
        endpoint_url=settings.SPACES_ENDPOINT_URL,
        aws_access_key_id=settings.SPACES_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SPACES_SECRET_ACCESS_KEY,
    ) as s3_client:
        try:
            if delete_folder:
                prefix = file_path.rstrip("/") + "/"
                logger.info(f"Deleting all objects under folder: {prefix}")
                continuation_token = None
                deleted_any = False

                while True:
                    list_kwargs = {
                        "Bucket": settings.SPACES_BUCKET_NAME,
                        "Prefix": prefix,
                        "MaxKeys": 1000,
                    }
                    if continuation_token:
                        list_kwargs["ContinuationToken"] = continuation_token

                    response = await s3_client.list_objects_v2(**list_kwargs)
                    contents = response.get("Contents", [])

                    if not contents:
                        break

                    delete_keys = [{"Key": obj["Key"]} for obj in contents]
                    await s3_client.delete_objects(
                        Bucket=settings.SPACES_BUCKET_NAME,
                        Delete={"Objects": delete_keys},
                    )
                    logger.info(
                        f"Deleted {len(delete_keys)} files from {prefix}"
                    )
                    deleted_any = True

                    if not response.get("IsTruncated"):
                        break
                    continuation_token = response.get("NextContinuationToken")

                return deleted_any

            else:
                await s3_client.delete_object(
                    Bucket=settings.SPACES_BUCKET_NAME,
                    Key=file_path,
                )
                logger.info(f"File deleted: {file_path}")
                return True

        except ClientError as e:
            logger.error(f"S3 deletion error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {e}")
            raise HTTPException(
                status_code=500, detail="Unexpected error during file deletion."
            )
