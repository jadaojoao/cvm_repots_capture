# -*- coding: utf-8 -*-
"""
CVM Analytics — Terminal Financeiro Corporativo
v6: Tema escuro Linear, sidebar toggle explícito, KPIs pré-computados,
    layout moderno, charts dark-mode, performance otimizada.
"""
import streamlit as st
import streamlit.components.v1 as st_components
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sqlite3
import io
import os
import re

ROOT    = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, '..', 'data', 'db', 'cvm_financials.db')

st.set_page_config(
    page_title="CVM Analytics",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — única fonte de verdade
# ═══════════════════════════════════════════════════════════════════════════════
_CSS_PATH = os.path.join(ROOT, 'styles', 'style.css')
with open(_CSS_PATH, 'r', encoding='utf-8') as _f:
    st.markdown(f'<style>{_f.read()}</style>', unsafe_allow_html=True)

# Botão de expandir sidebar: faixa fina que abre no hover (não sobrepõe conteúdo)
st_components.html("""
<script>
(function() {
  var STRIP_ID = '__cvm_sidebar_strip__';

  function getBtn() {
    try { return window.parent.document.querySelector('[data-testid="stExpandSidebarButton"]'); }
    catch(e) { return null; }
  }

  function getDoc() {
    try { return window.parent.document; } catch(e) { return null; }
  }

  function isCollapsed() {
    var doc = getDoc();
    if (!doc) return false;
    var sb = doc.querySelector('[data-testid="stSidebar"]');
    if (!sb) return true;
    var rect = sb.getBoundingClientRect();
    return rect.width < 50;
  }

  function ensureStrip() {
    var doc = getDoc();
    if (!doc) return;

    var existing = doc.getElementById(STRIP_ID);
    if (!existing) {
      var el = doc.createElement('div');
      el.id = STRIP_ID;
      Object.assign(el.style, {
        position: 'fixed',
        top: '0', left: '0', bottom: '0',
        width: '4px',
        background: '#00BF7A',
        zIndex: '9998',
        cursor: 'pointer',
        transition: 'width 0.2s ease, box-shadow 0.2s ease',
        opacity: '0.7',
        borderRadius: '0 4px 4px 0',
      });

      // Tooltip com seta ao expandir
      var arrow = doc.createElement('div');
      Object.assign(arrow.style, {
        position: 'absolute',
        top: '50%',
        left: '100%',
        transform: 'translateY(-50%)',
        background: '#00BF7A',
        color: '#000',
        fontWeight: '700',
        fontSize: '13px',
        width: '24px',
        height: '40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '0 8px 8px 0',
        opacity: '0',
        transition: 'opacity 0.18s ease',
        pointerEvents: 'none',
        fontFamily: 'Inter, sans-serif',
      });
      arrow.textContent = '›';
      el.appendChild(arrow);

      el.addEventListener('mouseenter', function() {
        el.style.width = '28px';
        el.style.opacity = '1';
        el.style.boxShadow = '2px 0 16px rgba(0,191,122,0.35)';
        arrow.style.opacity = '1';
      });
      el.addEventListener('mouseleave', function() {
        el.style.width = '4px';
        el.style.opacity = '0.7';
        el.style.boxShadow = 'none';
        arrow.style.opacity = '0';
      });
      el.addEventListener('click', function() {
        var btn = getBtn();
        if (btn) btn.click();
      });

      doc.body.appendChild(el);
      existing = el;
    }

    // Mostrar só quando sidebar estiver recolhida
    existing.style.display = isCollapsed() ? 'block' : 'none';
  }

  // Inicializa e observa mudanças de estado da sidebar
  [0, 200, 500, 1000, 2000].forEach(function(t) { setTimeout(ensureStrip, t); });
  try {
    var obs = new MutationObserver(ensureStrip);
    obs.observe(getDoc().body, { childList: true, subtree: true, attributes: true });
  } catch(e) {}
})();
</script>
""", height=1, scrolling=False)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTAS (mapeadas via diagnóstico real do banco)
# ═══════════════════════════════════════════════════════════════════════════════
RECEITA   = ['Receita de Venda de Bens e/ou Serviços', 'Receitas das Operações',
             'Receitas de Intermediação Financeira']
LUCRO     = ['Lucro/Prejuízo Consolidado do Período',
             'Resultado Líquido das Operações Continuadas']
RES_BRUT  = ['Resultado Bruto']
CUSTO     = ['Custo dos Bens e/ou Serviços Vendidos']
DESP_OP   = ['Despesas/Receitas Operacionais']
AT_CIRC   = ['Ativo Circulante']
AT_NCIRC  = ['Ativo Não Circulante']
CAIXA     = ['Caixa e Equivalentes de Caixa']
PL        = ['Patrimônio Líquido Consolidado']
PASS_C    = ['Passivo Circulante']
PASS_NC   = ['Passivo Não Circulante']
DIVIDA    = ['Empréstimos e Financiamentos', 'Debêntures']
FCO       = ['Caixa Líquido Atividades Operacionais']
FCI       = ['Caixa Líquido Atividades de Investimento']
FCF_ACTIV = ['Caixa Líquido Atividades de Financiamento']

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def val(df, names, year, period=None):
    """Busca valor anual ou trimestral. Retorna o primeiro nome que tiver dados
    (semântica de 'alias alternativo' — empresas usam nomes distintos)."""
    if isinstance(names, str): names = [names]
    p = period if period else str(year)
    base = df[(df['REPORT_YEAR'] == year) & (df['PERIOD_LABEL'] == p)]
    for n in names:
        r = base.loc[base['STANDARD_NAME'] == n, 'VL_CONTA']
        if not r.empty:
            s = r.sum()
            return float(s) if s != 0 else None
    return None

def safe_div(a, b):
    if a is not None and b is not None and b != 0: return a / b
    return None

def brl(v):
    if v is None: return "—"
    a = abs(v); s = "-" if v < 0 else ""
    if a >= 1e6: return f"{s}R$ {a/1e6:,.1f} bi"
    if a >= 1e3: return f"{s}R$ {a/1e3:,.1f} mi"
    return f"{s}R$ {a:,.0f} mil"

def pct(v):
    if v is None: return "—"
    return f"{v*100:.1f}%"

def qsort(label):
    m = re.match(r'(\d)Q(\d{2})', str(label))
    return (int('20' + m.group(2)), int(m.group(1))) if m else (9999, 0)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING (com cache agressivo)
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def load_companies():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT DISTINCT CD_CVM, COMPANY_NAME FROM financial_reports "
        "WHERE COMPANY_NAME IS NOT NULL ORDER BY COMPANY_NAME", conn
    )
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_sectors():
    EXCEL_BASE = os.path.join(ROOT, '..', 'output', 'reports',
                              'base_analitica_dashboard_preenchida.xlsx')
    # Correções e complementos ao mapeamento do Excel
    # (empresas ausentes ou com setor genérico "Holdings Setoriais" incorreto)
    _overrides = {
        # Sem mapeamento no Excel
        24783: 'Farmacêutico e Higiene',        # NATURA &CO HOLDING
        22217: 'Seguradoras e Corretoras',       # ALPER CONSULTORIA E CORRETORA DE SEGUROS

        # Petróleo e Gás — peers da Petrobras (scraped separately)
        22187: 'Petróleo e Gás',                 # PRIO S.A. (ex-PetroRio)
        25291: 'Petróleo e Gás',                 # BRAVA ENERGIA S.A. (ex-3R Petroleum)

        # Correções de setor genérico "Holdings Setoriais"
         5410: 'Máquinas, Equipamentos, Veículos e Peças',  # WEG SA
         2437: 'Energia Elétrica',               # ELETROBRAS
    }
    if os.path.exists(EXCEL_BASE):
        df = pd.read_excel(EXCEL_BASE)
        sm = (df[['cd_cvm', 'setor_analitico']].drop_duplicates()
                .set_index('cd_cvm')['setor_analitico'].to_dict())
        sm.update(_overrides)
        return sm
    return dict(_overrides)

