# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import sqlite3
import traceback
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from desktop.services import IntelligentSelectorService
from src.scraper import CVMScraper


class HealthWorker(QThread):
    health_ready = pyqtSignal(dict)
    health_failed = pyqtSignal(str)

    def __init__(
        self,
        service: IntelligentSelectorService,
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
                # workers.py lives in desktop/; project root is two levels up
                root_dir = Path(__file__).resolve().parent.parent
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
    REQUIRED_PACKAGE_STATEMENTS = ("BPA", "BPP", "DRE", "DFC")
    FAST_LANE_RECENT_YEARS = 2
    MAX_AUTO_REPORTING_YEAR_LAG = 1

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
        skip_complete_company_years: bool = True,
        enable_fast_lane: bool = True,
        force_refresh: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._companies = companies
        self._start_year = start_year
        self._end_year = end_year
        self._max_workers = max_workers
        self._skip_complete_company_years = bool(skip_complete_company_years)
        self._enable_fast_lane = bool(enable_fast_lane)
        self._force_refresh = bool(force_refresh)
        self._cancel_requested = False
        self._cancel_triggered = False

    def _load_complete_company_years(
        self,
        db_path: Path,
        company_codes: list[int],
    ) -> dict[int, set[int]]:
        if self._force_refresh or not self._skip_complete_company_years:
            return {}
        if not company_codes or not db_path.exists():
            return {}

        try:
            with sqlite3.connect(str(db_path)) as conn:
                if not self._table_exists(conn, "financial_reports"):
                    return {}

                placeholders_company = ",".join("?" for _ in company_codes)
                placeholders_stmt = ",".join("?" for _ in self.REQUIRED_PACKAGE_STATEMENTS)
                query = f"""
                    SELECT
                        "CD_CVM" AS cd_cvm,
                        "REPORT_YEAR" AS report_year,
                        COUNT(DISTINCT "STATEMENT_TYPE") AS stmt_count
                    FROM financial_reports
                    WHERE "CD_CVM" IN ({placeholders_company})
                      AND "REPORT_YEAR" BETWEEN ? AND ?
                      AND "STATEMENT_TYPE" IN ({placeholders_stmt})
                    GROUP BY "CD_CVM", "REPORT_YEAR"
                    HAVING COUNT(DISTINCT "STATEMENT_TYPE") >= ?
                """
                required_count = len(self.REQUIRED_PACKAGE_STATEMENTS)
                params: list[Any] = [
                    *[int(cd) for cd in company_codes],
                    int(self._start_year),
                    int(self._end_year),
                    *self.REQUIRED_PACKAGE_STATEMENTS,
                    int(required_count),
                ]
                rows = conn.execute(query, params).fetchall()
        except Exception:
            return {}

        completed_map: dict[int, set[int]] = defaultdict(set)
        for row in rows:
            try:
                cd = int(row[0])
                year = int(row[1])
            except Exception:
                continue
            completed_map[cd].add(year)
        return dict(completed_map)

    def _build_company_year_plan(
        self,
        db_path: Path,
    ) -> tuple[list[str], dict[int, list[int]], dict[str, int]]:
        raw_years_scope = list(range(int(self._start_year), int(self._end_year) + 1))
        max_auto_year = datetime.now().year - self.MAX_AUTO_REPORTING_YEAR_LAG
        years_scope = [int(y) for y in raw_years_scope if int(y) <= int(max_auto_year)]
        if not years_scope:
            return [], {}, {
                "requested_company_years": 0,
                "planned_company_years": 0,
                "skipped_complete_company_years": 0,
                "deferred_fast_lane_company_years": 0,
                "planned_companies": 0,
                "skipped_companies_all_complete": 0,
                "dropped_future_years": int(len(raw_years_scope)),
            }

        unique_company_codes: list[int] = []
        seen_codes: set[int] = set()
        for raw in self._companies:
            try:
                cd = int(raw)
            except Exception:
                continue
            if cd in seen_codes:
                continue
            seen_codes.add(cd)
            unique_company_codes.append(cd)

        completed_map = self._load_complete_company_years(db_path, unique_company_codes)

        recent_floor_year = datetime.now().year - (self.FAST_LANE_RECENT_YEARS - 1)
        planned_companies: list[str] = []
        company_year_overrides: dict[int, list[int]] = {}

        skipped_complete_company_years = 0
        deferred_fast_lane_company_years = 0
        skipped_companies_all_complete = 0

        for cd in unique_company_codes:
            completed_years = completed_map.get(cd, set())
            years_needed = [int(y) for y in years_scope if int(y) not in completed_years]
            skipped_complete_company_years += (len(years_scope) - len(years_needed))

            if not years_needed:
                skipped_companies_all_complete += 1
                continue

            years_to_run = years_needed
            if self._enable_fast_lane and not self._force_refresh:
                recent_years = [int(y) for y in years_needed if int(y) >= int(recent_floor_year)]
                if recent_years:
                    deferred_fast_lane_company_years += (len(years_needed) - len(recent_years))
                    years_to_run = recent_years

            if not years_to_run:
                skipped_companies_all_complete += 1
                continue

            planned_companies.append(str(cd))
            company_year_overrides[int(cd)] = sorted(set(int(y) for y in years_to_run))

        stats = {
            "requested_company_years": int(len(unique_company_codes) * len(raw_years_scope)),
            "planned_company_years": int(sum(len(v) for v in company_year_overrides.values())),
            "skipped_complete_company_years": int(skipped_complete_company_years),
            "deferred_fast_lane_company_years": int(deferred_fast_lane_company_years),
            "planned_companies": int(len(planned_companies)),
            "skipped_companies_all_complete": int(skipped_companies_all_complete),
            "dropped_future_years": int(len(raw_years_scope) - len(years_scope)),
        }
        return planned_companies, company_year_overrides, stats

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
                if raw_status == "success":
                    status = "success"
                elif raw_status == "no_data":
                    status = "no_data"
                else:
                    status = "error"

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
            # workers.py lives in desktop/; project root is two levels up
            root_dir = Path(__file__).resolve().parent.parent
            data_dir = str(root_dir / "data" / "input")
            output_dir = str(root_dir / "output" / "reports")
            db_path = root_dir / "data" / "db" / "cvm_financials.db"

            planned_companies, company_year_overrides, plan_stats = self._build_company_year_plan(db_path)
            self.log_message.emit(
                "Planejamento de execucao: "
                f"solicitado={plan_stats['requested_company_years']} empresa-anos, "
                f"planejado={plan_stats['planned_company_years']}, "
                f"skip_completos={plan_stats['skipped_complete_company_years']}, "
                f"adiados_fast_lane={plan_stats['deferred_fast_lane_company_years']}."
            )
            if plan_stats.get("dropped_future_years", 0) > 0:
                self.log_message.emit(
                    "Filtro automatico: "
                    f"{plan_stats['dropped_future_years']} ano(s) futuro(s) foram ignorados no planejamento."
                )
            if plan_stats["skipped_companies_all_complete"] > 0:
                self.log_message.emit(
                    "Skip inteligente: "
                    f"{plan_stats['skipped_companies_all_complete']} empresa(s) ja completas no periodo."
                )

            if not planned_companies:
                self.status_changed.emit("Nada para atualizar no periodo selecionado.")
                self.log_message.emit("Nenhuma empresa com anos pendentes apos aplicar politicas de skip/fast lane.")
                self.finished_success.emit(0)
                return

            self.log_message.emit(f"Paralelismo definido: {self._max_workers} worker(s).")
            if self._enable_fast_lane and not self._force_refresh:
                self.log_message.emit("Fast Lane automatico ativo para anos recentes (janela de 2 anos).")
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
                    companies=planned_companies,
                    start_year=self._start_year,
                    end_year=self._end_year,
                    company_year_overrides=company_year_overrides,
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
                # workers.py lives in desktop/; project root is two levels up
                root_dir=Path(__file__).resolve().parent.parent,
                company_name="__worker__",
                payload={"status": "error", "error": "Unhandled worker failure", "traceback": tb},
            )
            self.failed.emit(tb)
