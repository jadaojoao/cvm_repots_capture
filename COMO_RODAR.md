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
   no seletor **"Comparar com:"** para ver gráficos sobrepostos de Receita, Lucro,
   Margem Líquida e ROE.
3. **Mercado** — veja heatmap setorial de margem/ROE por ano.
4. **Exportar** — baixe os dados em Excel.

---

## 5. Atualizar dados (scraper)
```bash
python main.py --companies PETROBRAS VALE --start_year 2022 --end_year 2025 --type consolidated
```
Omita `--companies` para rodar todas as empresas configuradas no scraper.

---

## 6. Adicionar nova empresa ao mapa de tickers (Yahoo Finance)

Abra `dashboard/app.py`, localize o bloco `TICKER_MAP` (~linha 167) e adicione:
```python
TICKER_MAP: dict[int, str] = {
    ...
    99999: 'NOVO3.SA',   # NOME DA EMPRESA
}
```
- `99999` = código CVM da empresa (visível no badge "CVM XXXXX" no cabeçalho)
- `'NOVO3.SA'` = ticker B3 conforme listado no Yahoo Finance

---

## 7. Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError` | Confirme que o venv está ativo e rode `pip install -r requirements.txt` |
| Dashboard mostra banco vazio | Execute o scraper (passo 5) antes de subir o dashboard |
| Dados de mercado ausentes | Verifique conexão com internet — yfinance busca em tempo real |
| Encoding error no Windows | `set PYTHONIOENCODING=utf-8` antes de executar scripts Python |
| Streamlit não recarrega ao salvar | Clique **"Always rerun"** na barra amarela no topo da página |
| `Permission denied` no PowerShell | Execute: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