@st.cache_data(ttl=120)
def load_all(cd_cvm: int) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM financial_reports WHERE CD_CVM = ?",
        conn, params=(cd_cvm,)
    )
    conn.close()
    # Pre-cast para acelerar filtros booleanos
    df['REPORT_YEAR'] = df['REPORT_YEAR'].astype(int)
    return df

@st.cache_data(ttl=300)
def load_peer_df(sector: str, sector_map_items: tuple) -> pd.DataFrame:
    """Carrega dados dos peers num único query parametrizado."""
    sm = dict(sector_map_items)
    peer_cvms = [int(c) for c, s in sm.items() if s == sector]
    if not peer_cvms:
        return pd.DataFrame()
    placeholders = ','.join(['?'] * len(peer_cvms))
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        f"SELECT * FROM financial_reports "
        f"WHERE CD_CVM IN ({placeholders}) "
        f"AND REPORT_YEAR=2024 AND PERIOD_LABEL='2024'",
        conn, params=peer_cvms
    )
    conn.close()
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# PRÉ-COMPUTAÇÃO DE KPIs (único pass por empresa/ano — performance)
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=120)
def precompute_kpis(cd_cvm: int, years_tuple: tuple) -> dict:
    """
    Calcula todos os KPIs anuais de uma vez, evitando 30+ filtros individuais.
    Retorna dict {year: {kpi: value}}.
    """
    df = load_all(cd_cvm)
    annual = df[df['PERIOD_LABEL'].str.match(r'^\d{4}$', na=False)]

    result = {}
    for y in years_tuple:
        # Mesma semântica do val(): REPORT_YEAR == y E PERIOD_LABEL == str(y)
        ay = annual[(annual['REPORT_YEAR'] == y) & (annual['PERIOD_LABEL'] == str(y))]
        if ay.empty:
            result[y] = {}
            continue

        def _g(names):
            """First-match: retorna o primeiro nome da lista que tiver dados."""
            for n in names:
                r = ay.loc[ay['STANDARD_NAME'] == n, 'VL_CONTA']
                if not r.empty:
                    s = r.sum()
                    return float(s) if s != 0 else None
            return None

        rec  = _g(RECEITA);  luc  = _g(LUCRO);  rb  = _g(RES_BRUT)
        ac   = _g(AT_CIRC);  anc  = _g(AT_NCIRC)
        pl_v = _g(PL);       cx   = _g(CAIXA);  div = _g(DIVIDA)
        pc   = _g(PASS_C);   pnc  = _g(PASS_NC)
        fco  = _g(FCO);      fci  = _g(FCI);    dop = _g(DESP_OP)

        at       = ((ac or 0) + (anc or 0)) or None
        ebitda   = (rb + (dop or 0)) if rb else None
        div_liq  = ((div or 0) - (cx or 0)) if div else None
        fcl      = ((fco or 0) + (fci or 0)) if (fco or fci) else None

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
    """Calcula KPIs dos peers a partir do DataFrame serializado."""
    if not raw_df_json:
        return pd.DataFrame()
    peers_df = pd.read_json(io.StringIO(raw_df_json))
    rows = []
    for cd in peers_df['CD_CVM'].unique():
        p = peers_df[peers_df['CD_CVM'] == cd]
        name = p['COMPANY_NAME'].iloc[0] if 'COMPANY_NAME' in p.columns else str(cd)

        def _s(names, _p=p):
            v = _p[_p['STANDARD_NAME'].isin(names)]['VL_CONTA'].sum()
            return float(v) if v != 0 else None

        rec = _s(RECEITA); luc = _s(LUCRO); rb = _s(RES_BRUT)
        ac  = _s(AT_CIRC); anc = _s(AT_NCIRC); pl_v = _s(PL)
        at  = ((ac or 0) + (anc or 0)) or None
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

