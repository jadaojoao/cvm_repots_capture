# Como Rodar — CVM Analytics

Este guia explica como abrir e usar o dashboard financeiro, passo a passo.
Não é necessário saber programar para seguir as instruções.

---

## Antes de começar — o que você precisa ter instalado

- **Python 3.10 ou superior** — para verificar, abra o terminal e digite:
  ```
  python --version
  ```
  Se aparecer `Python 3.10.x` ou superior, está ok.
  Se não tiver, baixe em: https://www.python.org/downloads/

- **Pasta do projeto** — você precisa estar dentro da pasta `cvm_repots_capture`
  antes de rodar qualquer comando.

---

## Passo 1 — Abrir o terminal dentro da pasta do projeto

1. Abra o **Explorador de Arquivos** e navegue até a pasta `cvm_repots_capture`.
2. Clique na barra de endereço (onde aparece o caminho da pasta), digite `cmd` e aperte **Enter**.
3. Um terminal preto vai abrir já dentro da pasta correta.

> Alternativa: abra o PowerShell, o Prompt de Comando ou o terminal do VSCode
> e navegue até a pasta com: `cd C:\caminho\para\cvm_repots_capture`

---

## Passo 2 — Ativar o ambiente virtual

O ambiente virtual isola as bibliotecas do projeto para não conflitar com outros programas.
Você precisa ativá-lo toda vez que for usar o sistema.

**No Prompt de Comando (CMD):**
```
.venv\Scripts\activate.bat
```

**No PowerShell:**
```
.\.venv\Scripts\Activate.ps1
```

Quando der certo, você vai ver `(.venv)` no início da linha do terminal, assim:
```
(.venv) C:\...\cvm_repots_capture>
```

