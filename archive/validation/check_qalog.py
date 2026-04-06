import pandas as pd

xls = pd.ExcelFile('output/PETROBRAS_financials.xlsx')
print("Sheets:", xls.sheet_names)

if 'QA_LOG' in xls.sheet_names:
    qa = pd.read_excel('output/PETROBRAS_financials.xlsx', 'QA_LOG')
    print(f"\nQA_LOG rows: {len(qa)}")
    print(f"Types: {qa['type'].unique()}")
    print("\nFirst 5 entries:")
    print(qa.head())
else:
    print("\n❌ No QA_LOG sheet found")

print(f"\nExpected: VERSION_DEDUPLICATION logs from filter_by_version()")