# ═══════════════════════════════════════════════════════════════════════════════
# TEMA PLOTLY — dark mode alinhado com Linear
# ═══════════════════════════════════════════════════════════════════════════════
LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=42, b=10),
    font=dict(family='Inter', size=11, color='#8A8A90'),
    title_font=dict(family='Inter', size=13, color='#E8E8E8'),
    yaxis=dict(
        showgrid=True, gridcolor='#2A2A2D',
        zeroline=True, zerolinecolor='#2A2A2D',
        color='#525257',
    ),
    xaxis=dict(
        showgrid=False,
        color='#525257',
    ),
    legend=dict(
        bgcolor='rgba(0,0,0,0)',
        bordercolor='#2A2A2D',
        font=dict(color='#8A8A90'),
    ),
)

COLORS = {
    'green':  '#00BF7A',
    'blue':   '#3B82F6',
    'purple': '#8B5CF6',
    'amber':  '#F59E0B',
    'red':    '#EF4444',
    'slate':  '#475569',
    'muted':  '#3D3D42',
}

def lo(*exclude):
    """LAYOUT sem as chaves que serão passadas explicitamente,
    evitando TypeError de argumento duplicado em update_layout()."""
    skip = {'xaxis', 'yaxis', 'legend'} | set(exclude)
    return {k: v for k, v in LAYOUT.items() if k not in skip}

