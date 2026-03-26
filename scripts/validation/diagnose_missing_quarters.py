import pandas as pd
import os

"""
Diagnostic script to investigate missing quarterly DFC data.

Checks:
1. Does RAW data have ITR records for problematic CD_CONTA/years?
2. Is it a filtering bug or real absence of data?
3. What periods are available in RAW for these accounts?

Problematic cases from user:
- CD_CONTA=6.01.03.01: 2022 annual exists (-59.147) but 1Q22-4Q22 are NaN
- CD_CONTA=6.03.10: 2023 has 4Q23=-2.669 and annual=-3.644, but 1Q23-3Q23 are NaN
"""

print("="*80)
print("DFC MISSING QUARTERS DIAGNOSTIC")
print("="*80)

# Check if RAW CSV files exist
raw_dir = 'data/input'
if not os.path.exists(raw_dir):
    print(f"\n❌ ERROR: Raw data directory '{raw_dir}' not found")
    print("Cannot diagnose without raw CSV files")
    exit(1)

# Look for DFC files
dfc_files = [f for f in os.listdir(raw_dir) if 'DFC' in f and f.endswith('.csv')]
print(f"\nFound {len(dfc_files)} DFC files in {raw_dir}/")

if len(dfc_files) == 0:
    print("❌ No DFC files found - cannot diagnose")
    exit(1)

# Load all DFC data
all_dfc = []
for filename in dfc_files:
    filepath = os.path.join(raw_dir, filename)
    try:
        df = pd.read_csv(filepath, sep=';', encoding='latin1', low_memory=False)
        all_dfc.append(df)
        print(f"  Loaded: {filename} ({len(df)} rows)")
    except Exception as e:
        print(f"  ⚠️ Error loading {filename}: {e}")

if not all_dfc:
    print("❌ Could not load any DFC files")
    exit(1)

df_raw = pd.concat(all_dfc, ignore_index=True)
print(f"\nTotal RAW DFC records: {len(df_raw):,}")

# Problematic cases
problematic = [
    {'cd_conta': '6.01.03.01', 'year': 2022, 'issue': 'Annual exists but 1Q-4Q missing'},
    {'cd_conta': '6.03.10', 'year': 2023, 'issue': 'Annual + 4Q exist but 1Q-3Q missing'}
]

print(f"\n{'='*80}")
print("INVESTIGATING PROBLEMATIC CASES")
print(f"{'='*80}")

for case in problematic:
    cd_conta = case['cd_conta']
    year = case['year']
    issue = case['issue']
    
    print(f"\n{'-'*80}")
    print(f"CD_CONTA: {cd_conta} | Year: {year}")
    print(f"Issue: {issue}")
    print(f"{'-'*80}")
    
    # Filter for this account
    mask_conta = df_raw['CD_CONTA'] == cd_conta
    df_conta = df_raw[mask_conta].copy()
    
    if df_conta.empty:
        print(f"  ❌ NO RECORDS FOUND for CD_CONTA={cd_conta} in RAW data")
        print(f"     → Company may not disclose this account at all")
        continue
    
    print(f"  ✓ Found {len(df_conta)} total records for this account")
    
    # Convert dates
    for date_col in ['DT_REFER', 'DT_INI_EXERC', 'DT_FIM_EXERC']:
        if date_col in df_conta.columns:
            df_conta[date_col] = pd.to_datetime(df_conta[date_col], errors='coerce')
    
    # Filter for specific year
    if 'DT_REFER' in df_conta.columns:
        mask_year = df_conta['DT_REFER'].dt.year == year
        df_year = df_conta[mask_year]
    elif 'DT_FIM_EXERC' in df_conta.columns:
        mask_year = df_conta['DT_FIM_EXERC'].dt.year == year
        df_year = df_conta[mask_year]
    else:
        print(f"  ⚠️ Cannot filter by year - no date columns")
        df_year = df_conta
    
    if df_year.empty:
        print(f"  ❌ NO RECORDS for year {year}")
        print(f"     → Company did not disclose CD_CONTA={cd_conta} in {year}")
        continue
    
    print(f"\n  Records for {year}:")
    print(f"  {'-'*76}")
    
    # Show key columns
    display_cols = ['DT_REFER', 'DT_INI_EXERC', 'DT_FIM_EXERC', 'VL_CONTA', 
                   'ORDEM_EXERC', 'VERSAO', 'DT_RECEB']
    display_cols = [c for c in display_cols if c in df_year.columns]
    
    for idx, row in df_year.iterrows():
        line = "  "
        for col in display_cols:
            val = row[col]
            if pd.isna(val):
                line += f"{col}=NaN | "
            elif 'DT_' in col:
                line += f"{col}={val.strftime('%Y-%m-%d')} | "
            else:
                line += f"{col}={val} | "
        print(line.rstrip(" | "))
    
    # Identify periods
    print(f"\n  Period Analysis:")
    if 'DT_INI_EXERC' in df_year.columns and 'DT_FIM_EXERC' in df_year.columns:
        for idx, row in df_year.iterrows():
            ini = row['DT_INI_EXERC']
            fim = row['DT_FIM_EXERC']
            if pd.notna(ini) and pd.notna(fim):
                # Identify period type
                if ini.month == 1 and fim.month == 3:
                    period = f"1Q{fim.year%100:02d}"
                elif ini.month == 4 and fim.month == 6:
                    period = f"2Q{fim.year%100:02d}"
                elif ini.month == 7 and fim.month == 9:
                    period = f"3Q{fim.year%100:02d}"
                elif ini.month == 10 and fim.month == 12:
                    period = f"4Q{fim.year%100:02d}"
                elif ini.month == 1 and fim.month == 12:
                    period = f"{fim.year}"
                else:
                    period = f"{ini.strftime('%m/%d')}-{fim.strftime('%m/%d')}"
                
                print(f"    → {period}: VL_CONTA={row['VL_CONTA']:,.2f}")

print(f"\n{'='*80}")
print("DIAGNOSIS COMPLETE")
print(f"{'='*80}")
print("\nNext steps:")
print("1. If ITR records exist but weren't extracted:")
print("   → Fix filtering/join logic in process_data() or calculate_quarters()")
print("2. If ITR records don't exist:")
print("   → Log as 'TRIMESTRAL_NAO_DIVULGADO' in QA_LOG")
print("   → Keep QA_CONFLICT=True only for these specific cases")
print("="*80)
