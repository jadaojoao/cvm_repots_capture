# Code Review Report — cvm_pyqt_app.py

## Visão Geral

| Item | Valor |
|------|-------|
| Arquivo | `cvm_pyqt_app.py` |
| Linhas | ~2538 |
| Linguagem | Python 3.10+ |
| Framework | PyQt6 + SQLite + yfinance |
| Foco | Bugs que impedem atualização eficiente da base |
| Data | 2026-04-02 |

## Resumo de Problemas

| Severidade | Qtd |
|------------|-----|
| 🔴 Critical | 1 |
| 🟠 High | 6 |
| 🟡 Medium | 5 |
| 🔵 Low | 1 |
| **Total** | **13** |

| Dimensão | Qtd |
|----------|-----|
| Correctness | 4 |
| Performance | 3 |
| Architecture | 5 |
| Testing | 1 |

---

## Áreas de Alto Risco

| Área | Motivo | Prioridade |
|------|--------|------------|
| `IntelligentSelectorService` | 5 métodos duplicados, 2 versões de `build_base_health_snapshot` — editar a versão errada não tem efeito | P0 |
| `UpdateController._refresh_base_health` | Chamada síncrona (HTTP + I/O) na thread principal na inicialização | P0 |
| `build_base_health_snapshot` (linha 1226) | Loop O(n×m) sobre raw_presence para cada empresa | P1 |

---

## Correctness

---

### 🔴 [CORR-001] duplicate-method — `_load_refresh_status_map` definido duas vezes

- **Severidade**: Critical
- **Arquivo**: `cvm_pyqt_app.py:309` (morto) e `:816` (vivo)
- **Descrição**: O método `_load_refresh_status_map` está definido duas vezes na classe `IntelligentSelectorService`. Python usa a **segunda definição** (linha 816), descartando silenciosamente a primeira (linha 309). A versão morta consulta 3 colunas adicionais (`last_start_year`, `last_end_year`, `last_rows_inserted`); a viva não. Qualquer correção aplicada à versão de linha 309 tem efeito zero em runtime.

**Código (versão morta — linha 309):**
```python
def _load_refresh_status_map(self) -> dict[int, dict[str, Any]]:
    query = """
        SELECT cd_cvm, company_name, last_attempt_at, last_success_at,
               last_status, last_error, last_start_year, last_end_year, last_rows_inserted
        FROM company_refresh_status
    """
```

**Código (versão viva — linha 816):**
```python
def _load_refresh_status_map(self) -> dict[int, dict[str, Any]]:
    query = """
        SELECT cd_cvm, company_name, last_attempt_at, last_success_at,
               last_status, last_error, last_rows_inserted   # faltam last_start_year e last_end_year
        FROM company_refresh_status
    """
```

**Recomendação**: Deletar a definição das linhas 309–339 (a primeira). A versão viva (816) está funcional — os campos faltantes não são usados pelos callers atuais.

---

### 🟠 [CORR-002] duplicate-method — `build_base_health_snapshot` definido duas vezes

- **Severidade**: High
- **Arquivo**: `cvm_pyqt_app.py:557` (morto) e `:1145` (vivo)
- **Descrição**: Mesmo padrão do CORR-001. A primeira definição (linha 557) é uma implementação mais antiga com lógica diferente (`_load_active_cvm_universe`, `_build_raw_availability_index`, `_throughput_per_company_year_hour`). A segunda (linha 1145) é a versão refatorada em uso. As 143 linhas da versão morta (557–699) são código executável que nunca roda mas confunde manutenção.

**Recomendação**: Deletar o bloco inteiro das linhas 557–699.

---

### 🟠 [CORR-003] error-handling — `fetch_company_list()` falha silenciosamente em `scraper.run()`

- **Severidade**: High
- **Arquivo**: `src/scraper.py:427`, `cvm_pyqt_app.py:1797`
- **Descrição**: `scraper.run()` chama `self.fetch_company_list()` para popular `self.companies_map`. Se a rede estiver indisponível, `fetch_company_list` imprime um aviso mas retorna `None` sem lançar exceção. Se `self.companies_map` não foi inicializado no `__init__` (verificar), `resolve_company_codes` lança `AttributeError`. Se foi inicializado vazio, todas as empresas são resolvidas como `"CVM_12345"` e ainda assim processadas — o usuário não sabe que os nomes saíram errados.

**Recomendação**: Em `UpdateWorker.run()`, verificar se `scraper.companies_map` está populado após `fetch_company_list()`. Se vazio e companies são códigos numéricos, emitir aviso no log mas continuar (já funciona via ramo `if str(name).isdigit()`). Pelo menos emitir `self.log_message.emit("Aviso: lista CVM não disponível. Usando fallback por código.")`.

---

### 🟠 [CORR-004] logic-error — Pré-download de TODOS os anos antes de processar qualquer empresa

