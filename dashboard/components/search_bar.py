# -*- coding: utf-8 -*-
"""
dashboard/components/search_bar.py — Sidebar de busca e seleção de empresa.

Retorna (company_info, selected_years, include_dva_dmpl) ou None se nada selecionado.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st
import pandas as pd

from src.read_service import CVMReadService


@st.cache_data(ttl=300)
def _load_companies(search: str) -> pd.DataFrame:
    return CVMReadService().search_companies_df(search)


def render_sidebar() -> tuple[dict | None, list[int], bool]:
    """Renderiza sidebar e retorna (company_info, years, include_optional).

    Retorna (None, [], False) se nenhuma empresa selecionada.
    """
    st.sidebar.title("🔍 Buscar Empresa")

    search = st.sidebar.text_input(
        "Nome, ticker ou código CVM",
        placeholder="Ex: VALE, PETROBRAS, 9512...",
        key="search_input",
    )

    companies_df = _load_companies(search)

    if companies_df.empty:
        st.sidebar.info("Nenhuma empresa encontrada." if search else "Digite para buscar.")
        return None, [], False

    # Montar opções do selectbox
    def _label(row) -> str:
        ticker = f" [{row['ticker_b3']}]" if row["ticker_b3"] else ""
        return f"{row['company_name']}{ticker}"

    options = companies_df.apply(_label, axis=1).tolist()

    # Resetar seleção quando a busca muda (evita mostrar empresa anterior)
    if "prev_search" not in st.session_state:
        st.session_state["prev_search"] = search
    if st.session_state["prev_search"] != search:
        st.session_state["prev_search"] = search
        if "company_select" in st.session_state:
            del st.session_state["company_select"]

    selected_label = st.sidebar.selectbox(
        f"{len(companies_df)} empresa(s) encontrada(s)",
        options=options,
        key="company_select",
    )

    if selected_label is None:
        return None, [], False

    # Recuperar linha selecionada
    idx = options.index(selected_label)
    row = companies_df.iloc[idx]
    cd_cvm = int(row["cd_cvm"])

    # Metadados da empresa selecionada
    read_service = CVMReadService()
    company_info = read_service.get_company_info_dict(cd_cvm)
    available_years = read_service.get_available_years(cd_cvm)

    if not available_years:
        st.sidebar.warning("Sem dados disponíveis para esta empresa.")
        return None, [], False

    # Seleção de anos
    st.sidebar.divider()
    st.sidebar.markdown("**📅 Período**")
    selected_years = st.sidebar.multiselect(
        "Anos a incluir",
        options=available_years,
        default=available_years,
        key="years_select",
    )

    if not selected_years:
        st.sidebar.warning("Selecione ao menos um ano.")
        return company_info, [], False

    # Opções extras
    st.sidebar.divider()
    available_stmts = read_service.get_available_statements(cd_cvm)
    has_optional = any(s in available_stmts for s in ["DVA", "DMPL"])
    include_optional = False
    if has_optional:
        include_optional = st.sidebar.checkbox(
            "Incluir DVA e DMPL no Excel",
            value=False,
            help="Disponíveis para esta empresa",
        )

    # Card de info da empresa na sidebar
    st.sidebar.divider()
    ticker  = company_info.get("ticker_b3") or "—"
    setor   = company_info.get("setor_analitico") or company_info.get("setor_cvm") or "—"
    st.sidebar.markdown(f"""
**{company_info.get('company_name', '')}**
`{ticker}` · CVM `{cd_cvm}`
{setor}
""")

    return company_info, sorted(selected_years), include_optional
