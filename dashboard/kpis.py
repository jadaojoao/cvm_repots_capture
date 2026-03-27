# -*- coding: utf-8 -*-
"""
dashboard/kpis.py — Pré-computação de KPIs e utilitário safe_div.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from dashboard.constants import (
    RECEITA, LUCRO, RES_BRUT, DESP_OP,
    AT_CIRC, AT_NCIRC, CAIXA, PL,
    PASS_C, PASS_NC, DIVIDA, FCO, FCI,
)


def safe_div(a, b):
    """Divisão segura: retorna None se a ou b forem None/zero."""
    if a is not None and b is not None and b != 0:
        return a / b
    return None


@st.cache_data(ttl=120)
def precompute_kpis(cd_cvm: int, years_tuple: tuple) -> dict:
    """
    Calcula todos os KPIs anuais de uma vez, evitando 30+ filtros individuais.
    Retorna dict {year: {kpi: value}}.
    """
    # Import aqui para evitar importação circular (data → kpis → data)
    from dashboard.loaders import load_all

    df     = load_all(cd_cvm)
    annual = df[df['PERIOD_LABEL'].str.match(r'^\d{4}$', na=False)]

    result = {}
    for y in years_tuple:
        ay = annual[(annual['REPORT_YEAR'] == y) & (annual['PERIOD_LABEL'] == str(y))]
        if ay.empty:
            result[y] = {}
            continue

        def _g(names, _ay=ay):
            for n in names:
                r = _ay.loc[_ay['STANDARD_NAME'] == n, 'VL_CONTA']
                if not r.empty:
                    s = r.sum()
                    return float(s) if s != 0 else None
            return None

        rec  = _g(RECEITA);  luc  = _g(LUCRO);  rb   = _g(RES_BRUT)
        ac   = _g(AT_CIRC);  anc  = _g(AT_NCIRC)
        pl_v = _g(PL);       cx   = _g(CAIXA);  div  = _g(DIVIDA)
        pc   = _g(PASS_C);   pnc  = _g(PASS_NC)
        fco  = _g(FCO);      fci  = _g(FCI);    dop  = _g(DESP_OP)

        at      = ((ac or 0) + (anc or 0)) or None
        ebitda  = (rb + (dop or 0)) if rb else None
        div_liq = ((div or 0) - (cx or 0)) if div else None
        fcl     = ((fco or 0) + (fci or 0)) if (fco or fci) else None

        result[y] = dict(
            rec=rec, luc=luc, rb=rb, ac=ac, anc=anc, at=at,
            pl=pl_v, cx=cx, div=div, pc=pc, pnc=pnc,
            fco=fco, fci=fci, dop=dop, ebitda=ebitda,
            div_liq=div_liq, fcl=fcl,
            mb=safe_div(rb, rec), ml=safe_div(luc, rec),
            roe=safe_div(luc, pl_v), roa=safe_div(luc, at),
            liq_corr=safe_div(ac, pc),
            alav=safe_div(div_liq, ebitda) if div else None,
        )
    return result


@st.cache_data(ttl=300)
def compute_peer_kpis(raw_df_json: str) -> pd.DataFrame:
    """Calcula KPIs dos peers a partir do DataFrame serializado (JSON)."""
    if not raw_df_json:
        return pd.DataFrame()
    peers_df = pd.read_json(io.StringIO(raw_df_json))
    rows = []
    for cd in peers_df['CD_CVM'].unique():
        p    = peers_df[peers_df['CD_CVM'] == cd]
        name = p['COMPANY_NAME'].iloc[0] if 'COMPANY_NAME' in p.columns else str(cd)

        def _s(names, _p=p):
            v = _p[_p['STANDARD_NAME'].isin(names)]['VL_CONTA'].sum()
            return float(v) if v != 0 else None

        rec  = _s(RECEITA); luc = _s(LUCRO); rb  = _s(RES_BRUT)
        ac   = _s(AT_CIRC); anc = _s(AT_NCIRC); pl_v = _s(PL)
        at   = ((ac or 0) + (anc or 0)) or None
        rows.append({
            'Empresa':             name,
            'CD_CVM':              int(cd),
            'Receita (R$ mi)':     round(rec / 1e3, 1) if rec else None,
            'Lucro (R$ mi)':       round(luc / 1e3, 1) if luc else None,
            'Ativo Total (R$ mi)': round(at  / 1e3, 1) if at  else None,
            'Margem Líquida':      safe_div(luc, rec),
            'Margem Bruta':        safe_div(rb,  rec),
            'ROE':                 safe_div(luc, pl_v),
            'ROA':                 safe_div(luc, at),
        })
    return (pd.DataFrame(rows)
            .sort_values('Receita (R$ mi)', ascending=False, na_position='last')
            .reset_index(drop=True))
