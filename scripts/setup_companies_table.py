# -*- coding: utf-8 -*-
"""
Popula a tabela `companies` com metadados de empresa.

Cruza:
  - financial_reports
  - cadastro da CVM
  - ticker_map
  - Excel analitico opcional para setor_analitico
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import build_engine
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report
from src.ticker_map import TICKER_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CVM_MASTER_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"


def fetch_cvm_master(timeout: int) -> pd.DataFrame:
    log.info("Baixando cadastro CVM: %s", CVM_MASTER_URL)
    response = requests.get(CVM_MASTER_URL, timeout=timeout)
    response.raise_for_status()

    df = pd.read_csv(
        io.BytesIO(response.content),
        sep=";",
        encoding="latin1",
        usecols=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "CNPJ_CIA", "SETOR_ATIV", "SIT"],
        dtype={"CD_CVM": str, "CNPJ_CIA": str},
    )
    df["CD_CVM"] = df["CD_CVM"].str.strip()
    df = df[df["CD_CVM"].str.match(r"^\d+$", na=False)].copy()
    df["CD_CVM"] = df["CD_CVM"].astype(int)
    df["DENOM_COMERC"] = df["DENOM_COMERC"].fillna("").str.strip()
    df["DENOM_SOCIAL"] = df["DENOM_SOCIAL"].fillna("").str.strip()
    df["SETOR_ATIV"] = df["SETOR_ATIV"].fillna("").str.strip()
    df["CNPJ_CIA"] = df["CNPJ_CIA"].fillna("").str.strip()

    log.info("  %s empresas no cadastro CVM (%s ativas)", len(df), int((df["SIT"] == "A").sum()))
    return df.drop_duplicates(subset="CD_CVM").set_index("CD_CVM")


def load_existing_companies(conn) -> pd.DataFrame:
    df = pd.read_sql(
        text('SELECT DISTINCT "CD_CVM", "COMPANY_NAME", "COMPANY_TYPE" FROM financial_reports ORDER BY "CD_CVM"'),
        conn,
    )
    df["CD_CVM"] = df["CD_CVM"].astype(int)
    log.info("  %s empresas distintas em financial_reports", len(df))
    return df


def load_sector_excel(settings) -> dict[int, str]:
    excel_path = settings.paths.reports_dir / "base_analitica_dashboard_preenchida.xlsx"
    fallback = {
        24783: "Farmaceutico e Higiene",
        22217: "Seguradoras e Corretoras",
        22187: "Petroleo e Gas",
        25291: "Petroleo e Gas",
        5410: "Maquinas, Equipamentos, Veiculos e Pecas",
        2437: "Energia Eletrica",
    }

    if excel_path.exists():
        try:
            df = pd.read_excel(excel_path, usecols=["cd_cvm", "setor_analitico"])
            sector_map = df.dropna(subset=["setor_analitico"]).set_index("cd_cvm")["setor_analitico"].to_dict()
            sector_map.update(fallback)
            log.info("  %s setores analiticos carregados do Excel", len(sector_map))
            return sector_map
        except Exception as exc:
            log.warning("  Erro ao ler Excel de setor analitico: %s", exc)

    log.info("  Excel nao encontrado; usando %s setores fallback", len(fallback))
    return dict(fallback)


def build_companies_df(existing_df: pd.DataFrame, cvm_df: pd.DataFrame, sector_map: dict[int, str]) -> pd.DataFrame:
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
            is_active = 1 if sit in {"A", "ATIVO"} else 0

        rows.append(
            {
                "cd_cvm": cd_cvm,
                "company_name": str(row["COMPANY_NAME"]),
                "nome_comercial": nome_comercial,
                "cnpj": cnpj,
                "setor_cvm": setor_cvm,
                "setor_analitico": sector_map.get(cd_cvm),
                "company_type": str(row.get("COMPANY_TYPE", "comercial") or "comercial"),
                "ticker_b3": TICKER_MAP.get(cd_cvm),
                "is_active": is_active,
            }
        )
    return pd.DataFrame(rows)


def upsert_companies(conn, df: pd.DataFrame, dry_run: bool) -> None:
    if dry_run:
        log.info("  [DRY-RUN] Inseriria %s empresas", len(df))
        log.info("    com ticker_b3: %s", int(df["ticker_b3"].notna().sum()))
        log.info("    com setor_analitico: %s", int(df["setor_analitico"].notna().sum()))
        log.info("    com CNPJ: %s", int(df["cnpj"].notna().sum()))
        return

    try:
        conn.execute(text("SELECT 1 FROM companies LIMIT 1"))
    except Exception:
        log.error("  Tabela companies nao existe. Execute: python scripts/setup_db.py --step 2")
        return

    upsert_sql = text(
        """
        INSERT INTO companies
            (cd_cvm, company_name, nome_comercial, cnpj, setor_cvm,
             setor_analitico, company_type, ticker_b3, is_active, updated_at)
        VALUES
            (:cd_cvm, :company_name, :nome_comercial, :cnpj, :setor_cvm,
             :setor_analitico, :company_type, :ticker_b3, :is_active, :updated_at)
        ON CONFLICT(cd_cvm) DO UPDATE SET
            company_name = excluded.company_name,
            nome_comercial = excluded.nome_comercial,
            cnpj = excluded.cnpj,
            setor_cvm = excluded.setor_cvm,
            setor_analitico = excluded.setor_analitico,
            company_type = excluded.company_type,
            ticker_b3 = excluded.ticker_b3,
            is_active = excluded.is_active,
            updated_at = excluded.updated_at
        """
    )

    updated_at = datetime.utcnow().replace(microsecond=0).isoformat()
    for _, row in df.iterrows():
        conn.execute(
            upsert_sql,
            {
                "cd_cvm": int(row["cd_cvm"]),
                "company_name": row["company_name"],
                "nome_comercial": row["nome_comercial"],
                "cnpj": row["cnpj"],
                "setor_cvm": row["setor_cvm"],
                "setor_analitico": row["setor_analitico"],
                "company_type": row["company_type"],
                "ticker_b3": row["ticker_b3"],
                "is_active": int(row["is_active"]),
                "updated_at": updated_at,
            },
        )

    totals = conn.execute(
        text(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN ticker_b3 IS NOT NULL THEN 1 ELSE 0 END) AS com_ticker,
                SUM(CASE WHEN setor_analitico IS NOT NULL THEN 1 ELSE 0 END) AS com_setor
            FROM companies
            """
        )
    ).fetchone()
    log.info("  OK %s empresas em companies | %s com ticker | %s com setor analitico", totals[0], totals[1], totals[2])


