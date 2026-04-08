# WEBAPP_TRANSFORMATION_PLAN.md - Roteiro da transicao da V1 para uma web app real

> Documento de execucao para a transformacao do projeto atual em uma web app mais proxima de producao.
> Escopo deste documento: roadmap, primeiro slice tecnico e objetivos de aprendizado.
> Base arquitetural: [0002 - Stack recomendada para a V2 com GitHub Student Developer Pack](./decisions/0002-student-pack-v2-stack.md).

---

## 1. Objetivo

Transformar o projeto atual, que hoje opera com scraper Python + app PyQt6 + dashboard Streamlit, em uma arquitetura `web + API + Postgres` sem interromper a V1 operacional.

Esta transicao tem dois objetivos simultaneos:
- entregar uma V2 web mais escalavel e mais proxima de produto;
- usar o proprio projeto como trilha guiada de aprendizado em fullstack, deploy e observabilidade.

---

## 2. Principios da transicao

- A V1 continua operacional em paralelo durante toda a transicao.
- O scraper/updater permanece em Python e fica fora do escopo da Fase 1 da V2.
- O primeiro slice da V2 e somente leitura.
- A primeira publicacao remota assume deploy gerenciado e separado por camada.
- Nao ha migracao direta do Streamlit para a nova UI; a V2 nasce ao lado da V1.

---

## 3. Primeiro slice tecnico documentado agora

### Web UI

Aplicacao `Next.js`, read-only, com duas rotas iniciais:
- `/` para busca/selecionar empresa e anos;
- `/companies/[cd_cvm]` para detalhe da empresa.

### API

Aplicacao `FastAPI`, read-only, com os endpoints iniciais:
- `GET /companies?search=`
- `GET /companies/{cd_cvm}`
- `GET /companies/{cd_cvm}/statements?years=&stmt=`
- `GET /companies/{cd_cvm}/kpis?years=`

### Fronteira de dados

- leitura reaproveita a logica Python existente, principalmente `src/query_layer.py` e `src/kpi_engine.py`;
- nenhuma rota de escrita entra no primeiro slice;
- `PostgreSQL` e o banco alvo compartilhado da V2;
- `SQLite` continua valido para uso local e para a V1.

---

## 4. Fases

### Fase 1 - Slice local read-only

Meta de entrega:
- subir localmente uma UI web minima em `Next.js`;
- subir localmente uma API `FastAPI` somente leitura;
- validar busca de empresa, detalhe da empresa, demonstracoes e KPIs com base na logica ja existente em Python.

Meta de aprendizado:
- aprender a separar UI, API e banco sem reescrever o dominio;
- aprender o fluxo basico de consumo HTTP entre frontend e backend;
- aprender a transformar regras existentes em contratos de API pequenos e claros.

Saida esperada:
- uma navegacao web minima funcional;
- um contrato inicial de API estabilizado;
- clareza sobre o que pode ser reaproveitado da V1 sem refactor profundo.

### Fase 2 - Primeiro deploy gerenciado

Meta de entrega:
- publicar frontend, API e banco em modo separado;
- validar conectividade remota, erros basicos e operacao de leitura fora do ambiente local;
- manter a V1 local como fonte operacional em paralelo.

Meta de aprendizado:
- aprender deploy gerenciado por camada, sem assumir self-hosting cedo demais;
- aprender configuracao de ambiente, secrets e conexoes remotas;
- aprender como observabilidade entra no ciclo logo no primeiro runtime remoto.

Saida esperada:
- primeira fatia remota da V2 acessivel;
- ambiente de teste com `PostgreSQL` remoto;
- base pronta para Sentry, Codecov e demais ferramentas do Student Pack.

### Fase 3 - Hardening para app real

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

1. Registrar a direcao da V2 e do aprendizado nos docs do repo.
2. Congelar a fronteira da V1: scraper/updater seguem em Python e fora da primeira fatia web.
3. Definir o contrato da API read-only com base nas consultas atuais.
4. Criar a primeira UI web minima consumindo a API local.
5. Testar o slice local completo antes de qualquer deploy remoto.
6. Publicar o primeiro slice em deploy gerenciado, sem introduzir `Nginx` cedo demais.
7. Integrar observabilidade e qualidade antes de expandir escopo funcional.

---

## 6. O que este documento nao faz

- nao muda a stack atual da V1;
- nao cria `apps/web` ou `apps/api` neste commit;
- nao define provedor especifico de deploy;
- nao introduz endpoints de escrita;
- nao substitui o ADR 0002, que continua sendo a decisao arquitetural principal.
