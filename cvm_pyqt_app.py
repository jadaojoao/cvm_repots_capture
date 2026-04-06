"""
CVM Analytics - PyQt6 Desktop Updater (Intelligent Mode)

Modo unico de selecao inteligente:
- ranking por importancia (40% market cap + 60% liquidez),
- combinado com desatualizacao por anos,
- com penalizacao de empresas atualizadas recentemente (evita repetir o mesmo lote),
- leitura hibrida cache/local + online (yfinance),
- lista revisavel antes de iniciar.
"""

from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
import traceback
import webbrowser
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    from PyQt6.QtCore import QObject, Qt, QStringListModel, QThread, pyqtSignal
    from PyQt6.QtGui import QPalette, QColor
    from PyQt6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QComboBox,
        QCompleter,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    print("PyQt6 nao encontrado. Instale as dependencias com: pip install -r requirements.txt")
    raise SystemExit(1) from exc

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

from src.ticker_map import TICKER_MAP
from src.scraper import CVMScraper


APP_STYLESHEET = """
QWidget {
    background-color: #0b1220;
    color: #e5e7eb;
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #2d3f55;
    border-radius: 8px;
    margin-top: 10px;
    padding: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #93c5fd;
    font-weight: 600;
}
QPlainTextEdit, QTableWidget {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 6px;
    color: #e5e7eb;
    selection-background-color: #1e3a5f;
    selection-color: #e5e7eb;
}
QTableWidget:focus {
    border: 1px solid #60a5fa;
}
/* ── QSpinBox: all-state colors prevent Fusion highlight override ── */
QSpinBox {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 6px;
    color: #e5e7eb;
    selection-background-color: #1e3a5f;
    selection-color: #e5e7eb;
    min-height: 26px;
}
QSpinBox:focus {
    border: 1px solid #60a5fa;
    background-color: #111827;
    color: #e5e7eb;
}
/* ── QComboBox: explicit all-state styling to prevent Fusion blue block ── */
QComboBox {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 6px;
    padding-right: 24px;
    color: #e5e7eb;
    min-height: 26px;
}
QComboBox:!editable, QComboBox:!editable:on {
    background-color: #111827;
    color: #e5e7eb;
}
QComboBox:focus, QComboBox:on {
    border: 1px solid #60a5fa;
    background-color: #111827;
    color: #e5e7eb;
}
QPushButton {
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton#buildButton {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton#buildButton:hover {
    background-color: #1d4ed8;
}
QPushButton#buildButton:pressed {
    background-color: #1e40af;
}
QPushButton#buildButton:disabled {
    background-color: #1e293b;
    color: #9ca3af;
}
QPushButton#startButton {
    background-color: #16a34a;
    color: #ffffff;
}
QPushButton#startButton:hover {
    background-color: #15803d;
}
QPushButton#startButton:pressed {
    background-color: #166534;
}
QPushButton#startButton:disabled {
    background-color: #374151;
    color: #9ca3af;
}
QPushButton#cancelButton {
    background-color: #1f2937;
    color: #e5e7eb;
    border: 1px solid #334155;
}
QPushButton#cancelButton:disabled {
    background-color: #111827;
    color: #6b7280;
    border: 1px solid #1f2937;
}
QPushButton#dashboardButton {
    background-color: #0f172a;
    color: #bfdbfe;
    border: 1px solid #334155;
}
QPushButton#dashboardButton:hover {
    border: 1px solid #60a5fa;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 8px;
    text-align: center;
    background-color: #0f172a;
    min-height: 20px;
}
QProgressBar::chunk {
    border-radius: 7px;
    background-color: #22c55e;
}
QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
}
QLabel#subtitleLabel {
    color: #9ca3af;
}
QLabel#errorLabel {
    color: #f87171;
    font-size: 12px;
    min-height: 18px;
}
QLabel#summaryLabel {
    color: #93c5fd;
}
QLabel#statusLabel {
    color: #a7f3d0;
    font-weight: 600;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #bfdbfe;
    border: 1px solid #1f2937;
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: #1e3a5f;
    color: #e5e7eb;
}
QTableWidget::item:hover {
    background-color: #1f2937;
}

/* ── ComboBox dropdown button and arrow ── */
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #9ca3af;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    color: #e5e7eb;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    border: 1px solid #334155;
    outline: 0;
}

/* ── SpinBox up/down buttons ── */
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #1f2937;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #374151;
}
QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 4px solid #9ca3af;
}
QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #9ca3af;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #4b5563; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #0f172a;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #4b5563; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


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

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.db_path = project_root / "data" / "db" / "cvm_financials.db"
        self.cache_path = project_root / "data" / "cache" / "yfinance_cache.json"
        self.reports_dir = project_root / "output" / "reports"
        self.base_health_cache_path = project_root / "data" / "cache" / "base_health_snapshot.json"
        self.active_universe_cache_path = project_root / "data" / "cache" / "active_universe_cache.json"
        self.processed_dir = project_root / "data" / "input" / "processed"

    def _load_market_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

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
            if year < int(start_year) or year > int(end_year):
                continue

            try:
                df_codes = pd.read_csv(
                    csv_path,
                    sep=";",
                    encoding="latin1",
                    usecols=["CD_CVM"],
                    low_memory=False,
                )
            except Exception:
                continue

            codes = pd.to_numeric(df_codes["CD_CVM"], errors="coerce").dropna().astype(int).unique().tolist()
            for cd in codes:
                presence[(int(cd), int(year))].add(canonical_stmt)
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

        global_total = int(total_companies * len(years))
        global_completed = sum(int(bucket["completed"]) for bucket in per_year_buckets.values())
        global_missing = max(0, global_total - global_completed)
        global_pct = (100.0 * global_completed / global_total) if global_total > 0 else 0.0

        throughput = self._estimate_throughput_per_hour()
        throughput_per_hour = throughput.get("per_hour")
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
        }
        self._write_cached_json(self.base_health_cache_path, snapshot)
        return snapshot

    def build_ranked_selection(self, start_year: int, end_year: int, target_count: int) -> list[dict[str, Any]]:
        db_rows = self._load_db_company_rows()
        if not db_rows:
            return []

        cache = self._load_market_cache()
        refresh_status = self._load_refresh_status_map()
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
            total_score = (
                self.IMPORTANCE_WEIGHT * importance_score
                + self.STALENESS_WEIGHT * staleness_score
                - cooldown_penalty
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
                    only_end_year_history=row["only_end_year_history"],
                )
            )

        ranked.sort(
            key=lambda r: (
                1 if r.is_recently_updated else 0,   # recently-updated last
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


class HealthWorker(QThread):
    health_ready = pyqtSignal(dict)
    health_failed = pyqtSignal(str)

    def __init__(
        self,
        service: "IntelligentSelectorService",
        start_year: int,
        end_year: int,
        force_refresh: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.start_year = start_year
        self.end_year = end_year
        self.force_refresh = force_refresh

    def run(self):
        try:
            snapshot = self.service.build_base_health_snapshot(
                start_year=self.start_year,
                end_year=self.end_year,
                force_refresh=self.force_refresh,
            )
            self.health_ready.emit(snapshot)
        except Exception:
            self.health_failed.emit(traceback.format_exc())


class SignalLogStream(io.TextIOBase):
    """Encaminha stdout/stderr para sinal Qt linha a linha."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._buffer = ""

    def write(self, text):
        if not text:
            return 0
        self._buffer += str(text)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                self._callback(line)
        return len(text)

    def flush(self):
        remaining = self._buffer.strip()
        if remaining:
            self._callback(remaining)
        self._buffer = ""


