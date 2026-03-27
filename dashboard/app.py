# -*- coding: utf-8 -*-
"""
CVM Analytics — Terminal Financeiro Corporativo
Orquestrador principal: configuração da página, sidebar e roteamento de abas.

Lógica de negócio extraída para:
  dashboard/constants.py  — grupos de contas e TICKER_MAP
  dashboard/db.py         — factory get_engine()
  dashboard/data.py       — load_*() com @st.cache_data
  dashboard/kpis.py       — precompute_kpis(), compute_peer_kpis()
  dashboard/charts.py     — LAYOUT, COLORS, todos os chart builders
  dashboard/tabs/         — render_visao_geral, render_demo, render_peers,
                            render_mercado, render_export
"""
import os
import subprocess
import sys
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as st_components

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, '..'))

# ── Imports dos módulos extraídos ──────────────────────────────────────────────
from dashboard.constants import TICKER_MAP, REVERSE_TICKER_MAP
from dashboard.loaders import load_companies, load_all, load_sectors, load_cvm_master
from dashboard.kpis import precompute_kpis
from dashboard.tabs.visao   import render_visao_geral
from dashboard.tabs.demo    import render_demo
from dashboard.tabs.peers   import render_peers
from dashboard.tabs.mercado import render_mercado
from dashboard.tabs.export  import render_export

# ── Configuração da página ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="CVM Analytics",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS_PATH = os.path.join(ROOT, 'styles', 'style.css')
with open(_CSS_PATH, 'r', encoding='utf-8') as _f:
    st.markdown(f'<style>{_f.read()}</style>', unsafe_allow_html=True)

