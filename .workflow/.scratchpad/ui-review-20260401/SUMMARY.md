# UI Review Summary — Update Center Dialog
**Date**: 2026-04-01
**Files**: `dashboard/update_center.py`, `dashboard/styles/style.css`

---

## Quick Reference

| Report | File |
|--------|------|
| Design Critique (UX/hierarchy/accessibility) | `design-critique.md` |
| UI Review (design system compliance) | `ui-review.md` |
| Theme Suggestions (CSS fixes + tokens) | `theme-suggestions.md` |

---

## Action Items by Priority

### Fix Now (Critical/High)
1. **Reorder dialog layout** — Move preview dataframe above action buttons (`update_center.py:647-667`)
2. **Add confirmation before batch run** — Add `type="primary"` to Run button + confirmation step

### Fix Soon (Medium — 1-line changes)
3. **`prefers-reduced-motion`** — Add to `style.css` for `.velocity-bar-fill::after` and `.pulse-active`
4. **Inline styles → CSS classes** — Replace `unsafe_allow_html` inline `style=` attributes with `.velocity-unit` and `.velocity-company-label` classes
5. **Contrast** — Replace `--text-muted` with `--text-secondary` for readable secondary text (3.8:1 → 5.7:1)

### Fix When Convenient (Low)
6. **Hardcoded border-radius** — Change `4px` to `var(--r-xs)` in velocity bar CSS
7. **Language consistency** — Pick one name for the dialog (EN or PT)
8. **Run button** — Add `type="primary"` (even without confirmation flow, this is a one-liner)

### Token Additions (Theme)
9. **Status palette** — Add `--status-never/today/stale/error` tokens + optional bg tints
10. **Progress bar** — Replace `linear-gradient` with solid `var(--accent)` + `::after` sweep
