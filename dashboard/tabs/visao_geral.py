# -*- coding: utf-8 -*-
"""
dashboard/tabs/visao_geral.py — Aba Visão Geral com KPI cards + tabela resumo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.kpi_engine import format_kpi_value

# KPIs destacados no topo (cards)
_FEATURED_KPIS = [
    ("MG_BRUTA",  "Margem Bruta",     "pct"),
    ("MG_EBITDA", "Margem EBITDA",    "pct"),
    ("MG_EBIT",   "Margem EBIT",      "pct"),
    ("MG_LIQ",    "Margem Líquida",   "pct"),
    ("ROE",       "ROE",              "pct"),
    ("ROA",       "ROA",              "pct"),
    ("FCO_REC",   "FCO / Receita",    "pct"),
    ("LIQ_CORR",  "Liq. Corrente",    "ratio"),
]

_HIGHER_IS_BETTER = {
    "MG_BRUTA", "MG_EBITDA", "MG_EBIT", "MG_LIQ",
    "ROE", "ROA", "FCO_REC", "LIQ_CORR",
}


def _period_sort_key(label: str) -> tuple[int, int]:
    """Ordena períodos cronologicamente: '2022' → (2022, 99), '1Q22' → (2022, 1)."""
    import re
    m = re.match(r"(\d)Q(\d{2})", str(label))
    if m:
        return (2000 + int(m.group(2)), int(m.group(1)))
    m2 = re.match(r"(\d{4})", str(label))
    if m2:
        return (int(m2.group(1)), 99)
    return (0, 0)


def render(company_info: dict, kpis_df: pd.DataFrame, years: list[int]):
    """Renderiza a aba Visão Geral."""
    if kpis_df is None or kpis_df.empty:
        st.warning("KPIs não disponíveis para esta empresa.")
        return

    name   = company_info.get("company_name", "—")
    ticker = company_info.get("ticker_b3") or "—"
    setor  = company_info.get("setor_analitico") or company_info.get("setor_cvm") or "—"
    cd_cvm = company_info.get("cd_cvm", "—")

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    col_t, col_m = st.columns([3, 1])
    with col_t:
        st.markdown(f"## {name}")
        st.caption(f"`{ticker}`  ·  CVM: `{cd_cvm}`  ·  {setor}")
    with col_m:
        last_year = max(years) if years else "—"
        st.metric("Último ano", str(last_year))

    st.divider()

    # Detectar colunas de períodos disponíveis no df de KPIs
    meta_cols = {"CATEGORIA", "KPI_ID", "KPI_NOME", "FORMULA",
                 "IS_PLACEHOLDER", "FORMAT_TYPE", "HIGHER_IS_BETTER",
                 "UNIDADE", "DELTA_YOY", "DELTA_YOY_PCT"}
    period_cols = [c for c in kpis_df.columns if c not in meta_cols]
    period_cols = sorted(period_cols, key=_period_sort_key)
    # Alias para compatibilidade
    year_cols = period_cols
    if not year_cols:
        st.info("Sem dados de períodos para exibir.")
        return

    last_yr = year_cols[-1]
    prev_yr = year_cols[-2] if len(year_cols) >= 2 else None

    # Indexar KPIs por KPI_ID
    kpi_map = kpis_df.set_index("KPI_ID")

    # ── Cards de KPIs ─────────────────────────────────────────────────────
    st.markdown(f"### Indicadores-chave  `{last_yr}`")
    cols = st.columns(4)
    for i, (kpi_id, label, fmt_type) in enumerate(_FEATURED_KPIS):
        col = cols[i % 4]
        with col:
            if kpi_id not in kpi_map.index:
                st.metric(label, "—")
                continue

            row   = kpi_map.loc[kpi_id]
            v_now = row.get(last_yr)
            v_prv = row.get(prev_yr) if prev_yr else None
            higher = kpi_id in _HIGHER_IS_BETTER

            # Formatar valor principal
            disp = format_kpi_value(v_now, fmt_type)

            # Delta para o metric
            delta_str  = None
            delta_col  = None
            if v_now is not None and v_prv is not None:
                delta = v_now - v_prv
                sign = "+" if delta >= 0 else ""
                if fmt_type == "pct":
                    delta_str = f"{sign}{delta * 100:.1f} pp"
                else:
                    delta_str = f"{sign}{delta:.2f}x"
                delta_col = "normal" if (delta >= 0) == higher else "inverse"

            st.metric(
                label=label,
                value=disp,
                delta=delta_str,
                delta_color=delta_col or "normal",
            )

    st.divider()

    # ── Tabela resumo: Receita + Lucro + EBITDA ao longo dos anos ─────────
    st.markdown("### Evolução Financeira")

    summary_kpis = [
        ("Receita Líquida (R$ mil)",  _get_account_series(kpis_df, "Receita")),
        ("EBITDA (R$ mil)",           _get_account_series(kpis_df, "EBITDA_val")),
        ("Lucro Líquido (R$ mil)",    _get_account_series(kpis_df, "Lucro_val")),
    ]

    # Montar tabela de síntese com os KPIs percentuais
    pct_kpis = [
        ("Margem Bruta",    "MG_BRUTA"),
        ("Margem EBITDA",   "MG_EBITDA"),
        ("Margem EBIT",     "MG_EBIT"),
        ("Margem Líquida",  "MG_LIQ"),
        ("ROE",             "ROE"),
        ("ROA",             "ROA"),
        ("Liq. Corrente",   "LIQ_CORR"),
        ("FCO / Receita",   "FCO_REC"),
        ("Dív.Liq/EBITDA",  "DIV_EBITDA"),
        ("PL / Passivo",    "PL_PASS"),
        ("Cresc. Receita",  "CRESC_REC"),
    ]

    table_rows = []
    for label, kpi_id in pct_kpis:
        if kpi_id not in kpi_map.index:
            continue
        row = kpi_map.loc[kpi_id]
        fmt_type = row.get("FORMAT_TYPE", "pct")
        r = {"Indicador": label}
        for yr in year_cols:
            v = row.get(yr)
            r[str(yr)] = format_kpi_value(v, fmt_type)
        table_rows.append(r)

    if table_rows:
        df_table = pd.DataFrame(table_rows).set_index("Indicador")
        st.dataframe(df_table, use_container_width=True)
    else:
        st.info("Dados insuficientes para o resumo de KPIs.")


def _get_account_series(kpis_df: pd.DataFrame, col_name: str) -> dict:
    """Helper — extrai série de valores não-KPI (valores absolutos não estão no kpis_df)."""
    return {}
