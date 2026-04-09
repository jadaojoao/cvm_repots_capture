from __future__ import annotations

import io
import zipfile
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text

from desktop.services import IntelligentSelectorService
from src.contracts import (
    CompanyDirectoryAppliedFilters,
    CompanyDirectoryPage,
    CompanyDirectoryPagination,
    CompanyFiltersDTO,
    CompanyInfoDTO,
    CompanySectorFilterOption,
    CompanySearchResult,
    HealthSnapshot,
    KPIBundle,
    RefreshStatusDTO,
    SectorCompanyMetricDTO,
    SectorDetailDTO,
    SectorDirectoryDTO,
    SectorDirectoryItemDTO,
    SectorSnapshotDTO,
    SectorYearOverviewDTO,
    StatementMatrix,
    StatementSummaryDTO,
    SummaryBlockDTO,
    TabularData,
)
from src.statement_summary import build_general_summary_blocks
from src.db import build_engine
from src.excel_exporter import ExcelExporter, build_excel_filename
from src.kpi_engine import compute_all_kpis, compute_quarterly_kpis
from src.query_layer import CVMQueryLayer
from src.sector_taxonomy import canonical_sector_name, sector_slugify
from src.settings import AppSettings, get_settings

EXPORT_STATEMENT_TYPES = ("DRE", "BPA", "BPP", "DFC", "DVA", "DMPL")


