# Final Verification

import pandas as pd

print("="*80)
print("FINAL VERIFICATION - PRIORITY 2 FIXES")
print("="*80)

xls_file = 'output/PETROBRAS_financials.xlsx'

# 1. DS_CONTA_norm export
print("\n1. DS_CONTA_norm EXPORT")
print("-"*80)
bpa = pd.read_excel(xls_file, sheet_name='BPA', header=2)
ds_norm_present = 'DS_CONTA_norm' in bpa.columns

if ds_norm_present:
    print("✅ DS_CONTA_norm IS EXPORTED")
    print(f"   Columns: {list(bpa.columns[:10])}")
    print("\n   Sample:")
    for idx, row in bpa[['LINE_ID', 'DS_CONTA', 'DS_CONTA_norm']].head(3).iterrows():
        print(f"     {row['LINE_ID']}: '{row['DS_CONTA']}' → '{row['DS_CONTA_norm']}'")
else:
    print("❌ DS_CONTA_norm NOT EXPORTED")

# 2. LINE_ID uniqueness per sheet
print("\n2. LINE_ID UNIQUENESS PER SHEET")
print("-"*80)
all_unique = True

for sheet in ['BPA', 'BPP', 'DRE', 'DFC']:
    df = pd.read_excel(xls_file, sheet_name=sheet, header=2)
    line_id_counts = df['LINE_ID'].value_counts()
    dups = line_id_counts[line_id_counts > 1]
    
    if len(dups) == 0:
        print(f"✅ {sheet}: All {len(df)} LINE_IDs unique")
    else:
        all_unique = False
        print(f"❌ {sheet}: {len(dups)} duplicate LINE_ID(s)")
        for dup_id, count in dups.head(3).items():
            print(f"     '{dup_id}': appears {count} times")
            # Show the actual rows
            dup_rows = df[df['LINE_ID'] == dup_id]
            print(f"       CD_CONTA values: {dup_rows['CD_CONTA'].tolist()}")
            print(f"       DS_CONTA values: {dup_rows['DS_CONTA'].unique().tolist()}")

# 3. QA_Errors check
print("\n3. QA_ERRORS SHEET")
print("-"*80)
xls = pd.ExcelFile(xls_file)
if 'QA_Errors' in xls.sheet_names:
    qa_err = pd.read_excel(xls_file, sheet_name='QA_Errors')
    print(f"⚠️  {len(qa_err)} validation error(s) logged")
    for idx, row in qa_err.iterrows():
        print(f"\n   Error #{idx+1}:")
        print(f"     Statement: {row.get('statement', 'N/A')}")
        print(f"     LINE_ID: {row.get('line_id', 'N/A')}")
        print(f"     Description: {str(row.get('description', 'N/A'))[:100]}")
else:
    print("✅ No QA_Errors sheet - all validation passed")

# 4. QA_LOG summary
print("\n4. QA_LOG SUMMARY")
print("-"*80)
if 'QA_LOG' in xls.sheet_names:
    qa_log = pd.read_excel(xls_file, sheet_name='QA_LOG')
    print(f"Total QA entries: {len(qa_log)}")
    
    for qtype in qa_log['type'].unique():
        count = len(qa_log[qa_log['type'] == qtype])
        print(f"  {qtype}: {count}")
else:
    print("No QA_LOG sheet")

# Summary
print("\n"+"="*80)
print("SUMMARY")
print("="*80)
print(f"DS_CONTA_norm exported: {'YES ✅' if ds_norm_present else 'NO ❌'}")
print(f"All LINE_IDs unique: {'YES ✅' if all_unique else 'NO ❌'}")
print("="*80)
