# CVM Reports Capture

Projeto para captura, tratamento e consulta de demonstracoes financeiras da CVM, com persistencia em SQLite/PostgreSQL, app desktop operacional em PyQt6 e dashboard analitico em Streamlit.

> Este repositorio tem proposito duplo: manter o sistema operacional atual funcionando e servir como trilha de aprendizado para evolui-lo rumo a uma web app mais proxima de producao. A direcao da V2 esta registrada em [docs/decisions/0002-student-pack-v2-stack.md](docs/decisions/0002-student-pack-v2-stack.md), no [docs/STUDENT_PACK_PLAN.md](docs/STUDENT_PACK_PLAN.md) e no roadmap de execucao [docs/WEBAPP_TRANSFORMATION_PLAN.md](docs/WEBAPP_TRANSFORMATION_PLAN.md).

## Estrutura principal

- `desktop/cvm_pyqt_app.py`: [OFICIAL] app desktop em PyQt6 para atualizacao local e operacao do refresh.
- `main.py`: CLI suportada para rodar o scraper de forma pontual.
- `src/`: pipeline de captura, padronizacao, consulta e exportacao.
- `scripts/`: scripts auxiliares, setup de banco, batches e validacoes.
- `data/`: entrada, metadados, cache e banco SQLite local (`cvm_financials.db`).
- `output/`: artefatos gerados, incluindo relatórios e logs.
- `dashboard/`: aplicacao analitica em Streamlit com 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.
- `docs/`: documentacao de referencia (`CONTEXT.md`, `AGENTS.md`, `AUDIT.md`, `STUDENT_PACK_PLAN.md`, `WEBAPP_TRANSFORMATION_PLAN.md`).

## Fluxo recomendado (estado atual)

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Validar ambiente e diagnostico de bootstrap:
```bash
python scripts/runtime_doctor.py --require-canonical
```

3. Inicializar o banco em uma maquina nova ou apos migracao:
```bash
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

4. Atualizar dados pela interface operacional principal:
```bash
python desktop/cvm_pyqt_app.py
```

5. Alternativa para coleta pontual via CLI headless:
```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated --skip_complete
```

6. Alternativas para atualizacao em lote:
```bash
python scripts/batch_completo.py --dry-run
python scripts/atualizar_todos.py --anos 2024 2025
```

7. Subir o dashboard analitico read-only:
```bash
streamlit run dashboard/app.py
```

> Observacao: `scripts/gerar_base_analitica.py`, `scripts/calc_financial_kpis.py` e `scripts/smoke_validate.py` continuam uteis em fluxos especificos, mas nao sao pre-requisitos do caminho principal PyQt6 -> banco -> dashboard descrito em `CLAUDE.md`.

## Contrato operacional atual

- Configuracao centralizada em `src/settings.py`, baseada em env vars e caminhos canonicos.
- Diagnostico de startup em `src/startup.py`, consumido por CLI, desktop, dashboard e scripts.
- Refresh headless em `src/refresh_service.py`, que virou o caminho comum para CLI, workers PyQt e automacoes.
- Leitura headless em `src/read_service.py`, que virou o contrato consumido pelo dashboard.

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

Smoke test adicional:

```bash
pytest tests/ -q
```

Diagnostico adicional:

```bash
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
python scripts/db_portability_smoke.py --write-check
python scripts/canonicalize_data_layout.py
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

## Interfaces oficiais

### 1. App Desktop PyQt6 (operacional)

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

### 2. Dashboard Analitico (Streamlit)

Aplicacao read-only para consulta e exportacao do que ja esta no banco:
- busca empresa por nome, ticker ou codigo CVM,
- seleciona intervalo de anos,
- mostra 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.

```powershell
streamlit run dashboard/app.py
```

## Otimizacao de performance

O motor de captura foi reconstruido para suportar repopulacoes massivas sem travar o computador:
- vetorizacao com Pandas Boolean Masks,
- downloads simultaneos via `ThreadPoolExecutor`,
- SQLite em WAL mode com insercoes em lote.

## Observacoes

- Prefira `desktop/cvm_pyqt_app.py` como interface operacional principal.
- Prefira `src/refresh_service.py` e `src/read_service.py` como contratos de nucleo ao criar novas interfaces.
- Use `scripts/db_portability_smoke.py` para validar o backend de banco antes de subir uma API web.
- Use `scripts/canonicalize_data_layout.py` para auditar ou limpar arquivos fora do layout canonico `data/input/raw|processed`.
- O dashboard atual possui 3 abas. Referencias antigas a 9 abas nos docs estao desatualizadas.
- Erros e execucoes de refresh ficam em `output/logs/`, incluindo `refresh_runs.jsonl`.