def _parse_years(raw_years: str | None) -> tuple[int, ...]:
    if not raw_years:
        return ()
    if isinstance(raw_years, (list, tuple)):
        return tuple(sorted({int(value) for value in raw_years}))
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
        return self._build_company_results(df)

    def search_companies_df(self, search: str = "") -> pd.DataFrame:
        rows = [row.to_dict() for row in self.search_companies(search)]
        return pd.DataFrame(rows)

    def get_company_info(self, cd_cvm: int) -> CompanyInfoDTO | None:
        payload = self.query_layer.get_company_info(cd_cvm)
        if not payload:
            return None
        sector_name = canonical_sector_name(payload.get("setor_analitico"), payload.get("setor_cvm"))
        return CompanyInfoDTO(
            cd_cvm=int(payload.get("cd_cvm") or cd_cvm),
            company_name=str(payload.get("company_name") or ""),
            nome_comercial=payload.get("nome_comercial"),
            cnpj=payload.get("cnpj"),
            setor_cvm=payload.get("setor_cvm"),
            setor_analitico=payload.get("setor_analitico"),
            sector_name=sector_name,
            sector_slug=sector_slugify(sector_name),
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

    def list_companies(
        self,
        *,
        search: str = "",
        sector_slug: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CompanyDirectoryPage:
        resolved_sector_name = self._resolve_sector_slug(sector_slug)
        if sector_slug and resolved_sector_name is None:
            return self._empty_company_page(
                search=search,
                sector_slug=sector_slug,
                page=page,
                page_size=page_size,
            )

        rows_df, total_items = self.query_layer.get_companies_directory_page(
            search=search,
            sector_name=resolved_sector_name,
            page=page,
            page_size=page_size,
        )
        years_map = self.query_layer.get_company_years_map(rows_df["cd_cvm"].tolist()) if not rows_df.empty else {}
        if not rows_df.empty:
            rows_df = rows_df.copy()
            rows_df["anos_disponiveis"] = rows_df["cd_cvm"].map(lambda cd_cvm: years_map.get(int(cd_cvm), ()))

        total_pages = max(1, ((int(total_items) - 1) // int(page_size)) + 1) if total_items else 1
        pagination = CompanyDirectoryPagination(
            page=int(page),
            page_size=int(page_size),
            total_items=int(total_items),
            total_pages=int(total_pages),
            has_next=int(page) < int(total_pages),
            has_previous=int(page) > 1,
        )
        return CompanyDirectoryPage(
            items=tuple(self._build_company_results(rows_df)),
            pagination=pagination,
            applied_filters=CompanyDirectoryAppliedFilters(
                search=str(search or ""),
                sector=sector_slug,
            ),
        )

    def get_company_filters(self) -> CompanyFiltersDTO:
        df = self.query_layer.get_available_company_sectors()
        sectors = tuple(
            CompanySectorFilterOption(
                sector_name=str(row["sector_name"]),
                sector_slug=sector_slugify(row["sector_name"]),
                company_count=int(row["company_count"] or 0),
            )
            for _, row in df.iterrows()
        )
        return CompanyFiltersDTO(sectors=sectors)

    def resolve_sector_slug(self, sector_slug: str | None) -> str | None:
        return self._resolve_sector_slug(sector_slug)

    def list_sectors(self) -> SectorDirectoryDTO:
        sectors_df = self.query_layer.get_available_company_sectors()
        companies_df = self.query_layer.get_companies()
        metric_rows = self.query_layer.get_sector_metric_rows()
        yearly = self._aggregate_sector_yearly_metrics(metric_rows)

        items: list[SectorDirectoryItemDTO] = []
        for _, row in sectors_df.iterrows():
            sector_name = str(row["sector_name"])
            sector_companies = companies_df[companies_df["sector_name"] == sector_name]
            available_years = self._extract_years_from_company_rows(sector_companies)
            latest_year = max(available_years) if available_years else None
            snapshot_row = None
            if latest_year is not None and not yearly.empty:
                filtered = yearly[
                    (yearly["sector_name"] == sector_name)
                    & (yearly["year"] == latest_year)
                ]
                snapshot_row = filtered.iloc[0] if not filtered.empty else None

            items.append(
                SectorDirectoryItemDTO(
                    sector_name=sector_name,
                    sector_slug=sector_slugify(sector_name),
                    company_count=int(row["company_count"] or 0),
                    latest_year=latest_year,
                    snapshot=SectorSnapshotDTO(
                        roe=self._coerce_optional_float(snapshot_row["roe"]) if snapshot_row is not None else None,
                        mg_ebit=self._coerce_optional_float(snapshot_row["mg_ebit"]) if snapshot_row is not None else None,
                        mg_liq=self._coerce_optional_float(snapshot_row["mg_liq"]) if snapshot_row is not None else None,
                    ),
                )
            )

        items.sort(key=lambda item: (-item.company_count, item.sector_name))
        return SectorDirectoryDTO(items=tuple(items))

    def get_sector_detail(self, sector_slug: str, year: int | None = None) -> SectorDetailDTO | None:
        resolved_sector_name = self._resolve_sector_slug(sector_slug)
        if resolved_sector_name is None:
            return None

        company_rows, total_items = self.query_layer.get_companies_directory_page(
            search="",
            sector_name=resolved_sector_name,
            page=1,
            page_size=None,
        )
        if company_rows.empty:
            return None

        years_map = self.query_layer.get_company_years_map(company_rows["cd_cvm"].tolist())
        company_rows = company_rows.copy()
        company_rows["anos_disponiveis"] = company_rows["cd_cvm"].map(
            lambda cd_cvm: years_map.get(int(cd_cvm), ())
        )
        available_years = self._extract_years_from_company_rows(company_rows)
        if not available_years:
            return None

        if year is None:
            selected_year = max(available_years)
        else:
            selected_year = int(year)
            if selected_year not in available_years:
                raise ValueError(
                    f"O parametro 'year' precisa ser um dos anos disponiveis do setor: {', '.join(str(value) for value in available_years)}."
                )

        metric_rows = self.query_layer.get_sector_metric_rows(sector_name=resolved_sector_name)
        yearly = self._aggregate_sector_yearly_metrics(metric_rows)
        yearly_overview = tuple(
            SectorYearOverviewDTO(
                year=int(row["year"]),
                roe=self._coerce_optional_float(row["roe"]),
                mg_ebit=self._coerce_optional_float(row["mg_ebit"]),
                mg_liq=self._coerce_optional_float(row["mg_liq"]),
            )
            for _, row in yearly[yearly["sector_name"] == resolved_sector_name]
            .sort_values("year")
            .iterrows()
        )

        company_metrics = metric_rows[metric_rows["report_year"] == selected_year].copy()
        selected_companies = company_rows[
            company_rows["anos_disponiveis"].map(lambda years: selected_year in years)
        ][["cd_cvm", "company_name", "ticker_b3"]].drop_duplicates()
        selected_companies = selected_companies.merge(
            company_metrics[
                ["cd_cvm", "roe", "mg_ebit", "mg_liq"]
            ],
            on="cd_cvm",
            how="left",
        )
        selected_companies["ticker_b3"] = selected_companies["ticker_b3"].replace("", None)
        selected_companies["sort_roe"] = pd.to_numeric(selected_companies["roe"], errors="coerce")
        selected_companies = selected_companies.sort_values(
            by=["sort_roe", "company_name"],
            ascending=[False, True],
            na_position="last",
        )

        companies = tuple(
            SectorCompanyMetricDTO(
                cd_cvm=int(row["cd_cvm"]),
                company_name=str(row["company_name"]),
                ticker_b3=self._clean_optional_text(row.get("ticker_b3")),
                roe=self._coerce_optional_float(row.get("roe")),
                mg_ebit=self._coerce_optional_float(row.get("mg_ebit")),
                mg_liq=self._coerce_optional_float(row.get("mg_liq")),
            )
            for _, row in selected_companies.iterrows()
        )

        return SectorDetailDTO(
            sector_name=resolved_sector_name,
            sector_slug=sector_slugify(resolved_sector_name),
            company_count=int(total_items),
            available_years=tuple(available_years),
            selected_year=int(selected_year),
            yearly_overview=yearly_overview,
            companies=companies,
        )

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

    def get_statement_summary(self, cd_cvm: int, years: list[int]) -> StatementSummaryDTO:
        stmt_types = ["DRE", "BPA", "BPP", "DFC"]
        statements = {
            s: self.query_layer.get_statement(
                cd_cvm=cd_cvm,
                years=years,
                stmt_type=s,
                exclude_conflicts=True,
            )
            for s in stmt_types
        }
        raw_blocks = build_general_summary_blocks(statements)
        blocks = tuple(
            SummaryBlockDTO(
                stmt_type=b.stmt_type,
                title=b.title,
                table=TabularData.from_dataframe(b.rows),
            )
            for b in raw_blocks
        )
        return StatementSummaryDTO(
            cd_cvm=int(cd_cvm),
            years=tuple(sorted(int(y) for y in years)),
            blocks=blocks,
        )

    def build_company_excel_export(self, cd_cvm: int) -> tuple[str, bytes]:
        company_info = self.get_company_info_dict(cd_cvm)
        if not company_info:
            raise ValueError(f"Empresa {cd_cvm} nao encontrada.")

        years = self.get_available_years(cd_cvm)
        if not years:
            raise ValueError(f"Empresa {cd_cvm} nao possui anos disponiveis para exportacao.")

        statements = {
            stmt_type: self.get_statement_dataframe(cd_cvm, years, stmt_type)
            for stmt_type in EXPORT_STATEMENT_TYPES
        }
        exportable_statements = {
            stmt_type: df
            for stmt_type, df in statements.items()
            if df is not None and not df.empty
        }
        extra_sheets = [
            stmt_type
            for stmt_type in ("DVA", "DMPL")
            if stmt_type in exportable_statements
        ]
        kpis_df = self.get_kpi_bundle(cd_cvm, years).quarterly_dataframe()

        exporter = ExcelExporter(
            company_info=company_info,
            statements=exportable_statements,
            kpis_df=kpis_df,
            extra_sheets=extra_sheets,
        )
        return build_excel_filename(company_info), exporter.export()

    def build_companies_excel_batch_export(self, cd_cvms: list[int]) -> tuple[str, bytes]:
        if len(cd_cvms) < 2:
            raise ValueError("O lote de exportacao exige ao menos 2 empresas.")

        seen: set[int] = set()
        unique_ids: list[int] = []
        for cd_cvm in cd_cvms:
            normalized = int(cd_cvm)
            if normalized in seen:
                raise ValueError("O lote de exportacao nao aceita empresas duplicadas.")
            seen.add(normalized)
            unique_ids.append(normalized)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for cd_cvm in unique_ids:
                filename, payload = self.build_company_excel_export(cd_cvm)
                archive.writestr(filename, payload)

        buffer.seek(0)
        return "comparar_excel_lote.zip", buffer.read()

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

    def _build_company_results(self, df: pd.DataFrame) -> list[CompanySearchResult]:
        results = []
        if df is None or df.empty:
            return results

        for _, row in df.iterrows():
            setor_analitico = self._clean_optional_text(row.get("setor_analitico"))
            setor_cvm = self._clean_optional_text(row.get("setor_cvm"))
            raw_sector_name = self._clean_optional_text(row.get("sector_name"))
            sector_name = raw_sector_name or canonical_sector_name(setor_analitico, setor_cvm)
            results.append(
                CompanySearchResult(
                    cd_cvm=int(row["cd_cvm"]),
                    company_name=str(row["company_name"]),
                    ticker_b3=self._clean_optional_text(row.get("ticker_b3")),
                    setor_analitico=setor_analitico,
                    setor_cvm=setor_cvm,
                    sector_name=sector_name,
                    sector_slug=sector_slugify(sector_name),
                    anos_disponiveis=_parse_years(row.get("anos_disponiveis")),
                    total_rows=int(row.get("total_rows") or 0),
                )
            )
        return results

    @staticmethod
    def _clean_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        if pd.isna(value):
            return None
        text_value = str(value).strip()
        return text_value or None

    def _resolve_sector_slug(self, sector_slug: str | None) -> str | None:
        if not sector_slug:
            return None
        normalized_slug = str(sector_slug).strip().lower()
        if not normalized_slug:
            return None
        for option in self.get_company_filters().sectors:
            if option.sector_slug == normalized_slug:
                return option.sector_name
        return None

    @staticmethod
    def _extract_years_from_company_rows(df: pd.DataFrame) -> list[int]:
        years: set[int] = set()
        if df is None or df.empty:
            return []
        for raw_years in df.get("anos_disponiveis", []):
            years.update(_parse_years(raw_years))
        return sorted(years)

    @staticmethod
    def _aggregate_sector_yearly_metrics(metric_rows: pd.DataFrame) -> pd.DataFrame:
        if metric_rows is None or metric_rows.empty:
            return pd.DataFrame(columns=["sector_name", "year", "roe", "mg_ebit", "mg_liq"])

        aggregated = (
            metric_rows.groupby(["sector_name", "report_year"], dropna=False)[["roe", "mg_ebit", "mg_liq"]]
            .mean()
            .reset_index()
            .rename(columns={"report_year": "year"})
        )
        return aggregated

    @staticmethod
    def _coerce_optional_float(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _empty_company_page(
        *,
        search: str,
        sector_slug: str | None,
        page: int,
        page_size: int,
    ) -> CompanyDirectoryPage:
        return CompanyDirectoryPage(
            items=(),
            pagination=CompanyDirectoryPagination(
                page=int(page),
                page_size=int(page_size),
                total_items=0,
                total_pages=1,
                has_next=False,
                has_previous=int(page) > 1,
            ),
            applied_filters=CompanyDirectoryAppliedFilters(
                search=str(search or ""),
                sector=sector_slug,
            ),
        )
