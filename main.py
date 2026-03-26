import sys

# Garante UTF-8 no stdout mesmo quando o output é redirecionado para arquivo no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.scraper import CVMScraper
import argparse
from datetime import datetime

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
# Directories
DEFAULT_DATA_DIR = "data/input"
DEFAULT_OUTPUT_DIR = "output/reports"

# Default Execution Parameters (if not provided via args)
DEFAULT_REPORT_TYPE = "consolidated" # Options: 'consolidated', 'individual'

# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="CVM Financial Data Scraper")
    parser.add_argument("--companies", nargs="+", required=True, help="List of company names or CVM codes")
    parser.add_argument("--start_year", type=int, required=True, help="Start year (YYYY)")
    parser.add_argument("--end_year", type=int, required=True, help="End year (YYYY)")
    parser.add_argument("--type", choices=['consolidated', 'individual'], default=DEFAULT_REPORT_TYPE, help="Report type")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Directory for output files")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Directory for data storage")
    
    args = parser.parse_args()
    
    print(f"Initializing Scraper for {args.companies}...")
    
    scraper = CVMScraper(output_dir=args.output_dir, data_dir=args.data_dir, report_type=args.type)
    scraper.run(args.companies, args.start_year, args.end_year)

if __name__ == "__main__":
    main()
