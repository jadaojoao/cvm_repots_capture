# AGENTS.md - Estado Atual e Historico de Sessoes

> **Para agentes de IA.** Estado atual no topo; historico abaixo.
> Antes de modificar o codigo, leia este arquivo e `docs/CONTEXT.md`.
> Apos concluir, atualize a secao "Estado Atual" e adicione uma entrada de sessao quando fizer sentido.

---

## Estado Atual (2026-04-06)

### Dashboard
- **3 abas renderizadas** em `dashboard/app.py`:
  `Visao Geral`, `Demonstracoes`, `Download`
- `dashboard/app.py` atua como orquestrador read-only
- `dashboard/components/search_bar.py` controla busca de empresa e selecao de anos
- `dashboard/tabs/visao_geral.py`, `dashboard/tabs/demonstracoes.py` e `dashboard/tabs/download.py` sao os tabs ativos
- Atualizacao de dados nao acontece no Streamlit; ela pertence ao app PyQt6 e aos scripts

### Banco de Dados
- **449 empresas**, 1,735,340 registros, 2022-2025 (last confirmed)
- SQLite local: `data/db/cvm_financials.db` (WAL mode)
- Ticker map central em `src/ticker_map.py`
- Tabelas: `financial_reports` (UPPER_CASE), `companies`, `account_names` (snake_case)

### App Desktop
- `cvm_pyqt_app.py` e a interface operacional principal
- Ranking inteligente: 40% market cap + 60% liquidez, combinado com desatualizacao
- Paralelismo configuravel 2-8 workers, barra de progresso total e bloco "Saude da Base"

### Testes
- **114 pytest passing** (`pytest tests/ -v`, last confirmed)
- `pytest tests/ -v` e a validacao mais confiavel do fluxo atual

### Issues Abertas
- Supabase PostgreSQL nao deployado em producao
- Streamlit Cloud deploy pendente
- P10 (bancos financeiros: Itau, Bradesco) nao iniciado
- `export_parquet.py` nao criado

---

## Decisoes Tecnicas Nao-Obvias

| Decisao | Razao |
|---------|-------|
| `int(year)` antes de param SQLite | numpy int64 falha silenciosamente |
| yfinance `dividendYield` ja em % | nao multiplicar por 100 |
| SQLAlchemy IN clause: `bindparam("x", expanding=True)` | listas como params SQL |
| `_upsert_company_metadata`: INSERT OR IGNORE + UPDATE | preserva CNPJ/ticker preenchidos por `setup_companies_table` |
| `st.components.v1.html()` para JS | `st.markdown` nao executa `<script>` |
| `archive/` na raiz | evita misturar scripts antigos com scripts ativos |
| `fillna("")` antes de `pivot_table` | evita perda silenciosa de linhas com `STANDARD_NAME` nulo |

---

## Sessoes Recentes

### Sessao 26 - 2026-04-07 (ADR da stack V2 com Student Pack)
- `docs/decisions/0002-student-pack-v2-stack.md` criado para congelar a recomendacao da V2
- Stack recomendada registrada como `Next.js` + `FastAPI/Uvicorn` + `PostgreSQL` + `Ubuntu Linux`
- `Nginx` registrado como opcional no inicio, apenas para self-hosting/reverse proxy
- Correcao documental: evitar citar `Copilot Pro`; usar formulacao neutra `GitHub Copilot` e revalidar o beneficio vigente na pagina oficial
- `docs/STUDENT_PACK_PLAN.md` atualizado para apontar para o ADR 0002

### Sessao 27 - 2026-04-07 (roadmap da transformacao web + aprendizado)
- `docs/WEBAPP_TRANSFORMATION_PLAN.md` criado para registrar a execucao da V1 para a V2
- O repo passa a registrar explicitamente proposito duplo: sistema operacional atual + trilha de aprendizado por construcao
- Primeiro slice da V2 documentado como `Next.js` read-only consumindo API `FastAPI` read-only
- Deploy inicial assumido como gerenciado e separado por camada; `Nginx` segue opcional e tardio
- `README.md` e `docs/STUDENT_PACK_PLAN.md` atualizados para apontar para o roadmap da transformacao web

### Sessao 24 - 2026-04-05 (student pack roadmap)
- `docs/STUDENT_PACK_PLAN.md` criado como documento-base para registrar beneficios do GitHub Student Pack e os proximos 60 dias
- Roadmap consolidado em produtividade, cloud, observabilidade/qualidade e descoberta da V2
- Backlog do GitHub planejado em torno de 4 epicos: ativacao do Pack, estabilizacao da stack atual, observabilidade/qualidade e descoberta da V2
- Milestone `Student Pack 60 dias` criado no GitHub com issues `#2` a `#14` cobrindo epicos e fases do plano

### Sessao 25 - 2026-04-06 (docs cleanup)
- `COMO_RODAR.md` e `docs/AGENTS.md` alinhados ao fluxo atual do repo
- Fluxo principal reforcado como `setup_db.py` -> `setup_companies_table.py` -> `cvm_pyqt_app.py` -> `dashboard/app.py`
- Estado atual mantido curto e orientado ao que esta realmente ativo hoje

### Sessao 23 - 2026-04-05 (docs alinhados ao estado real)
- `README.md`, `docs/CONTEXT.md` e `COMO_RODAR.md` atualizados para refletir o fluxo atual
- `docs/AGENTS.md` atualizado para refletir o dashboard read-only de 3 abas
- Fluxo principal documentado como `setup_db.py` -> `setup_companies_table.py` -> `cvm_pyqt_app.py` -> `dashboard/app.py`
- Referencias antigas ao dashboard de 9 abas foram removidas do estado atual

### Sessao 22 - 2026-04-01 (doc-architect overhaul)
- Full audit + cleanup: ~41 scripts arquivados em `archive/`, `pytest.ini` criado, wrappers legados removidos
- Docs reorganizados: `CONTEXT.md` consolidado em `docs/CONTEXT.md`; memoria/sessoes consolidadas em `docs/AGENTS.md`; `AUDIT.md` movido para `docs/`
- Raiz limpa: apenas `README.md`, `CLAUDE.md`, `COMO_RODAR.md` como arquivos `.md` principais
- `scripts/sync_docs_check.py` criado + lembretes de sincronizacao de docs

### Sessoes 18-21 - 2026-03-28 (UI overhaul + novos tabs)
- Historicamente, houve uma fase com dashboard maior e varios tabs adicionais
- Parte dessa descricao ficou stale nos docs; o estado atual deve ser lido a partir da secao "Estado Atual" no topo
- Commits desse periodo continuam relevantes como historico de design/UI, nao como retrato do app atual

### Sessao 17 - 2026-04-01 (hardening do Updater)
- Contrato unificado do scraper com payload por empresa
- Retry + backoff por empresa para `OperationalError` sem derrubar lote
- Hardening de escrita em banco (`src/database.py`) com retry `to_sql` para SQLite
- Sync deterministico em `company_refresh_status`
- Logging com timestamp e traceback em `output/logs/updater_worker_errors.log`
- Rotacao inteligente da lista com penalizacao/cooldown para empresas recem-atualizadas
- Bloco "Saude da Base" no PyQt: cobertura global/por ano, ETA com confianca, top empresas defasadas

---

> **Historico completo (sessoes 1-16):** consulte `git log --oneline` ou arquivos arquivados em `archive/` se existirem.
