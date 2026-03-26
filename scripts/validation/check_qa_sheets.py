import pandas as pd

xls = pd.ExcelFile('output/PETROBRAS_financials.xlsx')
print(f"Sheets in Excel: {xls.sheet_names}")

# Load QA_LOG
if 'QA_LOG' in xls.sheet_names:
    qa_log = pd.read_excel('output/PETROBRAS_financials.xlsx', 'QA_LOG')
    print(f"\nQA_LOG rows: {len(qa_log)}")
    print(f"\nQA_LOG types:")
    print(qa_log['type'].value_counts())
    
    # Check for TRIMESTRAL_NAO_DIVULGADO
    trimestral = qa_log[qa_log['type'] == 'TRIMESTRAL_NAO_DIVULGADO']
    print(f"\nTRIMESTRAL_NAO_DIVULGADO entries: {len(trimestral)}")
    
    if len(trimestral) > 0:
        print("\nDetails:")
        print(trimestral[['type', 'statement', 'year', 'cd_conta', 'annual', 'action']].to_string())

# Load DFC
df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)
print(f"\n\nDFC rows with QA_CONFLICT=True: {(df_dfc['QA_CONFLICT'] == True).sum()}")
