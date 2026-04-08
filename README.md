# CVM Reports Capture

Projeto para captura, tratamento e consulta de demonstracoes financeiras da CVM, com persistencia em SQLite/PostgreSQL, app desktop operacional em PyQt6, dashboard analitico em Streamlit e API read-only da Fase 1 da V2 em FastAPI.

> Este repositorio tem proposito duplo: manter o sistema operacional atual funcionando e servir como trilha de aprendizado para evolui-lo rumo a uma web app mais proxima de producao. A direcao da V2 esta registrada em [docs/decisions/0002-student-pack-v2-stack.md](docs/decisions/0002-student-pack-v2-stack.md), no [docs/STUDENT_PACK_PLAN.md](docs/STUDENT_PACK_PLAN.md), no roadmap [docs/WEBAPP_TRANSFORMATION_PLAN.md](docs/WEBAPP_TRANSFORMATION_PLAN.md), no guia da fase [docs/V2_PHASE1_BACKEND.md](docs/V2_PHASE1_BACKEND.md) e no contrato [docs/V2_API_CONTRACT.md](docs/V2_API_CONTRACT.md).

## Estrutura principal

- `desktop/cvm_pyqt_app.py`: [OFICIAL] app desktop em PyQt6 para atualizacao local e operacao do refresh.
- `main.py`: CLI suportada para rodar o scraper de forma pontual.
- `apps/api/`: API `FastAPI` read-only da Fase 1 da V2.
- `src/`: pipeline de captura, padronizacao, consulta e exportacao.
- `scripts/`: scripts auxiliares, setup de banco, batches e validacoes.
- `data/`: entrada, metadados, cache e banco SQLite local (`cvm_financials.db`).
- `output/`: artefatos gerados, incluindo relatorios e logs.
- `dashboard/`: aplicacao analitica em Streamlit com 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.
- `docs/`: documentacao de referencia (`CONTEXT.md`, `AGENTS.md`, `AUDIT.md`, `STUDENT_PACK_PLAN.md`, `WEBAPP_TRANSFORMATION_PLAN.md`, `V2_PHASE1_BACKEND.md`, `V2_API_CONTRACT.md`).

## Fluxo recomendado

1. Instalar dependencias da V1:
```bash
pip install -r requirements.txt
```

2. Se voce tambem vai rodar a API da V2:
```bash
pip install -r apps/api/requirements-dev.txt
```

3. Validar ambiente e diagnostico de bootstrap:
```bash
python scripts/runtime_doctor.py --require-canonical
```

4. Inicializar o banco em uma maquina nova ou apos migracao:
```bash
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

5. Atualizar dados pela interface operacional principal:
```bash
python desktop/cvm_pyqt_app.py
```

6. Alternativa para coleta pontual via CLI headless:
```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated --skip_complete
```

7. Alternativas para atualizacao em lote:
```bash
python scripts/batch_completo.py --dry-run
python scripts/atualizar_todos.py --anos 2024 2025
```

8. Subir o dashboard analitico read-only:
```bash
streamlit run dashboard/app.py
```

9. Subir a API read-only da Fase 1 da V2:
```bash
uvicorn apps.api.app.main:app --reload
```

Docs da API:
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

> Observacao: `scripts/gerar_base_analitica.py`, `scripts/calc_financial_kpis.py` e `scripts/smoke_validate.py` continuam uteis em fluxos especificos, mas nao sao pre-requisitos do caminho principal PyQt6 -> banco -> dashboard/API.

## Contrato operacional atual

- Configuracao centralizada em `src/settings.py`, baseada em env vars e caminhos canonicos.
- Diagnostico de startup em `src/startup.py`, consumido por CLI, desktop, dashboard, scripts e API.
- Refresh headless em `src/refresh_service.py`, que virou o caminho comum para CLI, workers PyQt e automacoes.
- Leitura headless em `src/read_service.py`, que virou o contrato consumido pelo dashboard e pela API.
- `apps/api` e a superficie HTTP oficial da Fase 1 da V2. O frontend futuro deve consumir a API, nao reimplementar queries.

Variaveis principais em `.env.example`:
- `DATABASE_URL` para PostgreSQL
- `SQLITE_PATH` para SQLite local
- `CVM_DATA_DIR`, `CVM_OUTPUT_DIR`, `CVM_LOG_DIR`, `CVM_CACHE_DIR`
- `CVM_COMPANY_LIST_TIMEOUT`, `CVM_DOWNLOAD_TIMEOUT`
- `UPDATER_SKIP_COMPLETE`, `UPDATER_FAST_LANE`, `UPDATER_FORCE_REFRESH`

## Scripts de verificacao

Validacoes focadas em workbooks/exportacao:

```bash
python scripts/verify_consolidation.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/verify_line_id_base.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/quick_verify.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/final_verification.py --xlsx output/reports/PETROBRAS_financials.xlsx
```

Smoke tests:

```bash
pytest tests/ -q
pytest apps/api/tests -q
```

Diagnostico adicional:

```bash
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
python scripts/db_portability_smoke.py --write-check
python scripts/canonicalize_data_layout.py
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

## Interfaces oficiais

### 1. App Desktop PyQt6

Modo inteligente para atualizacao:
- ranking por importancia (40% market cap + 60% liquidez),
- combinado com desatualizacao por anos,
- lista revisavel antes de iniciar,
- paralelismo configuravel (`2` a `8` workers),
- barra de progresso total do lote,
- botao para abrir o dashboard local.

```powershell
python desktop/cvm_pyqt_app.py
```

### 2. Dashboard Analitico

Aplicacao read-only para consulta e exportacao do que ja esta no banco:
- busca empresa por nome, ticker ou codigo CVM,
- seleciona intervalo de anos,
- mostra 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.

```powershell
streamlit run dashboard/app.py
```

### 3. API V2 Phase 1

Aplicacao `FastAPI` read-only em `apps/api`, criada para servir a futura web app:
- `GET /health`
- `GET /companies`
- `GET /companies/{cd_cvm}`
- `GET /companies/{cd_cvm}/years`
- `GET /companies/{cd_cvm}/statements`
- `GET /companies/{cd_cvm}/kpis`
- `GET /refresh-status`
- `GET /base-health`

```powershell
uvicorn apps.api.app.main:app --reload
```

## Observacoes

- Prefira `desktop/cvm_pyqt_app.py` como interface operacional principal.
- Prefira `src/refresh_service.py` e `src/read_service.py` como contratos de nucleo ao criar novas interfaces.
- Prefira `apps/api` como superficie HTTP oficial da Fase 1 da V2.
- Use `scripts/db_portability_smoke.py` para validar o backend de banco antes de subir uma API web.
- Use `scripts/canonicalize_data_layout.py` para auditar ou limpar arquivos fora do layout canonico `data/input/raw|processed`.
- O dashboard atual possui 3 abas. Referencias antigas a 9 abas nos docs estao desatualizadas.
- Erros e execucoes de refresh ficam em `output/logs/`, incluindo `refresh_runs.jsonl`.
