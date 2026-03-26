import pandas as pd
import requests
import zipfile
import io
import os
from datetime import datetime

# ============================================================================
# USER CONFIGURATION
# ============================================================================

# Timeout (segundos) para download dos ZIPs da CVM
DICTIONARY_TIMEOUT = 120

# ============================================================================


class DictionaryBuilder:
    STATEMENT_MAP = {
        'BPA': 'BPA',
        'BPP': 'BPP',
        'DRE': 'DRE',
        'DFC_MD': 'DFC',
        'DFC_MI': 'DFC'
    }

    def __init__(self, start_year, end_year, data_dir="input", output_dir="output", max_companies=None):
        self.start_year = start_year
        self.end_year = end_year
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.max_companies = max_companies
        
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def get_statement_type(self, filename):
        """Determines statement type from filename."""
        for key, value in self.STATEMENT_MAP.items():
            if f"{key}_con" in filename:
                return value
        return None

    def build(self):
        seen_cnpjs = set()
        dictionary = set() # Stores (account_name, statement_type)
        
        print(f"Starting Master Dictionary Build...")
        print(f"Config: Max Companies={self.max_companies}, Years={self.start_year}-{self.end_year}")

        for year in range(self.start_year, self.end_year + 1):
            print(f"\nProcessing Year: {year}")
            filename = f"dfp_cia_aberta_{year}.zip"
            zip_path = os.path.join(self.raw_dir, filename)
            url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/{filename}"
            
            # Check if file exists, otherwise download (or stream)
            # Original script streamed, but for efficiency let's check local
            
            content = None
            if os.path.exists(zip_path):
                print(f"  Found local file: {zip_path}")
                with open(zip_path, 'rb') as f:
                    content = f.read()
            else:
                try:
                    print(f"  Downloading {url}...")
                    response = requests.get(url, stream=True, timeout=DICTIONARY_TIMEOUT)
                    if response.status_code != 200:
                        print(f"  Failed to download {url} (Status: {response.status_code})")
                        continue
                    content = response.content
                    # Optionally save?
                    with open(zip_path, 'wb') as f:
                        f.write(content)
                except requests.RequestException as e:
                    print(f"  Error [{type(e).__name__}] downloading {year}: {e}")
                    continue
                except Exception as e:
                    print(f"  Unexpected error [{type(e).__name__}] downloading {year}: {e}")
                    raise

            if not content:
                continue

            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    # Filter for relevant consolidated files
                    file_list = [f for f in z.namelist() if "_con" in f and any(k in f for k in self.STATEMENT_MAP.keys())]
                    
                    for filename in file_list:
                        statement_type = self.get_statement_type(filename)
                        if not statement_type:
                            continue
                            
                        print(f"    Scanning {filename}...")
                        
                        try:
                            with z.open(filename) as f:
                                df = pd.read_csv(f, sep=';', encoding='iso-8859-1', usecols=['CNPJ_CIA', 'DS_CONTA'])
                                
                                if df.empty:
                                    continue

                                # 1. Update Global Company List (if limit not reached)
                                unique_cnpjs = df['CNPJ_CIA'].unique()
                                
                                for cnpj in unique_cnpjs:
                                    if self.max_companies is None or len(seen_cnpjs) < self.max_companies:
                                        seen_cnpjs.add(cnpj)

                                # 2. Filter Data by Seen CNPJs
                                if self.max_companies is not None:
                                    df = df[df['CNPJ_CIA'].isin(seen_cnpjs)]
                                
                                if df.empty:
                                    continue

                                # 3. Extract Unique Accounts
                                unique_accounts = df['DS_CONTA'].unique()
                                
                                # Add to dictionary
                                for account in unique_accounts:
                                    dictionary.add((account, statement_type))
                                    
                        except (pd.errors.ParserError, UnicodeDecodeError, KeyError) as e:
                            print(f"    Error [{type(e).__name__}] reading {filename}: {e}")
                        except Exception as e:
                            print(f"    Unexpected error [{type(e).__name__}] reading {filename}: {e}")
                            raise

            except (zipfile.BadZipFile, OSError) as e:
                print(f"  Error [{type(e).__name__}] processing zip for {year}: {e}")
            except Exception as e:
                print(f"  Unexpected error [{type(e).__name__}] processing zip for {year}: {e}")
                raise

        # Output
        print(f"\nBuilding final CSV...")
        result_df = pd.DataFrame(list(dictionary), columns=['account_name', 'statement_type'])
        result_df = result_df.sort_values(by=['statement_type', 'account_name'])
        
        output_file = os.path.join(self.output_dir, "cvm_account_dictionary.csv")
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Done! Saved {len(result_df)} unique entries to {output_file}")