> **Se aparecer erro de permissão no PowerShell**, rode este comando uma vez e tente novamente:
> ```
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

> **Se ainda não criou o ambiente virtual**, rode antes:
> ```
> python -m venv .venv
> ```

---

## Passo 3 — Instalar as bibliotecas (somente na primeira vez)

Com o ambiente virtual ativo, rode:
```
pip install -r requirements.txt
```

Isso instala tudo que o projeto precisa. Pode demorar alguns minutos.
Nas próximas vezes você não precisa repetir este passo.

---

## Passo 4 — Abrir o dashboard

Com o ambiente virtual ativo, rode:
```
streamlit run dashboard/app.py
```

O terminal vai mostrar uma mensagem parecida com:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

Abra seu navegador e acesse: **http://localhost:8501**

O dashboard vai aparecer automaticamente.

> Para fechar o dashboard, volte ao terminal e aperte **Ctrl + C**.

---

## Passo 5 — Como usar o dashboard

### Escolher uma empresa
Na barra lateral (esquerda da tela), você pode:
- Digitar o nome da empresa na caixa de busca
- Ou digitar o código CVM numérico (ex: `9512` para PETROBRAS)

Após selecionar, os dados carregam automaticamente.

---

### O que tem em cada aba

**Visão Geral**
A aba principal. Mostra tudo o que você precisa saber de uma empresa:

- **Indicadores Principais** — Receita, Lucro, Ativo Total, ROE, Dívida/EBITDA e Liquidez Corrente com a variação em relação ao ano anterior.
- **Valuation de Mercado** — Cotação atual, Market Cap, P/L, P/VP, EV/EBITDA e Dividend Yield. Dados em tempo real do Yahoo Finance, atualizados a cada 15 minutos. Só aparece para empresas com ações na bolsa.
- **Histórico de Preço (1 ano)** — Gráfico com o preço da ação, a média móvel de 20 dias e o volume negociado por dia. Barras verdes = dia de alta, vermelhas = dia de queda.
- **Evolução Trimestral** — Gráficos de barras com Receita, Lucro, Resultado Bruto e Fluxo de Caixa ao longo dos trimestres.
- **Indicadores Anuais** — Linhas mostrando a evolução de Margem Bruta, ROE, Margem Líquida e ROA ano a ano.
- **Comparar com outra empresa** — Use o seletor no topo da aba para escolher uma segunda empresa. Os gráficos de Receita, Lucro, Margem e ROE aparecem sobrepostos para facilitar a comparação.
- **Composição Patrimonial** — Gráficos de rosca mostrando como o Ativo e o Passivo + PL estão distribuídos.
- **Variação Anual do Resultado** — Gráfico cascata mostrando o que mudou de um ano para o outro na receita e resultado.

**Peers (Concorrentes)**
Compara a empresa selecionada com outras do mesmo setor:
- Posição de ROE e Margem Líquida em relação à média do setor
- Tabela de ranking com todas as empresas do setor
- Gráfico de bolhas: quanto mais à direita e acima, melhor a empresa; o tamanho da bolha representa o ativo total

**Mercado**
Ranking de todas as empresas do banco por setor. Você escolhe o ano e a métrica (Margem Líquida, ROE, Margem Bruta ou ROA) e vê quem está melhor e pior.

**Demonstrativo**
Tabela com todos os dados financeiros brutos da empresa, organizada por período. Útil para quem quer ver os números completos.

**Exportar**
Baixa os dados da empresa selecionada em formato Excel (`.xlsx`).

---

## Passo 6 — Atualizar os dados financeiros

Os dados financeiros vêm do site da CVM (Comissão de Valores Mobiliários).
Para baixar os relatórios mais recentes, você tem três opções:

### Opção A — Pelo próprio dashboard (mais fácil)
Na barra lateral, clique no botão **"🔄 Atualizar Dados"**.
O sistema vai baixar os dados de todas as 69 empresas automaticamente.
Aguarde — pode levar de 5 a 15 minutos dependendo da sua conexão.

### Opção B — Pelo terminal
Com o ambiente virtual ativo, rode:
```
python scripts/atualizar_todos.py
```

Para atualizar apenas anos específicos:
```
python scripts/atualizar_todos.py --anos 2024 2025
```

Para ver quais empresas seriam atualizadas sem baixar nada de verdade:
```
python scripts/atualizar_todos.py --dry-run
```

Os registros de cada atualização ficam salvos na pasta `logs/`.

### Opção C — Automático todo domingo (já configurado)
Uma tarefa chamada **`CVM_Atualizar_Dados`** já está programada no Windows
para rodar todo domingo às 7h da manhã, mesmo que o computador estivesse
desligado antes desse horário.

Para verificar se está funcionando:
```powershell
Get-ScheduledTask -TaskName CVM_Atualizar_Dados
```

Para rodar agora sem esperar o domingo:
```powershell
Start-ScheduledTask -TaskName CVM_Atualizar_Dados
```

---

## Passo 7 — Adicionar uma nova empresa ao dashboard

O banco já tem 69 empresas. Para adicionar mais, siga os passos:

**1. Rodar o scraper para baixar os dados da nova empresa:**
```
python main.py --cvm CODIGO_CVM --anos 2022 2023 2024 2025
```
Substitua `CODIGO_CVM` pelo código numérico da empresa (ex: `9512` para PETROBRAS).
O código CVM pode ser encontrado no site da CVM: https://www.cvm.gov.br

**2. (Opcional) Mapear o ticker para ver cotação e valuation:**

Abra o arquivo `dashboard/constants.py` em qualquer editor de texto (Bloco de Notas, VSCode, etc.).
Encontre o bloco `TICKER_MAP` e adicione uma linha no formato:
```python
99999: 'NOVO3.SA',   # NOME DA EMPRESA
```
- `99999` = código CVM da empresa (o mesmo que você usou no passo anterior)
- `'NOVO3.SA'` = código da ação na bolsa, como aparece no Yahoo Finance
  (para verificar, pesquise a empresa em finance.yahoo.com)

**3. Recarregar o dashboard** — feche e abra novamente (Ctrl+C no terminal e rode `streamlit run dashboard/app.py` de novo).

---

## Problemas comuns

| O que aconteceu | O que fazer |
|---|---|
| Terminal mostra `ModuleNotFoundError` | O ambiente virtual não está ativo. Volte ao Passo 2. |
| Terminal mostra `python não reconhecido` | Python não está instalado ou não está no PATH. Reinstale em python.org marcando "Add to PATH". |
| Dashboard abre mas não mostra nenhuma empresa | Os dados ainda não foram baixados. Execute o Passo 6. |
| Valuation e cotação não aparecem | Verifique sua conexão com a internet. Os dados vêm do Yahoo Finance em tempo real. |
| Erro de encoding / caracteres estranhos | Antes de rodar qualquer comando, execute: `set PYTHONIOENCODING=utf-8` |
| Dashboard não atualiza ao editar arquivos | Clique em **"Always rerun"** na barra amarela que aparece no topo da página. |
| Erro "Permission denied" no PowerShell | Execute: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente de novo. |
| Botão "Atualizar" não faz nada | Veja a pasta `logs/` — haverá um arquivo com o erro completo. |
| Porta 8501 já em uso | Rode com outra porta: `streamlit run dashboard/app.py --server.port 8502` |

---

## Estrutura dos arquivos (para quem quiser mexer no código)

```
cvm_repots_capture/
│
├── dashboard/             # Tudo relacionado ao painel visual
│   ├── app.py             # Ponto de entrada do dashboard
│   ├── constants.py       # Configurações e mapa de tickers
│   ├── db.py              # Conexão com o banco de dados
│   ├── loaders.py         # Carregamento de dados
│   ├── kpis.py            # Cálculo dos indicadores financeiros
│   ├── charts.py          # Geração dos gráficos
│   └── tabs/              # Cada aba do dashboard em um arquivo separado
│
├── src/                   # Motor do scraper (baixa os dados da CVM)
├── scripts/               # Scripts de automação
├── data/db/               # Banco de dados SQLite (arquivo local)
├── logs/                  # Registros das atualizações
├── main.py                # Comando para baixar dados de uma empresa
└── requirements.txt       # Lista de bibliotecas necessárias
```

> Para alterar um KPI: edite `dashboard/kpis.py`
> Para alterar um gráfico: edite `dashboard/charts.py`
> Para alterar o layout de uma aba: edite o arquivo correspondente em `dashboard/tabs/`

---

## Deixar o dashboard online (acessível pela internet, sempre no ar)

Por padrão o dashboard só funciona no seu computador. Para publicá-lo na internet
de graça, você vai usar dois serviços:

- **Supabase** — banco de dados PostgreSQL gratuito na nuvem (substitui o arquivo SQLite local)
- **Streamlit Community Cloud** — hospedagem gratuita do painel, direto do seu GitHub

O código já está preparado para isso. Basta seguir os passos abaixo uma única vez.

---

### Etapa 1 — Criar uma conta no GitHub e subir o código

O Streamlit Cloud publica o dashboard diretamente de um repositório GitHub.

1. Crie uma conta gratuita em https://github.com
2. Crie um repositório novo (pode ser privado) com o nome que quiser, ex: `cvm-analytics`
3. Na pasta do projeto, abra o terminal com o ambiente virtual ativo e rode:
   ```
   git remote set-url origin https://github.com/SEU_USUARIO/cvm-analytics.git
   git push -u origin master
   ```
   Substitua `SEU_USUARIO` pelo seu nome de usuário do GitHub.

> Se for a primeira vez usando git, pode ser necessário configurar seu nome e e-mail:
> ```
> git config --global user.name "Seu Nome"
> git config --global user.email "seu@email.com"
> ```

---

### Etapa 2 — Criar o banco de dados na nuvem (Supabase)

O Supabase oferece um PostgreSQL gratuito com 500 MB — mais que suficiente para este projeto.

1. Acesse https://supabase.com e crie uma conta gratuita
2. Clique em **"New project"**
3. Escolha um nome (ex: `cvm-financials`), defina uma senha forte e selecione a região **South America (São Paulo)**
4. Aguarde o projeto inicializar (leva cerca de 1 minuto)
5. No menu lateral, vá em **Settings → Database**
6. Role até a seção **"Connection string"** e selecione a aba **"Transaction pooler"**
7. Copie a URI — ela tem este formato:
   ```
   postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```
   **Guarde essa URI**, você vai precisar dela nos próximos passos.

> A porta usada é **6543** (Transaction Pooler), não 5432. Isso é importante.

---

### Etapa 3 — Migrar os dados do seu computador para o Supabase

Este passo copia os dados do banco local (SQLite) para o banco na nuvem (Supabase).
Você só precisa fazer isso uma vez.

No terminal, com o ambiente virtual ativo, rode:

**Windows (CMD):**
```
set DATABASE_URL=postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
python scripts/migrate_to_supabase.py
```

**Windows (PowerShell):**
```
$env:DATABASE_URL="postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python scripts/migrate_to_supabase.py
```

Substitua a URI pela que você copiou no passo anterior.

O script vai exibir o progresso e, no final, mostrar a contagem de linhas migradas.
Se tudo correu bem, você verá algo como:
```
financial_reports: 246.000 rows migrados com sucesso.
```

> Para conferir sem migrar nada (teste):
> ```
> python scripts/migrate_to_supabase.py --dry-run
> ```

---

### Etapa 4 — Publicar o dashboard no Streamlit Community Cloud

1. Acesse https://share.streamlit.io e faça login com sua conta do GitHub
2. Clique em **"New app"**
3. Em **Repository**, selecione o repositório que você criou na Etapa 1
4. Em **Branch**, selecione `master`
5. Em **Main file path**, coloque: `dashboard/app.py`
6. Clique em **"Advanced settings"** e adicione o seguinte na caixa de **Secrets**:
   ```toml
   [database]
   url = "postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
   ```
   (a mesma URI da Etapa 2)
7. Clique em **"Deploy!"**

Aguarde o deploy — leva de 2 a 5 minutos. Quando terminar, você receberá um link público como:
```
https://seu-usuario-cvm-analytics-dashboard-app-XXXX.streamlit.app
```

Esse link funciona em qualquer dispositivo, 24 horas por dia, sem precisar do seu computador ligado.

---

### Etapa 5 — Atualizar os dados financeiros no banco da nuvem

Quando rodar o scraper para baixar novos relatórios da CVM, os dados precisam ir
para o Supabase (não mais para o SQLite local).

**Windows (CMD):**
```
set DATABASE_URL=postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
python scripts/atualizar_todos.py
```

**Windows (PowerShell):**
```
$env:DATABASE_URL="postgresql://postgres.XXXXXX:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python scripts/atualizar_todos.py
```

> Dica: você pode salvar a variável `DATABASE_URL` permanentemente no Windows para não precisar
> redigitar toda vez:
> 1. Pesquise **"Editar variáveis de ambiente do sistema"** no menu Iniciar
> 2. Clique em **"Variáveis de ambiente..."**
> 3. Em "Variáveis do usuário", clique em **"Nova..."**
> 4. Nome: `DATABASE_URL` / Valor: a URI completa do Supabase
> 5. Clique em OK — reinicie o terminal para o efeito entrar em vigor

---

### Resumo: o que fica onde

| O que é | Onde fica |
|---|---|
| Código do projeto | GitHub (privado, gratuito) |
| Banco de dados | Supabase (PostgreSQL, gratuito até 500 MB) |
| Dashboard publicado | Streamlit Community Cloud (gratuito) |
| Dados no seu PC | SQLite local — continua funcionando normalmente para desenvolvimento |

O dashboard local (no seu PC) continua funcionando normalmente com o SQLite.
Só a versão publicada na internet usa o Supabase.
