#!/usr/bin/env python3
"""
CVM Financial Data Extractor - Standalone Version
==================================================

Single-file Python script to download, process, and generate Excel reports
from CVM (Comissão de Valores Mobiliários) financial statements.

Features:
- Downloads DFP (annual) and ITR (quarterly) data automatically
- Processes BPA, BPP, DRE, and DFC statements
- Converts DFC/DRE from YTD to standalone quarterly values
- Generates stable LINE_ID_BASE identifiers
- Performs regression tests and QA validation
- Logs TRIMESTRAL_NAO_DIVULGADO cases
- Outputs Excel with QA_LOG sheet

Author: AI Agent  
Date: 2026-02-04
"""

# ============================================================================
# USER CONFIGURATION
# ============================================================================

# Directory where files will be saved
OUTPUT_DIR = "output"
DATA_DIR = "data/input"

# Company to process (name or CVM code)
# Examples: "PETROBRAS", "9512", "VALE", "ITAU"
COMPANY_NAME = "PETROBRAS"

# Year range (inclusive)
START_YEAR = 2021
END_YEAR = 2025

# Report type: "consolidated" or "individual"
REPORT_TYPE = "consolidated"  # Use "consolidated" for most cases

# Force re-download even if files exist
FORCE_REFRESH = False

# Request timeout (seconds)
REQUEST_TIMEOUT = 30

# Enable debug logging (more verbose)
DEBUG_MODE = False

# ============================================================================
# IMPORTS
# ============================================================================

import os
import sys
import requests
import zipfile
import pandas as pd
import numpy as np
import io
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_account_name(name: str) -> str:
    """
    Normalizes account names for consistent comparisons.
    
    Examples:
        "Caixa e Equivalentes" → "caixa e equivalentes"
        "RESULTADO LÍQUIDO   " → "resultado liquido"
    """
    if pd.isna(name) or not isinstance(name, str):
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    # Remove common punctuation
    normalized = normalized.replace('.', '').replace(',', '').replace('(', '').replace(')', '')
    
    return normalized


def generate_line_id_base(row: pd.Series) -> str:
    """
    Generates a stable, deterministic LINE_ID_BASE for each account.
    
    Based on: CD_CONTA + normalized DS_CONTA
    This ensures same account across different periods/versions has same ID.
    
    Args:
        row: DataFrame row with CD_CONTA and DS_CONTA
        
    Returns:
        Stable identifier string (e.g., "1.01_caixa_equivalentes")
    """
    cd_conta = str(row.get('CD_CONTA', ''))
    ds_conta = str(row.get('DS_CONTA', ''))
    
    # Normalize description
    ds_norm = normalize_account_name(ds_conta)
    
    # Create base ID
    if ds_norm:
        # Use first 3 words of normalized description
        words = ds_norm.split()[:3]
        desc_part = '_'.join(words)
        line_id = f"{cd_conta}_{desc_part}"
    else:
        line_id = cd_conta
    
    # Clean up any problematic characters
    line_id = re.sub(r'[^\w\-_.]', '_', line_id)
    
    return line_id


# ============================================================================
# MAIN CVM SCRAPER CLASS
# ============================================================================

