# CVM Analytics Web

Primeiro slice web da V2, construido em `Next.js`, consumindo apenas a API read-only em `apps/api`.

## Rotas desta fase

- `/`
- `/empresas`
- `/empresas/[cd_cvm]`

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

- O app usa `Server Components` por default.
- Componentes client ficam restritos a busca, filtros e mudancas de URL.
- O autocomplete da home usa `app/api/company-search/route.ts` como proxy interno.
- A fonte de verdade da aplicacao continua sendo a API V2.
