# AGENTS.md

Contrato operacional para qualquer agente ou pessoa que trabalhe neste
repositorio.

## Fonte de verdade

- O backlog oficial vive em `GitHub Issues`.
- `docs/AGENTS.md` registra estado atual e historico de sessoes. Nao use esse
  arquivo como lista viva de tarefas.
- `docs/STUDENT_PACK_PLAN.md` resume o roadmap e aponta para issues/milestones.
  Nao replique nele o backlog operacional dia a dia.

## Fluxo obrigatorio

1. Localize uma `task issue` aberta antes de alterar qualquer arquivo versionado.
2. Se a task ainda nao existir, crie uma issue a partir do template correto.
3. Garanta que a issue tenha, no minimo:
   - `kind:task`
   - um label `status:*`
   - um label `priority:*`
   - um label `area:*`
   - um label `risk:*`
4. Ao iniciar, marque a task como `status:in-progress` e atualize o checklist do
   corpo da issue.
5. Trabalhe em branch no formato `task/<issue-number>-<slug>`.
6. Abra PR com `Closes #<issue-number>` no corpo.
7. Antes de encerrar, atualize checklist, evidencias e docs afetados.
8. A task fecha com o merge da PR. Epics fecham manualmente.

## Regra de commit, push e merge

- Nao deixe trabalho concluido apenas localmente.
- Faca `commit` quando houver um checkpoint coerente e verificavel:
  - uma parte funcional completa;
  - uma correção validada;
  - ou antes de uma mudanca mais arriscada que mereca rollback claro.
- Faca `push` quando:
  - existir um commit verificavel que nao deve ficar so local;
  - a task precisar de backup remoto, handoff ou atualizacao da PR;
  - o fim da sessao deixar trabalho relevante em andamento.
- Abra ou atualize a PR assim que a branch estiver revisavel, mesmo em draft.
- Quando a task estiver completa e as validacoes relevantes tiverem passado:
  - atualize a issue;
  - marque a PR como pronta;
  - faca merge para `master` se nao houver bloqueio explicito do usuario.
- Preferencia de merge: `squash merge`.
- Depois do merge:
  - confirme o fechamento da task;
  - confirme que a branch remota sera removida automaticamente.

## Regras para issues

- `Epics` agregam contexto, objetivos e links para tasks filhas.
- `Tasks` sao a unidade executavel de trabalho.
- Se uma task crescer demais, abra uma follow-up issue e reduza o escopo da
  issue atual.
- Se um issue estiver defasado, atualize o corpo para refletir apenas o trabalho
  restante ou feche como `superseded`, apontando para o substituto.

## Protocolo de trabalho paralelo

- O protocolo vale por `task issue`, nao pela identidade da IA ou da pessoa.
- Toda task precisa declarar no corpo da issue:
  - `Owner atual`
  - `Write-set esperado`
  - `Classificacao de risco`
- Classificacoes aceitas:
  - `safe`: write-set isolado; pode seguir sem coordenacao especial
  - `shared`: toca arquivos compartilhados; a PR deve abrir em draft
  - `contract-sensitive`: toca contratos publicos; exige PR em draft e revisao
    explicita de compatibilidade
- Se outra IA ou pessoa assumir a task, atualize primeiro o `Owner atual` da
  issue e so depois continue implementando.
- Se duas tasks tiverem write-set relevante em comum, uma delas deve:
  - esperar;
  - reduzir escopo;
  - ou ser marcada como dependente.
- Registre a dependencia ou a disputa de write-set na propria issue antes de
  continuar.
- Arquivos compartilhados padrao:
  - `README.md`
  - `COMO_RODAR.md`
  - `docs/V2_API_CONTRACT.md`
  - `docs/STUDENT_PACK_PLAN.md`
  - `docs/AGENTS.md`
  - `.github/**` quando a mudanca afetar workflow comum
- Durante trabalho paralelo, a regra default para interfaces publicas e
  `additive-only`.
- Mudanca breaking em API/contrato so pode acontecer em task propria,
  classificada como `risk:contract-sensitive`, com coordenacao explicita e merge
  serializado.

## Onde registrar o que

- Estado tecnico atual e sessoes: `docs/AGENTS.md`
- Decisoes duraveis: `docs/decisions/`
- Roadmap de Student Pack e backlog resumido: `docs/STUDENT_PACK_PLAN.md`
- Release notes: `docs/releases/`

## Antes de marcar como concluido

- Execute as validacoes relevantes.
- Atualize a issue com a evidencia principal.
- Confirme que a PR referencia a mesma issue da branch.
- Se a branch estiver pronta, nao pare em "codigo feito": publique e finalize o merge.
