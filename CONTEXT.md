# CVM Reports Capture

## Resumo Executivo

Este projeto busca extrair demonstrações financeiras históricas de companhias listadas na CVM, organizar os dados em um Excel auditável e deixar a base pronta para uma etapa futura de padronização de contas. O caso de teste principal até aqui é a Petrobras (PETR4).

- **Objetivo final:** gerar uma base histórica confiável e um Dashboard Analítico (Terminal Financeiro) para análise fundamentalista rápida.
- **Escopo atual:** Prioridades 1 a 7 concluídas ou em fase final (Integridade, QA, Padronização, Bancos, Análise/KPIs, Dashboard e Automação SQLite).
- **Estado atual:** O projeto agora possui um **Terminal CVM Analytics** alimentado por SQLite com dados 2022-2025 e comparação de peers.

---

## 1. O que é o projeto

O projeto extrai dados financeiros públicos da CVM para montar, em um único Excel, as demonstrações financeiras históricas de uma companhia. O foco é produzir um output confiável, legível e verificável, sem misturar períodos, versões ou linhas conflitantes.

O pipeline deve funcionar como uma base de trabalho para análises futuras, valuation, pesquisa financeira e, principalmente, para uma camada posterior de padronização das contas.

---

## 2. Objetivo Final

O objetivo final é ter um pipeline único e consolidado que receba como entrada informações simples do usuário — como diretórios, companhia, ticker ou código, ano inicial e ano final — e gere automaticamente um Excel final com BPA, BPP, DRE e DFC, além de abas de QA.

Esse Excel precisa estar pronto para ser consumido por humanos e por etapas seguintes do projeto, especialmente a padronização por dicionário de contas, sem que seja necessário corrigir manualmente inconsistências de períodos, duplicatas ou conflitos de linha.

---

## 3. Fonte de Dados e Entidade Regulatória

A fonte principal do projeto é a CVM (Comissão de Valores Mobiliários). O pipeline precisa lidar com diferentes publicações da companhia, incluindo informações trimestrais (ITR) e anuais (DFP), preservando consistência de recorte e evitando misturar consolidado com individual quando isso não for desejado.

Na prática, o projeto precisa combinar extração, tratamento e validação. O dado bruto da CVM não deve ser copiado "como está" para o Excel final sem passar pelas regras de QA do pipeline.

---

## 4. Caso de Teste Principal

O caso de teste mais trabalhado até aqui é **PETR4 / Petrobras**. Isso não significa que o projeto deva ser hardcoded para a Petrobras; o código precisa ser configurável no topo do arquivo, para rodar com outra companhia sem exigir refatoração estrutural.

A Petrobras foi usada como referência para detectar regressões, validar fechamentos de balanço e conferir se a DFC está sendo tratada corretamente em base trimestral standalone.

---

## 5. Escopo Técnico Atual

**Prioridade 1 (concluída):** integridade contábil e periodização correta. Isso inclui fechar Ativo Total e Passivo Total, evitar "carimbar" anual em trimestre e tratar corretamente a janela de anos.

**Prioridade 2 (concluída):** chave estável por linha (`LINE_ID_BASE`), base wide, `DS_CONTA_norm`, filtro de versão (`ORDEM_EXERC='ÚLTIMO'`), QA por conflitos reais e exportação limpa do Excel final.

**Prioridade 3 (concluída):** padronização por dicionário de contas. O pipeline adiciona a coluna `STANDARD_NAME` buscando correspondência do `CD_CONTA` com o plano de contas fixas oficial da CVM (Comerciais, Financeiras e Seguradoras). Adicionada também aba de `PADRONIZACAO` para verificar a precisão do de/para.

---

## 6. Regras de Negócio Essenciais

- O pipeline final deve gerar abas **BPA**, **BPP**, **DRE** e **DFC**.
- As linhas precisam ser identificadas por um `LINE_ID_BASE` estável. Sempre que possível, esse identificador deve usar `CD_CONTA`. Quando isso não for possível, deve existir uma chave sintética determinística baseada em `DS_CONTA` normalizado e metadados estáveis.
- `DS_CONTA` raw deve ser preservado, e `DS_CONTA_norm` deve existir em todas as abas. A normalização precisa ser forte e determinística: lower, remoção de acentos, trim, colapso de espaços, remoção de NBSP e padronização de pontuação.
- O output final **não deve usar sufixos artificiais** como `#1`, `#2`, etc. Esse padrão é uma regressão — transforma o ID em "ID do registro" em vez de "ID da conta".

