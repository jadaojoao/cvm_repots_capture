## UI Review: Update Center Dialog

**Skill**: `skills/ui-review/SKILL.md` (Swiss International Style compliance)
**Files reviewed**: `dashboard/update_center.py`, `dashboard/styles/style.css`
**Date**: 2026-04-01

---

## Step 1: Automated Checks

### Gradients
```
[FAIL] dashboard/styles/style.css — .velocity-bar-fill: linear-gradient(90deg, var(--accent-dk), var(--accent), var(--accent-lt))
```

### Blur / Backdrop-filter
```
[FAIL] dashboard/styles/style.css:142 — backdrop-filter: blur(12px) on .stDialog [data-testid="stModal"]
[FAIL] dashboard/styles/style.css:252 — backdrop-filter: blur(var(--glass-blur)) on panel components
```

### Border-radius (hardcoded, not using tokens)
```
[WARN] dashboard/styles/style.css — .velocity-bar-bg: border-radius: 4px (hardcoded, should be var(--r-xs))
[WARN] dashboard/styles/style.css — .velocity-bar-fill: border-radius: 4px (hardcoded, should be var(--r-xs))
```

### unsafe_allow_html (inline style injection)
```
[FAIL] dashboard/update_center.py:697 — unsafe_allow_html=True with inline style attributes:
         style="font-size:0.6rem; color:var(--text-muted)"     → use class .velocity-unit
         style="font-size: 0.72rem; color: var(--text-secondary)" → use class .velocity-company-label
```

---

## Step 2: Manual Review

### Colors
- [PASS] Background: uses `var(--bg)`, `var(--bg-card)` — correct
- [PASS] Text primary: `var(--text-primary)` used for main content
- [FAIL] `--text-muted #4a5068` used for readable secondary text — contrast 3.8:1 FAIL WCAG AA
- [WARN] Status colors not defined in design system: Never/Error states use ad-hoc colors

### Typography
- [PASS] `--font-headline 'Nunito Sans'` applied to dialog title via CSS
- [PASS] `--font-mono 'JetBrains Mono'` used in `.velocity-value` (COMP/MIN label)
- [WARN] Section heading "Last Run Results" uses `st.markdown("### ...")` — should use `st.subheader()` for consistency

### Borders & Shadows
- [PASS] `.velocity-container` uses `var(--border)` for border
- [PASS] Card components use `var(--shadow-xs)` or `var(--shadow-sm)` tokens
- [WARN] `.velocity-bar-bg` uses hardcoded `border-radius: 4px` instead of `var(--r-xs)`

### Animations
- [FAIL] `.velocity-bar-fill` shimmer animation has no `@media (prefers-reduced-motion: reduce)` guard
- [FAIL] `.pulse-active` pulse animation has no `@media (prefers-reduced-motion: reduce)` guard

### Components
- [FAIL] `action_col1.button("Run Financial Statements Update")` — missing `type="primary"`, visually equal to Close
- [PASS] `st.selectbox()` filters use Streamlit default styling (consistent)
- [PASS] `st.metric()` cards are correctly structured
- [PASS] SQL queries in `update_center.py` use parameterized queries (`:param` pattern) — no injection risk

---

## Step 3: Report

```
[FAIL] style.css — .velocity-bar-fill uses linear-gradient (anti-pattern: gradients not in design system)
[FAIL] style.css:142 — backdrop-filter: blur(12px) on dialog overlay
[FAIL] style.css:252 — backdrop-filter: blur(var(--glass-blur)) on panel
[FAIL] update_center.py:688 — inline style="font-size:0.6rem; color:var(--text-muted)" bypasses CSS classes
[FAIL] update_center.py:693 — inline style="font-size: 0.72rem; color:var(--text-secondary)" bypasses CSS classes
[FAIL] update_center.py:659 — Run button missing type="primary" (no primary/secondary distinction)
[FAIL] style.css — shimmer animation missing @media (prefers-reduced-motion: reduce) guard
[FAIL] style.css — .pulse-active animation missing @media (prefers-reduced-motion: reduce) guard

[WARN] style.css — .velocity-bar-bg and .velocity-bar-fill use hardcoded border-radius: 4px (use var(--r-xs))
[WARN] update_center.py — --text-muted contrast 3.8:1 FAIL WCAG AA for readable text
[WARN] update_center.py — language mixing (EN dialog title, EN/PT content)
[WARN] update_center.py — "Last Run Results" uses st.markdown("### ...") inconsistently
[WARN] style.css — no status color tokens defined (Never/Today/Stale/Error states need palette)

[PASS] Color tokens (--bg, --bg-card, --accent) used correctly throughout
[PASS] Typography tokens (--font-headline, --font-mono) applied via CSS
[PASS] Border tokens (var(--border)) used on velocity container
[PASS] Shadow tokens (var(--shadow-*)) used for card elevation
[PASS] SQL queries are parameterized (no injection risk)
```

**Summary**: 8 `[FAIL]`, 5 `[WARN]`, 5 `[PASS]`

**Most critical**: The `unsafe_allow_html` inline styles (FAIL 4+5) and the missing `prefers-reduced-motion` guards (FAIL 7+8) are the highest-priority fixes. Both are 1-line changes.
