# -*- coding: utf-8 -*-
"""
Batch completo: refresh CVM em massa + cache yfinance.

Uso:
    python scripts/batch_completo.py
    python scripts/batch_completo.py --max-companies 200
    python scripts/batch_completo.py --dry-run
    python scripts/batch_completo.py --skip-yfinance
    python scripts/batch_completo.py --yfinance-only
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Garante UTF-8 no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.contracts import RefreshPolicy, RefreshRequest
from src.refresh_service import HeadlessRefreshService
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report

BATCH_SIZE = 10
DEFAULT_MAX = 150
DEFAULT_ANOS = [2022, datetime.now().year]
CVM_MASTER_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def get_active_companies(max_n: int, timeout: int) -> list[tuple[int, str]]:
    """Baixa o cadastro da CVM e retorna ate max_n empresas ativas."""
    log.info("Baixando lista de empresas ativas da CVM...")
    response = requests.get(CVM_MASTER_URL, timeout=timeout)
    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content), sep=";", encoding="latin1")
    active = df[df["SIT"] == "ATIVO"].copy()
    active = active.dropna(subset=["CD_CVM"])
    active["CD_CVM"] = active["CD_CVM"].astype(int)

    active["NAME"] = active["DENOM_COMERC"].fillna("").str.strip()
    empty_name_mask = active["NAME"] == ""
    active.loc[empty_name_mask, "NAME"] = (
        active.loc[empty_name_mask, "DENOM_SOCIAL"].fillna("").str.strip()
    )

    active = active.drop_duplicates(subset="CD_CVM")
    companies = list(zip(active["CD_CVM"].tolist(), active["NAME"].tolist()))
    log.info("Empresas ativas na CVM: %s (limitando em %s)", len(companies), max_n)
    return companies[:max_n]


def build_work_plan(
    companies: list[tuple[int, str]],
    *,
    start_year: int,
    end_year: int,
    service: HeadlessRefreshService,
    force_refresh: bool,
) -> tuple[list[tuple[int, str, list[int]]], dict[str, int]]:
    request = RefreshRequest(
        companies=tuple(str(cd_cvm) for cd_cvm, _ in companies),
        start_year=start_year,
        end_year=end_year,
        max_workers=2,
        policy=RefreshPolicy(
            skip_complete_company_years=not force_refresh,
            enable_fast_lane=False,
            force_refresh=force_refresh,
        ),
    )
    planned_companies, year_overrides, stats = service.build_company_year_plan(request)
    names_by_code = {int(cd_cvm): company_name for cd_cvm, company_name in companies}

    planned_items = []
    for company_code in planned_companies:
        code = int(company_code)
        planned_items.append(
            (
                code,
                names_by_code.get(code, str(code)),
                list(year_overrides.get(code, [])),
            )
        )
    return planned_items, stats


def run_refresh_batches(
    work_items: list[tuple[int, str, list[int]]],
    *,
    batch_size: int,
    service: HeadlessRefreshService,
    settings,
    force_refresh: bool,
) -> None:
    if not work_items:
        log.info("Nada a processar. Todas as combinacoes empresa-ano ja estao completas.")
        return

    total_batches = (len(work_items) + batch_size - 1) // batch_size
    total_company_years = sum(len(years) for _, _, years in work_items)
    log.info(
        "Iniciando refresh em massa: %s empresa(s), %s company-year(s), %s lote(s)",
        len(work_items),
        total_company_years,
        total_batches,
    )

    for batch_index in range(0, len(work_items), batch_size):
        batch_items = work_items[batch_index : batch_index + batch_size]
        batch_number = batch_index // batch_size + 1
        batch_codes = tuple(str(code) for code, _, _ in batch_items)
        batch_start_year = min(min(years) for _, _, years in batch_items)
        batch_end_year = max(max(years) for _, _, years in batch_items)
        batch_names = [name for _, name, _ in batch_items]

        log.info("Lote %s/%s: %s", batch_number, total_batches, batch_names)
        request = RefreshRequest(
            companies=batch_codes,
            start_year=batch_start_year,
            end_year=batch_end_year,
            max_workers=2,
            data_dir=str(settings.paths.input_dir),
            output_dir=str(settings.paths.reports_dir),
            policy=RefreshPolicy(
                skip_complete_company_years=not force_refresh,
                enable_fast_lane=False,
                force_refresh=force_refresh,
            ),
        )

        started_at = time.time()
        result = service.execute(request)
        elapsed_seconds = time.time() - started_at
        log.info(
            "Lote %s concluido em %.0fs: success=%s no_data=%s error=%s synced=%s planned_company_years=%s",
            batch_number,
            elapsed_seconds,
            result.success_count,
            result.no_data_count,
            result.error_count,
            result.synced_companies,
            result.planning_stats.get("planned_company_years", 0),
        )


def prefetch_yfinance(cache_path: Path) -> None:
    """Busca dados do Yahoo Finance para todos os tickers do TICKER_MAP e salva JSON."""
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance nao instalado. Pulando pre-cache de mercado.")
        return

    from src.ticker_map import TICKER_MAP

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache: dict = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    total = len(TICKER_MAP)
    log.info("Pre-cache yfinance: %s ticker(s)", total)

    for index, (cd_cvm, ticker) in enumerate(TICKER_MAP.items(), start=1):
        log.info("[%s/%s] %s (CVM %s)", index, total, ticker, cd_cvm)
        try:
            ticker_client = yf.Ticker(ticker)
            info = ticker_client.info
            history = ticker_client.history(period="1y")

            entry: dict = {
                "cd_cvm": cd_cvm,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "mktcap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "dy": info.get("dividendYield"),
                "ev": info.get("enterpriseValue"),
                "currency": info.get("currency", "BRL"),
                "fetched_at": datetime.now().isoformat(),
            }

            if not history.empty:
                history_frame = history.reset_index()[["Date", "Close", "Volume"]].copy()
                history_frame["Date"] = history_frame["Date"].dt.strftime("%Y-%m-%d")
                entry["history"] = history_frame.to_dict(orient="records")
                entry["history_len"] = len(history_frame)

            cache[ticker] = entry
        except Exception as exc:
            log.warning("yfinance falhou para %s: %s", ticker, exc)
            cache[ticker] = {
                "cd_cvm": cd_cvm,
                "error": str(exc),
                "fetched_at": datetime.now().isoformat(),
            }

    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, default=str, indent=2),
        encoding="utf-8",
    )
    log.info("Cache salvo: %s (%s ticker(s))", cache_path, len(cache))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch completo: refresh CVM em massa + cache yfinance",
        epilog=(
            "Exemplos:\n"
            "  python scripts/batch_completo.py --dry-run --max-companies 100\n"
            "  python scripts/batch_completo.py --max-companies 500 --start-year 2022 --end-year 2025\n"
            "  python scripts/batch_completo.py --yfinance-only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--max-companies",
        type=int,
        default=DEFAULT_MAX,
        help=f"Maximo de empresas ativas a processar (padrao: {DEFAULT_MAX})",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_ANOS[0],
        help=f"Ano inicial (padrao: {DEFAULT_ANOS[0]})",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=DEFAULT_ANOS[1],
        help=f"Ano final (padrao: {DEFAULT_ANOS[1]})",
    )
    parser.add_argument(
        "--anos",
        type=int,
        nargs="+",
        default=None,
        help="[LEGACY] Use --start-year e --end-year",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Empresas por lote (padrao: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o plano de refresh sem fazer requisicoes",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Compatibilidade legada. O planner atual ja retoma automaticamente.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignora company-years ja completos e reprocessa a faixa pedida",
    )
    parser.add_argument(
        "--skip-yfinance",
        action="store_true",
        help="Pula a etapa de pre-cache yfinance",
    )
    parser.add_argument(
        "--yfinance-only",
        action="store_true",
        help="Pula o refresh CVM e so atualiza o cache yfinance",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = build_settings(project_root=ROOT)

    settings.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.paths.logs_dir / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
    logging.getLogger().addHandler(file_handler)
    log.info("Log: %s", log_file)

    if args.anos:
        start_year = min(args.anos)
        end_year = max(args.anos)
        log.warning("Aviso: --anos e legado. Use --start-year e --end-year.")
    else:
        start_year = args.start_year
        end_year = args.end_year

    startup_report = collect_startup_report(
        settings,
        require_database=not args.yfinance_only,
        required_tables=("financial_reports",) if not args.yfinance_only else (),
        require_canonical_accounts=not args.yfinance_only,
    )
    if startup_report.issues:
        log.info(format_startup_report(startup_report))
        if startup_report.errors:
            raise SystemExit(1)

    log.info(
        "Configuracao: max_companies=%s, anos=%s-%s, batch_size=%s, dry_run=%s, force_refresh=%s, yfinance_only=%s",
        args.max_companies,
        start_year,
        end_year,
        args.batch_size,
        args.dry_run,
        args.force_refresh,
        args.yfinance_only,
    )
    if args.resume:
        log.info("Flag --resume recebida; o planner atual ja evita reprocessamento desnecessario.")

    started_at = time.time()
    service = HeadlessRefreshService(settings=settings)

    if not args.yfinance_only:
        companies = get_active_companies(args.max_companies, settings.company_list_timeout)
        work_items, planning_stats = build_work_plan(
            companies,
            start_year=start_year,
            end_year=end_year,
            service=service,
            force_refresh=bool(args.force_refresh),
        )

        log.info(
            "Plano consolidado: planned_companies=%s planned_company_years=%s skipped_complete=%s dropped_future_years=%s",
            planning_stats.get("planned_companies", 0),
            planning_stats.get("planned_company_years", 0),
            planning_stats.get("skipped_complete_company_years", 0),
            planning_stats.get("dropped_future_years", 0),
        )

        if args.dry_run:
            if not work_items:
                log.info("[DRY-RUN] Nenhum refresh necessario.")
            else:
                for code, company_name, years in work_items:
                    log.info("[DRY-RUN] %s (%s): anos %s", company_name, code, years)
        else:
            run_refresh_batches(
                work_items,
                batch_size=args.batch_size,
                service=service,
                settings=settings,
                force_refresh=bool(args.force_refresh),
            )

    if not args.skip_yfinance and not args.dry_run:
        prefetch_yfinance(settings.paths.yfinance_cache_path)

    elapsed_seconds = time.time() - started_at
    log.info("Batch completo em %.1f min (%.1fh)", elapsed_seconds / 60, elapsed_seconds / 3600)


if __name__ == "__main__":
    main()