# ═══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════════════
def chart_bars(df, names, title, color=COLORS['blue'], h=340):
    if isinstance(names, str): names = [names]
    sub = df[df['STANDARD_NAME'].isin(names)
             & df['PERIOD_LABEL'].str.match(r'^\dQ\d{2}$', na=False)].copy()
    if sub.empty: return None
    agg = sub.groupby('PERIOD_LABEL')['VL_CONTA'].sum().reset_index()
    agg = agg.iloc[agg['PERIOD_LABEL'].apply(qsort).argsort()]
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

def chart_line(data, title, h=300):
    if not data or all(v is None for v in data.values()): return None
    years = sorted(data.keys())
    vals  = [data[y] * 100 if data[y] is not None else None for y in years]
    valid = [(str(y), v) for y, v in zip(years, vals) if v is not None]
    if not valid: return None
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

def chart_donut(labels, values, title, h=300):
    if not values: return None
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

def sparkline(data, color=COLORS['green'], height=56):
    ys = [data.get(y) for y in sorted(data.keys())]
    ys_clean = [v if v is not None else float('nan') for v in ys]
    r_c = int(color[1:3], 16); g_c = int(color[3:5], 16); b_c = int(color[5:7], 16)
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

def chart_dfc_grouped(df, h=400):
    pattern = r'^\dQ\d{2}$'
    series  = [('FCO', FCO, COLORS['green']),
               ('FCI', FCI, COLORS['blue']),
               ('FCF', FCF_ACTIV, COLORS['amber'])]
    labels_union, traces_data, agg_map = set(), [], {}
    for name, acct_names, color in series:
        sub = df[df['STANDARD_NAME'].isin(acct_names)
                 & df['PERIOD_LABEL'].str.match(pattern, na=False)].copy()
        if sub.empty: continue
        agg = sub.groupby('PERIOD_LABEL')['VL_CONTA'].sum()
        labels_union.update(agg.index)
        traces_data.append((name, agg, color))
        agg_map[name] = agg
    if not traces_data: return None
    sorted_labels = sorted(labels_union, key=qsort)
    fig = go.Figure()
    for name, agg, color in traces_data:
        fig.add_trace(go.Bar(
            name=name, x=sorted_labels,
            y=[agg.get(l, 0) for l in sorted_labels],
            marker_color=color, marker_line_width=0,
            text=[f'{agg.get(l, 0):,.0f}' for l in sorted_labels],
            textposition='outside', textfont=dict(size=7, color='#525257'),
        ))
    if 'FCO' in agg_map and 'FCI' in agg_map:
        fcl_vals = [agg_map['FCO'].get(l, 0) + agg_map['FCI'].get(l, 0)
                    for l in sorted_labels]
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