class RankingWorker(QThread):
    finished_data = pyqtSignal(list)
    failed = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, service: IntelligentSelectorService, start_year: int, end_year: int, target_count: int, parent=None):
        super().__init__(parent)
        self.service = service
        self.start_year = start_year
        self.end_year = end_year
        self.target_count = target_count

    def run(self):
        try:
            self.status_changed.emit("Montando ranking inteligente...")
            self.log_message.emit(
                f"Gerando ranking para {self.target_count} empresas (periodo {self.start_year}-{self.end_year})."
            )
            data = self.service.build_ranked_selection(
                start_year=self.start_year,
                end_year=self.end_year,
                target_count=self.target_count,
            )
            self.finished_data.emit(data)
        except Exception:
            tb = traceback.format_exc()
            try:
                root_dir = Path(__file__).resolve().parent
                log_dir = root_dir / "output" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                error_log = log_dir / "updater_worker_errors.log"
                with open(error_log, "a", encoding="utf-8") as fh:
                    fh.write(f"\n[{datetime.now().isoformat()}]\n{tb}\n")
            except Exception:
                # Do not mask the original worker error due logging failures.
                pass
            self.failed.emit(tb)


class UpdateWorker(QThread):
    progress_changed = pyqtSignal(int, int, str)
    log_message = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    finished_success = pyqtSignal(int)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        companies: list[str],
        start_year: int,
        end_year: int,
        max_workers: int,
        parent=None,
    ):
        super().__init__(parent)
        self._companies = companies
        self._start_year = start_year
        self._end_year = end_year
        self._max_workers = max_workers
        self._cancel_requested = False
        self._cancel_triggered = False

    def request_cancel(self):
        self._cancel_requested = True

    def _should_cancel(self):
        if self._cancel_requested:
            self._cancel_triggered = True
            return True
        return False

    def _on_progress(self, current, total, company_name):
        # current = empresas concluidas ate aqui (callback disparado no inicio da proxima)
        self.progress_changed.emit(int(current), int(total), str(company_name))

    @staticmethod
    def _ensure_refresh_status_table(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS company_refresh_status (
                cd_cvm INTEGER PRIMARY KEY,
                company_name TEXT,
                source_scope TEXT NOT NULL DEFAULT 'local',
                last_attempt_at TEXT,
                last_success_at TEXT,
                last_status TEXT,
                last_error TEXT,
                last_start_year INTEGER,
                last_end_year INTEGER,
                last_rows_inserted INTEGER,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crs_status
            ON company_refresh_status(last_status)
            """
        )

    @staticmethod
    def _count_rows_for_company_years(
        conn: sqlite3.Connection,
        cd_cvm: int,
        start_year: int,
        end_year: int,
    ) -> int:
        cursor = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM financial_reports
            WHERE "CD_CVM" = ?
              AND "REPORT_YEAR" BETWEEN ? AND ?
            """,
            (int(cd_cvm), int(start_year), int(end_year)),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            LIMIT 1
            """,
            (str(table_name),),
        ).fetchone()
        return row is not None

    @staticmethod
    def _touch_company_updated_at(
        conn: sqlite3.Connection,
        cd_cvm: int,
        company_name: str,
        updated_at: str,
    ) -> None:
        conn.execute(
            """
            UPDATE companies
            SET company_name = COALESCE(NULLIF(?, ''), company_name),
                updated_at = ?
            WHERE cd_cvm = ?
            """,
            (str(company_name), str(updated_at), int(cd_cvm)),
        )

    @staticmethod
    def _append_worker_error_log(root_dir: Path, company_name: str, payload: dict[str, Any]) -> None:
        try:
            log_dir = root_dir / "output" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            error_log = log_dir / "updater_worker_errors.log"
            now_iso = datetime.now().isoformat()
            with open(error_log, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{now_iso}] company={company_name!r} payload_status={payload.get('status')!r}\n")
                fh.write(f"error={payload.get('error')!r}\n")
                traceback_text = str(payload.get("traceback") or "").strip()
                if traceback_text:
                    fh.write(f"{traceback_text}\n")
        except Exception:
            # Never raise from diagnostics path.
            pass

    def _sync_refresh_status(self, db_path: Path, results: dict[str, Any]) -> int:
        if not results:
            return 0

        now_iso = datetime.now().replace(microsecond=0).isoformat()
        updated = 0
        with sqlite3.connect(str(db_path)) as conn:
            self._ensure_refresh_status_table(conn)
            companies_table_exists = self._table_exists(conn, "companies")
            for result_key, payload in results.items():
                payload = payload if isinstance(payload, dict) else {}
                try:
                    cd_cvm = int(payload.get("cvm_code"))
                except Exception:
                    continue
                company_name = str(payload.get("company_name") or result_key)

                raw_status = str(payload.get("status") or "error").strip().lower()
                status = "success" if raw_status == "success" else "error"

                rows_from_payload = payload.get("rows_inserted")
                try:
                    rows_in_range = int(rows_from_payload) if rows_from_payload is not None else 0
                except Exception:
                    rows_in_range = 0

                if status == "success" and rows_in_range <= 0:
                    rows_in_range = self._count_rows_for_company_years(
                        conn=conn,
                        cd_cvm=cd_cvm,
                        start_year=self._start_year,
                        end_year=self._end_year,
                    )

                last_success_at = now_iso if status == "success" else None
                error_message = payload.get("error")
                if status == "success":
                    error_message = None
                elif not error_message:
                    error_message = f"Status={status}"

                conn.execute(
                    """
                    INSERT INTO company_refresh_status (
                        cd_cvm, company_name, source_scope,
                        last_attempt_at, last_success_at, last_status, last_error,
                        last_start_year, last_end_year, last_rows_inserted, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cd_cvm) DO UPDATE SET
                        company_name = excluded.company_name,
                        source_scope = excluded.source_scope,
                        last_attempt_at = excluded.last_attempt_at,
                        last_success_at = COALESCE(excluded.last_success_at, company_refresh_status.last_success_at),
                        last_status = excluded.last_status,
                        last_error = excluded.last_error,
                        last_start_year = excluded.last_start_year,
                        last_end_year = excluded.last_end_year,
                        last_rows_inserted = CASE
                            WHEN excluded.last_status = 'success'
                            THEN excluded.last_rows_inserted
                            ELSE company_refresh_status.last_rows_inserted
                        END,
                        updated_at = excluded.updated_at
                    """,
                    (
                        cd_cvm,
                        str(company_name),
                        "local",
                        now_iso,
                        last_success_at,
                        status,
                        error_message,
                        int(self._start_year),
                        int(self._end_year),
                        int(rows_in_range),
                        now_iso,
                    ),
                )
                if companies_table_exists and status == "success":
                    self._touch_company_updated_at(
                        conn=conn,
                        cd_cvm=cd_cvm,
                        company_name=str(company_name),
                        updated_at=now_iso,
                    )
                updated += 1

            conn.commit()
        return updated

    def run(self):
        try:
            root_dir = Path(__file__).resolve().parent
            data_dir = str(root_dir / "data" / "input")
            output_dir = str(root_dir / "output" / "reports")

            self.log_message.emit(f"Paralelismo definido: {self._max_workers} worker(s).")
            self.status_changed.emit("Inicializando motor CVM...")

            scraper = CVMScraper(
                data_dir=data_dir,
                output_dir=output_dir,
                max_workers=self._max_workers,
            )

            log_stream = SignalLogStream(self.log_message.emit)
            self.status_changed.emit("Executando atualizacao...")

            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                results = scraper.run(
                    companies=self._companies,
                    start_year=self._start_year,
                    end_year=self._end_year,
                    progress_callback=self._on_progress,
                    should_cancel=self._should_cancel,
                )
            log_stream.flush()
            was_cancelled = self._cancel_triggered

            success_count = 0
            error_count = 0
            no_data_count = 0
            for result_key, payload in (results or {}).items():
                payload_dict = payload if isinstance(payload, dict) else {}
                status = str(payload_dict.get("status") or "error").strip().lower()
                company_name = str(payload_dict.get("company_name") or result_key)
                if status == "success":
                    success_count += 1
                elif status == "no_data":
                    no_data_count += 1
                else:
                    error_count += 1
                    self._append_worker_error_log(
                        root_dir=root_dir,
                        company_name=company_name,
                        payload=payload_dict,
                    )

            try:
                synced = self._sync_refresh_status(
                    db_path=root_dir / "data" / "db" / "cvm_financials.db",
                    results=results,
                )
                if synced > 0:
                    self.log_message.emit(
                        f"Sync Dashboard: status atualizado para {synced} empresa(s)."
                    )
            except Exception as sync_exc:
                self.log_message.emit(
                    f"Aviso: nao foi possivel sincronizar status do Dashboard ({sync_exc})."
                )

            self.log_message.emit(
                f"Resumo do lote: success={success_count}, sem_dados={no_data_count}, erro={error_count}."
            )
            if was_cancelled:
                self.cancelled.emit()
                return
            self.finished_success.emit(success_count)
        except Exception:
            tb = traceback.format_exc()
            self._append_worker_error_log(
                root_dir=Path(__file__).resolve().parent,
                company_name="__worker__",
                payload={"status": "error", "error": "Unhandled worker failure", "traceback": tb},
            )
            self.failed.emit(tb)


class MainWindow(QMainWindow):
    build_requested = pyqtSignal(int, int, int)
    start_requested = pyqtSignal(list, int, int, int)
    cancel_requested = pyqtSignal()
    dashboard_requested = pyqtSignal()
    years_changed = pyqtSignal(int, int)
    preset_selected = pyqtSignal(str)
    selection_changed = pyqtSignal(int)
    add_company_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._internal_update = False
        self._is_running = False
        self._is_building = False
        self._can_start = False

        self._build_ui()
        self._wire_signals()
        self._emit_years_changed()

    def _build_ui(self):
        self.setWindowTitle("CVM Analytics - Updater Inteligente")
        self.setMinimumSize(780, 540)

        current_year = datetime.now().year

        # Scrollable container so the UI works on smaller/secondary screens
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        title = QLabel("CVM Analytics Updater")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Modo inteligente: importancia de mercado + desatualizacao por anos"
        )
        subtitle.setObjectName("subtitleLabel")
        root.addWidget(title)
        root.addWidget(subtitle)

        config_box = QGroupBox("① Configuração Inteligente")
        config_form = QFormLayout(config_box)
        config_form.setSpacing(10)

        years_row = QWidget()
        years_layout = QHBoxLayout(years_row)
        years_layout.setContentsMargins(0, 0, 0, 0)
        years_layout.setSpacing(8)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            ["Ultimos 2 anos", "Ultimos 3 anos", "Ultimos 5 anos", "Personalizado"]
        )
        self.preset_combo.setCurrentText("Ultimos 3 anos")
        self.preset_combo.setMinimumWidth(160)

        self.start_year_spin = QSpinBox()
        self.start_year_spin.setRange(1990, current_year + 1)
        self.start_year_spin.setValue(current_year - 2)
        self.start_year_spin.setMinimumWidth(75)

        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(1990, current_year + 1)
        self.end_year_spin.setValue(current_year)
        self.end_year_spin.setMinimumWidth(75)

        years_layout.addWidget(QLabel("Preset:"))
        years_layout.addWidget(self.preset_combo)
        years_layout.addSpacing(16)
        years_layout.addWidget(QLabel("Ano inicial:"))
        years_layout.addWidget(self.start_year_spin)
        years_layout.addSpacing(8)
        years_layout.addWidget(QLabel("Ano final:"))
        years_layout.addWidget(self.end_year_spin)
        years_layout.addStretch(1)
        config_form.addRow("Periodo:", years_row)

        strategy_row = QWidget()
        strategy_layout = QHBoxLayout(strategy_row)
        strategy_layout.setContentsMargins(0, 0, 0, 0)
        strategy_layout.setSpacing(8)

        self.target_count_spin = QSpinBox()
        self.target_count_spin.setRange(1, 300)
        self.target_count_spin.setValue(50)
        self.target_count_spin.setMinimumWidth(65)

        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(2, 8)
        self.max_workers_spin.setValue(2)
        self.max_workers_spin.setMinimumWidth(55)

        self.build_button = QPushButton("Gerar Lista Inteligente")
        self.build_button.setObjectName("buildButton")
        self.build_button.setMinimumWidth(170)

        strategy_layout.addWidget(QLabel("Qtd. empresas:"))
        strategy_layout.addWidget(self.target_count_spin)
        strategy_layout.addSpacing(16)
        strategy_layout.addWidget(QLabel("Paralelismo (2–8):"))
        strategy_layout.addWidget(self.max_workers_spin)
        strategy_layout.addStretch(1)
        config_form.addRow("Selecao:", strategy_row)

        # Botão numa linha dedicada para não ser espremido
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self.build_button)
        btn_layout.addStretch(1)
        config_form.addRow("", btn_row)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("summaryLabel")
        config_form.addRow("Resumo:", self.summary_label)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setText("")
        config_form.addRow("", self.error_label)

        root.addWidget(config_box)

        health_box = QGroupBox("Saúde da Base")
        health_layout = QVBoxLayout(health_box)
        health_layout.setSpacing(10)

        def _health_row(caption: str) -> tuple:
            row = QWidget()
            vbox = QVBoxLayout(row)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(2)
            cap = QLabel(caption.upper())
            cap.setStyleSheet("color: #9ca3af; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")
            val = QLabel("—")
            val.setWordWrap(True)
            val.setStyleSheet("color: #e5e7eb; font-size: 12px;")
            vbox.addWidget(cap)
            vbox.addWidget(val)
            return row, val

        global_row, self.health_global_label = _health_row("Global")
        self.health_global_label.setText("Aguardando calculo de cobertura...")
        health_layout.addWidget(global_row)

        years_row_h, self.health_years_label = _health_row("Por ano")
        health_layout.addWidget(years_row_h)

        laggards_row, self.health_laggards_label = _health_row("Mais defasadas")
        health_layout.addWidget(laggards_row)

        root.addWidget(health_box)

        table_box = QGroupBox("② Empresas Selecionadas")
        table_layout = QVBoxLayout(table_box)

        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 4)
        search_layout.setSpacing(8)
        self.company_search_edit = QLineEdit()
        self.company_search_edit.setPlaceholderText("Buscar empresa por nome, ticker ou código CVM...")
        self.company_search_edit.setMinimumWidth(300)
        self._company_completer = QCompleter([])
        self._company_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._company_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.company_search_edit.setCompleter(self._company_completer)
        self.add_company_button = QPushButton("Adicionar à lista")
        self.add_company_button.setObjectName("buildButton")
        self.add_company_button.setFixedWidth(150)
        search_layout.addWidget(self.company_search_edit, 1)
        search_layout.addWidget(self.add_company_button)
        table_layout.addWidget(search_row)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "Selecionar",
                "Empresa",
                "CVM",
                "Ticker",
                "Score",
                "Importancia",
                "Gap (anos)",
                "Cobertura",
                "Ultimo update",
                "MktCap (Bi)",
                "Liquidez (Mi)",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table)
        root.addWidget(table_box, 1)

        progress_box = QGroupBox("③ Execução")
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setSpacing(8)

        self.status_label = QLabel("Status: Pronto")
        self.status_label.setObjectName("statusLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        root.addWidget(progress_box)

        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(100)
        log_layout.addWidget(self.log_output)
        root.addWidget(log_box)

        button_row = QHBoxLayout()
        self.dashboard_button = QPushButton("Abrir Dashboard")
        self.dashboard_button.setObjectName("dashboardButton")
        button_row.addWidget(self.dashboard_button)
        button_row.addStretch(1)
        self.start_button = QPushButton("Iniciar atualizacao")
        self.start_button.setObjectName("startButton")
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        root.addLayout(button_row)

        scroll.setWidget(central)
        self.setCentralWidget(scroll)
        self._update_summary_label()

    def _wire_signals(self):
        self.start_year_spin.valueChanged.connect(self._on_year_changed)
        self.end_year_spin.valueChanged.connect(self._on_year_changed)
        self.target_count_spin.valueChanged.connect(self._update_summary_label)
        self.max_workers_spin.valueChanged.connect(self._update_summary_label)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self.build_button.clicked.connect(self._on_build_clicked)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.cancel_button.clicked.connect(lambda: self.cancel_requested.emit())
        self.dashboard_button.clicked.connect(lambda: self.dashboard_requested.emit())
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.add_company_button.clicked.connect(
            lambda: self.add_company_requested.emit(self.company_search_edit.text().strip())
        )
        self.company_search_edit.returnPressed.connect(
            lambda: self.add_company_requested.emit(self.company_search_edit.text().strip())
        )

    def _on_build_clicked(self):
        self.build_requested.emit(
            self.start_year_spin.value(),
            self.end_year_spin.value(),
            self.target_count_spin.value(),
        )

    def _on_start_clicked(self):
        self.start_requested.emit(
            self.get_selected_company_codes(),
            self.start_year_spin.value(),
            self.end_year_spin.value(),
            self.max_workers_spin.value(),
        )

    def _on_preset_changed(self, preset_name):
        if self._internal_update:
            return
        self.preset_selected.emit(preset_name)

    def _on_year_changed(self):
        if self._internal_update:
            return
        if self.preset_combo.currentText() != "Personalizado":
            self._internal_update = True
            self.preset_combo.setCurrentText("Personalizado")
            self._internal_update = False
        self._emit_years_changed()

    def _emit_years_changed(self):
        self._update_summary_label()
        self.years_changed.emit(self.start_year_spin.value(), self.end_year_spin.value())

    def _on_table_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            self.selection_changed.emit(self.get_selected_count())
            self._update_summary_label()

    def _update_summary_label(self):
        start = self.start_year_spin.value()
        end = self.end_year_spin.value()
        selected = self.get_selected_count()
        total = self.table.rowCount()
        self.summary_label.setText(
            f"Periodo {start}-{end} | Lista: {selected}/{total} selecionadas | Paralelismo: {self.max_workers_spin.value()}"
        )

    def set_years(self, start_year: int, end_year: int):
        self._internal_update = True
        self.start_year_spin.setValue(start_year)
        self.end_year_spin.setValue(end_year)
        self._internal_update = False
        self._emit_years_changed()

    def set_table_data(self, rows: list[dict[str, Any]]):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)

            select_item = QTableWidgetItem("")
            select_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            select_item.setCheckState(Qt.CheckState.Checked)
            select_item.setData(Qt.ItemDataRole.UserRole, str(row["cd_cvm"]))
            self.table.setItem(row_idx, 0, select_item)

            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row["company_name"])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row["cd_cvm"])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row["ticker"])))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{float(row['score']):.3f}"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"{float(row['importance_score']):.3f}"))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(int(row["year_gap"]))))
            self.table.setItem(row_idx, 7, QTableWidgetItem(str(row.get("coverage", "N/D"))))
            self.table.setItem(row_idx, 8, QTableWidgetItem(str(row["last_update"])))
            self.table.setItem(row_idx, 9, QTableWidgetItem(f"{float(row['mktcap_bi']):.2f}"))
            self.table.setItem(row_idx, 10, QTableWidgetItem(f"{float(row['liq_milhoes']):.2f}"))

        self.table.blockSignals(False)
        self.selection_changed.emit(self.get_selected_count())
        self._update_summary_label()

    def get_selected_company_codes(self) -> list[str]:
        selected: list[str] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                code = item.data(Qt.ItemDataRole.UserRole)
                if code:
                    selected.append(str(code))
        return selected

    def get_selected_count(self) -> int:
        return len(self.get_selected_company_codes())

    def set_validation_state(self, can_start: bool, message: str):
        self._can_start = can_start
        self.error_label.setText(message)
        self.start_button.setEnabled(can_start and not self._is_running and not self._is_building)

    def set_building_state(self, building: bool):
        self._is_building = building
        self.build_button.setEnabled(not building and not self._is_running)
        self.start_year_spin.setEnabled(not building and not self._is_running)
        self.end_year_spin.setEnabled(not building and not self._is_running)
        self.target_count_spin.setEnabled(not building and not self._is_running)
        self.preset_combo.setEnabled(not building and not self._is_running)
        self.max_workers_spin.setEnabled(not self._is_running)
        self.start_button.setEnabled((not building) and (not self._is_running) and self._can_start)

    def set_running_state(self, running: bool):
        self._is_running = running
        self.build_button.setEnabled(not running and not self._is_building)
        self.start_year_spin.setEnabled(not running and not self._is_building)
        self.end_year_spin.setEnabled(not running and not self._is_building)
        self.target_count_spin.setEnabled(not running and not self._is_building)
        self.preset_combo.setEnabled(not running and not self._is_building)
        self.max_workers_spin.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.start_button.setEnabled((not running) and (not self._is_building) and self._can_start)

    def set_status(self, text: str):
        self.status_label.setText(f"Status: {text}")

    def reset_progress(self):
        self.progress_bar.setValue(0)

    def set_progress_total(self, completed: int, total: int, current_company: str):
        pct = int((completed / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(max(0, min(100, pct)))
        self.set_status(f"Concluidas {completed}/{total} | Atual: {current_company}")

    @staticmethod
    def _format_eta(hours_value: Any) -> str:
        if hours_value is None:
            return "ETA indisponivel"
        try:
            hours = float(hours_value)
        except Exception:
            return "ETA indisponivel"
        if hours < 0:
            return "ETA indisponivel"
        if hours < 1:
            return f"ETA ~{max(1, int(round(hours * 60)))} min"
        if hours < 48:
            return f"ETA ~{hours:.1f} h"
        return f"ETA ~{(hours / 24.0):.1f} dias"

    def set_base_health(self, snapshot: dict[str, Any] | None):
        if not snapshot:
            self.health_global_label.setText("Cobertura indisponivel.")
            self.health_years_label.setText("N/D")
            self.health_laggards_label.setText("N/D")
            return

        global_stats = snapshot.get("global", {})
        pct = float(global_stats.get("pct", 0.0) or 0.0)
        complete = int(global_stats.get("completed_cells", 0) or 0)
        expected = int(global_stats.get("total_cells", 0) or 0)
        missing = int(global_stats.get("missing_cells", 0) or 0)
        eta_text = self._format_eta(global_stats.get("eta_hours"))
        throughput = snapshot.get("throughput", {})
        confidence = str(throughput.get("confidence") or "low")

        self.health_global_label.setText(
            f"{pct:.1f}% concluido ({complete}/{expected}) | faltantes: {missing} | {eta_text} | confianca ETA: {confidence}"
        )

        per_year_entries: list[str] = []
        for row in snapshot.get("per_year", []):
            year = row.get("year")
            year_pct = float(row.get("pct", 0.0) or 0.0)
            year_missing = int(row.get("missing", 0) or 0)
            year_eta = self._format_eta(row.get("eta_hours"))
            per_year_entries.append(
                f"{year}: {year_pct:.1f}% (faltam {year_missing}, {year_eta})"
            )
        self.health_years_label.setText(" | ".join(per_year_entries) if per_year_entries else "N/D")

        lag_parts: list[str] = []
        for row in snapshot.get("top_lagging", [])[:5]:
            name = str(row.get("company_name") or f"CVM {row.get('cd_cvm')}")
            miss = int(row.get("missing_years_count", 0) or 0)
            gap_leader = int(row.get("gap_to_leader_years", 0) or 0)
            lag_parts.append(f"{name} (faltam {miss}, gap lider {gap_leader})")
        self.health_laggards_label.setText(" | ".join(lag_parts) if lag_parts else "N/D")

    def append_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{ts}] {message}")
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def clear_log(self):
        self.log_output.clear()

    def set_company_list(self, companies: list[dict[str, Any]]) -> None:
        """Popula o autocompletador com todas as empresas do banco."""
        self._all_companies: list[dict[str, Any]] = companies
        labels: list[str] = []
        for c in companies:
            name = str(c.get("company_name") or "")
            ticker = str(c.get("ticker_b3") or "")
            cd_cvm = str(c.get("cd_cvm") or "")
            label = name
            if ticker:
                label += f" [{ticker}]"
            if cd_cvm:
                label += f" (CVM {cd_cvm})"
            c["_label"] = label
            labels.append(label)
        self._company_completer.setModel(QStringListModel(labels))

    def add_company_row(self, row_data: dict[str, Any]) -> None:
        """Insere uma empresa na tabela (já marcada), sem duplicar cd_cvm."""
        cd_cvm_new = str(row_data.get("cd_cvm", ""))
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == cd_cvm_new:
                # já está na lista — apenas marcar o checkbox
                self.table.blockSignals(True)
                item.setCheckState(Qt.CheckState.Checked)
                self.table.blockSignals(False)
                self.selection_changed.emit(self.get_selected_count())
                self._update_summary_label()
                return

        self.table.blockSignals(True)
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)

        select_item = QTableWidgetItem("")
        select_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsSelectable
        )
        select_item.setCheckState(Qt.CheckState.Checked)
        select_item.setData(Qt.ItemDataRole.UserRole, cd_cvm_new)
        self.table.setItem(row_idx, 0, select_item)

        self.table.setItem(row_idx, 1, QTableWidgetItem(str(row_data.get("company_name", ""))))
        self.table.setItem(row_idx, 2, QTableWidgetItem(cd_cvm_new))
        self.table.setItem(row_idx, 3, QTableWidgetItem(str(row_data.get("ticker_b3") or "—")))
        self.table.setItem(row_idx, 4, QTableWidgetItem("—"))
        self.table.setItem(row_idx, 5, QTableWidgetItem("—"))
        self.table.setItem(row_idx, 6, QTableWidgetItem("—"))
        self.table.setItem(row_idx, 7, QTableWidgetItem(str(row_data.get("coverage", "N/D"))))
        self.table.setItem(row_idx, 8, QTableWidgetItem("manual"))
        self.table.setItem(row_idx, 9, QTableWidgetItem("—"))
        self.table.setItem(row_idx, 10, QTableWidgetItem("—"))

        self.table.blockSignals(False)
        self.selection_changed.emit(self.get_selected_count())
        self._update_summary_label()
        self.company_search_edit.clear()


class UpdateController(QObject):
    PRESET_YEARS = {
        "Ultimos 2 anos": 2,
        "Ultimos 3 anos": 3,
        "Ultimos 5 anos": 5,
    }

    def __init__(self, view: MainWindow, service: IntelligentSelectorService):
        super().__init__()
        self.view = view
        self.service = service
        self.project_root = service.project_root
        self.update_worker: UpdateWorker | None = None
        self.ranking_worker: RankingWorker | None = None
        self.health_worker: HealthWorker | None = None
        self.dashboard_process: subprocess.Popen | None = None

        self.view.years_changed.connect(self.on_years_changed)
        self.view.build_requested.connect(self.on_build_requested)
        self.view.start_requested.connect(self.on_start_requested)
        self.view.cancel_requested.connect(self.on_cancel_requested)
        self.view.dashboard_requested.connect(self.on_dashboard_requested)
        self.view.preset_selected.connect(self.on_preset_selected)
        self.view.selection_changed.connect(self.on_selection_changed)
        self.view.add_company_requested.connect(self.on_add_company_requested)

        self._apply_preset_if_needed(self.view.preset_combo.currentText())
        self._validate_form()
        self._refresh_base_health(force_refresh=False)
        self._load_company_list()

    def _refresh_base_health(self, force_refresh: bool) -> None:
        # Se um worker não-force já está rodando, deixar concluir.
        if self.health_worker is not None and not force_refresh:
            return
        # Para force_refresh (pós-batch), encerrar worker anterior se ainda ativo.
        if self.health_worker is not None:
            self.health_worker.health_ready.disconnect()
            self.health_worker.health_failed.disconnect()
            self.health_worker.deleteLater()
            self.health_worker = None

        start_year = int(self.view.start_year_spin.value())
        end_year = int(self.view.end_year_spin.value())
        self.health_worker = HealthWorker(
            service=self.service,
            start_year=start_year,
            end_year=end_year,
            force_refresh=force_refresh,
            parent=self.view,
        )
        self.health_worker.health_ready.connect(self._on_health_ready)
        self.health_worker.health_failed.connect(self._on_health_failed)
        self.health_worker.start()

    def _on_health_ready(self, snapshot: dict) -> None:
        self.view.set_base_health(snapshot)
        if self.health_worker is not None:
            self.health_worker.deleteLater()
            self.health_worker = None

    def _on_health_failed(self, error_trace: str) -> None:
        self.view.set_base_health(None)
        first_line = error_trace.strip().splitlines()[0] if error_trace.strip() else "erro desconhecido"
        self.view.append_log(f"Aviso: falha ao calcular Saúde da Base ({first_line}).")
        if self.health_worker is not None:
            self.health_worker.deleteLater()
            self.health_worker = None

    def _is_dashboard_running(self) -> bool:
        if self.dashboard_process is None:
            return False
        return self.dashboard_process.poll() is None

    def _dashboard_command(self) -> list[str]:
        app_path = self.project_root / "dashboard" / "app.py"
        return [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
            "--server.port",
            "8501",
        ]

    def on_dashboard_requested(self):
        try:
            if self._is_dashboard_running():
                webbrowser.open("http://localhost:8501", new=2)
                self.view.set_status("Dashboard aberto no navegador.")
                self.view.append_log("Dashboard ja estava ativo. Abrindo navegador...")
                return

            cmd = self._dashboard_command()
            self.dashboard_process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.view.append_log("Inicializando dashboard local (Streamlit)...")
            self.view.set_status("Iniciando dashboard local...")
            webbrowser.open("http://localhost:8501", new=2)
        except Exception as exc:
            self.view.append_log(f"Falha ao abrir dashboard: {exc}")
            self.view.set_status("Falha ao iniciar dashboard.")

    def _validate_form(self):
        start_year = self.view.start_year_spin.value()
        end_year = self.view.end_year_spin.value()
        selected = self.view.get_selected_count()

        if start_year > end_year:
            self.view.set_validation_state(False, "Ano inicial deve ser menor ou igual ao ano final.")
            return False
        if self.view.table.rowCount() == 0:
            self.view.set_validation_state(False, "Gere a lista inteligente antes de iniciar.")
            return False
        if selected <= 0:
            self.view.set_validation_state(False, "Selecione ao menos uma empresa da lista.")
            return False

        self.view.set_validation_state(True, "")
        return True

    def _apply_preset_if_needed(self, preset_name: str):
        if preset_name not in self.PRESET_YEARS:
            return
        n_years = self.PRESET_YEARS[preset_name]
        current_year = datetime.now().year
        start_year = current_year - (n_years - 1)
        self.view.set_years(start_year, current_year)

    def _bind_update_worker(self, worker: UpdateWorker):
        worker.progress_changed.connect(self.on_worker_progress)
        worker.log_message.connect(self.view.append_log)
        worker.status_changed.connect(self.view.set_status)
        worker.finished_success.connect(self.on_worker_success)
        worker.cancelled.connect(self.on_worker_cancelled)
        worker.failed.connect(self.on_worker_failed)

    def _bind_ranking_worker(self, worker: RankingWorker):
        worker.finished_data.connect(self.on_ranking_ready)
        worker.failed.connect(self.on_ranking_failed)
        worker.status_changed.connect(self.view.set_status)
        worker.log_message.connect(self.view.append_log)

    def _cleanup_update_worker(self):
        if self.update_worker is None:
            return
        self.update_worker.deleteLater()
        self.update_worker = None

    def _cleanup_ranking_worker(self):
        if self.ranking_worker is None:
            return
        self.ranking_worker.deleteLater()
        self.ranking_worker = None

    def on_preset_selected(self, preset_name: str):
        if self.update_worker is not None or self.ranking_worker is not None:
            return
        self._apply_preset_if_needed(preset_name)

    def on_years_changed(self, _start: int, _end: int):
        if self.update_worker is not None:
            return
        self._refresh_base_health(force_refresh=False)
        self._validate_form()

    def on_selection_changed(self, _selected_count: int):
        if self.update_worker is not None:
            return
        self._validate_form()

    def on_build_requested(self, start_year: int, end_year: int, target_count: int):
        if self.update_worker is not None or self.ranking_worker is not None:
            return

        if start_year > end_year:
            self.view.set_validation_state(False, "Ano inicial deve ser menor ou igual ao ano final.")
            return

        self.view.clear_log()
        self.view.reset_progress()
        self.view.set_building_state(True)
        self.view.set_status("Preparando ranking...")

        self.ranking_worker = RankingWorker(
            service=self.service,
            start_year=start_year,
            end_year=end_year,
            target_count=target_count,
            parent=self.view,
        )
        self._bind_ranking_worker(self.ranking_worker)
        self.ranking_worker.start()

    def on_ranking_ready(self, rows: list[dict[str, Any]]):
        self.view.set_building_state(False)
        self.view.set_table_data(rows)
        self._refresh_base_health(force_refresh=True)
        if rows:
            self.view.append_log(f"Lista inteligente pronta com {len(rows)} empresas.")
            self.view.set_status("Lista inteligente pronta para revisao.")
        else:
            self.view.append_log("Nenhuma empresa encontrada no banco para montar o ranking.")
            self.view.set_status("Sem dados para ranking.")
        self._cleanup_ranking_worker()
        self._validate_form()

    def on_ranking_failed(self, error_trace: str):
        self.view.set_building_state(False)
        self.view.set_status("Falha ao montar ranking.")
        self.view.append_log("Erro ao montar lista inteligente:")
        for line in error_trace.strip().splitlines():
            self.view.append_log(line)
        self._cleanup_ranking_worker()
        self._validate_form()

    def on_start_requested(self, company_codes: list[str], start_year: int, end_year: int, max_workers: int):
        if self.update_worker is not None or self.ranking_worker is not None:
            return
        if not self._validate_form():
            return

        self.view.clear_log()
        self.view.append_log(
            f"Iniciando atualizacao de {len(company_codes)} empresa(s), periodo {start_year}-{end_year}, {max_workers} workers."
        )
        self.view.reset_progress()
        self.view.set_status("Preparando execucao...")
        self.view.set_running_state(True)

        self.update_worker = UpdateWorker(
            companies=company_codes,
            start_year=start_year,
            end_year=end_year,
            max_workers=max_workers,
            parent=self.view,
        )
        self._bind_update_worker(self.update_worker)
        self.update_worker.start()

    def _load_company_list(self) -> None:
        """Carrega todas as empresas do banco e popula o autocompletador."""
        try:
            db_path = self.service.db_path
            if not db_path.exists():
                return
            query = """
                SELECT
                    c.cd_cvm,
                    COALESCE(c.company_name, fr.COMPANY_NAME) AS company_name,
                    c.ticker_b3
                FROM companies c
                LEFT JOIN (
                    SELECT CD_CVM, MAX(COMPANY_NAME) AS COMPANY_NAME
                    FROM financial_reports
                    GROUP BY CD_CVM
                ) fr ON fr.CD_CVM = c.cd_cvm
                ORDER BY company_name
            """
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query).fetchall()
            self._companies_cache: list[dict[str, Any]] = [dict(r) for r in rows]
            self.view.set_company_list(self._companies_cache)
        except Exception as exc:
            self.view.append_log(f"Aviso: nao foi possivel carregar lista de empresas ({exc}).")
            self._companies_cache = []

    def on_add_company_requested(self, search_term: str) -> None:
        """Busca a empresa digitada e adiciona à tabela."""
        if not search_term:
            return
        term_lower = search_term.lower()
        companies: list[dict[str, Any]] = getattr(self, "_companies_cache", [])
        match: dict[str, Any] | None = None
        for c in companies:
            label = str(c.get("_label") or "").lower()
            name = str(c.get("company_name") or "").lower()
            ticker = str(c.get("ticker_b3") or "").lower()
            cd_cvm = str(c.get("cd_cvm") or "")
            if (
                term_lower in label
                or term_lower in name
                or term_lower == ticker
                or term_lower == cd_cvm
            ):
                match = c
                break
        if match is None:
            self.view.append_log(f"Empresa nao encontrada: '{search_term}'.")
            return
        self.view.add_company_row(match)
        self.view.append_log(f"Empresa adicionada manualmente: {match.get('company_name')} (CVM {match.get('cd_cvm')}).")
        self._validate_form()

    def on_cancel_requested(self):
        if self.update_worker is None:
            return
        self.update_worker.request_cancel()
        self.view.append_log(
            "Cancelamento solicitado. O processo sera encerrado de forma segura entre empresas."
        )
        self.view.set_status("Cancelamento solicitado...")

    def on_worker_progress(self, completed: int, total: int, company_name: str):
        self.view.set_progress_total(completed, total, company_name)

    def on_worker_success(self, processed_count: int):
        self.view.set_running_state(False)
        self.view.progress_bar.setValue(100)
        self.view.set_status(f"Concluido. Empresas processadas: {processed_count}.")
        self.view.append_log("Atualizacao finalizada com sucesso.")
        self._refresh_base_health(force_refresh=True)
        self._cleanup_update_worker()
        self._validate_form()

    def on_worker_cancelled(self):
        self.view.set_running_state(False)
        self.view.set_status("Atualizacao cancelada com seguranca.")
        self.view.append_log("Execucao cancelada.")
        self._refresh_base_health(force_refresh=True)
        self._cleanup_update_worker()
        self._validate_form()

    def on_worker_failed(self, error_trace: str):
        self.view.set_running_state(False)
        self.view.set_status("Falha na atualizacao.")
        self.view.append_log("Erro durante a execucao:")
        for line in error_trace.strip().splitlines():
            self.view.append_log(line)
        self._refresh_base_health(force_refresh=True)
        self._cleanup_update_worker()
        self._validate_form()


def _build_dark_palette() -> "QPalette":
    """Dark QPalette for Fusion style — makes all native controls respect the dark theme.

    Without this, Fusion uses a light QPalette by default on Windows, causing
    QPalette::Text (black) to paint on dark QSS backgrounds → invisible text.
    """
    p = QPalette()
    # Backgrounds
    p.setColor(QPalette.ColorRole.Window,          QColor("#0b1220"))
    p.setColor(QPalette.ColorRole.Base,            QColor("#111827"))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor("#1f2937"))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#1f2937"))
    p.setColor(QPalette.ColorRole.Button,          QColor("#1f2937"))
    # Foregrounds
    p.setColor(QPalette.ColorRole.WindowText,      QColor("#e5e7eb"))
    p.setColor(QPalette.ColorRole.Text,            QColor("#e5e7eb"))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor("#e5e7eb"))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor("#e5e7eb"))
    p.setColor(QPalette.ColorRole.BrightText,      QColor("#f9fafb"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6b7280"))
    p.setColor(QPalette.ColorRole.Link,            QColor("#60a5fa"))
    # Selection
    p.setColor(QPalette.ColorRole.Highlight,       QColor("#2563eb"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    # Disabled group — muted versions
    D = QPalette.ColorGroup.Disabled
    p.setColor(D, QPalette.ColorRole.WindowText,   QColor("#6b7280"))
    p.setColor(D, QPalette.ColorRole.Text,         QColor("#6b7280"))
    p.setColor(D, QPalette.ColorRole.ButtonText,   QColor("#6b7280"))
    p.setColor(D, QPalette.ColorRole.Base,         QColor("#0f172a"))
    p.setColor(D, QPalette.ColorRole.Button,       QColor("#111827"))
    return p


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_build_dark_palette())
    app.setStyleSheet(APP_STYLESHEET)

    root = Path(__file__).resolve().parent
    window = MainWindow()
    service = IntelligentSelectorService(project_root=root)
    controller = UpdateController(window, service)
    window._controller = controller  # keep reference
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
