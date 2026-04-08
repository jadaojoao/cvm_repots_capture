"""
Business logic for the CVM Analytics desktop app.

Extracted from cvm_pyqt_app.py — no PyQt6 dependencies.
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

from src.ticker_map import TICKER_MAP
from src.settings import AppSettings, build_settings


@dataclass
class RankedCompany:
    cd_cvm: int
    company_name: str
    ticker: str | None
    last_report_year: int | None
    last_file_update: datetime | None
    last_update_ref: datetime | None
    mktcap: float
    avg_volume: float
    importance_score: float
    staleness_score: float
    total_score: float
    year_gap: int
    days_since_update: float | None
    is_recently_updated: bool
    is_recent_no_data: bool
    has_source_presence: bool
    source_presence_years_count: int
    only_end_year_history: bool

    def to_row(self) -> dict[str, Any]:
        return {
            "cd_cvm": self.cd_cvm,
            "company_name": self.company_name,
            "ticker": self.ticker or "N/D",
            "score": self.total_score,
            "importance_score": self.importance_score,
            "staleness_score": self.staleness_score,
            "year_gap": self.year_gap,
            "last_update": self.last_update_ref.strftime("%Y-%m-%d %H:%M") if self.last_update_ref else "N/D",
            "mktcap_bi": self.mktcap / 1_000_000_000 if self.mktcap > 0 else 0.0,
            "liq_milhoes": self.avg_volume / 1_000_000 if self.avg_volume > 0 else 0.0,
            "recent_update": "Sim" if self.is_recently_updated else "Nao",
            "recent_no_data": "Sim" if self.is_recent_no_data else "Nao",
            "has_source_presence": "Sim" if self.has_source_presence else "Nao",
            "source_presence_years_count": self.source_presence_years_count,
            "days_since_update": self.days_since_update,
            "coverage": "So ano final" if self.only_end_year_history else "Multi-ano",
            "only_end_year_history": self.only_end_year_history,
        }


def _safe_name(company_name: str) -> str:
    return company_name.replace(" ", "_").replace("/", "_").replace("\\", "_")


def _minmax_normalize(value: float | None, values: list[float]) -> float:
    if value is None or value <= 0:
        return 0.0
    valid = [v for v in values if v > 0]
    if not valid:
        return 0.0
    v_min = min(valid)
    v_max = max(valid)
    if v_max == v_min:
        return 1.0
    return (value - v_min) / (v_max - v_min)


class IntelligentSelectorService:
    CACHE_TTL_DAYS = 7
    MAX_ONLINE_FETCH = 60
    IMPORTANCE_WEIGHT = 0.70
    STALENESS_WEIGHT = 0.30
    MKT_CAP_WEIGHT = 0.40
    LIQUIDITY_WEIGHT = 0.60
    STALENESS_YEAR_WEIGHT = 0.70
    STALENESS_RECENCY_WEIGHT = 0.30
    RECENT_UPDATE_COOLDOWN_HOURS = 24
    REQUIRED_PACKAGE_STATEMENTS = ("BPA", "BPP", "DRE", "DFC")
    BASE_HEALTH_CACHE_TTL_SECONDS = 300
    ACTIVE_UNIVERSE_CACHE_TTL_HOURS = 24
    ETA_MIN_SUCCESS_SAMPLES = 3
    ETA_WINDOW_HOURS = 24
    HEALTH_STATUS_CRITICAL_THRESHOLD = 70.0
    HEALTH_STATUS_OK_THRESHOLD = 90.0
    PRIORITY_LIST_LIMIT = 15
    NO_DATA_COOLDOWN_DAYS = 7

    def __init__(self, project_root: Path | None = None, settings: AppSettings | None = None):
        self.settings = settings or build_settings(project_root=project_root)
        self.project_root = self.settings.paths.project_root
        self.db_path = self.settings.paths.db_path
        self.cache_path = self.settings.paths.yfinance_cache_path
        self.reports_dir = self.settings.paths.reports_dir
        self.base_health_cache_path = self.settings.paths.base_health_snapshot_path
        self.active_universe_cache_path = self.settings.paths.active_universe_cache_path
        self.processed_presence_cache_path = self.settings.paths.processed_presence_index_path
        self.processed_dir = self.settings.paths.processed_dir

    def _load_market_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _health_status_from_score(score: float) -> str:
        if score < IntelligentSelectorService.HEALTH_STATUS_CRITICAL_THRESHOLD:
            return "critico"
        if score < IntelligentSelectorService.HEALTH_STATUS_OK_THRESHOLD:
            return "atencao"
        return "ok"

    @staticmethod
    def _risk_level(missing_years_count: int, gap_to_leader_years: int) -> str:
        if int(missing_years_count) >= 2 or int(gap_to_leader_years) >= 2:
            return "alto"
        if int(missing_years_count) >= 1 or int(gap_to_leader_years) >= 1:
            return "medio"
        return "baixo"

    @staticmethod
    def _priority_action(years_missing: list[int]) -> str:
        if not years_missing:
            return "Sem acao pendente"
        sorted_years = sorted(int(y) for y in years_missing)
        if len(sorted_years) == 1:
            return f"Atualizar ano {sorted_years[0]}"
        return f"Atualizar anos {sorted_years[0]}-{sorted_years[-1]}"

    def _save_market_cache(self, cache: dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(cache, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _load_db_company_rows(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []

        query = """
            SELECT
                CD_CVM AS cd_cvm,
                COMPANY_NAME AS company_name,
                COUNT(DISTINCT CASE WHEN REPORT_YEAR IS NOT NULL THEN REPORT_YEAR END) AS report_years_count,
                MIN(REPORT_YEAR) AS min_report_year,
                MAX(REPORT_YEAR) AS last_report_year
            FROM financial_reports
            WHERE CD_CVM IS NOT NULL
              AND COMPANY_NAME IS NOT NULL
            GROUP BY CD_CVM, COMPANY_NAME
            ORDER BY COMPANY_NAME
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]

    def _find_last_file_update(self, company_name: str) -> datetime | None:
        safe = _safe_name(company_name)
        if not self.reports_dir.exists():
            return None
        files = list(self.reports_dir.glob(f"{safe}_financials*.xlsx"))
        if not files:
            return None
        latest = max(files, key=lambda p: p.stat().st_mtime)
        return datetime.fromtimestamp(latest.stat().st_mtime)

    @staticmethod
    def _parse_fetched_at(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    @staticmethod
    def _extract_avg_volume_from_history(history: Any) -> float | None:
        if not isinstance(history, list) or not history:
            return None
        vols: list[float] = []
        for item in history[-20:]:
            try:
                vol = float(item.get("Volume", 0))
            except Exception:
                vol = 0
            if vol > 0:
                vols.append(vol)
        if not vols:
            return None
        return sum(vols) / len(vols)

    def _snapshot_from_cache(self, ticker: str, cache: dict[str, Any]) -> dict[str, Any] | None:
        entry = cache.get(ticker)
        if not isinstance(entry, dict):
            return None

        mktcap = entry.get("mktcap")
        avg_volume = entry.get("avg_volume")
        if avg_volume is None:
            avg_volume = self._extract_avg_volume_from_history(entry.get("history"))

        try:
            mktcap = float(mktcap) if mktcap is not None else 0.0
        except Exception:
            mktcap = 0.0
        try:
            avg_volume = float(avg_volume) if avg_volume is not None else 0.0
        except Exception:
            avg_volume = 0.0

        return {
            "mktcap": mktcap,
            "avg_volume": avg_volume,
            "fetched_at": entry.get("fetched_at"),
        }

    @staticmethod
    def _is_snapshot_stale(snapshot: dict[str, Any] | None, ttl_days: int) -> bool:
        if not snapshot:
            return True
        dt = IntelligentSelectorService._parse_fetched_at(snapshot.get("fetched_at"))
        if dt is None:
            return True
        return dt < datetime.now() - timedelta(days=ttl_days)

    def _fetch_online_snapshot(self, ticker: str) -> dict[str, Any] | None:
        if not _YF_AVAILABLE:
            return None
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info or {}
            mktcap = info.get("marketCap") or 0.0
            hist = ticker_obj.history(period="3mo")
            avg_volume = 0.0
            if hist is not None and not hist.empty and "Volume" in hist.columns:
                series = hist["Volume"].tail(20).dropna()
                if not series.empty:
                    avg_volume = float(series.mean())

            return {
                "mktcap": float(mktcap) if mktcap else 0.0,
                "avg_volume": float(avg_volume) if avg_volume else 0.0,
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception:
            return None

    def _load_market_snapshot(self, ticker: str | None, cache: dict[str, Any], fetch_budget: dict[str, int]) -> dict[str, Any]:
        if not ticker:
            return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

        cached = self._snapshot_from_cache(ticker, cache)
        if cached and not self._is_snapshot_stale(cached, self.CACHE_TTL_DAYS):
            return cached

        if fetch_budget["remaining"] > 0:
            online = self._fetch_online_snapshot(ticker)
            if online:
                fetch_budget["remaining"] -= 1
                prev = cache.get(ticker, {})
                if isinstance(prev, dict):
                    prev.update(online)
                    cache[ticker] = prev
                else:
                    cache[ticker] = online
                return online

        if cached:
            return cached
        return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

    def _load_refresh_status_map(self) -> dict[int, dict[str, Any]]:
        if not self.db_path.exists():
            return {}
        query = """
            SELECT
                cd_cvm,
                company_name,
                last_attempt_at,
                last_success_at,
                last_status,
                last_error,
                last_rows_inserted
            FROM company_refresh_status
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query).fetchall()
        except Exception:
            return {}

        out: dict[int, dict[str, Any]] = {}
        for row in rows:
            try:
                cd_cvm = int(row["cd_cvm"])
            except Exception:
                continue
            out[cd_cvm] = dict(row)
        return out

    @staticmethod
    def _read_cached_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_cached_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _latest_refresh_success_marker(self) -> str:
        if not self.db_path.exists():
            return ""
        query = """
            SELECT MAX(last_success_at) AS last_success_at
            FROM company_refresh_status
            WHERE last_success_at IS NOT NULL
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                row = conn.execute(query).fetchone()
            if not row:
                return ""
            marker = row[0]
            return str(marker or "")
        except Exception:
            return ""

    def _processed_files_signature(self, start_year: int, end_year: int) -> dict[str, Any]:
        if not self.processed_dir.exists():
            return {"count": 0, "latest_mtime": 0.0}

        latest_mtime = 0.0
        count = 0
        for csv_path in self.processed_dir.glob("*.csv"):
            name = csv_path.name.upper()
            if "_CIA_ABERTA_" not in name:
                continue
            parts = csv_path.stem.split("_")
            try:
                year = int(parts[-1])
            except Exception:
                continue
            if year < int(start_year) or year > int(end_year):
                continue
            if not any(stmt in name for stmt in ("BPA", "BPP", "DRE", "DFC_MD", "DFC_MI")):
                continue
            count += 1
            latest_mtime = max(latest_mtime, csv_path.stat().st_mtime)
        return {"count": int(count), "latest_mtime": float(latest_mtime)}

    def _load_active_universe(self) -> list[dict[str, Any]]:
        now = datetime.now()
        cached = self._read_cached_json(self.active_universe_cache_path)
        if isinstance(cached, dict):
            generated_at = self._parse_fetched_at(str(cached.get("generated_at") or ""))
            rows = cached.get("rows")
            if (
                generated_at is not None
                and isinstance(rows, list)
                and generated_at >= now - timedelta(hours=self.ACTIVE_UNIVERSE_CACHE_TTL_HOURS)
            ):
                return rows

        url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
        rows: list[dict[str, Any]] = []
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.read_csv(
                io.BytesIO(resp.content),
                sep=";",
                encoding="latin1",
                usecols=["CD_CVM", "DENOM_SOCIAL", "DENOM_COMERC", "SIT"],
            )
            df["CD_CVM"] = pd.to_numeric(df["CD_CVM"], errors="coerce")
            df = df.dropna(subset=["CD_CVM"]).copy()
            active_df = df[df["SIT"].astype(str).str.contains("ATIV", case=False, na=False)].copy()
            if active_df.empty:
                active_df = df.copy()

            dedupe: dict[int, str] = {}
            for _, item in active_df.iterrows():
                cd = int(item["CD_CVM"])
                display = str(item.get("DENOM_COMERC") or "").strip()
                if not display:
                    display = str(item.get("DENOM_SOCIAL") or "").strip()
                if not display:
                    display = f"CVM {cd}"
                dedupe[cd] = display
            rows = [
                {"cd_cvm": int(cd), "company_name": str(name)}
                for cd, name in sorted(dedupe.items(), key=lambda x: x[1].upper())
            ]
            self._write_cached_json(
                self.active_universe_cache_path,
                {
                    "generated_at": now.replace(microsecond=0).isoformat(),
                    "rows": rows,
                },
            )
            return rows
        except Exception:
            fallback_rows = self._load_db_company_rows()
            dedupe = {}
            for row in fallback_rows:
                try:
                    dedupe[int(row["cd_cvm"])] = str(row["company_name"])
                except Exception:
                    continue
            return [
                {"cd_cvm": int(cd), "company_name": str(name)}
                for cd, name in sorted(dedupe.items(), key=lambda x: x[1].upper())
            ]

    def _load_statement_presence(self, start_year: int, end_year: int) -> dict[tuple[int, int], set[str]]:
        if not self.db_path.exists():
            return {}

        placeholders = ",".join("?" for _ in self.REQUIRED_PACKAGE_STATEMENTS)
        query = f"""
            SELECT
                "CD_CVM" AS cd_cvm,
                "REPORT_YEAR" AS report_year,
                "STATEMENT_TYPE" AS statement_type
            FROM financial_reports
            WHERE "CD_CVM" IS NOT NULL
              AND "REPORT_YEAR" BETWEEN ? AND ?
              AND "STATEMENT_TYPE" IN ({placeholders})
            GROUP BY "CD_CVM", "REPORT_YEAR", "STATEMENT_TYPE"
        """
        params = [int(start_year), int(end_year), *self.REQUIRED_PACKAGE_STATEMENTS]
        presence: dict[tuple[int, int], set[str]] = defaultdict(set)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        for row in rows:
            try:
                key = (int(row["cd_cvm"]), int(row["report_year"]))
                stmt = str(row["statement_type"])
            except Exception:
                continue
            presence[key].add(stmt)
        return dict(presence)

    def _load_local_year_span(self) -> dict[int, tuple[int | None, int | None]]:
        if not self.db_path.exists():
            return {}
        query = """
            SELECT
                "CD_CVM" AS cd_cvm,
                MIN("REPORT_YEAR") AS min_year,
                MAX("REPORT_YEAR") AS max_year
            FROM financial_reports
            WHERE "CD_CVM" IS NOT NULL
              AND "REPORT_YEAR" IS NOT NULL
            GROUP BY "CD_CVM"
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
        spans: dict[int, tuple[int | None, int | None]] = {}
        for row in rows:
            try:
                cd = int(row["cd_cvm"])
            except Exception:
                continue
            min_year = int(row["min_year"]) if row["min_year"] is not None else None
            max_year = int(row["max_year"]) if row["max_year"] is not None else None
            spans[cd] = (min_year, max_year)
        return spans

    def _scan_processed_statement_presence(
        self,
        start_year: int,
        end_year: int,
    ) -> dict[tuple[int, int], set[str]]:
        if not self.processed_dir.exists():
            return {}

        canonical_by_token = {
            "BPA": "BPA",
            "BPP": "BPP",
            "DRE": "DRE",
            "DFC_MD": "DFC",
            "DFC_MI": "DFC",
        }
        presence: dict[tuple[int, int], set[str]] = defaultdict(set)

        cached_index = self._read_cached_json(self.processed_presence_cache_path)
        cached_files = cached_index.get("files", {}) if isinstance(cached_index, dict) else {}
        cached_files = cached_files if isinstance(cached_files, dict) else {}

        updated_files: dict[str, Any] = {}
        cache_dirty = False

        for csv_path in self.processed_dir.glob("*.csv"):
            stem = csv_path.stem
            parts = stem.split("_")
            if len(parts) < 6:
                continue

            stem_upper = stem.upper()
            token = ""
            if "_DFC_MD_" in stem_upper:
                token = "DFC_MD"
            elif "_DFC_MI_" in stem_upper:
                token = "DFC_MI"
            elif "_BPA_" in stem_upper:
                token = "BPA"
            elif "_BPP_" in stem_upper:
                token = "BPP"
            elif "_DRE_" in stem_upper:
                token = "DRE"

            canonical_stmt = canonical_by_token.get(token)
            if canonical_stmt is None:
                continue

            try:
                year = int(parts[-1])
            except Exception:
                continue

            try:
                stat = csv_path.stat()
                signature = {
                    "mtime": float(stat.st_mtime),
                    "size": int(stat.st_size),
                }
            except Exception:
                continue

            file_key = csv_path.name
            cached_entry = cached_files.get(file_key) if isinstance(cached_files, dict) else None
            cached_sig = cached_entry.get("signature") if isinstance(cached_entry, dict) else None
            cached_stmt = cached_entry.get("statement") if isinstance(cached_entry, dict) else None
            cached_year = cached_entry.get("year") if isinstance(cached_entry, dict) else None
            cached_codes = cached_entry.get("codes") if isinstance(cached_entry, dict) else None

            try:
                cached_year_int = int(cached_year)
            except Exception:
                cached_year_int = None

            use_cached_codes = (
                isinstance(cached_entry, dict)
                and isinstance(cached_sig, dict)
                and cached_sig == signature
                and str(cached_stmt or "") == canonical_stmt
                and cached_year_int == int(year)
                and isinstance(cached_codes, list)
            )

            codes: list[int] = []
            if use_cached_codes:
                try:
                    codes = sorted({int(v) for v in cached_codes})
                except Exception:
                    codes = []
            else:
                try:
                    df_codes = pd.read_csv(
                        csv_path,
                        sep=";",
                        encoding="latin1",
                        usecols=["CD_CVM"],
                        low_memory=False,
                    )
                    codes = sorted(
                        {
                            int(v)
                            for v in pd.to_numeric(df_codes["CD_CVM"], errors="coerce").dropna().tolist()
                        }
                    )
                except Exception:
                    codes = []
                cache_dirty = True

            updated_files[file_key] = {
                "signature": signature,
                "statement": canonical_stmt,
                "year": int(year),
                "codes": codes,
            }

            if int(start_year) <= int(year) <= int(end_year):
                for cd in codes:
                    presence[(int(cd), int(year))].add(canonical_stmt)

        if set(updated_files.keys()) != set(cached_files.keys()):
            cache_dirty = True

        if cache_dirty:
            self._write_cached_json(
                self.processed_presence_cache_path,
                {
                    "generated_at": datetime.now().replace(microsecond=0).isoformat(),
                    "files": updated_files,
                },
            )

        return dict(presence)

    def _estimate_throughput_per_hour(self) -> dict[str, Any]:
        if not self.db_path.exists():
            return {"per_hour": None, "sample_size": 0, "confidence": "low"}
        query = """
            SELECT last_success_at
            FROM company_refresh_status
            WHERE last_status = 'success'
              AND last_success_at IS NOT NULL
            ORDER BY last_success_at DESC
            LIMIT 200
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                rows = conn.execute(query).fetchall()
        except Exception:
            return {"per_hour": None, "sample_size": 0, "confidence": "low"}

        parsed = []
        for row in rows:
            dt = self._parse_fetched_at(str(row[0] or ""))
            if dt is not None:
                parsed.append(dt)
        if not parsed:
            return {"per_hour": None, "sample_size": 0, "confidence": "low"}

        now = datetime.now()
        cut = now - timedelta(hours=self.ETA_WINDOW_HOURS)
        recent = sorted(dt for dt in parsed if dt >= cut)
        if len(recent) < self.ETA_MIN_SUCCESS_SAMPLES:
            return {
                "per_hour": None,
                "sample_size": len(recent),
                "confidence": "low",
            }

        span_hours = (recent[-1] - recent[0]).total_seconds() / 3600.0
        if span_hours <= 0:
            return {
                "per_hour": None,
                "sample_size": len(recent),
                "confidence": "low",
            }

        per_hour = max(0.0, (len(recent) - 1) / span_hours)
        if per_hour <= 0:
            return {
                "per_hour": None,
                "sample_size": len(recent),
                "confidence": "low",
            }

        confidence = "medium"
        if len(recent) >= 12 and span_hours >= 6:
            confidence = "high"
        return {
            "per_hour": float(per_hour),
            "sample_size": len(recent),
            "confidence": confidence,
        }

    def build_base_health_snapshot(
        self,
        start_year: int,
        end_year: int,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        start = int(start_year)
        end = int(end_year)
        if start > end:
            raise ValueError("start_year must be <= end_year")

        now = datetime.now()
        years = list(range(start, end + 1))
        processed_signature = self._processed_files_signature(start, end)
        last_success_marker = self._latest_refresh_success_marker()

        cached = self._read_cached_json(self.base_health_cache_path)
        previous_snapshot = cached if isinstance(cached, dict) else None
        if isinstance(cached, dict) and not force_refresh:
            generated_at = self._parse_fetched_at(str(cached.get("generated_at") or ""))
            is_fresh = (
                generated_at is not None
                and generated_at >= now - timedelta(seconds=self.BASE_HEALTH_CACHE_TTL_SECONDS)
            )
            try:
                cached_start = int(cached.get("start_year", -1))
                cached_end = int(cached.get("end_year", -1))
            except Exception:
                cached_start = -1
                cached_end = -1
            if (
                is_fresh
                and cached_start == start
                and cached_end == end
                and cached.get("processed_signature") == processed_signature
                and str(cached.get("last_success_marker") or "") == last_success_marker
            ):
                return cached

        active_universe = self._load_active_universe()
        statement_presence = self._load_statement_presence(start, end)
        raw_presence = self._scan_processed_statement_presence(start, end)
        local_spans = self._load_local_year_span()
        required = set(self.REQUIRED_PACKAGE_STATEMENTS)

        combined_presence: dict[tuple[int, int], set[str]] = defaultdict(set)
        for key, values in statement_presence.items():
            combined_presence[key].update(values)
        for key, values in raw_presence.items():
            combined_presence[key].update(values)

        total_companies = len(active_universe)
        per_year_buckets = {
            int(year): {
                "year": int(year),
                "total_companies": int(total_companies),
                "completed": 0,
                "missing": 0,
            }
            for year in years
        }

        # Pre-index raw_presence by cd_cvm to avoid O(n×m) scan inside the loop.
        raw_years_by_cd: dict[int, list[int]] = defaultdict(list)
        for (raw_cd, raw_year), raw_stmts in raw_presence.items():
            if raw_stmts:
                raw_years_by_cd[int(raw_cd)].append(int(raw_year))

        companies: list[dict[str, Any]] = []
        leader_completed = 0
        for item in active_universe:
            cd = int(item["cd_cvm"])
            company_name = str(item["company_name"])
            complete_years: list[int] = []
            missing_years: list[int] = []

            for year in years:
                stmts = combined_presence.get((cd, int(year)), set())
                if required.issubset(stmts):
                    complete_years.append(int(year))
                    per_year_buckets[int(year)]["completed"] += 1
                else:
                    missing_years.append(int(year))

            completed_count = len(complete_years)
            leader_completed = max(leader_completed, completed_count)

            local_min, local_max = local_spans.get(cd, (None, None))
            raw_years = raw_years_by_cd.get(cd, [])
            raw_max = max(raw_years) if raw_years else None
            est_history_end = max([v for v in (local_max, raw_max) if v is not None], default=None)
            max_completed_year = max(complete_years) if complete_years else None

            companies.append(
                {
                    "cd_cvm": cd,
                    "company_name": company_name,
                    "history_start_local": local_min,
                    "history_end_local": local_max,
                    "estimated_history_end": est_history_end,
                    "years_completed": complete_years,
                    "years_missing": missing_years,
                    "completed_years_count": completed_count,
                    "missing_years_count": len(missing_years),
                    "max_completed_year": max_completed_year,
                }
            )

        for year in years:
            per_year_buckets[int(year)]["missing"] = (
                per_year_buckets[int(year)]["total_companies"] - per_year_buckets[int(year)]["completed"]
            )

        lagging_rows: list[dict[str, Any]] = []
        for row in companies:
            own_ceiling = row.get("estimated_history_end")
            max_completed = row.get("max_completed_year")
            if own_ceiling is None or int(own_ceiling) < start:
                gap_to_own_ceiling = 0
            else:
                ceiling_in_scope = min(end, int(own_ceiling))
                if max_completed is None:
                    gap_to_own_ceiling = max(0, ceiling_in_scope - start + 1)
                else:
                    gap_to_own_ceiling = max(0, ceiling_in_scope - int(max_completed))

            gap_to_leader = max(0, leader_completed - int(row["completed_years_count"]))
            row["gap_to_leader_years"] = int(gap_to_leader)
            row["gap_to_own_ceiling_years"] = int(gap_to_own_ceiling)

            lagging_rows.append(
                {
                    "cd_cvm": int(row["cd_cvm"]),
                    "company_name": str(row["company_name"]),
                    "missing_years_count": int(row["missing_years_count"]),
                    "gap_to_leader_years": int(gap_to_leader),
                    "gap_to_own_ceiling_years": int(gap_to_own_ceiling),
                    "years_missing": row["years_missing"],
                    "estimated_history_end": row["estimated_history_end"],
                }
            )

        lagging_rows.sort(
            key=lambda item: (
                -int(item["missing_years_count"]),
                -int(item["gap_to_leader_years"]),
                str(item["company_name"]).upper(),
            )
        )

        risks_summary = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "total_companies": int(total_companies),
        }
        prioritized_companies: list[dict[str, Any]] = []
        for row in lagging_rows:
            missing_years_count = int(row.get("missing_years_count", 0) or 0)
            gap_to_leader_years = int(row.get("gap_to_leader_years", 0) or 0)
            gap_to_own_ceiling_years = int(row.get("gap_to_own_ceiling_years", 0) or 0)
            risk_level = self._risk_level(missing_years_count, gap_to_leader_years)
            if risk_level == "alto":
                risks_summary["high"] += 1
            elif risk_level == "medio":
                risks_summary["medium"] += 1
            else:
                risks_summary["low"] += 1

            if missing_years_count <= 0:
                continue

            years_missing = [int(y) for y in row.get("years_missing", [])]
            priority_score = (missing_years_count * 100) + (gap_to_leader_years * 25) + (gap_to_own_ceiling_years * 15)
            if risk_level == "alto":
                reason = "Cobertura muito atrasada"
            elif risk_level == "medio":
                reason = "Gap relevante com lider"
            else:
                reason = "Ajuste fino de cobertura"

            prioritized_companies.append(
                {
                    "cd_cvm": int(row["cd_cvm"]),
                    "company_name": str(row["company_name"]),
                    "risk_level": risk_level,
                    "priority_score": int(priority_score),
                    "missing_years_count": missing_years_count,
                    "gap_to_leader_years": gap_to_leader_years,
                    "years_missing": years_missing,
                    "recommended_action": self._priority_action(years_missing),
                    "reason": reason,
                }
            )

        prioritized_companies.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                str(item["company_name"]).upper(),
            )
        )
        prioritized_companies = prioritized_companies[: self.PRIORITY_LIST_LIMIT]

        global_total = int(total_companies * len(years))
        global_completed = sum(int(bucket["completed"]) for bucket in per_year_buckets.values())
        global_missing = max(0, global_total - global_completed)
        global_pct = (100.0 * global_completed / global_total) if global_total > 0 else 0.0

        throughput = self._estimate_throughput_per_hour()
        throughput_per_hour = throughput.get("per_hour")
        throughput_confidence = str(throughput.get("confidence") or "low")
        remaining_company_count = sum(1 for row in companies if int(row["missing_years_count"]) > 0)
        eta_global_hours = (
            float(remaining_company_count) / float(throughput_per_hour)
            if throughput_per_hour
            else None
        )

        per_year_rows: list[dict[str, Any]] = []
        for year in years:
            bucket = per_year_buckets[int(year)]
            total = int(bucket["total_companies"])
            completed_year = int(bucket["completed"])
            missing_year = int(bucket["missing"])
            pct = (100.0 * completed_year / total) if total > 0 else 0.0
            eta_hours = (
                float(missing_year) / float(throughput_per_hour)
                if throughput_per_hour
                else None
            )
            per_year_rows.append(
                {
                    "year": int(year),
                    "total_companies": total,
                    "completed": completed_year,
                    "missing": missing_year,
                    "pct": pct,
                    "eta_hours": eta_hours,
                }
            )

        end_year_row = next((row for row in per_year_rows if int(row.get("year", 0)) == int(end)), None)
        end_year_pct = float(end_year_row.get("pct", global_pct) if end_year_row else global_pct)

        if throughput_per_hour:
            throughput_score = {
                "high": 100.0,
                "medium": 75.0,
                "low": 55.0,
            }.get(throughput_confidence, 55.0)
        else:
            throughput_score = {
                "high": 70.0,
                "medium": 50.0,
                "low": 30.0,
            }.get(throughput_confidence, 30.0)

        health_score = max(
            0.0,
            min(
                100.0,
                (0.6 * float(global_pct)) + (0.2 * float(end_year_pct)) + (0.2 * float(throughput_score)),
            ),
        )
        health_status = self._health_status_from_score(health_score)

        prev_global = previous_snapshot.get("global", {}) if isinstance(previous_snapshot, dict) else {}
        prev_completed = int(prev_global.get("completed_cells", 0) or 0)
        prev_missing = int(prev_global.get("missing_cells", 0) or 0)
        prev_pct = float(prev_global.get("pct", 0.0) or 0.0)
        has_previous = isinstance(previous_snapshot, dict) and bool(prev_global)

        delta_completed = int(global_completed) - prev_completed
        delta_missing = int(global_missing) - prev_missing
        delta_pct = float(global_pct) - prev_pct
        trend = "estavel"
        if delta_completed > 0 or delta_pct > 0:
            trend = "melhora"
        elif delta_completed < 0 or delta_pct < 0:
            trend = "piora"

        snapshot = {
            "generated_at": now.replace(microsecond=0).isoformat(),
            "start_year": start,
            "end_year": end,
            "required_package": list(self.REQUIRED_PACKAGE_STATEMENTS),
            "processed_signature": processed_signature,
            "last_success_marker": last_success_marker,
            "global": {
                "total_cells": global_total,
                "completed_cells": int(global_completed),
                "missing_cells": int(global_missing),
                "pct": global_pct,
                "active_universe": int(total_companies),
                "remaining_companies": int(remaining_company_count),
                "eta_hours": eta_global_hours,
            },
            "throughput": throughput,
            "per_year": per_year_rows,
            "top_lagging": lagging_rows[:10],
            "companies": companies,
            "health_score": round(float(health_score), 2),
            "health_status": health_status,
            "progress_delta": {
                "has_previous": bool(has_previous),
                "delta_completed_cells": int(delta_completed),
                "delta_missing_cells": int(delta_missing),
                "delta_pct": round(float(delta_pct), 4),
                "trend": trend,
            },
            "risks_summary": risks_summary,
            "prioritized_companies": prioritized_companies,
        }
        self._write_cached_json(self.base_health_cache_path, snapshot)
        return snapshot

    def build_ranked_selection(self, start_year: int, end_year: int, target_count: int) -> list[dict[str, Any]]:
        db_rows = self._load_db_company_rows()
        if not db_rows:
            return []

        cache = self._load_market_cache()
        refresh_status = self._load_refresh_status_map()
        db_presence = self._load_statement_presence(start_year, end_year)
        raw_presence = self._scan_processed_statement_presence(start_year, end_year)
        combined_presence: dict[tuple[int, int], set[str]] = defaultdict(set)
        for key, values in db_presence.items():
            combined_presence[key].update(values)
        for key, values in raw_presence.items():
            combined_presence[key].update(values)
        fetch_budget = {"remaining": self.MAX_ONLINE_FETCH}
        now = datetime.now()

        staged_rows: list[dict[str, Any]] = []
        mkt_values: list[float] = []
        liq_values: list[float] = []
        gaps: list[int] = []
        recency_days_values: list[float] = []

        for row in db_rows:
            cd_cvm = int(row["cd_cvm"])
            company_name = str(row["company_name"])
            last_report_year = int(row["last_report_year"]) if row["last_report_year"] is not None else None
            min_report_year = int(row["min_report_year"]) if row["min_report_year"] is not None else None
            report_years_count = int(row["report_years_count"] or 0)
            only_end_year_history = (
                report_years_count == 1
                and min_report_year == end_year
                and last_report_year == end_year
            )

            ticker = TICKER_MAP.get(cd_cvm)
            snapshot = self._load_market_snapshot(ticker, cache, fetch_budget)
            mktcap = float(snapshot.get("mktcap", 0.0) or 0.0)
            avg_volume = float(snapshot.get("avg_volume", 0.0) or 0.0)

            refresh_row = refresh_status.get(cd_cvm, {})
            refresh_success = self._parse_fetched_at(refresh_row.get("last_success_at"))
            refresh_attempt = self._parse_fetched_at(refresh_row.get("last_attempt_at"))
            refresh_state = str(refresh_row.get("last_status") or "").strip().lower()
            refresh_error = str(refresh_row.get("last_error") or "")
            last_file_update = self._find_last_file_update(company_name)
            db_ref = datetime(last_report_year, 12, 31) if last_report_year else None
            if refresh_success is not None:
                # Primary recency source for rotation: explicit updater success timestamp.
                last_update_ref = refresh_success
            else:
                candidates = [
                    d for d in (refresh_attempt, db_ref, last_file_update) if d is not None
                ]
                last_update_ref = max(candidates) if candidates else None
            if last_update_ref is not None:
                days_since_update = max(0.0, (now - last_update_ref).total_seconds() / 86_400.0)
                recency_for_score = days_since_update
            else:
                days_since_update = None
                # Sem referência de update => tratar como muito desatualizada
                recency_for_score = 3650.0

            if last_report_year is not None:
                year_gap = max(0, end_year - int(last_report_year))
            else:
                year_gap = max(1, end_year - start_year + 1)
            is_recently_updated = (
                days_since_update is not None
                and days_since_update < (self.RECENT_UPDATE_COOLDOWN_HOURS / 24.0)
            )
            is_recent_no_data = (
                refresh_attempt is not None
                and refresh_attempt >= now - timedelta(days=self.NO_DATA_COOLDOWN_DAYS)
                and (
                    refresh_state == "no_data"
                    or "No financial rows found for selected years" in refresh_error
                )
            )
            source_presence_years_count = sum(
                1
                for year in range(int(start_year), int(end_year) + 1)
                if combined_presence.get((cd_cvm, int(year)))
            )
            has_source_presence = source_presence_years_count > 0

            staged_rows.append(
                {
                    "cd_cvm": cd_cvm,
                    "company_name": company_name,
                    "ticker": ticker,
                    "last_report_year": last_report_year,
                    "last_file_update": last_file_update,
                    "last_update_ref": last_update_ref,
                    "mktcap": mktcap,
                    "avg_volume": avg_volume,
                    "year_gap": year_gap,
                    "days_since_update": days_since_update,
                    "recency_for_score": recency_for_score,
                    "is_recently_updated": is_recently_updated,
                    "is_recent_no_data": is_recent_no_data,
                    "has_source_presence": has_source_presence,
                    "source_presence_years_count": int(source_presence_years_count),
                    "only_end_year_history": only_end_year_history,
                }
            )
            mkt_values.append(mktcap)
            liq_values.append(avg_volume)
            gaps.append(year_gap)
            recency_days_values.append(recency_for_score)

        ranked: list[RankedCompany] = []
        gaps_float = [float(g) for g in gaps]
        for row in staged_rows:
            mkt_norm = _minmax_normalize(row["mktcap"], mkt_values)
            liq_norm = _minmax_normalize(row["avg_volume"], liq_values)
            importance_score = (
                self.MKT_CAP_WEIGHT * mkt_norm + self.LIQUIDITY_WEIGHT * liq_norm
            )
            staleness_year = _minmax_normalize(float(row["year_gap"]), gaps_float)
            staleness_recency = _minmax_normalize(
                float(row["recency_for_score"]),
                recency_days_values,
            )
            staleness_score = (
                self.STALENESS_YEAR_WEIGHT * staleness_year
                + self.STALENESS_RECENCY_WEIGHT * staleness_recency
            )
            cooldown_penalty = 0.35 if row["is_recently_updated"] else 0.0
            no_data_penalty = 0.60 if row["is_recent_no_data"] else 0.0
            total_score = (
                self.IMPORTANCE_WEIGHT * importance_score
                + self.STALENESS_WEIGHT * staleness_score
                - cooldown_penalty
                - no_data_penalty
            )

            ranked.append(
                RankedCompany(
                    cd_cvm=row["cd_cvm"],
                    company_name=row["company_name"],
                    ticker=row["ticker"],
                    last_report_year=row["last_report_year"],
                    last_file_update=row["last_file_update"],
                    last_update_ref=row["last_update_ref"],
                    mktcap=row["mktcap"],
                    avg_volume=row["avg_volume"],
                    importance_score=importance_score,
                    staleness_score=staleness_score,
                    total_score=total_score,
                    year_gap=row["year_gap"],
                    days_since_update=row["days_since_update"],
                    is_recently_updated=row["is_recently_updated"],
                    is_recent_no_data=row["is_recent_no_data"],
                    has_source_presence=row["has_source_presence"],
                    source_presence_years_count=row["source_presence_years_count"],
                    only_end_year_history=row["only_end_year_history"],
                )
            )

        ranked.sort(
            key=lambda r: (
                0 if r.has_source_presence else 1,  # no-source candidates last
                1 if r.is_recent_no_data else 0,   # recent no-data last
                1 if r.is_recently_updated else 0,   # recently-updated last
                -int(r.source_presence_years_count), # more years with source presence first
                0 if r.only_end_year_history else 1,  # end-year-only first
                -float(r.year_gap),                   # highest defasagem first
                -r.total_score,                       # then by composite score
                -r.importance_score,                  # tiebreaker
                -float(r.mktcap),                     # tiebreaker
            ),
        )
        self._save_market_cache(cache)
        top = ranked[: max(1, target_count)]
        return [item.to_row() for item in top]
