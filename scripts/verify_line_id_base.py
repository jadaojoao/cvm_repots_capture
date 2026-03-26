"""Verify LINE_ID_BASE implementation in wide-format workbook."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_XLS_FILE = REPO_ROOT / "output" / "reports" / "PETROBRAS_financials.xlsx"
LEGACY_XLS_FILE = REPO_ROOT / "output" / "PETROBRAS_financials.xlsx"


def resolve_xlsx_path(xlsx_arg: Optional[str]) -> Path:
    if xlsx_arg:
        candidate = Path(xlsx_arg)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Arquivo informado em --xlsx nao encontrado: {candidate}")

    if DEFAULT_XLS_FILE.exists():
        return DEFAULT_XLS_FILE
    if LEGACY_XLS_FILE.exists():
        return LEGACY_XLS_FILE

    raise FileNotFoundError(
        "Nao foi encontrado arquivo padrao. Esperado em "
        f"{DEFAULT_XLS_FILE} (ou legado {LEGACY_XLS_FILE})."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify LINE_ID_BASE implementation")
    parser.add_argument(
        "--xlsx",
        help="Caminho do arquivo XLSX de saida (padrao: output/reports/PETROBRAS_financials.xlsx)",
    )
    args = parser.parse_args()
    xls_file = resolve_xlsx_path(args.xlsx)

    print("=" * 80)
    print("VERIFICATION: LINE_ID_BASE IMPLEMENTATION")
    print("=" * 80)
    print(f"Arquivo analisado: {xls_file}")

    xls = pd.ExcelFile(xls_file)

    print("\n1. SHEETS AVAILABLE")
    print("-" * 80)
    print(f"Sheets: {xls.sheet_names}")

    print("\n2. BPA STRUCTURE VERIFICATION")
    print("-" * 80)
    bpa = pd.read_excel(xls_file, sheet_name="BPA", header=2)
    print(f"Total rows: {len(bpa)}")
    print(f"Columns (first 15): {list(bpa.columns[:15])}")
    print("\nFirst 3 rows:")
    print(bpa[["LINE_ID_BASE", "CD_CONTA", "DS_CONTA", "DS_CONTA_norm"]].head(3))

    print("\n3. WIDE FORMAT CHECK")
    print("-" * 80)
    line_id_counts = bpa["LINE_ID_BASE"].value_counts()
    dups = line_id_counts[line_id_counts > 1]
    if len(dups) == 0:
        print(f"OK - all {len(bpa)} LINE_ID_BASE values are unique")
    else:
        print(f"FAIL - found {len(dups)} duplicate LINE_ID_BASE values")
        for lid, count in dups.head(3).items():
            print(f"  {lid}: {count} rows")

    print("\n4. PERIOD COLUMNS")
    print("-" * 80)
    period_cols = [c for c in bpa.columns if c not in ["LINE_ID_BASE", "CD_CONTA", "DS_CONTA", "DS_CONTA_norm", "QA_CONFLICT"]]
    print(f"Total period columns: {len(period_cols)}")
    print(f"Period range: {period_cols[0] if period_cols else 'N/A'} to {period_cols[-1] if period_cols else 'N/A'}")
    print(f"Sample: {period_cols[:10] if len(period_cols) >= 10 else period_cols}")

    print("\n5. DS_CONTA_NORM")
    print("-" * 80)
    if "DS_CONTA_norm" in bpa.columns:
        print("OK - DS_CONTA_norm is present")
        print("\nSamples:")
        for _, row in bpa[["DS_CONTA", "DS_CONTA_norm"]].head(3).iterrows():
            print(f"  '{row['DS_CONTA']}' -> '{row['DS_CONTA_norm']}'")
    else:
        print("FAIL - DS_CONTA_norm is missing")

    print("\n6. QA_LOG REVIEW")
    print("-" * 80)
    if "QA_LOG" in xls.sheet_names:
        qa_log = pd.read_excel(xls_file, sheet_name="QA_LOG")
        print(f"Total QA entries: {len(qa_log)}")
        print("\nBy type:")
        for qtype in qa_log["type"].unique():
            count = len(qa_log[qa_log["type"] == qtype])
            print(f"  {qtype}: {count}")
    else:
        print("No QA_LOG sheet")

    if "QA_LOG" in xls.sheet_names:
        qa_log = pd.read_excel(xls_file, sheet_name="QA_LOG")
        version_dedups = qa_log[qa_log["type"] == "VERSION_DEDUPLICATION"]
        if len(version_dedups) > 0:
            print(f"\nOK - VERSION_DEDUPLICATION working in {len(version_dedups)} sheet(s)")
            for _, row in version_dedups.iterrows():
                print(f"  {row['statement']}: removed {row['removed_count']} versions")
        else:
            print("\nWARN - no VERSION_DEDUPLICATION entries found")

    print("\n7. QA_ERRORS")
    print("-" * 80)
    if "QA_Errors" in xls.sheet_names:
        qa_err = pd.read_excel(xls_file, sheet_name="QA_Errors")
        print(f"FAIL - {len(qa_err)} validation errors found")
        for idx, row in qa_err.head(3).iterrows():
            print(f"\n  Error #{idx + 1}:")
            print(f"    Statement: {row['statement']}")
            print(f"    LINE_ID_BASE: {row.get('line_id_base', 'N/A')}")
            print(f"    Description: {str(row.get('description', ''))[:80]}")
    else:
        print("OK - no QA_Errors sheet")

    print("\n8. SAMPLE DATA (Account #1)")
    print("-" * 80)
    sample = bpa.iloc[0]
    print(f"LINE_ID_BASE: {sample['LINE_ID_BASE']}")
    print(f"CD_CONTA: {sample['CD_CONTA']}")
    print(f"DS_CONTA: {sample['DS_CONTA']}")
    non_null_periods = {col: sample[col] for col in period_cols if pd.notna(sample[col])}
    print(f"Non-null periods: {len(non_null_periods)}")
    if len(non_null_periods) > 0:
        print(f"Sample values: {dict(list(non_null_periods.items())[:5])}")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
