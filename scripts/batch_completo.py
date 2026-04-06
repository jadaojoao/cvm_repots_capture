# -*- coding: utf-8 -*-
"""
Sessão 20 — Batch completo: scraper em massa + cache yfinance.

Baixa dados da CVM para até N empresas ativas e pré-busca dados do Yahoo Finance.

Uso:
    python scripts/batch_completo.py                          # 150 empresas, 2022-2025
    python scripts/batch_completo.py --max 200                # 200 empresas
    python scripts/batch_completo.py --max 5 --anos 2024 2025 # teste rápido
    python scripts/batch_completo.py --dry-run                # lista sem baixar
    python scripts/batch_completo.py --skip-yfinance          # pula cache YF
    python scripts/batch_completo.py --yfinance-only          # só atualiza cache YF
"""
import sys
import os
import argparse
import io
import json
import logging
import math
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Garante UTF-8 no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
LOG_DIR       = ROOT / "logs"
CACHE_DIR     = ROOT / "data" / "cache"
CACHE_FILE    = CACHE_DIR / "yfinance_cache.json"
BATCH_SIZE    = 10
DEFAULT_MAX   = 150
DEFAULT_ANOS  = [2022, datetime.now().year]
CVM_MASTER_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)


# ── Fase 1: Lista de empresas ativas da CVM ──────────────────────────────────

def get_active_companies(max_n: int) -> list[tuple[int, str]]:
    """Baixa o cadastro completo da CVM, filtra empresas ativas e retorna até max_n."""
    log.info(f"Baixando lista de empresas da CVM ({CVM_MASTER_URL})...")
    resp = requests.get(CVM_MASTER_URL, timeout=30)
    resp.raise_for_status()

    df = pd.read_csv(io.BytesIO(resp.content), sep=";", encoding="latin1")
    active = df[df['SIT'] == 'ATIVO'].copy()
    active = active.dropna(subset=['CD_CVM'])
    active['CD_CVM'] = active['CD_CVM'].astype(int)

    # Nome: preferir nome comercial, fallback para razão social
    active['NAME'] = active['DENOM_COMERC'].fillna('').str.strip()
    mask = active['NAME'] == ''
    active.loc[mask, 'NAME'] = active.loc[mask, 'DENOM_SOCIAL'].fillna('').str.strip()

    # Deduplicar por CD_CVM
    active = active.drop_duplicates(subset='CD_CVM')

    result = list(zip(active['CD_CVM'].tolist(), active['NAME'].tolist()))
    log.info(f"Empresas ativas na CVM: {len(result)} — usando até {max_n}")
    return result[:max_n]


# ── Fase 2: Scraper em lotes ─────────────────────────────────────────────────

# ── Fase 1.5: Detectar progresso anterior ────────────────────────────────────

def get_processed_years(cd_cvm: int) -> set[int]:
    """Retorna conjunto de anos já processados para uma empresa no DB."""
    try:
        from src.db import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT DISTINCT REPORT_YEAR FROM financial_reports WHERE CD_CVM = :cd "
                     "ORDER BY REPORT_YEAR"),
                {"cd": cd_cvm}
            ).fetchall()
        return set(int(r[0]) for r in rows if r[0])
    except Exception as e:
        log.warning(f"Erro ao detectar progresso para CVM {cd_cvm}: {e}")
        return set()


def filter_remaining_work(
    companies: list[tuple[int, str]],
    start_year: int,
    end_year: int,
    dry_run: bool = False,
) -> list[tuple[int, str, list[int]]]:
    """
    Filtra quais (empresa, ano) precisam ser processados.
    Retorna lista de (cd_cvm, nome, years_faltando).
    """
    result = []
    total_skips = 0
    total_news = 0

    for cd_cvm, name in companies:
        processed = get_processed_years(cd_cvm)
        years_needed = [y for y in range(start_year, end_year + 1) if y not in processed]

        if not years_needed:
            log.debug(f"✓ {name:30s} (CVM {cd_cvm:6d}) — todos os anos {start_year}–{end_year} já processados")
            total_skips += 1
        else:
            status = "↓" if not dry_run else "📋"
            log.info(f"{status} {name:30s} (CVM {cd_cvm:6d}) — faltam anos: {years_needed}")
            result.append((cd_cvm, name, years_needed))
            total_news += len(years_needed)

    if not dry_run:
        log.info(f"Resumo: {len(result)} empresa(s) com dados faltando ({total_news} ano/empresa)")
    else:
        log.info(f"[DRY-RUN] {len(result)} empresa(s) com {total_news} ano(s) faltando; "
                 f"{total_skips} empresa(s) completas")

    return result


# ── Fase 2: Scraper em lotes ─────────────────────────────────────────────────

