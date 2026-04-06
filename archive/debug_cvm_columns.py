import requests
import pandas as pd
import io

url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
try:
    response = requests.get(url, timeout=30)
    # Read just the first few lines to get headers
    content = response.content.decode('latin1')
    first_lines = "\n".join(content.splitlines()[:5])
    print("First 5 lines of CSV:")
    print(first_lines)
    
    df = pd.read_csv(io.StringIO(first_lines), sep=";")
    print("\nColumns:")
    print(df.columns.tolist())
except Exception as e:
    print(f"Error: {e}")
