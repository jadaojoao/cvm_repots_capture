# -*- coding: utf-8 -*-
"""dashboard/components/ui.py — Premium HTML component builders."""
from __future__ import annotations
import re


def _s(v) -> str:
    """Escapa caracteres que o parser Markdown do Streamlit interpreta ($ → LaTeX)."""
    return str(v).replace('$', '&#36;')


def _html(s: str) -> str:
    """Remove linhas só-branco que encerrariam HTML blocks no CommonMark parser do Streamlit."""
    return re.sub(r'\n[ \t]+\n', '\n', s).strip()


def hero_card(company_name: str, ticker: str | None, sector: str,
              cvm_code: int, year_range: str,
              price: float | None = None,
              mktcap_str: str | None = None) -> str:
    ticker_badge = f'<span class="hero-ticker">{ticker.replace(".SA","")}</span>' if ticker else ''
    price_block = ''
    if price is not None:
        price_str = f'R&#36;\u00a0{price:.2f}'
        mkt_str   = _s(mktcap_str) if mktcap_str else ''
        mkt_span  = f'<span class="hero-mktcap">{mkt_str}</span>' if mkt_str else ''
        price_block = (
            f'<div class="hero-price-block">'
            f'<span class="hero-price-label">Cota\u00e7\u00e3o</span>'
            f'<span class="hero-price">{price_str}</span>'
            f'{mkt_span}'
            f'</div>'
        )
    return _html(f'''
<div class="hero-card">
<div class="hero-card-glow"></div>
<div class="hero-top">
<div class="hero-logo-dot"></div>
<div class="hero-meta-row">{ticker_badge}<span class="hero-cvm">CVM\u00a0{cvm_code}</span></div>
</div>
<div class="hero-name">{company_name}</div>
<div class="hero-sub">{sector}\u00a0\u00b7\u00a0{year_range}</div>
{price_block}
</div>''')


def kpi_row(cards: list[dict]) -> str:
    """cards: list of {label, value, delta, delta_up (bool|None), icon}"""
    items = []
    for c in cards:
        up = c.get('delta_up')
        delta_cls = 'delta-up' if up is True else ('delta-down' if up is False else 'delta-neutral')
        delta_html = f'<span class="kpi-delta {delta_cls}">{c["delta"]}</span>' if c.get("delta") else ''
        icon = c.get('icon', '◆')
        items.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-icon">{icon}</div>'
            f'<div class="kpi-body">'
            f'<div class="kpi-label">{c["label"]}</div>'
            f'<div class="kpi-value">{_s(c["value"])}</div>'
            f'{delta_html}'
            f'</div></div>'
        )
    return f'<div class="kpi-row">{"".join(items)}</div>'


def quick_actions(actions: list[dict]) -> str:
    pills = ''.join(
        f'<div class="qa-pill"><span class="qa-icon">{a["icon"]}</span>'
        f'<span class="qa-label">{a["label"]}</span></div>'
        for a in actions
    )
    return f'<div class="qa-row">{pills}</div>'


def section_title(text: str, sub: str = '') -> str:
    sub_html = f'<span class="section-sub">{sub}</span>' if sub else ''
    return f'<div class="section-title">{text}{sub_html}</div>'


def stat_breakdown(title: str, total_label: str, total_value: str,
                   items: list[dict], period: str = '') -> str:
    """items: [{label, value, pct (0-100), color}]"""
    period_badge = f'<span class="stat-period">{period}</span>' if period else ''
    rows = ''.join(
        f'<div class="stat-row">'
        f'<div class="stat-bar-wrap">'
        f'<div class="stat-bar-fill" style="width:{it.get("pct", 0):.0f}%;background:{it.get("color", "var(--accent)")}"></div>'
        f'</div>'
        f'<div class="stat-row-body">'
        f'<span class="stat-row-label">{it["label"]}</span>'
        f'<span class="stat-row-value">{_s(it["value"])}</span>'
        f'</div></div>'
        for it in items
    )
    header_inner = f'<span class="stat-card-title">{title}</span>{period_badge}'
    return _html(f'''
<div class="stat-card">
<div class="stat-card-header">{header_inner}</div>
<div class="stat-total-label">{total_label}</div>
<div class="stat-total-value">{_s(total_value)}</div>
<div class="stat-divider"></div>
<div class="stat-rows">{rows}</div>
</div>''')


def activity_feed(title: str, groups: list[dict]) -> str:
    """groups: [{period, items: [{icon, text, time, color}]}]"""
    content = ''
    for g in groups:
        items_html = ''.join(
            f'<div class="act-item">'
            f'<div class="act-dot" style="background:{it.get("color", "var(--accent)")}"></div>'
            f'<div class="act-body">'
            f'<span class="act-text">{_s(it["text"])}</span>'
            f'<span class="act-time">{it["time"]}</span>'
            f'</div></div>'
            for it in g.get('items', [])
        )
        content += f'<div class="act-group"><div class="act-period">{g["period"]}</div>{items_html}</div>'
    return _html(f'''
<div class="act-card">
<div class="act-card-header">{title}</div>
{content}
</div>''')


def progress_card(title: str, used: float, total: float,
                  used_label: str, total_label: str, pct_label: str) -> str:
    pct = min(100, max(0, (used / total * 100) if total else 0))
    color = 'var(--accent)' if pct < 75 else ('var(--amber)' if pct < 90 else 'var(--red)')
    return _html(f'''
<div class="progress-card">
<div class="progress-header">
<span class="progress-title">{title}</span>
<span class="progress-pct" style="color:{color}">{_s(pct_label)}</span>
</div>
<div class="progress-sub">{_s(used_label)} de {_s(total_label)}</div>
<div class="progress-bar-bg">
<div class="progress-bar-fill" style="width:{pct:.0f}%;background:{color}"></div>
</div>
</div>''')
