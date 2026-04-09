# WEBAPP_TRANSFORMATION_PLAN.md - Roteiro da transicao da V1 para uma web app real

> Documento de execucao para a transformacao do projeto atual em uma web app mais proxima de producao.
> Escopo deste documento: roadmap, refinamento por fases e objetivo de aprendizado.
> Base arquitetural: [0002 - Stack recomendada para a V2 com GitHub Student Developer Pack](./decisions/0002-student-pack-v2-stack.md).
> Runtime remoto do ciclo atual: [0004 - Primeiro runtime remoto: Railway + Vercel](./decisions/0004-first-remote-runtime-railway-vercel.md).

---

## 1. Objetivo

Transformar o projeto atual, que hoje opera com scraper Python + app PyQt6 + dashboard Streamlit, em uma arquitetura `web + API + Postgres` sem interromper a V1 operacional.

Esta transicao tem dois objetivos simultaneos:
- entregar uma V2 web mais escalavel e mais proxima de produto;
- usar o proprio projeto como trilha guiada de aprendizado em fullstack, deploy e observabilidade.

---

## 2. Principios da transicao

- A V1 continua operacional em paralelo durante toda a transicao.
- O scraper/updater permanece em Python.
- A V2 comeca read-only.
- A primeira publicacao remota assume deploy gerenciado e separado por camada.
- Nao ha migracao direta do Streamlit para a nova UI; a V2 nasce ao lado da V1.
- O frontend web so entra depois que a fronteira HTTP da V2 estiver estavel.

---

## 3. Primeiro slice tecnico documentado agora

### Fase 1 refinada: backend-first

O primeiro slice da V2 foi refinado para um backend `FastAPI` local em `apps/api`, mantendo `apps/web` fora da implementacao inicial.

Motivo:
- a V1 ainda carregava risco operacional demais para iniciar pela UI;
- o ganho real da fase era estabilizar um contrato HTTP em cima do nucleo headless;
- isso reduz retrabalho quando o frontend web entrar.

### API da Fase 1

Aplicacao `FastAPI`, read-only, com os endpoints:
- `GET /health`
- `GET /companies?search=&sector=&page=&page_size=`
- `GET /companies/filters`
- `GET /companies/{cd_cvm}`
- `GET /companies/{cd_cvm}/years`
- `GET /companies/{cd_cvm}/statements?years=&stmt=`
- `GET /companies/{cd_cvm}/kpis?years=`
- `GET /refresh-status?cd_cvm=`
- `GET /base-health?start_year=&end_year=&force_refresh=`

### Fronteira de dados

- leitura reaproveita `src/read_service.py` e os DTOs de `src/contracts.py`;
- nenhuma rota de escrita entra na Fase 1;
- `SQLite` continua sendo o default local;
- `PostgreSQL` continua sendo o alvo da V2 e o gate obrigatorio de validacao.

---

## 4. Fases

### Fase 1 - Backend local read-only

Meta de entrega:
- subir localmente uma API `FastAPI` somente leitura em `apps/api`;
- estabilizar contratos HTTP para busca, detalhe, anos, demonstracoes, KPIs, refresh status e health snapshot;
- documentar bootstrap, testes e validacao SQLite/PostgreSQL.

Meta de aprendizado:
- aprender a transformar contratos Python internos em contratos HTTP claros;
- aprender a separar nucleo de produto e adaptador HTTP;
- aprender a documentar e testar uma API antes da UI web.

Saida esperada:
- API local com Swagger/OpenAPI;
- suite HTTP com `TestClient`;
- CI minima rodando V1 + API;
- backlog da Fase 2 reduzido a consumo frontend.

### Fase 2 - Web read-only em cima da API

Meta de entrega:
- criar `apps/web` em `Next.js`;
- entregar o primeiro slice local com `/`, `/empresas` e `/empresas/[cd_cvm]`;
- consumir exclusivamente a API da V2.

Meta de aprendizado:
- aprender a consumir contratos HTTP estaveis sem furar a fronteira do dominio;
- aprender a construir a primeira UX web sem reabrir decisoes de banco ou regras;
- aprender navegacao, estado e fetching sobre uma API local/preview.

Saida esperada:
- uma navegacao web minima funcional;
- paridade inicial de busca + detalhe rico de empresa;
- base pronta para `PG-04 /comparar` sem reabrir foundation.

### Fase 3 - Primeiro deploy gerenciado

Meta de entrega:
- publicar frontend, API e banco em modo separado;
- validar conectividade remota, erros basicos e operacao de leitura fora do ambiente local;
- manter a V1 local como fonte operacional em paralelo.

Decisao operacional do ciclo atual:
- API e banco alvo na `Railway`;
- web em `Vercel`;
- contrato minimo entre camadas usando `ALLOWED_ORIGINS` na API e
  `API_BASE_URL` na web.

Meta de aprendizado:
- aprender deploy gerenciado por camada, sem assumir self-hosting cedo demais;
- aprender configuracao de ambiente, secrets e conexoes remotas;
- aprender como observabilidade entra no ciclo logo no primeiro runtime remoto.

Saida esperada:
- primeira fatia remota da V2 acessivel;
- ambiente de teste com `PostgreSQL` remoto;
- base pronta para Sentry, Codecov e demais ferramentas do Student Pack.

### Fase 4 - Hardening para app real

Meta de entrega:
- adicionar auth quando houver necessidade funcional clara;
- integrar observabilidade, CI e quality gates;
- consolidar o fluxo de evolucao da V2 como frente principal de produto.

Meta de aprendizado:
- aprender a operar uma app web com feedback de erro melhor que o fluxo local atual;
- aprender rollout incremental com guardrails de teste e cobertura;
- aprender a distinguir prototipo funcional de aplicacao pronta para crescer.

Saida esperada:
- V2 com postura mais proxima de producao;
- caminho claro para priorizar UX, auth, deploy e manutencao;
- reducao progressiva da dependencia do Streamlit como interface estrategica.

---

## 5. Proximos passos concretos

1. Fechar a Fase 1 com validacao PostgreSQL real.
2. Consolidar o primeiro slice `Home -> Empresas -> Empresa` em `apps/web`.
3. Testar o slice local completo antes de qualquer deploy remoto.
4. Publicar a API na `Railway` e a web na `Vercel`, sem introduzir `Nginx`
   cedo demais.
5. Integrar observabilidade e qualidade antes de expandir escopo funcional.

---

## 6. O que este documento nao faz

- nao muda a stack atual da V1;
- nao substitui a documentacao detalhada da Fase 1 em `docs/V2_PHASE1_BACKEND.md`;
- nao substitui o ADR `0004`, que fixa o primeiro runtime remoto do ciclo;
- nao introduz endpoints de escrita;
- nao substitui o ADR 0002, que continua sendo a decisao arquitetural principal.
