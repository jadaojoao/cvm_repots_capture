# MEMORIADASIA.md — Memória Compartilhada entre Agentes de IA

> **PARA AGENTES DE IA**: Este arquivo é o registro contínuo de tudo que foi
> aprendido, sugerido, decidido e discutido neste projeto. Antes de fazer
> qualquer modificação no código, **leia este arquivo inteiro** e o `CONTEXT.md`.
> Depois de concluir seu trabalho, **atualize este arquivo** com o que aprendeu,
> o que sugeriu, o que o usuário decidiu, e qualquer contexto novo.
>
> O objetivo é evitar que o João (dono do projeto) precise repetir contexto.
> Trate este arquivo como um log de handoff entre agentes.

---

## Registro de Sessões

### Sessão 11 — 2026-03-26 (Agente: Claude Sonnet 4.6)

**O que foi feito:**

**🌐 Aba Mercado — Heatmap setorial funcionando:**
- Implementado `load_heatmap_data(year)` + `chart_sector_heatmap()` em `dashboard/app.py`
- Ranking horizontal de todas as empresas por Margem Líquida, ROE, Margem Bruta e ROA
- 61 empresas com dados válidos de ML em 2024; 68 empresas mapeadas por setor
- Seletor de Ano (dentro de `with mc1:`) e Métrica (dentro de `with mc2:`) lado a lado
- Empresa selecionada destacada com borda verde no gráfico
- Separação visual por setor via `fig.add_hline()` + anotações de setor no eixo Y
- Colorscale vermelho→âmbar→roxo→azul→verde (piores→melhores)

**🐛 Bug crítico corrigido — numpy int64 em params SQLite:**
- Sintoma: `load_heatmap_data(2024)` retornava DataFrame vazio (0×0) com `@st.cache_data`
- Diagnóstico: `st.selectbox` retorna itens do tipo numpy `int64` (vindo do `.groupby()` do pandas).
  SQLite/`pd.read_sql` com `params=(int64, str)` falha silenciosamente → 0 rows.
  Confirmado via debug: `total=246037 year_only=80263 both=18664 type=int64`
- Fix: `_year = int(year)` antes de usar como param — força Python `int` nativo
- **Regra geral**: sempre castear `int()` valores de `st.selectbox` antes de usar em queries parametrizadas

**🐛 Bug fix — TypeError 'margin' duplicado no chart:**
- `LAYOUT` dict tem `margin=dict(l=10,r=10,t=42,b=10)` (linha 394 de `app.py`)
- `chart_sector_heatmap` fazia `fig.update_layout(**lo(), margin=dict(l=160,...))` → `margin` duplicado
- Fix: `**lo('margin')` — `lo()` já suporta args extras para exclusão além do set padrão

**🔧 UI/UX — IOTA-inspired refinements (sessão anterior, já commitados):**
- Glassmorphism em KPI cards e company header (`backdrop-filter: blur()`)
- Dark/Light mode toggle no sidebar (JS via `st_components.html`)
- Tipografia dual-font: Nunito Sans (headlines) + Inter (body) via Google Fonts
- Badges pill-shaped (`border-radius: 400px`)
- State-layer nos tabs (`::after` com `opacity: 0→0.06` no hover)
- Animações: `dot-glow` no brand dot, `pulse-subtle` no spinner
- Scrollbar 6px→4px; sombras com elevação progressiva `--shadow-sm/md/lg`

