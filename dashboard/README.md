# CVM Analytical Dashboard

Dashboard Streamlit para analise financeira das empresas capturadas via CVM.

## Pre-requisitos de dados

Antes de subir o dashboard, rode esta sequencia na raiz do projeto:

```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
python scripts/gerar_base_analitica.py
python scripts/calc_financial_kpis.py
python scripts/smoke_validate.py
```

Ao final, estes arquivos devem existir:

- `data/db/cvm_financials.db`
- `output/reports/base_analitica_dashboard_preenchida.xlsx`

## Como executar

```bash
streamlit run dashboard/app.py
```

URL local padrao: `http://localhost:8501`.

## Arquitetura

- `dashboard/app.py`: orquestracao da UI.
- `dashboard/components/ui.py`: componentes visuais.
- `dashboard/data/data_loader.py`: consultas ao SQLite.
- `dashboard/styles/style.css`: estilos customizados.
- `dashboard/utils/excel_exporter.py`: exportacao para Excel.
