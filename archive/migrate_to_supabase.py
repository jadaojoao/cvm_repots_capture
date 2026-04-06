# -*- coding: utf-8 -*-
"""
migrate_to_supabase.py — Migração one-time: SQLite local → Supabase PostgreSQL.

Uso:
    # Migração completa
    DATABASE_URL="postgresql://postgres.[REF]:[PWD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres" \
        python scripts/migrate_to_supabase.py

    # Dry-run (conta rows sem migrar)
    DATABASE_URL="..." python scripts/migrate_to_supabase.py --dry-run

Pré-condições:
    - .venv ativo com sqlalchemy, psycopg2-binary e pandas instalados
    - DATABASE_URL deve usar porta 6543 (Transaction Pooler do Supabase)
    - SQLite local em data/db/cvm_financials.db deve existir

Comportamento:
    - Idempotente: TRUNCATE + bulk insert (safe para rodar múltiplas vezes)
    - Chunks de 5.000 rows para não estourar memória
    - Remove coluna 'id' antes de inserir (PostgreSQL gera SERIAL próprio)
    - Verifica contagem de rows ao final
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT / "data" / "db" / "cvm_financials.db"
SQLITE_URL  = f"sqlite:///{SQLITE_PATH}"
CHUNK_SIZE  = 5_000
TABLES      = ["financial_reports", "qa_logs"]


def _build_pg_engine(url: str):
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def _count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()


def run_migration(pg_url: str, dry_run: bool = False) -> None:
    if not SQLITE_PATH.exists():
        print(f"[ERRO] SQLite não encontrado: {SQLITE_PATH}")
        sys.exit(1)

    src = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    dst = _build_pg_engine(pg_url)

    print(f"Origem : {SQLITE_URL}")
    print(f"Destino: {pg_url[:60]}...")
    print()

    for table in TABLES:
        # Conta rows na origem
        src_count = _count(src, table)
        print(f"[{table}] origem: {src_count:,} rows")

        if dry_run:
            print(f"[{table}] dry-run — pulando.\n")
            continue

        if src_count == 0:
            print(f"[{table}] vazio — pulando.\n")
            continue

        # TRUNCATE destino (idempotente)
        print(f"[{table}] truncando destino...")
        with dst.begin() as conn:
            conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

        # Lê em chunks e insere
        inserted = 0
        offset = 0
        with src.connect() as src_conn:
            while True:
                chunk = pd.read_sql(
                    text(f'SELECT * FROM "{table}" LIMIT :lim OFFSET :off'),
                    src_conn,
                    params={"lim": CHUNK_SIZE, "off": offset},
                )
                if chunk.empty:
                    break

                # Remove coluna 'id' — PostgreSQL usa SERIAL e gera o próprio
                chunk = chunk.drop(columns=["id"], errors="ignore")

                with dst.begin() as dst_conn:
                    chunk.to_sql(table, dst_conn, if_exists="append", index=False, method="multi")

                inserted += len(chunk)
                offset   += CHUNK_SIZE
                print(f"[{table}]   inseridos {inserted:,}/{src_count:,}...", end="\r")

        print()  # nova linha após o \r

        # Verifica contagem
        dst_count = _count(dst, table)
        status = "✅" if dst_count == src_count else "⚠️ DIVERGÊNCIA"
        print(f"[{table}] destino: {dst_count:,} rows  {status}\n")

    print("Migração concluída." if not dry_run else "Dry-run finalizado.")


def main():
    parser = argparse.ArgumentParser(description="Migra SQLite → Supabase PostgreSQL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas conta rows, não migra dados")
    args = parser.parse_args()

    pg_url = os.getenv("DATABASE_URL", "")
    if not pg_url:
        print("[ERRO] Defina DATABASE_URL com a URI do Supabase antes de rodar este script.")
        print("  Exemplo (bash):")
        print('  export DATABASE_URL="postgresql://postgres.[REF]:[PWD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"')
        print("  Exemplo (PowerShell):")
        print('  $env:DATABASE_URL = "postgresql://..."')
        sys.exit(1)

    if not pg_url.startswith("postgresql"):
        print(f"[AVISO] DATABASE_URL não parece PostgreSQL: {pg_url[:40]}")

    run_migration(pg_url, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
