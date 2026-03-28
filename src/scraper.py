"""
CVM Financial Data Extractor
=============================

Extracts, processes, and generates Excel reports from CVM financial statements.
"""

# ============================================================================
# USER CONFIGURATION
# ============================================================================

# Company to process (name or CVM code)
# Examples: "PETROBRAS", "9512", "VALE", "ITAU"
COMPANY_NAME = "VALE"

# Year range (inclusive)
START_YEAR = 2020
END_YEAR = 2025

# Report type: "consolidated" or "individual"
REPORT_TYPE = "consolidated"  # Use "consolidated" for most cases

# Output directory
OUTPUT_DIR = "output/reports"

# Data directory (will create input/raw and input/processed subdirectories)
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

# Year interpretation: dois dígitos < Y2K_PIVOT → século 21, >= → século 20
Y2K_PIVOT = 50

# ============================================================================
# IMPORTS
# ============================================================================

import sys
import os

# Ensure project root is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import requests
import zipfile
import pandas as pd
import io
import argparse
from datetime import datetime
from src.utils import normalize_account_name, generate_line_id_base, validate_line_ids
from src.standardizer import AccountStandardizer
from src.database import CVMDatabase

class CVMScraper:
    BASE_URL = os.environ.get(
        'CVM_BASE_URL',
        "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
    )

    def __init__(self, output_dir="output/reports", data_dir="data/input", report_type="consolidated"):
        self.output_dir = output_dir
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")
        self.report_type = report_type
        output_abs = os.path.abspath(self.output_dir)
        if os.path.basename(output_abs).lower() == "reports":
            artifact_root = os.path.dirname(output_abs)
        else:
            artifact_root = output_abs
        self.logs_dir = os.path.join(artifact_root, "logs")
        self.batch_error_log_path = os.path.join(self.logs_dir, "batch_errors.log")
        
        # Define suffixes based on report type
        if self.report_type == "consolidated":
            self.suffix = "con"
        else:
            self.suffix = "ind"
            
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.companies_map = {}
        self.setores_map = {}
        
        # Inicia o padronizador
        canonical_csv_path = os.path.join(current_dir, '..', 'data', 'canonical_accounts.csv')
        self.standardizer = None
        if os.path.exists(canonical_csv_path):
            try:
                self.standardizer = AccountStandardizer(canonical_csv_path)
            except Exception as e:
                print(f"Aviso: Falha ao carregar padronizador: {e}")
                
        # Inicia banco de dados SQLite
        db_path = os.path.join(current_dir, '..', 'data', 'db', 'cvm_financials.db')
        self.db = CVMDatabase(db_path)

    def fetch_company_list(self):
        """Downloads and parses the CVM company master list."""
        print("Fetching company list...")
        url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
        try:
            response = requests.get(url, timeout=COMPANY_LIST_TIMEOUT)
            response.raise_for_status()
            
            df = pd.read_csv(io.BytesIO(response.content), sep=";", encoding="latin1")
            
            social_mask = df['DENOM_SOCIAL'].notna()
            social = df.loc[social_mask].set_index(
                df.loc[social_mask, 'DENOM_SOCIAL'].str.upper().str.strip()
            )['CD_CVM']
            comerc_mask = df['DENOM_COMERC'].notna()
            comerc = df.loc[comerc_mask].set_index(
                df.loc[comerc_mask, 'DENOM_COMERC'].str.upper().str.strip()
            )['CD_CVM']
            self.companies_map = {**social.to_dict(), **comerc.to_dict()}
            
            # Mapeia CD_CVM (como string) para SETOR_ATIV para padronizacao (P4)
            df['CD_CVM_STR'] = df['CD_CVM'].astype(str)
            setor_mask = df['SETOR_ATIV'].notna()
            self.setores_map = df.loc[setor_mask].set_index('CD_CVM_STR')['SETOR_ATIV'].to_dict()

            print(f"Loaded {len(self.companies_map)} company names.")
            return df
        except (requests.RequestException, pd.errors.ParserError, UnicodeDecodeError) as e:
            print(f"Error [{type(e).__name__}] fetching company list: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error [{type(e).__name__}] fetching company list: {e}")
            raise

    def resolve_company_codes(self, company_names):
        """Resolves a list of company names to CVM codes. Supports 'all' and 'topX' args."""
        resolved = {}
        code_to_name = {v: k for k, v in self.companies_map.items()}
        
        # Helper bulk queries
        if len(company_names) == 1:
            q = str(company_names[0]).lower().strip()
            if q == 'all':
                print(f"Batelada: Extraindo universo TOTA de empresas listadas ({len(self.companies_map)})...")
                return {k: v for k, v in self.companies_map.items()}
            elif q.startswith('top') and q[3:].isdigit():
                limit = int(q[3:])
                print(f"Batelada: Extraindo {limit} empresas...")
                return dict(list(self.companies_map.items())[:limit])
                
        for name in company_names:
            if name.isdigit():
                cvm_code = int(name)
                company_name = code_to_name.get(cvm_code, f"CVM_{cvm_code}")
                resolved[company_name] = cvm_code
                print(f"Using provided CVM code: {cvm_code} ({company_name})")
                continue
                
            name_upper = str(name).upper().strip()
            if name_upper in self.companies_map:
                resolved[name] = self.companies_map[name_upper]
            else:
                matches = [code for k, code in self.companies_map.items() if name_upper in k]
                if matches:
                    resolved[name] = matches[0]
                    print(f"Partial match found for '{name}': {matches[0]}")
                else:
                    print(f"Could not resolve company '{name}'")
        return resolved

    def download_and_extract(self, year, doc_type):
        """
        Downloads DFP or ITR zip for a specific year and extracts relevant files.
        """
        filename = f"{doc_type.lower()}_cia_aberta_{year}.zip"
        url = f"{self.BASE_URL}/{doc_type}/DADOS/{filename}"
        local_zip_path = os.path.join(self.raw_dir, filename)
        
        if os.path.exists(local_zip_path):
            print(f"  Skipping download (file exists): {local_zip_path}")
            # Still need to extract? 
            # The original logic extracted only if it downloaded? 
            # Original: download -> write -> extract.
            # If I skip download, I should still extract?
            # Or assume processed files exist?
            # Let's extract to be safe/idempotent.
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    target_files = [
                        f'BPA_{self.suffix}', 
                        f'BPP_{self.suffix}', 
                        f'DRE_{self.suffix}', 
                        f'DFC_MD_{self.suffix}',
                        f'DFC_MI_{self.suffix}'
                    ]
                    if any(x in file for x in target_files):
                        zip_ref.extract(file, self.processed_dir)
            return True

        print(f"Downloading {doc_type} for {year}...")
        
        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            if response.status_code != 200:
                print(f"  ⚠️ File not available at CVM: {url} (Status: {response.status_code})")
                print(f"     This is expected if {year} data hasn't been published yet.")
                return False
                
            with open(local_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    # Extract BPA, BPP, DRE, DFC based on report type suffix
                    # Patterns: BPA_con, BPP_con, DRE_con, DFC_MD_con, DFC_MI_con
                    target_files = [
                        f'BPA_{self.suffix}', 
                        f'BPP_{self.suffix}', 
                        f'DRE_{self.suffix}', 
                        f'DFC_MD_{self.suffix}',
                        f'DFC_MI_{self.suffix}'
                    ]
                    if any(x in file for x in target_files):
                        zip_ref.extract(file, self.processed_dir)
            
            return True
        except (requests.RequestException, zipfile.BadZipFile, OSError, IOError) as e:
            print(f"  Error [{type(e).__name__}] processing {doc_type} {year}: {e}")
            return False
        except Exception as e:
            print(f"  Unexpected error [{type(e).__name__}] processing {doc_type} {year}: {e}")
            raise

    def normalize_units(self, df):
        """Converts values to Millions based on ESCALA_MOEDA."""
        if 'ESCALA_MOEDA' not in df.columns or 'VL_CONTA' not in df.columns:
            return df
            
        def convert(row):
            val = row['VL_CONTA']
            scale = str(row['ESCALA_MOEDA']).upper()
            if scale == 'UNIDADE':
                return val / 1_000_000
            elif scale == 'MIL':
                return val / 1_000
            else: # MILHAO
                return val
                
        df['VL_CONTA'] = df.apply(convert, axis=1)
        return df

    def process_data(self, cvm_code, years):
        """
        Reads CSVs, filters, normalizes, and merges data.
        """
        all_data = []
        file_patterns = [
            f'BPA_{self.suffix}', 
            f'BPP_{self.suffix}', 
            f'DRE_{self.suffix}', 
            f'DFC_MD_{self.suffix}',
            f'DFC_MI_{self.suffix}'
        ]
        
        for year in years:
            for doc_type in ['dfp', 'itr']:
                for pattern in file_patterns:
                    filename = f"{doc_type}_cia_aberta_{pattern}_{year}.csv"
                    filepath = os.path.join(self.processed_dir, filename)
                    
                    if os.path.exists(filepath):
                        try:
                            df = pd.read_csv(filepath, sep=";", encoding="latin1")
                            df_company = df[df['CD_CVM'] == cvm_code].copy()
                            
                            if not df_company.empty:
                                # Data Quality Check: Verify recorte consistency
                                if 'ORDEM_EXERC' in df_company.columns:
                                    unique_ordem = df_company['ORDEM_EXERC'].unique()
                                    if len(unique_ordem) > 1:
                                        print(f"  ⚠️ Warning: Multiple ORDEM_EXERC versions in {filename}: {unique_ordem}")
                                        print(f"     Using ORDEM_EXERC='ÚLTIMO' for consistency...")
                                        df_company = df_company[df_company['ORDEM_EXERC'] == 'ÚLTIMO']
                                
                                # Normalize account names for stable identification
                                df_company['DS_CONTA_raw'] = df_company['DS_CONTA'].copy()
                                df_company['DS_CONTA_norm'] = df_company['DS_CONTA'].apply(normalize_account_name)
                                
                                df_company = self.normalize_units(df_company)
                                df_company['SOURCE_TYPE'] = doc_type.upper()
                                df_company['FILE_TYPE'] = pattern
                                df_company['YEAR_FILE'] = year # Track which file year it came from
                                all_data.append(df_company)
                        except (pd.errors.ParserError, UnicodeDecodeError, FileNotFoundError, OSError) as e:
                            print(f"  Error [{type(e).__name__}] reading {filename}: {e}")
                        except Exception as e:
                            print(f"  Unexpected error [{type(e).__name__}] reading {filename}: {e}")
                            raise
                            
        if not all_data:
            return None
        
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Final data quality check
        print(f"  ✓ Loaded {len(combined_df)} rows for CVM {cvm_code}")
        print(f"  ✓ Report type: {self.report_type} (suffix: {self.suffix})")
        
        return combined_df

    def calculate_quarters(self, df, report_type):
        """
        Pivot LONG format to WIDE format.
        
        Input: LONG DataFrame with 1 row per account+period after VERSION filtering
        Output: WIDE DataFrame with 1 row per account, columns per period
        
        Args:
            df: LONG format DataFrame with LINE_ID_BASE, period columns, VL_CONTA
            report_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            WIDE format DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        # Ensure dates are datetime — warn if any values cannot be parsed
        for _date_col in ['DT_REFER', 'DT_INI_EXERC', 'DT_FIM_EXERC']:
            if _date_col in df.columns:
                _before_nat = df[_date_col].isna().sum()
                df[_date_col] = pd.to_datetime(df[_date_col], errors='coerce')
                _new_nat = df[_date_col].isna().sum() - _before_nat
                if _new_nat > 0:
                    print(f"  WARNING: {_new_nat} valores em {_date_col} não puderam ser interpretados como data em {report_type}")
        
        # Create period label column
        df = df.copy()
        df['PERIOD_LABEL'] = df.apply(lambda row: self._create_period_label(row, report_type), axis=1)
        
        # Remove rows with no valid period label
        _before_drop = len(df)
        df = df[df['PERIOD_LABEL'].notna()]
        _dropped = _before_drop - len(df)
        if _dropped > 0:
            print(f"  WARNING: {_dropped} linhas descartadas em {report_type} — PERIOD_LABEL inválido (verifique _create_period_label)")

        if df.empty:
            return pd.DataFrame()
        
        # Prepare index columns - use LINE_ID_BASE (stable account ID)
        index_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA']
        
        # Prepare metadata to preserve
        metadata_dict = {}
        for col in ['DS_CONTA_norm']:
            if col in df.columns:
                # Get one value per LINE_ID_BASE
                metadata_dict[col] = df.groupby('LINE_ID_BASE')[col].first()
        
        # Pivot: index=account, columns=period, values=VL_CONTA
        df_wide = df.pivot_table(
            index=index_cols,
            columns='PERIOD_LABEL',
            values='VL_CONTA',
            aggfunc='first'  # Should be only 1 value after VERSION filter
        )
        
        # Reset index to make LINE_ID_BASE, CD_CONTA, DS_CONTA regular columns
        df_wide = df_wide.reset_index()
        
        # Add metadata columns
        for col_name, series in metadata_dict.items():
            df_wide[col_name] = df_wide['LINE_ID_BASE'].map(series)
        
        # Add QA_CONFLICT column (False by default - will be set by coalesce if conflicts found)
        df_wide['QA_CONFLICT'] = False
        
        # CRITICAL: Coalesce duplicate LINE_ID_BASEs (merge rows by taking first non-null per period)
        # This ensures 1 row per LINE_ID_BASE in final output
        df_wide, coalesce_logs, coalesce_errors = self.coalesce_duplicate_line_ids(df_wide, report_type)
        
        # Store coalesce errors for later reporting
        if not hasattr(self, '_coalesce_errors'):
            self._coalesce_errors = []
        self._coalesce_errors.extend(coalesce_errors)
        
        # NEW: Convert DFC (and optionally DRE) from YTD to standalone quarterly values
        if report_type in ['DFC', 'DRE']:
            print(f"    Applying YTD→standalone conversion for {report_type}...")
            df_wide, conversion_errors = self.convert_dfc_ytd_to_standalone(df_wide, report_type)
            self._coalesce_errors.extend(conversion_errors)  # Add to same error collection
        
        # Sort columns: metadata first, then periods chronologically
        metadata_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']
        metadata_cols_present = [c for c in metadata_cols if c in df_wide.columns]
        
        period_cols = [c for c in df_wide.columns if c not in metadata_cols_present]
        period_cols_sorted = sorted(period_cols, key=lambda x: self._period_sort_key(x))
        
        final_cols = metadata_cols_present + period_cols_sorted
        df_wide = df_wide[final_cols]
        
        return df_wide
    
    def _create_period_label(self, row, report_type):
        """
        Create period label like '1Q24', '2Q24', '2024' from date columns.
        """
        if report_type in ['BPA', 'BPP']:
            # Use DT_REFER
            dt = row.get('DT_REFER')
            if pd.isna(dt):
                return None
            
            year = dt.year
            yy = str(year)[2:]
            month = dt.month
            
            # Quarter labels
            if month == 3:
                return f'1Q{yy}'
            elif month == 6:
                return f'2Q{yy}'
            elif month == 9:
                return f'3Q{yy}'
            elif month == 12:
                return str(year)  # Annual
            else:
                return None
        
        else:  # DRE, DFC
            # Use DT_INI_EXERC and DT_FIM_EXERC
            dt_ini = row.get('DT_INI_EXERC')
            dt_fim = row.get('DT_FIM_EXERC')
            
            if pd.isna(dt_ini) or pd.isna(dt_fim):
                return None
            
            year = dt_fim.year
            yy = str(year)[2:]
            
            # Check if it's a quarter or annual
            if dt_ini.month == 1 and dt_ini.day == 1:
                if dt_fim.month == 3 and dt_fim.day == 31:
                    return f'1Q{yy}'
                elif dt_fim.month == 6 and dt_fim.day == 30:
                    # Could be 2Q (Apr-Jun) or YTD 6M
                    # Check if start is Jan or Apr
                    return f'2Q{yy}'  # Simplified - assume quarterly
                elif dt_fim.month == 9 and dt_fim.day == 30:
                    return f'3Q{yy}'  # Simplified  
                elif dt_fim.month == 12 and dt_fim.day == 31:
                    return str(year)  # Annual
            
            elif dt_ini.month == 4 and dt_fim.month == 6:
                return f'2Q{yy}'
            elif dt_ini.month == 7 and dt_fim.month == 9:
                return f'3Q{yy}'
            elif dt_ini.month == 10 and dt_fim.month == 12:
                return f'4Q{yy}'
            
            return None  # Unrecognized period
    
    def _period_sort_key(self, period_label):
        """
        Create sort key for period labels to order chronologically.
        Examples: '1Q21' < '2Q21' < '3Q21' < '4Q21' < '2021' < '1Q22'
        """
        if not period_label or not isinstance(period_label, str):
            return (9999, 0)
        
        # Annual format: '2021', '2022', etc.
        if period_label.isdigit() and len(period_label) == 4:
            year = int(period_label)
            return (year, 5)  # Annual comes after Q4
        
        # Quarterly format: '1Q21', '2Q21', etc.
        if len(period_label) >= 3 and period_label[0].isdigit() and period_label[1] == 'Q':
            quarter = int(period_label[0])
            year_part = period_label[2:]
            if year_part.isdigit():
                if len(year_part) == 2:
                    year = 2000 + int(year_part)
                else:
                    year = int(year_part)
                return (year, quarter)
        
        # Unknown format - put at end
        return (9999, 0)
    
    def coalesce_duplicate_line_ids(self, df_wide, statement_type):
        """
        Merge duplicate LINE_ID_BASEs in WIDE format by coalescing period columns.
        
        For each LINE_ID_BASE group:
        - Coalesce period columns (first non-null value)
        - Detect real conflicts (same period, different non-null values)
        - Choose canonical DS_CONTA (longest/most complete)
        
        Args:
            df_wide: WIDE format DataFrame (1+ rows per LINE_ID_BASE)
            statement_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            tuple: (coalesced_df with 1 row per LINE_ID_BASE, qa_log list, qa_errors list)
        """
        import re
        
        qa_log = []
        qa_errors = []
        
        if df_wide.empty or 'LINE_ID_BASE' not in df_wide.columns:
            return df_wide, qa_log, qa_errors
        
        # Identify period columns (regex: ^(\dQ\d{2}|\d{4})$)
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        
        # Metadata columns
        metadata_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']
        metadata_cols = [c for c in metadata_cols if c in df_wide.columns]
        
        # Find duplicates — pre-group once to avoid O(n) scans per duplicate
        grouped = df_wide.groupby('LINE_ID_BASE')
        duplicate_ids = [lid for lid, g in grouped if len(g) > 1]

        if not duplicate_ids:
            print(f"    No duplicate LINE_ID_BASEs in {statement_type} - already unique")
            return df_wide, qa_log, qa_errors

        print(f"    Coalescing {len(duplicate_ids)} duplicate LINE_ID_BASEs in {statement_type}...")

        coalesced_rows = []
        rows_to_remove = []
        conflicts_detected = 0

        for line_id_base, dup_group in grouped:
            if len(dup_group) <= 1:
                continue
            dup_group = dup_group.copy()
            dup_indices = dup_group.index.tolist()
            
            # Start with first row as template
            merged_row = dup_group.iloc[0].copy()
            
            # Track conflicts
            has_conflict = False
            conflict_periods = []
            
            # Coalesce each period column
            for period_col in period_cols:
                non_null_values = dup_group[period_col].dropna()
                
                if len(non_null_values) == 0:
                    # No data for this period
                    merged_row[period_col] = None
                elif len(non_null_values) == 1:
                    # Single value - no conflict
                    merged_row[period_col] = non_null_values.iloc[0]
                else:
                    # Multiple values - check if they're different
                    unique_values = non_null_values.unique()
                    
                    if len(unique_values) == 1:
                        # All same value - no conflict
                        merged_row[period_col] = unique_values[0]
                    else:
                        # REAL CONFLICT: different values for same period
                        has_conflict = True
                        conflict_periods.append(period_col)
                        merged_row[period_col] = non_null_values.iloc[0]  # Take first
                        
                        qa_errors.append({
                            'type': 'REAL_CONFLICT',
                            'statement': statement_type,
                            'line_id_base': str(line_id_base),
                            'period': period_col,
                            'values': unique_values.tolist(),
                            'descriptions': dup_group['DS_CONTA'].unique().tolist(),
                            'action': 'MANUAL REVIEW REQUIRED - same period has different values'
                        })
            
            # Choose canonical DS_CONTA
            # Prefer row with most periods filled
            periods_filled = dup_group[period_cols].notna().sum(axis=1)
            max_filled_idx = periods_filled.idxmax()
            
            # If tied, prefer longest DS_CONTA
            tied_rows = dup_group[periods_filled == periods_filled.max()]
            if len(tied_rows) > 1:
                ds_conta_lengths = tied_rows['DS_CONTA'].str.len()
                canonical_idx = ds_conta_lengths.idxmax()
            else:
                canonical_idx = max_filled_idx
            
            merged_row['DS_CONTA'] = dup_group.loc[canonical_idx, 'DS_CONTA']
            merged_row['CD_CONTA'] = dup_group.loc[canonical_idx, 'CD_CONTA']
            
            # Preserve DS_CONTA_norm from first row
            if 'DS_CONTA_norm' in dup_group.columns:
                merged_row['DS_CONTA_norm'] = dup_group['DS_CONTA_norm'].iloc[0]
            
            # Set QA_CONFLICT flag
            merged_row['QA_CONFLICT'] = has_conflict
            
            if has_conflict:
                conflicts_detected += 1
            
            coalesced_rows.append(merged_row)
            rows_to_remove.extend(dup_indices)
            
        # Build final DataFrame
        df_clean = df_wide.drop(index=rows_to_remove)
        df_coalesced = pd.DataFrame(coalesced_rows)
        df_final = pd.concat([df_clean, df_coalesced], ignore_index=True)
        
        # Log
        qa_log.append({
            'type': 'COALESCE_DUPLICATES',
            'statement': statement_type,
            'duplicates_found': len(duplicate_ids),
            'conflicts_detected': conflicts_detected,
            'action': f'Merged {len(duplicate_ids)} duplicate LINE_ID_BASEs by coalescing periods'
        })
        
        print(f"      Merged {len(duplicate_ids)} duplicates ({conflicts_detected} had real conflicts)")
        
        return df_final, qa_log, qa_errors
    
    def _identify_period_years(self, df_wide):
        """
        Identifica os anos presentes nas colunas de período do DataFrame wide.

        Returns:
            list: Anos ordenados encontrados nas colunas (ex: [2021, 2022, 2023])
        """
        import re
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        year_pattern = re.compile(r'^\d{4}$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        annual_cols = [col for col in period_cols if year_pattern.match(col)]

        years = set()
        for col in period_cols:
            if re.match(r'^\dQ(\d{2})$', col):
                yy = col[-2:]
                year = int('20' + yy) if int(yy) < Y2K_PIVOT else int('19' + yy)
                years.add(year)
        for col in annual_cols:
            years.add(int(col))
        return sorted(years)

    def _compute_standalone_quarters(self, df_converted, year, statement_type):
        """
        Calcula os valores standalone de Q1/Q2/Q3/Q4 a partir dos valores YTD para um dado ano.

        Lógica:
        - 1Q = YTD_1Q (direto)
        - 2Q = YTD_2Q - YTD_1Q
        - 3Q = YTD_3Q - YTD_2Q
        - 4Q = YYYY - YTD_3Q (preferindo fonte anual do DFP)

        Returns:
            tuple: (df_converted atualizado, qa_errors da conversão)
        """
        yy = str(year)[2:]
        qa_errors = []

        col_1q, col_2q, col_3q, col_4q = f'1Q{yy}', f'2Q{yy}', f'3Q{yy}', f'4Q{yy}'
        col_annual = str(year)

        has_1q = col_1q in df_converted.columns
        has_2q = col_2q in df_converted.columns
        has_3q = col_3q in df_converted.columns
        has_4q = col_4q in df_converted.columns
        has_annual = col_annual in df_converted.columns

        if not any([has_1q, has_2q, has_3q, has_4q, has_annual]):
            return df_converted, qa_errors

        import numpy as np
        null_series = pd.Series(np.nan, index=df_converted.index, dtype=float)

        ytd_1q = df_converted[col_1q].copy() if has_1q else null_series
        ytd_2q = df_converted[col_2q].copy() if has_2q else null_series
        ytd_3q = df_converted[col_3q].copy() if has_3q else null_series
        annual = df_converted[col_annual].copy() if has_annual else null_series

        # 1Q stays as-is
        standalone_1q = ytd_1q if has_1q else null_series

        # 2Q = YTD_2Q - YTD_1Q
        if has_2q and has_1q:
            standalone_2q = ytd_2q - ytd_1q
        elif has_2q:
            standalone_2q = ytd_2q
        else:
            standalone_2q = null_series

        # 3Q = YTD_3Q - YTD_2Q
        if has_3q and has_2q:
            standalone_3q = ytd_3q - ytd_2q
        elif has_3q:
            standalone_3q = ytd_3q
            qa_errors.append({
                'type': 'DFC_CONVERSION_WARNING',
                'statement': statement_type,
                'year': year,
                'issue': '3Q present but 2Q missing - cannot convert to standalone',
                'action': 'Kept YTD value for 3Q'
            })
        else:
            standalone_3q = null_series

        # 4Q = ANNUAL - YTD_3Q
        if has_annual and has_3q:
            standalone_4q = annual - ytd_3q
        elif has_4q:
            standalone_4q = df_converted[col_4q]
        else:
            standalone_4q = null_series
            if any([has_1q, has_2q, has_3q]):
                qa_errors.append({
                    'type': 'MISSING_4Q',
                    'statement': statement_type,
                    'year': year,
                    'issue': 'No 4Q data available (neither via annual-3Q nor standalone 4Q)',
                    'action': '4Q column will be empty for this year'
                })

        # Write back standalone values
        if has_1q:
            df_converted[col_1q] = standalone_1q
        if has_2q:
            df_converted[col_2q] = standalone_2q
        if has_3q:
            df_converted[col_3q] = standalone_3q
        if standalone_4q.notna().any():
            df_converted[col_4q] = standalone_4q

        return df_converted, qa_errors, standalone_1q, standalone_2q, standalone_3q, standalone_4q, annual

    def _validate_quarterly_sum(self, df_converted, year, standalone_1q, standalone_2q,
                                 standalone_3q, standalone_4q, annual, statement_type):
        """
        Valida que a soma dos quarters bate com o anual (dentro da tolerância).

        Returns:
            list: qa_errors de validação
        """
        qa_errors = []
        quarterly_sum = (
            standalone_1q.fillna(0) + standalone_2q.fillna(0) +
            standalone_3q.fillna(0) + standalone_4q.fillna(0)
        )
        diff = (quarterly_sum - annual).abs()

        for idx in df_converted.index:
            annual_val = annual.loc[idx]
            if pd.isna(annual_val):
                continue

            q1_val = standalone_1q.loc[idx]
            q2_val = standalone_2q.loc[idx]
            q3_val = standalone_3q.loc[idx]
            q4_val = standalone_4q.loc[idx]
            all_quarters_missing = pd.isna(q1_val) and pd.isna(q2_val) and pd.isna(q3_val) and pd.isna(q4_val)

            if all_quarters_missing:
                line_id = df_converted.loc[idx, 'LINE_ID_BASE'] if 'LINE_ID_BASE' in df_converted.columns else 'Unknown'
                cd_conta = df_converted.loc[idx, 'CD_CONTA'] if 'CD_CONTA' in df_converted.columns else 'Unknown'
                qa_errors.append({
                    'type': 'TRIMESTRAL_NAO_DIVULGADO',
                    'statement': statement_type,
                    'year': year,
                    'line_id_base': str(line_id),
                    'cd_conta': str(cd_conta),
                    'annual': float(annual_val),
                    'action': 'Company does not disclose quarterly data for this account - only annual (DFP) available'
                })
                if 'QA_CONFLICT' in df_converted.columns:
                    df_converted.loc[idx, 'QA_CONFLICT'] = True

            elif diff.loc[idx] > DFC_VALIDATION_TOLERANCE:
                line_id = df_converted.loc[idx, 'LINE_ID_BASE'] if 'LINE_ID_BASE' in df_converted.columns else 'Unknown'
                qa_errors.append({
                    'type': 'DFC_VALIDATION_FAILED',
                    'statement': statement_type,
                    'year': year,
                    'line_id_base': str(line_id),
                    'quarterly_sum': float(quarterly_sum.loc[idx]),
                    'annual': float(annual_val),
                    'difference': float(diff.loc[idx]),
                    'action': 'MANUAL REVIEW - quarterly sum does not match annual'
                })
                if 'QA_CONFLICT' in df_converted.columns:
                    df_converted.loc[idx, 'QA_CONFLICT'] = True

        return qa_errors

    def convert_dfc_ytd_to_standalone(self, df_wide, statement_type):
        """
        Convert DFC from YTD (cumulative) values to standalone quarterly values.

        DFC ITR values are typically YTD:
        - 1Q = YTD 3M
        - 2Q_ytd = YTD 6M
        - 3Q_ytd = YTD 9M

        We need standalone quarters:
        - 1Q = YTD_1Q (direct)
        - 2Q = YTD_2Q - YTD_1Q
        - 3Q = YTD_3Q - YTD_2Q
        - 4Q = YYYY - YTD_3Q (prefer annual from DFP)
        - YYYY = annual value (untouched)

        Args:
            df_wide: WIDE format DataFrame with period columns
            statement_type: 'DFC' or 'DRE'

        Returns:
            tuple: (df_converted, qa_errors list)
        """
        qa_errors = []

        if df_wide.empty:
            return df_wide, qa_errors

        years = self._identify_period_years(df_wide)
        print(f"    Converting {statement_type} from YTD to standalone for years: {years}")

        df_converted = df_wide.copy()

        for year in years:
            result = self._compute_standalone_quarters(df_converted, year, statement_type)
            if len(result) == 2:
                # No data for this year
                df_converted, year_errors = result
                qa_errors.extend(year_errors)
                continue

            df_converted, year_errors, s1q, s2q, s3q, s4q, annual = result
            qa_errors.extend(year_errors)

            col_annual = str(year)
            if col_annual in df_converted.columns:
                validation_errors = self._validate_quarterly_sum(
                    df_converted, year, s1q, s2q, s3q, s4q, annual, statement_type
                )
                qa_errors.extend(validation_errors)

                trimestral_count = sum(1 for e in validation_errors if e.get('type') == 'TRIMESTRAL_NAO_DIVULGADO')
                validation_count = sum(1 for e in validation_errors if e.get('type') == 'DFC_VALIDATION_FAILED')
                if trimestral_count > 0:
                    print(f"      ⚠️ {trimestral_count} accounts: TRIMESTRAL_NAO_DIVULGADO for {year}")
                if validation_count > 0:
                    print(f"      ⚠️ {validation_count} accounts: DFC_VALIDATION_FAILED for {year}")

        print(f"      Converted {len(years)} years to standalone values")
        return df_converted, qa_errors

    def detect_duplicates(self, df, statement_type):
        """
        Detects and handles duplicate accounts within the same period.
        
        Rules:
        - Same period + LINE_ID + identical values → Dedupe (merge bug)
        - Same period + LINE_ID + different values → Flag (data conflict)
        
        Args:
            df: DataFrame with account data
            statement_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            tuple: (cleaned_df, qa_log list)
        """
        qa_log = []
        
        if df.empty or 'LINE_ID_BASE' not in df.columns:
            return df, qa_log
        
        # Define grouping columns based on statement type
        if statement_type in ['BPA', 'BPP']:
            # Balance sheets: group by snapshot date
            group_cols = ['DT_REFER', 'LINE_ID_BASE']
        else:
            # Flow statements: group by period
            group_cols = ['DT_INI_EXERC', 'DT_FIM_EXERC', 'LINE_ID_BASE']
        
        # Add metadata to grouping if available for finer distinction
        for col in ['NIVEL_CONTA', 'GRUPO_DRE']:
            if col in df.columns:
                group_cols.append(col)
        
        # Find duplicates
        df_grouped = df.groupby(group_cols, dropna=False)
        
        rows_to_keep_indices = []
        rows_to_remove_indices = []
        
        for group_key, group_df in df_grouped:
            if len(group_df) <= 1:
                # No duplicates in this group
                rows_to_keep_indices.extend(group_df.index.tolist())
                continue
            
            # Multiple rows with same period + LINE_ID
            values = group_df['VL_CONTA'].values
            unique_values = set([v for v in values if pd.notna(v)])
            
            if len(unique_values) <= 1:
                # Identical values (or all NaN): keep first, remove rest (merge bug)
                rows_to_keep_indices.append(group_df.index[0])
                rows_to_remove_indices.extend(group_df.index[1:].tolist())
                
                qa_log.append({
                    'type': 'DUPLICATE_REMOVED',
                    'statement': statement_type,
                    'line_id_base': group_df.iloc[0]['LINE_ID_BASE'],
                    'cd_conta': group_df.iloc[0].get('CD_CONTA', ''),
                    'description': group_df.iloc[0]['DS_CONTA_raw'] if 'DS_CONTA_raw' in group_df.columns else group_df.iloc[0].get('DS_CONTA', ''),
                    'period': str(group_key[0]) if isinstance(group_key, tuple) else str(group_key),
                    'count': len(group_df),
                    'value': values[0] if len(values) > 0 else None,
                    'action': 'Kept first, removed duplicates (likely merge bug)'
                })
            else:
                # Different values: keep all, flag for manual review
                rows_to_keep_indices.extend(group_df.index.tolist())
                
                qa_log.append({
                    'type': 'DUPLICATE_CONFLICT',
                    'statement': statement_type,
                    'line_id_base': group_df.iloc[0]['LINE_ID_BASE'],
                    'cd_conta': group_df.iloc[0].get('CD_CONTA', ''),
                    'description': group_df.iloc[0]['DS_CONTA_raw'] if 'DS_CONTA_raw' in group_df.columns else group_df.iloc[0].get('DS_CONTA', ''),
                    'period': str(group_key[0]) if isinstance(group_key, tuple) else str(group_key),
                    'count': len(group_df),
                    'values': [float(v) if pd.notna(v) else None for v in values],
                    'action': 'Kept all - MANUAL REVIEW NEEDED (different values for same account)'
                })
        
        # Create cleaned dataframe
        cleaned_df = df.loc[rows_to_keep_indices].copy()
        
        if len(qa_log) > 0:
            removed_count = len(rows_to_remove_indices)
            conflict_count = sum(1 for log in qa_log if log['type'] == 'DUPLICATE_CONFLICT')
            print(f"  ⚠️ Duplicates detected in {statement_type}:")
            print(f"     - Removed {removed_count} duplicate rows (identical values)")
            print(f"     - Flagged {conflict_count} conflicts (different values)")
        
        return cleaned_df, qa_log

    def filter_by_version(self, df, statement_type):
        """
        Filters duplicate rows by keeping only the latest VERSION per account per period.
        
        For same account (LINE_ID_BASE) + same period, keeps the row with:
        - Highest VERSAO (if exists)
        - Latest ORDEM_EXERC (if exists) 
        - Latest DT_RECEB (if exists)
        
        This handles ITR vs DFP duplicates and version updates automatically.
        
        Args:
            df: DataFrame with LINE_ID_BASE column
            statement_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            tuple: (filtered_df, qa_log list)
        """
        qa_log = []
        
        if df.empty or 'LINE_ID_BASE' not in df.columns:
            return df, qa_log
        
        initial_count = len(df)
        
        # Define period columns based on statement type
        if statement_type in ['BPA', 'BPP']:
            period_cols = ['LINE_ID_BASE', 'DT_REFER']
        else:  # DRE, DFC
            period_cols = ['LINE_ID_BASE', 'DT_INI_EXERC', 'DT_FIM_EXERC']
        
        # Build list of sort columns (version indicators)
        sort_cols = []
        for col in ['VERSAO', 'ORDEM_EXERC', 'DT_RECEB']:
            if col in df.columns:
                sort_cols.append(col)
        
        if not sort_cols:
            # No version columns available, can't filter
            print(f"    No version columns found in {statement_type}, skipping version filtering")
            return df, qa_log
        
        # Sort by version columns descending (newest first)
        df_sorted = df.sort_values(
            by=sort_cols,
            ascending=False,
            na_position='last'
        )
        
        # Keep first (latest version) per account+period
        df_filtered = df_sorted.groupby(period_cols, as_index=False).first()
        
        removed_count = initial_count - len(df_filtered)
        
        # ALWAYS log VERSION filtering (even if removed_count=0)
        if removed_count > 0:
            action_msg = f'Filtered {removed_count} duplicate versions - kept latest per account+period'
            print(f"    Filtered {removed_count} duplicate versions (kept latest VERSION/DT_RECEB)")
        else:
            action_msg = f'No duplicate versions found - all records already at latest version'
            print(f"    No duplicate versions to filter (all unique)")
        
        qa_log.append({
            'type': 'VERSION_FILTER',
            'statement': statement_type,
            'removed_count': removed_count,
            'initial_count': initial_count,
            'final_count': len(df_filtered),
            'filter_criteria': ', '.join(sort_cols) if sort_cols else 'N/A',
            'action': action_msg
        })
        
        return df_filtered, qa_log
    
    def detect_true_conflicts(self, df, statement_type):
        """
        After version filtering, detects TRUE conflicts (same account+period with different values).
        
        This should only trigger if there are genuine data conflicts,
        not version duplicates (which should be filtered out first).
        
        Args:
            df: DataFrame after version filtering
            statement_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            tuple: (df_with_flags, qa_log list)
        """
        qa_log = []
        
        if df.empty or 'LINE_ID_BASE' not in df.columns:
            return df, qa_log
        
        # Initialize QA_CONFLICT column
        if 'QA_CONFLICT' not in df.columns:
            df['QA_CONFLICT'] = False
        
        # Define period columns
        if statement_type in ['BPA', 'BPP']:
            period_cols = ['LINE_ID_BASE', 'DT_REFER']
        else:
            period_cols = ['LINE_ID_BASE', 'DT_INI_EXERC', 'DT_FIM_EXERC']
        
        # Check for remaining duplicates
        dup_counts = df.groupby(period_cols).size()
        duplicates = dup_counts[dup_counts > 1]
        
        if len(duplicates) > 0:
            print(f"    ⚠️ Found {len(duplicates)} TRUE CONFLICTS in {statement_type} (after version filtering!)")
            
            for group_key, count in duplicates.items():
                # Get the duplicate rows
                if len(period_cols) == 2:
                    mask = (df['LINE_ID_BASE'] == group_key[0]) & (df[period_cols[1]] == group_key[1])
                else:
                    mask = (df['LINE_ID_BASE'] == group_key[0]) & \
                           (df[period_cols[1]] == group_key[1]) & \
                           (df[period_cols[2]] == group_key[2])
                
                group_df = df[mask]
                
                # Check if values are actually different
                values = group_df['VL_CONTA'].dropna().values
                unique_values = set(values)
                
                if len(unique_values) > 1:
                    # TRUE CONFLICT - different values
                    df.loc[mask, 'QA_CONFLICT'] = True
                    
                    qa_log.append({
                        'type': 'TRUE_CONFLICT',
                        'statement': statement_type,
                        'line_id_base': str(group_key[0]) if isinstance(group_key, tuple) else str(group_key),
                        'period': str(group_key),
                        'count': count,
                        'values': [float(v) for v in unique_values],
                        'descriptions': group_df['DS_CONTA'].unique().tolist(),
                        'action': 'MANUAL REVIEW REQUIRED - Different values for same account+period'
                    })
        
        return df, qa_log


    def process_all_reports(self, df):
        """
        Splits the raw combined DataFrame into report types and calculates quarters.
        Returns a dictionary: {'BPA': df, 'BPP': df, 'DRE': df, 'DFC': df}
        Also returns QA log for data quality issues.
        """
        processed_reports = {}
        all_qa_logs = []
        
        patterns = [
            ('BPA', 'BPA'), 
            ('BPP', 'BPP'), 
            ('DRE', 'DRE'), 
            ('DFC', 'DFC')
        ]
        
        for sheet_name, pattern in patterns:
            subset = df[df['FILE_TYPE'].str.contains(pattern)].copy()
            if subset.empty:
                continue
            
            # Generate LINE_ID_BASE for each row (stable account-level ID)
            # Fast path: use CD_CONTA directly for the majority of rows (vectorized)
            print(f"  Generating LINE_ID_BASE for {sheet_name}...")
            has_cd = subset['CD_CONTA'].notna() & (subset['CD_CONTA'].astype(str).str.strip() != '')
            subset.loc[has_cd, 'LINE_ID_BASE'] = subset.loc[has_cd, 'CD_CONTA'].astype(str).str.strip()
            # Slow path: hash-based ID only for rows without CD_CONTA (rare)
            mask_no_cd = ~has_cd
            if mask_no_cd.any():
                subset.loc[mask_no_cd, 'LINE_ID_BASE'] = subset[mask_no_cd].apply(
                    lambda row: generate_line_id_base(row, sheet_name),
                    axis=1
                )
            
            # Validate that all value-bearing lines have LINE_ID_BASE
            try:
                validate_line_ids(subset)
                print(f"    ✓ All {len(subset)} lines have valid LINE_ID_BASE")
            except ValueError as e:
                print(f"    ✗ Validation failed: {e}")
                all_qa_logs.append({
                    'type': 'VALIDATION_ERROR',
                    'statement': sheet_name,
                    'line_id_base': None,
                    'cd_conta': None,
                    'description': str(e),
                    'period': None,
                    'action': 'Check for missing LINE_ID_BASE'
                })
            
            # CORRECT FLOW: Work in LONG format, filter by VERSION, then pivot to WIDE
            
            # Step 1: Filter by VERSION in LONG format (keep latest per account+period)
            subset_filtered, version_logs = self.filter_by_version(subset, sheet_name)
            all_qa_logs.extend(version_logs)
            
            # Step 2: Calculate quarters (pivot LONG → WIDE)
            processed_df = self.calculate_quarters(subset_filtered, sheet_name)
            processed_reports[sheet_name] = processed_df
            
        return processed_reports, all_qa_logs

    def validate_line_id_uniqueness(self, processed_reports):
        """
        Validates that LINE_ID_BASE is unique within each sheet (after processing).
        
        Args:
            processed_reports: Dictionary of processed dataframes (indexed by LINE_ID_BASE, CD_CONTA, DS_CONTA)
            
        Returns:
            tuple: (is_valid bool, error_report list of dicts)
        """
        errors = []
        
        for sheet_name, df in processed_reports.items():
            # Reset index to access LINE_ID_BASE as column
            df_reset = df.reset_index()
            
            if 'LINE_ID_BASE' not in df_reset.columns:
                continue
            
            # Check for duplicate LINE_ID_BASEs
            line_id_counts = df_reset['LINE_ID_BASE'].value_counts()
            duplicates = line_id_counts[line_id_counts > 1]
            
            if len(duplicates) > 0:
                for line_id_base, count in duplicates.items():
                    dup_rows = df_reset[df_reset['LINE_ID_BASE'] == line_id_base]
                    
                    # Determine which columns have conflicts
                    value_cols = [col for col in dup_rows.columns if col not in 
                                 ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']]
                    conflict_cols = []
                    for col in value_cols:
                        non_null = dup_rows[col].dropna()
                        if len(non_null) > 1 and len(non_null.unique()) > 1:
                            conflict_cols.append(col)
                    
                    errors.append({
                        'sheet': sheet_name,
                        'line_id_base': str(line_id_base),
                        'count': int(count),
                        'cd_conta': str(dup_rows.iloc[0]['CD_CONTA']) if 'CD_CONTA' in dup_rows.columns else None,
                        'descriptions': [str(d) for d in dup_rows['DS_CONTA'].tolist()] if 'DS_CONTA' in dup_rows.columns else [],
                        'conflict_columns': conflict_cols[:10],  # Limit to 10
                        'error': 'LINE_ID_BASE not unique within sheet - CRITICAL'
                    })
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_final_output(self, processed_reports):
        """
        Validate final output for regression testing (Priority 2 protection).
        
        Checks:
        1. LINE_ID_BASE uniqueness per sheet
        2. DS_CONTA_norm no nulls
        3. LINE_ID_BASE contains no '#' characters
        4. QA_CONFLICT not 100% True
        5. CD_CONTA no nulls
        
        Args:
            processed_reports: Dictionary of processed DataFrames
            
        Returns:
            tuple: (is_valid bool, errors list of dicts)
        """
        errors = []
        
        for sheet_name, df in processed_reports.items():
            if df.empty:
                continue
            
            # Reset index if needed to access columns
            if 'LINE_ID_BASE' not in df.columns:
                df = df.reset_index()
            
            # 1. LINE_ID_BASE Uniqueness
            line_id_counts = df['LINE_ID_BASE'].value_counts()
            duplicates = line_id_counts[line_id_counts > 1]
            if len(duplicates) > 0:
                errors.append({
                    'type': 'REGRESSION_TEST_FAILED',
                    'test': 'LINE_ID_BASE_UNIQUENESS',
                    'statement': sheet_name,
                    'error': f'{len(duplicates)} duplicate LINE_ID_BASEs found',
                    'sample': str(duplicates.head(5).to_dict())
                })
            
            # 2. DS_CONTA_norm No Nulls
            if 'DS_CONTA_norm' in df.columns:
                null_count = df['DS_CONTA_norm'].isna().sum()
                if null_count > 0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'DS_CONTA_NORM_NO_NULLS',
                        'statement': sheet_name,
                        'error': f'{null_count} null values in DS_CONTA_norm',
                        'percentage': f'{null_count/len(df)*100:.1f}%'
                    })
            
            # 3. LINE_ID_BASE No '#' Characters
            hash_count = df['LINE_ID_BASE'].astype(str).str.contains('#', na=False).sum()
            if hash_count > 0:
                errors.append({
                    'type': 'REGRESSION_TEST_FAILED',
                    'test': 'LINE_ID_BASE_NO_HASH',
                    'statement': sheet_name,
                    'error': f'{hash_count} LINE_ID_BASEs contain "#" character',
                    'sample': str(df[df['LINE_ID_BASE'].astype(str).str.contains('#', na=False)]['LINE_ID_BASE'].head(5).tolist())
                })
            
            # 4. QA_CONFLICT Not 100% True
            if 'QA_CONFLICT' in df.columns:
                conflict_count = (df['QA_CONFLICT'] == True).sum()
                conflict_pct = conflict_count / len(df) * 100 if len(df) > 0 else 0
                if conflict_pct >= 100.0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'QA_CONFLICT_NOT_100_PCT',
                        'statement': sheet_name,
                        'error': f'QA_CONFLICT is {conflict_pct:.1f}% True (100% indicates broken logic)',
                        'count': int(conflict_count),
                        'total': len(df)
                    })
            
            # 5. CD_CONTA No Nulls
            if 'CD_CONTA' in df.columns:
                null_count = df['CD_CONTA'].isna().sum()
                if null_count > 0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'CD_CONTA_NO_NULLS',
                        'statement': sheet_name,
                        'error': f'{null_count} null values in CD_CONTA',
                        'percentage': f'{null_count/len(df)*100:.1f}%'
                    })
        
        is_valid = len(errors) == 0
        return is_valid, errors

    def generate_excel(self, company_name, cvm_code, processed_reports, qa_logs=None):
        """
        Writes the processed reports dictionary to Excel with QA logging.
        
        Args:
            company_name: Name of the company
            cvm_code: CVM code
            processed_reports: Dictionary of processed dataframes
            qa_logs: List of QA log entries (optional)
        """
        safe_name = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{safe_name}_financials.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"\nExportando dados para {company_name} (CVM {cvm_code})...")
        
        # Avalia o tipo de empresa usando a tabela CVM
        setor = str(self.setores_map.get(str(cvm_code), '')).lower()
        if any(k in setor for k in ['banc', 'financ', 'arrendamento', 'crédito', 'credito']):
            tipo_dinamico = 'financeira'
        elif 'segur' in setor:
            tipo_dinamico = 'seguradora'
        else:
            tipo_dinamico = 'comercial'
            
        # Efetua padronização nos dataframes em memória
        reports_final = {}
        if self.standardizer:
            print(f"  Enriquecendo com plano padrão CVM (tipo inferido: {tipo_dinamico})...")
            for sheet_name, df in processed_reports.items():
                reports_final[sheet_name] = self.standardizer.enrich(
                    df,
                    statement_type=sheet_name,
                    empresa_tipo=tipo_dinamico,
                    is_consolidated=(self.report_type == "consolidated")
                )
        else:
            reports_final = processed_reports
            
        # Exporta para SQLite
        try:
            print("  Gravando no banco de dados SQLite...")
            setor_cvm_val = self.setores_map.get(str(cvm_code)) or None
            inserted = self.db.insert_company_data(
                company_name=company_name,
                cvm_code=int(cvm_code),
                company_type=tipo_dinamico,
                processed_reports=reports_final,
                qa_logs=qa_logs,
                setor_cvm=setor_cvm_val,
            )
            print(f"  ✓ Inseridas {inserted} linhas estruturadas no SQLite")
        except Exception as e:
            print(f"  ❌ Erro gravando no SQLite para {company_name}: {e}")
            
        # Handle file lock para Excel
        base_filename = filename
        counter = 1
        while True:
            if counter > MAX_EXCEL_LOCK_RETRIES:
                raise RuntimeError(
                    f"Cannot write to {base_filename}: file is locked after "
                    f"{MAX_EXCEL_LOCK_RETRIES} retries. Close the file and try again."
                )
            try:
                with open(filepath, 'a'):
                    pass
                break
            except PermissionError:
                filename = f"{safe_name}_financials_{counter}.xlsx"
                filepath = os.path.join(self.output_dir, filename)
                counter += 1
        
        print(f"Generating Excel for {company_name} as {filename}...")
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                reports_to_export = reports_final
                
                # Write financial statements
                for sheet_name, processed_df in reports_to_export.items():
                    # Reset index to expose LINE_ID, CD_CONTA, DS_CONTA, DS_CONTA_norm as columns
                    df_output = processed_df.reset_index()
                    
                    df_output.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
                    ws = writer.sheets[sheet_name]
                    ws['A1'] = f"Report Type: {self.report_type.capitalize()}"
                    ws['A2'] = "Values in BRL Millions | LINE_ID = Deterministic identifier"
                
                # Write Padrão de Cobertura (se disponível)
                if self.standardizer:
                    coverage_report = self.standardizer.coverage_report(reports_to_export)
                    
                    # Constrói DF para a aba PADRONIZACAO
                    cov_rows = []
                    for stmt, info in coverage_report.items():
                        cov_rows.append({
                            'Demonstração': stmt,
                            'Total Linhas': info['total_linhas'],
                            'Mapeadas (Plano CVM)': info['mapeadas'],
                            'Cobertura (%)': info['pct_cobertura'],
                            'Exemplos não mapeados (Discricionários)': ", ".join(info['nao_mapeadas_CD_CONTA'][:5])
                        })
                    
                    if cov_rows:
                        df_cov = pd.DataFrame(cov_rows)
                        df_cov.to_excel(writer, sheet_name='PADRONIZACAO', index=False)
                        print(f"  ✓ Aba PADRONIZACAO adicionada (verifique a cobertura por aba)")

                # Write QA log — always present for auditability (empty if no events)
                qa_df = pd.DataFrame(qa_logs) if qa_logs else pd.DataFrame(
                    columns=['type', 'statement', 'action']
                )

                # Separate critical validation errors from normal QA logs
                validation_errors = qa_df[qa_df['type'] == 'VALIDATION_ERROR'] if len(qa_df) > 0 else qa_df
                other_logs = qa_df[qa_df['type'] != 'VALIDATION_ERROR'] if len(qa_df) > 0 else qa_df

                # Always write QA_LOG (even empty — allows auditors to confirm pipeline ran)
                other_logs.to_excel(writer, sheet_name='QA_LOG', index=False)
                if len(other_logs) > 0:
                    print(f"  ⚠️ {len(other_logs)} QA issues logged - review QA_LOG sheet")
                else:
                    print(f"  ✓ QA_LOG: no issues detected")

                # Write critical validation errors to separate sheet
                if len(validation_errors) > 0:
                    validation_errors.to_excel(writer, sheet_name='QA_Errors', index=False)
                    print(f"  CRITICAL: {len(validation_errors)} validation errors - see QA_Errors sheet")
            
            print(f"Saved to {filepath}")
            
            # Summary of what was saved
            if qa_logs:
                duplicates_removed = sum(1 for log in qa_logs if log['type'] == 'DUPLICATE_REMOVED')
                conflicts = sum(1 for log in qa_logs if log['type'] == 'DUPLICATE_CONFLICT')
                if duplicates_removed > 0:
                    print(f"  📊 Data Quality: Removed {duplicates_removed} duplicate entries")
                if conflicts > 0:
                    print(f"  ⚠️ ATTENTION: {conflicts} conflicts require manual review")
                    
        except (PermissionError, OSError) as e:
            print(f"Error [{type(e).__name__}] writing Excel {filename}: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error [{type(e).__name__}] writing Excel {filename}: {e}")
            raise

    def run(self, companies, start_year, end_year):
        """
        Main execution method.
        """
        self.fetch_company_list()
        resolved_companies = self.resolve_company_codes(companies)
        
        years = list(range(start_year, end_year + 1))
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING DATA FOR YEARS: {years}")
        print(f"{'='*80}")
        
        years_downloaded = {'DFP': [], 'ITR': []}
        years_failed = {'DFP': [], 'ITR': []}
        
        for year in years:
            dfp_success = self.download_and_extract(year, 'DFP')
            itr_success = self.download_and_extract(year, 'ITR')
            
            if dfp_success:
                years_downloaded['DFP'].append(year)
            else:
                years_failed['DFP'].append(year)
                
            if itr_success:
                years_downloaded['ITR'].append(year)
            else:
                years_failed['ITR'].append(year)
        
        print(f"\n{'='*80}")
        print(f"DOWNLOAD SUMMARY:")
        print(f"  DFP available: {years_downloaded['DFP']}")
        print(f"  DFP unavailable: {years_failed['DFP']}")
        print(f"  ITR available: {years_downloaded['ITR']}")
        print(f"  ITR unavailable: {years_failed['ITR']}")
        print(f"{'='*80}\n")
            
        results = {}
        failure_log = []
        for name, cvm_code in resolved_companies.items():
            print(f"Processing data for {name} (CVM: {cvm_code})...")
            try:
                # 1. Get Raw Data
                raw_df = self.process_data(cvm_code, years)
                
                if raw_df is None or raw_df.empty:
                    print(f"  No data found for {name} across all requested years.")
                    continue
                    
                # 2. Process into Reports (Calculate Quarters) - now returns QA logs
                processed_reports, qa_logs = self.process_all_reports(raw_df)
                
                # 2.5. Add coalesce errors to QA logs (from calculate_quarters → coalesce step)
                if hasattr(self, '_coalesce_errors') and self._coalesce_errors:
                    print(f"  Adding {len(self._coalesce_errors)} coalesce conflicts to QA logs")
                    qa_logs.extend(self._coalesce_errors)
                    # Clear for next run
                    self._coalesce_errors = []
                
                # 2.75. NEW: Regression Tests (Priority 2 protection)
                print(f"  Running regression tests...")
                regression_valid, regression_errors = self.validate_final_output(processed_reports)
                if not regression_valid:
                    print(f"  ❌ REGRESSION TESTS FAILED: {len(regression_errors)} failures")
                    qa_logs.extend(regression_errors)
                else:
                    print(f"  ✅ All regression tests passed")
                
                # 3. Validate LINE_ID uniqueness (final check - legacy, kept for compatibility)
                is_valid, validation_errors = self.validate_line_id_uniqueness(processed_reports)
                
                if not is_valid:
                    print(f"  ❌ VALIDATION FAILED: {len(validation_errors)} LINE_ID_BASE uniqueness errors")
                    for err in validation_errors:
                        qa_logs.append({
                            'type': 'VALIDATION_ERROR',
                            'statement': err['sheet'],
                            'line_id_base': err['line_id_base'],
                            'cd_conta': err['cd_conta'],
                            'description': f"Duplicate LINE_ID_BASE in {err['sheet']}: {err['descriptions']}",
                            'count': err['count'],
                            'conflict_columns': err.get('conflict_columns', []),
                            'action': 'CRITICAL: LINE_ID_BASE must be unique within sheet'
                        })
                else:
                    print(f"  ✓ LINE_ID_BASE uniqueness validated - all sheets OK")
                
                # 4. Generate Standard Excel (with QA logs) and Insert to SQLite
                self.generate_excel(name, cvm_code, processed_reports, qa_logs)
                
                results[name] = {
                    'cvm_code': cvm_code, 
                    'reports': processed_reports,
                    'raw_data': raw_df,
                    'qa_logs': qa_logs
                }
                
            except Exception as e:
                import traceback
                print(f"  ❌ CRITICAL FAILURE FOR {name}: {e}")
                failure_log.append(f"{name} (CVM {cvm_code}): {str(e)}")
                traceback.print_exc()
                continue
                
        if failure_log:
            with open(self.batch_error_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- BATCH ERRORS {datetime.now()} ---\n")
                f.write("\n".join(failure_log))
            print(f"\nAttention: {len(failure_log)} companies failed during batch. Check {self.batch_error_log_path}")
            
        return results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Main execution using USER CONFIGURATION parameters.
    
    To customize: Edit the USER CONFIGURATION block at the top of this file.
    
    To run:
        python src/scraper.py
    
    Or with command line arguments (overrides USER CONFIGURATION):
        python src/scraper.py --company VALE --start-year 2020 --end-year 2024
    """
    
    # Parse command line arguments (optional - overrides USER CONFIGURATION)
    parser = argparse.ArgumentParser(description='Extract CVM financial data')
    parser.add_argument('--company', type=str, help=f'Company name or CVM code (default: {COMPANY_NAME})')
    parser.add_argument('--start-year', type=int, help=f'Start year (default: {START_YEAR})')
    parser.add_argument('--end-year', type=int, help=f'End year (default: {END_YEAR})')
    parser.add_argument('--report-type', type=str, choices=['consolidated', 'individual'], 
                        help=f'Report type (default: {REPORT_TYPE})')
    parser.add_argument('--output-dir', type=str, help=f'Output directory (default: {OUTPUT_DIR})')
    parser.add_argument('--data-dir', type=str, help=f'Data directory (default: {DATA_DIR})')
    parser.add_argument('--force-refresh', action='store_true', help='Force re-download')
    
    args = parser.parse_args()
    
    # Use command line args if provided, otherwise use USER CONFIGURATION
    company = args.company if args.company else COMPANY_NAME
    start_year = args.start_year if args.start_year else START_YEAR
    end_year = args.end_year if args.end_year else END_YEAR
    report_type = args.report_type if args.report_type else REPORT_TYPE
    output_dir = args.output_dir if args.output_dir else OUTPUT_DIR
    data_dir = args.data_dir if args.data_dir else DATA_DIR
    force_refresh = args.force_refresh if args.force_refresh else FORCE_REFRESH
    
    # Print configuration
    print("="*80)
    print("CVM Financial Data Extractor")
    print("="*80)
    print(f"Company: {company}")
    print(f"Years: {start_year}-{end_year}")
    print(f"Report Type: {report_type}")
    print(f"Output Directory: {output_dir}")
    print(f"Data Directory: {data_dir}")
    print(f"Force Refresh: {force_refresh}")
    print("="*80)
    print()
    
    # Create scraper instance
    scraper = CVMScraper(
        output_dir=output_dir, 
        data_dir=data_dir, 
        report_type=report_type
    )
    
    # Run extraction
    # run method expects: companies (list), start_year (int), end_year (int)
    results = scraper.run([company], start_year, end_year)
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)

