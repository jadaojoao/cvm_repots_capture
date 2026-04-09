# 0004 - Primeiro runtime remoto: Railway + Vercel

- **Status:** accepted
- **Data:** 2026-04-09
- **Autor:** human+ai

## Contexto

Depois do ADR 0002, o projeto ainda precisava fixar qual seria o primeiro
ambiente remoto de aprendizado da V2.

Essa decisao precisava respeitar quatro restricoes praticas:
- manter a V1 operacional sem migracao forcada;
- publicar frontend e API em camadas separadas;
- reduzir a carga operacional da primeira wave remota;
- usar o estado real do repositorio, que ja possui artefatos de deploy para
  `apps/api` e `apps/web`.

## Decisao

O primeiro runtime remoto do ciclo atual fica definido como:
- **API e banco alvo:** `Railway`
- **Web app:** `Vercel`

O escopo remoto inicial continua limitado a:
- `/`
- `/empresas`
- `/empresas/[cd_cvm]`

O pacote `/comparar` fica fora do gate desta wave.

## Racional

### 1. Aderencia ao estado atual do repo

O repositorio ja possui:
- `apps/api/Dockerfile`
- `apps/api/requirements-prod.txt`
- `railway.toml`
- `apps/web/vercel.json`

Escolher `Railway + Vercel` reaproveita trabalho ja entregue e reduz retrabalho
na primeira publicacao.

### 2. Separacao limpa por camada

`Railway` atende bem ao runtime Python da API e ao uso de `PostgreSQL` como
alvo remoto. `Vercel` atende bem ao `Next.js` do slice web atual. A dupla
preserva a arquitetura `frontend + API + Postgres` sem forcar um host unico ou
reverse proxy cedo demais.

### 3. Menor atrito operacional na primeira wave

O objetivo desta fase nao e montar infraestrutura completa. O objetivo e obter
um runtime remoto funcional, com healthcheck, CORS configurado, variaveis de
ambiente claras e um caminho simples para observabilidade.

### 4. Compatibilidade com a proxima etapa

Essa decisao deixa explicito o contrato operacional minimo entre as camadas:
- a API remota deve aceitar o dominio publicado da web em `ALLOWED_ORIGINS`;
- a web remota deve apontar para a API publicada via `API_BASE_URL`;
- a validacao remota deve usar `PostgreSQL` real, nao fallback local;
- a integracao de Sentry entra depois, com escopo inicial `API first`.

## Consequencias

- `Railway + Vercel` vira o ambiente de aprendizado oficial desta wave.
- A V1 continua como fallback local e operacional durante toda a validacao
  remota.
- `Nginx` permanece opcional e fora do primeiro deploy.
- O fechamento da task de deploy remoto exige URLs publicas, smoke funcional do
  slice web e evidencia de conexao com `PostgreSQL`.

## Referencias

- [0002 - Stack recomendada para a V2 com GitHub Student Developer Pack](./0002-student-pack-v2-stack.md)
- [docs/STUDENT_PACK_PLAN.md](../STUDENT_PACK_PLAN.md)
- [docs/WEBAPP_TRANSFORMATION_PLAN.md](../WEBAPP_TRANSFORMATION_PLAN.md)