---

## 7. Regras Específicas para DRE e DFC

- DRE e DFC devem manter colunas trimestrais **e** anuais. Para anos completos, a expectativa é ter `1Q`, `2Q`, `3Q`, `4Q` e `YYYY`.
- A DFC **não deve ficar cumulativa** no output final. Quando o dado da CVM vier em formato YTD, a conversão para trimestre standalone deve ser feita internamente, preservando também o ano cheio.
- Regra esperada para DFC standalone:
  - `Q1 = YTD_1Q`
  - `Q2 = YTD_2Q - YTD_1Q`
  - `Q3 = YTD_3Q - YTD_2Q`
  - `Q4 = ANUAL - YTD_3Q`
  - `YYYY = ANUAL`
- Se faltar algum trimestre intermediário, o pipeline **não deve inventar valores**. O correto é deixar `NaN` e registrar no QA.

---

## 8. QA e Critérios de Aceite

Antes de exportar o Excel final, o pipeline deve executar testes automáticos. Se uma validação crítica falhar, o output não deve ser salvo silenciosamente como se estivesse correto.

**Validações obrigatórias:**
- `LINE_ID_BASE` único por aba
- `DS_CONTA_norm` sem nulos
- Ausência de `"#"` nos IDs finais
- Fechamento do BPA e do BPP (Ativo Total = Passivo Total)
- DFC fechando: `Q1 + Q2 + Q3 + Q4 = YYYY` quando todos os períodos existirem

As abas **QA_LOG** e **QA_Errors** precisam existir para facilitar rastreabilidade, debug e prevenção de regressões.

---

## 9. Como Pensar sobre o Projeto

Este projeto não é apenas um "scraper" da CVM. Ele é um **pipeline de dados financeiros com regras de consistência**. O dado extraído só é útil se o output final for auditável e estruturalmente estável.

Separar o que é **dado bruto da CVM** do que é **output final processado** é fundamental. Misturar essas camadas costuma ser a principal fonte de regressão.

Ao revisar um output, sempre tratar o **último arquivo gerado** como fonte da verdade. Não concluir que um erro "continua existindo" sem verificar diretamente o arquivo atual.

---

## 10. Entradas Configuráveis pelo Usuário

O código consolidado do projeto concentra no topo todas as informações que o usuário pode alterar: diretórios, nome da empresa, ticker ou código, ano inicial, ano final, recorte consolidado/individual, arquivos de saída, cache e parâmetros de execução.

A intenção é que alguém consiga adaptar o pipeline a outra empresa apenas editando esse bloco inicial de configuração, sem precisar navegar por múltiplos módulos.

**Uso via CLI:**
```bash
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
python main.py --companies VALE ITAU --start_year 2020 --end_year 2024
python main.py --companies 9512 --start_year 2020 --end_year 2024  # por código CVM
```

---

## 11. Próximos Marcos de Desenvolvimento (Roadmap)

Com as fundações do pipeline de dados impecáveis (P1 a P3), os próximos passos aprovados para o projeto seguem esta ordem de prioridade:

**Prioridade 4: Integração com Bancos (Instituições Financeiras)**
Adaptar e validar a extração para ler balanços de bancos (ex: Itaú, Bradesco), cujo plano de contas (3.xx - DRE) é totalmente diferente do padrão industrial. Aproveitaremos o dicionário canônico já construído.

**Prioridade 5: Análise e Indicadores Financeiros**
Criar um `analysis.py` que gere uma nova aba no Excel, calculando automaticamente as principais métricas (Margem Bruta, Margem EBITDA, ROE, Dívida Líquida, FCF) com base nas contas padronizadas da P3.

**Prioridade 6: Dashboard Visual**
Implementar um frontend analítico simples (Streamlit ou Dash) para ler os XLSX gerados e produzir comparações históricas em gráficos interativos.

