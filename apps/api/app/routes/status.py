from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from apps.api.app.dependencies import ensure_api_ready, get_read_service, get_settings
from apps.api.app.presenters import (
    HealthSnapshotPayload,
    RefreshStatusPayload,
    present_health_snapshot,
    present_refresh_status,
)
from src.read_service import CVMReadService

router = APIRouter(tags=["operations"])


@router.get(
    "/refresh-status",
    response_model=list[RefreshStatusPayload],
    summary="Lista o status operacional do refresh por empresa.",
)
def get_refresh_status(
    request: Request,
    cd_cvm: int | None = Query(default=None, description="Filtra por codigo CVM."),
    service: CVMReadService = Depends(get_read_service),
) -> list[RefreshStatusPayload]:
    ensure_api_ready(get_settings(request))
    return present_refresh_status(service.list_refresh_status(cd_cvm=cd_cvm))


@router.get(
    "/base-health",
    response_model=HealthSnapshotPayload,
    summary="Retorna o snapshot de saude e cobertura da base.",
)
def get_base_health(
    request: Request,
    start_year: int = Query(..., description="Ano inicial da janela analisada."),
    end_year: int = Query(..., description="Ano final da janela analisada."),
    force_refresh: bool = Query(default=False, description="Ignora cache local de health."),
    service: CVMReadService = Depends(get_read_service),
) -> HealthSnapshotPayload:
    ensure_api_ready(get_settings(request))
    snapshot = service.get_health_snapshot(
        start_year=start_year,
        end_year=end_year,
        force_refresh=force_refresh,
    )
    return present_health_snapshot(snapshot)
