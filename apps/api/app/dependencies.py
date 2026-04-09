from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException, Query, Request, status

from src.read_service import CVMReadService
from src.settings import AppSettings
from src.startup import StartupReport, collect_startup_report

API_VERSION = "v2-phase1"
REQUIRED_TABLES = ("financial_reports", "companies")
SUPPORTED_STATEMENTS = frozenset({"BPA", "BPP", "DRE", "DFC", "DVA", "DMPL"})


@dataclass(frozen=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str


class NotFoundError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=message,
        )


class ServiceUnavailableError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_unavailable",
            message=message,
        )


class InvalidRequestError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_request",
            message=message,
        )


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_read_service(request: Request) -> CVMReadService:
    return request.app.state.read_service


def collect_api_startup_report(
    settings: AppSettings,
    *,
    warn_on_legacy_data: bool,
) -> StartupReport:
    return collect_startup_report(
        settings,
        require_database=True,
        required_tables=REQUIRED_TABLES,
        require_canonical_accounts=False,
        warn_on_legacy_data=warn_on_legacy_data,
    )


def ensure_api_ready(settings: AppSettings) -> StartupReport:
    report = collect_api_startup_report(settings, warn_on_legacy_data=False)
    if not report.ok:
        first_error = report.errors[0]
        raise ServiceUnavailableError(first_error.message)
    return report


def parse_years_csv(years: str | None) -> list[int]:
    if years is None:
        raise InvalidRequestError("O parametro 'years' e obrigatorio.")

    tokens = [token.strip() for token in str(years).split(",")]
    if not tokens or any(not token for token in tokens):
        raise InvalidRequestError("O parametro 'years' deve ser uma lista CSV de inteiros.")

    parsed: list[int] = []
    seen: set[int] = set()
    for token in tokens:
        try:
            year = int(token)
        except ValueError as exc:
            raise InvalidRequestError("O parametro 'years' aceita apenas inteiros.") from exc
        if year in seen:
            raise InvalidRequestError("O parametro 'years' nao pode conter valores duplicados.")
        seen.add(year)
        parsed.append(year)

    return sorted(parsed)


def years_dependency(years: str | None = Query(default=None)) -> list[int]:
    return parse_years_csv(years)


def optional_year_dependency(year: str | None = Query(default=None)) -> int | None:
    if year is None:
        return None

    token = str(year).strip()
    if not token:
        raise InvalidRequestError("O parametro 'year' aceita um unico inteiro positivo.")

    try:
        parsed = int(token)
    except ValueError as exc:
        raise InvalidRequestError("O parametro 'year' aceita um unico inteiro positivo.") from exc

    if parsed <= 0:
        raise InvalidRequestError("O parametro 'year' aceita um unico inteiro positivo.")

    return parsed


def parse_company_ids_csv(
    raw_ids: str | None,
    *,
    minimum: int = 1,
) -> list[int]:
    if raw_ids is None:
        raise InvalidRequestError("O parametro 'ids' e obrigatorio.")

    tokens = [token.strip() for token in str(raw_ids).split(",")]
    if not tokens or any(not token for token in tokens):
        raise InvalidRequestError("O parametro 'ids' deve ser uma lista CSV de inteiros.")

    parsed: list[int] = []
    seen: set[int] = set()
    for token in tokens:
        try:
            company_id = int(token)
        except ValueError as exc:
            raise InvalidRequestError("O parametro 'ids' aceita apenas inteiros.") from exc
        if company_id in seen:
            raise InvalidRequestError("O parametro 'ids' nao pode conter valores duplicados.")
        seen.add(company_id)
        parsed.append(company_id)

    if len(parsed) < minimum:
        raise InvalidRequestError(f"O parametro 'ids' exige ao menos {minimum} empresa(s).")

    return parsed


def company_ids_dependency(ids: str | None = Query(default=None)) -> list[int]:
    return parse_company_ids_csv(ids, minimum=2)


def statement_dependency(stmt: str = Query(..., description="Tipo de demonstracao.")) -> str:
    normalized = str(stmt).strip().upper()
    if normalized not in SUPPORTED_STATEMENTS:
        allowed = ", ".join(sorted(SUPPORTED_STATEMENTS))
        raise InvalidRequestError(f"Parametro 'stmt' invalido. Use um de: {allowed}.")
    return normalized


def limit_dependency(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Numero maximo de resultados retornados.",
    ),
) -> int:
    return int(limit)


def coerce_company(cd_cvm: int, service: CVMReadService) -> None:
    if service.get_company_info(cd_cvm) is None:
        raise NotFoundError(f"Empresa {cd_cvm} nao encontrada.")


def serialize_error(exc: ApiError) -> dict[str, dict[str, str]]:
    return {"error": {"code": exc.code, "message": exc.message}}


def serialize_issue_list(issues: Iterable) -> list[dict[str, str | None]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "path": issue.path,
        }
        for issue in issues
    ]
