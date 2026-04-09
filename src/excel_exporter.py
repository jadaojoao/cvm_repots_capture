# -*- coding: utf-8 -*-
"""
src/excel_exporter.py — Exportador Excel profissional para analistas.

Gera workbook com até 9 abas:
  CAPA · KPIs · DRE · BPA · BPP · DFC · DVA · DMPL · METADADOS

Uso standalone:
    exp = ExcelExporter(company_info, statements, kpis_df)
    excel_bytes = exp.export()   # → bytes para st.download_button ou salvar em disco

Uso no Streamlit:
    st.download_button("Baixar Excel", exp.export(),
                       file_name=f"{ticker}.xlsx",
                       mime="application/vnd.ms-excel")
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import xlsxwriter

from src.statement_summary import build_general_summary_blocks

# ──────────────────────────────────────────────────────────────────────────────
# Paleta de cores
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "azul_escuro":  "#1B3A5C",   # cabeçalhos de seção
    "azul_medio":   "#2E6DA4",   # subtotais
    "azul_claro":   "#D6E4F0",   # fundo subtotal
    "cinza_claro":  "#F2F2F2",   # linhas pares / placeholders
    "cinza_texto":  "#808080",   # texto de placeholders
    "verde_claro":  "#D5F0D5",   # delta positivo
    "vermelho_claro":"#FFD5D5",  # delta negativo
    "branco":       "#FFFFFF",
    "texto_escuro": "#1A1A1A",
    "vermelho_val": "#C0392B",   # fonte para valores negativos
    "capa_azul":    "#1B3A5C",
    "capa_acento":  "#2E86AB",
}

# Contas que são subtotais (negrito + fundo) nas demonstrações
_SUBTOTAIS = {
    "DRE": {"3.01", "3.03", "3.05", "3.07", "3.11"},
    "BPA": {"1", "1.01", "1.02"},
    "BPP": {"2", "2.01", "2.02", "2.03"},
    "DFC": {"6.01", "6.02", "6.03"},
    "DVA": {"7.08"},
    "DMPL": set(),
}

# Siglas → nomes completos para tab labels
_STMT_LABELS = {
    "DRE":  "DRE",
    "BPA":  "BPA",
    "BPP":  "BPP",
    "DFC":  "DFC",
    "DVA":  "DVA",
    "DMPL": "DMPL",
}

# Categorias de KPI na ordem desejada
_KPI_CATEGORY_ORDER = [
    "Rentabilidade", "Liquidez", "Endividamento",
    "Fluxo de Caixa", "Crescimento", "Valuation",
]


def build_excel_file_stem(
    company_info: dict,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Retorna o file stem padrao usado pelos downloads de Excel."""
    timestamp = generated_at or datetime.now()
    ticker = company_info.get("ticker_b3") or f"cvm{company_info.get('cd_cvm', '')}"
    safe_ticker = str(ticker).replace(" ", "_").replace("/", "-")
    return f"{safe_ticker}_{timestamp.strftime('%Y%m%d')}"


def build_excel_filename(
    company_info: dict,
    *,
    generated_at: datetime | None = None,
) -> str:
    return f"{build_excel_file_stem(company_info, generated_at=generated_at)}.xlsx"


