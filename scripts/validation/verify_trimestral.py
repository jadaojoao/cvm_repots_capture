import pandas as pd

print("="*80)
print("FINAL VERIFICATION - TRIMESTRAL_NAO_DIVULGADO")
print("="*80)

# Load output
df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)
qa_errors_df = pd.read_excel('output/PETROBRAS_financials.xlsx', 'QA_Errors')

print(f"\nDFC total rows: {len(df_dfc)}")
print(f"QA_CONFLICT=True: {(df_dfc['QA_CONFLICT'] == True).sum()}")

# Check QA_Errors for TRIMESTRAL_NAO_DIVULGADO
trimestral_errors = qa_errors_df[qa_errors_df['type'] == 'TRIMESTRAL_NAO_DIVULGADO']
print(f"\nQA_Errors with TRIMESTRAL_NAO_DIVULGADO: {len(trimestral_errors)}")

if len(trimestral_errors) > 0:
    print("\nTRIMESTRAL_NAO_DIVULGADO entries:")
    for idx, row in trimestral_errors.iterrows():
        year = row.get('year', 'N/A')
        cd_conta = row.get('cd_conta', 'N/A')
        line_id = row.get('line_id_base', 'N/A')
        annual = row.get('annual', 0)
        print(f"  {year} | CD_CONTA={cd_conta} | Annual={annual:,.0f}")

# Verification: rows with QA_CONFLICT should match TRIMESTRAL_NAO_DIVULGADO + DFC_VALIDATION_FAILED
dfc_val_errors = qa_errors_df[qa_errors_df['type'] == 'DFC_VALIDATION_FAILED']
print(f"\nDFC_VALIDATION_FAILED: {len(dfc_val_errors)}")

total_expected_conflicts = len(trimestral_errors) + len(dfc_val_errors)
actual_conflicts = (df_dfc['QA_CONFLICT'] == True).sum()

print(f"\n{'='*80}")
print("FINAL CHECK:")
print(f"  Expected QA_CONFLICT rows: {total_expected_conflicts}")
print(f"  Actual QA_CONFLICT rows: {actual_conflicts}")

if actual_conflicts == total_expected_conflicts:
    print(f"  ✅ MATCH - QA_CONFLICT correctly set")
else:
    print(f"  ⚠️ MISMATCH - investigate discrepancy")

print("="*80)
