import sqlite3
import pandas as pd
import os
import re

class CVMDatabase:
    """Manages the SQLite database for CVM financial reports."""
    
    def __init__(self, db_path="data/db/cvm_financials.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Creates the necessary tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Matriz Financeira (Schema Longo)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    COMPANY_NAME TEXT,
                    CD_CVM INTEGER,
                    COMPANY_TYPE TEXT,
                    STATEMENT_TYPE TEXT,
                    REPORT_YEAR INTEGER,
                    PERIOD_LABEL TEXT,
                    LINE_ID_BASE TEXT,
                    CD_CONTA TEXT,
                    DS_CONTA TEXT,
                    STANDARD_NAME TEXT,
                    QA_CONFLICT BOOLEAN,
                    VL_CONTA REAL,
                    UNIQUE(CD_CVM, STATEMENT_TYPE, PERIOD_LABEL, LINE_ID_BASE)
                )
            ''')
            
            # QA Logs (Rastreabilidade de batelada)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS qa_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    COMPANY_NAME TEXT,
                    CD_CVM INTEGER,
                    ERROR_TYPE TEXT,
                    STATEMENT_TYPE TEXT,
                    PERIOD TEXT,
                    LINE_ID_BASE TEXT,
                    CD_CONTA TEXT,
                    DESCRIPTION TEXT,
                    ACTION TEXT
                )
            ''')
            
            conn.commit()

    def insert_company_data(self, company_name: str, cvm_code: int, company_type: str, 
                            processed_reports: dict, qa_logs: list):
        """
        Melts wide dataframes into long format and inserts them into SQLite.
        Deletes existing data for this company to allow idempotency.
        """
        with sqlite3.connect(self.db_path) as conn:
            # 1. Clean existing records for this company (Idempotency)
            conn.execute("DELETE FROM financial_reports WHERE CD_CVM = ?", (int(cvm_code),))
            conn.execute("DELETE FROM qa_logs WHERE CD_CVM = ?", (int(cvm_code),))
            
            # 2. Insert QA Logs
            if qa_logs:
                # Convert logs list of dicts to DataFrame
                df_qa = pd.DataFrame(qa_logs)
                df_qa['COMPANY_NAME'] = company_name
                df_qa['CD_CVM'] = int(cvm_code)
                
                # Rename columns to match DB schema safely
                col_map = {
                    'type': 'ERROR_TYPE',
                    'statement': 'STATEMENT_TYPE',
                    'period': 'PERIOD',
                    'line_id_base': 'LINE_ID_BASE',
                    'cd_conta': 'CD_CONTA',
                    'description': 'DESCRIPTION',
                    'action': 'ACTION'
                }
                
                # Keep only columns that exist in mapping
                db_cols = {k: v for k, v in col_map.items() if k in df_qa.columns}
                if db_cols:
                    df_qa = df_qa.rename(columns=db_cols)
                    
                    # Filter only columns that exist in DB
                    db_schema_cols = ['COMPANY_NAME', 'CD_CVM', 'ERROR_TYPE', 'STATEMENT_TYPE', 
                                    'PERIOD', 'LINE_ID_BASE', 'CD_CONTA', 'DESCRIPTION', 'ACTION']
                    df_to_insert = df_qa[[c for c in db_schema_cols if c in df_qa.columns]]
                    
                    df_to_insert.to_sql('qa_logs', conn, if_exists='append', index=False)

            # 3. Melt and Insert Financial Reports
            all_long_dfs = []
            
            for statement_type, df_wide in processed_reports.items():
                if df_wide.empty:
                    continue
                
                # Identify Metadata vs Period columns
                metadata_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT', 'STANDARD_NAME']
                id_vars = [c for c in metadata_cols if c in df_wide.columns]
                value_vars = [c for c in df_wide.columns if c not in id_vars]
                
                # Unpivot (Melt)
                df_long = df_wide.melt(
                    id_vars=id_vars,
                    value_vars=value_vars,
                    var_name='PERIOD_LABEL',
                    value_name='VL_CONTA'
                )
                
                # Drop rows where VL_CONTA is null (no point storing empty spaces in DB)
                df_long = df_long.dropna(subset=['VL_CONTA'])
                
                if df_long.empty:
                    continue
                    
                # Add DB explicit columns
                df_long['COMPANY_NAME'] = company_name
                df_long['CD_CVM'] = int(cvm_code)
                df_long['COMPANY_TYPE'] = company_type
                df_long['STATEMENT_TYPE'] = statement_type
                
                # Extract Report Year from Period Label (e.g. '1Q24' -> 2024, '2024' -> 2024)
                def extract_year(label):
                    label = str(label)
                    if label.isdigit() and len(label) == 4:
                        return int(label)
                    match = re.search(r'\dQ(\d{2})', label)
                    if match:
                        return 2000 + int(match.group(1))
                    return None
                
                df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)
                
                # Assign default values for optional columns if missing
                if 'CD_CONTA' not in df_long.columns:
                    df_long['CD_CONTA'] = None
                if 'STANDARD_NAME' not in df_long.columns:
                    df_long['STANDARD_NAME'] = None
                if 'QA_CONFLICT' not in df_long.columns:
                    df_long['QA_CONFLICT'] = False
                
                # Clean up structure to match Schema exactly
                final_cols = ['COMPANY_NAME', 'CD_CVM', 'COMPANY_TYPE', 'STATEMENT_TYPE', 
                              'REPORT_YEAR', 'PERIOD_LABEL', 'LINE_ID_BASE', 'CD_CONTA', 
                              'DS_CONTA', 'STANDARD_NAME', 'QA_CONFLICT', 'VL_CONTA']
                
                df_clean = df_long[final_cols]
                all_long_dfs.append(df_clean)
            
            if all_long_dfs:
                final_df = pd.concat(all_long_dfs, ignore_index=True)
                final_df.to_sql('financial_reports', conn, if_exists='append', index=False)
                return len(final_df)
            
            return 0
