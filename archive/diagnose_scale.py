import sqlite3

db_path = 'data/db/cvm_financials.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("Financeira - Ativo Total - CD_CONTA='1' - 2024")
cur.execute("SELECT CD_CVM, VL_CONTA FROM financial_reports WHERE CD_CONTA='1' AND PERIOD_LABEL='2024' AND COMPANY_TYPE='financeira' LIMIT 20")
for row in cur.fetchall():
    print(f"CVM {row[0]}: {row[1]:,.2f}")

print("\nComercial - Ativo Total - CD_CONTA='1' - 2024")
cur.execute("SELECT CD_CVM, VL_CONTA FROM financial_reports WHERE CD_CONTA='1' AND PERIOD_LABEL='2024' AND COMPANY_TYPE='comercial' LIMIT 20")
for row in cur.fetchall():
    print(f"CVM {row[0]}: {row[1]:,.2f}")

conn.close()
