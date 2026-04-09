# V2 Phase 2 - Primeiro Slice Web

## Objetivo

Entregar o primeiro fluxo web funcional da V2 em `apps/web`, consumindo apenas a API read-only em `apps/api`.

Escopo fechado original desta fase:
- `/`
- `/empresas`
- `/empresas/[cd_cvm]`

O objetivo nao e cobrir o sitemap inteiro. O objetivo e fechar o primeiro fluxo util:

`Home -> Empresas -> Empresa`

Pacote aditivo entregue depois do slice inicial:
- `/comparar`
- `/setores`
- `/setores/[slug]`

## Stack

- `Next.js 16`
- `App Router`
- `TypeScript`
- `Tailwind CSS`
- `shadcn/ui`
- `Playwright` para smoke e2e

## Fronteira tecnica

- O frontend fala apenas com a API V2.
- O frontend nao acessa `src/read_service.py` diretamente.
- O frontend nao acessa banco nem arquivos locais.
- `API_BASE_URL` define o host da API.
- `apps/web/app/api/company-search/route.ts` existe apenas para o autocomplete da home.

## Rotas entregues

### `/`

- hero com busca principal
- autocomplete de empresas
- CTA para o diretorio publico
- sinais de saude da API

### `/empresas`

- busca por `busca`
- filtro de setor por `setor`
- paginacao por `pagina`
- lista de empresas com nome, ticker, setor e anos disponiveis

### `/empresas/[cd_cvm]`

- header da empresa
- download do workbook Excel completo da empresa
- seletor de anos em URL
- aba `visao-geral`
- aba `demonstracoes`
- `stmt` em URL com `DRE`, `BPA`, `BPP`, `DFC`

### `/comparar`

- selecao de empresas por busca e sugestoes rapidas
- download em lote `.zip` com um `.xlsx` por empresa selecionada
- deep-link publico por `ids` e `anos`
- periodo anual resolvido por interseccao entre empresas
- tabela comparativa de KPIs com base de referencia na primeira empresa
- fallback explicito para ausencia de anos em comum, erro parcial e IDs invalidos

### `/setores`

- hub setorial com cards de descoberta
- snapshot por setor com `ROE`, `Margem EBIT` e `Margem Liquida`
- navegacao principal ativa em header, footer e home

### `/setores/[slug]`

- detalhe setorial com breadcrumbs e CTA vindo da pagina da empresa
- seletor anual por `ano`
- aba `visao-geral`
- aba `empresas`
- fallback para `slug` inexistente via `not-found`
- `ano` invalido ou ausente cai para o ano mais recente disponivel

## Query params publicos

### Hub

- `/empresas?busca=&setor=&pagina=`

Mapeamento interno:
- `busca -> search`
- `setor -> sector`
- `pagina -> page`

### Detalhe

- `/empresas/[cd_cvm]?anos=2023,2024&aba=visao-geral|demonstracoes&stmt=DRE|BPA|BPP|DFC`

Defaults:
- `aba=visao-geral`
- `stmt=DRE`
- `anos`: 3 anos mais recentes, ou menos se a empresa tiver menos historico

### Compare

- `/comparar?ids=9512,1179&anos=2023,2024`

Defaults:
- `ids`: vazio ate o usuario montar a selecao inicial
- `anos`: interseccao mais recente resolvida pelo frontend quando a URL nao informar um periodo valido

### Setores

- `/setores/[slug]?ano=2024&aba=visao-geral|empresas`

Defaults:
- `ano`: periodo mais recente disponivel do setor
- `aba=visao-geral`

## Comandos locais

API:

```powershell
uvicorn apps.api.app.main:app --reload
```

Web:

```powershell
cd apps/web
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Validacao

```powershell
pytest tests/ -q
pytest apps/api/tests -q

cd apps/web
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

## O que fica para a proxima fase

- `/kpis`
- `/macro`
- deploy remoto de preview
- integracao com PostgreSQL remoto na camada web
