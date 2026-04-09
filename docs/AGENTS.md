# AGENTS.md - Estado Atual e Historico de Sessoes

> **Para agentes de IA.** Estado atual no topo; historico abaixo.
> Antes de modificar o codigo, leia `AGENTS.md`, este arquivo e `docs/CONTEXT.md`.
> Apos concluir, atualize a secao "Estado Atual" e adicione uma entrada de sessao quando fizer sentido.
> Backlog oficial: `GitHub Issues`. Este arquivo nao e uma lista viva de tarefas.

---

## Estado Atual (2026-04-09)

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
- Endpoints iniciais: `health`, `companies`, `companies/filters`, `company detail`, `years`, `statements`, `kpis`, `refresh-status`, `base-health`

### V2 Web
- `apps/web` existe como o primeiro slice web da V2
- Stack: `Next.js 16.2.2` + `App Router` + `TypeScript` + `Tailwind v4` + `@base-ui/react 1.3.0`
- Sistema de icones: `Material Symbols Outlined` weight 200 (Google Fonts)
- Biblioteca de componentes: 21st.dev via shadcn CLI (coss.com, reaviz, isaiahbjork, larsen66, moumensoliman)
- Providers globais: `ThemeProvider` (next-themes) + `TooltipProvider` (radix) em `components/providers.tsx`
- Rotas de produto: `/`, `/empresas`, `/empresas/[cd_cvm]`
- Rota de tooling: `/design-system` — showcase de tokens e componentes (24 secoes)
- Cores chart: OkLch com ~72° de espacamento, chroma real em light e dark mode
- O frontend consome somente a API V2; nao acessa `src/` nem o banco diretamente

### Testes
- `pytest tests/ -q` continua sendo a validacao mais confiavel da V1
- `pytest apps/api/tests -q` cobre o contrato HTTP da Fase 1 da V2
- `apps/web` valida com `npm run lint`, `npm run typecheck`, `npm run build` e `npm run test:e2e`

### Governanca de Trabalho
- `GitHub Issues` passa a ser a fonte oficial do backlog e do status do trabalho
- `AGENTS.md` na raiz define o contrato operacional `issue -> branch -> PR -> merge`
- O repositorio passa a operar com tres lanes oficiais:
  `lane:frontend`, `lane:backend` e `lane:ops-quality`
- O repo raiz permanece estavel em `master`; cada task executavel roda em
  `.claude/worktrees/<lane>/<issue-number>-<slug>/`
- A regra oficial passa a ser `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`
- Trabalho paralelo agora e regido por `owner atual`, `write-set esperado` e
  classificacao `risk:*` declarados em cada task
- `risk:shared` e `risk:contract-sensitive` exigem PR em draft na abertura
- Paths sensiveis passam a ser governados por
  `.github/guardrails/path-policy.json`
- Interfaces publicas ficam `additive-only` por default durante execucao
  simultanea
- Delegacao entre lanes passa a exigir child task formal com `Task mae`,
  `Lane solicitante`, `Tasks filhas` e `Criterio de consumo`
- O inicio de cada chat executavel agora exige triagem de tasks abertas da
  propria lane, child tasks recebidas/solicitadas e PRs abertas aguardando
  consumo
- `status:awaiting-consumption` passa a representar task mae entregue por outra
  lane, mas ainda nao consumida pela lane solicitante
- O fechamento da task passa a exigir checks verdes e merge confirmado; PR
  aberta nao conta como concluido
- `docs/STUDENT_PACK_PLAN.md` deixa de espelhar task-by-task e passa a apontar para milestone + epics + filtros de issues
- `docs/AGENTS.md` permanece apenas como estado atual e historico de sessoes

### Pendencias Tecnicas Atuais
- Validacao contra PostgreSQL real ainda depende de `DATABASE_URL` valido
- Deploy de preview da V2 ainda nao foi iniciado
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

### Sessao 37 - 2026-04-09 (child tasks formais entre lanes)
- Delegacao entre lanes passa a exigir child task formal em GitHub Issue, nao
  pedido informal no chat
- `Task mae`, `Lane solicitante`, `Tasks filhas` e `Criterio de consumo`
  passam a ser metadados operacionais da governanca
- A task mae deve ficar `status:blocked` enquanto a child task estiver aberta e
  `status:awaiting-consumption` ate a lane solicitante consumir a entrega
- O inicio de cada chat executavel passa a exigir checagem de tasks abertas da
  propria lane, child tasks recebidas/solicitadas e PRs abertas ligadas a essas
  issues
- O template de task e o guardrail da PR passam a suportar child tasks entre
  lanes

### Sessao 36 - 2026-04-08 (fechamento por checks verdes e merge confirmado)
- `scripts/pr_complete.ps1` passa a ser o helper recomendado para concluir uma
  task com PR
- A governanca passa a exigir checks verdes, merge confirmado, issue fechada e
  branch remota removida quando aplicavel
- Templates de task e PR deixam explicito que PR aberta nao significa task
  concluida

### Sessao 35 - 2026-04-08 (fix no helper de remocao de worktree)
- `scripts/worktree_remove.ps1` deixa de quebrar quando o merge-check local
  retorna vazio
- sem `-Force`, o helper agora orienta atualizar `master` local ou usar
  `-Force` quando o clone ainda nao enxerga o merge remoto

### Sessao 34 - 2026-04-08 (lanes oficiais, worktrees e critical paths)
- O repositorio passa a operar com tres lanes oficiais:
  `lane:frontend`, `lane:backend` e `lane:ops-quality`
- Toda task executavel passa a exigir `Lane oficial` e `Workspace da task`
- A regra de execucao vira `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`
- O repo raiz permanece em `master`; worktrees oficiais vivem em
  `.claude/worktrees/<lane>/<issue-number>-<slug>/`