**Prioridade 7: Expansão em Massa (Automação SQLite)**
Orquestrar a ferramenta para ler as Top 100 ações da B3 de uma vez, salvando todo o conteúdo histórico validado em um banco de dados relacional flexível (SQLite/PostgreSQL) para viabilizar queries SQL pesadas.

---

## 12. Checklist para Quem Entrar no Projeto

- [ ] Entender a diferença entre RAW_LONG (dado bruto, formato longo) e FINAL_WIDE (output processado, formato wide).
- [ ] Validar se BPA, BPP, DRE e DFC estão presentes e com períodos coerentes.
- [ ] Checar se `LINE_ID_BASE` está único por aba.
- [ ] Confirmar se `DS_CONTA_norm` existe e está preenchido.
- [ ] Revisar QA_LOG e QA_Errors antes de confiar no Excel final.
- [ ] Lembrar que a P1, P2 e P3 estão no código `CVMScraper`. Novas lógicas analíticas e dashboards devem seguir para módulos separados (conforme roadmap).

---

## Stack Técnica

- **Linguagem:** Python 3.11+
- **Bibliotecas:** `pandas`, `openpyxl`, `requests`
- **Fonte dos dados:** CVM pública — `https://dados.cvm.gov.br`

---

## Estrutura de Pastas

```
cvm_repots_capture/
├── src/
│   ├── scraper.py        # Motor principal de extração e processamento (CVMScraper)
│   ├── dictionary.py     # Construtor do dicionário de contas CVM
│   └── utils.py          # Normalização de contas e geração de LINE_ID_BASE
├── scripts/
│   ├── validation/       # Scripts de QA e verificação de dados
│   └── experiments/      # Métodos experimentais e isolados
├── data/
│   └── input/            # CSVs e ZIPs brutos da CVM (DFP/ITR 2020–2025)
├── output/               # Relatórios Excel gerados e logs de execução
│   └── logs/
├── docs/
│   └── PROJECT_RULES.md  # Convenções e regras do projeto
├── main.py               # Entrypoint CLI (argparse)
├── CONTEXT.md            # Este documento
└── MEMORIADASIA.md       # Memória compartilhada entre agentes de IA
```

---

## Convenções de Código

- `snake_case` para variáveis e nomes de arquivos
- Orientação a Objetos no motor principal (`CVMScraper`)
- Docstrings em todas as funções públicas
- Bloco `USER CONFIGURATION` no topo de cada arquivo executável com todas as variáveis configuráveis
- `LINE_ID_BASE` como identificador canônico de linha (nunca usar alias `LINE_ID`)

---

## Estado Atual

- Pipeline funcional para BPA, BPP, DRE e DFC com Prioridades 1 e 2 concluídas.
- Caso de teste de referência: Petrobras (PETR4), com validações de fechamento de balanço e DFC standalone.
- DFC convertida de YTD para standalone trimestral via `convert_dfc_ytd_to_standalone()`.
- QA automatizado com abas `QA_LOG` e `QA_Errors` no Excel final.
- Cobertura de dados: 2020–2025, todos os setores da CVM.
- Prioridade 3 concluída: `STANDARD_NAME` integrado no Excel final via `AccountStandardizer`, com aba extra `PADRONIZACAO` para estatística de leitura.
- Roadmap definido pelo usuário: a próxima entrega será a Prioridade 4 (Extração de Bancos Financeiros como Itau e Bradesco).

---

## 13. Bootstrap rapido (Windows) - Atualizacao 2026-03-26

Para subir o ambiente em uma maquina Windows do zero:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_windows.ps1
```

O script `scripts/bootstrap_windows.ps1` faz:
- detecta `python`/`py` no sistema;
- instala Python 3.11 via `winget` se necessario;
- cria ou reaproveita `.venv`;
- atualiza `pip`, `setuptools`, `wheel`;
- instala `requirements.txt`;
- roda `scripts/smoke_validate.py --skip-compile` (pode pular com `-SkipSmoke`).

Flags utilitarias:
- `-ForceRecreateVenv`: recria `.venv` do zero.
- `-SkipSmoke`: pula a validacao smoke ao final.

Fluxo recomendado apos bootstrap:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated
python scripts/gerar_base_analitica.py
python scripts/calc_financial_kpis.py
python scripts/smoke_validate.py
streamlit run dashboard/app.py
```
