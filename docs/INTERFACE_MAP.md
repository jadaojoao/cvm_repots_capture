# Interface Map - Frontend routes x API endpoints

**Leitura obrigatoria antes de tocar `apps/web` ou `apps/api`.**

Este documento e a fonte de verdade sobre quais rotas o frontend tem, qual e o
status de cada uma, e quais endpoints de API cada rota consome. Qualquer IA ou
pessoa que trabalhe em qualquer uma das duas areas deve atualizar este arquivo
**antes** de comecar a implementacao.

> Contratos HTTP detalhados: `docs/V2_API_CONTRACT.md`
> Hierarquia de rotas e IA de produto: `docs/SITEMAP.MD`
> Requisitos de fase e scope: `docs/V2_PHASE2_WEB_SLICE.md`

---

## Como manter este documento

- **Nova rota no frontend**: adicione a secao, marque como `em desenvolvimento`,
  liste os endpoints necessarios. Se algum nao existir ainda, registre em
  [Pendencias de backend](#pendencias-de-backend).
- **Novo endpoint no backend**: adicione na [tabela inversa](#tabela-inversa-endpoint-x-rotas-que-o-usam).
  Verifique se alguma rota em _Pendencias_ esperava por ele e atualize o status.
- **Rota vai ao ar**: mude o status de `em desenvolvimento` para `live`.
- **Endpoint alterado ou removido**: verifique a tabela inversa, atualize todas as
  rotas afetadas, registre breaking change no PR.

---

## Rotas do frontend

### PG-01 - `/` (Home) `live`

**Objetivo**: roteador de entrada - leva o usuario ao caminho de analise mais curto.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /health` | - | Trust strip / sinal de saude da API |
| `GET /companies` | `page=1&page_size=8` | Sugestoes rapidas de empresas na home |

**Rota interna Next.js**:
- `GET /api/company-search?q=<termo>` -> chama `GET /companies` com `search=q` e
  retorna ate 6 itens para o autocomplete do hero.

---

### PG-02 - `/empresas` (Companies Hub) `live`

**Objetivo**: descoberta e selecao de empresa por busca e filtro de setor.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies` | `search=`, `sector=`, `page=`, `page_size=` | Lista paginada de empresas |
| `GET /companies/filters` | - | Opcoes de setor para o filtro |

**Query params publicos da rota**: `?busca=&setor=&pagina=`

---

### PG-03 - `/empresas/[cd_cvm]` (Company Detail) `live`

**Objetivo**: analise completa de uma empresa - KPIs, demonstracoes e contexto.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies/{cd_cvm}` | - | Metadados da empresa (header) |
| `GET /companies/{cd_cvm}/years` | - | Anos disponiveis (seletor de periodo) |
| `GET /companies/{cd_cvm}/statements` | `stmt=DRE\|BPA\|BPP\|DFC`, `years=2023,2024` | Aba Demonstracoes |
| `GET /companies/{cd_cvm}/kpis` | `years=2023,2024` | Aba Visao Geral |
| `GET /companies/{cd_cvm}/export/excel` | - | Download do workbook Excel completo da empresa, sempre com todos os anos disponiveis |

**Query params publicos da rota**: `?anos=2023,2024&aba=visao-geral\|demonstracoes&stmt=DRE\|BPA\|BPP\|DFC`

---

### PG-04 - `/comparar` (Compare) `live`

**Objetivo**: comparacao lado a lado entre ao menos 2 empresas com base em KPIs.

**Status**: rota entregue e integrada na navegacao principal. O fluxo cobre
estado inicial, deep-link por `ids`/`anos`, periodo em comum, fallback para
ausencia de interseccao anual e erro parcial sem derrubar a tela.

**Nao requer novos endpoints** - agrega chamadas existentes em paralelo.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /companies` | `page=1&page_size=8` | Sugestoes rapidas de empresas no seletor |
| `GET /companies/{cd_cvm}` | - | Metadados de cada empresa selecionada (paralelo) |
| `GET /companies/{cd_cvm}/years` | - | Anos disponiveis por empresa (paralelo) |
| `GET /companies/{cd_cvm}/kpis` | `years=<interseccao>` | KPI bundles por empresa (paralelo) |
| `GET /companies/export/excel-batch` | `ids=cd_cvm1,cd_cvm2,...` | Download do lote `.zip` com um workbook `.xlsx` por empresa selecionada |

**Query params publicos da rota**: `?ids=cd_cvm1,cd_cvm2,...&anos=2022,2023`

**Arquivos relevantes**:
- `apps/web/app/comparar/page.tsx` - page component
- `apps/web/lib/compare-page-data.ts` - orquestracao das chamadas paralelas
- `apps/web/lib/compare-utils.ts` - helpers de interseccao de anos e montagem de linhas
- `apps/web/components/compare/` - CompareSelector, CompareKpiTable, CompareTracker

---

### PG-05 - `/setores` (Sectors Hub) `live`

**Objetivo**: descoberta de setores com ranking de KPIs agregados.

**Status**: rota entregue e integrada na navegacao principal. O hub lista setores
com slug canonico, contagem de empresas, ano-base mais recente e snapshot
agregado de ROE, margem EBIT e margem liquida.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /sectors` | - | Lista ordenada de setores com snapshot anual mais recente |

**Query params publicos da rota**: nenhum na primeira entrega

**Arquivos relevantes**:
- `apps/web/app/setores/page.tsx` - page component
- `apps/web/lib/sectors-page-data.ts` - loader do hub e do detalhe
- `apps/web/components/sectors/sector-directory-list.tsx` - cards do hub
- `apps/web/components/sectors/sector-hub-tracker.tsx` - tracking de visualizacao

---

### PG-06 - `/setores/[slug]` (Sector Detail) `live`

**Objetivo**: analise profunda de um setor - empresas do setor, ranking de KPIs, contexto.

**Status**: rota entregue com fallback para `slug` inexistente, `ano` invalido
caindo para o ano mais recente disponivel e CTA ativo na pagina da empresa.

**Endpoints consumidos**:

| Endpoint | Params | Para que serve |
|---|---|---|
| `GET /sectors/{slug}` | `year=` | Metadados, serie anual agregada e ranking anual de empresas |

**Query params publicos da rota**: `?ano=<YYYY>&aba=visao-geral|empresas`

Defaults:
- `ano`: ano mais recente disponivel do setor
- `aba=visao-geral`

**Arquivos relevantes**:
- `apps/web/app/setores/[slug]/page.tsx` - page component
- `apps/web/components/sectors/sector-overview.tsx` - cards e serie anual
- `apps/web/components/sectors/sector-company-table.tsx` - tabela anual de empresas
- `apps/web/components/sectors/sector-year-selector.tsx` - ano em URL
- `apps/web/components/sectors/sector-detail-tracker.tsx` - tracking de visualizacao

---

### PG-07 - `/kpis` (KPI Hub) `planejado`

**Objetivo**: catalogo de KPIs com definicoes e top performers.

**Status**: nao iniciado. **Aguarda endpoints de backend** (ver Pendencias).

**Endpoints necessarios (nao existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /kpis` | Catalogo de KPIs com id, nome, formula, unidade, categoria |

---

### PG-08 - `/kpis/[kpi_id]` (KPI Detail) `planejado`

**Objetivo**: interpretacao de um KPI com benchmark setorial e top empresas.

**Status**: nao iniciado. **Aguarda endpoints de backend** (ver Pendencias).

**Endpoints necessarios (nao existem ainda)**:

| Endpoint | Dados esperados |
|---|---|
| `GET /kpis/{kpi_id}` | Definicao + distribuicao setorial + top empresas por KPI |

---

### PG-09 - `/macro` (Macro Hub) `planejado`

**Objetivo**: hub de indicadores macroeconomicos como contexto para analise.

**Status**: nao iniciado. Fonte de dados e externa (nao vem do banco CVM).

---

### PG-10 - `/macro/[indicator_id]` (Macro Detail) `planejado`

**Status**: nao iniciado. Depende de definicao de fonte de dados macro.

---

### `/design-system` - tooling interno

**Status**: showcase interno de tokens e componentes. Nao aparece na navegacao
de produto. Nao consome endpoints de API.

---

## Tabela inversa - endpoint x rotas que o usam

| Endpoint | Rotas que consomem |
|---|---|
| `GET /health` | `/` |
| `GET /companies` | `/`, `/empresas`, `/comparar` |
| `GET /companies/filters` | `/empresas` |
| `GET /companies/{cd_cvm}` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /companies/{cd_cvm}/years` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /companies/{cd_cvm}/statements` | `/empresas/[cd_cvm]` |
| `GET /companies/{cd_cvm}/kpis` | `/empresas/[cd_cvm]`, `/comparar` |
| `GET /companies/{cd_cvm}/export/excel` | `/empresas/[cd_cvm]` |
| `GET /companies/export/excel-batch` | `/comparar` |
| `GET /sectors` | `/setores` |
| `GET /sectors/{slug}` | `/setores/[slug]` |
| `GET /refresh-status` | Nao consumido pelo frontend ainda |
| `GET /base-health` | `/` (parcialmente, se trust strip expandir) |

---

## Pendencias de backend

Endpoints que o frontend vai precisar mas que ainda nao existem. Antes de
iniciar PG-07 ou posterior, o backend precisa cobrir a linha correspondente.

| Rota frontend | Endpoint necessario | Dados minimos esperados | Status |
|---|---|---|---|
| PG-07 `/kpis` | `GET /kpis` | id, nome, formula, unidade, categoria | Nao planejado |
| PG-08 `/kpis/[kpi_id]` | `GET /kpis/{kpi_id}` | definicao + distribuicao + top empresas | Nao planejado |

**Protocolo**: ao criar uma task de backend para qualquer linha acima, vincule
este documento no corpo da issue e atualize o status da linha quando o endpoint
for entregue.

---

## Protocolo de mudanca cross-area

### Adicionando rota no frontend

1. Adicione a secao neste arquivo com status `em desenvolvimento`.
2. Liste os endpoints necessarios. Se algum nao existe: adicione em Pendencias.
3. Crie task issue de backend antes de comecar o frontend se endpoints faltarem.
4. Ao abrir PR do frontend, referencie este arquivo na descricao.

### Adicionando endpoint no backend

1. Adicione o endpoint na tabela inversa.
2. Verifique Pendencias - se este endpoint estava la, atualize o status e notifique.
3. Atualize `docs/V2_API_CONTRACT.md` com o contrato completo.

### Alterando ou removendo endpoint existente

1. Consulte a tabela inversa - identifique todas as rotas afetadas.
2. Classifique como `risk:contract-sensitive` na task issue.
3. Coordene com o owner do frontend antes de fazer merge.
4. Atualize este documento e `docs/V2_API_CONTRACT.md` no mesmo PR.

---

_Ultima atualizacao: 2026-04-09 - issue #82_
