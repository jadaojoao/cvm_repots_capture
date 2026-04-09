# Interface Map — Frontend routes x API endpoints

**Leitura obrigatória antes de tocar `apps/web` ou `apps/api`.**

Este documento é a fonte de verdade sobre quais rotas o frontend tem, qual é o
status de cada uma, e quais endpoints de API cada rota consome. Qualquer IA ou
pessoa que trabalhe em qualquer uma das duas áreas deve atualizar este arquivo
**antes** de começar a implementação.

> Contratos HTTP detalhados: `docs/V2_API_CONTRACT.md`
> Hierarquia de rotas e IA de produto: `docs/SITEMAP.MD`
> Requisitos de fase e scope: `docs/V2_PHASE2_WEB_SLICE.md`

---

## Como manter este documento

- **Nova rota no frontend**: adicione a seção, marque como `em desenvolvimento`,
  liste os endpoints necessários. Se algum não existir ainda, registre em
  [Pendências de backend](#pendencias-de-backend).
- **Novo endpoint no backend**: adicione na [tabela inversa](#tabela-inversa-endpoint--rotas-que-o-usam).
  Verifique se alguma rota em _Pendências_ esperava por ele e atualize o status.
- **Rota vai ao ar**: mude o status de `em desenvolvimento` para `live`.
- **Endpoint alterado ou removido**: verifique a tabela inversa, atualize todas as
  rotas afetadas, registre breaking change no PR.

---

## Rotas do frontend

### PG-01 — `/` (Home) `live`

**Objetivo**: roteador de entrada — leva o usuário ao caminho de análise mais curto.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /health` | — | Trust strip / sinal de saúde da API |
| `GET /companies` | `page=1&page_size=8` | Sugestões rápidas de empresas na home |

**Rota interna Next.js**:
- `GET /api/company-search?q=<termo>` → chama `GET /companies` com `search=q` e
  retorna até 6 itens para o autocomplete do hero.

---

### PG-02 — `/empresas` (Companies Hub) `live`

**Objetivo**: descoberta e seleção de empresa por busca e filtro de setor.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies` | `search=`, `sector=`, `page=`, `page_size=` | Lista paginada de empresas |
| `GET /companies/filters` | — | Opções de setor para o filtro |

**Query params públicos da rota**: `?busca=&setor=&pagina=`

---

### PG-03 — `/empresas/[cd_cvm]` (Company Detail) `live`

**Objetivo**: análise completa de uma empresa — KPIs, demonstrações e contexto.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies/{cd_cvm}` | — | Metadados da empresa (header) |
| `GET /companies/{cd_cvm}/years` | — | Anos disponíveis (seletor de período) |
| `GET /companies/{cd_cvm}/statements` | `stmt=DRE\|BPA\|BPP\|DFC`, `years=2023,2024` | Aba Demonstrações |
| `GET /companies/{cd_cvm}/kpis` | `years=2023,2024` | Aba Visão Geral |

**Query params públicos da rota**: `?anos=2023,2024&aba=visao-geral\|demonstracoes&stmt=DRE\|BPA\|BPP\|DFC`

---

### PG-04 — `/comparar` (Compare) `em desenvolvimento`

**Objetivo**: comparação lado a lado entre ao menos 2 empresas com base em KPIs.

**Status**: componentes, data layer e link de navegação existem. Falta validação
E2E end-to-end e smoke do fluxo completo.

**Não requer novos endpoints** — agrega chamadas existentes em paralelo.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies` | `page=1&page_size=8` | Sugestões rápidas de empresas no seletor |
| `GET /companies/{cd_cvm}` | — | Metadados de cada empresa selecionada (paralelo) |
| `GET /companies/{cd_cvm}/years` | — | Anos disponíveis por empresa (paralelo) |
| `GET /companies/{cd_cvm}/kpis` | `years=<intersecção>` | KPI bundles por empresa (paralelo) |

**Query params públicos da rota**: `?ids=cd_cvm1,cd_cvm2,...&anos=2022,2023`

**Arquivos relevantes**:
- `apps/web/app/comparar/page.tsx` — page component
- `apps/web/lib/compare-page-data.ts` — orquestração das chamadas paralelas
- `apps/web/lib/compare-utils.ts` — helpers de interseção de anos e montagem de linhas
- `apps/web/components/compare/` — CompareSelector, CompareKpiTable, CompareTracker

---

### PG-05 — `/setores` (Sectors Hub) `planejado`

**Objetivo**: descoberta de setores com ranking de KPIs agregados.

**Status**: não iniciado. **Aguarda endpoints de backend** (ver Pendências).

**Endpoints necessários (não existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /sectors` | Lista de setores com slug, nome, contagem de empresas, KPIs médios (ROE, margem, etc.) |

---

### PG-06 — `/setores/[slug]` (Sector Detail) `planejado`

**Objetivo**: análise profunda de um setor — empresas do setor, ranking de KPIs, contexto.

**Status**: não iniciado. **Aguarda endpoints de backend** (ver Pendências).

**Endpoints necessários (não existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /sectors/{slug}` | Metadados do setor + lista de empresas + KPIs agregados por ano |

---

### PG-07 — `/kpis` (KPI Hub) `planejado`

**Objetivo**: catálogo de KPIs com definições e top performers.

**Status**: não iniciado. **Aguarda endpoints de backend** (ver Pendências).

**Endpoints necessários (não existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /kpis` | Catálogo de KPIs com id, nome, fórmula, unidade, categoria |

---

### PG-08 — `/kpis/[kpi_id]` (KPI Detail) `planejado`

**Objetivo**: interpretação de um KPI com benchmark setorial e top empresas.

**Status**: não iniciado. **Aguarda endpoints de backend** (ver Pendências).

**Endpoints necessários (não existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /kpis/{kpi_id}` | Definição + distribuição setorial + top empresas por KPI |

---

### PG-09 — `/macro` (Macro Hub) `planejado`

**Objetivo**: hub de indicadores macroeconômicos como contexto para análise.

**Status**: não iniciado. Fonte de dados é externa (não vem do banco CVM).

---

### PG-10 — `/macro/[indicator_id]` (Macro Detail) `planejado`

**Status**: não iniciado. Depende de definição de fonte de dados macro.

---

### `/design-system` — tooling interno

**Status**: showcase interno de tokens e componentes. Não aparece na navegação
de produto. Não consome endpoints de API.

---

## Tabela inversa — endpoint → rotas que o usam

| Endpoint | Rotas que consomem |
|---|---|
| `GET /health` | `/` |
| `GET /companies` | `/`, `/empresas`, `/comparar` |
| `GET /companies/filters` | `/empresas` |
| `GET /companies/{cd_cvm}` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /companies/{cd_cvm}/years` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /companies/{cd_cvm}/statements` | `/empresas/[cd_cvm]` |
| `GET /companies/{cd_cvm}/kpis` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /refresh-status` | Não consumido pelo frontend ainda |
| `GET /base-health` | `/` (parcialmente, se trust strip expandir) |

---

## Pendências de backend

Endpoints que o frontend vai precisar mas que ainda não existem. Antes de
iniciar PG-05 ou posterior, o backend precisa cobrir a linha correspondente.

| Rota frontend | Endpoint necessário | Dados mínimos esperados | Status |
|---|---|---|---|
| PG-05 `/setores` | `GET /sectors` | slug, nome, n_empresas, KPI médio (ROE, margem) | Não planejado |
| PG-06 `/setores/[slug]` | `GET /sectors/{slug}` | metadados + empresas + KPIs por ano | Não planejado |
| PG-07 `/kpis` | `GET /kpis` | id, nome, fórmula, unidade, categoria | Não planejado |
| PG-08 `/kpis/[kpi_id]` | `GET /kpis/{kpi_id}` | definição + distribuição + top empresas | Não planejado |

**Protocolo**: ao criar um task de backend para qualquer linha acima, vincule
este documento no corpo da issue e atualize o status da linha quando o endpoint
for entregue.

---

## Protocolo de mudança cross-área

### Adicionando rota no frontend

1. Adicione a seção neste arquivo com status `em desenvolvimento`.
2. Liste os endpoints necessários. Se algum não existe: adicione em Pendências.
3. Crie task issue de backend antes de começar o frontend se endpoints faltarem.
4. Ao abrir PR do frontend, referencie este arquivo na descrição.

### Adicionando endpoint no backend

1. Adicione o endpoint na tabela inversa.
2. Verifique Pendências — se este endpoint estava lá, atualize o status e notifique.
3. Atualize `docs/V2_API_CONTRACT.md` com o contrato completo.

### Alterando ou removendo endpoint existente

1. Consulte a tabela inversa — identifique todas as rotas afetadas.
2. Classifique como `risk:contract-sensitive` na task issue.
3. Coordinate com o owner do frontend antes de fazer merge.
4. Atualize este documento e `docs/V2_API_CONTRACT.md` no mesmo PR.

---

_Última atualização: 2026-04-09 — Sessão 34_
