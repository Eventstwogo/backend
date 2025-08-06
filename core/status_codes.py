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
