# -*- coding: utf-8 -*-
"""
dashboard/kpis.py — Pré-computação de KPIs e utilitário safe_div.

Indicadores implementados (referência: Indicadores_Financeiros_DFP_ITR_CVM.pdf):
  Liquidez:      liq_corr, liq_seca, liq_imediata, liq_geral, cgl
  Margens:       mb, mg_ebit, mg_ebitda, ml, mg_ant_ir
  Retorno:       roe, roa, giro_ativo, mult_pl, dupont_roe, tax_burden, int_burden
  Endividamento: div_liq, alav, alav_ebit, endiv_geral, de_ratio, div_pl,
                 div_liq_pl, comp_endiv, imo_pl, imo_rnc
  Cobertura:     icr_ebit, icr_liq
  Atividade:     pmr, pme, pmp, ciclo_op, ciclo_fin, giro_estoques, giro_ativo_fixo
  Fluxo Caixa:   fco, fci, fcf_fin, fcl, fco_lucro, fco_div_liq, ccr,
                 capex_proxy, capex_rec, fco_capex
  Horizontal:    yoy_rec, yoy_luc, yoy_ebit, cagr_rec
"""
from __future__ import annotations

import io
import re

import pandas as pd
import streamlit as st

from dashboard.constants import (
    RECEITA, LUCRO, RES_BRUT, CUSTO, DESP_OP,
    AT_CIRC, AT_NCIRC, CAIXA, PL,
    PASS_C, PASS_NC, DIVIDA, FCO, FCI, FCF_ACTIV,
    EBIT_REAL, EBT, DESP_FIN, REC_FIN,
    ESTOQUES, CLIENTES, APLIC_FIN, RLP,
    FORNEC, IMOB,
)


def safe_div(a, b):
    """Divisão segura: retorna None se a ou b forem None/zero."""
    if a is not None and b is not None and b != 0:
        return a / b
    return None


def _get_da(df: pd.DataFrame, year: int) -> float | None:
    """
    Extrai D&A da DFC método indireto por keyword em DS_CONTA.
    Busca subcontas do 6.01 com 'deprec', 'amort', 'exaust', 'deplec'
    e exclui linhas de financiamentos (amortização de dívida).
    """
    mask = (
        (df['REPORT_YEAR'] == year)
        & (df['PERIOD_LABEL'] == str(year))
        & (df['STATEMENT_TYPE'] == 'DFC')
        & df['CD_CONTA'].str.startswith('6.01', na=False)
        & df['DS_CONTA'].str.contains(
            r'deprec|amort|exaust|deplec', case=False, na=False, regex=True
        )
        & ~df['DS_CONTA'].str.contains(
            r'financi|arrendamen|principal|juros', case=False, na=False, regex=True
        )
    )
    sub = df.loc[mask, 'VL_CONTA']
    if sub.empty:
        return None
    val = float(sub.sum())
    return val if val != 0 else None