def print_summary(conn) -> None:
    log.info("")
    log.info("=== Resumo da tabela companies ===")
    row = conn.execute(
        text(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN ticker_b3 IS NOT NULL THEN 1 ELSE 0 END) AS com_ticker,
                SUM(CASE WHEN setor_analitico IS NOT NULL THEN 1 ELSE 0 END) AS com_setor,
                SUM(CASE WHEN cnpj IS NOT NULL THEN 1 ELSE 0 END) AS com_cnpj,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS ativas
            FROM companies
            """
        )
    ).fetchone()
    log.info("  Total: %s", row[0])
    log.info("  Com ticker B3: %s", row[1])
    log.info("  Com setor: %s", row[2])
    log.info("  Com CNPJ: %s", row[3])
    log.info("  Ativas: %s", row[4])


def main() -> None:
    parser = argparse.ArgumentParser(description="Popula tabela companies com CVM + tickers + setores")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-cvm-download", action="store_true", help="Nao baixa o cadastro da CVM")
    args = parser.parse_args()

    settings = build_settings(project_root=ROOT)
    report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports", "companies"),
        require_canonical_accounts=False,
    )
    if report.issues:
        log.info(format_startup_report(report))
        if report.errors:
            raise SystemExit(1)

    engine = build_engine(settings)
    if args.no_cvm_download:
        log.info("--no-cvm-download: usando DataFrame vazio para dados CVM")
        cvm_df = pd.DataFrame(
            columns=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "CNPJ_CIA", "SETOR_ATIV", "SIT"]
        ).set_index("CD_CVM")
    else:
        cvm_df = fetch_cvm_master(settings.company_list_timeout)

    sector_map = load_sector_excel(settings)
    with engine.begin() as conn:
        existing_df = load_existing_companies(conn)
        companies_df = build_companies_df(existing_df, cvm_df, sector_map)
        log.info("=== Inserindo em companies ===")
        upsert_companies(conn, companies_df, args.dry_run)
        if not args.dry_run:
            print_summary(conn)

    if not args.dry_run:
        log.info("")
        log.info("Proximos passos:")
        log.info("  python scripts/expand_tickers.py")


if __name__ == "__main__":
    main()
