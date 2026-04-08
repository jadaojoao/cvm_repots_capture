# -*- coding: utf-8 -*-
"""
Smoke de banco para validar prontidao de SQLite/PostgreSQL.

Valida:
  - conexao ao banco configurado
  - existencia de tabelas obrigatorias
  - leitura simples de contagem
  - escrita temporaria opcional
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import build_engine
from src.settings import build_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke de banco para SQLite/PostgreSQL")
    parser.add_argument("--table", action="append", default=["financial_reports", "companies"], help="Tabela obrigatoria")
    parser.add_argument("--write-check", action="store_true", help="Executa escrita temporaria")
    parser.add_argument("--database-url", help="Override explicito de DATABASE_URL para validar PostgreSQL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    settings = build_settings(project_root=ROOT)
    engine = build_engine(settings)
    inspector = inspect(engine)

    print(f"dialect={engine.dialect.name}")
    missing_tables = [table_name for table_name in args.table if not inspector.has_table(table_name)]
    if missing_tables:
        print("missing_tables=" + ",".join(missing_tables))
        return 1

    with engine.begin() as conn:
        for table_name in args.table:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"{table_name}_count={int(count or 0)}")

        if args.write_check:
            conn.execute(text("CREATE TEMP TABLE codex_db_smoke (id INTEGER PRIMARY KEY, note TEXT)"))
            conn.execute(text("INSERT INTO codex_db_smoke (id, note) VALUES (1, 'ok')"))
            note = conn.execute(text("SELECT note FROM codex_db_smoke WHERE id = 1")).scalar()
            print(f"write_check_note={note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
