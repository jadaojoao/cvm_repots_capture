from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.dependencies import ApiError, ServiceUnavailableError, serialize_error
from apps.api.app.presenters import ErrorResponsePayload
from apps.api.app.routes.companies import router as companies_router
from apps.api.app.routes.health import router as health_router
from apps.api.app.routes.status import router as status_router
from src.read_service import CVMReadService
from src.settings import AppSettings, get_settings as get_shared_settings

log = logging.getLogger("cvm.api")


def create_app(
    *,
    settings: AppSettings | None = None,
    read_service: CVMReadService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_shared_settings()
    resolved_service = read_service or CVMReadService(settings=resolved_settings)

    app = FastAPI(
        title="CVM V2 API",
        version="v2-phase1",
        description="API read-only da Fase 1 da V2, reaproveitando o nucleo headless da V1.",
    )
    app.state.settings = resolved_settings
    app.state.read_service = resolved_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            log.exception("request_failed method=%s path=%s elapsed_ms=%.2f", request.method, request.url.path, elapsed_ms)
            raise
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        log.info(
            "request_completed method=%s path=%s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=serialize_error(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorResponsePayload(
            error={
                "code": "validation_error",
                "message": "A requisicao nao passou na validacao HTTP.",
            }
        )
        payload = error.model_dump()
        payload["details"] = exc.errors()
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected_api_error", exc_info=exc)
        fallback = ServiceUnavailableError("Falha operacional ao processar a requisicao.")
        return JSONResponse(status_code=fallback.status_code, content=serialize_error(fallback))

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": "CVM V2 API", "docs": "/docs", "openapi": "/openapi.json"}

    app.include_router(health_router)
    app.include_router(companies_router)
    app.include_router(status_router)
    return app


app = create_app()
