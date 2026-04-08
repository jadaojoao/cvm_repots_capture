# -*- coding: utf-8 -*-
"""
scripts/expand_tickers.py — Descobre tickers B3 para empresas sem mapeamento.

Estratégia em duas etapas:
  1. Cruzamento por CNPJ com lista pública da B3 (100% confiável)
  2. Fuzzy match por nome para empresas sem CNPJ encontrado (revisão manual)

Saídas:
  - data/metadata/ticker_candidates.csv   ← para revisão manual antes de adicionar
  - Imprime snippet Python pronto para colar em dashboard/constants.py

Uso:
    python scripts/expand_tickers.py                 # busca + valida no Yahoo Finance
    python scripts/expand_tickers.py --dry-run       # só cruza, sem chamar Yahoo Finance
    python scripts/expand_tickers.py --no-validate   # gera candidatos sem validar no YF
    python scripts/expand_tickers.py --limit 50      # testa só 50 candidatos
"""
import sys
import io
import re
import json
import argparse
import logging
import time
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

# Sufixos mais comuns de ações na B3 (em ordem de frequência)
TICKER_SUFFIXES = ["3", "4", "11", "5", "6", "31", "32", "33", "34"]


# ── Helpers de normalização ────────────────────────────────────────────────────

def _norm_name(name: str) -> str:
    """Normaliza nome para comparação fuzzy."""
    import unicodedata
    name = unicodedata.normalize("NFKD", str(name).lower())
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\b(s\.?a\.?|sa|ltda|s\/a|cia|grupo|holding|part|participações|participacoes)\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _norm_cnpj(cnpj: str) -> str:
    """Remove pontuação do CNPJ: '00.000.000/0001-00' → '00000000000100'."""
    return re.sub(r"[^\d]", "", str(cnpj or ""))


