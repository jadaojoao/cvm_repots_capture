import pandas as pd

print("="*80)
print("VERIFICATION: LINE_ID FIXES")
print("="*80)

xls_file = 'output/PETROBRAS_financials.xlsx'
xls = pd.ExcelFile(xls_file)

print("\n1. SHEETS AVAILABLE")
print("-"*80)
print(f"Sheets: {xls.sheet_names}")

# Check for DS_CONTA_norm
print("\n2. DS_CONTA_NORM EXPORT CHECK")
print("-"*80)
bpa = pd.read_excel(xls_file, sheet_name='BPA', header=2)
if 'DS_CONTA_norm' in bpa.columns:
    print("✓ DS_CONTA_norm is present in output!")
    print(f"Columns: {list(bpa.columns[:12])}")
    print("\nSample:")
    print(bpa[['LINE_ID', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm']].head(3).to_string())
else:
    print("✗ DS_CONTA_norm is NOT in output")
    print(f"Columns: {list(bpa.columns[:12])}")

# Check QA_Errors
print("\n3. VALIDATION ERRORS")
print("-"*80)
if 'QA_Errors' in xls.sheet_names:
    qa_err = pd.read_excel(xls_file, sheet_name='QA_Errors')
    print(f"Number of errors: {len(qa_err)}")
    print("\nError details:")
    for idx, row in qa_err.iterrows():
        print(f"\n  Error #{idx+1}:")
        print(f"  Sheet: {row['sheet']}")
        print(f"  LINE_ID: {row['line_id']}")
        print(f"  Count: {row['count']}")
        if 'conflict_columns' in row and pd.notna(row['conflict_columns']):
            print(f"  Conflict columns: {row['conflict_columns']}")
        print(f"  Descriptions: {row.get('description', 'N/A')}")
else:
    print("✓ No QA_Errors sheet - all validation passed!")

# Check QA_LOG
print("\n4. QA LOG SUMMARY")
print("-"*80)
if 'QA_LOG' in xls.sheet_names:
    qa_log = pd.read_excel(xls_file, sheet_name='QA_LOG')
    print(f"Total QA entries: {len(qa_log)}")
    print("\nBy type:")
    type_counts = qa_log['type'].value_counts()
    for t, count in type_counts.items():
        print(f"  {t}: {count}")
    
    # Show consolidations and disambiguations
    consolidations = qa_log[qa_log['type'] == 'LINE_ID_CONSOLIDATED']
    disambiguations = qa_log[qa_log['type'] == 'LINE_ID_DISAMBIGUATED']
    
    if len(consolidations) > 0:
        print(f"\nConsolidated {len(consolidations)} LINE_ID groups")
        print("Sample consolidations:")
        for idx, row in consolidations.head(3).iterrows():
            print(f"  {row['statement']}: LINE_ID={row['line_id']} ({row['count']} rows merged)")
    
    if len(disambiguations) > 0:
        print(f"\nDisambiguated {len(disambiguations)} LINE_ID groups")
        print("Sample disambiguations:")
        for idx, row in disambiguations.head(3).iterrows():
            print(f"  {row['statement']}: LINE_ID={row['original_line_id']} ({row['count']} rows, {len(row.get('conflict_periods',[]))} conflicts)")
else:
    print("No QA_LOG sheet")

# Check LINE_ID uniqueness in each sheet
print("\n5. LINE_ID UNIQUENESS CHECK (Manual)")
print("-"*80)
for sheet in ['BPA', 'BPP', 'DRE', 'DFC']:
    df = pd.read_excel(xls_file, sheet_name=sheet, header=2)
    if 'LINE_ID' in df.columns:
        line_id_counts = df['LINE_ID'].value_counts()
        duplicates = line_id_counts[line_id_counts > 1]
        if len(duplicates) > 0:
            print(f"✗ {sheet}: {len(duplicates)} duplicate LINE_IDs")
            for line_id, count in duplicates.head(3).items():
                print(f"    {line_id}: appears {count} times")
        else:
            print(f"✓ {sheet}: All LINE_IDs are unique ({len(df)} rows)")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
