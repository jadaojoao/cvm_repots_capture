# -*- coding: utf-8 -*-
"""
Setup e otimizacao do banco de dados CVM.

Executa em ordem:
  1. Cria indices de performance em financial_reports e qa_logs
  2. Cria tabela companies
  3. Cria tabela company_refresh_status
  4. Cria tabela account_names e popula via canonical_accounts.csv
  5. Preenche STANDARD_NAME em financial_reports via account_names
  6. Remove registros orfaos em company_refresh_status
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import build_engine
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

INDEXES = [
    {
        "name": "idx_fr_year_period",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_fr_year_period ON financial_reports("REPORT_YEAR", "PERIOD_LABEL")',
        "desc": "heatmap da aba Mercado",
    },
    {
        "name": "idx_fr_cvm_year",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_fr_cvm_year ON financial_reports("CD_CVM", "REPORT_YEAR", "PERIOD_LABEL")',
        "desc": "consultas por empresa-ano",
    },
    {
        "name": "idx_qa_cvm",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_qa_cvm ON qa_logs("CD_CVM")',
        "desc": "limpeza de qa_logs por empresa",
    },
]


def _identity_pk(dialect: str) -> str:
    return "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "SERIAL PRIMARY KEY"


def _companies_ddl() -> str:
    return """
    CREATE TABLE IF NOT EXISTS companies (
        cd_cvm          INTEGER PRIMARY KEY,
        company_name    TEXT NOT NULL,
        nome_comercial  TEXT,
        cnpj            TEXT,
        setor_cvm       TEXT,
        setor_analitico TEXT,
        company_type    TEXT NOT NULL DEFAULT 'comercial',
        ticker_b3       TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        updated_at      TEXT NOT NULL
    )
    """


def _account_names_ddl(dialect: str) -> str:
    pk = _identity_pk(dialect)
    return f"""
    CREATE TABLE IF NOT EXISTS account_names (
        id              {pk},
        statement_type  TEXT NOT NULL,
        cd_conta        TEXT NOT NULL,
        standard_name   TEXT NOT NULL,
        company_type    TEXT NOT NULL DEFAULT 'comercial',
        is_consolidated INTEGER NOT NULL DEFAULT 1,
        nivel           INTEGER,
        UNIQUE(statement_type, cd_conta, company_type, is_consolidated)
    )
    """


def step1_create_indexes(conn, dry_run: bool) -> None:
    log.info("=== Passo 1: Criando indices de performance ===")
    for idx in INDEXES:
        if dry_run:
            log.info("  [DRY-RUN] Criaria %s (%s)", idx["name"], idx["desc"])
            continue
        started_at = time.time()
        conn.execute(text(idx["sql"]))
        log.info("  OK %s em %.1fs (%s)", idx["name"], time.time() - started_at, idx["desc"])


def step2_create_companies_table(conn, dry_run: bool) -> None:
    log.info("=== Passo 2: Criando tabela companies ===")
    if dry_run:
        log.info("  [DRY-RUN] Criaria tabela companies + indices auxiliares")
        return

    conn.execute(text(_companies_ddl()))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_setor ON companies(setor_analitico)"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_companies_cnpj ON companies(cnpj) WHERE cnpj IS NOT NULL"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker_b3) WHERE ticker_b3 IS NOT NULL"))
    log.info("  OK tabela companies criada")
    log.info("  Execute scripts/setup_companies_table.py para popular os metadados")


def step3_create_company_refresh_status(conn, dry_run: bool) -> None:
    log.info("=== Passo 3: Criando tabela company_refresh_status ===")
    if dry_run:
        log.info("  [DRY-RUN] Criaria tabela company_refresh_status + indice")
        return

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS company_refresh_status (
                cd_cvm             INTEGER PRIMARY KEY,
                company_name       TEXT,
                source_scope       TEXT NOT NULL DEFAULT 'local',
                last_attempt_at    TEXT,
                last_success_at    TEXT,
                last_status        TEXT,
                last_error         TEXT,
                last_start_year    INTEGER,
                last_end_year      INTEGER,
                last_rows_inserted INTEGER,
                updated_at         TEXT
            )
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crs_status ON company_refresh_status(last_status)"))
    log.info("  OK tabela company_refresh_status criada")


def step4_create_account_names(conn, dry_run: bool, settings, dialect: str) -> None:
    log.info("=== Passo 4: Criando tabela account_names e populando ===")
    canon_path = settings.paths.canonical_accounts_path
    if not canon_path.exists():
        log.error("  Arquivo nao encontrado: %s", canon_path)
        return

    df = pd.read_csv(canon_path, encoding="utf-8-sig")
    rename_map = {
        "CD_CONTA": "cd_conta",
        "STANDARD_NAME": "standard_name",
        "STATEMENT_TYPE": "statement_type",
        "EMPRESA_TIPO": "company_type",
        "NIVEL": "nivel",
        "IS_CONSOLIDADO": "is_consolidated",
    }
    df = df.rename(columns={key: value for key, value in rename_map.items() if key in df.columns})
    for column, default in [("company_type", "comercial"), ("is_consolidated", 1), ("nivel", None)]:
        if column not in df.columns:
            df[column] = default

    if df["is_consolidated"].dtype == object:
        df["is_consolidated"] = df["is_consolidated"].map(
            {"True": 1, "False": 0, True: 1, False: 0}
        ).fillna(1).astype(int)

    required = ["statement_type", "cd_conta", "standard_name", "company_type", "is_consolidated"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        log.error("  Colunas obrigatorias ausentes em canonical_accounts.csv: %s", missing)
        return

    payload = df[["statement_type", "cd_conta", "standard_name", "company_type", "is_consolidated", "nivel"]].copy()
    if dry_run:
        log.info("  [DRY-RUN] Criaria tabela account_names e processaria %s linhas", len(payload))
        return

    conn.execute(text(_account_names_ddl(dialect)))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_account_lookup ON account_names(statement_type, cd_conta)"))

    insert_sql = text(
        """
        INSERT INTO account_names
            (statement_type, cd_conta, standard_name, company_type, is_consolidated, nivel)
        VALUES
            (:statement_type, :cd_conta, :standard_name, :company_type, :is_consolidated, :nivel)
        ON CONFLICT(statement_type, cd_conta, company_type, is_consolidated) DO NOTHING
        """
    )

    inserted = 0
    for _, row in payload.iterrows():
        conn.execute(
            insert_sql,
            {
                "statement_type": row["statement_type"],
                "cd_conta": row["cd_conta"],
                "standard_name": row["standard_name"],
                "company_type": row["company_type"],
                "is_consolidated": int(row["is_consolidated"]) if row["is_consolidated"] is not None else 1,
                "nivel": int(row["nivel"]) if row["nivel"] is not None and str(row["nivel"]) != "nan" else None,
            },
        )
        inserted += 1
    log.info("  OK %s linhas processadas em account_names", inserted)


def step5_fill_standard_names(conn, dry_run: bool) -> None:
    log.info("=== Passo 5: Preenchendo STANDARD_NAME NULLs ===")
    try:
        count_account_names = conn.execute(text("SELECT COUNT(*) FROM account_names")).scalar()
    except Exception:
        log.warning("  Tabela account_names nao existe. Pulando passo 5.")
        return

    if int(count_account_names or 0) == 0:
        log.warning("  account_names esta vazia. Execute o passo 4 primeiro.")
        return

    null_before = conn.execute(
        text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
    ).scalar()
    log.info("  STANDARD_NAME NULLs antes: %s", f"{int(null_before or 0):,}")

    if int(null_before or 0) == 0:
        log.info("  Nada a fazer.")
        return

    if dry_run:
        log.info("  [DRY-RUN] Preencheria STANDARD_NAME via account_names e DS_CONTA")
        return

    started_at = time.time()
    conn.execute(
        text(
            """
            UPDATE financial_reports
            SET "STANDARD_NAME" = (
                SELECT an.standard_name
                FROM account_names an
                WHERE an.cd_conta = financial_reports."CD_CONTA"
                  AND an.statement_type = financial_reports."STATEMENT_TYPE"
                ORDER BY an.is_consolidated DESC
                LIMIT 1
            )
            WHERE "STANDARD_NAME" IS NULL
            """
        )
    )
    null_after_dict = conn.execute(
        text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
    ).scalar()
    filled_from_dict = int(null_before or 0) - int(null_after_dict or 0)
    log.info("  OK %s NULLs preenchidos via account_names em %.1fs", filled_from_dict, time.time() - started_at)

    if int(null_after_dict or 0) > 0:
        fallback_started_at = time.time()
        conn.execute(
            text(
                """
                UPDATE financial_reports
                SET "STANDARD_NAME" = "DS_CONTA"
                WHERE "STANDARD_NAME" IS NULL
                  AND "DS_CONTA" IS NOT NULL
                  AND TRIM("DS_CONTA") != ''
                """
            )
        )
        null_after_fallback = conn.execute(
            text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
        ).scalar()
        filled_from_ds = int(null_after_dict or 0) - int(null_after_fallback or 0)
        log.info("  OK %s NULLs preenchidos via DS_CONTA em %.1fs", filled_from_ds, time.time() - fallback_started_at)
        log.info("  Ainda NULL: %s", f"{int(null_after_fallback or 0):,}")


def step6_clean_orphan_refresh_status(conn, dry_run: bool) -> None:
    log.info("=== Passo 6: Limpando registros orfaos em company_refresh_status ===")
    try:
        orphan_count = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM company_refresh_status
                WHERE cd_cvm NOT IN (SELECT cd_cvm FROM companies)
                """
            )
        ).scalar()
    except Exception:
        log.warning("  Tabela company_refresh_status nao existe. Pulando passo 6.")
        return

    if int(orphan_count or 0) == 0:
        log.info("  Nada a fazer.")
        return

    if dry_run:
        log.info("  [DRY-RUN] Removeria %s registros orfaos", orphan_count)
        return

    conn.execute(
        text(
            """
            DELETE FROM company_refresh_status
            WHERE cd_cvm NOT IN (SELECT cd_cvm FROM companies)
            """
        )
    )
    log.info("  OK %s registros orfaos removidos", orphan_count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Setup e otimizacao do banco de dados CVM",
        epilog=(
            "Exemplos:\n"
            "  python scripts/setup_db.py\n"
            "  python scripts/setup_db.py --dry-run\n"
            "  python scripts/setup_db.py --step 1\n"
            "  python scripts/setup_db.py --step 3 --step 4 --step 5"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria feito sem executar")
    parser.add_argument("--step", type=int, action="append", dest="steps", help="Executa apenas passos especificos (1-6)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    steps = set(args.steps) if args.steps else {1, 2, 3, 4, 5, 6}
    settings = build_settings(project_root=ROOT)
    report = collect_startup_report(
        settings,
        require_database=False,
        require_canonical_accounts=bool({4, 5} & steps),
    )
    if report.issues:
        log.info(format_startup_report(report))
        if report.errors:
            raise SystemExit(1)

    engine = build_engine(settings)
    dialect = engine.dialect.name
    log.info("Banco: %s | Dry-run: %s | Passos: %s", dialect, args.dry_run, sorted(steps))

    started_at = time.time()
    with engine.begin() as conn:
        if 1 in steps:
            step1_create_indexes(conn, args.dry_run)
        if 2 in steps:
            step2_create_companies_table(conn, args.dry_run)
        if 3 in steps:
            step3_create_company_refresh_status(conn, args.dry_run)
        if 4 in steps:
            step4_create_account_names(conn, args.dry_run, settings, dialect)
        if 5 in steps:
            step5_fill_standard_names(conn, args.dry_run)
        if 6 in steps:
            step6_clean_orphan_refresh_status(conn, args.dry_run)

    log.info("Setup concluido em %.1fs", time.time() - started_at)
    if not args.dry_run:
        log.info("")
        log.info("Proximos passos:")
        log.info("  python scripts/setup_companies_table.py")
        log.info("  python scripts/expand_tickers.py")


if __name__ == "__main__":
    main()