def _levenshtein_ratio(a: str, b: str) -> float:
    """Similaridade entre 0 e 1 usando distância de Levenshtein simplificada."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    max_len = max(la, lb)
    # Versão simplificada (sem matrix completa para nomes curtos)
    common = sum(ca == cb for ca, cb in zip(a, b))
    return (2.0 * common) / (la + lb)


# ── Fase 1: Baixar lista B3 ───────────────────────────────────────────────────

def fetch_b3_companies(settings) -> dict:
    """
    Baixa lista de empresas listadas na B3 via endpoint público.
    Usa cache local (b3_companies_cache.json) para evitar re-download.
    Retorna dict com duas chaves:
      - by_cvm:  {cd_cvm_int: {issuing, nome_pregao, cnpj}}  ← match direto pelo código CVM
      - by_cnpj: {cnpj_norm:  {issuing, nome_pregao}}        ← fallback por CNPJ
    """
    import requests

    # Usar cache se existir (menos de 7 dias)
    cache_path = settings.paths.metadata_dir / "b3_companies_cache.json"

    if cache_path.exists():
        age_days = (time.time() - cache_path.stat().st_mtime) / 86400
        if age_days < 7:
            log.info(f"Carregando cache B3 ({age_days:.1f} dias)...")
            with open(cache_path, encoding="utf-8") as f:
                cached = json.load(f)
            # Converter chaves inteiras (JSON serializa como strings)
            by_cvm = {int(k): v for k, v in cached.get("by_cvm", {}).items()}
            by_cnpj = cached.get("by_cnpj", {})
            log.info(f"  {len(by_cvm)} por CVM, {len(by_cnpj)} por CNPJ (cache)")
            return {"by_cvm": by_cvm, "by_cnpj": by_cnpj}

    url = ("https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/"
           "CompanyCall/GetInitialCompanies/eyJsYW5ndWFnZSI6InB0LWJyIn0=")

    log.info("Baixando lista da B3...")
    try:
        resp = requests.get(url, timeout=settings.download_timeout,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; CVM-Analytics)"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning(f"Endpoint B3 falhou ({e}): {e}")
        return {"by_cvm": {}, "by_cnpj": {}}

    by_cvm  = {}
    by_cnpj = {}
    companies = data if isinstance(data, list) else data.get("results", [])
    for item in companies:
        issuing = str(item.get("issuingCompany", "") or "").strip().upper()
        nome    = str(item.get("companyName", "") or item.get("tradingName", "") or "").strip()
        cnpj    = _norm_cnpj(item.get("cnpj", ""))
        cvm_raw = str(item.get("codeCVM", "") or "").strip()

        if not issuing:
            continue

        # Índice por código CVM (chave primária)
        if cvm_raw and cvm_raw.isdigit():
            cvm_int = int(cvm_raw)
            by_cvm[cvm_int] = {"issuing": issuing, "nome_pregao": nome, "cnpj": cnpj}

        # Índice por CNPJ (fallback)
        if cnpj and len(cnpj) >= 14:
            by_cnpj[cnpj] = {"issuing": issuing, "nome_pregao": nome}

    log.info(f"  {len(by_cvm)} entradas por CVM code, {len(by_cnpj)} por CNPJ")

    # Salvar cache
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"by_cvm": {str(k): v for k, v in by_cvm.items()},
                       "by_cnpj": by_cnpj}, f, ensure_ascii=False)
        log.info(f"  Cache salvo em {cache_path.name}")
    except Exception:
        pass

    return {"by_cvm": by_cvm, "by_cnpj": by_cnpj}


# ── Fase 2: Carregar dados locais ─────────────────────────────────────────────

def load_companies_without_ticker(settings) -> list[dict]:
    """Retorna empresas no banco sem ticker mapeado."""
    from src.db import build_engine
    from sqlalchemy import text

    engine = build_engine(settings)

    try:
        # Tentar via tabela companies
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT c.cd_cvm, c.company_name, c.nome_comercial, c.cnpj
                FROM companies c
                WHERE c.ticker_b3 IS NULL
                ORDER BY c.cd_cvm
            """)).fetchall()
            result = [{"cd_cvm": int(r[0]), "company_name": r[1],
                       "nome_comercial": r[2], "cnpj": r[3]} for r in rows]
            log.info(f"  {len(result)} empresas sem ticker (via tabela companies)")
            return result
    except Exception:
        pass

    # Fallback: via financial_reports
    from src.ticker_map import TICKER_MAP
    with engine.connect() as conn:
        rows = conn.execute(text(
            'SELECT DISTINCT "CD_CVM", "COMPANY_NAME" FROM financial_reports ORDER BY "CD_CVM"'
        )).fetchall()

    result = [{"cd_cvm": int(r[0]), "company_name": r[1], "nome_comercial": None, "cnpj": None}
              for r in rows if int(r[0]) not in TICKER_MAP]
    log.info(f"  {len(result)} empresas sem ticker (via financial_reports)")
    return result


# ── Fase 3: Cruzar e gerar candidatos ─────────────────────────────────────────

def match_by_cvm_code(companies: list[dict], b3_map: dict) -> tuple[list, list]:
    """
    Cruza por código CVM (codeCVM da B3 == cd_cvm do nosso banco).
    Retorna (candidates, unmatched).
    candidates: lista de dicts com cd_cvm + issuing_code + fonte
                (ainda sem ticker final — o suffix é determinado na validação YF)
    """
    by_cvm  = b3_map.get("by_cvm",  {})
    by_cnpj = b3_map.get("by_cnpj", {})

    candidates = []
    unmatched  = []

    for co in companies:
        cd = co["cd_cvm"]
        info = by_cvm.get(cd)

        # Fallback por CNPJ se não achou por código CVM
        if info is None:
            cnpj = _norm_cnpj(co.get("cnpj") or "")
            if cnpj:
                info = by_cnpj.get(cnpj)
                fonte = "cnpj"
            else:
                fonte = None
        else:
            fonte = "cvm_code"

        if info:
            candidates.append({
                "cd_cvm":        cd,
                "company_name":  co["company_name"],
                "issuing_code":  info["issuing"],
                "nome_pregao":   info["nome_pregao"],
                "fonte":         fonte,
                "confianca":     1.0,
            })
        else:
            unmatched.append(co)

    log.info(f"  Cruzamento CVM/CNPJ: {len(candidates)} matches, {len(unmatched)} sem match")
    return candidates, unmatched


