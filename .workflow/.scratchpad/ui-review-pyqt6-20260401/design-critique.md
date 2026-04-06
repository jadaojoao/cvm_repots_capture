## Design Critique: CVM Analytics Updater (PyQt6)

**File reviewed**: `cvm_pyqt_app.py`
**Date**: 2026-04-01
**Context**: App desktop de atualização de dados CVM. Usuário operador (não end-user). Fluxo: configurar → gerar lista inteligente → revisar tabela → iniciar batch → monitorar progresso.

---

### Overall Impression

O app é funcionalmente sólido — MVC bem separado, workers em threads, cancelamento seguro. O problema central é de **hierarquia visual**: tudo tem o mesmo peso. Título, grupo de saúde da base, tabela de empresas e log compartilham a mesma densidade visual, fazendo o olho não saber onde focar. O fluxo de 3 passos (Gerar → Revisar → Iniciar) não está visualmente comunicado.

---

### Usability

| Finding | Severity | Recommendation |
|---------|----------|----------------|
| Fluxo de 3 passos não sinalizado | 🔴 Critical | Numerar os grupos: "① Configuração", "② Empresas Selecionadas", "③ Execução". Botão "Gerar" habilita passo 2; "Iniciar" só fica ativo após passo 2 concluído — já funciona assim, mas o usuário não sabe. |
| Tabela sem feedback de seleção agregada | 🟡 Moderate | O `summaryLabel` mostra "Lista: X/Y selecionadas" mas fica no topo, longe da tabela. Mover para dentro do GroupBox "Empresas Selecionadas", acima da tabela. |
| "Gerar Lista Inteligente" e "Iniciar atualização" têm nomes muito longos | 🟡 Moderate | Renomear para "Gerar Lista" e "Iniciar" — economiza espaço e não perde clareza. |
| Cancelamento sem confirmação | 🟡 Moderate | Clicar "Cancelar" ativa `_cancel_requested` silenciosamente. Adicionar `QMessageBox.question()` "Cancelar o batch em andamento?" para evitar clique acidental. |
| Janela mínima 980×760 pode ser grande em laptops pequenos | 🟢 Minor | Reduzir para 900×680, deixar o log com `minimumHeight=120` em vez de 190. |

---

### Visual Hierarchy

- **O que chama atenção primeiro**: O título "CVM Analytics Updater" (22px bold) — correto.
- **Fluxo de leitura**: Título → Config → Saúde da Base → Tabela → Execução → Log → Botões. Razoável, mas "Saúde da Base" interrompe o fluxo de configuração→ação.
- **Ênfase errada**: `buildButton` (azul `#2563eb`) e `startButton` (verde `#16a34a`) têm destaque correto. Mas são do mesmo tamanho que `cancelButton` e `dashboardButton`, diluindo a hierarquia primário/secundário.
- **Log**: ocupa muito espaço vertical (min 190px) para informação secundária. Deveria ser colapsável ou menor por padrão.

**Sugestão de reordenação dos grupos:**
```
Título + Subtítulo
① Configuração Inteligente  [Preset / Anos / Qtd / Paralelismo / Gerar]
② Empresas Selecionadas     [Tabela com checkbox — stretch factor 1]
   └─ Summary label dentro deste grupo
③ Execução                  [StatusLabel + ProgressBar]
Log (colapsável)
Botões [Dashboard | · | Iniciar | Cancelar]
```
"Saúde da Base" poderia ir dentro de ① como seção recolhível, ou ser removida do fluxo principal (exibida apenas quando relevante).

---

### Consistency

| Element | Issue | Recommendation |
|---------|-------|----------------|
| Paleta desconectada do dashboard | App usa azuis Tailwind (`#2563eb`, `#93c5fd`) enquanto dashboard usa verde `#00BF7A` como accent | Não é obrigatório ser idêntico (apps diferentes), mas o verde poderia aparecer no `startButton` e progresso para criar reconhecimento de marca |
| `border-radius: 10px` nos GroupBoxes | Inconsistente com `border-radius: 8px` nos inputs e `7px` na progress bar | Escolher um valor e usar em tudo: `8px` |
| Títulos dos grupos sem acento (`Configuracao`, `Execucao`) | Textos em PT-BR sem acentuação parecem bug, não estilo | Corrigir: "Configuração Inteligente", "Execução" |
| `font-family: "Segoe UI"` hardcoded | Só funciona no Windows; no Linux/Mac cai para fonte padrão sem fallback | Adicionar fallback: `"Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif` |

---

### Accessibility

- **Contraste**: Texto `#e5e7eb` sobre `#0b1220` ≈ 14:1 — excelente.
- **Texto muted** (`#9ca3af` sobre `#0b1220`) ≈ 7:1 — passa WCAG AA.
- **Error label** (`#f87171` sobre `#0b1220`) ≈ 5.2:1 — passa WCAG AA para texto normal.
- **Focus state**: `QSpinBox:focus` e `QComboBox:focus` têm `border: 1px solid #60a5fa` — correto, mas `QTableWidget:focus` aplica a borda na tabela inteira, não na célula selecionada.
- **Teclado**: PyQt6 tem navegação por teclado nativa — OK.
- **Log auto-scroll**: `QPlainTextEdit` auto-scrolls ao append — correto para monitoramento.

---

### What Works Well

- MVC limpo: `MainWindow` só trata UI, `UpdateController` trata lógica, workers em threads separadas.
- `_cancel_requested` flag é thread-safe e não mata o processo abruptamente.
- `RankingWorker` emite `status_changed` para feedback em tempo real durante o ranking.
- `IntelligentSelectorService` com scoring composto (importância × 0.7 + staleness × 0.3) é uma feature sofisticada bem comunicada no subtítulo.
- Checkboxes na tabela permitem desselecionar empresas individualmente antes de iniciar — bom controle granular.

---

### Priority Recommendations

1. **Numerar os grupos e comunicar o fluxo de 3 passos** — adicionar "①", "②", "③" nos títulos dos GroupBoxes. Zero código de lógica, só mudança de texto.
2. **Corrigir acentuação nos títulos** — "Configuracao" → "Configuração", "Execucao" → "Execução". Passa credibilidade.
3. **Reduzir altura mínima do log** — de 190px para 120px. A tabela de empresas merece mais espaço vertical.
