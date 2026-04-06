from src.scraper import CVMScraper

# Using exact CVM Codes for top liquid companies
companies = [
    '9512',   # Petrobras
    '4170',   # Vale
    '19348',  # Itau
    '906',    # Bradesco
    '23264',  # Ambev
    '5410',   # Weg
    '2437',   # Eletrobras
    '11612',  # B3
    '13240',  # Suzano
    '22739',  # Raia Drogasil
    '20658',  # Equatorial
    '22275',  # Localiza
    '24180',  # Rumo
    '21431',  # Cosan
    '24201',  # Vibra
    '14443',  # Sabesp
    '23132',  # BB Seguridade
    '25380',  # Rede D Or
    '24512',  # Hapvida
    '17671'   # Telefonica
]

scraper = CVMScraper()
scraper.run(companies, 2023, 2025)

print("Mass extraction finished for liquid companies!")
