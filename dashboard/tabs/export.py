# -*- coding: utf-8 -*-
"""
dashboard/tabs/export.py — Aba "Exportar" (download Excel).

4 abas geradas:
  Indicadores  — KPIs anuais agrupados por categoria (com cabeçalhos coloridos)
  KPI_Graficos — mesmos KPIs transpostos (anos nas colunas), prontos para gráfico
  Trimestral   — pivot por trimestre (STANDARD_NAME x período)
  Base_CVM     — dados brutos do banco
"""
from __future__ import annotations

import io
import math
import re

import pandas as pd
import streamlit as st

from dashboard.loaders import qsort

# ── Definição dos KPIs exportados ─────────────────────────────────────────────
# Tuplas: (grupo, chave_kpi, label_excel, formato)
# formato: 'num' = R$ mil  |  'pct' = %  |  'ratio' = ×  |  'days' = dias
_KPI_DEFS: list[tuple[str, str, str, str]] = [
    # LIQUIDEZ
    ('LIQUIDEZ',      'liq_corr',       'Liquidez Corrente',              'ratio'),
    ('LIQUIDEZ',      'liq_seca',       'Liquidez Seca',                  'ratio'),
    ('LIQUIDEZ',      'liq_imediata',   'Liquidez Imediata',              'ratio'),
    ('LIQUIDEZ',      'liq_geral',      'Liquidez Geral',                 'ratio'),
    ('LIQUIDEZ',      'cgl',            'Capital de Giro Líquido (R$ mil)', 'num'),
    # MARGENS
    ('MARGENS',       'mb',             'Margem Bruta',                   'pct'),
    ('MARGENS',       'mg_ebit',        'Margem EBIT',                    'pct'),
    ('MARGENS',       'mg_ebitda',      'Margem EBITDA',                  'pct'),
    ('MARGENS',       'ml',             'Margem Líquida',                 'pct'),
    ('MARGENS',       'mg_ant_ir',      'Margem antes de IR',             'pct'),
    # RETORNO
    ('RETORNO',       'roe',            'ROE',                            'pct'),
    ('RETORNO',       'roa',            'ROA',                            'pct'),
    ('RETORNO',       'giro_ativo',     'Giro do Ativo',                  'ratio'),
    ('RETORNO',       'mult_pl',        'Multiplicador de PL',            'ratio'),
    ('RETORNO',       'dupont_roe',     'DuPont ROE (3 fatores)',         'pct'),
    ('RETORNO',       'tax_burden',     'Tax Burden (Lucro/EBT)',         'ratio'),
    ('RETORNO',       'int_burden',     'Interest Burden (EBT/EBIT)',     'ratio'),
    # ENDIVIDAMENTO
    ('ENDIVIDAMENTO', 'endiv_geral',    'Endividamento Geral',            'pct'),
    ('ENDIVIDAMENTO', 'de_ratio',       'D/E — Dívida Total / PL',        'ratio'),
    ('ENDIVIDAMENTO', 'div_pl',         'Dívida Bruta / PL',              'ratio'),
    ('ENDIVIDAMENTO', 'div_liq_pl',     'Dívida Líquida / PL',            'ratio'),
    ('ENDIVIDAMENTO', 'comp_endiv',     'Composição Endiv. (% CP)',       'pct'),
    ('ENDIVIDAMENTO', 'imo_pl',         'Imobilização do PL',             'ratio'),
    ('ENDIVIDAMENTO', 'imo_rnc',        'Imobilização dos Rec. Não-Circ.','ratio'),
    ('ENDIVIDAMENTO', 'alav',           'Alavancagem — Dív.Líq / EBITDA', 'ratio'),
    ('ENDIVIDAMENTO', 'alav_ebit',      'Alavancagem — Dív.Líq / EBIT',   'ratio'),
    # COBERTURA
    ('COBERTURA',     'icr_ebit',       'ICR — EBIT / Desp. Financeiras', 'ratio'),
    ('COBERTURA',     'icr_liq',        'ICR Líquido — EBIT / (DF-RF)',   'ratio'),
    # ATIVIDADE
    ('ATIVIDADE',     'pmr',            'PMR — Prazo Médio de Recebimento','days'),
    ('ATIVIDADE',     'pme',            'PME — Prazo Médio de Estoques',  'days'),
    ('ATIVIDADE',     'pmp',            'PMP — Prazo Médio de Pagamento', 'days'),
    ('ATIVIDADE',     'ciclo_op',       'Ciclo Operacional (dias)',        'days'),
    ('ATIVIDADE',     'ciclo_fin',      'Ciclo Financeiro / CCC (dias)',   'days'),
    ('ATIVIDADE',     'giro_estoques',  'Giro de Estoques',               'ratio'),
    ('ATIVIDADE',     'giro_ativo_fixo','Giro do Ativo Fixo',             'ratio'),
    # FLUXO DE CAIXA
    ('FLUXO DE CAIXA','fco',            'FCO (R$ mil)',                   'num'),
    ('FLUXO DE CAIXA','fci',            'FCI (R$ mil)',                   'num'),
    ('FLUXO DE CAIXA','fcf_fin',        'FCF Financiamento (R$ mil)',     'num'),
    ('FLUXO DE CAIXA','fcl',            'FCL = FCO + FCI (R$ mil)',       'num'),
    ('FLUXO DE CAIXA','fco_lucro',      'FCO / Lucro Líquido',            'ratio'),
    ('FLUXO DE CAIXA','fco_div_liq',    'FCO / Dívida Líquida',           'ratio'),
    ('FLUXO DE CAIXA','ccr',            'CCR — FCO / EBITDA',             'ratio'),
    ('FLUXO DE CAIXA','capex_proxy',    'CAPEX Proxy = |FCI| (R$ mil)',   'num'),
    ('FLUXO DE CAIXA','capex_rec',      'CAPEX / Receita',                'pct'),
    ('FLUXO DE CAIXA','fco_capex',      'FCO / CAPEX (Autofinanciamento)','ratio'),
    # ABSOLUTOS
    ('ABSOLUTOS',     'rec',            'Receita (R$ mil)',               'num'),
    ('ABSOLUTOS',     'luc',            'Lucro Líquido (R$ mil)',         'num'),
    ('ABSOLUTOS',     'ebit',           'EBIT (R$ mil)',                  'num'),
    ('ABSOLUTOS',     'ebitda',         'EBITDA (R$ mil)',                'num'),
    ('ABSOLUTOS',     'da',             'D&A (R$ mil)',                   'num'),
    ('ABSOLUTOS',     'rb',             'Resultado Bruto (R$ mil)',       'num'),
    ('ABSOLUTOS',     'at',             'Ativo Total (R$ mil)',           'num'),
    ('ABSOLUTOS',     'pl',             'Patrimônio Líquido (R$ mil)',    'num'),
    ('ABSOLUTOS',     'div',            'Dívida Bruta (R$ mil)',          'num'),
    ('ABSOLUTOS',     'div_liq',        'Dívida Líquida (R$ mil)',        'num'),
    ('ABSOLUTOS',     'cx',             'Caixa e Equiv. (R$ mil)',        'num'),
    ('ABSOLUTOS',     'aplic',          'Aplicações Financeiras (R$ mil)','num'),
    ('ABSOLUTOS',     'est',            'Estoques (R$ mil)',              'num'),
    ('ABSOLUTOS',     'cli',            'Clientes / Rec. a Receber (R$ mil)', 'num'),
    ('ABSOLUTOS',     'forn',           'Fornecedores (R$ mil)',          'num'),
    # ANÁLISE HORIZONTAL
    ('HORIZONTAL',    'yoy_rec',        'YoY Receita',                    'pct'),
    ('HORIZONTAL',    'yoy_luc',        'YoY Lucro Líquido',              'pct'),
    ('HORIZONTAL',    'yoy_ebit',       'YoY EBIT',                       'pct'),
    ('HORIZONTAL',    'cagr_rec',       'CAGR Receita (3 anos)',          'pct'),
]


