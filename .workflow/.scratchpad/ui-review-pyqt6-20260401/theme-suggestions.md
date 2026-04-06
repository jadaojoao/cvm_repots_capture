## Theme Suggestions: CVM Analytics Updater (PyQt6)

**Date**: 2026-04-01

---

## 1. Correções Imediatas ao APP_STYLESHEET

### Font-family com fallback
```python
# ANTES:
font-family: "Segoe UI";

# DEPOIS:
font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
```

### Border-radius unificado (escolher 8px como padrão)
```css
/* ANTES: 10px grupos, 8px inputs/botões, 7px progress, 6px chunk */

/* DEPOIS — usar 8px em tudo: */
QGroupBox {
    border-radius: 8px;   /* era 10px */
}
QProgressBar {
    border-radius: 8px;   /* era 7px */
}
QProgressBar::chunk {
    border-radius: 7px;   /* era 6px — manter 1px menor que o container */
}
/* QSpinBox/QComboBox/QPushButton já estão em 8px — sem mudança */
```

### Hover states para botões primários
```css
QPushButton#buildButton:hover {
    background-color: #1d4ed8;
}
QPushButton#buildButton:pressed {
    background-color: #1e40af;
}
QPushButton#startButton:hover {
    background-color: #15803d;
}
QPushButton#startButton:pressed {
    background-color: #166534;
}
```

### QTableWidget selection no tema dark
```css
QTableWidget::item:selected {
    background-color: #1e3a5f;
    color: #e5e7eb;
}
QTableWidget::item:hover {
    background-color: #1f2937;
}
```

---

## 2. Paleta de Accent Única

O app usa azul para Build e verde para Start — dois accents primários que competem. Sugestão: manter verde como accent único (alinhado ao dashboard) e rebaixar Build para azul secundário:

```css
/* Accent principal: verde (ação final — Iniciar) */
QPushButton#startButton {
    background-color: #16a34a;   /* mantém */
    color: #ffffff;
}
QPushButton#startButton:hover {
    background-color: #15803d;
}

/* Ação preparatória: azul secundário (Gerar Lista) */
QPushButton#buildButton {
    background-color: #1e40af;   /* azul mais escuro = menos destaque que startButton */
    color: #ffffff;
}
QPushButton#buildButton:hover {
    background-color: #1d4ed8;
}

/* Títulos de grupos: usar verde muted em vez de azul */
QGroupBox::title {
    color: #86efac;   /* green-300, mais alinhado ao accent verde */
}

/* Summary label: manter azul como informacional */
/* QLabel#summaryLabel: #93c5fd — OK, cor informacional ≠ accent de ação */
```

---

## 3. Tokens CSS Propostos

Organizar como variáveis comentadas no topo do `APP_STYLESHEET` (Qt não suporta CSS variables, mas documentar os valores usados evita inconsistências):

```python
APP_STYLESHEET = """
/* === Design Tokens (reference) ===
   --bg:           #0b1220
   --bg-input:     #111827
   --bg-header:    #0f172a
   --border:       #1f2937
   --border-input: #334155
   --border-focus: #60a5fa
   --text:         #e5e7eb
   --text-muted:   #9ca3af
   --text-disable: #6b7280
   --accent:       #16a34a  (verde — ação primária)
   --accent-2:     #1e40af  (azul — ação preparatória)
   --accent-info:  #93c5fd  (azul claro — labels informativos)
   --success:      #a7f3d0  (verde claro — status OK)
   --error:        #f87171  (vermelho — validação)
   --radius:       8px
=================================== */
```

---

## 4. Correções de Texto (sem mudança de código de lógica)

```python
# Em _build_ui(), substituir strings dos GroupBox titles:
"Configuracao Inteligente"  →  "Configuração Inteligente"
"Saude da Base"             →  "Saúde da Base"
"Execucao"                  →  "Execução"

# Colunas da tabela (se definidas como lista):
"Gap (anos)"    →  manter (já está em PT)
"Score"         →  pode virar "Pontuação" ou manter Score (termo técnico aceitável)
"Abrir Dashboard" →  manter (hibridismo comum em PT-BR técnico)
```

---

## 5. Resumo das Mudanças por Prioridade

| Prioridade | Mudança | Onde |
|-----------|---------|------|
| Alta | Adicionar fallback ao font-family | `APP_STYLESHEET` — 1 linha |
| Alta | Corrigir acentuação nos títulos | `_build_ui()` — 3 strings |
| Alta | Adicionar `:hover` e `:pressed` nos botões primários | `APP_STYLESHEET` — 8 linhas |
| Média | Unificar border-radius para 8px | `APP_STYLESHEET` — 3 valores |
| Média | Adicionar `QTableWidget::item:selected` dark | `APP_STYLESHEET` — 4 linhas |
| Baixa | Rebaixar buildButton para azul mais escuro | `APP_STYLESHEET` — 2 valores |
| Baixa | Documentar tokens como comentário | `APP_STYLESHEET` — bloco de comentário |
