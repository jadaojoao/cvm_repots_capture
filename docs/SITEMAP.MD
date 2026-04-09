# SITEMAP and IA Blueprint - Webapp CVM

Status: draft approved for incremental implementation
Owner: Product + Architecture
Last update: 2026-04-09

## 1) Product Context
- Product: financial analysis platform with CVM data for Brazilian companies.
- Main users: investors and analysts who need fast discovery and comparison.
- Architecture goals: discoverability, efficient comparison, and lead base growth.
- Growth constraint: keep MVP public now, preserve path for future logged area.

## 2) User Preferences
- Structure: simple.
- Navigation depth: shallow.
- Navigation style: product-led.
- Discovery model: hub-first, then detail pages.
- Priority order: analysis, comparison, discoverability, lead generation.
- Access model: public for now.
- Naming preference: short product labels.

## 3) Assumptions
- MVP stays read-only and consumes only V2 Phase 1 API contracts.
- No web-side data refresh flow.
- Institutional and legal pages support trust but stay outside primary tasks.
- SEO gains come from strong detail pages and clear internal linking.

## 4) Information Architecture Model
### 4.1 Content domains
- Companies
- Sectors
- KPIs
- Macro
- Compare
- Trust and Conversion (Methodology, Sources, Glossary, Contact, Newsletter)

### 4.2 Content relationships
- Company belongs to a sector.
- Company and sector are interpreted through KPI views.
- Macro indicators provide context for KPI and sector behavior.
- Compare crosses Company x Company and Company x Sector.

### 4.3 Grouping and hierarchy logic
- Level 1: hub pages for discovery.
- Level 2: detail pages for deep analysis.
- Utility and legal pages are globally reachable but not in primary task flow.

### 4.4 IA vs Sitemap vs Navigation UI
- IA: logical model of domains and relationships.
- Sitemap: hierarchy of pages and routes.
- Navigation UI: menus, breadcrumbs, contextual links, and footer.

## 5) Sitemap
### 5.1 MVP core routes
- /
- /empresas
- /empresas/[cd_cvm]
- /comparar
- /setores
- /setores/[slug]
- /kpis
- /kpis/[kpi_id]
- /macro
- /macro/[indicator_id]

### 5.2 Trust and support routes
- /metodologia
- /fontes
- /glossario
- /contato
- /newsletter
- /sobre

### 5.3 Utility and legal routes
- /obrigado
- /privacidade
- /termos
- /busca
- /404

## 6) Navigation System
### 6.1 Primary navigation
- Empresas
- Setores
- KPIs
- Macro
- Comparar

### 6.2 Secondary navigation (detail pages)
- Visao Geral
- Historico
- Comparaveis
- Contexto

### 6.3 Contextual navigation
- Breadcrumbs on all detail pages.
- Related links between company, sector, KPI, and macro pages.
- Fast action link to Compare from hubs and detail pages.

### 6.4 Footer navigation
- Sobre
- Metodologia
- Fontes
- Glossario
- Contato
- Newsletter
- Privacidade
- Termos

### 6.5 Exclusions from primary nav
- Obrigado
- Privacidade
- Termos
- Busca
- 404

## 7) Naming and Taxonomy Notes
- Keep labels short in menus.
- Canonical terms:
  - KPI as product term.
  - Macro in navigation, Macroeconomia in on-page SEO text.
- Avoid parallel labels for same concept.
- Slugs must be stable and deterministic.

## 8) Rationale
- Hub-first and shallow structure improves orientation and reduces click friction.
- Product-led navigation brings users directly to analysis tasks.
- Public MVP supports faster discoverability and adoption.
- Clear route ownership avoids content duplication over time.

## 9) Risks and Gaps
- SEO cannibalization risk between hubs and detail pages.
- Content overlap risk across company, sector, and KPI pages.
- Future logged features can create route inflation if not staged.
- Need ownership rules for each content domain before scale.

## 10) MVP vs Expanded Structure
### 10.1 MVP
- Public read-only navigation.
- Hubs and details for Companies, Sectors, KPIs, Macro.
- Compare route live.
- Trust, utility, and legal essentials.

### 10.2 Expanded
- Logged area: saved comparisons, watchlist, alerts, user preferences.
- Programmatic long-tail pages for SEO clusters.
- Stronger conversion funnels tied to content intent.

## 11) Next Recommendations
1. Validate the tree with 5 to 8 core user tasks.
2. Define content ownership per domain.
3. Add event tracking by intent: discover, analyze, compare, convert.
4. Lock slug strategy before broad page generation.

## 12) Documentation and Handoff Notes
This document is the implementation source for building pages incrementally.
Do not implement all pages at once.
Implement page by page following priority and acceptance criteria.

## 12.1 Current delivery checkpoint
- Live hoje: PG-01, PG-02, PG-03, PG-04, PG-05 e PG-06.
- Proximo bloco de produto: PG-07 e PG-08 (`/kpis` e `/kpis/[kpi_id]`).
- Macro (`PG-09` e `PG-10`) continua travado em discovery de fonte e contrato.

---

## 13) Quick Spec Index for Page-by-Page Build
Goal: find each page spec in less than 60 seconds.

### 13.1 Priority legend
- P0: required for core product value.
- P1: trust and conversion support.
- P2: utility, legal, and edge routes.