- **Severidade**: High
- **Arquivo**: `src/scraper.py:429–431`
- **Descrição**: `scraper.run()` baixa todos os ZIPs DFP+ITR para todo o range de anos **antes** de iniciar o processamento das empresas. Com 3 anos = 6 downloads sequenciais. Isso não é um bug de crash, mas é ineficiência direta: progresso da barra fica em 0% por vários minutos enquanto os downloads ocorrem, sem feedback visual para o usuário no PyQt6 (o `progress_callback` só é chamado durante o loop de empresas, não durante os downloads).

**Recomendação (no PyQt6)**: Em `UpdateWorker.run()`, adicionar `self.status_changed.emit("Baixando dados CVM para anos selecionados...")` antes de `scraper.run()` para dar feedback. Longo prazo: mover os downloads para dentro do loop de empresa, ou emitir sinais do scraper durante download.

---

## Performance

---

### 🔴 [PERF-001] blocking-io — `_refresh_base_health` chamado síncronamente na thread principal

- **Severidade**: Critical (UI freeze)
- **Arquivo**: `cvm_pyqt_app.py:2286` (`UpdateController.__init__`), `2403` (`on_years_changed`)
- **Descrição**: `_refresh_base_health` chama `self.service.build_base_health_snapshot(...)` **na thread principal (UI thread)**. Internamente, `build_base_health_snapshot` chama `_load_active_universe` que:
  - Verifica cache JSON
  - Se cache expirado (TTL 24h) ou ausente → faz HTTP GET em `https://dados.cvm.gov.br/...` com `timeout=30`
  - Escaneia `data/input/processed/` lendo colunas `CD_CVM` de dezenas de CSVs

Resultado: **UI congela por até 30 segundos** ao abrir o app (se cache expirado), e congela novamente toda vez que o usuário muda os spinboxes de ano (via `on_years_changed → _refresh_base_health`).

Esse é o bug mais impactante para a experiência de atualização — o app parece travado.

**Recomendação**: Criar um `HealthWorker(QThread)` semelhante ao `RankingWorker` para executar `build_base_health_snapshot` em background. Emitir sinal `health_ready(dict)` ao completar. Conectar a `on_years_changed` com debounce (300ms).

**Esboço:**
```python
class HealthWorker(QThread):
    health_ready = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, service, start_year, end_year, force_refresh, parent=None):
        super().__init__(parent)
        self.service = service
        self.start_year = start_year
        self.end_year = end_year
        self.force_refresh = force_refresh

    def run(self):
        try:
            snapshot = self.service.build_base_health_snapshot(
                self.start_year, self.end_year, self.force_refresh
            )
            self.health_ready.emit(snapshot)
        except Exception:
            self.failed.emit(traceback.format_exc())
```

---

### 🟠 [PERF-002] inefficient-algorithm — Loop O(n×m) em `build_base_health_snapshot`

- **Severidade**: High
- **Arquivo**: `cvm_pyqt_app.py:1226`
- **Descrição**: Para cada empresa (449 empresas), o código itera sobre **todos** os itens de `raw_presence` para encontrar os anos dessa empresa:

```python
# Linha 1226 — dentro do loop `for item in active_universe` (449 iterações)
raw_years = [
    year
    for (raw_cd, year), stmts in raw_presence.items()
    if raw_cd == cd and stmts   # <- varre todo raw_presence a cada empresa
]
```

Se `raw_presence` tem 2000 entradas e há 449 empresas = ~900,000 comparações por chamada.

**Recomendação**: Pré-calcular um índice invertido antes do loop:
```python
# Antes do loop de empresas
raw_years_by_cd: dict[int, list[int]] = defaultdict(list)
for (raw_cd, year), stmts in raw_presence.items():
    if stmts:
        raw_years_by_cd[raw_cd].append(year)

# Dentro do loop
raw_years = raw_years_by_cd.get(cd, [])
```
Reduz de O(n×m) para O(n+m).

---

### 🟡 [PERF-003] blocking-io — `_scan_processed_statement_presence` sem cache

- **Severidade**: Medium
- **Arquivo**: `cvm_pyqt_app.py:1025`
- **Descrição**: `_scan_processed_statement_presence` lê a coluna `CD_CVM` de cada CSV em `data/input/processed/` toda vez que `build_base_health_snapshot` é invocado. Com dezenas de arquivos CSV (vários anos × 5 tipos de statement), isso pode demorar segundos. A invalidação de cache em `build_base_health_snapshot` usa `processed_signature` (contagem + mtime mais recente), então o resultado final do snapshot é cacheado — mas se o cache for invalidado, o scan completo re-ocorre.

**Recomendação**: O comportamento atual está aceitável desde que o cache de snapshot funcione. O problema real é PERF-001 (chamada síncrona). Se PERF-001 for resolvido (thread), PERF-003 deixa de bloquear a UI.

---

## Architecture

---

### 🟠 [ARCH-001] god-class — `IntelligentSelectorService` tem 5 métodos mortos

- **Severidade**: High
- **Arquivo**: `cvm_pyqt_app.py`
- **Descrição**: Além dos duplicados já listados, os seguintes métodos existem **apenas** para servir a versão morta de `build_base_health_snapshot` (linhas 557–699) e nunca são chamados pelo código vivo:

