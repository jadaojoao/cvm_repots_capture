# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from desktop.services import IntelligentSelectorService
from src.contracts import CompanyRefreshResult, RefreshPolicy, RefreshRequest
from src.refresh_service import HeadlessRefreshService
from src.settings import build_settings


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
                root_dir = Path(__file__).resolve().parent.parent
                log_dir = root_dir / "output" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                error_log = log_dir / "updater_worker_errors.log"
                with open(error_log, "a", encoding="utf-8") as fh:
                    fh.write(f"\n[{datetime.now().isoformat()}]\n{tb}\n")
            except Exception:
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

    def _project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def _build_refresh_request(self, root_dir: Path | None = None) -> RefreshRequest:
        root = root_dir or self._project_root()
        settings = build_settings(project_root=root)
        return RefreshRequest(
            companies=tuple(self._companies),
            start_year=self._start_year,
            end_year=self._end_year,
            max_workers=self._max_workers,
            data_dir=str(settings.paths.input_dir),
            output_dir=str(settings.paths.reports_dir),
            policy=RefreshPolicy(
                skip_complete_company_years=self._skip_complete_company_years,
                enable_fast_lane=self._enable_fast_lane,
                force_refresh=self._force_refresh,
            ),
        )

    def _headless_service(self, root_dir: Path | None = None) -> HeadlessRefreshService:
        root = root_dir or self._project_root()
        return HeadlessRefreshService(settings=build_settings(project_root=root))

    def _build_company_year_plan(
        self,
        db_path: Path,
    ) -> tuple[list[str], dict[int, list[int]], dict[str, int]]:
        service = self._headless_service()
        request = self._build_refresh_request()
        return service.build_company_year_plan(request, db_path_override=db_path)

    def request_cancel(self):
        self._cancel_requested = True

    def _should_cancel(self):
        if self._cancel_requested:
            self._cancel_triggered = True
            return True
        return False

    def _on_progress(self, current, total, company_name):
        self.progress_changed.emit(int(current), int(total), str(company_name))

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
            pass

    def _sync_refresh_status(self, db_path: Path, results: dict[str, Any]) -> int:
        service = self._headless_service()
        request = self._build_refresh_request()
        companies = tuple(
            CompanyRefreshResult.from_payload(payload if isinstance(payload, dict) else {})
            for payload in results.values()
        )
        return service.sync_refresh_status(
            request=request,
            companies=companies,
            db_path_override=db_path,
        )

    def run(self):
        try:
            root_dir = self._project_root()
            db_path = build_settings(project_root=root_dir).paths.db_path
            service = self._headless_service(root_dir)
            request = self._build_refresh_request(root_dir)

            planned_companies, _company_year_overrides, plan_stats = service.build_company_year_plan(
                request,
                db_path_override=db_path,
            )
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

            log_stream = SignalLogStream(self.log_message.emit)
            self.status_changed.emit("Executando atualizacao...")

            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                result = service.execute(
                    request=request,
                    progress_callback=self._on_progress,
                    should_cancel=self._should_cancel,
                )
            log_stream.flush()

            for company_result in result.companies:
                if company_result.status not in {"success", "no_data"}:
                    self._append_worker_error_log(
                        root_dir=root_dir,
                        company_name=company_result.company_name,
                        payload=company_result.to_dict(),
                    )

            if result.synced_companies > 0:
                self.log_message.emit(
                    f"Sync Dashboard: status atualizado para {result.synced_companies} empresa(s)."
                )

            self.log_message.emit(
                f"Resumo do lote: success={result.success_count}, "
                f"sem_dados={result.no_data_count}, erro={result.error_count}."
            )
            if result.cancelled:
                self.cancelled.emit()
                return
            self.finished_success.emit(result.success_count)
        except Exception:
            tb = traceback.format_exc()
            self._append_worker_error_log(
                root_dir=self._project_root(),
                company_name="__worker__",
                payload={"status": "error", "error": "Unhandled worker failure", "traceback": tb},
            )
            self.failed.emit(tb)
