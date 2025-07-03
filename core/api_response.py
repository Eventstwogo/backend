from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.requests import Request

from core.logging_config import get_logger
from core.request_context import request_context

logger = get_logger("api_response")


def api_response(
    status_code: int,
    message: str,
    data: Optional[Any] = None,
    log_error: bool = False,
    suppress_raise: bool = False,
) -> JSONResponse:
    """
    Clean and unified API response handler without request dependency.
    """

    timestamp = datetime.now(timezone.utc).isoformat()

    # Retrieve request context (if available)
    try:
        request: Request = request_context.get()
        method: Optional[str] = request.method
        path: Optional[str] = request.url.path
    except Exception:
        method = None
        path = None

    # Construct response payload
    response_body: dict[str, Any] = {
        "statusCode": status_code,
        "message": message,
        "timestamp": timestamp,
        "method": method,
        "path": path,
    }

    if data is not None:
        response_body["data"] = jsonable_encoder(data)

    # Prepare log metadata
    log_payload = {
        "status_code": status_code,
        "message": message,
        "method": method,
        "path": path,
        "data": data if data is not None else None,
    }

    # Logging based on status or flag
    if log_error or status_code >= 400:
        logger.error(log_payload)
    else:
        logger.info(log_payload)

    # Raise HTTPException for client-side errors (400–499)
    if 400 <= status_code < 500 and not suppress_raise:
        raise HTTPException(status_code=status_code, detail=response_body)

    # Return normal response for other codes
    return JSONResponse(status_code=status_code, content=response_body)
