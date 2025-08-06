# utils/exception_handlers.py

from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.api_response import api_response
from core.logging_config import get_logger

# Scoped logger for this module
logger = get_logger(__name__)


def handle_general_exception(e: Exception) -> JSONResponse:
    """
    Handles unhandled server-side exceptions.
    Logs and returns a standard API response.
    """
    return api_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=f"Something went wrong. {e}",
        log_error=True,
    )


def handle_http_exception(e: HTTPException) -> JSONResponse:
    """
    Converts HTTPException into standard API error response.
    """
    return api_response(
        status_code=e.status_code, message=str(e.detail), log_error=True
    )


def handle_not_found(entity_name: str = "Item") -> JSONResponse:
    """
    Returns a 404 response for missing resources using API format.
    """
    msg = f"{entity_name} not found."
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND, message=msg, log_error=True
    )


async def handle_422_exception(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handles Pydantic validation errors raised at runtime.
    """
    logger.warning("Validation error on %s: %s", request.url, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "statusCode": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation error",
            "details": exc.errors(),
            "timestamp": request.scope.get(
                "timestamp"
            ),  # optional if you're tracking it
            "method": request.method,
            "path": request.url.path,
        },
    )


async def handle_404_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handles unmatched routes or explicit 404s at the application level.
    Includes details from the HTTPException if available.
    """
    # If it's not a 404, re-raise to let FastAPI handle it
    if exc.status_code != status.HTTP_404_NOT_FOUND:
        raise exc

    logger.warning(
        "404 Not Found: %s | Detail: %s",
        request.url,
        getattr(exc, "detail", None),
    )
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message=(
            str(exc.detail)
            if getattr(exc, "detail", None)
            else "Resource not found."
        ),
        log_error=False,
        suppress_raise=True,  # prevents raising inside handler
    )


def exception_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for endpoints to standardize exception handling.
    Automatically logs and returns API-formatted responses.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException as he:
            raise he  # Let FastAPI handle HTTP exceptions
        except Exception as e:
            return handle_general_exception(e)

    return wrapper