def _safe(v):
    """Converte None / NaN / inf para string vazia para escrita no Excel."""
    if v is None:
        return ''
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ''
    return v


def _write_indicadores_sheet(wb, name: str, years_sorted: list, kpis_by_year: dict):
    """Cria a aba 'Indicadores' com cabeçalhos de grupo e KPIs agrupados."""
    # ── Formatos ──────────────────────────────────────────────────────────────
    ttl = wb.add_format({'bold': True, 'font_size': 14})
    col_hdr = wb.add_format({
        'bold': True, 'bg_color': '#00BF7A', 'font_color': '#000',
        'border': 1, 'align': 'center', 'valign': 'vcenter',
    })
    grp_hdr = wb.add_format({
        'bold': True, 'bg_color': '#1A3C2A', 'font_color': '#00BF7A',
        'border': 1, 'font_size': 10,
    })
    lbl_cell = wb.add_format({'border': 1, 'indent': 1})
    num_f  = wb.add_format({'num_format': '#,##0',   'border': 1})
    pct_f  = wb.add_format({'num_format': '0.0%',    'border': 1})
    rat_f  = wb.add_format({'num_format': '0.00',    'border': 1})
    day_f  = wb.add_format({'num_format': '0.0',     'border': 1})
    emp_f  = wb.add_format({'bg_color': '#0D1F16',   'border': 1})

    fmt_map = {'num': num_f, 'pct': pct_f, 'ratio': rat_f, 'days': day_f}

    ws = wb.add_worksheet('Indicadores')
    n_years = len(years_sorted)

    # Título
    ws.write(0, 0, f'Indicadores Financeiros — {name}', ttl)

    # Linha de cabeçalho das colunas
    ws.write(1, 0, 'Indicador', col_hdr)
    for ci, y in enumerate(years_sorted):
        ws.write(1, ci + 1, str(y), col_hdr)

    # Linhas de dados
    row = 2
    prev_group = None
    for group, key, label, fmt in _KPI_DEFS:
        if group != prev_group:
            # Cabeçalho de grupo
            ws.write(row, 0, f'  {group}', grp_hdr)
            for ci in range(n_years):
                ws.write(row, ci + 1, '', grp_hdr)
            row += 1
            prev_group = group

        ws.write(row, 0, label, lbl_cell)
        val_fmt = fmt_map.get(fmt, lbl_cell)
        for ci, y in enumerate(years_sorted):
            v = _safe(kpis_by_year.get(y, {}).get(key))
            if v == '':
                ws.write(row, ci + 1, '', emp_f)
            else:
                ws.write(row, ci + 1, v, val_fmt)
        row += 1

    # Larguras de coluna
    ws.set_column(0, 0, 42)
    for ci in range(n_years):
        ws.set_column(ci + 1, ci + 1, 14)

    return ws


