# -*- coding: utf-8 -*-
"""
src/query_layer.py - API de leitura do banco CVM.

Centraliza toda logica de SELECT para que dashboard, scripts e testes
nao precisem escrever SQL raw. Depende apenas de sqlalchemy + pandas.

Schema relevante:
  financial_reports: id, COMPANY_NAME, CD_CVM, COMPANY_TYPE, STATEMENT_TYPE,
                     REPORT_YEAR, PERIOD_LABEL, LINE_ID_BASE, CD_CONTA, DS_CONTA,
                     STANDARD_NAME, QA_CONFLICT, VL_CONTA
  companies:         cd_cvm, company_name, nome_comercial, cnpj, setor_cvm,
                     setor_analitico, company_type, ticker_b3, is_active, updated_at
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd
from sqlalchemy import Engine, text

from src.db import get_engine

_KPI_ACCOUNTS = {
    "Receita": "3.01",
    "Res_Bruto": "3.03",
    "EBIT": "3.05",
    "Lucro_Liq": "3.11",
    "PL": "2.03",
    "Ativo_Total": "1",
    "Passivo_Total": "2",
    "PC": "2.01",
    "PNC": "2.02",
    "AC": "1.01",
    "Caixa": "1.01.01",
    "FCO": "6.01",
    "FCI": "6.02",
    "FCF": "6.03",
}

_CANONICAL_SECTOR_SQL = """
COALESCE(
    NULLIF(TRIM(c.setor_analitico), ''),
    NULLIF(TRIM(c.setor_cvm), ''),
    'Nao classificado'
)
"""


def _period_sort_key(label: str) -> tuple[int, int]:
    m = re.match(r"(\d{4})", label)
    year = int(m.group(1)) if m else 0
    q_match = re.match(r"(\d)Q(\d{2})", label)
    if q_match:
        return (2000 + int(q_match.group(2)), int(q_match.group(1)))
    return (year, 99)


class CVMQueryLayer:
    """Camada de leitura reutilizavel do banco CVM."""

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    def get_companies(self, search: str = "") -> pd.DataFrame:
        rows_df, _ = self.get_companies_directory_page(
            search=search,
            sector_name=None,
            page=1,
            page_size=None,
        )
        if rows_df.empty:
            rows_df["anos_disponiveis"] = []
            return rows_df.reset_index(drop=True)

        years_map = self.get_company_years_map(rows_df["cd_cvm"].tolist())
        rows_df = rows_df.copy()
        rows_df["anos_disponiveis"] = rows_df["cd_cvm"].map(
            lambda cd_cvm: ",".join(str(year) for year in years_map.get(int(cd_cvm), ()))
        )
        return rows_df.reset_index(drop=True)

    def get_companies_directory_page(
        self,
        *,
        search: str = "",
        sector_name: str | None = None,
        page: int = 1,
        page_size: int | None = 20,
    ) -> tuple[pd.DataFrame, int]:
        where_sql, params = self._company_directory_filters(search=search, sector_name=sector_name)

        count_sql = text(
            f"""
            SELECT COUNT(*) AS total_items
            FROM (
                SELECT c.cd_cvm
                FROM companies c
                JOIN financial_reports fr ON fr.CD_CVM = c.cd_cvm
                WHERE {where_sql}
                GROUP BY c.cd_cvm, c.company_name, c.ticker_b3, c.setor_analitico, c.setor_cvm
            ) company_rows
            """
        )
        total_items = int(pd.read_sql(count_sql, self.engine, params=params).iloc[0]["total_items"])

        paging_sql = ""
        paged_params = dict(params)
        if page_size is not None:
            paging_sql = " LIMIT :limit OFFSET :offset"
            paged_params["limit"] = int(page_size)
            paged_params["offset"] = max(0, (int(page) - 1) * int(page_size))

        rows_sql = text(
            f"""
            SELECT
                c.cd_cvm,
                c.company_name,
                COALESCE(c.ticker_b3, '') AS ticker_b3,
                c.setor_analitico,
                c.setor_cvm,
                {_CANONICAL_SECTOR_SQL} AS sector_name,
                COUNT(*) AS total_rows
            FROM companies c
            JOIN financial_reports fr ON fr.CD_CVM = c.cd_cvm
            WHERE {where_sql}
            GROUP BY c.cd_cvm, c.company_name, c.ticker_b3, c.setor_analitico, c.setor_cvm
            ORDER BY c.company_name ASC
            {paging_sql}
            """
        )
        rows_df = pd.read_sql(rows_sql, self.engine, params=paged_params)
        return rows_df.reset_index(drop=True), total_items

    def get_available_company_sectors(self) -> pd.DataFrame:
        sql = text(
            f"""
            SELECT
                {_CANONICAL_SECTOR_SQL} AS sector_name,
                COUNT(DISTINCT c.cd_cvm) AS company_count
            FROM companies c
            JOIN financial_reports fr ON fr.CD_CVM = c.cd_cvm
            GROUP BY {_CANONICAL_SECTOR_SQL}
            ORDER BY sector_name ASC
            """
        )
        return pd.read_sql(sql, self.engine).reset_index(drop=True)

    def get_sector_available_years(self, sector_name: str) -> list[int]:
        sql = text(
            f"""
            SELECT DISTINCT fr.REPORT_YEAR
            FROM financial_reports fr
            JOIN companies c ON c.cd_cvm = fr.CD_CVM
            WHERE {_CANONICAL_SECTOR_SQL} = :sector_name
              AND fr.PERIOD_LABEL = CAST(fr.REPORT_YEAR AS TEXT)
            ORDER BY fr.REPORT_YEAR
            """
        )
        df = pd.read_sql(sql, self.engine, params={"sector_name": str(sector_name)})
        return [int(year) for year in df["REPORT_YEAR"].tolist()]

    def get_sector_metric_rows(
        self,
        *,
        sector_name: str | None = None,
        years: list[int] | None = None,
    ) -> pd.DataFrame:
        where_parts = [
            "fr.PERIOD_LABEL = CAST(fr.REPORT_YEAR AS TEXT)",
            "fr.QA_CONFLICT = 0",
            "fr.CD_CONTA IN ('3.01', '3.05', '3.11', '2.03')",
        ]
        params: dict[str, object] = {}

        if sector_name:
            where_parts.append(f"{_CANONICAL_SECTOR_SQL} = :sector_name")
            params["sector_name"] = str(sector_name)

        normalized_years = sorted({int(year) for year in years or []})
        if normalized_years:
            placeholders = ", ".join(f":y{i}" for i in range(len(normalized_years)))
            where_parts.append(f"fr.REPORT_YEAR IN ({placeholders})")
            params.update({f"y{i}": year for i, year in enumerate(normalized_years)})

        sql = text(
            f"""
            SELECT
                c.cd_cvm,
                c.company_name,
                c.ticker_b3,
                {_CANONICAL_SECTOR_SQL} AS sector_name,
                fr.REPORT_YEAR,
                fr.CD_CONTA,
                SUM(fr.VL_CONTA) AS account_value
            FROM financial_reports fr
            JOIN companies c ON c.cd_cvm = fr.CD_CVM
            WHERE {' AND '.join(where_parts)}
            GROUP BY
                c.cd_cvm,
                c.company_name,
                c.ticker_b3,
                {_CANONICAL_SECTOR_SQL},
                fr.REPORT_YEAR,
                fr.CD_CONTA
            """
        )
        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "cd_cvm",
                    "company_name",
                    "ticker_b3",
                    "sector_name",
                    "report_year",
                    "roe",
                    "mg_ebit",
                    "mg_liq",
                ]
            )

        pivot = df.pivot_table(
            index=["cd_cvm", "company_name", "ticker_b3", "sector_name", "REPORT_YEAR"],
            columns="CD_CONTA",
            values="account_value",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None
        pivot = pivot.rename(
            columns={
                "REPORT_YEAR": "report_year",
                "3.01": "receita",
                "3.05": "ebit",
                "3.11": "lucro_liq",
                "2.03": "pl",
            }
        )

        for column in ("receita", "ebit", "lucro_liq", "pl"):
            if column not in pivot.columns:
                pivot[column] = pd.NA

        receita = pd.to_numeric(pivot["receita"], errors="coerce")
        ebit = pd.to_numeric(pivot["ebit"], errors="coerce")
        lucro_liq = pd.to_numeric(pivot["lucro_liq"], errors="coerce")
        pl = pd.to_numeric(pivot["pl"], errors="coerce")

        pivot["mg_ebit"] = ebit.divide(receita.where(receita != 0))
        pivot["mg_liq"] = lucro_liq.divide(receita.where(receita != 0))
        pivot["roe"] = lucro_liq.divide(pl.where(pl != 0))

        return pivot[
            [
                "cd_cvm",
                "company_name",
                "ticker_b3",
                "sector_name",
                "report_year",
                "roe",
                "mg_ebit",
                "mg_liq",
            ]
        ].reset_index(drop=True)

    def get_company_years_map(self, cd_cvms: list[int]) -> dict[int, tuple[int, ...]]:
        """Retorna mapa cd_cvm → anos com dados anuais completos (DFP).

        Filtra por PERIOD_LABEL = REPORT_YEAR (ex: '2024') para excluir anos que
        possuam apenas dados trimestrais ITR, mantendo consistencia com
        get_available_years e garantindo que anos_disponiveis reflita apenas
        periodos computaveis pelo KPI engine.
        """
        if not cd_cvms:
            return {}

        unique_ids = tuple(sorted({int(cd_cvm) for cd_cvm in cd_cvms}))
        placeholders = ", ".join(f":cd{i}" for i in range(len(unique_ids)))
        params = {f"cd{i}": cd_cvm for i, cd_cvm in enumerate(unique_ids)}
        sql = text(
            f"""
            SELECT CD_CVM, REPORT_YEAR
            FROM financial_reports
            WHERE CD_CVM IN ({placeholders})
              AND PERIOD_LABEL = CAST(REPORT_YEAR AS TEXT)
            GROUP BY CD_CVM, REPORT_YEAR
            ORDER BY CD_CVM, REPORT_YEAR
            """
        )
        df = pd.read_sql(sql, self.engine, params=params)
        years_map: dict[int, list[int]] = {int(cd_cvm): [] for cd_cvm in unique_ids}
        for _, row in df.iterrows():
            years_map.setdefault(int(row["CD_CVM"]), []).append(int(row["REPORT_YEAR"]))
        return {cd_cvm: tuple(years) for cd_cvm, years in years_map.items()}

    def _company_directory_filters(
        self,
        *,
        search: str,
        sector_name: str | None,
    ) -> tuple[str, dict]:
        where_parts = ["1 = 1"]
        params: dict[str, object] = {}

        normalized_search = search.strip().lower()
        if normalized_search:
            params["search"] = f"%{normalized_search}%"
            where_parts.append(
                """
                (
                    LOWER(c.company_name) LIKE :search
                    OR LOWER(COALESCE(c.ticker_b3, '')) LIKE :search
                    OR CAST(c.cd_cvm AS TEXT) LIKE :search
                )
                """
            )

        if sector_name:
            params["sector_name"] = str(sector_name)
            where_parts.append(f"{_CANONICAL_SECTOR_SQL} = :sector_name")

        return " AND ".join(where_parts), params

    def get_company_info(self, cd_cvm: int) -> dict:
        sql = text(
            """
            SELECT
                cd_cvm,
                company_name,
                nome_comercial,
                cnpj,
                setor_cvm,
                setor_analitico,
                COALESCE(
                    NULLIF(TRIM(setor_analitico), ''),
                    NULLIF(TRIM(setor_cvm), ''),
                    'Nao classificado'
                ) AS sector_name,
                company_type,
                ticker_b3
            FROM companies
            WHERE cd_cvm = :cd_cvm
            LIMIT 1
            """
        )
        row = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def get_available_years(self, cd_cvm: int) -> list[int]:
        """Retorna os anos com dados anuais completos (DFP) para a empresa.

        Filtra por PERIOD_LABEL = REPORT_YEAR (ex: '2024') para excluir anos que
        possuam apenas dados trimestrais ITR (ex: '1Q24', '3Q25').  Isso garante
        que o endpoint /years retorne somente anos computaveis pelo KPI engine,
        que tambem filtra por periodo anual.  Sem esse filtro, companias com ITR
        mais recente do que o ultimo DFP publicado causariam referenceYear sem
        dados no Comparar, exibindo '-' em todas as celulas.
        """
        sql = text(
            """
            SELECT DISTINCT REPORT_YEAR
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND PERIOD_LABEL = CAST(REPORT_YEAR AS TEXT)
            ORDER BY REPORT_YEAR
            """
        )
        df = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        return [int(year) for year in df["REPORT_YEAR"].tolist()]

    def get_available_statements(self, cd_cvm: int) -> list[str]:
        sql = text(
            """
            SELECT DISTINCT STATEMENT_TYPE
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
            ORDER BY STATEMENT_TYPE
            """
        )
        df = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        return df["STATEMENT_TYPE"].tolist()

    def get_statement(
        self,
        cd_cvm: int,
        years: list[int],
        stmt_type: str,
        exclude_conflicts: bool = True,
    ) -> pd.DataFrame:
        if not years:
            return pd.DataFrame()

        years_int = [int(year) for year in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": year for i, year in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)
        params["stmt"] = stmt_type

        conflict_clause = "AND QA_CONFLICT = 0" if exclude_conflicts else ""
        sql = text(
            f"""
            SELECT CD_CONTA, DS_CONTA, STANDARD_NAME, LINE_ID_BASE,
                   PERIOD_LABEL, VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = :stmt
              AND REPORT_YEAR IN ({placeholders})
              {conflict_clause}
            """
        )

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return df

        df["STANDARD_NAME"] = df["STANDARD_NAME"].fillna("")
        pivot = df.pivot_table(
            index=["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"],
            columns="PERIOD_LABEL",
            values="VL_CONTA",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        id_cols = ["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"]
        period_cols = [column for column in pivot.columns if column not in id_cols]
        period_cols_sorted = sorted(period_cols, key=_period_sort_key)
        result = pivot[id_cols + period_cols_sorted]

        if period_cols_sorted:
            numeric_data = result[period_cols_sorted].fillna(0)
            all_zero_mask = (numeric_data == 0).all(axis=1)
            result = result[~all_zero_mask].reset_index(drop=True)

        return result

    def get_kpi_accounts(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        if not years:
            return pd.DataFrame()

        years_int = [int(year) for year in years]
        cd_contas = list(_KPI_ACCOUNTS.values())
        placeholders_y = ", ".join(f":y{i}" for i in range(len(years_int)))
        placeholders_c = ", ".join(f":c{i}" for i in range(len(cd_contas)))

        params: dict = {f"y{i}": year for i, year in enumerate(years_int)}
        params.update({f"c{i}": conta for i, conta in enumerate(cd_contas)})
        params["cd_cvm"] = int(cd_cvm)

        sql = text(
            f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, CD_CONTA, SUM(VL_CONTA) AS VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND REPORT_YEAR IN ({placeholders_y})
              AND CD_CONTA IN ({placeholders_c})
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL, CD_CONTA
            """
        )

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.DataFrame()

        df = df[df["PERIOD_LABEL"] == df["REPORT_YEAR"].astype(str)].copy()
        pivot = df.pivot_table(
            index="REPORT_YEAR",
            columns="CD_CONTA",
            values="VL_CONTA",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        inv_map = {value: key for key, value in _KPI_ACCOUNTS.items()}
        pivot = pivot.rename(columns=inv_map)
        return pivot.sort_values("REPORT_YEAR").reset_index(drop=True)

    def get_kpi_accounts_all_periods(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        if not years:
            return pd.DataFrame()

        years_int = [int(year) for year in years]
        cd_contas = list(_KPI_ACCOUNTS.values())
        placeholders_y = ", ".join(f":y{i}" for i in range(len(years_int)))
        placeholders_c = ", ".join(f":c{i}" for i in range(len(cd_contas)))

        params: dict = {f"y{i}": year for i, year in enumerate(years_int)}
        params.update({f"c{i}": conta for i, conta in enumerate(cd_contas)})
        params["cd_cvm"] = int(cd_cvm)

        sql = text(
            f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, CD_CONTA, SUM(VL_CONTA) AS VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND REPORT_YEAR IN ({placeholders_y})
              AND CD_CONTA IN ({placeholders_c})
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL, CD_CONTA
            """
        )

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.DataFrame()

        pivot = df.pivot_table(
            index=["REPORT_YEAR", "PERIOD_LABEL"],
            columns="CD_CONTA",
            values="VL_CONTA",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        inv_map = {value: key for key, value in _KPI_ACCOUNTS.items()}
        pivot = pivot.rename(columns=inv_map)
        pivot["_sort"] = pivot["PERIOD_LABEL"].apply(_period_sort_key)
        return pivot.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

    def get_da_all_periods(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        if not years:
            return pd.DataFrame()

        years_int = [int(year) for year in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": year for i, year in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)

        sql = text(
            f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, SUM(ABS(VL_CONTA)) AS da_value
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = 'DFC'
              AND REPORT_YEAR IN ({placeholders})
              AND CD_CONTA LIKE '6.01.01%'
              AND LOWER(DS_CONTA) LIKE '%depreci%'
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL
            """
        )

        return pd.read_sql(sql, self.engine, params=params)

    def get_da_from_dfc(self, cd_cvm: int, years: list[int]) -> pd.Series:
        if not years:
            return pd.Series(dtype=float)

        years_int = [int(year) for year in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": year for i, year in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)

        sql = text(
            f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, SUM(ABS(VL_CONTA)) AS da_value
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = 'DFC'
              AND REPORT_YEAR IN ({placeholders})
              AND CD_CONTA LIKE '6.01.01%'
              AND LOWER(DS_CONTA) LIKE '%depreci%'
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL
            """
        )

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.Series(dtype=float)

        df = df[df["PERIOD_LABEL"] == df["REPORT_YEAR"].astype(str)]
        return df.set_index("REPORT_YEAR")["da_value"]