**📦 Expansão da base de dados (68 empresas):**
- Rodado scraper em batch para 30 novas empresas (JBS, BB, Santander, BTG, Magazine Luiza, Hapvida, Rede D'Or etc.)
- DB expandido de ~39 → 68 empresas com dados 2022-2025

**Git:**
- Commit `d709d48`: `feat: Mercado tab — ranking setorial com 68 empresas e fix int64 params`
- Branch: `codex/spawn-subagent-to-explore-repo`
- Push concluído para `origin`

**Bugs conhecidos RESOLVIDOS nesta sessão:**
- `load_heatmap_data` retornando empty por `numpy.int64` em SQLite params
- `TypeError: update_layout() got multiple values for keyword argument 'margin'`
- Layout de selectboxes ANO/MÉTRICA fora das colunas Streamlit

**Padrões técnicos importantes descobertos:**
1. **numpy int64 + sqlite3 params**: `st.selectbox` com opções vindas de `df.groupby()` ou `pd.read_sql` retorna `numpy.int64`, não Python `int`. Sempre fazer `int(year)` antes de usar como parâmetro SQL.
2. **`lo()` helper extensível**: `lo('margin')` exclui `margin` além do set padrão `{xaxis, yaxis, legend}`. Usar sempre que `update_layout` tiver um kwarg que também está no `LAYOUT` global.
3. **Streamlit auto-reload**: precisa clicar "Always rerun" na primeira vez para habilitar hot-reload ao salvar arquivos.

**Caminho atualizado:**
```
✅ Sessão 7  → Waterfall seletor + FCL
✅ Sessão 8  → Expansão para 19→39 empresas
✅ Sessão 9  → Dashboard v6 (Dark/Linear theme, sidebar JS, performance)
✅ Sessão 10 → Bootstrap Windows + docs
✅ Sessão 11 → IOTA UI refinement + aba Mercado (heatmap) funcionando com 68 empresas
✅ Sessão 12 → Valuation via yfinance (P/L, EV/EBITDA, P/VP, DY) para 58 tickers B3
→  Sessão 13 → Comparação multi-empresa overlay
→  Sessão 14 → Automação scraper (CronJob)
```

---

### Sessão 12 — 2026-03-26 (Agente: Claude Sonnet 4.6)

**O que foi feito:**

**📈 Valuation de Mercado via yfinance — aba Visão Geral:**
- Adicionado import condicional `yfinance` com flag `_YF_AVAILABLE` (graceful fallback)
- Adicionado `TICKER_MAP: dict[int, str]` com 58 tickers B3 mapeados por código CVM
  - Cobre grandes e médias capitalizações: PETR4, VALE3, ITUB4, BBDC4, WEGE3, RENT3, B3SA3 etc.
- Adicionado `load_market_data(ticker: str) -> dict` com `@st.cache_data(ttl=900)` (15 min)
  - Busca: preço, market cap, P/L (trailingPE), P/VP (priceToBook), EV/EBITDA, Dividend Yield, EV
  - Retorna `{}` sem exceção caso yfinance falhe (ex: ticker inválido, sem internet)
- Adicionado bloco "VALUATION DE MERCADO" em `tab_visao` (entre sparklines e evolução trimestral)
  - 6 colunas: Preço · Market Cap · P/L · P/VP · EV/EBITDA · Div. Yield
  - Caption com fonte, ticker e frequência de atualização
  - Fallback elegante: "Ticker não mapeado" ou "Não foi possível obter dados"

**🐛 Bug corrigido — Div. Yield 867% (yfinance format):**
- `dividendYield` no yfinance já vem em % (ex: `8.67` = 8.67%), NÃO como decimal (0.0867)
- Código inicial tinha `_mkt['dy']*100` → mostrava 867.0% para VALE
- Fix: usar direto `f"{_mkt['dy']:.1f}%"` sem multiplicar por 100

**✅ Validado para:**
- VALE3.SA: R$ 78.91 · R$ 336.8 bi · P/L 27.4x · P/VP 1.83x · EV/EBITDA 5.4x · DY 8.7%
- PETR4.SA: R$ 48.02 · R$ 618.9 bi · P/L 5.9x · P/VP 1.49x · EV/EBITDA 4.6x · DY 8.2%

**📦 Arquivo `requirements.txt`:**
- Adicionado `yfinance>=0.2`

**Git:**
- Commit pendente (a ser feito após atualização da MEMORIADASIA)

**Padrões técnicos importantes:**
1. **yfinance `dividendYield` format**: retorna valor já em % (ex: `8.67`), NÃO decimal. Não multiplicar por 100.
2. **`_YF_AVAILABLE` guard**: permite que o dashboard funcione mesmo sem yfinance instalado — import condicional com `try/except ImportError`.
3. **`TICKER_MAP` extensão**: para adicionar novas empresas, basta inserir `{cvm_code: 'TICK3.SA'}` no dict no topo de `app.py`.
4. **Cache 15 min**: `@st.cache_data(ttl=900)` para dados de mercado — balance entre frescor e performance.

---

### Sessão 6 — 2026-03-26 (Agente: Claude Sonnet 4.6)

**O que foi feito:**
- **Dashboard v5 — Refatoração e melhorias completas**:
  - `requirements.txt` atualizado com streamlit, plotly, xlsxwriter
  - Bug de regex corrigido em `data_loader.py` (linha 58: `r'\\((\\d+)\\)'` → `r'\((\d+)\)'`)
  - Queries SQL inline substituídas por queries parametrizadas (`?`) — sem SQL injection
  - CSS consolidado em `styles/style.css`; inline removido do `app.py`
  - Cores unificadas para `#00BF7A` (igual ao `config.toml`)
  - Navegação por 4 tabs: Visão Geral · Demonstrações · Comparação Setorial · Exportar
  - Sparklines sob os 6 KPI cards
  - Busca fuzzy de empresas na sidebar (nome ou código CVM)
  - DFC agrupado (FCO / FCI / FCF) em barras agrupadas por trimestre
  - Waterfall YoY: decompõe variação do Lucro (Δ Receita, Δ Custo/Margem, Δ Desp. Op., Δ Outros)
  - Tabela de Demonstrações com toggle Anual/Trimestral
  - Aba Comparação Setorial: tabela de peers + scatter Margem Líquida vs ROE
  - Aba Exportar: botão de download isolado
- **Bug fix**: `chart_peer_scatter` — `LAYOUT` continha `xaxis` e `yaxis`; passá-los novamente causava `TypeError: multiple values`. Fix: filtrar o dict antes de expandir.

**Bugs conhecidos resolvidos:**
- `TypeError: multiple values for keyword argument 'xaxis'` em `chart_peer_scatter` (linha 382)

**Caminhos de melhoria registrados (roadmap):**

| # | Melhoria | Prioridade |
|---|----------|------------|
| 1 | Waterfall com seletor de anos (radio year_curr/year_prev) | ⭐⭐⭐ |
| 2 | FCL = FCO + FCI como métrica nova | ⭐⭐⭐ |
| 3 | Expandir empresas: VALE, ITUB4, BBDC4, WEGE3, RENT3 | ⭐⭐⭐ |
| 4 | Modo comparação multi-empresa (overlay de 2-3 empresas) | ⭐⭐ |
| 5 | Heatmap setorial (go.Heatmap com Margem × ROE) | ⭐⭐ |
| 6 | Automação do scraper via scheduled-tasks MCP | ⭐⭐ |
| 7 | Testes automatizados (pytest para utils.py e scraper) | ⭐⭐ |
| 8 | Valuation: P/L e EV/EBITDA via yfinance (PETR4.SA) | ⭐ |
| 9 | Exportar PDF (pdfkit/weasyprint) | ⭐ |
| 10 | Deploy cloud (SQLite → PostgreSQL + Streamlit Cloud) | ⭐ |

**Caminho recomendado:**
```
Sessão 7  → #1 e #2 (waterfall seletor + FCL) — baixo esforço, alto valor
Sessão 8  → #3 (rodar scraper para 5+ empresas) — desbloqueia #4 e #5
Sessão 9  → #4 ou #5 (multi-empresa ou heatmap)
Sessão 10+→ #6 automação → #7 testes → #8 valuation
```

**Padrão importante descoberto:**
- Ao usar `**LAYOUT` em `fig.update_layout()`, nunca passar `xaxis=`, `yaxis=`, ou `height=`
  explicitamente junto — causará `TypeError: multiple values`. Sempre filtrar antes:
  `_lo = {k: v for k, v in LAYOUT.items() if k not in ('xaxis', 'yaxis')}`
  Ou usar `fig.update_xaxes()` / `fig.update_yaxes()` separadamente (padrão recomendado).

---

### Sessão 9 — 2026-03-26 (Agente: Claude Sonnet 4.6)

**O que foi feito:**

**UI/UX — Tema Dark Linear-inspired (v6):**
- CSS completamente reescrito em `dashboard/styles/style.css` com design tokens CSS (`--bg`, `--bg-card`, `--border`, `--accent`, `--text-primary` etc.)
- Paleta: `#0F0F10` (fundo), `#1C1C1E` (cards), `#2A2A2D` (bordas), `#00BF7A` (accent verde)
- Cards com `.company-header`, badges de setor/CVM/período, layout de terminal financeiro moderno
- Referência de UI: Linear.app (`docs/references/sites_ex/saveweb2zip-com-linear-app/`)

**Sidebar toggle — faixa hover na borda esquerda:**
- Problema: botão de expandir era invisível quando sidebar recolhida
- Tentativa 1: CSS styling do botão nativo → aparecia grande e sobrepunha conteúdo
- Tentativa 2: Remoção completa do botão → sumiu totalmente (usuário reclamou)
- Solução final: Faixa verde fina (4px) na borda esquerda, que expande para 28px com seta `›` ao hover
- Implementada via `st_components.html()` (único método que executa JS no Streamlit, já que `st.markdown` não executa `<script>`)
- `MutationObserver` detecta mudanças de estado da sidebar e mostra/esconde a faixa
- CSS oculta o botão nativo `[data-testid="stExpandSidebarButton"]` com `opacity: 0; pointer-events: none`

**Performance — precompute_kpis():**
- KPIs eram calculados com ~30 chamadas individuais `val()` por empresa → ~30 DB reads
- Substituído por `@st.cache_data` + `precompute_kpis(cd_cvm, years_tuple)` → 1 DB read por empresa
- `val()` com semântica de "primeiro match" (não soma todos os aliases — corrige bug de double-counting)
- Filtro crítico: `PERIOD_LABEL == str(y)` para excluir períodos de comparação dentro de filings recentes

**Bug fix lo() helper — elimina TypeError em update_layout:**
- `LAYOUT` dict contém `xaxis`, `yaxis`, `legend` → passá-los explicitamente junto causa `TypeError: multiple values`
- Criado helper `lo(*exclude)` que filtra `{xaxis, yaxis, legend} | set(exclude)` antes de `**lo()`
- Todas as funções de chart migradas: `chart_dfc_grouped`, `chart_donut`, `chart_peer_scatter`, `chart_peer_bars`, `chart_yoy_waterfall`

**Peers setoriais Petrobras:**
- CVM não tem tabela de peers direta — identificados manualmente via setor "Petróleo e Gás"
- PRIO S.A. (CVM 22187) e BRAVA ENERGIA (CVM 25291) adicionados como peers
- `_overrides` dict em `load_sectors()` corrigido para PRIO e BRAVA que não constavam na base analítica

**Decisão do usuário:**
- Botão de sidebar: "era só trocar, ou mudar de lugar, ou fazer aparecer quando vai perto do canto esquerdo, não tirar totalmente"
- Solução aprovada: faixa hover discreta na borda esquerda

**Padrão técnico importante descoberto:**
- `st.markdown('<script>...</script>')` NÃO executa JS — React usa `dangerouslySetInnerHTML` que ignora scripts
- Único jeito de executar JS no Streamlit: `st.components.v1.html("""<script>...</script>""", height=1, scrolling=False)`
- Para acessar o DOM do app a partir do componente: usar `window.parent.document`

**Caminho atualizado:**
```
✅ Sessão 7  → #1 e #2 (waterfall seletor + FCL)
✅ Sessão 8  → #3 (expansão scraper para 8 empresas)
✅ Sessão 9  → UX/performance/bug fix dashboard v6 + sidebar hover strip
→  Sessão 10 → #4 ou #5 (multi-empresa overlay ou heatmap setorial)
→  Sessão 11+→ #6 automação → #7 testes → #8 valuation via yfinance
```

---

### Sessão 7+8 — 2026-03-26 (Agente: Claude Sonnet 4.6)

**O que foi feito:**

**Sessão 7 — Waterfall com seletor de anos + FCL:**
- Waterfall YoY agora tem dois `st.selectbox` (Ano atual / Ano base) — não mais fixo no latest
- FCL (Free Cash Flow = FCO + FCI) adicionado: linha overlay roxa (dash dot) no gráfico DFC agrupado
- FCL incluído também no Excel de exportação (`build_excel`) como coluna separada

**Sessão 8 — Expansão da base de dados:**
- Rodado scraper para 8 novas empresas: LOCALIZA, EMBRAER, B3 S.A., NATURA, TOTVS, SUZANO PAPEL, GERDAU, RENNER
- DB expandido de 11 → 19 empresas com cobertura 2022-2025 completa
- Total de empresas no SQLite: 37 (19 com 4 anos, 1 com 3 anos, 16+ com 1 ano)
- `load_sectors()` corrigido: adicionado override para NATURA (CVM 24783) ausente da base analítica
  - NATURA &CO HOLDING (24783) ≠ NATURA COSMÉTICOS (19550) que está na base — são entidades distintas
- 19 empresas × 16 setores distintos — peer scatter funcional para todos

**Estado do banco (2026-03-26):**
```
19 empresas com 4 anos (2022-2025):
AMBEV · B3 · BRADESCO · ELETROBRAS · EMBRAER · EZ INC · GERDAU · HYPERA · IRB
ITAÚ UNIBANCO · LOCALIZA · NATURA · PETROBRAS · RENNER · SUZANO · TELEFÔNICA
TOTVS · VALE · WEG
```

**Caminho atualizado:**
```
✅ Sessão 7  → #1 e #2 (waterfall seletor + FCL)
✅ Sessão 8  → #3 (expansão scraper para 8 empresas)
→  Sessão 9  → #4 ou #5 (multi-empresa overlay ou heatmap setorial)
→  Sessão 10+→ #6 automação → #7 testes → #8 valuation via yfinance
```

---

### Sessão 5 — 2026-03-25 (Agente: Antigravity/Gemini)

**O que foi feito:**
- **Expansão do Dashboard (v5)**: Implementado módulo de **Comparação de Peers** (Comparativo setorial dinâmico).
- **Suíte de KPIs de Solvência**: Adicionados cartões de `Dívida/EBITDA` (via proxy de EBITDA) e `Liquidez Corrente`.
- **UX/UI Refinada**: Implementados `Modo Denso` (compactação visual), `Tooltips` explicativos e formatação contábil na tabela.
- **Fix de Exportação**: Resolvido bug de download do Excel adicionando `buf.seek(0)` e chaves de estado únicas no Streamlit.

**O que foi aprendido:**
- O cálculo de EBITDA via CVM precisa de proxies (`Resultado Bruto + Despesas Operacionais`) quando a depreciação não está explicitada de forma padronizada em todos os setores.
- O mapeamento setorial da base analítica é a chave para o "Peer Comparison" em tempo real.

---

### Sessão 4 — 2026-03-25 (Agente: Antigravity/Gemini)

**O que foi feito:**
- **Prioridade 6 e 7 (Dashboard & SQLite)**: Migração total da arquitetura para leitura direta de Banco de Dados SQLite (`cvm_financials.db`).
- **Dashboard Terminal (v4)**: Criado app Streamlit com visual de terminal internacional (Koyfin-like), 6 KPIs, gráficos trimestrais de 16 períodos (2Q22-4Q25) e exportador de 3 abas.
- **Correção Crítica de Dados**: Identificada a ausência de `STANDARD_NAME` para `Ativo Total` no banco; implementado cálculo dinâmico (`AC + ANC`).
- **Backfill Massivo**: Repovoado o banco com dados de 2022 a 2025 para garantir timelines contínuas sem quebras.

**O que foi aprendido:**
- A estrutura hierárquica da CVM (`CD_CONTA`) é mais confiável que o `STANDARD_NAME` para contas de balanço raiz (`1` e `2`).
- O SQLite permite performance de milissegundos no dashboard em comparação com o carregamento de arquivos Excel pesados.

---

### Sessão 3 — 2026-03-25 (Agente: Antigravity/Gemini)

**O que foi feito:**
- Conclusão da Prioridade 3 (Dicionário de Padronização) com sucesso.
- Criados `scripts/build_canonical_dict.py`, gerado o artefato `data/canonical_accounts.csv` (1.395 contas) e implementada a classe `AccountStandardizer` (`src/standardizer.py`).
- Integrado o `AccountStandardizer` na rotina de exportação do Excel em `scraper.py`, preenchendo a coluna `STANDARD_NAME`.
- Gerado um relatório/aba `PADRONIZACAO` contendo a estatística de assertividade do mapeamento.
- **Acordo do Roadmap**: Definida a prioridade de próximos passos com o João.

**O que foi aprendido sobre o projeto:**
- O Banco Central/CVM fornece planos de contas brutalmente diferentes para Comerciais vs Financeiras. A Prioridade 4 vai desarmar exatamente esse desafio testando bancos (Itaú).
- A cobertura de mapeamento para contas discricionárias na DFC pelo método indireto varia muito, mas as rubricas raiz da CVM sempre dão "match".

---

### Sessão 2 — 2026-03-25 (Agente: Antigravity/Gemini)

**O que foi feito:**
- Rodada a pipeline completa para Petrobras 2021–2025 (consolidado) → exit code 0, todos os testes de regressão passaram
- Leitura dos arquivos de referência em `entender_CD/`: plano de contas fixas DFP (3 tipos de empresa), metadados dos campos CVM, manual de envio
- Extração completa da hierarquia de CD_CONTA para `output/plano_contas.txt`
- Atualização do `MEMORIADASIA.md` com o conhecimento das contas CVM

**O que foi aprendido sobre o plano de contas CVM (Empresas Comerciais/Industriais):**

A estrutura de `CD_CONTA` é hierárquica, separada por ponto. O **primeiro dígito** identifica o bloco:

| Bloco | Demonstração | Exemplos |
|-------|-------------|---------|
| `1.xx` | BPA — Ativo | `1.01` Ativo Circ., `1.02` Ativo Não Circ. |
| `2.xx` | BPP — Passivo + PL | `2.01` Passivo Circ., `2.02` Passivo NC, `2.03` PL |
| `3.xx` | DRE | `3.01` Receita, `3.02` CPV, `3.03` Resultado Bruto |
| `4.xx` | DRA — Resultado Abrangente | `4.01` LL, `4.02` Outros Result. Abrangentes |
| `5.xx` | DMPL | `5.04.06` Dividendos, `5.04.01` Aumentos de Capital |
| `6.xx` | DFC (método indireto) | `6.01` Op., `6.02` Invest., `6.03` Financiamento |
| `7.xx` | DVA — Valor Adicionado | Não usado no pipeline atual |

**Contas relevantes para o pipeline:**

Contas-chave BPA (`ST_CONTA_FIXA = S` — sempre presentes):
- `1.01` → Ativo Circulante
- `1.01.01` → Caixa e Equivalentes de Caixa
- `1.02` → Ativo Não Circulante
- `1.02.03` → Imobilizado
- `1.02.04` → Intangível

Contas-chave BPP:
- `2.01.04` → Empréstimos e Financiamentos (Circulante)
- `2.02.01` → Empréstimos e Financiamentos (NC)
- `2.03` → Patrimônio Líquido (`2.03` ind. / consolidado tem `Patrimônio Líquido Consolidado`)
- `2.03.01` → Capital Social Realizado
- `2.03.05` → Lucros/Prejuízos Acumulados

Contas-chave DRE:
- `3.01` → Receita de Venda de Bens e/ou Serviços
- `3.02` → Custo dos Bens e/ou Serviços Vendidos (CPV)
- `3.03` → Resultado Bruto
- `3.04.01` → Despesas com Vendas
- `3.04.02` → Despesas Gerais e Administrativas
- `3.04.03` → Perdas pela Não Recuperabilidade de Ativos
- `3.06.01` → Receitas Financeiras
- `3.06.02` → Despesas Financeiras
- `3.08` → Imposto de Renda e CSLL
- `3.11` → Lucro/Prejuízo do Período (ind.) / `3.11` Lucro Consolidado
- `3.11.01` → Atribuído aos Controladores (consolidado)
- `3.11.02` → Atribuído a Não Controladores (consolidado)

Contas-chave DFC (método indireto — código usa `DFC_MI`):
- `6.01` → Caixa Líquido Atividades Operacionais
- `6.02` → Caixa Líquido Atividades de Investimento
- `6.03` → Caixa Líquido Atividades de Financiamento
- `6.05` → Aumento (Redução) de Caixa e Equivalentes

Contas-chave DMPL:
- `5.04.01` → Aumentos de Capital
- `5.04.06` → Dividendos
- `5.04.07` → Juros sobre Capital Próprio
- `5.05.01` → Lucro Líquido do Período

**Diferença Individual vs. Consolidado:**
- BPP individual: `2.03` = `Patrimônio Líquido`
- BPP consolidado: `2.03` = `Patrimônio Líquido Consolidado` + inclui `2.03.09` (Participação dos Acionistas Não Controladores)
- DRE consolidado: tem `3.11.01` e `3.11.02` (atribuição do lucro); individual só tem `3.11`

**Tipos de empresa têm planos diferentes:**
- `plano-contas-fixas-DFP/` → Comerciais/Industriais, Inst. Financeiras, Seguradoras
- A distinção importa porque **Bancos** (Financeiras) têm estrutura de DRE completamente diferente (contas `3.xx` com outro layout)
- O pipeline atual foi testado apenas com Petrobras (Industrial) — atenção ao rodar com Bancos ou Seguradoras

**Arquivos de referência em `entender_CD/`:**
- `plano-contas-fixas-DFP/` → 3 arquivos XLSX com o plano de contas fixas por tipo de empresa (Ind., Financeiras, Seguradoras)
- `plano-de-contas-fixas-DFP-ENET/` → versão alternativa dos mesmos arquivos (ENET = sistema CVM legado)
- `meta_dfp_cia_aberta_txt/` → metadados dos campos dos CSVs CVM (BPA, BPP, DRE, DFC_MD, DFC_MI, DMPL, DVA, DRA)
- `manual-de-envio-de-informacoes-periodicas-e-eventuais.pdf` → manual CVM completo
- `oc-sep-0621.pdf` → ofício circular CVM

**Resultado da execução de verificação (Petrobras 2021-2025 cons.):**
- Exit code 0, todos os testes de regressão passaram
- 8 QA issues logados (esperados): 4 coalesce + 1 TRIMESTRAL_NAO_DIVULGADO (2022) + 1 DFC_VALIDATION_FAILED (2023)
- Output: `output/PETROBRAS_financials.xlsx`

---

### Sessão 1 — 2026-03-25 (Agente: Antigravity/Gemini)

**O que foi feito:**
- Leitura completa de todos os módulos do projeto (`src/scraper.py`, `src/dictionary.py`, `src/utils.py`, `main.py`)
- Leitura de toda a documentação existente (`CONTEXT.md`, `README.md`, `docs/PROJECT_RULES.md`)
- Criação deste arquivo `MEMORIADASIA.md` como registro de memória entre agentes
- Atualização de `CONTEXT.md` e `README.md` para referenciar este arquivo

**O que foi aprendido sobre o projeto:**

- **Pipeline principal**: `main.py` → `CVMScraper` (em `src/scraper.py`) — extrai dados financeiros da CVM pública, processa com regras de QA, exporta Excel com abas BPA, BPP, DRE, DFC + abas de QA
- **Caso de teste**: Petrobras (PETR4) — usado para validar fechamentos de balanço, DFC standalone e consistência geral
- **Prioridades concluídas**: P1 (integridade contábil, periodização) e P2 (chave estável `LINE_ID_BASE`, base wide, `DS_CONTA_norm`, QA)
- **Prioridade pendente**: P3 — dicionário de contas para padronização de demonstrações financeiras (fora do escopo atual)
- **Motor principal**: `src/scraper.py` (~66KB) — contém toda a lógica de scraping, filtragem, consolidação, desambiguação e exportação
- **DFC standalone**: conversão de YTD para trimestral via `convert_dfc_ytd_to_standalone()`
- **QA automático**: validações obrigatórias incluem `LINE_ID_BASE` único, `DS_CONTA_norm` sem nulos, fechamento BPA/BPP, e DFC Q1+Q2+Q3+Q4=YYYY

**Estrutura do projeto:**
```
cvm_repots_capture/
├── main.py               # Entrypoint CLI (argparse)
├── src/
│   ├── scraper.py        # Motor principal (~66KB)
│   ├── dictionary.py     # Construtor de dicionário de contas
│   └── utils.py          # Normalização, LINE_ID_BASE
├── scripts/              # 16 scripts de verificação/debug
│   ├── validation/       # Scripts de QA
│   └── experiments/      # Métodos experimentais
├── data/input/           # CSVs e ZIPs brutos da CVM
├── output/               # Relatórios Excel e logs
├── docs/
│   └── PROJECT_RULES.md  # Convenções e regras
├── CONTEXT.md            # Documentação de domínio e técnica
├── README.md             # Como rodar
└── MEMORIADASIA.md       # Este arquivo
```

**Regras de código identificadas:**
- `snake_case` para variáveis e nomes de arquivos
- Bloco `USER CONFIGURATION` no topo de cada script executável
- `LINE_ID_BASE` como identificador canônico (nunca `LINE_ID`)
- Scripts pontuais em `scripts/`, módulos reutilizáveis em `src/`

---

## Sugestões Registradas

*Nenhuma sugestão registrada até o momento.*

---

## Decisões Tomadas pelo João

| Data | Decisão |
|------|---------|
| 2026-03-25 | João aprovou a conclusão da Prioridade 3 e definiu a ordem do Roadmap final: P4 (Integração de Bancos), P5 (Análise/Indicadores), P6 (Dashboard Visual) e P7 (Massificação via Banco de Dados SQLite). |
| 2026-03-25 | Criação do `MEMORIADASIA.md` como registro de memória entre agentes de IA |

---

## Contexto Técnico para Agentes Futuros

### Coisas que NÃO são óbvias no código

1. **Scraper monolítico**: O `src/scraper.py` tem ~66KB e concentra toda a lógica de extração, processamento, validação e exportação dentro da classe `CVMScraper`. Não se assuste com o tamanho — é intencional por ora.

2. **DFC não é cumulativa**: O dado bruto da CVM vem em formato YTD, mas o output final deve ter trimestres standalone. A conversão é feita internamente. Se Q1+Q2+Q3+Q4 ≠ YYYY, o QA captura.

3. **`LINE_ID_BASE` ≠ `LINE_ID`**: O projeto usa apenas `LINE_ID_BASE`. Se você vir `LINE_ID` sem o sufixo `_BASE`, trate como bug ou legado.

4. **Sufixos artificiais proibidos**: O output final NÃO deve usar `#1`, `#2` etc. Isso transforma ID de conta em ID de registro — é regressão. O `CONTEXT.md` é explícito sobre isso.

5. **Prioridade 3 não existe no código**: O dicionário de contas para padronização é um objetivo futuro. Não implemente nada relacionado sem aprovação explícita do João.

6. **USER CONFIGURATION obrigatório**: Todo script executável precisa de um bloco `USER CONFIGURATION` no topo (ver `docs/PROJECT_RULES.md`). Não coloque caminhos hardcoded no meio do código.

### Ordem de leitura recomendada para agentes

1. `MEMORIADASIA.md` (este arquivo) — o que já foi feito e decidido
2. `CONTEXT.md` — entendimento completo do domínio e código
3. `README.md` — como rodar
4. `src/scraper.py` — o motor principal
5. O módulo específico que precisa ser alterado

### Como atualizar este arquivo

Ao final de cada sessão de trabalho, adicione uma nova entrada em
"Registro de Sessões" com:
- Data e identificação do agente
- O que foi feito
- O que foi aprendido de novo
- Sugestões dadas e decisões tomadas
- Qualquer contexto relevante para o próximo agente

### Sessao 10 - 2026-03-26 (Agente: Codex GPT-5)

**O que foi feito:**
- Criado bootstrap rapido para Windows em `scripts/bootstrap_windows.ps1`.
- O bootstrap agora instala Python 3.11 via `winget` quando necessario, cria `.venv`, instala `requirements.txt` e executa `scripts/smoke_validate.py --skip-compile`.
- Fluxo de verificacao foi normalizado para `output/reports` com suporte a `--xlsx` nos scripts:
  - `scripts/verify_consolidation.py`
  - `scripts/quick_verify.py`
  - `scripts/verify_line_id_base.py`
  - `scripts/final_verification.py`
- `scripts/gerar_base_analitica.py` foi ajustado para resolver arquivos de metadados via `data/metadata` a partir da raiz do repo.
- `src/scraper.py` foi alinhado para:
  - output padrao em `output/reports`;
  - `data_dir` padrao em `data/input`;
  - log de falhas de batch em `output/logs/batch_errors.log`.
- Documentacao operacional foi atualizada em:
  - `README.md`
  - `dashboard/README.md`
  - `CONTEXT.md` (nova secao de bootstrap rapido)

**Decisao do usuario nesta sessao:**
- Solicitar preparo de bootstrap rapido para instalar Python + dependencias e atualizar a documentacao de contexto/memoria.

**Riscos/observacoes tecnicas:**
- Ambiente local usado pelo agente nao tinha runtime Python ativo (`python` ausente e `py.exe` sem versao instalada), por isso o bootstrap foi preparado mas nao executado no proprio ambiente.
- Alguns arquivos antigos estao com encoding legado (mojibake na exibicao do terminal). Para evitar perda de historico, as atualizacoes foram adicionadas sem reescrita total desses arquivos.
