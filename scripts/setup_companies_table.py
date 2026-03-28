# -*- coding: utf-8 -*-
"""
scripts/setup_companies_table.py — Popula a tabela `companies` com metadados.

Cruza dados de:
  - financial_reports (empresas já no banco)
  - cad_cia_aberta.csv da CVM (CNPJ, setor, nome comercial)
  - TICKER_MAP de dashboard/constants.py (tickers B3)
  - Excel base_analitica_dashboard_preenchida.xlsx (setor analítico — se existir)

Idempotente: pode rodar múltiplas vezes, usa INSERT OR REPLACE.

Uso:
    python scripts/setup_companies_table.py
    python scripts/setup_companies_table.py --dry-run
    python scripts/setup_companies_table.py --no-cvm-download   # usa só dados locais
"""
import sys
import os
import io
import argparse
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

CVM_MASTER_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"


def fetch_cvm_master() -> "pd.DataFrame":
    """Baixa cadastro completo da CVM. Retorna DataFrame com CD_CVM, CNPJ, setor, nomes."""
    import requests
    import pandas as pd

    log.info(f"Baixando cadastro CVM: {CVM_MASTER_URL}")
    resp = requests.get(CVM_MASTER_URL, timeout=30)
    resp.raise_for_status()

    df = pd.read_csv(
        io.BytesIO(resp.content), sep=";", encoding="latin1",
        usecols=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "CNPJ_CIA", "SETOR_ATIV", "SIT"],
        dtype={"CD_CVM": str, "CNPJ_CIA": str},
    )
    df["CD_CVM"] = df["CD_CVM"].str.strip()
    df = df[df["CD_CVM"].str.match(r"^\d+$", na=False)].copy()
    df["CD_CVM"] = df["CD_CVM"].astype(int)

    # Nome: preferir comercial, fallback para social
    df["DENOM_COMERC"] = df["DENOM_COMERC"].fillna("").str.strip()
    df["DENOM_SOCIAL"] = df["DENOM_SOCIAL"].fillna("").str.strip()
    df["SETOR_ATIV"]   = df["SETOR_ATIV"].fillna("").str.strip()
    df["CNPJ_CIA"]     = df["CNPJ_CIA"].fillna("").str.strip()

    log.info(f"  {len(df)} empresas no cadastro CVM ({(df['SIT']=='A').sum()} ativas)")
    return df.drop_duplicates(subset="CD_CVM").set_index("CD_CVM")


def load_existing_companies(conn) -> "pd.DataFrame":
    """Empresas já no banco: CD_CVM, COMPANY_NAME, COMPANY_TYPE."""
    import pandas as pd
    from sqlalchemy import text

    df = pd.read_sql(
        text('SELECT DISTINCT "CD_CVM", "COMPANY_NAME", "COMPANY_TYPE" FROM financial_reports ORDER BY "CD_CVM"'),
        conn,
    )
    df["CD_CVM"] = df["CD_CVM"].astype(int)
    log.info(f"  {len(df)} empresas distintas em financial_reports")
    return df


def load_sector_excel() -> dict:
    """Carrega mapa setor_analitico do Excel (se existir). Retorna {cd_cvm: setor}."""
    import pandas as pd

    excel_path = ROOT / "output" / "reports" / "base_analitica_dashboard_preenchida.xlsx"
    _overrides = {
        24783: 'Farmacêutico e Higiene',
        22217: 'Seguradoras e Corretoras',
        22187: 'Petróleo e Gás',
        25291: 'Petróleo e Gás',
         5410: 'Máquinas, Equipamentos, Veículos e Peças',
         2437: 'Energia Elétrica',
    }

    if excel_path.exists():
        try:
            df = pd.read_excel(excel_path, usecols=["cd_cvm", "setor_analitico"])
            sm = df.dropna(subset=["setor_analitico"]).set_index("cd_cvm")["setor_analitico"].to_dict()
            sm.update(_overrides)
            log.info(f"  {len(sm)} setores analíticos carregados do Excel")
            return sm
        except Exception as e:
            log.warning(f"  Erro ao ler Excel: {e}")

    log.info(f"  Excel não encontrado — usando {len(_overrides)} setores hardcoded")
    return dict(_overrides)


def build_companies_df(existing_df, cvm_df, ticker_map, sector_map) -> "pd.DataFrame":
    """Monta DataFrame final para inserção na tabela companies."""
    import pandas as pd

    rows = []
    for _, row in existing_df.iterrows():
        cd_cvm = int(row["CD_CVM"])
        cvm_info = cvm_df.loc[cd_cvm] if cd_cvm in cvm_df.index else None

        nome_comercial = None
        cnpj = None
        setor_cvm = None
        is_active = 1

        if cvm_info is not None:
            nome_comercial = cvm_info["DENOM_COMERC"] or None
            cnpj_raw = str(cvm_info["CNPJ_CIA"]).strip()
            cnpj = cnpj_raw if cnpj_raw and cnpj_raw != "nan" else None
            setor_raw = str(cvm_info["SETOR_ATIV"]).strip()
            setor_cvm = setor_raw if setor_raw and setor_raw != "nan" else None
            sit = str(cvm_info.get("SIT", "ATIVO")).strip().upper()
            is_active = 1 if sit in ("A", "ATIVO") else 0

        rows.append({
            "cd_cvm":          cd_cvm,
            "company_name":    str(row["COMPANY_NAME"]),
            "nome_comercial":  nome_comercial,
            "cnpj":            cnpj,
            "setor_cvm":       setor_cvm,
            "setor_analitico": sector_map.get(cd_cvm),
            "company_type":    str(row.get("COMPANY_TYPE", "comercial") or "comercial"),
            "ticker_b3":       ticker_map.get(cd_cvm),
            "is_active":       is_active,
        })

    return pd.DataFrame(rows)


