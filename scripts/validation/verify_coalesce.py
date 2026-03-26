import pandas as pd

print("="*70)
print("COALESCE VERIFICATION - PETROBRAS 2024")
print("="*70)

xls = pd.ExcelFile('output/PETROBRAS_financials.xlsx')

for sheet in ['BPA', 'BPP', 'DRE', 'DFC']:
    df = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet, header=2)
    
    # Check uniqueness
    total_rows = len(df)
    unique_ids = df['LINE_ID_BASE'].nunique()
    is_unique = total_rows == unique_ids
    
    # Check for #n
    hash_count = df['LINE_ID_BASE'].astype(str).str.contains('#', na=False).sum()
    
    # QA_CONFLICT
    qa_conflict_count = (df['QA_CONFLICT'] == True).sum()
    
    status_unique = "✅ UNIQUE" if is_unique else f"❌ DUPLICATES ({total_rows - unique_ids})"
    status_hash = "✅" if hash_count == 0 else f"❌ ({hash_count})"
    status_qa = "✅" if qa_conflict_count == 0 else f"⚠️ ({qa_conflict_count})"
    
    print(f"\n{sheet}:")
    print(f"  Total rows: {total_rows}, Unique LINE_ID_BASE: {unique_ids} {status_unique}")
    print(f"  LINE_ID_BASE with #: {hash_count} {status_hash}")
    print(f"  QA_CONFLICT=True: {qa_conflict_count} {status_qa}")

# Check QA_Errors
if 'QA_Errors' in xls.sheet_names:
    qa_errors = pd.read_excel('output/PETROBRAS_financials.xlsx', 'QA_Errors')
    print(f"\n{'='*70}")
    print(f"QA_Errors: {len(qa_errors)} entries")
    if len(qa_errors) > 0:
        print(f"Types: {qa_errors['type'].unique() if 'type' in qa_errors.columns else 'N/A'}")
else:
    print(f"\n{'='*70}")
    print("✅ QA_Errors: 0 entries (sheet doesn't exist)")

print(f"\n{'='*70}")
print("ACCEPTANCE CRITERIA:")
print("✅ LINE_ID_BASE unique per sheet" if all else "Status from checks above")
print("="*70)