@st.cache_data(ttl=120)
def precompute_kpis(cd_cvm: int, years_tuple: tuple) -> dict:
    """
    Calcula todos os KPIs anuais de uma vez.
    Retorna dict {year: {kpi: value}}.
    """
    from dashboard.loaders import load_all

    df     = load_all(cd_cvm)
    annual = df[df['PERIOD_LABEL'].str.match(r'^\d{4}$', na=False)]

    # Primeira passagem: coletar valores brutos por ano
    raw: dict[int, dict] = {}
    for y in years_tuple:
        ay = annual[(annual['REPORT_YEAR'] == y) & (annual['PERIOD_LABEL'] == str(y))]
        if ay.empty:
            raw[y] = {}
            continue

        def _g(names, _ay=ay):
            for n in names:
                r = _ay.loc[_ay['STANDARD_NAME'] == n, 'VL_CONTA']
                if not r.empty:
                    s = r.sum()
                    return float(s) if s != 0 else None
            return None

        def _gsum(names, _ay=ay):
            """Soma TODOS os aliases (para contas que podem ter múltiplas linhas)."""
            total = _ay.loc[_ay['STANDARD_NAME'].isin(names), 'VL_CONTA'].sum()
            return float(total) if total != 0 else None

        rec    = _g(RECEITA)
        luc    = _g(LUCRO)
        rb     = _g(RES_BRUT)
        cpv    = _g(CUSTO)
        ac     = _g(AT_CIRC)
        anc    = _g(AT_NCIRC)
        pl_v   = _g(PL)
        cx     = _g(CAIXA)
        div    = _gsum(DIVIDA)
        pc     = _g(PASS_C)
        pnc    = _g(PASS_NC)
        fco_v  = _g(FCO)
        fci_v  = _g(FCI)
        fcf_v  = _g(FCF_ACTIV)
        ebit_v = _g(EBIT_REAL)
        ebt_v  = _g(EBT)
        df_v   = _g(DESP_FIN)
        rf_v   = _g(REC_FIN)
        est    = _g(ESTOQUES)
        cli    = _gsum(CLIENTES)
        aplic  = _gsum(APLIC_FIN)
        rlp_v  = _g(RLP)
        forn   = _gsum(FORNEC)
        imob   = _g(IMOB)
        da_v   = _get_da(df, y)

        raw[y] = dict(
            rec=rec, luc=luc, rb=rb, cpv=cpv,
            ac=ac, anc=anc, pl=pl_v, cx=cx, div=div,
            pc=pc, pnc=pnc,
            fco=fco_v, fci=fci_v, fcf_fin=fcf_v,
            ebit=ebit_v, ebt=ebt_v,
            df=df_v, rf=rf_v,
            est=est, cli=cli, aplic=aplic, rlp=rlp_v,
            forn=forn, imob=imob, da=da_v,
        )

    # Segunda passagem: calcular KPIs derivados (incluindo médias de PL/AT)
    result = {}
    sorted_years = sorted(years_tuple)
    for i, y in enumerate(sorted_years):
        r = raw.get(y, {})
        if not r:
            result[y] = {}
            continue

        rec    = r.get('rec');   luc  = r.get('luc');  rb   = r.get('rb')
        cpv    = r.get('cpv');   ac   = r.get('ac');   anc  = r.get('anc')
        pl_v   = r.get('pl');    cx   = r.get('cx');   div  = r.get('div')
        pc     = r.get('pc');    pnc  = r.get('pnc')
        fco_v  = r.get('fco');   fci_v = r.get('fci'); fcf_v = r.get('fcf_fin')
        ebit_v = r.get('ebit');  ebt_v = r.get('ebt')
        df_v   = r.get('df');    rf_v  = r.get('rf')
        est    = r.get('est');   cli   = r.get('cli'); aplic = r.get('aplic')
        rlp_v  = r.get('rlp');   forn  = r.get('forn'); imob = r.get('imob')
        da_v   = r.get('da')

        # Valores derivados base
        at      = ((ac or 0) + (anc or 0)) or None
        ebitda  = (ebit_v + da_v) if (ebit_v and da_v) else None
        aplic_s = aplic or 0
        div_liq = ((div or 0) - (cx or 0) - aplic_s) if div else None
        fcl     = ((fco_v or 0) + (fci_v or 0)) if (fco_v or fci_v) else None

        # Médias de PL e AT para ROE/ROA (Bug 2)
        prev_y = sorted_years[i - 1] if i > 0 else None
        r_prev = raw.get(prev_y, {}) if prev_y else {}
        pl_prev = r_prev.get('pl')
        at_prev = ((r_prev.get('ac') or 0) + (r_prev.get('anc') or 0)) or None

        pl_med = ((pl_v + pl_prev) / 2) if (pl_v and pl_prev) else pl_v
        at_med = ((at + at_prev) / 2) if (at and at_prev) else at

        # Análise horizontal
        r_prev_y = raw.get(sorted_years[i - 1], {}) if i > 0 else {}
        yoy_rec  = safe_div(rec, r_prev_y.get('rec')) - 1 if (rec and r_prev_y.get('rec')) else None
        yoy_luc  = safe_div(luc, r_prev_y.get('luc')) - 1 if (luc and r_prev_y.get('luc')) else None
        yoy_ebit = safe_div(ebit_v, r_prev_y.get('ebit')) - 1 if (ebit_v and r_prev_y.get('ebit')) else None

        # CAGR receita (3 anos)
        cagr_rec = None
        if i >= 2:
            rec_base = raw.get(sorted_years[i - 2], {}).get('rec')
            if rec and rec_base and rec_base > 0:
                cagr_rec = (rec / rec_base) ** (1 / 2) - 1

        result[y] = dict(
            # ── Valores absolutos ──────────────────────────────────────────────
            rec=rec, luc=luc, rb=rb, cpv=cpv,
            ac=ac, anc=anc, at=at, pl=pl_v, cx=cx, div=div, aplic=aplic,
            pc=pc, pnc=pnc,
            fco=fco_v, fci=fci_v, fcf_fin=fcf_v,
            ebit=ebit_v, ebt=ebt_v, ebitda=ebitda, da=da_v,
            div_liq=div_liq, fcl=fcl,
            est=est, cli=cli, rlp=rlp_v, forn=forn, imob=imob,

            # ── Liquidez ──────────────────────────────────────────────────────
            liq_corr    = safe_div(ac, pc),
            liq_seca    = safe_div((ac or 0) - (est or 0), pc) if ac and pc else None,
            liq_imediata= safe_div((cx or 0) + aplic_s, pc) if pc else None,
            liq_geral   = safe_div((ac or 0) + (rlp_v or 0), (pc or 0) + (pnc or 0)) if (ac and (pc or pnc)) else None,
            cgl         = ((ac or 0) - (pc or 0)) if (ac and pc) else None,

            # ── Margens ───────────────────────────────────────────────────────
            mb      = safe_div(rb, rec),
            mg_ebit = safe_div(ebit_v, rec),
            mg_ebitda = safe_div(ebitda, rec),
            ml      = safe_div(luc, rec),
            mg_ant_ir = safe_div(ebt_v, rec),

            # ── Retorno ───────────────────────────────────────────────────────
            roe         = safe_div(luc, pl_med),
            roa         = safe_div(luc, at_med),
            giro_ativo  = safe_div(rec, at_med),
            mult_pl     = safe_div(at, pl_v),
            dupont_roe  = safe_div(luc, rec) * safe_div(rec, at_med) * safe_div(at, pl_v)
                          if (luc and rec and at_med and pl_v) else None,
            tax_burden  = safe_div(luc, ebt_v),
            int_burden  = safe_div(ebt_v, ebit_v),

            # ── Endividamento ─────────────────────────────────────────────────
            alav        = safe_div(div_liq, ebitda),
            alav_ebit   = safe_div(div_liq, ebit_v),
            endiv_geral = safe_div((pc or 0) + (pnc or 0), at) if at else None,
            de_ratio    = safe_div((pc or 0) + (pnc or 0), pl_v) if pl_v else None,
            div_pl      = safe_div(div, pl_v),
            div_liq_pl  = safe_div(div_liq, pl_v),
            comp_endiv  = safe_div(pc, (pc or 0) + (pnc or 0)) if (pc and (pc or pnc)) else None,
            imo_pl      = safe_div(anc, pl_v),
            imo_rnc     = safe_div(anc, (pl_v or 0) + (pnc or 0)) if anc else None,

            # ── Cobertura ─────────────────────────────────────────────────────
            icr_ebit = safe_div(ebit_v, abs(df_v) if df_v else None),
            icr_liq  = safe_div(ebit_v, abs((df_v or 0) - (rf_v or 0)) or None) if ebit_v else None,

            # ── Atividade ─────────────────────────────────────────────────────
            pmr            = safe_div(cli, rec) * 360 if cli and rec else None,
            pme            = safe_div(est, cpv) * 360 if est and cpv else None,
            pmp            = safe_div(forn, cpv) * 360 if forn and cpv else None,
            ciclo_op       = (safe_div(cli, rec) * 360 + safe_div(est, cpv) * 360)
                             if (cli and rec and est and cpv) else None,
            ciclo_fin      = (safe_div(cli, rec) * 360 + safe_div(est, cpv) * 360
                              - safe_div(forn, cpv) * 360)
                             if (cli and rec and est and cpv and forn) else None,
            giro_estoques  = safe_div(cpv, est),
            giro_ativo_fixo= safe_div(rec, imob),

            # ── Fluxo de Caixa ────────────────────────────────────────────────
            fco_lucro  = safe_div(fco_v, luc),
            fco_div_liq= safe_div(fco_v, div_liq),
            ccr        = safe_div(fco_v, ebitda),
            capex_proxy= abs(fci_v) if fci_v else None,
            capex_rec  = safe_div(abs(fci_v), rec) if fci_v and rec else None,
            fco_capex  = safe_div(fco_v, abs(fci_v)) if fco_v and fci_v else None,

            # ── Análise Horizontal ────────────────────────────────────────────
            yoy_rec=yoy_rec, yoy_luc=yoy_luc, yoy_ebit=yoy_ebit,
            cagr_rec=cagr_rec,
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
        pc   = _s(PASS_C);  pnc = _s(PASS_NC); div = _s(DIVIDA)
        at   = ((ac or 0) + (anc or 0)) or None
        ebit = _s(EBIT_REAL)
        div_liq = ((div or 0) - (_s(CAIXA) or 0) - (_s(APLIC_FIN) or 0)) if div else None

        rows.append({
            'Empresa':             name,
            'CD_CVM':              int(cd),
            'Receita (R$ mi)':     round(rec / 1e3, 1) if rec else None,
            'Lucro (R$ mi)':       round(luc / 1e3, 1) if luc else None,
            'EBIT (R$ mi)':        round(ebit / 1e3, 1) if ebit else None,
            'Ativo Total (R$ mi)': round(at  / 1e3, 1) if at  else None,
            'Dív. Líq (R$ mi)':    round(div_liq / 1e3, 1) if div_liq else None,
            'Margem Líquida':      safe_div(luc, rec),
            'Margem Bruta':        safe_div(rb,  rec),
            'Margem EBIT':         safe_div(ebit, rec),
            'ROE':                 safe_div(luc, pl_v),
            'ROA':                 safe_div(luc, at),
            'Liq. Corrente':       safe_div(ac, pc),
            'Dív.Líq/EBIT':        safe_div(div_liq, ebit),
        })
    return (pd.DataFrame(rows)
            .sort_values('Receita (R$ mi)', ascending=False, na_position='last')
            .reset_index(drop=True))