def _write_kpi_graficos_sheet(wb, name: str, years_sorted: list, kpis_by_year: dict):
    """Cria a aba 'KPI_Graficos': KPIs × anos, transposto para graficos no Excel."""
    ttl = wb.add_format({'bold': True, 'font_size': 14})
    col_hdr = wb.add_format({
        'bold': True, 'bg_color': '#00BF7A', 'font_color': '#000',
        'border': 1, 'align': 'center',
    })
    grp_cell = wb.add_format({'bold': True, 'font_color': '#00BF7A', 'border': 1, 'indent': 0})
    lbl_cell = wb.add_format({'border': 1, 'indent': 1})
    num_f  = wb.add_format({'num_format': '#,##0',   'border': 1})
    pct_f  = wb.add_format({'num_format': '0.0%',    'border': 1})
    rat_f  = wb.add_format({'num_format': '0.00',    'border': 1})
    day_f  = wb.add_format({'num_format': '0.0',     'border': 1})
    emp_f  = wb.add_format({'bg_color': '#0D1F16',   'border': 1})

    fmt_map = {'num': num_f, 'pct': pct_f, 'ratio': rat_f, 'days': day_f}

    ws = wb.add_worksheet('KPI_Graficos')
    n_years = len(years_sorted)

    # Título
    ws.write(0, 0, f'KPI × Ano — {name}  (pronto para gráfico)', ttl)

    # Cabeçalho: Grupo | Indicador | Ano1 | Ano2 | ...
    ws.write(1, 0, 'Grupo',      col_hdr)
    ws.write(1, 1, 'Indicador',  col_hdr)
    for ci, y in enumerate(years_sorted):
        ws.write(1, ci + 2, str(y), col_hdr)

    # Linhas — uma por KPI, sem cabeçalhos de grupo intercalados
    row = 2
    for group, key, label, fmt in _KPI_DEFS:
        ws.write(row, 0, group, grp_cell)
        ws.write(row, 1, label, lbl_cell)
        val_fmt = fmt_map.get(fmt, lbl_cell)
        for ci, y in enumerate(years_sorted):
            v = _safe(kpis_by_year.get(y, {}).get(key))
            if v == '':
                ws.write(row, ci + 2, '', emp_f)
            else:
                ws.write(row, ci + 2, v, val_fmt)
        row += 1

    # Larguras
    ws.set_column(0, 0, 16)
    ws.set_column(1, 1, 42)
    for ci in range(n_years):
        ws.set_column(ci + 2, ci + 2, 14)

    return ws


