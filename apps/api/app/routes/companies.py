from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from apps.api.app.dependencies import (
    NotFoundError,
    coerce_company,
    ensure_api_ready,
    get_read_service,
    get_settings,
    limit_dependency,
    statement_dependency,
    years_dependency,
)
from apps.api.app.presenters import (
    CompanyInfoPayload,
    CompanySearchResultPayload,
    KPIBundlePayload,
    StatementMatrixPayload,
    present_company_info,
    present_company_search,
    present_kpis,
    present_statement,
)
from src.read_service import CVMReadService

router = APIRouter(tags=["companies"])


@router.get(
    "/companies",
    response_model=list[CompanySearchResultPayload],
    summary="Busca empresas disponiveis na base.",
)
def list_companies(
    request: Request,
    search: str = Query(default="", description="Filtro livre por nome, ticker ou codigo CVM."),
    limit: int = Depends(limit_dependency),
    service: CVMReadService = Depends(get_read_service),
) -> list[CompanySearchResultPayload]:
    ensure_api_ready(get_settings(request))
    return present_company_search(service.search_companies(search=search)[:limit])


@router.get(
    "/companies/{cd_cvm}",
    response_model=CompanyInfoPayload,
    summary="Retorna os metadados principais de uma empresa.",
)
def get_company(
    cd_cvm: int,
    request: Request,
    service: CVMReadService = Depends(get_read_service),
) -> CompanyInfoPayload:
    ensure_api_ready(get_settings(request))
    info = service.get_company_info(cd_cvm)
    if info is None:
        raise NotFoundError(f"Empresa {cd_cvm} nao encontrada.")
    return present_company_info(info)


@router.get(
    "/companies/{cd_cvm}/years",
    response_model=list[int],
    summary="Lista os anos disponiveis para a empresa.",
)
def get_company_years(
    cd_cvm: int,
    request: Request,
    service: CVMReadService = Depends(get_read_service),
) -> list[int]:
    ensure_api_ready(get_settings(request))
    coerce_company(cd_cvm, service)
    return service.get_available_years(cd_cvm)


@router.get(
    "/companies/{cd_cvm}/statements",
    response_model=StatementMatrixPayload,
    summary="Retorna a demonstracao financeira em formato tabular.",
)
def get_company_statement(
    cd_cvm: int,
    request: Request,
    stmt: str = Depends(statement_dependency),
    years: list[int] = Depends(years_dependency),
    service: CVMReadService = Depends(get_read_service),
) -> StatementMatrixPayload:
    ensure_api_ready(get_settings(request))
    coerce_company(cd_cvm, service)
    matrix = service.get_statement_matrix(cd_cvm=cd_cvm, years=years, stmt_type=stmt)
    return present_statement(matrix)


@router.get(
    "/companies/{cd_cvm}/kpis",
    response_model=KPIBundlePayload,
    summary="Retorna os bundles anuais e trimestrais de KPIs.",
)
def get_company_kpis(
    cd_cvm: int,
    request: Request,
    years: list[int] = Depends(years_dependency),
    service: CVMReadService = Depends(get_read_service),
) -> KPIBundlePayload:
    ensure_api_ready(get_settings(request))
    coerce_company(cd_cvm, service)
    bundle = service.get_kpi_bundle(cd_cvm=cd_cvm, years=years)
    return present_kpis(bundle)
