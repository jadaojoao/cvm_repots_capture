"""
Debug script to trace DRE duplicate issue
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from src.scraper import CVMScraper

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
# Parameters
START_YEAR = 2024
END_YEAR = 2025
REPORT_TYPE = 'consolidated'
OUTPUT_DIR = '../output' # relative to scripts/
DATA_DIR = '../data/input' # relative to scripts/
CVM_CODE_PETR4 = 9512
# ==============================================================================

# Initialize scraper
scraper = CVMScraper(
    output_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), OUTPUT_DIR)), 
    data_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), DATA_DIR)),
    report_type=REPORT_TYPE
)

# Get raw data for PETR4
print("Loading raw data for PETR4...")
# Note: process_data takes 'years' list
raw_df = scraper.process_data(CVM_CODE_PETR4, [START_YEAR, END_YEAR])

if raw_df is not None:
    # Filter for DRE only
    dre_df = raw_df[raw_df['FILE_TYPE'].str.contains('DRE')].copy()
    
    print(f"\nRaw DRE rows: {len(dre_df)}")
    
    # Check for 3.04.05.07
    target = dre_df[dre_df['CD_CONTA'] == '3.04.05.07'].copy()
    
    if len(target) > 0:
        print(f"\nRows with CD_CONTA='3.04.05.07': {len(target)}")
        print("\nDetailed breakdown:")
        for idx, row in target.iterrows():
            print(f"\n  Row {idx}:")
            print(f"    CD_CONTA: {row['CD_CONTA']}")
            print(f"    DS_CONTA: {row['DS_CONTA'][:60]}")
            if 'DS_CONTA_norm' in row:
                print(f"    DS_CONTA_norm: {row['DS_CONTA_norm'][:60]}")
            print(f"    SOURCE_TYPE: {row.get('SOURCE_TYPE', 'N/A')}")
            print(f"    FILE_TYPE: {row.get('FILE_TYPE', 'N/A')}")
            print(f"    DT_INI_EXERC: {row.get('DT_INI_EXERC', 'N/A')}")
            print(f"    DT_FIM_EXERC: {row.get('DT_FIM_EXERC', 'N/A')}")
            print(f"    VL_CONTA: {row.get('VL_CONTA', 'N/A')}")
    else:
        print("\nNo rows found with CD_CONTA='3.04.05.07'")
        
    # Check if there are any duplicates in raw data
    print("\n\n=== Checking for raw duplicates (same period + CD_CONTA) ===")
    dre_dup_check = dre_df.groupby(['DT_INI_EXERC', 'DT_FIM_EXERC', 'CD_CONTA']).size()
    raw_dups = dre_dup_check[dre_dup_check > 1]
    if len(raw_dups) > 0:
        print(f"Found {len(raw_dups)} CD_CONTAs with raw duplicates")
        for (dt_ini, dt_fim, cd_conta), count in raw_dups.head(5).items():
            print(f"  {cd_conta} [{dt_ini} to {dt_fim}]: {count} rows")
    else:
        print("No raw duplicates found")
else:
    print("Failed to load raw data")
