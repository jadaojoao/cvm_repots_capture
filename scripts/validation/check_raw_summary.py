import pandas as pd
import os

# Get problematic accounts
df_dfc = pd.read_excel('output/PETROBRAS_financials.xlsx', 'DFC', header=2)
conflict_rows = df_dfc[df_dfc['QA_CONFLICT'] == True]

problematic = list(conflict_rows['CD_CONTA'].unique())
print(f"Problematic CD_CONTAs: {problematic}")

# Check ITR 2022 and 2023
results = {}

for year in [2022, 2023]:
    itr_file = f'data/input/itr_cia_aberta_DFC_MI_con_{year}.csv'
    dfp_file = f'data/input/dfp_cia_aberta_DFC_MI_con_{year}.csv'
    
    results[year] = {}
    
    # Check ITR
    if os.path.exists(itr_file):
        df_itr = pd.read_csv(itr_file, sep=';', encoding='latin1', low_memory=False)
        df_itr_petro = df_itr[df_itr['CD_CVM'] == 9512]
        
        for cd in problematic:
            found_itr = len(df_itr_petro[df_itr_petro['CD_CONTA'] == cd]) > 0
            results[year][cd] = {'ITR': found_itr}
    
    # Check DFP
    if os.path.exists(dfp_file):
        df_dfp = pd.read_csv(dfp_file, sep=';', encoding='latin1', low_memory=False)
        df_dfp_petro = df_dfp[df_dfp['CD_CVM'] == 9512]
        
        for cd in problematic:
            found_dfp = len(df_dfp_petro[df_dfp_petro['CD_CONTA'] == cd]) > 0
            if cd in results[year]:
                results[year][cd]['DFP'] = found_dfp
            else:
                results[year][cd]= {'DFP': found_dfp}

print("\nRESULTS:")
print("="*60)
for year in sorted(results.keys()):
    print(f"\nYear {year}:")
    for cd in sorted(results[year].keys()):
        itr = results[year][cd].get('ITR', False)
        dfp = results[year][cd].get('DFP', False)
        
        if dfp and not itr:
            status = "DFP YES, ITR NO -> Company doesn't disclose quarterly"
        elif dfp and itr:
            status = "DFP YES, ITR YES -> BUG in pipeline!"
        elif not dfp and not itr:
            status = "Both missing"
        else:
            status = "ITR only (unusual)"
        
        print(f"  CD_CONTA {cd}: {status}")

print("\n" + "="*60)
print("CONCLUSION:")
for year in results:
    for cd in results[year]:
        if results[year][cd].get('DFP') and not results[year][cd].get('ITR'):
            print(f"  {cd} ({year}): TRIMESTRAL_NAO_DIVULGADO")
        elif results[year][cd].get('DFP') and results[year][cd].get('ITR'):
            print(f"  {cd} ({year}): BUG - ITR exists but not extracted!")
print("="*60)
