from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import inspect, text

from desktop.services import IntelligentSelectorService
from src.contracts import (
    CompanyInfoDTO,
    CompanySearchResult,
    HealthSnapshot,
    KPIBundle,
    RefreshStatusDTO,
    StatementMatrix,
    TabularData,
)
from src.db import build_engine
from src.kpi_engine import compute_all_kpis, compute_quarterly_kpis
from src.query_layer import CVMQueryLayer
from src.settings import AppSettings, get_settings


def _parse_years(raw_years: str | None) -> tuple[int, ...]:
    if not raw_years:
        return ()
    result = []
    for value in str(raw_years).split(","):
        value = value.strip()
        if not value:
            continue
        try:
            result.append(int(value))
        except ValueError:
            continue
    return tuple(sorted(set(result)))


class CVMReadService:
    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or get_settings()
        self.engine = build_engine(self.settings)
        self.query_layer = CVMQueryLayer(engine=self.engine)
        self.operational_service = IntelligentSelectorService(settings=self.settings)

    def search_companies(self, search: str = "") -> list[CompanySearchResult]:
        df = self.query_layer.get_companies(search)
        results = []
        for _, row in df.iterrows():
            results.append(
                CompanySearchResult(
                    cd_cvm=int(row["cd_cvm"]),
                    company_name=str(row["company_name"]),
                    ticker_b3=(str(row["ticker_b3"]).strip() or None),
                    setor_analitico=(str(row["setor_analitico"]).strip() or None),
                    setor_cvm=(str(row["setor_cvm"]).strip() or None),
                    anos_disponiveis=_parse_years(row.get("anos_disponiveis")),
                    total_rows=int(row.get("total_rows") or 0),
                )
            )
        return results

    def search_companies_df(self, search: str = "") -> pd.DataFrame:
        rows = [row.to_dict() for row in self.search_companies(search)]
        return pd.DataFrame(rows)

    def get_company_info(self, cd_cvm: int) -> CompanyInfoDTO | None:
        payload = self.query_layer.get_company_info(cd_cvm)
        if not payload:
            return None
        return CompanyInfoDTO(
            cd_cvm=int(payload.get("cd_cvm") or cd_cvm),
            company_name=str(payload.get("company_name") or ""),
            nome_comercial=payload.get("nome_comercial"),
            cnpj=payload.get("cnpj"),
            setor_cvm=payload.get("setor_cvm"),
            setor_analitico=payload.get("setor_analitico"),
            company_type=payload.get("company_type"),
            ticker_b3=payload.get("ticker_b3"),
        )

    def get_company_info_dict(self, cd_cvm: int) -> dict[str, Any]:
        info = self.get_company_info(cd_cvm)
        return info.to_dict() if info else {}

    def get_available_years(self, cd_cvm: int) -> list[int]:
        return self.query_layer.get_available_years(cd_cvm)

    def get_available_statements(self, cd_cvm: int) -> list[str]:
        return self.query_layer.get_available_statements(cd_cvm)

    def get_statement_matrix(
        self,
        cd_cvm: int,
        years: list[int],
        stmt_type: str,
        *,
        exclude_conflicts: bool = True,
    ) -> StatementMatrix:
        df = self.query_layer.get_statement(
            cd_cvm=cd_cvm,
            years=years,
            stmt_type=stmt_type,
            exclude_conflicts=exclude_conflicts,
        )
        return StatementMatrix(
            cd_cvm=int(cd_cvm),
            statement_type=str(stmt_type),
            years=tuple(int(year) for year in years),
            table=TabularData.from_dataframe(df),
            exclude_conflicts=bool(exclude_conflicts),
        )

    def get_statement_dataframe(
        self,
        cd_cvm: int,
        years: list[int],
        stmt_type: str,
        *,
        exclude_conflicts: bool = True,
    ) -> pd.DataFrame:
        return self.get_statement_matrix(
            cd_cvm,
            years,
            stmt_type,
            exclude_conflicts=exclude_conflicts,
        ).to_dataframe()

    def get_kpi_bundle(self, cd_cvm: int, years: list[int]) -> KPIBundle:
        accounts = self.query_layer.get_kpi_accounts(cd_cvm, years)
        da_series = self.query_layer.get_da_from_dfc(cd_cvm, years)
        annual = compute_all_kpis(accounts, da_series)

        quarterly_accounts = self.query_layer.get_kpi_accounts_all_periods(cd_cvm, years)
        quarterly_da = self.query_layer.get_da_all_periods(cd_cvm, years)
        quarterly = compute_quarterly_kpis(quarterly_accounts, quarterly_da)

        return KPIBundle(
            cd_cvm=int(cd_cvm),
            years=tuple(int(year) for year in years),
            annual=TabularData.from_dataframe(annual),
            quarterly=TabularData.from_dataframe(quarterly),
        )

    def get_health_snapshot(
        self,
        start_year: int,
        end_year: int,
        *,
        force_refresh: bool = False,
    ) -> HealthSnapshot:
        payload = self.operational_service.build_base_health_snapshot(
            start_year=start_year,
            end_year=end_year,
            force_refresh=force_refresh,
        )
        return HealthSnapshot.from_payload(payload)

    def list_refresh_status(self, cd_cvm: int | None = None) -> list[RefreshStatusDTO]:
        if not inspect(self.engine).has_table("company_refresh_status"):
            return []

        query = text(
            """
            SELECT
                cd_cvm,
                company_name,
                source_scope,
                last_attempt_at,
                last_success_at,
                last_status,
                last_error,
                last_start_year,
                last_end_year,
                last_rows_inserted,
                updated_at
            FROM company_refresh_status
            WHERE (:cd_cvm IS NULL OR cd_cvm = :cd_cvm)
            ORDER BY company_name
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"cd_cvm": int(cd_cvm) if cd_cvm is not None else None}).mappings().all()
        return [
            RefreshStatusDTO(
                cd_cvm=int(row["cd_cvm"]),
                company_name=str(row["company_name"] or ""),
                source_scope=row.get("source_scope"),
                last_attempt_at=row.get("last_attempt_at"),
                last_success_at=row.get("last_success_at"),
                last_status=row.get("last_status"),
                last_error=row.get("last_error"),
                last_start_year=int(row["last_start_year"]) if row.get("last_start_year") is not None else None,
                last_end_year=int(row["last_end_year"]) if row.get("last_end_year") is not None else None,
                last_rows_inserted=int(row["last_rows_inserted"]) if row.get("last_rows_inserted") is not None else None,
                updated_at=row.get("updated_at"),
            )
            for row in rows
        ]
