# -*- coding: utf-8 -*-
"""
dashboard/app.py - Orquestrador do dashboard CVM Analytics.

Execucao:
    streamlit run dashboard/app.py

Arquitetura (read-only):
  Sidebar -> busca empresa + selecao de anos
  Tabs    -> Visao Geral | Demonstracoes | Download

Atualizacao de dados: exclusivamente via cvm_pyqt_app.py (PyQt6).
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

st.set_page_config(
    page_title="CVM Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd

from src.read_service import CVMReadService
from src.startup import StartupReport, collect_startup_report, format_startup_report
from dashboard.components.search_bar import render_sidebar
from dashboard.tabs import demonstracoes, download, visao_geral

st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 0.4rem 1rem; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600, show_spinner="Carregando demonstracoes...")
def load_statements(cd_cvm: int, years: tuple[int, ...]) -> dict[str, pd.DataFrame]:
    read_service = CVMReadService()
    years_list = list(years)
    return {
        stmt: read_service.get_statement_dataframe(cd_cvm, years_list, stmt)
        for stmt in ["DRE", "BPA", "BPP", "DFC", "DVA", "DMPL"]
    }


@st.cache_data(ttl=600, show_spinner="Calculando KPIs...")
def load_kpis(cd_cvm: int, years: tuple[int, ...]) -> pd.DataFrame:
    bundle = CVMReadService().get_kpi_bundle(cd_cvm, list(years))
    return bundle.annual_dataframe()


@st.cache_data(ttl=600, show_spinner="Calculando KPIs trimestrais...")
def load_quarterly_kpis(cd_cvm: int, years: tuple[int, ...]) -> pd.DataFrame:
    bundle = CVMReadService().get_kpi_bundle(cd_cvm, list(years))
    return bundle.quarterly_dataframe()


def _single_issue_report(issue) -> StartupReport:
    return StartupReport(issues=(issue,))


def main():
    startup_report = collect_startup_report(
        require_database=True,
        required_tables=("financial_reports", "companies"),
        require_canonical_accounts=False,
    )
    for issue in startup_report.warnings:
        st.warning(format_startup_report(_single_issue_report(issue)))
    if startup_report.errors:
        st.error(format_startup_report(startup_report))
        st.stop()

    company_info, selected_years, include_optional = render_sidebar()

    if not company_info or not selected_years:
        st.title("📊 CVM Analytics")
        st.markdown(
            """
Bem-vindo ao **CVM Analytics** - visualizacao e download de dados financeiros
de empresas listadas na Bolsa brasileira.

**Como usar:**
1. Use a barra lateral para buscar uma empresa (nome, ticker ou codigo CVM)
2. Selecione os anos desejados
3. Explore as abas: **Visao Geral**, **Demonstracoes** ou **Download**

> Base: **449 empresas** · **2.5M+ registros** · Fonte: CVM / dados.cvm.gov.br
"""
        )
        return

    cd_cvm = int(company_info["cd_cvm"])
    years_tuple = tuple(sorted(selected_years))

    statements = load_statements(cd_cvm, years_tuple)
    kpis_df = load_kpis(cd_cvm, years_tuple)
    qkpis_df = load_quarterly_kpis(cd_cvm, years_tuple)

    tab_visao, tab_demo, tab_dl = st.tabs([
        "📋 Visao Geral",
        "📄 Demonstracoes",
        "⬇️  Download",
    ])

    with tab_visao:
        visao_geral.render(company_info, qkpis_df, list(years_tuple))

    with tab_demo:
        demonstracoes.render(statements)

    with tab_dl:
        download.render(
            company_info=company_info,
            statements=statements,
            kpis_df=qkpis_df,
            include_optional=include_optional,
        )


if __name__ == "__main__":
    main()
