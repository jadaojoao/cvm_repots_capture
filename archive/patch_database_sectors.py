import sqlite3
import pandas as pd
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper import CVMScraper

def patch_database():
    print("Iniciando patch global do banco de dados...")
    
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
    cur.execute("SELECT DISTINCT CD_CVM FROM financial_reports")
    cvm_codes = [r[0] for r in cur.fetchall()]
    print(f"Encontradas {len(cvm_codes)} empresas no banco.")
    
    # 3. Atualizar COMPANY_TYPE e aplicar heurística de escala
    updated_count = 0
    scale_fix_count = 0
    
    for cvm_code in cvm_codes:
        setor = str(setores.get(str(cvm_code), '')).lower()
        if any(k in setor for k in ['banc', 'financ', 'arrendamento', 'crédito', 'credito']):
            tipo = 'financeira'
        elif 'segur' in setor:
            tipo = 'seguradora'
        else:
            tipo = 'comercial'
            
        # Atualizar COMPANY_TYPE para todos os registros desta empresa
        cur.execute("UPDATE financial_reports SET COMPANY_TYPE = ? WHERE CD_CVM = ?", (tipo, cvm_code))
        updated_count += cur.rowcount
        
        # 4. Heurística de Correção de Escala (1000x)
        # Se for banco de grande porte (Lucro > 0 mas < 10.000 (milhões) em ano cheio)
        # O Bradesco 1Q25 estava em ~5600 (R$ 5.6M) em vez de 5.6M (R$ 5.6B).
        # Vamos checar o valor do Lucro Total ou Ativo Total médio.
        
        # Buscar Ativo Total (1.01) para 2024
        cur.execute("""
            SELECT VL_CONTA FROM financial_reports 
            WHERE CD_CVM = ? AND CD_CONTA = '1' AND PERIOD_LABEL = '2024'
        """, (cvm_code,))
        row = cur.fetchone()
        if row:
            ativo = row[0]
            # Se Ativo Total for < 100M (num banco ou grande empresa), está na escala errada
            # Um banco pequeno tem Ativo > 1B (1.000.000 em R$ mil).
            # Se estiver reportado como 1.000, está em R$ milhões (escala errada).
            if ativo < 100_000 and (tipo in ['financeira', 'seguradora'] or ativo < 1000):
                print(f"  Fixing scale for CVM {cvm_code} (Ativo: {ativo:,.1f})")
                cur.execute("""
                    UPDATE financial_reports SET VL_CONTA = VL_CONTA * 1000 
                    WHERE CD_CVM = ?
                """, (cvm_code,))
                scale_fix_count += 1
                
    conn.commit()
    conn.close()
    print(f"Patch concluído: {updated_count} linhas atualizadas, {scale_fix_count} empresas corrigidas em escala.")

if __name__ == "__main__":
    patch_database()
