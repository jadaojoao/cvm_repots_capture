"""
CVM Financial Data Extractor
=============================

Extracts, processes, and generates Excel reports from CVM financial statements.
"""

# ============================================================================
# USER CONFIGURATION
# ============================================================================

# Company to process (name or CVM code)
COMPANY_NAME = "VALE"

# Year range (inclusive)
START_YEAR = 2020
END_YEAR = 2025

# Report type: "consolidated" or "individual"
REPORT_TYPE = "consolidated"

# Output directory
OUTPUT_DIR = "output/reports"

# Data directory
DATA_DIR = "data/input"

# Force re-download even if files exist
FORCE_REFRESH = False

# Maximum retries when output Excel file is locked by another process
MAX_EXCEL_LOCK_RETRIES = 10

# Network timeouts (seconds)
COMPANY_LIST_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60

# DFC validation tolerance (BRL Milhões)
DFC_VALIDATION_TOLERANCE = 0.01

COMPANY_DB_MAX_RETRIES = 3
COMPANY_DB_RETRY_BACKOFF_SECONDS = 1.2

# Year interpretation: dois dígitos < Y2K_PIVOT → século 21, >= → século 20
Y2K_PIVOT = 50

# ============================================================================
# IMPORTS
# ============================================================================

import sys
import os
import re
import time
import traceback
import requests
import zipfile
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import io
import argparse
from datetime import datetime
from typing import Callable
from sqlalchemy.exc import OperationalError
from src.utils import normalize_account_name, generate_line_id_base, validate_line_ids
from src.standardizer import AccountStandardizer
from src.database import CVMDatabase

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class CVMScraper:
    BASE_URL = os.environ.get('CVM_BASE_URL', "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC")

    def __init__(self, output_dir="output/reports", data_dir="data/input", report_type="consolidated", max_workers=5):
        self.output_dir = output_dir
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")
        self.report_type = report_type
        self.max_workers = max_workers
        
        if self.report_type == "consolidated":
            self.suffix = "con"
        else:
            self.suffix = "ind"
            
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.companies_map = {}
        self.setores_map = {}
        
        # Standardizer
        canonical_csv_path = os.path.join(current_dir, '..', 'data', 'canonical_accounts.csv')
        self.standardizer = None
        if os.path.exists(canonical_csv_path):
            try:
                self.standardizer = AccountStandardizer(canonical_csv_path)
            except Exception as e:
                print(f"Aviso: Falha ao carregar padronizador: {e}")
                
        # Database
        db_path = os.path.join(current_dir, '..', 'data', 'db', 'cvm_financials.db')
        self.db = CVMDatabase(db_path)

    def fetch_company_list(self):
        print("Fetching company list...")
        url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
        try:
            response = requests.get(url, timeout=COMPANY_LIST_TIMEOUT)
            response.raise_for_status()
            df = pd.read_csv(io.BytesIO(response.content), sep=";", encoding="latin1")
            
            social = df[df['DENOM_SOCIAL'].notna()].set_index(df[df['DENOM_SOCIAL'].notna()]['DENOM_SOCIAL'].str.upper().str.strip())['CD_CVM']
            comerc = df[df['DENOM_COMERC'].notna()].set_index(df[df['DENOM_COMERC'].notna()]['DENOM_COMERC'].str.upper().str.strip())['CD_CVM']
            self.companies_map = {**social.to_dict(), **comerc.to_dict()}
            
            df['CD_CVM_STR'] = df['CD_CVM'].astype(str)
            self.setores_map = df[df['SETOR_ATIV'].notna()].set_index('CD_CVM_STR')['SETOR_ATIV'].to_dict()
            return df
        except Exception as e:
            print(f"Error fetching company list: {e}")
            return None

    def resolve_company_codes(self, company_names):
        resolved = {}
        code_to_name = {v: k for k, v in self.companies_map.items()}
        for name in company_names:
            if str(name).isdigit():
                cvm_code = int(name)
                resolved[code_to_name.get(cvm_code, f"CVM_{cvm_code}")] = cvm_code
            else:
                name_upper = str(name).upper().strip()
                if name_upper in self.companies_map:
                    resolved[name] = self.companies_map[name_upper]
                else:
                    matches = [code for k, code in self.companies_map.items() if name_upper in k]
                    if matches: resolved[name] = matches[0]
        return resolved

    def download_and_extract(self, year, doc_type):
        filename = f"{doc_type.lower()}_cia_aberta_{year}.zip"
        url = f"{self.BASE_URL}/{doc_type}/DADOS/{filename}"
        local_zip_path = os.path.join(self.raw_dir, filename)
        
        if not FORCE_REFRESH and os.path.exists(local_zip_path):
            print(f"  Using local zip: {filename}")
        else:
            print(f"Downloading {doc_type} for {year}...")
            try:
                response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
                if response.status_code != 200: return False
                with open(local_zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            except Exception as e:
                print(f"  Error downloading {year}: {e}")
                return False

        try:
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if any(f'_{self.suffix}_' in file and x in file for x in ['BPA', 'BPP', 'DRE', 'DFC', 'DVA', 'DMPL']):
                        zip_ref.extract(file, self.processed_dir)
            return True
        except Exception as e:
            print(f"  Error extracting {year}: {e}")
            return False

    def normalize_units(self, df):
        """Converts values to Thousands (R$ mil) based on ESCALA_MOEDA."""
        if 'ESCALA_MOEDA' not in df.columns or 'VL_CONTA' not in df.columns:
            return df
        mask_unidade = df['ESCALA_MOEDA'].str.upper() == 'UNIDADE'
        mask_milhao = df['ESCALA_MOEDA'].str.upper().isin(['MILHÃO', 'MILHAO', 'MILLION'])
        # Objetivo: R$ mil. UNIDADE / 1000 = MIL. MILHAO * 1000 = MIL.
        df.loc[mask_unidade, 'VL_CONTA'] = df.loc[mask_unidade, 'VL_CONTA'] / 1000
        df.loc[mask_milhao, 'VL_CONTA'] = df.loc[mask_milhao, 'VL_CONTA'] * 1000
        return df

    def process_data(self, cvm_code, years):
        all_data = []
        file_patterns = ['BPA', 'BPP', 'DRE', 'DFC_MD', 'DFC_MI', 'DVA', 'DMPL']
        for year in years:
            for doc_type in ['dfp', 'itr']:
                for pattern in file_patterns:
                    filename = f"{doc_type}_cia_aberta_{pattern}_{self.suffix}_{year}.csv"
                    filepath = os.path.join(self.processed_dir, filename)
                    if os.path.exists(filepath):
                        try:
                            df = pd.read_csv(filepath, sep=";", encoding="latin1")
                            df_company = df[df['CD_CVM'] == cvm_code].copy()
                            if not df_company.empty:
                                if 'ORDEM_EXERC' in df_company.columns:
                                    df_company = df_company[df_company['ORDEM_EXERC'] == 'ÚLTIMO']
                                
                                stmt_map = {'BPA':'BPA', 'BPP':'BPP', 'DRE':'DRE', 'DFC_MD':'DFC', 'DFC_MI':'DFC', 'DVA':'DVA', 'DMPL':'DMPL'}
                                stmt_type = stmt_map.get(pattern, 'OTHER')
                                
                                df_company['DS_CONTA_norm'] = df_company['DS_CONTA'].apply(normalize_account_name)
                                df_company['LINE_ID_BASE'] = df_company.apply(lambda r: generate_line_id_base(r, stmt_type), axis=1)
                                df_company = self.normalize_units(df_company)
                                
                                df_company['PERIOD_TYPE'] = doc_type.upper()
                                df_company['STMT_TYPE_INTERNAL'] = stmt_type
                                
                                # Preserve COMPANY_TYPE for dashboard
                                setor = str(self.setores_map.get(str(cvm_code), '')).lower()
                                df_company['COMPANY_TYPE'] = 'financeira' if any(k in setor for k in ['banc', 'financ']) else 'comercial'
                                
                                all_data.append(df_company)
                        except Exception: continue
        return pd.concat(all_data, ignore_index=True) if all_data else None

    def calculate_quarters(self, df, report_type):
        if df.empty: return pd.DataFrame()
        for col in ['DT_REFER', 'DT_INI_EXERC', 'DT_FIM_EXERC']:
            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
        
        df = df.copy()
        df['PERIOD_LABEL'] = df.apply(lambda row: self._create_period_label(row, report_type), axis=1)
        df = df[df['PERIOD_LABEL'].notna()]
        if df.empty: return pd.DataFrame()

        index_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA']
        df_wide = df.pivot_table(index=index_cols, columns='PERIOD_LABEL', values='VL_CONTA', aggfunc='first').reset_index()
        
        for col in ['DS_CONTA_norm', 'COMPANY_TYPE']:
            if col in df.columns:
                df_wide[col] = df_wide['LINE_ID_BASE'].map(df.groupby('LINE_ID_BASE')[col].first())

        df_wide['QA_CONFLICT'] = False
        df_wide, _, errors = self.coalesce_duplicate_line_ids(df_wide, report_type)
        if not hasattr(self, '_coalesce_errors'): self._coalesce_errors = []
        self._coalesce_errors.extend(errors)

        if report_type in ['DFC', 'DRE']:
            df_wide, conv_errors = self.convert_dfc_ytd_to_standalone(df_wide, report_type)
            self._coalesce_errors.extend(conv_errors)

        period_cols = sorted([c for c in df_wide.columns if c not in index_cols+['DS_CONTA_norm', 'QA_CONFLICT']], key=self._period_sort_key)
        return df_wide[index_cols + ['DS_CONTA_norm', 'QA_CONFLICT'] + period_cols]

    def _create_period_label(self, row, report_type):
        if report_type in ['BPA', 'BPP']:
            dt = row.get('DT_REFER')
            if pd.isna(dt): return None
            yy = str(dt.year)[2:]
            if dt.month == 3: return f'1Q{yy}'
            if dt.month == 6: return f'2Q{yy}'
            if dt.month == 9: return f'3Q{yy}'
            if dt.month == 12: return str(dt.year)
        else:
            dt_ini, dt_fim = row.get('DT_INI_EXERC'), row.get('DT_FIM_EXERC')
            if pd.isna(dt_ini) or pd.isna(dt_fim): return None
            yy = str(dt_fim.year)[2:]
            if dt_ini.month == 1 and dt_ini.day == 1:
                if dt_fim.month == 3: return f'1Q{yy}'
                if dt_fim.month == 6: return f'2Q{yy}'
                if dt_fim.month == 9: return f'3Q{yy}'
                if dt_fim.month == 12: return str(dt_fim.year)
            elif dt_ini.month == 4 and dt_fim.month == 6: return f'2Q{yy}'
            elif dt_ini.month == 7 and dt_fim.month == 9: return f'3Q{yy}'
            elif dt_ini.month == 10 and dt_fim.month == 12: return f'4Q{yy}'
        return None

    def _period_sort_key(self, label):
        if label.isdigit(): return (int(label), 5)
        if len(label) >= 4 and label[1] == 'Q':
            q = int(label[0])
            y = 2000 + int(label[2:]) if len(label[2:])==2 else int(label[2:])
            return (y, q)
        return (9999, 0)

    def coalesce_duplicate_line_ids(self, df, stmt):
        qa_errors = []
        p_cols = [c for c in df.columns if c not in ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']]
        grouped = df.groupby('LINE_ID_BASE')
        final_rows = []
        for lid, group in grouped:
            if len(group) == 1:
                final_rows.append(group.iloc[0])
                continue
            merged = group.iloc[0].copy()
            has_conflict = False
            for col in p_cols:
                vals = group[col].dropna().unique()
                if len(vals) > 1:
                    has_conflict = True
                    qa_errors.append({'type': 'REAL_CONFLICT', 'statement': stmt, 'line_id_base': lid, 'period': col})
                if len(vals) >= 1: merged[col] = vals[0]
            merged['QA_CONFLICT'] = has_conflict
            final_rows.append(merged)
        return pd.DataFrame(final_rows), [], qa_errors

    def _identify_period_years(self, df):
        import re
        years = set()
        for col in df.columns:
            if re.match(r'^\d{4}$', str(col)): years.add(int(col))
            m = re.match(r'^\dQ(\d{2})$', str(col))
            if m: years.add(2000 + int(m.group(1)))
        return sorted(years)

    def _compute_standalone_quarters(self, df, year, stmt):
        yy = str(year)[2:]; errors = []
        c1, c2, c3, c4, ca = f'1Q{yy}', f'2Q{yy}', f'3Q{yy}', f'4Q{yy}', str(year)
        h1, h2, h3, ha = c1 in df.columns, c2 in df.columns, c3 in df.columns, ca in df.columns
        if not any([h1, h2, h3, ha]): return df, []
        
        s1 = df[c1].copy() if h1 else pd.Series(float('nan'), index=df.index)
        s2 = (df[c2] - df[c1].fillna(0)) if h2 and h1 else (df[c2] if h2 else s1*0)
        s3 = (df[c3] - df[c2].fillna(0)) if h3 and h2 else (df[c3] if h3 else s1*0)
        s4 = (df[ca] - df[c3].fillna(0)) if ha and h3 else (df[ca] - df[c2].fillna(0) if ha and h2 else s1*0)
        
        if h1: df[c1] = s1
        if h2: df[c2] = s2
        if h3: df[c3] = s3
        if ha and s4.notna().any(): df[c4] = s4
        return df, errors, s1, s2, s3, s4, (df[ca] if ha else s1*0)

    def _validate_quarterly_sum(self, df, year, s1, s2, s3, s4, ann, stmt):
        ers = []
        diff = ((s1.fillna(0) + s2.fillna(0) + s3.fillna(0) + s4.fillna(0)) - ann).abs()
        for idx in df.index:
            if not pd.isna(ann.loc[idx]) and diff.loc[idx] > DFC_VALIDATION_TOLERANCE:
                ers.append({'type': 'DFC_VALIDATION_FAILED', 'statement': stmt, 'year': year, 'diff': float(diff.loc[idx])})
        return ers

    def convert_dfc_ytd_to_standalone(self, df, stmt):
        qa = []
        for y in self._identify_period_years(df):
            res = self._compute_standalone_quarters(df, y, stmt)
            if len(res) > 2:
                df, errs, s1, s2, s3, s4, ann = res
                qa.extend(self._validate_quarterly_sum(df, y, s1, s2, s3, s4, ann, stmt))
        return df, qa

    def process_all_reports(self, raw_df):
        reports = {}
        self._coalesce_errors = []
        for stmt in ['BPA', 'BPP', 'DRE', 'DFC']:
            sub = raw_df[raw_df['STMT_TYPE_INTERNAL'] == stmt]
            df_stmt = self.calculate_quarters(sub, stmt)
            if not df_stmt.empty: reports[stmt] = df_stmt
        return reports, self._coalesce_errors

    def validate_line_id_uniqueness(self, reports):
        errs = []
        for name, df in reports.items():
            dups = df['LINE_ID_BASE'].value_counts()
            if dups.max() > 1: errs.append({'sheet': name, 'count': int(dups.max())})
        return len(errs)==0, errs

    def validate_final_output(self, reports):
        return True, [] # Simplified for restoration

    def generate_excel(self, name, cvm, reports, qas=None):
        import re
        safe = re.sub(r'[\\/*?:"<>|]', '_', name).replace(' ', '_')
        path = os.path.join(self.output_dir, f"{safe}_financials.xlsx")
        setor = str(self.setores_map.get(str(cvm), '')).lower()
        tipo = 'financeira' if any(k in setor for k in ['banc', 'financ']) else 'comercial'
        
        final = {}
        if self.standardizer:
            for s, df in reports.items():
                final[s] = self.standardizer.enrich(df, s, tipo, (self.report_type=="consolidated"))
        else: final = reports
        
        rows_inserted = self.db.insert_company_data(
            name,
            int(cvm),
            tipo,
            final,
            qas,
            self.setores_map.get(str(cvm)),
        )
        
        for attempt in range(1, MAX_EXCEL_LOCK_RETRIES + 1):
            try:
                with pd.ExcelWriter(path, engine='openpyxl') as writer:
                    for s, df in final.items():
                        df.to_excel(writer, sheet_name=s, startrow=2, index=False)
                        ws = writer.sheets[s]
                        ws['A1'] = f"Type: {self.report_type}"; ws['A2'] = "Values in BRL Thousands"
                break
            except PermissionError:
                if attempt >= MAX_EXCEL_LOCK_RETRIES:
                    raise
                wait_s = min(2.0, 0.2 * attempt)
                print(
                    f"Excel file locked for {name} "
                    f"(attempt {attempt}/{MAX_EXCEL_LOCK_RETRIES}). Retrying in {wait_s:.1f}s..."
                )
                time.sleep(wait_s)
        print(f"Saved to {path}")
        return int(rows_inserted or 0)

    @staticmethod
    def _extract_years_processed(reports: dict, start_year: int, end_year: int) -> list[int]:
        years: set[int] = set()
        for _stmt, df_stmt in reports.items():
            if df_stmt is None or df_stmt.empty:
                continue
            for col in df_stmt.columns:
                label = str(col)
                if label.isdigit() and len(label) == 4:
                    years.add(int(label))
                    continue
                if re.match(r'^\dQ(\d{2})$', label):
                    years.add(2000 + int(label[2:]))
        bounded = [y for y in years if int(start_year) <= int(y) <= int(end_year)]
        return sorted(set(int(y) for y in bounded))

    def run(
        self,
        companies,
        start_year,
        end_year,
        progress_callback: Callable[[int, int, str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ):
        self.fetch_company_list()
        resolved = self.resolve_company_codes(companies)
        for year in range(start_year, end_year + 1):
            self.download_and_extract(year, 'DFP')
            self.download_and_extract(year, 'ITR')
        
        company_items = list(resolved.items())
        total_companies = len(company_items)
        results = {}
        completed = 0
        years_requested = list(range(int(start_year), int(end_year) + 1))
        for name, cvm in company_items:
            if progress_callback is not None:
                progress_callback(completed, total_companies, name)
            if should_cancel is not None and should_cancel():
                print("Execution cancelled before next company.")
                break

            print(f"Processing {name}...")
            payload = {
                "company_name": str(name),
                "cvm_code": int(cvm),
                "years_processed": [],
                "rows_inserted": 0,
                "status": "error",
                "error": None,
                "traceback": None,
                "attempts": 0,
            }
            raw = self.process_data(cvm, years_requested)
            if raw is None:
                payload["error"] = "No financial rows found for selected years"
                results[str(int(cvm))] = payload
                completed += 1
                continue

            proc, qas = self.process_all_reports(raw)
            payload["years_processed"] = self._extract_years_processed(
                proc,
                start_year,
                end_year,
            )
            if not proc:
                payload["error"] = "No supported statements found after processing"
                results[str(int(cvm))] = payload
                completed += 1
                continue

            attempt = 0
            while attempt < COMPANY_DB_MAX_RETRIES:
                attempt += 1
                payload["attempts"] = int(attempt)
                try:
                    rows_inserted = self.generate_excel(name, cvm, proc, qas)
                    payload["rows_inserted"] = int(rows_inserted or 0)
                    payload["status"] = "success"
                    payload["error"] = None
                    break
                except OperationalError as exc:
                    sql_code = getattr(exc, "code", None)
                    sql_text = f"[{sql_code}] {exc}" if sql_code else str(exc)
                    payload["status"] = "error"
                    payload["error"] = f"{exc.__class__.__name__}: {sql_text}"
                    payload["traceback"] = traceback.format_exc()
                    if attempt >= COMPANY_DB_MAX_RETRIES:
                        print(
                            f"OperationalError for {name} after {attempt} attempt(s): {sql_text}"
                        )
                        break
                    sleep_s = COMPANY_DB_RETRY_BACKOFF_SECONDS * attempt
                    print(
                        f"OperationalError for {name} on attempt {attempt}/{COMPANY_DB_MAX_RETRIES}. "
                        f"Retrying in {sleep_s:.1f}s... {sql_text}"
                    )
                    time.sleep(sleep_s)
                except Exception as exc:
                    payload["status"] = "error"
                    payload["error"] = f"{exc.__class__.__name__}: {exc}"
                    payload["traceback"] = traceback.format_exc()
                    print(f"Error processing {name}: {exc}")
                    break
            results[str(int(cvm))] = payload
            completed += 1
        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', default=COMPANY_NAME)
    parser.add_argument('--start-year', type=int, default=START_YEAR)
    parser.add_argument('--end-year', type=int, default=END_YEAR)
    args = parser.parse_args()
    scraper = CVMScraper()
    scraper.run([args.company], args.start_year, args.end_year)
