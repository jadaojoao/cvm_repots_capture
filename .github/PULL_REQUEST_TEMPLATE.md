## Issue

Closes #

## Resumo

- descreva o escopo principal desta PR

## Paralelismo

- lane da task: `lane:frontend | lane:backend | lane:ops-quality`
- worktree usada: `.claude/worktrees/<lane>/<issue-number>-<slug>/`
- esta e a unica PR oficial da task: `sim | nao`
- risco da task: `risk:safe | risk:shared | risk:contract-sensitive`
- task mae: `#<numero> | n/a`
- lane solicitante: `lane:frontend | lane:backend | lane:ops-quality | n/a`
- consumo registrado na task mae: `sim | nao | n/a`
- write-set principal:
- coordenacao com outras tasks/PRs:

## Compatibilidade

- politica aplicada: `additive-only | breaking-approved | n/a`
- impacto em API, schema ou docs publicos:

## Validacao

- [ ] validacoes executadas e registradas abaixo

```text
# comandos executados
```

## Checklist

- [ ] a branch segue `task/<issue-number>-<slug>`
- [ ] a issue vinculada esta atualizada com checklist/status/evidencias
- [ ] a issue vinculada registra owner atual, lane oficial, workspace da task, write-set esperado e `risk:*`
- [ ] docs relevantes foram atualizados quando necessario
- [ ] lane da task e worktree oficial foram registradas nesta PR
- [ ] se a task for `risk:shared` ou `risk:contract-sensitive`, a PR abriu em draft
- [ ] se a task for `risk:contract-sensitive`, a compatibilidade foi revisada e documentada
- [ ] PR em draft apenas enquanto o trabalho ou as validacoes ainda estiverem incompletos
- [ ] checks obrigatorios verdes ou helper de conclusao acionado para aguardar
- [ ] pronto para `squash merge` em `master` quando os checks estiverem verdes
- [ ] nao considerar a task concluida ate confirmar merge, issue fechada e branch remota removida quando aplicavel
