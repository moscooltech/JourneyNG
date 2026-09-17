"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.api.v1.health import router as health_router
from app.config.settings import settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger, new_request_id, request_id_ctx
from app.websocket.handlers import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level=settings.log_level, json_output=not settings.is_development)
    logger.info("startup", env=settings.app_env)
    yield
    from app.infrastructure.database import dispose_engine
    from app.infrastructure.redis import close_redis

    await dispose_engine()
    await close_redis()
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="JourneyNG API",
        version="1.0.0",
        description="Consent-based journey sharing. Share your journey, not just your location.",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request ID middleware ---
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = new_request_id()
        request_id_ctx.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # --- Structured access logging (no GPS/tokens in logs) ---
    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next):
        import time

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request",
            route=request.url.path,
            method=request.method,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response

    # --- Error envelope ---
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code.value,
                    "message": exc.message,
                    "request_id": request_id_ctx.get(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id_ctx.get(),
                }
            },
        )

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(health_router)

    # --- WebSocket ---
    app.include_router(ws_router)

    return app


app = create_app()
