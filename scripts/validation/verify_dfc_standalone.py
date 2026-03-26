import pandas as pd

print("="*70)
print("DFC/DRE VERIFICATION - PETROBRAS 2024")
print("="*70)

df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)
df_dre = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DRE', header=2)

# Check for 4Q columns
dfc_cols = df_dfc.columns.tolist()
dre_cols = df_dre.columns.tolist()

dfc_4q_cols = [c for c in dfc_cols if '4Q' in str(c)]
dre_4q_cols = [c for c in dre_cols if '4Q' in str(c)]

print(f"\n{'='*70}")
print("4Q COLUMN CHECK:")
print(f"  DFC has 4Q columns: {len(dfc_4q_cols)} → {dfc_4q_cols}")
print(f"  DRE has 4Q columns: {len(dre_4q_cols)} → {dre_4q_cols}")

# Check for annual columns (YYYY)
dfc_annual = [c for c in dfc_cols if str(c).isdigit() and len(str(c)) == 4]
dre_annual = [c for c in dre_cols if str(c).isdigit() and len(str(c)) == 4]

print(f"\nANNUAL COLUMN CHECK:")
print(f"  DFC annual columns: {dfc_annual}")
print(f"  DRE annual columns: {dre_annual}")

# DFC Standalone Verification
# Pick a sample account and check if values are cumulative or standalone
# If standalone: 1Q < 2Q approximately, and sum(Q1-Q4) ≈ annual
# If cumulative: 1Q < 2Q < 3Q < 4Q (strictly increasing)

print(f"\n{'='*70}")
print("DFC STANDALONE VERIFICATION (Sample Account):")

# Find first account with data in all quarters for 2024
sample_idx = None
for idx, row in df_dfc.iterrows():
    if all(pd.notna(row.get(c)) for c in ['1Q24', '2Q24', '3Q24', '2024']):
        sample_idx = idx
        break

if sample_idx is not None:
    row = df_dfc.loc[sample_idx]
    line_id = row['LINE_ID_BASE']
    q1 = row.get('1Q24', 0)
    q2 = row.get('2Q24', 0)
    q3 = row.get('3Q24', 0)
    q4 = row.get('4Q24', 0) if '4Q24' in row.index else 0
    annual = row.get('2024', 0)
    
    quarterly_sum = q1 + q2 + q3 + q4
    is_cumulative = (q1 < q2 < q3) if (q1 and q2 and q3) else False
    sum_matches = abs(quarterly_sum - annual) < 1.0
    
    print(f"  Account: {line_id}")
    print(f"  1Q24: {q1:,.2f}")
    print(f"  2Q24: {q2:,.2f}")
    print(f"  3Q24: {q3:,.2f}")
    print(f"  4Q24: {q4:,.2f}")
    print(f"  2024 (annual): {annual:,.2f}")
    print(f"  Sum(Q1-Q4): {quarterly_sum:,.2f}")
    print(f"  Cumulative pattern (Q1<Q2<Q3): {is_cumulative}")
    print(f"  Sum matches annual: {sum_matches}")
    
    if is_cumulative:
        print(f"  ⚠️ WARNING: Values appear cumulative (YTD), not standalone!")
    else:
        print(f"  ✅ Values appear standalone (not cumulative)")
else:
    print("  ⚠️ Could not find sample account with full 2024 data")

# Regression test summary
print(f"\n{'='*70}")
print("REGRESSION TEST RESULTS:")

has_4q_dfc = len(dfc_4q_cols) > 0
has_4q_dre = len(dre_4q_cols) > 0
has_annual_dfc = len(dfc_annual) > 0
has_annual_dre = len(dre_annual) > 0

print(f"  ✅ DFC has 4Q column" if has_4q_dfc else "  ❌ DFC missing 4Q column")
print(f"  ✅ DRE has 4Q column" if has_4q_dre else "  ❌ DRE missing 4Q column")
print(f"  ✅ DFC has annual columns" if has_annual_dfc else "  ❌ DFC missing annual")
print(f"  ✅ DRE has annual columns" if has_annual_dre else "  ❌ DRE missing annual")

print("="*70)
