# V2 API Contract

## Escopo

Contrato HTTP da Fase 1 da V2 em `apps/api`.

Base tecnica:
- app: `apps/api/app/main.py`
- dominio: `src/read_service.py`
- DTOs: `src/contracts.py`

## Endpoints

### `GET /health`

Uso:
- retorna status da API
- retorna dialeto do banco
- expoe warnings e erros do `startup.py`

Resposta exemplo:

```json
{
  "status": "ok",
  "version": "v2-phase1",
  "database_dialect": "sqlite",
  "required_tables": ["financial_reports", "companies"],
  "warnings": [],
  "errors": []
}
```

### `GET /companies?search=&sector=&page=&page_size=`

Parametros:
- `search`: opcional, filtro por nome, ticker ou codigo CVM
- `sector`: opcional, slug canonico do setor
- `page`: opcional, default `1`, minimo `1`
- `page_size`: opcional, default `20`, maximo `100`

DTO de saida:
- `src.contracts.CompanyDirectoryPage`

Resposta exemplo:

```json
{
  "items": [
    {
      "cd_cvm": 9512,
      "company_name": "PETROBRAS",
      "ticker_b3": "PETR4",
      "setor_analitico": "Energia",
      "setor_cvm": "Energia",
      "sector_name": "Energia",
      "sector_slug": "energia",
      "anos_disponiveis": [2023, 2024],
      "total_rows": 30
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  },
  "applied_filters": {
    "search": "petro",
    "sector": null
  }
}
```

Regras do endpoint:
- retorna apenas empresas que possuem dados em `financial_reports`
- ordena por `company_name ASC`
- `sector` usa slug canonico estavel, nao label livre
- `anos_disponiveis` e montado de forma portavel na camada de leitura

### `GET /companies/filters`

DTO de saida:
- `src.contracts.CompanyFiltersDTO`

Resposta exemplo:

```json
{
  "sectors": [
    {
      "sector_name": "Energia",
      "sector_slug": "energia",
      "company_count": 12
    },
    {
      "sector_name": "Saneamento",
      "sector_slug": "saneamento",
      "company_count": 4
    }
  ]
}
```

### `GET /sectors`

Uso:
- retorna o hub setorial da V2 com snapshot agregado por setor
- a ordenacao padrao e `company_count DESC`, depois `sector_name ASC`

Resposta exemplo:

```json
{
  "items": [
    {
      "sector_name": "Energia",
      "sector_slug": "energia",
      "company_count": 12,
      "latest_year": 2024,
      "snapshot": {
        "roe": 0.18,
        "mg_ebit": 0.21,
        "mg_liq": 0.14
      }
    }
  ]
}
```

Regras do endpoint:
- `snapshot` usa os KPIs agregados do `latest_year` do setor
- `roe`, `mg_ebit` e `mg_liq` podem ser `null` quando o setor nao tiver contas suficientes
- o item do setor continua valido mesmo quando o snapshot vier parcial ou nulo

### `GET /sectors/{slug}?year=`

Parametros:
- `year`: opcional; inteiro positivo. Quando omitido, o backend usa o ano mais recente disponivel do setor

Resposta exemplo:

```json
{
  "sector_name": "Energia",
  "sector_slug": "energia",
  "company_count": 12,
  "available_years": [2023, 2024],
  "selected_year": 2024,
  "yearly_overview": [
    {
      "year": 2023,
      "roe": 0.16,
      "mg_ebit": 0.19,
      "mg_liq": 0.13
    }
  ],
  "companies": [
    {
      "cd_cvm": 9512,
      "company_name": "PETROBRAS",
      "ticker_b3": "PETR4",
      "roe": 0.47,
      "mg_ebit": 0.21,
      "mg_liq": 0.16
    }
  ]
}
```

Regras do endpoint:
- `404` para `slug` inexistente
- `422` para `year` invalido ou fora dos anos disponiveis do setor
- `available_years` sai em ordem crescente
- `companies` sai ordenado por `roe DESC`, depois `company_name ASC`, com `null` no fim
- `yearly_overview` agrega `roe`, `mg_ebit` e `mg_liq` por ano, ignorando valores ausentes
- `companies` do `selected_year` continuam presentes mesmo quando as metricas do ano vierem `null`

### `GET /companies/{cd_cvm}`

DTO de saida:
- `src.contracts.CompanyInfoDTO`

Resposta exemplo:

```json
{
  "cd_cvm": 9512,
  "company_name": "PETROBRAS",
  "nome_comercial": "Petrobras",
  "cnpj": "33.000.167/0001-01",
  "setor_cvm": "Energia",
  "setor_analitico": "Energia",
  "sector_name": "Energia",
  "sector_slug": "energia",
  "company_type": "comercial",
  "ticker_b3": "PETR4"
}
```

### `GET /companies/{cd_cvm}/export/excel`

Uso:
- retorna o workbook Excel completo da empresa como binario `.xlsx`
- usa sempre todos os anos disponiveis da empresa na base
- preserva o contrato atual do exportador da V1: `CAPA`, `GERAL`, `KPIs`,
  `DRE`, `BPA`, `BPP`, `DFC`, opcionais `DVA` e `DMPL` quando houver dados, e
  `METADADOS`

Headers principais:
- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="<ticker-ou-cvm>_<yyyymmdd>.xlsx"`

Regras do endpoint:
- `404` para empresa inexistente
- `422` para empresa existente sem anos exportaveis
- o workbook e gerado no dominio Python (`src/read_service.py` +
  `src/excel_exporter.py`), nao na camada HTTP

### `GET /companies/export/excel-batch?ids=`

Parametros:
- `ids`: obrigatorio; CSV de inteiros sem duplicatas, com ao menos 2 empresas,
  ex. `9512,4170`

Uso:
- retorna um `.zip` com um workbook `.xlsx` por empresa selecionada
- existe para o fluxo `/comparar`, sem inventar um workbook combinado novo

Headers principais:
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="comparar_excel_lote.zip"`

