# AGENTS.md

Contrato operacional para qualquer agente ou pessoa que trabalhe neste
repositorio.

## Fonte de verdade

- O backlog oficial vive em `GitHub Issues`.
- `docs/AGENTS.md` registra estado atual e historico de sessoes. Nao use esse
  arquivo como lista viva de tarefas.
- `docs/STUDENT_PACK_PLAN.md` resume o roadmap e aponta para issues/milestones.
  Nao replique nele o backlog operacional dia a dia.

## Check inicial por chat

- No inicio de qualquer chat executavel, a IA deve verificar:
  - tasks abertas da propria `lane:*`
  - child tasks recebidas de outras lanes na propria lane
  - child tasks que sua lane abriu para outras lanes
  - PRs abertas ligadas a essas issues para saber se algo ja foi entregue e
    aguarda consumo
- Se existir entrega pendente de consumo para a lane atual, a IA deve tratar
  isso antes de expandir escopo com novas delegacoes.

## Fluxo obrigatorio

1. Localize uma `task issue` aberta antes de alterar qualquer arquivo versionado.
2. Se a task ainda nao existir, crie uma issue a partir do template correto.
3. Garanta que a issue tenha, no minimo:
   - `kind:task`
   - um label `status:*`
   - um label `priority:*`
   - um label `area:*`
   - um label `risk:*`
   - um label `lane:*`
4. Garanta que o corpo da issue declare:
   - `Owner atual`
   - `Lane oficial`
   - `Workspace da task`
   - `Write-set esperado`
   - `Classificacao de risco`
5. Trabalhe sempre em uma worktree dedicada:
   - repo raiz permanece em `master`
   - a task usa branch `task/<issue-number>-<slug>`
   - a worktree vive em `.claude/worktrees/<lane>/<issue-number>-<slug>/`
6. Abra PR com `Closes #<issue-number>` no corpo.
7. Quando a implementacao estiver pronta, conclua a task com
   `scripts/pr_complete.ps1` ou processo equivalente:
   - checks obrigatorios verdes;
   - PR mergeada;
   - issue fechada;
   - branch remota removida quando aplicavel.
8. Antes de encerrar, atualize checklist, evidencias e docs afetados.
9. A task so conta como concluida depois do merge confirmado da PR. Epics fecham
   manualmente.

## Regra de commit, push e merge

- Nao deixe trabalho concluido apenas localmente.
- Faca `commit` quando houver um checkpoint coerente e verificavel:
  - uma parte funcional completa;
  - uma correcao validada;
  - ou antes de uma mudanca mais arriscada que mereca rollback claro.
- Faca `push` quando:
  - existir um commit verificavel que nao deve ficar so local;
  - a task precisar de backup remoto, handoff ou atualizacao da PR;
  - o fim da sessao deixar trabalho relevante em andamento.
- Abra ou atualize a PR assim que a branch estiver revisavel, mesmo em draft.
- Quando a task estiver completa e as validacoes relevantes tiverem passado:
  - atualize a issue;
  - marque a PR como pronta;
  - use `scripts/pr_complete.ps1 -Pr <numero>` ou fluxo equivalente para esperar
    os checks e concluir o merge.
- Preferencia de merge: `squash merge`.
- Depois do merge:
  - confirme o fechamento da task;
  - remova a worktree da task;
  - confirme que a branch remota foi removida ou remova-a explicitamente.

## Lanes oficiais

- `lane:frontend`
  - ownership principal: `apps/web/**` e docs internos do web app
- `lane:backend`
  - ownership principal: `apps/api/**`, `src/**`, `desktop/**`,
    `dashboard/**`, `tests/**` e `apps/api/tests/**`
- `lane:ops-quality`
  - ownership principal: `.github/**`, `docs/**`, `README.md`,
    `COMO_RODAR.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`,
    scripts operacionais e smokes

Uma task pertence a exatamente uma lane. Se o trabalho realmente precisar tocar
duas lanes de produto, divida em child tasks separadas.

