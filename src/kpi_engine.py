# -*- coding: utf-8 -*-
"""
src/kpi_engine.py — Motor de cálculo de KPIs financeiros a partir de contas CVM.

Entrada:  accounts_df  — DataFrame retornado por CVMQueryLayer.get_kpi_accounts()
          da_series    — pd.Series retornada por CVMQueryLayer.get_da_from_dfc() (opcional)

Saída:    pd.DataFrame com colunas:
            CATEGORIA, KPI_ID, KPI_NOME, FORMULA, IS_PLACEHOLDER,
            *anos (ex: 2022, 2023, 2024), DELTA_YOY, DELTA_YOY_PCT
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# Catálogo de KPIs
# Cada entrada: (kpi_id, nome, formula_str, categoria, is_placeholder)
# ──────────────────────────────────────────────────────────────────────────────
_KPI_CATALOG = [
    # RENTABILIDADE
    ("MG_BRUTA",   "Margem Bruta",          "Res_Bruto / Receita",                           "Rentabilidade", False),
    ("MG_EBITDA",  "Margem EBITDA",         "EBITDA / Receita  [EBIT + D&A da DFC]",         "Rentabilidade", False),
    ("MG_EBIT",    "Margem EBIT",           "EBIT / Receita",                                "Rentabilidade", False),
    ("MG_LIQ",     "Margem Líquida",        "Lucro_Liq / Receita",                           "Rentabilidade", False),
    ("ROE",        "ROE",                   "Lucro_Liq / PL",                                "Rentabilidade", False),
    ("ROA",        "ROA",                   "Lucro_Liq / Ativo_Total",                       "Rentabilidade", False),
    ("ROIC",       "ROIC *",                "NOPAT / Capital Investido  [futuro]",            "Rentabilidade", True),
    # LIQUIDEZ
    ("LIQ_CORR",   "Liquidez Corrente",     "AC / PC",                                       "Liquidez",      False),
    ("LIQ_SECA",   "Liquidez Seca",         "(AC - Estoque) / PC  [≈ AC / PC s/ ajuste]",    "Liquidez",      False),
    ("LIQ_IMED",   "Liquidez Imediata",     "Caixa / PC",                                    "Liquidez",      False),
    # ENDIVIDAMENTO
    ("DIV_EBITDA", "Dívida Líq./EBITDA",    "PNC_proxy / EBITDA  [proxy: PNC sem PL]",       "Endividamento", False),
    ("PL_PASS",    "PL / Passivo Total",    "PL / Passivo_Total",                            "Endividamento", False),
    ("PC_PASS",    "Passivo Circ./Total",   "PC / Passivo_Total",                            "Endividamento", False),
    # FLUXO DE CAIXA
    ("FCO_REC",    "FCO / Receita",         "FCO / Receita",                                 "Fluxo de Caixa",False),
    ("FCL_REC",    "FCL / Receita",         "(FCO + FCI) / Receita",                         "Fluxo de Caixa",False),
    ("CAPEX_REC",  "CAPEX / Receita *",     "|FCI| / Receita  [FCI ≈ CAPEX, proxy]",         "Fluxo de Caixa",False),
    # CRESCIMENTO
    ("CRESC_REC",  "Crescimento Receita",   "Receita(t) / Receita(t-1) - 1",                 "Crescimento",   False),
    ("CRESC_LUC",  "Crescimento Lucro",     "Lucro_Liq(t) / Lucro_Liq(t-1) - 1",            "Crescimento",   False),
    ("CAGR_REC",   "CAGR Receita (5a) *",   "CAGR período disponível  [futuro]",             "Crescimento",   True),
    # VALUATION (placeholders — requerem preço de mercado)
    ("EV_EBITDA",  "EV/EBITDA *",           "(Market Cap + Dív.Liq) / EBITDA  [futuro]",     "Valuation",     True),
    ("PL_PRECO",   "P/L *",                 "Preço / LPA  [futuro]",                         "Valuation",     True),
    ("DY",         "Dividend Yield *",      "DPA / Preço  [futuro]",                         "Valuation",     True),
]

_PCTS = {
    "MG_BRUTA", "MG_EBITDA", "MG_EBIT", "MG_LIQ",
    "ROE", "ROA", "ROIC",
    "FCO_REC", "FCL_REC", "CAPEX_REC",
    "CRESC_REC", "CRESC_LUC", "CAGR_REC",
    "PC_PASS", "PL_PASS",
    "DY",
}

_HIGHER_IS_BETTER = {
    "MG_BRUTA", "MG_EBITDA", "MG_EBIT", "MG_LIQ",
    "ROE", "ROA", "ROIC",
    "LIQ_CORR", "LIQ_SECA", "LIQ_IMED",
    "PL_PASS",
    "FCO_REC", "FCL_REC",
    "CRESC_REC", "CRESC_LUC", "CAGR_REC",
}


def compute_all_kpis(
    accounts_df: pd.DataFrame,
    da_series: pd.Series | None = None,
) -> pd.DataFrame:
    """Calcula todos os KPIs do catálogo.

    Parâmetros
    ----------
    accounts_df : pd.DataFrame
        Saída de CVMQueryLayer.get_kpi_accounts(). Deve ter REPORT_YEAR como coluna.
    da_series : pd.Series, opcional
        Saída de CVMQueryLayer.get_da_from_dfc(). Index = REPORT_YEAR.

    Retorna
    -------
    pd.DataFrame com (CATEGORIA, KPI_ID, KPI_NOME, FORMULA, IS_PLACEHOLDER,
                       FORMAT_TYPE, HIGHER_IS_BETTER, *anos, DELTA_YOY, DELTA_YOY_PCT)
    """
    if accounts_df.empty:
        return pd.DataFrame()

    acc = accounts_df.copy()
    acc = acc.set_index("REPORT_YEAR")
    years = sorted(acc.index.tolist())

    def col(name: str) -> pd.Series:
        return acc[name] if name in acc.columns else pd.Series(np.nan, index=acc.index)

    # ── Derivar EBITDA ────────────────────────────────────────────────────────
    ebit = col("EBIT")
    if da_series is not None and not da_series.empty:
        da = da_series.reindex(acc.index).fillna(0)
        ebitda = ebit + da
    else:
        ebitda = pd.Series(np.nan, index=acc.index)

    # ── Derivar proxy dívida líquida para Dív/EBITDA ─────────────────────────
    # Dívida bruta proxy = PNC (Passivo Não Circulante)
    # Dívida líquida proxy = PNC - Caixa
    pnc  = col("PNC")
    cash = col("Caixa")
    div_liq_proxy = pnc - cash

    # ── Funções auxiliares de divisão segura ─────────────────────────────────
    def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
        result = num / den.replace(0, np.nan)
        return result

    # ── Calcular cada KPI ────────────────────────────────────────────────────
    receita   = col("Receita")
    res_bruto = col("Res_Bruto")
    lucro     = col("Lucro_Liq")
    pl        = col("PL")
    at        = col("Ativo_Total")
    pass_tot  = col("Passivo_Total")
    pc        = col("PC")
    ac        = col("AC")
    caixa     = col("Caixa")
    fco       = col("FCO")
    fci       = col("FCI")

    kpi_values: dict[str, pd.Series] = {
        "MG_BRUTA":   safe_div(res_bruto, receita),
        "MG_EBITDA":  safe_div(ebitda, receita),
        "MG_EBIT":    safe_div(ebit, receita),
        "MG_LIQ":     safe_div(lucro, receita),
        "ROE":        safe_div(lucro, pl),
        "ROA":        safe_div(lucro, at),
        "ROIC":       pd.Series(np.nan, index=acc.index),
        "LIQ_CORR":   safe_div(ac, pc),
        "LIQ_SECA":   safe_div(ac, pc),          # sem estoque separado no nível 1
        "LIQ_IMED":   safe_div(caixa, pc),
        "DIV_EBITDA": safe_div(div_liq_proxy, ebitda),
        "PL_PASS":    safe_div(pl, pass_tot),
        "PC_PASS":    safe_div(pc, pass_tot),
        "FCO_REC":    safe_div(fco, receita),
        "FCL_REC":    safe_div(fco + fci, receita),
        "CAPEX_REC":  safe_div(fci.abs(), receita),
        "CRESC_REC":  receita.pct_change(fill_method=None),
        "CRESC_LUC":  lucro.pct_change(fill_method=None),
        "CAGR_REC":   pd.Series(np.nan, index=acc.index),
        "EV_EBITDA":  pd.Series(np.nan, index=acc.index),
        "PL_PRECO":   pd.Series(np.nan, index=acc.index),
        "DY":         pd.Series(np.nan, index=acc.index),
    }

    # ── Montar DataFrame de saída ─────────────────────────────────────────────
    rows = []
    for kpi_id, kpi_nome, formula, categoria, is_placeholder in _KPI_CATALOG:
        vals = kpi_values.get(kpi_id, pd.Series(np.nan, index=acc.index))
        row: dict = {
            "CATEGORIA":       categoria,
            "KPI_ID":          kpi_id,
            "KPI_NOME":        kpi_nome,
            "FORMULA":         formula,
            "IS_PLACEHOLDER":  is_placeholder,
            "FORMAT_TYPE":     "pct" if kpi_id in _PCTS else "ratio",
            "HIGHER_IS_BETTER": kpi_id in _HIGHER_IS_BETTER,
            "UNIDADE":         "%" if kpi_id in _PCTS else "x",
        }
        for yr in years:
            v = vals.get(yr, np.nan)
            row[yr] = round(float(v), 6) if pd.notna(v) and not np.isinf(v) else None

        # Delta YoY: último ano vs penúltimo
        if len(years) >= 2:
            last, prev = years[-1], years[-2]
            v_last = row.get(last)
            v_prev = row.get(prev)
            if v_last is not None and v_prev is not None and v_prev != 0:
                delta = v_last - v_prev
                row["DELTA_YOY"]     = round(delta, 6)
                row["DELTA_YOY_PCT"] = round(delta / abs(v_prev), 6)
            else:
                row["DELTA_YOY"] = None
                row["DELTA_YOY_PCT"] = None
        else:
            row["DELTA_YOY"] = None
            row["DELTA_YOY_PCT"] = None

        rows.append(row)

    return pd.DataFrame(rows)


def _parse_period(label: str) -> tuple[int, int]:
    """Extrai (ano, trimestre) de um PERIOD_LABEL.

    '1Q22' → (2022, 1), '2Q23' → (2023, 2), '4Q22' → (2022, 4),
    '2022' → (2022, 99).  trimestre=99 indica período anual.
    """
    import re
    m = re.match(r"(\d)Q(\d{2})", label)
    if m:
        return (2000 + int(m.group(2)), int(m.group(1)))
    m2 = re.match(r"(\d{4})", label)
    if m2:
        return (int(m2.group(1)), 99)
    return (0, 0)


def compute_quarterly_kpis(
    accounts_df: pd.DataFrame,
    da_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calcula KPIs para TODOS os períodos (anuais + trimestrais) com LTM.

    Abordagem LTM (Last Twelve Months) via trailing 4 quarters:
      LTM = soma dos últimos 4 trimestres standalone.

    Tipos de conta:
      - Flow (DRE/DFC): LTM para indicadores anualizados
      - Stock (BPA/BPP): valor direto do período (quarter-end snapshot)

    Parâmetros
    ----------
    accounts_df : pd.DataFrame
        Saída de CVMQueryLayer.get_kpi_accounts_all_periods().
    da_df : pd.DataFrame, opcional
        Saída de CVMQueryLayer.get_da_all_periods().

    Retorna
    -------
    pd.DataFrame com colunas de período + metadados de KPI.
    """
    if accounts_df.empty:
        return pd.DataFrame()

    acc = accounts_df.copy()

    # Mesclar D&A
    if da_df is not None and not da_df.empty:
        da_merged = da_df[["REPORT_YEAR", "PERIOD_LABEL", "da_value"]].copy()
        acc = acc.merge(da_merged, on=["REPORT_YEAR", "PERIOD_LABEL"], how="left")
    else:
        acc["da_value"] = np.nan

    # Parse período
    acc["_parsed"] = acc["PERIOD_LABEL"].apply(_parse_period)
    acc["_year"] = acc["_parsed"].apply(lambda x: x[0])
    acc["_quarter"] = acc["_parsed"].apply(lambda x: x[1])

    # Indexar por (year, quarter) para lookup rápido
    acc = acc.set_index(["_year", "_quarter"])

    # Coletar todos os períodos na ordem cronológica
    all_periods = sorted(acc.index.unique().tolist())
    period_labels = {}
    for yr, q in all_periods:
        lbl = acc.loc[(yr, q), "PERIOD_LABEL"]
        if isinstance(lbl, pd.Series):
            lbl = lbl.iloc[0]
        period_labels[(yr, q)] = lbl

    # Coletar trimestres standalone (excluindo anuais q=99)
    quarterly_keys = sorted([k for k in all_periods if k[1] != 99])

    def _get_val(year: int, quarter: int, col: str) -> float:
        """Busca valor de uma conta num período específico."""
        try:
            row = acc.loc[(year, quarter)]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            v = row.get(col, np.nan)
            return float(v) if pd.notna(v) else np.nan
        except (KeyError, IndexError):
            return np.nan

    def _trailing_4q(year: int, quarter: int, col: str) -> float:
        """LTM via soma dos últimos 4 trimestres standalone.

        Para período anual (q=99): usa o valor anual direto.
        Para trimestre: encontra os 4 trimestres anteriores (inclusive este) e soma.
        """
        if quarter == 99:
            return _get_val(year, 99, col)

        # Encontrar posição deste trimestre na lista de quarterly_keys
        try:
            idx = quarterly_keys.index((year, quarter))
        except ValueError:
            return np.nan

        if idx < 3:
            # Não temos 4 trimestres para trás
            return np.nan

        total = 0.0
        for i in range(4):
            yr_i, q_i = quarterly_keys[idx - i]
            v = _get_val(yr_i, q_i, col)
            if np.isnan(v):
                return np.nan
            total += v
        return total

    def safe_div(num: float, den: float) -> float:
        if np.isnan(num) or np.isnan(den) or den == 0:
            return np.nan
        return num / den

    # ── Calcular KPIs para cada período ──────────────────────────────────
    def _compute_period(yr: int, q: int) -> dict:
        """Retorna dict {kpi_id: value} para um período."""
        def flow(col: str) -> float:
            return _trailing_4q(yr, q, col)

        def stock(col: str) -> float:
            return _get_val(yr, q, col)

        receita   = flow("Receita")
        res_bruto = flow("Res_Bruto")
        ebit      = flow("EBIT")
        lucro     = flow("Lucro_Liq")
        fco       = flow("FCO")
        fci       = flow("FCI")

        pl        = stock("PL")
        at        = stock("Ativo_Total")
        pass_tot  = stock("Passivo_Total")
        pc        = stock("PC")
        pnc       = stock("PNC")
        ac        = stock("AC")
        caixa     = stock("Caixa")

        da = _trailing_4q(yr, q, "da_value")
        ebitda = (ebit + da) if not (np.isnan(ebit) or np.isnan(da)) else np.nan
        div_liq = (pnc - caixa) if not (np.isnan(pnc) or np.isnan(caixa)) else np.nan

        return {
            "MG_BRUTA":   safe_div(res_bruto, receita),
            "MG_EBITDA":  safe_div(ebitda, receita),
            "MG_EBIT":    safe_div(ebit, receita),
            "MG_LIQ":     safe_div(lucro, receita),
            "ROE":        safe_div(lucro, pl),
            "ROA":        safe_div(lucro, at),
            "ROIC":       np.nan,
            "LIQ_CORR":   safe_div(ac, pc),
            "LIQ_SECA":   safe_div(ac, pc),
            "LIQ_IMED":   safe_div(caixa, pc),
            "DIV_EBITDA": safe_div(div_liq, ebitda),
            "PL_PASS":    safe_div(pl, pass_tot),
            "PC_PASS":    safe_div(pc, pass_tot),
            "FCO_REC":    safe_div(fco, receita),
            "FCL_REC":    safe_div(fco + fci if not (np.isnan(fco) or np.isnan(fci)) else np.nan,
                                   receita),
            "CAPEX_REC":  safe_div(abs(fci) if not np.isnan(fci) else np.nan, receita),
            "CRESC_REC":  np.nan,  # calculado depois
            "CRESC_LUC":  np.nan,  # calculado depois
            "CAGR_REC":   np.nan,
            "EV_EBITDA":  np.nan,
            "PL_PRECO":   np.nan,
            "DY":         np.nan,
        }

    # Calcular para todos os períodos
    period_kpis: dict[tuple[int, int], dict] = {}
    for yr, q in all_periods:
        period_kpis[(yr, q)] = _compute_period(yr, q)

    # Crescimento YoY LTM (comparar LTM atual com LTM do mesmo período 1 ano atrás)
    for yr, q in all_periods:
        rec_c = _trailing_4q(yr, q, "Receita")
        luc_c = _trailing_4q(yr, q, "Lucro_Liq")

        if q == 99:
            prev_key = (yr - 1, 99)
        else:
            prev_key = (yr - 1, q)

        rec_p = _trailing_4q(*prev_key, "Receita") if prev_key[0] > 0 else np.nan
        luc_p = _trailing_4q(*prev_key, "Lucro_Liq") if prev_key[0] > 0 else np.nan

        if not np.isnan(rec_c) and not np.isnan(rec_p) and rec_p != 0:
            period_kpis[(yr, q)]["CRESC_REC"] = rec_c / rec_p - 1
        if not np.isnan(luc_c) and not np.isnan(luc_p) and luc_p != 0:
            period_kpis[(yr, q)]["CRESC_LUC"] = luc_c / luc_p - 1

    # ── Montar DataFrame de saída ─────────────────────────────────────────
    # Excluir Q4 do output — é redundante com o período anual
    # (LTM at Q4 = Annual para flow; stock Q4 = stock Annual)
    output_periods = [k for k in all_periods if not (k[1] == 4)]

    # Podar trimestres iniciais onde todos os KPIs de fluxo são NaN
    # (LTM não computável por falta de 4 trimestres anteriores)
    _flow_kpi_ids = {"MG_BRUTA", "MG_EBITDA", "MG_EBIT", "MG_LIQ",
                     "ROE", "ROA", "FCO_REC", "FCL_REC", "CAPEX_REC"}

    def _has_valid_flow(yr: int, q: int) -> bool:
        kpis = period_kpis.get((yr, q), {})
        return any(not np.isnan(kpis.get(k, np.nan)) for k in _flow_kpi_ids)

    trimmed: list[tuple[int, int]] = []
    started = False
    for yr, q in output_periods:
        if q == 99 or started or _has_valid_flow(yr, q):
            trimmed.append((yr, q))
            if q != 99:
                started = True
    output_periods = trimmed

    ordered_labels = [period_labels[k] for k in output_periods]

    rows = []
    for kpi_id, kpi_nome, formula, categoria, is_placeholder in _KPI_CATALOG:
        row: dict = {
            "CATEGORIA":        categoria,
            "KPI_ID":           kpi_id,
            "KPI_NOME":         kpi_nome,
            "FORMULA":          formula,
            "IS_PLACEHOLDER":   is_placeholder,
            "FORMAT_TYPE":      "pct" if kpi_id in _PCTS else "ratio",
            "HIGHER_IS_BETTER": kpi_id in _HIGHER_IS_BETTER,
            "UNIDADE":          "%" if kpi_id in _PCTS else "x",
        }
        for (yr, q), lbl in zip(output_periods, ordered_labels):
            v = period_kpis[(yr, q)].get(kpi_id, np.nan)
            row[lbl] = round(float(v), 6) if pd.notna(v) and not np.isinf(v) else None

        # Delta YoY: último período vs mesmo período do ano anterior
        if len(output_periods) >= 2:
            last_yr, last_q = output_periods[-1]
            prev_key = (last_yr - 1, last_q)
            last_lbl = ordered_labels[-1]
            prev_lbl = period_labels.get(prev_key)

            v_last = row.get(last_lbl)
            v_prev = row.get(prev_lbl) if prev_lbl else None

            if v_last is not None and v_prev is not None and v_prev != 0:
                delta = v_last - v_prev
                row["DELTA_YOY"]     = round(delta, 6)
                row["DELTA_YOY_PCT"] = round(delta / abs(v_prev), 6)
            else:
                row["DELTA_YOY"] = None
                row["DELTA_YOY_PCT"] = None
        else:
            row["DELTA_YOY"] = None
            row["DELTA_YOY_PCT"] = None

        rows.append(row)

    return pd.DataFrame(rows)


def format_kpi_value(value, format_type: str) -> str:
    """Formata um valor de KPI para exibição legível."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    if format_type == "pct":
        return f"{value * 100:.1f}%"
    return f"{value:.2f}x"
