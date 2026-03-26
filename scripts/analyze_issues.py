import pandas as pd

# Load existing PETR4 file
print("=" * 80)
print("ANALYZING PETROBRAS_financials.xlsx")
print("=" * 80)

# 1. Check years/columns
print("\n1. YEAR COVERAGE CHECK:")
print("-" * 40)
bpp = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet_name='BPP', header=2, index_col=[0,1])
print(f"BPP Columns: {list(bpp.columns)}")
print(f"Years detected: {sorted(set([col for col in bpp.columns if col.isdigit()]))}")

# 2. Check BPP "cravado" (replicated quarterly data)
print("\n2. BPP REPLICATION CHECK (First 5 rows):")
print("-" * 40)
for i in range(min(5, len(bpp))):
    row = bpp.iloc[i]
    account = bpp.index[i]
    print(f"\nAccount: {account[0]} - {account[1][:50]}")
    
    # Check 2021 data
    if all(col in bpp.columns for col in ['1Q21', '2Q21', '3Q21', '2021']):
        vals = {
            '1Q21': row['1Q21'],
            '2Q21': row['2Q21'],
            '3Q21': row['3Q21'],
            '2021': row['2021']
        }
        print(f"  2021 Data: {vals}")
        # Check if all are equal (cravado)
        unique_vals = set([v for v in vals.values() if pd.notna(v)])
        if len(unique_vals) == 1:
            print(f"  ⚠️ WARNING: All quarters equal! Value={unique_vals.pop()}")
        elif len(unique_vals) > 1:
            print(f"  ✓ OK: Different values detected")
    
    # Check 2024 data
    if all(col in bpp.columns for col in ['1Q24', '2Q24', '3Q24', '2024']):
        vals = {
            '1Q24': row['1Q24'],
            '2Q24': row['2Q24'],
            '3Q24': row['3Q24'],
            '2024': row['2024']
        }
        print(f"  2024 Data: {vals}")
        unique_vals = set([v for v in vals.values() if pd.notna(v)])
        if len(unique_vals) == 1:
            print(f"  ⚠️ WARNING: All quarters equal! Value={unique_vals.pop()}")

# 3. Check BPA totals
print("\n3. BPA TOTALS CONSISTENCY CHECK:")
print("-" * 40)
bpa = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet_name='BPA', header=2, index_col=[0,1])

# Find Total Assets (1), Circulante (1.01), Não Circulante (1.02)
for code in ['1', '1.01', '1.02']:
    try:
        rows = bpa.loc[(code, slice(None)), :]
        if not rows.empty:
            print(f"\nAccount {code}:")
            print(f"  {rows.index[0][1][:60]}")
            # Show a sample year
            if '2024' in bpa.columns:
                print(f"  2024 value: {rows.iloc[0]['2024']}")
    except:
        print(f"\nAccount {code}: NOT FOUND")

# Check if 1 = 1.01 + 1.02 for 2024
try:
    total_2024 = bpa.loc[('1', slice(None)), '2024'].iloc[0]
    circ_2024 = bpa.loc[('1.01', slice(None)), '2024'].iloc[0]
    naocirc_2024 = bpa.loc[('1.02', slice(None)), '2024'].iloc[0]
    
    print(f"\n2024 Math Check:")
    print(f"  Total Assets (1):           {total_2024:,.2f}")
    print(f"  Circulante (1.01):         {circ_2024:,.2f}")
    print(f"  Não Circulante (1.02):     {naocirc_2024:,.2f}")
    print(f"  Sum (1.01 + 1.02):         {circ_2024 + naocirc_2024:,.2f}")
    print(f"  Difference:                 {total_2024 - (circ_2024 + naocirc_2024):,.2f}")
    
    if abs(total_2024 - (circ_2024 + naocirc_2024)) < 0.01:
        print(f"  ✓ OK: Totals match!")
    else:
        print(f"  ⚠️ ERROR: Totals don't match!")
except Exception as e:
    print(f"\nError checking 2024 totals: {e}")

print("\n" + "=" * 80)
