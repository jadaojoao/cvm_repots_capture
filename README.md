# CVM Reports Capture

Projeto para captura, tratamento e consulta de demonstracoes financeiras da CVM, com persistencia em SQLite/PostgreSQL, app desktop operacional em PyQt6 e dashboard analitico em Streamlit.

## Estrutura principal

- `cvm_pyqt_app.py`: [OFICIAL] app desktop em PyQt6 para atualizacao local e operacao do refresh.
- `main.py`: CLI suportada para rodar o scraper de forma pontual.
- `src/`: pipeline de captura, padronizacao, consulta e exportacao.
- `scripts/`: scripts auxiliares, setup de banco, batches e validacoes.
- `data/`: entrada, metadados, cache e banco SQLite local (`cvm_financials.db`).
- `output/`: artefatos gerados, incluindo relatórios e logs.
- `dashboard/`: aplicacao analitica em Streamlit com 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.
- `docs/`: documentacao de referencia (`CONTEXT.md`, `AGENTS.md`, `AUDIT.md`, `STUDENT_PACK_PLAN.md`).

## Fluxo recomendado (estado atual)

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Inicializar o banco em uma maquina nova ou apos migracao:
```bash
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

3. Atualizar dados pela interface operacional principal:
```bash
python cvm_pyqt_app.py
```

4. Alternativa para coleta pontual via CLI:
```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
```

5. Alternativas para atualizacao em lote:
```bash
python scripts/batch_completo.py --dry-run
python scripts/atualizar_todos.py --anos 2024 2025
```

6. Subir o dashboard analitico read-only:
```bash
streamlit run dashboard/app.py
```

> Observacao: `scripts/gerar_base_analitica.py`, `scripts/calc_financial_kpis.py` e `scripts/smoke_validate.py` continuam uteis em fluxos especificos, mas nao sao pre-requisitos do caminho principal PyQt6 -> banco -> dashboard descrito em `CLAUDE.md`.

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
python cvm_pyqt_app.py
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

- Prefira `cvm_pyqt_app.py` como interface operacional principal.
- O dashboard atual possui 3 abas. Referencias antigas a 9 abas nos docs estao desatualizadas.
- Erros de lote sao gravados em `output/logs/batch_errors.log`.
