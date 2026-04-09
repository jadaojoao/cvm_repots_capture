# STUDENT_PACK_PLAN.md - Registro do GitHub Student Developer Pack

> Documento-base para registrar o que o GitHub Student Developer Pack pode acelerar neste projeto e como isso se traduz em backlog e proximos passos.
> Data do levantamento inicial: 2026-04-05.
> Importante: ofertas, parceiros, limites e prazos do Pack mudam ao longo do tempo. Revalidar no momento da ativacao, usando a pagina oficial do Pack e a pagina oficial do parceiro.

---

## 1. Contexto e direcao escolhida

Este projeto vai manter a stack atual operacional no curto prazo:
- scraper Python continua sendo a fonte operacional de dados;
- SQLite/Postgres continuam sendo a fronteira de dados da V1;
- o app PyQt6 continua sendo a interface principal de atualizacao;
- o dashboard Streamlit continua util como apoio, mas nao e a aposta de longo prazo.

Direcao para os proximos 60 dias:
- estabilizar o que existe;
- aproveitar o Student Pack em produtividade, cloud, observabilidade e qualidade;
- preparar uma V2 em formato `frontend + API + Postgres`;
- adiar a escolha exata de framework para depois da fase inicial de estudo.

Atualizacao em 2026-04-07:
- a stack recomendada para a V2 foi congelada no ADR [0002 - Stack recomendada para a V2 com GitHub Student Developer Pack](./decisions/0002-student-pack-v2-stack.md);
- a execucao da transformacao passa a ser acompanhada em [WEBAPP_TRANSFORMATION_PLAN.md](./WEBAPP_TRANSFORMATION_PLAN.md);
- direcao escolhida: `Next.js` + `FastAPI/Uvicorn` + `PostgreSQL` + `Ubuntu Linux`;
- `Nginx` fica opcional no inicio e entra apenas quando houver self-hosting ou necessidade real de reverse proxy.

Atualizacao em 2026-04-09:
- o primeiro runtime remoto de aprendizado da V2 fica congelado no ADR
  [0004 - Primeiro runtime remoto: Railway + Vercel](./decisions/0004-first-remote-runtime-railway-vercel.md);
- o deploy inicial continua limitado ao slice `/`, `/empresas` e
  `/empresas/[cd_cvm]`;
- `/comparar` continua fora do gate remoto desta wave.

## 1.1 Aprendizado por construcao

Este projeto nao e apenas uma migracao de stack. Ele tambem funciona como trilha pratica de aprendizado em:
- arquitetura web moderna sobre uma base Python ja existente;
- separacao entre frontend, API e banco compartilhado;
- deploy gerenciado, observabilidade e qualidade de software;
- tomada de decisao incremental sem descartar a V1 operacional.

Por isso, o Student Pack entra em duas frentes ao mesmo tempo:
- **frente de entrega:** acelerar a descoberta e a construcao da V2;
- **frente de aprendizado:** usar a propria evolucao do projeto para aprender fullstack, deploy e operacao com contexto real.

Sequencia adotada:
1. `docs/decisions/0002-student-pack-v2-stack.md` congela a stack recomendada.
2. `docs/WEBAPP_TRANSFORMATION_PLAN.md` define as fases, o primeiro slice tecnico e os objetivos de aprendizado.
3. `docs/decisions/0004-first-remote-runtime-railway-vercel.md` fixa o primeiro runtime remoto do ciclo atual.
4. `docs/STUDENT_PACK_PLAN.md` registra como os beneficios do Pack apoiam essa trajetoria.

---

## 2. Legenda de status

- `disponivel`: beneficio confirmado no Pack e pronto para ativacao
- `ativado`: beneficio ja habilitado e em uso
- `em avaliacao`: beneficio priorizado, mas ainda sem ativacao concluida ou sem decisao final de uso
- `nao priorizado agora`: beneficio util, mas fora do foco do ciclo atual

---

## 3. Beneficios priorizados para este projeto

Atualizacao operacional em 2026-04-09:
- `Codecov` ja foi integrado ao CI atual pela task `#8` e deixa de ser apenas
  hipotese de backlog.
- a stack recomendada da V2 ja esta congelada no ADR `0002`; esta tabela passa
  a registrar beneficio operacional, nao decisao de stack.
- a decisao do primeiro runtime remoto e o criterio formal da V2 seguem nas
  tasks `#9` e `#11`.

