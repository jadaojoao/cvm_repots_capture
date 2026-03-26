"""Verify consolidation and disambiguation results."""

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
    parser = argparse.ArgumentParser(description="Verify consolidation and disambiguation results")
    parser.add_argument(
        "--xlsx",
        help="Caminho do arquivo XLSX de saida (padrao: output/reports/PETROBRAS_financials.xlsx)",
    )
    args = parser.parse_args()
    xls_file = resolve_xlsx_path(args.xlsx)

    print("=" * 80)
    print("VERIFICATION: CONSOLIDATION & DISAMBIGUATION")
    print("=" * 80)
    print(f"Arquivo analisado: {xls_file}")

    xls = pd.ExcelFile(xls_file)

    print("\n1. LINE_ID UNIQUENESS CHECK")
    print("-" * 80)
    for sheet in ["BPA", "BPP", "DRE", "DFC"]:
        df = pd.read_excel(xls_file, sheet_name=sheet, header=2)

        if "LINE_ID" in df.columns:
            id_col = "LINE_ID"
        elif "LINE_ID_BASE" in df.columns:
            id_col = "LINE_ID_BASE"
        else:
            print(f"{sheet}: No ID column found!")
            continue

        id_counts = df[id_col].value_counts()
        dups = id_counts[id_counts > 1]

        if len(dups) == 0:
            print(f"{sheet}: OK - all {len(df)} {id_col}s are unique")
        else:
            print(f"{sheet}: FAIL - {len(dups)} duplicate {id_col}s")
            for lid, count in dups.head(5).items():
                print(f"  {lid}: {count} rows")

    print("\n2. QA_LOG - CONSOLIDATION & DISAMBIGUATION")
    print("-" * 80)
    qa_log = pd.read_excel(xls_file, sheet_name="QA_LOG")

    type_counts = qa_log["type"].value_counts()
    print(f"Total QA entries: {len(qa_log)}\n")

    for qtype in ["VERSION_DEDUPLICATION", "CONSOLIDATED", "DISAMBIGUATED"]:
        if qtype in type_counts.index:
            count = type_counts[qtype]
            print(f"{qtype}: {count}")

            qtype_df = qa_log[qa_log["type"] == qtype]
            if qtype == "VERSION_DEDUPLICATION":
                for _, row in qtype_df.iterrows():
                    print(f"  {row['statement']}: removed {row.get('removed_count', 0)} versions")
            elif qtype == "CONSOLIDATED":
                for _, row in qtype_df.head(3).iterrows():
                    print(f"  {row['statement']}/{row['line_id_base']}: merged {row.get('merged_rows', 0)} rows")
            elif qtype == "DISAMBIGUATED":
                for _, row in qtype_df.head(3).iterrows():
                    print(f"  {row['statement']}/{row['line_id_base']}: discriminator={row.get('discriminator', 'N/A')}")
        else:
            print(f"{qtype}: 0")

    print("\n3. QA_CONFLICT FLAG")
    print("-" * 80)
    for sheet in ["BPA", "BPP", "DRE", "DFC"]:
        df = pd.read_excel(xls_file, sheet_name=sheet, header=2)
        if "QA_CONFLICT" in df.columns:
            conflict_count = df["QA_CONFLICT"].sum()
            print(f"{sheet}: {conflict_count} rows with QA_CONFLICT=True")

            if conflict_count > 0:
                conflicts = df[df["QA_CONFLICT"] == True]
                for _, row in conflicts.head(3).iterrows():
                    id_col = "LINE_ID" if "LINE_ID" in df.columns else "LINE_ID_BASE"
                    print(f"  {row[id_col]}: {row['DS_CONTA']}")
        else:
            print(f"{sheet}: No QA_CONFLICT column")

    print("\n4. DISAMBIGUATED LINE_IDs (with | suffix)")
    print("-" * 80)
    for sheet in ["BPA", "BPP", "DRE", "DFC"]:
        df = pd.read_excel(xls_file, sheet_name=sheet, header=2)

        if "LINE_ID" in df.columns:
            suffixed = df[df["LINE_ID"].astype(str).str.contains("\\|", na=False)]
            print(f"{sheet}: {len(suffixed)} disambiguated rows (LINE_ID contains |)")

            if len(suffixed) > 0:
                for _, row in suffixed.head(3).iterrows():
                    print(f"  {row['LINE_ID']}: {row['DS_CONTA'][:50]}")
        else:
            print(f"{sheet}: Uses LINE_ID_BASE (no disambiguation)")

    print("\n5. QA_ERRORS")
    print("-" * 80)
    if "QA_Errors" in xls.sheet_names:
        qa_err = pd.read_excel(xls_file, sheet_name="QA_Errors")
        print(f"FAIL: {len(qa_err)} validation errors")
        for _, row in qa_err.head(5).iterrows():
            print(f"  {row['statement']}: {str(row.get('description', ''))[:80]}")
    else:
        print("OK: No QA_Errors sheet - validation passed")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
