# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hybrid Python project: a CLI scraper that extracts DFP/ITR financial reports from Brazil's CVM regulator and persists them to SQLite/PostgreSQL, plus a Streamlit analytics dashboard and a PyQt6 desktop app for 449+ public companies.

> For business rules, pipeline details, and troubleshooting see `docs/CONTEXT.md`.
> For current state and session history see `docs/AGENTS.md`.

## Commands

### Running the App

```bash
# Dashboard (Streamlit)
streamlit run dashboard/app.py

# Desktop GUI (PyQt6 — official; handles data refresh)
python desktop/cvm_pyqt_app.py

# CLI scraper
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
```

### Testing

```bash
pytest tests/ -v                         # all tests
pytest tests/test_scraper.py -v          # single file
pytest -k "test_normalize" -v            # by name pattern
```

Configuration lives in `pytest.ini` at the repo root.

### Database Setup (after clone or migration)

```bash
python scripts/setup_db.py               # indices + companies/account_names tables
python scripts/setup_companies_table.py  # populate companies with CVM metadata + tickers
python scripts/expand_tickers.py --dry-run  # discover new B3 tickers
```

### Batch Data Collection

```bash
python scripts/batch_completo.py --dry-run           # preview
python scripts/batch_completo.py --max-companies 450 --start-year 2022 --end-year 2025
python scripts/atualizar_todos.py --anos 2024 2025   # update specific years only
```

### Activation

```bash
.venv\Scripts\activate.bat       # Windows CMD
.\.venv\Scripts\Activate.ps1     # PowerShell
```

## Architecture

### Data Pipeline

CVM website → `src/scraper.py` (CVMScraper) → `src/standardizer.py` (AccountStandardizer) → `src/database.py` (CVMDatabase, SQLAlchemy) → SQLite or PostgreSQL → `dashboard/` (Streamlit) or `cvm_pyqt_app.py` (PyQt6)

**`src/` module roles:**
- `src/utils.py` — `normalize_account_name()` + `generate_line_id_base()` (used throughout)
- `src/dictionary.py` — builds canonical account dictionary from CVM raw data
- `src/db.py` — Streamlit-free `get_engine()` factory (2-tier: `DATABASE_URL` env → SQLite); safe to import from CLI scripts and PyQt6
- `src/query_layer.py` — `CVMQueryLayer` class: all SQL queries for fetching statements (DRE, BPA, BPP, DFC, DVA, DMPL) by company/year/period. **Important**: `get_statement()` applies `fillna("")` on `STANDARD_NAME` before `pivot_table` — pandas silently drops NaN index rows.
- `src/kpi_engine.py` — `compute_all_kpis()`, `compute_quarterly_kpis()`: 60+ financial indicators (ROE, ROA, margins, solvency, etc.). Outputs include `UNIDADE` column (`"%"` or `"x"`). Quarterly mode trims leading periods where LTM flow KPIs are not computable.
- `src/ticker_map.py` — B3 ticker ↔ CVM code mapping utilities
- `src/excel_exporter.py` — Excel report generation with QA logs and validations. KPI sheet has columns: INDICADOR, FÓRMULA, UNIDADE, [periods], Δ YoY, Tendência. Category headers use individual cell writes (no merge_range).
- `src/statement_summary.py` — condensed multi-block statement builder (DRE, BPA, BPP, DFC). Filters to subtotal/summary `CD_CONTA` codes and optionally expands direct children. Used for high-level views without loading full pivot tables.

### Database

- **Local**: `data/db/cvm_financials.db` (SQLite, WAL mode); `data/cache/base_health_snapshot.json` stores the last base-health check result (committed to git, updated by PyQt6 app)
- **Production**: PostgreSQL via `DATABASE_URL`
- Connection fallback order: `DATABASE_URL` → SQLite (in `src/db.py`)
- Write path lives in `src/database.py`; read/query path lives in `src/query_layer.py`
- Core table: `financial_reports` (UPPER_CASE columns); metadata tables: `companies`, `account_names` (snake_case)
- Key column: `LINE_ID_BASE` (never `LINE_ID`)

### Dashboard Modules

`dashboard/app.py` is the slim orchestrator. Current tab structure:

- `dashboard/tabs/visao_geral.py` — KPI summary blocks and quarterly/period views
- `dashboard/tabs/demonstracoes.py` — Financial statement pivot tables (BPA, BPP, DRE, DFC, DVA, DMPL)
- `dashboard/tabs/download.py` — Excel export with KPIs