## Protocolo de trabalho paralelo

- O protocolo vale por `task issue`, nao pela identidade da IA ou da pessoa.
- Regra central: `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`.
- Se outra IA ou pessoa assumir a task, atualize primeiro o `Owner atual` da
  issue e so depois continue implementando.
- Se duas tasks tiverem write-set relevante em comum, uma delas deve:
  - esperar;
  - reduzir escopo;
  - ou ser marcada como dependente.
- Registre a dependencia ou a disputa de write-set na propria issue antes de
  continuar.
- Durante trabalho paralelo, interfaces publicas seguem `additive-only` por
  default.
- Mudanca breaking em API/contrato so pode acontecer em task propria,
  classificada como `risk:contract-sensitive`, com coordenacao explicita e merge
  serializado.

## Child tasks entre lanes

- Se uma lane precisar de mudanca em write-set de outra lane, nao use pedido
  informal no chat como mecanismo de execucao. Abra uma child task formal na
  lane dona do write-set.
- Toda child task precisa registrar no corpo da issue:
  - `Task mae`
  - `Lane solicitante`
  - `Criterio de consumo`
- Toda task mae precisa registrar `Tasks filhas` no proprio corpo da issue.
- A child task continua obedecendo `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`
  e fecha pela sua propria PR.
- Enquanto a child task estiver aberta ou em revisao, a task mae fica
  `status:blocked`.
- Quando a child task ja tiver sido entregue/mergeada mas a lane solicitante
  ainda nao tiver validado ou consumido a entrega, a task mae vira
  `status:awaiting-consumption`.
- So a lane solicitante pode marcar a entrega como consumida e tirar a task mae
  de `status:blocked` ou `status:awaiting-consumption`.
- `Lane solicitante` deve coincidir com a `Lane oficial` da task mae.

## Critical paths

- A fonte oficial de paths sensiveis vive em
  `.github/guardrails/path-policy.json`.
- Classes oficiais:
  - `shared-governance`
  - `critical-bootstrap`
  - `critical-runtime`
  - `critical-contract`
- Paths classificados exigem, no minimo, o risco e a lane permitidos pela
  policy versionada.
- Se um arquivo nao estiver coberto pela policy nem pela allowlist da lane,
  classifique o path antes de abrir PR.
- `shared-governance` pode acompanhar qualquer lane, mas nao autoriza misturar
  frontend e backend na mesma task.

## Leitura obrigatoria por area

Antes de tocar qualquer arquivo dentro das areas abaixo, leia o documento
indicado. Nao assuma contexto de arquitetura sem ter lido.

| Area | Leitura obrigatoria |
|---|---|
| `apps/web` | `docs/INTERFACE_MAP.md` — rotas existentes, status e endpoints consumidos |
| `apps/api` | `docs/INTERFACE_MAP.md` + `docs/V2_API_CONTRACT.md` — contratos e quem consome cada endpoint |
| `src/` | `docs/CONTEXT.md` — dominio Python, regras de negocio e convencoes criticas |
| `docs/SITEMAP.MD` | `docs/INTERFACE_MAP.md` — o sitemap e derivado do mapa de interface |

## Onde registrar o que

- Estado tecnico atual e sessoes: `docs/AGENTS.md`
- Decisoes duraveis: `docs/decisions/`
- Regras de lanes/worktrees/critical paths: `docs/governance/parallel-lanes.md`
- Roadmap de Student Pack e backlog resumido: `docs/STUDENT_PACK_PLAN.md`
- Mapa de rotas x endpoints: `docs/INTERFACE_MAP.md`
- Release notes: `docs/releases/`

## Antes de marcar como concluido

- Execute as validacoes relevantes.
- Atualize a issue com a evidencia principal.
- Confirme que a PR referencia a mesma issue da branch.
- Confirme que a worktree da task esta registrada na issue.
- Nao pare com a PR apenas aberta: confirme checks verdes e merge real.
- Confirme que a issue fechou e que a branch remota foi removida, quando
  aplicavel.