# ── Sidebar expand strip (JS) ──────────────────────────────────────────────────
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

    existing.style.display = isCollapsed() ? 'block' : 'none';
  }

  [0, 200, 500, 1000, 2000].forEach(function(t) { setTimeout(ensureStrip, t); });
  try {
    var obs = new MutationObserver(ensureStrip);
    obs.observe(getDoc().body, { childList: true, subtree: true, attributes: true });
  } catch(e) {}
})();
</script>
""", height=1, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    companies = load_companies()
    if companies.empty:
        st.error("Banco de dados vazio. Execute o scraper primeiro.")
        return

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<span class="dot"></span>CVM Analytics'
            '</div>'
            '<div class="sidebar-version">Terminal Financeiro Corporativo</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Empresas já no banco
        db_map = {int(r['CD_CVM']): r['COMPANY_NAME'] for _, r in companies.iterrows()}
        db_cvms = set(db_map.keys())

        # Lista completa da CVM (cache 24h) — permite buscar empresas não baixadas
        try:
            master_df = load_cvm_master()
            master_map = {
                int(row['CD_CVM']): (row['DENOM_SOCIAL'], row['DENOM_COMERC'])
                for _, row in master_df.iterrows()
                if row['CD_CVM']
            }
        except Exception:
            master_map = {}

        search_term = st.text_input(
            "Buscar empresa",
            placeholder="Nome, ticker (ex: PETR4) ou código CVM…",
            key="company_search",
        )

        def _build_results(term: str) -> list[tuple[str, int, bool]]:
            """Retorna lista de (label, cd_cvm, in_db) filtrada pelo termo."""
            s = term.strip().upper()
            seen: set[int] = set()
            out: list[tuple[str, int, bool]] = []

            def _add(cd: int, name: str, in_db: bool):
                if cd in seen:
                    return
                seen.add(cd)
                ticker = TICKER_MAP.get(cd, '')
                t_str  = f' [{ticker.replace(".SA", "")}]' if ticker else ''
                prefix = '' if in_db else '⬇ '
                out.append((f'{prefix}{name}{t_str}', cd, in_db))

            # 1. Busca direta por ticker (ex: "PETR4")
            if s in REVERSE_TICKER_MAP:
                cd = REVERSE_TICKER_MAP[s]
                name = db_map.get(cd) or master_map.get(cd, ('', ''))[1] or master_map.get(cd, ('', ''))[0] or f'CVM {cd}'
                _add(cd, name, cd in db_cvms)

            # 2. Empresas do banco (nome ou código CVM)
            for cd, name in db_map.items():
                ticker = TICKER_MAP.get(cd, '').replace('.SA', '').upper()
                if s in name.upper() or s in str(cd) or (ticker and s in ticker):
                    _add(cd, name, True)

            # 3. Empresas da CVM não baixadas ainda
            for cd, (social, comerc) in master_map.items():
                if cd in db_cvms:
                    continue
                nome = comerc or social
                ticker = TICKER_MAP.get(cd, '').replace('.SA', '').upper()
                if s in social.upper() or s in comerc.upper() or s in str(cd) or (ticker and s in ticker):
                    _add(cd, nome, False)

            # Ordena: banco primeiro, depois alfabético
            out.sort(key=lambda x: (not x[2], x[0].lstrip('⬇ ')))
            return out

        if search_term:
            results = _build_results(search_term)
            if not results:
                st.caption('Nenhuma empresa encontrada.')
                results = [(db_map[cd], cd, True) for cd in list(db_cvms)[:1]]
        else:
            # Sem busca: exibe apenas as empresas já no banco
            results = []
            for cd in sorted(db_cvms, key=lambda c: db_map[c]):
                ticker = TICKER_MAP.get(cd, '')
                t_str  = f' [{ticker.replace(".SA", "")}]' if ticker else ''
                results.append((f'{db_map[cd]}{t_str}', cd, True))

        labels      = [r[0] for r in results]
        label_to_cd = {r[0]: r[1] for r in results}
        label_in_db = {r[0]: r[2] for r in results}

        # Índice padrão → PETROBRAS
        _def = next((i for i, l in enumerate(labels) if 'PETROBRAS' in l), 0)
        sel_label = st.selectbox('Empresa', labels, index=_def, key='company_select')
        cvm = label_to_cd[sel_label]
        company_in_db = label_in_db[sel_label]

        # Nome limpo (sem [TICKER] e sem ⬇)
        sel = sel_label.lstrip('⬇ ')
        _b = sel.find(' [')
        if _b != -1:
            sel = sel[:_b]
        sel = sel.strip()

        # Botão de download se empresa não está no banco
        if not company_in_db:
            st.info(f'**{sel}** ainda não está no banco local.')
            _ano_dl = datetime.now().year
            if st.button('⬇ Baixar dados desta empresa',
                         use_container_width=True, key='dl_company'):
                with st.spinner(f'Baixando dados de {sel}…'):
                    try:
                        _main_path = os.path.join(ROOT, '..', 'main.py')
                        _res = subprocess.run(
                            [sys.executable, _main_path,
                             '--companies', str(cvm),
                             '--start_year', str(_ano_dl - 3),
                             '--end_year', str(_ano_dl)],
                            capture_output=True, text=True, encoding='utf-8',
                            cwd=os.path.join(ROOT, '..'),
                        )
                        if _res.returncode == 0:
                            st.success('✅ Dados baixados! Recarregue a página.')
                            st.cache_data.clear()
                        else:
                            st.error(f'Erro:\n{_res.stderr[-400:]}')
                    except Exception as _exc:
                        st.error(f'Falha: {_exc}')

        st.markdown("---")
        dark_mode  = st.toggle("🌙 Dark Mode", value=True, key="dark_mode")
        dark_dense = st.checkbox("Modo Denso", value=False, key="dense_mode")
        st.markdown("---")

        _script_path = os.path.join(ROOT, '..', 'scripts', 'atualizar_todos.py')
        _ano_atual   = datetime.now().year
        if st.button("🔄 Atualizar Dados",
                     help="Roda o scraper para todas as empresas (ano atual e anterior)",
                     use_container_width=True):
            with st.spinner("Baixando dados da CVM... (pode demorar alguns minutos)"):
                try:
                    result = subprocess.run(
                        [sys.executable, _script_path,
                         "--anos", str(_ano_atual - 1), str(_ano_atual)],
                        capture_output=True, text=True, encoding='utf-8',
                        cwd=os.path.join(ROOT, '..'),
                    )
                    if result.returncode == 0:
                        st.success("✅ Dados atualizados! Recarregue a página.")
                    else:
                        st.error(f"Erro ao atualizar:\n{result.stderr[-500:]}")
                except Exception as _exc:
                    st.error(f"Falha ao executar scraper: {_exc}")

        st.markdown("---")
        st.markdown(
            '<p style="font-size:0.7rem;color:#525257;text-align:center;">'
            '← clique na seta verde para expandir</p>',
            unsafe_allow_html=True,
        )

    # Empresa não está no banco → não renderiza dashboard
    if not company_in_db:
        st.info(
            f'**{sel}** ainda não tem dados baixados. '
            'Use o botão **⬇ Baixar dados desta empresa** na barra lateral e '
            'recarregue a página após o download concluir.'
        )
        return

    # ── Tema dark/light via JS ─────────────────────────────────────────────────
    theme_classes = []
    if not dark_mode:
        theme_classes.append('light-mode')
    if dark_dense:
        theme_classes.append('modo-denso')
    if theme_classes:
        class_str = ' '.join(theme_classes)
        st_components.html(f"""<script>
        (function(){{
            try {{
                var app = window.parent.document.querySelector('.stApp');
                if (app) {{
                    app.classList.remove('light-mode', 'modo-denso');
                    app.classList.add('{class_str}');
                }}
            }} catch(e) {{}}
        }})();
        </script>""", height=0)

    # ── DADOS ─────────────────────────────────────────────────────────────────
    df = load_all(cvm)
    if df.empty:
        st.warning("Sem dados para esta empresa.")
        return

    years      = tuple(sorted(df['REPORT_YEAR'].unique()))
    latest     = max(years)
    sector_map = load_sectors()
    this_sector = sector_map.get(cvm, 'N/D')
    kpis       = precompute_kpis(cvm, years)

    # ── HEADER ────────────────────────────────────────────────────────────────
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

    # ── ABAS ──────────────────────────────────────────────────────────────────
    tab_visao, tab_demo, tab_peers, tab_market, tab_export = st.tabs([
        "📈  Visão Geral", "📋  Demonstrações",
        "🏢  Peers", "🌐  Mercado", "⬇  Exportar",
    ])

    with tab_visao:
        render_visao_geral(sel, cvm, df, years, latest, kpis, companies)

    with tab_demo:
        render_demo(df)

    with tab_peers:
        render_peers(sel, cvm, kpis, latest, this_sector, sector_map)

    with tab_market:
        render_mercado(sel, years, sector_map)

    with tab_export:
        render_export(sel, cvm, df, years, kpis)


if __name__ == '__main__':
    main()
