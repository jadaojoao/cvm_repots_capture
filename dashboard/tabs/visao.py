# -*- coding: utf-8 -*-
"""
dashboard/tabs/visao.py — Aba "Visão Geral".
"""
from __future__ import annotations

import streamlit as st

from dashboard.charts import (
    brl, pct, COLORS,
    chart_bars, chart_line, chart_line_compare,
    chart_donut, sparkline, chart_dfc_grouped, chart_yoy_waterfall,
    chart_price_history,
)
from dashboard.constants import RECEITA, LUCRO, RES_BRUT, FCO, TICKER_MAP
from dashboard.loaders import load_all, load_market_data, load_price_history
from dashboard.kpis import precompute_kpis, safe_div


def render_visao_geral(sel: str, cvm: int, df, years: tuple, latest: int,
                       kpis: dict, companies) -> None:
    """Renderiza a aba Visão Geral completa."""

    # ── Seletor de empresa para comparação ────────────────────────────────────
    _cmp_opts = {'— Nenhuma —': None}
    _cmp_opts.update({
        r['COMPANY_NAME']: int(r['CD_CVM'])
        for _, r in companies.iterrows()
        if int(r['CD_CVM']) != cvm
    })
    _cmp_sel = st.selectbox('Comparar com:', list(_cmp_opts.keys()),
                            index=0, key='cmp_company')
    _cmp_cvm = _cmp_opts[_cmp_sel]
    if _cmp_cvm is not None:
        _cmp_df    = load_all(_cmp_cvm)
        _cmp_years = tuple(sorted(_cmp_df['REPORT_YEAR'].unique())) if not _cmp_df.empty else ()
        _cmp_kpis  = precompute_kpis(_cmp_cvm, _cmp_years) if _cmp_years else {}
    else:
        _cmp_years = ()
        _cmp_kpis  = {}

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    k      = kpis.get(latest, {})
    k_prev = kpis.get(years[-2], {}) if len(years) >= 2 else {}

    def yoy(curr, prev):
        g = safe_div(curr, prev)
        return f'{(g-1)*100:+.1f}% YoY' if g is not None else None

    def yoy_pp(curr, prev):
        if curr is not None and prev is not None:
            return f'{(curr-prev)*100:+.1f} pp'
        return None

    st.markdown('<div class="sec">Indicadores Principais</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Receita Líq.",   brl(k.get('rec')), yoy(k.get('rec'), k_prev.get('rec')),
              help="Receitas de venda e serviços.")
    c2.metric("Lucro Líq.",     brl(k.get('luc')), yoy(k.get('luc'), k_prev.get('luc')),
              help="Resultado final após impostos.")
    c3.metric("Ativo Total",    brl(k.get('at')),  help="Bens + Direitos da empresa.")
    c4.metric("ROE",            pct(k.get('roe')), yoy_pp(k.get('roe'), k_prev.get('roe')),
              help="Lucro / Patrimônio Líquido.")
    c5.metric("Dívida/EBITDA",
              f"{k['alav']:.2f}x" if k.get('alav') else "—",
              help="Dívida Líquida / EBITDA proxy.")
    c6.metric("Liq. Corrente",
              f"{k['liq_corr']:.2f}x" if k.get('liq_corr') else "—",
              help="Ativo Circ. / Passivo Circ.")

    # Sparklines
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    spark_data = [
        (s1, {y: kpis[y].get('rec')      for y in years}, COLORS['blue'],   'sp_rec'),
        (s2, {y: kpis[y].get('luc')      for y in years}, COLORS['purple'], 'sp_luc'),
        (s3, {y: kpis[y].get('at')       for y in years}, COLORS['amber'],  'sp_at'),
        (s4, {y: kpis[y].get('roe')      for y in years}, COLORS['green'],  'sp_roe'),
        (s5, {y: kpis[y].get('alav')     for y in years}, COLORS['red'],    'sp_alav'),
        (s6, {y: kpis[y].get('liq_corr') for y in years}, COLORS['green'],  'sp_liq'),
    ]
    for col, data, color, key in spark_data:
        with col:
            st.plotly_chart(sparkline(data, color), use_container_width=True,
                            config={'staticPlot': True}, key=key)

    # ── Valuation de Mercado ───────────────────────────────────────────────────
    _ticker = TICKER_MAP.get(int(cvm))
    _mkt    = load_market_data(_ticker) if _ticker else {}

    st.markdown('<div class="sec">Valuation de Mercado</div>', unsafe_allow_html=True)
    if _mkt:
        def _fmt_mktcap(v):
            if v is None: return '—'
            if v >= 1e12: return f'R$ {v/1e12:.2f} tri'
            if v >= 1e9:  return f'R$ {v/1e9:.1f} bi'
            if v >= 1e6:  return f'R$ {v/1e6:.0f} mi'
            return f'R$ {v:,.0f}'

        mv1, mv2, mv3, mv4, mv5, mv6 = st.columns(6)
        mv1.metric("Preço",      f"R$ {_mkt['price']:.2f}", help=f"Cotação atual ({_ticker})")
        mv2.metric("Market Cap", _fmt_mktcap(_mkt.get('mktcap')), help="Valor de mercado total")
        mv3.metric("P/L",        f"{_mkt['pe']:.1f}x" if _mkt.get('pe') else '—',
                   help="Preço / Lucro por ação (trailing 12m)")
        mv4.metric("P/VP",       f"{_mkt['pb']:.2f}x" if _mkt.get('pb') else '—',
                   help="Preço / Valor Patrimonial")
        mv5.metric("EV/EBITDA",  f"{_mkt['ev_ebitda']:.1f}x" if _mkt.get('ev_ebitda') else '—',
                   help="Enterprise Value / EBITDA (trailing 12m)")
        mv6.metric("Div. Yield", f"{_mkt['dy']:.1f}%" if _mkt.get('dy') else '—',
                   help="Dividend Yield (12m)")
        st.caption(
            f"📡 Fonte: Yahoo Finance · Ticker: `{_ticker}` · "
            f"Atualizado a cada 15 min · Valores em {_mkt.get('currency', 'BRL')}"
        )
    elif not _ticker:
        st.caption(
            f"ℹ️ Ticker não mapeado para CVM {cvm}. "
            "Adicione em `TICKER_MAP` em `dashboard/constants.py`."
        )
    else:
        st.caption(
            f"⚠️ Não foi possível obter dados de mercado para `{_ticker}`. "
            "Verifique a conexão ou tente novamente."
        )

    # ── Histórico de Preço (1 ano) ─────────────────────────────────────────────
    st.markdown('<div class="sec">Histórico de Preço (12 meses)</div>', unsafe_allow_html=True)
    if _ticker:
        df_hist = load_price_history(_ticker)
        fig = chart_price_history(df_hist, _ticker)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key='price_hist')
        else:
            st.caption(
                f"⚠️ Não foi possível carregar o histórico de preços para `{_ticker}`. "
                "Verifique a conexão com a internet."
            )
    else:
        st.caption(
            f"ℹ️ Ticker não mapeado para CVM {cvm}. "
            "Adicione em `TICKER_MAP` em `dashboard/constants.py`."
        )

    # ── Gráficos trimestrais ───────────────────────────────────────────────────
    st.markdown('<div class="sec">Evolução Trimestral</div>', unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    with t1:
        fig = chart_bars(df, RECEITA, 'Receita Líquida (R$ mil)', COLORS['blue'])
        if fig: st.plotly_chart(fig, use_container_width=True, key='q_rec')
        else:   st.info("Sem dados trimestrais de receita.")
    with t2:
        fig = chart_bars(df, LUCRO, 'Lucro Líquido (R$ mil)', COLORS['purple'])
        if fig: st.plotly_chart(fig, use_container_width=True, key='q_luc')
        else:   st.info("Sem dados trimestrais de lucro.")
    t3, t4 = st.columns(2)
    with t3:
        fig = chart_bars(df, RES_BRUT, 'Resultado Bruto (R$ mil)', COLORS['green'])
        if fig: st.plotly_chart(fig, use_container_width=True, key='q_rb')
    with t4:
        fig = chart_dfc_grouped(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key='q_dfc')
        else:
            fig = chart_bars(df, FCO, 'FCO (R$ mil)', COLORS['amber'])
            if fig: st.plotly_chart(fig, use_container_width=True, key='q_fco')

    # ── KPIs anuais (linhas) ───────────────────────────────────────────────────
    st.markdown('<div class="sec">Indicadores Anuais</div>', unsafe_allow_html=True)
    kpi_series = {
        'Margem Bruta':   {y: kpis[y].get('mb')  for y in years},
        'ROE':            {y: kpis[y].get('roe') for y in years},
        'Margem Líquida': {y: kpis[y].get('ml')  for y in years},
        'ROA':            {y: kpis[y].get('roa') for y in years},
    }
    k1, k2 = st.columns(2)
    with k1:
        fig = chart_line(kpi_series['Margem Bruta'], 'Margem Bruta (%)')
        if fig: st.plotly_chart(fig, use_container_width=True, key='kl_mb')
    with k2:
        fig = chart_line(kpi_series['ROE'], 'ROE (%)')
        if fig: st.plotly_chart(fig, use_container_width=True, key='kl_roe')
    k3, k4 = st.columns(2)
    with k3:
        fig = chart_line(kpi_series['Margem Líquida'], 'Margem Líquida (%)')
        if fig: st.plotly_chart(fig, use_container_width=True, key='kl_ml')
    with k4:
        fig = chart_line(kpi_series['ROA'], 'ROA (%)')
        if fig: st.plotly_chart(fig, use_container_width=True, key='kl_roa')

    # ── Comparação overlay ─────────────────────────────────────────────────────
    if _cmp_cvm is not None and _cmp_kpis:
        st.markdown(
            f'<div class="sec">Comparação: {sel} vs {_cmp_sel}</div>',
            unsafe_allow_html=True)

        def _ks(kpis_dict, key):
            return {y: kpis_dict[y].get(key) for y in kpis_dict}

        cmp1, cmp2 = st.columns(2)
        with cmp1:
            fig = chart_line_compare(
                {sel: _ks(kpis, 'rec'), _cmp_sel: _ks(_cmp_kpis, 'rec')},
                'Receita Líquida', unit='R$ mi')
            if fig: st.plotly_chart(fig, use_container_width=True, key='cmp_rec')
        with cmp2:
            fig = chart_line_compare(
                {sel: _ks(kpis, 'luc'), _cmp_sel: _ks(_cmp_kpis, 'luc')},
                'Lucro Líquido', unit='R$ mi')
            if fig: st.plotly_chart(fig, use_container_width=True, key='cmp_luc')
        cmp3, cmp4 = st.columns(2)
        with cmp3:
            fig = chart_line_compare(
                {sel: _ks(kpis, 'ml'), _cmp_sel: _ks(_cmp_kpis, 'ml')},
                'Margem Líquida', unit='%')
            if fig: st.plotly_chart(fig, use_container_width=True, key='cmp_ml')
        with cmp4:
            fig = chart_line_compare(
                {sel: _ks(kpis, 'roe'), _cmp_sel: _ks(_cmp_kpis, 'roe')},
                'ROE', unit='%')
            if fig: st.plotly_chart(fig, use_container_width=True, key='cmp_roe')

    # ── Composição patrimonial ─────────────────────────────────────────────────
    st.markdown('<div class="sec">Composição Patrimonial</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1:
        ac = k.get('ac'); anc = k.get('anc')
        labs, vs = [], []
        if ac  and ac  > 0: labs.append('Ativo Circulante');     vs.append(ac)
        if anc and anc > 0: labs.append('Ativo Não Circulante'); vs.append(anc)
        fig = chart_donut(labs, vs, f'Composição do Ativo ({latest})')
        if fig: st.plotly_chart(fig, use_container_width=True, key='d_ativo')
    with p2:
        pc_ = k.get('pc'); pnc = k.get('pnc'); plv = k.get('pl')
        labs2, vs2 = [], []
        if pc_  and pc_  > 0: labs2.append('Passivo Circulante');     vs2.append(pc_)
        if pnc  and pnc  > 0: labs2.append('Passivo Não Circulante'); vs2.append(pnc)
        if plv  and plv  > 0: labs2.append('Patrimônio Líquido');     vs2.append(plv)
        fig = chart_donut(labs2, vs2, f'Passivo + PL ({latest})')
        if fig: st.plotly_chart(fig, use_container_width=True, key='d_passivo')

    # ── Waterfall YoY ─────────────────────────────────────────────────────────
    if len(years) >= 2:
        st.markdown('<div class="sec">Variação Anual do Resultado</div>',
                    unsafe_allow_html=True)
        wf1, wf2, _wf3 = st.columns([2, 2, 8])
        with wf1:
            year_curr_wf = st.selectbox(
                "Ano atual", options=list(reversed(years)), index=0, key="wf_curr")
        with wf2:
            prev_opts = [y for y in reversed(years) if y < year_curr_wf]
            year_prev_wf = st.selectbox(
                "Ano base", options=prev_opts or [None], index=0,
                key="wf_prev", disabled=not prev_opts)
        if prev_opts:
            fig = chart_yoy_waterfall(df, year_curr_wf, year_prev_wf)
            if fig: st.plotly_chart(fig, use_container_width=True, key='wf')
