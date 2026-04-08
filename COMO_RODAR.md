# Como Rodar - CVM Analytics

Este guia explica como usar o sistema de coleta e consulta de dados financeiros da CVM, passo a passo.
Nao e necessario saber programar para seguir as instrucoes.

Fluxo principal atual: `runtime_doctor.py` -> `setup_db.py` -> `setup_companies_table.py` -> `desktop/cvm_pyqt_app.py` -> `dashboard/app.py` -> `apps/api`.

---

## Antes de comecar

- **Python 3.11 ou superior**
  ```powershell
  python --version
  ```
- **Pasta do projeto**
  Entre na pasta `cvm_repots_capture` antes de rodar qualquer comando.

---

## Passo 1 - Abrir o terminal na pasta do projeto

1. Abra o Explorador de Arquivos e navegue ate a pasta `cvm_repots_capture`.
2. Clique na barra de endereco, digite `powershell` ou `cmd` e aperte Enter.

Alternativa:
```powershell
cd C:\caminho\para\cvm_repots_capture
```

---

## Passo 2 - Criar e ativar o ambiente virtual

Se ainda nao existir:
```powershell
python -m venv .venv
```

**No CMD:**
```bat
.venv\Scripts\activate.bat
```

**No PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

Se aparecer erro de permissao no PowerShell:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## Passo 3 - Instalar as bibliotecas

Com o ambiente virtual ativo:
```powershell
pip install -r requirements.txt
```

Se voce tambem vai usar a API da V2:
```powershell
pip install -r apps/api/requirements-dev.txt
```

---

## Passo 4 - Rodar o diagnostico de runtime

Antes de inicializar ou subir a aplicacao, rode:

```powershell
python scripts/runtime_doctor.py --require-canonical
```

Se quiser validar banco + tabelas obrigatorias:

```powershell
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
```

Esse script verifica:
- interpretador Python atual,
- `.venv` quebrada,
- arquivo `canonical_accounts.csv`,
- banco configurado e tabelas obrigatorias,
- diretorios legados que podem causar ambiguidade operacional.

Para validar layout de dados e banco antes da web:

```powershell
python scripts/canonicalize_data_layout.py
python scripts/db_portability_smoke.py --write-check
```

Se voce quiser validar um PostgreSQL especifico sem exportar a variavel antes:

```powershell
python scripts/runtime_doctor.py --database-url postgresql://user:pass@host:5432/db --require-db --table financial_reports --table companies
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

---

## Passo 5 - Configurar o banco de dados

Se e a primeira vez usando o projeto, ou se voce mudou de maquina, rode estes dois scripts antes de abrir o app:

```powershell
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

Esses scripts:
- criam indices e tabelas de apoio,
- preenchem a tabela `companies`,
- preparam o banco para o app desktop, dashboard e API.

Opcional:
```powershell
python scripts/expand_tickers.py --dry-run
```

---

## Passo 6 - Atualizar os dados financeiros

### Opcao A - Pelo aplicativo desktop (recomendado)

Este e o caminho principal do projeto.

```powershell
python desktop/cvm_pyqt_app.py
```

No app:
1. escolha os anos desejados,
2. revise a lista/ranking de empresas,
3. clique para iniciar a atualizacao.

O app mostra progresso, erros e cobertura da base.

### Opcao B - Pelo terminal, para uma empresa especifica

```powershell
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated --skip_complete
```

Voce tambem pode usar o codigo CVM numerico no lugar do nome.
Esse caminho usa o mesmo servico headless do updater desktop.

### Opcao C - Atualizacao em lote

Preview:
```powershell
python scripts/batch_completo.py --dry-run
```

Lote amplo:
```powershell
python scripts/batch_completo.py --max-companies 450 --start-year 2022 --end-year 2025
```

Ou:
```powershell
python scripts/atualizar_todos.py --anos 2024 2025
```

Os logs principais ficam em `output/logs/`.
As execucoes headless tambem ficam registradas em `output/logs/refresh_runs.jsonl`.

---

## Passo 7 - Abrir o dashboard analitico

Depois que houver dados no banco:

```powershell
streamlit run dashboard/app.py
```

O dashboard atual e **somente leitura**. Ele serve para:
- buscar empresa por nome, ticker ou codigo CVM,
- selecionar anos,
- visualizar 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.

Atualizacao de dados pertence ao app PyQt6 ou aos scripts.
O dashboard consome o contrato de leitura centralizado em `src/read_service.py`.

---

## Passo 8 - Subir a API da Fase 1 da V2

A API web desta fase e somente leitura e reaproveita o mesmo contrato headless da V1.

```powershell
uvicorn apps.api.app.main:app --reload
```

Abrir:
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Endpoints principais:
- `GET /health`
- `GET /companies`
- `GET /companies/{cd_cvm}`
- `GET /companies/{cd_cvm}/years`
- `GET /companies/{cd_cvm}/statements`
- `GET /companies/{cd_cvm}/kpis`
- `GET /refresh-status`
- `GET /base-health`

Exemplo rapido:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/companies?search=petro
```

---

## Passo 9 - Validar

Suite principal:
```powershell
pytest tests/ -q
```

Suite da API:
```powershell
pytest apps/api/tests -q
```

Validacoes de workbook/exportacao:
```powershell
python scripts/verify_consolidation.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/verify_line_id_base.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/quick_verify.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/final_verification.py --xlsx output/reports/PETROBRAS_financials.xlsx
```

Observacao:
- `scripts/gerar_base_analitica.py`, `scripts/calc_financial_kpis.py` e `scripts/smoke_validate.py` existem, mas nao sao passos obrigatorios do fluxo principal atual.
- `src/settings.py` e `.env.example` definem o contrato central de configuracao por ambiente.
- `scripts/restaurar_historico.py` usa o planner headless para detectar company-years faltantes antes de uma restauracao.
- `apps/api/app/main.py` e o entrypoint da API read-only da V2.

---

## Problemas comuns

| O que aconteceu | O que fazer |
|---|---|
| `ModuleNotFoundError` | O ambiente virtual nao esta ativo. |
| `python` nao reconhecido | Python nao esta instalado ou nao esta no PATH. |
| `runtime_doctor.py` falha com `venv-broken` | Recrie a `.venv` com `python -m venv .venv` e reinstale `requirements.txt`. |
| App abre mas nao mostra empresas | Rode `setup_db.py` e `setup_companies_table.py`, depois atualize dados. |
| Dashboard vazio | Verifique se a empresa/anos escolhidos ja foram processados e se `financial_reports` tem linhas. |
| API responde `503` | Valide `runtime_doctor.py`, tabelas obrigatorias e a conexao de banco. |
| Erro de permissao no PowerShell | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
