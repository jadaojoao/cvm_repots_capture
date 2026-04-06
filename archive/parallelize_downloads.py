# -*- coding: utf-8 -*-
import os

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\src\scraper.py'
with open(path, 'r', encoding='latin1') as f:
    content = f.read()

# Refactor run method to use Parallel Downloads
old_loop = """        for year in years:
            dfp_success = self.download_and_extract(year, 'DFP')
            itr_success = self.download_and_extract(year, 'ITR')
            
            if dfp_success:
                years_downloaded['DFP'].append(year)
            else:
                years_failed['DFP'].append(year)
                
            if itr_success:
                years_downloaded['ITR'].append(year)
            else:
                years_failed['ITR'].append(year)"""

new_parallel = """        # Parallel Download Task Queue
        tasks = []
        for year in years:
            tasks.append((year, 'DFP'))
            tasks.append((year, 'ITR'))
            
        print(f"  Launching {len(tasks)} parallel download tasks...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # map maintains order, but we want result with year/type info
            futures = {executor.submit(self.download_and_extract, y, t): (y, t) for y, t in tasks}
            
            for future in futures:
                y, t = futures[future]
                try:
                    success = future.result()
                    if success:
                        years_downloaded[t].append(y)
                    else:
                        years_failed[t].append(y)
                except Exception as e:
                    print(f"  Parallel download error [{y} {t}]: {e}")
                    years_failed[t].append(y)"""

if old_loop in content:
    print("Found old sequential download loop, replacing with parallel executor...")
    content = content.replace(old_loop, new_parallel)

with open(path, 'w', encoding='latin1') as f:
    f.write(content)

print("Optimization 3: Parallelized downloads implemented in scraper.py.")
