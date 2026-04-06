# -*- coding: utf-8 -*-
import os

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\src\scraper.py'
with open(path, 'r', encoding='latin1') as f:
    content = f.read()

# 1. Add ThreadPoolExecutor import
if 'from concurrent.futures import ThreadPoolExecutor' not in content:
    content = content.replace('import pandas as pd', 'import pandas as pd\nfrom concurrent.futures import ThreadPoolExecutor')

# 2. Vectorize normalize_units
old_method = """    def normalize_units(self, df):
        \"\"\"Converts values to Millions based on ESCALA_MOEDA.\"\"\"
        if 'ESCALA_MOEDA' not in df.columns or 'VL_CONTA' not in df.columns:
            return df
            
        def convert(row):
            val = row['VL_CONTA']
            scale = str(row['ESCALA_MOEDA']).upper()
            if scale == 'UNIDADE':
                return val / 1_000_000
            elif scale == 'MIL':
                return val / 1_000
            else: # MILHAO
                return val
                
        df['VL_CONTA'] = df.apply(convert, axis=1)
        return df"""

new_method = """    def normalize_units(self, df):
        \"\"\"Converts values to Millions based on ESCALA_MOEDA (Vectorized).\"\"\"
        if 'ESCALA_MOEDA' not in df.columns or 'VL_CONTA' not in df.columns:
            return df
            
        mask_unidade = df['ESCALA_MOEDA'].str.upper() == 'UNIDADE'
        mask_mil = df['ESCALA_MOEDA'].str.upper() == 'MIL'
        
        df.loc[mask_unidade, 'VL_CONTA'] = df.loc[mask_unidade, 'VL_CONTA'] / 1_000_000
        df.loc[mask_mil, 'VL_CONTA'] = df.loc[mask_mil, 'VL_CONTA'] / 1_000
        
        return df"""

# Note: Using part of string to be sure it matches despite whitespace
if "df['VL_CONTA'] = df.apply(convert, axis=1)" in content:
    print("Found old normalize_units, replacing...")
    # Replacing the whole method block by looking for the start and end
    start_idx = content.find("    def normalize_units(self, df):")
    end_idx = content.find("    def process_data(self, cvm_code, years):")
    if start_idx != -1 and end_idx != -1:
        content = content[:start_idx] + new_method + "\n\n" + content[end_idx:]

with open(path, 'w', encoding='latin1') as f:
    f.write(content)

print("Optimization 1: Scraper unit normalization vectorized.")
