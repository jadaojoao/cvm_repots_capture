# Design System Adoption

## Objetivo

Consolidar a V2 web como um produto coerente entre home, diretorio e detalhe de
empresa, usando um conjunto pequeno de tokens e recipes compartilhados.

## Escopo deste ciclo

- Base visual
- Home `/`
- Diretorio `/empresas`
- Detalhe `/empresas/[cd_cvm]`
- Catalogo interno `/design-system`

## Fora de escopo

- Novas rotas publicas
- Redesign profundo da arquitetura das paginas
- Mudancas de contrato HTTP
- Auditoria completa de dark mode
- Portar demos de terceiros sem adaptacao semantica

## Tokens oficiais

Os tokens vivem em `app/globals.css`.

### Cor

- `--background`
- `--foreground`
- `--primary`
- `--secondary`
- `--muted`
- `--accent`
- `--destructive`
- `--border`
- `--chart-1` a `--chart-5`

### Tipografia

- `--font-heading`
- `--font-body`
- `--font-mono`

### Superficie

- `--radius`
- sombras e gradientes derivados nas classes do app

## Recipes aprovados

Os recipes vivem em `components/shared/design-system-recipes.tsx`.

### `PageShell`

Uso:

- Estrutura principal das rotas de produto
- Controle de largura, densidade vertical e respiro lateral

### `SurfaceCard`

Uso:

- Blocos principais de conteudo
- Hero shell, cards de apoio, estados de erro e superficies elevadas

Variantes:

- `default`
- `subtle`
- `muted`
- `hero`
- `inset`

### `InfoChip`

Uso:

- Metadados de baixo peso
- Status leve
- Badges de contexto

### `SectionHeading`

Uso:

- Hero textual
- Cabecalhos de secao
- Blocos com eyebrow, titulo, descricao e meta

## Mapa pagina -> recipes

### Home `/`

- `PageShell`
- `SurfaceCard`
- `InfoChip`
- `SectionHeading`

### Diretorio `/empresas`

- `PageShell`
- `SurfaceCard`
- `InfoChip`
- `SectionHeading`
- tabela/listagem com superficie consistente

### Detalhe `/empresas/[cd_cvm]`

- `PageShell`
- `SurfaceCard`
- `InfoChip`
- `SectionHeading`
- tabs, seletor de anos e tabelas harmonizados

### Estados globais

- `app/loading.tsx`
- `app/error.tsx`
- `app/not-found.tsx`

Todos seguem o mesmo vocabulario de superficie, tipografia e acao.

## Bugs corrigidos neste ciclo

- Mojibake em paginas e docs mais visiveis
- Metadata incompleta do `/design-system`
- Aliases invalidos em `app/globals.css`
- Inconsistencia de densidade e superficie entre as rotas de produto
- Excesso de destaque visual em areas ainda indisponiveis na navegacao

## Regras para proximos ciclos

- Preferir recipes compartilhados antes de criar estilos locais novos
- Tratar `/design-system` como fonte de referencia do produto
- Introduzir novo primitive so quando um recipe nao for suficiente
- Validar mudancas com lint, typecheck, build e Playwright
