import pandas as pd

print("="*80)
print("ANALYZING DFC OUTPUT FOR MISSING QUARTERS")
print("="*80)

# Load DFC sheet
df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)

print(f"\nTotal DFC rows: {len(df_dfc)}")
print(f"QA_CONFLICT=True: {(df_dfc['QA_CONFLICT'] == True).sum()}")

# Find rows with QA_CONFLICT=True
conflict_rows = df_dfc[df_dfc['QA_CONFLICT'] == True]

if len(conflict_rows) > 0:
    print(f"\n{len(conflict_rows)} rows with QA_CONFLICT=True")
    print("\nAnalyzing patterns:")
    
    for idx, row in conflict_rows.iterrows():
        cd_conta = row['CD_CONTA']
        line_id = row['LINE_ID_BASE']
        desc = row['DS_CONTA'][:50] if len(str(row['DS_CONTA'])) > 50 else row['DS_CONTA']
        
        print(f"\n{'-'*80}")
        print(f"CD_CONTA: {cd_conta}")
        print(f"LINE_ID_BASE: {line_id}")
        print(f"DS_CONTA: {desc}")
        
        # Check which years have data
        period_cols = [c for c in df_dfc.columns if isinstance(c, str) and ('Q' in c or c.isdigit())]
        
        for year in [2021, 2022, 2023, 2024, 2025]:
            yy = str(year)[2:]
            annual_col = str(year)
            q_cols = [f'{q}Q{yy}' for q in [1,2,3,4]]
            
            # Check if annual exists
            has_annual = annual_col in df_dfc.columns and pd.notna(row.get(annual_col))
            
            if has_annual:
                annual_val = row.get(annual_col, 0)
                q_vals = [row.get(c, None) if c in df_dfc.columns else None for c in q_cols]
                q_filled = sum(1 for v in q_vals if pd.notna(v))
                
                print(f"  {year}: Annual={annual_val:,.0f} | Quarters filled: {q_filled}/4")
                
                if q_filled < 4:
                    print(f"    Missing quarters:")
                    for i, (qcol, qval) in enumerate(zip(q_cols, q_vals), 1):
                        if pd.isna(qval):
                            print(f"      {i}Q{yy}: NaN")
                        else:
                            print(f"      {i}Q{yy}: {qval:,.0f}")
else:
    print("\n✅ NO ROWS with QA_CONFLICT=True")

print("\n" + "="*80)
