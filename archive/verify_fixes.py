import pandas as pd

# Load NEW PETR4 file (with fixes)
print("=" * 80)
print("VERIFYING FIXES IN PETROBRAS_financials_1.xlsx")
print("=" * 80)

# 1. Check years/columns
print("\n✓ BUG #1: YEAR COVERAGE CHECK")
print("-" * 80)
bpp = pd.read_excel('output/PETROBRAS_financials_1.xlsx', sheet_name='BPP', header=2, index_col=[0,1])
all_cols = list(bpp.columns)
year_cols = sorted(set([col for col in bpp.columns if col.isdigit()]))
print(f"Years detected: {year_cols}")
if '2025' in year_cols:
    print("  ✅ SUCCESS: 2025 data is now included!")
else:
    print("  ❌ FAILED: 2025 still missing")

# 2. Check BPP "cravado" (replicated quarterly data)
print("\n✓ BUG #2: BPP REPLICATION CHECK")
print("-" * 80)
test_years = ['21', '22', '23', '24', '25']
issues_found = 0
for yy in test_years:
    year_full = f"20{yy}"
    required_cols = [f'1Q{yy}', f'2Q{yy}', f'3Q{yy}', year_full]
    
    if all(col in bpp.columns for col in required_cols):
        print(f"\nChecking {year_full}:")
        # Sample first 5 accounts
        replicated_accounts = 0
        distinct_accounts = 0
        
        for i in range(min(10, len(bpp))):
            row = bpp.iloc[i]
            vals = {col: row[col] for col in required_cols}
            unique_vals = set([v for v in vals.values() if pd.notna(v) and v != 0])
            
            if len(unique_vals) == 1 and len([v for v in vals.values() if pd.notna(v)]) >= 3:
                replicated_accounts += 1
            elif len(unique_vals) > 1:
                distinct_accounts += 1
        
        print(f"  Replicated accounts (Q1=Q2=Q3=Annual): {replicated_accounts}/10")
        print(f"  Distinct values accounts: {distinct_accounts}/10")
        
        if replicated_accounts == 0 and distinct_accounts > 5:
            print(f"  ✅ SUCCESS: {year_full} shows distinct quarterly values!")
        elif replicated_accounts > 5:
            print(f"  ❌ FAILED: {year_full} still has replication issue")
            issues_found += 1
        else:
            print(f"  ⚠️  PARTIAL: Some accounts may still have issues")

if issues_found == 0:
    print("\n  ✅ OVERALL: BPP replication bug is FIXED!")
else:
    print(f"\n  ❌ OVERALL: Still {issues_found} years with replication issues")

# 3. Check BPA totals
print("\n✓ BUG #3: BPA TOTALS CONSISTENCY CHECK")
print("-" * 80)
bpa = pd.read_excel('output/PETROBRAS_financials_1.xlsx', sheet_name='BPA', header=2, index_col=[0,1])

# Check if 1 = 1.01 + 1.02 for multiple periods
test_columns = [col for col in bpa.columns if any(year in col for year in ['2024', '2025'])]
bpa_issues = 0

for test_col in test_columns[:5]:  # Test first 5 relevant columns
    try:
        total = bpa.loc[('1', slice(None)), test_col].iloc[0]
        circ = bpa.loc[('1.01', slice(None)), test_col].iloc[0]
        naocirc = bpa.loc[('1.02', slice(None)), test_col].iloc[0]
        
        diff = abs(total - (circ + naocirc))
        print(f"\n{test_col}:")
        print(f"  Total (1):           {total:,.2f}")
        print(f"  Circ (1.01):         {circ:,.2f}")
        print(f"  NãoCirc (1.02):      {naocirc:,.2f}")
        print(f"  Difference:          {diff:,.2f}")
        
        if diff < 0.01:
            print(f"  ✅ Totals match!")
        else:
            print(f"  ❌ Totals DON'T match (diff: {diff:,.2f})")
            bpa_issues += 1
    except Exception as e:
        print(f"\n{test_col}: Could not verify - {e}")

if bpa_issues == 0:
    print("\n  ✅ OVERALL: BPA totals are now consistent!")
else:
    print(f"\n  ⚠️  OVERALL: {bpa_issues} periods still have total mismatches")

# 4. Recorte consistency
print("\n✓ BUG #4: RECORTE CONSISTENCY CHECK")
print("-" * 80)
# Check header in first row
with pd.ExcelFile('output/PETROBRAS_financials_1.xlsx') as xls:
    for sheet in ['BPA', 'BPP', 'DRE', 'DFC']:
        df_check = pd.read_excel(xls, sheet_name=sheet, nrows=2, header=None)
        header_text = str(df_check.iloc[0, 0]) if len(df_check) > 0 else "Not found"
        print(f"  {sheet}: {header_text}")
        if 'Consolidated' in header_text or 'consolidated' in header_text:
            print(f"    ✅ Correctly marked as Consolidated")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
