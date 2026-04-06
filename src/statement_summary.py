from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.utils import normalize_account_name

_BASE_COLS = {"CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"}
_BLOCK_ORDER = ["DRE", "BPA", "BPP", "DFC"]
_BLOCK_TITLES = {
    "DRE": "DRE — Resumo Condensado",
    "BPA": "BPA — Resumo Condensado",
    "BPP": "BPP — Resumo Condensado",
    "DFC": "DFC — Resumo Condensado",
}
_SUBTOTAL_CODES = {
    "DRE": {"3.01", "3.03", "3.05", "3.07", "3.11"},
    "BPA": {"1", "1.01", "1.02"},
    "BPP": {"2", "2.01", "2.02", "2.03"},
    "DFC": {"6.01", "6.02", "6.03"},
}
_SUMMARY_CODES = {
    "DRE": ["3.01", "3.02", "3.03", "3.04", "3.05", "3.06", "3.07", "3.08", "3.11"],
    "BPA": ["1", "1.01", "1.01.01", "1.02"],
    "BPP": ["2", "2.01", "2.01.04", "2.02", "2.02.01", "2.03", "2.03.01", "2.03.04"],
    "DFC": ["6.01", "6.02", "6.03", "6.04", "6.05"],
}
_EXPAND_DIRECT_CHILDREN = {
    "BPA": {"1.01", "1.02"},
    "BPP": {"2.01", "2.02", "2.03"},
    "DFC": {"6.01", "6.02", "6.03"},
}
_DFC_ALWAYS_KEEP_CHILD_CODES = {"6.01.01", "6.01.02"}
_DFC_OTHERS_LABELS = {
    "6.01": "Outros Operacionais",
    "6.02": "Outros de Investimento",
    "6.03": "Outros de Financiamento",
}
_DFC_DA_CODE = "6.01.01.DA"
_DFC_DA_LABEL = "Depreciacao e Amortizacao"
_DFC_MATERIALITY_THRESHOLD = 0.10
_DRE_REQUIRED_CODES = {"3.01", "3.03", "3.05", "3.07", "3.11"}
_DFC_CASH_VARIATION_LABELS = {
    "aumento (reducao) de caixa e equivalentes",
    "aumento (reducao) de caixa e equivalentes de caixa",
    "aumento (diminuicao) liquido no caixa e equivalentes",
    "aumento liquido em caixa e equivalentes de caixa",
    "variacao liquida de caixa e equivalentes",
    "variacao liquida de caixa e equivalentes de caixa",
}
_DFC_CASH_FINAL_LABELS = {
    "caixa e equivalente a caixa no final do periodo",
    "caixa e equivalentes de caixa no final do periodo",
    "caixa e equivalentes de caixa no final do trimestre",
    "caixa e equivalentes de caixa no fim do periodo",
    "caixa e equivalentes de caixa no fim do trimestre",
    "saldo final de caixa",
    "saldo final de caixa e equivalentes",
    "saldo final de caixa e equivalentes de caixa",
}


@dataclass(frozen=True)
class SummaryBlock:
    stmt_type: str
    title: str
    rows: pd.DataFrame


def build_general_summary_blocks(statements: dict[str, pd.DataFrame]) -> list[SummaryBlock]:
    blocks: list[SummaryBlock] = []
    for stmt_type in _BLOCK_ORDER:
        block = build_statement_summary(stmt_type, statements.get(stmt_type))
        if block is not None:
            blocks.append(block)
    return blocks