Regras do endpoint:
- `404` se alguma empresa informada nao existir
- `422` para `ids` invalido, duplicado ou com menos de 2 empresas
- cada arquivo interno reutiliza o mesmo contrato do endpoint individual por
  empresa
- a ordem dos arquivos no lote segue a ordem dos `ids` recebidos

### `GET /companies/{cd_cvm}/years`

Resposta:

```json
[2023, 2024]
```

### `GET /companies/{cd_cvm}/statements?stmt=&years=`

Parametros:
- `stmt`: obrigatorio; aceitos `BPA`, `BPP`, `DRE`, `DFC`, `DVA`, `DMPL`
- `years`: obrigatorio; CSV de inteiros sem duplicatas, ex. `2023,2024`

DTO de saida:
- `src.contracts.StatementMatrix`

Resposta exemplo:

```json
{
  "cd_cvm": 9512,
  "statement_type": "DRE",
  "years": [2023, 2024],
  "exclude_conflicts": true,
  "table": {
    "columns": ["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE", "2023", "2024"],
    "rows": [
      {
        "CD_CONTA": "3.01",
        "DS_CONTA": "Receita Liquida",
        "STANDARD_NAME": "Receita",
        "LINE_ID_BASE": "dre-1",
        "2023": 1000.0,
        "2024": 1100.0
      }
    ]
  }
}
```

### `GET /companies/{cd_cvm}/kpis?years=`

Parametros:
- `years`: obrigatorio; CSV de inteiros sem duplicatas

DTO de saida:
- `src.contracts.KPIBundle`

Resposta exemplo:

```json
{
  "cd_cvm": 9512,
  "years": [2023, 2024],
  "annual": {
    "columns": ["CATEGORIA", "KPI_ID", "2023", "2024"],
    "rows": [
      {
        "CATEGORIA": "Rentabilidade",
        "KPI_ID": "MG_EBIT",
        "2023": 0.2,
        "2024": 0.218182
      }
    ]
  },
  "quarterly": {
    "columns": ["CATEGORIA", "KPI_ID", "2023", "2024"],
    "rows": []
  }
}
```

### `GET /companies/{cd_cvm}/summary?years=`

Parametros:
- `years`: obrigatorio; CSV de inteiros sem duplicatas, ex. `2023,2024`

DTO de saida:
- `src.contracts.StatementSummaryDTO`

Resposta exemplo:

```json
{
  "cd_cvm": 9512,
  "years": [2023, 2024],
  "blocks": [
    {
      "stmt_type": "DRE",
      "title": "DRE — Resumo Condensado",
      "table": {
        "columns": ["CD_CONTA", "LABEL", "IS_SUBTOTAL", "2023", "2024"],
        "rows": [
          {
            "CD_CONTA": "3.01",
            "LABEL": "Receita",
            "IS_SUBTOTAL": true,
            "2023": 1000.0,
            "2024": 1100.0
          }
        ]
      }
    }
  ]
}
```

Regras do endpoint:
- `blocks` contem apenas demonstracoes com dados disponiveis para os anos solicitados
- ordem dos blocos: DRE, BPA, BPP, DFC (quando presentes)
- cada bloco expoe apenas linhas de resumo condensado (codigos subtotais e filhos diretos selecionados)
- `IS_SUBTOTAL` e `true` para codigos marcados como subtotais em cada demonstracao
- se nenhuma demonstracao tiver dados, `blocks` retorna `[]` (nao e erro)
- `years` no response reflete exatamente os anos solicitados, ordenados ascendente

### `GET /refresh-status?cd_cvm=`

Parametros:
- `cd_cvm`: opcional

DTO de saida:
- `src.contracts.RefreshStatusDTO`

Resposta exemplo:

```json
[
  {
    "cd_cvm": 9512,
    "company_name": "PETROBRAS",
    "source_scope": "local",
    "last_attempt_at": "2026-04-08T08:50:00",
    "last_success_at": "2026-04-08T08:55:00",
    "last_status": "success",
    "last_error": null,
    "last_start_year": 2023,
    "last_end_year": 2024,
    "last_rows_inserted": 30,
    "updated_at": "2026-04-08T08:55:00"
  }
]
```

### `GET /base-health?start_year=&end_year=&force_refresh=`

Parametros:
- `start_year`: obrigatorio
- `end_year`: obrigatorio
- `force_refresh`: opcional, default `false`

DTO de saida:
- `src.contracts.HealthSnapshot`

Resposta exemplo:

```json
{
  "generated_at": "2026-04-08T09:00:00",
  "start_year": 2023,
  "end_year": 2024,
  "total_cells": 4,
  "completed_cells": 3,
  "missing_cells": 1,
  "pct": 75.0,
  "health_score": 82.5,
  "health_status": "atencao",
  "eta_hours": 1.5,
  "throughput_per_hour": 2.0,
  "throughput_confidence": "medium",
  "per_year": [],
  "prioritized_companies": [],
  "raw": {}
}
```

## Regras de interface

- respostas usam DTOs estabilizados em `src/contracts.py`
- nao expor `DataFrame` bruto nos endpoints JSON
- `404` para empresa inexistente
- `422` para validacao HTTP e parametros invalidos
- `503` para falha operacional ou banco indisponivel
- endpoints binarios devem usar `Content-Disposition: attachment` com nome de
  arquivo estavel

Payload padrao de erro:

```json
{
  "error": {
    "code": "service_unavailable",
    "message": "Falha operacional ao processar a requisicao."
  }
}
```
