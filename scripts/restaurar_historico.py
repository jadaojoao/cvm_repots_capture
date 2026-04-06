# -*- coding: utf-8 -*-
"""
Restaurar Historico — Detecta e repõe anos faltantes (2022-2024) no banco.

Empresas que perderam dados históricos (ex.: DELETE sem escopo de ano) podem
ser restauradas re-executando o scraper apenas para os anos ausentes.

Uso:
    python scripts/restaurar_historico.py                  # dry-run (padrão)
    python scripts/restaurar_historico.py --run             # executa de fato
    python scripts/restaurar_historico.py --run --max 20    # limita a 20 empresas
    python scripts/restaurar_historico.py --anos 2022 2023  # anos específicos
"""
import sys
import argparse
import logging
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Garante UTF-8 no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)

BATCH_SIZE = 10
DEFAULT_MAX = 50
DEFAULT_ANOS = [2022, 2023, 2024]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_engine():
    """Retorna engine SQLAlchemy (Supabase se DATABASE_URL, senão SQLite)."""
    import os
    from sqlalchemy import create_engine

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return create_engine(db_url)
    db_path = ROOT / "data" / "db" / "cvm_financials.db"
    return create_engine(f"sqlite:///{db_path}")


def get_company_year_coverage(engine, target_years: list[int]) -> list[dict]:
    """Retorna lista de empresas com anos faltantes no range especificado."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Todas as empresas que possuem pelo menos 1 registro
        rows = conn.execute(
            text(
                "SELECT DISTINCT fr.\"CD_CVM\", c.company_name "
                "FROM financial_reports fr "
                "LEFT JOIN companies c ON fr.\"CD_CVM\" = c.cd_cvm "
                "ORDER BY fr.\"CD_CVM\""
            )
        ).fetchall()

        if not rows:
            log.warning("Nenhuma empresa encontrada no banco.")
            return []

        results = []
        for cd_cvm, name in rows:
            cd_cvm = int(cd_cvm)
            existing = conn.execute(
                text(
                    "SELECT DISTINCT \"REPORT_YEAR\" FROM financial_reports "
                    "WHERE \"CD_CVM\" = :cvm"
                ),
                {"cvm": cd_cvm},
            ).fetchall()
            existing_years = {int(r[0]) for r in existing if r[0]}
            missing = sorted(y for y in target_years if y not in existing_years)
            if missing:
                results.append({
                    "cd_cvm": cd_cvm,
                    "name": name or f"CVM_{cd_cvm}",
                    "existing": sorted(existing_years),
                    "missing": missing,
                })

    return results


def run_restore(items: list[dict]) -> None:
    """Executa o scraper para cada empresa/anos faltantes."""
    from src.scraper import CVMScraper

    if not items:
        log.info("Nada a restaurar.")
        return

    total_years = sum(len(it["missing"]) for it in items)
    total_batches = math.ceil(len(items) / BATCH_SIZE)
    log.info(
        f"Restaurando {len(items)} empresa(s), {total_years} ano(s) "
        f"em {total_batches} lote(s)"
    )

    ok, fail = 0, 0
    for batch_idx in range(0, len(items), BATCH_SIZE):
        batch = items[batch_idx : batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        log.info(
            f"Lote {batch_num}/{total_batches}: "
            f"{[it['name'] for it in batch]}"
        )
        t0 = time.time()
        for it in batch:
            try:
                scraper = CVMScraper()
                start = min(it["missing"])
                end = max(it["missing"])
                log.info(
                    f"  -> {it['name']} (CVM {it['cd_cvm']}): "
                    f"anos {it['missing']}"
                )
                scraper.run([str(it["cd_cvm"])], start, end)
                ok += 1
            except Exception as exc:
                log.error(f"  x {it['name']} (CVM {it['cd_cvm']}): {exc}")
                fail += 1

        elapsed = time.time() - t0
        log.info(f"Lote {batch_num} concluido em {elapsed:.0f}s")

    log.info(f"Resumo: {ok} ok, {fail} falha(s)")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Detecta e restaura anos faltantes no banco CVM."
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Executa a restauracao (padrao: dry-run apenas lista)",
    )
    parser.add_argument(
        "--max", type=int, default=DEFAULT_MAX,
        help=f"Maximo de empresas a restaurar (padrao: {DEFAULT_MAX})",
    )
    parser.add_argument(
        "--anos", type=int, nargs="+", default=DEFAULT_ANOS,
        help=f"Anos a verificar (padrao: {DEFAULT_ANOS})",
    )
    args = parser.parse_args()

    engine = _get_engine()
    log.info(f"Verificando cobertura para anos: {args.anos}")

    items = get_company_year_coverage(engine, args.anos)

    if not items:
        log.info("Todas as empresas possuem cobertura completa. Nada a fazer.")
        return

    # Limitar
    items = items[: args.max]

    # Exibir resumo
    total_missing = sum(len(it["missing"]) for it in items)
    log.info(
        f"{len(items)} empresa(s) com anos faltantes "
        f"({total_missing} combinacoes empresa/ano)"
    )
    for it in items:
        existing_str = ",".join(str(y) for y in it["existing"])
        missing_str = ",".join(str(y) for y in it["missing"])
        log.info(
            f"  {it['name']:40s} (CVM {it['cd_cvm']:6d}) "
            f"  tem=[{existing_str}]  falta=[{missing_str}]"
        )

    if not args.run:
        log.info(
            "[DRY-RUN] Use --run para executar a restauracao."
        )
        return

    run_restore(items)
    log.info("Restauracao concluida.")


if __name__ == "__main__":
    main()
