import sqlite3
import pandas as pd
import numpy as np
import os

def load_data(db_path):
    conn = sqlite3.connect(db_path)
    # Fetch all relevant standardized accounts
    query = """
    SELECT CD_CVM, REPORT_YEAR, STATEMENT_TYPE, PERIOD_LABEL, STANDARD_NAME, SUM(VL_CONTA) as VL_CONTA
    FROM financial_reports
    WHERE STANDARD_NAME IN (
        'Receita de Venda de Bens e/ou Serviços',
        'Receitas das Operações',
        'Receitas de Intermediação Financeira',
        'Resultado Bruto',
        'Lucro/Prejuízo Consolidado do Período',
        'Ativo Total',
        'Patrimônio Líquido',
        'Caixa Líquido Atividades Operacionais'
    )
    GROUP BY CD_CVM, REPORT_YEAR, STATEMENT_TYPE, PERIOD_LABEL, STANDARD_NAME
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def aggregate_annual(df):
    """
    For DRE/DFC (Flows), sum the quarters.
    For BPA/BPP (Stocks), take the 4Q value (or the latest quarter available).
    """
    # Fix standard names for Revenue
    df['STANDARD_NAME'] = df['STANDARD_NAME'].replace({
        'Receitas das Operações': 'Receita',
        'Receitas de Intermediação Financeira': 'Receita',
        'Receita de Venda de Bens e/ou Serviços': 'Receita'
    })
    
    # Separate Stocks and Flows
    df_flows = df[df['STATEMENT_TYPE'].isin(['DRE', 'DFC'])].copy()
    df_stocks = df[df['STATEMENT_TYPE'].isin(['BPA', 'BPP'])].copy()
    
    # Sum flows
    annual_flows = df_flows.groupby(['CD_CVM', 'REPORT_YEAR', 'STANDARD_NAME'])['VL_CONTA'].sum().reset_index()
    
    # Latest stock (4Q preferred)
    # Sort so 4Q is last, and take last
    df_stocks = df_stocks.sort_values(['CD_CVM', 'REPORT_YEAR', 'STANDARD_NAME', 'PERIOD_LABEL'])
    annual_stocks = df_stocks.groupby(['CD_CVM', 'REPORT_YEAR', 'STANDARD_NAME']).last().reset_index()
    annual_stocks = annual_stocks[['CD_CVM', 'REPORT_YEAR', 'STANDARD_NAME', 'VL_CONTA']]
    
    return pd.concat([annual_flows, annual_stocks], ignore_index=True)

def compute_kpis(df_annual):
    # Pivot to wide format
    pivot = df_annual.pivot_table(
        index=['CD_CVM', 'REPORT_YEAR'], 
        columns='STANDARD_NAME', 
        values='VL_CONTA', 
        aggfunc='sum'
    ).reset_index()
    
    # Ensure columns exist
    for col in ['Receita', 'Resultado Bruto', 'Lucro/Prejuízo Consolidado do Período', 
                'Ativo Total', 'Patrimônio Líquido', 'Caixa Líquido Atividades Operacionais']:
        if col not in pivot.columns:
            pivot[col] = np.nan
            
    # Compute KPIs
    # UNI_002: Margem Bruta = Lucro Bruto / Receita
    pivot['UNI_002'] = pivot['Resultado Bruto'] / pivot['Receita']
    
    # UNI_005: ROA = Lucro / Ativo Total
    pivot['UNI_005'] = pivot['Lucro/Prejuízo Consolidado do Período'] / pivot['Ativo Total']
    
    # UNI_006: ROE = Lucro / PL
    pivot['UNI_006'] = pivot['Lucro/Prejuízo Consolidado do Período'] / pivot['Patrimônio Líquido']
    
    # UNI_008: FCO / Receita
    pivot['UNI_008'] = pivot['Caixa Líquido Atividades Operacionais'] / pivot['Receita']
    
    # UNI_011: Margem Líquida = Lucro / Receita
    pivot['UNI_011'] = pivot['Lucro/Prejuízo Consolidado do Período'] / pivot['Receita']
    
    # UNI_001: Crescimento Receita YoY = Receita(t) / Receita(t-1) - 1
    # Sort by year first
    pivot = pivot.sort_values(['CD_CVM', 'REPORT_YEAR'])
    pivot['Receita_prev'] = pivot.groupby('CD_CVM')['Receita'].shift(1)
    pivot['UNI_001'] = (pivot['Receita'] / pivot['Receita_prev']) - 1
    
    # Melt back to long format for easy mapping
    kpi_cols = ['UNI_001', 'UNI_002', 'UNI_005', 'UNI_006', 'UNI_008', 'UNI_011']
    melted = pivot.melt(
        id_vars=['CD_CVM', 'REPORT_YEAR'], 
        value_vars=kpi_cols,
        var_name='KPI_ID',
        value_name='CALCULATED_VALUE'
    )
    # Drop NAs to keep it clean
    melted = melted.dropna(subset=['CALCULATED_VALUE'])
    
    return melted

def main():
    db_path = 'data/db/cvm_financials.db'
    base_file = 'output/reports/base_analitica_dashboard_pronta.xlsx'
    
    if not os.path.exists(db_path):
        print("Database not found. Run scraper first.")
        return
        
    print("1. Lendo banco de dados SQLite...")
    df_raw = load_data(db_path)
    
    print("2. Agrupando anualmente e calculando KPIs Mapeados...")
    annual = aggregate_annual(df_raw)
    kpis = compute_kpis(annual)
    
    print(f"   Calculados {len(kpis)} pontos de dados (KPI x Empresa x Ano).")
    
    if os.path.exists(base_file):
        print("3. Injetando na Base Analitica Dashboard...")
        base_df = pd.read_excel(base_file)
        
        # Merge values retroactively
        # We need to map year -> VALUE_YYYY
        for year in [2023, 2024, 2025]:
            year_kpis = kpis[kpis['REPORT_YEAR'] == year].copy()
            year_kpis = year_kpis.rename(columns={'CALCULATED_VALUE': f'CALC_{year}'})
            
            # Merge
            base_df = base_df.merge(
                year_kpis[['CD_CVM', 'KPI_ID', f'CALC_{year}']], 
                left_on=['cd_cvm', 'kpi_id'], 
                right_on=['CD_CVM', 'KPI_ID'], 
                how='left'
            )
            
            # Overwrite VALUE_YYYY where CALC exists
            calc_col = f'CALC_{year}'
            val_col = f'VALUE_{year}'
            
            if val_col not in base_df.columns:
                base_df[val_col] = None
                
            mask = base_df[calc_col].notna()
            base_df.loc[mask, val_col] = base_df.loc[mask, calc_col]
            
            # Drop temporary columns
            base_df.drop(columns=['CD_CVM', 'KPI_ID', calc_col], inplace=True, errors='ignore')
            
            # Se preencheu algo, muda API_STATUS para FILLED_INTERNALLY
            base_df.loc[mask, 'API_STATUS'] = 'CALCULATED_FROM_CVM_DB'
            
        out_file = 'output/reports/base_analitica_dashboard_preenchida.xlsx'
        base_df.to_excel(out_file, index=False)
        print(f"Base populada salva em: {out_file}")
    else:
        print("Base Analítica não encontrada para merge.")
        
if __name__ == '__main__':
    main()
