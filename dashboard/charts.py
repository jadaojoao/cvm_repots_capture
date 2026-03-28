# -*- coding: utf-8 -*-
"""
dashboard/charts.py — Funções de visualização Plotly + formatadores de display.
"""
from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go

from dashboard.constants import (
    RECEITA, LUCRO, RES_BRUT, DESP_OP,
    FCO, FCI, FCF_ACTIV,
)

# ── Formatadores de display ────────────────────────────────────────────────────

def brl(v) -> str:
    """Formata valor em R$ (R$ mil no DB) para exibição humana."""
    if v is None:
        return "—"
    a = abs(v)
    s = "-" if v < 0 else ""
    if a >= 1e6:
        return f"{s}R$ {a/1e6:,.1f} bi"
    if a >= 1e3:
        return f"{s}R$ {a/1e3:,.1f} mi"
    return f"{s}R$ {a:,.0f} mil"


def pct(v) -> str:
    """Formata proporção como porcentagem."""
    if v is None:
        return "—"
    return f"{v*100:.1f}%"


# ── Tema Plotly ────────────────────────────────────────────────────────────────

LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=42, b=10),
    font=dict(family='Inter', size=11, color='#8890a8'),
    title_font=dict(family='Inter', size=13, color='#e8eaf0'),
    yaxis=dict(
        showgrid=True, gridcolor='#1e2030',
        zeroline=True, zerolinecolor='#1e2030',
        color='#4a5068',
    ),
    xaxis=dict(
        showgrid=False,
        color='#4a5068',
    ),
    legend=dict(
        bgcolor='rgba(0,0,0,0)',
        bordercolor='#1e2030',
        font=dict(color='#8890a8'),
    ),
)

COLORS = {
    'green':      '#00BF7A',
    'blue':       '#3B82F6',
    'purple':     '#8B5CF6',
    'amber':      '#F59E0B',
    'red':        '#EF4444',
    'cyan':       '#06b6d4',
    'slate':      '#475569',
    'muted':      '#3D3D42',
    'blue_iota':  '#2563F5',
}


def lo(*exclude):
    """Retorna LAYOUT sem as chaves indicadas (evita TypeError de argumento duplicado)."""
    skip = {'xaxis', 'yaxis', 'legend'} | set(exclude)
    return {k: v for k, v in LAYOUT.items() if k not in skip}


# ── Helpers internos ───────────────────────────────────────────────────────────

def _qsort(label: str) -> tuple:
    """Chave de ordenação para period labels ('1Q24' < '2Q24' < '2024')."""
    m = re.match(r'(\d)Q(\d{2})', str(label))
    return (int('20' + m.group(2)), int(m.group(1))) if m else (9999, 0)


def _val(df: pd.DataFrame, names, year: int, period=None):
    """Extrai valor anual ou trimestral do DataFrame longo."""
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


# ── Chart builders ─────────────────────────────────────────────────────────────

def chart_bars(df: pd.DataFrame, names, title: str,
               color: str = COLORS['blue'], h: int = 340):
    if isinstance(names, str):
        names = [names]
    sub = df[df['STANDARD_NAME'].isin(names)
             & df['PERIOD_LABEL'].str.match(r'^\dQ\d{2}$', na=False)].copy()
    if sub.empty:
        return None
    agg = sub.groupby('PERIOD_LABEL')['VL_CONTA'].sum().reset_index()
    agg = agg.iloc[agg['PERIOD_LABEL'].apply(_qsort).argsort()]
    fig = go.Figure(go.Bar(
        x=agg['PERIOD_LABEL'], y=agg['VL_CONTA'],
        marker_color=color,
        marker_line_width=0,
        text=agg['VL_CONTA'],
        texttemplate='%{y:,.0f}',
        textposition='outside',
        textfont=dict(size=8, color='#525257'),
    ))
    fig.update_layout(title=title, **LAYOUT, height=h)
    fig.update_xaxes(type='category', title_text='', tickfont=dict(size=9))
    fig.update_yaxes(title_text='R$ mil')
    return fig


