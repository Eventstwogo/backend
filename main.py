

# import os
# from typing import Awaitable, Callable

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.gzip import GZipMiddleware
# from fastapi.staticfiles import StaticFiles
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.responses import Response

# from core.config_log import setup_logging
# setup_logging()

# from api.v1.routes import api_router
# from core.config import settings
# from core.request_context import request_context
# from core.lifespan import lifespan
# from utils.execution_time import ExecutionTimeMiddleware


# def create_app() -> FastAPI:
#     app: FastAPI = FastAPI(
#         title=settings.APP_NAME,
#         openapi_url="/shoppersky.json",
#         version="0.1.0",
#         description="Shoppersky Service API",
#         lifespan=lifespan,
#         debug=settings.ENVIRONMENT == "development",
#     )

#     @app.get(path="/", tags=["System"])
#     async def root() -> dict[str, str]:
#         return {
#             "message": "Welcome to Shoppersky API Services",
#             "version": "1.0.0",
#             "docs_url": "/docs",
#             "redoc_url": "/redoc",
#         }

#     @app.get(path="/health", tags=["System"])
#     async def health_check() -> dict[str, str]:
#         return {"status": "healthy", "message": "API is running fine!"}

#     app.include_router(router=api_router)

#     return app


# app: FastAPI = create_app()

# origins = settings.CORS_ORIGINS
# print("CORS Origins: ", origins)

# app.add_middleware(
#     middleware_class=CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# class RequestLoggingMiddleware(BaseHTTPMiddleware):
#     async def dispatch(
#         self,
#         request: Request,
#         call_next: Callable[[Request], Awaitable[Response]],
#     ) -> Response:
#         method: str = request.method
#         path: str = request.url.path
#         request_context.set(request)  # store current request globally
#         response: Response = await call_next(request)
#         response.headers["X-Method"] = method
#         response.headers["X-Path"] = path
#         return response


# # Mount media directory
# os.makedirs(name=settings.MEDIA_ROOT, exist_ok=True)
# app.mount(
#     path="/media", app=StaticFiles(directory=settings.MEDIA_ROOT), name="media"
# )

# app.add_middleware(
#     middleware_class=GZipMiddleware, minimum_size=1000
# )
# app.add_middleware(ExecutionTimeMiddleware)
# app.add_middleware(middleware_class=RequestLoggingMiddleware)


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(
#         app="main:app",
#         host=settings.APP_HOST,
#         port=settings.APP_PORT,
#         reload=True,
#         reload_delay=15,
#     )



# main.py

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Awaitable, Callable

from api.v1.routes import api_router
from core.config import settings
from core.config_log import setup_logging
from core.request_context import request_context
from core.lifespan import lifespan
from utils.execution_time import ExecutionTimeMiddleware

setup_logging()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Shoppersky Service API",
        openapi_url="/shoppersky.json",
        lifespan=lifespan,
        debug=settings.ENVIRONMENT == "development",
        redirect_slashes=True,
    )

    @app.get("/", tags=["System"])
    async def root() -> dict[str, str]:
        return {
            "message": "Welcome to Shoppersky API Services",
            "version": "1.0.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        }

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "message": "API is running fine!"}

    app.include_router(api_router)
    return app


app = create_app()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_context.set(request)
        response = await call_next(request)
        response.headers["X-Method"] = request.method
        response.headers["X-Path"] = request.url.path
        return response

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ExecutionTimeMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Static files
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

# Dev mode runner
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app="main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        reload_delay=15,
    )