def build_statement_summary(stmt_type: str, df: pd.DataFrame | None) -> SummaryBlock | None:
    if stmt_type not in _SUMMARY_CODES or df is None or df.empty:
        return None

    prepared = _prepare_statement(df)
    if prepared.empty:
        return None

    period_cols = _period_columns(df)
    rows: list[pd.Series] = []
    seen_codes: set[str] = set()

    for code in _SUMMARY_CODES[stmt_type]:
        row = _pick_row(prepared, stmt_type, code)
        if row is None:
            continue

        actual_code = str(row["CD_CONTA"])
        if actual_code in seen_codes:
            continue

        rows.append(_format_row(row, stmt_type, period_cols))
        seen_codes.add(actual_code)

        if code in _EXPAND_DIRECT_CHILDREN.get(stmt_type, set()):
            if stmt_type == "DFC":
                kept_children, grouped_other = _select_dfc_children(prepared, code, row, period_cols)
                for child_row in kept_children:
                    child_code = str(child_row["CD_CONTA"])
                    if child_code in seen_codes:
                        continue
                    rows.append(_format_row(child_row, stmt_type, period_cols))
                    seen_codes.add(child_code)

                if code == "6.01":
                    da_row = _build_dfc_da_summary_row(prepared, period_cols)
                    if da_row is not None:
                        da_code = str(da_row["CD_CONTA"])
                        if da_code not in seen_codes:
                            rows.append(da_row)
                            seen_codes.add(da_code)

                if grouped_other is not None:
                    other_code = str(grouped_other["CD_CONTA"])
                    if other_code not in seen_codes:
                        rows.append(grouped_other)
                        seen_codes.add(other_code)
            else:
                for child_row in _iter_direct_children(prepared, code):
                    child_code = str(child_row["CD_CONTA"])
                    if child_code in seen_codes:
                        continue
                    rows.append(_format_row(child_row, stmt_type, period_cols))
                    seen_codes.add(child_code)

    if stmt_type == "DFC":
        for label_group in (_DFC_CASH_VARIATION_LABELS, _DFC_CASH_FINAL_LABELS):
            row = _pick_unique_label_match(prepared, label_group)
            if row is None:
                continue
            actual_code = str(row["CD_CONTA"])
            if actual_code in seen_codes:
                continue
            rows.append(_format_row(row, stmt_type, period_cols))
            seen_codes.add(actual_code)

    if not rows:
        return None

    summary_df = pd.DataFrame(rows)
    return SummaryBlock(
        stmt_type=stmt_type,
        title=_BLOCK_TITLES[stmt_type],
        rows=summary_df.reset_index(drop=True),
    )


