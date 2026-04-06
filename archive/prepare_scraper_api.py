# -*- coding: utf-8 -*-
import os

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\src\scraper.py'
with open(path, 'r', encoding='latin1') as f:
    content = f.read()

# 1. Update __init__ to accept max_workers
if 'report_type=\'consolidated\'):' in content:
    content = content.replace('report_type=\'consolidated\'):', 'report_type=\'consolidated\', max_workers=5):')
    content = content.replace('self.report_type = report_type', 'self.report_type = report_type\n        self.max_workers = max_workers')

# 2. Update run() to use self.max_workers and Progress Callback (optional)
if 'def run(self, companies, start_year, end_year):' in content:
    content = content.replace('def run(self, companies, start_year, end_year):', 'def run(self, companies, start_year, end_year, progress_callback=None):')

if 'with ThreadPoolExecutor(max_workers=5) as executor:' in content:
    content = content.replace('with ThreadPoolExecutor(max_workers=5) as executor:', 'with ThreadPoolExecutor(max_workers=self.max_workers) as executor:')

# 3. Add progress_callback call inside company processing loop
# Found around line 1530+
if 'for name, cvm_code in resolved_companies.items():' in content:
    old_loop_start = 'for name, cvm_code in resolved_companies.items():\n            print(f"Processing data for {name} (CVM: {cvm_code})...")'
    new_loop_start = 'for i, (name, cvm_code) in enumerate(resolved_companies.items()):\n            if progress_callback: progress_callback(i, len(resolved_companies), name)\n            print(f"Processing data for {name} (CVM: {cvm_code})...")'
    content = content.replace(old_loop_start, new_loop_start)

with open(path, 'w', encoding='latin1') as f:
    f.write(content)

print("Scraper API: __init__ and run() updated for TUI compatibility.")
