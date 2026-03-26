# -*- coding: utf-8 -*-
from src.scraper import CVMScraper
companies = ['9512','4170','19348','906','23264','5410','2437','14443','21431','24180','25380','17671']
scraper = CVMScraper()
scraper.run(companies, 2022, 2025)
print("FULL reload 2022-2025 complete!")
