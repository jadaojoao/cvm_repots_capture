import pandas as pd
import sqlite3
import os
import re

BASE_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'reports', 'base_analitica_dashboard_preenchida.xlsx')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'db', 'cvm_financials.db')


def load_analytical_base():
    """Loads the pre-filled analytical master table."""
    try:
        df = pd.read_excel(BASE_FILE_PATH)
        return df
    except Exception as e:
        print(f"Error loading base: {e}")
        return pd.DataFrame()


def load_all_financial_data(cd_cvm):
    """Loads all rows for one company (full SELECT *). Uses parameterized query."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT * FROM financial_reports WHERE CD_CVM = ?",
            conn, params=(int(cd_cvm),)
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading DB: {e}")
        return pd.DataFrame()


def load_company_raw_data(cd_cvm):
    """Loads aggregated standard lines for a company (for export use)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT REPORT_YEAR, STATEMENT_TYPE, PERIOD_LABEL, STANDARD_NAME, "
            "SUM(VL_CONTA) as VL_CONTA "
            "FROM financial_reports WHERE CD_CVM = ? "
            "GROUP BY REPORT_YEAR, STATEMENT_TYPE, PERIOD_LABEL, STANDARD_NAME "
            "ORDER BY REPORT_YEAR DESC, STATEMENT_TYPE, PERIOD_LABEL",
            conn, params=(int(cd_cvm),)
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading DB: {e}")
        return pd.DataFrame()


def get_sectors_list(df):
    """Returns a list of unique sectors."""
    if df.empty or 'mapped_sector' not in df.columns:
        return []
    return sorted([str(s) for s in df['mapped_sector'].dropna().unique()])


def get_companies_list(df, sector=None):
    """Returns a clean list of unique companies, optionally filtered by sector."""
    if df.empty or 'cd_cvm' not in df.columns or 'razao_social' not in df.columns:
        return []
    if sector and 'mapped_sector' in df.columns and sector != 'Todos':
        df = df[df['mapped_sector'] == sector]
    unique_cos = df[['cd_cvm', 'razao_social']].drop_duplicates().dropna()
    return sorted([f"{row['razao_social']} ({int(row['cd_cvm'])})" for _, row in unique_cos.iterrows()])


def extract_cvm_code(selection_string):
    """Extracts the integer CVM code from the dropdown selection string, e.g. 'PETROBRAS (9512)'."""
    try:
        match = re.search(r'\((\d+)\)', selection_string)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None
