# -*- coding: utf-8 -*-
import os

path = r'c:\\Users\\jadaojoao\\Documents\\cvm_repots_capture\\src\\database.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add SQLite PRAGMAs for performance during bulk insertions
# We'll add a context manager for performance mode or just set it in insert_company_data
pragma_setup = """        # Performance PRAGMAs for bulk insertion
        with self._engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode = WAL"))
            conn.execute(text("PRAGMA synchronous = OFF"))
            conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB cache
"""

if 'def insert_company_data' in content:
    # Set performance PRAGMAs at the start of insert_company_data
    # Or better yet, in _init_db? Let's do it in insert_company_data to be safe.
    
    insert_start = content.find('def insert_company_data')
    block_start = content.find('with self._engine.begin() as conn:', insert_start)
    
    if block_start != -1:
        # Insert PRAGMAs before the main transaction if possible
        # Actually, PRAGMAs like WAL/synchronous should be set outside the main transaction if they change the file state.
        content = content.replace('with self._engine.begin() as conn:', 
                                 '# Set performance PRAGMAs\n        with self._engine.connect() as pragma_conn:\n            pragma_conn.execute(text("PRAGMA journal_mode = WAL"))\n            pragma_conn.execute(text("PRAGMA synchronous = OFF"))\n\n        with self._engine.begin() as conn:', 1)

# 2. Vectorize extract_year in insert_company_data
old_extract = """                def extract_year(label):
                    label = str(label)
                    if label.isdigit() and len(label) == 4:
                        return int(label)
                    match = re.search(r'\\dQ(\\d{2})', label)
                    if match:
                        return 2000 + int(match.group(1))
                    return None

                df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)"""

# Note: The backslashes in regex need to be handled carefully in the python script.
# In the source it is: match = re.search(r'\dQ(\d{2})', label)

new_extract = """                # Vectorized extract_year
                df_long['REPORT_YEAR'] = None
                labels = df_long['PERIOD_LABEL'].astype(str)
                # Annual: 2024
                mask_ann = labels.str.match(r'^\\d{4}$')
                df_long.loc[mask_ann, 'REPORT_YEAR'] = labels[mask_ann].astype(int)
                # Quarterly: 1Q24
                mask_qtr = labels.str.match(r'^\\dQ(\\d{2})$')
                if mask_qtr.any():
                    yy = labels[mask_qtr].str.extract(r'\\dQ(\\d{2})')[0].astype(int)
                    df_long.loc[mask_qtr, 'REPORT_YEAR'] = 2000 + yy"""

if "df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)" in content:
    print("Found old extract_year apply, replacing...")
    # Replacing the block. Using a more unique part to find it.
    start_point = content.find('def extract_year(label):')
    end_point = content.find("df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)")
    if start_point != -1 and end_point != -1:
        content = content[:start_point] + new_extract + content[end_point + len("df_long['REPORT_YEAR'] = df_long['PERIOD_LABEL'].apply(extract_year)"):]

# 3. Optimize to_sql with method='multi'
if "df_to_insert.to_sql('qa_logs', conn, if_exists='append', index=False)" in content:
    content = content.replace("df_to_insert.to_sql('qa_logs', conn, if_exists='append', index=False)",
                             "df_to_insert.to_sql('qa_logs', conn, if_exists='append', index=False, method='multi')")

if "final_df.to_sql('financial_reports', conn, if_exists='append', index=False)" in content:
    content = content.replace("final_df.to_sql('financial_reports', conn, if_exists='append', index=False)",
                             "final_df.to_sql('financial_reports', conn, if_exists='append', index=False, method='multi')")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimization 2: Database layer optimized (WAL mode, Vectorized years, Multi-row inserts).")
