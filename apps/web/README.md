# CVM Analytics Web

Primeiro slice web da V2, construido em `Next.js`, consumindo apenas a API read-only em `apps/api`.

## Stack

- Next.js 16.2.2 (App Router, React 19, Turbopack)
- Tailwind CSS v4 (tokens OkLch, sem tailwind.config.js)
- `@base-ui/react 1.3.0` como headless primitive principal
- Material Symbols Outlined weight 200 (Google Fonts) como sistema de icones
- Componentes 21st.dev via shadcn CLI (coss.com, reaviz, isaiahbjork, larsen66...)
- next-themes para dark/light mode
- `components/providers.tsx` — ThemeProvider + TooltipProvider

## Rotas de produto

- `/` — Home com busca principal
- `/empresas` — Hub com busca, filtro de setor e paginacao por URL
- `/empresas/[cd_cvm]` — Detalhe: Visao Geral + Demonstracoes (DRE, BPA, BPP, DFC)

## Rota de tooling

- `/design-system` — Showcase de tokens e componentes (24 secoes, sem autenticacao)

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
npm run test:e2e
```

## Observacoes

- O app usa `Server Components` por default; `"use client"` fica restrito a interacao e URL state.
- O autocomplete da home usa `app/api/company-search/route.ts` como proxy interno.
- A fonte de verdade da aplicacao continua sendo a API V2.
- `/design-system` e uma rota de tooling — nao faz parte do sitemap de produto.
