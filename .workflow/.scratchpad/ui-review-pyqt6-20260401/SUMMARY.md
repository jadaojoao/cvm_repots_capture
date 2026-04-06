# UI Review Summary — CVM Analytics Updater (PyQt6)
**Date**: 2026-04-01
**File**: `cvm_pyqt_app.py`

## Relatórios

| Relatório | Arquivo |
|-----------|---------|
| Design Critique (UX/hierarquia/fluxo) | `design-critique.md` |
| UI Review (stylesheet compliance) | `ui-review.md` |
| Theme Suggestions (correções CSS + tokens) | `theme-suggestions.md` |

## Action Items por Prioridade

### Corrigir agora (1-liners de alto impacto)
1. **Acentuação** — "Configuracao" → "Configuração", "Saude da Base" → "Saúde da Base", "Execucao" → "Execução"
2. **Font-family fallback** — adicionar `"SF Pro Display", "Helvetica Neue", sans-serif` após `"Segoe UI"`
3. **Hover states** — adicionar `:hover` e `:pressed` para `#buildButton` e `#startButton`

### Corrigir em seguida
4. **Border-radius** — unificar para 8px (grupos estão em 10px, progress em 7px)
5. **Table selection** — adicionar `QTableWidget::item:selected { background-color: #1e3a5f; }`
6. **Fluxo de 3 passos** — numerar GroupBoxes: "① Configuração", "② Empresas Selecionadas", "③ Execução"

### Quando conveniente
7. **Rebaixar buildButton** para azul mais escuro (`#1e40af`) — verde como único accent primário
8. **Reduzir log** `minimumHeight` de 190px para 120px
9. **Confirmação no Cancel** — `QMessageBox.question()` antes de `_cancel_requested = True`

## Score: 4 FAIL, 6 WARN, 7 PASS
Nenhum problema crítico de segurança ou funcionalidade — todos os issues são visuais/UX.
