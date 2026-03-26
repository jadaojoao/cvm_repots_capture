import pandas as pd
import io

def generate_company_excel(company_name, cvm_code, raw_df, indicators_df):
    """
    Gera um buffer de Excel em memória contendo a base analítica e os dados brutos
    da empresa selecionada.
    """
    output = io.BytesIO()
    
    # Filtrar dados de indicadores dessa empresa
    ind_df = indicators_df[indicators_df['cd_cvm'] == cvm_code].copy()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Aba 1: Indicadores Analíticos (Opção 1)
        if not ind_df.empty:
            ind_df.to_excel(writer, sheet_name='Base_Indicadores', index=False)
            worksheet = writer.sheets['Base_Indicadores']
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:E', 30)
            worksheet.set_column('F:Z', 18)
            
        # Aba 2: Dados CVM Brutos (Opção 3 / 5)
        if not raw_df.empty:
            raw_df.to_excel(writer, sheet_name='Base_CVM_Padronizada', index=False)
            worksheet2 = writer.sheets['Base_CVM_Padronizada']
            worksheet2.set_column('A:B', 15)
            worksheet2.set_column('C:D', 20)
            worksheet2.set_column('D:E', 40)
            worksheet2.set_column('E:F', 20)
    
    processed_data = output.getvalue()
    
    # Nome limpo para o arquivo
    safe_name = "".join([c if c.isalnum() else "_" for c in company_name]).strip("_")
    filename = f"base_empresa_{safe_name}.xlsx"
    
    return processed_data, filename
