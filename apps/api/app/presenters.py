from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel

from src.contracts import (
    CompanyDirectoryPage,
    CompanyFiltersDTO,
    CompanyInfoDTO,
    CompanySearchResult,
    HealthSnapshot,
    KPIBundle,
    RefreshStatusDTO,
    SectorDetailDTO,
    SectorDirectoryDTO,
    StatementMatrix,
    StatementSummaryDTO,
)
from src.startup import StartupIssue


class StartupIssuePayload(BaseModel):
    severity: str
    code: str
    message: str
    path: str | None = None


class ErrorBodyPayload(BaseModel):
    code: str
    message: str


class ErrorResponsePayload(BaseModel):
    error: ErrorBodyPayload


class HealthResponsePayload(BaseModel):
    status: str
    version: str
    database_dialect: str | None = None
    required_tables: list[str]
    warnings: list[StartupIssuePayload]
    errors: list[StartupIssuePayload]


class CompanySearchResultPayload(BaseModel):
    cd_cvm: int
    company_name: str
    ticker_b3: str | None = None
    setor_analitico: str | None = None
    setor_cvm: str | None = None
    sector_name: str
    sector_slug: str
    anos_disponiveis: list[int]
    total_rows: int


class CompanyInfoPayload(BaseModel):
    cd_cvm: int
    company_name: str
    nome_comercial: str | None = None
    cnpj: str | None = None
    setor_cvm: str | None = None
    setor_analitico: str | None = None
    sector_name: str
    sector_slug: str
    company_type: str | None = None
    ticker_b3: str | None = None


