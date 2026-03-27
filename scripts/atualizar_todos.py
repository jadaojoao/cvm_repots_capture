# -*- coding: utf-8 -*-
"""
Sessão 14 — Automação do scraper.
Lê todas as empresas do banco SQLite e roda o scraper para o ano atual e o anterior.
Uso:
    python scripts/atualizar_todos.py
    python scripts/atualizar_todos.py --anos 2024 2025
    python scripts/atualizar_todos.py --dry-run
"""
import sys, os, sqlite3, argparse, logging
from datetime import datetime
from pathlib import Path

# Garante UTF-8 no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Adiciona raiz do projeto ao path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
DB_PATH      = ROOT / "data" / "db" / "cvm_financials.db"
LOG_DIR      = ROOT / "logs"
BATCH_SIZE   = 10        # Empresas por lote (pausa entre lotes para não sobrecarregar CVM)
DEFAULT_ANOS = [datetime.now().year - 1, datetime.now().year]
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)


def get_all_companies() -> list[tuple[int, str]]:
    """Retorna lista de (CD_CVM, COMPANY_NAME) distintos do banco."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT CD_CVM, COMPANY_NAME FROM financial_reports ORDER BY CD_CVM"
    ).fetchall()
    conn.close()
    return rows


def run_update(anos: list[int], dry_run: bool = False) -> None:
    from src.scraper import CVMScraper

    companies = get_all_companies()
    codes     = [str(cd) for cd, _ in companies]
    log.info(f"Empresas no banco: {len(companies)}")
    log.info(f"Anos a atualizar: {anos}")
    if dry_run:
        log.info("[DRY-RUN] Nenhuma requisição será feita.")
        for cd, name in companies:
            log.info(f"  {cd:>6}  {name}")
        return

    start_year = min(anos)
    end_year   = max(anos)

    # Processar em lotes
    for i in range(0, len(codes), BATCH_SIZE):
        batch = codes[i:i + BATCH_SIZE]
        nomes = [companies[j][1] for j in range(i, min(i + BATCH_SIZE, len(companies)))]
        log.info(f"Lote {i//BATCH_SIZE + 1}: {nomes}")
        try:
            scraper = CVMScraper()
            scraper.run(batch, start_year, end_year)
        except Exception as exc:
            log.error(f"Erro no lote {i//BATCH_SIZE + 1}: {exc}")

    log.info("Atualização concluída.")


def main():
    parser = argparse.ArgumentParser(description="Atualiza dados de todas as empresas do banco CVM")
    parser.add_argument("--anos", type=int, nargs="+", default=DEFAULT_ANOS,
                        help="Anos a atualizar (padrão: ano atual e anterior)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lista empresas sem fazer requisições")
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"atualizar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s  %(message)s'))
    logging.getLogger().addHandler(fh)
    log.info(f"Log: {log_file}")

    run_update(anos=args.anos, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