### 13.2 Build queue with priority and functional milestone
| Order | ID | Priority | Route | Page | Purpose | Functional milestone |
|---|---|---|---|---|---|---|
| 1 | PG-01 | P0 | / | Home | entry and routing to analysis | no |
| 2 | PG-02 | P0 | /empresas | Companies hub | discover and choose company | no |
| 3 | PG-03 | P0 | /empresas/[cd_cvm] | Company detail | analyze one company deeply | YES: app becomes functional here |
| 4 | PG-04 | P0 | /comparar | Compare | compare entities directly | YES: full core proposition |
| 5 | PG-05 | P0 | /setores | Sectors hub | sector discovery | yes |
| 6 | PG-06 | P0 | /setores/[slug] | Sector detail | sector analysis | yes |
| 7 | PG-07 | P0 | /kpis | KPI hub | discover KPI catalog | yes |
| 8 | PG-08 | P0 | /kpis/[kpi_id] | KPI detail | KPI interpretation | yes |
| 9 | PG-09 | P0 | /macro | Macro hub | macro indicator discovery | yes |
| 10 | PG-10 | P0 | /macro/[indicator_id] | Macro detail | macro context depth | yes |
| 11 | PG-11 | P1 | /metodologia | Methodology | trust and transparency | support |
| 12 | PG-12 | P1 | /fontes | Sources | trust and data provenance | support |
| 13 | PG-13 | P1 | /glossario | Glossary | reduce terminology friction | support |
| 14 | PG-14 | P1 | /contato | Contact | inbound lead capture | support |
| 15 | PG-15 | P1 | /newsletter | Newsletter | recurring lead capture | support |
| 16 | PG-16 | P1 | /sobre | About | product positioning | support |
| 17 | PG-17 | P2 | /obrigado | Thank you | post-conversion flow | support |
| 18 | PG-18 | P2 | /privacidade | Privacy | legal | support |
| 19 | PG-19 | P2 | /termos | Terms | legal | support |
| 20 | PG-20 | P2 | /busca | Search results | utility | support |
| 21 | PG-21 | P2 | /404 | Not found | resilience | support |

### 13.3 Functional threshold
- Minimum functional app starts at PG-03.
- Reason: user can discover a company and complete a full company analysis flow.
- Full core proposition starts at PG-04 when direct comparison is available.

---

## 14) Incremental Execution Model (One Page at a Time)
For each page, execute this checklist before moving to the next:
1. Confirm route and objective.
2. Define required data from API contracts.
3. Define mandatory content blocks.
4. Define primary CTA and secondary CTA.
5. Define inbound and outbound links.
6. Validate acceptance criteria.
7. Only then start next page.

### 14.1 Page spec card template
Use this exact card per page:
- ID:
- Route:
- Priority:
- Goal:
- User job-to-be-done:
- Required data contracts:
- Mandatory content blocks:
- Primary CTA:
- Secondary CTA:
- Internal links in:
- Internal links out:
- Acceptance criteria:
- Analytics events:

### 14.2 Ready-to-build cards for first four pages
#### PG-01 - Home
- Route: /
- Priority: P0
- Goal: route users to the shortest analysis path.
- User job-to-be-done: start analysis in one action.
- Required data contracts: health and basic company search availability.
- Mandatory content blocks: hero search, quick entry links, trust strip.
- Primary CTA: Buscar empresa.
- Secondary CTA: Ir para comparar.
- Internal links out: /empresas, /comparar, /setores, /kpis, /macro.
- Acceptance criteria: user can move to hub/detail in one click from home.

#### PG-02 - Companies Hub
- Route: /empresas
- Priority: P0
- Goal: let users discover and select target company quickly.
- User job-to-be-done: filter and pick a company for analysis.
- Required data contracts: companies search endpoint.
- Mandatory content blocks: searchable list, filters, key metadata.
- Primary CTA: Ver empresa.
- Secondary CTA: Comparar.
- Internal links out: /empresas/[cd_cvm], /comparar.
- Acceptance criteria: user can find and open target company in under 2 interactions.

#### PG-03 - Company Detail
- Route: /empresas/[cd_cvm]
- Priority: P0
- Goal: deliver complete single-company analysis page.
- User job-to-be-done: understand company performance over years.
- Required data contracts: company info, years, statements, kpis.
- Mandatory content blocks: summary, KPI highlights, statements, contextual links.
- Primary CTA: Comparar empresa.
- Secondary CTA: Ver setor.
- Internal links out: /comparar, /setores/[slug], /kpis/[kpi_id].
- Acceptance criteria: one-company analysis flow is complete and reliable.

#### PG-04 - Compare
- Route: /comparar
- Priority: P0
- Goal: enable direct comparison flow for decision support.
- User job-to-be-done: compare at least two entities side by side.
- Required data contracts: companies search, company detail, KPI bundles.
- Mandatory content blocks: selectors, comparable KPI table, difference highlights.
- Primary CTA: Ajustar comparacao.
- Secondary CTA: Abrir detalhe da empresa.
- Internal links out: /empresas/[cd_cvm], /setores/[slug], /kpis/[kpi_id].
- Acceptance criteria: user can complete one comparison task without dead ends.

---

## 15) Traceability to Existing Project Docs
- API contracts and payloads: docs/V2_API_CONTRACT.md
- Backend source of truth and constraints: docs/V2_PHASE1_BACKEND.md
- Transition roadmap and phase boundaries: docs/WEBAPP_TRANSFORMATION_PLAN.md
- Business domain conventions: docs/CONTEXT.md

## 16) Change Control
- Any new page must include: priority, route owner, and relation to current IA domains.
- Any route rename requires redirect strategy and taxonomy update.
- If a page cannot map to one domain, create a design review before implementation.
