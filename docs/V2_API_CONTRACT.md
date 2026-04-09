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
- nao expor `DataFrame` bruto
- `404` para empresa inexistente
- `422` para validacao HTTP e parametros invalidos
- `503` para falha operacional ou banco indisponivel

Payload padrao de erro:

```json
{
  "error": {
    "code": "service_unavailable",
    "message": "Falha operacional ao processar a requisicao."
  }
}
```
