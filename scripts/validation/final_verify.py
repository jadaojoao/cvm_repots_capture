import pandas as pd

xls_file = 'output/PETROBRAS_financials.xlsx'

print("="*60)
print("FINAL VERIFICATION - PETROBRAS 2021-2025")
print("="*60)

# Check row counts and uniqueness
sheets = ['BPA', 'BPP', 'DRE', 'DFC']
for sheet in sheets:
    df = pd.read_excel(xls_file, sheet_name=sheet, header=2)
    id_col = 'LINE_ID' if 'LINE_ID' in df.columns else 'LINE_ID_BASE'
    unique_count = len(df[id_col].unique())
    
    if len(df) == unique_count:
        status = "✅ UNIQUE"
    else:
        status = f"❌ {len(df) - unique_count} DUPS"
    
    print(f"{sheet}: {len(df)} rows, {unique_count} unique {id_col}s - {status}")

# Check QA_LOG
print("\n" + "="*60)
print("QA_LOG SUMMARY")
print("="*60)
qa_log = pd.read_excel(xls_file, sheet_name='QA_LOG')
print(f"Total entries: {len(qa_log)}")
print("\nBy type:")
for qtype, count in qa_log['type'].value_counts().items():
    print(f"  {qtype}: {count}")

# Check period columns    
print("\n" + "="*60)
print("PERIOD COVERAGE (BPA)")
print("="*60)
bpa = pd.read_excel(xls_file, sheet_name='BPA', header=2)
period_cols = [c for c in bpa.columns if 'Q' in str(c) or c in ['2021','2022','2023','2024','2025']]
print(f"Period columns: {len(period_cols)}")
print(f"Range: {period_cols[0] if period_cols else 'N/A'} to {period_cols[-1] if period_cols else 'N/A'}")

# Check for QA_Errors
xls = pd.ExcelFile(xls_file)
if 'QA_Errors' in xls.sheet_names:
    print("\n❌ QA_Errors sheet exists - validation FAILED")
else:
    print("\n✅ No QA_Errors sheet - validation PASSED")

print("="*60)
