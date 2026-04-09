# Trabalho Paralelo com Lanes, Worktrees e Critical Paths

## Resumo

O repositorio opera com tres frentes oficiais:

- `lane:frontend`
- `lane:backend`
- `lane:ops-quality`

Regra central: `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`.

O repo raiz permanece em `master`. Toda task executavel roda em uma worktree
dedicada em `.claude/worktrees/<lane>/<issue-number>-<slug>/`.

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
6. Validar, atualizar a issue e fazer `squash merge`
7. Remover a worktree da task

## Handoff entre IAs ou humanos

- Se outra pessoa ou IA assumir a task, atualize primeiro o `Owner atual`.
- A task continua usando a mesma branch e a mesma PR oficial.
- O handoff nao cria uma segunda branch nem uma segunda PR para a mesma issue.
- O workspace da task continua sendo a referencia de onde o trabalho ativo vive.

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

Boas praticas:

- mantenha o repo raiz estavel em `master`
- abra uma segunda janela do editor para a worktree da task
- nao reuse a mesma worktree para duas tasks diferentes
- nao remova worktree com branch nao mergeada sem `-Force`

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

## CODEOWNERS

`CODEOWNERS` pode ser adicionado depois para visibilidade e revisao por dominio.
Ele nao e o mecanismo principal de enforcement enquanto varias IAs operarem sob
a mesma conta humana.