def chart_line(data: dict, title: str, h: int = 300):
    if not data or all(v is None for v in data.values()):
        return None
    years = sorted(data.keys())
    vals  = [data[y] * 100 if data[y] is not None else None for y in years]
    valid = [(str(y), v) for y, v in zip(years, vals) if v is not None]
    if not valid:
        return None
    xs, ys = zip(*valid)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(xs), y=list(ys),
        mode='lines+markers+text',
        text=[f'{v:.1f}%' for v in ys],
        textposition='top center',
        textfont=dict(size=11, color='#E8E8E8'),
        marker=dict(size=9, color=COLORS['green'],
                    line=dict(width=2, color='#0F0F10')),
        line=dict(color=COLORS['green'], width=2.5),
        fill='tozeroy',
        fillcolor='rgba(0,191,122,0.07)',
    ))
    fig.update_layout(title=title, **LAYOUT, height=h)
    fig.update_xaxes(title_text='')
    fig.update_yaxes(title_text='%')
    return fig


def chart_line_compare(series: dict, title: str, unit: str = '%', h: int = 300):
    """Overlay de 2+ empresas num mesmo gráfico de linha.
    series = {'EMPRESA A': {2022: val, ...}, 'EMPRESA B': {...}}
    unit='%'    → multiplica por 100, sufixo %
    unit='R$ mi'→ divide por 1000 (DB armazena R$ mil)
    """
    if not series:
        return None
    all_years = sorted({y for vals in series.values() for y in vals})
    if not all_years:
        return None
    palette = [COLORS['green'], COLORS['amber'], COLORS['blue']]
    fig = go.Figure()
    for idx, (company, data) in enumerate(series.items()):
        color = palette[min(idx, len(palette) - 1)]
        r_c = int(color[1:3], 16)
        g_c = int(color[3:5], 16)
        b_c = int(color[5:7], 16)
        xs, ys_raw = [], []
        for y in all_years:
            v = data.get(y)
            xs.append(str(y))
            if v is None:
                ys_raw.append(None)
            elif unit == '%':
                ys_raw.append(v * 100)
            else:
                ys_raw.append(v / 1e3)   # R$ mil → R$ mi
        text_labels = [
            (f'{v:.1f}%' if unit == '%' else f'{v:,.0f}') if v is not None else ''
            for v in ys_raw
        ]
        kw = dict(
            name=company, x=xs, y=ys_raw,
            mode='lines+markers+text', text=text_labels,
            textposition='top center', textfont=dict(size=10, color='#E8E8E8'),
            marker=dict(size=8, color=color, line=dict(width=2, color='#0F0F10')),
            line=dict(color=color, width=2.5), connectgaps=False,
        )
        if idx == 0:
            kw['fill'] = 'tozeroy'
            kw['fillcolor'] = f'rgba({r_c},{g_c},{b_c},0.07)'
        fig.add_trace(go.Scatter(**kw))
    fig.update_layout(
        title=title, **lo(), height=h, showlegend=True,
        legend=dict(orientation='h', y=1.12, x=0,
                    font=dict(size=10, color='#8A8A90'),
                    bgcolor='rgba(0,0,0,0)', bordercolor='#2A2A2D'),
        xaxis=dict(showgrid=False, color='#525257'),
        yaxis=dict(showgrid=True, gridcolor='#2A2A2D', zeroline=True,
                   zerolinecolor='#2A2A2D', color='#525257',
                   title_text='%' if unit == '%' else 'R$ mi'),
    )
    return fig


