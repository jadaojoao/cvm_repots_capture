import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.dictionary import DictionaryBuilder
import argparse
from datetime import datetime

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
# Directories
DEFAULT_DATA_DIR = "../data/input" # Relative to scripts/
DEFAULT_OUTPUT_DIR = "../data"     # Output to data/ directory for the dictionary
# Note: Dictionary is considered 'data' used by scraper or analysis, 
# but user might want it in root output. 
# Plan said: cvm_account_dictionary.csv -> data/
# So OUTPUT_DIR here should be "../data"

# Default Execution Parameters
DEFAULT_START_YEAR = 2020
DEFAULT_END_YEAR = datetime.now().year
DEFAULT_MAX_COMPANIES = None

# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Build CVM Master Account Dictionary")
    parser.add_argument("--start_year", type=int, default=DEFAULT_START_YEAR, help="Start year")
    parser.add_argument("--end_year", type=int, default=DEFAULT_END_YEAR, help="End year")
    parser.add_argument("--max_companies", type=int, default=DEFAULT_MAX_COMPANIES, help="Limit number of companies to scan")
    
    args = parser.parse_args()
    
    # Resolve relative paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, DEFAULT_DATA_DIR)
    output_dir = os.path.join(script_dir, DEFAULT_OUTPUT_DIR)
    
    print(f"Building dictionary...")
    print(f"Data Dir: {data_dir}")
    print(f"Output Dir: {output_dir}")

    builder = DictionaryBuilder(
        start_year=args.start_year, 
        end_year=args.end_year, 
        data_dir=data_dir, 
        output_dir=output_dir,
        max_companies=args.max_companies
    )
    builder.build()

if __name__ == "__main__":
    main()
