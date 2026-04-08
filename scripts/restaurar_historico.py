# -*- coding: utf-8 -*-
"""
Detecta e restaura anos faltantes no banco usando o planner headless.

Uso:
    python scripts/restaurar_historico.py
    python scripts/restaurar_historico.py --run
    python scripts/restaurar_historico.py --run --max 20
    python scripts/restaurar_historico.py --anos 2022 2023
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.contracts import RefreshPolicy, RefreshRequest
from src.db import build_engine
from src.refresh_service import HeadlessRefreshService
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

BATCH_SIZE = 10
DEFAULT_MAX = 50
DEFAULT_ANOS = [2022, 2023, 2024]


def load_company_catalog(settings) -> list[tuple[int, str]]:
    engine = build_engine(settings)
    query = text(
        """
        SELECT DISTINCT
            fr."CD_CVM" AS cd_cvm,
            COALESCE(c.company_name, fr."COMPANY_NAME") AS company_name
        FROM financial_reports fr
        LEFT JOIN companies c ON c.cd_cvm = fr."CD_CVM"
        ORDER BY fr."CD_CVM"
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [(int(row[0]), str(row[1] or f"CVM_{row[0]}")) for row in rows]


def build_restore_items(service: HeadlessRefreshService, settings, anos: list[int]) -> tuple[list[dict], dict[str, int]]:
    company_catalog = load_company_catalog(settings)
    if not company_catalog:
        return [], {
            "planned_companies": 0,
            "planned_company_years": 0,
            "skipped_complete_company_years": 0,
        }

    request = RefreshRequest(
        companies=tuple(str(cd_cvm) for cd_cvm, _ in company_catalog),
        start_year=min(anos),
        end_year=max(anos),
        max_workers=2,
        data_dir=str(settings.paths.input_dir),
        output_dir=str(settings.paths.reports_dir),
        policy=RefreshPolicy(
            skip_complete_company_years=True,
            enable_fast_lane=False,
            force_refresh=False,
        ),
    )
    planned_companies, year_overrides, stats = service.build_company_year_plan(request)
    name_by_code = {cd_cvm: company_name for cd_cvm, company_name in company_catalog}

    items = []
    for company_code in planned_companies:
        code = int(company_code)
        items.append(
            {
                "cd_cvm": code,
                "name": name_by_code.get(code, str(code)),
                "missing": year_overrides.get(code, []),
            }
        )
    return items, stats


def run_restore(service: HeadlessRefreshService, settings, items: list[dict], anos: list[int]) -> None:
    if not items:
        log.info("Nada a restaurar.")
        return

    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    total_company_years = sum(len(item["missing"]) for item in items)
    log.info(
        "Restaurando %s empresa(s), %s company-year(s) em %s lote(s)",
        len(items),
        total_company_years,
        total_batches,
    )

    for batch_index in range(0, len(items), BATCH_SIZE):
        batch = items[batch_index : batch_index + BATCH_SIZE]
        batch_number = batch_index // BATCH_SIZE + 1
        log.info("Lote %s/%s: %s", batch_number, total_batches, [item["name"] for item in batch])
        request = RefreshRequest(
            companies=tuple(str(item["cd_cvm"]) for item in batch),
            start_year=min(anos),
            end_year=max(anos),
            max_workers=2,
            data_dir=str(settings.paths.input_dir),
            output_dir=str(settings.paths.reports_dir),
            policy=RefreshPolicy(
                skip_complete_company_years=True,
                enable_fast_lane=False,
                force_refresh=False,
            ),
        )
        started_at = time.time()
        result = service.execute(request)
        log.info(
            "Resumo do lote %s: success=%s no_data=%s error=%s synced=%s em %.0fs",
            batch_number,
            result.success_count,
            result.no_data_count,
            result.error_count,
            result.synced_companies,
            time.time() - started_at,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Detecta e restaura anos faltantes no banco CVM")
    parser.add_argument("--run", action="store_true", help="Executa a restauracao; sem isso fica em dry-run")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, help=f"Maximo de empresas (padrao: {DEFAULT_MAX})")
    parser.add_argument("--anos", type=int, nargs="+", default=DEFAULT_ANOS, help=f"Anos a verificar (padrao: {DEFAULT_ANOS})")
    args = parser.parse_args()

    settings = build_settings(project_root=ROOT)
    report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports",),
        require_canonical_accounts=True,
    )
    if report.issues:
        log.info(format_startup_report(report))
        if report.errors:
            raise SystemExit(1)

    service = HeadlessRefreshService(settings=settings)
    items, stats = build_restore_items(service, settings, args.anos)
    items = items[: args.max]

    if not items:
        log.info("Todas as empresas possuem cobertura completa no range solicitado.")
        return

    total_missing = sum(len(item["missing"]) for item in items)
    log.info(
        "%s empresa(s) com anos faltantes (%s combinacoes company-year)",
        len(items),
        total_missing,
    )
    log.info(
        "Planner: planned_companies=%s planned_company_years=%s skipped_complete=%s",
        stats.get("planned_companies", 0),
        stats.get("planned_company_years", 0),
        stats.get("skipped_complete_company_years", 0),
    )
    for item in items:
        log.info("  %-40s (CVM %6s) falta=%s", item["name"], item["cd_cvm"], item["missing"])

    if not args.run:
        log.info("[DRY-RUN] Use --run para executar a restauracao.")
        return

    run_restore(service, settings, items, args.anos)
    log.info("Restauracao concluida.")


if __name__ == "__main__":
    main()
