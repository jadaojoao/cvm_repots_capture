# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
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


def _build_dark_palette() -> QPalette:
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


class MainWindow(QMainWindow):
    build_requested = pyqtSignal(int, int, int)
    start_requested = pyqtSignal(list, int, int, int)
    cancel_requested = pyqtSignal()
    dashboard_requested = pyqtSignal()
    years_changed = pyqtSignal(int, int)
    preset_selected = pyqtSignal(str)
    selection_changed = pyqtSignal(int)
    add_company_requested = pyqtSignal(str)
    base_health_refresh_requested = pyqtSignal()
    base_health_priorities_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._internal_update = False
        self._is_running = False
        self._is_building = False
        self._can_start = False
        self._last_base_health_snapshot: dict[str, Any] | None = None

        self._build_ui()
        self._wire_signals()
        self._emit_years_changed()

    def _build_ui(self):
        self.setWindowTitle("CVM Analytics - Updater Inteligente")
        self.setMinimumSize(780, 540)

        current_year = datetime.now().year
        latest_reporting_year = max(1990, current_year - 1)

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
        self.start_year_spin.setValue(max(1990, latest_reporting_year - 2))
        self.start_year_spin.setMinimumWidth(75)

        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(1990, current_year + 1)
        self.end_year_spin.setValue(latest_reporting_year)
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

        years_row_h, self.health_years_label = _health_row("Tendencia")
        health_layout.addWidget(years_row_h)

        laggards_row, self.health_laggards_label = _health_row("Riscos e prioridades")
        health_layout.addWidget(laggards_row)

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        self.health_refresh_button = QPushButton("Recalcular Saude")
        self.health_refresh_button.setObjectName("buildButton")
        self.health_refresh_button.setMinimumWidth(160)

        self.health_priorities_button = QPushButton("Ver Prioridades")
        self.health_priorities_button.setObjectName("dashboardButton")
        self.health_priorities_button.setMinimumWidth(140)
        self.health_priorities_button.setEnabled(False)

        actions_layout.addWidget(self.health_refresh_button)
        actions_layout.addWidget(self.health_priorities_button)
        actions_layout.addStretch(1)
        health_layout.addWidget(actions_row)

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
        self.health_refresh_button.clicked.connect(lambda: self.base_health_refresh_requested.emit())
        self.health_priorities_button.clicked.connect(lambda: self.base_health_priorities_requested.emit())

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
        self.health_refresh_button.setEnabled((not building) and (not self._is_running))
        self.health_priorities_button.setEnabled((not building) and (not self._is_running) and self._last_base_health_snapshot is not None)

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
        self.health_refresh_button.setEnabled((not running) and (not self._is_building))
        self.health_priorities_button.setEnabled((not running) and (not self._is_building) and self._last_base_health_snapshot is not None)

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
            self._last_base_health_snapshot = None
            self.health_global_label.setText("Cobertura indisponivel.")
            self.health_years_label.setText("N/D")
            self.health_laggards_label.setText("N/D")
            self.health_global_label.setStyleSheet("color: #e5e7eb; font-size: 12px;")
            self.health_priorities_button.setEnabled(False)
            return

        self._last_base_health_snapshot = snapshot

        global_stats = snapshot.get("global", {})
        pct = float(global_stats.get("pct", 0.0) or 0.0)
        complete = int(global_stats.get("completed_cells", 0) or 0)
        expected = int(global_stats.get("total_cells", 0) or 0)
        missing = int(global_stats.get("missing_cells", 0) or 0)
        eta_text = self._format_eta(global_stats.get("eta_hours"))
        throughput = snapshot.get("throughput", {})
        confidence = str(throughput.get("confidence") or "low")
        health_score = float(snapshot.get("health_score", 0.0) or 0.0)
        health_status = str(snapshot.get("health_status") or "atencao")

        if health_status == "critico":
            status_label = "CRITICO"
            status_color = "#f87171"
        elif health_status == "ok":
            status_label = "OK"
            status_color = "#34d399"
        else:
            status_label = "ATENCAO"
            status_color = "#fbbf24"

        self.health_global_label.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: 600;")

        self.health_global_label.setText(
            f"Status {status_label} | Score {health_score:.1f}/100 | {pct:.1f}% concluido ({complete}/{expected}) | faltantes: {missing} | {eta_text} | confianca ETA: {confidence}"
        )

        progress_delta = snapshot.get("progress_delta", {})
        delta_pct = float(progress_delta.get("delta_pct", 0.0) or 0.0)
        delta_cells = int(progress_delta.get("delta_completed_cells", 0) or 0)
        trend = str(progress_delta.get("trend") or "estavel")

        if delta_pct > 0:
            delta_pct_txt = f"+{delta_pct:.2f} pp"
        elif delta_pct < 0:
            delta_pct_txt = f"{delta_pct:.2f} pp"
        else:
            delta_pct_txt = "0.00 pp"

        if delta_cells > 0:
            delta_cells_txt = f"+{delta_cells} celulas"
        elif delta_cells < 0:
            delta_cells_txt = f"{delta_cells} celulas"
        else:
            delta_cells_txt = "0 celulas"

        per_year_entries: list[str] = []
        per_year_rows = sorted(snapshot.get("per_year", []), key=lambda row: int(row.get("year", 0)))
        for row in per_year_rows[-3:]:
            year = row.get("year")
            year_pct = float(row.get("pct", 0.0) or 0.0)
            year_missing = int(row.get("missing", 0) or 0)
            per_year_entries.append(f"{year}: {year_pct:.1f}% (faltam {year_missing})")
        trend_text = f"Tendencia {trend} | delta {delta_pct_txt} | {delta_cells_txt}"
        self.health_years_label.setText(
            f"{trend_text} | " + " | ".join(per_year_entries) if per_year_entries else trend_text
        )

        risks = snapshot.get("risks_summary", {})
        high_risk = int(risks.get("high", 0) or 0)
        medium_risk = int(risks.get("medium", 0) or 0)
        low_risk = int(risks.get("low", 0) or 0)

        priorities = snapshot.get("prioritized_companies", [])
        priority_parts: list[str] = []
        for row in priorities[:3]:
            name = str(row.get("company_name") or f"CVM {row.get('cd_cvm')}")
            miss = int(row.get("missing_years_count", 0) or 0)
            action = str(row.get("recommended_action") or "Revisar")
            priority_parts.append(f"{name} (faltam {miss}, {action})")

        risks_text = f"Risco alto: {high_risk} | medio: {medium_risk} | baixo: {low_risk}"
        if priority_parts:
            risks_text += " | Prioridades: " + " ; ".join(priority_parts)
        self.health_laggards_label.setText(risks_text)
        self.health_priorities_button.setEnabled(bool(priorities) and not self._is_running and not self._is_building)

    def show_base_health_priorities_dialog(self) -> None:
        snapshot = self._last_base_health_snapshot or {}
        priorities = snapshot.get("prioritized_companies", [])
        if not priorities:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Prioridades de Atualizacao")
        dlg.resize(960, 460)

        layout = QVBoxLayout(dlg)
        title = QLabel(
            f"Top {len(priorities)} empresas com maior impacto para cobertura no periodo selecionado."
        )
        title.setWordWrap(True)
        title.setStyleSheet("color: #93c5fd; font-weight: 600;")
        layout.addWidget(title)

        table = QTableWidget(len(priorities), 7)
        table.setHorizontalHeaderLabels(
            [
                "Empresa",
                "CVM",
                "Risco",
                "Faltam (anos)",
                "Gap lider",
                "Motivo",
                "Acao recomendada",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        for idx, row in enumerate(priorities):
            table.setItem(idx, 0, QTableWidgetItem(str(row.get("company_name") or "")))
            table.setItem(idx, 1, QTableWidgetItem(str(row.get("cd_cvm") or "")))
            table.setItem(idx, 2, QTableWidgetItem(str(row.get("risk_level") or "")))
            table.setItem(idx, 3, QTableWidgetItem(str(int(row.get("missing_years_count", 0) or 0))))
            table.setItem(idx, 4, QTableWidgetItem(str(int(row.get("gap_to_leader_years", 0) or 0))))
            table.setItem(idx, 5, QTableWidgetItem(str(row.get("reason") or "")))
            table.setItem(idx, 6, QTableWidgetItem(str(row.get("recommended_action") or "")))

        layout.addWidget(table)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Fechar")
        close_btn.setObjectName("dashboardButton")
        close_btn.clicked.connect(dlg.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        dlg.exec()

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