def chart_yoy_waterfall(df, year_curr, year_prev, h=380):
    def _d(names, y):
        v = val(df, names, y)
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
        a = abs(v); s = '-' if v < 0 else '+'
        if a >= 1e6: return f'{s}R${a/1e6:,.1f}bi'
        if a >= 1e3: return f'{s}R${a/1e3:,.1f}mi'
        return f'{s}R${a:,.0f}k'

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

def chart_peer_scatter(peer_df, selected_company, h=420):
    df2 = peer_df.dropna(subset=['Margem Líquida', 'ROE']).copy()
    if df2.empty: return None
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

def chart_peer_bars(company_val, sector_avg, label, color, h=240):
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

# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
def build_excel(name, df, years, kpis_by_year):
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
                'Ano': y,
                'Receita':              k.get('rec'),
                'Lucro':                k.get('luc'),
                'Ativo Total':          k.get('at'),
                'PL':                   k.get('pl'),
                'Res.Bruto':            k.get('rb'),
                'FCO':                  k.get('fco'),
                'FCI':                  k.get('fci'),
                'FCL (FCO+FCI)':        k.get('fcl'),
                'Dívida Líquida':       k.get('div_liq'),
                'EBITDA (Proxy)':       k.get('ebitda'),
                'Margem Bruta':         k.get('mb'),
                'Margem Líquida':       k.get('ml'),
                'ROE':                  k.get('roe'),
                'ROA':                  k.get('roa'),
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

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    companies = load_companies()
    if companies.empty:
        st.error("Banco de dados vazio. Execute o scraper primeiro.")
        return

    # ── SIDEBAR ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<span class="dot"></span>CVM Analytics'
            '</div>'
            '<div class="sidebar-version">Terminal Financeiro Corporativo</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        opts = {r['COMPANY_NAME']: int(r['CD_CVM'])
                for _, r in companies.iterrows()}
        company_names = list(opts.keys())

        search_term = st.text_input(
            "Buscar empresa",
            placeholder="Nome ou código CVM…",
            key="company_search",
        )
        if search_term:
            s = search_term.lower()
            filtered = [n for n in company_names
                        if s in n.lower() or s in str(opts[n])]
            if not filtered:
                st.warning("Nenhuma empresa encontrada.")
                filtered = company_names
        else:
            filtered = company_names

        default_idx = filtered.index('PETROBRAS') if 'PETROBRAS' in filtered else 0
        sel = st.selectbox("Empresa", filtered, index=default_idx,
                           key="company_select")
        cvm = opts[sel]

        st.markdown("---")
        dark_dense = st.checkbox("Modo Denso", value=False, key="dense_mode")
        st.markdown("---")
        st.markdown(
            '<p style="font-size:0.7rem;color:#525257;text-align:center;">'
            '← clique na seta verde para expandir</p>',
            unsafe_allow_html=True,
        )

    # Aplica modo denso via classe CSS no container raiz
    if dark_dense:
        st.markdown(
            '<script>document.querySelector(".stApp").classList.add("modo-denso")</script>',
            unsafe_allow_html=True,
        )

    # ── DADOS ─────────────────────────────────────────────────────────────────
    df          = load_all(cvm)
    if df.empty:
        st.warning("Sem dados para esta empresa.")
        return

    years       = tuple(sorted(df['REPORT_YEAR'].unique()))
    latest      = max(years)
    sector_map  = load_sectors()
    this_sector = sector_map.get(cvm, 'N/D')

    # Pré-computação única de todos os KPIs
    kpis = precompute_kpis(cvm, years)
    k    = kpis.get(latest, {})

    # ── HEADER ───────────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="company-header">'
        f'  <div class="company-name">{sel}</div>'
        f'  <div class="company-meta">'
        f'    <span class="badge badge-accent">{this_sector}</span>'
        f'    <span class="badge">CVM {cvm}</span>'
        f'    <span class="badge">{min(years)}–{max(years)}</span>'
        f'    <span class="badge">Consolidado</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab_visao, tab_demo, tab_peers, tab_export = st.tabs([
        "📈  Visão Geral", "📋  Demonstrações",
        "🏢  Peers", "⬇  Exportar",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — VISÃO GERAL
    # ─────────────────────────────────────────────────────────────────────────
    with tab_visao:
        # YoY deltas usando KPIs pré-computados
        k_prev = kpis.get(years[-2], {}) if len(years) >= 2 else {}

        def yoy(curr, prev):
            g = safe_div(curr, prev)
            return f'{(g-1)*100:+.1f}% YoY' if g is not None else None

        def yoy_pp(curr, prev):
            if curr is not None and prev is not None:
                return f'{(curr-prev)*100:+.1f} pp'
            return None

        # KPI Cards
        st.markdown('<div class="sec">Indicadores Principais</div>',
                    unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Receita Líq.",   brl(k.get('rec')),
                  yoy(k.get('rec'), k_prev.get('rec')),
                  help="Receitas de venda e serviços.")
        c2.metric("Lucro Líq.",     brl(k.get('luc')),
                  yoy(k.get('luc'), k_prev.get('luc')),
                  help="Resultado final após impostos.")
        c3.metric("Ativo Total",    brl(k.get('at')),
                  help="Bens + Direitos da empresa.")
        c4.metric("ROE",            pct(k.get('roe')),
                  yoy_pp(k.get('roe'), k_prev.get('roe')),
                  help="Lucro / Patrimônio Líquido.")
        c5.metric("Dívida/EBITDA",
                  f"{k['alav']:.2f}x" if k.get('alav') else "—",
                  help="Dívida Líquida / EBITDA proxy.")
        c6.metric("Liq. Corrente",
                  f"{k['liq_corr']:.2f}x" if k.get('liq_corr') else "—",
                  help="Ativo Circ. / Passivo Circ.")

        # Sparklines abaixo dos cards
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

        # Gráficos trimestrais
        st.markdown('<div class="sec">Evolução Trimestral</div>',
                    unsafe_allow_html=True)
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

        # KPIs anuais (linhas)
        st.markdown('<div class="sec">Indicadores Anuais</div>',
                    unsafe_allow_html=True)
        kpi_series = {
            'Margem Bruta':    {y: kpis[y].get('mb')  for y in years},
            'ROE':             {y: kpis[y].get('roe') for y in years},
            'Margem Líquida':  {y: kpis[y].get('ml')  for y in years},
            'ROA':             {y: kpis[y].get('roa') for y in years},
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

        # Composição patrimonial
        st.markdown('<div class="sec">Composição Patrimonial</div>',
                    unsafe_allow_html=True)
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

        # Waterfall YoY
        if len(years) >= 2:
            st.markdown('<div class="sec">Variação Anual do Resultado</div>',
                        unsafe_allow_html=True)
            wf1, wf2, _wf3 = st.columns([2, 2, 8])
            with wf1:
                year_curr_wf = st.selectbox(
                    "Ano atual", options=list(reversed(years)), index=0, key="wf_curr"
                )
            with wf2:
                prev_opts = [y for y in reversed(years) if y < year_curr_wf]
                year_prev_wf = st.selectbox(
                    "Ano base", options=prev_opts or [None], index=0,
                    key="wf_prev", disabled=not prev_opts,
                )
            if prev_opts:
                fig = chart_yoy_waterfall(df, year_curr_wf, year_prev_wf)
                if fig: st.plotly_chart(fig, use_container_width=True, key='wf')

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — DEMONSTRAÇÕES
    # ─────────────────────────────────────────────────────────────────────────
    with tab_demo:
        st.markdown('<div class="sec">Detalhamento Contábil</div>',
                    unsafe_allow_html=True)
        all_stmts = sorted(df['STATEMENT_TYPE'].dropna().unique())

        dc1, dc2, dc3 = st.columns([2, 3, 2])
        with dc1:
            period_mode = st.radio("Período", ["Anual", "Trimestral"],
                                   horizontal=True, key="demo_period")
        with dc2:
            stmt_filter = st.multiselect("Demonstrativos", all_stmts,
                                         default=list(all_stmts), key="demo_stmts")
        with dc3:
            hide_zeros = st.checkbox("Ocultar linhas zeradas", value=True,
                                     key="demo_zeros")

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
            st.dataframe(pv.style.format('{:,.0f}'),
                         use_container_width=True, height=580)
        else:
            st.info("Nenhum dado para os filtros selecionados.")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — PEERS
    # ─────────────────────────────────────────────────────────────────────────
    with tab_peers:
        if this_sector == 'N/D':
            st.info(
                "Setor não mapeado para esta empresa. "
                "Preencha `base_analitica_dashboard_preenchida.xlsx` e recarregue."
            )
        else:
            st.markdown(
                f'<div class="sec">Setor: {this_sector}</div>',
                unsafe_allow_html=True,
            )
            # Carrega peers (único query cacheado)
            sector_map_items = tuple(sorted(sector_map.items()))
            raw_peer_df = load_peer_df(this_sector, sector_map_items)

            if raw_peer_df.empty:
                st.info("Sem dados de peers disponíveis para este setor em 2024.")
            else:
                peer_df = compute_peer_kpis(raw_peer_df.to_json())

                # KPIs médios do setor
                roe_v = k.get('roe'); ml_v = k.get('ml'); mb_v = k.get('mb')
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
                    above = roe_v and roe_sector and roe_v > roe_sector
                    st.metric(
                        "ROE vs Setor",
                        pct(roe_v),
                        f'{(roe_v - roe_sector)*100:+.1f} pp vs média'
                        if roe_v and roe_sector else '—',
                    )
                    st.metric(
                        "Margem Líq. vs Setor",
                        pct(ml_v),
                        f'{(ml_v - ml_sector)*100:+.1f} pp vs média'
                        if ml_v and ml_sector else '—',
                    )

                # Tabela de todos os peers
                st.markdown('<div class="sec">Ranking do Setor (2024)</div>',
                            unsafe_allow_html=True)
                display_df = peer_df.drop(columns=['CD_CVM'], errors='ignore').copy()
                pct_cols_p = ['Margem Líquida', 'Margem Bruta', 'ROE', 'ROA']
                fmt = {c: '{:.1%}' for c in pct_cols_p if c in display_df.columns}
                fmt.update({c: '{:,.1f}' for c in
                            ['Receita (R$ mi)', 'Lucro (R$ mi)', 'Ativo Total (R$ mi)']
                            if c in display_df.columns})
                st.dataframe(
                    display_df.style.format(fmt, na_rep='—'),
                    use_container_width=True, height=300,
                )

                # Scatter de posicionamento
                st.markdown(
                    '<div class="sec">Mapa de Posicionamento — Margem Líquida vs ROE</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<p class="scatter-note">Tamanho da bolha proporcional ao Ativo Total. '
                    'Empresa selecionada em verde.</p>',
                    unsafe_allow_html=True,
                )
                fig = chart_peer_scatter(peer_df, sel)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key='peer_scatter')

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4 — EXPORTAR
    # ─────────────────────────────────────────────────────────────────────────
    with tab_export:
        st.markdown('<div class="sec">Exportação de Dados</div>',
                    unsafe_allow_html=True)

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


if __name__ == '__main__':
    main()