def upsert_companies(conn, df: "pd.DataFrame", dry_run: bool) -> None:
    """INSERT OR REPLACE em companies."""
    from sqlalchemy import text

    if dry_run:
        tickers_found = df["ticker_b3"].notna().sum()
        setores_found = df["setor_analitico"].notna().sum()
        cnpjs_found   = df["cnpj"].notna().sum()
        log.info(f"  [DRY-RUN] Inseriria {len(df)} empresas:")
        log.info(f"    com ticker_b3:       {tickers_found}")
        log.info(f"    com setor_analitico: {setores_found}")
        log.info(f"    com CNPJ:            {cnpjs_found}")
        log.info(f"    com setor_cvm:       {df['setor_cvm'].notna().sum()}")
        return

    # Verificar se tabela existe
    try:
        conn.execute(text("SELECT 1 FROM companies LIMIT 1"))
    except Exception:
        log.error("  Tabela companies não existe. Execute: python scripts/setup_db.py --step 2")
        return

    for _, row in df.iterrows():
        conn.execute(text("""
            INSERT OR REPLACE INTO companies
            (cd_cvm, company_name, nome_comercial, cnpj, setor_cvm,
             setor_analitico, company_type, ticker_b3, is_active, updated_at)
            VALUES
            (:cd_cvm, :company_name, :nome_comercial, :cnpj, :setor_cvm,
             :setor_analitico, :company_type, :ticker_b3, :is_active,
             strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        """), {
            "cd_cvm":          int(row["cd_cvm"]),
            "company_name":    row["company_name"],
            "nome_comercial":  row["nome_comercial"],
            "cnpj":            row["cnpj"],
            "setor_cvm":       row["setor_cvm"],
            "setor_analitico": row["setor_analitico"],
            "company_type":    row["company_type"],
            "ticker_b3":       row["ticker_b3"],
            "is_active":       int(row["is_active"]),
        })

    total = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar()
    tickers = conn.execute(text("SELECT COUNT(*) FROM companies WHERE ticker_b3 IS NOT NULL")).scalar()
    setores = conn.execute(text("SELECT COUNT(*) FROM companies WHERE setor_analitico IS NOT NULL")).scalar()
    log.info(f"  ✓ {total} empresas em companies | {tickers} com ticker | {setores} com setor analítico")


def print_summary(conn) -> None:
    """Imprime resumo dos dados inseridos."""
    from sqlalchemy import text

    log.info("")
    log.info("=== Resumo da tabela companies ===")
    rows = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN ticker_b3 IS NOT NULL THEN 1 ELSE 0 END) as com_ticker,
            SUM(CASE WHEN setor_analitico IS NOT NULL THEN 1 ELSE 0 END) as com_setor,
            SUM(CASE WHEN cnpj IS NOT NULL THEN 1 ELSE 0 END) as com_cnpj,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as ativas
        FROM companies
    """)).fetchone()

    log.info(f"  Total:          {rows[0]}")
    log.info(f"  Com ticker B3:  {rows[1]}")
    log.info(f"  Com setor:      {rows[2]}")
    log.info(f"  Com CNPJ:       {rows[3]}")
    log.info(f"  Ativas:         {rows[4]}")

    # Distribuição de setores CVM (top 10)
    top_setores = conn.execute(text("""
        SELECT setor_cvm, COUNT(*) as n
        FROM companies WHERE setor_cvm IS NOT NULL
        GROUP BY setor_cvm ORDER BY n DESC LIMIT 10
    """)).fetchall()
    if top_setores:
        log.info("")
        log.info("  Top 10 setores CVM:")
        for s, n in top_setores:
            log.info(f"    {n:3d}  {s}")


def main():
    parser = argparse.ArgumentParser(
        description="Popula tabela companies com dados da CVM + tickers + setores"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-cvm-download", action="store_true",
                        help="Não baixa o cadastro da CVM (usa só dados do banco)")
    args = parser.parse_args()

    import pandas as pd
    from dashboard.db import get_engine
    from dashboard.constants import TICKER_MAP

    engine = get_engine()

    # Baixar cadastro CVM
    if args.no_cvm_download:
        log.info("--no-cvm-download: usando DataFrame vazio para dados CVM")
        cvm_df = pd.DataFrame(
            columns=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "CNPJ_CIA", "SETOR_ATIV", "SIT"]
        ).set_index("CD_CVM")
    else:
        cvm_df = fetch_cvm_master()

    # Carregar setor analítico do Excel
    sector_map = load_sector_excel()

    with engine.begin() as conn:
        # Empresas do banco
        existing_df = load_existing_companies(conn)

        # Montar DataFrame final
        companies_df = build_companies_df(existing_df, cvm_df, TICKER_MAP, sector_map)

        log.info("=== Inserindo em companies ===")
        upsert_companies(conn, companies_df, args.dry_run)

        if not args.dry_run:
            print_summary(conn)

    if not args.dry_run:
        log.info("")
        log.info("Próximos passos:")
        log.info("  python scripts/expand_tickers.py   ← descobrir mais tickers B3")


if __name__ == "__main__":
    main()