class CompanyDirectoryPaginationPayload(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class CompanyDirectoryAppliedFiltersPayload(BaseModel):
    search: str
    sector: str | None = None


class CompanyDirectoryPagePayload(BaseModel):
    items: list[CompanySearchResultPayload]
    pagination: CompanyDirectoryPaginationPayload
    applied_filters: CompanyDirectoryAppliedFiltersPayload


class CompanySectorFilterPayload(BaseModel):
    sector_name: str
    sector_slug: str
    company_count: int


class CompanyFiltersPayload(BaseModel):
    sectors: list[CompanySectorFilterPayload]


class SectorSnapshotPayload(BaseModel):
    roe: float | None = None
    mg_ebit: float | None = None
    mg_liq: float | None = None


class SectorDirectoryItemPayload(BaseModel):
    sector_name: str
    sector_slug: str
    company_count: int
    latest_year: int | None = None
    snapshot: SectorSnapshotPayload


class SectorDirectoryPayload(BaseModel):
    items: list[SectorDirectoryItemPayload]


class SectorYearOverviewPayload(BaseModel):
    year: int
    roe: float | None = None
    mg_ebit: float | None = None
    mg_liq: float | None = None


class SectorCompanyMetricPayload(BaseModel):
    cd_cvm: int
    company_name: str
    ticker_b3: str | None = None
    roe: float | None = None
    mg_ebit: float | None = None
    mg_liq: float | None = None


class SectorDetailPayload(BaseModel):
    sector_name: str
    sector_slug: str
    company_count: int
    available_years: list[int]
    selected_year: int
    yearly_overview: list[SectorYearOverviewPayload]
    companies: list[SectorCompanyMetricPayload]


class TabularDataPayload(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]


class StatementMatrixPayload(BaseModel):
    cd_cvm: int
    statement_type: str
    years: list[int]
    table: TabularDataPayload
    exclude_conflicts: bool


class KPIBundlePayload(BaseModel):
    cd_cvm: int
    years: list[int]
    annual: TabularDataPayload
    quarterly: TabularDataPayload


class SummaryBlockPayload(BaseModel):
    stmt_type: str
    title: str
    table: TabularDataPayload


class StatementSummaryPayload(BaseModel):
    cd_cvm: int
    years: list[int]
    blocks: list[SummaryBlockPayload]


class RefreshStatusPayload(BaseModel):
    cd_cvm: int
    company_name: str
    source_scope: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None
    last_start_year: int | None = None
    last_end_year: int | None = None
    last_rows_inserted: int | None = None
    updated_at: str | None = None


class HealthYearCoveragePayload(BaseModel):
    year: int
    total_companies: int
    completed: int
    missing: int
    pct: float
    eta_hours: float | None = None


class HealthPriorityPayload(BaseModel):
    cd_cvm: int
    company_name: str
    risk_level: str
    priority_score: int
    missing_years_count: int
    gap_to_leader_years: int
    years_missing: list[int]
    recommended_action: str
    reason: str


class HealthSnapshotPayload(BaseModel):
    generated_at: str | None = None
    start_year: int
    end_year: int
    total_cells: int
    completed_cells: int
    missing_cells: int
    pct: float
    health_score: float
    health_status: str
    eta_hours: float | None = None
    throughput_per_hour: float | None = None
    throughput_confidence: str
    per_year: list[HealthYearCoveragePayload]
    prioritized_companies: list[HealthPriorityPayload]
    raw: dict[str, Any]


def _normalize_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _normalize_tabular_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_rows: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        normalized_rows.append({str(key): _normalize_value(value) for key, value in row.items()})
    return {
        "columns": [str(column) for column in payload.get("columns", [])],
        "rows": normalized_rows,
    }


def present_issue(issue: StartupIssue) -> StartupIssuePayload:
    return StartupIssuePayload(
        severity=issue.severity,
        code=issue.code,
        message=issue.message,
        path=issue.path,
    )


def present_company_search(rows: list[CompanySearchResult]) -> list[CompanySearchResultPayload]:
    return [CompanySearchResultPayload(**row.to_dict()) for row in rows]


def present_company_directory_page(dto: CompanyDirectoryPage) -> CompanyDirectoryPagePayload:
    payload = dto.to_dict()
    payload["items"] = [item.model_dump() for item in present_company_search(list(dto.items))]
    return CompanyDirectoryPagePayload(**payload)


def present_company_filters(dto: CompanyFiltersDTO) -> CompanyFiltersPayload:
    return CompanyFiltersPayload(**dto.to_dict())


def present_sector_directory(dto: SectorDirectoryDTO) -> SectorDirectoryPayload:
    return SectorDirectoryPayload(**dto.to_dict())


def present_sector_detail(dto: SectorDetailDTO) -> SectorDetailPayload:
    return SectorDetailPayload(**dto.to_dict())


def present_company_info(dto: CompanyInfoDTO) -> CompanyInfoPayload:
    return CompanyInfoPayload(**dto.to_dict())


def present_statement(dto: StatementMatrix) -> StatementMatrixPayload:
    payload = dto.to_dict()
    payload["table"] = _normalize_tabular_payload(payload["table"])
    return StatementMatrixPayload(**payload)


def present_kpis(dto: KPIBundle) -> KPIBundlePayload:
    payload = dto.to_dict()
    payload["annual"] = _normalize_tabular_payload(payload["annual"])
    payload["quarterly"] = _normalize_tabular_payload(payload["quarterly"])
    return KPIBundlePayload(**payload)


def present_statement_summary(dto: StatementSummaryDTO) -> StatementSummaryPayload:
    blocks = [
        SummaryBlockPayload(
            stmt_type=b.stmt_type,
            title=b.title,
            table=TabularDataPayload(**_normalize_tabular_payload(b.table.to_dict())),
        )
        for b in dto.blocks
    ]
    return StatementSummaryPayload(cd_cvm=dto.cd_cvm, years=list(dto.years), blocks=blocks)


def present_refresh_status(rows: list[RefreshStatusDTO]) -> list[RefreshStatusPayload]:
    return [RefreshStatusPayload(**row.to_dict()) for row in rows]


def present_health_snapshot(dto: HealthSnapshot) -> HealthSnapshotPayload:
    return HealthSnapshotPayload(**dto.to_dict())
