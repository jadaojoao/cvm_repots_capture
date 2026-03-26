import pandas as pd
import os

print("="*80)
print("INVESTIGATING RAW CSV FOR MISSING DFC QUARTERS")
print("="*80)

# First, get the problematic CD_CONTAs from the output
df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)
conflict_rows = df_dfc[df_dfc['QA_CONFLICT'] == True]

problematic_accounts = []
for idx, row in conflict_rows.iterrows():
    cd_conta = row['CD_CONTA']
    problematic_accounts.append(cd_conta)

print(f"\nFound {len(problematic_accounts)} accounts with QA_CONFLICT=True:")
for acc in problematic_accounts:
    print(f"  - {acc}")

# Now search RAW CSV files for these accounts
print(f"\n{'='*80}")
print("SEARCHING RAW CSV FILES...")
print(f"{'='*80}")

# Load ITR DFC files (where quarterly data comes from)
itr_files = [
    'data/input/itr_cia_aberta_DFC_MI_con_2022.csv',
    'data/input/itr_cia_aberta_DFC_MI_con_2023.csv',
]

for filepath in itr_files:
    if not os.path.exists(filepath):
        print(f"\n⚠️ File not found: {filepath}")
        continue
    
    print(f"\n{'-'*80}")
    print(f"Checking: {os.path.basename(filepath)}")
    print(f"{'-'*80}")
    
    try:
        df_raw = pd.read_csv(filepath, sep=';', encoding='latin1', low_memory=False)
        print(f"  Total rows: {len(df_raw):,}")
        
        # Filter for PETROBRAS (CVM code)
        # First, check column names
        if 'CD_CVM' in df_raw.columns:
            df_petro = df_raw[df_raw['CD_CVM'] == 9512]
        elif 'CNPJ_CIA' in df_raw.columns:
            # Try by CNPJ if CVM code not available
            df_petro = df_raw[df_raw['CNPJ_CIA'].astype(str).str.contains('33000167', na=False)]
        else:
            print(f"  ⚠️ Cannot filter by company - no CD_CVM or CNPJ_CIA column")
            continue
        
        print(f"  PETROBRAS rows: {len(df_petro):,}")
        
        if df_petro.empty:
            print(f"  ⚠️ No PETROBRAS data found")
            continue
        
        # Check for problematic accounts
        for cd_conta in problematic_accounts:
            df_conta = df_petro[df_petro['CD_CONTA'] == cd_conta]
            
            if not df_conta.empty:
                print(f"\n  CD_CONTA={cd_conta}: {len(df_conta)} records found")
                
                # Show period information
                for idx, rec in df_conta.iterrows():
                    dt_ini = rec.get('DT_INI_EXERC', 'N/A')
                    dt_fim = rec.get('DT_FIM_EXERC', 'N/A')
                    vl_conta = rec.get('VL_CONTA', 0)
                    ordem = rec.get('ORDEM_EXERC', 'N/A')
                    
                    print(f"    {dt_ini} → {dt_fim} | VL={vl_conta:,.2f} | ORDEM={ordem}")
            else:
                print(f"\n  CD_CONTA={cd_conta}: ❌ NOT FOUND in this file")
    
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")

# Also check DFP (annual) files
print(f"\n{'='*80}")
print("CHECKING DFP (ANNUAL) FILES FOR COMPARISON")
print(f"{'='*80}")

dfp_files = [
    'data/input/dfp_cia_aberta_DFC_MI_con_2022.csv',
    'data/input/dfp_cia_aberta_DFC_MI_con_2023.csv',
]

for filepath in dfp_files:
    if not os.path.exists(filepath):
        continue
    
    print(f"\n{os.path.basename(filepath)}:")
    
    try:
        df_raw = pd.read_csv(filepath, sep=';', encoding='latin1', low_memory=False)
        
        if 'CD_CVM' in df_raw.columns:
            df_petro = df_raw[df_raw['CD_CVM'] == 9512]
        else:
            continue
        
        for cd_conta in problematic_accounts:
            df_conta = df_petro[df_petro['CD_CONTA'] == cd_conta]
            
            if not df_conta.empty:
                vl_conta = df_conta.iloc[0].get('VL_CONTA', 0)
                print(f"  CD_CONTA={cd_conta}: Annual VL_CONTA={vl_conta:,.2f}")
    
    except Exception as e:
        print(f"  Error: {e}")

print(f"\n{'='*80}")
print("DIAGNOSIS:")
print(f"{'='*80}")
print("If account found in DFP but NOT in ITR:")
print("  → Company doesn't disclose this account quarterly")
print("  → Log as 'TRIMESTRAL_NAO_DIVULGADO'")
print("\nIf account found in BOTH DFP and ITR:")
print("  → Bug in processing pipeline")
print("  → Need to fix extraction/filtering logic")
print("="*80)
