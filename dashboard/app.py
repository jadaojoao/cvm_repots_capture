# -*- coding: utf-8 -*-
"""
dashboard/app.py — Orquestrador do dashboard CVM Analytics.

Execução:
    streamlit run dashboard/app.py

Arquitetura (read-only):
  Sidebar → busca empresa + seleção de anos
  Tabs    → Visão Geral | Demonstrações | Download

Atualização de dados: exclusivamente via cvm_pyqt_app.py (PyQt6).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Garantir que a raiz do projeto está no sys.path (necessário quando
# Streamlit é invocado de qualquer diretório)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

# ── Configuração da página (deve ser o primeiro comando Streamlit) ─────────
st.set_page_config(
    page_title="CVM Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd

from src.query_layer  import CVMQueryLayer
from src.kpi_engine   import compute_all_kpis, compute_quarterly_kpis
from dashboard.components.search_bar  import render_sidebar
from dashboard.tabs   import visao_geral, demonstracoes, download

# ──────────────────────────────────────────────────────────────────────────────
# CSS global mínimo
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 0.4rem 1rem; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Loaders com cache
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner="Carregando demonstrações…")
def load_statements(cd_cvm: int, years: tuple[int, ...]) -> dict[str, pd.DataFrame]:
    ql = CVMQueryLayer()
    years_list = list(years)
    return {
        stmt: ql.get_statement(cd_cvm, years_list, stmt)
        for stmt in ["DRE", "BPA", "BPP", "DFC", "DVA", "DMPL"]
    }


@st.cache_data(ttl=600, show_spinner="Calculando KPIs…")
def load_kpis(cd_cvm: int, years: tuple[int, ...]) -> pd.DataFrame:
    ql = CVMQueryLayer()
    years_list = list(years)
    accounts = ql.get_kpi_accounts(cd_cvm, years_list)
    da       = ql.get_da_from_dfc(cd_cvm, years_list)
    return compute_all_kpis(accounts, da)


@st.cache_data(ttl=600, show_spinner="Calculando KPIs trimestrais…")
def load_quarterly_kpis(cd_cvm: int, years: tuple[int, ...]) -> pd.DataFrame:
    ql = CVMQueryLayer()
    years_list = list(years)
    accounts = ql.get_kpi_accounts_all_periods(cd_cvm, years_list)
    da       = ql.get_da_all_periods(cd_cvm, years_list)
    return compute_quarterly_kpis(accounts, da)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Sidebar: retorna empresa selecionada + anos + flag opcional
    company_info, selected_years, include_optional = render_sidebar()

    # Estado vazio
    if not company_info or not selected_years:
        st.title("📊 CVM Analytics")
        st.markdown("""
Bem-vindo ao **CVM Analytics** — visualização e download de dados financeiros
de empresas listadas na Bolsa brasileira.

**Como usar:**
1. 🔍 Use a barra lateral para buscar uma empresa (nome, ticker ou código CVM)
2. 📅 Selecione os anos desejados
3. Explore as abas: **Visão Geral**, **Demonstrações** ou **Download**

> Base: **449 empresas** · **2.5M+ registros** · Fonte: CVM / dados.cvm.gov.br
""")
        return

    cd_cvm = int(company_info["cd_cvm"])
    years_tuple = tuple(sorted(selected_years))

    # Carregar dados
    statements = load_statements(cd_cvm, years_tuple)
    kpis_df    = load_kpis(cd_cvm, years_tuple)
    qkpis_df   = load_quarterly_kpis(cd_cvm, years_tuple)

    # Tabs principais
    tab_visao, tab_demo, tab_dl = st.tabs([
        "📋 Visão Geral",
        "📄 Demonstrações",
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
