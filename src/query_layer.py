# -*- coding: utf-8 -*-
"""
src/query_layer.py — API de leitura do banco CVM.

Centraliza toda lógica de SELECT para que dashboard, scripts e testes
não precisem escrever SQL raw. Depende apenas de sqlalchemy + pandas.

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

# ──────────────────────────────────────────────────────────────────────────────
# Contas-chave mapeadas por CD_CONTA
# ──────────────────────────────────────────────────────────────────────────────
_KPI_ACCOUNTS = {
    "Receita":       "3.01",
    "Res_Bruto":     "3.03",
    "EBIT":          "3.05",
    "Lucro_Liq":     "3.11",
    "PL":            "2.03",
    "Ativo_Total":   "1",
    "Passivo_Total": "2",
    "PC":            "2.01",   # Passivo Circulante
    "PNC":           "2.02",   # Passivo Não Circulante
    "AC":            "1.01",   # Ativo Circulante
    "Caixa":         "1.01.01",
    "FCO":           "6.01",
    "FCI":           "6.02",
    "FCF":           "6.03",
}

# Ordem cronológica dos períodos dentro de um ano
_PERIOD_ORDER_MAP = {
    "1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4,
}


def _period_sort_key(label: str) -> tuple[int, int]:
    """Retorna (ano, trimestre) para ordenação de PERIOD_LABEL."""
    m = re.match(r"(\d{4})", label)
    year = int(m.group(1)) if m else 0
    q_m = re.match(r"(\d)Q(\d{2})", label)
    if q_m:
        return (2000 + int(q_m.group(2)), int(q_m.group(1)))
    return (year, 99)  # anual = seta para o fim do ano


class CVMQueryLayer:
    """Camada de leitura reutilizável do banco CVM.

    Uso:
        ql = CVMQueryLayer()                     # usa get_engine() padrão
        ql = CVMQueryLayer(engine=my_engine)     # engine customizado
    """

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    # ──────────────────────────────────────────────────────────────────────
    # Listagem de empresas
    # ──────────────────────────────────────────────────────────────────────

    def get_companies(self, search: str = "") -> pd.DataFrame:
        """Retorna DataFrame de empresas com anos disponíveis.

        Parâmetros
        ----------
        search : str
            Filtro livre (nome, ticker ou cd_cvm). Vazio = todas.

        Retorna
        -------
        pd.DataFrame com colunas:
            cd_cvm, company_name, ticker_b3, setor_analitico, setor_cvm,
            anos_disponiveis, total_rows
        """
        sql = text("""
            SELECT
                c.cd_cvm,
                c.company_name,
                COALESCE(c.ticker_b3, '') AS ticker_b3,
                COALESCE(c.setor_analitico, c.setor_cvm, 'Não classificado') AS setor_analitico,
                COALESCE(c.setor_cvm, '') AS setor_cvm,
                GROUP_CONCAT(DISTINCT fr.REPORT_YEAR ORDER BY fr.REPORT_YEAR) AS anos_disponiveis,
                COUNT(*) AS total_rows
            FROM companies c
            JOIN financial_reports fr ON fr.CD_CVM = c.cd_cvm
            GROUP BY c.cd_cvm
            ORDER BY c.company_name
        """)
        df = pd.read_sql(sql, self.engine)

        if search:
            s = search.strip().lower()
            mask = (
                df["company_name"].str.lower().str.contains(s, na=False)
                | df["ticker_b3"].str.lower().str.contains(s, na=False)
                | df["cd_cvm"].astype(str).str.contains(s, na=False)
            )
            df = df[mask]

        return df.reset_index(drop=True)

    # ──────────────────────────────────────────────────────────────────────
    # Info de uma empresa
    # ──────────────────────────────────────────────────────────────────────

    def get_company_info(self, cd_cvm: int) -> dict:
        """Retorna metadados de uma empresa como dict."""
        sql = text("""
            SELECT cd_cvm, company_name, nome_comercial, cnpj,
                   setor_cvm, setor_analitico, company_type, ticker_b3
            FROM companies
            WHERE cd_cvm = :cd_cvm
            LIMIT 1
        """)
        row = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def get_available_years(self, cd_cvm: int) -> list[int]:
        """Retorna lista de anos disponíveis para uma empresa, ordenada."""
        sql = text("""
            SELECT DISTINCT REPORT_YEAR
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
            ORDER BY REPORT_YEAR
        """)
        df = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        return [int(y) for y in df["REPORT_YEAR"].tolist()]

    def get_available_statements(self, cd_cvm: int) -> list[str]:
        """Retorna quais tipos de demonstração existem para a empresa."""
        sql = text("""
            SELECT DISTINCT STATEMENT_TYPE
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
            ORDER BY STATEMENT_TYPE
        """)
        df = pd.read_sql(sql, self.engine, params={"cd_cvm": int(cd_cvm)})
        return df["STATEMENT_TYPE"].tolist()

    # ──────────────────────────────────────────────────────────────────────
    # Demonstrações financeiras
    # ──────────────────────────────────────────────────────────────────────

    def get_statement(
        self,
        cd_cvm: int,
        years: list[int],
        stmt_type: str,
        exclude_conflicts: bool = True,
    ) -> pd.DataFrame:
        """Retorna demonstração no formato WIDE (CD_CONTA × períodos).

        Colunas fixas: CD_CONTA, DS_CONTA, STANDARD_NAME, LINE_ID_BASE
        Colunas de período: 2022, 1Q23, 2Q23, 3Q23, 2023, ...  (ordenadas)

        QA_CONFLICT = 1 pode ser incluído via exclude_conflicts=False.
        """
        if not years:
            return pd.DataFrame()

        years_int = [int(y) for y in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": y for i, y in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)
        params["stmt"] = stmt_type

        conflict_clause = "AND QA_CONFLICT = 0" if exclude_conflicts else ""

        sql = text(f"""
            SELECT CD_CONTA, DS_CONTA, STANDARD_NAME, LINE_ID_BASE,
                   PERIOD_LABEL, VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = :stmt
              AND REPORT_YEAR IN ({placeholders})
              {conflict_clause}
        """)

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return df

        # Preencher NaN em STANDARD_NAME antes do pivot — pivot_table descarta
        # linhas com NaN no index por padrão, o que eliminava sub-contas sem
        # nome padrão (ex: DFC 6.02.xx, 6.03.xx).
        df["STANDARD_NAME"] = df["STANDARD_NAME"].fillna("")

        # Pivot: linhas = contas, colunas = períodos
        pivot = df.pivot_table(
            index=["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"],
            columns="PERIOD_LABEL",
            values="VL_CONTA",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        # Ordenar colunas de período cronologicamente
        id_cols = ["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"]
        period_cols = [c for c in pivot.columns if c not in id_cols]
        period_cols_sorted = sorted(period_cols, key=_period_sort_key)

        result = pivot[id_cols + period_cols_sorted]

        # Remover linhas onde TODOS os períodos são zero ou nulos
        if period_cols_sorted:
            num_data = result[period_cols_sorted].fillna(0)
            all_zero_mask = (num_data == 0).all(axis=1)
            result = result[~all_zero_mask].reset_index(drop=True)

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Contas-chave para KPIs
    # ──────────────────────────────────────────────────────────────────────

    def get_kpi_accounts(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        """Extrai contas-chave para o KPI engine.

        Retorna DataFrame wide:
            index = REPORT_YEAR (somente períodos anuais — ex: "2022")
            colunas = {Receita, Res_Bruto, EBIT, Lucro_Liq, PL, Ativo_Total,
                       Passivo_Total, PC, PNC, AC, Caixa, FCO, FCI, FCF}
        """
        if not years:
            return pd.DataFrame()

        years_int = [int(y) for y in years]
        cd_contas = list(_KPI_ACCOUNTS.values())
        placeholders_y = ", ".join(f":y{i}" for i in range(len(years_int)))
        placeholders_c = ", ".join(f":c{i}" for i in range(len(cd_contas)))

        params: dict = {f"y{i}": y for i, y in enumerate(years_int)}
        params.update({f"c{i}": c for i, c in enumerate(cd_contas)})
        params["cd_cvm"] = int(cd_cvm)

        sql = text(f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, CD_CONTA, SUM(VL_CONTA) AS VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND REPORT_YEAR IN ({placeholders_y})
              AND CD_CONTA IN ({placeholders_c})
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL, CD_CONTA
        """)

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.DataFrame()

        # Filtrar apenas períodos anuais (ex: "2022", "2023")
        df = df[df["PERIOD_LABEL"] == df["REPORT_YEAR"].astype(str)].copy()

        # Pivot: linhas = REPORT_YEAR, colunas = CD_CONTA
        pivot = df.pivot_table(
            index="REPORT_YEAR", columns="CD_CONTA", values="VL_CONTA", aggfunc="first"
        ).reset_index()
        pivot.columns.name = None

        # Renomear colunas de CD_CONTA → nome legível
        inv_map = {v: k for k, v in _KPI_ACCOUNTS.items()}
        pivot = pivot.rename(columns=inv_map)
        pivot = pivot.sort_values("REPORT_YEAR").reset_index(drop=True)

        return pivot

    def get_kpi_accounts_all_periods(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        """Extrai contas-chave para KPIs — TODOS os períodos (anuais + trimestrais).

        Retorna DataFrame wide:
            index = PERIOD_LABEL (ex: "1Q22", "2Q22", "3Q22", "2022", ...)
            colunas = REPORT_YEAR + {Receita, Res_Bruto, EBIT, Lucro_Liq, PL, ...}
        """
        if not years:
            return pd.DataFrame()

        years_int = [int(y) for y in years]
        cd_contas = list(_KPI_ACCOUNTS.values())
        placeholders_y = ", ".join(f":y{i}" for i in range(len(years_int)))
        placeholders_c = ", ".join(f":c{i}" for i in range(len(cd_contas)))

        params: dict = {f"y{i}": y for i, y in enumerate(years_int)}
        params.update({f"c{i}": c for i, c in enumerate(cd_contas)})
        params["cd_cvm"] = int(cd_cvm)

        sql = text(f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, CD_CONTA, SUM(VL_CONTA) AS VL_CONTA
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND REPORT_YEAR IN ({placeholders_y})
              AND CD_CONTA IN ({placeholders_c})
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL, CD_CONTA
        """)

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.DataFrame()

        # Pivot: linhas = (REPORT_YEAR, PERIOD_LABEL), colunas = CD_CONTA
        pivot = df.pivot_table(
            index=["REPORT_YEAR", "PERIOD_LABEL"],
            columns="CD_CONTA",
            values="VL_CONTA",
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        # Renomear colunas de CD_CONTA → nome legível
        inv_map = {v: k for k, v in _KPI_ACCOUNTS.items()}
        pivot = pivot.rename(columns=inv_map)

        # Ordenar cronologicamente
        pivot["_sort"] = pivot["PERIOD_LABEL"].apply(_period_sort_key)
        pivot = pivot.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

        return pivot

    def get_da_all_periods(self, cd_cvm: int, years: list[int]) -> pd.DataFrame:
        """Extrai D&A da DFC — TODOS os períodos (anuais + trimestrais).

        Retorna DataFrame com colunas: REPORT_YEAR, PERIOD_LABEL, da_value.
        """
        if not years:
            return pd.DataFrame()

        years_int = [int(y) for y in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": y for i, y in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)

        sql = text(f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, SUM(ABS(VL_CONTA)) AS da_value
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = 'DFC'
              AND REPORT_YEAR IN ({placeholders})
              AND CD_CONTA LIKE '6.01.01%'
              AND LOWER(DS_CONTA) LIKE '%depreci%'
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL
        """)

        return pd.read_sql(sql, self.engine, params=params)

    def get_da_from_dfc(self, cd_cvm: int, years: list[int]) -> pd.Series:
        """Extrai D&A da DFC (método indireto) por ano.

        Busca subcontas de 6.01.01.xx que contenham "deprecia" ou "amortiza"
        (case-insensitive). Agrega por REPORT_YEAR (somente período anual).

        Retorna pd.Series(index=REPORT_YEAR, values=D&A como valor positivo).
        """
        if not years:
            return pd.Series(dtype=float)

        years_int = [int(y) for y in years]
        placeholders = ", ".join(f":y{i}" for i in range(len(years_int)))
        params: dict = {f"y{i}": y for i, y in enumerate(years_int)}
        params["cd_cvm"] = int(cd_cvm)

        # IMPORTANTE: Filtramos por "depreci" para pegar "Depreciação e amortização"
        # mas EXCLUÍMOS amortizações puramente financeiras (captação, debêntures,
        # gastos na emissão, etc.) que contaminariam o EBITDA.
        # O match por "depreci" cobre ~95% dos casos (429 empresas em 2024)
        # pois a maioria reporta como "Depreciação e amortização" numa única linha.
        sql = text(f"""
            SELECT REPORT_YEAR, PERIOD_LABEL, SUM(ABS(VL_CONTA)) AS da_value
            FROM financial_reports
            WHERE CD_CVM = :cd_cvm
              AND STATEMENT_TYPE = 'DFC'
              AND REPORT_YEAR IN ({placeholders})
              AND CD_CONTA LIKE '6.01.01%'
              AND LOWER(DS_CONTA) LIKE '%depreci%'
              AND QA_CONFLICT = 0
            GROUP BY REPORT_YEAR, PERIOD_LABEL
        """)

        df = pd.read_sql(sql, self.engine, params=params)
        if df.empty:
            return pd.Series(dtype=float)

        # Apenas períodos anuais
        df = df[df["PERIOD_LABEL"] == df["REPORT_YEAR"].astype(str)]
        return df.set_index("REPORT_YEAR")["da_value"]