| Beneficio | Objetivo | Status atual | Prioridade | Problema que resolve | Onde entra no fluxo atual | Pre-requisitos | Risco/custo de adocao | Decisao do ciclo de 60 dias | Fonte oficial |
|---|---|---|---|---|---|---|---|---|---|
| GitHub Copilot | Produtividade | em avaliacao | imediata | acelera refactor, testes, queries e exploracao de codigo | desenvolvimento diario no repo | ativar no GitHub/IDE | risco baixo; exige disciplina de review | ativar cedo e usar no fluxo diario | [GitHub Pack](https://education.github.com/pack), [Copilot](https://github.com/features/copilot) |
| JetBrains Student | Produtividade | em avaliacao | alta | melhora navegacao e manutencao do codigo Python | manutencao do scraper, DB e testes | conta elegivel e IDE instalada | baixo; depende de preferencia de IDE | avaliar junto com Copilot | [GitHub Pack](https://education.github.com/pack), [JetBrains Education](https://www.jetbrains.com/community/education/) |
| GitHub Codespaces | Produtividade | em avaliacao | alta | ajuda a ter ambiente reproduzivel e trabalho remoto | onboarding, testes, estudo da V2 | repo configuravel para dev container depois | custo de tempo para configurar ambiente | avaliar no ciclo, sem bloquear entregas | [GitHub Pack](https://education.github.com/pack), [Codespaces](https://github.com/features/codespaces) |
| Frontend Masters | Aprendizado aplicado | em avaliacao | imediata | acelera a transicao para fullstack sem travar a V1 | fase de descoberta da V2 | trilha inicial definida e rotina de estudo | custo principal e tempo | usar como base para decidir stack da V2 | [GitHub Pack](https://education.github.com/pack), [Frontend Masters](https://frontendmasters.com/) |
| Trilha cloud compativel com V2 | Infra/deploy | em avaliacao | imediata | permite ambiente remoto de aprendizado e futura V2 | deploy de testes e primeira fatia da V2 | decisao do runtime remoto registrada no ADR 0004 | risco medio se a escolha vier cedo demais | usar `Railway + Vercel` como ambiente de aprendizado desta wave | [GitHub Pack](https://education.github.com/pack) |
| Sentry | Observabilidade | em avaliacao | imediata | captura erros e reduz diagnostico manual em ambiente remoto | primeiro runtime remoto da V2 ou servico exposto | projeto remoto minimo e DSN configurado | baixo; exige decidir primeiro runtime remoto | integrar no primeiro runtime que ficar online | [GitHub Pack](https://education.github.com/pack), [Sentry](https://sentry.io/) |
| Codecov | Qualidade | ativado | imediata | torna cobertura visivel e cria guardrail antes da V2 | CI/testes do repo atual | workflow de CI com pytest | baixo; upload externo segue dependente do servico | manter ativo no CI atual e revalidar a visibilidade no servico externo | [GitHub Pack](https://education.github.com/pack), [Codecov](https://about.codecov.io/) |
| Doppler ou similar | Secrets/operacao | nao priorizado agora | depois | melhora gestao de segredos quando houver multiplos ambientes | deploy cloud e ambientes remotos | multiplos secrets reais e ambientes persistentes | custo operacional desnecessario cedo demais | avaliar apenas depois do primeiro runtime remoto estavel | [GitHub Pack](https://education.github.com/pack), [Doppler](https://www.doppler.com/) |
| Dominio/subdominio patrocinado | Apresentacao/publicacao | nao priorizado agora | depois | ajuda quando houver demo publica estavel | fase posterior de publicacao | app web estavel e ambiente remoto fixo | baixo, mas irrelevante no momento | adiar ate existir V2 demonstravel | [GitHub Pack](https://education.github.com/pack) |
| Extras nao ligados ao gargalo atual | Geral | nao priorizado agora | depois | adicionam dispersao sem resolver entrega imediata | fora do fluxo principal | avaliar caso a caso | risco alto de espalhar foco | manter fora do ciclo atual | [GitHub Pack](https://education.github.com/pack) |

---

## 4. Registro operacional por beneficio

Preencher esta tabela conforme os beneficios forem ativados ou descartados.

| Beneficio | Owner | Status | Link oficial de ativacao/uso | Limites ou prazo | Dependencias | Proximo passo |
|---|---|---|---|---|---|---|
| GitHub Copilot | `@jadaojoao` | em avaliacao | GitHub Pack + Copilot | revalidar no momento da ativacao | conta GitHub elegivel | ativar e confirmar setup no editor principal |
| JetBrains Student | `@jadaojoao` | em avaliacao | GitHub Pack + JetBrains Education | revalidar no momento da ativacao | decidir IDE principal | validar se entrara no fluxo diario |
| GitHub Codespaces | `@jadaojoao` | em avaliacao | GitHub Pack + Codespaces | revalidar no momento da ativacao | definir ambiente de dev remoto | avaliar depois da documentacao do ambiente |
| Frontend Masters | `@jadaojoao` | em avaliacao | GitHub Pack + Frontend Masters | revalidar no momento da ativacao | definir trilha inicial | concluir trilha inicial e registrar aprendizados |
| Trilha cloud compativel com V2 | `@jadaojoao` | em avaliacao | GitHub Pack + parceiro cloud ativo | revalidar no momento da ativacao | ADR 0004 publicado | executar onboarding e validacao remota em `Railway + Vercel` |
| Sentry | `@jadaojoao` | em avaliacao | GitHub Pack + Sentry | revalidar no momento da ativacao | existir runtime remoto | integrar no primeiro runtime remoto |
| Codecov | `@jadaojoao` | ativado | GitHub Pack + Codecov | revalidar no momento da ativacao | CI atual ja integrado na task #8 | manter upload nao bloqueante e confirmar visibilidade no servico |
| Doppler ou similar | `@jadaojoao` | nao priorizado agora | GitHub Pack + parceiro ativo | revalidar no momento da ativacao | multiplos ambientes remotos | revisitar apos primeiro deploy estavel |

### 4.1 Checklist manual de ativacao

- GitHub Copilot: confirmar que o beneficio esta ativo na conta GitHub, validar
  login no editor principal e registrar o resultado na issue `#6`.
- JetBrains Student: resgatar a licenca educacional, decidir se a IDE entrara
  no fluxo diario e registrar a decisao na issue `#6`.
- GitHub Codespaces: revalidar limites vigentes, adiar criacao de ambiente ate
  existir contexto de dev container ou onboarding remoto.
- Frontend Masters: confirmar o resgate do beneficio, concluir a trilha
  inicial e publicar os aprendizados na issue `#7`.
- Trilha cloud compativel com V2: seguir o ADR `0004`, publicar API na
  `Railway`, publicar web na `Vercel` e registrar o smoke remoto na task `#14`.
- Sentry: criar o projeto apenas depois do primeiro runtime remoto definido e
  validar a integracao pela task `#13`.
- Codecov: manter a integracao do CI ativa, confirmar a visibilidade do
  relatorio no servico externo e reavaliar se a politica master-only deve
  permanecer.
- Doppler ou similar: nao ativar nesta fase; revisitar apenas depois do
  primeiro ambiente remoto estavel.

---

## 5. Roadmap de 60 dias

### Fase 1 - 2026-04-05 a 2026-04-18

- ativar e registrar os beneficios priorizados;
- concluir trilha inicial de Frontend Masters orientada a fullstack;
- escrever um ADR curto com criterios de escolha da V2:
  - velocidade de entrega
  - aderencia ao projeto
  - deploy simples
  - observabilidade
  - integracao com Postgres
- integrar Codecov ao CI atual;
- escolher o primeiro ambiente cloud de aprendizado, sem amarrar a arquitetura final.

### Fase 2 - 2026-04-19 a 2026-05-04

- decidir a stack da V2 com base no estudo e nos criterios do ADR;
- congelar a fronteira da V1:
  - scraper Python continua como produtor de dados;
  - banco continua como camada compartilhada;
  - Streamlit segue util, mas deixa de ser aposta estrategica;
- definir o contrato inicial da V2:
  - frontend consome API HTTP;
  - backend expoe leitura de empresa, anos, demonstracoes e KPIs;
  - Postgres vira o banco alvo;
- integrar Sentry no primeiro runtime remoto.

### Fase 3 - 2026-05-05 a 2026-06-04

- subir a primeira fatia da V2 em ambiente de teste:
  - uma tela web minima;
  - uma API minima;
  - conexao com Postgres;
- manter o fluxo atual em paralelo;
- medir:
  - facilidade de deploy
  - qualidade do feedback de erro
  - clareza do modelo de dados
  - esforco de evolucao

Decisao esperada ao final de 2026-06-04:
- manter a V1 como base operacional/local;
- usar a V2 como nova frente principal de produto.

---

## 6. Defaults e limites deste ciclo

- nao iniciar migracao direta de Streamlit para outra UI;
- nao reescrever o scraper agora;
- nao acoplar a escolha de framework da V2 antes da trilha inicial de estudo;
- Codecov entra antes de qualquer avanco tecnico relevante na V2;
- Sentry entra no primeiro runtime remoto;
- o contrato minimo da V2 deve ser documentado antes de implementacao.

---

## 7. Backlog no GitHub

O backlog operacional oficial agora vive em `GitHub Issues`.

Use sempre:
- milestone atual: [Student Pack 60 dias](https://github.com/jadaojoao/cvm_repots_capture/milestone/1)
- epics abertas: [filtro de epics](https://github.com/jadaojoao/cvm_repots_capture/issues?q=is%3Aissue+is%3Aopen+milestone%3A%22Student+Pack+60+dias%22+label%3Akind%3Aepic)
- tasks abertas: [filtro de tasks](https://github.com/jadaojoao/cvm_repots_capture/issues?q=is%3Aissue+is%3Aopen+milestone%3A%22Student+Pack+60+dias%22+label%3Akind%3Atask)

Epics atuais:
1. [#2 - Student Pack Activation](https://github.com/jadaojoao/cvm_repots_capture/issues/2)
2. [#3 - Current Stack Stabilization](https://github.com/jadaojoao/cvm_repots_capture/issues/3)
3. [#4 - Observability and Quality](https://github.com/jadaojoao/cvm_repots_capture/issues/4)
4. [#5 - V2 Discovery](https://github.com/jadaojoao/cvm_repots_capture/issues/5)

Regras de operacao:
- toda mudanca em arquivo versionado deve estar vinculada a uma `task issue`
- backlog diario, status e concluido vivem nas issues, nao neste documento
- este arquivo resume direcao e links, mas nao espelha a lista viva de tasks
