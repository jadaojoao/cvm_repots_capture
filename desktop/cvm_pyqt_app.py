"""
CVM Analytics - PyQt6 Desktop Updater (Intelligent Mode)

Entry point only. Business logic is split into:
  desktop/services.py   — IntelligentSelectorService, RankedCompany
  desktop/workers.py    — UpdateWorker, RankingWorker, HealthWorker, SignalLogStream
  desktop/ui.py         — APP_STYLESHEET, _build_dark_palette, MainWindow
  desktop/controller.py — UpdateController
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:
    print("PyQt6 nao encontrado. Instale as dependencias com: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from desktop.controller import UpdateController
from desktop.services import IntelligentSelectorService
from desktop.ui import APP_STYLESHEET, MainWindow, _build_dark_palette
from src.settings import build_settings
from src.startup import collect_startup_report, format_startup_report


def main() -> int:
    settings = build_settings(project_root=ROOT)
    startup_report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports", "companies"),
        require_canonical_accounts=True,
    )
    if startup_report.errors:
        print(format_startup_report(startup_report))
        return 1
    if startup_report.warnings:
        print(format_startup_report(startup_report))

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_build_dark_palette())
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    service = IntelligentSelectorService(settings=settings)
    controller = UpdateController(window, service)
    window._controller = controller  # keep reference
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
