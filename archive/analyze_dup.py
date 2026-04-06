import pandas as pd

print("Analyzing DRE duplicate LINE_ID...")
dre = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet_name='DRE', header=2)

# Find duplicates
dup_mask = dre.duplicated('LINE_ID', keep=False)
dups = dre[dup_mask]

print(f"Total duplicate rows: {len(dups)}")

if len(dups) > 0:
    print("\nDuplicate LINE_IDs:")
    for line_id in dups['LINE_ID'].unique():
        print(f"\n  LINE_ID: '{line_id}'")
        rows = dups[dups['LINE_ID'] == line_id]
        print(f"  Number of rows: {len(rows)}")
        print(f"  CD_CONTA: {rows['CD_CONTA'].unique().tolist()}")
        print(f"  DS_CONTA: {rows['DS_CONTA'].unique().tolist()}")
        
        if 'DS_CONTA_norm' in rows.columns:
            print(f"  DS_CONTA_norm: {rows['DS_CONTA_norm'].unique().tolist()}")
        
        if 'QA_CONFLICT' in rows.columns:
            print(f"  QA_CONFLICT: {rows['QA_CONFLICT'].tolist()}")
        
        # Check value columns
        value_cols = [c for c in rows.columns if c not in ['LINE_ID', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']]
        print(f"\n  Value columns: {value_cols[:7]}")
        
        for idx, row in rows.iterrows():
            vals = [row[c] for c in value_cols[:7]]
            print(f"  Row {idx}: {[f'{v:.2f}' if pd.notna(v) else 'NaN' for v in vals]}")
else:
    print("No duplicates found")
