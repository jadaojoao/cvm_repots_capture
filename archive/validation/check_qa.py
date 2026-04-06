import pandas as pd

qa = pd.read_excel('output/PETROBRAS_financials.xlsx', 'QA_LOG')
print('Total QA entries:', len(qa))
print('\nBy type:')
print(qa['type'].value_counts())

print('\n\nCONSOLIDATED samples (merged rows):')
consol = qa[qa['type'] == 'CONSOLIDATED']
for i, r in consol.head(10).iterrows():
    print(f"  {r['statement']}/{r['line_id_base']}: merged {r.get('merged_rows', 0)} rows")

print('\n\nBPA row count check:')
bpa = pd.read_excel('output/PETROBRAS_financials.xlsx', 'BPA', header=2)
print(f"BPA has {len(bpa)} rows")
print(f"Columns: {len(bpa.columns)} ({list(bpa.columns[:10])}...)")
