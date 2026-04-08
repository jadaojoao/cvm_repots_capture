# V2 Phase 1 - Backend First Read-Only

## Objetivo

Entregar a Fase 1 da V2 como um backend `FastAPI` local, read-only e documentado, sem reescrever o dominio da V1.

Esta fase existe para criar uma fronteira estavel entre o nucleo Python atual e a futura web app:
- `src/` continua como fonte de verdade do dominio;
- `apps/api` nasce como adaptador HTTP fino;
- `apps/web` fica explicitamente fora desta fase.

## Decisoes congeladas

- Arquitetura da fase: `backend-first`
- Layout do repo: `apps/api` agora, `apps/web` depois
- Banco default local: `SQLite`
- Gate obrigatorio para encerrar a fase: smoke contra `PostgreSQL` real
- Escopo da proxima fase: `busca + detalhe rico de empresa`
- V1 continua operacional em paralelo

## Fronteira tecnica da fase

`apps/api` nao implementa regra de negocio. Ele apenas adapta HTTP para os contratos ja existentes:

- `src/settings.py`: configuracao e paths canonicos
- `src/startup.py`: diagnostico de bootstrap e readiness
- `src/read_service.py`: busca, detalhe, demonstracoes, KPIs, health snapshot e refresh status
- `src/contracts.py`: DTOs e contratos de dados da transicao

Regra pratica: qualquer nova interface da V2 deve consumir `src/read_service.py` ou novos contratos explicitamente adicionados em `src/`, e nao SQL espalhado.

## Estrutura entregue

```text
apps/
`-- api/
    |-- app/
    |   |-- main.py
    |   |-- dependencies.py
    |   |-- presenters.py
    |   `-- routes/
    |       |-- health.py
    |       |-- companies.py
    |       `-- status.py
    |-- requirements.txt
    |-- requirements-dev.txt
    `-- tests/
```

## Como rodar localmente

Instalacao minima para a V2 API:

```powershell
pip install -r apps/api/requirements-dev.txt
```

Subir a API:

```powershell
uvicorn apps.api.app.main:app --reload
```

Documentacao viva:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Rodar lado a lado com a V1:

1. `python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical`
2. `python desktop/cvm_pyqt_app.py`
3. `streamlit run dashboard/app.py`
4. `uvicorn apps.api.app.main:app --reload`

## Criterios de aceite da fase

- API local sobe em SQLite e responde `/health`
- contratos HTTP cobrem diretorio paginado de empresas, filtros canonicos, detalhe, anos, demonstracoes, KPIs, refresh status e health snapshot
- Swagger/OpenAPI fica utilizavel
- testes da API passam com `TestClient`
- suite principal da V1 continua verde
- smoke SQLite passa com `runtime_doctor.py` e `db_portability_smoke.py --write-check`
- validacao em PostgreSQL fica documentada e obrigatoria antes de considerar a fase encerrada

## Validacao obrigatoria antes de fechar a fase

SQLite local:

```powershell
python scripts/runtime_doctor.py --require-db --table financial_reports --table companies --require-canonical
python scripts/db_portability_smoke.py --write-check
pytest tests -q
pytest apps/api/tests -q
```

PostgreSQL real:

```powershell
python scripts/runtime_doctor.py --database-url postgresql://user:pass@host:5432/db --require-db --table financial_reports --table companies
python scripts/db_portability_smoke.py --database-url postgresql://user:pass@host:5432/db --write-check
```

## O que esta fora da Fase 1

- `apps/web` real em `Next.js`
- auth
- endpoints de escrita
- job/queue web para refresh
- deploy remoto

## Backlog imediato da Fase 2

1. Criar `apps/web` em `Next.js`
2. Entregar rota `/` com busca e selecao de empresa
3. Entregar rota `/companies/[cd_cvm]` com detalhe rico
4. Consumir exclusivamente a API da Fase 1
5. Publicar um preview interno somente leitura
