# -*- coding: utf-8 -*-
"""
Automacao do scraper para o universo ja presente no banco.

Uso:
    python scripts/atualizar_todos.py
    python scripts/atualizar_todos.py --anos 2024 2025
    python scripts/atualizar_todos.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.contracts import RefreshPolicy, RefreshRequest
from src.db import build_engine
from src.refresh_service import HeadlessRefreshService
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report

BATCH_SIZE = 10
DEFAULT_ANOS = [datetime.now().year - 1, datetime.now().year]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def get_all_companies(settings) -> list[tuple[int, str]]:
    """Retorna lista de (CD_CVM, COMPANY_NAME) distintos do banco."""
    engine = build_engine(settings)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT CD_CVM, COMPANY_NAME FROM financial_reports ORDER BY CD_CVM")
        ).fetchall()
    return [(int(row[0]), row[1]) for row in rows]


def run_update(anos: list[int], dry_run: bool = False) -> None:
    settings = build_settings(project_root=ROOT)
    startup_report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports",),
        require_canonical_accounts=True,
    )
    if startup_report.issues:
        log.info(format_startup_report(startup_report))
        if startup_report.errors:
            raise RuntimeError("Ambiente nao pronto para atualizar_todos.py")

    companies = get_all_companies(settings)
    company_codes = [str(cd_cvm) for cd_cvm, _ in companies]
    log.info("Empresas no banco: %s", len(companies))
    log.info("Anos a atualizar: %s", anos)

    if dry_run:
        log.info("[DRY-RUN] Nenhuma requisicao sera feita.")
        for cd_cvm, company_name in companies:
            log.info("  %6s  %s", cd_cvm, company_name)
        return

    start_year = min(anos)
    end_year = max(anos)
    service = HeadlessRefreshService(settings=settings)

    for index in range(0, len(company_codes), BATCH_SIZE):
        batch_codes = company_codes[index : index + BATCH_SIZE]
        batch_names = [
            companies[row_index][1]
            for row_index in range(index, min(index + BATCH_SIZE, len(companies)))
        ]
        batch_number = index // BATCH_SIZE + 1
        log.info("Lote %s: %s", batch_number, batch_names)
        try:
            request = RefreshRequest(
                companies=tuple(batch_codes),
                start_year=start_year,
                end_year=end_year,
                max_workers=2,
                data_dir=str(settings.paths.input_dir),
                output_dir=str(settings.paths.reports_dir),
                policy=RefreshPolicy(
                    skip_complete_company_years=True,
                    enable_fast_lane=False,
                    force_refresh=False,
                ),
            )
            result = service.execute(request)
            log.info(
                "Resumo do lote %s: success=%s no_data=%s error=%s synced=%s planned_company_years=%s",
                batch_number,
                result.success_count,
                result.no_data_count,
                result.error_count,
                result.synced_companies,
                result.planning_stats.get("planned_company_years", 0),
            )
        except Exception as exc:
            log.error("Erro no lote %s: %s", batch_number, exc)

    log.info("Atualizacao concluida.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Atualiza dados de todas as empresas ja presentes no banco CVM")
    parser.add_argument(
        "--anos",
        type=int,
        nargs="+",
        default=DEFAULT_ANOS,
        help="Anos a atualizar (padrao: ano atual e anterior)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista empresas sem fazer requisicoes",
    )
    args = parser.parse_args()

    settings = build_settings(project_root=ROOT)
    settings.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.paths.logs_dir / f"atualizar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
    logging.getLogger().addHandler(file_handler)
    log.info("Log: %s", log_file)

    run_update(anos=args.anos, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
