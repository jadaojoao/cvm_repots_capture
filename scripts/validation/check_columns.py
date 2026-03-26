import pandas as pd
from src.scraper import CVMScraper

# Load raw data
scraper = CVMScraper(output_dir='output', data_dir='input', report_type='consolidated')
raw_df = scraper.load_all_data(['PETROBRAS'], 2024, 2024)

print("Raw DataFrame columns:")
print(list(raw_df.columns))

print("\n\nChecking for version columns:")
for col in ['VERSAO', 'ORDEM_EXERC', 'DT_RECEB']:
    if col in raw_df.columns:
        print(f"✅ {col} exists - sample values: {raw_df[col].dropna().unique()[:5]}")
    else:
        print(f"❌ {col} NOT FOUND")

print("\n\nBPA subset:")
bpa_subset = raw_df[raw_df['FILE_TYPE'].str.contains('BPA')].copy()
print(f"BPA rows: {len(bpa_subset)}")
print("BPA columns:", [c for c in bpa_subset.columns if 'VER' in c.upper() or 'ORDEM' in c.upper() or 'RECEB' in c.upper()])