def match_by_fuzzy(unmatched: list[dict], b3_map: dict, threshold: float = 0.75) -> list:
    """Tenta match por nome (fuzzy) para empresas sem código CVM no B3."""
    from src.ticker_map import TICKER_MAP

    by_cvm   = b3_map.get("by_cvm",  {})
    by_cnpj  = b3_map.get("by_cnpj", {})

    # Construir lista de nomes B3 normalizados
    seen_issuing = set()
    b3_entries   = []

    for info in list(by_cvm.values()) + list(by_cnpj.values()):
        issuing = info["issuing"]
        if issuing in seen_issuing:
            continue
        seen_issuing.add(issuing)
        b3_entries.append({
            "issuing":     issuing,
            "nome_norm":   _norm_name(info["nome_pregao"]),
            "nome_pregao": info["nome_pregao"],
        })

    # Issuings já mapeados (TICKER_MAP usa formato XXXX3.SA → base é XXXX)
    already_issuings = {t.replace(".SA", "").rstrip("0123456789")
                        for t in TICKER_MAP.values()}

    candidates = []
    for co in unmatched:
        nome_co = _norm_name(co.get("nome_comercial") or co["company_name"])
        best_ratio = 0.0
        best_entry = None

        for entry in b3_entries:
            if entry["issuing"] in already_issuings:
                continue
            ratio = _levenshtein_ratio(nome_co, entry["nome_norm"])
            if ratio > best_ratio:
                best_ratio = ratio
                best_entry = entry

        if best_entry and best_ratio >= threshold:
            candidates.append({
                "cd_cvm":       co["cd_cvm"],
                "company_name": co["company_name"],
                "issuing_code": best_entry["issuing"],
                "nome_pregao":  best_entry["nome_pregao"],
                "fonte":        "fuzzy",
                "confianca":    round(best_ratio, 3),
            })

    log.info(f"  Fuzzy match: {len(candidates)} candidatos (limiar={threshold})")
    return candidates


# ── Fase 4: Validar via Yahoo Finance ─────────────────────────────────────────

def _resolve_ticker(issuing: str) -> str | None:
    """
    Dado o código base (ex: 'PETR'), tenta sufixos comuns e retorna o
    primeiro ticker válido no Yahoo Finance com currency BRL e market_cap > 0.
    Retorna None se nenhum sufixo funcionar.
    """
    import yfinance as yf

    for suffix in TICKER_SUFFIXES:
        ticker = f"{issuing}{suffix}.SA"
        try:
            info = yf.Ticker(ticker).fast_info
            if (getattr(info, "currency", None) == "BRL"
                    and (getattr(info, "market_cap", 0) or 0) > 0):
                return ticker
        except Exception:
            pass
    return None


def validate_candidates(candidates: list[dict], limit: int | None = None) -> list[dict]:
    """
    Para cada candidato, resolve o melhor ticker via Yahoo Finance.
    Retorna só os validados (com campo ticker_b3 preenchido).
    """
    to_validate = candidates[:limit] if limit else candidates
    valid  = []
    total  = len(to_validate)

    for i, cand in enumerate(to_validate, 1):
        issuing = cand.get("issuing_code", "")
        name    = cand["company_name"][:30]
        log.info(f"  [{i}/{total}] Resolvendo {issuing}* ({name})...")
        t0 = time.time()
        ticker = _resolve_ticker(issuing) if issuing else None
        elapsed = time.time() - t0

        if ticker:
            log.info(f"    -> {ticker} ({elapsed:.1f}s)")
            cand = dict(cand, ticker_b3=ticker)
            valid.append(cand)
        else:
            log.info(f"    ✗ sem ticker BRL ({elapsed:.1f}s)")

        if i % 10 == 0:
            time.sleep(1)

    log.info(f"  Validação: {len(valid)}/{total} aprovados")
    return valid


