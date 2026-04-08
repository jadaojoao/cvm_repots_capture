# 0002 — Stack recomendada para a V2 com GitHub Student Developer Pack

- **Status:** accepted
- **Data:** 2026-04-07
- **Autor:** human+ai

## Contexto

O projeto atual ja funciona com:
- pipeline e scraper em Python;
- banco local SQLite com suporte opcional a PostgreSQL;
- app desktop PyQt6 para atualizacao operacional;
- dashboard Streamlit read-only para consulta e download.

O objetivo da V2 e adicionar uma superficie web mais produtizada sem reescrever o motor de ingestao.
O `docs/STUDENT_PACK_PLAN.md` ja apontava a direcao `frontend + API + Postgres`, mas ainda faltava congelar a stack recomendada.

Tambem era necessario separar:
- o que e escolha arquitetural do projeto;
- o que e apenas beneficio ou ferramenta do GitHub Student Developer Pack.

Levantamento revalidado em 2026-04-07 nas paginas oficiais do GitHub Education e Appwrite Education:
- GitHub Student Developer Pack;
- pagina do beneficio GitHub Codespaces;
- Appwrite Education em colaboracao com o GitHub Student Developer Pack.

## Decisao

Para a V2, a stack recomendada para este projeto e:

- **UI:** `Next.js`
- **Web server:** `Nginx` apenas quando houver self-hosting; em plataforma gerenciada, pode ser omitido no inicio
- **Application server:** `FastAPI + Uvicorn`
- **Database:** `PostgreSQL`
- **Operating system:** `Ubuntu Linux`

Complementos importantes:
- o scraper/updater continua em Python;
- a V1 atual continua operando em paralelo durante a transicao;
- `Streamlit` continua valido como interface interna/read-only enquanto a V2 amadurece;
- `Appwrite` nao vira backend principal deste projeto; pode ser avaliado apenas como acelerador de auth, storage ou prototipos.

## Racional

### 1. Melhor aderencia ao codigo existente

O backend atual ja esta em Python, com regras de negocio relevantes em:
- `src/scraper.py`
- `src/query_layer.py`
- `src/kpi_engine.py`
- `src/database.py`

Trocar o backend principal para outra stack agora aumentaria custo de migracao sem vantagem clara.
`FastAPI` permite expor leitura de demonstracoes, KPIs e metadados reaproveitando a base atual.

### 2. PostgreSQL e o banco alvo correto para a V2

O projeto ja admite PostgreSQL via `DATABASE_URL`, e a necessidade da V2 e multiusuario, acesso remoto e consultas analiticas mais serias.
Por isso, `PostgreSQL` e uma extensao natural da V1; `SQLite` permanece util para dev local e operacao individual.

### 3. Next.js e a melhor aposta para a interface web da V2

O dashboard atual em Streamlit serve bem para consulta interna, mas nao e a melhor fundacao para:
- auth e sessao de usuario;
- UX mais refinada;
- rotas e composicao de produto;
- crescimento de frontend ao longo do tempo.

`Next.js` e uma escolha pragmaticamente forte para uma V2 web sem forcar mudanca do backend.

### 4. Ubuntu Linux e o default mais simples para deploy

Para ambiente remoto, `Ubuntu Linux` continua sendo o caminho com menos atrito para:
- deploy;
- observabilidade;
- troubleshooting;
- documentacao e suporte comunitario.

Windows permanece aceitavel para desenvolvimento local.

### 5. Nginx e opcional, nao um compromisso precoce

`Nginx` continua sendo uma boa escolha como reverse proxy em self-hosting.
Mas ele nao deve ser tratado como requisito da primeira entrega da V2 se a publicacao ocorrer em plataforma gerenciada.

## Como o Student Pack entra nessa decisao

O GitHub Student Developer Pack influencia ferramentas e velocidade, nao a arquitetura principal por si so.

Ferramentas/beneficios que reforcam esta direcao:
- `GitHub Copilot` para acelerar implementacao e refactor
- `GitHub Codespaces` para ambiente reproduzivel
- `JetBrains Student` para produtividade em Python
- `Codecov` para cobertura/guardrails
- `Datadog` e `Sentry` para observabilidade
- `Appwrite Education` como opcional para servicos perifericos, nao como core analytics backend

Correcao factual importante:
- o registro anterior citava `Copilot Pro`;
- a formulacao segura aqui e `GitHub Copilot` para estudantes, conforme o beneficio vigente deve ser revalidado na pagina oficial no momento da ativacao.

## Alternativas Consideradas

- **Manter Streamlit como UI principal de longo prazo:** simples no curto prazo, mas mais fraco para uma V2 de produto.
- **Usar Appwrite como backend/database principal:** atraente pelo beneficio educacional, mas desalinhado com a natureza analitica e relacional do projeto.
- **Migrar backend para Node/Java/.NET:** possivel, mas com alto custo de reimplementacao das regras que ja existem em Python.
- **Windows como SO de producao:** aceitavel em contexto local, mas inferior como default de deploy.

## Consequencias

- A V1 nao precisa ser descartada para iniciar a V2.
- A fronteira recomendada passa a ser:
  - ingestao/refresh em Python;
  - API de leitura em Python;
  - frontend web em `Next.js`;
  - banco compartilhado em `PostgreSQL`.
- O primeiro deploy da V2 pode acontecer sem `Nginx` se usar plataforma gerenciada.
- `Appwrite` deve ser tratado como opcional e periferico, nao como decisao central de stack.

## Referencias

- [GitHub Student Developer Pack](https://education.github.com/pack)
- [GitHub Codespaces benefit page](https://education.github.com/pack/redeem/github-codespaces)
- [Appwrite Education](https://appwrite.io/education)
- [docs/STUDENT_PACK_PLAN.md](../STUDENT_PACK_PLAN.md)
