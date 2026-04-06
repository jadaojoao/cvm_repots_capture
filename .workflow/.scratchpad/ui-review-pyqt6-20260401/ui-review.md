## UI Review: CVM Analytics Updater (PyQt6)

**Skill**: `skills/ui-review/SKILL.md` (Swiss International Style — adaptado para Qt stylesheet)
**File reviewed**: `cvm_pyqt_app.py` — `APP_STYLESHEET` constant
**Date**: 2026-04-01

---

## Step 1: Automated Checks

### Gradients
```
[PASS] APP_STYLESHEET — nenhum gradient encontrado
```

### Blur / Backdrop-filter
```
[PASS] APP_STYLESHEET — nenhum blur encontrado (Qt não suporta backdrop-filter nativamente)
```

### Border-radius (inconsistências)
```
[WARN] APP_STYLESHEET — QGroupBox: border-radius: 10px
[WARN] APP_STYLESHEET — QSpinBox/QComboBox/QPlainTextEdit/QTableWidget: border-radius: 8px
[WARN] APP_STYLESHEET — QPushButton: border-radius: 8px
[WARN] APP_STYLESHEET — QProgressBar: border-radius: 7px / chunk: border-radius: 6px
       → 4 valores diferentes (10, 8, 7, 6px) sem padrão consistente
```

### Inline styles fora do stylesheet
```
[PASS] Nenhum setStyleSheet() inline em widgets individuais encontrado — tudo centralizado em APP_STYLESHEET
```

---

## Step 2: Manual Review

### Colors

- [PASS] Background: `#0b1220` — escuro, consistente
- [PASS] Texto primário: `#e5e7eb` — contraste alto (~14:1)
- [WARN] Accent principal: `#2563eb` (azul) para buildButton, `#16a34a` (verde) para startButton — dois accents primários sem hierarquia clara. Qual é o "accent" do app?
- [WARN] `#93c5fd` (grupo titles + summary), `#60a5fa` (focus), `#bfdbfe` (header) — 3 tons de azul diferentes para elementos relacionados
- [PASS] Error: `#f87171` — vermelho legível
- [PASS] Status/success: `#a7f3d0` (status label), `#22c55e` (progress chunk)

### Typography

- [FAIL] `font-family: "Segoe UI"` sem fallback — falha silenciosamente em Linux/Mac
- [PASS] Tamanhos hierárquicos: título 22px, base 13px — diferença adequada
- [WARN] `QGroupBox::title` usa `color: #93c5fd; font-weight: 600` mas não define font-size explícito (herda 13px do QWidget base) — pode ficar pequeno demais
- [PASS] Botões com `font-weight: 600` — correto para elementos de ação

### Borders & Shadows

- [FAIL] Nenhum shadow em nenhum widget — PyQt6 suporta `box-shadow` via stylesheet apenas no Windows com algumas limitações, mas `QGraphicsDropShadowEffect` poderia ser usado para cards/grupos
- [PASS] Borders usam tokens consistentes: `#1f2937` (grupos) e `#334155` (inputs/botões secondary)
- [WARN] `border-radius` inconsistente (ver Step 1 acima): 10px / 8px / 7px / 6px

### Components

- [FAIL] `QPushButton` genérico tem `border-radius: 8px` e `padding: 8px 12px` mas **sem border definido** para os estados `normal` — botões secondary (`cancelButton`, `dashboardButton`) precisam de `border: 1px solid #334155` no estado base (já tem no `#cancelButton` e `#dashboardButton` mas não no seletor genérico `QPushButton`)
- [PASS] Estados `:disabled` definidos para todos os botões nomeados
- [WARN] `QPushButton#buildButton` e `QPushButton#startButton` não têm `:hover` state — sem feedback visual ao passar o mouse
- [WARN] `QTableWidget` sem definição de `selection-background-color` — usa cor padrão do sistema, que pode não ter contraste adequado no tema dark
- [PASS] `QHeaderView::section` estilizado corretamente

### Acentuação / Texto

- [FAIL] Títulos dos GroupBoxes sem acentuação PT-BR: "Configuracao Inteligente", "Saude da Base", "Execucao" — parece bug
- [WARN] Subtítulo usa inglês misturado: "importancia de mercado" (PT) mas o app tem labels em PT e EN misturados ("Abrir Dashboard", "Score", "Gap (anos)")

---

## Step 3: Report

```
[FAIL] APP_STYLESHEET — font-family: "Segoe UI" sem fallback (falha em Linux/Mac)
[FAIL] APP_STYLESHEET — QPushButton genérico sem border no estado normal (cancela herança de border nos botões secondary)
[FAIL] cvm_pyqt_app.py — GroupBox titles sem acentuação: "Configuracao", "Saude da Base", "Execucao"
[FAIL] APP_STYLESHEET — buildButton e startButton sem :hover state (sem feedback visual)

[WARN] APP_STYLESHEET — border-radius inconsistente: 10px (grupos) / 8px (inputs/botões) / 7px (progress) / 6px (chunk)
[WARN] APP_STYLESHEET — 2 accent colors primários (azul buildButton + verde startButton) sem hierarquia definida
[WARN] APP_STYLESHEET — 3 tons de azul para elementos relacionados (#93c5fd, #60a5fa, #bfdbfe)
[WARN] APP_STYLESHEET — QGroupBox::title sem font-size explícito (herda 13px base)
[WARN] APP_STYLESHEET — QTableWidget sem selection-background-color no tema dark
[WARN] cvm_pyqt_app.py — linguagem mista PT/EN em labels da tabela e botões

[PASS] Nenhum gradient no stylesheet
[PASS] Nenhum blur (incompatível com Qt de qualquer forma)
[PASS] Stylesheet centralizado em APP_STYLESHEET — sem inline setStyleSheet() espalhados
[PASS] Estados :disabled definidos para todos os botões nomeados
[PASS] Contraste de texto: #e5e7eb/#9ca3af sobre #0b1220 passa WCAG AA
[PASS] QHeaderView::section estilizado corretamente
[PASS] Error label com cor semântica correta (#f87171)
```

**Resumo**: 4 `[FAIL]`, 6 `[WARN]`, 7 `[PASS]`

**Mais críticos**: font-family sem fallback (FAIL 1) e ausência de `:hover` nos botões primários (FAIL 4) são os mais impactantes na experiência. A falta de acentuação (FAIL 3) impacta credibilidade.
