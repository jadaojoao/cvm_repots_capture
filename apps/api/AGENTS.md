# AGENTS.md — apps/api

Contrato operacional para qualquer agente ou pessoa que trabalhe nesta area.

## Leitura obrigatoria antes de comecar

1. `docs/INTERFACE_MAP.md` — todas as rotas do frontend, quais endpoints cada
   rota consome, e quais endpoints ainda nao existem mas sao necessarios.
   **Sem ler este arquivo voce nao sabe quem depende do que voce vai criar ou alterar.**

2. `docs/V2_API_CONTRACT.md` — contrato HTTP completo: payloads, status codes,
   validacoes e convencoes de resposta de erro.

3. `AGENTS.md` (raiz) — fluxo obrigatorio de issue -> branch -> PR -> merge.

## Regras especificas desta area

- Toda nova rota ou mudanca de schema deve ser refletida em `docs/V2_API_CONTRACT.md`
  e em `docs/INTERFACE_MAP.md` no mesmo PR.
- Remover ou alterar um endpoint existente requer verificar a tabela inversa em
  `docs/INTERFACE_MAP.md` para identificar rotas do frontend afetadas.
  Classifique como `risk:contract-sensitive`.
- Endpoints novos que estavam listados em "Pendencias de backend" em
  `docs/INTERFACE_MAP.md` devem ter essa linha atualizada quando entregues.
- A API e read-only. Nenhuma rota de escrita deve ser adicionada sem task
  propria e coordenacao explicita.
- O adaptador HTTP fica em `apps/api/`. O dominio fica em `src/`.
  Nao reimplemente logica SQL ou KPI dentro de `apps/api/`.

## Onde fica o que

| Responsabilidade | Arquivo |
|---|---|
| Criacao do app FastAPI + CORS + middlewares | `apps/api/app/main.py` |
| Injecao de dependencias e validacoes | `apps/api/app/dependencies.py` |
| Conversao DTO -> payload HTTP | `apps/api/app/presenters.py` |
| Rotas de empresas | `apps/api/app/routes/companies.py` |
| Rotas de saude e status | `apps/api/app/routes/health.py`, `status.py` |
| Queries SQL e leitura do banco | `src/read_service.py`, `src/query_layer.py` |
| DTOs de dominio | `src/contracts.py` |
| Calculo de KPIs | `src/kpi_engine.py` |
