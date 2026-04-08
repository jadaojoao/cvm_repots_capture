# CVM Reports Capture

Projeto para captura, tratamento e consulta de demonstracoes financeiras da CVM, com persistencia em SQLite/PostgreSQL, app desktop operacional em PyQt6, dashboard analitico em Streamlit, API read-only da V2 em FastAPI e primeiro slice web em Next.js.

> Este repositorio tem proposito duplo: manter o sistema operacional atual funcionando e servir como trilha de aprendizado para evolui-lo rumo a uma web app mais proxima de producao. A direcao da V2 esta registrada em [docs/decisions/0002-student-pack-v2-stack.md](docs/decisions/0002-student-pack-v2-stack.md), [docs/STUDENT_PACK_PLAN.md](docs/STUDENT_PACK_PLAN.md), [docs/WEBAPP_TRANSFORMATION_PLAN.md](docs/WEBAPP_TRANSFORMATION_PLAN.md), [docs/V2_PHASE1_BACKEND.md](docs/V2_PHASE1_BACKEND.md), [docs/V2_API_CONTRACT.md](docs/V2_API_CONTRACT.md) e [docs/V2_PHASE2_WEB_SLICE.md](docs/V2_PHASE2_WEB_SLICE.md).

## Estrutura principal

- `desktop/cvm_pyqt_app.py`: interface operacional principal para atualizacao local.
- `main.py`: CLI suportada para refresh pontual.
- `apps/api/`: API `FastAPI` read-only da V2.
- `apps/web/`: primeiro slice web da V2 em `Next.js`.
- `src/`: nucleo de captura, padronizacao, leitura, refresh e exportacao.
- `scripts/`: setup de banco, batches, diagnosticos e validacoes.
- `dashboard/`: dashboard analitico em Streamlit.
- `data/`: banco SQLite local, insumos e caches.
- `output/`: logs e artefatos gerados.
- `docs/`: contexto, roadmap e contratos da V2.

## Fluxo recomendado

1. Instalar dependencias Python:

```bash
pip install -r requirements.txt
pip install -r apps/api/requirements-dev.txt
```

2. Se for usar a web:

```bash
cd apps/web
npm install
```

3. Validar ambiente:

```bash
python scripts/runtime_doctor.py --require-canonical
```

4. Inicializar banco em maquina nova:

```bash
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

5. Atualizar dados:

```bash
python desktop/cvm_pyqt_app.py
```

6. Alternativas headless:

```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated --skip_complete
python scripts/batch_completo.py --dry-run
python scripts/atualizar_todos.py --anos 2024 2025
```

7. Subir superficies de leitura:

```bash
streamlit run dashboard/app.py
uvicorn apps.api.app.main:app --reload
cd apps/web && npm run dev
```

## Interfaces oficiais

### 1. App Desktop PyQt6

Interface operacional principal para atualizar a base local. Reaproveita `src/refresh_service.py` e concentra ranking, lotes e saude da base.

```powershell
python desktop/cvm_pyqt_app.py
```

### 2. Dashboard Streamlit

Aplicacao read-only para consulta do que ja esta no banco, com 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.

```powershell
streamlit run dashboard/app.py
```

### 3. API V2

Aplicacao `FastAPI` read-only em `apps/api`, thin wrapper sobre `src/read_service.py`.

Endpoints principais:
- `GET /health`
- `GET /companies`
- `GET /companies/filters`
- `GET /companies/{cd_cvm}`
- `GET /companies/{cd_cvm}/years`
- `GET /companies/{cd_cvm}/statements`
- `GET /companies/{cd_cvm}/kpis`
- `GET /refresh-status`
- `GET /base-health`

```powershell
uvicorn apps.api.app.main:app --reload
```

Docs:
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

### 4. Web App V2 Slice 1

Aplicacao `Next.js` em `apps/web`, consumindo exclusivamente a API V2.

Rotas entregues:
- `/`
- `/empresas`
- `/empresas/[cd_cvm]`

```powershell
cd apps/web
Copy-Item .env.example .env.local
npm run dev
```

Variavel principal:
- `API_BASE_URL=http://127.0.0.1:8000`

## Contrato operacional atual

- Configuracao centralizada em `src/settings.py`.
- Diagnostico de startup em `src/startup.py`.
- Refresh headless em `src/refresh_service.py`.
- Leitura headless em `src/read_service.py`.
- `apps/api` e a superficie HTTP oficial da V2.
- `apps/web` e o cliente web oficial do slice `Home -> Empresas -> Empresa`.

## Validacao

```bash
pytest tests/ -q
pytest apps/api/tests -q
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
python scripts/db_portability_smoke.py --write-check
cd apps/web && npm run lint
cd apps/web && npm run typecheck
cd apps/web && npm run build
cd apps/web && npm run test:e2e
```

Validacao PostgreSQL real:

```bash
python scripts/runtime_doctor.py --database-url postgresql://user:pass@host:5432/db --require-db --table financial_reports --table companies
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

## Observacoes

- Prefira `desktop/cvm_pyqt_app.py` como interface operacional principal.
- Prefira `src/refresh_service.py` e `src/read_service.py` como contratos de nucleo.
- O frontend da V2 deve consumir a API, nao reimplementar queries do `src/`.
- O dashboard atual continua sendo fallback read-only durante a transicao.
- Erros e execucoes de refresh ficam em `output/logs/`, incluindo `refresh_runs.jsonl`.
