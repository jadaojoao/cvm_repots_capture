# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject

from desktop.services import IntelligentSelectorService
from desktop.ui import MainWindow
from desktop.workers import HealthWorker, RankingWorker, UpdateWorker


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
        self._skip_complete_company_years = os.getenv("UPDATER_SKIP_COMPLETE", "1") != "0"
        self._enable_fast_lane = os.getenv("UPDATER_FAST_LANE", "1") != "0"
        self._force_refresh_updates = os.getenv("UPDATER_FORCE_REFRESH", "0") == "1"
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
        self.view.base_health_refresh_requested.connect(self.on_base_health_refresh_requested)
        self.view.base_health_priorities_requested.connect(self.on_base_health_priorities_requested)

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
        latest_reporting_year = max(1990, datetime.now().year - 1)
        start_year = latest_reporting_year - (n_years - 1)
        self.view.set_years(start_year, latest_reporting_year)

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
        self.view.append_log(
            "Politicas: "
            f"skip_completos={'on' if self._skip_complete_company_years else 'off'}, "
            f"fast_lane={'on' if self._enable_fast_lane else 'off'}, "
            f"force_refresh={'on' if self._force_refresh_updates else 'off'}."
        )
        self.view.reset_progress()
        self.view.set_status("Preparando execucao...")
        self.view.set_running_state(True)

        self.update_worker = UpdateWorker(
            companies=company_codes,
            start_year=start_year,
            end_year=end_year,
            max_workers=max_workers,
            skip_complete_company_years=self._skip_complete_company_years,
            enable_fast_lane=self._enable_fast_lane,
            force_refresh=self._force_refresh_updates,
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

    def on_base_health_refresh_requested(self) -> None:
        if self.health_worker is not None:
            return
        self.view.append_log("Recalculando Saude da Base (force refresh)...")
        self._refresh_base_health(force_refresh=True)

    def on_base_health_priorities_requested(self) -> None:
        self.view.show_base_health_priorities_dialog()

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
