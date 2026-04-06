import os
import re
import time
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

SQLITE_WRITE_MAX_RETRIES = 3
SQLITE_WRITE_BACKOFF_SECONDS = 0.6
DEFAULT_TO_SQL_CHUNKSIZE = 2000
SQLITE_SAFE_MAX_VARIABLES = 900


class CVMDatabase:
    """Manages the database for CVM financial reports.

    Suporta SQLite (local) e PostgreSQL (Supabase/produção) via SQLAlchemy.
    A escolha do backend é feita por variável de ambiente DATABASE_URL:
      - Definida → PostgreSQL (Supabase)
      - Ausente   → SQLite local (fallback padrão)
    """

    def __init__(self, db_path="data/db/cvm_financials.db"):
        self._engine = self._build_engine(db_path)
        self._init_db()

    @staticmethod
    def _build_engine(db_path: str) -> Engine:
        url = os.getenv("DATABASE_URL", "")
        if url:
            return create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
            )
        abs_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        return create_engine(
            f"sqlite:///{abs_path}",
            connect_args={"check_same_thread": False},
        )

    def _init_db(self):
        """Creates the necessary tables if they don't exist."""
        dialect = self._engine.dialect.name  # "sqlite" or "postgresql"
        if dialect == "sqlite":
            pk   = "INTEGER PRIMARY KEY AUTOINCREMENT"
            real = "REAL"
        else:
            pk   = "SERIAL PRIMARY KEY"
            real = "DOUBLE PRECISION"

        # Apply PRAGMAs only for SQLite.
        if dialect == "sqlite":
            with self._engine.connect() as pragma_conn:
                pragma_conn.execute(text("PRAGMA journal_mode = WAL"))
                pragma_conn.execute(text("PRAGMA synchronous = OFF"))

        with self._engine.begin() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id {pk},
                    "COMPANY_NAME" TEXT,
                    "CD_CVM" INTEGER,
                    "COMPANY_TYPE" TEXT,
                    "STATEMENT_TYPE" TEXT,
                    "REPORT_YEAR" INTEGER,
                    "PERIOD_LABEL" TEXT,
                    "LINE_ID_BASE" TEXT,
                    "CD_CONTA" TEXT,
                    "DS_CONTA" TEXT,
                    "STANDARD_NAME" TEXT,
                    "QA_CONFLICT" BOOLEAN,
                    "VL_CONTA" {real},
                    UNIQUE("CD_CVM", "STATEMENT_TYPE", "PERIOD_LABEL", "LINE_ID_BASE")
                )
            """))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS qa_logs (
                    id {pk},
                    "COMPANY_NAME" TEXT,
                    "CD_CVM" INTEGER,
                    "ERROR_TYPE" TEXT,
                    "STATEMENT_TYPE" TEXT,
                    "PERIOD" TEXT,
                    "LINE_ID_BASE" TEXT,
                    "CD_CONTA" TEXT,
                    "DESCRIPTION" TEXT,
                    "ACTION" TEXT
                )
            """))

    def _upsert_company_metadata(self, conn, company_name: str, cvm_code: int,
                                 company_type: str, setor_cvm: str | None = None,
                                 ticker_b3: str | None = None) -> None:
        """Persiste metadados na tabela companies (se existir). Idempotente."""
        updated_at = datetime.utcnow().replace(microsecond=0).isoformat()
        params = {
            "cd": int(cvm_code),
            "name": company_name,
            "ctype": company_type or "comercial",
            "setor": setor_cvm,
            "ticker": ticker_b3,
            "updated_at": updated_at,
        }

        conn.execute(text("""
            INSERT INTO companies
                (cd_cvm, company_name, company_type, setor_cvm, ticker_b3, updated_at)
            SELECT
                :cd, :name, :ctype, :setor, :ticker, :updated_at
            WHERE NOT EXISTS (
                SELECT 1 FROM companies WHERE cd_cvm = :cd
            )
        """), params)
        conn.execute(text("""
            UPDATE companies
            SET company_name = :name,
                company_type = :ctype,
                setor_cvm    = COALESCE(:setor, setor_cvm),
                ticker_b3    = COALESCE(:ticker, ticker_b3),
                updated_at   = :updated_at
            WHERE cd_cvm = :cd
        """), params)

    def _to_sql_with_retry(self, table_name: str, df: pd.DataFrame, conn) -> None:
        """Retry writes for transient SQLite lock errors without masking final failures."""
        dialect = self._engine.dialect.name
        max_retries = SQLITE_WRITE_MAX_RETRIES if dialect == "sqlite" else 1
        chunksize = self._resolve_to_sql_chunksize(df)
        attempt = 0
        while True:
            attempt += 1
            try:
                df.to_sql(
                    table_name,
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=chunksize,
                )
                return
            except OperationalError as exc:
                if attempt >= max_retries:
                    raise
                sleep_s = SQLITE_WRITE_BACKOFF_SECONDS * attempt
                logger.warning(
                    "Transient DB write failure for table=%s attempt=%s/%s error=%s",
                    table_name,
                    attempt,
                    max_retries,
                    exc,
                )
                time.sleep(sleep_s)

    def _resolve_to_sql_chunksize(self, df: pd.DataFrame) -> int:
        """Keep SQLite inserts below the engine parameter limit for multi-row writes."""
        if self._engine.dialect.name != "sqlite":
            return DEFAULT_TO_SQL_CHUNKSIZE

        column_count = max(1, len(getattr(df, "columns", [])))
        safe_chunksize = SQLITE_SAFE_MAX_VARIABLES // column_count
        return max(1, min(DEFAULT_TO_SQL_CHUNKSIZE, safe_chunksize))

    def insert_company_data(self, company_name: str, cvm_code: int, company_type: str,
                            processed_reports: dict, qa_logs: list,
                            setor_cvm: str | None = None,
                            ticker_b3: str | None = None):
        """
        Melts wide dataframes into long format and inserts them into the database.
        Deletes existing data for this company to allow idempotency.
        Também atualiza a tabela companies com metadados (setor, ticker).
        """
        with self._engine.begin() as conn:
            # 0. Persistir metadados na tabela companies
            # Use nested transaction so metadata failures don't abort main data writes on PostgreSQL.
            try:
                with conn.begin_nested():
                    self._upsert_company_metadata(
                        conn, company_name, cvm_code, company_type, setor_cvm, ticker_b3
                    )
            except Exception as exc:
                logger.warning(
                    "Non-fatal company metadata upsert failure "
                    "(table may not exist or schema may differ): cd_cvm=%s company_name=%r error_type=%s error=%s",
                    cvm_code,
                    company_name,
                    exc.__class__.__name__,
                    exc,
                )

            # 1. Clean existing records for this company (Idempotency — scoped to years being inserted)
            years_to_delete: set[int] = set()
            _meta = {'LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT', 'STANDARD_NAME'}
            for df_wide in processed_reports.values():
                if df_wide is None or df_wide.empty:
                    continue
                for col in df_wide.columns:
                    col_str = str(col)
                    if col_str in _meta:
                        continue
                    if col_str.isdigit() and len(col_str) == 4:
                        years_to_delete.add(int(col_str))
                    else:
                        m = re.search(r'\dQ(\d{2})', col_str)
                        if m:
                            years_to_delete.add(2000 + int(m.group(1)))

            if years_to_delete:
                placeholders = ', '.join(str(y) for y in sorted(years_to_delete))
                conn.execute(
                    text(
                        f'DELETE FROM financial_reports '
                        f'WHERE "CD_CVM" = :cvm '
                        f'AND ("REPORT_YEAR" IN ({placeholders}) OR "REPORT_YEAR" IS NULL)'
                    ),
                    {"cvm": int(cvm_code)},
                )
            else:
                conn.execute(
                    text('DELETE FROM financial_reports WHERE "CD_CVM" = :cvm'),
                    {"cvm": int(cvm_code)},
                )
            conn.execute(
                text('DELETE FROM qa_logs WHERE "CD_CVM" = :cvm'),
                {"cvm": int(cvm_code)},
            )

            # 2. Insert QA Logs
            if qa_logs:
                df_qa = pd.DataFrame(qa_logs)
                df_qa['COMPANY_NAME'] = company_name
                df_qa['CD_CVM'] = int(cvm_code)

                col_map = {
                    'type': 'ERROR_TYPE',
                    'statement': 'STATEMENT_TYPE',
                    'period': 'PERIOD',
                    'line_id_base': 'LINE_ID_BASE',
                    'cd_conta': 'CD_CONTA',
                    'description': 'DESCRIPTION',
                    'action': 'ACTION',
                }

                db_cols = {k: v for k, v in col_map.items() if k in df_qa.columns}
                if db_cols:
                    df_qa = df_qa.rename(columns=db_cols)
                    db_schema_cols = [
                        'COMPANY_NAME', 'CD_CVM', 'ERROR_TYPE', 'STATEMENT_TYPE',
                        'PERIOD', 'LINE_ID_BASE', 'CD_CONTA', 'DESCRIPTION', 'ACTION',
                    ]
                    df_to_insert = df_qa[[c for c in db_schema_cols if c in df_qa.columns]]
                    self._to_sql_with_retry('qa_logs', df_to_insert, conn)

            # 3. Melt and Insert Financial Reports
            all_long_dfs = []

            for statement_type, df_wide in processed_reports.items():
                if df_wide.empty:
                    continue

                metadata_cols = [
                    'LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm',
                    'QA_CONFLICT', 'STANDARD_NAME', 'COMPANY_TYPE',
                ]
                id_vars    = [c for c in metadata_cols if c in df_wide.columns]
                value_vars = []
                for c in df_wide.columns:
                    if c in id_vars:
                        continue
                    col = str(c)
                    if col.isdigit() and len(col) == 4:
                        value_vars.append(c)
                        continue
                    if re.match(r'^\dQ(\d{2})$', col):
                        value_vars.append(c)

                if not value_vars:
                    continue

                df_long = df_wide.melt(
                    id_vars=id_vars,
                    value_vars=value_vars,
                    var_name='PERIOD_LABEL',
                    value_name='VL_CONTA',
                )
                df_long = df_long.dropna(subset=['VL_CONTA'])

                if df_long.empty:
                    continue

                df_long['COMPANY_NAME']   = company_name
                df_long['CD_CVM']         = int(cvm_code)
                df_long['COMPANY_TYPE']   = company_type
                df_long['STATEMENT_TYPE'] = statement_type

                                # Vectorized extract_year
                df_long['REPORT_YEAR'] = None
                labels = df_long['PERIOD_LABEL'].astype(str)
                # Annual: 2024
                mask_ann = labels.str.match(r'^\d{4}$')
                df_long.loc[mask_ann, 'REPORT_YEAR'] = labels[mask_ann].astype(int)
                # Quarterly: 1Q24
                mask_qtr = labels.str.match(r'^\dQ(\d{2})$')
                if mask_qtr.any():
                    yy = labels[mask_qtr].str.extract(r'\dQ(\d{2})')[0].astype(int)
                    df_long.loc[mask_qtr, 'REPORT_YEAR'] = 2000 + yy

                if 'CD_CONTA' not in df_long.columns:
                    df_long['CD_CONTA'] = None
                if 'STANDARD_NAME' not in df_long.columns:
                    df_long['STANDARD_NAME'] = None
                if 'QA_CONFLICT' not in df_long.columns:
                    df_long['QA_CONFLICT'] = False

                final_cols = [
                    'COMPANY_NAME', 'CD_CVM', 'COMPANY_TYPE', 'STATEMENT_TYPE',
                    'REPORT_YEAR', 'PERIOD_LABEL', 'LINE_ID_BASE', 'CD_CONTA',
                    'DS_CONTA', 'STANDARD_NAME', 'QA_CONFLICT', 'VL_CONTA',
                ]
                all_long_dfs.append(df_long[final_cols])

            if all_long_dfs:
                final_df = pd.concat(all_long_dfs, ignore_index=True)
                unique_key_cols = ["CD_CVM", "STATEMENT_TYPE", "PERIOD_LABEL", "LINE_ID_BASE"]
                before_dedupe = len(final_df)
                final_df = final_df.drop_duplicates(subset=unique_key_cols, keep="last").reset_index(drop=True)
                removed = before_dedupe - len(final_df)
                if removed > 0:
                    logger.warning(
                        "Deduplicated %s financial_reports rows before insert "
                        "for cd_cvm=%s company_name=%r",
                        removed,
                        cvm_code,
                        company_name,
                    )
                self._to_sql_with_retry('financial_reports', final_df, conn)
                return len(final_df)

            return 0
