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

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:
    print("PyQt6 nao encontrado. Instale as dependencias com: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from desktop.controller import UpdateController
from desktop.services import IntelligentSelectorService
from desktop.ui import APP_STYLESHEET, MainWindow, _build_dark_palette


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_build_dark_palette())
    app.setStyleSheet(APP_STYLESHEET)

    # cvm_pyqt_app.py lives in desktop/; project root is one level up
    root = Path(__file__).resolve().parent.parent
    window = MainWindow()
    service = IntelligentSelectorService(project_root=root)
    controller = UpdateController(window, service)
    window._controller = controller  # keep reference
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
