# -*- coding: utf-8 -*-
"""
dashboard/tabs/export.py — Aba "Exportar" (download Excel).
"""
from __future__ import annotations

import io
import re

import pandas as pd
import streamlit as st

from dashboard.loaders import qsort


def build_excel(name: str, df: pd.DataFrame, years: tuple, kpis_by_year: dict):
    """Gera workbook Excel com 3 abas: Indicadores, Trimestral, Base_CVM."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        wb  = w.book
        hdr = wb.add_format({'bold': True, 'bg_color': '#00BF7A',
                              'font_color': '#000', 'border': 1})
        nf  = wb.add_format({'num_format': '#,##0', 'border': 1})
        pf  = wb.add_format({'num_format': '0.0%', 'border': 1})
        tf  = wb.add_format({'border': 1})

        rows = []
        for y in sorted(years):
            k = kpis_by_year.get(y, {})
            rows.append({
                'Ano':                      y,
                'Receita':                  k.get('rec'),
                'Lucro':                    k.get('luc'),
                'Ativo Total':              k.get('at'),
                'PL':                       k.get('pl'),
                'Res.Bruto':                k.get('rb'),
                'FCO':                      k.get('fco'),
                'FCI':                      k.get('fci'),
                'FCL (FCO+FCI)':            k.get('fcl'),
                'Dívida Líquida':           k.get('div_liq'),
                'EBITDA (Proxy)':           k.get('ebitda'),
                'Margem Bruta':             k.get('mb'),
                'Margem Líquida':           k.get('ml'),
                'ROE':                      k.get('roe'),
                'ROA':                      k.get('roa'),
                'Alavancagem (Dív/EBITDA)': k.get('alav'),
            })
        kdf = pd.DataFrame(rows)
        kdf.to_excel(w, sheet_name='Indicadores', index=False, startrow=1)
        ws = w.sheets['Indicadores']
        ws.write(0, 0, f'Indicadores — {name}',
                 wb.add_format({'bold': True, 'font_size': 14}))
        pct_cols = {'Margem Bruta', 'Margem Líquida', 'ROE', 'ROA'}
        for ci, col in enumerate(kdf.columns):
            ws.write(1, ci, col, hdr)
        for ri in range(len(kdf)):
            for ci, col in enumerate(kdf.columns):
                v = kdf.iloc[ri, ci]
                if col == 'Ano':      ws.write(ri+2, ci, v, tf)
                elif col in pct_cols: ws.write(ri+2, ci, v if pd.notna(v) else '', pf)
                else:                 ws.write(ri+2, ci, v if pd.notna(v) else '', nf)
        ws.set_column('A:A', 8); ws.set_column('B:N', 18); ws.set_column('O:P', 22)

        qtrs = df[df['PERIOD_LABEL'].str.match(r'^\dQ\d{2}$', na=False)
                  & df['STANDARD_NAME'].notna()]
        if not qtrs.empty:
            pv = qtrs.pivot_table(
                index=['STATEMENT_TYPE', 'STANDARD_NAME'],
                columns='PERIOD_LABEL', values='VL_CONTA', aggfunc='sum'
            ).fillna(0)
            pv = pv[sorted(pv.columns, key=qsort)]
            pv.to_excel(w, sheet_name='Trimestral')
            w.sheets['Trimestral'].set_column('A:B', 22)
            w.sheets['Trimestral'].set_column('C:Z', 14)

        cols_out = [c for c in ['REPORT_YEAR', 'STATEMENT_TYPE', 'PERIOD_LABEL',
                                 'CD_CONTA', 'DS_CONTA', 'STANDARD_NAME', 'VL_CONTA']
                    if c in df.columns]
        df[cols_out].to_excel(w, sheet_name='Base_CVM', index=False)
        ws3 = w.sheets['Base_CVM']
        ws3.set_column('A:A', 10); ws3.set_column('B:C', 14)
        ws3.set_column('D:F', 40); ws3.set_column('G:G', 16)

    buf.seek(0)
    safe = re.sub(r'[^\w]', '_', name).strip('_')
    return buf.getvalue(), f'CVM_{safe}.xlsx'


def render_export(sel: str, cvm: int, df: pd.DataFrame,
                  years: tuple, kpis: dict) -> None:
    """Renderiza a aba Exportar."""
    st.markdown('<div class="sec">Exportação de Dados</div>', unsafe_allow_html=True)

    ex1, ex2 = st.columns([3, 1])
    with ex1:
        st.markdown(
            f"**Empresa:** {sel}  \n"
            f"**Código CVM:** {cvm}  \n"
            f"**Períodos disponíveis:** {', '.join(str(y) for y in years)}  \n"
            f"**Registros no banco:** {len(df):,}"
        )
    with ex2:
        try:
            xls, xname = build_excel(sel, df, years, kpis)
            st.download_button(
                label="⬇  Exportar Excel",
                data=xls,
                file_name=xname,
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key=f'dl_{cvm}',
            )
            st.caption(f'`{xname}` · 3 abas')
        except Exception as e:
            st.error(f"Erro ao gerar Excel: {e}")
