# CVM Reports Capture

Projeto para captura, tratamento e exportacao de demonstracoes financeiras da CVM, com persistencia em SQLite e dashboard em Streamlit.

## Estrutura principal

- `main.py`: CLI principal suportada para rodar o scraper.
- `src/`: pipeline de captura/processamento/exportacao.
- `scripts/`: scripts auxiliares (validacao, base analitica, KPIs).
- `data/`: entrada, metadados e banco SQLite.
- `output/`: artefatos gerados (`reports/` e `logs/`).
- `dashboard/`: aplicacao Streamlit.

## Fluxo recomendado (fim a fim)

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Rodar scraper (CLI principal):
```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
```

3. Gerar base analitica para dashboard:
```bash
python scripts/gerar_base_analitica.py
```

4. Preencher KPIs a partir do SQLite:
```bash
python scripts/calc_financial_kpis.py
```

5. Validacao smoke minima:
```bash
python scripts/smoke_validate.py
```

6. Subir dashboard:
```bash
streamlit run dashboard/app.py
```

## Scripts de verificacao (com caminho customizavel)

Todos aceitam `--xlsx`. Padrao: `output/reports/PETROBRAS_financials.xlsx`.

```bash
python scripts/verify_consolidation.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/verify_line_id_base.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/quick_verify.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/final_verification.py --xlsx output/reports/PETROBRAS_financials.xlsx
```

## Observacoes

- A CLI em `src/scraper.py` existe por compatibilidade, mas a interface oficial e recomendada e `main.py`.
- Erros de lote sao gravados em `output/logs/batch_errors.log`.
