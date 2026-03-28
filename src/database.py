import os
import re
import pandas as pd
from sqlalchemy import create_engine, text, Engine


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
        try:
            # INSERT OR IGNORE: não sobrescreve cnpj/setor_analitico/ticker_b3 já preenchidos
            conn.execute(text("""
                INSERT OR IGNORE INTO companies
                    (cd_cvm, company_name, company_type, setor_cvm, ticker_b3, updated_at)
                VALUES
                    (:cd, :name, :ctype, :setor, :ticker,
                     strftime('%Y-%m-%dT%H:%M:%S', 'now'))
            """), {
                "cd":     int(cvm_code),
                "name":   company_name,
                "ctype":  company_type or "comercial",
                "setor":  setor_cvm,
                "ticker": ticker_b3,
            })
            # Atualiza campos não-nulos que podem ter mudado
            conn.execute(text("""
                UPDATE companies
                SET company_name = :name,
                    company_type = :ctype,
                    setor_cvm    = COALESCE(:setor, setor_cvm),
                    updated_at   = strftime('%Y-%m-%dT%H:%M:%S', 'now')
                WHERE cd_cvm = :cd
            """), {
                "cd":    int(cvm_code),
                "name":  company_name,
                "ctype": company_type or "comercial",
                "setor": setor_cvm,
            })
        except Exception:
            pass  # tabela companies pode não existir em instâncias antigas

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
            self._upsert_company_metadata(
                conn, company_name, cvm_code, company_type, setor_cvm, ticker_b3
            )

            # 1. Clean existing records for this company (Idempotency)
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
                    df_to_insert.to_sql('qa_logs', conn, if_exists='append', index=False)

            # 3. Melt and Insert Financial Reports
            all_long_dfs = []

            for statement_type, df_wide in processed_reports.items():
                if df_wide.empty:
                    continue

                metadata_cols = [
                    'LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm',
                    'QA_CONFLICT', 'STANDARD_NAME',
                ]
                id_vars    = [c for c in metadata_cols if c in df_wide.columns]
                value_vars = [c for c in df_wide.columns if c not in id_vars]

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

                def extract_year(label):
                    label = str(label)
                    if label.isdigit() and len(label) == 4:
                        return int(label)
                    match = re.search(r'\dQ(\d{2})', label)
                    if match:
                        return 2000 + int(match.group(1))
                    return None

                df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)

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
                final_df.to_sql('financial_reports', conn, if_exists='append', index=False)
                return len(final_df)

            return 0
