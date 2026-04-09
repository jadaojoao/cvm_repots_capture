# Trabalho Paralelo com Lanes, Worktrees e Critical Paths

## Resumo

O repositorio opera com tres frentes oficiais:

- `lane:frontend`
- `lane:backend`
- `lane:ops-quality`

Regra central: `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`.

O repo raiz permanece em `master`. Toda task executavel roda em uma worktree
dedicada em `.claude/worktrees/<lane>/<issue-number>-<slug>/`.

## Check inicial por chat

Antes de iniciar trabalho executavel em qualquer chat, a IA deve verificar:

- tasks abertas da propria `lane:*`
- child tasks recebidas de outras lanes na propria lane
- child tasks que sua lane abriu para outras lanes
- PRs abertas ligadas a essas issues, principalmente quando houver entrega
  pronta aguardando consumo

Se existir entrega pendente de consumo para a lane atual, isso deve ser tratado
antes de abrir nova frente dependente de outra lane.

## Lanes oficiais

### `lane:frontend`

- ownership principal: `apps/web/**`
- pode tocar docs internos do web app
- pode tocar `shared-governance` quando necessario

### `lane:backend`

- ownership principal: `apps/api/**`, `src/**`, `desktop/**`, `dashboard/**`,
  `tests/**`, `apps/api/tests/**`
- pode tocar `critical-contract`
- pode tocar `shared-governance` quando necessario

### `lane:ops-quality`

- ownership principal: `.github/**`, `docs/**`, root docs e scripts
  operacionais
- pode tocar `critical-bootstrap`
- pode tocar `shared-governance`

Se uma entrega realmente exigir frontend e backend ao mesmo tempo, quebre em
child tasks. Nao use uma task gigante multi-lane.

## Fluxo oficial por task

1. Localizar ou criar uma `task issue`
2. Declarar:
   - `Owner atual`
   - `Lane oficial`
   - `Workspace da task`
   - `Write-set esperado`
   - `Classificacao de risco`
3. Criar a worktree da task:
   - branch `task/<issue-number>-<slug>`
   - path `.claude/worktrees/<lane>/<issue-number>-<slug>/`
4. Implementar somente dentro dessa worktree
5. Abrir uma unica PR oficial para a task com `Closes #<issue-number>`
6. Validar e atualizar a issue
7. Concluir a PR com `scripts/pr_complete.ps1 -Pr <numero>` ou fluxo
   equivalente
8. Remover a worktree da task

## Handoff entre IAs ou humanos

- Se outra pessoa ou IA assumir a task, atualize primeiro o `Owner atual`.
- A task continua usando a mesma branch e a mesma PR oficial.
- O handoff nao cria uma segunda branch nem uma segunda PR para a mesma issue.
- O workspace da task continua sendo a referencia de onde o trabalho ativo vive.

## Child tasks entre lanes

Quando uma lane precisar de mudanca em write-set de outra lane, a delegacao vira
uma child task formal.

### Metadados obrigatorios

- Na task mae:
  - `Tasks filhas`
- Na child task:
  - `Task mae`
  - `Lane solicitante`
  - `Criterio de consumo`

`Lane solicitante` da child task deve coincidir com a `Lane oficial` da task
mae.

### Fluxo

1. A lane solicitante identifica que o write-set pertence a outra lane.
2. Ela abre uma child task formal na lane dona do write-set.
3. A task mae registra a child task em `Tasks filhas`.
4. A task mae fica `status:blocked` enquanto a child task estiver aberta ou com
   PR em revisao.
5. A child task segue o fluxo normal: branch propria, worktree propria, PR
   propria e merge proprio.
6. Quando a child task for entregue e a lane solicitante ainda nao tiver
   validado/consumido a mudanca, a task mae vira
   `status:awaiting-consumption`.
7. So a lane solicitante pode consumir a entrega e tirar a task mae de
   `status:blocked` ou `status:awaiting-consumption`.

### Regra dura

- Pedido entre lanes sem issue formal nao conta como handoff valido.
- Child task nao compartilha branch, worktree nem PR com a task mae.
- A task mae nao volta para `status:in-progress` ate a lane solicitante
  confirmar o consumo da entrega.

## Critical paths

A fonte oficial de verdade e `.github/guardrails/path-policy.json`.

Classes:

- `shared-governance`
  - docs e arquivos de governanca compartilhados
  - risco minimo: `risk:shared`
- `critical-bootstrap`
  - scripts que sobem, validam ou checam o ambiente
  - owner lane padrao: `ops-quality`
  - excecao permitida: `backend` com `risk:shared`
- `critical-runtime`
  - arquivos que podem quebrar runtime Python, bootstrap ou query core
  - lane permitida: `backend`
  - risco minimo: `risk:shared`
- `critical-contract`
  - rotas/presenters da API e contrato publico documentado
  - lane permitida: `backend`
  - risco minimo: `risk:contract-sensitive`

Regras duras:

- `critical-contract` exige PR em draft na abertura e secao de compatibilidade.
- `critical-runtime` e `critical-bootstrap` exigem pelo menos `risk:shared`.
- `shared-governance` pode acompanhar qualquer lane, mas nao libera misturar
  `apps/web/**` com `src/**` ou `apps/api/**` na mesma PR.
- Se um arquivo nao estiver coberto pela policy ou pela allowlist da lane, ele
  deve ser classificado antes de a PR ser aprovada.

## Worktrees

Scripts oficiais:

- `scripts/worktree_create.ps1`
- `scripts/worktree_status.ps1`
- `scripts/worktree_remove.ps1`
- `scripts/pr_complete.ps1`

Boas praticas:

- mantenha o repo raiz estavel em `master`
- abra uma segunda janela do editor para a worktree da task
- nao reuse a mesma worktree para duas tasks diferentes
- nao remova worktree com branch nao mergeada sem `-Force`
- se o branch-base local estiver desatualizado, atualize o base ou use `-Force`;
  o helper deve falhar com mensagem clara, nao com erro interno do PowerShell
- nao considere a task concluida com a PR apenas aberta; confirme merge e issue
  fechada
- se o branch-base local estiver desatualizado, atualize o base ou use `-Force`;
  o helper deve falhar com mensagem clara, nao com erro interno do PowerShell

## Exemplos

### PR valida

- issue `lane:frontend`
- worktree `.claude/worktrees/frontend/31-home-hero/`
- branch `task/31-home-hero`
- arquivos alterados em `apps/web/**`
- nenhuma PR concorrente para `#31`

### PR invalida

- issue `lane:frontend`
- branch `task/32-mixed-change`
- arquivos alterados em `apps/web/**` e `src/read_service.py`
- resultado esperado: falha do guardrail por mistura de frontend e backend

### Child task valida

- task mae `#40` em `lane:backend`, listando `#41` em `Tasks filhas`
- child task `#41` em `lane:frontend`
- child task registra `Task mae: #40`, `Lane solicitante: backend` e
  `Criterio de consumo`
- task `#40` fica `status:blocked` enquanto `#41` estiver aberta e muda para
  `status:awaiting-consumption` depois da entrega, ate o backend consumir a
  mudanca

## CODEOWNERS

`CODEOWNERS` pode ser adicionado depois para visibilidade e revisao por dominio.
Ele nao e o mecanismo principal de enforcement enquanto varias IAs operarem sob
a mesma conta humana.