# ── Fase 5: Salvar resultados ─────────────────────────────────────────────────

def save_results(settings, all_candidates: list[dict], validated: list[dict]) -> None:
    """Salva CSV de candidatos e imprime snippet Python."""
    import pandas as pd

    out_dir = settings.paths.metadata_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "ticker_candidates.csv"

    # Marcar quais foram validados
    validated_tickers = {c["ticker_b3"] for c in validated}
    for c in all_candidates:
        c.setdefault("ticker_b3", None)
        c["yf_validado"] = c["ticker_b3"] in validated_tickers

    df = pd.DataFrame(all_candidates)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    log.info(f"CSV salvo: {out_csv} ({len(df)} candidatos)")

    # Snippet Python para constants.py
    log.info("")
    log.info("=" * 70)
    log.info("Snippet para adicionar em dashboard/constants.py → TICKER_MAP:")
    log.info("=" * 70)
    log.info("    # ── Novos tickers descobertos por expand_tickers.py ────────────────")
    for c in validated:
        log.info(f"    {c['cd_cvm']:6d}: '{c['ticker_b3']}',   # {c['company_name'][:40]}")
    log.info("=" * 70)
    log.info(f"Total de novos tickers validados: {len(validated)}")
    log.info(f"Revisar manualmente em: {out_csv}")


# ── Orquestrador ──────────────────────────────────────────────────────────────

def main():
    from src.settings import build_settings
    from src.startup import collect_startup_report, format_startup_report

    parser = argparse.ArgumentParser(
        description="Descobre tickers B3 para empresas sem mapeamento"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Cruza dados sem chamar Yahoo Finance")
    parser.add_argument("--no-validate", action="store_true",
                        help="Gera candidatos sem validar no Yahoo Finance")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limitar validação a N candidatos (útil para testes)")
    parser.add_argument("--threshold", type=float, default=0.75,
                        help="Limiar de similaridade para fuzzy match (padrão: 0.75)")
    args = parser.parse_args()
    settings = build_settings(project_root=ROOT)
    startup_report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports",),
    )
    if startup_report.issues:
        log.info(format_startup_report(startup_report))
        if startup_report.errors:
            raise SystemExit(1)

    t_total = time.time()

    # Fase 1: Baixar lista B3
    b3_map = fetch_b3_companies(settings)
    if not b3_map.get("by_cvm"):
        log.error("Não foi possível baixar dados da B3. Verifique a conexão.")
        return

    # Fase 2: Empresas sem ticker
    log.info("Carregando empresas sem ticker...")
    companies = load_companies_without_ticker(settings)
    if not companies:
        log.info("Todas as empresas já têm ticker mapeado!")
        return

    # Fase 3: Cruzar
    log.info("Cruzando por código CVM / CNPJ...")
    matched_cvm, unmatched = match_by_cvm_code(companies, b3_map)

    log.info("Cruzando por nome (fuzzy)...")
    matched_fuzzy = match_by_fuzzy(unmatched, b3_map, args.threshold)

    all_candidates = matched_cvm + matched_fuzzy
    log.info(f"Total de candidatos: {len(all_candidates)} "
             f"({len(matched_cvm)} por CVM/CNPJ + {len(matched_fuzzy)} por fuzzy)")

    if args.dry_run or args.no_validate:
        # Só listar, sem validar
        import pandas as pd
        for c in all_candidates:
            c.setdefault("ticker_b3", None)
            c["yf_validado"] = None
        df = pd.DataFrame(all_candidates)
        out = settings.paths.metadata_dir / "ticker_candidates.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        log.info(f"\nSalvo em: {out}")
        log.info("Execute sem --dry-run para validar no Yahoo Finance.")
        return

    # Fase 4: Validar
    log.info("Validando no Yahoo Finance (pode demorar)...")
    validated = validate_candidates(all_candidates, args.limit)

    # Fase 5: Salvar
    save_results(settings, all_candidates, validated)

    elapsed = time.time() - t_total
    log.info(f"\nConcluído em {elapsed:.1f}s")


if __name__ == "__main__":
    main()
