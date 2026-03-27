# -*- coding: utf-8 -*-
"""
dashboard/tabs/mercado.py — Aba "Mercado" (heatmap setorial).
"""
from __future__ import annotations

import streamlit as st

from dashboard.charts import chart_sector_heatmap
from dashboard.loaders import load_heatmap_data


def render_mercado(sel: str, years: tuple, sector_map: dict) -> None:
    """Renderiza a aba Mercado."""
    st.markdown('<div class="sec">Ranking de Mercado — Todas as Empresas</div>',
                unsafe_allow_html=True)

    mc1, mc2 = st.columns([1, 2])
    with mc1:
        _hm_opts = list(reversed(list(years)))
        hm_year  = st.selectbox(
            "Ano", options=_hm_opts,
            index=min(1, len(_hm_opts) - 1),
            key='hm_year')
    with mc2:
        _hm_metric_sel = st.selectbox(
            "Métrica",
            options=[
                ('Margem Líquida', 'ML'),
                ('ROE',            'ROE'),
                ('Margem Bruta',   'MB'),
                ('ROA',            'ROA'),
            ],
            format_func=lambda x: x[0],
            key='hm_metric')
        hm_metric_label, hm_metric = _hm_metric_sel

    hdf = load_heatmap_data(hm_year)
    if hdf.empty:
        st.info(f"Sem dados para {hm_year}.")
        return

    n_valid   = hdf[hm_metric].notna().sum()
    n_sectors = hdf['CD_CVM'].map(sector_map).notna().sum()

    mc_a, mc_b, mc_c = st.columns(3)
    mc_a.metric("Empresas no ranking", n_valid)
    mc_b.metric("Com setor mapeado",   n_sectors)
    mc_c.metric("Ano de referência",   hm_year)

    fig = chart_sector_heatmap(hdf, sector_map, hm_metric, hm_metric_label, sel)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key='heatmap_main')
    else:
        st.warning("Dados insuficientes para gerar o ranking.")
