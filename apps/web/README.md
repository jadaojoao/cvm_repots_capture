# CVM Analytics Web

Primeiro slice web da V2, construido em `Next.js`, consumindo apenas a API
read-only em `apps/api`.

## Stack

- Next.js 16.2.2 com App Router, React 19 e Turbopack
- Tailwind CSS v4 com tokens OkLch em `app/globals.css`
- `@base-ui/react` como primitive headless principal
- Material Symbols Outlined como sistema de icones
- Componentes 21st.dev adaptados ao contexto do produto
- `next-themes` para suporte a light/dark mode
- `components/providers.tsx` com ThemeProvider e TooltipProvider

## Rotas de produto

- `/` - home com busca principal e atalhos para a navegacao inicial
- `/empresas` - diretorio com busca, filtro setorial e paginacao por URL
- `/empresas/[cd_cvm]` - detalhe da companhia com overview e demonstracoes

## Rota de tooling

- `/design-system` - catalogo interno de tokens, primitives e recipes

## Design System Adoption

O ciclo atual estabiliza a base visual antes de expandir produto:

- `app/globals.css` concentra tokens oficiais e aliases validos
- `components/shared/design-system-recipes.tsx` define recipes reutilizaveis
- Home, diretorio e detalhe compartilham page shell, cards, chips e headings
- Estados globais de loading, error e not-found seguem o mesmo vocabulio visual
- `/design-system` continua como ferramenta interna e nao entra na navegacao principal

Estado atual da adocao:

- Base consolidada: tokens, recipes, surfaces e tabela compartilhada
- Produto migrado: `/`, `/empresas`, `/empresas/[cd_cvm]`
- Documentacao interna atualizada em `app/design-system/PROGRESS.md`
- Guia operacional da migracao em `docs/design-system-adoption.md`

## Como rodar

Suba a API em outro terminal:

```powershell
uvicorn apps.api.app.main:app --reload
```

Depois rode o web app:

```bash
npm install
npx playwright install chromium
npm run dev
```

Se necessario, crie `apps/web/.env.local` a partir de `.env.example`:

```bash
cp .env.example .env.local
```

## Variaveis

- `API_BASE_URL=http://127.0.0.1:8000`

## Validacao

```bash
npm run lint
npm run typecheck
npm run build
npm run test:unit
npm run test:e2e
```

## Observacoes

- O app usa Server Components por padrao; `"use client"` fica restrito a interacao e URL state.
- O autocomplete da home usa `app/api/company-search/route.ts` como proxy interno.
- A fonte de verdade da aplicacao continua sendo a API V2.
- O Design System documenta o produto; nao substitui a navegacao de produto.
- O layout raiz usa um video ambiente sutil apenas na faixa superior da pagina, com overlay escuro para preservar contraste.
