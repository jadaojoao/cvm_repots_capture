from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from apps.api.app.dependencies import (
    API_VERSION,
    REQUIRED_TABLES,
    collect_api_startup_report,
    get_read_service,
)
from apps.api.app.presenters import HealthResponsePayload, present_issue
from src.read_service import CVMReadService

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponsePayload,
    summary="Retorna o healthcheck da API.",
)
def get_health(
    request: Request,
    service: CVMReadService = Depends(get_read_service),
) -> JSONResponse:
    settings = request.app.state.settings
    report = collect_api_startup_report(settings, warn_on_legacy_data=True)
    payload = HealthResponsePayload(
        status="ok" if report.ok else "degraded",
        version=API_VERSION,
        database_dialect=service.engine.dialect.name if service.engine else None,
        required_tables=list(REQUIRED_TABLES),
        warnings=[present_issue(issue) for issue in report.warnings],
        errors=[present_issue(issue) for issue in report.errors],
    )
    status_code = 200 if report.ok else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump())