def build_excel(name: str, df: pd.DataFrame, years: tuple, kpis_by_year: dict):
    """Gera workbook Excel com 4 abas: Indicadores, KPI_Graficos, Trimestral, Base_CVM."""
    buf = io.BytesIO()
    years_sorted = sorted(years)

    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        wb = w.book

        # ── Aba 1: Indicadores ────────────────────────────────────────────────
        ws1 = _write_indicadores_sheet(wb, name, years_sorted, kpis_by_year)
        w.sheets['Indicadores'] = ws1

        # ── Aba 2: KPI_Graficos ───────────────────────────────────────────────
        ws2 = _write_kpi_graficos_sheet(wb, name, years_sorted, kpis_by_year)
        w.sheets['KPI_Graficos'] = ws2

        # ── Aba 3: Trimestral ─────────────────────────────────────────────────
        qtrs = df[
            df['PERIOD_LABEL'].str.match(r'^\dQ\d{2}$', na=False)
            & df['STANDARD_NAME'].notna()
        ]
        if not qtrs.empty:
            pv = qtrs.pivot_table(
                index=['STATEMENT_TYPE', 'STANDARD_NAME'],
                columns='PERIOD_LABEL', values='VL_CONTA', aggfunc='sum',
            ).fillna(0)
            pv = pv[sorted(pv.columns, key=qsort)]
            pv.to_excel(w, sheet_name='Trimestral')
            w.sheets['Trimestral'].set_column('A:B', 22)
            w.sheets['Trimestral'].set_column('C:Z', 14)

        # ── Aba 4: Base_CVM ───────────────────────────────────────────────────
        cols_out = [c for c in [
            'REPORT_YEAR', 'STATEMENT_TYPE', 'PERIOD_LABEL',
            'CD_CONTA', 'DS_CONTA', 'STANDARD_NAME', 'VL_CONTA',
        ] if c in df.columns]
        df[cols_out].to_excel(w, sheet_name='Base_CVM', index=False)
        ws4 = w.sheets['Base_CVM']
        ws4.set_column('A:A', 10)
        ws4.set_column('B:C', 14)
        ws4.set_column('D:F', 40)
        ws4.set_column('G:G', 16)

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
            st.caption(f'`{xname}` · 4 abas · {len(_KPI_DEFS)} indicadores')
        except Exception as e:
            st.error(f"Erro ao gerar Excel: {e}")
