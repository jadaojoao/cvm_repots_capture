# -*- coding: utf-8 -*-
"""
dashboard/tabs/screener.py — Aba Screener: filtre empresas por KPIs financeiros.
"""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from dashboard.loaders import load_screener_data


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:.1f}%"


def _fmt_x(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.2f}x"


def _fmt_r(v) -> str:
    """Formata em R$ bi/mi."""
    if v is None or pd.isna(v):
        return "—"
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:.1f} bi"
    return f"R$ {v / 1e3:.0f} mi"


def _color_cell(v, low=0.0, high=0.20):
    """Retorna estilo CSS de cor para valor numérico normalizado."""
    if v is None or pd.isna(v):
        return ""
    norm = max(0, min(1, (v - low) / (high - low) if high != low else 0))
    r = int(255 * (1 - norm))
    g = int(180 * norm + 60)
    return f"color: rgb({r},{g},60)"


# ── Render principal ───────────────────────────────────────────────────────────

def render_screener(years: list[int], sector_map: dict) -> None:
    """Renderiza a aba Screener completa."""
    st.markdown("### 🔍 Screener de Empresas")

    # ── Linha de controles ──────────────────────────────────────────────────
    col_yr, col_setores, _ = st.columns([1, 3, 4])
    with col_yr:
        year = st.selectbox("Ano base", sorted(years, reverse=True),
                            key="screener_year")
    with col_setores:
        all_sectors = sorted({s for s in sector_map.values() if s})
        sel_sectors = st.multiselect("Setor", all_sectors,
                                     placeholder="Todos os setores",
                                     key="screener_sectors")

    df = load_screener_data(int(year))
    if df.empty:
        st.info(f"Sem dados para {year}.")
        return

    # Adicionar setor
    df["Setor"] = df["CD_CVM"].map(sector_map).fillna("N/D")

    # ── Filtros numéricos (expander) ────────────────────────────────────────
    with st.expander("Filtros de KPIs", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ml_min = st.slider("ML mín (%)", -50, 100, 0, key="sc_ml") / 100
        with c2:
            roe_min = st.slider("ROE mín (%)", -50, 100, 0, key="sc_roe") / 100
        with c3:
            rec_min = st.slider("Receita mín (R$ mi)", 0, 50_000, 0,
                                step=500, key="sc_rec") * 1e3
        with c4:
            liq_min = st.slider("Liq. Corrente mín", 0.0, 5.0, 0.0,
                                step=0.1, key="sc_liq")

    # Aplicar filtros
    mask = pd.Series([True] * len(df), index=df.index)
    if sel_sectors:
        mask &= df["Setor"].isin(sel_sectors)
    mask &= df["ML"].fillna(-999) >= ml_min
    mask &= df["ROE"].fillna(-999) >= roe_min
    mask &= df["Receita"].fillna(0) >= rec_min
    mask &= df["Liq.Corrente"].fillna(0) >= liq_min

    filtered = df[mask].copy()

    # ── Métricas de topo ────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Empresas", len(filtered), f"de {len(df)}")
    m2.metric("ML mediana",
              _fmt_pct(filtered["ML"].median()),
              delta=None)
    m3.metric("ROE mediana",
              _fmt_pct(filtered["ROE"].median()),
              delta=None)
    m4.metric("Receita total",
              _fmt_r(filtered["Receita"].sum()),
              delta=None)

    if filtered.empty:
        st.warning("Nenhuma empresa passou nos filtros.")
        return

    # ── Tabela ──────────────────────────────────────────────────────────────
    display = filtered[["Empresa", "Setor", "Receita", "ML", "MB", "ROE", "ROA",
                         "EBIT", "Liq.Corrente", "Div.Liq/PL", "CAGR_Rec_3a"]].copy()
    display = display.sort_values("Receita", ascending=False, na_position="last")

    # Formatar colunas para exibição
    fmt_cols_pct = ["ML", "MB", "ROE", "ROA", "EBIT", "CAGR_Rec_3a"]
    fmt_cols_x   = ["Liq.Corrente", "Div.Liq/PL"]

    col_cfg = {
        "Empresa":      st.column_config.TextColumn("Empresa", width=180),
        "Setor":        st.column_config.TextColumn("Setor",   width=160),
        "Receita":      st.column_config.NumberColumn(
            "Receita (R$ mil)", format="R$ %,.0f", width=130),
        "ML":           st.column_config.NumberColumn("ML",    format="%.1f%%", width=80),
        "MB":           st.column_config.NumberColumn("MB",    format="%.1f%%", width=80),
        "ROE":          st.column_config.NumberColumn("ROE",   format="%.1f%%", width=80),
        "ROA":          st.column_config.NumberColumn("ROA",   format="%.1f%%", width=80),
        "EBIT":         st.column_config.NumberColumn("M.EBIT",format="%.1f%%", width=80),
        "Liq.Corrente": st.column_config.NumberColumn("Liq.Corr.", format="%.2f", width=90),
        "Div.Liq/PL":   st.column_config.NumberColumn("D.Liq/PL",  format="%.2f", width=90),
        "CAGR_Rec_3a":  st.column_config.NumberColumn("CAGR 3a",   format="%.1f%%", width=90),
    }

    # Converter % para 0-100 para exibição com column_config format
    for c in fmt_cols_pct:
        display[c] = display[c] * 100

    st.dataframe(
        display,
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
        height=520,
    )

    # ── Exportar CSV ────────────────────────────────────────────────────────
    csv_buf = io.StringIO()
    display.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇ Exportar CSV",
        data=csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"screener_{year}.csv",
        mime="text/csv",
        key="screener_export",
    )
