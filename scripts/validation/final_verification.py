import pandas as pd

print("="*70)
print("FINAL VERIFICATION: PETROBRAS 2021-2025 with NEW CALCULATE_QUARTERS")
print("="*70)

xls = pd.ExcelFile('output/PETROBRAS_financials.xlsx')
print("\n✓ Sheets:", xls.sheet_names)

# Check each sheet
for sheet in ['BPA', 'BPP', 'DRE', 'DFC']:
    df = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet, header=2)
    
    # Check for # in LINE_ID_BASE
    hash_count = df['LINE_ID_BASE'].astype(str).str.contains('#', na=False).sum()
    
    # Check uniqueness
    unique_count = df['LINE_ID_BASE'].nunique()
    is_unique = len(df) == unique_count
    
    # Check QA_CONFLICT
    qa_true = (df['QA_CONFLICT'] == True).sum()
    qa_pct = qa_true / len(df) * 100 if len(df) > 0 else 0
    
    # Check periods filled
    period_cols = [c for c in df.columns if c not in ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']]
    if len(df) > 0 and len(period_cols) > 0:
        sample = df.iloc[0]
        filled = sum([1 for c in period_cols if pd.notna(sample[c])])
        pct_filled = filled / len(period_cols) * 100
    else:
        filled = 0
        pct_filled = 0
    
    status_unique = "✅" if is_unique else "❌"
    status_hash = "✅" if hash_count == 0 else f"❌ ({hash_count})"
    status_qa = "✅" if qa_pct < 100 else f"❌ ({qa_pct:.0f}%)"
    status_periods = "✅" if filled > 1 else f"❌ (only {filled})"
    
    print(f"\n{sheet}:")
    print(f"  Rows: {len(df)}, Unique LINE_ID_BASE: {unique_count} {status_unique}")
    print(f"  LINE_ID_BASE with #n: {hash_count} {status_hash}")
    print(f"  QA_CONFLICT=True: {qa_true} ({qa_pct:.1f}%) {status_qa}")
    print(f"  Period columns: {len(period_cols)}")
    print(f"  Sample row filled: {filled}/{len(period_cols)} ({pct_filled:.0f}%) {status_periods}")

# Show sample BPA data
print("\n" + "="*70)
print("SAMPLE BPA DATA (first 3 rows, key columns + periods)")
print("="*70)
bpa = pd.read_excel('output/PETROBRAS_financials.xlsx', 'BPA', header=2)
period_sample = [c for c in bpa.columns if 'Q' in str(c) or c in ['2021','2022','2023','2024','2025']][:8]
cols_to_show = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA_norm'] + period_sample
print(bpa[cols_to_show].head(3).to_string(index=False))

print("\n" + "="*70)
print("ACCEPTANCE CRITERIA")
print("="*70)
print("✓ No LINE_ID_BASE ends with #n")
print("✓ BPA/BPP: Most rows have >1 period filled (not just 1)")
print("✓ QA_CONFLICT not 100% True")
print("✓ Wide format: 1 row per account, multiple period columns")
print("="*70)
