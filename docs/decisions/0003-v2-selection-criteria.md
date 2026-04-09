# 0003 - Criterios de escolha da V2

- **Status:** accepted
- **Data:** 2026-04-09
- **Autor:** human+ai

## Contexto

O ADR 0002 ja congelou a stack recomendada da V2 como `Next.js` + `FastAPI` +
`PostgreSQL` + `Ubuntu Linux`.

Faltava registrar, de forma separada da escolha de stack e das ofertas do
GitHub Student Developer Pack, quais criterios orientaram essa decisao.

Este registro existe para evitar duas confusoes:
- tratar ferramentas do Pack como criterio arquitetural;
- reabrir a escolha de stack sem revisar os mesmos criterios de forma explicita.

## Criterios

### 1. Velocidade de entrega

A V2 precisa nascer ao lado da V1, com ganho pratico em poucas fases.
Tecnologias que permitam entregar uma API read-only, uma web minima e um
primeiro deploy sem reescrever o motor atual recebem preferencia.

### 2. Aderencia ao projeto existente

O backend atual, o dominio de leitura e o pipeline operacional ja vivem em
Python. A stack escolhida precisa reaproveitar esse nucleo em vez de deslocar a
complexidade para uma reimplementacao desnecessaria.

### 3. Deploy simples

O primeiro runtime remoto precisa ser gerenciavel com pouco atrito. A escolha
de tecnologia deve funcionar bem em deploy por camada, sem exigir
self-hosting, reverse proxy obrigatorio ou operacao pesada logo na primeira
wave.

### 4. Observabilidade

A nova stack precisa permitir healthcheck claro, logging, integracao de erro e
diagnostico inicial desde o primeiro runtime remoto. A capacidade de receber
feedback operacional cedo pesa tanto quanto a ergonomia de desenvolvimento.

### 5. Integracao com PostgreSQL

`PostgreSQL` e o banco alvo da V2. A stack escolhida precisa se integrar bem a
um banco relacional remoto, sem empurrar o projeto para modelos de dados ou
plataformas que atrapalhem consultas analiticas e evolucao de contrato.

## Aplicacao ao ADR 0002

O ADR 0002 satisfaz esses criterios desta forma:
- `FastAPI` preserva a aderencia ao dominio Python e acelera a entrega da API.
- `Next.js` atende a necessidade de UI web mais forte sem reescrever o backend.
- `PostgreSQL` preserva a fronteira relacional necessaria para a V2.
- `Ubuntu Linux` e deploy gerenciado reduzem atrito operacional no runtime
  remoto.
- `Nginx` fica opcional no inicio porque simplicidade de deploy pesa mais que
  completude de infraestrutura na primeira wave.

## Fora de escopo

Este ADR nao escolhe ferramentas do Student Pack como arquitetura principal.
Beneficios como Copilot, Codespaces, Sentry e Codecov aceleram execucao e
aprendizado, mas nao substituem os criterios acima.

## Consequencias

- Mudancas futuras de stack devem declarar qual criterio deixou de ser
  atendido e por que.
- Novas fases da V2 podem ampliar ferramentas, mas sem reabrir a direcao
  principal sem justificativa explicita.
- O ADR 0002 continua sendo a decisao arquitetural principal; este documento e
  o seu criterio de leitura.

## Referencias

- [0002 - Stack recomendada para a V2 com GitHub Student Developer Pack](./0002-student-pack-v2-stack.md)
- [docs/STUDENT_PACK_PLAN.md](../STUDENT_PACK_PLAN.md)
- [docs/WEBAPP_TRANSFORMATION_PLAN.md](../WEBAPP_TRANSFORMATION_PLAN.md)
