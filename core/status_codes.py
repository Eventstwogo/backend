# from datetime import datetime, timezone
# from typing import Any, Optional

# from fastapi import HTTPException
# from fastapi.encoders import jsonable_encoder
# from fastapi.responses import JSONResponse
# from starlette.requests import Request

# from core.logging_config import Logging
# from core.request_context import request_context


# def api_response(
#     status_code: int,
#     message: str,
#     data: Optional[Any] = None,
#     log_error: bool = False,
# ) -> JSONResponse:
#     """
#     Clean and unified API response handler without request dependency.
#     """
#     timestamp = datetime.now(timezone.utc).isoformat()

#     # Try to get method/path from request context
#     try:
#         request: Request = request_context.get()
#         method: str | None = request.method
#         path: str | None = request.url.path
#     except Exception:
#         method = None
#         path = None

#     response_body: dict[str, Any] = {
#         "statusCode": status_code,
#         "message": message,
#         "timestamp": timestamp,
#         "method": method,
#         "path": path,
#     }

#     if data is not None:
#         response_body["data"] = jsonable_encoder(obj=data)

#     log_data: dict[str, Any] = {
#         "message": message,
#         "data": data if data else None,
#         "method": method,
#         "path": path,
#     }

#     if log_error or status_code >= 400:
#         Logging.error(log_data)
#     else:
#         Logging.info(log_data["message"])

#     # For 400+ status codes, raise HTTPException
#     if status_code >= 400 and status_code < 500:
#         raise HTTPException(status_code=status_code, detail=response_body)

#     # For 200 and 500 series, return JSONResponse
#     return JSONResponse(status_code=status_code, content=response_body)



import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException


class StatusCode(Enum):
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    EXISTS = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500


class APIResponse:
    @staticmethod
    def response(
        status_code: StatusCode,
        message: str,
        data: Optional[Any] = None,
        log_error: bool = False,
    ) -> Dict[str, Any]:
        response = {
            "status_code": status_code.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if data is not None:
            response["data"] = data

        log_message = (
            f"API Response - Code: {status_code.value}, Message: {message}"
        )
        if data:
            log_message += f", Data: {data}"

        logger = logging.getLogger(__name__)
        if log_error or status_code.value >= 400:
            logger.error(log_message)
        else:
            logger.info(log_message)

        if status_code.value >= 400:
            raise HTTPException(status_code=status_code.value, detail=message)

        return response