| Método morto | Linha | Substituto vivo |
|---|---|---|
| `_load_active_cvm_universe` | 346 | `_load_active_universe` (904) |
| `_build_raw_availability_index` | 471 | `_scan_processed_statement_presence` (1025) |
| `_throughput_per_company_year_hour` | 503 | `_estimate_throughput_per_hour` (1085) |
| `_load_package_coverage` | 422 | `_load_statement_presence` (968) |

Total de linhas mortas na classe: ~350 linhas.

**Recomendação**: Remover todos os métodos mortos após confirmar que os testes passam sem eles. Isso tornará a classe ~30% menor e eliminará a confusão sobre qual versão está ativa.

---

### 🟡 [ARCH-002] srp-violation — `IntelligentSelectorService` mistura serviço de ranking, health snapshot e cache de mercado

- **Severidade**: Medium
- **Arquivo**: `cvm_pyqt_app.py:247`
- **Descrição**: A classe tem 3 responsabilidades distintas: (1) ranking de empresas para atualização, (2) snapshot de saúde da base, (3) gerenciamento de cache yfinance/mercado. Para um arquivo único isso é tolerável, mas dificulta testes unitários.
- **Recomendação**: Não é urgente. Se o arquivo crescer, separar em `RankingService`, `HealthService`, `MarketCacheService`.

---

### 🟡 [ARCH-003] coupling — `UpdateWorker` usa `sqlite3` direto para `_sync_refresh_status`

- **Severidade**: Medium
- **Arquivo**: `cvm_pyqt_app.py:1688`
- **Descrição**: `UpdateWorker` abre conexão SQLite diretamente para sincronizar `company_refresh_status`. O scraper (`CVMScraper`) já usa `CVMDatabase` (SQLAlchemy). Duas abstrações de acesso a dados para o mesmo banco.
- **Recomendação**: Mover `_sync_refresh_status` para `CVMDatabase` ou para `IntelligentSelectorService`.

---

### 🟡 [ARCH-004] layer-violation — `MainWindow` referencia `_controller` via atributo público

- **Severidade**: Medium
- **Arquivo**: `cvm_pyqt_app.py:2531`
- **Descrição**:
```python
window._controller = controller  # keep reference
```
O controller é injetado no view via atributo privado por convenção mas público de fato. Isso quebra o MVC — a view não deveria saber sobre o controller.
- **Recomendação**: Passar `parent` adequado no QObject ou manter referência no escopo de `main()` com variável local (`_controller = controller`). O comentário "keep reference" indica que é apenas para evitar garbage collection — solução adequada: `app._controller = controller` (referência no QApplication, que tem lifetime igual ao processo).

---

### 🔵 [ARCH-005] magic-number — Constantes hardcoded na lógica de scoring

- **Severidade**: Low
- **Arquivo**: `cvm_pyqt_app.py:1451`
- **Descrição**: `cooldown_penalty = 0.35` está hardcoded no cálculo de score sem ser uma constante de classe. As outras constantes (`IMPORTANCE_WEIGHT`, `STALENESS_WEIGHT`, etc.) são atributos de classe — `cooldown_penalty` deveria ser também.
- **Recomendação**: Adicionar `COOLDOWN_PENALTY = 0.35` aos atributos de classe de `IntelligentSelectorService`.

---

## Testing

---

### 🟡 [TEST-001] coverage — Testes podem cobrir código morto

- **Severidade**: Medium
- **Arquivo**: `tests/test_cvm_pyqt_app.py`
- **Descrição**: `test_cvm_pyqt_app.py` testa `IntelligentSelectorService`. Se algum teste instancia o serviço e chama `build_base_health_snapshot` com mocks que cobrem a primeira versão (linha 557, que chama `_load_active_cvm_universe`), esses testes testam código morto. A cobertura parece maior do que é.
- **Recomendação**: Após remover os métodos mortos, re-rodar os testes para garantir que cobrem apenas o código vivo.

---

## Recomendações por Prioridade

### Deve corrigir agora (blockers de eficiência)

1. **[PERF-001]** — Mover `_refresh_base_health` para thread (`HealthWorker`). Este é o bug mais impactante: UI freeze na inicialização e ao mudar anos. Sem isso, o app parece travado para o usuário.

2. **[CORR-001] + [CORR-002] + [ARCH-001]** — Remover todos os métodos duplicados/mortos de `IntelligentSelectorService` (≈350 linhas). Risco de editar a versão errada e achar que o bug está corrigido.

### Deve corrigir em seguida

3. **[PERF-002]** — Pré-indexar `raw_presence` antes do loop (2 linhas de mudança). Melhoria de performance proporcional ao número de empresas.

4. **[CORR-003]** — Emitir log de aviso quando `fetch_company_list()` falha.

### Quando conveniente

5. **[ARCH-003]** — Mover `_sync_refresh_status` para `CVMDatabase`.
6. **[ARCH-004]** — Mudar `window._controller` para `app._controller`.
7. **[ARCH-005]** — Extrair `COOLDOWN_PENALTY = 0.35` como constante de classe.

---

*Relatório gerado em: 2026-04-02*
