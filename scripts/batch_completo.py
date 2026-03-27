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

def run_scraper_batches(
    companies: list[tuple[int, str]],
    start_year: int,
    end_year: int,
    batch_size: int = BATCH_SIZE,
) -> None:
    """Roda o CVMScraper em lotes de batch_size."""
    from src.scraper import CVMScraper

    codes = [str(cd) for cd, _ in companies]
    total_batches = math.ceil(len(codes) / batch_size)
    log.info(f"Iniciando scraper: {len(codes)} empresas em {total_batches} lotes "
             f"({start_year}–{end_year})")

    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        nomes = [companies[j][1] for j in range(i, min(i + batch_size, len(companies)))]
        log.info(f"Lote {batch_num}/{total_batches}: {nomes}")

        t0 = time.time()
        try:
            scraper = CVMScraper()
            scraper.run(batch, start_year, end_year)
        except Exception as exc:
            log.error(f"Erro no lote {batch_num}: {exc}")
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

    from dashboard.constants import TICKER_MAP

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
        description="Batch completo: scraper CVM em massa + cache yfinance"
    )
    parser.add_argument(
        "--max", type=int, default=DEFAULT_MAX,
        help=f"Máximo de empresas a processar (padrão: {DEFAULT_MAX})",
    )
    parser.add_argument(
        "--anos", type=int, nargs="+", default=DEFAULT_ANOS,
        help=f"Range de anos (padrão: {DEFAULT_ANOS[0]} {DEFAULT_ANOS[1]})",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Empresas por lote (padrão: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Lista empresas sem fazer requisições",
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
    start_year = min(args.anos)
    end_year = max(args.anos)

    # ── Fase scraper ──────────────────────────────────────────────────────────
    if not args.yfinance_only:
        companies = get_active_companies(args.max)

        if args.dry_run:
            for cd, name in companies:
                log.info(f"  {cd:>6}  {name}")
            log.info(f"[DRY-RUN] {len(companies)} empresas seriam processadas "
                     f"({start_year}–{end_year}).")
        else:
            run_scraper_batches(companies, start_year, end_year, args.batch_size)

    # ── Fase yfinance ─────────────────────────────────────────────────────────
    if not args.skip_yfinance and not args.dry_run:
        prefetch_yfinance(CACHE_FILE)

    elapsed = time.time() - t_global
    log.info(f"Batch completo em {elapsed / 60:.1f} min ({elapsed / 3600:.1f}h)")


if __name__ == "__main__":
    main()
