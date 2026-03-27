# Como Rodar — CVM Analytics

## Pré-requisitos
- Python 3.10 ou superior
- pip atualizado: `python -m pip install --upgrade pip`

---

## 1. Ativar o ambiente virtual

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD / Prompt de Comando):**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

> Se ainda não criou o venv: `python -m venv .venv`

---

## 2. Instalar dependências (uma vez)
```bash
pip install -r requirements.txt
```

---

## 3. Subir o dashboard
```bash
streamlit run dashboard/app.py
```
Acesse em: **http://localhost:8501**

Para usar uma porta diferente:
```bash
streamlit run dashboard/app.py --server.port 8502
```

> Na primeira vez que o arquivo for modificado, clique **"Always rerun"** na barra
> amarela que aparece no topo para habilitar o hot-reload automático.

---

## 4. Usar o dashboard

1. **Selecionar empresa** — use a barra lateral (busca por nome ou código CVM).
2. **Comparar empresas** — na aba **Visão Geral**, selecione uma segunda empresa
   no seletor **"Comparar com:"** para ver 4 gráficos sobrepostos:
   Receita Líquida · Lucro Líquido · Margem Líquida · ROE.
3. **Valuation** — abaixo dos KPI cards, veja Preço, Market Cap, P/L, P/VP,
   EV/EBITDA e Div. Yield via Yahoo Finance (atualizado a cada 15 min).
4. **Mercado** — heatmap setorial de Margem/ROE por ano para todas as empresas.
5. **Exportar** — baixe os dados em Excel.

---

## 5. Atualizar dados — opção A: botão no dashboard

Na barra lateral do dashboard, clique em **"🔄 Atualizar Dados"**.
O scraper rodará para todas as 69 empresas do banco (ano atual e anterior).
Aguarde o spinner — pode levar alguns minutos.

---

## 6. Atualizar dados — opção B: linha de comando

**Todas as empresas do banco (recomendado):**
```bash
python scripts/atualizar_todos.py
```

**Com anos específicos:**
```bash
python scripts/atualizar_todos.py --anos 2024 2025
```

**Dry-run (lista empresas sem baixar):**
```bash
python scripts/atualizar_todos.py --dry-run
```

**Via PowerShell (com log automático):**
```powershell
.\scripts\atualizar_dados.ps1
.\scripts\atualizar_dados.ps1 -DryRun
.\scripts\atualizar_dados.ps1 -Anos 2024,2025
```

Logs salvos em: `logs/atualizar_YYYYMMDD_HHMMSS.log`

---

## 7. Atualização automática (Task Scheduler)

Uma tarefa chamada **`CVM_Atualizar_Dados`** já está registrada no Windows Task Scheduler.
Ela roda automaticamente **todo domingo às 07h**, mesmo que o PC estivesse desligado
no horário (opção StartWhenAvailable).

Para verificar / editar:
```powershell
# Ver status
Get-ScheduledTask -TaskName CVM_Atualizar_Dados

# Próxima execução
(Get-ScheduledTaskInfo -TaskName CVM_Atualizar_Dados).NextRunTime

# Rodar agora manualmente
Start-ScheduledTask -TaskName CVM_Atualizar_Dados

# Remover tarefa
Unregister-ScheduledTask -TaskName CVM_Atualizar_Dados -Confirm:$false
```

---

## 8. Adicionar nova empresa ao mapa de tickers (Yahoo Finance)

Abra `dashboard/app.py`, localize o bloco `TICKER_MAP` (~linha 170) e adicione:
```python
99999: 'NOVO3.SA',   # NOME DA EMPRESA
```
- `99999` = código CVM (visível no badge "CVM XXXXX" no cabeçalho do dashboard)
- `'NOVO3.SA'` = ticker B3 conforme listado no Yahoo Finance

---

## 9. Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError` | Confirme que o venv está ativo e rode `pip install -r requirements.txt` |
| Dashboard mostra banco vazio | Execute o scraper (passo 6) antes de subir o dashboard |
| Dados de mercado ausentes | Verifique conexão com internet — yfinance busca em tempo real |
| Encoding error no Windows | `set PYTHONIOENCODING=utf-8` antes de executar scripts Python |
| Streamlit não recarrega ao salvar | Clique **"Always rerun"** na barra amarela no topo da página |
| `Permission denied` no PowerShell | Execute: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Botão "Atualizar" sem resposta | Verifique que o venv tem todas as dependências; veja `logs/` para detalhes |
