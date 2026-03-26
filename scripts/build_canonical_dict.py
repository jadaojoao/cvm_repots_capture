"""
build_canonical_dict.py — Constrói o dicionário canônico de contas CVM.

Lê os arquivos XLSX de plano de contas fixas da CVM (entender_CD/plano-contas-fixas-DFP/)
e gera data/canonical_accounts.csv com a hierarquia completa de CD_CONTA → STANDARD_NAME.

Uso:
    python scripts/build_canonical_dict.py
"""

import sys
import os
import re
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Garante UTF-8 no stdout no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
# Pasta com os XLSXs do plano de contas fixas da CVM
ENTENDER_CD_DIR = os.path.join(os.path.dirname(__file__), '..', 'entender_CD', 'plano-contas-fixas-DFP')

# Arquivo de saída
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'canonical_accounts.csv')
# ==============================================================================

# Mapeamento: trecho do nome da aba -> STATEMENT_TYPE
SHEET_TO_STATEMENT = [
    ('Ativo',                'BPA'),
    ('Passivo',              'BPP'),
    ('Resultado Per',        'DRE'),
    ('Resultado Abrangente', 'DRA'),
    ('Fluxo',                'DFC'),
    ('DMPL',                 'DMPL'),
    ('Valor Adicionado',     'DVA'),
]

# Mapeamento de arquivo -> tipo de empresa
FILE_TO_TIPO = {
    'Empresas Comerciais': 'comercial',
    'Instituições Financeiras': 'financeira',
    'Instituicoes Financeiras': 'financeira',
    'InstituiçΣes Financeiras': 'financeira',  # encoding corrupto
    'Seguradoras': 'seguradora',
}


def get_statement_type(sheet_name: str) -> str | None:
    for keyword, stmt in SHEET_TO_STATEMENT:
        if keyword in sheet_name:
            return stmt
    return None


def get_empresa_tipo(filename: str) -> str:
    for key, tipo in FILE_TO_TIPO.items():
        if key.lower() in filename.lower():
            return tipo
    return 'comercial'  # default


def get_nivel(cd_conta: str) -> int:
    """Calcula o nível hierárquico pelo número de pontos + 1."""
    return cd_conta.count('.') + 1


def extract_accounts_from_xlsx(xlsx_path: str) -> list[dict]:
    """
    Extrai todas as contas (CD_CONTA, STANDARD_NAME, STATEMENT_TYPE, IS_CONSOLIDADO)
    de um arquivo XLSX do plano de contas CVM.

    Retorna uma lista de dicionários.
    """
    filename = os.path.basename(xlsx_path)
    empresa_tipo = get_empresa_tipo(filename)

    xls = pd.ExcelFile(xlsx_path)
    records = []

    for sheet in xls.sheet_names:
        statement_type = get_statement_type(sheet)
        if not statement_type:
            continue

        is_consolidado = 'Cons.' in sheet or 'consolidado' in sheet.lower()

        df = pd.read_excel(xls, sheet_name=sheet, header=None)

        for _, row in df.iterrows():
            for j, v in enumerate(row.values):
                if not isinstance(v, str):
                    continue
                v = v.strip()
                # Identifica CD_CONTA: começa com dígito, tem ponto, ex: "1.01" ou "3.04.01"
                if not re.match(r'^\d+\.\d+', v):
                    continue

                # Busca a descrição nas colunas seguintes
                standard_name = ''
                for k in range(j + 1, min(j + 6, len(row.values))):
                    candidate = str(row.values[k]).strip()
                    if (candidate and candidate != 'nan'
                            and not re.match(r'^[\d0]', candidate)
                            and len(candidate) > 2):
                        standard_name = candidate
                        break

                if not standard_name:
                    continue

                records.append({
                    'CD_CONTA': v,
                    'STANDARD_NAME': standard_name,
                    'STATEMENT_TYPE': statement_type,
                    'EMPRESA_TIPO': empresa_tipo,
                    'NIVEL': get_nivel(v),
                    'IS_CONSOLIDADO': is_consolidado,
                })
                break  # próxima linha

    return records


def build_canonical_dict():
    print("=" * 60)
    print("Build Canonical Account Dictionary")
    print("=" * 60)

    if not os.path.isdir(ENTENDER_CD_DIR):
        print(f"ERRO: pasta nao encontrada: {ENTENDER_CD_DIR}")
        sys.exit(1)

    xlsx_files = [f for f in os.listdir(ENTENDER_CD_DIR) if f.endswith('.xlsx')]
    if not xlsx_files:
        print(f"ERRO: nenhum XLSX encontrado em {ENTENDER_CD_DIR}")
        sys.exit(1)

    all_records = []

    for xlsx_file in sorted(xlsx_files):
        path = os.path.join(ENTENDER_CD_DIR, xlsx_file)
        print(f"\nProcessando: {xlsx_file}")
        records = extract_accounts_from_xlsx(path)
        print(f"  -> {len(records)} contas extraidas")
        all_records.extend(records)

    if not all_records:
        print("ERRO: nenhuma conta extraida.")
        sys.exit(1)

    df = pd.DataFrame(all_records)

    # Remove duplicatas exatas
    before = len(df)
    df = df.drop_duplicates(subset=['CD_CONTA', 'STATEMENT_TYPE', 'EMPRESA_TIPO', 'IS_CONSOLIDADO'])
    print(f"\nDeduplicacao: {before} -> {len(df)} registros")

    # Ordena
    df = df.sort_values(['EMPRESA_TIPO', 'IS_CONSOLIDADO', 'STATEMENT_TYPE', 'CD_CONTA'])

    # Salva
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    print(f"\nSalvo em: {OUTPUT_CSV}")
    print(f"Total: {len(df)} contas unicas")
    print("\nDistribuicao por STATEMENT_TYPE:")
    print(df.groupby(['EMPRESA_TIPO', 'STATEMENT_TYPE']).size().to_string())
    print("\nAmostra BPA comercial:")
    sample = df[(df['EMPRESA_TIPO'] == 'comercial') & (df['STATEMENT_TYPE'] == 'BPA')].head(8)
    for _, row in sample.iterrows():
        print(f"  {row['CD_CONTA']:<28} {row['STANDARD_NAME']}")
    print("\nDone!")


if __name__ == '__main__':
    build_canonical_dict()
