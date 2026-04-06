# -*- coding: utf-8 -*-
"""
scripts/setup_db.py — Setup e otimização do banco de dados CVM.

Executa em ordem:
  1. Cria índices de performance em financial_reports e qa_logs
  2. Cria tabela `companies` (metadados: CNPJ, setor, ticker)
  3. Cria tabela `company_refresh_status` (status do Update Center)
  4. Cria tabela `account_names` (dicionário canônico de contas)
  5. Preenche STANDARD_NAME NULLs em financial_reports via account_names

Seguro de rodar múltiplas vezes (idempotente).

Uso:
    python scripts/setup_db.py
    python scripts/setup_db.py --dry-run   # mostra o que faria sem executar
    python scripts/setup_db.py --step 1    # executa só o passo 1
"""
import sys
import os
import argparse
import logging
import time
from pathlib import Path

# Garante UTF-8 no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


# ==============================================================================
# PASSO 1 — Índices de performance
# ==============================================================================

INDEXES = [
    {
        "name": "idx_fr_year_period",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_fr_year_period ON financial_reports("REPORT_YEAR", "PERIOD_LABEL")',
        "desc": "heatmap da aba Mercado (65% ganho estimado)",
    },
    {
        "name": "idx_fr_cvm_year",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_fr_cvm_year ON financial_reports("CD_CVM", "REPORT_YEAR", "PERIOD_LABEL")',
        "desc": "load_peer_df() da aba Peers",
    },
    {
        "name": "idx_qa_cvm",
        "sql": 'CREATE INDEX IF NOT EXISTS idx_qa_cvm ON qa_logs("CD_CVM")',
        "desc": "limpeza de qa_logs por empresa",
    },
]


def step1_create_indexes(conn, dry_run: bool) -> None:
    log.info("=== Passo 1: Criando índices de performance ===")
    for idx in INDEXES:
        if dry_run:
            log.info(f"  [DRY-RUN] Criaria: {idx['name']} ({idx['desc']})")
            continue
        t0 = time.time()
        conn.execute(_text(idx["sql"]))
        elapsed = time.time() - t0
        log.info(f"  ✓ {idx['name']} criado em {elapsed:.1f}s ({idx['desc']})")


# ==============================================================================
# PASSO 2 — Tabela `companies`
# ==============================================================================

DDL_COMPANIES = """
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
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
"""

DDL_COMPANIES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_companies_setor ON companies(setor_analitico)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uix_companies_cnpj ON companies(cnpj) WHERE cnpj IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker_b3) WHERE ticker_b3 IS NOT NULL",
]

