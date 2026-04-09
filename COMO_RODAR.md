# Como Rodar - CVM Analytics

Guia pratico para subir a V1 operacional e o primeiro slice da V2 no ambiente local.

Fluxo principal atual:

`runtime_doctor.py -> setup_db.py -> setup_companies_table.py -> python -m desktop.cvm_pyqt_app -> dashboard/app.py -> apps/api -> apps/web`

---

## 1. Preparar o ambiente

Entre na pasta do projeto:

```powershell
cd C:\caminho\para\cvm_repots_capture
```

Crie e ative a `.venv` se necessario:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependencias Python:

```powershell
pip install -r requirements.txt
pip install -r apps/api/requirements-dev.txt
```

Se for usar a web:

```powershell
cd apps/web
npm install
cd ..\..
```

Se for trabalhar em uma task versionada, prefira criar uma worktree antes de
editar arquivos:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/worktree_create.ps1 -Issue 27 -Slug exemplo-task -Lane ops-quality
```

Ao concluir a task, prefira finalizar a PR com o helper abaixo para esperar
checks, mergear e confirmar o fechamento:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/pr_complete.ps1 -Pr 28
```

---

## 2. Diagnosticar o runtime

Bootstrap minimo:

```powershell
python scripts/runtime_doctor.py --require-canonical
```

Diagnostico completo:

```powershell
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
python scripts/canonicalize_data_layout.py
python scripts/db_portability_smoke.py --write-check
```

Validacao de PostgreSQL sem exportar variavel:

```powershell
python scripts/runtime_doctor.py --database-url postgresql://user:pass@host:5432/db --require-db --table financial_reports --table companies
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

---

## 3. Inicializar o banco

Em maquina nova ou depois de migracao:

```powershell
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

Opcional:

```powershell
python scripts/expand_tickers.py --dry-run
```

---

## 4. Atualizar dados financeiros

### Opcao A - App desktop oficial

```powershell
python -m desktop.cvm_pyqt_app
```

Compatibilidade:

```powershell
python desktop/cvm_pyqt_app.py
```

### Opcao B - CLI pontual

```powershell
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated --skip_complete
```

### Opcao C - Lote headless

```powershell
python scripts/batch_completo.py --dry-run
python scripts/atualizar_todos.py --anos 2024 2025
```

Os logs ficam em `output/logs/`.

---

## 5. Abrir o dashboard Streamlit

```powershell
streamlit run dashboard/app.py
```

Uso:
- buscar empresa por nome, ticker ou codigo CVM
- selecionar anos
- consultar `Visao Geral`, `Demonstracoes` e `Download`

---

## 6. Subir a API da V2

```powershell
uvicorn apps.api.app.main:app --reload
```

Abrir:
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

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

Exemplos:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/companies?search=petro&page=1&page_size=20"
Invoke-RestMethod http://127.0.0.1:8000/companies/filters
```

---

## 7. Subir o web app da V2

Em outro terminal:

```powershell
cd apps/web
Copy-Item .env.example .env.local
npm run dev
```

Abrir:
- app web: `http://127.0.0.1:3000`

Rotas desta fase:
- `/`
- `/empresas`
- `/empresas/[cd_cvm]`

Observacoes:
- `API_BASE_URL` fica em `apps/web/.env.local`
- o frontend consome apenas a API V2
- `apps/web/app/api/company-search/route.ts` faz o proxy interno do autocomplete

---

## 8. Validar tudo

Suite principal:

```powershell
pytest tests/ -q
pytest apps/api/tests -q
```

Web:

```powershell
cd apps/web
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Validacoes de workbook/exportacao:

```powershell
python scripts/verify_consolidation.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/verify_line_id_base.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/quick_verify.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/final_verification.py --xlsx output/reports/PETROBRAS_financials.xlsx
```

---

## Problemas comuns

| O que aconteceu | O que fazer |
|---|---|
| `ModuleNotFoundError` ao abrir o desktop | Prefira `python -m desktop.cvm_pyqt_app`; o entrypoint por arquivo tambem deve funcionar no estado atual. |
| `python` nao reconhecido | Instale o Python e coloque no `PATH`. |
| `runtime_doctor.py` falha com `venv-broken` | Recrie a `.venv` com `python -m venv .venv`. |
| App desktop abre sem empresas | Rode `setup_db.py`, `setup_companies_table.py` e atualize dados. |
| Dashboard vazio | Verifique se a empresa/anos escolhidos ja foram processados. |
| API responde `503` | Valide o banco, tabelas obrigatorias e o `runtime_doctor.py`. |
| Web app sem dados | Verifique `API_BASE_URL` e se `uvicorn apps.api.app.main:app --reload` esta rodando. |
| Erro de permissao no PowerShell | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