`dashboard/components/search_bar.py` — `render_sidebar()`: company search + year selection widget

**Data flow in app.py:**
1. `render_sidebar()` → selected company + year range
2. `CVMQueryLayer` → fetch statements from DB (cached `@st.cache_data` TTL 600s)
3. `compute_all_kpis()` / `compute_quarterly_kpis()` → KPI DataFrames
4. Tab renderers consume the precomputed data

> The dashboard is **read-only** — data refresh is handled exclusively by `cvm_pyqt_app.py`. There is no update button in Streamlit.

### PyQt6 Desktop App (`cvm_pyqt_app.py`)

Operational updater GUI. Main moving parts:
- `IntelligentSelectorService` ranks and prioritizes refresh work
- `UpdateWorker` builds the company/year plan, runs `CVMScraper`, and syncs `company_refresh_status`
- The UI exposes company search, year selection, progress tracking, and base-health summaries

### Scraper Core (`src/scraper.py`)

`CVMScraper` is the ingestion entrypoint for both CLI and PyQt flows. Key design choices:
- Vectorized Pandas (Boolean masks, no row-by-row loops)
- `ThreadPoolExecutor` for concurrent downloads (`max_workers=5` default)
- SQLite WAL + `synchronous=OFF` for bulk inserts
- retry + backoff around company-level DB write failures
- DFC YTD→standalone conversion (`convert_dfc_ytd_to_standalone`)
- BPA/BPP closing validation + QA logs per run

### Scripts

Active scripts in `scripts/`. Key ones:
- `scripts/restaurar_historico.py` — restore historical data
- `scripts/patch_database_sectors_v2.py` — sector metadata patching
- `scripts/sync_docs_check.py` — warns when docs are out of sync with code changes
- `scripts/validation/` — one-off diagnostic scripts (DFC standalone verification, missing quarters, trimestral checks); safe to run as read-only audits

Dead/archived scripts are in `archive/` at the repo root — do not touch those.

**Script convention**: prefer keeping user-tunable values near the top of executable scripts and avoid burying operational constants deep in the logic.

## Critical Conventions

**Numeric types**: Always `int(year)` before using as SQLite param — numpy `int64` causes silent failures.

**yfinance `dividendYield`**: Already in % form — do NOT multiply by 100.

**SQLAlchemy IN clauses**: Use `bindparam("x", expanding=True)` for list parameters.

**B3 API**: `issuingCompany` = 4-letter base code (e.g., `"PETR"`); `codeCVM` = `cd_cvm` from DB.

**`_upsert_company_metadata`**: Uses INSERT OR IGNORE + UPDATE (not REPLACE) to preserve existing CNPJ/ticker data.

**Account normalization**: `normalize_account_name()` → lowercase, remove accents, collapse spaces. `generate_line_id_base()` creates stable IDs from `CD_CONTA` or `DS_CONTA_norm`.

**Streamlit JS injection**: Use `st.components.v1.html()` to embed `<script>` tags — `st.markdown` does not execute JavaScript.

**pandas `pivot_table` and NaN index**: `pd.pivot_table()` silently drops rows where any index column is NaN. Always `fillna("")` on index columns before pivoting. This caused DFC sub-accounts (82% of rows) to disappear when `STANDARD_NAME` was NULL.

**Excel number formats**: Zeros display as `"-"`, negatives as `(1,234)` in red. Format string: `'#,##0;(#,##0);"-"'`. Applied to `subtotal_neg` and `neg_center` styles in `excel_exporter.py`.

**KPI UNIDADE column**: Every KPI row includes `UNIDADE` (`"%"` for percentages, `"x"` for ratios). Propagated through kpi_engine → excel_exporter → dashboard meta_cols.

## Deployment

**Environment variable**: `DATABASE_URL=postgresql://...` (used by scraper, query layer, and dashboard).

**Task Scheduler**: `CVM_Atualizar_Dados` task runs `scripts/atualizar_dados.ps1` every Sunday at 07:00.

## Testing Conventions

- Tests use `unittest.mock.patch` — no real CVM API calls or DB writes
- Fixtures provide mocked `CVMScraper`, `CVMDatabase`, `AccountStandardizer`
- `conftest.py` at repo root inserts the project root into `sys.path` (required for `cvm_pyqt_app` imports)
- Test files: `test_scraper.py`, `test_cvm_pyqt_app.py`, `test_base_health_snapshot.py`, `test_database_portability.py`, `test_excel_exporter.py`, `test_statement_summary.py`, `test_utils.py`
