# -*- coding: utf-8 -*-
"""
dashboard/tabs/download.py — Aba de download: Excel completo + CSV por demonstração.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import sys
from pathlib import Path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.excel_exporter import ExcelExporter


def render(
    company_info: dict,
    statements: dict[str, pd.DataFrame],
    kpis_df: pd.DataFrame,
    include_optional: bool = False,
):
    """Renderiza a aba de download."""
    name   = company_info.get("company_name", "empresa")
    ticker = company_info.get("ticker_b3") or f"cvm{company_info.get('cd_cvm', '')}"
    cd_cvm = company_info.get("cd_cvm", "")
    date_str = datetime.now().strftime("%Y%m%d")
    file_stem = f"{ticker}_{date_str}".replace(" ", "_").replace("/", "-")

    # ── Excel completo ─────────────────────────────────────────────────────
    st.markdown("### 📥 Excel Completo")
    st.markdown(
        f"Workbook profissional para **{name}** com KPIs, DRE, BPA, BPP, DFC"
        + (" + DVA, DMPL" if include_optional else "")
        + " e metadados."
    )

    extra = []
    if include_optional:
        extra = [s for s in ["DVA", "DMPL"]
                 if s in statements and not statements[s].empty]

    stmts_for_export = {k: statements[k] for k in ["DRE", "BPA", "BPP", "DFC", "DVA", "DMPL"]
                        if k in statements and not statements[k].empty}

    # Gera Excel sem cache de closure — o cache dos dados brutos já está em
    # load_statements() e load_kpis() no app.py
    exp = ExcelExporter(
        company_info=company_info,
        statements=stmts_for_export,
        kpis_df=kpis_df,
        extra_sheets=extra,
    )
    excel_bytes = exp.export()

    st.download_button(
        label=f"⬇️  Baixar {ticker} — Excel Completo",
        data=excel_bytes,
        file_name=f"{file_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
        key=f"dl_excel_{cd_cvm}",
    )

    st.caption(
        "✅ Inclui: CAPA · KPIs (com fórmulas e Δ YoY) · DRE · BPA · BPP · DFC"
        + (" · DVA · DMPL" if extra else "")
        + " · METADADOS"
    )

    # ── CSVs individuais ───────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📄 CSV por Demonstração")
    st.caption("Útil para importar em ferramentas externas (Excel manual, Python, R).")

    csv_stmts = [s for s in ["DRE", "BPA", "BPP", "DFC"]
                 if s in statements and not statements[s].empty]

    cols = st.columns(len(csv_stmts)) if csv_stmts else []
    for col, stmt_type in zip(cols, csv_stmts):
        with col:
            df = statements[stmt_type]
            csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label=f"⬇️ {stmt_type} (.csv)",
                data=csv_bytes,
                file_name=f"{file_stem}_{stmt_type}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"dl_csv_{stmt_type}_{cd_cvm}",
            )

    # ── KPIs CSV ───────────────────────────────────────────────────────────
    if kpis_df is not None and not kpis_df.empty:
        st.divider()
        kpis_csv = kpis_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️ KPIs (.csv)",
            data=kpis_csv,
            file_name=f"{file_stem}_KPIs.csv",
            mime="text/csv",
            key=f"dl_kpis_{cd_cvm}",
        )

    # ── Aviso de escala ────────────────────────────────────────────────────
    st.divider()
    st.info(
        "ℹ️  **Nota de escala:** Valores conforme reportado à CVM. "
        "A maioria das empresas usa R$ mil. Consulte a aba METADADOS no Excel para detalhes."
    )
