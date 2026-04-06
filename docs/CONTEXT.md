# CONTEXT.md - CVM Reports Capture

> Referencia tecnica: regras de negocio, pipeline, arquitetura e troubleshooting.
> Para comandos e convencoes rapidas, veja `CLAUDE.md`. Para estado atual e historico de sessoes, veja `docs/AGENTS.md`.

---

## 1. O que e o projeto

Extrai demonstracoes financeiras historicas de companhias listadas na CVM, organiza em SQLite/PostgreSQL e expoe os dados via dashboard Streamlit read-only e app PyQt6 para atualizacao operacional. O foco e produzir output confiavel, legivel e verificavel sem misturar periodos, versoes ou linhas conflitantes.

**Objetivo final:** pipeline unico que recebe empresa + ano inicial/final, persiste demonstracoes e metadados em banco e disponibiliza consulta/exportacao via PyQt6, Streamlit e Excel auditavel.

**Fonte de dados:** CVM publica - `https://dados.cvm.gov.br` (DFP anual + ITR trimestral).

---

## 2. Escopo tecnico atual

**Prioridade 1 (concluida):** integridade contabil e periodizacao correta - fechar Ativo/Passivo Total, evitar carimbar anual em trimestre, tratar janela de anos.

**Prioridade 2 (concluida):** chave estavel `LINE_ID_BASE`, base wide, `DS_CONTA_norm`, filtro `ORDEM_EXERC='ULTIMO'`, QA por conflitos, exportacao limpa do Excel.

**Prioridade 3 (concluida):** padronizacao por dicionario de contas (`STANDARD_NAME`), aba `PADRONIZACAO` no Excel.

**Prioridades 4-8 (concluidas):** expansao em massa (449 empresas), vetorizacao + WAL + paralelismo, dashboard Streamlit read-only, app Desktop PyQt6, testes automatizados.

---

## 3. Regras de negocio essenciais

- Output gera abas **BPA**, **BPP**, **DRE** e **DFC**.
- Linhas identificadas por `LINE_ID_BASE` estavel - sempre usa `CD_CONTA` quando disponivel; chave sintetica deterministica quando nao.
- `DS_CONTA_norm` obrigatorio em todas as abas: lower, remocao de acentos, trim, colapso de espacos, remocao de NBSP.
- Output nao deve usar sufixos artificiais como `#1`, `#2`.

### Regras DRE e DFC

- DRE e DFC mantem colunas trimestrais e anuais (`1Q`, `2Q`, `3Q`, `4Q`, `YYYY`).
- DFC nao fica cumulativa: conversao YTD -> standalone feita internamente.
  - `Q1 = YTD_1Q`
  - `Q2 = YTD_2Q - YTD_1Q`
  - `Q3 = YTD_3Q - YTD_2Q`
  - `Q4 = ANUAL - YTD_3Q`
  - `YYYY = ANUAL`
- Trimestre faltante: deixar `NaN` e registrar no QA; nao inventar valores.

### QA e criterios de aceite

Validacoes obrigatorias antes de exportar Excel:
- `LINE_ID_BASE` unico por aba
- `DS_CONTA_norm` sem nulos
- ausencia de `"#"` nos IDs finais
- fechamento BPA e BPP (Ativo Total = Passivo Total)
- DFC: `Q1 + Q2 + Q3 + Q4 = YYYY` quando todos os periodos existirem

Abas **QA_LOG** e **QA_Errors** sao obrigatorias para rastreabilidade.

---

## 4. Pipeline e data flow

### Ciclo completo (download -> banco -> dashboard)

**1. Trigger**
- CLI: `python main.py --companies ... --start_year ... --end_year ...`
- Desktop: PyQt6 invoca o scraper para empresas/range selecionados

**2. Download e extracao**
- `src/scraper.py` baixa ZIPs da CVM para `data/input/raw`
- CSVs (BPA/BPP/DRE/DFC/DVA/DMPL) sao extraidos para `data/input/processed`

**3. Transform e normalizacao**
- filtra por `CD_CVM`, normaliza unidades financeiras
- deriva labels de periodo, monta tabelas por demonstracao
- gera `LINE_ID_BASE`, aplica padronizacao e logs de QA

**4. Persistencia**
- `src/database.py` escreve linhas long-form em `financial_reports` e eventos de QA em `qa_logs`
- metadados de empresa sao atualizados em `companies`
- exportacao Excel continua disponivel em `output/reports/`

**5. Dashboard**
- `dashboard/app.py` orquestra a aplicacao Streamlit atual
- `src/query_layer.py` consulta `financial_reports` e tabelas relacionadas
- `src/kpi_engine.py` calcula KPIs para as visoes e exportacoes
- o app atual possui 3 abas: `Visao Geral`, `Demonstracoes` e `Download`
- atualizacao de dados nao acontece no Streamlit; ela pertence ao app PyQt6 e aos scripts

### PyQt6 updater

1. Ranking inteligente: relevancia de mercado (40% market cap + 60% liquidez) combinada com desatualizacao
2. Executa `CVMScraper.run(...)` para as empresas/anos selecionados
3. Persiste status de refresh em `company_refresh_status`
4. Exibe progresso, erros, cobertura e pode abrir o dashboard local