DDL_COMPANY_REFRESH_STATUS = """
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

DDL_COMPANY_REFRESH_STATUS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_crs_status ON company_refresh_status(last_status)",
]


def step2_create_companies_table(conn, dry_run: bool) -> None:
    log.info("=== Passo 2: Criando tabela `companies` ===")
    if dry_run:
        log.info("  [DRY-RUN] Criaria tabela companies + 3 índices")
        return
    conn.execute(_text(DDL_COMPANIES))
    for sql in DDL_COMPANIES_INDEXES:
        conn.execute(_text(sql))
    log.info("  ✓ Tabela companies criada")
    log.info("  Nota: execute scripts/setup_companies_table.py para popular os dados")


def step3_create_company_refresh_status(conn, dry_run: bool) -> None:
    log.info("=== Passo 3: Criando tabela `company_refresh_status` ===")
    if dry_run:
        log.info("  [DRY-RUN] Criaria tabela company_refresh_status + 1 índice")
        return
    conn.execute(_text(DDL_COMPANY_REFRESH_STATUS))
    for sql in DDL_COMPANY_REFRESH_STATUS_INDEXES:
        conn.execute(_text(sql))
    log.info("  ✓ Tabela company_refresh_status criada")


# ==============================================================================
# PASSO 4 — Tabela `account_names` + população via canonical_accounts.csv
# ==============================================================================

DDL_ACCOUNT_NAMES = """
CREATE TABLE IF NOT EXISTS account_names (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_type  TEXT NOT NULL,
    cd_conta        TEXT NOT NULL,
    standard_name   TEXT NOT NULL,
    company_type    TEXT NOT NULL DEFAULT 'comercial',
    is_consolidated INTEGER NOT NULL DEFAULT 1,
    nivel           INTEGER,
    UNIQUE(statement_type, cd_conta, company_type, is_consolidated)
)
"""

DDL_ACCOUNT_NAMES_IDX = "CREATE INDEX IF NOT EXISTS idx_account_lookup ON account_names(statement_type, cd_conta)"


def step4_create_account_names(conn, dry_run: bool) -> None:
    import pandas as pd

    log.info("=== Passo 3: Criando tabela `account_names` e populando ===")

    canon_path = ROOT / "data" / "canonical_accounts.csv"
    if not canon_path.exists():
        log.error(f"  Arquivo não encontrado: {canon_path}")
        log.error("  Pulando passo 4.")
        return

    df = pd.read_csv(canon_path, encoding='utf-8-sig')
    log.info(f"  Lido {len(df)} linhas de {canon_path.name}")
    log.info(f"  Colunas: {df.columns.tolist()}")

    # Mapear colunas do CSV para o schema da tabela
    rename_map = {
        'CD_CONTA':        'cd_conta',
        'STANDARD_NAME':   'standard_name',
        'STATEMENT_TYPE':  'statement_type',
        'EMPRESA_TIPO':    'company_type',
        'NIVEL':           'nivel',
        'IS_CONSOLIDADO':  'is_consolidated',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Garantir colunas mínimas
    for col, default in [('company_type', 'comercial'), ('is_consolidated', 1), ('nivel', None)]:
        if col not in df.columns:
            df[col] = default

    # Converter is_consolidated para inteiro
    if df['is_consolidated'].dtype == object:
        df['is_consolidated'] = df['is_consolidated'].map(
            {'True': 1, 'False': 0, True: 1, False: 0}
        ).fillna(1).astype(int)

    required = ['statement_type', 'cd_conta', 'standard_name', 'company_type', 'is_consolidated']
    missing = [c for c in required if c not in df.columns]
    if missing:
        log.error(f"  Colunas obrigatórias ausentes no CSV: {missing}")
        return

    df_insert = df[['statement_type', 'cd_conta', 'standard_name', 'company_type', 'is_consolidated', 'nivel']].copy()

    if dry_run:
        log.info(f"  [DRY-RUN] Criaria tabela account_names e inseriria {len(df_insert)} linhas")
        return

    conn.execute(_text(DDL_ACCOUNT_NAMES))
    conn.execute(_text(DDL_ACCOUNT_NAMES_IDX))

    # Verificar quantas já existem
    existing = conn.execute(_text("SELECT COUNT(*) FROM account_names")).scalar()
    if existing > 0:
        log.info(f"  Tabela já contém {existing} linhas — fazendo INSERT OR IGNORE")
        # Inserir linha a linha para respeitar UNIQUE sem erro
        inserted = 0
        for _, row in df_insert.iterrows():
            try:
                conn.execute(_text("""
                    INSERT OR IGNORE INTO account_names
                    (statement_type, cd_conta, standard_name, company_type, is_consolidated, nivel)
                    VALUES (:st, :cc, :sn, :ct, :ic, :nv)
                """), {
                    'st': row['statement_type'],
                    'cc': row['cd_conta'],
                    'sn': row['standard_name'],
                    'ct': row['company_type'],
                    'ic': int(row['is_consolidated']) if row['is_consolidated'] is not None else 1,
                    'nv': int(row['nivel']) if row['nivel'] is not None and str(row['nivel']) != 'nan' else None,
                })
                inserted += 1
            except Exception:
                pass
        log.info(f"  ✓ {inserted} linhas inseridas/ignoradas em account_names")
    else:
        df_insert.to_sql('account_names', conn, if_exists='append', index=False)
        log.info(f"  ✓ {len(df_insert)} linhas inseridas em account_names")


# ==============================================================================
# PASSO 5 — Preencher STANDARD_NAME NULLs em financial_reports
# ==============================================================================

UPDATE_STANDARD_NAME_SQL = """
UPDATE financial_reports
SET "STANDARD_NAME" = (
    SELECT an.standard_name
    FROM account_names an
    WHERE an.cd_conta       = financial_reports."CD_CONTA"
      AND an.statement_type = financial_reports."STATEMENT_TYPE"
    ORDER BY an.is_consolidated DESC
    LIMIT 1
)
WHERE "STANDARD_NAME" IS NULL
"""

UPDATE_STANDARD_NAME_FALLBACK_SQL = """
UPDATE financial_reports
SET "STANDARD_NAME" = "DS_CONTA"
WHERE "STANDARD_NAME" IS NULL
  AND "DS_CONTA" IS NOT NULL
  AND TRIM("DS_CONTA") != ''
