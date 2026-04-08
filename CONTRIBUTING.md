# Contributing

## Issue-first workflow

- Todo trabalho executavel deve nascer ou estar vinculado a uma `task issue`.
- Use branch no formato `task/<issue-number>-<slug>`.
- Abra PR com `Closes #<issue-number>`.
- A task deve declarar `owner atual`, `write-set esperado` e classificacao
  `risk:*`.
- Atualize checklist, status e evidencias na issue antes do merge.
- Faca `commit` em checkpoints verificaveis, `push` ao finalizar um checkpoint remoto e `merge` para `master` quando a task estiver concluida e os checks estiverem verdes.
- Preferencia de merge: `squash merge`.

## Paralelismo

- O protocolo e por task, nao por IA.
- `risk:safe`: write-set isolado.
- `risk:shared`: toca arquivos compartilhados e a PR deve abrir em draft.
- `risk:contract-sensitive`: toca contratos publicos e exige compatibilidade
  explicita.
- Se outra IA ou pessoa assumir a task, atualize a issue antes de continuar.
- Em trabalho paralelo, contratos publicos seguem `additive-only` por default.

## Tipos de issue

- `Epic`: agrega contexto, objetivo e tasks filhas.
- `Task`: unidade executavel de trabalho.

## Fonte de verdade

- Backlog oficial: GitHub Issues
- Estado tecnico e historico: `docs/AGENTS.md`
- Regras para agentes: `AGENTS.md`
