# -*- coding: utf-8 -*-
"""
dashboard/tabs/demo.py — Aba "Demonstrações".
"""
from __future__ import annotations

import streamlit as st

from dashboard.loaders import qsort


def render_demo(df) -> None:
    """Renderiza a aba Demonstrações Contábeis."""
    st.markdown('<div class="sec">Detalhamento Contábil</div>', unsafe_allow_html=True)
    all_stmts = sorted(df['STATEMENT_TYPE'].dropna().unique())

    dc1, dc2, dc3 = st.columns([2, 3, 2])
    with dc1:
        period_mode = st.radio("Período", ["Anual", "Trimestral"],
                               horizontal=True, key="demo_period")
    with dc2:
        stmt_filter = st.multiselect("Demonstrativos", all_stmts,
                                     default=list(all_stmts), key="demo_stmts")
    with dc3:
        hide_zeros = st.checkbox("Ocultar linhas zeradas", value=True, key="demo_zeros")

    table = df[df['STANDARD_NAME'].notna()].copy()
    if stmt_filter:
        table = table[table['STATEMENT_TYPE'].isin(stmt_filter)]

    if period_mode == "Anual":
        table    = table[table['PERIOD_LABEL'].str.match(r'^\d{4}$', na=False)]
        piv_col  = 'REPORT_YEAR'
        col_sort = sorted
    else:
        table    = table[table['PERIOD_LABEL'].str.match(r'^\dQ\d{2}$', na=False)]
        piv_col  = 'PERIOD_LABEL'
        col_sort = lambda cols: sorted(cols, key=qsort)

    if not table.empty:
        pv = table.pivot_table(
            index=['STATEMENT_TYPE', 'STANDARD_NAME'],
            columns=piv_col, values='VL_CONTA', aggfunc='sum'
        ).fillna(0)
        pv = pv[col_sort(pv.columns)]
        if hide_zeros:
            pv = pv[(pv != 0).any(axis=1)]
        pv.index = pv.index.set_names(['Tipo', 'Conta'])
        st.dataframe(pv.style.format('{:,.0f}'), use_container_width=True, height=580)
    else:
        st.info("Nenhum dado para os filtros selecionados.")
