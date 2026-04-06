# -*- coding: utf-8 -*-
"""
dashboard/tabs/demonstracoes.py — Aba de demonstrações financeiras.

Exibe DRE / BPA / BPP / DFC com colunas anuais e trimestrais,
subtotais em negrito, valores negativos em vermelho.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# Contas que são subtotais — mesmo mapeamento do excel_exporter
_SUBTOTAIS = {
    "DRE": {"3.01", "3.03", "3.05", "3.07", "3.11"},
    "BPA": {"1", "1.01", "1.02"},
    "BPP": {"2", "2.01", "2.02", "2.03"},
    "DFC": {"6.01", "6.02", "6.03"},
}

_STMT_NAMES = {
    "DRE": "📈 DRE — Demonstração de Resultado",
    "BPA": "🏦 BPA — Balanço Ativo",
    "BPP": "🏦 BPP — Balanço Passivo + PL",
    "DFC": "💰 DFC — Fluxo de Caixa",
}


def render(statements: dict[str, pd.DataFrame]):
    """Renderiza a aba de demonstrações financeiras."""
    available = [s for s in ["DRE", "BPA", "BPP", "DFC"]
                 if s in statements and not statements[s].empty]

    if not available:
        st.warning("Nenhuma demonstração financeira disponível.")
        return

    tabs = st.tabs([_STMT_NAMES.get(s, s) for s in available])

    for tab, stmt_type in zip(tabs, available):
        with tab:
            _render_statement(statements[stmt_type], stmt_type)


def _render_statement(df: pd.DataFrame, stmt_type: str):
    """Renderiza uma demonstração no formato wide com estilo."""
    if df.empty:
        st.info("Sem dados.")
        return

    id_cols    = [c for c in ["CD_CONTA", "DS_CONTA", "STANDARD_NAME"] if c in df.columns]
    period_cols = [c for c in df.columns if c not in id_cols and c != "LINE_ID_BASE"]
    subtotais  = _SUBTOTAIS.get(stmt_type, set())

    display_df = df[id_cols + period_cols].copy()

    # ── Estilo ─────────────────────────────────────────────────────────────
    def _style(df_s: pd.DataFrame):
        """Aplica estilos: subtotais em negrito, negativos em vermelho."""
        styles = pd.DataFrame("", index=df_s.index, columns=df_s.columns)

        for r_idx, row in df_s.iterrows():
            cd = str(row.get("CD_CONTA", ""))
            is_sub = cd in subtotais

            for col in df_s.columns:
                val = row[col]
                style_parts = []

                if is_sub:
                    style_parts.append("font-weight: bold")
                    style_parts.append("background-color: #D6E4F0")

                if col in period_cols and pd.notna(val):
                    try:
                        if float(val) < 0:
                            style_parts.append("color: #C0392B")
                    except (ValueError, TypeError):
                        pass

                styles.loc[r_idx, col] = "; ".join(style_parts)

        return styles

    # Formatar valores numéricos para exibição legível
    display_formatted = display_df.copy()
    for col in period_cols:
        display_formatted[col] = display_df[col].apply(
            lambda v: f"{v:,.0f}" if pd.notna(v) else ""
        )

    styled = display_formatted.style.apply(_style, axis=None)

    st.caption(f"Valores em R$ mil · {len(period_cols)} períodos · {len(display_df)} linhas")
    st.dataframe(
        styled,
        use_container_width=True,
        height=min(600, 35 + len(display_df) * 35),
    )
