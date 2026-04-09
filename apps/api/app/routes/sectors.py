from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from apps.api.app.dependencies import (
    InvalidRequestError,
    NotFoundError,
    ensure_api_ready,
    get_read_service,
    get_settings,
    optional_year_dependency,
)
from apps.api.app.presenters import (
    SectorDetailPayload,
    SectorDirectoryPayload,
    present_sector_detail,
    present_sector_directory,
)
from src.read_service import CVMReadService

router = APIRouter(tags=["sectors"])


@router.get(
    "/sectors",
    response_model=SectorDirectoryPayload,
    summary="Retorna o hub setorial com snapshot agregado por setor.",
)
def list_sectors(
    request: Request,
    service: CVMReadService = Depends(get_read_service),
) -> SectorDirectoryPayload:
    ensure_api_ready(get_settings(request))
    return present_sector_directory(service.list_sectors())


@router.get(
    "/sectors/{sector_slug}",
    response_model=SectorDetailPayload,
    summary="Retorna o detalhe de um setor com serie anual e empresas do ano selecionado.",
)
def get_sector_detail(
    sector_slug: str,
    request: Request,
    year: int | None = Depends(optional_year_dependency),
    service: CVMReadService = Depends(get_read_service),
) -> SectorDetailPayload:
    ensure_api_ready(get_settings(request))
    try:
        detail = service.get_sector_detail(sector_slug=sector_slug, year=year)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc

    if detail is None:
        raise NotFoundError(f"Setor '{sector_slug}' nao encontrado.")

    return present_sector_detail(detail)