- `.github/guardrails/path-policy.json` passa a versionar `shared-governance`,
  `critical-bootstrap`, `critical-runtime` e `critical-contract`
- O guardrail de PR passa a validar lane, workspace, paths criticos, risco
  minimo, write-set coberto e unicidade de PR por task
- Scripts `worktree_create.ps1`, `worktree_status.ps1` e
  `worktree_remove.ps1` passam a apoiar o fluxo local

### Sessao 33 - 2026-04-08 (smoke local da V1 e bootstrap do desktop)
- `desktop/cvm_pyqt_app.py` passa a inserir a raiz do projeto em `sys.path`,
  permitindo execucao tanto por `python -m desktop.cvm_pyqt_app` quanto por
  `python desktop/cvm_pyqt_app.py`
- `README.md`, `COMO_RODAR.md` e `CLAUDE.md` passam a preferir a execucao por
  modulo para o app desktop
- Smoke local revalidado com `runtime_doctor.py`, `smoke_validate.py`,
  `db_portability_smoke.py --write-check`, desktop em modo offscreen e
  Streamlit headless com resposta HTTP 200
- SQLite local confirmado; PostgreSQL real continua pendente por ausencia de
  `DATABASE_URL`

### Sessao 32 - 2026-04-08 (protocolo de trabalho paralelo agnostico a IA)
- Nova familia de labels `risk:*` criada no GitHub: `risk:safe`, `risk:shared`,
  `risk:contract-sensitive`
- Template de task passa a exigir `Owner atual`, `Write-set esperado` e
  `Classificacao de risco`
- PR template passa a registrar risco, write-set e politica de compatibilidade
- Guardrail de PR passa a validar labels `status:*`, `priority:*`, `area:*`,
  `risk:*` e a presenca de metadados de ownership/write-set na issue
- PRs de tasks `risk:shared` e `risk:contract-sensitive` precisam abrir em draft
- O protocolo passa a ser por task e write-set, nao por identidade da IA

### Sessao 31 - 2026-04-08 (governanca issue-first no GitHub)
- `AGENTS.md` criado na raiz como contrato operacional para agentes e contribuidores
- `.github/ISSUE_TEMPLATE/` criado com forms de `epic` e `task`; blank issues desabilitadas
- `.github/PULL_REQUEST_TEMPLATE.md` criado com referencia obrigatoria a issue
- `.github/workflows/pr-issue-guardrails.yml` criado para validar branch `task/<issue-number>-<slug>`, `Closes #<issue>` e label `kind:task`
- `CLAUDE.md` atualizado para abandonar `tasks/todo.md` e seguir fluxo issue-first
- `docs/STUDENT_PACK_PLAN.md` atualizado para apontar para milestone/epics/tasks do GitHub em vez de espelhar backlog diario
- Labels operacionais criadas no GitHub: `kind:*`, `status:*`, `priority:*`, `area:*`
- Triage inicial aplicada aos issues `#2` a `#14`, com `#12` fechado como concluido por evidencia ja entregue

### Sessao 30 - 2026-04-08 (design system + biblioteca de componentes V2 web)
- `/design-system` criada como showcase de tokens e componentes (24 secoes, sidebar nav)
- 20+ componentes instalados via 21st.dev shadcn CLI: coss.com (tabs, toolbar, field, textarea, checkbox, accordion, calendar), reaviz (charts), isaiahbjork (3 tabelas), larsen66 (tooltip, toggle-theme, feature-carousel), moumensoliman (delete-button), shadcnspace (switch), easemize (mobile-menu), Shatlyk1011 (animated-dropdown)
- `@base-ui/react` confirmado como headless primitive; Radix coexiste sem conflito
- `components/providers.tsx` criado: `ThemeProvider` (next-themes) + `TooltipProvider` (radix)
- `suppressHydrationWarning` adicionado ao `<html>` para compatibilidade com next-themes SSR
- Tokens de cor dos charts atualizados para OkLch com hues espacados ~72° e chroma real em dark mode
- Footer sitemap reestruturado com 4 colunas e link "Design System" em Recursos
- 8 erros TypeScript corrigidos nos componentes de terceiros instalados
- Zero erros TypeScript; zero runtime errors no `/design-system`

### Sessao 28 - 2026-04-08 (Fase 1 V2 backend-first)
- `apps/api` criado como API `FastAPI` read-only em cima de `src/read_service.py`
- Rotas de Fase 1 entregues: `health`, `companies`, `company detail`, `years`, `statements`, `kpis`, `refresh-status`, `base-health`
- `apps/api/tests` adicionados para contratos HTTP e serializacao
- `.github/workflows/ci.yml` criado para rodar V1 + API
- `docs/V2_PHASE1_BACKEND.md` e `docs/V2_API_CONTRACT.md` criados
- `docs/WEBAPP_TRANSFORMATION_PLAN.md` refinado para `backend-first`

### Sessao 29 - 2026-04-08 (Fase 2 V2 web slice 1)
- `apps/web` criado em `Next.js 16` com `App Router`, `TypeScript`, `Tailwind` e `shadcn`
- Rotas entregues: `/`, `/empresas`, `/empresas/[cd_cvm]`
- Home recebeu busca principal com autocomplete via route handler interno
- Hub de empresas recebeu busca, filtro de setor e paginacao orientados por URL
- Detalhe da empresa recebeu `Visao Geral` e `Demonstracoes` (`DRE`, `BPA`, `BPP`, `DFC`)
- CI passou a incluir `lint`, `typecheck` e `build` do `apps/web`

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
