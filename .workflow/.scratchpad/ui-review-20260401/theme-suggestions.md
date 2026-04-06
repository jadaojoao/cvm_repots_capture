## Theme Suggestions: Update Center Dialog

**Context**: Dark SaaS financial dashboard, design system tokens defined in `dashboard/styles/style.css`
**Date**: 2026-04-01

---

## 1. Status Color Palette (4 states)

Add these tokens to the `:root` block in `style.css`:

```css
/* Status palette — Update Center metric cards */
--status-never:       #4a5068;   /* Neutral grey — matches --text-muted, low urgency */
--status-never-bg:    #1a1b2e;   /* --bg-elevated */
--status-today:       #00BF7A;   /* --accent green — success/current */
--status-today-bg:    #0a2018;   /* dark green tint */
--status-stale:       #F59E0B;   /* Amber — warning, data aging */
--status-stale-bg:    #1f1608;   /* dark amber tint */
--status-error:       #EF4444;   /* Red — alert, action required */
--status-error-bg:    #1f0808;   /* dark red tint */
```

Usage in Python (metric card delta color approximation):
```python
# In update_center.py, use st.metric delta to signal status
st.metric("Never Updated", never_count, delta=None, delta_color="off")
st.metric("Updated Today", today_count, delta=f"+{today_count}", delta_color="normal")
st.metric("Stale", stale_count, delta=f"-{stale_count}", delta_color="inverse")
st.metric("Errors", error_count, delta=None, delta_color="off")
```

For richer card styling, add CSS targeting the metric containers:
```css
/* Status metric card variants */
[data-testid="stMetric"]:nth-child(1) { border-left: 3px solid var(--status-never); }
[data-testid="stMetric"]:nth-child(2) { border-left: 3px solid var(--status-today); }
[data-testid="stMetric"]:nth-child(3) { border-left: 3px solid var(--status-stale); }
[data-testid="stMetric"]:nth-child(4) { border-left: 3px solid var(--status-error); }
```

---

## 2. Velocity Progress Bar — Clean Replacement

Replace the `linear-gradient` + shimmer with a solid accent fill and CSS-only progress using `--accent`.

### Remove from `style.css`:
```css
/* DELETE these: */
.velocity-bar-fill {
    background: linear-gradient(90deg, var(--accent-dk), var(--accent), var(--accent-lt));
    animation: shimmer 2s infinite linear;
}
@keyframes shimmer { ... }
```

### Add to `style.css`:
```css
/* Velocity progress bar — no gradient, prefers-reduced-motion safe */
.velocity-bar-bg {
    background: var(--border);
    border-radius: var(--r-xs);   /* was hardcoded 4px */
    height: 6px;
    overflow: hidden;
    position: relative;
}

.velocity-bar-fill {
    background: var(--accent);
    border-radius: var(--r-xs);   /* was hardcoded 4px */
    height: 100%;
    transition: width 0.4s ease-out;
    position: relative;
    overflow: hidden;
}

/* Subtle sweep animation — respects reduced-motion */
.velocity-bar-fill::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.15) 50%,
        transparent 100%
    );
    animation: sweep 1.8s ease-in-out infinite;
}

@keyframes sweep {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* CRITICAL: disable for users with motion sensitivity */
@media (prefers-reduced-motion: reduce) {
    .velocity-bar-fill::after {
        animation: none;
        background: none;
    }
    .velocity-bar-fill {
        transition: none;
    }
    .pulse-active {
        animation: none !important;
    }
}
```

**Why `::after` instead of the element itself**: The gradient lives in the pseudo-element, so the fill color (`var(--accent)`) is always visible even without animation. The sweep is pure decoration.

---

## 3. Inline Style Replacements

Remove `unsafe_allow_html` inline styles by adding CSS classes.

### Add to `style.css`:
```css
/* Velocity container labels */
.velocity-unit {
    font-size: 0.6rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.velocity-company-label {
    font-size: 0.72rem;
    color: var(--text-secondary);
    margin-top: 4px;
    font-family: var(--font-mono);
}
```

### Update in `update_center.py` (the unsafe_allow_html block):
```python
# Replace:
<span class="velocity-value">{velocity:.1f} <small style="font-size:0.6rem; color:var(--text-muted)">COMP/MIN</small></span>
# With:
<span class="velocity-value">{velocity:.1f} <span class="velocity-unit">COMP/MIN</span></span>

# Replace:
<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 4px;">
# With:
<div class="velocity-company-label">
```

---

## 4. Text Contrast Fix

Replace `--text-muted` with `--text-secondary` for any readable secondary text (contrast 3.8:1 → 5.7:1):

```css
/* In :root, update the muted token or add an alias */
--text-readable-secondary: var(--text-secondary);  /* #9aa0b8, passes WCAG AA */
```

In `update_center.py` velocity bar HTML, the inline `color:var(--text-muted)` already flagged above should become `.velocity-unit` (which uses `--text-muted` for the de-emphasized unit label, acceptable since it's large-ish text) and `.velocity-company-label` (which uses `--text-secondary` for the company name, which is readable content).

---

## Summary of Token Additions

| Token | Value | Purpose |
|-------|-------|---------|
| `--status-never` | `#4a5068` | Never-updated count label |
| `--status-today` | `#00BF7A` | Updated-today count label (= `--accent`) |
| `--status-stale` | `#F59E0B` | Stale/before-today count label |
| `--status-error` | `#EF4444` | Error count label |
| `--status-*-bg` | dark tints | Optional card background tints |

All other changes use existing tokens — no new colors introduced for the progress bar.