def run_scraper_batches(
    work_items: list[tuple[int, str, list[int]]],
    batch_size: int = BATCH_SIZE,
) -> None:
    """Roda o CVMScraper em lotes, processando anos específicos por empresa."""
    from src.scraper import CVMScraper

    if not work_items:
        log.info("Nada a processar. Todas as combinações (empresa, ano) já existem no DB.")
        return

    total_work = sum(len(years) for _, _, years in work_items)
    total_batches = math.ceil(len(work_items) / batch_size)
    log.info(f"Iniciando scraper: {len(work_items)} empresa(s), {total_work} ano(s) em {total_batches} lote(s)")

    for batch_idx in range(0, len(work_items), batch_size):
        batch_items = work_items[batch_idx : batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1

        batch_nomes = [name for _, name, _ in batch_items]
        log.info(f"Lote {batch_num}/{total_batches}: {batch_nomes}")

        t0 = time.time()
        for cd_cvm, name, years in batch_items:
            try:
                scraper = CVMScraper()
                start = min(years)
                end = max(years)
                log.info(f"  → {name} (CVM {cd_cvm}): {start}–{end}")
                scraper.run([str(cd_cvm)], start, end)
            except Exception as exc:
                log.error(f"  ✗ {name} (CVM {cd_cvm}): {exc}")

        elapsed = time.time() - t0
        log.info(f"Lote {batch_num} concluído em {elapsed:.0f}s")


# ── Fase 3: Pré-cache yfinance ───────────────────────────────────────────────

def prefetch_yfinance(cache_path: Path) -> None:
    """Busca dados do Yahoo Finance para todos os tickers do TICKER_MAP e salva JSON."""
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance não instalado. Pulando pré-cache de mercado.")
        return

    from src.ticker_map import TICKER_MAP

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Carregar cache existente (se houver)
    cache: dict = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding='utf-8'))
        except Exception:
            cache = {}

    total = len(TICKER_MAP)
    log.info(f"Pré-cache yfinance: {total} tickers")

    for idx, (cd_cvm, ticker) in enumerate(TICKER_MAP.items(), 1):
        log.info(f"[{idx}/{total}] {ticker} (CVM {cd_cvm})")
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            hist = tk.history(period="1y")

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

            # Histórico de preço (1 ano)
            if not hist.empty:
                h = hist.reset_index()[['Date', 'Close', 'Volume']].copy()
                h['Date'] = h['Date'].dt.strftime('%Y-%m-%d')
                entry["history"] = h.to_dict(orient='records')
                entry["history_len"] = len(h)

            cache[ticker] = entry

        except Exception as exc:
            log.warning(f"yfinance falhou para {ticker}: {exc}")
            cache[ticker] = {
                "cd_cvm": cd_cvm,
                "error": str(exc),
                "fetched_at": datetime.now().isoformat(),
            }

    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, default=str, indent=2),
        encoding='utf-8',
    )
    log.info(f"Cache salvo: {cache_path} ({len(cache)} tickers)")


# ── Orquestrador ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch completo: scraper CVM em massa + cache yfinance",
        epilog="Exemplos:\n"
               "  python scripts/batch_completo.py --dry-run --max-companies 100\n"
               "  python scripts/batch_completo.py --max-companies 500 --start-year 2022 --end-year 2025\n"
               "  python scripts/batch_completo.py --max-companies 300 --start-year 2020 --end-year 2025 --resume\n"
               "  python scripts/batch_completo.py --yfinance-only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--max-companies", type=int, default=DEFAULT_MAX,
        help=f"Máximo de empresas ativas a processar (padrão: {DEFAULT_MAX})",
    )
    parser.add_argument(
        "--start-year", type=int, default=DEFAULT_ANOS[0],
        help=f"Ano inicial (padrão: {DEFAULT_ANOS[0]})",
    )
    parser.add_argument(
        "--end-year", type=int, default=DEFAULT_ANOS[1],
        help=f"Ano final (padrão: {DEFAULT_ANOS[1]})",
    )
    # Manter --anos para compatibilidade
    parser.add_argument(
        "--anos", type=int, nargs="+", default=None,
        help="[DEPRECATED] Use --start-year e --end-year",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Empresas por lote (padrão: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra o que seria feito, sem fazer requisições",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Retoma de onde parou (útil se houve falha)",
    )
    parser.add_argument(
        "--skip-yfinance", action="store_true",
        help="Pula a etapa de pré-cache yfinance",
    )
    parser.add_argument(
        "--yfinance-only", action="store_true",
        help="Pula o scraper, só atualiza o cache yfinance",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Logging em arquivo
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s  %(message)s'))
    logging.getLogger().addHandler(fh)
    log.info(f"Log: {log_file}")

    t_global = time.time()

    # Resolver anos (--anos é legacy, usar --start-year/--end-year)
    if args.anos:
        start_year = min(args.anos)
        end_year = max(args.anos)
        log.warning("Aviso: --anos é legacy. Use --start-year e --end-year.")
    else:
        start_year = args.start_year
        end_year = args.end_year

    log.info(f"Configuração: max_companies={args.max_companies}, "
             f"anos={start_year}–{end_year}, batch_size={args.batch_size}, "
             f"dry_run={args.dry_run}, resume={args.resume}")

    # ── Fase scraper ──────────────────────────────────────────────────────────
    if not args.yfinance_only:
        companies = get_active_companies(args.max_companies)

        # Detectar progresso anterior
        work_items = filter_remaining_work(companies, start_year, end_year, args.dry_run)

        if args.dry_run:
            log.info("")
            log.info("=" * 80)
            log.info("[DRY-RUN] O que seria processado:")
            log.info("=" * 80)
            for cd_cvm, name, years in work_items:
                log.info(f"  ↓ {name:30s} (CVM {cd_cvm:6d}): anos {years}")
            log.info("=" * 80)
        else:
            if work_items:
                run_scraper_batches(work_items, args.batch_size)
            else:
                log.info("Nenhum trabalho a fazer. Todas as combinações (empresa, ano) já estão no DB.")

    # ── Fase yfinance ─────────────────────────────────────────────────────────
    if not args.skip_yfinance and not args.dry_run:
        prefetch_yfinance(CACHE_FILE)

    elapsed = time.time() - t_global
    log.info("")
    log.info(f"Batch completo em {elapsed / 60:.1f} min ({elapsed / 3600:.1f}h)")


if __name__ == "__main__":
    main()
