import pandas as pd

print("="*80)
print("VERIFYING STABLE LINE IDENTIFICATION")
print("="*80)

# Load the Excel output
xls_file = 'output/PETROBRAS_financials.xlsx'
xls = pd.ExcelFile(xls_file)

print("\n1. SHEETS AVAILABLE")
print("-"*80)
print(f"Sheets: {xls.sheet_names}")
has_qa = 'QA_LOG' in xls.sheet_names
print(f"QA_LOG sheet: {'YES' if has_qa else 'NO'}")

# Check BPA columns
print("\n2. BPA COLUMNS (New Structure)")
print("-"*80)
bpa = pd.read_excel(xls_file, sheet_name='BPA', header=2)
print(f"Total columns: {len(bpa.columns)}")
print(f"First 10 columns: {list(bpa.columns[:10])}")

# Check for required columns
required_cols = ['LINE_ID', 'CD_CONTA', 'DS_CONTA']
for col in required_cols:
    status = "FOUND" if col in bpa.columns else "MISSING"
    print(f"  {col}: {status}")

# Check for DS_CONTA_norm
if 'DS_CONTA_norm' in bpa.columns:
    print(f"  DS_CONTA_norm: FOUND")
else:
    print(f"  DS_CONTA_norm: NOT IN OUTPUT (may be internal only)")

# Sample data
print("\n3. SAMPLE DATA (First 5 rows)")
print("-"*80)
display_cols = ['LINE_ID', 'CD_CONTA', 'DS_CONTA']
if 'DS_CONTA_norm' in bpa.columns:
    display_cols.append('DS_CONTA_norm')
print(bpa[display_cols].head(5).to_string())

# Check LINE_ID patterns
print("\n4. LINE_ID PATTERNS")
print("-"*80)
with_cd = bpa[bpa['CD_CONTA'].notna()]['LINE_ID'].head(3)
print("  LINE_IDs with CD_CONTA (should match CD_CONTA):")
for lid, cd in zip(with_cd, bpa[bpa['CD_CONTA'].notna()]['CD_CONTA'].head(3)):
    print(f"    LINE_ID={lid}, CD_CONTA={cd}, Match={str(lid)==str(cd)}")

# Check for hash-based LINE_IDs (without CD_CONTA)
without_cd = bpa[bpa['CD_CONTA'].isna()]
if len(without_cd) > 0:
    print(f"\n  Lines without CD_CONTA: {len(without_cd)}")
    hash_ids = without_cd['LINE_ID'].head(3)
    print("  Sample hash-based LINE_IDs:")
    for lid in hash_ids:
        starts_with_ds = str(lid).startswith('DS|')
        print(f"    {lid} (starts with 'DS|': {starts_with_ds})")
else:
    print(f"\n  No lines without CD_CONTA found (all accounts have codes)")

# Check QA Log
print("\n5. QA LOG CHECK")
print("-"*80)
if has_qa:
    qa = pd.read_excel(xls_file, sheet_name='QA_LOG')
    print(f"QA issues logged: {len(qa)}")
    if len(qa) > 0:
        print(f"\nIssue types:")
        for issue_type in qa['type'].unique():
            count = len(qa[qa['type'] == issue_type])
            print(f"  {issue_type}: {count}")
        
        print(f"\nFirst few QA entries:")
        print(qa[['type','statement','line_id','description','action']].head().to_string())
else:
    print("No QA_LOG sheet - no duplicates or issues detected")

# Verify no phantom lines
print("\n6. PHANTOM LINE CHECK")
print("-"*80)
print(f"Total BPA rows: {len(bpa)}")
print(f"Unique LINE_IDs: {bpa['LINE_ID'].nunique()}")
print(f"All LINE_IDs unique: {len(bpa) == bpa['LINE_ID'].nunique()}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
