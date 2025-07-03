# Standard Library Imports
import asyncio
import functools
import time
from typing import Any, Callable

# Third-Party Library Imports
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Application-Specific Imports
from core.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Any:
        """Middleware to add execution time to the response headers."""
        start_time = time.process_time()
        response = await call_next(request)
        process_time = time.process_time() - start_time
        response.headers["API-Execution-Time"] = f"{process_time:.4f} seconds"
        return response


def measure_sync_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure the execution time of a synchronous function."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.process_time()
        result = func(*args, **kwargs)
        execution_time = time.process_time() - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result

    return wrapper


def measure_async_execution_time(
    func: Callable[..., Any],
) -> Callable[..., Any]:
    """Decorator to measure the execution time of an asynchronous function."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.process_time()
        result = await func(*args, **kwargs)
        execution_time = time.process_time() - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result

    return wrapper


def measure_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Universal decorator to measure execution time of both sync and
    async functions.

    It detects if the function is asynchronous and applies the appropriate
    timing decorator.
    """
    return (
        measure_async_execution_time(func)
        if asyncio.iscoroutinefunction(func)
        else measure_sync_execution_time(func)
    )


def retry_on_exception(retries: int = 3, delay: int = 2) -> Callable[..., Any]:
    """
    Decorator to retry an asynchronous function call if it raises an exception.

    Args:
        retries (int): Number of retry attempts.
        delay (int): Delay in seconds between retries.

    Returns:
        Callable: Wrapped function that will retry on exception.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, retries + 1):
                try:
                    logger.info(
                        f"Attempt {attempt} of {retries} for {func.__name__}"
                    )
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {e}"
                    )
                    if attempt < retries:
                        logger.info(
                            f"Retrying {func.__name__} in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {retries} attempts failed for {func.__name__}"
                        )
                        raise

        return wrapper

    return decorator
