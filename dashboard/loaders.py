# -*- coding: utf-8 -*-
"""
dashboard/loaders.py — Carregamento de dados com cache e utilitários de extração.
"""
from __future__ import annotations

import io
import os
import re

import pandas as pd
import requests
import streamlit as st
from sqlalchemy import text, bindparam

from dashboard.db import get_engine
from dashboard.constants import (
    RECEITA, LUCRO, RES_BRUT, AT_CIRC, AT_NCIRC, PL,
)
from dashboard.kpis import safe_div

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

# Raiz do projeto (um nível acima de dashboard/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Utilitários de extração ────────────────────────────────────────────────────

def val(df: pd.DataFrame, names, year: int, period=None):
    """Extrai valor anual ou trimestral do DataFrame longo.
    Retorna o primeiro nome da lista que tiver dados (alias alternativo)."""
    if isinstance(names, str):
        names = [names]
    p = period if period else str(year)
    base = df[(df['REPORT_YEAR'] == year) & (df['PERIOD_LABEL'] == p)]
    for n in names:
        r = base.loc[base['STANDARD_NAME'] == n, 'VL_CONTA']
        if not r.empty:
            s = r.sum()
            return float(s) if s != 0 else None
    return None


def qsort(label: str) -> tuple:
    """Chave de ordenação para period labels ('1Q24' < '2Q24' < '2024')."""
    m = re.match(r'(\d)Q(\d{2})', str(label))
    return (int('20' + m.group(2)), int(m.group(1))) if m else (9999, 0)


# ── Queries com cache ──────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_companies() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT DISTINCT CD_CVM, COMPANY_NAME FROM financial_reports "
                 "WHERE COMPANY_NAME IS NOT NULL ORDER BY COMPANY_NAME"), conn)
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def load_cvm_master() -> pd.DataFrame:
    """Lista completa de empresas abertas da CVM (DENOM_SOCIAL + DENOM_COMERC).
    Cache 24h. Retorna DataFrame vazio se a requisição falhar."""
    url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        df = pd.read_csv(
            io.BytesIO(resp.content), sep=";", encoding="latin1",
            usecols=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "SIT"],
        )
        df["CD_CVM"] = pd.to_numeric(df["CD_CVM"], errors="coerce")
        df = df.dropna(subset=["CD_CVM"]).copy()
        df["CD_CVM"] = df["CD_CVM"].astype(int)
        df["DENOM_SOCIAL"] = df["DENOM_SOCIAL"].fillna("").str.strip()
        df["DENOM_COMERC"] = df["DENOM_COMERC"].fillna("").str.strip()
        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "SIT"])


@st.cache_data(ttl=300)
def load_sectors() -> dict:
    excel_base = os.path.join(
        _ROOT, 'output', 'reports', 'base_analitica_dashboard_preenchida.xlsx'
    )
    _overrides = {
        24783: 'Farmacêutico e Higiene',
        22217: 'Seguradoras e Corretoras',
        22187: 'Petróleo e Gás',
        25291: 'Petróleo e Gás',
         5410: 'Máquinas, Equipamentos, Veículos e Peças',
         2437: 'Energia Elétrica',
    }
    if os.path.exists(excel_base):
        df = pd.read_excel(excel_base)
        sm = (df[['cd_cvm', 'setor_analitico']].drop_duplicates()
              .set_index('cd_cvm')['setor_analitico'].to_dict())
        sm.update(_overrides)
        return sm
    return dict(_overrides)


@st.cache_data(ttl=120)
def load_all(cd_cvm: int) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT * FROM financial_reports WHERE CD_CVM = :cvm"),
            conn, params={"cvm": int(cd_cvm)})
    df['REPORT_YEAR'] = df['REPORT_YEAR'].astype(int)
    return df


@st.cache_data(ttl=300)
def load_heatmap_data(year: int) -> pd.DataFrame:
    """Carrega KPIs de TODAS as empresas num único query para o heatmap setorial."""
    _year = int(year)
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT CD_CVM, COMPANY_NAME, STANDARD_NAME, VL_CONTA "
                 "FROM financial_reports "
                 "WHERE REPORT_YEAR = :year AND PERIOD_LABEL = :label"),
            conn, params={"year": _year, "label": str(_year)})
    if df.empty:
        return pd.DataFrame()

    rows = []
    for cd, grp in df.groupby('CD_CVM'):
        name = grp['COMPANY_NAME'].iloc[0]

        def _get_val(names, _df=grp):
            for n in names:
                r = _df.loc[_df['STANDARD_NAME'] == n, 'VL_CONTA']
                if not r.empty:
                    s = r.sum()
                    return float(s) if s != 0 else None
            return None

        rec  = _get_val(RECEITA); luc = _get_val(LUCRO); rb  = _get_val(RES_BRUT)
        ac   = _get_val(AT_CIRC); anc = _get_val(AT_NCIRC); pl_v = _get_val(PL)
        at   = ((ac or 0) + (anc or 0)) or None
        rows.append({
            'CD_CVM':  int(cd),
            'Empresa': name,
            'ML':      safe_div(luc, rec),
            'MB':      safe_div(rb,  rec),
            'ROE':     safe_div(luc, pl_v),
            'ROA':     safe_div(luc, at),
            'Receita': rec,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def load_market_data(ticker: str) -> dict:
    """Busca dados de mercado via yfinance. Cache 15 min. Retorna {} se falhar."""
    if not _YF_AVAILABLE or not ticker:
        return {}
    try:
        info    = yf.Ticker(ticker).info
        price   = info.get('currentPrice') or info.get('regularMarketPrice')
        mktcap  = info.get('marketCap')
        pe      = info.get('trailingPE')
        pb      = info.get('priceToBook')
        ev_ebit = info.get('enterpriseToEbitda')
        dy      = info.get('dividendYield')
        ev      = info.get('enterpriseValue')
        curr    = info.get('currency', 'BRL')
        if price is None:
            return {}
        return dict(price=price, mktcap=mktcap, pe=pe, pb=pb,
                    ev_ebitda=ev_ebit, dy=dy, ev=ev, currency=curr, ticker=ticker)
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def load_price_history(ticker: str) -> pd.DataFrame:
    """Histórico de preço + volume de 1 ano via yfinance.
    Retorna DataFrame com colunas Date, Close, Volume (ou vazio se falhar)."""
    if not _YF_AVAILABLE or not ticker:
        return pd.DataFrame()
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()[['Date', 'Close', 'Volume']].copy()
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        # Média móvel 20 dias
        df['MA20'] = df['Close'].rolling(20, min_periods=1).mean()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_peer_df(sector: str, sector_map_items: tuple) -> pd.DataFrame:
    """Carrega dados dos peers num único query parametrizado."""
    sm        = dict(sector_map_items)
    peer_cvms = [int(c) for c, s in sm.items() if s == sector]
    if not peer_cvms:
        return pd.DataFrame()
    engine = get_engine()
    stmt = text(
        "SELECT * FROM financial_reports "
        "WHERE CD_CVM IN :cvms AND REPORT_YEAR=2024 AND PERIOD_LABEL='2024'"
    ).bindparams(bindparam("cvms", expanding=True))
    with engine.connect() as conn:
        result = conn.execute(stmt, {"cvms": peer_cvms})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df
