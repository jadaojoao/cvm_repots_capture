import pandas as pd
import os

# Simulate what the scraper does
print("DEBUGGING: Why is 2025 missing?")
print("=" * 80)

# 1. Check raw files
petr_code = 9512
processed_dir = 'input/processed'
all_data = []

years = [2021, 2022, 2023, 2024, 2025]
suffix = 'con'
pattern = 'BPP_con'

for year in years:
    for doc_type in ['dfp', 'itr']:
        filename = f"{doc_type}_cia_aberta_{pattern}_{year}.csv"
        filepath = os.path.join(processed_dir, filename)
        
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, sep=";", encoding="latin1")
                df_company = df[df['CD_CVM'] == petr_code].copy()
                
                if not df_company.empty:
                    df_company['SOURCE_TYPE'] = doc_type.upper()
                    df_company['YEAR_FILE'] = year
                    all_data.append(df_company)
                    print(f"{year} {doc_type.upper()}: {len(df_company)} rows")
            except Exception as e:
                print(f"{year} {doc_type.upper()}: Error - {e}")

print("\n2. Combined data:")
combined = pd.concat(all_data, ignore_index=True)
print(f"Total rows: {len(combined)}")

# Check dates
combined['DT_REFER'] = pd.to_datetime(combined['DT_REFER'])
years_in_data = sorted(combined['DT_REFER'].dt.year.unique())
print(f"Years in DT_REFER: {years_in_data}")

# Check what happens in calculate_quarters
print("\n3. Years that will be processed:")
print(f"   {years_in_data}")

# Test 2025 specifically
df_2025 = combined[combined['DT_REFER'].dt.year == 2025]
print(f"\n4. 2025 Data:")
print(f"   Rows: {len(df_2025)}")
print(f"   Unique dates: {sorted(df_2025['DT_REFER'].unique())}")
print(f"   Sources: {df_2025['SOURCE_TYPE'].unique()}")

# Check if any accounts exist
print(f"\n5. Sample account from 2025:")
if len(df_2025) > 0:
    sample = df_2025.iloc[0]
    print(f"   CD_CONTA: {sample['CD_CONTA']}")
    print(f"   DS_CONTA: {sample['DS_CONTA']}")
    print(f"   DT_REFER: {sample['DT_REFER']}")
    print(f"   VL_CONTA: {sample['VL_CONTA']}")
