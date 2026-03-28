# -*- coding: utf-8 -*-
"""
dashboard/tabs/visao.py — Aba "Visão Geral" com layout premium (2 colunas).
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
from dashboard.components.ui import (
    hero_card, kpi_row, quick_actions, section_title,
    stat_breakdown, activity_feed, progress_card,
)


def _fmt_mktcap(v) -> str:
    if v is None:
        return ''
    if v >= 1e12:
        return f'Mkt R$ {v/1e12:.1f} tri'
    if v >= 1e9:
        return f'Mkt R$ {v/1e9:.1f} bi'
    return f'Mkt R$ {v/1e6:.0f} mi'


def render_visao_geral(sel: str, cvm: int, df, years: tuple, latest: int,
                       kpis: dict, companies) -> None:
    """Renderiza a aba Visão Geral com layout premium de 2 colunas."""

    k      = kpis.get(latest, {})
    k_prev = kpis.get(years[-2], {}) if len(years) >= 2 else {}

    def yoy(curr, prev):
        g = safe_div(curr, prev)
        return f'{(g-1)*100:+.1f}% YoY' if g is not None else None

    def yoy_pp(curr, prev):
        if curr is not None and prev is not None:
            return f'{(curr-prev)*100:+.1f} pp'
        return None

    # ── Dados de mercado ───────────────────────────────────────────────────────
    _ticker = TICKER_MAP.get(int(cvm))
    _mkt    = load_market_data(_ticker) if _ticker else {}

    # ══════════════════════════════════════════════════════════════════════════
    # LINHA 1: Hero card (esq) + KPI mini-cards (dir)
    # ══════════════════════════════════════════════════════════════════════════
    col_hero, col_kpis = st.columns([1.05, 1])

    with col_hero:
        price_val  = _mkt.get('price')
        mktcap_str = _fmt_mktcap(_mkt.get('mktcap')) if _mkt else None
        year_range = f'{min(years)}–{max(years)}'
        st.markdown(
            hero_card(sel, _ticker, 'Dados Consolidados', cvm, year_range,
                      price=price_val, mktcap_str=mktcap_str),
            unsafe_allow_html=True,
        )
        st.markdown(
            quick_actions([
                {'icon': '📋', 'label': 'Demonstrações'},
                {'icon': '🏢', 'label': 'Comparar Peers'},
                {'icon': '🔍', 'label': 'Screener'},
                {'icon': '⬇', 'label': 'Exportar Excel'},
            ]),
            unsafe_allow_html=True,
        )

    with col_kpis:
        rec_val  = k.get('rec')
        luc_val  = k.get('luc')
        at_val   = k.get('at')
        roe_val  = k.get('roe')
        alav_val = k.get('alav')
        liq_val  = k.get('liq_corr')

        rec_yoy  = yoy(rec_val,  k_prev.get('rec'))
        luc_yoy  = yoy(luc_val,  k_prev.get('luc'))
        roe_yoyp = yoy_pp(roe_val, k_prev.get('roe'))

        row1 = [
            {'label': 'Receita Líq.', 'value': brl(rec_val),
             'delta': rec_yoy,
             'delta_up': None if rec_yoy is None else (rec_val or 0) > (k_prev.get('rec') or 0),
             'icon': '💰'},
            {'label': 'Lucro Líq.', 'value': brl(luc_val),
             'delta': luc_yoy,
             'delta_up': None if luc_yoy is None else (luc_val or 0) > (k_prev.get('luc') or 0),
             'icon': '📈'},
            {'label': 'Ativo Total', 'value': brl(at_val),
             'delta': None, 'delta_up': None, 'icon': '🏦'},
        ]
        row2 = [
            {'label': 'ROE', 'value': pct(roe_val),
             'delta': roe_yoyp,
             'delta_up': None if roe_yoyp is None else (roe_val or 0) > (k_prev.get('roe') or 0),
             'icon': '⚡'},
            {'label': 'Dívida/EBITDA',
             'value': f"{alav_val:.2f}x" if alav_val else '—',
             'delta': None, 'delta_up': None, 'icon': '🔗'},
            {'label': 'Liq. Corrente',
             'value': f"{liq_val:.2f}x" if liq_val else '—',
             'delta': None, 'delta_up': None, 'icon': '💧'},
        ]
        st.markdown(kpi_row(row1), unsafe_allow_html=True)
        st.markdown(kpi_row(row2), unsafe_allow_html=True)

        # Sparklines
        sp1, sp2, sp3 = st.columns(3)
        sp4, sp5, sp6 = st.columns(3)
        spark_data = [
            (sp1, {y: kpis[y].get('rec')      for y in years}, COLORS['blue'],   'sp_rec'),
            (sp2, {y: kpis[y].get('luc')      for y in years}, COLORS['purple'], 'sp_luc'),
            (sp3, {y: kpis[y].get('at')       for y in years}, COLORS['amber'],  'sp_at'),
            (sp4, {y: kpis[y].get('roe')      for y in years}, COLORS['green'],  'sp_roe'),
            (sp5, {y: kpis[y].get('alav')     for y in years}, COLORS['red'],    'sp_alav'),
            (sp6, {y: kpis[y].get('liq_corr') for y in years}, COLORS['green'],  'sp_liq'),
        ]
        for col_sp, data, color, key in spark_data:
            with col_sp:
                st.plotly_chart(sparkline(data, color), use_container_width=True,
                                config={'staticPlot': True}, key=key)

    # ══════════════════════════════════════════════════════════════════════════
    # LINHA 2: Conteúdo principal (esq 65%) + Painel direito (35%)
    # ══════════════════════════════════════════════════════════════════════════
    col_main, col_right = st.columns([2, 1])

    with col_main:
        # ── Valuation de Mercado ──────────────────────────────────────────────
        if _mkt:
            st.markdown(section_title('Valuation de Mercado', _ticker or ''),
                        unsafe_allow_html=True)

            def _fv(v, suffix=''):
                return f'{v:.2f}{suffix}' if v is not None else '—'

            mkt_cards = [
                {'label': 'Preço',     'value': f"R$ {_mkt['price']:.2f}",
                 'delta': None, 'delta_up': None, 'icon': '💹'},
                {'label': 'Market Cap',
                 'value': _fmt_mktcap(_mkt.get('mktcap')).replace('Mkt ', ''),
                 'delta': None, 'delta_up': None, 'icon': '🏢'},
                {'label': 'P/L',       'value': _fv(_mkt.get('pe'),  'x'),
                 'delta': None, 'delta_up': None, 'icon': '📊'},
                {'label': 'P/VP',      'value': _fv(_mkt.get('pb'),  'x'),
                 'delta': None, 'delta_up': None, 'icon': '📋'},
                {'label': 'EV/EBITDA', 'value': _fv(_mkt.get('ev_ebitda'), 'x'),
                 'delta': None, 'delta_up': None, 'icon': '⚖️'},
                {'label': 'Div. Yield',
                 'value': f"{(_mkt.get('dy') or 0)*100:.1f}%",
                 'delta': None, 'delta_up': None, 'icon': '💵'},
            ]
            st.markdown(kpi_row(mkt_cards), unsafe_allow_html=True)

        # ── Histórico de preço ────────────────────────────────────────────────
        if _ticker:
            _price_hist = load_price_history(_ticker)
            if not _price_hist.empty:
                st.markdown(section_title('Histórico de Preço', '12 meses'),
                            unsafe_allow_html=True)
                st.plotly_chart(
                    chart_price_history(_price_hist, _ticker),
                    use_container_width=True,
                    config={'displayModeBar': False},
                    key='price_history',
                )

        # ── Seletor de comparação ─────────────────────────────────────────────
        st.markdown(section_title('Evolução Financeira'), unsafe_allow_html=True)
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
            _cmp_df = None
            _cmp_years = ()
            _cmp_kpis  = {}

        ch1, ch2 = st.columns(2)
        with ch1:
            if _cmp_cvm and _cmp_kpis:
                series = {
                    sel:      {y: kpis[y].get('rec')      for y in years      if kpis.get(y)},
                    _cmp_sel: {y: _cmp_kpis[y].get('rec') for y in _cmp_years if _cmp_kpis.get(y)},
                }
                st.plotly_chart(
                    chart_line_compare(series, 'Receita', unit='R$ mi'),
                    use_container_width=True, config={'displayModeBar': False}, key='cmp_rec',
                )
            else:
                st.plotly_chart(
                    chart_bars(df, RECEITA, 'Receita Líquida', COLORS['blue']),
                    use_container_width=True, config={'displayModeBar': False}, key='bar_rec',
                )
        with ch2:
            if _cmp_cvm and _cmp_kpis:
                series = {
                    sel:      {y: kpis[y].get('luc')      for y in years      if kpis.get(y)},
                    _cmp_sel: {y: _cmp_kpis[y].get('luc') for y in _cmp_years if _cmp_kpis.get(y)},
                }
                st.plotly_chart(
                    chart_line_compare(series, 'Lucro Líquido', unit='R$ mi'),
                    use_container_width=True, config={'displayModeBar': False}, key='cmp_luc',
                )
            else:
                st.plotly_chart(
                    chart_bars(df, LUCRO, 'Lucro Líquido', COLORS['purple']),
                    use_container_width=True, config={'displayModeBar': False}, key='bar_luc',
                )

        # ── Margens e Rentabilidade ───────────────────────────────────────────
        st.markdown(section_title('Margens e Rentabilidade'), unsafe_allow_html=True)
        mg1, mg2 = st.columns(2)
        with mg1:
            if _cmp_cvm and _cmp_kpis:
                series = {
                    sel:      {y: kpis[y].get('ml')      for y in years      if kpis.get(y)},
                    _cmp_sel: {y: _cmp_kpis[y].get('ml') for y in _cmp_years if _cmp_kpis.get(y)},
                }
                st.plotly_chart(
                    chart_line_compare(series, 'Margem Líquida', unit='%'),
                    use_container_width=True, config={'displayModeBar': False}, key='cmp_ml',
                )
            else:
                ml_data = {y: kpis[y].get('ml') for y in years if kpis.get(y)}
                mb_data = {y: kpis[y].get('mb') for y in years if kpis.get(y)}
                series  = {'Margem Líq.': ml_data, 'Margem Bruta': mb_data}
                st.plotly_chart(
                    chart_line_compare(series, 'Margens', unit='%'),
                    use_container_width=True, config={'displayModeBar': False}, key='line_mg',
                )
        with mg2:
            if _cmp_cvm and _cmp_kpis:
                series = {
                    sel:      {y: kpis[y].get('roe')      for y in years      if kpis.get(y)},
                    _cmp_sel: {y: _cmp_kpis[y].get('roe') for y in _cmp_years if _cmp_kpis.get(y)},
                }
                st.plotly_chart(
                    chart_line_compare(series, 'ROE', unit='%'),
                    use_container_width=True, config={'displayModeBar': False}, key='cmp_roe',
                )
            else:
                roe_data = {y: kpis[y].get('roe') for y in years if kpis.get(y)}
                roa_data = {y: kpis[y].get('roa') for y in years if kpis.get(y)}
                series   = {'ROE': roe_data, 'ROA': roa_data}
                st.plotly_chart(
                    chart_line_compare(series, 'Rentabilidade', unit='%'),
                    use_container_width=True, config={'displayModeBar': False}, key='line_roa',
                )

        # ── Fluxo de Caixa + Waterfall ────────────────────────────────────────
        st.markdown(section_title('Fluxo de Caixa e Variação Anual'),
                    unsafe_allow_html=True)
        fc1, fc2 = st.columns(2)
        with fc1:
            fig_dfc = chart_dfc_grouped(df)
            if fig_dfc:
                st.plotly_chart(fig_dfc, use_container_width=True,
                                config={'displayModeBar': False}, key='dfc')
        with fc2:
            if len(years) >= 2:
                fig_wf = chart_yoy_waterfall(df, latest, years[-2])
                if fig_wf:
                    st.plotly_chart(fig_wf, use_container_width=True,
                                    config={'displayModeBar': False}, key='wf')

        # ── Composição patrimonial ────────────────────────────────────────────
        st.markdown(section_title('Composição Patrimonial', str(latest)),
                    unsafe_allow_html=True)
        don1, don2 = st.columns(2)
        with don1:
            ac_v  = k.get('ac')  or 0
            anc_v = k.get('anc') or 0
            if ac_v + anc_v > 0:
                fig_d = chart_donut(
                    ['Ativo Circ.', 'Ativo N. Circ.'],
                    [ac_v, anc_v],
                    'Ativo Total',
                )
                if fig_d:
                    st.plotly_chart(fig_d, use_container_width=True,
                                    config={'displayModeBar': False}, key='don_at')
        with don2:
            pc_v  = k.get('pc')  or 0
            pnc_v = k.get('pnc') or 0
            pl_v  = k.get('pl')  or 0
            if pc_v + pnc_v + pl_v > 0:
                fig_d = chart_donut(
                    ['Passivo Circ.', 'Passivo N. Circ.', 'PL'],
                    [pc_v, pnc_v, pl_v],
                    'Passivo + PL',
                )
                if fig_d:
                    st.plotly_chart(fig_d, use_container_width=True,
                                    config={'displayModeBar': False}, key='don_pas')

    with col_right:
        # ── Painel de indicadores ─────────────────────────────────────────────
        ml_v  = k.get('ml',  0) or 0
        mb_v  = k.get('mb',  0) or 0
        roe_v = k.get('roe', 0) or 0
        roa_v = k.get('roa', 0) or 0

        vals_abs = [abs(ml_v), abs(mb_v), abs(roe_v), abs(roa_v)]
        _max = max(vals_abs) if any(v > 0 for v in vals_abs) else 1

        def _bar(v):
            return min(80, abs(v) / _max * 80) if _max > 0 else 0

        stat_items = [
            {'label': 'Margem Líquida', 'value': pct(ml_v),  'pct': _bar(ml_v),
             'color': 'var(--accent)'},
            {'label': 'Margem Bruta',   'value': pct(mb_v),  'pct': _bar(mb_v),
             'color': 'var(--blue)'},
            {'label': 'ROE',            'value': pct(roe_v), 'pct': _bar(roe_v),
             'color': 'var(--purple)'},
            {'label': 'ROA',            'value': pct(roa_v), 'pct': _bar(roa_v),
             'color': 'var(--cyan)'},
        ]
        st.markdown(
            stat_breakdown('Indicadores', 'Receita Total', brl(k.get('rec')),
                           stat_items, period=str(latest)),
            unsafe_allow_html=True,
        )

        # ── Giro do Ativo (progress card) ─────────────────────────────────────
        if k.get('at') and k.get('rec'):
            st.markdown(
                progress_card(
                    title='Giro do Ativo',
                    used=k['rec'], total=k['at'],
                    used_label=brl(k['rec']),
                    total_label=brl(k['at']),
                    pct_label=f"{k['rec']/k['at']:.2f}x",
                ),
                unsafe_allow_html=True,
            )

        # ── Alavancagem (progress card) ───────────────────────────────────────
        if k.get('alav') is not None:
            alav_v = k['alav']
            alav_max = 6.0
            st.markdown(
                progress_card(
                    title='Dívida Líq. / EBITDA',
                    used=max(0, alav_v), total=alav_max,
                    used_label=f"{alav_v:.2f}x",
                    total_label=f'{alav_max:.0f}x ref.',
                    pct_label=f"{alav_v:.2f}x",
                ),
                unsafe_allow_html=True,
            )

        # ── Activity feed — histórico financeiro por ano ───────────────────────
        act_groups = []
        for y in sorted(years, reverse=True)[:4]:
            ky = kpis.get(y, {})
            items = []
            rec_y = ky.get('rec')
            luc_y = ky.get('luc')
            ml_y  = ky.get('ml')
            roe_y = ky.get('roe')
            if rec_y is not None:
                items.append({
                    'text': f'Receita: {brl(rec_y)}',
                    'time': f'DFP {y}',
                    'color': 'var(--accent)',
                })
            if luc_y is not None:
                color = 'var(--blue)' if (luc_y or 0) >= 0 else 'var(--red)'
                items.append({
                    'text': f'Lucro: {brl(luc_y)}',
                    'time': f'ML {pct(ml_y)}' if ml_y else f'Resultado {y}',
                    'color': color,
                })
            if roe_y is not None:
                items.append({
                    'text': f'ROE: {pct(roe_y)}',
                    'time': 'Rentabilidade',
                    'color': 'var(--purple)',
                })
            if items:
                act_groups.append({'period': str(y), 'items': items})

        if act_groups:
            st.markdown(
                activity_feed('Histórico Financeiro', act_groups),
                unsafe_allow_html=True,
            )

        # ── Sem ticker ────────────────────────────────────────────────────────
        if not _ticker:
            st.markdown(
                '<div class="stat-card" style="text-align:center;padding:24px 16px;">'
                '<div style="font-size:1.4rem;margin-bottom:8px;">📡</div>'
                '<div style="font-size:0.73rem;font-weight:600;color:var(--text-muted);">'
                'Sem ticker mapeado</div>'
                '<div style="font-size:0.67rem;color:var(--text-muted);margin-top:4px;">'
                'Dados de mercado indisponíveis</div>'
                '</div>',
                unsafe_allow_html=True,
            )