class ExcelExporter:
    """Gera workbook Excel profissional para uma empresa CVM.

    Parâmetros
    ----------
    company_info : dict
        Saída de CVMQueryLayer.get_company_info().
    statements   : dict[str, pd.DataFrame]
        Mapa {stmt_type: df_wide} — saída de CVMQueryLayer.get_statement().
    kpis_df      : pd.DataFrame
        Saída de kpi_engine.compute_all_kpis().
    extra_sheets : list[str], opcional
        Tipos adicionais a incluir (ex: ["DVA", "DMPL"]) se disponíveis.
    """

    def __init__(
        self,
        company_info: dict,
        statements: dict[str, pd.DataFrame],
        kpis_df: pd.DataFrame,
        extra_sheets: Optional[list[str]] = None,
    ):
        self.info       = company_info
        self.stmts      = statements
        self.kpis       = kpis_df
        self.extra      = extra_sheets or []
        self._wb:  xlsxwriter.Workbook | None = None
        self._fmt: dict = {}

    # ──────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────

    def export(self) -> bytes:
        """Retorna o workbook como bytes. Pronto para download ou escrita em disco."""
        buf = io.BytesIO()
        self._wb = xlsxwriter.Workbook(buf, {"in_memory": True, "nan_inf_to_errors": True})
        self._build_formats()

        self._write_capa()
        self._write_general()
        self._write_kpis()
        for stmt in ["DRE", "BPA", "BPP", "DFC"]:
            if stmt in self.stmts and not self.stmts[stmt].empty:
                self._write_statement(stmt)
        for stmt in ["DVA", "DMPL"]:
            if stmt in self.extra and stmt in self.stmts and not self.stmts[stmt].empty:
                self._write_statement(stmt)
        self._write_metadata()

        self._wb.close()
        buf.seek(0)
        return buf.read()

    # ──────────────────────────────────────────────────────────────────────
    # Formatos
    # ──────────────────────────────────────────────────────────────────────

    def _build_formats(self):
        wb = self._wb

        def fmt(**kw) -> xlsxwriter.workbook.Format:
            return wb.add_format(kw)

        base = {"font_name": "Calibri", "font_size": 10, "text_wrap": False}

        self._fmt = {
            # ── Gerais ──────────────────────────────────────────────────
            "normal":      fmt(**base),
            "normal_num":  fmt(**base, num_format="#,##0"),
            "normal_pct":  fmt(**base, num_format="0.0%"),
            "normal_2x":   fmt(**base, num_format="0.00x"),
            "neg_num":     fmt(**base, num_format="#,##0", font_color=C["vermelho_val"]),
            "neg_pct":     fmt(**base, num_format="0.0%",  font_color=C["vermelho_val"]),
            "bold":        fmt(**base, bold=True),

            # ── Cabeçalho de seção (KPIs) ───────────────────────────────
            "sec_header":  fmt(**base, bold=True,
                               font_color=C["branco"], bg_color=C["azul_escuro"],
                               align="left", valign="vcenter"),

            # ── Subtotais (demonstrações) ────────────────────────────────
            "subtotal":    fmt(**base, bold=True, bg_color=C["azul_claro"]),
            "subtotal_num":fmt(**base, bold=True, bg_color=C["azul_claro"],
                               num_format='#,##0;-#,##0;"-"'),
            "subtotal_neg":fmt(**base, bold=True, bg_color=C["azul_claro"],
                               num_format='#,##0;(#,##0);"-"', font_color=C["vermelho_val"]),

            # ── Placeholder (KPI futuro) ─────────────────────────────────
            "placeholder": fmt(**base, italic=True, font_color=C["cinza_texto"],
                               bg_color=C["cinza_claro"]),

            # ── Cabeçalho de coluna (linha 1) ────────────────────────────
            "col_header":  fmt(**base, bold=True, bg_color=C["azul_escuro"],
                               font_color=C["branco"], align="center",
                               valign="vcenter", border=1),
            "col_header_l":fmt(**base, bold=True, bg_color=C["azul_escuro"],
                               font_color=C["branco"], align="left",
                               valign="vcenter", border=1),

            # ── Delta YoY ────────────────────────────────────────────────
            "delta_pos":   fmt(**base, bg_color=C["verde_claro"],
                               num_format="▲ 0.0%", align="center"),
            "delta_neg":   fmt(**base, bg_color=C["vermelho_claro"],
                               num_format="▼ 0.0%", align="center"),
            "delta_zero":  fmt(**base, num_format="0.0%", align="center"),

            # ── Números com alinhamento central (colunas de período) ─────
            "num_center":  fmt(**base, num_format='#,##0;-#,##0;"-"', align="right"),
            "pct_center":  fmt(**base, num_format="0.0%",  align="right"),
            "ratio_center":fmt(**base, num_format="0.00x", align="right"),
            "neg_center":  fmt(**base, num_format='#,##0;(#,##0);"-"', align="right",
                               font_color=C["vermelho_val"]),

            # ── Capa ──────────────────────────────────────────────────────
            "capa_title":  fmt(font_name="Calibri", font_size=22, bold=True,
                               font_color=C["branco"], bg_color=C["capa_azul"],
                               valign="vcenter"),
            "capa_sub":    fmt(font_name="Calibri", font_size=12,
                               font_color=C["branco"], bg_color=C["capa_azul"],
                               valign="vcenter"),
            "capa_label":  fmt(font_name="Calibri", font_size=10, bold=True,
                               font_color=C["azul_escuro"]),
            "capa_value":  fmt(font_name="Calibri", font_size=10,
                               font_color=C["texto_escuro"]),
            "capa_warn":   fmt(font_name="Calibri", font_size=9, italic=True,
                               font_color=C["vermelho_val"]),

            # ── Metadados ──────────────────────────────────────────────────
            "meta_key":    fmt(**base, bold=True, font_color=C["azul_escuro"]),
            "meta_val":    fmt(**base),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Aba CAPA
    # ──────────────────────────────────────────────────────────────────────

    def _write_capa(self):
        ws = self._wb.add_worksheet("CAPA")
        ws.set_column("A:A", 2)
        ws.set_column("B:B", 22)
        ws.set_column("C:C", 40)
        ws.set_column("D:D", 20)

        info = self.info
        name    = info.get("company_name", "—")
        ticker  = info.get("ticker_b3") or "—"
        cd_cvm  = info.get("cd_cvm", "—")
        setor   = info.get("setor_analitico") or info.get("setor_cvm") or "—"
        cnpj    = info.get("cnpj") or "—"
        now_str = datetime.now().strftime("%Y-%m-%d  %H:%M")

        # Título
        ws.set_row(1, 40)
        ws.merge_range("B2:D2", name, self._fmt["capa_title"])
        ws.set_row(2, 25)
        ws.merge_range("B3:D3", f"{setor}  ·  CVM: {cd_cvm}  ·  {ticker}", self._fmt["capa_sub"])

        # Linha separadora
        ws.set_row(3, 6)
        ws.merge_range("B4:D4", "", self._wb.add_format({
            "bg_color": C["capa_acento"]
        }))

        # Dados
        rows_info = [
            ("Ticker B3",        ticker),
            ("Código CVM",       str(cd_cvm)),
            ("CNPJ",             cnpj),
            ("Setor CVM",        info.get("setor_cvm") or "—"),
            ("Setor Analítico",  setor),
            ("Gerado em",        now_str),
            ("Fonte de dados",   "CVM — dados.cvm.gov.br"),
            ("Escala valores",   "Ver nota abaixo"),
            ("Unidade padrão",   "R$ milhares (exceto onde indicado na aba METADADOS)"),
        ]

        r = 5
        for label, value in rows_info:
            ws.set_row(r, 18)
            ws.write(r, 1, label, self._fmt["capa_label"])
            ws.write(r, 2, value, self._fmt["capa_value"])
            r += 1

        # Nota de escala
        r += 1
        ws.merge_range(r, 1, r, 3,
            "⚠  NOTA DE ESCALA: Valores armazenados conforme reportado à CVM. "
            "A maioria das empresas reporta em R$ mil (milhares). Algumas empresas "
            "(ex: Ânima) reportam em R$ milhões. Consulte a aba METADADOS para confirmar.",
            self._fmt["capa_warn"])

        # Ocultar linhas de grade
        ws.hide_gridlines(2)

    # ──────────────────────────────────────────────────────────────────────
    # Aba KPIs
    # ──────────────────────────────────────────────────────────────────────

    def _write_kpis(self):
        ws = self._wb.add_worksheet("KPIs")
        kpis = self.kpis

        if kpis is None or kpis.empty:
            ws.write(0, 0, "KPIs não disponíveis", self._fmt["normal"])
            return

        # Detectar colunas de anos
        meta_cols = {"CATEGORIA", "KPI_ID", "KPI_NOME", "FORMULA",
                     "IS_PLACEHOLDER", "FORMAT_TYPE", "HIGHER_IS_BETTER",
                     "UNIDADE", "DELTA_YOY", "DELTA_YOY_PCT"}
        year_cols = [c for c in kpis.columns if c not in meta_cols]

        # ── Cabeçalho ────────────────────────────────────────────────────
        ws.set_row(0, 22)
        headers = ["INDICADOR", "FÓRMULA", "UNIDADE"] + [str(y) for y in year_cols] + ["Δ YoY", "Tendência"]
        col_widths = [32, 42, 8] + [10] * len(year_cols) + [10, 12]

        for c, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(0, c, h, self._fmt["col_header_l"] if c < 3 else self._fmt["col_header"])
            ws.set_column(c, c, w)

        # Freeze header + coluna INDICADOR
        ws.freeze_panes(1, 1)

        # ── Linhas por categoria ──────────────────────────────────────────
        row = 1
        current_cat = None
        for _, kpi_row in kpis.iterrows():
            cat = kpi_row["CATEGORIA"]

            # Inserir separador de seção quando muda a categoria
            if cat != current_cat:
                current_cat = cat
                ws.set_row(row, 18)
                ws.write(row, 0, f"  {cat.upper()}", self._fmt["sec_header"])
                for _c in range(1, len(headers)):
                    ws.write_blank(row, _c, None, self._fmt["sec_header"])
                row += 1

            is_placeholder = bool(kpi_row.get("IS_PLACEHOLDER", False))
            fmt_type = kpi_row.get("FORMAT_TYPE", "ratio")
            higher   = bool(kpi_row.get("HIGHER_IS_BETTER", True))

            txt_fmt = self._fmt["placeholder"] if is_placeholder else self._fmt["normal"]

            ws.set_row(row, 16)
            ws.write(row, 0, kpi_row["KPI_NOME"], txt_fmt)
            ws.write(row, 1, kpi_row["FORMULA"],  txt_fmt)
            ws.write(row, 2, kpi_row.get("UNIDADE", ""), txt_fmt)

            # Valores por ano
            for c_idx, yr in enumerate(year_cols, start=3):
                v = kpi_row.get(yr)
                if is_placeholder or v is None:
                    ws.write_blank(row, c_idx, None, txt_fmt)
                    continue
                num_fmt = (self._fmt["pct_center"] if fmt_type == "pct"
                           else self._fmt["ratio_center"])
                ws.write_number(row, c_idx, v, num_fmt)

            # Delta YoY
            delta = kpi_row.get("DELTA_YOY")
            delta_pct = kpi_row.get("DELTA_YOY_PCT")
            c_delta  = 3 + len(year_cols)
            c_trend  = c_delta + 1

            if is_placeholder or delta is None or delta_pct is None:
                ws.write_blank(row, c_delta, None, txt_fmt)
                ws.write_blank(row, c_trend, None, txt_fmt)
            else:
                is_good = (delta > 0) == higher
                delta_fmt = (self._fmt["delta_pos"] if is_good
                             else self._fmt["delta_neg"])
                ws.write_number(row, c_delta, delta,     (self._fmt["pct_center"]
                                                           if fmt_type == "pct"
                                                           else self._fmt["ratio_center"]))
                trend = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
                trend_fmt = (self._fmt["delta_pos"] if is_good else
                             self._fmt["delta_neg"])
                ws.write(row, c_trend, trend, trend_fmt)

            row += 1

        ws.hide_gridlines(2)

    # ──────────────────────────────────────────────────────────────────────
    # Abas de demonstrações (DRE / BPA / BPP / DFC / DVA / DMPL)
    # ──────────────────────────────────────────────────────────────────────

    def _write_general(self):
        ws = self._wb.add_worksheet("GERAL")
        blocks = build_general_summary_blocks(self.stmts)

        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 42)

        max_period_cols = 0
        for block in blocks:
            period_cols = [c for c in block.rows.columns if c not in {"CD_CONTA", "LABEL", "IS_SUBTOTAL"}]
            max_period_cols = max(max_period_cols, len(period_cols))

        if max_period_cols > 0:
            ws.set_column(2, 1 + max_period_cols, 13)

        if not blocks:
            ws.write(0, 0, "Resumo condensado indisponível", self._fmt["normal"])
            ws.hide_gridlines(2)
            return

        row = 0
        for block in blocks:
            period_cols = [c for c in block.rows.columns if c not in {"CD_CONTA", "LABEL", "IS_SUBTOTAL"}]
            last_col = max(1, 1 + len(period_cols))
            ws.write(row, 0, block.title, self._fmt["sec_header"])
            for c_idx in range(1, last_col + 1):
                ws.write_blank(row, c_idx, None, self._fmt["sec_header"])
            row += 1

            headers = ["CD_CONTA", "LINHA"] + [str(col) for col in period_cols]
            for c_idx, header in enumerate(headers):
                fmt = self._fmt["col_header_l"] if c_idx < 2 else self._fmt["col_header"]
                ws.write(row, c_idx, header, fmt)
            row += 1

            for _, stmt_row in block.rows.iterrows():
                is_subtotal = bool(stmt_row.get("IS_SUBTOTAL", False))
                text_fmt = self._fmt["subtotal"] if is_subtotal else self._fmt["normal"]
                ws.write(row, 0, str(stmt_row.get("CD_CONTA", "")), text_fmt)
                ws.write(row, 1, str(stmt_row.get("LABEL", "")), text_fmt)

                for c_idx, period_col in enumerate(period_cols, start=2):
                    value = stmt_row.get(period_col)
                    if pd.isna(value) or value is None:
                        blank_fmt = self._fmt["subtotal_num"] if is_subtotal else self._fmt["normal"]
                        ws.write_blank(row, c_idx, None, blank_fmt)
                        continue

                    number = float(value)
                    if is_subtotal:
                        num_fmt = self._fmt["subtotal_neg"] if number < 0 else self._fmt["subtotal_num"]
                    else:
                        num_fmt = self._fmt["neg_center"] if number < 0 else self._fmt["num_center"]
                    ws.write_number(row, c_idx, number, num_fmt)

                row += 1

            row += 1

        ws.hide_gridlines(2)

    def _write_statement(self, stmt_type: str):
        df = self.stmts.get(stmt_type)
        if df is None or df.empty:
            return

        label = _STMT_LABELS.get(stmt_type, stmt_type)
        ws = self._wb.add_worksheet(label)
        subtotais = _SUBTOTAIS.get(stmt_type, set())

        # Colunas fixas e de período
        id_cols    = [c for c in ["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"]
                      if c in df.columns]
        period_cols = [c for c in df.columns if c not in id_cols]

        all_cols = id_cols + period_cols
        col_widths = {
            "CD_CONTA":      14,
            "DS_CONTA":      44,
            "STANDARD_NAME": 34,
            "LINE_ID_BASE":  24,
        }

        # ── Cabeçalho ────────────────────────────────────────────────────
        ws.set_row(0, 22)
        for c_idx, col in enumerate(all_cols):
            w = col_widths.get(col, 13)
            ws.set_column(c_idx, c_idx, w)
            fmt = self._fmt["col_header_l"] if col in id_cols else self._fmt["col_header"]
            ws.write(0, c_idx, col, fmt)

        # Freeze: linha 1 + primeiras 3 colunas
        freeze_cols = min(3, len(id_cols))
        ws.freeze_panes(1, freeze_cols)

        # ── Dados ────────────────────────────────────────────────────────
        for r_idx, (_, row) in enumerate(df.iterrows(), start=1):
            cd = str(row.get("CD_CONTA", ""))
            is_subtotal = cd in subtotais

            ws.set_row(r_idx, 15)

            for c_idx, col in enumerate(all_cols):
                val = row[col]
                is_period = col in period_cols

                if not is_period:
                    # Coluna de texto
                    ws.write(r_idx, c_idx, "" if pd.isna(val) else str(val),
                             self._fmt["subtotal"] if is_subtotal else self._fmt["normal"])
                    continue

                # Coluna numérica (período)
                if pd.isna(val) or val is None:
                    ws.write_blank(r_idx, c_idx, None,
                                   self._fmt["subtotal_num"] if is_subtotal
                                   else self._fmt["normal"])
                    continue

                v = float(val)
                if is_subtotal:
                    fmt = (self._fmt["subtotal_neg"] if v < 0
                           else self._fmt["subtotal_num"])
                else:
                    fmt = (self._fmt["neg_center"] if v < 0
                           else self._fmt["num_center"])
                ws.write_number(r_idx, c_idx, v, fmt)

        ws.hide_gridlines(2)

    # ──────────────────────────────────────────────────────────────────────
    # Aba METADADOS
    # ──────────────────────────────────────────────────────────────────────

    def _write_metadata(self):
        ws = self._wb.add_worksheet("METADADOS")
        ws.set_column("A:A", 30)
        ws.set_column("B:B", 60)
        ws.set_column("C:C", 20)

        ws.set_row(0, 22)
        ws.write(0, 0, "CAMPO",  self._fmt["col_header_l"])
        ws.write(0, 1, "VALOR",  self._fmt["col_header_l"])
        ws.write(0, 2, "NOTAS",  self._fmt["col_header_l"])

        info = self.info
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stmts_present = ", ".join(
            k for k in ["DRE", "BPA", "BPP", "DFC", "DVA", "DMPL"]
            if k in self.stmts and not self.stmts[k].empty
        )

        rows = [
            ("Empresa",              info.get("company_name", "—"),          ""),
            ("Código CVM (cd_cvm)",  str(info.get("cd_cvm", "—")),           ""),
            ("Ticker B3",            info.get("ticker_b3") or "—",           ""),
            ("CNPJ",                 info.get("cnpj") or "—",                ""),
            ("Setor CVM",            info.get("setor_cvm") or "—",           ""),
            ("Setor Analítico",      info.get("setor_analitico") or "—",     ""),
            ("Demonstrações",        stmts_present,                          "Abas geradas neste workbook"),
            ("Gerado em",            now_str,                                ""),
            ("Fonte de dados",       "CVM — dados.cvm.gov.br",               "DFP/ITR"),
            ("Ferramenta",           "cvm_reports_capture",                  "github / uso interno"),
            ("Escala padrão CVM",    "R$ milhares (mil)",                    "A maioria das empresas"),
            ("Atenção escala",       "Verificar empresa — algumas reportam em R$ milhões",
             "Ex: Ânima Holding reporta em R$ mi"),
            ("QA_CONFLICT",          "Linhas com conflito de dados excluídas", "QA_CONFLICT=0 aplicado"),
            ("D&A na DFC",           "CD_CONTA 6.01.01.x filtrado por 'depreci' (exclui amortiz. financeira)",
             "EBITDA = EBIT + D&A"),
            ("EBITDA",               "EBIT (3.05) + D&A (DFC 6.01.01.x)",   "Se D&A não encontrado → NaN"),
            ("Dívida Liq./EBITDA",   "Proxy: PNC - Caixa / EBITDA",          "PNC ≈ dívida financeira LP"),
            ("Liquidez Seca",        "Sem separação de estoque no nível 1",  "≈ Liquidez Corrente"),
            ("CAPEX / Receita",      "FCI total (proxy)",                    "Inclui todas saídas de investimento"),
            ("Placeholders (*)",     "KPIs futuros marcados com * requerem preço de mercado", ""),
        ]

        for r_idx, (key, val, note) in enumerate(rows, start=1):
            ws.set_row(r_idx, 16)
            ws.write(r_idx, 0, key,  self._fmt["meta_key"])
            ws.write(r_idx, 1, val,  self._fmt["meta_val"])
            ws.write(r_idx, 2, note, self._fmt["normal"])

        ws.freeze_panes(1, 0)
        ws.hide_gridlines(2)
