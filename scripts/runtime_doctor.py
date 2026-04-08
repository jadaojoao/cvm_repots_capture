# -*- coding: utf-8 -*-
"""
Diagnostico rapido do ambiente operacional do projeto.

Uso:
    python scripts/runtime_doctor.py
    python scripts/runtime_doctor.py --require-db --table financial_reports --table companies
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostico de runtime do CVM Reports Capture")
    parser.add_argument("--require-db", action="store_true", help="Falha se o banco nao estiver acessivel")
    parser.add_argument("--table", action="append", default=[], help="Tabela obrigatoria (pode repetir)")
    parser.add_argument("--require-canonical", action="store_true", help="Valida arquivo canonical_accounts.csv")
    parser.add_argument("--database-url", help="Override explicito de DATABASE_URL para validar PostgreSQL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    settings = build_settings(project_root=ROOT)
    report = collect_startup_report(
        settings,
        require_database=bool(args.require_db),
        required_tables=tuple(args.table),
        require_canonical_accounts=bool(args.require_canonical),
    )
    print(format_startup_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