### Modelo de cobertura

- **Universo:** empresas ativas da CVM master
- **Celula coberta:** empresa-ano com pacote completo (`BPA + BPP + DRE + DFC`)
- **Sinal hibrido:** `financial_reports` + arquivos raw/processados + cache local

---

## 5. Arquitetura de pastas

```text
cvm_repots_capture/
|-- src/                        # Pipeline de extracao e processamento
|   |-- scraper.py              # CVMScraper
|   |-- database.py             # CVMDatabase
|   |-- db.py                   # get_engine() SQLite/PostgreSQL
|   |-- standardizer.py         # AccountStandardizer
|   |-- dictionary.py           # Dicionario de contas
|   |-- query_layer.py          # Camada de leitura para dashboard/exportacao
|   |-- kpi_engine.py           # KPIs financeiros
|   |-- excel_exporter.py       # Exportacao Excel
|   |-- statement_summary.py    # Resumos de demonstracoes
|   |-- ticker_map.py           # Mapa CVM -> ticker
|   `-- utils.py                # Helpers compartilhados
|-- dashboard/                  # Dashboard Streamlit read-only
|   |-- app.py                  # Orquestrador principal
|   |-- components/
|   |   `-- search_bar.py       # Busca de empresa e selecao de anos
|   `-- tabs/
|       |-- visao_geral.py      # KPIs e visoes resumidas
|       |-- demonstracoes.py    # Tabelas das demonstracoes
|       `-- download.py         # Exportacao/download
|-- scripts/                    # Setup, batches e validacoes
|-- archive/                    # Scripts antigos/arquivados
|-- tests/                      # Suite pytest focada em scraper, PyQt, DB e exportacao
|-- data/
|   |-- db/cvm_financials.db    # SQLite local
|   |-- cache/                  # Caches auxiliares
|   `-- metadata/               # Metadados de empresas e tickers
|-- docs/
|   |-- CONTEXT.md              # Este arquivo
|   |-- AGENTS.md               # Estado atual + historico de sessoes
|   `-- AUDIT.md                # Registro de audit/cleanup
|-- cvm_pyqt_app.py             # Interface oficial para updates
|-- main.py                     # Entrypoint CLI
|-- CLAUDE.md                   # Guia operacional para agentes
|-- README.md                   # Overview do projeto
`-- COMO_RODAR.md               # Tutorial passo a passo
```

---

## 6. Stack e convencoes de codigo

**Stack:**
- Python 3.11+, pandas, sqlalchemy, requests, PyQt6, yfinance, Streamlit e Plotly

**Convencoes:**
- `snake_case` para variaveis e nomes de arquivos
- OO no motor principal (`CVMScraper`)
- bloco `USER CONFIGURATION` no topo de cada script executavel
- `LINE_ID_BASE` como identificador canonico

---

## 7. Estado atual (2026-04-05)

- Banco local SQLite com suporte opcional a PostgreSQL via `DATABASE_URL`
- Dashboard Streamlit com 3 abas: `Visao Geral`, `Demonstracoes`, `Download`
- App Desktop PyQt6 como interface oficial de atualizacao
- Automacao e batches via `batch_completo.py` e `atualizar_todos.py`
- Testes: 114 pytest passing
- `CLAUDE.md` reflete melhor o estado atual do que referencias antigas em outros docs

**Proximas prioridades:**
- deploy cloud (Supabase PostgreSQL + Streamlit Cloud)
- ampliacao de cobertura/contas para outros setores
- exportacoes auxiliares e melhoria de documentacao operacional

---

## 8. Bootstrap rapido (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_windows.ps1
```

Flags: `-ForceRecreateVenv`, `-SkipSmoke`.

Fluxo pos-bootstrap recomendado:
```powershell
.\.venv\Scripts\Activate.ps1
python scripts/setup_db.py
python scripts/setup_companies_table.py
python cvm_pyqt_app.py
streamlit run dashboard/app.py
```

Fluxo alternativo via CLI:
```powershell
.\.venv\Scripts\Activate.ps1
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
streamlit run dashboard/app.py
```

---

## 9. Troubleshooting

| Sintoma | Diagnostico |
|---------|-------------|
| Sem dados no dashboard | Verificar se `financial_reports` tem linhas e se a empresa/anos selecionados foram processados |
| Empresa ausente | Verificar se o `CD_CVM` foi processado com sucesso |
| SQL error no updater | Inspecionar logs do updater e confirmar que o SQLite nao esta bloqueado |
| Lista repete as mesmas empresas | Verificar se `last_success_at` esta sendo atualizado corretamente |
| ETA nao aparece | Comportamento esperado quando ainda ha poucas amostras de throughput |
| Numeros de cobertura desatualizados | Forcar refresh do ranking e checar o cache local |
| Widgets de mercado vazios | Verificar disponibilidade do yfinance e mapeamento de ticker |
| Tabelas do dashboard retornam vazias | Checar consultas em `src/query_layer.py` e cobertura real da empresa/anos selecionados |
