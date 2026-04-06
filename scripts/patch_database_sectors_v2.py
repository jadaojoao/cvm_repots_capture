import sqlite3
import pandas as pd
import os
import sys

# Standardizer needs this for the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper import CVMScraper

def patch_database_v2():
    print("Iniciando patch global v2 (HEURÍSTICA REFINADA)...")
    
    db_path = 'data/db/cvm_financials.db'
    if not os.path.exists(db_path):
        print("Erro: Banco de dados não encontrado.")
        return
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Obter mapeamento de setores da CVM
    scraper = CVMScraper()
    scraper.fetch_company_list()
    setores = scraper.setores_map
    
    # 2. Identificar todas as empresas no banco
    cur.execute("SELECT DISTINCT CD_CVM, COMPANY_NAME FROM financial_reports")
    cvm_list = cur.fetchall()
    print(f"Encontradas {len(cvm_list)} empresas no banco.")
    
    # 3. Atualizar COMPANY_TYPE e aplicar heurística de escala agressiva
    scale_fix_count = 0
    updated_count = 0
    
    for cvm_code, company_name in cvm_list:
        setor = str(setores.get(str(cvm_code), '')).lower()
        if any(k in setor for k in ['banc', 'financ', 'arrendamento', 'crédito', 'credito']):
            tipo = 'financeira'
        elif 'segur' in setor:
            tipo = 'seguradora'
        else:
            tipo = 'comercial'
            
        # Atualizar COMPANY_TYPE (caso tenha mudado ou seja novo)
        cur.execute("UPDATE financial_reports SET COMPANY_TYPE = ? WHERE CD_CVM = ?", (tipo, cvm_code))
        updated_count += cur.rowcount
        
        # 4. HEURÍSTICA REFINADA:
        # Se for banco ou seguradora, e o Ativo Total ('1') do ano mais recente estiver < 20.000.000, 
        # é sinal que o bilhão foi reportado como milhão (R$ milhões).
        # Multiplicamos por 1000 para converter em 'R$ mil' (unidade do Dashboard).
        
        cur.execute("""
            SELECT VL_CONTA, PERIOD_LABEL FROM financial_reports 
            WHERE CD_CVM = ? AND CD_CONTA = '1'
            ORDER BY PERIOD_LABEL DESC LIMIT 1
        """, (cvm_code,))
        row = cur.fetchone()
        
        if row and row[0] is not None:
            try:
                ativo = float(row[0])
                label = row[1]
                needs_fix = False
                
                # Ignorar se o dado for o 1Q25 que acabamos de fixar hoje (espetáculo)
                if label == '1Q25' and ativo > 100_000_000:
                    pass 
                elif tipo in ['financeira', 'seguradora']:
                    # Qualquer banco/seguradora com ativo < 20.000.000 (20 bilhões em R$ mil)
                    if ativo < 20_000_000:
                        needs_fix = True
                elif tipo == 'comercial':
                    # Grandes comerciais como Vale/Petrobras também foram afetadas.
                    if ativo < 1_000_000 and any(k in company_name.upper() for k in ['PETROBRAS', 'VALE', 'ELETROBRAS']):
                        needs_fix = True

                if needs_fix:
                    print(f"  Fixing scale for {company_name} (CVM {cvm_code}): {ativo:,.1f} ({label})")
                    cur.execute("""
                        UPDATE financial_reports SET VL_CONTA = VL_CONTA * 1000 
                        WHERE CD_CVM = ?
                    """, (cvm_code,))
                    scale_fix_count += 1
            except (ValueError, TypeError):
                continue
                
    conn.commit()
    conn.close()
    print(f"Patch concluído: {updated_count} linhas atualizadas, {scale_fix_count} empresas corrigidas em escala.")

if __name__ == "__main__":
    patch_database_v2()
