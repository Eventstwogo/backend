from contextvars import ContextVar

from fastapi import Request

# Create a ContextVar to store the current request
request_context: ContextVar[Request] = ContextVar("request_context")
