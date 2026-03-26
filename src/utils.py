"""
Utility functions for CVM data processing.
Provides account name normalization and deterministic LINE_ID generation.
"""

from __future__ import annotations

import pandas as pd
import unicodedata
import re
import hashlib
from typing import Union


def normalize_account_name(text: Union[str, float, None]) -> str:
    """
    Normalizes account description for stable matching.
    
    Steps:
    1. Convert to string and handle None/NaN
    2. Convert to lowercase
    3. Remove accents (NFD decomposition)
    4. Replace NBSP (\xa0) with regular space
    5. Standardize hyphens/dashes to single dash
    6. Collapse multiple spaces to single space
    7. Trim leading/trailing whitespace
    8. Remove special characters except dash, parentheses, slash
    
    Args:
        text: Account description string
        
    Returns:
        Normalized string
        
    Examples:
        >>> normalize_account_name("Ativo  Total")
        'ativo total'
        >>> normalize_account_name("Receita Líquida")
        'receita liquida'
        >>> normalize_account_name("Fluxo\\xa0de\\xa0Caixa")
        'fluxo de caixa'
    """
    if pd.isna(text):
        return ""
    
    # Convert to string
    text = str(text)
    
    # Lowercase
    text = text.lower()
    
    # Remove accents using NFD normalization
    # NFD separates base characters from combining marks (accents)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Replace NBSP (U+00A0) with regular space — \xa0 e \u00A0 são o mesmo codepoint
    text = text.replace('\xa0', ' ')
    
    # Standardize various hyphens and dashes to single dash
    text = re.sub(r'[‐‑‒–—―]', '-', text)
    
    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim leading/trailing whitespace
    text = text.strip()
    
    return text


def generate_line_id_base(row: pd.Series, statement_type: str) -> str:
    """
    Generates stable LINE_ID_BASE for account (no sequence numbers, no version info).
    
    This creates an ACCOUNT-LEVEL identifier, not a record-level identifier.
    Multiple periods for the same account will share the same LINE_ID_BASE.
    
    Logic:
    - If CD_CONTA exists and is non-empty → return CD_CONTA as string
    - Otherwise → return "DS|" + hash of normalized components
    
    Hash components (stable, version-independent):
    - DS_CONTA_norm (normalized account name)
    - statement_type (BPA, BPP, DRE, DFC)
    - NIVEL_CONTA (if available)
    - GRUPO_DRE (if available and statement is DRE)
    
    NOTE: ORDEM_EXERC is NOT included as it varies by version.
    
    Args:
        row: pandas Series representing a data row
        statement_type: string ('BPA', 'BPP', 'DRE', 'DFC')
        
    Returns:
        string LINE_ID_BASE (stable account identifier)
        
    Examples:
        >>> row = pd.Series({'CD_CONTA': '1.01', 'DS_CONTA_norm': 'ativo circulante'})
        >>> generate_line_id_base(row, 'BPA')
        '1.01'
        
        >>> row = pd.Series({'CD_CONTA': None, 'DS_CONTA_norm': 'nota explicativa 1'})
        >>> generate_line_id_base(row, 'DRE')
        'DS|...' # hash value
    """
    # Primary: Use CD_CONTA if available
    cd_conta = row.get('CD_CONTA')
    if pd.notna(cd_conta) and str(cd_conta).strip():
        return str(cd_conta).strip()
    
    # Fallback: Generate hash-based ID using stable components only
    components = [
        str(row.get('DS_CONTA_norm', '')),
        str(statement_type)
    ]
    
    # Add stable metadata fields (exclude version-specific fields like ORDEM_EXERC)
    if 'NIVEL_CONTA' in row.index and pd.notna(row.get('NIVEL_CONTA')):
        components.append(str(row['NIVEL_CONTA']))
    
    if statement_type == 'DRE' and 'GRUPO_DRE' in row.index and pd.notna(row.get('GRUPO_DRE')):
        components.append(str(row['GRUPO_DRE']))
    
    # Create deterministic hash
    hash_input = '|'.join(components)
    hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
    hash_str = hash_obj.hexdigest()[:16]  # First 16 chars for readability
    
    return f"DS|{hash_str}"


def validate_line_ids(df: pd.DataFrame) -> int:
    """
    Validates that all value-bearing lines have LINE_ID_BASE.

    Args:
        df: DataFrame with VL_CONTA and LINE_ID_BASE columns

    Raises:
        ValueError: If any line with non-zero value lacks LINE_ID_BASE

    Returns:
        int: Count of validated lines
    """
    id_col = 'LINE_ID_BASE'

    if id_col not in df.columns:
        raise ValueError("DataFrame must have LINE_ID_BASE column")
    
    # Find lines with values but no ID
    missing_id = df[
        (df['VL_CONTA'].notna()) & 
        (df['VL_CONTA'] != 0) & 
        (df[id_col].isna() | (df[id_col] == ''))
    ]
    
    if len(missing_id) > 0:
        print(f"⚠️ WARNING: {len(missing_id)} lines with values lack {id_col}")
        print(missing_id[['DS_CONTA', 'VL_CONTA']].head(10))
        raise ValueError(f"{len(missing_id)} lines with values lack {id_col}")
    
    return len(df[df['VL_CONTA'].notna()])


# Test functions if run directly
if __name__ == "__main__":
    # Test normalization
    test_cases = [
        ("Ativo  Total", "ativo total"),
        ("Receita Líquida", "receita liquida"),
        ("Fluxo\xa0de\xa0Caixa", "fluxo de caixa"),
        ("Provisão para Créditos–Baixa", "provisao para creditos-baixa"),
        ("ATIVO   CIRCULANTE", "ativo circulante"),
    ]
    
    print("Testing normalize_account_name():")
    for input_text, expected in test_cases:
        result = normalize_account_name(input_text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text}' → '{result}' (expected: '{expected}')")
    
    # Test LINE_ID generation
    print("\nTesting generate_line_id_base():")

    # With CD_CONTA
    row1 = pd.Series({
        'CD_CONTA': '1.01',
        'DS_CONTA_norm': 'ativo circulante'
    })
    line_id1 = generate_line_id_base(row1, 'BPA')
    print(f"  With CD_CONTA: {line_id1} (expected: '1.01')")

    # Without CD_CONTA
    row2 = pd.Series({
        'CD_CONTA': None,
        'DS_CONTA_norm': 'nota explicativa 1'
    })
    line_id2 = generate_line_id_base(row2, 'DRE')
    print(f"  Without CD_CONTA: {line_id2} (expected: 'DS|...')")
    print(f"    Starts with 'DS|': {line_id2.startswith('DS|')}")