"""


def step5_fill_standard_names(conn, dry_run: bool) -> None:
    log.info("=== Passo 5: Preenchendo STANDARD_NAME NULLs ===")

    # Verificar se account_names existe e tem dados
    try:
        count_an = conn.execute(_text("SELECT COUNT(*) FROM account_names")).scalar()
    except Exception:
        log.warning("  Tabela account_names não existe. Pulando passo 5.")
        return

    if count_an == 0:
        log.warning("  account_names está vazia. Execute o passo 4 primeiro.")
        return

    null_before = conn.execute(
        _text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
    ).scalar()
    log.info(f"  STANDARD_NAME NULLs antes: {null_before:,}")

    if null_before == 0:
        log.info("  Nenhum NULL encontrado. Nada a fazer.")
        return

    if dry_run:
        log.info(f"  [DRY-RUN] Preencheria até {null_before:,} NULLs usando account_names")
        log.info(f"  [DRY-RUN] Restantes sem mapeamento seriam preenchidos com DS_CONTA")
        return

    t0 = time.time()
    conn.execute(_text(UPDATE_STANDARD_NAME_SQL))
    null_after_dict = conn.execute(
        _text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
    ).scalar()
    filled_from_dict = null_before - null_after_dict
    log.info(f"  ✓ {filled_from_dict:,} NULLs preenchidos via account_names em {time.time()-t0:.1f}s")

    if null_after_dict > 0:
        t1 = time.time()
        conn.execute(_text(UPDATE_STANDARD_NAME_FALLBACK_SQL))
        null_after_fallback = conn.execute(
            _text('SELECT COUNT(*) FROM financial_reports WHERE "STANDARD_NAME" IS NULL')
        ).scalar()
        filled_from_ds = null_after_dict - null_after_fallback
        log.info(f"  ✓ {filled_from_ds:,} NULLs preenchidos via DS_CONTA (fallback) em {time.time()-t1:.1f}s")
        log.info(f"  Ainda NULL: {null_after_fallback:,} (DS_CONTA também nulo — raro)")
    else:
        log.info("  Nenhum NULL restante após account_names.")


# ==============================================================================
# PASSO 6 — Limpar registros órfãos em company_refresh_status
# ==============================================================================

def step6_clean_orphan_refresh_status(conn, dry_run: bool) -> None:
    log.info("=== Passo 6: Limpando registros órfãos em company_refresh_status ===")
    try:
        count = conn.execute(_text("""
            SELECT COUNT(*) FROM company_refresh_status
            WHERE cd_cvm NOT IN (SELECT cd_cvm FROM companies)
        """)).scalar()
    except Exception:
        log.warning("  Tabela company_refresh_status não existe. Pulando passo 6.")
        return
    log.info(f"  Órfãos encontrados: {count}")
    if count == 0:
        log.info("  Nada a fazer.")
        return
    if dry_run:
        log.info(f"  [DRY-RUN] Removeria {count} registros órfãos")
        return
    conn.execute(_text("""
        DELETE FROM company_refresh_status
        WHERE cd_cvm NOT IN (SELECT cd_cvm FROM companies)
    """))
    log.info(f"  ✓ {count} registros órfãos removidos")


# ==============================================================================
# Orquestrador
# ==============================================================================

def _text(sql: str):
    """Lazy import de sqlalchemy.text para evitar import no topo."""
    from sqlalchemy import text
    return text(sql)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Setup e otimização do banco de dados CVM",
        epilog=(
            "Exemplos:\n"
            "  python scripts/setup_db.py\n"
            "  python scripts/setup_db.py --dry-run\n"
            "  python scripts/setup_db.py --step 1\n"
            "  python scripts/setup_db.py --step 3 --step 4 --step 5"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra o que seria feito sem executar",
    )
    parser.add_argument(
        "--step", type=int, action="append", dest="steps",
        help="Executar só passos específicos (1-6). Pode repetir: --step 1 --step 2",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    steps = set(args.steps) if args.steps else {1, 2, 3, 4, 5, 6}

    from src.db import get_engine
    engine = get_engine()
    dialect = engine.dialect.name
    log.info(f"Banco: {dialect} | Dry-run: {args.dry_run} | Passos: {sorted(steps)}")

    t_total = time.time()

    with engine.begin() as conn:
        if 1 in steps:
            step1_create_indexes(conn, args.dry_run)
        if 2 in steps:
            step2_create_companies_table(conn, args.dry_run)
        if 3 in steps:
            step3_create_company_refresh_status(conn, args.dry_run)
        if 4 in steps:
            step4_create_account_names(conn, args.dry_run)
        if 5 in steps:
            step5_fill_standard_names(conn, args.dry_run)
        if 6 in steps:
            step6_clean_orphan_refresh_status(conn, args.dry_run)

    elapsed = time.time() - t_total
    log.info(f"Setup concluído em {elapsed:.1f}s")

    if not args.dry_run:
        log.info("")
        log.info("Próximos passos:")
        log.info("  python scripts/setup_companies_table.py   ← popula tabela companies")
        log.info("  python scripts/expand_tickers.py          ← descobre novos tickers B3")


if __name__ == "__main__":
    main()