def chart_donut(labels, values, title: str, h: int = 300):
    if not values:
        return None
    palette = [COLORS['green'], COLORS['blue'], COLORS['purple'],
               COLORS['amber'], COLORS['red'], '#0891b2']
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=palette[:len(labels)],
                    line=dict(color='#0F0F10', width=2)),
        textinfo='percent',
        textfont=dict(size=12, color='#E8E8E8'),
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.0f} mil<br>%{percent}<extra></extra>',
    ))
    fig.update_layout(
        title=title, **lo(), height=h, showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.18,
                    xanchor='center', x=0.5, font=dict(size=10, color='#8A8A90'),
                    bgcolor='rgba(0,0,0,0)'),
    )
    return fig


def sparkline(data: dict, color: str = COLORS['green'], height: int = 56):
    ys = [data.get(y) for y in sorted(data.keys())]
    ys_clean = [v if v is not None else float('nan') for v in ys]
    r_c = int(color[1:3], 16)
    g_c = int(color[3:5], 16)
    b_c = int(color[5:7], 16)
    fig = go.Figure(go.Scatter(
        y=ys_clean, mode='lines',
        line=dict(color=color, width=1.5),
        fill='tozeroy',
        fillcolor=f'rgba({r_c},{g_c},{b_c},0.1)',
        hoverinfo='skip',
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
    )
    return fig


def chart_dfc_grouped(df: pd.DataFrame, h: int = 400):
    pattern = r'^\dQ\d{2}$'
    series  = [('FCO', FCO, COLORS['green']),
               ('FCI', FCI, COLORS['blue']),
               ('FCF', FCF_ACTIV, COLORS['amber'])]
    labels_union, traces_data, agg_map = set(), [], {}
    for name, acct_names, color in series:
        sub = df[df['STANDARD_NAME'].isin(acct_names)
                 & df['PERIOD_LABEL'].str.match(pattern, na=False)].copy()
        if sub.empty:
            continue
        agg = sub.groupby('PERIOD_LABEL')['VL_CONTA'].sum()
        labels_union.update(agg.index)
        traces_data.append((name, agg, color))
        agg_map[name] = agg
    if not traces_data:
        return None
    sorted_labels = sorted(labels_union, key=_qsort)
    fig = go.Figure()
    for name, agg, color in traces_data:
        fig.add_trace(go.Bar(
            name=name, x=sorted_labels,
            y=[agg.get(lbl, 0) for lbl in sorted_labels],
            marker_color=color, marker_line_width=0,
            text=[f'{agg.get(lbl, 0):,.0f}' for lbl in sorted_labels],
            textposition='outside', textfont=dict(size=7, color='#525257'),
        ))
    if 'FCO' in agg_map and 'FCI' in agg_map:
        fcl_vals = [agg_map['FCO'].get(lbl, 0) + agg_map['FCI'].get(lbl, 0)
                    for lbl in sorted_labels]
        fig.add_trace(go.Scatter(
            name='FCL (FCO+FCI)', x=sorted_labels, y=fcl_vals,
            mode='lines+markers',
            line=dict(color=COLORS['purple'], width=2, dash='dot'),
            marker=dict(size=6, color=COLORS['purple'], symbol='diamond'),
        ))
    fig.update_layout(
        **lo(), barmode='group', height=h,
        title='Fluxo de Caixa por Atividade (R$ mil)',
        legend=dict(orientation='h', y=1.08, x=0, font=dict(size=10, color='#8A8A90'),
                    bgcolor='rgba(0,0,0,0)', bordercolor='#2A2A2D'),
        xaxis=dict(showgrid=False, color='#525257', type='category', tickfont=dict(size=9)),
        yaxis=dict(showgrid=True, gridcolor='#2A2A2D', color='#525257', title_text='R$ mil'),
    )
    return fig


def chart_yoy_waterfall(df: pd.DataFrame, year_curr: int, year_prev: int, h: int = 380):
    def _d(names, y):
        v = _val(df, names, y)
        return v if v is not None else 0.0

    rec_c = _d(RECEITA,  year_curr); rec_p = _d(RECEITA,  year_prev)
    rb_c  = _d(RES_BRUT, year_curr); rb_p  = _d(RES_BRUT, year_prev)
    luc_c = _d(LUCRO,    year_curr); luc_p = _d(LUCRO,    year_prev)
    dop_c = _d(DESP_OP,  year_curr); dop_p = _d(DESP_OP,  year_prev)

    d_rec    = rec_c - rec_p
    d_custo  = (rb_c - rb_p) - (rec_c - rec_p)
    d_dop    = dop_c - dop_p
    d_outros = (luc_c - luc_p) - (d_rec + d_custo + d_dop)

    x_labels = [f'Lucro {year_prev}', 'Δ Receita', 'Δ Custo/Margem',
                'Δ Desp. Operac.', 'Δ Outros', f'Lucro {year_curr}']
    y_values = [luc_p, d_rec, d_custo, d_dop, d_outros, luc_c]
    measures = ['absolute', 'relative', 'relative', 'relative', 'relative', 'total']

    def _fmt(v):
        a = abs(v); sign = '-' if v < 0 else '+'
        if a >= 1e6: return f'{sign}R${a/1e6:,.1f}bi'
        if a >= 1e3: return f'{sign}R${a/1e3:,.1f}mi'
        return f'{sign}R${a:,.0f}k'

    fig = go.Figure(go.Waterfall(
        measure=measures, x=x_labels, y=y_values,
        connector=dict(line=dict(color='#2A2A2D', width=1, dash='dot')),
        decreasing=dict(marker=dict(color=COLORS['red'])),
        increasing=dict(marker=dict(color=COLORS['green'])),
        totals=dict(marker=dict(color=COLORS['blue'])),
        text=[_fmt(v) for v in y_values],
        textposition='outside',
        textfont=dict(size=9, color='#8A8A90'),
    ))
    fig.update_layout(
        title=f'Variação do Lucro Líquido: {year_prev} → {year_curr}',
        **lo(), height=h, showlegend=False,
        xaxis=dict(showgrid=False, color='#525257'),
        yaxis=dict(showgrid=True, gridcolor='#2A2A2D', color='#525257',
                   title_text='R$ mil'),
    )
    return fig


def chart_peer_scatter(peer_df: pd.DataFrame, selected_company: str, h: int = 420):
    df2 = peer_df.dropna(subset=['Margem Líquida', 'ROE']).copy()
    if df2.empty:
        return None
    med_at = df2['Ativo Total (R$ mi)'].median() or 1
    df2['_size_px'] = (
        df2['Ativo Total (R$ mi)'].fillna(med_at).clip(lower=1)
        .apply(lambda v: min(max(v ** 0.28, 10), 70))
    )
    colors = [COLORS['green'] if e == selected_company else '#3D3D42'
              for e in df2['Empresa']]
    fig = go.Figure(go.Scatter(
        x=df2['Margem Líquida'] * 100,
        y=df2['ROE'] * 100,
        mode='markers+text',
        text=df2['Empresa'],
        textposition='top center',
        textfont=dict(size=9, color='#8A8A90'),
        marker=dict(size=df2['_size_px'], color=colors,
                    line=dict(width=1, color='#0F0F10'), opacity=0.85),
        hovertemplate=(
            '<b>%{text}</b><br>Margem Líq: %{x:.1f}%<br>'
            'ROE: %{y:.1f}%<extra></extra>'
        ),
    ))
    fig.update_layout(
        title='Margem Líquida vs ROE — Posicionamento Setorial',
        **lo(), height=h,
        xaxis=dict(title='Margem Líquida (%)', showgrid=True,
                   gridcolor='#2A2A2D', color='#525257'),
        yaxis=dict(title='ROE (%)', showgrid=True,
                   gridcolor='#2A2A2D', color='#525257'),
    )
    fig.add_hline(y=0, line_dash='dot', line_color='#2A2A2D')
    fig.add_vline(x=0, line_dash='dot', line_color='#2A2A2D')
    return fig


def chart_peer_bars(company_val, sector_avg, label: str, color: str, h: int = 240):
    """Barra empresa vs média setor."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Empresa', x=[label], y=[company_val * 100 if company_val else 0],
        marker_color=COLORS['green'], marker_line_width=0,
    ))
    fig.add_trace(go.Bar(
        name='Média Setor', x=[label], y=[sector_avg * 100 if sector_avg else 0],
        marker_color='#3D3D42', marker_line_width=0,
    ))
    fig.update_layout(
        **lo(), barmode='group', height=h,
        title=f'{label} (%)',
        legend=dict(orientation='h', y=1.1, x=0, font=dict(color='#8A8A90'),
                    bgcolor='rgba(0,0,0,0)'),
        xaxis=dict(showgrid=False, color='#525257'),
        yaxis=dict(showgrid=True, gridcolor='#2A2A2D', color='#525257', title_text='%'),
    )
    return fig


def chart_price_history(df_hist: pd.DataFrame, ticker: str, h: int = 360) -> go.Figure:
    """Gráfico de preço (1 ano) com volume e MA20.

    Eixo esquerdo  → Preço (Close + MA20)
    Eixo direito   → Volume (barras semitransparentes)
    """
    if df_hist.empty:
        return None

    # Cores por variação diária
    pct_change = df_hist['Close'].pct_change().fillna(0)
    bar_colors = [COLORS['green'] if v >= 0 else COLORS['red'] for v in pct_change]

    fig = go.Figure()

    # Barras de volume (eixo direito)
    fig.add_trace(go.Bar(
        x=df_hist['Date'], y=df_hist['Volume'],
        name='Volume',
        marker_color=bar_colors,
        marker_line_width=0,
        opacity=0.25,
        yaxis='y2',
        hovertemplate='%{x|%d/%m/%y}<br>Volume: %{y:,.0f}<extra></extra>',
    ))

    # Linha de preço (Close)
    fig.add_trace(go.Scatter(
        x=df_hist['Date'], y=df_hist['Close'],
        name='Preço',
        mode='lines',
        line=dict(color=COLORS['blue'], width=2),
        hovertemplate='%{x|%d/%m/%y}<br>R$ %{y:.2f}<extra></extra>',
    ))

    # MA20
    fig.add_trace(go.Scatter(
        x=df_hist['Date'], y=df_hist['MA20'],
        name='MA 20',
        mode='lines',
        line=dict(color=COLORS['amber'], width=1.5, dash='dot'),
        hovertemplate='MA20: R$ %{y:.2f}<extra></extra>',
    ))

    # Anotação min/max
    idx_max = df_hist['Close'].idxmax()
    idx_min = df_hist['Close'].idxmin()
    annotations = []
    for idx, label, ay in [(idx_max, 'Máx', 1.02), (idx_min, 'Mín', -0.06)]:
        annotations.append(dict(
            x=df_hist.loc[idx, 'Date'],
            y=df_hist.loc[idx, 'Close'],
            text=f"{label} R$ {df_hist.loc[idx, 'Close']:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor='#525257',
            arrowsize=0.8,
            ax=0, ay=ay * 40,
            font=dict(size=9, color='#8A8A90'),
            bgcolor='rgba(15,15,16,0.7)',
            bordercolor='#2A2A2D',
        ))

    fig.update_layout(
        title=f'Histórico de Preço — {ticker} (12 meses)',
        **lo('margin'),
        height=h,
        showlegend=True,
        annotations=annotations,
        legend=dict(orientation='h', y=1.08, x=0,
                    font=dict(size=10, color='#8A8A90'),
                    bgcolor='rgba(0,0,0,0)', bordercolor='#2A2A2D'),
        xaxis=dict(showgrid=False, color='#525257', tickformat='%b %y',
                   rangeslider=dict(visible=False)),
        yaxis=dict(title='Preço (R$)', showgrid=True, gridcolor='#2A2A2D',
                   color='#525257', side='left'),
        yaxis2=dict(title='Volume', overlaying='y', side='right',
                    showgrid=False, color='#525257',
                    tickformat='.2s'),
        margin=dict(l=60, r=60, t=42, b=10),
        hovermode='x unified',
    )
    return fig


def chart_sector_heatmap(hdf: pd.DataFrame, sector_map: dict, metric: str,
                         metric_label: str, selected: str, h: int = 700) -> go.Figure:
    """Heatmap setorial: ranking horizontal por métrica, colorido por quartil."""
    hdf = hdf.copy()
    hdf['Setor'] = hdf['CD_CVM'].map(sector_map).fillna('Outros')

    valid = hdf.dropna(subset=[metric]).copy()
    valid = valid.sort_values(['Setor', metric], ascending=[True, False])

    if valid.empty:
        return None

    def _abbr(name):
        words = name.split()
        return ' '.join(words[:3]) if len(words) > 3 else name

    valid['EmpresaLabel'] = valid['Empresa'].apply(_abbr)

    companies  = valid['EmpresaLabel'].tolist()
    values     = valid[metric].tolist()
    sectors    = valid['Setor'].tolist()
    full_names = valid['Empresa'].tolist()

    text  = [f'{v*100:.1f}%' if v is not None else '—' for v in values]
    hover = [
        f'<b>{full_names[i]}</b><br>'
        f'{metric_label}: {values[i]*100:.1f}%<br>'
        f'Setor: {sectors[i]}'
        for i in range(len(companies))
    ]

    fig = go.Figure(go.Bar(
        x=values, y=companies, orientation='h',
        text=text, textposition='auto',
        textfont=dict(size=9, color='#E8E8E8'),
        hovertext=hover, hoverinfo='text',
        marker=dict(
            color=values,
            colorscale=[
                [0.0,  '#EF4444'],
                [0.35, '#F59E0B'],
                [0.55, '#8B5CF6'],
                [0.75, '#3B82F6'],
                [1.0,  '#00BF7A'],
            ],
            showscale=True,
            colorbar=dict(
                title=dict(text=metric_label, font=dict(color='#8A8A90', size=10)),
                tickformat='.0%',
                tickfont=dict(color='#8A8A90', size=9),
                len=0.8,
            ),
            line=dict(width=0),
        ),
    ))

    sector_breaks = [i - 0.5 for i in range(1, len(sectors)) if sectors[i] != sectors[i-1]]
    for brk in sector_breaks:
        fig.add_hline(y=brk, line_color='#2A2A2D', line_width=1, line_dash='dot')

    seen: dict = {}
    for i, s in enumerate(sectors):
        if s not in seen:
            seen[s] = i
    annotations = [
        dict(x=-0.01, y=companies[i], text=s[:20],
             xref='paper', yref='y',
             showarrow=False, xanchor='right',
             font=dict(size=8, color='#525257'))
        for s, i in seen.items()
    ]

    sel_abbr = _abbr(selected)
    if sel_abbr in companies:
        idx = companies.index(sel_abbr)
        fig.add_shape(
            type='rect',
            x0=min(0, min(v for v in values if v)),
            x1=max(v for v in values if v) * 1.05,
            y0=idx - 0.4, y1=idx + 0.4,
            line=dict(color='#00BF7A', width=1.5),
            fillcolor='rgba(0,191,122,0.05)',
        )

    fig.update_layout(
        **lo('margin'),
        height=max(h, len(companies) * 22 + 60),
        annotations=annotations,
        xaxis=dict(tickformat='.0%', color='#525257', showgrid=True, gridcolor='#2A2A2D'),
        yaxis=dict(color='#8A8A90', showgrid=False, autorange='reversed',
                   tickfont=dict(size=9)),
        margin=dict(l=160, r=20, t=40, b=30),
        title=dict(text=f'Ranking de {metric_label} — Todas as Empresas',
                   font=dict(size=13)),
    )
    return fig
