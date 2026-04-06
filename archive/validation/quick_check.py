import pandas as pd

xls = pd.ExcelFile('output/PETROBRAS_financials.xlsx')
print("Sheets:", xls.sheet_names)

bpa = pd.read_excel('output/PETROBRAS_financials.xlsx', 'BPA', header=2)
print(f"\nBPA: {len(bpa)} rows")
print(f"Columns ({len(bpa.columns)}): {list(bpa.columns[:10])}")

# Check for #n in LINE_ID_BASE
if 'LINE_ID_BASE' in bpa.columns:
    hash_count = bpa['LINE_ID_BASE'].astype(str).str.contains('#').sum()
    print(f"\nLINE_ID_BASE with #: {hash_count}")
else:
    print("\nNo LINE_ID_BASE column!")

# Check QA_CONFLICT
if 'QA_CONFLICT' in bpa.columns:
    print(f"QA_CONFLICT=True: {bpa['QA_CONFLICT'].sum()}")

# Sample data
print("\nFirst  3 rows (key columns):")
cols_to_show = [c for c in ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT'] if c in bpa.columns]
period_cols = [c for c in bpa.columns if c not in cols_to_show][:5]
print(bpa[cols_to_show + period_cols].head(3))

# Check periods per row
if len(period_cols) > 0:
    sample = bpa.iloc[0]
    filled = sum([1 for c in period_cols if pd.notna(sample[c])])
    print(f"\nSample row (first account): {filled} of {len(period_cols)} periods filled")
