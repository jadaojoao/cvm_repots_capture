# -*- coding: utf-8 -*-
"""
dashboard/tabs/peers.py — Aba "Peers".
"""
from __future__ import annotations

import streamlit as st

from dashboard.charts import pct, COLORS, chart_peer_bars, chart_peer_scatter
from dashboard.loaders import load_peer_df
from dashboard.kpis import compute_peer_kpis


def render_peers(sel: str, cvm: int, kpis: dict, latest: int,
                 this_sector: str, sector_map: dict) -> None:
    """Renderiza a aba Peers."""
    if this_sector == 'N/D':
        st.info(
            "Setor não mapeado para esta empresa. "
            "Preencha `base_analitica_dashboard_preenchida.xlsx` e recarregue."
        )
        return

    st.markdown(f'<div class="sec">Setor: {this_sector}</div>', unsafe_allow_html=True)

    sector_map_items = tuple(sorted(sector_map.items()))
    raw_peer_df      = load_peer_df(this_sector, sector_map_items)

    if raw_peer_df.empty:
        st.info("Sem dados de peers disponíveis para este setor em 2024.")
        return

    peer_df    = compute_peer_kpis(raw_peer_df.to_json())
    k          = kpis.get(latest, {})
    roe_v      = k.get('roe'); ml_v = k.get('ml')
    roe_sector = peer_df['ROE'].mean() if not peer_df.empty else None
    ml_sector  = peer_df['Margem Líquida'].mean() if not peer_df.empty else None

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        fig = chart_peer_bars(roe_v, roe_sector, 'ROE', COLORS['green'])
        st.plotly_chart(fig, use_container_width=True, key='peer_roe')
    with pc2:
        fig = chart_peer_bars(ml_v, ml_sector, 'Margem Líq.', COLORS['blue'])
        st.plotly_chart(fig, use_container_width=True, key='peer_ml')
    with pc3:
        st.metric(
            "ROE vs Setor", pct(roe_v),
            f'{(roe_v - roe_sector)*100:+.1f} pp vs média' if roe_v and roe_sector else '—',
        )
        st.metric(
            "Margem Líq. vs Setor", pct(ml_v),
            f'{(ml_v - ml_sector)*100:+.1f} pp vs média' if ml_v and ml_sector else '—',
        )

    st.markdown('<div class="sec">Ranking do Setor (2024)</div>', unsafe_allow_html=True)
    display_df  = peer_df.drop(columns=['CD_CVM'], errors='ignore').copy()
    pct_cols_p  = ['Margem Líquida', 'Margem Bruta', 'ROE', 'ROA']
    fmt         = {c: '{:.1%}' for c in pct_cols_p if c in display_df.columns}
    fmt.update({c: '{:,.1f}' for c in
                ['Receita (R$ mi)', 'Lucro (R$ mi)', 'Ativo Total (R$ mi)']
                if c in display_df.columns})
    st.dataframe(display_df.style.format(fmt, na_rep='—'),
                 use_container_width=True, height=300)

    st.markdown(
        '<div class="sec">Mapa de Posicionamento — Margem Líquida vs ROE</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<p class="scatter-note">Tamanho da bolha proporcional ao Ativo Total. '
        'Empresa selecionada em verde.</p>',
        unsafe_allow_html=True)
    fig = chart_peer_scatter(peer_df, sel)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key='peer_scatter')