class CVMFinancialExtractor:
    """
    Main class for extracting and processing CVM financial data.
    """
    
    BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
    
    def __init__(self, output_dir=OUTPUT_DIR, data_dir=DATA_DIR, report_type=REPORT_TYPE):
        """Initialize the extractor with configuration."""
        self.output_dir = output_dir
        self.data_dir = data_dir
        self.report_type = report_type
        
        # Define suffixes based on report type
        self.suffix = "con" if report_type == "consolidated" else "ind"
        
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Company mapping
        self.companies_map = {}
        
        # Store coalesce errors for QA logging
        self._coalesce_errors = []
    
    # ========================================================================
    # SECTION 1: COMPANY RESOLUTION
    # ========================================================================
    
    def fetch_company_list(self):
        """Downloads and parses the CVM company master list."""
        print("Fetching company list...")
        url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
        
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            df = pd.read_csv(io.BytesIO(response.content), sep=";", encoding="latin1")
            
            for _, row in df.iterrows():
                cvm_code = row['CD_CVM']
                if pd.notna(row['DENOM_SOCIAL']):
                    self.companies_map[row['DENOM_SOCIAL'].upper().strip()] = cvm_code
                if pd.notna(row['DENOM_COMERC']):
                    self.companies_map[row['DENOM_COMERC'].upper().strip()] = cvm_code
            
            print(f"Loaded {len(self.companies_map)} company names.")
            return df
        except Exception as e:
            print(f"Error fetching company list: {e}")
            return None
    
    def resolve_company_codes(self, company_names: List[str]) -> Dict[str, int]:
        """Resolves a list of company names to CVM codes."""
        resolved = {}
        code_to_name = {v: k for k, v in self.companies_map.items()}
        
        for name in company_names:
            # Check if input is already a CVM code
            if name.isdigit():
                cvm_code = int(name)
                company_name = code_to_name.get(cvm_code, f"CVM_{cvm_code}")
                resolved[company_name] = cvm_code
                print(f"Using provided CVM code: {cvm_code} ({company_name})")
                continue
            
            name_upper = name.upper().strip()
            if name_upper in self.companies_map:
                resolved[name] = self.companies_map[name_upper]
            else:
                # Partial match
                matches = [code for k, code in self.companies_map.items() if name_upper in k]
                if matches:
                    resolved[name] = matches[0]
                    print(f"Partial match found for '{name}': {matches[0]}")
                else:
                    print(f"Could not resolve company '{name}'")
        
        return resolved
    
    # ========================================================================
    # SECTION 2: DATA DOWNLOAD & EXTRACTION
    # ========================================================================
    
    def download_and_extract(self, year: int, doc_type: str) -> bool:
        """
        Downloads DFP or ITR zip for a specific year and extracts relevant files.
        
        Args:
            year: Year to download
            doc_type: 'DFP' or 'ITR'
            
        Returns:
            True if successful, False otherwise
        """
        filename = f"{doc_type.lower()}_cia_aberta_{year}.zip"
        url = f"{self.BASE_URL}/{doc_type}/DADOS/{filename}"
        local_zip_path = os.path.join(self.data_dir, filename)
        
        # Download if needed
        if not os.path.exists(local_zip_path) or FORCE_REFRESH:
            print(f"  Downloading {doc_type} {year}...")
            try:
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                with open(local_zip_path, 'wb') as f:
                    f.write(response.content)
                print(f"    Downloaded: {filename}")
            except requests.exceptions.RequestException as e:
                print(f"    Failed to download {filename}: {e}")
                return False
        else:
            print(f"  Using cached: {filename}")
        
        # Extract relevant CSV files
        try:
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    # Extract BPA, BPP, DRE, DFC files for our report type
                    if any(stmt in file for stmt in ['BPA', 'BPP', 'DRE', 'DFC']):
                        if f"_{self.suffix}_" in file and file.endswith('.csv'):
                            extract_path = os.path.join(self.data_dir, file)
                            if not os.path.exists(extract_path) or FORCE_REFRESH:
                                zip_ref.extract(file, self.data_dir)
            return True
        except Exception as e:
            print(f"    Error extracting {filename}: {e}")
            return False
    
    # ========================================================================
    # SECTION 3: DATA PROCESSING
    # ========================================================================
    
    def process_data(self, cvm_code: int, years: List[int]) -> pd.DataFrame:
        """
        Loads and combines all statement data for a company.
        
        Args:
            cvm_code: Company CVM code
            years: List of years to process
            
        Returns:
            Combined DataFrame with all financial data
        """
        all_dfs = []
        
        for year in years:
            for doc_type in ['DFP', 'ITR']:
                for statement in ['BPA', 'BPP', 'DRE', 'DFC']:
                    # Construct filename patterns
                    # CRITICAL: BPA/BPP/DRE use just suffix, Only DFC has _MI_/_MD_ variants
                    if statement == 'DFC':
                        patterns = [
                            f"{doc_type.lower()}_cia_aberta_DFC_MI_{self.suffix}_{year}.csv",
                            f"{doc_type.lower()}_cia_aberta_DFC_MD_{self.suffix}_{year}.csv",
                        ]
                    else:
                        patterns = [
                            f"{doc_type.lower()}_cia_aberta_{statement}_{self.suffix}_{year}.csv",
                        ]
                    
                    for pattern in patterns:
                        filepath = os.path.join(self.data_dir, pattern)
                        if os.path.exists(filepath):
                            try:
                                df = pd.read_csv(filepath, sep=';', encoding='latin1', low_memory=False)
                                
                                # Filter for our company
                                if 'CD_CVM' in df.columns:
                                    df = df[df['CD_CVM'] == cvm_code].copy()
                                    
                                    if not df.empty:
                                        # Add metadata
                                        df['STATEMENT_TYPE'] = statement
                                        df['DOC_TYPE'] = doc_type
                                        df['YEAR'] = year
                                        all_dfs.append(df)
                            except Exception as e:
                                if DEBUG_MODE:
                                    print(f"    Error reading {pattern}: {e}")
        
        if not all_dfs:
            return pd.DataFrame()
        
        combined = pd.concat(all_dfs, ignore_index=True)
        
        # Convert date columns
        for col in ['DT_REFER', 'DT_INI_EXERC', 'DT_FIM_EXERC', 'DT_RECEB', 'DT_ENTREGA']:
            if col in combined.columns:
                combined[col] = pd.to_datetime(combined[col], errors='coerce')
        
        # Convert VL_CONTA to numeric
        if 'VL_CONTA' in combined.columns:
            combined['VL_CONTA'] = pd.to_numeric(combined['VL_CONTA'], errors='coerce')
        
        # Add normalized account name
        combined['DS_CONTA_norm'] = combined['DS_CONTA'].apply(normalize_account_name)
        
        # Generate LINE_ID_BASE
        combined['LINE_ID_BASE'] = combined.apply(generate_line_id_base, axis=1)
        
        return combined
    
    # ========================================================================
    # SECTION 4: VERSION FILTERING
    # ========================================================================
    
    def filter_by_version(self, df: pd.DataFrame, statement_type: str) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Filters data by version, keeping only the latest version per account/period.
        
        Returns:
            Tuple of (filtered_df, qa_logs)
        """
        qa_logs = []
        
        if df.empty:
            return df, qa_logs
        
        initial_count = len(df)
        
        # Handle ORDEM_EXERC if present
        if 'ORDEM_EXERC' in df.columns:
            ordem_values = df['ORDEM_EXERC'].unique()
            if len(ordem_values) > 1:
                print(f"  ⚠️ Warning: Multiple ORDEM_EXERC versions in {statement_type}: {list(ordem_values)}")
                print(f"     Using ORDEM_EXERC='ÚLTIMO' for consistency")
                df = df[df['ORDEM_EXERC'] == 'ÚLTIMO'].copy()
        
        # Group by LINE_ID_BASE + period
        group_cols = ['LINE_ID_BASE', 'DT_REFER']
        
        if all(col in df.columns for col in group_cols):
            # Sort by version-related columns (latest first)
            sort_cols = []
            if 'VERSAO' in df.columns:
                sort_cols.append('VERSAO')
            if 'DT_RECEB' in df.columns:
                sort_cols.append('DT_RECEB')
            if 'DT_ENTREGA' in df.columns:
                sort_cols.append('DT_ENTREGA')
            
            if sort_cols:
                df = df.sort_values(sort_cols, ascending=False)
            
            # Keep first (latest) version per group
            df_filtered = df.groupby(group_cols, as_index=False).first()
            
            filtered_count = initial_count - len(df_filtered)
            
            if filtered_count > 0:
                qa_logs.append({
                    'type': 'VERSION_FILTER',
                    'statement': statement_type,
                    'initial_rows': initial_count,
                    'filtered_rows': len(df_filtered),
                    'removed': filtered_count,
                    'action': f'Kept latest version per account/period'
                })
                
                if DEBUG_MODE:
                    print(f"    Filtered {filtered_count} duplicate versions")
            
            return df_filtered, qa_logs
        
        return df, qa_logs
    
    # ========================================================================
    # SECTION 5: PERIOD LABELING
    # ========================================================================
    
    def _create_period_label(self, row: pd.Series) -> Optional[str]:
        """
        Creates a period label from date columns.
        
        Examples:
            '1Q21', '2Q21', '3Q21', '4Q21', '2021'
            
        Handles both DFC/DRE (with DT_INI_EXERC) and BPA/BPP (using DT_REFER)
        """
        dt_ini = row.get('DT_INI_EXERC')
        dt_fim = row.get('DT_FIM_EXERC')
        dt_refer = row.get('DT_REFER')
        
        # BPA/BPP don't have DT_INI_EXERC, use DT_REFER as reference
        if pd.isna(dt_ini) and pd.notna(dt_refer):
            dt_ini = dt_refer
        
        if pd.isna(dt_fim):
            return None
        
        year = dt_fim.year
        yy = str(year)[2:]
        
        # Check for quarterly vs annual (DFC/DRE path - has DT_INI_EXERC)
        if pd.notna(dt_ini):
            if dt_ini.month == 1 and dt_ini.day == 1:
                if dt_fim.month == 3 and dt_fim.day == 31:
                    return f'1Q{yy}'
                elif dt_fim.month == 6 and dt_fim.day == 30:
                    return f'2Q{yy}'
                elif dt_fim.month == 9 and dt_fim.day == 30:
                    return f'3Q{yy}'
                elif dt_fim.month == 12 and dt_fim.day == 31:
                    return str(year)  # Annual
            
            # Standalone quarters
            elif dt_ini.month == 4 and dt_fim.month == 6:
                return f'2Q{yy}'
            elif dt_ini.month == 7 and dt_fim.month == 9:
                return f'3Q{yy}'
            elif dt_ini.month == 10 and dt_fim.month == 12:
                return f'4Q{yy}'
        
        # BPA/BPP path - infer from DT_FIM_EXERC only
        if dt_fim.month == 3 and dt_fim.day == 31:
            return f'1Q{yy}'
        elif dt_fim.month == 6 and dt_fim.day == 30:
            return f'2Q{yy}'
        elif dt_fim.month == 9 and dt_fim.day == 30:
            return f'3Q{yy}'
        elif dt_fim.month == 12 and dt_fim.day == 31:
            return str(year)  # Annual
        
        return None
    
    def _period_sort_key(self, period_label: str) -> Tuple[int, int]:
        """
        Creates a sort key for chronological ordering of periods.
        
        Examples: '1Q21' < '2Q21' < '3Q21' < '4Q21' < '2021' < '1Q22'
        """
        if not period_label or not isinstance(period_label, str):
            return (9999, 0)
        
        # Annual format: '2021', '2022', etc.
        if period_label.isdigit() and len(period_label) == 4:
            year = int(period_label)
            return (year, 5)  # Annual comes after Q4
        
        # Quarterly format: '1Q21', '2Q22', etc.
        match = re.match(r'(\d)Q(\d{2})', period_label)
        if match:
            quarter = int(match.group(1))
            year_suffix = int(match.group(2))
            full_year = 2000 + year_suffix if year_suffix < 50 else 1900 + year_suffix
            return (full_year, quarter)
        
        return (9999, 0)
    
    # ========================================================================
    # SECTION 6: WIDE FORMAT PIVOT
    # ========================================================================
    
    def calculate_quarters(self, df: pd.DataFrame, report_type: str) -> pd.DataFrame:
        """
        Pivots LONG format data to WIDE format with periods as columns.
        
        Also applies coalescing and YTD-to-standalone conversion.
        """
        if df.empty:
            return df
        
        print(f"  Processing {report_type}...")
        
        # Create period labels
        df['PERIOD'] = df.apply(self._create_period_label, axis=1)
        df = df[df['PERIOD'].notna()].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        # Pivot: LINE_ID_BASE × PERIOD
        df_wide = df.pivot_table(
            index='LINE_ID_BASE',
            columns='PERIOD',
            values='VL_CONTA',
            aggfunc='first'
        )
        
        df_wide = df_wide.reset_index()
        
        # Add metadata columns
        metadata_cols = {
            'CD_CONTA': df.groupby('LINE_ID_BASE')['CD_CONTA'].first(),
            'DS_CONTA': df.groupby('LINE_ID_BASE')['DS_CONTA'].first(),
            'DS_CONTA_norm': df.groupby('LINE_ID_BASE')['DS_CONTA_norm'].first()
        }
        
        for col_name, series in metadata_cols.items():
            df_wide[col_name] = df_wide['LINE_ID_BASE'].map(series)
        
        # Add QA_CONFLICT column (False by default)
        df_wide['QA_CONFLICT'] = False
        
        # CRITICAL: Coalesce duplicate LINE_ID_BASEs
        df_wide, coalesce_logs, coalesce_errors = self.coalesce_duplicate_line_ids(df_wide, report_type)
        
        # Store coalesce errors for QA logging
        self._coalesce_errors.extend(coalesce_errors)
        
        # NEW: Convert DFC/DRE from YTD to standalone
        if report_type in ['DFC', 'DRE']:
            print(f"    Applying YTD→standalone conversion for {report_type}...")
            df_wide, conversion_errors = self.convert_dfc_ytd_to_standalone(df_wide, report_type)
            self._coalesce_errors.extend(conversion_errors)
        
        # Sort columns: metadata first, then periods chronologically
        metadata_cols_list = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']
        metadata_cols_present = [c for c in metadata_cols_list if c in df_wide.columns]
        
        period_cols = [c for c in df_wide.columns if c not in metadata_cols_present]
        period_cols_sorted = sorted(period_cols, key=lambda x: self._period_sort_key(x))
        
        final_cols = metadata_cols_present + period_cols_sorted
        df_wide = df_wide[final_cols]
        
        return df_wide
    
    # ========================================================================
    # SECTION 7: COALESCE DUPLICATES
    # ========================================================================
    
    def coalesce_duplicate_line_ids(self, df_wide: pd.DataFrame, statement_type: str) -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
        """
        Merges duplicate LINE_ID_BASEs by coalescing period columns.
        
        Returns:
            Tuple of (cleaned_df, qa_logs, qa_errors)
        """
        qa_log = []
        qa_errors = []
        
        # Identify period columns
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        
        metadata_cols = [c for c in df_wide.columns if c not in period_cols]
        
        # Find duplicates
        line_id_counts = df_wide['LINE_ID_BASE'].value_counts()
        duplicate_ids = line_id_counts[line_id_counts > 1].index.tolist()
        
        if not duplicate_ids:
            return df_wide, qa_log, qa_errors
        
        coalesced_rows = []
        rows_to_remove = []
        conflicts_detected = 0
        
        for line_id_base in duplicate_ids:
            dup_group = df_wide[df_wide['LINE_ID_BASE'] == line_id_base]
            
            # Start with first row
            merged_row = dup_group.iloc[0].copy()
            has_conflict = False
            
            # Coalesce each period column
            for period_col in period_cols:
                non_null_values = dup_group[period_col].dropna()
                if len(non_null_values) > 1:
                    unique_values = non_null_values.unique()
                    if len(unique_values) > 1:
                        # REAL CONFLICT: different values for same period
                        has_conflict = True
                        conflicts_detected += 1
                        
                        qa_errors.append({
                            'type': 'REAL_CONFLICT',
                            'statement': statement_type,
                            'line_id_base': str(line_id_base),
                            'period': period_col,
                           'values': list(unique_values),
                            'action': 'Took first value - MANUAL REVIEW RECOMMENDED'
                        })
                
                # Take first non-null value
                if len(non_null_values) > 0:
                    merged_row[period_col] = non_null_values.iloc[0]
            
            # Choose canonical DS_CONTA (prefer row with most periods filled, then longest)
            max_filled = 0
            best_desc = merged_row['DS_CONTA']
            
            for idx, row in dup_group.iterrows():
                filled_count = row[period_cols].notna().sum()
                if filled_count > max_filled:
                    max_filled = filled_count
                    best_desc = row['DS_CONTA']
                elif filled_count == max_filled and len(str(row['DS_CONTA'])) > len(str(best_desc)):
                    best_desc = row['DS_CONTA']
            
            merged_row['DS_CONTA'] = best_desc
            merged_row['DS_CONTA_norm'] = normalize_account_name(best_desc)
            merged_row['QA_CONFLICT'] = has_conflict
            
            coalesced_rows.append(merged_row)
            rows_to_remove.extend(dup_group.index.tolist())
        
        # Build final DataFrame
        df_clean = df_wide.drop(index=rows_to_remove)
        df_coalesced = pd.DataFrame(coalesced_rows)
        df_final = pd.concat([df_clean, df_coalesced], ignore_index=True)
        
        # Log summary
        qa_log.append({
            'type': 'COALESCE_DUPLICATES',
            'statement': statement_type,
            'duplicates_found': len(duplicate_ids),
            'conflicts_detected': conflicts_detected,
            'action': f'Merged {len(duplicate_ids)} duplicate LINE_ID_BASEs'
        })
        
        if DEBUG_MODE:
            print(f"      Merged {len(duplicate_ids)} duplicates ({conflicts_detected} had real conflicts)")
        
        return df_final, qa_log, qa_errors
    
    # ========================================================================
    # SECTION 8: DFC YTD → STANDALONE CONVERSION
    # ========================================================================
    
    def convert_dfc_ytd_to_standalone(self, df_wide: pd.DataFrame, statement_type: str) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Converts DFC from YTD (cumulative) to standalone quarterly values.
        
        DFC ITR values are typically YTD:
        - 1Q = YTD 3M
        - 2Q_ytd = YTD 6M  
        - 3Q_ytd = YTD 9M
        
        We convert to standalone:
        - 1Q = YTD_1Q (direct)
        - 2Q = YTD_2Q - YTD_1Q
        - 3Q = YTD_3Q - YTD_2Q
        - 4Q = YYYY - YTD_3Q (prefer annual from DFP)
        - YYYY = annual value (untouched)
        """
        qa_errors = []
        
        if df_wide.empty:
            return df_wide, qa_errors
        
        # Identify period columns
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        
        # Extract unique years
        year_pattern = re.compile(r'^\d{4}$')
        years = set()
        
        for col in period_cols:
            if re.match(r'^\dQ(\d{2})$', col):
                yy = col[-2:]
                year = int('20' + yy) if int(yy) < 50 else int('19' + yy)
                years.add(year)
            elif year_pattern.match(col):
                years.add(int(col))
        
        years = sorted(years)
        
        if DEBUG_MODE:
            print(f"    Converting {statement_type} from YTD to standalone for years: {years}")
        
        df_converted = df_wide.copy()
        
        for year in years:
            yy = str(year)[2:]
            
            # Column names
            col_1q = f'1Q{yy}'
            col_2q = f'2Q{yy}'
            col_3q = f'3Q{yy}'
            col_4q = f'4Q{yy}'
            col_annual = str(year)
            
            # Check which columns exist
            has_1q = col_1q in df_converted.columns
            has_2q = col_2q in df_converted.columns
            has_3q = col_3q in df_converted.columns
            has_4q = col_4q in df_converted.columns
            has_annual = col_annual in df_converted.columns
            
            if not any([has_1q, has_2q, has_3q, has_4q, has_annual]):
                continue
            
            # Store original YTD values
            ytd_1q = df_converted[col_1q].copy() if has_1q else pd.Series([None] * len(df_converted))
            ytd_2q = df_converted[col_2q].copy() if has_2q else pd.Series([None] * len(df_converted))
            ytd_3q = df_converted[col_3q].copy() if has_3q else pd.Series([None] * len(df_converted))
            annual = df_converted[col_annual].copy() if has_annual else pd.Series([None] * len(df_converted))
            
            # Convert to standalone
            standalone_1q = ytd_1q if has_1q else pd.Series([None] * len(df_converted))
            
            # 2Q = YTD_2Q - YTD_1Q
            if has_2q and has_1q:
                standalone_2q = ytd_2q - ytd_1q
            elif has_2q:
                standalone_2q = ytd_2q
            else:
                standalone_2q = pd.Series([None] * len(df_converted))
            
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
                standalone_3q = pd.Series([None] * len(df_converted))
            
            # 4Q = ANNUAL - YTD_3Q
            if has_annual and has_3q:
                standalone_4q = annual - ytd_3q
            elif has_4q:
                standalone_4q = df_converted[col_4q] if has_4q else pd.Series([None] * len(df_converted))
            else:
                standalone_4q = pd.Series([None] * len(df_converted))
                
                if any([has_1q, has_2q, has_3q]):
                    qa_errors.append({
                        'type': 'MISSING_4Q',
                        'statement': statement_type,
                        'year': year,
                        'issue': 'No 4Q data available',
                        'action': '4Q column will be empty for this year'
                    })
            
            # Update DataFrame with standalone values
            if has_1q:
                df_converted[col_1q] = standalone_1q
            if has_2q:
                df_converted[col_2q] = standalone_2q
            if has_3q:
                df_converted[col_3q] = standalone_3q
            
            # Add or update 4Q column
            if standalone_4q.notna().any():
                df_converted[col_4q] = standalone_4q
            
            # Validation: sum(1Q+2Q+3Q+4Q) == YYYY (with tolerance)
            if has_annual:
                quarterly_sum = standalone_1q.fillna(0) + standalone_2q.fillna(0) + standalone_3q.fillna(0) + standalone_4q.fillna(0)
                diff = (quarterly_sum - annual).abs()
                tolerance = 0.01  # 0.01 million BRL
                
                # Check each row individually
                for idx in df_converted.index:
                    annual_val = annual.loc[idx]
                    
                    if pd.isna(annual_val):
                        continue
                    
                    # Check if ALL quarters are NaN for this specific row
                    q1_val = standalone_1q.loc[idx]
                    q2_val = standalone_2q.loc[idx]
                    q3_val = standalone_3q.loc[idx]
                    q4_val = standalone_4q.loc[idx]
                    
                    all_quarters_missing = pd.isna(q1_val) and pd.isna(q2_val) and pd.isna(q3_val) and pd.isna(q4_val)
                    
                    if all_quarters_missing:
                        # TRIMESTRAL_NAO_DIVULGADO: annual exists but no quarterly data
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
                        
                        # Mark QA_CONFLICT for this specific row
                        if 'QA_CONFLICT' in df_converted.columns:
                            df_converted.loc[idx, 'QA_CONFLICT'] = True
                    
                    elif diff.loc[idx] > tolerance:
                        # DFC_VALIDATION_FAILED: sum doesn't match annual
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
                        
                        # Mark QA_CONFLICT
                        if 'QA_CONFLICT' in df_converted.columns:
                            df_converted.loc[idx, 'QA_CONFLICT'] = True
                
                # Summary logging
                trimestral_count = sum(1 for e in qa_errors if e.get('type') == 'TRIMESTRAL_NAO_DIVULGADO' and e.get('year') == year)
                validation_count = sum(1 for e in qa_errors if e.get('type') == 'DFC_VALIDATION_FAILED' and e.get('year') == year)
                
                if DEBUG_MODE:
                    if trimestral_count > 0:
                        print(f"      ⚠️ {trimestral_count} accounts: TRIMESTRAL_NAO_DIVULGADO for {year}")
                    if validation_count > 0:
                        print(f"      ⚠️ {validation_count} accounts: DFC_VALIDATION_FAILED for {year}")
        
        if DEBUG_MODE:
            print(f"      Converted {len(years)} years to standalone values")
        
        return df_converted, qa_errors
    
    # ========================================================================
    # SECTION 9: VALIDATION & REGRESSION TESTS
    # ========================================================================
    
    def validate_final_output(self, processed_reports: Dict[str, pd.DataFrame]) -> Tuple[bool, List[Dict]]:
        """
        Validates final output for regression testing (Priority 2 protection).
        
        Checks:
        1. LINE_ID_BASE uniqueness per sheet
        2. DS_CONTA_norm no nulls
        3. LINE_ID_BASE contains no '#' characters
        4. QA_CONFLICT not 100% True
        5. CD_CONTA no nulls
        """
        errors = []
        
        for sheet_name, df in processed_reports.items():
            if df.empty:
                continue
            
            # Reset index if needed
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
    
    # ========================================================================
    # SECTION 10: PROCESS ALL REPORTS
    # ========================================================================
    
    def process_all_reports(self, raw_df: pd.DataFrame) -> Tuple[Dict[str, pd.DataFrame], List[Dict]]:
        """
        Processes all statement types (BPA, BPP, DRE, DFC).
        
        Returns:
            Tuple of (processed_reports dict, qa_logs list)
        """
        processed = {}
        qa_logs = []
        
        for stmt in ['BPA', 'BPP', 'DRE', 'DFC']:
            df_stmt = raw_df[raw_df['STATEMENT_TYPE'] == stmt].copy()
            
            if df_stmt.empty:
                continue
            
            # Apply version filtering
            df_filtered, version_logs = self.filter_by_version(df_stmt, stmt)
            qa_logs.extend(version_logs)
            
            # Calculate quarters (pivot to wide format)
            df_wide = self.calculate_quarters(df_filtered, stmt)
            
            if not df_wide.empty:
                processed[stmt] = df_wide
        
        return processed, qa_logs
    
    # ========================================================================
    # SECTION 11: EXCEL GENERATION
    # ========================================================================
    
    def generate_excel(self, company_name: str, cvm_code: int, processed_reports: Dict[str, pd.DataFrame], qa_logs: List[Dict] = None):
        """
        Generates Excel file with all statement sheets + QA_LOG.
        """
        filename = f"{company_name}_financials.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"  Generating Excel for {company_name} as {filename}...")
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Write financial statements
                for sheet_name, processed_df in processed_reports.items():
                    df_output = processed_df.reset_index(drop=True)
                    
                    df_output.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
                    ws = writer.sheets[sheet_name]
                    ws['A1'] = f"Report Type: {self.report_type.capitalize()}"
                    ws['A2'] = "Values in BRL Millions | LINE_ID_BASE = Deterministic identifier"
                
                # Write QA log if available
                if qa_logs and len(qa_logs) > 0:
                    qa_df = pd.DataFrame(qa_logs)
                    qa_df.to_excel(writer, sheet_name='QA_LOG', index=False)
                    print(f"  ⚠️ {len(qa_logs)} QA issues logged - review QA_LOG sheet")
            
            print(f"  Saved to {filepath}")
        except Exception as e:
            print(f"  Error generating Excel: {e}")
    
    # ========================================================================
    # SECTION 12: MAIN RUN METHOD
    # ========================================================================
    
    def run(self, company_names: List[str], years: List[int]):
        """
        Main execution method.
        
        Args:
            company_names: List of company names or CVM codes
            years: List of years to process
        """
        print("="*80)
        print(f"CVM Financial Data Extractor - Standalone")
        print("="*80)
        print(f"Companies: {company_names}")
        print(f"Years: {years}")
        print(f"Report Type: {self.report_type}")
        print("="*80)
        
        # 1. Fetch company list
        self.fetch_company_list()
        
        # 2. Resolve company codes
        resolved_companies = self.resolve_company_codes(company_names)
        
        if not resolved_companies:
            print("No valid companies found.")
            return
        
        # 3. Download data
        print("\n" + "="*80)
        print("DOWNLOADING DATA")
        print("="*80)
        
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
        print("DOWNLOAD SUMMARY:")
        print(f"  DFP available: {years_downloaded['DFP']}")
        print(f"  DFP unavailable: {years_failed['DFP']}")
        print(f"  ITR available: {years_downloaded['ITR']}")
        print(f"  ITR unavailable: {years_failed['ITR']}")
        print(f"{'='*80}\n")
        
        # 4. Process each company
        for name, cvm_code in resolved_companies.items():
            print(f"Processing data for {name} (CVM: {cvm_code})...")
            
            # Load raw data
            raw_df = self.process_data(cvm_code, years)
            
            if raw_df is None or raw_df.empty:
                print(f"  No data found for {name}")
                continue
            
            # Process into reports
            processed_reports, qa_logs = self.process_all_reports(raw_df)
            
            # Add coalesce errors to QA logs
            if hasattr(self, '_coalesce_errors') and self._coalesce_errors:
                print(f"  Adding {len(self._coalesce_errors)} coalesce conflicts to QA logs")
                qa_logs.extend(self._coalesce_errors)
                self._coalesce_errors = []
            
            # Run regression tests
            print(f"  Running regression tests...")
            regression_valid, regression_errors = self.validate_final_output(processed_reports)
            if not regression_valid:
                print(f"  ❌ REGRESSION TESTS FAILED: {len(regression_errors)} failures")
                qa_logs.extend(regression_errors)
            else:
                print(f"  ✅ All regression tests passed")
            
            # Generate Excel
            self.generate_excel(name, cvm_code, processed_reports, qa_logs=qa_logs)
        
        print("\n" + "="*80)
        print("PROCESSING COMPLETE")
        print("="*80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create extractor instance
    extractor = CVMFinancialExtractor(
        output_dir=OUTPUT_DIR,
        data_dir=DATA_DIR,
        report_type=REPORT_TYPE
    )
    
    # Run extraction
    extractor.run(
        company_names=[COMPANY_NAME],
        years=list(range(START_YEAR, END_YEAR + 1))
    )
