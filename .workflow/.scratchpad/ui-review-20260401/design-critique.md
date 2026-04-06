## Design Critique: Update Center Dialog

**File reviewed**: `dashboard/update_center.py` (722 lines)
**Date**: 2026-04-01
**Context**: Modal dialog (`@st.dialog`) for triggering financial statement batch updates. Used by operators, not end-users.

---

### Overall Impression

The dialog is functional and information-dense, but suffers from two critical UX gaps: the preview table is positioned below the fold of the dialog viewport, and there is no confirmation step before launching a potentially 90-minute batch operation. The animation and status system are well-intentioned but need contract improvements and reduced-motion support.

---

### Usability

| Finding | Severity | Recommendation |
|---------|----------|----------------|
| Preview table below the fold | 🔴 Critical | Reorder layout: filters → summary metrics → **preview** → action buttons. Preview must be visible before clicking Run. |
| No confirmation before batch run | 🟡 Moderate | Add a second click or `st.warning` confirmation step: "This will process N companies. Continue?" — `subprocess.run` per company cannot be cancelled. |
| Close button during active run silently abandons subprocesses | 🟡 Moderate | On dialog close while `st.session_state.update_running` is True, show a warning: "Update in progress. Closing will not stop running processes." |
| Filter state is ephemeral (resets on rerun) | 🟡 Moderate | Persist filter values in `st.session_state` so filters survive Streamlit reruns during batch execution. |
| `Run` button has no visual primary emphasis | 🟢 Minor | Add `type="primary"` to `st.button("Run Financial Statements Update")`. |
| "Never updated" count is the most critical metric but is first, not last | 🟢 Minor | Reorder status cards: Updated Today → Before Today → Error → Never. Users care most about errors and gaps. |

---

### Visual Hierarchy

- **What draws the eye first**: The 4 status metric cards (large numbers). This is correct — gives instant database health status.
- **Reading flow**: Cards → Filters → Buttons → Preview table (hidden) → Progress bar. The preview table being after the buttons breaks the expected "configure → review → act" flow.
- **Emphasis**: The `Run` button (the most consequential action) is visually equal to `Close`. Primary/secondary distinction is missing.
- **Progress bar**: The velocity container during execution is the most visually complex element (gradient, shimmer, pulse). It communicates execution state well, but the inline styles break design system cohesion.

---

### Consistency

| Element | Issue | Recommendation |
|---------|-------|----------------|
| Language mixing | Dialog title "Update Center", subheading "Financial Statement Refresh", button "Run Financial Statements Update" — 3 different names for the same concept | Pick one: "Atualizar Demonstrações" (PT) or "Refresh Statements" (EN) |
| Inline styles in progress bar | `style="font-size:0.6rem; color:var(--text-muted)"` — bypasses CSS design system | Extract to CSS classes `.velocity-unit` and `.velocity-company-label` in `style.css` |
| `--text-secondary` vs `--text-muted` | Both used for secondary text in the same component | Use `--text-secondary` for informational text, `--text-muted` for disabled/inactive only |
| Dialog heading level | "Update Center" renders as dialog title (h1-equivalent), but "Last Run" uses `st.markdown("### Last Run Results")` — inconsistent heading hierarchy | Use `st.subheader()` for section headings consistently |

---

### Accessibility

- **Color contrast**: `--text-muted #4a5068` on `--bg-card #13141d` = **3.8:1** — FAIL WCAG AA (requires 4.5:1 for normal text). Use `--text-secondary #9aa0b8` instead for readable secondary text.
- **Animation**: Shimmer (`.velocity-bar-fill`) and pulse (`.pulse-active`) have no `@media (prefers-reduced-motion: reduce)` guard. Users with vestibular disorders will see constant motion.
- **Touch targets**: Action buttons appear correctly sized via Streamlit defaults.
- **Screen readers**: `st.metric()` cards announce value + label correctly. `unsafe_allow_html` progress bar content is not announced by screen readers (no ARIA live region).

---

### What Works Well

- The 4-metric status card pattern gives instant operational awareness.
- `@st.cache_data(ttl=30)` on `load_update_center_data()` correctly prevents stale data without hammering the DB.
- Velocity calculation (companies/minute) during batch is a thoughtful operator UX feature.
- `st.expander("Advanced")` for custom year range correctly hides complexity.
- The batch architecture (subprocess per company with progress tracking via `session_state`) is resilient — one company failure doesn't crash the batch.

---

### Priority Recommendations

1. **Move preview dataframe above action buttons** — The current order (filter → buttons → preview) asks users to act before seeing what they're acting on. Reorder to: status cards → filters → preview → buttons.
2. **Add `type="primary"` to Run button and a confirmation step** — `action_col1.button("Run...", type="primary")` + a `st.warning` + second confirmation button before triggering the batch.
3. **Fix accessibility**: Replace `--text-muted` with `--text-secondary` for readable content, and add `prefers-reduced-motion` to the shimmer/pulse CSS.
