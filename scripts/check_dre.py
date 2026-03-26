import pandas as pd

# Check DRE duplicate
print("Checking DRE duplicate LINE_IDs...")
dre = pd.read_excel('output/PETROBRAS_financials.xlsx', sheet_name='DRE', header=2)
line_id_counts = dre['LINE_ID'].value_counts()
dups = line_id_counts[line_id_counts > 1]

if len(dups) > 0:
    print(f"Found {len(dups)} duplicate LINE_IDs in DRE")
    for dup_id in dups.index[:3]:
        print(f"\nLINE_ID: {dup_id} (appears {dups[dup_id]} times)")
        dup_rows = dre[dre['LINE_ID'] == dup_id]
        print(dup_rows[['LINE_ID', 'CD_CONTA', 'DS_CONTA']].to_string())
else:
    print("No duplicate LINE_IDs found in DRE")

# Check columns
print("\n\nFirst row columns check:")
print(f"Columns: {list(dre.columns[:15])}")
