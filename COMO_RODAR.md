# Como Rodar - CVM Analytics

Este guia explica como usar o sistema de coleta e consulta de dados financeiros da CVM, passo a passo.
Nao e necessario saber programar para seguir as instrucoes.

Fluxo principal atual: `setup_db.py` -> `setup_companies_table.py` -> `desktop/cvm_pyqt_app.py` -> `dashboard/app.py`.

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

---

## Passo 4 - Configurar o banco de dados

Se e a primeira vez usando o projeto, ou se voce mudou de maquina, rode estes dois scripts antes de abrir o app:

```powershell
python scripts/setup_db.py
python scripts/setup_companies_table.py
```

Esses scripts:
- criam indices e tabelas de apoio,
- preenchem a tabela `companies`,
- preparam o banco para o app desktop e o dashboard.

Opcional:
```powershell
python scripts/expand_tickers.py --dry-run
```

---

## Passo 5 - Atualizar os dados financeiros

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
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
```

Voce tambem pode usar o codigo CVM numerico no lugar do nome.

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

### Opcao D - Atualizacao automatica aos domingos

Para criar a tarefa agendada no Windows:

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
             -Argument "-ExecutionPolicy Bypass -File `"$PWD\scripts\atualizar_dados.ps1`"" `
             -WorkingDirectory $PWD
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 07:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "CVM_Atualizar_Dados" `
  -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
```

Verificar:
```powershell
Get-ScheduledTask -TaskName CVM_Atualizar_Dados
```

Rodar agora:
```powershell
Start-ScheduledTask -TaskName CVM_Atualizar_Dados
```

---

## Passo 6 - Abrir o dashboard analitico

Depois que houver dados no banco:

```powershell
streamlit run dashboard/app.py
```

O dashboard atual e **somente leitura**. Ele serve para:
- buscar empresa por nome, ticker ou codigo CVM,
- selecionar anos,
- visualizar 3 abas: `Visao Geral`, `Demonstracoes` e `Download`.

Atualizacao de dados pertence ao app PyQt6 ou aos scripts.

---

## Passo 7 - Validar

Suite principal:
```powershell
pytest tests/ -q
```

Se precisar confirmar o numero de testes, use a suite acima como referencia; os docs mantem o ultimo valor confirmado em `docs/AGENTS.md`.

Validacoes de workbook/exportacao:
```powershell
python scripts/verify_consolidation.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/verify_line_id_base.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/quick_verify.py --xlsx output/reports/PETROBRAS_financials.xlsx
python scripts/final_verification.py --xlsx output/reports/PETROBRAS_financials.xlsx
```

Observacao:
- `scripts/gerar_base_analitica.py`, `scripts/calc_financial_kpis.py` e `scripts/smoke_validate.py` existem, mas nao sao passos obrigatorios do fluxo principal atual.

---

## Adicionar uma nova empresa

1. Baixe os dados da empresa:
```powershell
python main.py --companies NOME_EMPRESA --start_year 2022 --end_year 2025
```

2. Se precisar mapear ticker manualmente, edite `src/ticker_map.py`:
```python
99999: 'NOVO3.SA',   # NOME DA EMPRESA
```

- `99999` = codigo CVM
- `'NOVO3.SA'` = ticker no Yahoo Finance

---

## Problemas comuns

| O que aconteceu | O que fazer |
|---|---|
| `ModuleNotFoundError` | O ambiente virtual nao esta ativo. |
| `python` nao reconhecido | Python nao esta instalado ou nao esta no PATH. |
| App abre mas nao mostra empresas | Rode `setup_db.py` e `setup_companies_table.py`, depois atualize dados. |
| Dashboard vazio | Verifique se a empresa/anos escolhidos ja foram processados e se `financial_reports` tem linhas. |
| Erro de permissao no PowerShell | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| Batch interrompido | Rode novamente; os scripts de lote evitam reprocessar o que ja foi concluido. |
| Cotacao nao aparece | Verifique internet e mapeamento de ticker. |

---

## Estrutura dos arquivos

```text
cvm_repots_capture/
|-- src/                   # Motor do scraper e da consulta
|-- scripts/               # Automacao, setup, batch e validacoes
|-- data/db/               # Banco SQLite local
|-- logs/                  # Registros das atualizacoes
|-- dashboard/             # App Streamlit read-only
|-- desktop/               # App desktop PyQt6 (cvm_pyqt_app.py)
|-- main.py                # CLI para coleta pontual
`-- requirements.txt       # Dependencias
```

Para alterar:
- ticker map: `src/ticker_map.py`
- conexao de banco: `src/db.py`
- scraper: `src/scraper.py`
