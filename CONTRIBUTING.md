# Contributing

## Issue-first workflow

- Todo trabalho executavel deve nascer ou estar vinculado a uma `task issue`.
- A issue deve ter exatamente um label `lane:*` e declarar:
  - `Owner atual`
  - `Lane oficial`
  - `Workspace da task`
  - `Write-set esperado`
  - `Classificacao de risco`
- Use branch no formato `task/<issue-number>-<slug>`.
- Trabalhe em uma worktree dedicada em
  `.claude/worktrees/<lane>/<issue-number>-<slug>/`.
- O repo raiz permanece em `master`.
- Abra PR com `Closes #<issue-number>`.
- Quando a task estiver pronta, use `scripts/pr_complete.ps1 -Pr <numero>` ou
  fluxo equivalente para esperar checks verdes e concluir o merge real.
- Atualize checklist, status e evidencias na issue antes do merge.
- Faca `commit` em checkpoints verificaveis, `push` ao finalizar um checkpoint
  remoto e `merge` para `master` quando a task estiver concluida e os checks
  estiverem verdes.
- Preferencia de merge: `squash merge`.

## Lanes oficiais

- `lane:frontend`: `apps/web/**`
- `lane:backend`: `apps/api/**`, `src/**`, `desktop/**`, `dashboard/**`,
  `tests/**`, `apps/api/tests/**`
- `lane:ops-quality`: `.github/**`, `docs/**`, root docs e scripts
  operacionais

Se a entrega realmente tocar duas lanes de produto, quebre em tasks separadas.

## Paralelismo e critical paths

- O protocolo e por task, nao por IA.
- Regra central: `1 task = 1 owner = 1 branch = 1 worktree = 1 PR`.
- `risk:safe`: write-set isolado.
- `risk:shared`: toca arquivos compartilhados ou paths criticos de runtime;
  a PR deve abrir em draft.
- `risk:contract-sensitive`: toca contratos publicos e exige compatibilidade
  explicita.
- Paths criticos sao governados por `.github/guardrails/path-policy.json`.
- Em trabalho paralelo, contratos publicos seguem `additive-only` por default.
- A task so e concluida depois de PR mergeada e issue fechada.

## Tipos de issue

- `Epic`: agrega contexto, objetivo e tasks filhas.
- `Task`: unidade executavel de trabalho.

## Fonte de verdade

- Backlog oficial: GitHub Issues
- Estado tecnico e historico: `docs/AGENTS.md`
- Regras para agentes e worktrees: `AGENTS.md`
- Regras detalhadas de lanes: `docs/governance/parallel-lanes.md`
