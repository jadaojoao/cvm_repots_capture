import pandas as pd
import os

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
DATA_DIR = '../data/input' # Relative to scripts/
PETR_CODE = 9512
# ==============================================================================

print("Checking raw data sources for BPP replication issue...")

# Resolve paths
script_dir = os.path.dirname(os.path.abspath(__file__))
processed_dir = os.path.join(script_dir, DATA_DIR, 'processed')

# PETR4 CVM Code
petr_code = PETR_CODE

# Load 2024 data
print("\n1. Loading 2024 ITR and DFP BPP files...")
try:
    df_itr = pd.read_csv(os.path.join(processed_dir, 'itr_cia_aberta_BPP_con_2024.csv'), sep=';', encoding='latin1')
    df_dfp = pd.read_csv(os.path.join(processed_dir, 'dfp_cia_aberta_BPP_con_2024.csv'), sep=';', encoding='latin1')
    
    petr_itr = df_itr[df_itr['CD_CVM'] == petr_code].copy()
    petr_dfp = df_dfp[df_dfp['CD_CVM'] == petr_code].copy()
    
    print(f"   ITR rows for PETR4: {len(petr_itr)}")
    print(f"   DFP rows for PETR4: {len(petr_dfp)}")
    
    print("\n2. Checking unique reference dates (DT_REFER):")
    print("   ITR dates:", sorted(petr_itr['DT_REFER'].unique()))
    print("   DFP dates:", sorted(petr_dfp['DT_REFER'].unique()))
    
    print("\n3. Sample account check (first account):")
    if len(petr_itr) > 0:
        sample_account = petr_itr.iloc[0]['CD_CONTA']
        sample_desc = petr_itr.iloc[0]['DS_CONTA']
        print(f"   Account: {sample_account} - {sample_desc}")
        
        # Get all records for this account
        itr_acct = petr_itr[petr_itr['CD_CONTA'] == sample_account]
        dfp_acct = petr_dfp[petr_dfp['CD_CONTA'] == sample_account]
        
        print("\n   ITR records for this account:")
        for _, row in itr_acct.iterrows():
            print(f"     {row['DT_REFER']}: {row['VL_CONTA']} (Source: ITR)")
        
        print("\n   DFP records for this account:")
        for _, row in dfp_acct.iterrows():
            print(f"     {row['DT_REFER']}: {row['VL_CONTA']} (Source: DFP)")
    
    print("\n4. Checking column availability:")
    print(f"   ITR columns: {', '.join(df_itr.columns.tolist()[:15])}...")
    
except Exception as e:
    print(f"Error: {e}")

print("\n5. Checking 2025 data availability:")
try:
    df_itr_2025 = pd.read_csv(os.path.join(processed_dir, 'itr_cia_aberta_BPP_con_2025.csv'), sep=';', encoding='latin1')
    petr_itr_2025 = df_itr_2025[df_itr_2025['CD_CVM'] == petr_code]
    print(f"   2025 ITR rows for PETR4: {len(petr_itr_2025)}")
    if len(petr_itr_2025) > 0:
        print(f"   2025 ITR dates: {sorted(petr_itr_2025['DT_REFER'].unique())}")
except Exception as e:
    print(f"   Error loading 2025 ITR: {e}")