def _prepare_statement(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy().reset_index(drop=True)
    prepared["CD_CONTA"] = prepared["CD_CONTA"].apply(_normalize_code)
    prepared = prepared[prepared["CD_CONTA"].notna()].copy()
    if prepared.empty:
        return prepared

    prepared["LABEL"] = prepared.apply(_preferred_label, axis=1)
    prepared["_LABEL_NORM"] = prepared["LABEL"].apply(normalize_account_name)
    prepared["_DS_CONTA_NORM"] = prepared["DS_CONTA"].apply(normalize_account_name)
    prepared["_SEGMENT_COUNT"] = prepared["CD_CONTA"].str.count(r"\.") + 1
    prepared["_CODE_SORT"] = prepared["CD_CONTA"].apply(_code_sort_key)
    return prepared.reset_index(drop=True)


def _normalize_code(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _preferred_label(row: pd.Series) -> str:
    standard_name = str(row.get("STANDARD_NAME", "") or "").strip()
    if standard_name:
        return standard_name
    ds_conta = str(row.get("DS_CONTA", "") or "").strip()
    if ds_conta:
        return ds_conta
    return str(row.get("CD_CONTA", "") or "")


def _period_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if col not in _BASE_COLS]


def _code_sort_key(code: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(code).split("."))


def _pick_row(prepared: pd.DataFrame, stmt_type: str, code: str) -> pd.Series | None:
    exact = prepared[prepared["CD_CONTA"] == code]
    if not exact.empty:
        return exact.iloc[0]

    if stmt_type != "DRE" or code not in _DRE_REQUIRED_CODES:
        return None

    descendants = prepared[prepared["CD_CONTA"].str.startswith(f"{code}.")]
    if descendants.empty:
        return None

    min_depth = int(descendants["_SEGMENT_COUNT"].min())
    shallowest = descendants[descendants["_SEGMENT_COUNT"] == min_depth]
    if len(shallowest) != 1:
        return None
    return shallowest.iloc[0]


def _pick_unique_label_match(prepared: pd.DataFrame, labels: set[str]) -> pd.Series | None:
    matches = prepared[prepared["_LABEL_NORM"].isin(labels)]
    if len(matches) != 1:
        return None
    return matches.iloc[0]


def _iter_direct_children(prepared: pd.DataFrame, parent_code: str) -> list[pd.Series]:
    parent_depth = parent_code.count(".") + 1
    children = prepared[
        prepared["CD_CONTA"].str.startswith(f"{parent_code}.")
        & (prepared["_SEGMENT_COUNT"] == parent_depth + 1)
    ]
    if children.empty:
        return []
    children = children.sort_values("_CODE_SORT")
    return [row for _, row in children.iterrows()]


def _select_dfc_children(
    prepared: pd.DataFrame,
    parent_code: str,
    parent_row: pd.Series,
    period_cols: list[str],
) -> tuple[list[pd.Series], dict[str, object] | None]:
    kept: list[pd.Series] = []
    grouped: list[pd.Series] = []

    for child_row in _iter_direct_children(prepared, parent_code):
        child_code = str(child_row["CD_CONTA"])
        if (
            child_code in _DFC_ALWAYS_KEEP_CHILD_CODES
            or _is_dfc_da_candidate(child_row)
            or _is_material_vs_parent(child_row, parent_row, period_cols)
        ):
            kept.append(child_row)
        else:
            grouped.append(child_row)

    return kept, _build_grouped_other_row(parent_code, grouped, period_cols)


def _is_material_vs_parent(child_row: pd.Series, parent_row: pd.Series, period_cols: list[str]) -> bool:
    max_share = 0.0
    for period_col in period_cols:
        child_value = child_row.get(period_col)
        parent_value = parent_row.get(period_col)
        if pd.isna(child_value) or pd.isna(parent_value):
            continue
        parent_abs = abs(float(parent_value))
        if parent_abs <= 0:
            continue
        max_share = max(max_share, abs(float(child_value)) / parent_abs)
    return max_share >= _DFC_MATERIALITY_THRESHOLD


def _build_grouped_other_row(
    parent_code: str,
    grouped_rows: list[pd.Series],
    period_cols: list[str],
) -> dict[str, object] | None:
    if not grouped_rows:
        return None

    result: dict[str, object] = {
        "CD_CONTA": f"{parent_code}.OUTROS",
        "LABEL": _DFC_OTHERS_LABELS[parent_code],
        "IS_SUBTOTAL": False,
    }

    has_signal = False
    for period_col in period_cols:
        values = [row.get(period_col) for row in grouped_rows if pd.notna(row.get(period_col))]
        if not values:
            result[period_col] = None
            continue
        total = float(sum(float(value) for value in values))
        result[period_col] = total
        if total != 0:
            has_signal = True

    return result if has_signal else None


def _build_dfc_da_summary_row(prepared: pd.DataFrame, period_cols: list[str]) -> dict[str, object] | None:
    candidates = prepared[
        prepared["CD_CONTA"].str.startswith("6.01.01")
        & prepared.apply(_is_dfc_da_candidate, axis=1)
    ]
    if candidates.empty:
        return None

    candidates = candidates.sort_values(["_SEGMENT_COUNT", "_CODE_SORT"])
    shallowest_depth = int(candidates["_SEGMENT_COUNT"].min())
    shallowest = candidates[candidates["_SEGMENT_COUNT"] == shallowest_depth]
    if len(shallowest) == 1:
        return _format_row(shallowest.iloc[0], "DFC", period_cols)

    result: dict[str, object] = {
        "CD_CONTA": _DFC_DA_CODE,
        "LABEL": _DFC_DA_LABEL,
        "IS_SUBTOTAL": False,
    }

    has_signal = False
    for period_col in period_cols:
        values = [row.get(period_col) for _, row in candidates.iterrows() if pd.notna(row.get(period_col))]
        if not values:
            result[period_col] = None
            continue
        total = float(sum(float(value) for value in values))
        result[period_col] = total
        if total != 0:
            has_signal = True

    return result if has_signal else None


def _is_dfc_da_candidate(row: pd.Series) -> bool:
    return str(row.get("CD_CONTA", "")).startswith("6.01.01") and "depreci" in str(row.get("_DS_CONTA_NORM", ""))


def _format_row(row: pd.Series, stmt_type: str, period_cols: list[str]) -> dict[str, object]:
    summary_row: dict[str, object] = {
        "CD_CONTA": row["CD_CONTA"],
        "LABEL": row["LABEL"],
        "IS_SUBTOTAL": str(row["CD_CONTA"]) in _SUBTOTAL_CODES.get(stmt_type, set()),
    }
    for col in period_cols:
        summary_row[col] = row.get(col)
    return summary_row
