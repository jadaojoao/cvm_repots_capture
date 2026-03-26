"""Minimal smoke validation for the project setup."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import List, Set


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def check_main_help(errors: List[str]) -> None:
    cmd = [sys.executable, str(REPO_ROOT / "main.py"), "--help"]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("main.py --help falhou.")
        return
    print("[OK] main.py --help")


def check_required_paths(errors: List[str]) -> None:
    required_paths = [
        REPO_ROOT / "data" / "metadata" / "companhias_abertas_cvm_766_v2.xlsx",
        REPO_ROOT / "data" / "metadata" / "matriz_kpis_setores_cvm_agressiva_v3_open_data.xlsx",
        REPO_ROOT / "data" / "db" / "cvm_financials.db",
        REPO_ROOT / "output" / "reports" / "base_analitica_dashboard_preenchida.xlsx",
    ]

    for path in required_paths:
        if path.exists():
            print(f"[OK] {path}")
        else:
            errors.append(f"Arquivo obrigatorio ausente: {path}")


def check_database(errors: List[str]) -> None:
    db_path = REPO_ROOT / "data" / "db" / "cvm_financials.db"
    if not db_path.exists():
        errors.append(f"Banco SQLite ausente: {db_path}")
        return

    required_tables = {"financial_reports", "qa_logs"}
    found_tables: Set[str] = set()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('financial_reports', 'qa_logs')"
            ).fetchall()
        found_tables = {row[0] for row in rows}
    except sqlite3.Error as exc:
        errors.append(f"Falha ao abrir SQLite: {exc}")
        return

    missing = required_tables - found_tables
    if missing:
        errors.append(f"Tabelas ausentes no SQLite: {sorted(missing)}")
    else:
        print("[OK] SQLite com tabelas financial_reports e qa_logs")


def run_compileall(errors: List[str]) -> None:
    cmd = [sys.executable, "-m", "compileall", "src", "dashboard", "scripts"]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("compileall falhou em src/dashboard/scripts.")
    else:
        print("[OK] compileall em src/dashboard/scripts")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validador smoke minimo do projeto")
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Pula etapa de compileall",
    )
    args = parser.parse_args()

    errors: List[str] = []

    print("== Smoke validation ==")
    check_main_help(errors)
    check_required_paths(errors)
    check_database(errors)
    if not args.skip_compile:
        run_compileall(errors)

    if errors:
        print("\n[FAIL] Validacao concluiu com erros:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("\n[OK] Smoke validation concluida sem erros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
