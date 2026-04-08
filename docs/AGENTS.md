# AGENTS.md - Estado Atual e Historico de Sessoes

> **Para agentes de IA.** Estado atual no topo; historico abaixo.
> Antes de modificar o codigo, leia este arquivo e `docs/CONTEXT.md`.
> Apos concluir, atualize a secao "Estado Atual" e adicione uma entrada de sessao quando fizer sentido.

---

## Estado Atual (2026-04-08)

### Dashboard
- **3 abas renderizadas** em `dashboard/app.py`: `Visao Geral`, `Demonstracoes`, `Download`
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

### V2 Backend
- `apps/api` existe como a Fase 1 da V2
- API `FastAPI` read-only, thin wrapper sobre `src/read_service.py`
- Endpoints iniciais: `health`, `companies`, `company detail`, `years`, `statements`, `kpis`, `refresh-status`, `base-health`
- `apps/web` ainda nao foi implementado; entra na fase seguinte

### Testes
- **141 pytest passing** (`pytest tests/ -q` + `pytest apps/api/tests -q`, last confirmed)
- `pytest tests/ -q` continua sendo a validacao mais confiavel da V1
- `pytest apps/api/tests -q` cobre o contrato HTTP da Fase 1 da V2

### Issues Abertas
- Validacao contra PostgreSQL real ainda depende de `DATABASE_URL` valido
- `apps/web` ainda nao foi iniciado
- Streamlit Cloud deploy pendente
- P10 (bancos financeiros: Itau, Bradesco) nao iniciado

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
| `apps/api` consome `src/read_service.py` | evita reimplementar SQL e KPI logic no adaptador HTTP |

---

## Sessoes Recentes

### Sessao 28 - 2026-04-08 (Fase 1 V2 backend-first)
- `apps/api` criado como API `FastAPI` read-only em cima de `src/read_service.py`
- Rotas de Fase 1 entregues: `health`, `companies`, `company detail`, `years`, `statements`, `kpis`, `refresh-status`, `base-health`
- `apps/api/tests` adicionados para contratos HTTP e serializacao
- `.github/workflows/ci.yml` criado para rodar V1 + API
- `docs/V2_PHASE1_BACKEND.md` e `docs/V2_API_CONTRACT.md` criados
- `docs/WEBAPP_TRANSFORMATION_PLAN.md` refinado para `backend-first`

### Sessao 27 - 2026-04-07 (roadmap da transformacao web + aprendizado)
- `docs/WEBAPP_TRANSFORMATION_PLAN.md` criado para registrar a execucao da V1 para a V2
- O repo passa a registrar explicitamente proposito duplo: sistema operacional atual + trilha de aprendizado por construcao
- Primeiro slice da V2 documentado como `Next.js` read-only consumindo API `FastAPI` read-only
- Deploy inicial assumido como gerenciado e separado por camada; `Nginx` segue opcional e tardio
- `README.md` e `docs/STUDENT_PACK_PLAN.md` atualizados para apontar para o roadmap da transformacao web

### Sessao 26 - 2026-04-07 (ADR da stack V2 com Student Pack)
- `docs/decisions/0002-student-pack-v2-stack.md` criado para congelar a recomendacao da V2
- Stack recomendada registrada como `Next.js` + `FastAPI/Uvicorn` + `PostgreSQL` + `Ubuntu Linux`
- `Nginx` registrado como opcional no inicio, apenas para self-hosting/reverse proxy
- Correcao documental: evitar citar `Copilot Pro`; usar formulacao neutra `GitHub Copilot` e revalidar o beneficio vigente na pagina oficial
- `docs/STUDENT_PACK_PLAN.md` atualizado para apontar para o ADR 0002

### Sessao 25 - 2026-04-06 (docs cleanup)
- `COMO_RODAR.md` e `docs/AGENTS.md` alinhados ao fluxo atual do repo
- Fluxo principal reforcado como `setup_db.py` -> `setup_companies_table.py` -> `cvm_pyqt_app.py` -> `dashboard/app.py`
- Estado atual mantido curto e orientado ao que esta realmente ativo hoje

### Sessao 24 - 2026-04-05 (student pack roadmap)
- `docs/STUDENT_PACK_PLAN.md` criado como documento-base para registrar beneficios do GitHub Student Pack e os proximos 60 dias
- Roadmap consolidado em produtividade, cloud, observabilidade/qualidade e descoberta da V2
- Backlog do GitHub planejado em torno de 4 epicos: ativacao do Pack, estabilizacao da stack atual, observabilidade/qualidade e descoberta da V2
- Milestone `Student Pack 60 dias` criado no GitHub com issues `#2` a `#14` cobrindo epicos e fases do plano

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

---

> **Historico completo (sessoes 1-21):** consulte `git log --oneline` ou arquivos arquivados em `archive/` se existirem.
