# -*- coding: utf-8 -*-
import cProfile
import pstats
import io
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.scraper import CVMScraper

def profile_run():
    # Use a real CVM code but localized to 1-2 companies to avoid long wait
    # PETROBRAS (9512) and VALE (4170)
    companies = ['9512']
    # Use recent years to ensure data is there
    start_year = 2023
    end_year = 2024
    
    scraper = CVMScraper()
    scraper.run(companies, start_year, end_year)

if __name__ == "__main__":
    pr = cProfile.Profile()
    pr.enable()
    profile_run()
    pr.disable()
    
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(50)  # Top 50 functions
    print(s.getvalue())
